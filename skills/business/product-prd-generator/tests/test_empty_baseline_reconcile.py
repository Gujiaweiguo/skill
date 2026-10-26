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
