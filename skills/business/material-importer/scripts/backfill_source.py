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
SKIP_DIR_NAMES = {"_media", "csv", "parsed", "images", "_extracted",
                  "__pycache__", ".venv", "node_modules", ".playwright-mcp"}
# whole-base index excludes these top-level trees (projections / state)
EXCLUDED_ROOT_DIRS = {"raw", "materials", "out", ".git"}
LEGACY_PREFIX = "90-legacy/"


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


def iter_index_files(base: Path):
    """Yield original-candidate files over the WHOLE base, excluding the
    projection/state trees raw/, materials/, out/, .git (mirrors
    backfill_candidates.build_index — originals sometimes live in
    10-strategy/, 30-products/, incoming/ ...)."""
    for root, dirs, files in base.walk():
        if Path(root) == base:
            dirs[:] = [d for d in dirs
                       if d not in EXCLUDED_ROOT_DIRS and not d.startswith(".")
                       and d not in SKIP_DIR_NAMES]
        else:
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES and not d.startswith(".")]
        for f in files:
            if f.startswith(".") or f.startswith("_") or f == "_backfill_report.json":
                continue
            yield Path(root) / f


def _rep_sorted(paths, base: Path):
    """Distinct relative paths, non-90-legacy copies preferred first.

    90-legacy/ is a read-only historical snapshot; when the same original
    exists elsewhere (e.g. incoming/), that copy is the canonical anchor.
    """
    rels = sorted({p.relative_to(base).as_posix() for p in paths},
                  key=lambda s: (s.startswith(LEGACY_PREFIX), s))
    return rels


def build_base_index(base: Path):
    """Whole-base index: basename/stem (lower) -> [abs Path], representative
    first (non-legacy preferred)."""
    by_basename, by_stem = {}, {}
    for p in iter_index_files(base):
        if not p.is_file():
            continue
        by_basename.setdefault(p.name.lower(), []).append(p)
        by_stem.setdefault(p.stem.lower(), []).append(p)
    for d in (by_basename, by_stem):
        for k, paths in d.items():
            rels = _rep_sorted(paths, base)
            d[k] = [base / rels[0]] + [base / r for r in rels[1:]]
    return by_basename, by_stem


def unique(seq):
    s = sorted(set(seq))
    return s[0] if len(s) == 1 else None


def raw_md_for(orig_path: Path, raw_by_orig):
    hits = raw_by_orig.get(orig_path.name.lower(), [])
    return unique(hits)


def unique_rep(paths, base: Path):
    """Unique original among distinct paths; 90-legacy copies ignored when a
    non-legacy copy of the same basename exists; byte-identical duplicates
    (same sha256) collapse to one logical original (representative first).
    None if genuinely ambiguous."""
    rels = _rep_sorted(paths, base)
    non_legacy = [r for r in rels if not r.startswith(LEGACY_PREFIX)]
    if non_legacy:
        rels = non_legacy
    if len(rels) == 1:
        return base / rels[0]
    hashes = set()
    try:
        for r in rels:
            hashes.add(hashlib.sha256((base / r).read_bytes()).hexdigest())
    except OSError:
        return None
    return base / rels[0] if len(hashes) == 1 else None


def match_material(md_path: Path, by_basename, by_stem, raw_by_orig,
                   base_stem_index=None, base: Path = None):
    """Return (source_value, confidence, applied_rule) or (None, reason, None)."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return None, f"read-error: {e}", None
    name = md_path.name.lower()
    stem = md_path.stem.lower()

    # 1) exact basename hint in body text (original filename with extension)
    body_hits = [fs[0] for b, fs in by_basename.items() if b in text.lower()]
    if len(body_hits) == 1:
        orig = unique(by_basename[body_hits[0].name.lower()])
        if orig:
            return orig, "exact", "exact"

    # 2) material filename contains an incoming basename
    name_hits = [f for b, fs in by_basename.items() if b in name for f in fs]
    if len(name_hits) == 1:
        return name_hits[0], "exact", "exact"

    # 3) material stem equals/contains a unique incoming stem
    stem_hits = [f for s, fs in by_stem.items() if s and (s == stem or s in stem) for f in fs]
    if len(stem_hits) == 1:
        return stem_hits[0], "suffix", "suffix"

    # 4) prefix-rescue: material stem (>=4 chars) is a prefix/substring of
    #    exactly ONE whole-base indexed original stem → accept. Rescues e.g.
    #    近三年服务业绩.md ← 近三年服务业绩表-蓝联科技.xlsx. Only unique
    #    containment counts (ambiguity → no match).
    if base_stem_index is not None and base is not None and len(stem) >= 4:
        containing = [s for s in base_stem_index if stem in s]
        if len(containing) == 1:
            orig = unique_rep(base_stem_index[containing[0]], base)
            if orig:
                return orig, "prefix-rescue", "prefix-rescue"

    return None, "no-unique-hint", None


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


def raw_suffix_keys(md_stem: str):
    """Every underscore-suffix of a raw md stem that ends in an original ext,
    longest-first. Phase-1 finding: leading parts like
    `03-competitors_会员系统_科传_` are decorations, so shorter suffixes are
    the ones that actually hit the index — the longest-only logic was the
    blind spot behind 29 `raw/no-suffix-match` files."""
    parts = md_stem.split("_")
    keys = []
    for i in range(len(parts)):
        cand = "_".join(parts[i:])
        if Path(cand).suffix.lower() in ORIG_EXTS:
            keys.append(cand)
    return keys


def backfill_raw_md(md_path: Path, base: Path, by_basename):
    """Match raw md to an original by trying ALL ext-suffixed underscore
    suffixes, longest-first; first UNIQUE whole-base hit wins."""
    text = md_path.read_text(encoding="utf-8", errors="replace")
    if PROV_MARK in text[:2000]:
        return None, "already-has-provenance", None
    for cand in raw_suffix_keys(md_path.name[:-3]):
        hits = by_basename.get(cand.lower(), [])
        orig = unique_rep(hits, base)
        if orig:
            return orig, "suffix", "raw-suffix-fixed"
    return None, "no-suffix-match", None


def load_mapping(tsv_path: Path):
    """Load approved proposal TSV (file/proposed_source/bucket).
    Returns {file: (proposed, bucket)}; keeps accept rows (materials/ AND
    raw/ — raw rows carry human-approved targets where the deterministic
    suffix rule hits ambiguous duplicates) and authored rows for materials/
    only (authored raw files have no `source: "none"` representation — they
    stay unmatched). mid/review rows are ignored."""
    mapping = {}
    for line in tsv_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("file\t"):
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        f, proposed, bucket = parts[0], parts[1], parts[2]
        if bucket not in ("accept", "authored"):
            continue
        if bucket == "authored" and not f.startswith("materials/"):
            continue
        mapping[f] = (proposed, bucket)
    return mapping


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json-report", default=None)
    ap.add_argument("--mapping", default=None,
                    help="approved proposal TSV (file/proposed_source/bucket); "
                         "applies accept rows as source + authored rows as "
                         "source: \"none\"; mid/review ignored")
    args = ap.parse_args()
    base = Path(args.base).resolve()
    incoming = base / "incoming"
    raw = base / "raw"
    materials = base / "materials"

    mapping = load_mapping(Path(args.mapping)) if args.mapping else {}
    mapping_missing = []

    by_basename, by_stem = build_incoming_index(incoming)
    raw_by_orig = build_raw_index(raw)
    base_by_basename, base_by_stem = build_base_index(base)

    report = {"matched": [], "unmatched": [], "skipped": [], "written": 0,
              "mapping_missing": mapping_missing}
    today = datetime.date.today().isoformat()

    # --- materials ---
    mat_files = [p for p in materials.rglob("*.md") if p.is_file()]
    for md in mat_files:
        rel = md.relative_to(base).as_posix()
        text = md.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^source:", text[:4000], re.M):
            report["skipped"].append({"file": rel, "reason": "has-source"})
            continue

        # approved mapping takes precedence (accept → source, authored → "none")
        if rel in mapping:
            proposed, bucket = mapping[rel]
            if bucket == "authored":
                if not args.dry_run:
                    insert_source(md, "none")
                    report["written"] += 1
                report["matched"].append({"file": rel, "source": "none",
                                          "confidence": "authored",
                                          "applied_rule": "mapping-authored"})
                continue
            target = base / proposed
            if not target.is_file():
                mapping_missing.append({"file": rel, "missing_target": proposed})
                report["unmatched"].append({"file": rel,
                                            "reason": "mapping-target-missing"})
                continue
            if not args.dry_run:
                insert_source(md, proposed)
                report["written"] += 1
            report["matched"].append({"file": rel, "source": proposed,
                                      "confidence": "mapping-accept",
                                      "applied_rule": "mapping"})
            continue

        orig, conf, rule = match_material(md, by_basename, by_stem, raw_by_orig,
                                          base_stem_index=base_by_stem, base=base)
        if not orig:
            report["unmatched"].append({"file": rel, "reason": conf})
            continue
        value, root = source_value_for(orig, base, raw_by_orig)
        entry = {"file": rel, "source": value,
                 "confidence": conf, "root": root,
                 "applied_rule": rule,
                 "original": str(orig.relative_to(base))}
        if not args.dry_run:
            insert_source(md, value)
            report["written"] += 1
        report["matched"].append(entry)

    # --- raw top-level md ---
    for md in sorted(raw.glob("*.md")):
        rel = md.relative_to(base).as_posix()

        # approved mapping first (deterministic suffix rule stays as fallback)
        if rel in mapping and PROV_MARK not in \
                md.read_text(encoding="utf-8", errors="replace")[:2000]:
            proposed, bucket = mapping[rel]
            target = base / proposed
            if not target.is_file():
                mapping_missing.append({"file": rel, "missing_target": proposed})
                report["unmatched"].append({"file": rel,
                                            "reason": "mapping-target-missing"})
                continue
            sha = hashlib.sha256(target.read_bytes()).hexdigest()
            entry = {"file": rel, "source": proposed,
                     "confidence": "mapping-accept", "applied_rule": "mapping",
                     "sha256": sha}
            if not args.dry_run:
                block = (f"<!-- source: {proposed} -->\n"
                         f"<!-- source_sha256: {sha} -->\n"
                         f"<!-- extracted_by: markitdown (pre-existing artifact, backfilled {today}) -->\n")
                cur = md.read_text(encoding="utf-8", errors="replace")
                md.write_text(block + cur, encoding="utf-8")
                report["written"] += 1
            report["matched"].append(entry)
            continue

        orig, reason, rule = backfill_raw_md(md, base, base_by_basename)
        if not orig:
            report["unmatched"].append({"file": str(md.relative_to(base)),
                                        "reason": f"raw/{reason}"})
            continue
        sha = hashlib.sha256(orig.read_bytes()).hexdigest()
        entry = {"file": str(md.relative_to(base)),
                 "source": str(orig.relative_to(base)),
                 "confidence": "suffix", "applied_rule": rule, "sha256": sha}
        if not args.dry_run:
            block = (f"<!-- source: {orig.relative_to(base).as_posix()} -->\n"
                     f"<!-- source_sha256: {sha} -->\n"
                     f"<!-- extracted_by: markitdown (pre-existing artifact, backfilled {today}) -->\n")
            cur = md.read_text(encoding="utf-8", errors="replace")
            md.write_text(block + cur, encoding="utf-8")
            report["written"] += 1
        report["matched"].append(entry)

    total = len(report["matched"]) + len(report["unmatched"])
    by_rule = {}
    for m in report["matched"]:
        by_rule[m.get("applied_rule") or m["confidence"]] = \
            by_rule.get(m.get("applied_rule") or m["confidence"], 0) + 1
    print(f"materials scanned: {len(mat_files)}, skipped(has-source): "
          f"{len([s for s in report['skipped']])}")
    print(f"matched: {len(report['matched'])}  unmatched: {len(report['unmatched'])}  "
          f"(total candidates {total})")
    for rule, n in sorted(by_rule.items(), key=lambda kv: -kv[1]):
        print(f"  rule {rule}: {n}")
    if mapping_missing:
        print(f"mapping targets missing (skipped): {len(mapping_missing)}")
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
