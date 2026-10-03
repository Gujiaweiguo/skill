from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final, TypeAlias

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012, Schema

ROOT: Final = Path(__file__).resolve().parents[1]
CONTRACTS: Final = ROOT / "references" / "product-governance"

JsonValue: TypeAlias = (
    None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
)


def _json_value(value: JsonValue) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _schema(path: Path) -> Schema:
    raw: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    parsed = _json_value(raw)
    if not isinstance(parsed, dict):
        raise TypeError(f"{path.name} must contain a JSON schema object")
    return parsed


def _yaml_mapping(path: Path) -> dict[str, JsonValue]:
    raw: JsonValue = yaml.safe_load(path.read_text(encoding="utf-8"))
    parsed = _json_value(raw)
    if not isinstance(parsed, dict):
        raise TypeError(f"{path.name} must contain a YAML mapping")
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


def _validate(name: str, value: Mapping[str, JsonValue]) -> list[str]:
    validator = Draft202012Validator(_schema(CONTRACTS / name), registry=_REGISTRY)
    return [error.message for error in validator.iter_errors(value)]


def test_layer_reference_accepts_business_and_tool_profiles_and_unresolved() -> None:
    business: dict[str, JsonValue] = {
        "product_id": "lnkcre",
        "product_class": "business",
        "ontology_profile": "business-ontology",
        "layer": "ontology",
        "status": "resolved",
        "authority_ref": "30-products/lnkcre/ontology/README.md",
    }
    tool: dict[str, JsonValue] = {
        "product_id": "lnkreport",
        "product_class": "tool",
        "ontology_profile": "tool-ontology",
        "layer": "ontology",
        "status": "resolved",
        "authority_ref": "30-products/lnkreport/ontology/ontology.yaml",
    }
    unresolved: dict[str, JsonValue] = {
        "product_id": "lnkgateway",
        "product_class": "tool",
        "ontology_profile": "tool-ontology",
        "layer": "ontology",
        "status": "unresolved",
        "reason": "No owner-confirmed ontology authority",
    }
    assert _validate("layer-reference.schema.json", business) == []
    assert _validate("layer-reference.schema.json", tool) == []
    assert _validate("layer-reference.schema.json", unresolved) == []


def test_layer_reference_rejects_cross_product_ontology_fallback() -> None:
    value: dict[str, JsonValue] = {
        "product_id": "lnkreport",
        "product_class": "tool",
        "ontology_profile": "business-ontology",
        "layer": "ontology",
        "status": "resolved",
        "authority_ref": "30-products/lnkcre/ontology/README.md",
    }
    assert _validate("layer-reference.schema.json", value)


def test_product_registry_contains_seven_software_products_and_lnkwebsite_prd_only() -> None:
    registry = _yaml_mapping(ROOT / "references" / "product-registry.yaml")
    products = registry["products"]
    assert isinstance(products, dict)
    expected_profiles = {
        "lnkcre": ("business", "business-ontology"),
        "lnkcrm": ("business", "business-ontology"),
        "lnkchatbi": ("tool", "tool-ontology"),
        "lnkreport": ("tool", "tool-ontology"),
        "lnkvision": ("tool", "tool-ontology"),
        "lnkgateway": ("tool", "tool-ontology"),
        "lnkchat": ("tool", "tool-ontology"),
    }
    # 七产品软件治理契约范围不变；lnkwebsite 2026-10-02 起为 prd-only 登记
    # （OPC：不建本体层，out of software product contract，仅消 Check 4 漂移信号）。
    assert set(products) - {"lnkwebsite"} == set(expected_profiles)
    assert "lnkwebsite" in products
    website = products["lnkwebsite"]
    assert isinstance(website, dict)
    assert website["ontology"] is None
    assert website["ontology_profile"] is None
    assert website["adapter_status"] == "unsupported"
    for product_id in expected_profiles:
        product = products[product_id]
        assert isinstance(product, dict)
        assert product["product_class"] == expected_profiles[product_id][0]
        assert product["ontology_profile"] == expected_profiles[product_id][1]
        assert "origin_flow" not in product
    chatbi = products["lnkchatbi"]
    assert isinstance(chatbi, dict)
    assert chatbi["product_status"] == "complete"
    assert chatbi["adapter_status"] == "partial"


def test_source_reference_keeps_decisions_separate_from_observations() -> None:
    observed: dict[str, JsonValue] = {
        "source_id": "SRC-001",
        "source_type": "competitor_observation",
        "source_ref": "30-products/lnkcre/evidence/competitors/vendor/evidence-ledger.json#EV-001",
        "evidence_id": "EV-001",
        "content_sha256": "a" * 64,
        "evidence_state": "observed",
    }
    decision: dict[str, JsonValue] = {
        "source_id": "DEC-001",
        "source_type": "product_decision",
        "source_ref": "30-products/lnkcre/prd/decisions/decision-001.md",
        "evidence_state": "inferred",
        "decision": {
            "decision_id": "DEC-001",
            "owner": "OPC",
            "status": "proposed",
            "rationale": "Product direction",
            "supporting_source_ids": ["SRC-001"],
        },
    }
    assert _validate("source-reference.schema.json", observed) == []
    assert _validate("source-reference.schema.json", decision) == []

    wrong_decision_owner: dict[str, JsonValue] = {
        **decision,
        "decision": {
            "decision_id": "DEC-001",
            "owner": "Product Team",
            "status": "proposed",
            "rationale": "Wrong approval owner",
        },
    }
    assert _validate("source-reference.schema.json", wrong_decision_owner)
    assert _validate("source-reference.schema.json", {
        **observed,
        "source_type": "product_decision",
        "decision": None,
    })
    material: dict[str, JsonValue] = {
        "source_id": "raw:vendor/manual.md",
        "source_type": "material_source",
        "source_ref": "raw/vendor/manual.md",
        "content_sha256": "b" * 64,
        "evidence_state": "observed",
    }
    assert _validate("source-reference.schema.json", material) == []
    code_without_revision: dict[str, JsonValue] = {
        "source_id": "CODE-001",
        "source_type": "code_fact",
        "source_ref": "/opt/code/lnkcre/src/resource.py",
        "evidence_state": "observed",
    }
    assert _validate("source-reference.schema.json", code_without_revision)


def test_scan_coverage_accepts_partial_manifest_with_scanner_states() -> None:
    value: dict[str, JsonValue] = {
        "status": "partial",
        "scope": ["configured OpenSpec specs", "direct runtime code", "direct tests"],
        "limitations": ["Direct runtime code and test evidence are not scanned."],
        "scanners": {
            "specs": {"status": "complete", "scope": ["openspec/specs", "*/spec.md"], "artifact_count": 272},
            "matrix": {"status": "not-scanned", "scope": ["matrix disabled by code-map rules"], "artifact_count": 0},
            "direct_code": {"status": "not-scanned", "scope": ["runtime source code"], "artifact_count": 0},
            "direct_tests": {"status": "not-scanned", "scope": ["test files and test execution"], "artifact_count": 0},
        },
    }

    assert _validate("scan-coverage.schema.json", value) == []
    assert _validate("implementation-return.schema.json", {
        "schema_version": "1.0",
        "return_id": "RET-SCAN-001",
        "product_id": "lnkchat",
        "origin_flow": "code-evidence-reverse",
        "trace_ids": ["SCAN-001"],
        "target_repo": "/opt/code/lnkchat",
        "source_revision": "71fddad4",
        "scan_coverage": value,
        "review_status": "pending",
        "proposed_updates": [],
    }) == []


def test_ontology_change_set_requires_mode_consistent_baseline_and_approval() -> None:
    source: dict[str, JsonValue] = {
        "source_id": "REQ-001",
        "source_type": "customer_requirement",
        "source_ref": "incoming/customer/request.md",
        "evidence_state": "observed",
    }
    initial: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKCRM-001",
        "product_id": "lnkcrm",
        "ontology_profile": "business-ontology",
        "change_mode": "initial-baseline",
        "origin_flow": "forward-governance",
        "baseline": {"status": "absent"},
        "inputs": [source],
        "changes": [{
            "change_id": "ADD-001",
            "operation": "add",
            "concept_ref": "member-segment",
            "proposed_content": {"name": "Member Segment", "attributes": ["criteria"]},
            "rationale": "Source requirement indicates reusable concept",
            "source_ids": ["REQ-001"],
        }],
        "review": {"status": "draft"},
    }
    assert _validate("ontology-change-set.schema.json", initial) == []
    approved_without_decision: dict[str, JsonValue] = {
        **initial,
        "review": {"status": "accepted", "owner": "OPC", "reviewed_at": "2026-09-30T09:00:00Z"},
    }
    assert _validate("ontology-change-set.schema.json", approved_without_decision)
    wrong_approver: dict[str, JsonValue] = {
        **initial,
        "review": {
            "status": "accepted", "owner": "Product Team", "decision_ref": "DEC-CRM-001",
            "reviewed_at": "2026-09-30T09:00:00Z",
        },
        "proposed_release": {"version": "0.1.0", "source_revision": "abc123"},
    }
    assert _validate("ontology-change-set.schema.json", wrong_approver)
    wrong_mode: dict[str, JsonValue] = {**initial, "change_mode": "incremental"}
    assert _validate("ontology-change-set.schema.json", wrong_mode)


def test_incremental_ontology_change_requires_change_local_flow_direction() -> None:
    candidate: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKCRM-DELTA-001",
        "product_id": "lnkcrm",
        "ontology_profile": "business-ontology",
        "change_mode": "incremental",
        "baseline": {"status": "identified", "version": "0.1.0", "authority_ref": "ontology/ontology.yaml"},
        "inputs": [],
        "changes": [],
        "review": {"status": "draft"},
    }
    assert _validate("ontology-change-set.schema.json", candidate)


def test_reverse_ontology_candidate_is_per_change_and_remains_review_gated() -> None:
    candidate: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKCHATBI-REVERSE-001",
        "product_id": "lnkchatbi",
        "ontology_profile": "tool-ontology",
        "change_mode": "initial-baseline",
        "origin_flow": "code-evidence-reverse",
        "scan_coverage": {"status": "partial", "scope": ["src/reports"], "limitations": ["Tests not scanned"]},
        "baseline": {"status": "absent"},
        "inputs": [{
            "source_id": "CODE-LCHBI-001",
            "source_type": "code_fact",
            "source_ref": "/opt/code/lnkchatbi@abc123/src/reports.py",
            "revision": "abc123",
            "evidence_state": "observed",
        }],
        "changes": [{
            "change_id": "ADD-REPORT-EXECUTION",
            "operation": "add",
            "concept_ref": "report-execution",
            "proposed_content": {"name": "Report Execution"},
            "rationale": "Observed in code at the recorded source revision",
            "source_ids": ["CODE-LCHBI-001"],
        }],
        "review": {"status": "draft"},
    }
    assert _validate("ontology-change-set.schema.json", candidate) == []
    without_coverage: dict[str, JsonValue] = dict(candidate)
    _removed_coverage = without_coverage.pop("scan_coverage")
    assert _validate("ontology-change-set.schema.json", without_coverage)
    assert _validate("ontology-change-set.schema.json", {
        **candidate,
        "origin_flow": "product-history-code-first",
    })


def test_forward_ontology_impact_check_can_record_reasoned_no_change() -> None:
    no_change: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKCRM-NOCHANGE-001",
        "product_id": "lnkcrm",
        "ontology_profile": "business-ontology",
        "change_mode": "incremental",
        "origin_flow": "forward-governance",
        "ontology_impact": {
            "result": "no-change",
            "rationale": "The request adjusts dashboard wording but adds no semantic concept or rule.",
            "baseline_ref": "ontology/0.1.0",
        },
        "baseline": {
            "status": "identified",
            "version": "0.1.0",
            "authority_ref": "30-products/lnkcrm/ontology/ontology.yaml",
        },
        "inputs": [{
            "source_id": "REQ-CRM-002",
            "source_type": "customer_requirement",
            "source_ref": "incoming/lnkcrm/requirement-002.md",
            "evidence_state": "observed",
        }],
        "changes": [],
        "review": {"status": "draft"},
    }
    assert _validate("ontology-change-set.schema.json", no_change) == []


def test_reconciliation_has_pair_specific_coverage_and_cannot_infer_missing_from_unscanned() -> None:
    base: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "reconciliation_id": "REC-001",
        "product_id": "lnkreport",
        "pair": "ontology-code",
        "left": {
            "product_id": "lnkreport", "product_class": "tool", "ontology_profile": "tool-ontology",
            "layer": "ontology", "status": "resolved", "authority_ref": "ontology/ontology.yaml", "version": "1.0",
        },
        "right": {
            "product_id": "lnkreport", "product_class": "tool", "ontology_profile": "tool-ontology",
            "layer": "code", "status": "resolved", "authority_ref": "/opt/code/lnkreport", "revision": "abc123",
        },
        "coverage": {"status": "not-scanned", "scope": [], "limitations": ["No scanner"]},
        "outcome": "not-scanned",
        "findings": [],
    }
    assert _validate("reconciliation-record.schema.json", base) == []
    assert _validate("reconciliation-record.schema.json", {**base, "outcome": "missing"})


def test_reconciliation_pair_requires_its_declared_layer_order() -> None:
    base: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "reconciliation_id": "REC-PRD-CODE-001",
        "product_id": "lnkreport",
        "pair": "prd-code",
        "left": {
            "product_id": "lnkreport", "product_class": "tool", "ontology_profile": "tool-ontology",
            "layer": "prd", "status": "resolved", "authority_ref": "prd/baseline/", "version": "1.0",
        },
        "right": {
            "product_id": "lnkreport", "product_class": "tool", "ontology_profile": "tool-ontology",
            "layer": "code", "status": "resolved", "authority_ref": "/opt/code/lnkreport", "revision": "abc123",
        },
        "coverage": {"status": "complete", "scope": ["report-export"], "limitations": []},
        "outcome": "aligned",
        "findings": [],
    }
    assert _validate("reconciliation-record.schema.json", base) == []
    invalid_pair: dict[str, JsonValue] = {**base, "pair": "ontology-prd"}
    assert _validate("reconciliation-record.schema.json", invalid_pair)
    ontology_prd: dict[str, JsonValue] = {
        **base,
        "reconciliation_id": "REC-ONTOLOGY-PRD-001",
        "pair": "ontology-prd",
        "left": {
            "product_id": "lnkreport", "product_class": "tool", "ontology_profile": "tool-ontology",
            "layer": "ontology", "status": "resolved", "authority_ref": "ontology/ontology.yaml", "version": "1.0",
        },
        "right": {
            "product_id": "lnkreport", "product_class": "tool", "ontology_profile": "tool-ontology",
            "layer": "prd", "status": "resolved", "authority_ref": "prd/baseline/", "version": "1.0",
        },
    }
    ontology_code: dict[str, JsonValue] = {
        **base,
        "reconciliation_id": "REC-ONTOLOGY-CODE-001",
        "pair": "ontology-code",
        "left": {
            "product_id": "lnkreport", "product_class": "tool", "ontology_profile": "tool-ontology",
            "layer": "ontology", "status": "resolved", "authority_ref": "ontology/ontology.yaml", "version": "1.0",
        },
    }
    assert _validate("reconciliation-record.schema.json", ontology_prd) == []
    assert _validate("reconciliation-record.schema.json", ontology_code) == []


def test_reconciliation_routes_semantic_decisions_to_opc() -> None:
    record: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "reconciliation_id": "REC-OPC-ROUTE-001",
        "product_id": "lnkchatbi",
        "pair": "ontology-code",
        "left": {
            "product_id": "lnkchatbi", "product_class": "tool", "ontology_profile": "tool-ontology",
            "layer": "ontology", "status": "unresolved", "reason": "No accepted baseline yet",
        },
        "right": {
            "product_id": "lnkchatbi", "product_class": "tool", "ontology_profile": "tool-ontology",
            "layer": "code", "status": "resolved", "authority_ref": "/opt/code/lnkchatbi", "revision": "abc123",
        },
        "coverage": {"status": "partial", "scope": ["src/reports"], "limitations": []},
        "outcome": "drifted",
        "findings": [{
            "finding_id": "FND-OPC-001",
            "summary": "Observed behavior needs product-semantic decision",
            "source_ids": ["CODE-LCHBI-001"],
            "disposition": "ontology-review",
            "owner": "OPC",
        }],
    }
    assert _validate("reconciliation-record.schema.json", record) == []
    wrong_owner: dict[str, JsonValue] = {
        **record,
        "findings": [{
            "finding_id": "FND-OPC-001",
            "summary": "Observed behavior needs product-semantic decision",
            "source_ids": ["CODE-LCHBI-001"],
            "disposition": "ontology-review",
            "owner": "Engineering",
        }],
    }
    assert _validate("reconciliation-record.schema.json", wrong_owner)


def test_implementation_return_requires_verification_for_accepted_status() -> None:
    base: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "return_id": "RET-001",
        "product_id": "lnkcre",
        "trace_ids": ["PRD-CRE-001"],
        "target_repo": "/opt/code/lnkcre",
        "review_status": "accepted",
        "proposed_updates": [],
    }
    assert _validate("implementation-return.schema.json", base)
    assert _validate("implementation-return.schema.json", {
        **base,
        "open_spec_change_id": "cre-change-1",
        "source_revision": "abc123",
        "verification_refs": ["verification-report.md"],
        "review_owner": "OPC",
    }) == []


def test_unreviewed_implementation_return_remains_proposed() -> None:
    pending: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "return_id": "RET-PENDING-001",
        "product_id": "lnkcre",
        "trace_ids": ["PRD-CRE-001"],
        "target_repo": "/opt/code/lnkcre",
        "review_status": "incomplete",
        "proposed_updates": [{
            "destination_layer": "ontology",
            "summary": "Review semantic mismatch found during implementation",
            "status": "proposed",
        }],
    }
    assert _validate("implementation-return.schema.json", pending) == []
    accepted_without_verification: dict[str, JsonValue] = {
        **pending,
        "review_status": "accepted",
        "review_owner": "OPC",
    }
    assert _validate("implementation-return.schema.json", accepted_without_verification)


def test_reverse_implementation_return_cannot_mutate_canonical_code_or_accept_update() -> None:
    reverse_return: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "return_id": "RET-REVERSE-001",
        "product_id": "lnkchatbi",
        "origin_flow": "code-evidence-reverse",
        "trace_ids": ["CODE-LCHBI-001"],
        "target_repo": "/opt/code/lnkchatbi",
        "source_revision": "abc123",
        "scan_coverage": {"status": "partial", "scope": ["src/reports"], "limitations": ["Tests not scanned"]},
        "review_status": "pending",
        "proposed_updates": [{
            "destination_layer": "reconciliation",
            "summary": "Record code evidence for ontology and PRD comparison",
            "status": "proposed",
        }],
    }
    assert _validate("implementation-return.schema.json", reverse_return) == []
    code_write: dict[str, JsonValue] = {
        **reverse_return,
        "proposed_updates": [{
            "destination_layer": "code",
            "summary": "Direct reverse mutation is forbidden",
            "status": "proposed",
        }],
    }
    assert _validate("implementation-return.schema.json", code_write)
    accepted_reverse: dict[str, JsonValue] = {
        **reverse_return,
        "review_status": "accepted",
        "open_spec_change_id": "lchbi-change-1",
        "verification_refs": ["verification.md"],
        "review_owner": "OPC",
        "proposed_updates": [{
            "destination_layer": "ontology",
            "summary": "Direct canonical promotion is forbidden",
            "status": "accepted",
        }],
    }
    assert _validate("implementation-return.schema.json", accepted_reverse)


def test_accepted_reverse_return_does_not_accept_its_candidate_updates() -> None:
    reverse_return: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "return_id": "RET-REVERSE-ACCEPTED-001",
        "product_id": "lnkchatbi",
        "origin_flow": "code-evidence-reverse",
        "trace_ids": ["CODE-LCHBI-001"],
        "target_repo": "/opt/code/lnkchatbi",
        "open_spec_change_id": "lchbi-change-1",
        "source_revision": "abc123",
        "scan_coverage": {"status": "complete", "scope": ["src/reports"]},
        "verification_refs": ["verification.md"],
        "review_status": "accepted",
        "review_owner": "OPC",
        "proposed_updates": [{
            "destination_layer": "ontology",
            "summary": "Candidate for OPC semantic decision",
            "status": "proposed",
        }],
    }
    assert _validate("implementation-return.schema.json", reverse_return) == []
    promoted_update: dict[str, JsonValue] = {
        **reverse_return,
        "proposed_updates": [{
            "destination_layer": "ontology",
            "summary": "Must have a separate ontology-change-set promotion decision",
            "status": "accepted",
            "decision_ref": "DEC-ONTOLOGY-001",
        }],
    }
    assert _validate("implementation-return.schema.json", promoted_update)


def test_accepted_initial_ontology_change_requires_versioned_release() -> None:
    source: dict[str, JsonValue] = {
        "source_id": "DEC-CRM-001",
        "source_type": "product_decision",
        "source_ref": "prd/decisions/DEC-CRM-001.md",
        "evidence_state": "inferred",
        "decision": {
            "decision_id": "DEC-CRM-001", "owner": "OPC", "status": "accepted",
            "rationale": "Establish the initial membership model",
        },
    }
    change_set: dict[str, JsonValue] = {
        "schema_version": "1.0",
        "change_set_id": "ONT-LNKCRM-BASELINE-001",
        "product_id": "lnkcrm",
        "ontology_profile": "business-ontology",
        "change_mode": "initial-baseline",
        "origin_flow": "forward-governance",
        "baseline": {"status": "absent"},
        "inputs": [source],
        "changes": [{
            "change_id": "ADD-MEMBER-001", "operation": "add", "concept_ref": "member",
            "proposed_content": {"name": "Member", "attributes": ["member_id", "status"]},
            "rationale": "Create an explicit product concept from the approved decision",
            "source_ids": ["DEC-CRM-001"],
        }],
        "review": {
            "status": "accepted", "owner": "OPC", "decision_ref": "DEC-CRM-001",
            "reviewed_at": "2026-10-01T08:00:00Z",
        },
    }
    assert _validate("ontology-change-set.schema.json", change_set)
    accepted_with_release: dict[str, JsonValue] = {
        **change_set,
        "proposed_release": {"version": "0.1.0", "source_revision": "a" * 40, "release_id": "SEM-CRM-001"},
    }
    assert _validate("ontology-change-set.schema.json", accepted_with_release) == []
