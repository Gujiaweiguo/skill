"""规划型产品的待确认项只给指针，不在 skill 侧按产品硬编码（2026-11-27 泛化）。

背景：2026-11-21 把 lnkretail 的四条产品待确认项硬编码进 review.py，review 简报的
规划型判定也只认 lnkretail。lnkmember 首版生成（2026-11-27）把 LnkRetail 的条目原样
带进自己的 review 清单；而硬编码副本相对产品台账早已过时（R-03/R-04/R-08/R-11 均已
裁定）。泛化后：产品级待确认项只留在产品侧 ``30-products/<pid>/reconciliation/`` 台账，
skill 对任何产品都只给指针；规划型判定与产品无关，由 render 统一算好传入。
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from product_prd_generator import _paths, render, review
from product_prd_generator.review_format import ReviewBriefInput, render_review_brief

_POINTER_TITLE = "产品级待确认项：见产品 reconciliation 台账"
_LNKRETAIL_ONLY = ("R-03", "R-04", "R-08", "R-11", "POS↔lnkcard", "POS↔lnkretail", "便利店", "卖菜")


def _capability(name: str, status: str = "present-unconfirmed") -> dict[str, object]:
    return {
        "id": name,
        "name": name,
        "reconciled_status": status,
        "confidence": "medium",
        "gaps": [],
        "evidence": [],
    }


def _reconcile(project: str, *capabilities: dict[str, object]) -> dict[str, object]:
    return {"project": project, "capabilities": list(capabilities)}


@pytest.mark.parametrize("project", ["lnkretail", "lnkmember", "lnkcard"])
def test_any_product_all_present_unconfirmed_gets_one_pointer_item(project: str) -> None:
    """能力全为 present-unconfirmed → 恰好一条指针；任何产品都不再出现 lnkretail 专属条目。"""
    report = review.build_report(_reconcile(project, _capability("a"), _capability("b")))
    assert [item.title for item in report.items] == [_POINTER_TITLE]
    assert report.items[0].priority == "高优先级"
    assert "present-unconfirmed" in report.items[0].problem
    text = review.render_report(report)
    for token in _LNKRETAIL_ONLY:
        assert token not in text
    high = text.split("## 高优先级", 1)[1].split("## 中优先级", 1)[0]
    assert "（无）" not in high


def test_pointer_item_names_the_product_ledger_when_it_resolves(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _paths, "reconciliation_pointer_for_project", lambda project: f"30-products/{project}/reconciliation/"
    )
    item = review.build_report(_reconcile("lnkmember", _capability("a"))).items[0]
    assert "30-products/lnkmember/reconciliation/" in item.problem
    assert item.evidence == "30-products/lnkmember/reconciliation/"


def test_pointer_item_omits_the_path_when_the_ledger_does_not_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_paths, "reconciliation_pointer_for_project", lambda project: "")
    item = review.build_report(_reconcile("lnkmember", _capability("a"))).items[0]
    assert "30-products/" not in item.problem
    assert "由产品侧 reconciliation 台账维护" in item.problem
    assert item.evidence == "（暂无）"


def test_mixed_or_empty_capabilities_get_no_pointer_item() -> None:
    mixed = review.build_report(
        _reconcile("lnkmember", _capability("a", status="existing"), _capability("b"))
    )
    assert _POINTER_TITLE not in [item.title for item in mixed.items]
    assert review.build_report({"project": "lnkmember", "capabilities": []}).items == ()


def test_reconciliation_pointer_is_written_only_when_the_directory_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "company.yaml").write_text("id: demo-company\n", encoding="utf-8")
    monkeypatch.setenv("COMPANY_BASE", str(tmp_path))
    monkeypatch.delenv("LANLNK_BASE", raising=False)
    docs_root = tmp_path / "30-products" / "demo"
    monkeypatch.setattr(_paths, "resolve_product_paths", lambda project: SimpleNamespace(docs_root=docs_root))

    assert _paths.reconciliation_pointer_for_project("demo") == ""
    (docs_root / "reconciliation").mkdir(parents=True)
    assert _paths.reconciliation_pointer_for_project("demo") == "30-products/demo/reconciliation/"


def test_reconciliation_pointer_is_empty_when_unresolvable(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(project: str) -> None:
        raise SystemExit("COMPANY_BASE 未设置")

    monkeypatch.setattr(_paths, "resolve_product_paths", _boom)
    assert _paths.reconciliation_pointer_for_project("demo") == ""


def test_review_brief_planning_flag_is_passed_in_not_guessed_from_project() -> None:
    common: dict[str, object] = {
        "status_stats": {"present-unconfirmed": 55},
        "requirement_count": 0,
        "tables_by_module": {},
        "unmatched_table_count": 0,
    }
    planning_text = render_review_brief(ReviewBriefInput(project="lnkmember", planning=True, **common))
    assert "历史系统参考资料，不构成已授权客户需求" in planning_text
    assert "55 项能力是目标蓝图" in planning_text
    assert "历史参考条目（非已授权需求）" in planning_text
    # 不传标志：即使 lnkretail 且全部 present-unconfirmed，简报也不再自行判为规划型
    plain = render_review_brief(ReviewBriefInput(project="lnkretail", **common))
    assert "历史系统参考资料" not in plain
    assert "| 需求条目 | 0 |" in plain


def test_priority_review_planning_fallback_is_product_neutral() -> None:
    with_pointer = render._render_priority_review(
        [], planning=True, pending_pointer="30-products/lnkmember/reconciliation/"
    )
    assert "review/pending-items.md" in with_pointer
    assert "30-products/lnkmember/reconciliation/" in with_pointer
    without_pointer = render._render_priority_review([], planning=True)
    assert "review/pending-items.md" in without_pointer
    assert "open 项台账" not in without_pointer
    for text in (with_pointer, without_pointer):
        for token in _LNKRETAIL_ONLY:
            assert token not in text
    assert render._render_priority_review([], planning=False) == (
        "# 高优先级需求 review 清单\n\n当前无高优先级需求。\n"
    )
