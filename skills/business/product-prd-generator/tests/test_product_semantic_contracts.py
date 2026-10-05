from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

from product_prd_generator import _paths

# 与 tests/test_paths.py 同款环境兜底：resolver 需要 COMPANY_BASE / LANLNK_BASE。
if not (os.environ.get("COMPANY_BASE") or os.environ.get("LANLNK_BASE")):
    os.environ["LANLNK_BASE"] = "/opt/code/docs/lanlnk"

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


def test_product_baseline_schema_supports_domain_and_platform_models() -> None:
    schema = _schema("product-semantic-baseline.schema.json")
    properties = _mapping(schema["properties"])
    model_kinds = _strings(_mapping(properties["model_kind"])["enum"])
    assert "operational-domain-model" in model_kinds
    assert "capability-model" in model_kinds
    assert "product-runtime-model" in model_kinds
    assert "semantic-release" in model_kinds
    assert "model_kind" not in _strings(schema["required"])


def test_resolver_paths_cover_registered_products() -> None:
    """B1 迁移（2026-10-04）：code_root / docs_root 断言来源自 product-registry.yaml
    （已退役，D1 2026-10-04 删除）改为 company.yaml + shared.product_context resolver
    （resolver-first 唯一权威源；registry 同名字段为历史冻结镜像，迁移审计 §4-B1）。
    """
    company = _paths.resolve_company(company_id="lanlnk")
    product_ids = {str(item["id"]) for item in company.products}
    expected = {"lnkcre", "lnkreport", "lnkchatbi", "lnkchat", "lnkvision", "lnkgateway", "lnkcrm"}
    assert expected <= product_ids
    code_roots = {
        pid: _paths.resolve_product(pid, company).layers.get("code_root")
        for pid in expected
    }
    assert code_roots["lnkcre"] == Path("/opt/code/lnkcre")
    assert code_roots["lnkchat"] == Path("/opt/code/lnkchat")
    # 2026-09-24 registry-feedback 回填 + 2026-09-26 owner 确认：code_root 全部已确认
    # （go-forward 权威值登记于 company.yaml products[].code_root）
    assert code_roots["lnkvision"] == Path("/opt/code/lnkvision")
    assert code_roots["lnkgateway"] == Path("/opt/code/lnkgateway")
    assert code_roots["lnkchatbi"] == Path("/opt/code/lnkchatbi")
    for pid in expected:
        code_root = code_roots[pid]
        # lnkcrm code_root=null（planned，company.yaml 冻结线）→ 不做存在性断言
        if code_root is not None:
            assert code_root.is_dir(), f"{pid} code_root 应存在: {code_root}"
    # mi-cre 合并完成后产品台账不得再携带 legacy_* fallback 字段
    for item in company.products:
        assert not any(str(key).startswith("legacy_") for key in item), (
            f"{item.get('id')} 不应再携带 legacy_* 字段（mi-cre 合并已完成）"
        )
    for pid in expected:
        docs_root = _paths.resolve_product(pid, company).layers.get("docs_root")
        assert isinstance(docs_root, Path) and docs_root.is_dir(), (
            f"{pid} docs_root 应存在: {docs_root}"
        )


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
