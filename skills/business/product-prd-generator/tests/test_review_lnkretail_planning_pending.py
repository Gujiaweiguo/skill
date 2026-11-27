"""lnkretail 规划型基线的 pending-items 兜底（2026-11-21）。

背景：render.py 高优先级清单的规划型兜底文案声称"逐项清单见
review/pending-items.md"，但当 reconcile 能力全为 present-unconfirmed 时
review.build_report 不产生任何 item，pending-items.md 各优先级均无项。
回归：project=lnkretail 且能力全 present-unconfirmed 时，必须补齐
产品待决策项（R-03/R-04/R-08/R-11）、跨产品契约（POS↔lnkcard、
POS↔lnkretail）、业态/财务专项（便利店/卖菜/财务）待确认项。
"""

from __future__ import annotations

from product_prd_generator import review
from product_prd_generator.review_format import ReviewBriefInput, render_review_brief


def _capability(name: str, status: str = "present-unconfirmed") -> dict[str, object]:
    return {
        "id": name,
        "name": name,
        "reconciled_status": status,
        "confidence": "medium",
        "gaps": [],
        "evidence": [],
    }


def test_lnkretail_all_present_unconfirmed_appends_planning_pending_items() -> None:
    reconcile = {
        "project": "lnkretail",
        "capabilities": [_capability("pos-checkout"), _capability("inventory")],
    }
    report = review.build_report(reconcile)
    titles = [item.title for item in report.items]
    assert "产品待决策项 R-03/R-04/R-08/R-11" in titles
    assert any("POS↔lnkcard" in title for title in titles)
    assert any("POS↔lnkretail" in title for title in titles)
    assert any("便利店" in title and "财务" in title for title in titles)
    # 渲染后各级不得全为空
    text = review.render_report(report)
    assert "## 高优先级" in text
    assert "（无）" not in text.split("## 高优先级", 1)[1].split("## 中优先级", 1)[0]


def test_other_project_all_present_unconfirmed_no_planning_items() -> None:
    reconcile = {
        "project": "lnkcard",
        "capabilities": [_capability("card-issue")],
    }
    report = review.build_report(reconcile)
    titles = [item.title for item in report.items]
    assert "产品待决策项 R-03/R-04/R-08/R-11" not in titles


def test_lnkretail_mixed_statuses_no_planning_items() -> None:
    reconcile = {
        "project": "lnkretail",
        "capabilities": [
            _capability("pos-checkout", status="existing"),
            _capability("inventory"),
        ],
    }
    report = review.build_report(reconcile)
    titles = [item.title for item in report.items]
    assert "产品待决策项 R-03/R-04/R-08/R-11" not in titles


def test_lnkretail_empty_capabilities_no_planning_items() -> None:
    report = review.build_report({"project": "lnkretail", "capabilities": []})
    assert report.items == ()


def test_lnkretail_review_brief_labels_historical_reference_not_requirements() -> None:
    text = render_review_brief(ReviewBriefInput(
        project="lnkretail",
        status_stats={"present-unconfirmed": 32},
        requirement_count=1065,
        tables_by_module={},
        unmatched_table_count=0,
    ))
    assert "历史系统参考资料，不构成已授权客户需求" in text
    assert "历史参考条目（非已授权需求）" in text


def test_other_project_review_brief_keeps_existing_requirement_label() -> None:
    text = render_review_brief(ReviewBriefInput(
        project="lnkcard",
        status_stats={"present-unconfirmed": 1},
        requirement_count=1,
        tables_by_module={},
        unmatched_table_count=0,
    ))
    assert "| 需求条目 | 1 |" in text
