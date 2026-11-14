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
import os
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


def iter_index_files(base: Path, discovery_errors=None):
    """Yield original-candidate files over the WHOLE base, excluding the
    projection/state trees raw/, materials/, out/, .git (mirrors
    backfill_candidates.build_index — originals sometimes live in
    10-strategy/, 30-products/, incoming/ ...).

    Uses os.walk (Python 3.10+; Path.walk requires 3.12) with an explicit
    onerror hook: os.walk silently skips unreadable directories by default,
    and a skipped directory must surface as a recorded discovery error
    rather than an invisible "not found" (AGENTS.md os.walk 静默跳过陷阱,
    2026-10-02).
    """
    if discovery_errors is None:
        discovery_errors = []

    def _on_error(exc: OSError):
        discovery_errors.append(f"{exc.filename or base}: {exc.strerror or exc}")

    for root, dirs, files in os.walk(base, onerror=_on_error):
        if Path(root) == base:
            dirs[:] = [d for d in dirs
                       if d not in EXCLUDED_ROOT_DIRS and not d.startswith(".")
                       and d not in SKIP_DIR_NAMES]
        else:
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES and not d.startswith(".")]
        for f in files:
            if f.startswith(".") or f.startswith("_") or f == "_backfill_report.json":
                continue
            p = Path(root) / f
            # Review-fix 1: a file symlink inside the base may point into
            # another company base — exclude it from the match index so no
            # candidate path can read outside the base (recorded, not silent).
            if p.is_symlink():
                try:
                    p.resolve().relative_to(base)
                except ValueError:
                    discovery_errors.append(
                        f"{p}: symlink resolves outside base, excluded from index")
                    continue
                except OSError as e:
                    discovery_errors.append(f"{p}: {e}")
                    continue
            yield p


def _rep_sorted(paths, base: Path):
    """Distinct relative paths, non-90-legacy copies preferred first.

    90-legacy/ is a read-only historical snapshot; when the same original
    exists elsewhere (e.g. incoming/), that copy is the canonical anchor.
    """
    rels = sorted({p.relative_to(base).as_posix() for p in paths},
                  key=lambda s: (s.startswith(LEGACY_PREFIX), s))
    return rels


def build_base_index(base: Path, discovery_errors=None):
    """Whole-base index: basename/stem (lower) -> [abs Path], representative
    first (non-legacy preferred)."""
    by_basename, by_stem = {}, {}
    for p in iter_index_files(base, discovery_errors):
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


FM_RE = re.compile(
    r"\A(?P<open>---\r?\n)(?P<fm>.*?)(?P<close>\r?\n---)(?:\r?\n|\Z)", re.S)

PROVENANCE_CLASS = "candidate-association"


def insert_source(md_path: Path, value: str, sha256_at_backfill: str = None,
                  backfilled_at: str = None):
    """Insert source frontmatter. When sha256_at_backfill is given (backfill
    of an associated original), persist provenance class + at-backfill hash
    semantics into the product itself (D7: candidate-association must not
    live only in the one-shot report). authored rows (source: "none") pass
    no hash → no provenance_class field (authored is not a backfill).

    Review-fix 3: a closing `---` at EOF without a trailing newline is a
    valid frontmatter and MUST match (otherwise a second frontmatter block
    would be prepended). Appending inserts new lines INSIDE the original
    block (before the closing `---`) as a pure string splice — the original
    block's bytes and newline style are preserved, no regex re-flow."""
    text = md_path.read_bytes().decode("utf-8")
    m = FM_RE.match(text)
    lines = [f'source: "{value}"']
    if sha256_at_backfill is not None:
        lines.append(f"provenance_class: {PROVENANCE_CLASS}")
        lines.append(f"source_sha256_at_backfill: {sha256_at_backfill}")
        lines.append(f"backfilled_at: {backfilled_at}")
    line = "\n".join(lines)
    if m:
        fm = m.group("fm")
        if re.search(r"^source:", fm, re.M):
            return None  # already has source
        nl = "\r\n" if m.group("close").startswith("\r\n") else "\n"
        new_text = text[:m.end("fm")] + nl + line + text[m.start("close"):]
        md_path.write_bytes(new_text.encode("utf-8"))
        return "frontmatter-appended"
    new_text = f"---\n{line}\n---\n\n" + text
    md_path.write_bytes(new_text.encode("utf-8"))
    return "frontmatter-created"


PROV_MARK = "source_sha256"
SOURCE_MARK = "<!-- source:"
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
CONVERTER_SIG_RE = re.compile(r"via convert_\w+\.py(?:\s+v\d+)?")


def raw_provenance_block(source_rel: str, sha: str, today: str) -> str:
    """Backfill provenance comment block. Deliberately does NOT use the bare
    `source_sha256` field name — that name is shared with converter-time
    hashes (the ambiguity this change fixes); the at-backfill observation
    gets its own explicit field name."""
    return (f"<!-- source: {source_rel} -->\n"
            f"<!-- provenance_class: {PROVENANCE_CLASS} -->\n"
            f"<!-- source_sha256_at_backfill: {sha} -->\n"
            f"<!-- backfilled_at: {today} -->\n"
            f"<!-- extracted_by: markitdown (pre-existing artifact, "
            f"backfilled {today}) -->\n")


def _header_fields(header_text: str) -> dict:
    """Parse `key: value` pairs from an HTML-comment provenance block and/or
    frontmatter-style lines (first occurrence wins for each key)."""
    fields = {}
    for m in re.finditer(r"<!--\s*([A-Za-z0-9_]+):\s*(.*?)\s*-->", header_text):
        fields.setdefault(m.group(1), m.group(2))
    for m in re.finditer(r"^([A-Za-z0-9_]+):\s*(.*)$", header_text, re.M):
        fields.setdefault(m.group(1), m.group(2).strip().strip('"'))
    return fields


def _resolves_inside_base(src: str, base: Path) -> bool:
    if not src or src == "none":
        return False
    p = Path(src)
    if not p.is_absolute():
        p = base / p
    try:
        p.resolve().relative_to(base.resolve())
        return True
    except (ValueError, OSError):
        return False


def classify_record(header_text: str, base: Path) -> dict:
    """Compatibility reader for provenance headers (D7).

    - extracted_by carries a "backfilled" marker → backfill nature is kept:
      provenance_class=candidate-association, hash_semantics=at-backfill,
      regardless of whether the hash field uses the old name
      (`source_sha256`) or the new one (`source_sha256_at_backfill`).
    - converter signature (e.g. `markitdown via convert_doc.py vN`, or the
      convert_excel manifest extractor field shape) AND a source path that
      resolves inside the same base AND a valid 64-hex recorded hash →
      recorded-at-conversion candidate. This only certifies that a
      conversion-time source declaration EXISTS; it does not assert
      historical authenticity and does NOT require the current original
      hash to equal the recorded one (freshness is a separate dimension).
    - old bare `source_sha256` with neither marker → hash_semantics=unknown.
    - Never upgrades a record to conversion-time-verified merely because
      the field name matches.
    """
    fields = _header_fields(header_text)
    extracted_by = fields.get("extracted_by", "") or ""
    hash_val = (fields.get("source_sha256_at_backfill")
                or fields.get("source_sha256") or "")
    if "backfilled" in extracted_by.lower():
        return {"provenance_class": PROVENANCE_CLASS,
                "hash_semantics": "at-backfill"}
    sig = any(CONVERTER_SIG_RE.search(fields.get(k, "") or "")
              for k in ("extracted_by", "extractor"))
    if sig:
        if _resolves_inside_base(fields.get("source")
                                 or fields.get("source_path", ""), base) and \
                HEX64_RE.match(hash_val):
            return {"provenance_class": "recorded-at-conversion",
                    "hash_semantics": "at-conversion"}
        return {"provenance_class": None, "hash_semantics": "unknown"}
    if "source_sha256" in fields or "source_sha256_at_backfill" in fields:
        return {"provenance_class": None, "hash_semantics": "unknown"}
    return {"provenance_class": None, "hash_semantics": "no-declared-hash"}


FM_SOURCE_RE = re.compile(r'^source:\s*"?([^"\n]+?)"?\s*$', re.M)
RAW_SOURCE_RE = re.compile(r"<!--\s*source:\s*(.*?)\s*-->")


def resolve_in_base(value: str, base: Path):
    """Review-fix 1 boundary guard for paths that will actually be READ
    (mapping targets). Normalize (absolute/relative) → resolve() following
    symlinks → must stay inside base. Returns (resolved|None, status):
    status "ok" | "boundary-violation" | "resolve-error: ...". An OSError
    during resolve/stat is an observation failure (reported separately),
    NOT a boundary violation."""
    p = Path(value)
    if not p.is_absolute():
        p = base / p
    try:
        rp = p.resolve()
        rp.relative_to(base.resolve())
    except ValueError:
        return None, "boundary-violation"
    except OSError as e:
        return None, f"resolve-error: {e}"
    return rp, "ok"


def read_strict(p: Path) -> str:
    """Strict UTF-8 decode (review-fix 2): anything written back to disk must
    come from a strict decode — errors="replace" output must NEVER be
    persisted (it would silently corrupt the original bytes)."""
    return p.read_bytes().decode("utf-8")


def _fail(report, file_rel: str, reason: str, stage: str):
    report["failed"].append({"file": file_rel, "reason": reason,
                             "stage": stage})


def evaluate_declared_source(value: str, base: Path):
    """Assess an already-declared source for wrong_source_suspects.
    Returns None when the source resolves to an existing file inside the
    base, else (assessment, suggestion). Suggest only — never rewrite."""
    if not value or value == "none":
        return None
    p = Path(value)
    if not p.is_absolute():
        p = base / p
    try:
        rp = p.resolve()
        rp.relative_to(base.resolve())
    except (ValueError, OSError):
        return ("boundary-violation",
                "声明来源解析后落在公司基座之外；人工确认后修正 source 为基座内路径")
    if not rp.is_file():
        return ("missing",
                "声明来源在基座内不存在（原件可能被移动/重命名）；人工核实后修正 source")
    return None


def suspect_entry(file_rel: str, declared: str, assessment: str, suggestion: str):
    return {"file": file_rel, "declared_source": declared,
            "assessment": assessment, "suggestion": suggestion}



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


def filter_legacy_accepts(candidates_json: Path, tsv_out: Path,
                          ratio_min: float = 0.75):
    """Phase-3: turn the phase-1 candidates JSON into a --mapping TSV holding
    exactly the user-approved legacy anchors — materials/ files whose best
    candidate ratio >= ratio_min AND whose best (only) copy lives under
    90-legacy/. Returns the selected rows."""
    data = json.loads(candidates_json.read_text(encoding="utf-8"))
    rows = []
    for x in data.get("results", []):
        best = x.get("best")
        if not best or not x["file"].startswith("materials/"):
            continue
        if best["ratio"] >= ratio_min and best.get("legacy"):
            rows.append((x["file"], best["path"]))
    tsv_out.parent.mkdir(parents=True, exist_ok=True)
    tsv_out.write_text(
        "file\tproposed_source\tbucket\n" +
        "".join(f"{f}\t{p}\taccept\n" for f, p in rows), encoding="utf-8")
    return rows


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
    discovery_errors = []
    base_by_basename, base_by_stem = build_base_index(base, discovery_errors)

    report = {"matched": [], "unmatched": [], "skipped": [], "written": 0,
              "mapping_missing": mapping_missing,
              "mapping_target_out_of_base": [],
              "wrong_source_suspects": [],
              "failed": [],
              "discovery_errors": discovery_errors}
    today = datetime.date.today().isoformat()

    # --- materials ---
    mat_files = [p for p in materials.rglob("*.md") if p.is_file()]
    for md in mat_files:
        rel = md.relative_to(base).as_posix()
        try:
            text = read_strict(md)
        except UnicodeDecodeError as e:
            _fail(report, rel, f"encoding-invalid: {e}", "read")
            continue
        except OSError as e:
            _fail(report, rel, f"read-error: {e}", "read")
            continue
        try:
            if re.search(r"^source:", text[:4000], re.M):
                report["skipped"].append({"file": rel, "reason": "has-source"})
                m = FM_RE.match(text)
                sm = FM_SOURCE_RE.search(m.group("fm")) if m else None
                declared = sm.group(1) if sm else ""
                bad = evaluate_declared_source(declared, base)
                if bad:
                    report["wrong_source_suspects"].append(
                        suspect_entry(rel, declared, *bad))
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
                target, tstat = resolve_in_base(proposed, base)
                if tstat == "boundary-violation":
                    report["mapping_target_out_of_base"].append(
                        {"file": rel, "proposed": proposed, "status": tstat})
                    report["unmatched"].append(
                        {"file": rel, "reason": "mapping-target-out-of-base"})
                    continue
                if tstat != "ok":
                    _fail(report, rel, tstat, "mapping-target-resolve")
                    continue
                if not target.is_file():
                    mapping_missing.append({"file": rel, "missing_target": proposed})
                    report["unmatched"].append({"file": rel,
                                                "reason": "mapping-target-missing"})
                    continue
                sha = hashlib.sha256(target.read_bytes()).hexdigest()
                if not args.dry_run:
                    insert_source(md, proposed, sha256_at_backfill=sha,
                                  backfilled_at=today)
                    report["written"] += 1
                report["matched"].append({"file": rel, "source": proposed,
                                          "confidence": "mapping-accept",
                                          "applied_rule": "mapping",
                                          "provenance_class": PROVENANCE_CLASS,
                                          "hash_semantics": "at-backfill"})
                continue

            orig, conf, rule = match_material(md, by_basename, by_stem,
                                              raw_by_orig,
                                              base_stem_index=base_by_stem,
                                              base=base)
            if not orig:
                report["unmatched"].append({"file": rel, "reason": conf})
                continue
            value, root = source_value_for(orig, base, raw_by_orig)
            sha = hashlib.sha256(orig.read_bytes()).hexdigest()
            entry = {"file": rel, "source": value,
                     "confidence": conf, "root": root,
                     "applied_rule": rule,
                     "provenance_class": PROVENANCE_CLASS,
                     "hash_semantics": "at-backfill",
                     "original": str(orig.relative_to(base))}
            if not args.dry_run:
                insert_source(md, value, sha256_at_backfill=sha,
                              backfilled_at=today)
                report["written"] += 1
            report["matched"].append(entry)
        except UnicodeDecodeError as e:
            _fail(report, rel, f"encoding-invalid: {e}", "process")
        except OSError as e:
            _fail(report, rel, f"io-error: {e}", "process")

    # --- raw top-level md ---
    for md in sorted(raw.glob("*.md")):
        rel = md.relative_to(base).as_posix()
        try:
            text = read_strict(md)
        except UnicodeDecodeError as e:
            _fail(report, rel, f"encoding-invalid: {e}", "read")
            continue
        except OSError as e:
            _fail(report, rel, f"read-error: {e}", "read")
            continue
        try:
            head = text[:2000]

            # already-declared source: skip writing, assess only (suggest, never rewrite)
            if PROV_MARK in head or SOURCE_MARK in head:
                sm = RAW_SOURCE_RE.search(head)
                declared = sm.group(1) if sm else ""
                bad = evaluate_declared_source(declared, base)
                if bad:
                    report["wrong_source_suspects"].append(
                        suspect_entry(rel, declared, *bad))
                report["unmatched"].append({"file": rel,
                                            "reason": "already-has-provenance"})
                continue

            # approved mapping first (deterministic suffix rule stays as fallback)
            if rel in mapping:
                proposed, bucket = mapping[rel]
                target, tstat = resolve_in_base(proposed, base)
                if tstat == "boundary-violation":
                    report["mapping_target_out_of_base"].append(
                        {"file": rel, "proposed": proposed, "status": tstat})
                    report["unmatched"].append(
                        {"file": rel, "reason": "mapping-target-out-of-base"})
                    continue
                if tstat != "ok":
                    _fail(report, rel, tstat, "mapping-target-resolve")
                    continue
                if not target.is_file():
                    mapping_missing.append({"file": rel, "missing_target": proposed})
                    report["unmatched"].append({"file": rel,
                                                "reason": "mapping-target-missing"})
                    continue
                sha = hashlib.sha256(target.read_bytes()).hexdigest()
                entry = {"file": rel, "source": proposed,
                         "confidence": "mapping-accept", "applied_rule": "mapping",
                         "provenance_class": PROVENANCE_CLASS,
                         "hash_semantics": "at-backfill",
                         "sha256": sha}
                if not args.dry_run:
                    # write back the STRICT-decoded text only — a replace-
                    # decoded variant would corrupt bad bytes on disk
                    md.write_text(
                        raw_provenance_block(proposed, sha, today) + text,
                        encoding="utf-8")
                    report["written"] += 1
                report["matched"].append(entry)
                continue

            orig, reason, rule = backfill_raw_md(md, base, base_by_basename)
            if not orig:
                report["unmatched"].append({"file": rel,
                                            "reason": f"raw/{reason}"})
                continue
            sha = hashlib.sha256(orig.read_bytes()).hexdigest()
            entry = {"file": rel,
                     "source": str(orig.relative_to(base)),
                     "confidence": "suffix", "applied_rule": rule,
                     "provenance_class": PROVENANCE_CLASS,
                     "hash_semantics": "at-backfill", "sha256": sha}
            if not args.dry_run:
                md.write_text(
                    raw_provenance_block(
                        orig.relative_to(base).as_posix(), sha, today) + text,
                    encoding="utf-8")
                report["written"] += 1
            report["matched"].append(entry)
        except UnicodeDecodeError as e:
            _fail(report, rel, f"encoding-invalid: {e}", "process")
        except OSError as e:
            _fail(report, rel, f"io-error: {e}", "process")

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
    if report["mapping_target_out_of_base"]:
        print(f"mapping targets out of base (not read): "
              f"{len(report['mapping_target_out_of_base'])}")
    if report["failed"]:
        print(f"failed files (skipped, bytes untouched): {len(report['failed'])}")
        for f in report["failed"]:
            print(f"  {f['file']} [{f['stage']}]: {f['reason']}")
    if report["wrong_source_suspects"]:
        print(f"wrong source suspects (assessment only, no rewrite): "
              f"{len(report['wrong_source_suspects'])}")
    if discovery_errors:
        print(f"discovery errors (unreadable paths skipped): {len(discovery_errors)}")
        for e in discovery_errors:
            print(f"  {e}")
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
