"""技术骨架基线（technical-only baseline）回归测试 —— 2026-11-23 lnkretail。

背景：lnkretail 的技术骨架已建立（有提交、3 个技术 OpenSpec scope），业务模块未实现。
生成器此前只有两条播种路径：空基线→present-unconfirmed；基线已有内容→（开关打开时）
missing。技术骨架让 specs 扫描不再为空，48 项本体能力整体掉出对账矩阵。

本文件覆盖 code-map rules 的 ``specs.exclude``：
1. 被排除的技术 scope 不进入业务基线，其余 scope 不受影响，并留下 technical-only 说明；
2. 全部 scope 被排除 → 业务基线为空（artifact_count=0 + empty baseline 语义 + technical-only 标记）；
3. 该基线下本体能力按 present-unconfirmed 播种（不是 missing），gap 文案如实写“技术骨架”；
4. 渲染措辞区分技术骨架与零提交骨架仓；
5. 默认（未配置 exclude）行为不变；
6. 归档证据路径同样跳过被排除的技术 scope（它们不得以 missing 回到对账结果）。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from product_prd_generator import code_map
from product_prd_generator import reconcile as recon
from product_prd_generator import render
from product_prd_generator.reconcile import (
    _is_empty_code_baseline,
    _is_technical_only_baseline,
    reconcile,
)
from product_prd_generator.scan_coverage import build_scan_coverage, scan_coverage_to_json
from product_prd_generator.archive_evidence import ArchiveEvidence, apply_archive_evidence

SKILL_ROOT = Path(__file__).resolve().parents[1]

ONT = {
    "modules": {
        "procurement": {
            "name": "采购",
            "sub_functions": {
                "purchase-order": {"capabilities": ["purchase-order-management"], "terms": ["采购订单"]},
            },
        },
        "inventory": {
            "name": "库存",
            "sub_functions": {
                "goods-receipt": {"capabilities": ["goods-receipt-management"], "terms": ["收货验收"]},
            },
        },
    }
}

SKELETON_COVERAGE = {
    "status": "partial",
    "scanners": {
        "specs": {
            "status": "complete",
            "artifact_count": 0,
            "limitations": [
                "OpenSpec specs root exists but contains no spec scopes (empty baseline; no code capability claims)."
            ],
        },
        "matrix": {"status": "not-scanned", "artifact_count": 0, "limitations": []},
    },
}


def _make_repo(root: Path, scopes: list[str]) -> Path:
    for scope in scopes:
        scope_dir = root / "openspec" / "specs" / scope
        scope_dir.mkdir(parents=True)
        (scope_dir / "spec.md").write_text(
            f"# {scope} requirement\n\n#### Scenario: s\n- **WHEN** x\n", encoding="utf-8"
        )
    return root


def _skill_root(root: Path, exclude: list[str]) -> Path:
    """以 lnkretail 真实规则文件为模板（结构一致），但 exclude 列表由测试给定。"""
    template = yaml.safe_load((SKILL_ROOT / "references" / "code-map-rules-lnkretail.yaml").read_text(encoding="utf-8"))
    template["project"] = "demo"
    template["specs"]["exclude"] = exclude
    skill_root = root / "skill"
    (skill_root / "references").mkdir(parents=True, exist_ok=True)
    (skill_root / "references" / "code-map-rules-demo.yaml").write_text(
        yaml.safe_dump(template, allow_unicode=True), encoding="utf-8"
    )
    return skill_root


def _extract(tmp_path: Path, scopes: list[str], exclude: list[str]) -> code_map.CodeMap:
    root = tmp_path / "case"
    return code_map.extract(
        _make_repo(root, scopes), project="demo", skill_root=_skill_root(tmp_path / "skillroot", exclude)
    )


def test_partial_exclude_keeps_business_scopes_and_reports_technical_only(tmp_path) -> None:
    cm = _extract(tmp_path, ["service-health", "purchase-order"], ["service-health"])
    assert sorted(str(cap.id) for cap in cm.spec_capabilities) == ["purchase-order"]
    assert [str(cap.id) for cap in cm.excluded_spec_capabilities] == ["service-health"]
    assert cm.scan_coverage.specs.artifact_count == 1
    assert "technical-only" in cm.scan_coverage.specs.limitations[0]
    assert code_map.to_json(cm)["excluded_spec_scopes"] == ["service-health"]


def test_all_scopes_excluded_is_empty_technical_only_baseline(tmp_path) -> None:
    cm = _extract(tmp_path, ["service-health", "database-isolation"], ["service-health", "database-isolation"])
    assert cm.spec_capabilities == ()
    assert cm.scan_coverage.specs.artifact_count == 0
    limitations = list(cm.scan_coverage.specs.limitations)
    assert len(limitations) == 1
    assert "technical-only" in limitations[0] and "empty baseline" in limitations[0] and "2" in limitations[0]
    coverage_json = scan_coverage_to_json(cm.scan_coverage)
    assert _is_empty_code_baseline(coverage_json) is True
    assert _is_technical_only_baseline(coverage_json) is True


def test_no_exclude_keeps_default_behavior(tmp_path) -> None:
    cm = _extract(tmp_path, ["service-health", "purchase-order"], [])
    assert sorted(str(cap.id) for cap in cm.spec_capabilities) == ["purchase-order", "service-health"]
    assert cm.excluded_spec_capabilities == ()
    assert cm.scan_coverage.specs.artifact_count == 2
    assert not cm.scan_coverage.specs.limitations
    assert _is_technical_only_baseline(scan_coverage_to_json(cm.scan_coverage)) is False


def _coverage(tmp_path: Path, excluded: int) -> dict:
    """specs 目录存在、计入的 scope 数为 0、另有 excluded 个技术 scope 被排除。"""
    specs_root = tmp_path / "specs"
    specs_root.mkdir(exist_ok=True)
    return scan_coverage_to_json(
        build_scan_coverage(tmp_path, specs_root, None, 0, 0, excluded_spec_count=excluded)
    )


def test_seeds_present_unconfirmed_with_technical_only_wording(monkeypatch, tmp_path) -> None:
    ontology = tmp_path / "ontology.yaml"
    ontology.write_text(yaml.safe_dump(ONT, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(recon, "ontology_path_for_project", lambda project: ontology)
    coverage = _coverage(tmp_path, 3)
    cm = {
        "project": "demo",
        "source_path": str(tmp_path),
        "commit_sha": "unknown",
        "scan_coverage": coverage,
        "spec_capabilities": [],
        "matrix_rows": [],
    }
    result = reconcile(cm, {"features": [], "requirements": []})
    assert {cap.id for cap in result.capabilities} == {"purchase-order-management", "goods-receipt-management"}
    assert {cap.reconciled_status for cap in result.capabilities} == {"present-unconfirmed"}
    for cap in result.capabilities:
        gap = cap.gaps[0]
        assert "技术骨架" in gap and "present-unconfirmed" in gap
        assert "无提交" not in gap and "无测试" not in gap
        assert cap.roadmap_seeded is False


def test_empty_baseline_takes_precedence_over_roadmap_flag_on_technical_only(monkeypatch, tmp_path) -> None:
    """ontology_roadmap_seeding=true 也不得把技术骨架基线上的本体能力记成 missing。"""
    ontology = tmp_path / "ontology.yaml"
    ontology.write_text(yaml.safe_dump(ONT, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(recon, "ontology_path_for_project", lambda project: ontology)
    cm = {
        "project": "demo",
        "source_path": str(tmp_path),
        "commit_sha": "unknown",
        "scan_coverage": _coverage(tmp_path, 3),
        "spec_capabilities": [],
        "matrix_rows": [],
        "ontology_roadmap_seeding": True,
    }
    result = reconcile(cm, {"features": [], "requirements": []})
    assert {cap.reconciled_status for cap in result.capabilities} == {"present-unconfirmed"}


def test_render_wording_distinguishes_technical_only_from_skeleton(tmp_path) -> None:
    technical = _coverage(tmp_path, 3)
    _, note = render._baseline_notes(None, str(tmp_path), technical)
    assert "技术骨架" in note and "无提交" not in note and "无测试" not in note
    _, skeleton_note = render._baseline_notes(None, str(tmp_path), SKELETON_COVERAGE)
    assert "无提交" in skeleton_note  # 零提交骨架仓的既有措辞不变
    assert "技术骨架" in render._planning_changes_reason(technical)
    assert render._planning_changes_reason(SKELETON_COVERAGE) == render._PLANNING_CHANGES_REASON


TECHNICAL_SCOPES = ("client-app-shell", "database-isolation", "service-health")


def _archive_evidence() -> tuple[ArchiveEvidence, ...]:
    return (
        ArchiveEvidence(
            change_id="add-technical-foundation",
            archive_date="2026-11-23",
            new_capabilities=(*TECHNICAL_SCOPES, "some-business-scope"),
            modified_capabilities=(),
            tasks_completed=3,
            tasks_total=3,
            short_description="技术骨架",
            archive_path="/nowhere/openspec/changes/archive/2026-11-23-add-technical-foundation",
        ),
    )


def test_apply_archive_evidence_skips_excluded_capabilities() -> None:
    by_id: dict = {}
    apply_archive_evidence(by_id, _archive_evidence())
    assert set(by_id) == {*TECHNICAL_SCOPES, "some-business-scope"}  # 默认行为不变

    by_id = {}
    apply_archive_evidence(by_id, _archive_evidence(), excluded_capabilities=frozenset(TECHNICAL_SCOPES))
    assert set(by_id) == {"some-business-scope"}


def test_reconcile_does_not_reinsert_excluded_scopes_via_archive_evidence(monkeypatch, tmp_path) -> None:
    ontology = tmp_path / "ontology.yaml"
    ontology.write_text(yaml.safe_dump(ONT, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(recon, "ontology_path_for_project", lambda project: ontology)
    monkeypatch.setattr(recon, "load_archive_evidence", lambda root: _archive_evidence())

    def run(excluded: list[str]) -> dict:
        cm = {
            "project": "demo",
            "source_path": str(tmp_path),
            "commit_sha": "unknown",
            "scan_coverage": _coverage(tmp_path, 3),
            "spec_capabilities": [],
            "matrix_rows": [],
            "excluded_spec_scopes": excluded,
        }
        return {cap.id: cap.reconciled_status for cap in reconcile(cm, {"features": [], "requirements": []}).capabilities}

    without_flag = run([])
    assert {scope for scope in TECHNICAL_SCOPES if without_flag.get(scope) == "missing"} == set(TECHNICAL_SCOPES)

    with_flag = run(list(TECHNICAL_SCOPES))
    assert not (set(TECHNICAL_SCOPES) & set(with_flag))
    # 未被排除的业务 scope 仍按既有行为保留归档证据条目（archive-only → missing）
    assert with_flag == {
        "purchase-order-management": "present-unconfirmed",
        "goods-receipt-management": "present-unconfirmed",
        "some-business-scope": "missing",
    }
    assert all(status == "missing" for status in without_flag.values() if status != "present-unconfirmed")
