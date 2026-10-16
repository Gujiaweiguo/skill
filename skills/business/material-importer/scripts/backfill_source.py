#!/usr/bin/env python3
"""Backfill provenance (source:) for lanlnk materials corpus.

- materials/**/*.md lacking `source:` frontmatter → match original in incoming/
  via filename/body hints → insert `source: "raw/<md>"` (dominant convention,
  falls back to `incoming/<relpath>`).
- raw/*.md (top-level markitdown outputs) lacking provenance block →
  prepend HTML comment block with source path + sha256 + extraction note.

PEP 723 inline deps (none needed — stdlib only).
Usage: uv run scripts/backfill_source.py <lanlnk_base> [--dry-run] [--json-report PATH]
"""

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

ORIG_EXTS = {".pptx", ".docx", ".xlsx", ".pdf", ".doc", ".xls", ".ppt"}
SKIP_DIR_NAMES = {"_media", "csv", "parsed", "images", "_extracted"}


def build_incoming_index(incoming: Path):
    by_basename = {}
    by_stem = {}
    for f in incoming.rglob("*"):
        if not f.is_file():
            continue
        b = f.name.lower()
        by_basename.setdefault(b, []).append(f)
        by_stem.setdefault(f.stem.lower(), []).append(f)
    return by_basename, by_stem


def build_raw_index(raw: Path):
    """Map original-basename (e.g. foo.pptx) -> raw md path (top-level raw/*.md)."""
    raw_by_orig = {}
    for f in raw.glob("*.md"):
        stem = f.name[:-3]  # strip .md
        # try progressively longer underscore-split suffixes containing an ext
        parts = stem.split("_")
        for i in range(len(parts)):
            cand = "_".join(parts[i:])
            if Path(cand).suffix.lower() in ORIG_EXTS:
                raw_by_orig.setdefault(cand.lower(), []).append(f)
                break
    return raw_by_orig


def unique(seq):
    s = sorted(set(seq))
    return s[0] if len(s) == 1 else None


def raw_md_for(orig_path: Path, raw_by_orig):
    hits = raw_by_orig.get(orig_path.name.lower(), [])
    return unique(hits)


def match_material(md_path: Path, by_basename, by_stem, raw_by_orig):
    """Return (source_value, confidence) or (None, reason)."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return None, f"read-error: {e}"
    name = md_path.name.lower()
    stem = md_path.stem.lower()

    # 1) exact basename hint in body text (original filename with extension)
    body_hits = [fs[0] for b, fs in by_basename.items() if b in text.lower()]
    if len(body_hits) == 1:
        orig = unique(by_basename[body_hits[0].name.lower()])
        if orig:
            return orig, "exact"

    # 2) material filename contains an incoming basename
    name_hits = [f for b, fs in by_basename.items() if b in name for f in fs]
    if len(name_hits) == 1:
        return name_hits[0], "exact"

    # 3) material stem equals/contains a unique incoming stem
    stem_hits = [f for s, fs in by_stem.items() if s and (s == stem or s in stem) for f in fs]
    if len(stem_hits) == 1:
        return stem_hits[0], "suffix"

    return None, "no-unique-hint"


def source_value_for(orig: Path, base: Path, raw_by_orig):
    """Always point to the canonical incoming original, never to a projection."""
    del raw_by_orig  # retained in the signature for callers built during dry-run design
    return orig.relative_to(base).as_posix(), "incoming"


FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


def insert_source(md_path: Path, value: str):
    text = md_path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    line = f'source: "{value}"'
    if m:
        fm = m.group(1)
        if re.search(r"^source:", fm, re.M):
            return None  # already has source
        new_fm = fm + "\n" + line
        new_text = FM_RE.sub(lambda _: f"---\n{new_fm}\n---\n", text, count=1)
        md_path.write_text(new_text, encoding="utf-8")
        return "frontmatter-appended"
    new_text = f"---\n{line}\n---\n\n" + text
    md_path.write_text(new_text, encoding="utf-8")
    return "frontmatter-created"


PROV_MARK = "source_sha256"


def backfill_raw_md(md_path: Path, base: Path, by_basename):
    """Match raw md to incoming original via longest underscore suffix."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    if PROV_MARK in text[:2000]:
        return None, "already-has-provenance"
    stem = md_path.name[:-3]
    parts = stem.split("_")
    # longest suffix first
    for i in range(len(parts)):
        cand = "_".join(parts[i:])
        if Path(cand).suffix.lower() not in ORIG_EXTS:
            continue
        hits = by_basename.get(cand.lower(), [])
        orig = unique(hits)
        if orig:
            return orig, "suffix"
    return None, "no-suffix-match"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json-report", default=None)
    args = ap.parse_args()
    base = Path(args.base).resolve()
    incoming = base / "incoming"
    raw = base / "raw"
    materials = base / "materials"

    by_basename, by_stem = build_incoming_index(incoming)
    raw_by_orig = build_raw_index(raw)

    report = {"matched": [], "unmatched": [], "skipped": [], "written": 0}
    today = datetime.date.today().isoformat()

    # --- materials ---
    mat_files = [p for p in materials.rglob("*.md") if p.is_file()]
    for md in mat_files:
        text = md.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^source:", text[:4000], re.M):
            report["skipped"].append({"file": str(md.relative_to(base)), "reason": "has-source"})
            continue
        orig, conf = match_material(md, by_basename, by_stem, raw_by_orig)
        if not orig:
            report["unmatched"].append({"file": str(md.relative_to(base)), "reason": conf})
            continue
        value, root = source_value_for(orig, base, raw_by_orig)
        entry = {"file": str(md.relative_to(base)), "source": value,
                 "confidence": conf, "root": root,
                 "original": str(orig.relative_to(base))}
        if not args.dry_run:
            insert_source(md, value)
            report["written"] += 1
        report["matched"].append(entry)

    # --- raw top-level md ---
    for md in sorted(raw.glob("*.md")):
        orig, reason = backfill_raw_md(md, base, by_basename)
        if not orig:
            report["unmatched"].append({"file": str(md.relative_to(base)), "reason": f"raw/{reason}"})
            continue
        sha = hashlib.sha256(orig.read_bytes()).hexdigest()
        entry = {"file": str(md.relative_to(base)),
                 "source": str(orig.relative_to(base)),
                 "confidence": "suffix", "sha256": sha}
        if not args.dry_run:
            block = (f"<!-- source: {orig.relative_to(base).as_posix()} -->\n"
                     f"<!-- source_sha256: {sha} -->\n"
                     f"<!-- extracted_by: markitdown (pre-existing artifact, backfilled {today}) -->\n")
            cur = md.read_text(encoding="utf-8", errors="replace")
            md.write_text(block + cur, encoding="utf-8")
            report["written"] += 1
        report["matched"].append(entry)

    total = len(report["matched"]) + len(report["unmatched"])
    print(f"materials scanned: {len(mat_files)}, skipped(has-source): "
          f"{len([s for s in report['skipped']])}")
    print(f"matched: {len(report['matched'])}  unmatched: {len(report['unmatched'])}  "
          f"(total candidates {total})")
    if total:
        print(f"unmatched ratio: {len(report['unmatched'])/total:.1%}")
    print(f"written: {report['written']} {'(DRY RUN)' if args.dry_run else ''}")

    out = Path(args.json_report) if args.json_report else base / "raw" / "_backfill_report.json" \
        if not args.dry_run else Path("/tmp/opencode/backfill_dryrun_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
