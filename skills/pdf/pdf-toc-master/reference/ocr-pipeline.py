#!/usr/bin/env python3
"""
PDF TOC Master — OCR Pipeline Reference Implementation

Extracts table of contents from scanned PDF TOC pages using EasyOCR,
merges same-line text, pairs with nearest page number, applies OCR corrections,
and embeds clickable bookmarks into the PDF.

Usage:
    python3 ocr-pipeline.py <input.pdf> [output.pdf]

Dependencies:
    pip install pypdf pdf2image easyocr Pillow
    (system: poppler-utils for pdf2image)

Offsets:
    The script uses an OFFSET constant to map printed page numbers to PDF page indices.
    This offset must be determined per-PDF by cross-referencing TOC sample points.
    For 吉他指弹曲200首大合集: offset = 8 (printed page + 8 = PDF page index)
"""

import pdf2image  # type: ignore
import easyocr  # type: ignore
import re
import sys
from pypdf import PdfReader, PdfWriter

# ==================== CONFIGURATION ====================
OFFSET = 8            # Printed page → PDF page offset
CONF_THRESHOLD = 0.5  # Minimum OCR confidence
DPI = 200             # PDF→image resolution
TOC_PAGES = (6, 8)    # (first_page, last_page) of TOC in PDF (1-indexed)

# ==================== OCR POST-PROCESSING ====================
PHRASE_CORRECTIONS = {
    '历史的夭空': '历史的天空',
    '万水干山总是情': '万水千山总是情',
    '大壬叫我来巡山': '大王叫我来巡山',
}

CHAR_CORRECTIONS = {
    '夭': '天',     # 天空 → 夭空 (common OCR error)
    '干': '千',     # 千山 → 干山
    '壬': '王',     # 大王 → 大壬
    '曰': '日',     # 秋日私语 → 秋曰私语
}


def apply_corrections(text: str) -> str:
    """Apply phrase-level and character-level OCR corrections."""
    for wrong, correct in PHRASE_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    for wrong, correct in CHAR_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    return text


# ==================== MAIN PIPELINE ====================
def extract_toc(pdf_path: str, output_path: str | None = None):
    """Main pipeline: OCR → parse → merge → pair → embed → save."""

    if output_path is None:
        output_path = pdf_path.replace('.pdf', '-toc.pdf')

    # ---- Step 1: OCR ----
    print("Initializing EasyOCR...")
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

    print(f"Converting PDF pages {TOC_PAGES[0]}-{TOC_PAGES[1]} to images...")
    images = pdf2image.convert_from_path(
        pdf_path,
        first_page=TOC_PAGES[0],
        last_page=TOC_PAGES[1],
        dpi=DPI,
        fmt='jpeg'
    )

    all_entries = []

    for img_idx, img in enumerate(images):
        src_page = TOC_PAGES[0] + img_idx
        results = reader.readtext(img, detail=1, paragraph=False)

        # Filter and clean blocks
        blocks = []
        for bbox, text, conf in results:
            if float(conf) > CONF_THRESHOLD and text:  # type: ignore[arg-type]
                cleaned = text.strip()
                blocks.append({
                    'text': apply_corrections(cleaned),
                    'conf': conf,
                    'x': (float(bbox[0][0]) + float(bbox[2][0])) / 2,
                    'y': (float(bbox[0][1]) + float(bbox[2][1])) / 2,
                })

        # ---- Step 2: Group into lines (±10px y-tolerance) ----
        sorted_blocks = sorted(blocks, key=lambda b: (b['y'], b['x']))
        lines = []
        cur_line, cur_y = [], None
        for b in sorted_blocks:
            if cur_y is None or abs(b['y'] - cur_y) > 10:
                if cur_line:
                    lines.append(cur_line)
                cur_line, cur_y = [b], b['y']
            else:
                cur_line.append(b)
        if cur_line:
            lines.append(cur_line)

        # ---- Step 3: Merge same-column texts per line ----
        line_entries = []
        for line in lines:
            left_texts, right_texts = [], []
            left_page_blocks, right_page_blocks = [], []

            for b in line:
                is_num = re.match(r'^\d{2,3}$', b['text'])
                x = b['x']
                if is_num:
                    if 690 < x < 730:
                        left_page_blocks.append(b)
                    elif 1500 < x < 1540:
                        right_page_blocks.append(b)
                else:
                    if x < 700:
                        left_texts.append(b['text'])
                    elif x > 850:
                        right_texts.append(b['text'])

            if left_texts:
                line_entries.append({
                    'title': re.sub(r'\s+', ' ', ' '.join(left_texts)).strip(),
                    'y': line[0]['y'], 'col': 'left'
                })
            if right_texts:
                line_entries.append({
                    'title': re.sub(r'\s+', ' ', ' '.join(right_texts)).strip(),
                    'y': line[0]['y'], 'col': 'right'
                })

        # ---- Step 4: Pair titles with nearest page number below ----
        all_left_pages = sorted(
            [b for b in blocks
             if re.match(r'^\d{2,3}$', b['text']) and 690 < b['x'] < 730],
            key=lambda b: b['y']
        )
        all_right_pages = sorted(
            [b for b in blocks
             if re.match(r'^\d{2,3}$', b['text']) and 1500 < b['x'] < 1540],
            key=lambda b: b['y']
        )

        for entry in line_entries:
            pages = all_left_pages if entry['col'] == 'left' else all_right_pages
            best_page, best_dist = None, 999
            for p in pages:
                dist = p['y'] - entry['y']
                if 0 < dist < 80 and dist < best_dist:
                    best_dist, best_page = dist, p
            if best_page:
                all_entries.append({
                    'title': entry['title'],
                    'printed_page': int(best_page['text']),
                    'pdf_page': int(best_page['text']) + OFFSET,
                    'y': entry['y'],
                    'src_page': src_page,
                    'col': entry['col']
                })

        left_count = sum(1 for e in all_entries
                         if e['src_page'] == src_page and e['col'] == 'left')
        right_count = sum(1 for e in all_entries
                          if e['src_page'] == src_page and e['col'] == 'right')
        print(f"  Page {src_page}: {len(lines)} lines → "
              f"{left_count}L + {right_count}R = {left_count + right_count} entries")

    # ---- Step 5: Sort (by source page → y → left before right) ----
    all_entries.sort(key=lambda e: (
        e['src_page'], e['y'], 0 if e['col'] == 'left' else 1
    ))

    # ---- Step 6: Deduplicate ----
    seen, deduped = set(), []
    for e in all_entries:
        key = (e['title'], e['printed_page'])
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    all_entries = deduped

    # ---- Step 7: Embed bookmarks ----
    print(f"\nEmbedding {len(all_entries)} bookmarks...")
    reader_pdf = PdfReader(pdf_path)
    writer = PdfWriter()
    for p in range(len(reader_pdf.pages)):
        writer.add_page(reader_pdf.pages[p])

    for entry in all_entries:
        pdf_idx = entry['pdf_page'] - 1  # 0-indexed
        if 0 <= pdf_idx < len(reader_pdf.pages):
            writer.add_outline_item(
                title=entry['title'],
                page_number=pdf_idx
            )

    with open(output_path, 'wb') as f:
        writer.write(f)

    print(f"✓ Saved: {output_path}")
    print(f"  Bookmarks: {len(writer.outline)} / Pages: {len(reader_pdf.pages)}")

    return all_entries


# ==================== CLI ====================
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 ocr-pipeline.py <input.pdf> [output.pdf]")
        sys.exit(1)
    extract_toc(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
