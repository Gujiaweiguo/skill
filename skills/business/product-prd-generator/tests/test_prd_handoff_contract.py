from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final, TypeAlias

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


def test_handoff_accepts_trace_with_layer_baselines_and_separate_decision() -> None:
    value: dict[str, JsonValue] = {
        "trace_id": "PRD-CRE-001",
        "product_id": "lnkcre",
        "product_class": "business",
        "ontology_profile": "business-ontology",
        "ontology_baseline": {
            "product_id": "lnkcre", "product_class": "business", "ontology_profile": "business-ontology",
            "layer": "ontology", "status": "resolved", "authority_ref": "30-products/lnkcre/ontology/README.md",
            "version": "0.2.0", "revision": "abc123", "release_id": "SEM-CRE-002",
        },
        "prd_baseline": {
            "product_id": "lnkcre", "product_class": "business", "ontology_profile": "business-ontology",
            "layer": "prd", "status": "resolved", "authority_ref": "30-products/lnkcre/prd/baseline/",
            "version": "1.0",
        },
        "target_repo": "/opt/code/lnkcre",
        "source_refs": ["REQ-001", "DEC-001"],
        "sources": [
            {
                "source_id": "REQ-001", "source_type": "customer_requirement",
                "source_ref": "materials/customer/requirement.md", "evidence_state": "observed",
            },
            {
                "source_id": "DEC-001", "source_type": "product_decision", "source_ref": "prd/decisions/DEC-001.md",
                "evidence_state": "inferred",
                "decision": {"decision_id": "DEC-001", "owner": "OPC", "status": "proposed", "rationale": "Prioritize pilot"},
            },
        ],
        "evidence_state": "inferred",
        "implementation_status": "partial",
    }
    assert _validate(value) == []


def test_handoff_rejects_mixed_profile_and_decision_without_decision_metadata() -> None:
    base: dict[str, JsonValue] = {
        "trace_id": "PRD-CRE-001", "product_id": "lnkcre", "product_class": "business",
        "ontology_profile": "business-ontology",
        "ontology_baseline": {"product_id": "lnkcre", "product_class": "business", "ontology_profile": "business-ontology", "layer": "ontology", "status": "unresolved", "reason": "No confirmed version"},
        "prd_baseline": {"product_id": "lnkcre", "product_class": "business", "ontology_profile": "business-ontology", "layer": "prd", "status": "unresolved", "reason": "Baseline not identified"},
        "target_repo": "/opt/code/lnkcre", "source_refs": ["DEC-001"], "source_type": "product_decision",
        "evidence_state": "inferred", "implementation_status": "unknown",
    }
    assert _validate(base)
    assert _validate({**base, "product_class": "tool"})
