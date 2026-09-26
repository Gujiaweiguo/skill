from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import yaml


REFERENCES = Path(__file__).resolve().parents[1] / "references"


def _schema(name: str) -> dict[str, object]:
    value = cast(object, json.loads((REFERENCES / name).read_text(encoding="utf-8")))
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _strings(value: object) -> list[str]:
    assert isinstance(value, list)
    items = cast(list[object], value)
    assert all(isinstance(item, str) for item in items)
    return [cast(str, item) for item in items]


def _yaml_mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    mapping = cast(dict[object, object], value)
    assert all(isinstance(key, str) for key in mapping)
    return {cast(str, key): item for key, item in mapping.items()}


def test_product_baseline_schema_supports_domain_and_platform_models() -> None:
    schema = _schema("product-semantic-baseline.schema.json")
    properties = _mapping(schema["properties"])
    model_kinds = _strings(_mapping(properties["model_kind"])["enum"])
    assert "operational-domain-model" in model_kinds
    assert "capability-model" in model_kinds
    assert "product-runtime-model" in model_kinds
    assert "semantic-release" in model_kinds
    assert "model_kind" not in _strings(schema["required"])


def test_product_registry_covers_registered_products() -> None:
    registry = _yaml_mapping(cast(object, yaml.safe_load(
        (REFERENCES / "product-registry.yaml").read_text(encoding="utf-8")
    )))
    products = _yaml_mapping(registry["products"])
    expected = {"lnkcre", "lnkreport", "lnkchatbi", "lnkchat", "lnkvision", "lnkgateway", "lnkcrm"}
    assert expected <= set(products)
    assert _yaml_mapping(products["lnkcre"])["code_root"] == "/opt/code/lnkcre"
    assert _yaml_mapping(products["lnkchat"])["code_root"] == "/opt/code/lnkchat"
    # 2026-09-24 registry-feedback 回填 + 2026-09-26 owner 确认：code_root 全部已确认
    assert _yaml_mapping(products["lnkvision"])["code_root"] == "/opt/code/lnkvision"
    assert _yaml_mapping(products["lnkgateway"])["code_root"] == "/opt/code/lnkgateway"
    assert _yaml_mapping(products["lnkchatbi"])["code_root"] == "/opt/code/lnkchatbi"
    for pid in expected:
        code_root = _yaml_mapping(products[pid]).get("code_root")
        if isinstance(code_root, str):
            assert Path(code_root).is_dir(), f"{pid} code_root 应存在: {code_root}"
    # mi-cre 合并完成后注册表不得再携带 legacy_* fallback 字段
    for pid in expected:
        entry = _yaml_mapping(products[pid])
        assert not any(str(key).startswith("legacy_") for key in entry), (
            f"{pid} 不应再携带 legacy_* 字段（mi-cre 合并已完成）"
        )
        docs_root = entry.get("docs_root")
        if isinstance(docs_root, str):
            assert Path(docs_root).is_dir(), f"{pid} docs_root 应存在: {docs_root}"


def test_handoff_schema_separates_evidence_and_implementation_states() -> None:
    properties = _mapping(_schema("prd-handoff.schema.json")["properties"])
    evidence_states = _strings(_mapping(properties["evidence_state"])["enum"])
    implementation_states = _strings(_mapping(properties["implementation_status"])["enum"])
    assert evidence_states != implementation_states
    assert "not_scanned" in evidence_states
    assert "missing" in implementation_states


def test_handoff_schema_requires_trace_and_source_evidence() -> None:
    schema = _schema("prd-handoff.schema.json")
    required = _strings(schema["required"])
    assert "trace_id" in required
    assert "source_refs" in required
    assert "target_repo" in required
