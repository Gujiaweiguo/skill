"""Product authority contract fixtures (tasks 1.1 / 1.4).

Seven-product layer fixtures mirroring the product-semantic-baseline contract
(business/tool split, §1 rule 2) plus per-layer authority or an explicit
unresolved state. Registry nulls are never upgraded to invented authority
refs (task 1.4), and no product borrows another product's ontology.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final, TypeAlias

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012, Schema

from tests.test_product_governance_contracts import SOFTWARE_PRODUCT_PROFILES

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
    schema = _schema(CONTRACTS / "layer-reference.schema.json")
    validator = Draft202012Validator(schema, registry=_REGISTRY)
    return [error.message for error in validator.iter_errors(value)]


def _ref(
    product_id: str,
    product_class: str,
    ontology_profile: str,
    layer: str,
    *,
    authority_ref: str | None = None,
    reason: str | None = None,
    version: str | None = None,
    revision: str | None = None,
) -> dict[str, JsonValue]:
    value: dict[str, JsonValue] = {
        "product_id": product_id,
        "product_class": product_class,
        "ontology_profile": ontology_profile,
        "layer": layer,
    }
    if authority_ref is None:
        value["status"] = "unresolved"
        value["reason"] = reason or "Authority not confirmed"
    else:
        value["status"] = "resolved"
        value["authority_ref"] = authority_ref
        if version is not None:
            value["version"] = version
        if revision is not None:
            value["revision"] = revision
    return value


def _layer_fixtures() -> dict[str, dict[str, dict[str, JsonValue]]]:
    """7 products × 3 layers, mirroring the declared three-layer state.

    Profile 对账面 = baseline 契约（product-semantic-baseline.md §1 规则 2 的
    可执行形态见 tests.test_product_governance_contracts.SOFTWARE_PRODUCT_PROFILES）；
    product-registry.yaml 同名字段为历史冻结快照（B1 迁移 2026-10-04；该文件已随
    D1 2026-10-04 退役删除）。
    """
    business, tool = "business-ontology", "tool-ontology"
    return {
        "lnkcre": {
            "ontology": _ref("lnkcre", "business", business, "ontology", authority_ref="30-products/lnkcre/ontology/README.md"),
            "prd": _ref("lnkcre", "business", business, "prd", authority_ref="30-products/lnkcre/prd/baseline/"),
            "code": _ref("lnkcre", "business", business, "code", authority_ref="/opt/code/lnkcre"),
        },
        "lnkcrm": {
            # lnkcrm ontology accepted v1.0 (release SEM-CRM-OPS-001, OPC 2026-10-02,
            # registry rule 9); resolver status complete (revision v1.0), authority
            # file = 30-products/lnkcrm/ontology/ontology.yaml. code = complete per
            # O5-lnkcrm-code reconciliation (see code fixture below).
            "ontology": _ref("lnkcrm", "business", business, "ontology", authority_ref="30-products/lnkcrm/ontology/ontology.yaml"),
            "prd": _ref("lnkcrm", "business", business, "prd", reason="PRD baseline unresolved: planned (prd_ready false, guided onboarding)"),
            # O5-lnkcrm-code reconciliation (route A, 2026-10-04): source =
            # company.yaml code_root (docs c41a978 ratified); code authority
            # complete per resolver. revision is the ratify-time snapshot.
            "code": _ref(
                "lnkcrm",
                "business",
                business,
                "code",
                authority_ref="/opt/code/lnkcrm",
                revision="4323b8c9f6f195dd82083348dd6e854e7360afa3",
            ),
        },
        "lnkchatbi": {
            "ontology": _ref("lnkchatbi", "tool", tool, "ontology", authority_ref="30-products/lnkchatbi/ontology/ontology.yaml"),
            "prd": _ref("lnkchatbi", "tool", tool, "prd", authority_ref="30-products/lnkchatbi/prd/"),
            "code": _ref("lnkchatbi", "tool", tool, "code", authority_ref="/opt/code/lnkchatbi"),
        },
        "lnkreport": {
            "ontology": _ref("lnkreport", "tool", tool, "ontology", authority_ref="30-products/lnkreport/ontology/ontology.yaml"),
            "prd": _ref("lnkreport", "tool", tool, "prd", authority_ref="30-products/lnkreport/prd/"),
            "code": _ref("lnkreport", "tool", tool, "code", authority_ref="/opt/code/lnkreport"),
        },
        "lnkvision": {
            "ontology": _ref("lnkvision", "tool", tool, "ontology", authority_ref="30-products/lnkvision/ontology/域知识.md"),
            "prd": _ref("lnkvision", "tool", tool, "prd", authority_ref="30-products/lnkvision/prd/"),
            "code": _ref("lnkvision", "tool", tool, "code", authority_ref="/opt/code/lnkvision"),
        },
        "lnkgateway": {
            "ontology": _ref("lnkgateway", "tool", tool, "ontology", reason="Ontology unresolved: no owner-confirmed docs ontology candidate (registry null)"),
            "prd": _ref("lnkgateway", "tool", tool, "prd", reason="PRD baseline unresolved: no prd_root declared in registry"),
            "code": _ref("lnkgateway", "tool", tool, "code", authority_ref="/opt/code/lnkgateway"),
        },
        "lnkchat": {
            "ontology": _ref("lnkchat", "tool", tool, "ontology", authority_ref="30-products/lnkchat/ontology.yaml"),
            "prd": _ref("lnkchat", "tool", tool, "prd", authority_ref="30-products/lnkchat/prd/"),
            "code": _ref("lnkchat", "tool", tool, "code", authority_ref="/opt/code/lnkchat"),
        },
    }


def test_all_seven_products_declare_three_layers_with_valid_contracts() -> None:
    fixtures = _layer_fixtures()
    expected_products = {
        "lnkcre", "lnkcrm", "lnkchatbi", "lnkreport", "lnkvision", "lnkgateway", "lnkchat",
    }
    assert set(fixtures) == expected_products
    for product_id, layers in fixtures.items():
        assert set(layers) == {"ontology", "prd", "code"}, product_id
        for layer, layer_ref in layers.items():
            assert layer_ref["layer"] == layer
            assert _validate(layer_ref) == [], f"{product_id}/{layer}: {_validate(layer_ref)}"


def test_fixture_profiles_match_baseline_contract_and_business_tool_split() -> None:
    """B1 迁移（2026-10-04）：镜像对账面自 product-registry.yaml（已退役，D1
    2026-10-04 删除）改为 baseline 契约。

    product_class / ontology_profile 的语义权威源 = product-semantic-baseline.md
    §1 规则 2（业务系统 lnkcre/lnkcrm ↔ business-ontology；平台/AI 产品 ↔
    tool-ontology）；company.yaml 产品台账不携带这两个字段（迁移审计 §4-B1）。
    """
    fixtures = _layer_fixtures()
    for product_id, layers in fixtures.items():
        product_class, ontology_profile = SOFTWARE_PRODUCT_PROFILES[product_id]
        for layer_ref in layers.values():
            assert layer_ref["product_class"] == product_class
            assert layer_ref["ontology_profile"] == ontology_profile
    business_products = {p for p, l in fixtures.items() if l["ontology"]["product_class"] == "business"}
    tool_products = set(fixtures) - business_products
    assert business_products == {"lnkcre", "lnkcrm"}
    assert tool_products == {"lnkchatbi", "lnkreport", "lnkvision", "lnkgateway", "lnkchat"}


def test_registry_nulls_stay_unresolved_without_invented_authority() -> None:
    fixtures = _layer_fixtures()
    unresolved_expectations = {
        ("lnkcrm", "prd"): "planned",
        ("lnkgateway", "ontology"): "no owner-confirmed",
        ("lnkgateway", "prd"): "no prd_root",
    }
    # lnkcrm/code left the unresolved set via O5-lnkcrm-code reconciliation
    # (route A, 2026-10-04): company.yaml code_root ratified, so it must now
    # stay resolved with an authority_ref and a revision.
    lnkcrm_code = fixtures["lnkcrm"]["code"]
    assert lnkcrm_code["status"] == "resolved", "lnkcrm/code regressed to unresolved"
    assert lnkcrm_code["authority_ref"] == "/opt/code/lnkcrm"
    assert lnkcrm_code["revision"], "lnkcrm/code missing revision"
    for (product_id, layer), reason_fragment in unresolved_expectations.items():
        layer_ref = fixtures[product_id][layer]
        assert layer_ref["status"] == "unresolved", f"{product_id}/{layer}"
        assert "authority_ref" not in layer_ref, f"{product_id}/{layer} invented an authority"
        assert reason_fragment in layer_ref["reason"]

    # No fixture borrows another product's authority (cross-product fallback).
    owners_by_ref: dict[str, str] = {}
    for product_id, layers in fixtures.items():
        for layer, layer_ref in layers.items():
            authority = layer_ref.get("authority_ref")
            if authority is None:
                continue
            assert authority not in owners_by_ref or owners_by_ref[authority] == product_id, (
                f"{product_id}/{layer} reuses authority of {owners_by_ref[authority]}"
            )
            owners_by_ref[authority] = product_id
            assert "lnkcre" not in authority or product_id == "lnkcre", (
                f"{product_id}/{layer} points into lnkcre ontology territory"
            )


def test_unresolved_reference_requires_reason_and_schema_rejects_silent_gap() -> None:
    fixtures = _layer_fixtures()
    gateway_ontology = fixtures["lnkgateway"]["ontology"]
    assert _validate(gateway_ontology) == []
    silent: dict[str, JsonValue] = {
        "product_id": "lnkgateway",
        "product_class": "tool",
        "ontology_profile": "tool-ontology",
        "layer": "ontology",
        "status": "unresolved",
    }
    assert _validate(silent)
