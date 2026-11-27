from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ReviewItem:
    priority: str
    title: str
    problem: str
    reason: str
    evidence: str
    suggestion: str


@dataclass(frozen=True, slots=True)
class ReviewReport:
    project: str
    items: tuple[ReviewItem, ...]


def _load_json(path: str) -> Mapping[str, object]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, Mapping) else {}


def _join_evidence(capability: Mapping[str, object]) -> str:
    refs: list[str] = []
    evidence = capability.get("evidence", [])
    if isinstance(evidence, list):
        for item in evidence[:3]:
            if isinstance(item, Mapping):
                kind = str(item.get("kind", ""))
                ref = str(item.get("ref", ""))
                if kind and ref:
                    refs.append(f"{kind}:{ref}")
    return "；".join(refs) if refs else "（暂无）"


def _priority_for(capability: Mapping[str, object]) -> str:
    confidence = str(capability.get("confidence", "low"))
    status = str(capability.get("reconciled_status", "missing"))
    if confidence == "low":
        return "高优先级"
    if status == "explicitly-not-do":
        return "中优先级"
    if status == "partial":
        return "中优先级"
    return "低优先级"


_LNKRETAIL_PLANNING_PENDING_ITEMS: tuple[ReviewItem, ...] = (
    ReviewItem(
        priority="高优先级",
        title="产品待决策项 R-03/R-04/R-08/R-11",
        problem="lnkretail 规划阶段产品待决策项（R-03/R-04/R-08/R-11）尚未经 owner 逐项确认",
        reason="status=present-unconfirmed（目标能力，代码基线未建立），规划型 PRD 无已授权客户需求输入",
        evidence="（暂无）",
        suggestion="逐项确认 R-03/R-04/R-08/R-11 后回写 owner-decisions 与版本规划",
    ),
    ReviewItem(
        priority="高优先级",
        title="跨产品契约：POS↔lnkcard",
        problem="POS 与 lnkcard（独立预付费卡系统）之间的 tender 对接契约未确认（D-007：lnkretail 不作必经中转层）",
        reason="status=present-unconfirmed，跨产品契约无单侧代码基线可佐证",
        evidence="（暂无）",
        suggestion="与 lnkcard 侧对齐 POS↔lnkcard 契约边界后回写词表",
    ),
    ReviewItem(
        priority="高优先级",
        title="跨产品契约：POS↔lnkretail",
        problem="POS 与 lnkretail 之间的对接契约（接口/职责边界）未确认",
        reason="status=present-unconfirmed，跨产品契约无单侧代码基线可佐证",
        evidence="（暂无）",
        suggestion="确认 POS↔lnkretail 契约范围后纳入版本规划",
    ),
    ReviewItem(
        priority="中优先级",
        title="业态/财务专项：便利店/卖菜/财务",
        problem="便利店、卖菜业态专项与财务专项能力范围未确认",
        reason="status=present-unconfirmed，业态/财务专项为目标能力，无代码基线佐证",
        evidence="（暂无）",
        suggestion="按业态/财务逐项确认能力范围后回写词表",
    ),
)


def _build_item(capability: Mapping[str, object]) -> ReviewItem:
    name = str(capability.get("name", capability.get("id", "")))
    gaps = capability.get("gaps", [])
    gap_text = "; ".join(str(item) for item in gaps) if isinstance(gaps, list) else ""
    status = str(capability.get("reconciled_status", "missing"))
    confidence = str(capability.get("confidence", "low"))
    problem = gap_text or f"{name} 需要人工确认"
    reason = f"status={status}, confidence={confidence}"
    suggestion = "确认后回写词表 / 版本规划"
    if status == "partial":
        suggestion = "补齐缺口后纳入版本"
    elif status == "explicitly-not-do":
        suggestion = "确认是否保留为排除项"
    elif confidence == "low":
        suggestion = "先人工确认再入主清单"
    return ReviewItem(
        priority=_priority_for(capability),
        title=name,
        problem=problem,
        reason=reason,
        evidence=_join_evidence(capability),
        suggestion=suggestion,
    )


def build_report(reconcile: Mapping[str, object]) -> ReviewReport:
    project = str(reconcile.get("project", "商管系统"))
    items: list[ReviewItem] = []
    capabilities = reconcile.get("capabilities", [])
    if isinstance(capabilities, list):
        for capability in capabilities:
            if not isinstance(capability, Mapping):
                continue
            confidence = str(capability.get("confidence", "low"))
            gaps = capability.get("gaps", [])
            has_gaps = isinstance(gaps, list) and len(gaps) > 0
            status = str(capability.get("reconciled_status", "missing"))
            provenance = str(capability.get("evidence_provenance", ""))
            if provenance in {"spec-only", "archive-only", "archive-and-spec-only"}:
                items.append(_build_item(capability))
                continue
            if confidence == "low" or status == "explicitly-not-do" or (status == "partial" and has_gaps):
                items.append(_build_item(capability))
                continue
            evidence = capability.get("evidence", [])
            if isinstance(evidence, list):
                kinds = {
                    str(entry.get("kind", ""))
                    for entry in evidence
                    if isinstance(entry, Mapping)
                } - {""}
                if kinds and kinds <= {"openspec-archive", "code"}:
                    item = _build_item(capability)
                    items.append(
                        replace(
                            item,
                            problem=(
                                f"{item.title} 仅有 {'/'.join(sorted(kinds))} 单一证据来源，"
                                "建议人工复核实现完整性（无现行 spec 佐证）"
                            ),
                        )
                    )
    statuses = {
        str(capability.get("reconciled_status", ""))
        for capability in capabilities
        if isinstance(capability, Mapping)
    }
    # lnkretail 规划型基线（2026-11-21）：能力全为 present-unconfirmed 时，
    # capability 维度不产生任何 item，会导致 pending-items.md 各优先级均无项——
    # 与 render.py 高优先级清单的规划型兜底文案（指向 pending-items.md）不一致。
    # 此处补齐规划待确认项（与 render._render_priority_review 的列举保持一致）。
    if project == "lnkretail" and capabilities and statuses == {"present-unconfirmed"}:
        items.extend(_LNKRETAIL_PLANNING_PENDING_ITEMS)
    return ReviewReport(project=project, items=tuple(items))


def render_report(report: ReviewReport) -> str:
    grouped: dict[str, list[ReviewItem]] = {"高优先级": [], "中优先级": [], "低优先级": []}
    for item in report.items:
        grouped.setdefault(item.priority, []).append(item)

    lines = ["# 待确认项", ""]
    for priority in ("高优先级", "中优先级", "低优先级"):
        lines.append(f"## {priority}")
        items = grouped.get(priority, [])
        if not items:
            lines.append("- （无）")
            lines.append("")
            continue
        for item in items:
            lines.extend(
                [
                    f"- [ ] 项目：{report.project}",
                    f"  - 问题：{item.problem}",
                    f"  - 理由：{item.reason}",
                    f"  - 证据：{item.evidence}",
                    f"  - 建议：{item.suggestion}",
                ]
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render review/pending-items.md from reconciliation results")
    parser.add_argument("--reconcile", required=True)
    parser.add_argument("--output-dir", default="review")
    args = parser.parse_args()

    report = build_report(_load_json(args.reconcile))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "pending-items.md").write_text(render_report(report), encoding="utf-8")
    print(f"rendered review to {output_dir / 'pending-items.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
