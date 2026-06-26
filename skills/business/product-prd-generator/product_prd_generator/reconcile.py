from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from typing import Any

from .models import RequirementRecord


@unique
class CapabilityStatus(str, Enum):
    EXISTING = "existing"
    PARTIAL = "partial"
    MISSING = "missing"
    EXPLICITLY_NOT_DO = "explicitly-not-do"


@unique
class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    kind: str
    ref: str


@dataclass(frozen=True, slots=True)
class ReconciledCapability:
    id: str
    name: str
    code_status: str
    doc_status: str
    reconciled_status: str
    confidence: str
    gaps: tuple[str, ...]
    evidence: tuple[EvidenceRef, ...]


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    project: str
    capabilities: tuple[ReconciledCapability, ...]
    requirements: tuple[RequirementRecord, ...] = ()


def _coerce_status(value: str) -> CapabilityStatus:
    try:
        return CapabilityStatus(value)
    except ValueError:
        return CapabilityStatus.MISSING


def _reconcile_pair(code_status: CapabilityStatus, doc_status: CapabilityStatus) -> tuple[CapabilityStatus, Confidence, tuple[str, ...]]:
    gaps: list[str] = []
    if code_status == CapabilityStatus.EXPLICITLY_NOT_DO:
        if doc_status != CapabilityStatus.EXPLICITLY_NOT_DO:
            gaps.append("doc describes a capability marked explicitly-not-do in code")
        return CapabilityStatus.EXPLICITLY_NOT_DO, Confidence.HIGH, tuple(gaps)
    if doc_status == CapabilityStatus.EXPLICITLY_NOT_DO:
        gaps.append("code implements a capability marked explicitly-not-do in doc")
        return CapabilityStatus.EXPLICITLY_NOT_DO, Confidence.LOW, tuple(gaps)
    if code_status == doc_status:
        confidence = Confidence.HIGH if code_status == CapabilityStatus.EXISTING else Confidence.MEDIUM
        return code_status, confidence, tuple(gaps)
    if code_status == CapabilityStatus.EXISTING and doc_status == CapabilityStatus.MISSING:
        gaps.append("doc gap: code has it but doc does not mention it")
        return CapabilityStatus.EXISTING, Confidence.MEDIUM, tuple(gaps)
    if code_status == CapabilityStatus.MISSING and doc_status == CapabilityStatus.EXISTING:
        gaps.append("phantom feature: doc claims it but code does not implement it")
        return CapabilityStatus.PARTIAL, Confidence.LOW, tuple(gaps)
    if code_status == CapabilityStatus.PARTIAL or doc_status == CapabilityStatus.PARTIAL:
        gaps.append("partial on one side; reconcile to partial")
        return CapabilityStatus.PARTIAL, Confidence.MEDIUM, tuple(gaps)
    return code_status, Confidence.MEDIUM, tuple(gaps)


def reconcile(code_map: Mapping[str, object], doc_map: Mapping[str, object]) -> ReconcileResult:
    project = str(code_map.get("project", doc_map.get("project", "商管系统")))
    by_id: dict[str, ReconciledCapability] = {}

    spec_capabilities = code_map.get("spec_capabilities", [])
    if isinstance(spec_capabilities, list):
        for cap in spec_capabilities:
            if not isinstance(cap, Mapping):
                continue
            cap_id = str(cap.get("id", ""))
            code_status = _coerce_status(str(cap.get("status", CapabilityStatus.MISSING.value)))
            evidence_items = cap.get("evidence", [])
            evidence: tuple[EvidenceRef, ...] = ()
            if isinstance(evidence_items, list):
                evidence = tuple(
                    EvidenceRef(kind=str(e.get("kind", "")), ref=str(e.get("ref", "")))
                    for e in evidence_items
                    if isinstance(e, Mapping)
                )
            reconciled, confidence, pair_gaps = _reconcile_pair(code_status, CapabilityStatus.MISSING)
            by_id[cap_id] = ReconciledCapability(
                id=cap_id,
                name=str(cap.get("name", cap_id)),
                code_status=code_status.value,
                doc_status=CapabilityStatus.MISSING.value,
                reconciled_status=reconciled.value,
                confidence=confidence.value,
                gaps=tuple(["spec has no doc evidence yet", *pair_gaps]),
                evidence=evidence,
            )

    matrix_rows = code_map.get("matrix_rows", [])
    if isinstance(matrix_rows, list):
        for row in matrix_rows:
            if not isinstance(row, Mapping):
                continue
            cap_id = str(row.get("id", ""))
            code_status = _coerce_status(str(row.get("mi_status", CapabilityStatus.MISSING.value)))
            if cap_id in by_id:
                existing = by_id[cap_id]
                reconciled, confidence, pair_gaps = _reconcile_pair(code_status, _coerce_status(existing.doc_status))
                by_id[cap_id] = ReconciledCapability(
                    id=cap_id,
                    name=existing.name,
                    code_status=code_status.value,
                    doc_status=existing.doc_status,
                    reconciled_status=reconciled.value,
                    confidence=confidence.value,
                    gaps=existing.gaps + pair_gaps,
                    evidence=existing.evidence,
                )
            else:
                reconciled, confidence, pair_gaps = _reconcile_pair(code_status, CapabilityStatus.MISSING)
                by_id[cap_id] = ReconciledCapability(
                    id=cap_id,
                    name=str(row.get("function_point", cap_id)),
                    code_status=code_status.value,
                    doc_status=CapabilityStatus.MISSING.value,
                    reconciled_status=reconciled.value,
                    confidence=confidence.value,
                    gaps=tuple(["matrix row without matching spec id", *pair_gaps]),
                    evidence=(),
                )

    doc_features = doc_map.get("features", [])
    if isinstance(doc_features, list):
        for feat in doc_features:
            if not isinstance(feat, Mapping):
                continue
            term = str(feat.get("normalized_term", ""))
            if term in by_id:
                existing = by_id[term]
                doc_status = CapabilityStatus.EXISTING
                reconciled, confidence, pair_gaps = _reconcile_pair(_coerce_status(existing.code_status), doc_status)
                evidence_items = feat.get("evidence", [])
                evidence = existing.evidence
                if isinstance(evidence_items, list):
                    evidence = evidence + tuple(
                        EvidenceRef(kind=str(e.get("kind", "")), ref=str(e.get("ref", "")))
                        for e in evidence_items
                        if isinstance(e, Mapping)
                    )
                stale_markers = ("spec has no doc evidence yet", "doc gap: code has it but doc does not mention it")
                # When a doc feature matches a spec capability, remove stale
                # "no doc evidence" gaps — they are no longer true. Without
                # this cleanup every matched capability carries a false gap.
                retained_gaps = tuple(g for g in existing.gaps if not any(m in g for m in stale_markers))
                by_id[term] = ReconciledCapability(
                    id=term,
                    name=existing.name,
                    code_status=existing.code_status,
                    doc_status=doc_status.value,
                    reconciled_status=reconciled.value,
                    confidence=confidence.value,
                    gaps=retained_gaps + pair_gaps,
                    evidence=evidence,
                )

    _add_unmatched_customer_requirements(by_id, doc_features)

    requirements = _build_requirement_records(doc_map, by_id)

    return ReconcileResult(
        project=project,
        capabilities=tuple(by_id.values()),
        requirements=requirements,
    )


def _add_unmatched_customer_requirements(
    by_id: dict[str, ReconciledCapability],
    doc_features: object,
) -> None:
    # Discovers customer requirements that have NO matching code capability,
    # creates them as `missing`. Capped at 80, sorted by depth (shallow =
    # core modules first) then by client count. Heavy noise filtering because
    # raw doc headings include IDs, metadata, and generic chapter names.
    if not isinstance(doc_features, list):
        return
    features_list: list[Mapping[str, object]] = [f for f in doc_features if isinstance(f, Mapping)]
    import re as _re

    noise = _re.compile(
        r"^("
        r"\d"
        r"|.*需求说明$"
        r"|.*业务流程图$"
        r"|.*[（(].*[)）]\s*$"
        r"|参考文档"
        r"|文档历史"
        r"|文档控制"
        r"|审核"
        r"|前言"
        r"|引言"
        r"|目录"
        r"|版本"
        r"|附录"
        r"|其他"
        r"|Unnamed"
        r"|NaN"
        r"|总结"
        r"|技术参数"
        r"|技术标准"
        r"|Notes"
        r"|谢谢"
        r"|[A-Z]{1,4}[\d\-\.]+"  # FW01, GC01, L02-01 等编号
        r"|#.*"  # markdown 残留
        r"|\|.*"  # 表格分隔符残留
        r"|EBITDA"
        r"|ATM"
        r"|OA"
        r"|SAP"
        r"|EAS"
        r"|DevOps"
        r"|API"
        r"|BI\b"
        r"|K2"
        r"|NaN"
        r"|.*公司"
        r"|.*科技"
        r"|.*集团"
        r"|文档编号"
        r"|密级"
        r"|修改原因"
        r"|根据.*"
        r"|.*确认表"
        r"|.*确认单"
        r"|.*汇报"
        r"|建立.*"
        r"|蓝图设计"
        r"|企业概况"
        r"|业务蓝图"
        r"|.*目标和价值"
        r"|.*业务流程$"
        r"|.*范围"
        r"|.*要求$"
        r"|.*管理$"
        r"|.*原则$"
        r"|.*规范$"
        r"|.*标准$"
        r"|.*说明$"
        r")"
    )
    sources_by_term: dict[str, dict[str, Any]] = {}  # type: ignore[unused-ignore]  # noqa: ANY_OK
    for feat in features_list:
        if str(feat.get("source_type", "")) != "customer-requirements":
            continue
        term = str(feat.get("normalized_term", ""))
        if not term or term in by_id or len(term) < 4 or noise.match(term):
            continue
        depth = int(str(feat.get("depth", 99)))
        if depth > 3:
            continue
        source_file = str(feat.get("source_file", ""))
        client = source_file.split("/")[2] if "/" in source_file else source_file
        entry = sources_by_term.setdefault(term, {"clients": [], "depth": depth})
        entry["clients"].append(client)
        if depth < entry["depth"]:
            entry["depth"] = depth

    sorted_terms = sorted(sources_by_term.items(), key=lambda kv: (kv[1]["depth"], -len(set(kv[1]["clients"]))))
    for term, data in sorted_terms[:80]:
        unique_clients = sorted(set(data["clients"]))
        evidence = tuple(
            EvidenceRef(kind="doc", ref=f"customer:{c}") for c in unique_clients
        )
        by_id[term] = ReconciledCapability(
            id=term,
            name=term,
            code_status=CapabilityStatus.MISSING.value,
            doc_status=CapabilityStatus.EXISTING.value,
            reconciled_status=CapabilityStatus.MISSING.value,
            confidence=Confidence.LOW.value,
            gaps=(f"客户提出但代码无对应能力 ({len(unique_clients)} 个客户: {', '.join(unique_clients[:3])})",),
            evidence=evidence,
        )


def to_json(result: ReconcileResult) -> dict[str, object]:
    return {
        "project": result.project,
        "capabilities": [
            {
                "id": cap.id,
                "name": cap.name,
                "code_status": cap.code_status,
                "doc_status": cap.doc_status,
                "reconciled_status": cap.reconciled_status,
                "confidence": cap.confidence,
                "gaps": list(cap.gaps),
                "evidence": [{"kind": e.kind, "ref": e.ref} for e in cap.evidence],
            }
            for cap in result.capabilities
        ],
        "requirements": [
            {
                "source_file": r.source_file,
                "source_type": r.source_type,
                "source_customer": r.source_customer,
                "scenario": r.scenario,
                "sub_scenario": r.sub_scenario,
                "function": r.function,
                "nearby_text": r.nearby_text,
                "normalized_term": r.normalized_term,
                "matched_capability": r.matched_capability,
                "code_status": r.code_status,
                "priority": r.priority,
            }
            for r in result.requirements
        ],
    }


def _load_json(path: str) -> Mapping[str, object]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        return {}
    return data


_VALUE_KEYWORDS = ("效率", "降低", "提升", "减少", "提高", "自动", "优化", "避免", "防止", "加快", "简化")


def _calculate_priority(customer_count: int, code_status: str, nearby_text: str) -> str:
    """Rule 3B: auto-suggest priority based on customer count, code status, value keywords.
    'unmatched' (can't match term) scores lower than 'missing' (confirmed absent)."""
    score = min(customer_count, 3)
    if code_status == "missing":
        score += 2
    elif code_status in ("partial", "unmatched"):
        score += 1
    if any(kw in nearby_text for kw in _VALUE_KEYWORDS):
        score += 1
    if score >= 4:
        return "高"
    if score >= 2:
        return "中"
    return "低"


def _build_requirement_records(
    doc_map: Mapping[str, object],
    by_id: dict[str, ReconciledCapability],
) -> tuple[RequirementRecord, ...]:
    """Build RequirementRecords from doc_map requirements, matched against capabilities."""
    raw_reqs = doc_map.get("requirements", [])
    if not raw_reqs and isinstance(doc_map.get("features"), list):
        raw_reqs = doc_map["features"]
    if not isinstance(raw_reqs, list):
        return ()

    term_customers: dict[str, set[str]] = {}
    for feat in raw_reqs:
        if not isinstance(feat, Mapping):
            continue
        term = str(feat.get("normalized_term", ""))
        customer = str(feat.get("source_customer", ""))
        if term and customer:
            term_customers.setdefault(term, set()).add(customer)

    records: list[RequirementRecord] = []
    for feat in raw_reqs:
        if not isinstance(feat, Mapping):
            continue
        term = str(feat.get("normalized_term", ""))
        if not term:
            continue
        matched = by_id.get(term)
        matched_cap = matched.id if matched else ""
        code_status = matched.reconciled_status if matched else "unmatched"
        customers = term_customers.get(term, set())
        nearby = str(feat.get("nearby_text", ""))
        priority = _calculate_priority(len(customers), code_status, nearby)
        records.append(RequirementRecord(
            source_file=str(feat.get("source_file", "")),
            source_type=str(feat.get("source_type", "")),
            source_customer=str(feat.get("source_customer", "")),
            scenario=str(feat.get("scenario", "未分类")),
            sub_scenario=str(feat.get("sub_scenario", "")),
            function=str(feat.get("function", feat.get("heading", ""))),
            nearby_text=nearby,
            normalized_term=term,
            matched_capability=matched_cap,
            code_status=code_status,
            priority=priority,
        ))
    return tuple(records)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile code-map and doc-map into unified capability view.")
    parser.add_argument("--code-map", required=True)
    parser.add_argument("--doc-map", required=True)
    parser.add_argument("--output", default="-")
    args = parser.parse_args()

    result = reconcile(_load_json(args.code_map), _load_json(args.doc_map))
    payload = json.dumps(to_json(result), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
