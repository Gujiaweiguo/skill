# ─── How to run ───
#   cd skills/business/product-prd-generator
#   uv run scripts/extract_doc_map.py --docs-root /opt/code/docs/lanlnk/prd/projects/商管系统/raw --output parsed/current-doc-map.json

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path

import yaml


@unique
class EvidenceKind(str, Enum):
    DOC = "doc"
    IMAGE = "image"


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    kind: str
    ref: str


@dataclass(frozen=True, slots=True)
class DocFeature:
    source_file: str
    source_type: str
    heading: str
    depth: int
    normalized_term: str
    evidence: tuple[EvidenceRef, ...]


@dataclass(frozen=True, slots=True)
class DocMap:
    project: str
    source_path: str
    features: tuple[DocFeature, ...]


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_TABLE_ROW = re.compile(r"^\|.*\|$")
_MD_SUFFIX = (".md",)
_MEDIA_SUFFIX = ("_media",)


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


def _classify_source_type(rel_path: Path, docs_root: Path) -> str:
    parts = rel_path.parts
    if "01-customer-requirements" in parts:
        return "customer-requirements"
    if "00-current-product" in parts:
        return "current-product"
    if "02-competitors" in parts:
        return "competitor"
    return "unknown"


def _iter_markdown_files(docs_root: Path) -> tuple[Path, ...]:
    if not docs_root.is_dir():
        return ()
    return tuple(
        p
        for p in sorted(docs_root.rglob("*.md"))
        if p.is_file()
        and not any(part.startswith(".") for part in p.relative_to(docs_root).parts)
    )


def _media_dir_for(md_path: Path, docs_root: Path) -> Path:
    stem = md_path.stem
    return md_path.parent / f"{stem}{_MEDIA_SUFFIX[0]}"


def _collect_image_refs(md_path: Path, docs_root: Path, text: str) -> tuple[EvidenceRef, ...]:
    refs: list[EvidenceRef] = []
    for match in _IMAGE.finditer(text):
        target = match.group(1)
        resolved = (md_path.parent / target).resolve()
        try:
            rel = resolved.relative_to(docs_root.resolve())
        except ValueError:
            rel = Path(target)
        refs.append(EvidenceRef(kind=EvidenceKind.IMAGE.value, ref=str(rel)))
    media_dir = _media_dir_for(md_path, docs_root)
    if media_dir.is_dir():
        for img in sorted(media_dir.iterdir()):
            if img.is_file() and img.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
                try:
                    rel = img.relative_to(docs_root.resolve())
                except ValueError:
                    rel = img
                ref = EvidenceRef(kind=EvidenceKind.IMAGE.value, ref=str(rel))
                if ref not in refs:
                    refs.append(ref)
    return tuple(refs)


def _normalize_term(heading: str, aliases: dict[str, str]) -> str:
    cleaned = re.sub(r"[`*_~]", "", heading).strip()
    for alias, standard in aliases.items():
        if alias and alias in cleaned:
            return standard
    return cleaned or heading


def _parse_markdown(md_path: Path, docs_root: Path, aliases: dict[str, str]) -> tuple[DocFeature, ...]:
    text = md_path.read_text(encoding="utf-8", errors="replace")
    rel_path = md_path.relative_to(docs_root)
    source_type = _classify_source_type(rel_path, docs_root)
    image_refs = _collect_image_refs(md_path, docs_root, text)
    doc_ref = EvidenceRef(kind=EvidenceKind.DOC.value, ref=str(rel_path))
    features: dict[str, DocFeature] = {}
    for match in _HEADING.finditer(text):
        depth = len(match.group(1))
        heading = match.group(2).strip()
        normalized = _normalize_term(heading, aliases)
        existing = features.get(normalized)
        candidate = DocFeature(
            source_file=str(rel_path),
            source_type=source_type,
            heading=heading,
            depth=depth,
            normalized_term=normalized,
            evidence=(doc_ref, *image_refs),
        )
        if existing is None or depth > existing.depth:
            features[normalized] = candidate
    if not features:
        fallback = DocFeature(
                source_file=str(rel_path),
                source_type=source_type,
                heading=md_path.stem,
                depth=1,
                normalized_term=_normalize_term(md_path.stem, aliases),
                evidence=(doc_ref, *image_refs),
            )
        features[fallback.normalized_term] = fallback
    return tuple(features.values())


def extract(docs_root: Path, skill_root: Path, project: str = "商管系统") -> DocMap:
    aliases = _load_aliases(skill_root)
    md_files = _iter_markdown_files(docs_root)
    features: dict[str, DocFeature] = {}
    for md_path in md_files:
        for feature in _parse_markdown(md_path, docs_root, aliases):
            existing = features.get(feature.normalized_term)
            if existing is None or feature.depth > existing.depth:
                features[feature.normalized_term] = feature
    return DocMap(
        project=project,
        source_path=str(docs_root),
        features=tuple(features.values()),
    )


def _to_dict(doc_map: DocMap) -> dict[str, object]:
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
                "evidence": [{"kind": e.kind, "ref": e.ref} for e in f.evidence],
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
    payload = json.dumps(_to_dict(doc_map), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
