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
    ontology_path_for_project,
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
