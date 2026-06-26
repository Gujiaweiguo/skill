from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path

import yaml

from .models import DocFeature, DocMap, EvidenceKind, EvidenceRef

# --- Extraction regexes ---------------------------------------------------
# Three heading styles are extracted because customer/competitor docs use
# inconsistent formats:
#
#   _HEADING      — standard markdown  # / ## / ###
#   _BOLD_HEADING — **bold text** on its own line (Wanda docs use bold as
#                   headings without any # prefix)
#   _TABLE_ROW    — two-column markdown tables (中旅/锦和/安居 docs embed
#                   functional points as xlsx table rows). MUST use
#                   re.MULTILINE or ^/$ anchors won't match across lines.
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_BOLD_HEADING = re.compile(r"^\*\*(.+?)\*\*\s*$", re.MULTILINE)
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_TABLE_ROW = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|", re.MULTILINE)


@unique
class SourceType(str, Enum):
    CUSTOMER = "customer-requirements"
    CURRENT = "current-product"
    COMPETITOR = "competitor"
    UNKNOWN = "unknown"


def _load_aliases(skill_root: Path) -> dict[str, str]:
    aliases_path = skill_root / "references" / "term-aliases.yaml"
    if not aliases_path.is_file():
        return {}
    data = yaml.safe_load(aliases_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    aliases: dict[str, str] = {}
    for standard, items in data.items():
        if not isinstance(standard, str) or not isinstance(items, list):
            continue
        aliases[standard] = standard
        for item in items:
            if isinstance(item, str):
                aliases[item] = standard
    return aliases


def _classify_source_type(rel_path: Path) -> str:
    parts = rel_path.parts
    if "01-customer-requirements" in parts:
        return SourceType.CUSTOMER.value
    if "00-current-product" in parts:
        return SourceType.CURRENT.value
    if "02-competitors" in parts:
        return SourceType.COMPETITOR.value
    return SourceType.UNKNOWN.value


def _iter_markdown_files(docs_root: Path) -> tuple[Path, ...]:
    if not docs_root.is_dir():
        return ()
    return tuple(sorted(p for p in docs_root.rglob("*.md") if p.is_file() and not any(part.startswith(".") for part in p.relative_to(docs_root).parts)))


def _normalize_term(heading: str, aliases: dict[str, str]) -> str:
    cleaned = re.sub(r"[`*_~]", "", heading).strip()
    for alias, standard in aliases.items():
        if alias and alias in cleaned:
            return standard
    return cleaned or heading


def _collect_image_refs(md_path: Path, docs_root: Path, text: str) -> tuple[EvidenceRef, ...]:
    # Dedup via `seen` set: same image may appear both as inline ![](path)
    # and in _media/ dir — we keep it once. media_dir stem uses dual
    # candidates (foo.docx and foo) because markitdown may strip the
    # .docx suffix when naming the _media directory.
    docs_root = docs_root.resolve()
    seen: set[str] = set()
    refs: list[EvidenceRef] = []

    def _add(ref_str: str) -> None:
        key = f"image:{ref_str}"
        if key not in seen:
            seen.add(key)
            refs.append(EvidenceRef(kind=EvidenceKind.IMAGE, ref=ref_str))
    for match in _IMAGE.finditer(text):
        target = match.group(1)
        resolved = (md_path.parent / target).resolve()
        try:
            rel = resolved.relative_to(docs_root)
        except ValueError:
            rel = Path(target)
        _add(str(rel))

    # media_dir 的 stem 匹配：markdown 文件名可能含 .docx/.pptx 后缀
    stem_candidates = [md_path.stem, md_path.stem.rsplit(".", 1)[0]]
    for stem in dict.fromkeys(stem_candidates):
        media_dir = md_path.parent / f"{stem}_media"
        if not media_dir.is_dir():
            continue
        for img in sorted(media_dir.iterdir()):
            if img.is_file() and img.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
                try:
                    rel = img.resolve().relative_to(docs_root)
                except ValueError:
                    rel = img
                _add(str(rel))

    return tuple(refs)


_NOISE_HEADING = re.compile(
    r"^("
    r".*需求说明$"
    r"|.*业务流程图$"
    r"|.*需求规格$"
    r"|\d+\.?\d*\s*$"
    r"|[（(][一二三四五六七八九十\d]+[)）]\s*$"
    r")$"
)


def _is_noise_heading(heading: str) -> bool:
    return bool(_NOISE_HEADING.match(heading.strip()))


def _parse_markdown(md_path: Path, docs_root: Path, aliases: dict[str, str]) -> tuple[DocFeature, ...]:
    text = md_path.read_text(encoding="utf-8", errors="replace")
    rel_path = md_path.relative_to(docs_root)
    source_type = _classify_source_type(rel_path)
    image_refs = _collect_image_refs(md_path, docs_root, text)
    doc_ref = EvidenceRef(kind=EvidenceKind.DOC, ref=str(rel_path))
    features: dict[str, DocFeature] = {}
    for match in _HEADING.finditer(text):
        depth = len(match.group(1))
        heading = match.group(2).strip()
        if _is_noise_heading(heading):
            continue
        normalized = _normalize_term(heading, aliases)
        nearby_images = _nearby_image_refs(text, match.start(), image_refs)
        candidate = DocFeature(
            source_file=str(rel_path),
            source_type=source_type,
            heading=heading,
            depth=depth,
            normalized_term=normalized,
            evidence=(doc_ref, *nearby_images),
        )
        existing = features.get(normalized)
        if existing is None or depth > existing.depth:
            features[normalized] = candidate
    for match in _BOLD_HEADING.finditer(text):
        heading = match.group(1).strip()
        if len(heading) < 3 or len(heading) > 80:
            continue
        if _is_noise_heading(heading):
            continue
        depth = 2 if re.match(r"^\d+[\.\、]", heading) else 3
        normalized = _normalize_term(heading, aliases)
        if normalized in features:
            continue
        nearby_images = _nearby_image_refs(text, match.start(), image_refs)
        candidate = DocFeature(
            source_file=str(rel_path),
            source_type=source_type,
            heading=heading,
            depth=depth,
            normalized_term=normalized,
            evidence=(doc_ref, *nearby_images),
        )
        features[normalized] = candidate
    for match in _TABLE_ROW.finditer(text):
        col1 = match.group(1).strip()
        col2 = match.group(2).strip()
        if col1 in ("---", "", "NaN") or col2 in ("---", "", "NaN"):
            continue
        if col1.startswith("--"):
            continue
        for depth, heading in ((1, col1), (2, col2)):
            if len(heading) < 2 or len(heading) > 60:
                continue
            if _is_noise_heading(heading):
                continue
            normalized = _normalize_term(heading, aliases)
            if normalized in features:
                continue
            features[normalized] = DocFeature(
                source_file=str(rel_path),
                source_type=source_type,
                heading=heading,
                depth=depth,
                normalized_term=normalized,
                evidence=(doc_ref,),
            )
    if not features:
        fallback = DocFeature(
            source_file=str(rel_path),
            source_type=source_type,
            heading=md_path.stem,
            depth=1,
            normalized_term=_normalize_term(md_path.stem, aliases),
            evidence=(doc_ref,),
        )
        features[fallback.normalized_term] = fallback
    return tuple(features.values())


def _nearby_image_refs(
    text: str, heading_pos: int, all_images: tuple[EvidenceRef, ...]
) -> tuple[EvidenceRef, ...]:
    # Only attach images that appear within the heading's section (from
    # heading_pos to the next "# " heading). Without this, all images in
    # the file would pile onto the first heading.
    span_end = text.find("\n#", heading_pos + 1)
    if span_end == -1:
        span_end = len(text)
    span = text[heading_pos:span_end]
    result: list[EvidenceRef] = []
    for img in all_images:
        if img.ref.split("/")[-1].split(".")[0] in span or img.ref in span:
            if img not in result:
                result.append(img)
    return tuple(result)


def extract(docs_root: Path, skill_root: Path, project: str = "商管系统") -> DocMap:
    aliases = _load_aliases(skill_root)
    md_files = _iter_markdown_files(docs_root)
    features: dict[str, DocFeature] = {}
    for md_path in md_files:
        for feature in _parse_markdown(md_path, docs_root, aliases):
            existing = features.get(feature.normalized_term)
            if existing is None or feature.depth > existing.depth:
                features[feature.normalized_term] = feature
    return DocMap(project=project, source_path=str(docs_root), features=tuple(features.values()))


def to_json(doc_map: DocMap) -> dict[str, object]:
    return {
        "project": doc_map.project,
        "source_path": doc_map.source_path,
        "features": [
            {
                "source_file": f.source_file,
                "source_type": f.source_type,
                "heading": f.heading,
                "depth": f.depth,
                "normalized_term": f.normalized_term,
                "evidence": [{"kind": e.kind.value, "ref": e.ref} for e in f.evidence],
            }
            for f in doc_map.features
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract doc-side capability map from raw/*.md + images.")
    parser.add_argument("--docs-root", required=True)
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--project", default="商管系统")
    parser.add_argument("--output", default="-")
    args = parser.parse_args()

    doc_map = extract(Path(args.docs_root), Path(args.skill_root), args.project)
    payload = json.dumps(to_json(doc_map), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
