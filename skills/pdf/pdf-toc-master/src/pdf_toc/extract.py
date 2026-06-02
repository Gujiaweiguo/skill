#!/usr/bin/env python3
"""
PDF TOC Master — OCR Pipeline

Extracts table of contents from scanned PDF TOC pages using EasyOCR,
merges same-line text, pairs with nearest page number, applies OCR corrections,
and embeds clickable bookmarks into the PDF.

Usage:
    pdf-toc-extract <input.pdf> [output.pdf] --offset N --toc-start M --toc-end K

Examples:
    # Manual: printed_page + 8 = PDF page index, TOC is on pages 6-8
    pdf-toc-extract book.pdf --offset 8 --toc-start 6 --toc-end 8

    # Auto crop: output replaces book.pdf with book-toc.pdf
    pdf-toc-extract book.pdf --offset 12 --toc-start 4 --toc-end 6

Dependencies:
    python-deps: pypdf pdf2image easyocr Pillow
    system: poppler-utils for pdf2image
"""

from __future__ import annotations

import argparse
import re
from typing import Any

import pdf2image
from pypdf import PdfReader, PdfWriter


CONF_THRESHOLD: float = 0.5


def extract_toc(
    pdf_path: str, output_path: str | None = None,
    offset: int = 0, dpi: int = 200,
    toc_start: int = 1, toc_end: int = 3,
    conf_threshold: float = CONF_THRESHOLD,
) -> list[dict[str, Any]]:

    if output_path is None:
        output_path = pdf_path.replace(".pdf", "-toc.pdf")

    import easyocr
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(["ch_sim", "en"], gpu=False)

    print(f"Converting PDF pages {toc_start}-{toc_end} to images (dpi={dpi})...")
    images = pdf2image.convert_from_path(
        pdf_path,
        first_page=toc_start,
        last_page=toc_end,
        dpi=dpi,
        fmt="jpeg",
    )

    all_entries: list[dict[str, Any]] = []

    for img_idx, img in enumerate(images):
        src_page = toc_start + img_idx
        results = reader.readtext(img, detail=1, paragraph=False)

        # Collect all OCR blocks
        blocks = []
        for bbox, text, conf in results:
            if float(conf) > conf_threshold and text:
                cleaned = text.strip()
                blocks.append({
                    "text": cleaned,
                    "conf": conf,
                    "x": (float(bbox[0][0]) + float(bbox[2][0])) / 2,
                    "y": (float(bbox[0][1]) + float(bbox[2][1])) / 2,
                })

        # Column split: pick the gap closest to page center with text on both sides
        def has_text(blk_list):
            return any(b["text"] for b in blk_list)

        all_x = sorted(set(b["x"] for b in blocks))
        col_split = 0
        if len(all_x) >= 4:
            x_range = max(all_x) - min(all_x)
            center_x = (min(all_x) + max(all_x)) / 2
            gaps = [(all_x[i + 1] - all_x[i], all_x[i]) for i in range(len(all_x) - 1)]
            best_gap, best_dist = 0, float("inf")
            for gap_size, gap_start in gaps:
                if gap_size < x_range * 0.06:
                    continue
                split_x = gap_start + gap_size / 2
                left_blocks = [b for b in blocks if b["x"] < split_x]
                right_blocks = [b for b in blocks if b["x"] > split_x]
                if has_text(left_blocks) and has_text(right_blocks):
                    dist = abs(split_x - center_x)
                    if dist < best_dist:
                        best_dist, best_gap = dist, split_x
            col_split = best_gap

        def group_into_lines(blk_list):
            if not blk_list:
                return []
            sorted_b = sorted(blk_list, key=lambda b: (b["y"], b["x"]))
            grouped = []
            cur_line, cur_y = [], None
            for b in sorted_b:
                if cur_y is None or abs(b["y"] - cur_y) > 10:
                    if cur_line:
                        grouped.append(cur_line)
                    cur_line, cur_y = [b], b["y"]
                else:
                    cur_line.append(b)
            if cur_line:
                grouped.append(cur_line)
            return grouped

        if col_split > 0:
            left_lines = group_into_lines([b for b in blocks if b["x"] < col_split])
            right_lines = group_into_lines([b for b in blocks if b["x"] > col_split])
            cols = [("left", left_lines), ("right", right_lines)]
        else:
            left_lines = group_into_lines(blocks)
            cols = [("single", left_lines)]

        page_count = 0
        for col_name, lines in cols:
            for line in lines:
                line_sorted = sorted(line, key=lambda b: b["x"])
                def _is_page_num(b):
                    clean = b["text"].lstrip("/").strip(".,，。、:：_ ")
                    return bool(re.match(r"^\d{2,4}$", clean))

                text_blocks = [b for b in line_sorted if not _is_page_num(b)]
                number_blocks = [b for b in line_sorted if _is_page_num(b)]
                rightmost_num = None
                if number_blocks and text_blocks:
                    last_text_x = max(b["x"] for b in text_blocks)
                    rightmost = max(number_blocks, key=lambda b: b["x"])
                    if rightmost["x"] > last_text_x:
                        clean = rightmost["text"].lstrip("/").strip(".,，。、:：_ ")
                        m = re.match(r"^\d{2,4}$", clean)
                        if m:
                            rightmost_num = int(m.group())
                # OCR correction: strip leading "1" prefix (e.g., 1001→001)
                if rightmost_num and rightmost_num > 999:
                    s = str(rightmost_num)
                    for i in range(1, len(s)):
                        cand = int(s[i:])
                        if cand < rightmost_num:
                            rightmost_num = cand
                            break
                texts = [b["text"] for b in text_blocks]
                title = re.sub(r"\s+", " ", " ".join(texts)).strip()
                if title and rightmost_num is not None:
                    all_entries.append({
                        "title": title,
                        "printed_page": rightmost_num,
                        "pdf_page": rightmost_num + offset,
                        "y": line[0]["y"],
                        "src_page": src_page,
                        "col": col_name,
                    })
                    page_count += 1
                elif title:
                    print(f"  ⚠ No page# [{col_name}]: {title[:50]}")

        print(f"  Page {src_page}: {page_count} entries")

    # --- Sort by content page number ---
    all_entries.sort(key=lambda e: e["printed_page"])  # type: ignore[typeddict-item]

    # --- Deduplicate ---
    seen, deduped = set(), []
    for e in all_entries:
        key = (e["title"], e["printed_page"])
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    all_entries = deduped

    # --- Embed bookmarks ---
    print(f"\nEmbedding {len(all_entries)} bookmarks (offset={offset})...")
    reader_pdf = PdfReader(pdf_path)
    writer = PdfWriter()
    writer.append(reader_pdf)

    for entry in all_entries:
        pdf_idx = entry["pdf_page"] - 1  # type: ignore[operator]
        if 0 <= pdf_idx < len(reader_pdf.pages):
            writer.add_outline_item(
                title=str(entry["title"]),
                page_number=pdf_idx,
            )

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"✓ Saved: {output_path}")
    print(f"  Bookmarks: {len(writer.outline)}\n  PDF Pages: {len(reader_pdf.pages)}")

    # Show first/last few entries for verification
    print("\n  Sample entries:")
    for e in all_entries[:5]:
        print(f"    {e['printed_page']:>3} → {e['title'][:50]}")
    if len(all_entries) > 5:
        print(f"    ... ({len(all_entries) - 10} more)" if len(all_entries) > 10
              else "")
        for e in all_entries[-5:]:
            print(f"    {e['printed_page']:>3} → {e['title'][:50]}")

    return all_entries


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="PDF TOC Master — OCR pipeline for table of contents extraction"
    )
    parser.add_argument("input_pdf", help="Path to the input PDF file")
    parser.add_argument(
        "output_pdf", nargs="?", default=None,
        help="Output PDF path (default: input-toc.pdf)",
    )
    parser.add_argument(
        "--offset", type=int, default=0,
        help="PDF page index = printed_page + offset (default: 0)",
    )
    parser.add_argument(
        "--toc-start", type=int, default=1,
        help="First page of TOC in PDF, 1-indexed (default: 1)",
    )
    parser.add_argument(
        "--toc-end", type=int, default=3,
        help="Last page of TOC in PDF, 1-indexed (default: 3)",
    )
    parser.add_argument(
        "--dpi", type=int, default=200,
        help="DPI for PDF-to-image conversion (default: 200)",
    )
    args = parser.parse_args(argv)

    if args.offset == 0 and args.toc_start == 1 and args.toc_end == 3:
        print("⚠ Using defaults: offset=0, toc_start=1, toc_end=3")
        print("  For correct results, specify:")
        print("    --offset N     PDF page index = printed_page + N")
        print("    --toc-start M  First TOC page number")
        print("    --toc-end K    Last TOC page number")
        print()

    extract_toc(
        args.input_pdf, args.output_pdf,
        offset=args.offset, dpi=args.dpi,
        toc_start=args.toc_start, toc_end=args.toc_end,
    )


if __name__ == "__main__":
    main()
