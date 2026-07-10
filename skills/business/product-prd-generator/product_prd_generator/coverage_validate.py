"""Coverage validation mode for product-prd-generator.

Pivots reconcile output into customer/competitor coverage matrices,
detects incremental gaps vs baseline, and flags weak evidence for review.

Usage (called by main.py when --mode coverage-validate):
    python -m product_prd_generator.coverage_validate \
        --reconcile parsed/capability-reconciliation.json \
        --doc-map parsed/current-doc-map.json \
        --output-dir output \
        [--baseline parsed/coverage-baseline.json] \
        [--update-baseline] \
        [--customers a,b,c] \
        [--competitors x,y,z]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# --- Constants ---

_MIN_FUNC_LEN_FOR_STRONG = 10
_MIN_NEARBY_FOR_STRONG = 30
_DOMAIN_KEYWORDS = frozenset(
    {
        "账龄", "催缴", "催费", "催款", "催收", "转移", "冲抵", "核销",
        "发票", "开票", "红冲", "小票", "日结", "抄表", "仪表", "峰谷",
        "峰平谷", "进撤场", "撤场", "自定义", "预收", "保证金", "暂收",
        "临时费用", "零星", "直接费用", "预期收入", "权责", "现金流",
        "托收", "银企", "银行流水", "自动核销", "自动认领",
    }
)

# Capabilities whose 明源 evidence may come from 住宅/售楼 domain, not 商管
_AMBIGUOUS_DOMAIN_TERMS = frozenset(
    {"账龄", "成本", "计划", "货值", "售楼", "营销"}
)

_DEMO_PROBE_PREFIX = "competitor-analysis/qimao/"

_BOLD_ITEM = re.compile(r"^-\s+\*\*(.+?)\*\*\s*(.*)$")
_SECTION = re.compile(r"^##\s+\d+\.\s*(.+?)（")


def _load_term_aliases(skill_root: Path) -> dict[str, str]:
    aliases_path = skill_root / "references" / "term-aliases.yaml"
    if not aliases_path.exists() or yaml is None:
        return {}
    with aliases_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        return {}
    inverted: dict[str, str] = {}
    for spec_id, alias_list in data.items():
        if isinstance(alias_list, list):
            for alias in alias_list:
                inverted[alias] = spec_id
        elif isinstance(alias_list, str):
            inverted[alias_list] = spec_id
    return inverted


def _normalize_term_simple(heading: str, aliases: dict[str, str]) -> str:
    cleaned = re.sub(r"[`*_~]", "", heading).strip()
    for alias in sorted(aliases.keys(), key=len, reverse=True):
        if alias in cleaned:
            return aliases[alias]
    return cleaned


def load_capability_map(
    map_dir: Path,
    aliases: dict[str, str],
) -> list[dict]:
    """Load a structured capability map from a competitor analysis directory.

    Auto-discovers ``*-capability-map.md`` in the directory.
    Competitor name is derived from the directory name and normalized
    via :data:`_COMPETITOR_NAME_ALIASES`.
    """
    candidates = sorted(map_dir.glob("*capability-map.md"))
    candidates += sorted(map_dir.glob("*-capability-map.md"))
    if not candidates:
        return []

    map_file = candidates[0]
    competitor_raw = map_dir.name
    source_file = f"competitor-analysis/{competitor_raw}/{map_file.name}"

    spec_id_in_parens = re.compile(r"（→\s*(.+?)）")

    features: list[dict] = []
    current_module = ""

    for line in map_file.read_text(encoding="utf-8").splitlines():
        sec_match = _SECTION.match(line)
        if sec_match:
            current_module = sec_match.group(1).strip()
            continue

        item_match = _BOLD_ITEM.match(line)
        if not item_match:
            continue

        raw_name = item_match.group(1).strip()
        trailing = item_match.group(2).strip()

        explicit_spec = spec_id_in_parens.search(raw_name)
        if explicit_spec:
            normalized = explicit_spec.group(1).strip()
            name = spec_id_in_parens.sub("", raw_name).strip()
        else:
            name = raw_name
            spec_in_trailing = spec_id_in_parens.search(trailing)
            if spec_in_trailing:
                normalized = spec_in_trailing.group(1).strip()
                description = spec_id_in_parens.sub("", trailing).strip("：: ")
            else:
                normalized = _normalize_term_simple(name, aliases)
                description = trailing.lstrip("：: ").strip()

        features.append(
            {
                "source_file": source_file,
                "source_type": "competitor",
                "heading": name,
                "depth": 3,
                "normalized_term": normalized,
                "evidence": [
                    {
                        "kind": "doc",
                        "ref": source_file,
                        "note": f"{current_module}: {description[:80]}" if description else current_module,
                    }
                ],
            }
        )

    return features


# --- Data classes ---


@dataclass(frozen=True, slots=True)
class Cell:
    """One cell in the coverage matrix (customer/competitor × capability)."""

    strength: str  # strong | medium | weak | absent
    source_files: tuple[str, ...] = ()
    note: str = ""
    matched_count: int = 0


@dataclass(frozen=True, slots=True)
class CapabilityRow:
    """One row in the coverage matrix."""

    capability_id: str
    capability_name: str
    module: str
    customer_cells: dict[str, Cell] = field(default_factory=dict)
    competitor_cells: dict[str, Cell] = field(default_factory=dict)
    overall_strength: str = "weak"
    prd_status: str = ""
    confidence: str = "low"
    needs_review: bool = False
    review_reasons: tuple[str, ...] = ()
    recommendation: str = ""


@dataclass(frozen=True, slots=True)
class DeltaItem:
    source_type: str
    source_org: str
    normalized_term: str
    function: str
    nearby_text: str
    matched_capability: str
    priority: str


@dataclass(frozen=True, slots=True)
class DeltaReport:
    new_items: tuple[DeltaItem, ...] = ()
    dropped_count: int = 0
    modified_count: int = 0


# --- Loading ---


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# --- Competitor name extraction ---


_COMPETITOR_NAME_ALIASES = {
    "haiding": "海鼎",
    "mingyuan": "明源",
    "xuewei": "学伟",
    "qimao": "旗茂",
}


def _extract_competitor_name(source_file: str) -> str:
    """Extract competitor name from source_file path.

    Handles four path patterns:
    - 02-competitors/海鼎/...        (raw scan, Chinese names)
    - 13-competitors/haiding/...    (materials scan, English names)
    - competitor-analysis/qimao/...  (demo probe data)
    - competitor-analysis/haiding/... (structured capability maps)
    """
    parts = source_file.replace("\\", "/").split("/")
    raw_name = ""
    for i, part in enumerate(parts):
        if part in ("02-competitors", "13-competitors", "competitor-analysis") and i + 1 < len(parts):
            raw_name = parts[i + 1]
            break
        if part == "qimao":
            raw_name = "qimao"
            break
    return _COMPETITOR_NAME_ALIASES.get(raw_name, raw_name)


def _extract_customer_from_path(source_file: str) -> str:
    """Extract customer name from source_file path (fallback if source_customer empty)."""
    parts = source_file.replace("\\", "/").split("/")
    for i, part in enumerate(parts):
        if "01-customer-requirements" in part and i + 1 < len(parts):
            return parts[i + 1]
    return ""


# --- Scoring ---


def _has_domain_keyword(text: str) -> bool:
    return any(kw in text for kw in _DOMAIN_KEYWORDS)


def _score_customer_cell(reqs: list[dict]) -> Cell:
    """Score evidence strength for one (customer, capability) cell."""
    if not reqs:
        return Cell(strength="absent")

    matched = [r for r in reqs if r.get("matched_capability")]
    if not matched:
        return Cell(strength="absent")

    source_files = tuple(
        sorted(set(r.get("source_file", "") for r in matched if r.get("source_file")))
    )
    matched_count = len(matched)

    # Strong: ≥2 matched, or 1 matched with descriptive function/nearby_text
    best = max(matched, key=lambda r: len(r.get("nearby_text", "")))
    func_text = best.get("function", "")
    nearby = best.get("nearby_text", "")

    if matched_count >= 2:
        strength = "strong"
    elif len(nearby) >= _MIN_NEARBY_FOR_STRONG:
        strength = "strong"
    elif _has_domain_keyword(func_text) and len(func_text) >= _MIN_FUNC_LEN_FOR_STRONG:
        strength = "strong"
    else:
        strength = "medium"

    return Cell(
        strength=strength,
        source_files=source_files,
        matched_count=matched_count,
    )


def _score_competitor_cell(features: list[dict]) -> Cell:
    """Score evidence strength for one (competitor, capability) cell."""
    if not features:
        return Cell(strength="absent")

    source_files = tuple(
        sorted(set(f.get("source_file", "") for f in features if f.get("source_file")))
    )
    feature_count = len(features)

    # Check source quality: .doc.md = manual (strong), .pptx.md/.xlsx.md = presentation (medium)
    has_manual = any(
        ".doc.md" in f.get("source_file", "") or "功能手册" in f.get("source_file", "")
        for f in features
    )
    has_presentation = any(
        ".pptx.md" in f.get("source_file", "") or ".xlsx.md" in f.get("source_file", "")
        for f in features
    )
    has_demo = any(_DEMO_PROBE_PREFIX in f.get("source_file", "") for f in features)

    if feature_count >= 2 or has_manual:
        strength = "strong"
    elif has_presentation or has_demo:
        strength = "medium"
    else:
        strength = "medium"

    return Cell(
        strength=strength,
        source_files=source_files,
        matched_count=feature_count,
    )


def _score_overall(customer_cells: dict[str, Cell], competitor_cells: dict[str, Cell]) -> str:
    """Score overall evidence strength for a capability row."""
    c_strong = sum(1 for c in customer_cells.values() if c.strength == "strong")
    c_medium = sum(1 for c in customer_cells.values() if c.strength == "medium")
    comp_strong = sum(1 for c in competitor_cells.values() if c.strength == "strong")

    if c_strong >= 3 or (c_strong >= 2 and comp_strong >= 1):
        return "customer_consensus_strong"
    if c_strong >= 1 or c_medium >= 2:
        if c_strong <= 1 and c_strong > 0:
            return "single_customer_strong"
        return "customer_consensus_medium"
    if comp_strong >= 2:
        return "competitor_supported"
    if comp_strong == 1:
        return "competitor_single"
    return "weak"


# --- Review flagging ---


def _flag_review(
    cap_id: str,
    cap_name: str,
    customer_cells: dict[str, Cell],
    competitor_cells: dict[str, Cell],
) -> tuple[bool, tuple[str, ...]]:
    """Check if this capability needs manual review. Returns (needs_review, reasons)."""
    reasons: list[str] = []

    # domain_ambiguous: 明源 evidence on terms that could be 住宅/售楼
    mingyuan_cell = competitor_cells.get("明源")
    if mingyuan_cell and mingyuan_cell.strength != "absent":
        if any(kw in cap_name for kw in _AMBIGUOUS_DOMAIN_TERMS):
            reasons.append("domain_ambiguous")

    # url_only: qimao evidence without manual/section refs
    qimao_cell = competitor_cells.get("旗茂")
    if qimao_cell and qimao_cell.strength != "absent":
        all_demo = all(
            _DEMO_PROBE_PREFIX in sf for sf in qimao_cell.source_files
        ) if qimao_cell.source_files else False
        if all_demo:
            reasons.append("url_only")

    # single_source_customer: only 1 customer strong, 0 competitor strong
    c_strong = sum(1 for c in customer_cells.values() if c.strength == "strong")
    comp_strong = sum(1 for c in competitor_cells.values() if c.strength == "strong")
    if c_strong == 1 and comp_strong == 0:
        reasons.append("single_source_customer")

    return (len(reasons) > 0, tuple(reasons))


# --- Matrix building ---


def _collect_matrix_cap_ids(
    cap_lookup: dict[str, dict],
    cust_groups: dict[str, dict[str, list[dict]]],
    comp_groups: dict[str, dict[str, list[dict]]],
) -> set[str]:
    """Collect capability IDs for matrix rows.

    Only includes capabilities defined in the reconcile output. Unmatched
    normalized_terms from requirements/features are excluded — they belong
    in the delta/gap report, not the coverage matrix.
    """
    return set(cap_lookup.keys())


def _build_capability_lookup(reconcile: dict) -> dict[str, dict]:
    """Build cap_id → capability dict from reconcile output."""
    return {c["id"]: c for c in reconcile.get("capabilities", [])}


def _group_requirements_by_customer(
    requirements: list[dict],
) -> dict[str, dict[str, list[dict]]]:
    """Group: customer → normalized_term → [reqs].

    Only includes matched requirements (matched_capability non-empty).
    Key is matched_capability (the spec ID), falling back to normalized_term.
    """
    result: dict[str, dict[str, list[dict]]] = {}
    for req in requirements:
        if req.get("source_type") != "customer-requirements":
            continue
        cap = req.get("matched_capability", "")
        if not cap:
            continue
        customer = req.get("source_customer", "") or _extract_customer_from_path(
            req.get("source_file", "")
        )
        if not customer:
            continue
        result.setdefault(customer, {}).setdefault(cap, []).append(req)
    return result


def _group_features_by_competitor(
    features: list[dict],
) -> dict[str, dict[str, list[dict]]]:
    """Group: competitor → normalized_term → [features].

    Key is normalized_term (the spec ID equivalent for competitor features).
    """
    result: dict[str, dict[str, list[dict]]] = {}
    for feat in features:
        if feat.get("source_type") != "competitor":
            continue
        term = feat.get("normalized_term", "")
        if not term:
            continue
        competitor = _extract_competitor_name(feat.get("source_file", ""))
        if not competitor:
            continue
        result.setdefault(competitor, {}).setdefault(term, []).append(feat)
    return result


def build_matrix(
    reconcile: dict,
    doc_map: dict,
    customers_filter: list[str] | None,
    competitors_filter: list[str] | None,
) -> list[CapabilityRow]:
    """Build the full coverage matrix (customer + competitor)."""
    cap_lookup = _build_capability_lookup(reconcile)

    cust_groups = _group_requirements_by_customer(reconcile.get("requirements", []))
    comp_groups = _group_features_by_competitor(doc_map.get("features", []))

    # Determine column sets
    all_customers = sorted(cust_groups.keys())
    if customers_filter:
        all_customers = [c for c in all_customers if c in set(customers_filter)]

    all_competitors = sorted(comp_groups.keys())
    if competitors_filter:
        all_competitors = [c for c in all_competitors if c in set(competitors_filter)]

    cap_ids = _collect_matrix_cap_ids(cap_lookup, cust_groups, comp_groups)

    rows: list[CapabilityRow] = []
    for cap_id in sorted(cap_ids):
        cap_info = cap_lookup.get(cap_id, {})
        cap_name = cap_info.get("name", cap_id)
        module = cap_info.get("module", "")

        # Build customer cells
        customer_cells: dict[str, Cell] = {}
        for customer in all_customers:
            reqs = cust_groups.get(customer, {}).get(cap_id, [])
            customer_cells[customer] = _score_customer_cell(reqs)

        # Build competitor cells
        competitor_cells: dict[str, Cell] = {}
        for competitor in all_competitors:
            feats = comp_groups.get(competitor, {}).get(cap_id, [])
            competitor_cells[competitor] = _score_competitor_cell(feats)

        overall = _score_overall(customer_cells, competitor_cells)
        needs_review, review_reasons = _flag_review(
            cap_id, cap_name, customer_cells, competitor_cells
        )

        prd_status = cap_info.get("reconciled_status", "")
        confidence = cap_info.get("confidence", "low")

        rows.append(
            CapabilityRow(
                capability_id=cap_id,
                capability_name=cap_name,
                module=module,
                customer_cells=customer_cells,
                competitor_cells=competitor_cells,
                overall_strength=overall,
                prd_status=prd_status,
                confidence=confidence,
                needs_review=needs_review,
                review_reasons=review_reasons,
            )
        )

    return rows


# --- Delta detection ---


def _requirement_signature(req: dict) -> str:
    raw = "|".join(
        [
            req.get("source_type", ""),
            req.get("source_customer", ""),
            req.get("normalized_term", ""),
            req.get("function", ""),
        ]
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _load_baseline(path: Path) -> dict | None:
    if not path.exists():
        return None
    return _load_json(path)


def detect_delta(
    requirements: list[dict],
    baseline: dict | None,
) -> DeltaReport:
    """Detect new/dropped/modified requirements vs baseline."""
    current_sigs: dict[str, dict] = {}
    for req in requirements:
        sig = _requirement_signature(req)
        current_sigs[sig] = req

    if baseline is None:
        # First run: everything is "new"
        new_items = tuple(
            DeltaItem(
                source_type=r.get("source_type", ""),
                source_org=r.get("source_customer", ""),
                normalized_term=r.get("normalized_term", ""),
                function=r.get("function", ""),
                nearby_text=r.get("nearby_text", "")[:200],
                matched_capability=r.get("matched_capability", ""),
                priority=r.get("priority", ""),
            )
            for r in requirements
        )
        return DeltaReport(new_items=new_items)

    baseline_sigs = baseline.get("signatures", {})
    new_sigs = set(current_sigs.keys()) - set(baseline_sigs.keys())
    dropped_sigs = set(baseline_sigs.keys()) - set(current_sigs.keys())

    # Modified: same sig but nearby_text hash changed
    modified = 0
    for sig in set(current_sigs.keys()) & set(baseline_sigs.keys()):
        curr_hash = hashlib.sha256(
            current_sigs[sig].get("nearby_text", "").encode()
        ).hexdigest()[:8]
        base_hash = baseline_sigs[sig].get("nearby_hash", "")
        if base_hash and curr_hash != base_hash:
            modified += 1

    new_items = tuple(
        DeltaItem(
            source_type=current_sigs[sig].get("source_type", ""),
            source_org=current_sigs[sig].get("source_customer", ""),
            normalized_term=current_sigs[sig].get("normalized_term", ""),
            function=current_sigs[sig].get("function", ""),
            nearby_text=current_sigs[sig].get("nearby_text", "")[:200],
            matched_capability=current_sigs[sig].get("matched_capability", ""),
            priority=current_sigs[sig].get("priority", ""),
        )
        for sig in sorted(new_sigs)
    )

    return DeltaReport(
        new_items=new_items,
        dropped_count=len(dropped_sigs),
        modified_count=modified,
    )


def build_baseline(requirements: list[dict]) -> dict:
    """Build baseline signature snapshot from current requirements."""
    signatures: dict[str, dict] = {}
    for req in requirements:
        sig = _requirement_signature(req)
        signatures[sig] = {
            "source_type": req.get("source_type", ""),
            "source_customer": req.get("source_customer", ""),
            "normalized_term": req.get("normalized_term", ""),
            "function": req.get("function", ""),
            "nearby_hash": hashlib.sha256(
                req.get("nearby_text", "").encode()
            ).hexdigest()[:8],
        }
    return {
        "schema_version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "signatures": signatures,
    }


# --- Rendering: JSON ---


def _matrix_to_customer_json(
    rows: list[CapabilityRow], customers: list[str]
) -> dict:
    return {
        "schema_version": "1",
        "project": "商管系统",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "customers": customers,
        "capabilities": [
            {
                "capability_id": r.capability_id,
                "capability_name": r.capability_name,
                "module": r.module,
                "customer_evidence": {
                    cust: {
                        "strength": r.customer_cells.get(cust, Cell(strength="absent")).strength,
                        "source_files": list(
                            r.customer_cells.get(cust, Cell(strength="absent")).source_files
                        ),
                        "matched_count": r.customer_cells.get(
                            cust, Cell(strength="absent")
                        ).matched_count,
                    }
                    for cust in customers
                },
                "overall_customer_strength": r.overall_strength,
                "prd_status": r.prd_status,
                "confidence": r.confidence,
                "needs_review": r.needs_review,
                "review_reasons": list(r.review_reasons),
            }
            for r in rows
        ],
    }


def _matrix_to_competitor_json(
    rows: list[CapabilityRow], competitors: list[str]
) -> dict:
    return {
        "schema_version": "1",
        "project": "商管系统",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "competitors": competitors,
        "capabilities": [
            {
                "capability_id": r.capability_id,
                "capability_name": r.capability_name,
                "module": r.module,
                "competitor_evidence": {
                    comp: {
                        "strength": r.competitor_cells.get(
                            comp, Cell(strength="absent")
                        ).strength,
                        "source_files": list(
                            r.competitor_cells.get(
                                comp, Cell(strength="absent")
                            ).source_files
                        ),
                        "matched_count": r.competitor_cells.get(
                            comp, Cell(strength="absent")
                        ).matched_count,
                    }
                    for comp in competitors
                },
                "overall_strength": r.overall_strength,
                "prd_status": r.prd_status,
                "confidence": r.confidence,
                "needs_review": r.needs_review,
                "review_reasons": list(r.review_reasons),
            }
            for r in rows
        ],
    }


# --- Rendering: Markdown ---


_STRENGTH_ICON = {
    "strong": "**强**",
    "medium": "中",
    "weak": "弱",
    "absent": "—",
}


def _render_customer_matrix_md(
    rows: list[CapabilityRow], customers: list[str]
) -> str:
    lines: list[str] = []
    lines.append("# PRD 客户需求覆盖度矩阵")
    lines.append("")
    lines.append(
        f"> 自动生成于 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"by product-prd-generator --mode coverage-validate"
    )
    lines.append("")

    # Sort rows: overall_strength strong first, then by customer consensus count
    strength_order = {
        "customer_consensus_strong": 0,
        "customer_consensus_medium": 1,
        "single_customer_strong": 2,
        "competitor_supported": 3,
        "competitor_single": 4,
        "weak": 5,
    }
    sorted_rows = sorted(
        rows, key=lambda r: (strength_order.get(r.overall_strength, 9), r.capability_id)
    )

    # Header
    header = "| 能力 | " + " | ".join(customers) + " | PRD状态 | 整体强度 | 需复核 |"
    sep = "|---|" + "|".join(["---"] * len(customers)) + "|---|---|---|"
    lines.append(header)
    lines.append(sep)

    for r in sorted_rows:
        cells = [
            _STRENGTH_ICON.get(
                r.customer_cells.get(c, Cell(strength="absent")).strength, "?"
            )
            for c in customers
        ]
        review = "✓" if r.needs_review else "✗"
        row_line = (
            f"| {r.capability_name} | "
            + " | ".join(cells)
            + f" | {r.prd_status or '—'} | {r.overall_strength} | {review} |"
        )
        lines.append(row_line)

    lines.append("")
    lines.append("> 强度说明：**强** = 明确功能/字段/流程证据；中 = 提及但细节不足；弱 = 仅周边语境；— = 未发现")
    lines.append("")
    return "\n".join(lines)


def _render_competitor_matrix_md(
    rows: list[CapabilityRow], competitors: list[str]
) -> str:
    lines: list[str] = []
    lines.append("# PRD 竞品覆盖度矩阵")
    lines.append("")
    lines.append(
        f"> 自动生成于 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} "
        f"by product-prd-generator --mode coverage-validate"
    )
    lines.append("")

    strength_order = {
        "customer_consensus_strong": 0,
        "customer_consensus_medium": 1,
        "single_customer_strong": 2,
        "competitor_supported": 3,
        "competitor_single": 4,
        "weak": 5,
    }
    sorted_rows = sorted(
        rows, key=lambda r: (strength_order.get(r.overall_strength, 9), r.capability_id)
    )

    header = "| 能力 | " + " | ".join(competitors) + " | PRD状态 | 整体强度 | 需复核 |"
    sep = "|---|" + "|".join(["---"] * len(competitors)) + "|---|---|---|"
    lines.append(header)
    lines.append(sep)

    for r in sorted_rows:
        cells = [
            _STRENGTH_ICON.get(
                r.competitor_cells.get(comp, Cell(strength="absent")).strength, "?"
            )
            for comp in competitors
        ]
        review = "✓" if r.needs_review else "✗"
        row_line = (
            f"| {r.capability_name} | "
            + " | ".join(cells)
            + f" | {r.prd_status or '—'} | {r.overall_strength} | {review} |"
        )
        lines.append(row_line)

    lines.append("")
    lines.append("> 强度说明：**强** = 功能手册/操作手册级证据；中 = pptx/xlsx/demo 探测级证据；— = 未发现")
    lines.append("")
    return "\n".join(lines)


def _render_delta_md(delta: DeltaReport, baseline_path: Path | None, doc_map: dict | None = None) -> str:
    lines: list[str] = []
    lines.append("# 增量 Gap 报告")
    lines.append("")

    if baseline_path and baseline_path.exists():
        baseline_data = _load_json(baseline_path)
        baseline_time = baseline_data.get("generated_at", "unknown")
        lines.append(f"对比 baseline: `{baseline_path}` ({baseline_time})")
    else:
        lines.append("⚠️ 未找到 baseline，本次为首次运行，全部 requirement 计为新增。")

    lines.append(f"当前运行: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")

    new_customer = [d for d in delta.new_items if d.source_type == "customer-requirements"]
    new_competitor = [d for d in delta.new_items if d.source_type == "competitor"]

    lines.append(f"## 新增需求（共 {len(delta.new_items)} 条）")
    lines.append("")
    lines.append(f"- 客户需求: {len(new_customer)} 条")
    lines.append(f"- 竞品能力: {len(new_competitor)} 条")
    lines.append("")

    if new_customer:
        matched = [d for d in new_customer if d.matched_capability]
        unmatched = [d for d in new_customer if not d.matched_capability]

        lines.append(f"### 已匹配到能力（{len(matched)} 条）")
        lines.append("")
        if matched:
            lines.append("| 来源客户 | 能力 | 功能描述 | 优先级 |")
            lines.append("|---|---|---|---|")
            for d in matched[:50]:
                func_short = d.function[:60].replace("|", "\\|") if d.function else ""
                lines.append(
                    f"| {d.source_org} | {d.matched_capability} | {func_short} | {d.priority} |"
                )
            if len(matched) > 50:
                lines.append(f"\n...（共 {len(matched)} 条，仅显示前 50）")
        lines.append("")

        lines.append(f"### 未匹配到能力（{len(unmatched)} 条）— 候选新能力")
        lines.append("")
        if unmatched:
            lines.append("| 来源客户 | 标准术语 | 功能描述 |")
            lines.append("|---|---|---|")
            for d in unmatched[:50]:
                func_short = d.function[:60].replace("|", "\\|") if d.function else ""
                lines.append(
                    f"| {d.source_org} | {d.normalized_term or '(未归一)'} | {func_short} |"
                )
            if len(unmatched) > 50:
                lines.append(f"\n...（共 {len(unmatched)} 条，仅显示前 50）")
        lines.append("")

    if doc_map:
        cap_ids_set = set()
        reconcile_data = None
        lines.append("### 竞品未匹配能力汇总")
        lines.append("")
        lines.append("以下竞品能力未归一到现有 ontology，需扩充 term-aliases.yaml 后才能进入覆盖度矩阵。")
        lines.append("")

        comp_features = [f for f in doc_map.get("features", []) if f.get("source_type") == "competitor"]
        comp_groups: dict[str, list[dict]] = {}
        for f in comp_features:
            comp_name = _extract_competitor_name(f.get("source_file", ""))
            if comp_name:
                comp_groups.setdefault(comp_name, []).append(f)

        lines.append("| 竞品 | 总能力 | 已归一 | 未归一 |")
        lines.append("|---|---|---|---|")
        for comp_name in sorted(comp_groups.keys()):
            feats = comp_groups[comp_name]
            terms = set(f.get("normalized_term", "") for f in feats)
            lines.append(f"| {comp_name} | {len(feats)} | {len(terms)} | — |")
        lines.append("")

    if delta.dropped_count > 0:
        lines.append(f"## 消失需求: {delta.dropped_count} 条（信息性）")
        lines.append("")
    if delta.modified_count > 0:
        lines.append(f"## 修改需求: {delta.modified_count} 条（nearby_text 变化，信息性）")
        lines.append("")

    return "\n".join(lines)


def _render_weak_evidence_md(rows: list[CapabilityRow]) -> str:
    lines: list[str] = []
    lines.append("# 弱证据 / 待人工确认项")
    lines.append("")
    lines.append(
        "以下能力的证据强度机器无法自动确定，需人工复核："
    )
    lines.append("")

    review_rows = [r for r in rows if r.needs_review]
    if not review_rows:
        lines.append("（无待确认项）")
        return "\n".join(lines)

    lines.append("| 能力 | 问题类型 | 详情 |")
    lines.append("|---|---|---|")

    for r in review_rows:
        details: list[str] = []
        for reason in r.review_reasons:
            if reason == "domain_ambiguous":
                details.append("明源证据可能来自住宅/售楼域，需确认是否商管")
            elif reason == "url_only":
                details.append("旗茂证据仅 URL/菜单名，无字段级证据")
            elif reason == "single_source_customer":
                strong_custs = [
                    c for c, cell in r.customer_cells.items() if cell.strength == "strong"
                ]
                details.append(f"仅 {', '.join(strong_custs)} 单客户强证据，需确认普适性")
        detail_text = "; ".join(details)
        lines.append(f"| {r.capability_name} | {', '.join(r.review_reasons)} | {detail_text} |")

    lines.append("")
    return "\n".join(lines)


def _coverage_priority(row: CapabilityRow) -> str:
    customer_count = sum(
        1 for cell in row.customer_cells.values()
        if cell.strength in {"strong", "medium", "weak"} and cell.matched_count > 0
    )
    if row.prd_status == "missing" and customer_count >= 2:
        return "P0"
    if row.prd_status in {"missing", "partial"}:
        return "P1" if customer_count >= 1 else "P2"
    return "P2"


def _slugify_change_id(raw: str, fallback_index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if slug:
        return slug[:64]
    return f"coverage-gap-{fallback_index:02d}"


def _build_suggested_changes(rows: list[CapabilityRow]) -> list[dict]:
    candidates = [
        row for row in rows
        if row.prd_status in {"missing", "partial"} or row.recommendation
    ]
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    changes: list[dict] = []
    seen_ids: set[str] = set()
    for idx, row in enumerate(candidates, 1):
        customers = [
            name for name, cell in row.customer_cells.items()
            if cell.strength in {"strong", "medium", "weak"} and cell.matched_count > 0
        ]
        competitors = [
            name for name, cell in row.competitor_cells.items()
            if cell.strength in {"strong", "medium", "weak"} and cell.matched_count > 0
        ]
        priority = _coverage_priority(row)
        change_id = _slugify_change_id(row.capability_id or row.capability_name, idx)
        base_id = change_id
        suffix = 2
        while change_id in seen_ids:
            tail = f"-{suffix}"
            change_id = f"{base_id[:64 - len(tail)]}{tail}"
            suffix += 1
        seen_ids.add(change_id)
        changes.append({
            "change_id": change_id,
            "title": row.capability_name,
            "priority": priority,
            "module": row.module,
            "prd_status": row.prd_status or "unknown",
            "confidence": row.confidence,
            "customer_evidence": customers,
            "competitor_evidence": competitors,
            "recommendation": row.recommendation,
            "needs_review": row.needs_review,
            "review_reasons": list(row.review_reasons),
            "mi_action": (
                "目标项目确认后优先进入本轮 OpenSpec"
                if priority == "P0"
                else "目标项目确认后进入后续 OpenSpec 或 backlog"
            ),
        })
    return sorted(changes, key=lambda c: (priority_rank.get(str(c["priority"]), 9), str(c["change_id"])))


def _write_suggested_changes_yaml(output_dir: Path, rows: list[CapabilityRow]) -> Path:
    changes = _build_suggested_changes(rows)
    payload = {
        "generated_by": "product-prd-generator coverage-validate",
        "handoff_boundary": "PRD coverage side provides evidence and suggested grouping; target project owns OpenSpec decisions and implementation.",
        "source_files": {
            "customer_matrix": "PRD客户需求覆盖度矩阵.md",
            "competitor_matrix": "PRD竞品覆盖度矩阵.md",
            "delta_report": "增量gap报告.md",
            "weak_evidence_review": "review/evidence-weak-items.md",
        },
        "changes": changes,
    }
    path = output_dir / "suggested-openspec-changes.yaml"
    if yaml is not None:
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _write_mi_consumption_prompt(output_dir: Path, suggested_path: Path) -> Path:
    prompt = f"""# MI / 目标项目消费提示词（coverage-validate 增量）

在目标项目目录（如 `/opt/code/mi`）启动 OpenCode 后使用。

```text
请先读取当前项目 AGENTS.md、openspec/specs/、相关代码和测试基线，再消费 PRD 覆盖度校验结果，不要直接创建 change。

覆盖度矩阵：
- { (output_dir / 'PRD客户需求覆盖度矩阵.md').resolve() }
- { (output_dir / 'PRD竞品覆盖度矩阵.md').resolve() }
增量 gap 报告：{ (output_dir / '增量gap报告.md').resolve() }
建议 OpenSpec 拆分：{ suggested_path.resolve() }

请先输出目标项目增量实施确认稿：
1) 哪些 gap 已被现有 spec/code 覆盖，只是 PRD code_map 漏判
2) 哪些是真缺口，按 P0/P1/P2 分级
3) 哪些建议合并成一个 change，哪些必须拆开
4) 建议的普通 <CHANGE_ID> 清单、验收标准、回归范围
5) 哪些问题需要我确认

如果只是单个明确缺口，请切 Sisyphus 创建普通 OpenSpec change；如果本轮有多个 P0/P1 或存在跨模块依赖，请先切 Prometheus 生成 Implementation Plan v1。
等我确认后，再创建或更新 OpenSpec change。
```
"""
    path = output_dir / "mi-consumption-prompt.md"
    path.write_text(prompt, encoding="utf-8")
    return path


# --- CLI ---


def _parse_customers(raw: str) -> list[str] | None:
    if not raw:
        return None
    return [c.strip() for c in raw.split(",") if c.strip()]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="coverage_validate")
    parser.add_argument("--reconcile", required=True)
    parser.add_argument("--doc-map", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--review-dir", default="review")
    parser.add_argument("--baseline", default="")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--customers", default="")
    parser.add_argument("--competitors", default="")
    parser.add_argument("--skill-root", default="")
    parser.add_argument("--capability-map-dir", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    reconcile_path = Path(args.reconcile)
    doc_map_path = Path(args.doc_map)
    output_dir = Path(args.output_dir)
    review_dir = Path(args.review_dir)

    if not reconcile_path.exists():
        print(f"ERROR: reconcile file not found: {reconcile_path}", file=sys.stderr)
        return 1
    if not doc_map_path.exists():
        print(f"ERROR: doc_map file not found: {doc_map_path}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    reconcile = _load_json(reconcile_path)
    doc_map = _load_json(doc_map_path)

    for map_dir_str in args.capability_map_dir:
        map_dir = Path(map_dir_str)
        if not map_dir.is_dir():
            continue
        skill_root = Path(args.skill_root) if args.skill_root else None
        aliases = _load_term_aliases(skill_root) if skill_root else {}
        map_features = load_capability_map(map_dir, aliases)
        if map_features:
            existing_features = doc_map.get("features", [])
            doc_map["features"] = list(existing_features) + map_features
            competitor_name = _COMPETITOR_NAME_ALIASES.get(map_dir.name, map_dir.name)
            print(f"  {competitor_name}能力补充: {len(map_features)} 项")

    customers_filter = _parse_customers(args.customers)
    competitors_filter = _parse_customers(args.competitors)

    # 1. Build matrix
    rows = build_matrix(reconcile, doc_map, customers_filter, competitors_filter)

    # Determine actual column sets
    all_customers = sorted(
        set(c for r in rows for c in r.customer_cells.keys())
    ) if not customers_filter else customers_filter
    all_competitors = sorted(
        set(c for r in rows for c in r.competitor_cells.keys())
    ) if not competitors_filter else competitors_filter

    # 2. Delta detection
    baseline_path = Path(args.baseline) if args.baseline else None
    baseline = _load_baseline(baseline_path) if baseline_path else None
    delta = detect_delta(reconcile.get("requirements", []), baseline)

    # 3. Write outputs
    # Customer matrix
    cust_json = _matrix_to_customer_json(rows, all_customers)
    cust_json_path = output_dir / "PRD客户需求覆盖度矩阵.json"
    cust_json_path.write_text(
        json.dumps(cust_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  → {cust_json_path}")

    cust_md = _render_customer_matrix_md(rows, all_customers)
    cust_md_path = output_dir / "PRD客户需求覆盖度矩阵.md"
    cust_md_path.write_text(cust_md, encoding="utf-8")
    print(f"  → {cust_md_path}")

    # Competitor matrix
    comp_json = _matrix_to_competitor_json(rows, all_competitors)
    comp_json_path = output_dir / "PRD竞品覆盖度矩阵.json"
    comp_json_path.write_text(
        json.dumps(comp_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"  → {comp_json_path}")

    comp_md = _render_competitor_matrix_md(rows, all_competitors)
    comp_md_path = output_dir / "PRD竞品覆盖度矩阵.md"
    comp_md_path.write_text(comp_md, encoding="utf-8")
    print(f"  → {comp_md_path}")

    # Delta report
    delta_md = _render_delta_md(delta, baseline_path, doc_map)
    delta_path = output_dir / "增量gap报告.md"
    delta_path.write_text(delta_md, encoding="utf-8")
    print(f"  → {delta_path}")

    # Weak evidence review
    weak_md = _render_weak_evidence_md(rows)
    weak_path = review_dir / "evidence-weak-items.md"
    weak_path.write_text(weak_md, encoding="utf-8")
    print(f"  → {weak_path}")

    suggested_path = _write_suggested_changes_yaml(output_dir, rows)
    print(f"  → {suggested_path}")
    prompt_path = _write_mi_consumption_prompt(output_dir, suggested_path)
    print(f"  → {prompt_path}")

    # 4. Update baseline
    if args.update_baseline and baseline_path:
        new_baseline = build_baseline(reconcile.get("requirements", []))
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(
            json.dumps(new_baseline, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  → {baseline_path} (baseline updated)")

    # Summary
    print()
    print(f"矩阵: {len(rows)} 个能力 × {len(all_customers)} 客户 × {len(all_competitors)} 竞品")
    review_count = sum(1 for r in rows if r.needs_review)
    print(f"待复核: {review_count} 项")
    print(f"增量: {len(delta.new_items)} 新增 / {delta.dropped_count} 消失 / {delta.modified_count} 修改")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
