from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from typing import Any

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


def _load_aliases(skill_root: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Load aliases from term-aliases.yaml + business-ontology.yaml.
    Returns (flat_aliases_dict, ontology_structure_dict).
    """
    aliases: dict[str, str] = {}
    ontology: dict[str, object] = {}

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
    import os
    ontology_path = Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk")) / "knowledge" / "ontology" / "business-ontology.yaml"
    if ontology_path.is_file():
        ontology = yaml.safe_load(ontology_path.read_text(encoding="utf-8")) or {}
        if isinstance(ontology, dict):
            modules = ontology.get("modules", {})
            if not isinstance(modules, dict):
                modules = {}
            for module in modules.values():
                if not isinstance(module, dict):
                    continue
                for sub in module.get("sub_functions", {}).values():
                    if not isinstance(sub, dict):
                        continue
                    caps = sub.get("capabilities", [])
                    terms = sub.get("terms", [])
                    if not isinstance(caps, list) or not isinstance(terms, list) or not caps:
                        continue
                    primary_cap = str(caps[0])
                    for term in terms:
                        if isinstance(term, str) and term not in aliases:
                            aliases[term] = primary_cap

    return aliases, ontology


_HAIDING_FAMILY = ('海鼎', '华侨城', '锦和')


def _source_family(source_file: str) -> str | None:
    """Detect 海鼎 system family by scanning path segments.

    华侨城、锦和的蓝图/合同文档由海鼎编写，属于同一系统家族。
    扫描整个路径段而非固定 /02-competitors/X/ 前缀，因为家族成员
    会出现在客户需求目录或其他位置。
    """
    for segment in source_file.replace('\\', '/').split('/'):
        for member in _HAIDING_FAMILY:
            if member in segment:
                return member
    return None


def _source_priority(source_file: str) -> int:
    if _source_family(source_file):
        return 0
    source = source_file.replace('\\', '/')
    if '/00-current-product/' in source:
        return 1
    if '/01-customer-requirements/' in source:
        return 2
    if '/02-competitors/' in source:
        return 3
    return 4


# 海鼎家族（海鼎/华侨城/锦和）的文档使用不同标题风格描述同一套合同条款。
# 锦和蓝图由海鼎编写，华侨城用表格行条目。此表把变体标题归一到海鼎标准条款名。
_FAMILY_CLAUSE_ALIASES: dict[str, str] = {
    # 锦和 "X业务说明" 风格
    "固定租金计算方式": "账款条款",
    "进场管理业务说明": "进场条款",
    "进场管理流程图": "进场条款",
    "进场管理": "进场条款",
    "意向合同(特批)管理说明": "新合同申请",
    "居间合同管理": "新合同申请",
    "外包合同管理": "新合同申请",
    "增值合同管理": "新合同申请",
    "租赁合同管理业务说明": "新合同申请",
    # 华侨城 表格行条目
    "正式合同": "新合同申请",
    "合同退租/提前解约": "合同终止",
    "合同模板管理": "合同模板",
    "结算管理": "结算周期",
    "保证金管理": "预存款条款",
    "预付款管理": "预存款条款",
}


def _normalize_clause_heading(heading: str) -> str:
    """Remap family variant headings to canonical 海鼎 clause titles.

    Only exact matches are remapped to avoid over-normalizing unrelated headings.
    """
    clean = re.sub(r'[*#`~]', '', heading).strip()
    clean = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', clean)
    return _FAMILY_CLAUSE_ALIASES.get(clean, clean)


def _kind_priority(kind: str) -> int:
    return {
        'clause-group': 0,
        'clause-field': 1,
        'data-structure': 2,
        'workflow': 3,
        'permission': 4,
        'feature': 5,
    }.get(kind, 6)


def _merge_evidence(existing: tuple[EvidenceRef, ...], incoming: tuple[EvidenceRef, ...]) -> tuple[EvidenceRef, ...]:
    merged = list(existing)
    seen = {(e.kind, e.ref) for e in existing}
    for evidence in incoming:
        key = (evidence.kind, evidence.ref)
        if key in seen:
            continue
        seen.add(key)
        merged.append(evidence)
    return tuple(merged)


def _prefer_doc_feature(existing: DocFeature, candidate: DocFeature) -> bool:
    return (
        _source_priority(candidate.source_file),
        -candidate.depth,
    ) < (
        _source_priority(existing.source_file),
        -existing.depth,
    )


def _prefer_requirement(existing: Requirement, candidate: Requirement) -> bool:
    return (
        _source_priority(candidate.source_file),
        _kind_priority(candidate.kind),
        -candidate.depth,
    ) < (
        _source_priority(existing.source_file),
        _kind_priority(existing.kind),
        -existing.depth,
    )


def _classify_source_type(rel_path: Path) -> str:
    parts = rel_path.parts
    if "01-customer-requirements" in parts:
        return SourceType.CUSTOMER.value
    if "00-current-product" in parts:
        return SourceType.CURRENT.value
    if "02-competitors" in parts or "13-competitors" in parts:
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
    re.compile(r'(人天|报价|乙方应|甲方应|投标|招标|中标|供应商应)'),  # commercial terms
    re.compile(r'(平衡计分卡|考核表|考核目标|绩效考核|目标管理责任)'),  # performance assessment
    re.compile(r'(安全生产|综合治理|隐患整改率|应急演练执行率)'),  # safety management policy
    re.compile(r'(根据.*更新|根据.*新增|根据.*沟通|根据.*反馈|根据.*调研)'),  # version history
    re.compile(r'(开发和运行要求|运行要求|操作系统|数据库.*要求)'),  # IT infrastructure
    re.compile(r'^实施范围'),  # project scope
    re.compile(r'^(修改原因|关联业务说明|名词解释|功能操作注意|要点说明|文档目的|操作菜单|操作界面|参考文档|模块说明|功能手册|功能介绍|概要信息|步骤名称|业务要点|目录表|适用范围|文档名)$'),  # doc metadata
    re.compile(r'^(简介|说明|附表|基本信息|其他|链接|按钮|附件|姓名|合计|描述|金额|日期|时间|名称|单位)$'),  # generic labels
    re.compile(r'^Unnamed'),                  # pandas/xlsx column artifacts
    re.compile(r'^NaN\s*$'),                  # null cell artifacts
    re.compile(r'^20\d{2}年\d{1,2}月'),       # standalone year-month dates
    re.compile(r'^20\d{2}-\d{1,2}-\d{1,2}'),  # standalone full dates
    re.compile(r'^\d{4}年\d{1,2}月份'),       # "2019年8月份..." dates
    re.compile(r'^(FW|GC|WL)\d+'),            # maintenance item codes (锦和)
    re.compile(r'^XM-\d+'),                   # project IDs (华侨城)
    re.compile(r'(并稿|初审|复审|终稿|草稿)'), # document revision stages
    re.compile(r'(有限公司|股份有限公司|企业管理有限公司|置业|房地产开发|经纪|资产管理有限|投资管理有限)'),  # company names
    re.compile(r'(系统测试计划|软件测试|交付文档|交付材料|运维部署|运维支持|运行日志|数据备份和恢复|部署指南)'),  # project delivery artifacts
    re.compile(r'(灰度发布|微服务架构|中台架构|容器化部署|双活|多活|自主可控|容错性|敏捷部署)'),  # architecture requirements
    re.compile(r'^(可用性|兼容性|稳定性|可靠性|安全性|多应用架构要求|架构标准|技术集成要求|其他系统组件要求|DevOps\s*规范)$'),  # non-functional requirements
    re.compile(r'(知识产权|商用权利|源代码.*交付|二次开发.*源代码|软件著作权)'),  # IP/legal terms in function field
    re.compile(r'(变更管理要求|技术支持要求|免费运维|技术开发|技术安全|培训支持|培训计划|售后服务|运维服务期满|项目进度要求|服务团队配置)'),  # project implementation requirements
    re.compile(r'^总结'),  # document summary sections
    re.compile(r'^招\s*标\s*文\s*件'),  # bidding document titles with spaces
    re.compile(r'^(天数|小计|人均|字段分类|办事指南|二级模块概述)$'),  # table field labels not yet covered
    re.compile(r'^(入住率|平均房价|间房收|客房收入|宴会指标|售票数|计价人数|门票收入|非门票收入|人均票|人均消费|对标市场|委托方|运营方)$'),  # hospitality/tourism metrics out of scope
    re.compile(r'^(驻场办公|管理范围内授权|产品设计|UI/UE|整体需求|范围要求|技术目标|引言|采购具体需求)$'),  # project doc sections
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
    result = re.sub(r'\bNaN\b', '', result)
    result = re.sub(r'Unnamed:\s*\d+', '', result)
    result = re.sub(r'\s{2,}', ' ', result).strip()
    return result[:200]


def _classify_requirement_kind(source_file: str, heading: str, nearby_text: str, source_type: str) -> str:
    combined = f"{source_file} {heading} {nearby_text} {source_type}"
    section_titles = {
        "合同模板",
        "新合同申请",
        "合同概要字段显示配置",
        "合同变更",
        "合同改期",
        "合同提前",
        "合同推迟",
        "合同延期",
        "合同终止",
        "合同作废",
        "合同保存",
        "合同保存草稿",
        "合同查询",
        "合同台账",
        "结算周期",
        "账款条款",
        "销售付款扣率",
        "滞纳金条款",
        "免租条款",
        "调租条款",
        "条件免租条款",
        "一次性费用",
        "预存款条款",
        "自定义条款",
        "合同附件",
        "结束申请",
        "结算预览",
    }
    if heading in section_titles:
        return "clause-group"
    if heading in {"合同基本信息", "基本信息"} and any(token in nearby_text for token in ("合同", "条款", "字段", "配置", "显示")):
        return "clause-group"
    if any(keyword in combined for keyword in ("权限", "授权", "用户组", "岗位", "角色", "数据权限", "模块权限", "授权组", "组织管理", "用户管理")):
        return "permission"
    if any(keyword in combined for keyword in ("流程", "审批", "流转", "待办", "节点", "会签", "委派", "候选人", "签收", "生效", "作废", "发起", "终止", "回调", "定时事件")):
        return "workflow"
    if any(keyword in combined for keyword in ("数据结构", "表结构", "数据逻辑", "模型", "实体", "主表", "明细表", "子表", "关联表", "字段定义", "字段说明", "表单关键字段", "关键字段", "账款表", "合同账务表", "结构分类", "汇总明细表", "账款模型")):
        return "data-structure"
    return "feature"


def _extract_clause_items(section_text: str) -> tuple[tuple[str, str], ...]:
    items: list[tuple[str, str]] = []
    for raw_line in section_text.splitlines():
        line = raw_line.strip().strip("*")
        if not line or line.startswith(("!", "|", "```")):
            continue
        if "：" not in line and ":" not in line and "包括" not in line and "包含" not in line:
            continue
        left, sep, right = line.partition("：") if "：" in line else line.partition(":")
        head = _strip_section_prefix(left).strip().strip("：:，,。；;")
        body = right.strip().strip("。；;") if sep else line
        if not head:
            continue
        if len(head) > 40 and not any(keyword in head for keyword in ("合同", "条款", "周期", "字段", "信息", "配置", "说明")):
            continue
        if body:
            items.append((head, body))
        quote_items: list[str] = []
        for match in re.findall(r"“([^”]+)”|\"([^\"]+)\"", body or line):
            quote_items.append(match[0] or match[1])
        if quote_items:
            for item in quote_items:
                if item and item != head:
                    items.append((item, body or line))
    return tuple(items)


def _extract_customer(rel_path: Path) -> str:
    """Extract customer name from path segment after source-type directory."""
    parts = rel_path.parts
    for i, part in enumerate(parts):
        if "01-customer-requirements" in part and i + 1 < len(parts):
            return parts[i + 1]
    return ""


def _classify_module(
    scenario: str, sub_scenario: str, function: str, ontology: dict[str, Any]
) -> str | None:
    """Phase 1: classify requirement into business module using weighted signals."""
    modules = ontology.get("modules", {})
    if not isinstance(modules, dict):
        return None
    scores: dict[str, float] = {}
    for mod_name, mod_data in modules.items():
        if not isinstance(mod_data, dict):
            continue
        score = 0.0
        for alias in mod_data.get("aliases", []):
            if not isinstance(alias, str):
                continue
            if alias in scenario:
                score += len(alias) * 3
            if alias in sub_scenario:
                score += len(alias) * 2
            if alias in function:
                score += len(alias)
        for sub in mod_data.get("sub_functions", {}).values():
            if not isinstance(sub, dict):
                continue
            for term in sub.get("terms", []):
                if isinstance(term, str) and term in function:
                    score += len(term) * 0.5
        if score > 0:
            scores[mod_name] = score
    if scores:
        return max(scores, key=lambda k: scores[k])
    return None


def _match_with_context(
    function: str,
    scenario: str,
    sub_scenario: str,
    ontology: dict[str, Any],
    flat_aliases: dict[str, str],
    nearby_text: str = "",
) -> str:
    """Three-phase matching with module classification and nearby_text fallback.

    Phase 1: classify module, then exact term match in ``function``.
    Phase 2: if function has no hit, long-term (≥4 chars) match in
    ``nearby_text`` within the same module.
    Phase 3: if module classification failed entirely, global nearby_text
    search across all modules (long terms ≥5 chars, stricter to avoid false hits).
    Phase 4: flat alias matching on function alone.
    """
    mod_name = _classify_module(scenario, sub_scenario, function, ontology)
    if mod_name:
        mod_data = ontology.get("modules", {}).get(mod_name, {})
        if isinstance(mod_data, dict):
            # Phase 1: function exact match
            for sub in mod_data.get("sub_functions", {}).values():
                if not isinstance(sub, dict):
                    continue
                caps = sub.get("capabilities", [])
                terms = sub.get("terms", [])
                if not isinstance(caps, list) or not isinstance(terms, list) or not caps:
                    continue
                for term in sorted(terms, key=len, reverse=True):
                    if isinstance(term, str) and term in function:
                        return str(caps[0])
            # Phase 2: nearby_text fallback (long terms only, ≥4 chars)
            if nearby_text:
                for sub in mod_data.get("sub_functions", {}).values():
                    if not isinstance(sub, dict):
                        continue
                    caps = sub.get("capabilities", [])
                    terms = sub.get("terms", [])
                    if not isinstance(caps, list) or not isinstance(terms, list) or not caps:
                        continue
                    for term in sorted(terms, key=len, reverse=True):
                        if isinstance(term, str) and len(term) >= 4 and term in nearby_text:
                            return str(caps[0])
    elif nearby_text:
        # Phase 3: module classification failed — global nearby_text search (≥5 chars)
        for mod_data in ontology.get("modules", {}).values():
            if not isinstance(mod_data, dict):
                continue
            for sub in mod_data.get("sub_functions", {}).values():
                if not isinstance(sub, dict):
                    continue
                caps = sub.get("capabilities", [])
                terms = sub.get("terms", [])
                if not isinstance(caps, list) or not isinstance(terms, list) or not caps:
                    continue
                for term in sorted(terms, key=len, reverse=True):
                    if isinstance(term, str) and len(term) >= 5 and term in nearby_text:
                        return str(caps[0])
    return _normalize_term(function, flat_aliases)


def _parse_requirements(
    md_path: Path, docs_root: Path, aliases: dict[str, str], ontology: dict[str, Any]
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
            clean_t = re.sub(r'[*#`~]', '', t).strip()
            if d == 1 and scenario == "未分类":
                scenario = clean_t
            elif d == 2 and not sub_scenario:
                sub_scenario = clean_t

        _GENERIC_SCENARIOS = {"一级模块", "二级模块", "三级模块", "序号", "编号", "分类", "说明", "基础数据"}
        _SKIP_SCENARIOS = {"业态代码"}
        if scenario in _SKIP_SCENARIOS:
            stack.append((cand.depth, cand.text))
            continue
        if scenario in _GENERIC_SCENARIOS:
            scenario = "未分类"

        is_leaf = True
        for j in range(i + 1, len(candidates)):
            if candidates[j].depth > cand.depth:
                is_leaf = False
                break
            if candidates[j].depth <= cand.depth:
                break

        if is_leaf and not _is_noise_text(cand.text):
            nearby = _extract_nearby_text(text, cand.end)
            canonical_heading = _normalize_clause_heading(cand.text)
            normalized = _match_with_context(canonical_heading, scenario, sub_scenario, ontology, aliases, nearby)
            nearby_images = _nearby_image_refs(text, cand.pos, image_refs)
            kind = _classify_requirement_kind(str(rel_path), canonical_heading, nearby, source_type)
            clause_items = _extract_clause_items(nearby)
            clause_parent = ""
            clause_path = ""
            if kind == "clause-group" and clause_items:
                clause_parent = canonical_heading
                clause_path = " / ".join(item for item, _ in clause_items[:4])
            req = Requirement(
                source_file=str(rel_path),
                source_type=source_type,
                source_customer=source_customer,
                scenario=scenario,
                sub_scenario=sub_scenario,
                function=canonical_heading,
                depth=cand.depth,
                nearby_text=nearby,
                normalized_term=normalized,
                evidence=(doc_ref, *nearby_images),
                kind=kind,
                clause_parent=clause_parent,
                clause_path=clause_path,
            )
            dedup_key = canonical_heading if canonical_heading.startswith("数据结构") else normalized
            existing = requirements.get(dedup_key)
            if existing is None or cand.depth > existing.depth:
                requirements[dedup_key] = req

            if kind == "clause-group":
                for clause_name, clause_desc in clause_items:
                    clause_norm = _normalize_term(f"{canonical_heading} {clause_name}", aliases)
                    clause_req = Requirement(
                        source_file=str(rel_path),
                        source_type=source_type,
                        source_customer=source_customer,
                        scenario=scenario,
                        sub_scenario=canonical_heading if not sub_scenario else sub_scenario,
                        function=clause_name,
                        depth=cand.depth + 1,
                        nearby_text=clause_desc,
                        normalized_term=clause_norm,
                        evidence=(doc_ref, *nearby_images),
                        kind="clause-field",
                        clause_parent=canonical_heading,
                        clause_path=f"{canonical_heading} / {clause_name}",
                    )
                    existing_clause = requirements.get(clause_norm)
                    if existing_clause is None or clause_req.depth > existing_clause.depth:
                        requirements[clause_norm] = clause_req

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
            kind=_classify_requirement_kind(str(rel_path), md_path.stem, "", source_type),
            clause_parent="",
            clause_path="",
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


def _merge_requirement(
    requirements: dict[tuple[str, str], Requirement],
    req: Requirement,
) -> None:
    key = (req.normalized_term, req.function)
    existing = requirements.get(key)
    if existing is None:
        requirements[key] = req
        return
    if _prefer_requirement(existing, req):
        requirements[key] = Requirement(
            source_file=req.source_file,
            source_type=req.source_type,
            source_customer=req.source_customer,
            scenario=req.scenario,
            sub_scenario=req.sub_scenario,
            function=req.function,
            depth=req.depth,
            nearby_text=req.nearby_text,
            normalized_term=req.normalized_term,
            evidence=_merge_evidence(existing.evidence, req.evidence),
            kind=req.kind,
            clause_parent=req.clause_parent,
            clause_path=req.clause_path,
        )
    else:
        requirements[key] = Requirement(
            source_file=existing.source_file,
            source_type=existing.source_type,
            source_customer=existing.source_customer,
            scenario=existing.scenario,
            sub_scenario=existing.sub_scenario,
            function=existing.function,
            depth=existing.depth,
            nearby_text=existing.nearby_text,
            normalized_term=existing.normalized_term,
            evidence=_merge_evidence(existing.evidence, req.evidence),
            kind=existing.kind,
            clause_parent=existing.clause_parent,
            clause_path=existing.clause_path,
        )


def extract(
    docs_root: Path,
    skill_root: Path,
    project: str = "商管系统",
    extra_roots: list[Path] | None = None,
) -> DocMap:
    aliases, ontology = _load_aliases(skill_root)
    md_files = _iter_markdown_files(docs_root)
    features: dict[str, DocFeature] = {}
    requirements: dict[tuple[str, str], Requirement] = {}
    for md_path in md_files:
        for feature in _parse_markdown(md_path, docs_root, aliases):
            existing = features.get(feature.normalized_term)
            if existing is None or _prefer_doc_feature(existing, feature):
                features[feature.normalized_term] = feature
        for req in _parse_requirements(md_path, docs_root, aliases, ontology):
            _merge_requirement(requirements, req)
    for extra_root in (extra_roots or []):
        virtual_parent = extra_root.parent
        for md_path in _iter_markdown_files(extra_root):
            for feature in _parse_markdown(md_path, virtual_parent, aliases):
                existing = features.get(feature.normalized_term)
                if existing is None or _prefer_doc_feature(existing, feature):
                    features[feature.normalized_term] = feature
            for req in _parse_requirements(md_path, virtual_parent, aliases, ontology):
                _merge_requirement(requirements, req)
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
                "kind": r.kind,
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
    parser.add_argument("--extra-docs-root", action="append", default=[])
    args = parser.parse_args()

    extra_roots = [Path(r) for r in args.extra_docs_root if r]
    doc_map = extract(Path(args.docs_root), Path(args.skill_root), args.project, extra_roots or None)
    payload = json.dumps(to_json(doc_map), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
