#!/usr/bin/env python3
"""Phase-1 analysis companion to backfill_source.py (REPORT ONLY, zero writes to base).

For the 227 unmatched files recorded in <base>/raw/_backfill_report.json:
  - build an original-file index over the WHOLE base excluding raw/, materials/,
    out/, .git (originals sometimes live in 10-strategy/, 30-products/, incoming/ …)
  - for each unmatched file, rank difflib.SequenceMatcher candidates (top-3)
  - classify `authored` when no candidate reaches the ratio floor AND the
    file's name/path looks like human-authored corpus content (heuristic below)
  - emit a human-readable report + JSON + a TSV mapping PROPOSAL for human review

NO fuzzy auto-writes — mapping application happens in phase 2 after approval.

PEP 723 inline deps (none needed — stdlib + difflib only).
Usage:
  uv run scripts/backfill_candidates.py <lanlnk_base> \
      [--report /tmp/opencode/backfill_candidates.json] \
      [--proposal /tmp/opencode/backfill_mapping_proposal.tsv] \
      [--ratio 0.6]
"""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path

ORIG_EXTS = {".pptx", ".docx", ".xlsx", ".pdf", ".doc", ".xls", ".ppt"}
# index building: directories never containing originals (projections/state)
EXCLUDED_ROOT_DIRS = {"raw", "materials", "out", ".git"}
SKIP_DIR_NAMES = {"_media", "csv", "parsed", "images", "_extracted",
                  "__pycache__", ".venv", "node_modules", ".playwright-mcp"}

# --- authored heuristic (EXPLICIT, applied only when best ratio < RATIO_FLOOR) ---
# A corpus file is *guessed* authored when its relative path or filename matches
# any pattern below. Rationale: these are synthesis/curation artifacts the team
# writes itself (company intro decks, org charts, roadmaps, product baselines,
# indexes/ledgers), not markitdown projections of an incoming original.
# NOTE: 16-customers deliberately NOT here — those materials ARE projections of
# customer originals living in incoming/客户SOP/ (verified empirically).
AUTHORED_NAME_RE = re.compile(
    r"README|公司简介|组织架构|发展历程|产品规划|产品路线|INDEX|台账|白皮书|简介|手册$"
)
AUTHORED_DIR_HINTS = ("01-company-overview", "03-products")

# generic stems that spuriously ratio-match everything (README -> README is a
# name collision, not provenance)
GENERIC_STEMS = {"readme", "index"}


def is_authored_guess(rel_posix: str, stem_lower: str) -> bool:
    if AUTHORED_NAME_RE.search(stem_lower) or AUTHORED_NAME_RE.search(rel_posix):
        return True
    return any(h in rel_posix for h in AUTHORED_DIR_HINTS)


def iter_index_files(base: Path, discovery_errors=None):
    """Yield candidate original files under base, excluding projection trees.

    Whole-base walk EXCLUDING top-level raw/, materials/, out/, .git (and
    known junk dir names anywhere). incoming/, 10-strategy/, 30-products/,
    00-90 trees are all included.

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
        rel_parts = Path(root).relative_to(base).parts
        if not rel_parts:
            dirs[:] = [d for d in dirs
                       if d not in EXCLUDED_ROOT_DIRS and not d.startswith(".")
                       and d not in SKIP_DIR_NAMES]
        else:
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES and not d.startswith(".")]
        for f in files:
            if f.startswith(".") or f.startswith("_"):
                continue
            p = Path(root) / f
            if p.name == "_backfill_report.json":
                continue
            yield p


def build_index(base: Path, discovery_errors=None):
    """stem(lower) -> sorted list of relative posix paths."""
    by_stem = {}
    for p in iter_index_files(base, discovery_errors):
        by_stem.setdefault(p.stem.lower(), []).append(p.relative_to(base).as_posix())
    # representative order: prefer non-legacy copies (90-legacy is a read-only
    # historical snapshot; incoming/30-products copies are canonical), then
    # shortest path
    return {k: sorted(v, key=lambda s: (s.startswith("90-legacy"), len(s), s))
            for k, v in by_stem.items()}


def top_candidates(query_stem: str, by_stem: dict, topk: int = 3):
    """Rank indexed stems by SequenceMatcher ratio; return top-k (path, ratio).

    Uses real_quick_ratio/quick_ratio as cheap upper-bound pruning. Ties broken
    by ratio then lexicographic path. Representative path per stem = first path.
    """
    sm = difflib.SequenceMatcher(b=query_stem)
    scored = []
    for stem, paths in by_stem.items():
        if stem in GENERIC_STEMS:
            continue
        sm.set_seq1(stem)
        if sm.real_quick_ratio() < 0.4 or sm.quick_ratio() < 0.4:
            continue
        r = sm.ratio()
        if r >= 0.4:
            scored.append((r, paths[0], len(paths)))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [{"path": p, "ratio": round(r, 4), "alt_paths": n - 1,
             "legacy": p.startswith("90-legacy/")}
            for r, p, n in scored[:topk]]


def raw_suffix_keys(md_name: str):
    """All underscore-suffixes of a raw md stem that end in an original ext,
    ordered longest -> shortest.

    backfill_source.py only tries the LONGEST suffix, which spans the whole
    stem whenever the last underscore part carries an extension — that blind
    spot is exactly why these 29 raw files landed in `raw/no-suffix-match`.
    Here we also consider shorter suffixes (leading parts are category
    decorations like `03-competitors_会员系统_科传_`), preferring hits on the
    shortest suffix. May be empty.
    """
    stem = md_name[:-3] if md_name.endswith(".md") else md_name
    parts = stem.split("_")
    keys = []
    for i in range(len(parts)):
        cand = "_".join(parts[i:])
        if Path(cand).suffix.lower() in ORIG_EXTS:
            keys.append(cand)
    return keys


def analyse(base: Path, report_in: Path, floor: float, discovery_errors=None):
    try:
        rep = json.loads(report_in.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"cannot read input report {report_in}: {e}", file=sys.stderr)
        return None, None
    unmatched = rep.get("unmatched", [])
    by_stem = build_index(base, discovery_errors)

    results = []
    for entry in unmatched:
        rel = entry["file"]
        p = base / rel
        is_raw = entry["reason"].startswith("raw/")

        if is_raw:
            keys = raw_suffix_keys(p.name)
            # exact stem hit on any ext-suffixed key wins; prefer shortest
            # suffix (leading parts are category decorations)
            hit = None
            for key in reversed(keys):
                stem_key = Path(key).stem.lower()
                if stem_key in by_stem:
                    hit = by_stem[stem_key]
                    break
            if hit:
                top3 = [{"path": hit[0], "ratio": 1.0, "alt_paths": len(hit) - 1,
                         "legacy": hit[0].startswith("90-legacy/")}]
            else:
                query_stem = Path(keys[-1]).stem.lower() if keys else p.stem.lower()
                top3 = top_candidates(query_stem, by_stem)
        else:
            top3 = top_candidates(p.stem.lower(), by_stem)

        best = top3[0] if top3 else None
        best_ratio = best["ratio"] if best else 0.0
        authored = is_authored_guess(rel, p.stem.lower())
        cls = "authored" if (best_ratio < floor and authored) else "candidate"
        results.append({
            "file": rel, "reason": entry["reason"], "class": cls,
            "authored_guess": authored, "best": best, "top3": top3,
        })
    return results, by_stem


def proposal_rows(results, floor=0.6, accept=0.75):
    """(file, proposed, bucket) — bucket: accept|mid|authored|review."""
    for r in results:
        best = r["best"]
        ratio = best["ratio"] if best else 0.0
        if ratio >= accept and not best.get("legacy"):
            yield r["file"], best["path"], "accept"
        elif ratio >= accept:
            # only copy found lives in the read-only 90-legacy snapshot —
            # human decides whether to accept a legacy source anchor
            yield r["file"], "REVIEW", "review"
        elif r["class"] == "authored":
            yield r["file"], "NONE", "authored"
        elif ratio >= floor:
            yield r["file"], "REVIEW", "mid"
        else:
            yield r["file"], "REVIEW", "review"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("--report", default="/tmp/opencode/backfill_candidates.json")
    ap.add_argument("--proposal", default="/tmp/opencode/backfill_mapping_proposal.tsv")
    ap.add_argument("--ratio", type=float, default=0.6)
    ap.add_argument("--accept", type=float, default=0.75)
    args = ap.parse_args()
    base = Path(args.base).resolve()
    report_in = base / "raw" / "_backfill_report.json"

    discovery_errors = []
    results, by_stem = analyse(base, report_in, args.ratio, discovery_errors)
    if results is None:
        return 1

    buckets = {"accept": 0, "mid": 0, "authored": 0, "review": 0}
    rows = list(proposal_rows(results, args.ratio, args.accept))
    for _, _, b in rows:
        buckets[b] += 1

    # --- human-readable summary ---
    print(f"index: {len(by_stem)} unique stems over whole base "
          f"(excluding raw/materials/out/.git)")
    print(f"analysed: {len(results)} unmatched files")
    print(f"buckets: accept(>={args.accept}) {buckets['accept']}  "
          f"mid({args.ratio}-{args.accept}) {buckets['mid']}  "
          f"authored->NONE {buckets['authored']}  REVIEW {buckets['review']}")
    print("\ntop high-ratio pairs:")
    for r in sorted(results, key=lambda x: -(x["best"]["ratio"] if x["best"] else 0))[:10]:
        if r["best"]:
            print(f"  {r['best']['ratio']:.3f}  {r['file']}  ->  {r['best']['path']}")
    if discovery_errors:
        print(f"\ndiscovery errors (unreadable paths skipped): {len(discovery_errors)}")
        for e in discovery_errors:
            print(f"  {e}")
    print("\nauthored guesses (ratio below floor):")
    for r in results:
        if r["class"] == "authored":
            print(f"  {r['file']}")

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"floor": args.ratio, "accept": args.accept,
                    "buckets": buckets, "results": results,
                    "discovery_errors": discovery_errors},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    proposal_path = Path(args.proposal)
    proposal_path.parent.mkdir(parents=True, exist_ok=True)
    proposal_path.write_text(
        "file\tproposed_source\tbucket\n" +
        "\n".join(f"{f}\t{s}\t{b}" for f, s, b in rows) + "\n",
        encoding="utf-8")
    print(f"\nreport:   {report_path}")
    print(f"proposal: {proposal_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
