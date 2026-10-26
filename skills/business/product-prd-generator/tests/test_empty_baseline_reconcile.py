"""Regression tests for the 2026-10-26 lnkcard empty-baseline incident.

Covers:
1. Generic product-ontology capability extraction (modules -> sub_functions
   -> capabilities, dict or list shapes) — the lnkcard 26 capabilities must
   reach reconcile/render statistics instead of collapsing to 0.
2. Empty code baseline (skeleton repo, zero commits, no specs) must render as
   "仓库骨架存在、无提交/无业务代码/无测试、代码基线未建立/未扫描" with
   present-unconfirmed + scan coverage empty-baseline semantics — NOT
   "存在未提交修改", NOT all-missing, NOT empty-set-as-complete.
3. Owner-decision inputs (00-owner-decisions.md) classify as
   source_type=owner-decisions and boost priority; legacy NN-legacy-*.md
   files classify as legacy-material (source path retained).
"""

from __future__ import annotations

from pathlib import Path

from product_prd_generator import reconcile as recon
from product_prd_generator import render
from product_prd_generator.doc_map import _classify_source_type
from product_prd_generator.reconcile import (
    CapabilityStatus,
    _calculate_priority,
    _iter_ontology_capabilities,
    _is_empty_code_baseline,
    reconcile,
)

ONT_INPUT = {
    "modules": {
        "card-account": {
            "name": "卡账户",
            "sub_functions": {
                "stored-value-topup": {
                    "name": "储值充值",
                    "capabilities": ["card-account-topup"],
                    "terms": ["储值", "充值"],
                },
                "online-consumption": {
                    "name": "在线消费",
                    "capabilities": ["card-online-consumption"],
                    "terms": ["消费"],
                },
            },
        },
        "card-trade": {
            "name": "卡交易",
            "sub_functions": {
                "refund-reversal": {
                    "name": "退款与冲正",
                    "capabilities": [
                        "card-original-trade-refund",
                        "card-trade-reversal",
                    ],
                    "terms": ["退款", "冲正"],
                },
            },
        },
    }
}

ONT_LIST_SHAPE = {
    "modules": [
        {
            "name": "卡账户",
            "sub_functions": [
                {
                    "name": "掉单恢复",
                    "capabilities": [{"id": "card-lost-order-recovery", "name": "掉单恢复"}],
                }
            ],
        }
    ]
}

EMPTY_BASELINE_COVERAGE = {
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

POPULATED_COVERAGE = {
    "scanners": {"specs": {"status": "complete", "artifact_count": 3, "limitations": []}}
}


def test_iter_ontology_capabilities_dict_shape() -> None:
    caps = _iter_ontology_capabilities(ONT_INPUT)
    ids = {cap_id for cap_id, _ in caps}
    assert ids == {
        "card-account-topup",
        "card-online-consumption",
        "card-original-trade-refund",
        "card-trade-reversal",
    }
    names = {cap_id: name for cap_id, name in caps}
    assert names["card-account-topup"] == "储值充值"


def test_iter_ontology_capabilities_list_shape() -> None:
    caps = _iter_ontology_capabilities(ONT_LIST_SHAPE)
    assert caps == (("card-lost-order-recovery", "掉单恢复"),)


def test_is_empty_code_baseline() -> None:
    assert _is_empty_code_baseline(EMPTY_BASELINE_COVERAGE) is True
    assert _is_empty_code_baseline(POPULATED_COVERAGE) is False
    assert _is_empty_code_baseline(None) is False


def _patch_ontology(monkeypatch, tmp_path: Path, data: dict) -> Path:
    ontology = tmp_path / "ontology.yaml"
    import yaml

    ontology.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    monkeypatch.setattr(recon, "ontology_path_for_project", lambda project: ontology)
    return ontology


ONT_WITH_COVERAGE = {
    **ONT_INPUT,
    "coverage": {
        # 匹配合成 spec scope：full / partial / 未知 id 各一
        "card-topup-scope": {
            "change": "add-card-topup",
            "commit": "abc123",
            "capabilities": [
                {"id": "card-account-topup", "coverage": "full"},
                {"id": "card-online-consumption", "coverage": "partial", "note": "仅支持在线余额消费，积分消费未实现"},
                {"id": "capability-not-in-ontology", "coverage": "full"},
            ],
        },
        # 反例：scope 不在 spec_capabilities 中，整组不得生效
        "archived-but-unscanned-scope": {
            "change": "add-old-refund",
            "commit": "def456",
            "capabilities": [
                {"id": "card-original-trade-refund", "coverage": "full"},
            ],
        },
    },
}


def test_reconcile_seeds_ontology_capabilities_on_empty_baseline(monkeypatch, tmp_path) -> None:
    _patch_ontology(monkeypatch, tmp_path, ONT_INPUT)
    # source_path 必须指向隔离 tmp_path：reconcile 会读 <source_path>/openspec/
    # changes/archive/ 的归档证据——真实 /opt/code/lnkcard 在 2026-10-26
    # Change A/B 归档后不再是空基线，会污染本合成用例（4→8 capability）。
    code_map = {
        "project": "lnkcard",
        "source_path": str(tmp_path),
        "commit_sha": "unknown",
        "scan_coverage": EMPTY_BASELINE_COVERAGE,
        "spec_capabilities": [],
        "matrix_rows": [],
    }
    doc_map = {"features": [], "requirements": []}

    result = reconcile(code_map, doc_map)

    assert len(result.capabilities) == 4
    by_status = {cap.reconciled_status for cap in result.capabilities}
    assert by_status == {"present-unconfirmed"}
    for cap in result.capabilities:
        assert cap.confidence == "low"
        assert "empty-baseline" in cap.gaps[0]
        assert "present-unconfirmed" in cap.gaps[0]


def test_reconcile_does_not_seed_when_baseline_populated(monkeypatch, tmp_path) -> None:
    _patch_ontology(monkeypatch, tmp_path, ONT_INPUT)
    code_map = {
        "project": "lnkcard",
        "source_path": "/opt/code/lnkcre",
        "commit_sha": "abc123",
        "scan_coverage": POPULATED_COVERAGE,
        "spec_capabilities": [],
        "matrix_rows": [],
    }
    result = reconcile(code_map, {"features": [], "requirements": []})
    # 有真实基线的产品保持 spec/matrix 驱动流程，不注入本体目标能力
    assert all(cap.reconciled_status != "present-unconfirmed" for cap in result.capabilities)


def test_reconcile_roadmap_seeding_on_populated_baseline(monkeypatch, tmp_path) -> None:
    """populated 基线 + 产品级开关：本体未命中能力播种为 missing roadmap 项。"""
    _patch_ontology(monkeypatch, tmp_path, ONT_INPUT)
    code_map = {
        "project": "lnkcard",
        "source_path": str(tmp_path),
        "commit_sha": "abc123",
        "scan_coverage": POPULATED_COVERAGE,
        "ontology_roadmap_seeding": True,
        "spec_capabilities": [],
        "matrix_rows": [],
    }
    result = reconcile(code_map, {"features": [], "requirements": []})

    assert len(result.capabilities) == 4
    for cap in result.capabilities:
        assert cap.reconciled_status == "missing"
        assert cap.code_status == "missing"
        assert cap.doc_status == "existing"
        assert cap.confidence == "low"
        assert any("roadmap" in g for g in cap.gaps)
        assert any(e.kind == "doc" and e.ref.startswith("ontology:") for e in cap.evidence)


def test_reconcile_populated_without_flag_still_does_not_seed(monkeypatch, tmp_path) -> None:
    """populated 基线 + 无开关：不播种（回归保护，行为与 does_not_seed 一致）。"""
    _patch_ontology(monkeypatch, tmp_path, ONT_INPUT)
    code_map = {
        "project": "lnkcard",
        "source_path": str(tmp_path),
        "commit_sha": "abc123",
        "scan_coverage": POPULATED_COVERAGE,
        "ontology_roadmap_seeding": False,
        "spec_capabilities": [],
        "matrix_rows": [],
    }
    result = reconcile(code_map, {"features": [], "requirements": []})
    assert len(result.capabilities) == 0


def test_reconcile_json_keeps_status() -> None:
    payload = recon.to_json(recon.ReconcileResult(
        project="lnkcard",
        capabilities=(),
        scan_coverage=EMPTY_BASELINE_COVERAGE,
    ))
    assert payload["scan_coverage"] == EMPTY_BASELINE_COVERAGE


def test_render_project_context_shows_present_unconfirmed() -> None:
    from collections import Counter

    stats = Counter({"present-unconfirmed": 26})
    text = render._render_project_context("lnkcard", stats, "/opt/code/lnkcard", "", "")
    assert "present-unconfirmed 26" in text
    assert "目标能力，代码基线未建立" in text


def test_baseline_notes_empty_skeleton_repo(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "lnkcard"
    repo.mkdir()
    (repo / "openspec").mkdir()
    doc_map = {"features": [{"source_type": "owner-decisions"}]}
    sources, note = render._baseline_notes(doc_map, str(repo), EMPTY_BASELINE_COVERAGE)
    assert "owner 产品决策" in sources
    assert "存在未提交修改" not in note
    for token in ("仓库骨架存在", "无提交", "无业务代码", "无测试", "代码基线未建立", "empty-baseline", "present-unconfirmed"):
        assert token in note, token


def test_baseline_notes_zero_commit_repo_even_without_coverage(monkeypatch, tmp_path) -> None:
    import subprocess

    repo = tmp_path / "lnkcard-git"
    repo.mkdir()
    subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
    (repo / "openspec.txt").write_text("skeleton\n", encoding="utf-8")  # untracked-only repo
    _, note = render._baseline_notes(None, str(repo), None)
    assert "存在未提交修改" not in note
    assert "无提交" in note


def test_baseline_notes_dirty_repo_unchanged(monkeypatch, tmp_path) -> None:
    import subprocess

    repo = tmp_path / "normal-repo"
    repo.mkdir()
    subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
    subprocess.run(["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "--allow-empty", "-m", "init", "-q"], check=True)
    (repo / "a.txt").write_text("x", encoding="utf-8")
    _, note = render._baseline_notes(None, str(repo), POPULATED_COVERAGE)
    assert "存在未提交修改" in note


def test_owner_and_legacy_source_classification() -> None:
    assert _classify_source_type(Path("00-owner-decisions.md")) == "owner-decisions"
    assert _classify_source_type(Path("01-legacy-requirement-spec.md")) == "legacy-material"
    assert _classify_source_type(Path("04-legacy-settlement-design.md")) == "legacy-material"
    # 目录规则不被文件名规则破坏
    assert _classify_source_type(Path("01-customer-requirements/x/00-owner-decisions.md")) == "customer-requirements"
    assert _classify_source_type(Path("02-competitors/hd/01-legacy-x.md")) == "competitor"


def test_calculate_priority_owner_decision_boost() -> None:
    base = _calculate_priority(0, "unmatched", "", "范围")
    owner = _calculate_priority(0, "unmatched", "", "范围", source_type="owner-decisions")
    assert owner == "高"
    assert base != "高" or owner == "高"


def test_status_enum_untouched() -> None:
    # 四值状态枚举保持稳定（新增的 present-unconfirmed 只经由字符串流通，
    # 不改 CapabilityStatus，避免波及既有产品链路）
    assert {s.value for s in CapabilityStatus} == {
        "existing", "partial", "missing", "explicitly-not-do"
    }


def test_roadmap_seeded_items_aggregated_in_prd_body(monkeypatch, tmp_path) -> None:
    """roadmap 播种项在 PRD 正文聚合渲染：版本规划/风险节不逐条内联 26 项明细。"""
    _patch_ontology(monkeypatch, tmp_path, ONT_INPUT)
    code_map = {
        "project": "lnkcard",
        "source_path": str(tmp_path),
        "commit_sha": "abc123",
        "scan_coverage": POPULATED_COVERAGE,
        "ontology_roadmap_seeding": True,
        "spec_capabilities": [],
        "matrix_rows": [],
    }
    result = reconcile(code_map, {"features": [], "requirements": []})
    caps = recon.to_json(result)["capabilities"]

    plan = render._render_version_plan(caps)
    # 聚合行存在，且不逐条列出 roadmap 项 ID
    assert "roadmap 目标能力 4 项" in plan
    for cap in result.capabilities:
        assert cap.id not in plan
        assert cap.name not in plan

    risks = render._render_risks(caps)
    # 风险节：roadmap 项合并为一条聚合风险，无逐条条目
    assert "- 4 项本体目标能力未实施（roadmap）" in risks
    for cap in result.capabilities:
        assert f"**{cap.name}**" not in risks

    # 客户需求未覆盖节：roadmap 项仅聚合行，不逐条内联 cap id
    unmatched = render._render_unmatched_requirements(caps)
    assert "- roadmap 目标能力 4 项" in unmatched
    for cap in result.capabilities:
        assert cap.id not in unmatched
        assert f"**{cap.name}**" not in unmatched

    # 版本规划节：existing 项不进任何 bucket，节首聚合已交付行
    existing_caps = [
        {
            "id": "test-gates", "name": "test gates", "reconciled_status": "existing",
            "confidence": "high", "gaps": ["spec/archive evidence does not directly verify current runtime or tests"],
        }
    ]
    plan_with_existing = render._render_version_plan(caps + existing_caps)
    assert "已交付（existing）1 项，不再列入规划" in plan_with_existing
    assert "test-gates" not in plan_with_existing
    assert "test gates" not in plan_with_existing

    # 播种项带 roadmap_seeded 标记，可被下游区分
    assert all(c["roadmap_seeded"] for c in caps)


def test_reconcile_applies_ontology_coverage_ledger(monkeypatch, tmp_path) -> None:
    """结构化 coverage 台账：扫描到的 scope 把 roadmap 播种项升级为已交付/部分交付。"""
    _patch_ontology(monkeypatch, tmp_path, ONT_WITH_COVERAGE)
    code_map = {
        "project": "lnkcard",
        "source_path": str(tmp_path),
        "commit_sha": "abc123",
        "scan_coverage": POPULATED_COVERAGE,
        "ontology_roadmap_seeding": True,
        "spec_capabilities": [
            {"id": "card-topup-scope", "status": "existing", "evidence": []},
        ],
        "matrix_rows": [],
    }
    result = reconcile(code_map, {"features": [], "requirements": []})
    by_id = {cap.id: cap for cap in result.capabilities}

    # full：existing / high / 无 gap / spec ref / 不再是 roadmap 项
    full = by_id["card-account-topup"]
    assert full.reconciled_status == "existing"
    assert full.code_status == "existing"
    assert full.confidence == "high"
    assert full.gaps == ()
    assert full.roadmap_seeded is False
    assert any(
        e.kind == "spec" and e.ref == "spec:card-topup-scope/spec.md" for e in full.evidence
    )

    # partial：partial / 单条含 note 的 gap / spec ref
    partial = by_id["card-online-consumption"]
    assert partial.reconciled_status == "partial"
    assert partial.code_status == "partial"
    assert partial.gaps == ("仅支持在线余额消费，积分消费未实现",)
    assert partial.roadmap_seeded is False
    assert any(
        e.kind == "spec" and e.ref == "spec:card-topup-scope/spec.md" for e in partial.evidence
    )

    # 未知 id：不产生新条目（总数 = 本体 4 项 + spec scope 1 项）
    assert "capability-not-in-ontology" not in by_id
    assert len(result.capabilities) == 5

    # 反例：scope 不在 spec_capabilities → 状态保持 roadmap missing 不变
    untouched = by_id["card-original-trade-refund"]
    assert untouched.reconciled_status == "missing"
    assert untouched.roadmap_seeded is True
    assert any("roadmap" in g for g in untouched.gaps)


def test_reconcile_coverage_ledger_noop_without_key(monkeypatch, tmp_path) -> None:
    """ontology 无 coverage 键 → 无操作，既有 roadmap 播种行为不变。"""
    _patch_ontology(monkeypatch, tmp_path, ONT_INPUT)
    code_map = {
        "project": "lnkcard",
        "source_path": str(tmp_path),
        "commit_sha": "abc123",
        "scan_coverage": POPULATED_COVERAGE,
        "ontology_roadmap_seeding": True,
        "spec_capabilities": [
            {"id": "card-topup-scope", "status": "existing", "evidence": []},
        ],
        "matrix_rows": [],
    }
    result = reconcile(code_map, {"features": [], "requirements": []})
    # 无 coverage 键 → 台账无操作：本体 4 项仍全部 roadmap missing，spec scope 1 项原样
    assert len(result.capabilities) == 5
    for cap in result.capabilities:
        if cap.roadmap_seeded:
            assert cap.reconciled_status == "missing"
            assert any("roadmap" in g for g in cap.gaps)
