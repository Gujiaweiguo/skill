# ─── How to run ───
#   cd skills/business/product-prd-generator
#   uv run scripts/reconcile_capabilities.py \
#     --code-map parsed/current-code-map.json \
#     --doc-map parsed/current-doc-map.json \
#     --output parsed/capability-reconciliation.json

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import Enum, unique
from pathlib import Path
from typing import Any


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


_STATUS_RANK = {
    CapabilityStatus.EXPLICITLY_NOT_DO: 0,
    CapabilityStatus.EXISTING: 1,
    CapabilityStatus.PARTIAL: 2,
    CapabilityStatus.MISSING: 3,
}


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

    dominant = doc_status if _STATUS_RANK[doc_status] < _STATUS_RANK[code_status] else code_status
    return dominant, Confidence.MEDIUM, tuple(gaps)


def reconcile(code_map: dict[str, Any], doc_map: dict[str, Any]) -> ReconcileResult:  # noqa: ANY_OK
    project = code_map.get("project", doc_map.get("project", "商管系统"))
    by_id: dict[str, ReconciledCapability] = {}

    for cap in code_map.get("spec_capabilities", []):
        cap_id = cap.get("id", "")
        code_status = _coerce_status(cap.get("status", CapabilityStatus.MISSING.value))
        doc_status = CapabilityStatus.MISSING
        gaps = [f"spec has no doc evidence yet"]
        evidence = tuple(EvidenceRef(kind=e["kind"], ref=e["ref"]) for e in cap.get("evidence", []))
        reconciled, confidence, pair_gaps = _reconcile_pair(code_status, doc_status)
        all_gaps = gaps + list(pair_gaps)
        by_id[cap_id] = ReconciledCapability(
            id=cap_id,
            name=cap.get("name", cap_id),
            code_status=code_status.value,
            doc_status=doc_status.value,
            reconciled_status=reconciled.value,
            confidence=confidence.value,
            gaps=tuple(all_gaps),
            evidence=evidence,
        )

    for cap in code_map.get("matrix_rows", []):
        cap_id = cap.get("id", "")
        code_status = _coerce_status(cap.get("mi_status", CapabilityStatus.MISSING.value))
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
            gaps = ["matrix row without matching spec id"]
            reconciled, confidence, pair_gaps = _reconcile_pair(code_status, CapabilityStatus.MISSING)
            by_id[cap_id] = ReconciledCapability(
                id=cap_id,
                name=cap.get("function_point", cap_id),
                code_status=code_status.value,
                doc_status=CapabilityStatus.MISSING.value,
                reconciled_status=reconciled.value,
                confidence=confidence.value,
                gaps=tuple(gaps + list(pair_gaps)),
                evidence=(),
            )

    for feat in doc_map.get("features", []):
        term = feat.get("normalized_term", "")
        if term in by_id:
            existing = by_id[term]
            doc_status = CapabilityStatus.EXISTING
            reconciled, confidence, pair_gaps = _reconcile_pair(_coerce_status(existing.code_status), doc_status)
            evidence = existing.evidence + tuple(EvidenceRef(kind=e["kind"], ref=e["ref"]) for e in feat.get("evidence", []))
            by_id[term] = ReconciledCapability(
                id=term,
                name=existing.name,
                code_status=existing.code_status,
                doc_status=doc_status.value,
                reconciled_status=reconciled.value,
                confidence=confidence.value,
                gaps=existing.gaps + pair_gaps,
                evidence=evidence,
            )

    return ReconcileResult(project=project, capabilities=tuple(by_id.values()))


def _to_dict(result: ReconcileResult) -> dict[str, object]:
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
    }


def _load_json(path: str) -> dict[str, Any]:  # noqa: ANY_OK
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile code-map and doc-map into unified capability view.")
    parser.add_argument("--code-map", required=True)
    parser.add_argument("--doc-map", required=True)
    parser.add_argument("--output", default="-")
    args = parser.parse_args()

    code_map = _load_json(args.code_map)
    doc_map = _load_json(args.doc_map)
    result = reconcile(code_map, doc_map)
    payload = json.dumps(_to_dict(result), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
