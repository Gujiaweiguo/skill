"""Incremental ontology delta fixtures (tasks 2.5 / 2.6 / 2.8 / 3.7).

Deltas against a named baseline classify add / modify / deprecate / relate
operations explicitly (2.5); customer, competitor, code, and OPC inputs stay
distinct and no input alone forces canonical inclusion (2.6); reject / defer /
approve transitions keep unapproved content out of canonical versions (2.8);
and an approved promotion marks affected PRD records for comparison without
rewriting them (3.7).
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
    schema = _schema(CONTRACTS / "ontology-change-set.schema.json")
    validator = Draft202012Validator(schema, registry=_REGISTRY)
    return [error.message for error in validator.iter_errors(value)]


def _delta_base(changes: list[dict[str, JsonValue]], inputs: list[dict[str, JsonValue]]) -> dict[str, JsonValue]:
    return {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKCRE-DELTA-001",
        "product_id": "lnkcre",
        "ontology_profile": "business-ontology",
        "change_mode": "incremental",
        "origin_flow": "forward-governance",
        "ontology_impact": {"result": "changed", "rationale": "New customer and code inputs alter membership semantics", "baseline_ref": "30-products/lnkcre/ontology/1.0.0"},
        "baseline": {"status": "identified", "version": "1.0.0", "authority_ref": "30-products/lnkcre/ontology/README.md"},
        "inputs": inputs,
        "changes": changes,
        "review": {"status": "draft"},
    }


def test_incremental_delta_expresses_all_four_operations_against_named_baseline() -> None:
    inputs: list[dict[str, JsonValue]] = [
        {
            "source_id": "REQ-CRE-101",
            "source_type": "customer_requirement",
            "source_ref": "incoming/lnkcre/多经点位诉求.md",
            "evidence_state": "observed",
        },
        {
            "source_id": "CODE-CRE-101",
            "source_type": "code_fact",
            "source_ref": "/opt/code/lnkcre@4444444/src/contract.py",
            "revision": "4444444",
            "evidence_state": "observed",
        },
    ]
    changes: list[dict[str, JsonValue]] = [
        {
            "change_id": "ADD-AD-SPACE",
            "operation": "add",
            "concept_ref": "ad-space",
            "proposed_content": {"name": "Ad Space", "attributes": ["position", "billing_mode"]},
            "rationale": "Customer requests multi-use positioning",
            "source_ids": ["REQ-CRE-101"],
        },
        {
            "change_id": "MODIFY-CONTRACT-STATUS",
            "operation": "modify",
            "concept_ref": "contract-status",
            "proposed_content": {"name": "Contract Status", "states": ["draft", "active", "expiring", "terminated"]},
            "rationale": "Code shows an expiring state absent from baseline",
            "source_ids": ["CODE-CRE-101"],
            "compatibility_notes": "Adds one state; existing consumers of terminated unaffected",
            "impact_refs": ["PRD-CRE-014"],
        },
        {
            "change_id": "DEPRECATE-PAPER-ARCHIVE",
            "operation": "deprecate",
            "concept_ref": "paper-archive",
            "proposed_content": {"name": "Paper Archive", "deprecated": True, "successor": "e-archive"},
            "rationale": "Superseded by electronic archiving",
            "source_ids": ["CODE-CRE-101"],
            "compatibility_notes": "Read-only consumers keep working until removal release",
        },
        {
            "change_id": "RELATE-ADSPACE-CONTRACT",
            "operation": "relate",
            "concept_ref": "ad-space",
            "proposed_content": {"relation": "billed-under", "target": "contract", "cardinality": "n:1"},
            "rationale": "Ad-space billing attaches to the lease contract",
            "source_ids": ["REQ-CRE-101", "CODE-CRE-101"],
        },
    ]
    record = _delta_base(changes, inputs)
    assert _validate(record) == []
    operations = [str(change["operation"]) for change in changes]
    assert operations == ["add", "modify", "deprecate", "relate"]
    assert record["baseline"] == {
        "status": "identified",
        "version": "1.0.0",
        "authority_ref": "30-products/lnkcre/ontology/README.md",
    }


def test_input_classes_stay_distinct_and_none_alone_forces_canonical_inclusion() -> None:
    inputs: list[dict[str, JsonValue]] = [
        {
            "source_id": "REQ-CRE-102",
            "source_type": "customer_requirement",
            "source_ref": "incoming/lnkcre/车位月保诉求.md",
            "evidence_state": "observed",
        },
        {
            "source_id": "EV-HD-021",
            "source_type": "competitor_observation",
            "source_ref": "30-products/lnkcre/evidence/competitors/haiding/evidence-ledger.json#EV-HD-021",
            "evidence_id": "EV-HD-021",
            "capability_id": "CAP-HD-MONTHLY-PARKING",
            "evidence_state": "observed",
        },
        {
            "source_id": "DEC-CRE-102",
            "source_type": "product_decision",
            "source_ref": "30-products/lnkcre/prd/decisions/DEC-CRE-102.md",
            "evidence_state": "inferred",
            "decision": {
                "decision_id": "DEC-CRE-102",
                "owner": "OPC",
                "status": "proposed",
                "rationale": "Monthly parking fits the commercial-property member scenario",
            },
        },
    ]
    changes: list[dict[str, JsonValue]] = [
        {
            "change_id": "ADD-MONTHLY-PARKING",
            "operation": "add",
            "concept_ref": "monthly-parking",
            "proposed_content": {"name": "Monthly Parking", "attributes": ["stall", "fee_cycle"]},
            "rationale": "Customer request + competitor capability; candidate for review, competitor presence is not a mandate",
            "source_ids": ["REQ-CRE-102", "EV-HD-021"],
        },
        {
            "change_id": "ADD-PARKING-ENTITLEMENT",
            "operation": "add",
            "concept_ref": "parking-entitlement",
            "proposed_content": {"name": "Parking Entitlement", "attributes": ["member_tier", "hours"]},
            "rationale": "OPC product judgment recorded as decision, kept separate from observations",
            "source_ids": ["DEC-CRE-102"],
        },
    ]
    record = _delta_base(changes, inputs)
    assert _validate(record) == []
    # Classification: customer/competitor inputs carry no decision block;
    # the OPC idea is product judgment (decision block), never external evidence.
    by_class = {str(i["source_id"]): i for i in inputs}
    assert "decision" not in by_class["REQ-CRE-102"]
    assert "decision" not in by_class["EV-HD-021"]
    assert isinstance(by_class["DEC-CRE-102"].get("decision"), dict)
    # No input alone promotes anything: still a draft, still version-less.
    assert record["review"] == {"status": "draft"}
    assert "proposed_release" not in record


def test_reject_defer_approve_transitions_keep_unapproved_content_out() -> None:
    inputs: list[dict[str, JsonValue]] = [
        {
            "source_id": "REQ-CRE-103",
            "source_type": "customer_requirement",
            "source_ref": "incoming/lnkcre/电子发票诉求.md",
            "evidence_state": "observed",
        },
    ]
    changes: list[dict[str, JsonValue]] = [
        {
            "change_id": "ADD-E-INVOICE",
            "operation": "add",
            "concept_ref": "e-invoice",
            "proposed_content": {"name": "E-Invoice", "attributes": ["issuer", "tax_code"]},
            "rationale": "Customer request",
            "source_ids": ["REQ-CRE-103"],
        },
    ]

    rejected = _delta_base(changes, inputs)
    rejected["review"] = {
        "status": "rejected",
        "owner": "OPC",
        "rationale": "Out of scope for this product increment",
        "reviewed_at": "2026-10-02T01:00:00Z",
    }
    assert _validate(rejected) == []
    assert "proposed_release" not in rejected

    deferred = _delta_base(changes, inputs)
    deferred["review"] = {
        "status": "deferred",
        "owner": "OPC",
        "rationale": "Waiting for finance-system integration decision",
        "reviewed_at": "2026-10-02T01:05:00Z",
    }
    assert _validate(deferred) == []
    assert "proposed_release" not in deferred

    approved = _delta_base(changes, inputs)
    approved["review"] = {
        "status": "accepted",
        "owner": "OPC",
        "decision_ref": "DEC-CRE-103",
        "reviewed_at": "2026-10-02T01:10:00Z",
    }
    approved["proposed_release"] = {"version": "1.1.0", "source_revision": "b" * 40, "release_id": "SEM-CRE-011"}
    assert _validate(approved) == []
    # New version links to the parent baseline it supersedes.
    assert approved["baseline"] == {
        "status": "identified",
        "version": "1.0.0",
        "authority_ref": "30-products/lnkcre/ontology/README.md",
    }
    release = cast(dict[str, JsonValue], approved["proposed_release"])
    assert release["version"] == "1.1.0"

    # Acceptance without a versioned release must not validate.
    accepted_without_release = _delta_base(changes, inputs)
    accepted_without_release["review"] = {
        "status": "accepted", "owner": "OPC", "decision_ref": "DEC-CRE-103",
        "reviewed_at": "2026-10-02T01:15:00Z",
    }
    assert _validate(accepted_without_release)


def test_approved_promotion_marks_prd_records_for_comparison_without_rewriting() -> None:
    inputs: list[dict[str, JsonValue]] = [
        {
            "source_id": "CODE-CRE-104",
            "source_type": "code_fact",
            "source_ref": "/opt/code/lnkcre@5555555/src/merchant.py",
            "revision": "5555555",
            "evidence_state": "observed",
        },
    ]
    changes: list[dict[str, JsonValue]] = [
        {
            "change_id": "MODIFY-MERCHANT-GRADE",
            "operation": "modify",
            "concept_ref": "merchant-grade",
            "proposed_content": {"name": "Merchant Grade", "attributes": ["grade_code", "review_cycle"]},
            "rationale": "Code adds a review cycle to grades at the recorded revision",
            "source_ids": ["CODE-CRE-104"],
            "impact_refs": ["PRD-CRE-020", "PRD-CRE-021"],
        },
    ]
    approved = _delta_base(changes, inputs)
    approved["review"] = {
        "status": "accepted",
        "owner": "OPC",
        "decision_ref": "DEC-CRE-104",
        "reviewed_at": "2026-10-02T02:00:00Z",
    }
    approved["proposed_release"] = {"version": "1.1.0", "source_revision": "c" * 40}
    assert _validate(approved) == []

    # Impact is expressed as references for comparison — the promotion itself
    # carries no PRD content and rewrites nothing.
    affected = cast(list[str], changes[0]["impact_refs"])
    assert affected == ["PRD-CRE-020", "PRD-CRE-021"]
    promoted_fields = set(approved)
    assert "prd_updates" not in promoted_fields
    assert "prd_baseline" not in promoted_fields
