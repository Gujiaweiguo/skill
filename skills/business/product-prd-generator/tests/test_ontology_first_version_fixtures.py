"""First-version ontology generation fixtures (tasks 2.1 / 2.3 / 5.7).

Initial-baseline change sets synthesized from customer, competitor, code, and
OPC inputs. Each proposed concept retains per-input provenance (task 2.1);
absent / unverified / conflicting inputs are disclosed, never fabricated
(task 2.3); and every change links back to its contributing source traces with
evidence / inference / judgment kept distinct (task 5.7).
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


def _assert_source_links(record: Mapping[str, JsonValue]) -> None:
    """Task 5.7: every change links to contributing input traces by class."""
    inputs = cast(list[dict[str, JsonValue]], record["inputs"])
    changes = cast(list[dict[str, JsonValue]], record["changes"])
    inputs_by_id = {str(item["source_id"]): item for item in inputs}
    for change in changes:
        source_ids = cast(list[str], change["source_ids"])
        assert source_ids, "change must retain at least one source trace"
        for source_id in source_ids:
            assert source_id in inputs_by_id, f"dangling source {source_id}"
    # Judgment contributions carry a decision block; observations never do.
    for item in inputs:
        if item["source_type"] == "product_decision":
            assert isinstance(item.get("decision"), dict)
        else:
            assert "decision" not in item


def test_business_first_version_synthesizes_all_four_input_classes() -> None:
    record: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKCRM-FIRST-001",
        "product_id": "lnkcrm",
        "ontology_profile": "business-ontology",
        "change_mode": "initial-baseline",
        "origin_flow": "forward-governance",
        "baseline": {"status": "absent"},
        "inputs": [
            {
                "source_id": "REQ-CRM-010",
                "source_type": "customer_requirement",
                "source_ref": "incoming/lnkcrm/会员积分诉求.md",
                "evidence_state": "observed",
            },
            {
                "source_id": "EV-QM-014",
                "source_type": "competitor_observation",
                "source_ref": "30-products/lnkcre/evidence/competitors/qimao/evidence-ledger.json#EV-QM-014",
                "evidence_id": "EV-QM-014",
                "capability_id": "CAP-QM-POINTS-EXPIRY",
                "evidence_state": "observed",
            },
            {
                "source_id": "CODE-CRM-000",
                "source_type": "code_fact",
                "source_ref": "/opt/code/lnkcrm@1111111/src/member.py",
                "revision": "1111111",
                "evidence_state": "observed",
            },
            {
                "source_id": "DEC-CRM-010",
                "source_type": "product_decision",
                "source_ref": "30-products/lnkcrm/prd/decisions/DEC-CRM-010.md",
                "evidence_state": "inferred",
                "decision": {
                    "decision_id": "DEC-CRM-010",
                    "owner": "OPC",
                    "status": "proposed",
                    "rationale": "Membership tiers are core CRM semantics",
                },
            },
        ],
        "changes": [
            {
                "change_id": "ADD-MEMBER-TIER",
                "operation": "add",
                "concept_ref": "member-tier",
                "proposed_content": {"name": "Member Tier", "attributes": ["tier_code", "upgrade_rule"]},
                "rationale": "Owner judgment: tiered membership is core; corroborated by customer request",
                "source_ids": ["DEC-CRM-010", "REQ-CRM-010"],
            },
            {
                "change_id": "ADD-POINTS-EXPIRY",
                "operation": "add",
                "concept_ref": "points-expiry-rule",
                "proposed_content": {"name": "Points Expiry Rule", "attributes": ["validity_days", "rollover"]},
                "rationale": "Competitor capability observed; proposed for owner review, not mandated",
                "source_ids": ["EV-QM-014"],
            },
            {
                "change_id": "ADD-MEMBER-STATUS",
                "operation": "add",
                "concept_ref": "member-status",
                "proposed_content": {"name": "Member Status", "states": ["active", "frozen"]},
                "rationale": "Recovered from existing code at recorded revision",
                "source_ids": ["CODE-CRM-000"],
            },
        ],
        "review": {"status": "draft"},
    }
    assert _validate(record) == []
    _assert_source_links(record)
    # Generated content remains a draft pending owner review.
    assert record["review"] == {"status": "draft"}
    assert "proposed_release" not in record


def test_tool_first_version_uses_tool_concepts_without_business_taxonomy() -> None:
    record: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKREPORT-FIRST-001",
        "product_id": "lnkreport",
        "ontology_profile": "tool-ontology",
        "change_mode": "initial-baseline",
        "origin_flow": "forward-governance",
        "baseline": {"status": "absent"},
        "inputs": [
            {
                "source_id": "REQ-RPT-001",
                "source_type": "customer_requirement",
                "source_ref": "incoming/lnkreport/报表导出诉求.md",
                "evidence_state": "observed",
            },
            {
                "source_id": "CODE-RPT-001",
                "source_type": "code_fact",
                "source_ref": "/opt/code/lnkreport@2222222/src/export.py",
                "revision": "2222222",
                "evidence_state": "observed",
            },
        ],
        "changes": [
            {
                "change_id": "ADD-DATASET",
                "operation": "add",
                "concept_ref": "dataset",
                "proposed_content": {"name": "Dataset", "attributes": ["source", "refresh_policy"]},
                "rationale": "Tool capability observed in export flow",
                "source_ids": ["CODE-RPT-001", "REQ-RPT-001"],
            },
            {
                "change_id": "ADD-REPORT-EXPORT",
                "operation": "add",
                "concept_ref": "report-export",
                "proposed_content": {"name": "Report Export", "formats": ["xlsx", "pdf"]},
                "rationale": "Customer-requested capability",
                "source_ids": ["REQ-RPT-001"],
            },
        ],
        "review": {"status": "draft"},
    }
    assert _validate(record) == []
    _assert_source_links(record)
    # Tool concepts: no CRE-style business entities forced into the taxonomy.
    business_entities = {"shop", "contract", "merchant", "lease", "property"}
    for change in cast(list[dict[str, JsonValue]], record["changes"]):
        assert str(change["concept_ref"]) not in business_entities


def test_absent_unverified_conflicting_inputs_are_disclosed_not_fabricated() -> None:
    record: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKCRM-FIRST-002",
        "product_id": "lnkcrm",
        "ontology_profile": "business-ontology",
        "change_mode": "initial-baseline",
        "origin_flow": "forward-governance",
        "baseline": {"status": "absent"},
        "inputs": [
            {
                # Absent class: competitor analysis not provided for this task.
                "source_id": "SRC-CRM-COMPETITOR-N/A",
                "source_type": "competitor_observation",
                "source_ref": "incoming/lnkcrm/competitor-evidence",
                "evidence_state": "not_applicable",
            },
            {
                # Unverified: code exists but the area was not scanned.
                "source_id": "CODE-CRM-UNSCANNED",
                "source_type": "code_fact",
                "source_ref": "/opt/code/lnkcrm@1111111/src/marketing.py",
                "revision": "1111111",
                "evidence_state": "not_scanned",
            },
            {
                # Conflicting: two sources disagree on the same concept.
                "source_id": "REQ-CRM-011",
                "source_type": "customer_requirement",
                "source_ref": "incoming/lnkcrm/积分清零口径A.md",
                "evidence_state": "conflicting",
            },
        ],
        "changes": [
            {
                "change_id": "ADD-POINTS-CLEARING",
                "operation": "add",
                "concept_ref": "points-clearing-rule",
                "proposed_content": {"name": "Points Clearing Rule", "attributes": ["cycle", "threshold"]},
                "rationale": "Conflicting customer inputs; concept flagged for owner clarification, values not invented",
                "source_ids": ["REQ-CRM-011"],
            },
        ],
        "review": {"status": "draft"},
    }
    assert _validate(record) == []
    states = {
        str(item["source_id"]): str(item["evidence_state"])
        for item in cast(list[dict[str, JsonValue]], record["inputs"])
    }
    assert states["SRC-CRM-COMPETITOR-N/A"] == "not_applicable"
    assert states["CODE-CRM-UNSCANNED"] == "not_scanned"
    assert states["REQ-CRM-011"] == "conflicting"
    # Gaps surface for review: no accepted content, no release, draft retained.
    assert record["review"] == {"status": "draft"}
    assert "proposed_release" not in record


def test_all_inputs_absent_yields_empty_draft_claiming_nothing() -> None:
    record: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKGATEWAY-FIRST-EMPTY",
        "product_id": "lnkgateway",
        "ontology_profile": "tool-ontology",
        "change_mode": "initial-baseline",
        "origin_flow": "forward-governance",
        "baseline": {"status": "absent"},
        "inputs": [
            {
                "source_id": "SRC-GW-CUSTOMER-N/A",
                "source_type": "customer_requirement",
                "source_ref": "incoming/lnkgateway/requirements",
                "evidence_state": "not_applicable",
            },
            {
                "source_id": "CODE-GW-N/A",
                "source_type": "code_fact",
                "source_ref": "/opt/code/lnkgateway@3333333/src",
                "revision": "3333333",
                "evidence_state": "not_scanned",
            },
        ],
        "changes": [],
        "review": {"status": "draft"},
    }
    assert _validate(record) == []
    assert record["changes"] == []
    assert "proposed_release" not in record
