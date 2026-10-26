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


# ─── lnkcard（2026-10-26 onboarding）：空基线扫描规则 ───────────────────


def test_rules_lnkcard_matrix_and_direct_scanners_disabled():
    """lnkcard 首轮基线：只扫 openspec/specs；matrix/直接代码/测试一律禁用。

    代码仓为空骨架（无业务代码），启用关键词扫描会把空集误读为
    「已验证的能力缺失」——故 direct_runtime_sources/tests 均 disabled。
    """
    rules = _load_code_map_rules("lnkcard", SKILL_ROOT)
    assert rules["project"] == "lnkcard"
    assert rules["specs"]["path"] == "openspec/specs"
    assert rules["matrix"]["enabled"] is False
    assert rules["future_scanners"]["direct_runtime_sources"]["enabled"] is False
    assert rules["future_scanners"]["tests"]["enabled"] is False


def test_scan_coverage_empty_specs_dir_reports_explicit_empty_baseline(tmp_path):
    """specs 目录存在但零 scope：扫描已执行（complete）但必须携带 empty-baseline
    limitation + artifact_count=0——空集不得被读成已验证的完整基线。"""
    from product_prd_generator.scan_coverage import build_scan_coverage

    code_root = tmp_path
    specs_root = code_root / "openspec" / "specs"
    specs_root.mkdir(parents=True)
    coverage = build_scan_coverage(code_root, specs_root, None, 0, 0)
    assert coverage.specs.artifact_count == 0
    assert coverage.specs.status.value == "complete"
    assert coverage.specs.limitations
    assert "empty baseline" in coverage.specs.limitations[0]
    # matrix disabled + direct scanners disabled → 全部 not-scanned，整体不报 complete
    assert coverage.matrix.status.value == "not-scanned"
    assert coverage.direct_code.status.value == "not-scanned"
    assert coverage.direct_tests.status.value == "not-scanned"
    assert coverage.status.value != "complete"


def test_extract_lnkcard_repo_renders_populated_spec_baseline():
    """真实 /opt/code/lnkcard（Change A/B 归档后）端到端：commit_sha=真实 HEAD、
    4 个 spec scope（含 card-accounts-and-value-ledger）、matrix/direct 全
    not-scanned——不得产出任何 LnkCRE matrix/ontology 引用。空基线渲染语义
    （commit_sha=unknown、零 capability、empty-baseline limitation）已被
    Change A/B 的真实推进取代（2026-10-26）。"""
    import unittest
    code_root = Path("/opt/code/lnkcard")
    if not code_root.is_dir():
        raise unittest.SkipTest("真实 /opt/code/lnkcard 不在本机（CI 跳过）")
    from product_prd_generator.code_map import extract, to_json

    code_map = extract(code_root, "lnkcard", skill_root=SKILL_ROOT)
    payload = to_json(code_map)
    spec_ids = {cap.id for cap in code_map.spec_capabilities}
    assert spec_ids == {
        "card-accounts-and-value-ledger",
        "dev-test-environment",
        "test-gates",
        "verification-evidence",
    }
    assert code_map.matrix_rows == ()
    assert payload["commit_sha"] not in ("", "unknown", None)
    scanners = payload["scan_coverage"]["scanners"]
    assert scanners["matrix"]["status"] == "not-scanned"
    assert scanners["direct_code"]["status"] == "not-scanned"
    assert scanners["direct_tests"]["status"] == "not-scanned"
    assert scanners["specs"]["artifact_count"] == 4
    assert scanners["specs"]["status"] == "complete"
    assert not scanners["specs"]["limitations"]
    # direct 扫描器未启用 → 整体不得报 complete
    assert payload["scan_coverage"]["status"] != "complete"
