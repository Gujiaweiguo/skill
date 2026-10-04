"""pricing-generator × shared.product_context 最小集成测试。

只覆盖本 skill 实际消费面：LnkCRE 功能基线候选路径的 resolver-first 解析。
八产品完整性 / lnkchat / lnkgateway / lnkwebsite 等产品面回归在
`/opt/code/skill/shared/product_context/tests/test_resolver.py`（31 项），本文件
不重复跑全产品矩阵——resolver 能解析某产品 ≠ pricing-generator 支持该产品报价
（adapter 维度见 references/product-context-消费方审计-2026-10.md §4）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

REPO_ROOT = SKILL_DIR.parents[2]


def _make_company(tmp_path: Path, products_yaml: str) -> Path:
    """建一个满足 resolver 校验（id == 目录名）的 fixture 公司基座。"""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "company.yaml").write_text(
        f"schema_version: 1\nid: {tmp_path.name}\nbrand: Test\nproducts:\n{products_yaml}",
        encoding="utf-8",
    )
    return tmp_path


_LNKCRE_AND_LNKCRM = """\
  - id: lnkcre
    name: LnkCRE Test
    code_root: /nonexistent-lnkcre-code
    prd_ready: false
  - id: lnkcrm
    name: CRM Test
    code_root: null
    prd_ready: false
"""


@pytest.fixture
def company_with_lnkcre(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = _make_company(tmp_path, _LNKCRE_AND_LNKCRM)
    monkeypatch.setenv("COMPANY_BASE", str(base))
    monkeypatch.delenv("LANLNK_BASE", raising=False)
    return base


def _load_generate_quote():
    import generate_quote  # noqa: E402 - script-run skill（无包结构），同 material-importer 测试惯例

    return generate_quote


def test_baseline_paths_resolver_first(company_with_lnkcre: Path) -> None:
    """resolver 命中 lnkcre → prd_root 推导候选排第一。"""
    gq = _load_generate_quote()
    prd_root = company_with_lnkcre / "30-products" / "lnkcre" / "prd"
    (prd_root / "baseline").mkdir(parents=True)
    paths = gq._mi_feature_baseline_paths()
    assert paths[0] == prd_root / "baseline" / "feature-baseline.yaml"
    assert str(company_with_lnkcre) in str(paths[0])


def test_baseline_paths_fallback_when_resolver_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """lnkcre 未注册于当前公司台账 → resolver 失败，仅保留既有 canonical 兼容候选。"""
    base = _make_company(tmp_path, "  - id: other\n    name: Other\n    code_root: null\n")
    monkeypatch.setenv("COMPANY_BASE", str(base))
    monkeypatch.delenv("LANLNK_BASE", raising=False)
    gq = _load_generate_quote()
    paths = gq._mi_feature_baseline_paths()
    assert paths == [
        base / "30-products" / "lnkcre" / "prd" / "baseline" / "feature-baseline.yaml"
    ]


def test_baseline_paths_without_shared_module(
    company_with_lnkcre: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """独立部署（shared.product_context 不可用）→ 同样只保留兼容候选。"""
    gq = _load_generate_quote()
    monkeypatch.setattr(gq, "_product_context", None)
    paths = gq._mi_feature_baseline_paths()
    assert paths == [
        company_with_lnkcre / "30-products" / "lnkcre" / "prd" / "baseline" / "feature-baseline.yaml"
    ]


def test_resolver_keeps_null_code_root_unconfirmed(company_with_lnkcre: Path) -> None:
    """code_root: null（lnkcrm 形态）→ layers.code_root 恒为 None，不猜路径。

    本机存在 /opt/code/lnkcrm 时 status = present-unconfirmed（观察证据），
    不存在时 = planned；两种情况下 code_root 都不得被推断出来。
    """
    gq = _load_generate_quote()
    assert gq._product_context is not None
    company = gq._product_context.resolve_company(
        company_base=company_with_lnkcre, require_explicit=True
    )
    product = gq._product_context.resolve_product("lnkcrm", company)
    assert product.code_root is None
    assert product.layers["code_root"] is None
    assert product.authority["code"].status in {"present-unconfirmed", "planned"}
    if product.authority["code"].status == "present-unconfirmed":
        assert product.authority["code"].source == "observed-external-checkout"


def test_unknown_product_fails_without_lnkcre_fallback(company_with_lnkcre: Path) -> None:
    """未注册产品 → ResolutionError，不静默回退 lnkcre。"""
    gq = _load_generate_quote()
    assert gq._product_context is not None
    company = gq._product_context.resolve_company(
        company_base=company_with_lnkcre, require_explicit=True
    )
    with pytest.raises(gq._product_context.ProductContextError):
        gq._product_context.resolve_product("lnkchatbi", company)


def test_company_base_has_no_silent_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """COMPANY_BASE/LANLNK_BASE 均未设置 → 明确退出，绝不回落 /opt/code/docs/lanlnk。"""
    gq = _load_generate_quote()
    monkeypatch.delenv("COMPANY_BASE", raising=False)
    monkeypatch.delenv("LANLNK_BASE", raising=False)
    with pytest.raises(SystemExit):
        gq.get_company_base()
