from __future__ import annotations

from typing import TypedDict


class Evidence(TypedDict, total=False):
    kind: str
    ref: str


class Capability(TypedDict, total=False):
    id: str
    name: str
    reconciled_status: str
    confidence: str
    evidence: list[Evidence]


def _markdown_cell(value: str) -> str:
    return value.replace("|", "／").replace("\n", " ").strip()


def render_competitor_feature_list(capabilities: list[Capability]) -> str:
    rows: list[tuple[str, str, str, tuple[str, ...], int]] = []
    source_files: set[str] = set()
    for capability in capabilities:
        evidence = tuple(
            item
            for item in capability.get("evidence", [])
            if item.get("ref", "").startswith("02-competitors/")
        )
        if not evidence:
            continue
        sources = tuple(
            sorted(
                {
                    item.get("ref", "")
                    for item in evidence
                    if item.get("kind") == "doc" and item.get("ref")
                }
            )
        )
        source_files.update(sources)
        rows.append(
            (
                capability.get("name", capability.get("id", "")),
                capability.get("reconciled_status", "missing"),
                capability.get("confidence", "low"),
                sources,
                len(evidence),
            )
        )

    lines = [
        "# 竞品功能清单",
        "",
        f"共 {len(rows)} 项归一化能力，来源文件 {len(source_files)} 份。",
        "",
        "| 功能名 | 状态 | 置信度 | 竞品证据数 | 来源文件 |",
        "|---|---|---|---:|---|",
    ]
    for name, status, confidence, sources, evidence_count in sorted(rows):
        source_text = "<br>".join(f"`{_markdown_cell(value)}`" for value in sources) or "—"
        lines.append(
            f"| {_markdown_cell(name)} | {status} | {confidence} | {evidence_count} | {source_text} |"
        )
    return "\n".join(lines) + "\n"
