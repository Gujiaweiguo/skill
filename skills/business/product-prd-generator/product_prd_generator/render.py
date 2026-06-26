from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VERSION_BY_STATUS = {
    "existing": "P3",
    "partial": "P1",
    "missing": "P2",
    "explicitly-not-do": "暂缓",
}


@dataclass(frozen=True, slots=True)
class RenderInputs:
    reconcile: dict[str, Any]  # noqa: ANY_OK
    doc_map: dict[str, Any] | None  # noqa: ANY_OK


def _load_json(path: str) -> dict[str, Any]:  # noqa: ANY_OK
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_inputs(reconcile_path: str, doc_map_path: str | None) -> RenderInputs:
    return RenderInputs(
        reconcile=_load_json(reconcile_path),
        doc_map=_load_json(doc_map_path) if doc_map_path else None,
    )


def _status_stats(capabilities: list[dict[str, Any]]) -> Counter[str]:  # noqa: ANY_OK
    return Counter(cap.get("reconciled_status", "missing") for cap in capabilities)


def _render_header(project: str, stats: Counter[str]) -> str:
    total = sum(stats.values())
    return f"""# {project} 产品 PRD

## 1. 背景

- 项目：{project}
- 来源：客户需求 + 竞品资料 + 当前产品代码基线（/opt/code/mi）
- 能力总数：{total}
- 状态分布：existing {stats.get("existing", 0)} / partial {stats.get("partial", 0)} / missing {stats.get("missing", 0)} / explicitly-not-do {stats.get("explicitly-not-do", 0)}

## 2. 当前产品基线

| 状态 | 数量 |
|---|---|
| existing | {stats.get("existing", 0)} |
| partial | {stats.get("partial", 0)} |
| missing | {stats.get("missing", 0)} |
| explicitly-not-do | {stats.get("explicitly-not-do", 0)} |
"""


def _render_customer_summary(doc_map: dict[str, Any] | None) -> str:  # noqa: ANY_OK
    if not doc_map:
        return "## 3. 客户需求汇总\n\n（待 doc-map 提供 source_type=customer-requirements 的 features 后填充）\n"
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"files": [], "items": []})
    by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)  # noqa: ANY_OK
    for feat in doc_map.get("features", []):
        if feat.get("source_type") == "customer-requirements":
            by_file[feat.get("source_file", "")].append(feat)
    for source_file, feats in sorted(by_file.items()):
        current_module = ""
        for feat in sorted(feats, key=lambda item: (int(item.get("depth", 99)), item.get("heading", ""))):
            term = feat.get("normalized_term", "")
            if not term:
                continue
            depth = int(feat.get("depth", 99))
            if depth == 1 or not current_module:
                current_module = term
                grouped[current_module]["files"].append(source_file)
                continue
            if term not in grouped[current_module]["items"]:
                grouped[current_module]["items"].append(term)
    lines = ["## 3. 客户需求汇总", "", f"共 {len(grouped)} 个模块。", ""]
    for module, payload in grouped.items():
        files = ", ".join(dict.fromkeys(payload["files"]))
        items = payload["items"]
        lines.append(f"### {module}")
        lines.append(f"- 来源：{files}")
        if items:
            lines.append("- 需求：")
            for item in items:
                lines.append(f"  - {item}")
        else:
            lines.append("- 需求：无下级标题，待补充")
        lines.append("")
    if len(grouped) == 0:
        lines.append("- （暂无）")
    return "\n".join(lines) + "\n"


def _render_feature_list(capabilities: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    lines = ["# 功能清单", "", "| 功能名 | 状态 | 置信度 | 证据数 |", "|---|---|---|---|"]
    for cap in capabilities:
        name = cap.get("name", cap.get("id", ""))
        status = cap.get("reconciled_status", "missing")
        confidence = cap.get("confidence", "low")
        evidence_count = len(cap.get("evidence", []))
        lines.append(f"| {name} | {status} | {confidence} | {evidence_count} |")
    return "\n".join(lines) + "\n"


def _render_gap_analysis(capabilities: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    gapped = [cap for cap in capabilities if cap.get("gaps")]
    lines = ["# 差距分析", "", f"共 {len(gapped)} 项存在差距。", ""]
    for cap in gapped:
        name = cap.get("name", cap.get("id", ""))
        status = cap.get("reconciled_status", "missing")
        gaps = "; ".join(cap.get("gaps", []))
        lines.append(f"- **{name}** ({status}): {gaps}")
    return "\n".join(lines) + "\n"


def _render_evidence_table(capabilities: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    lines = ["# 需求证据表", "", "| 功能名 | 证据类型 | 证据引用 |", "|---|---|---|"]
    for cap in capabilities:
        name = cap.get("name", cap.get("id", ""))
        for ev in cap.get("evidence", []):
            lines.append(f"| {name} | {ev.get('kind', '')} | {ev.get('ref', '')} |")
    return "\n".join(lines) + "\n"


def _render_version_plan(capabilities: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    buckets: dict[str, list[str]] = {label: [] for label in ("P0", "P1", "P2", "P3", "暂缓")}
    for cap in capabilities:
        if not cap.get("gaps"):
            continue
        status = cap.get("reconciled_status", "missing")
        version = VERSION_BY_STATUS.get(status, "P2")
        name = cap.get("name", cap.get("id", ""))
        gaps = "; ".join(cap.get("gaps", []))
        buckets[version].append(f"{name}：{gaps}" if gaps else name)
    lines = ["## 6. 版本规划", "", "说明：仅列出存在 gap 的能力；已实现且无 gap 的项不进入版本规划。", ""]
    for label in ("P0", "P1", "P2", "P3", "暂缓"):
        items = buckets[label]
        lines.append(f"### {label}（{len(items)} 项）")
        if items:
            for item in items:
                lines.append(f"- {item}")
        else:
            lines.append("- （无）")
        lines.append("")
    return "\n".join(lines)


def _render_image_refs(capabilities: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    lines = ["## 7. 界面 / 流程参考", ""]
    seen: set[str] = set()
    for cap in capabilities:
        for ev in cap.get("evidence", []):
            if ev.get("kind") == "image":
                ref = ev.get("ref", "")
                if ref and ref not in seen:
                    seen.add(ref)
                    lines.append(f"- {ref}")
    if len(seen) == 0:
        lines.append("- （暂无图片证据，待 raw/ 转换后补充）")
    return "\n".join(lines) + "\n"


def _render_risks(capabilities: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    low_conf = [cap for cap in capabilities if cap.get("confidence") == "low"]
    lines = ["## 8. 风险与待确认项", "", f"低置信度能力：{len(low_conf)} 项", ""]
    for cap in low_conf:
        name = cap.get("name", cap.get("id", ""))
        gaps = "; ".join(cap.get("gaps", []))
        lines.append(f"- **{name}**: {gaps}")
    return "\n".join(lines) + "\n"


def _render_unmatched_requirements(capabilities: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    missing = [cap for cap in capabilities if cap.get("reconciled_status") == "missing"]
    if not missing:
        return "## 5. 客户需求未覆盖\n\n当前所有客户需求均在代码能力范围内有对应。\n"
    missing.sort(key=lambda c: (-len(c.get("evidence", [])), c.get("name", "")))
    lines = [
        "## 5. 客户需求未覆盖",
        "",
        f"共 {len(missing)} 项客户明确提出但当前代码无对应能力的需求：",
        "",
    ]
    for cap in missing:
        name = cap.get("name", cap.get("id", ""))
        evidence = cap.get("evidence", [])
        clients = [e.get("ref", "").replace("customer:", "") for e in evidence if e.get("kind") == "doc"]
        client_str = ", ".join(clients[:4])
        if len(clients) > 4:
            client_str += f" 等 {len(clients)} 个客户"
        lines.append(f"- **{name}** ← {client_str}")
    return "\n".join(lines) + "\n"


def render_prd(inputs: RenderInputs) -> str:
    project = inputs.reconcile.get("project", "商管系统")
    capabilities = inputs.reconcile.get("capabilities", [])
    stats = _status_stats(capabilities)
    parts = [
        _render_header(project, stats),
        _render_customer_summary(inputs.doc_map),
        "## 4. 功能清单",
        "",
        f"共 {len(capabilities)} 项能力，详见 [功能清单.md](功能清单.md)。",
        "",
        _render_unmatched_requirements(capabilities),
        _render_version_plan(capabilities),
        _render_image_refs(capabilities),
        _render_risks(capabilities),
        "## 9. 附录",
        "",
        "- 差距分析详见 [差距分析.md](差距分析.md)",
        "- 证据表详见 [需求证据表.md](需求证据表.md)",
    ]
    return "\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render PRD markdown from capability-reconciliation.json")
    parser.add_argument("--reconcile", required=True)
    parser.add_argument("--doc-map", default="")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    doc_map_path = args.doc_map if args.doc_map else None
    inputs = _load_inputs(args.reconcile, doc_map_path)
    capabilities = inputs.reconcile.get("capabilities", [])

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "产品PRD.md").write_text(render_prd(inputs), encoding="utf-8")
    (output_dir / "功能清单.md").write_text(_render_feature_list(capabilities), encoding="utf-8")
    (output_dir / "差距分析.md").write_text(_render_gap_analysis(capabilities), encoding="utf-8")
    (output_dir / "需求证据表.md").write_text(_render_evidence_table(capabilities), encoding="utf-8")

    print(f"rendered 4 files to {output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
