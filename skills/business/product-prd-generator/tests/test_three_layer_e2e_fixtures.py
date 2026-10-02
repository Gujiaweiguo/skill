"""Three-layer end-to-end fixtures (tasks 4.5 / 4.6 / 6.1 / 7.6).

Pairwise reconciliation samples for one business and one tool product (4.5),
post-promotion comparisons against affected PRD/code revisions (4.6), a full
forward chain from PRD inputs through release state, reconciliations, and
reviewed writeback for both profiles (6.1), and forward/reverse end-to-end
scenarios with trace continuity and no automatic canonical promotion (7.6).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final, TypeAlias, cast

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012, Schema

ROOT: Final = Path(__file__).resolve().parents[1]
CONTRACTS: Final = ROOT / "references" / "product-governance"

JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)


def _json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _schema(path: Path) -> Schema:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    parsed = _json_value(raw)
    if not isinstance(parsed, dict):
        raise TypeError(f"{path.name} must contain a JSON schema object")
    return parsed


def _build_registry() -> Registry[Schema]:
    registry: Registry[Schema] = Registry()
    for schema_path in sorted(CONTRACTS.glob("*.schema.json")):
        resource = Resource.from_contents(
            _schema(schema_path), default_specification=DRAFT202012
        )
        schema_id = resource.id()
        if schema_id is not None:
            registry = registry.with_resource(schema_id, resource)
    return registry


_REGISTRY: Final = _build_registry()


def _validate(schema_name: str, value: Mapping[str, JsonValue]) -> list[str]:
    path = CONTRACTS / schema_name
    if schema_name == "prd-handoff.schema.json":
        path = ROOT / "references" / "prd-handoff.schema.json"
    validator = Draft202012Validator(_schema(path), registry=_REGISTRY)
    return [error.message for error in validator.iter_errors(value)]


def _layer(product_id: str, product_class: str, profile: str, layer: str, **extra: str) -> dict[str, JsonValue]:
    value: dict[str, JsonValue] = {
        "product_id": product_id,
        "product_class": product_class,
        "ontology_profile": profile,
        "layer": layer,
        "status": "resolved",
        "authority_ref": f"30-products/{product_id}/{'ontology/README.md' if layer == 'ontology' else 'prd/' if layer == 'prd' else ''}",
    }
    if layer == "code":
        value["authority_ref"] = f"/opt/code/{product_id}"
    value.update({k: v for k, v in extra.items()})
    return value


def _reconciliation(
    reconciliation_id: str,
    product_id: str,
    product_class: str,
    profile: str,
    pair: str,
    left: dict[str, JsonValue],
    right: dict[str, JsonValue],
    coverage: dict[str, JsonValue],
    outcome: str,
    findings: list[dict[str, JsonValue]],
) -> dict[str, JsonValue]:
    return {
        "schema_version": "1.0",
        "reconciliation_id": reconciliation_id,
        "product_id": product_id,
        "pair": pair,
        "left": left,
        "right": right,
        "coverage": coverage,
        "outcome": outcome,
        "findings": findings,
    }


_FULL_COVERAGE: Final[dict[str, JsonValue]] = {"status": "complete", "scope": ["named scopes"], "limitations": []}
_NOT_SCANNED: Final[dict[str, JsonValue]] = {"status": "not-scanned", "scope": [], "limitations": ["scanner not run for this pair"]}


def test_business_and_tool_products_produce_three_pairwise_results() -> None:
    business = [
        _reconciliation(
            "REC-CRE-FULL-01", "lnkcre", "business", "business-ontology", "ontology-prd",
            _layer("lnkcre", "business", "business-ontology", "ontology", version="1.0.0"),
            _layer("lnkcre", "business", "business-ontology", "prd", version="1.0"),
            _FULL_COVERAGE, "aligned", [],
        ),
        _reconciliation(
            "REC-CRE-FULL-02", "lnkcre", "business", "business-ontology", "prd-code",
            _layer("lnkcre", "business", "business-ontology", "prd", version="1.0"),
            _layer("lnkcre", "business", "business-ontology", "code", revision="6666666"),
            _FULL_COVERAGE, "drifted",
            [{
                "finding_id": "FND-CRE-01",
                "summary": "PRD batch-rent item not implemented",
                "source_ids": ["PRD-CRE-100"],
                "trace_ids": ["PRD-CRE-100"],
                "disposition": "implementation",
            }],
        ),
        _reconciliation(
            "REC-CRE-FULL-03", "lnkcre", "business", "business-ontology", "ontology-code",
            _layer("lnkcre", "business", "business-ontology", "ontology", version="1.0.0"),
            _layer("lnkcre", "business", "business-ontology", "code", revision="6666666"),
            _FULL_COVERAGE, "aligned", [],
        ),
    ]
    tool = [
        _reconciliation(
            "REC-RPT-FULL-01", "lnkreport", "tool", "tool-ontology", "ontology-prd",
            _layer("lnkreport", "tool", "tool-ontology", "ontology", version="1.0"),
            _layer("lnkreport", "tool", "tool-ontology", "prd", version="1.0"),
            _FULL_COVERAGE, "aligned", [],
        ),
        _reconciliation(
            "REC-RPT-FULL-02", "lnkreport", "tool", "tool-ontology", "prd-code",
            _layer("lnkreport", "tool", "tool-ontology", "prd", version="1.0"),
            _layer("lnkreport", "tool", "tool-ontology", "code", revision="2222222"),
            _FULL_COVERAGE, "aligned", [],
        ),
        # Explicit unavailable state: pair not scanned, not asserted missing.
        _reconciliation(
            "REC-RPT-FULL-03", "lnkreport", "tool", "tool-ontology", "ontology-code",
            _layer("lnkreport", "tool", "tool-ontology", "ontology", version="1.0"),
            _layer("lnkreport", "tool", "tool-ontology", "code", revision="2222222"),
            _NOT_SCANNED, "not-scanned", [],
        ),
    ]
    for record in business + tool:
        assert _validate("reconciliation-record.schema.json", record) == []
    assert {r["pair"] for r in business} == {"ontology-prd", "prd-code", "ontology-code"}
    assert {r["pair"] for r in tool} == {"ontology-prd", "prd-code", "ontology-code"}
    assert tool[2]["outcome"] == "not-scanned"
    assert not tool[2]["findings"]


def test_post_promotion_compares_new_version_against_affected_layers() -> None:
    promoted_ontology = _layer("lnkcre", "business", "business-ontology", "ontology", version="1.1.0", release_id="SEM-CRE-011")
    prd = _layer("lnkcre", "business", "business-ontology", "prd", version="1.0")
    code = _layer("lnkcre", "business", "business-ontology", "code", revision="7777777")

    onto_prd = _reconciliation(
        "REC-CRE-PROMO-01", "lnkcre", "business", "business-ontology", "ontology-prd",
        promoted_ontology, prd, _FULL_COVERAGE, "drifted",
        [{
            "finding_id": "FND-PROMO-01",
            "summary": "merchant-grade review cycle needs a PRD update decision",
            "source_ids": ["CODE-CRE-104"],
            "trace_ids": ["PRD-CRE-020", "PRD-CRE-021"],
            "disposition": "product-decision",
            "owner": "OPC",
        }],
    )
    onto_code = _reconciliation(
        "REC-CRE-PROMO-02", "lnkcre", "business", "business-ontology", "ontology-code",
        promoted_ontology, code, _FULL_COVERAGE, "drifted",
        [{
            "finding_id": "FND-PROMO-02",
            "summary": "ad-space relation not yet observed in code",
            "source_ids": ["REQ-CRE-101"],
            "trace_ids": ["PRD-CRE-014"],
            "disposition": "implementation",
        }],
    )
    prd_code = _reconciliation(
        "REC-CRE-PROMO-03", "lnkcre", "business", "business-ontology", "prd-code",
        prd, code, _FULL_COVERAGE, "aligned", [],
    )
    for record in (onto_prd, onto_code, prd_code):
        assert _validate("reconciliation-record.schema.json", record) == []
    # Independent findings per affected pair, routed to distinct owners.
    assert cast(dict[str, JsonValue], onto_prd["findings"][0])["disposition"] == "product-decision"
    assert cast(dict[str, JsonValue], onto_code["findings"][0])["disposition"] == "implementation"


def _forward_chain(product_id: str, product_class: str, profile: str, code_revision: str) -> dict[str, JsonValue]:
    """Full forward chain: PRD baseline + delta + accepted release + 3 pairs + reviewed return."""
    release_id = f"SEM-{product_id.upper()}-010"
    baseline_handoff: dict[str, JsonValue] = {
        "trace_id": f"PRD-{product_id.upper()}-100",
        "product_id": product_id, "product_class": product_class, "ontology_profile": profile,
        "ontology_baseline": _layer(product_id, product_class, profile, "ontology", version="1.0.0", release_id=release_id),
        "prd_baseline": _layer(product_id, product_class, profile, "prd", version="1.0"),
        "target_repo": f"/opt/code/{product_id}",
        "source_refs": [f"REQ-{product_id.upper()}-100"],
        "sources": [{
            "source_id": f"REQ-{product_id.upper()}-100",
            "source_type": "customer_requirement",
            "source_ref": f"incoming/{product_id}/诉求.md",
            "evidence_state": "observed",
        }],
        "evidence_state": "inferred",
        "implementation_status": "missing",
    }
    delta_handoff: dict[str, JsonValue] = {
        **baseline_handoff,
        "trace_id": f"PRD-{product_id.upper()}-101",
        "source_refs": [f"REQ-{product_id.upper()}-101"],
        "sources": [{
            "source_id": f"REQ-{product_id.upper()}-101",
            "source_type": "customer_requirement",
            "source_ref": f"incoming/{product_id}/新诉求.md",
            "evidence_state": "observed",
            "trace_id": f"PRD-{product_id.upper()}-101",
        }],
    }
    ontology_release: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": f"ONT-{product_id.upper()}-BASE-001",
        "product_id": product_id, "ontology_profile": profile,
        "change_mode": "initial-baseline", "origin_flow": "forward-governance",
        "baseline": {"status": "absent"},
        "inputs": baseline_handoff["sources"],
        "changes": [{
            "change_id": "ADD-CORE-001", "operation": "add", "concept_ref": "core-concept",
            "proposed_content": {"name": "Core Concept"},
            "rationale": "Baseline synthesis from available inputs",
            "source_ids": [f"REQ-{product_id.upper()}-100"],
        }],
        "review": {"status": "accepted", "owner": "OPC", "decision_ref": f"DEC-{product_id.upper()}-001", "reviewed_at": "2026-10-02T00:00:00Z"},
        "proposed_release": {"version": "1.0.0", "source_revision": "d" * 40, "release_id": release_id},
    }
    reconciliations = [
        _reconciliation(
            f"REC-{product_id.upper()}-E2E-0{i}", product_id, product_class, profile, pair,
            _layer(product_id, product_class, profile, left_layer, **({"version": "1.0.0"} if left_layer == "ontology" else {"version": "1.0"})),
            _layer(product_id, product_class, profile, right_layer, **({"revision": code_revision} if right_layer == "code" else {"version": "1.0"})),
            _FULL_COVERAGE, "aligned", [],
        )
        for i, (pair, left_layer, right_layer) in enumerate(
            [("ontology-prd", "ontology", "prd"), ("prd-code", "prd", "code"), ("ontology-code", "ontology", "code")], 1
        )
    ]
    implementation_return: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "return_id": f"RET-{product_id.upper()}-001",
        "product_id": product_id,
        "trace_ids": [f"PRD-{product_id.upper()}-100", f"PRD-{product_id.upper()}-101"],
        "target_repo": f"/opt/code/{product_id}",
        "open_spec_change_id": f"{product_id}-change-1",
        "source_revision": code_revision,
        "verification_refs": [f"verification-{product_id}.md"],
        "review_status": "accepted",
        "review_owner": "OPC",
        "proposed_updates": [],
    }
    return {
        "baseline": baseline_handoff,
        "delta": delta_handoff,
        "release": ontology_release,
        "reconciliations": reconciliations,
        "implementation_return": implementation_return,
    }


def test_end_to_end_traceability_business_and_tool_products() -> None:
    for product_id, product_class, profile, code_revision in (
        ("lnkcre", "business", "business-ontology", "8888888"),
        ("lnkchatbi", "tool", "tool-ontology", "9999999"),
    ):
        chain = _forward_chain(product_id, product_class, profile, code_revision)
        assert _validate("prd-handoff.schema.json", chain["baseline"]) == []
        assert _validate("prd-handoff.schema.json", chain["delta"]) == []
        assert _validate("ontology-change-set.schema.json", chain["release"]) == []
        for record in chain["reconciliations"]:
            assert _validate("reconciliation-record.schema.json", record) == []
        assert _validate("implementation-return.schema.json", chain["implementation_return"]) == []

        # Trace continuity: the accepted return covers both handoff traces.
        ret = cast(dict[str, JsonValue], chain["implementation_return"])
        trace_ids = set(cast(list[str], ret["trace_ids"]))
        assert trace_ids == {chain["baseline"]["trace_id"], chain["delta"]["trace_id"]}
        # Release continuity: handoff ontology basis equals the accepted release.
        release = cast(dict[str, JsonValue], chain["release"]["proposed_release"])
        ontology_basis = cast(dict[str, JsonValue], chain["baseline"]["ontology_baseline"])
        assert ontology_basis["release_id"] == release["release_id"]


def test_forward_no_change_flow_and_reverse_recovery_never_auto_promote() -> None:
    # Forward: reasoned no-change assessment precedes the PRD delta.
    no_change: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKREPORT-NOCHANGE-001",
        "product_id": "lnkreport", "ontology_profile": "tool-ontology",
        "change_mode": "incremental", "origin_flow": "forward-governance",
        "ontology_impact": {
            "result": "no-change",
            "rationale": "Dashboard wording change adds no semantic concept",
            "baseline_ref": "30-products/lnkreport/ontology/1.0.0",
        },
        "baseline": {"status": "identified", "version": "1.0.0", "authority_ref": "30-products/lnkreport/ontology/ontology.yaml"},
        "inputs": [{
            "source_id": "REQ-RPT-101", "source_type": "customer_requirement",
            "source_ref": "incoming/lnkreport/文案调整.md", "evidence_state": "observed",
        }],
        "changes": [],
        "review": {"status": "draft"},
    }
    forward_delta: dict[str, JsonValue] = {
        "trace_id": "PRD-RPT-101",
        "product_id": "lnkreport", "product_class": "tool", "ontology_profile": "tool-ontology",
        "ontology_baseline": _layer("lnkreport", "tool", "tool-ontology", "ontology", version="1.0.0", release_id="SEM-LNKREPORT-010"),
        "prd_baseline": _layer("lnkreport", "tool", "tool-ontology", "prd", version="1.0"),
        "target_repo": "/opt/code/lnkreport",
        "source_refs": ["REQ-RPT-101"],
        "sources": [{
            "source_id": "REQ-RPT-101", "source_type": "customer_requirement",
            "source_ref": "incoming/lnkreport/文案调整.md", "evidence_state": "observed",
            "trace_id": "PRD-RPT-101",
        }],
        "evidence_state": "observed",
        "implementation_status": "missing",
    }
    forward_return: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "return_id": "RET-RPT-FWD-001",
        "product_id": "lnkreport",
        "trace_ids": ["PRD-RPT-101"],
        "target_repo": "/opt/code/lnkreport",
        "open_spec_change_id": "lnkreport-change-9",
        "source_revision": "2222222",
        "verification_refs": ["verification-9.md"],
        "review_status": "accepted",
        "review_owner": "OPC",
        "proposed_updates": [],
    }
    assert _validate("ontology-change-set.schema.json", no_change) == []
    assert _validate("prd-handoff.schema.json", forward_delta) == []
    assert _validate("implementation-return.schema.json", forward_return) == []
    assert cast(dict[str, JsonValue], forward_return)["trace_ids"] == [forward_delta["trace_id"]]

    # Reverse: code scan recovers facts; candidates stay proposals forever
    # until a separate OPC-reviewed ontology promotion.
    reverse_candidate: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKCHATBI-REV-001",
        "product_id": "lnkchatbi", "ontology_profile": "tool-ontology",
        "change_mode": "initial-baseline", "origin_flow": "code-evidence-reverse",
        "scan_coverage": {"status": "partial", "scope": ["src/reports"], "limitations": ["tests not scanned"]},
        "baseline": {"status": "absent"},
        "inputs": [{
            "source_id": "CODE-LCHBI-200", "source_type": "code_fact",
            "source_ref": "/opt/code/lnkchatbi@9999999/src/reports.py",
            "revision": "9999999", "evidence_state": "observed",
        }],
        "changes": [{
            "change_id": "ADD-CHART-TYPE", "operation": "add", "concept_ref": "chart-type",
            "proposed_content": {"name": "Chart Type", "values": ["bar", "line"]},
            "rationale": "Recovered from code at the recorded revision",
            "source_ids": ["CODE-LCHBI-200"],
        }],
        "review": {"status": "draft"},
    }
    reverse_finding = _reconciliation(
        "REC-LCHBI-REV-01", "lnkchatbi", "tool", "tool-ontology", "ontology-code",
        _layer("lnkchatbi", "tool", "tool-ontology", "ontology", version="draft"),
        _layer("lnkchatbi", "tool", "tool-ontology", "code", revision="9999999"),
        {"status": "partial", "scope": ["src/reports"], "limitations": ["tests not scanned"]},
        "drifted",
        [{
            "finding_id": "FND-REV-01",
            "summary": "chart-type concept recovered from code awaits OPC semantic decision",
            "source_ids": ["CODE-LCHBI-200"],
            "disposition": "ontology-review",
            "owner": "OPC",
        }],
    )
    reverse_return: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "return_id": "RET-LCHBI-REV-001",
        "product_id": "lnkchatbi",
        "origin_flow": "code-evidence-reverse",
        "trace_ids": ["CODE-LCHBI-200"],
        "target_repo": "/opt/code/lnkchatbi",
        "open_spec_change_id": "lnkchatbi-change-7",
        "source_revision": "9999999",
        "scan_coverage": {"status": "partial", "scope": ["src/reports"], "limitations": ["tests not scanned"]},
        "verification_refs": ["verification-7.md"],
        "review_status": "accepted",
        "review_owner": "OPC",
        "proposed_updates": [{
            "destination_layer": "ontology",
            "summary": "Candidate chart-type concept from code evidence",
            "status": "proposed",
        }],
    }
    assert _validate("ontology-change-set.schema.json", reverse_candidate) == []
    assert _validate("reconciliation-record.schema.json", reverse_finding) == []
    assert _validate("implementation-return.schema.json", reverse_return) == []
    # No automatic canonical promotion, even after the return is accepted.
    assert reverse_candidate["review"] == {"status": "draft"}
    updates = cast(list[dict[str, JsonValue]], reverse_return["proposed_updates"])
    assert updates[0]["status"] == "proposed"
