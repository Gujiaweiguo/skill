"""PRD provenance fixtures against prd-handoff.schema.json (tasks 2.9 / 3.2 / 3.3 / 3.5 / 5.4).

Semantic-release consumer gating (2.9), full-baseline input disclosure (3.2),
incremental deltas against a prior baseline (3.3), and competitor evidence
chains that stay observations until an owner decision approves them (3.5/5.4).
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


def _validate(value: Mapping[str, JsonValue]) -> list[str]:
    schema = _schema(ROOT / "references" / "prd-handoff.schema.json")
    validator = Draft202012Validator(schema, registry=_REGISTRY)
    return [error.message for error in validator.iter_errors(value)]


def _handoff_base(product: str, product_class: str, profile: str) -> dict[str, JsonValue]:
    return {
        "trace_id": "PRD-CRE-100",
        "product_id": product,
        "product_class": product_class,
        "ontology_profile": profile,
        "ontology_baseline": {
            "product_id": product, "product_class": product_class, "ontology_profile": profile,
            "layer": "ontology", "status": "resolved",
            "authority_ref": f"30-products/{product}/ontology/README.md",
        },
        "prd_baseline": {
            "product_id": product, "product_class": product_class, "ontology_profile": profile,
            "layer": "prd", "status": "resolved",
            "authority_ref": f"30-products/{product}/prd/baseline/",
        },
        "target_repo": f"/opt/code/{product}",
        "source_refs": ["REQ-CRE-100"],
        "evidence_state": "inferred",
        "implementation_status": "missing",
    }


def test_accepted_semantic_release_is_the_consumable_ontology_basis() -> None:
    value = _handoff_base("lnkcre", "business", "business-ontology")
    ontology_baseline = cast(dict[str, JsonValue], value["ontology_baseline"])
    ontology_baseline.update({
        "version": "1.0.0",
        "revision": "a" * 40,
        "release_id": "SEM-CRE-010",
    })
    value["sources"] = [{
        "source_id": "REQ-CRE-100",
        "source_type": "customer_requirement",
        "source_ref": "incoming/lnkcre/诉求.md",
        "evidence_state": "observed",
    }]
    assert _validate(value) == []
    assert ontology_baseline["release_id"] == "SEM-CRE-010"


def test_unaccepted_ontology_model_is_labeled_not_released() -> None:
    value = _handoff_base("lnkchatbi", "tool", "tool-ontology")
    ontology_baseline = cast(dict[str, JsonValue], value["ontology_baseline"])
    ontology_baseline["authority_ref"] = "30-products/lnkchatbi/ontology/ontology.yaml"
    ontology_baseline["reason"] = "canonical 仍 proposed（owner 未确认）；planning use only, not a released runtime contract"
    value["sources"] = [{
        "source_id": "REQ-LCHBI-100",
        "source_type": "customer_requirement",
        "source_ref": "incoming/lnkchatbi/诉求.md",
        "evidence_state": "observed",
    }]
    assert _validate(value) == []
    # Draft basis: no release_id, no version — structurally not a released slice.
    assert "release_id" not in ontology_baseline
    assert "version" not in ontology_baseline
    assert "proposed" in str(ontology_baseline["reason"])


def test_full_prd_baseline_discloses_available_and_absent_input_classes() -> None:
    value = _handoff_base("lnkcre", "business", "business-ontology")
    ontology_baseline = cast(dict[str, JsonValue], value["ontology_baseline"])
    ontology_baseline.update({"version": "1.0.0", "release_id": "SEM-CRE-010"})
    value["source_refs"] = ["REQ-CRE-100", "EV-QM-020", "CODE-CRE-100", "DEC-CRE-100", "SRC-COMPETITOR-N/A"]
    value["sources"] = [
        {
            "source_id": "REQ-CRE-100", "source_type": "customer_requirement",
            "source_ref": "incoming/lnkcre/诉求.md", "evidence_state": "observed",
        },
        {
            "source_id": "EV-QM-020", "source_type": "competitor_observation",
            "source_ref": "30-products/lnkcre/evidence/competitors/qimao/evidence-ledger.json#EV-QM-020",
            "evidence_id": "EV-QM-020", "capability_id": "CAP-QM-BATCH-RENT",
            "evidence_state": "observed",
        },
        {
            "source_id": "CODE-CRE-100", "source_type": "code_fact",
            "source_ref": "/opt/code/lnkcre@6666666/src/rent.py", "revision": "6666666",
            "evidence_state": "observed",
        },
        {
            "source_id": "DEC-CRE-100", "source_type": "product_decision",
            "source_ref": "30-products/lnkcre/prd/decisions/DEC-CRE-100.md",
            "evidence_state": "inferred",
            "decision": {
                "decision_id": "DEC-CRE-100", "owner": "OPC", "status": "accepted",
                "rationale": "Batch rent adjustment is in product direction",
                "supporting_source_ids": ["REQ-CRE-100", "EV-QM-020"],
            },
        },
        {
            # Absent class disclosed, not silently omitted.
            "source_id": "SRC-COMPETITOR-N/A", "source_type": "competitor_observation",
            "source_ref": "incoming/lnkcre/competitor-evidence", "evidence_state": "not_applicable",
        },
    ]
    value["decision"] = {
        "decision_id": "DEC-CRE-100", "owner": "OPC", "status": "accepted",
        "rationale": "Batch rent adjustment is in product direction",
        "supporting_source_ids": ["REQ-CRE-100", "EV-QM-020"],
    }
    value["source_type"] = "product_decision"
    assert _validate(value) == []
    classes = {str(s["source_type"]) for s in cast(list[dict[str, JsonValue]], value["sources"])}
    assert classes == {
        "customer_requirement", "competitor_observation", "code_fact",
        "product_decision",  # present classes
    } | {"competitor_observation"}  # absent-class marker reuses the class with not_applicable
    states = {str(s["source_id"]): str(s["evidence_state"]) for s in cast(list[dict[str, JsonValue]], value["sources"])}
    assert states["SRC-COMPETITOR-N/A"] == "not_applicable"


def test_incremental_prd_identifies_prior_baseline_and_changed_sources() -> None:
    value = _handoff_base("lnkcre", "business", "business-ontology")
    value["trace_id"] = "PRD-CRE-101"
    ontology_baseline = cast(dict[str, JsonValue], value["ontology_baseline"])
    ontology_baseline.update({"version": "1.0.0", "release_id": "SEM-CRE-010"})
    prd_baseline = cast(dict[str, JsonValue], value["prd_baseline"])
    prd_baseline["version"] = "1.0"  # prior baseline this delta is against
    value["source_refs"] = ["REQ-CRE-101"]
    value["sources"] = [
        {
            "source_id": "REQ-CRE-101", "source_type": "customer_requirement",
            "source_ref": "incoming/lnkcre/新诉求.md", "evidence_state": "observed",
            "trace_id": "PRD-CRE-101",
        },
    ]
    assert _validate(value) == []
    assert prd_baseline["version"] == "1.0"
    assert ontology_baseline["release_id"] == "SEM-CRE-010"
    changed = cast(list[dict[str, JsonValue]], value["sources"])
    assert changed[0]["trace_id"] == "PRD-CRE-101"


def test_competitor_evidence_chain_survives_until_decision_and_no_further() -> None:
    # Candidate: competitor observation alone — no decision, not approved.
    candidate = _handoff_base("lnkcre", "business", "business-ontology")
    candidate["trace_id"] = "PRD-CRE-102"
    candidate["source_type"] = "competitor"
    candidate["capability_id"] = "CAP-QM-POINTS-EXPIRY"
    candidate["source_refs"] = ["EV-QM-014"]
    candidate["sources"] = [{
        "source_id": "EV-QM-014", "source_type": "competitor_observation",
        "source_ref": "30-products/lnkcre/evidence/competitors/qimao/evidence-ledger.json#EV-QM-014",
        "evidence_id": "EV-QM-014", "capability_id": "CAP-QM-POINTS-EXPIRY",
        "evidence_state": "observed",
    }]
    candidate["evidence_state"] = "observed"
    assert _validate(candidate) == []
    assert "decision" not in candidate

    # Approved: same capability, now carrying an OPC decision that cites the evidence.
    approved = {
        **candidate,
        "trace_id": "PRD-CRE-102",
        "decision": {
            "decision_id": "DEC-CRE-102", "owner": "OPC", "status": "accepted",
            "rationale": "Points expiry fits member operations",
            "supporting_source_ids": ["EV-QM-014"],
        },
    }
    assert _validate(approved) == []
    decision = cast(dict[str, JsonValue], approved["decision"])
    assert decision["supporting_source_ids"] == ["EV-QM-014"]
    # 5.4: capability and evidence identities preserved in both records.
    for record in (candidate, approved):
        assert record["capability_id"] == "CAP-QM-POINTS-EXPIRY"
        sources = cast(list[dict[str, JsonValue]], record["sources"])
        assert sources[0]["evidence_id"] == "EV-QM-014"
