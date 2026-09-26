"""Unit tests for product_prd_generator._paths helpers.

Verifies fallback semantics: project-specific config takes precedence;
when absent, falls back to 商管 defaults. Tests run against the REAL
environment (LANLNK_BASE = /opt/code/docs/lanlnk) — they verify actual
yaml files exist for langchat/LnkChatBI (Phase A deliverables) and the
business-ontology.yaml fallback is intact.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from product_prd_generator._paths import (
    _lanlnk_base,
    canonical_product_id,
    competitor_evidence_paths_for_project,
    domain_knowledge_path_for_project,
    feature_baseline_path_for_project,
    is_lnkre_product,
    MissingProductDataError,
    ontology_path_for_project,
    PRD_OUTPUT_SUBDIRS,
    resolve_product_paths,
    term_aliases_path_for_project,
)


SKILL_ROOT = Path(__file__).resolve().parents[1]

# 单测依赖真实 docs 仓的 yaml 资产：仅在两个基座变量都未设时补一个
# 已注册公司默认（任一变量已设时尊重调用方，不覆盖）。
if not (os.environ.get("COMPANY_BASE") or os.environ.get("LANLNK_BASE")):
    os.environ["LANLNK_BASE"] = "/opt/code/docs/lanlnk"

DEFAULT_LANLNK_BASE = _lanlnk_base()


# ─── _lanlnk_base（COMPANIES.md §3 契约）───────────────────────────────


def test_lanlnk_base_exits_when_both_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPANY_BASE", raising=False)
    monkeypatch.delenv("LANLNK_BASE", raising=False)
    with pytest.raises(SystemExit):
        _lanlnk_base()


def test_lanlnk_base_exits_on_relative_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """复现事故形态：COMPANY_BASE=lanlnk（裸 slug 相对路径）必须被拒。"""
    monkeypatch.setenv("COMPANY_BASE", "lanlnk")
    monkeypatch.delenv("LANLNK_BASE", raising=False)
    with pytest.raises(SystemExit):
        _lanlnk_base()


def test_lanlnk_base_exits_on_unregistered_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("COMPANY_BASE", str(tmp_path))
    monkeypatch.delenv("LANLNK_BASE", raising=False)
    with pytest.raises(SystemExit):
        _lanlnk_base()


def test_lanlnk_base_prefers_company_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPANY_BASE", "/opt/code/docs/lanlnk")
    monkeypatch.setenv("LANLNK_BASE", "/opt/code/docs/lianyou")
    assert _lanlnk_base() == Path("/opt/code/docs/lanlnk")


# ─── ontology_path_for_project ─────────────────────────────────────────


def test_ontology_path_商管_falls_back_to_business_ontology():
    """商管系统 has no project-specific ontology.yaml, so falls back to business-ontology.yaml."""
    p = ontology_path_for_project("商管系统")
    assert p == DEFAULT_LANLNK_BASE / "config" / "ontology" / "business-ontology.yaml"
    assert p.is_file(), f"Fallback path must exist: {p}"


def test_ontology_path_langchat_returns_project_specific():
    """langchat ontology.yaml migrated to 30-products/langchat/."""
    p = ontology_path_for_project("langchat")
    assert p == DEFAULT_LANLNK_BASE / "30-products" / "lnkchat" / "ontology.yaml"
    assert p.is_file(), f"langchat ontology.yaml must exist: {p}"


def test_ontology_path_lnkcrm_returns_own_draft_ontology():
    """lnkcrm 已注册（2026-09-26 docs 侧 onboarding）：命中自有 draft ontology。

    未注册时该调用会静默回落商管 business-ontology（registry 规则 2 禁止项）——
    本测试是该跨域回落的永久回归闸。
    """
    p = ontology_path_for_project("lnkcrm")
    assert p == DEFAULT_LANLNK_BASE / "30-products" / "lnkcrm" / "ontology" / "ontology.yaml"
    assert p.is_file(), f"lnkcrm draft ontology must exist: {p}"
    assert not is_lnkre_product("lnkcrm")


def test_ontology_path_LnkChatBI_returns_project_specific():
    """Phase A deliverable: LnkChatBI/output/ontology.yaml exists."""
    p = ontology_path_for_project("LnkChatBI")
    assert p == DEFAULT_LANLNK_BASE / "out" / "prd" / "LnkChatBI" / "output" / "ontology.yaml"
    assert p.is_file(), f"LnkChatBI ontology.yaml must exist (Phase A deliverable): {p}"


def test_ontology_path_unknown_project_falls_back():
    """Unknown project does not raise; falls back to business-ontology.yaml path."""
    p = ontology_path_for_project("不存在的项目_xyz_123")
    assert p == DEFAULT_LANLNK_BASE / "config" / "ontology" / "business-ontology.yaml"


def test_ontology_path_langchat_excludes_shangguan_modules():
    """ Sanity check: langchat ontology content must NOT include 商管 modules. """
    import yaml

    p = ontology_path_for_project("langchat")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    modules = data.get("modules", {})
    forbidden = ["资源管理", "招商管理", "合同管理", "财务管理", "营运管理", "物业管理", "推广管理", "系统管理"]
    for mod in forbidden:
        assert mod not in modules, f"langchat ontology must NOT include 商管 module: {mod}"


# ─── term_aliases_path_for_project ─────────────────────────────────────


def test_term_aliases_path_商管_falls_back_to_skill_references():
    """商管系统 has no project-specific term-aliases.yaml, falls back to skill references/."""
    p = term_aliases_path_for_project("商管系统", SKILL_ROOT)
    assert p == SKILL_ROOT / "references" / "term-aliases.yaml"
    assert p.is_file(), f"Fallback path must exist: {p}"


def test_term_aliases_path_langchat_returns_project_specific():
    """langchat term-aliases.yaml migrated to 30-products/langchat/."""
    p = term_aliases_path_for_project("langchat", SKILL_ROOT)
    assert p == DEFAULT_LANLNK_BASE / "30-products" / "lnkchat" / "term-aliases.yaml"
    assert p.is_file(), f"langchat term-aliases.yaml must exist: {p}"


def test_term_aliases_path_LnkChatBI_returns_project_specific():
    """Phase A deliverable: LnkChatBI/output/term-aliases.yaml exists."""
    p = term_aliases_path_for_project("LnkChatBI", SKILL_ROOT)
    assert p == DEFAULT_LANLNK_BASE / "out" / "prd" / "LnkChatBI" / "output" / "term-aliases.yaml"
    assert p.is_file(), f"LnkChatBI term-aliases.yaml must exist (Phase A deliverable): {p}"


def test_term_aliases_path_unknown_project_falls_back():
    """Unknown project does not raise; falls back to skill references/."""
    p = term_aliases_path_for_project("不存在的项目_xyz_123", SKILL_ROOT)
    assert p == SKILL_ROOT / "references" / "term-aliases.yaml"


def test_term_aliases_path_skill_root_none_returns_fallback():
    """When skill_root is None... actually the signature requires skill_root. Just check it works with valid path."""
    p = term_aliases_path_for_project("any_project", SKILL_ROOT)
    # No project-specific yaml for "any_project", so should fall back
    assert p == SKILL_ROOT / "references" / "term-aliases.yaml"


# ─── LnkCRE canonical id 别名归一（MI / MI-CRE / LnkCRE / lnkcre / 商管系统）───


@pytest.mark.parametrize("raw", ["MI", "mi", "MI-CRE", "mi-cre", "LnkCRE", "lnkcre", "LNKCRE", "商管系统"])
def test_canonical_product_id_lnkcre_family(raw: str) -> None:
    assert canonical_product_id(raw) == "lnkcre"


@pytest.mark.parametrize("raw", ["langchat", "LnkChat", "lnkchat"])
def test_canonical_product_id_lnkchat_family(raw: str) -> None:
    assert canonical_product_id(raw) == "lnkchat"


def test_canonical_product_id_unknown_stays_identity() -> None:
    assert canonical_product_id("LnkChatBI") == "LnkChatBI"
    assert canonical_product_id("不存在的项目_xyz_123") == "不存在的项目_xyz_123"


def test_is_lnkre_product_covers_aliases_and_excludes_others() -> None:
    for raw in ("MI", "MI-CRE", "LnkCRE", "lnkcre", "商管系统"):
        assert is_lnkre_product(raw)
    assert not is_lnkre_product("lnkreport")
    assert not is_lnkre_product("langchat")


# ─── ProductPaths 统一路径契约 ────────────────────────────────────────


def test_resolve_product_paths_lnkcre_contract() -> None:
    paths = resolve_product_paths("LnkCRE")
    base = DEFAULT_LANLNK_BASE / "30-products"
    assert paths.canonical_product_id == "lnkcre"
    assert paths.docs_root == base / "lnkcre"
    assert paths.ontology_root == base / "lnkcre" / "ontology"
    assert paths.prd_root == base / "lnkcre" / "prd"
    assert paths.feature_baseline_path == base / "lnkcre" / "prd" / "baseline" / "feature-baseline.yaml"
    assert paths.competitor_evidence_root == base / "lnkcre" / "evidence" / "competitors"
    assert paths.legacy_docs_root == base / "mi-cre"
    assert paths.legacy_feature_baseline_path == base / "mi-cre" / "feature-baseline" / "feature-baseline.yaml"
    assert paths.legacy_competitor_root == base / "mi-cre" / "competitor-analysis"
    assert paths.legacy_fallback_enabled is False


def test_resolve_product_paths_alias_inputs_agree() -> None:
    for raw in ("MI", "MI-CRE", "LnkCRE", "lnkcre", "商管系统"):
        assert resolve_product_paths(raw) == resolve_product_paths("LnkCRE")


def test_prd_output_dir_kinds() -> None:
    paths = resolve_product_paths("lnkcre")
    for kind, subdir in PRD_OUTPUT_SUBDIRS.items():
        assert paths.prd_output_dir(kind) == paths.prd_root / subdir
    with pytest.raises(ValueError):
        paths.prd_output_dir("nope")


def test_resolve_product_paths_lnkreport_has_no_lnkcre_legacy() -> None:
    paths = resolve_product_paths("lnkreport")
    assert paths.canonical_product_id == "lnkreport"
    assert paths.legacy_docs_root is None
    assert paths.docs_root.name == "lnkreport"


# ─── feature baseline：canonical 优先 → legacy 迁移 fallback → 显式报错 ───


def _fake_company_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "company.yaml").write_text("company: test\n", encoding="utf-8")
    monkeypatch.setenv("COMPANY_BASE", str(tmp_path))
    monkeypatch.delenv("LANLNK_BASE", raising=False)
    return tmp_path


def test_feature_baseline_prefers_canonical_when_both_exist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = _fake_company_base(tmp_path, monkeypatch)
    canonical = base / "30-products" / "lnkcre" / "prd" / "baseline" / "feature-baseline.yaml"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("version: 2\n", encoding="utf-8")
    legacy = base / "30-products" / "mi-cre" / "feature-baseline" / "feature-baseline.yaml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("version: 1\n", encoding="utf-8")
    assert feature_baseline_path_for_project("LnkCRE") == canonical


def test_feature_baseline_no_legacy_fallback_after_merge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mi-cre→lnkcre 合并完成后（2026-09），即使残留 legacy 文件也不再回退。"""
    base = _fake_company_base(tmp_path, monkeypatch)
    legacy = base / "30-products" / "mi-cre" / "feature-baseline" / "feature-baseline.yaml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("version: 1\n", encoding="utf-8")
    with pytest.raises(MissingProductDataError):
        feature_baseline_path_for_project("mi-cre")
    with pytest.raises(MissingProductDataError):
        feature_baseline_path_for_project("LnkCRE")


def test_feature_baseline_missing_raises_actionable_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = _fake_company_base(tmp_path, monkeypatch)
    with pytest.raises(MissingProductDataError) as excinfo:
        feature_baseline_path_for_project("LnkCRE")
    msg = str(excinfo.value)
    assert "lnkcre" in msg
    assert str(base / "30-products" / "lnkcre" / "prd" / "baseline" / "feature-baseline.yaml") in msg


def test_feature_baseline_lnkreport_never_reads_lnkcre(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """LnkReport 解析不得读到 LnkCRE 的 feature baseline（防跨产品静默回退）。"""
    base = _fake_company_base(tmp_path, monkeypatch)
    lnkcre_baseline = base / "30-products" / "lnkcre" / "prd" / "baseline" / "feature-baseline.yaml"
    lnkcre_baseline.parent.mkdir(parents=True)
    lnkcre_baseline.write_text("version: 2\n", encoding="utf-8")
    with pytest.raises(MissingProductDataError):
        feature_baseline_path_for_project("lnkreport")


# ─── domain knowledge：a → b → c 优先级链 ────────────────────────


def test_domain_knowledge_priority_a_b_c(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = _fake_company_base(tmp_path, monkeypatch)
    # 只有 INDEX.md → c 级
    index = base / "30-products" / "lnkcre" / "INDEX.md"
    index.parent.mkdir(parents=True)
    index.write_text("# index\n", encoding="utf-8")
    assert domain_knowledge_path_for_project("lnkcre") == index
    # 出现 ontology/README.md → b 级优先于 c
    readme = base / "30-products" / "lnkcre" / "ontology" / "README.md"
    readme.parent.mkdir(parents=True)
    readme.write_text("# ontology entry\n", encoding="utf-8")
    assert domain_knowledge_path_for_project("lnkcre") == readme
    # 出现 canonical domain-knowledge.md → a 级最优先
    dk = base / "30-products" / "lnkcre" / "ontology" / "domain-knowledge.md"
    dk.write_text("# dk\n", encoding="utf-8")
    assert domain_knowledge_path_for_project("LnkCRE") == dk


def test_domain_knowledge_missing_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_company_base(tmp_path, monkeypatch)
    with pytest.raises(MissingProductDataError) as excinfo:
        domain_knowledge_path_for_project("LnkCRE")
    assert "lnkcre" in str(excinfo.value)


# ─── competitor evidence：canonical 写入根 + legacy 只读根 ─────────────


def test_competitor_evidence_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = _fake_company_base(tmp_path, monkeypatch)
    canonical, legacy = competitor_evidence_paths_for_project("LnkCRE")
    assert canonical == base / "30-products" / "lnkcre" / "evidence" / "competitors"
    assert legacy is None  # mi-cre 合并完成后无 legacy 读取根
    canonical2, legacy2 = competitor_evidence_paths_for_project("lnkreport")
    assert legacy2 is None
    assert canonical2.name == "competitors"


# ─── 真实环境冒烟：canonical feature-baseline 可解析 ────────────────


def test_real_env_lnkcre_feature_baseline_resolves() -> None:
    """真实 docs 仓（合并完成后）：canonical lnkcre 基线必须可解析。"""
    p = feature_baseline_path_for_project("LnkCRE")
    assert p.is_file(), f"feature baseline should resolve: {p}"
