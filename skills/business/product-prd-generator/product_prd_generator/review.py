from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
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
            if confidence == "low" or status == "explicitly-not-do" or (status == "partial" and has_gaps):
                items.append(_build_item(capability))
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
