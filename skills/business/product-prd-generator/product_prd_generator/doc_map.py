from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path

import yaml

from .models import DocFeature, DocMap, EvidenceKind, EvidenceRef, Requirement

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
    aliases: dict[str, str] = {}

    # Source 1: term-aliases.yaml (specific, skill-local)
    aliases_path = skill_root / "references" / "term-aliases.yaml"
    if aliases_path.is_file():
        data = yaml.safe_load(aliases_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for standard, items in data.items():
                if not isinstance(standard, str) or not isinstance(items, list):
                    continue
                aliases[standard] = standard
                for item in items:
                    if isinstance(item, str):
                        aliases[item] = standard

    # Source 2: business-ontology.yaml (broad, shared industry knowledge)
    # Located at $LANLNK_BASE/knowledge/business-ontology.yaml
    import os
    ontology_path = Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk")) / "knowledge" / "business-ontology.yaml"
    if ontology_path.is_file():
        onto = yaml.safe_load(ontology_path.read_text(encoding="utf-8"))
        if isinstance(onto, dict):
            for module in onto.get("modules", {}).values():
                if not isinstance(module, dict):
                    continue
                for sub in module.get("sub_functions", {}).values():
                    if not isinstance(sub, dict):
                        continue
                    caps = sub.get("capabilities", [])
                    terms = sub.get("terms", [])
                    if not isinstance(caps, list) or not isinstance(terms, list):
                        continue
                    if not caps:
                        continue
                    primary_cap = str(caps[0])
                    for term in terms:
                        if isinstance(term, str) and term not in aliases:
                            aliases[term] = primary_cap

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
    # Longest alias first — ensures "合同模板" matches before "合同"
    for alias, standard in sorted(aliases.items(), key=lambda x: -len(x[0])):
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
    r"|序号\s*$"
    r"|项目背景$"
    r"|项目目标$"
    r"|项目概述$"
    r"|项目简介$"
    r"|技术参数.*$"
    r"|技术要求.*$"
    r"|技术标准.*$"
    r"|备注.*$"
    r"|说明\s*$"
    r"|目录\s*$"
    r"|前言\s*$"
    r"|附录.*$"
    r"|文档.*历史$"
    r"|文档.*控制$"
    r"|审核.*$"
    r"|修订.*记录$"
    r"|建设目标$"
    r"|建设内容$"
    r"|总体.*要求$"
    r"|总体.*架构$"
    r"|总体.*设计$"
    r"|系统.*概述$"
    r"|系统.*简介$"
    r"|企业.*概况$"
    r"|公司.*简介$"
    r"|业务.*蓝图$"
    r"|实施.*计划$"
    r"|培训.*计划$"
    r"|售后.*服务$"
    r"|运维.*服务$"
    r"|报价.*$"
    r"|投标.*$"
    r"|响应.*$"
    r"|偏离.*$"
    r"|资格.*$"
    r"|资质.*$"
    r"|商务.*$"
    r"|法律.*$"
    r"|知识产权.*$"
    r"|保密.*$"
    r")$"
)

_SECTION_PREFIX = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)*[\.\s\、]+"
    r"|[一二三四五六七八九十]+[\、\．\.\s]+"
    r"|[（(][一二三四五六七八九十\d]+[)）]\s*"
    r"|第[一二三四五六七八九十\d]+[章节条]\s*"
    r")"
)


def _strip_section_prefix(text: str) -> str:
    return _SECTION_PREFIX.sub("", text).strip()


def _is_noise_heading(heading: str) -> bool:
    return bool(_NOISE_HEADING.match(heading.strip()))


_NOISE_TEXT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'^\|'),           # table artifacts
    re.compile(r'^\s*---'),       # table separators
    re.compile(r'!\['),            # image markdown
    re.compile(r'data:image'),     # base64 images
    re.compile(r'_media/'),        # image paths
    re.compile(r'^[A-Z][A-Z\s]{1,10}$'),  # all-caps English (EBITDA, NOI, SAP)
    re.compile(r'^[\d\.,\-\s]+$'), # numbers only
    re.compile(r'^\s*\{.*\}\s*$'), # JSON blocks
    re.compile(r'^\s*"data"'),     # JSON data fragments
]


def _is_noise_text(text: str) -> bool:
    """Comprehensive noise filter for requirement function text."""
    stripped = text.strip()
    if len(stripped) < 2 or len(stripped) > 80:
        return True
    if _is_noise_heading(stripped):
        return True
    for pattern in _NOISE_TEXT_PATTERNS:
        if pattern.search(stripped):
            return True
    if any(c in stripped for c in '。！？'):
        return True
    if stripped.count('，') > 2 or stripped.count(',') > 2:
        return True
    return False


def _parse_markdown(md_path: Path, docs_root: Path, aliases: dict[str, str]) -> tuple[DocFeature, ...]:
    text = md_path.read_text(encoding="utf-8", errors="replace")
    rel_path = md_path.relative_to(docs_root)
    source_type = _classify_source_type(rel_path)
    image_refs = _collect_image_refs(md_path, docs_root, text)
    doc_ref = EvidenceRef(kind=EvidenceKind.DOC, ref=str(rel_path))
    features: dict[str, DocFeature] = {}
    for match in _HEADING.finditer(text):
        depth = len(match.group(1))
        heading = _strip_section_prefix(match.group(2).strip())
        if not heading or _is_noise_heading(heading):
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


# --- Structural extraction (leaf-only Requirement model) -------------------

@dataclass
class _HeadingCandidate:
    pos: int
    end: int
    depth: int
    text: str


def _collect_heading_candidates(text: str) -> list[_HeadingCandidate]:
    """Collect ALL heading candidates from # headings, bold, and table rows."""
    candidates: list[_HeadingCandidate] = []
    for match in _HEADING.finditer(text):
        heading = _strip_section_prefix(match.group(2).strip())
        if not heading or _is_noise_text(heading):
            continue
        candidates.append(_HeadingCandidate(
            pos=match.start(), end=match.end(),
            depth=len(match.group(1)), text=heading,
        ))
    for match in _BOLD_HEADING.finditer(text):
        heading = _strip_section_prefix(match.group(1).strip())
        if len(heading) < 3 or len(heading) > 80 or _is_noise_text(heading):
            continue
        depth = 2 if re.match(r"^\d+[\.\、]", heading) else 3
        candidates.append(_HeadingCandidate(
            pos=match.start(), end=match.end(),
            depth=depth, text=heading,
        ))
    for match in _TABLE_ROW.finditer(text):
        col1 = _strip_section_prefix(match.group(1).strip())
        col2 = _strip_section_prefix(match.group(2).strip())
        if col1 in ("---", "", "NaN") or col2 in ("---", "", "NaN") or col1.startswith("--"):
            continue
        if 2 <= len(col1) <= 60 and not _is_noise_text(col1):
            candidates.append(_HeadingCandidate(
                pos=match.start(), end=match.end(), depth=1, text=col1,
            ))
        if 2 <= len(col2) <= 60 and not _is_noise_text(col2):
            candidates.append(_HeadingCandidate(
                pos=match.start(), end=match.end(), depth=2, text=col2,
            ))
    candidates.sort(key=lambda c: (c.pos, c.depth))
    return candidates


def _extract_nearby_text(text: str, heading_end: int) -> str:
    """First paragraph after a heading position (≤200 chars). Rule 2B."""
    after = text[heading_end:]
    next_marker = re.search(r'^[#\*|]', after, re.MULTILINE)
    section = after[:next_marker.start()] if next_marker else after
    para: list[str] = []
    for line in section.strip().split('\n'):
        stripped = line.strip()
        if not stripped:
            if para:
                break
            continue
        if stripped.startswith('![') or stripped.startswith('|'):
            continue
        para.append(stripped)
    result = ' '.join(para)
    return result[:200]


def _extract_customer(rel_path: Path) -> str:
    """Extract customer name from path segment after source-type directory."""
    parts = rel_path.parts
    for i, part in enumerate(parts):
        if "01-customer-requirements" in part and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def _parse_requirements(
    md_path: Path, docs_root: Path, aliases: dict[str, str]
) -> tuple[Requirement, ...]:
    """Extract leaf-only Requirements with scenario context + nearby_text.

    Rule 1C: depth 1-2 headings with children are containers (scenario/
    sub_scenario context only). Only leaf headings (no sub-headings beneath)
    become Requirements.
    """
    text = md_path.read_text(encoding="utf-8", errors="replace")
    rel_path = md_path.relative_to(docs_root)
    source_type = _classify_source_type(rel_path)
    source_customer = _extract_customer(rel_path)
    image_refs = _collect_image_refs(md_path, docs_root, text)
    doc_ref = EvidenceRef(kind=EvidenceKind.DOC, ref=str(rel_path))

    candidates = _collect_heading_candidates(text)
    requirements: dict[str, Requirement] = {}
    stack: list[tuple[int, str]] = []

    for i, cand in enumerate(candidates):
        while stack and stack[-1][0] >= cand.depth:
            stack.pop()

        scenario = "未分类"
        sub_scenario = ""
        for d, t in stack:
            if d == 1:
                scenario = t
            elif d == 2:
                sub_scenario = t

        is_leaf = True
        for j in range(i + 1, len(candidates)):
            if candidates[j].depth > cand.depth:
                is_leaf = False
                break
            if candidates[j].depth <= cand.depth:
                break

        if is_leaf and not _is_noise_heading(cand.text):
            nearby = _extract_nearby_text(text, cand.end)
            normalized = _normalize_term(cand.text, aliases)
            nearby_images = _nearby_image_refs(text, cand.pos, image_refs)
            req = Requirement(
                source_file=str(rel_path),
                source_type=source_type,
                source_customer=source_customer,
                scenario=scenario,
                sub_scenario=sub_scenario,
                function=cand.text,
                depth=cand.depth,
                nearby_text=nearby,
                normalized_term=normalized,
                evidence=(doc_ref, *nearby_images),
            )
            existing = requirements.get(normalized)
            if existing is None or cand.depth > existing.depth:
                requirements[normalized] = req

        stack.append((cand.depth, cand.text))

    if not requirements:
        normalized = _normalize_term(md_path.stem, aliases)
        requirements[normalized] = Requirement(
            source_file=str(rel_path),
            source_type=source_type,
            source_customer=source_customer,
            scenario="未分类",
            sub_scenario="",
            function=md_path.stem,
            depth=1,
            nearby_text="",
            normalized_term=normalized,
            evidence=(doc_ref,),
        )

    return tuple(requirements.values())


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
    requirements: dict[tuple[str, str], Requirement] = {}
    for md_path in md_files:
        for feature in _parse_markdown(md_path, docs_root, aliases):
            existing = features.get(feature.normalized_term)
            if existing is None or feature.depth > existing.depth:
                features[feature.normalized_term] = feature
        for req in _parse_requirements(md_path, docs_root, aliases):
            # Dedup by (normalized_term, source_file) — NOT normalized_term alone.
            # Broad aliases map many headings to the same term; collapsing them
            # would lose distinct requirements from different docs.
            key = (req.normalized_term, req.source_file)
            existing = requirements.get(key)
            if existing is None or req.depth > existing.depth:
                requirements[key] = req
    return DocMap(
        project=project,
        source_path=str(docs_root),
        features=tuple(features.values()),
        requirements=tuple(requirements.values()),
    )


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
        "requirements": [
            {
                "source_file": r.source_file,
                "source_type": r.source_type,
                "source_customer": r.source_customer,
                "scenario": r.scenario,
                "sub_scenario": r.sub_scenario,
                "function": r.function,
                "depth": r.depth,
                "nearby_text": r.nearby_text,
                "normalized_term": r.normalized_term,
                "evidence": [{"kind": e.kind.value, "ref": e.ref} for e in r.evidence],
            }
            for r in doc_map.requirements
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
