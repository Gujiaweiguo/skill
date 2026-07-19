"""Unit tests for product_prd_generator.code_map._load_code_map_rules.

Verifies fallback semantics: project-specific yaml takes precedence;
when yaml missing or skill_root is None, falls back to legacy hardcoded
商管 defaults. Tests run against REAL environment.
"""
from __future__ import annotations

from pathlib import Path

from product_prd_generator.code_map import _load_code_map_rules, _LEGACY_RULES


SKILL_ROOT = Path(__file__).resolve().parents[1]


def test_rules_商管_loads_matrix_enabled_true():
    """Phase B deliverable: code-map-rules-商管系统.yaml has matrix.enabled=true."""
    rules = _load_code_map_rules("商管系统", SKILL_ROOT)
    assert rules["project"] == "商管系统"
    assert rules["matrix"]["enabled"] is True
    assert rules["matrix"]["path"] == "artifacts/alignment/product-definition-matrix.md"
    assert rules["specs"]["path"] == "openspec/specs"


def test_rules_langchat_loads_matrix_enabled_false():
    """Phase B deliverable: code-map-rules-langchat.yaml has matrix.enabled=false."""
    rules = _load_code_map_rules("langchat", SKILL_ROOT)
    assert rules["project"] == "langchat"
    assert rules["matrix"]["enabled"] is False
    assert "fastapi_routes" in rules["future_scanners"]
    assert "skill_release" in rules["future_scanners"]


def test_rules_LnkChatBI_loads_matrix_enabled_false():
    """Phase B deliverable: code-map-rules-LnkChatBI.yaml has matrix.enabled=false + LnkChatBI-specific scanners."""
    rules = _load_code_map_rules("LnkChatBI", SKILL_ROOT)
    assert rules["project"] == "LnkChatBI"
    assert rules["matrix"]["enabled"] is False
    assert "datasource_sync" in rules["future_scanners"]
    assert "openclaw_integration" in rules["future_scanners"]


def test_rules_unknown_project_falls_back_to_legacy():
    """Unknown project does not raise; falls back to legacy hardcoded dict."""
    rules = _load_code_map_rules("不存在的项目_xyz_123", SKILL_ROOT)
    assert rules["project"] == "商管系统"
    assert rules["matrix"]["enabled"] is True
    assert rules["matrix"]["path"] == "artifacts/alignment/product-definition-matrix.md"


def test_rules_skill_root_none_falls_back_to_legacy():
    """When skill_root is None (legacy mode), returns legacy hardcoded dict."""
    rules = _load_code_map_rules("anything", None)
    assert rules == _LEGACY_RULES or rules["project"] == "商管系统"
    assert rules["matrix"]["enabled"] is True


def test_rules_returns_dict_with_required_keys():
    """All return paths must produce dict with the 5 required top-level keys."""
    for project in ["商管系统", "langchat", "LnkChatBI", "unknown"]:
        rules = _load_code_map_rules(project, SKILL_ROOT)
        for key in ["project", "description", "specs", "matrix", "future_scanners", "exclude_paths"]:
            assert key in rules, f"Project {project}: missing required key {key}"
        assert "path" in rules["specs"], f"Project {project}: specs.path missing"
        assert "enabled" in rules["matrix"], f"Project {project}: matrix.enabled missing"
