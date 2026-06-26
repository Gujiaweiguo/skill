from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class WordExportPaths:
    content_package: Path
    docx_path: Path | None


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _yaml_block(data: dict[str, Any]) -> list[str]:
    rendered = yaml.safe_dump(data, allow_unicode=True, sort_keys=False).rstrip()
    return rendered.splitlines()


def _stringify_table(rows: list[list[Any]]) -> list[list[str]]:
    return [[str(cell) for cell in row] for row in rows]


def _frontmatter_lines(reconcile: dict[str, Any], doc_map: dict[str, Any] | None) -> list[str]:
    project = str(reconcile.get("project", "商管系统"))
    today = str(reconcile.get("generated_at", date.today().isoformat()))
    sources = [{"path": reconcile.get("source_code_root", "/opt/code/mi"), "type": "code-baseline"}]
    if doc_map and doc_map.get("source_root"):
        sources.append({"path": doc_map["source_root"], "type": "doc-baseline"})

    frontmatter = {
        "title": f"{project} 产品PRD",
        "project": project,
        "client": project,
        "type": "proposal",
        "template": "proposal",
        "date": today,
        "author": "product-prd-generator",
        "cover": {
            "title": f"{project} 产品PRD",
            "subtitle": "产品需求说明",
            "version": "V1.0",
            "confidential": False,
        },
        "header": {"left": "蓝联科技", "right": f"{project} 产品PRD"},
        "footer": {"left": "机密", "center": "", "right": "第 {page} 页"},
        "toc": {"enabled": True, "max_level": 3, "include_heading": False},
        "sources": sources,
    }

    return ["---", *_yaml_block(frontmatter), "---"]


def _status_stats(capabilities: list[dict[str, Any]]) -> dict[str, int]:
    stats = {"existing": 0, "partial": 0, "missing": 0, "explicitly-not-do": 0}
    for cap in capabilities:
        status = str(cap.get("reconciled_status", "missing"))
        stats[status] = stats.get(status, 0) + 1
    return stats


def _group_customer_requirements(doc_map: dict[str, Any] | None) -> dict[str, dict[str, list[str]]]:
    grouped: dict[str, dict[str, list[str]]] = {}
    if not doc_map:
        return grouped

    by_file: dict[str, list[dict[str, Any]]] = {}
    for feat in doc_map.get("features", []):
        if feat.get("source_type") != "customer-requirements":
            continue
        source_file = str(feat.get("source_file", ""))
        by_file.setdefault(source_file, []).append(feat)

    for source_file, feats in sorted(by_file.items()):
        current_module = ""
        for feat in sorted(feats, key=lambda item: (int(item.get("depth", 99)), str(item.get("heading", "")))):
            term = str(feat.get("normalized_term", ""))
            if not term:
                continue
            depth = int(feat.get("depth", 99))
            if depth == 1 or not current_module:
                current_module = term
                grouped.setdefault(current_module, {"files": [], "items": []})["files"].append(source_file)
                continue
            items = grouped.setdefault(current_module, {"files": [], "items": []})["items"]
            if term not in items:
                items.append(term)

    return grouped


def _image_refs(capabilities: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for cap in capabilities:
        for ev in cap.get("evidence", []):
            if ev.get("kind") != "image":
                continue
            ref = str(ev.get("ref", ""))
            if ref and ref not in seen:
                seen.add(ref)
                refs.append(ref)
    return refs


def _chapter_with_lines(title: str, lines: list[str], level: int = 1, page_break: bool = False) -> list[str]:
    heading = "#" * (level + 1)
    body = [f"{heading} {title}", ""]
    body.extend([
        "```yaml",
        *_yaml_block({"style": f"heading-{level}", "page_break": page_break}),
        "```",
        "",
    ])
    body.extend(lines)
    body.append("")
    return body


def _render_customer_section(doc_map: dict[str, Any] | None) -> list[str]:
    grouped = _group_customer_requirements(doc_map)
    lines = ["共 " + str(len(grouped)) + " 个模块。", ""]
    if not grouped:
        lines.append("- （暂无，待 raw/ 转换后补充）")
        return _chapter_with_lines("2. 客户需求汇总", lines, page_break=False)

    for module, payload in grouped.items():
        files = ", ".join(dict.fromkeys(payload["files"]))
        lines.append(f"### {module}")
        lines.append("")
        lines.append(f"- 来源：{files}")
        if payload["items"]:
            lines.append("- 需求：")
            for item in payload["items"]:
                lines.append(f"  - {item}")
        else:
            lines.append("- 需求：无下级标题，待补充")
        lines.append("")

    return _chapter_with_lines("2. 客户需求汇总", lines, page_break=False)


def _render_baseline_section(stats: dict[str, int], capabilities: list[dict[str, Any]]) -> list[str]:
    lines = [
        f"- 项目：{capabilities[0].get('project', '商管系统') if capabilities else '商管系统'}",
        "- 来源：客户需求 + 竞品资料 + 当前产品代码基线（/opt/code/mi）",
        f"- 能力总数：{sum(stats.values())}",
        f"- 状态分布：existing {stats.get('existing', 0)} / partial {stats.get('partial', 0)} / missing {stats.get('missing', 0)} / explicitly-not-do {stats.get('explicitly-not-do', 0)}",
        "",
        "### 1.1 当前产品基线",
        "",
        "```yaml",
        *_yaml_block({
            "style": "heading-2",
            "table": "baseline-stats",
            "table_data": {
                "header": ["状态", "数量"],
                "rows": _stringify_table([[k, v] for k, v in stats.items()]),
            },
        }),
        "```",
    ]
    return _chapter_with_lines("1. 背景", lines, page_break=True)


def _render_feature_section(capabilities: list[dict[str, Any]]) -> list[str]:
    rows = []
    for cap in capabilities:
        rows.append([
            str(cap.get("name", cap.get("id", ""))),
            str(cap.get("reconciled_status", "missing")),
            str(cap.get("confidence", "low")),
            str(len(cap.get("evidence", []))),
        ])
    return _chapter_with_lines(
        "3. 功能清单",
        [
            "```yaml",
            *_yaml_block({
                "style": "heading-1",
                "table": "feature-matrix",
                "table_data": {
                    "header": ["功能名", "状态", "置信度", "证据数"],
                    "rows": _stringify_table(rows),
                },
            }),
            "```",
        ],
        page_break=False,
    )


def _render_gap_section(capabilities: list[dict[str, Any]]) -> list[str]:
    lines = []
    for cap in capabilities:
        gaps = [str(item) for item in cap.get("gaps", [])]
        if not gaps:
            continue
        name = str(cap.get("name", cap.get("id", "")))
        status = str(cap.get("reconciled_status", "missing"))
        lines.append(f"- **{name}** ({status}): {'; '.join(gaps)}")
    if not lines:
        lines.append("- （暂无明显差距）")
    return _chapter_with_lines("4. 差距分析", lines, page_break=False)


def _render_evidence_section(capabilities: list[dict[str, Any]]) -> list[str]:
    rows = []
    for cap in capabilities:
        name = str(cap.get("name", cap.get("id", "")))
        for ev in cap.get("evidence", []):
            rows.append([name, str(ev.get("kind", "")), str(ev.get("ref", ""))])
    return _chapter_with_lines(
        "5. 需求证据表",
        [
            "```yaml",
            *_yaml_block({
                "style": "heading-1",
                "table": "evidence-matrix",
                "table_data": {
                    "header": ["功能名", "证据类型", "证据引用"],
                    "rows": _stringify_table(rows),
                },
            }),
            "```",
        ],
        page_break=False,
    )


def _render_version_section(capabilities: list[dict[str, Any]]) -> list[str]:
    buckets: dict[str, list[str]] = {label: [] for label in ("P0", "P1", "P2", "P3", "暂缓")}
    version_by_status = {"existing": "P3", "partial": "P1", "missing": "P2", "explicitly-not-do": "暂缓"}
    for cap in capabilities:
        if not cap.get("gaps"):
            continue
        version = version_by_status.get(str(cap.get("reconciled_status", "missing")), "P2")
        name = str(cap.get("name", cap.get("id", "")))
        gaps = "; ".join(str(item) for item in cap.get("gaps", []))
        buckets[version].append(f"{name}：{gaps}" if gaps else name)

    lines = ["说明：仅列出存在 gap 的能力；已实现且无 gap 的项不进入版本规划。", ""]
    for label in ("P0", "P1", "P2", "P3", "暂缓"):
        lines.append(f"### {label}（{len(buckets[label])} 项）")
        lines.append("")
        if buckets[label]:
            for item in buckets[label]:
                lines.append(f"- {item}")
        else:
            lines.append("- （无）")
        lines.append("")
    return _chapter_with_lines("6. 版本规划", lines, page_break=False)


def _render_image_section(capabilities: list[dict[str, Any]]) -> list[str]:
    refs = _image_refs(capabilities)
    lines = refs or ["- （暂无图片证据，待 raw/ 转换后补充）"]
    return _chapter_with_lines("7. 界面 / 流程参考", lines, page_break=False)


def _render_risk_section(capabilities: list[dict[str, Any]]) -> list[str]:
    low_conf = [cap for cap in capabilities if str(cap.get("confidence", "")) == "low"]
    lines = [f"低置信度能力：{len(low_conf)} 项", ""]
    for cap in low_conf:
        name = str(cap.get("name", cap.get("id", "")))
        gaps = "; ".join(str(item) for item in cap.get("gaps", []))
        lines.append(f"- **{name}**: {gaps}")
    if not low_conf:
        lines.append("- （暂无）")
    return _chapter_with_lines("8. 风险与待确认项", lines, page_break=False)


def _render_unmatched_section(capabilities: list[dict[str, Any]]) -> list[str]:
    missing = [cap for cap in capabilities if str(cap.get("reconciled_status", "")) == "missing"]
    if not missing:
        return _chapter_with_lines("5. 客户需求未覆盖", ["当前所有客户需求均在代码能力范围内有对应。"], page_break=False)
    missing.sort(key=lambda c: (-len(c.get("evidence", [])), str(c.get("name", ""))))
    lines = [f"共 {len(missing)} 项客户明确提出但当前代码无对应能力的需求：", ""]
    for cap in missing:
        name = str(cap.get("name", cap.get("id", "")))
        evidence = cap.get("evidence", [])
        clients = [str(e.get("ref", "")).replace("customer:", "") for e in evidence if e.get("kind") == "doc"]
        client_str = ", ".join(clients[:4])
        if len(clients) > 4:
            client_str += f" 等 {len(clients)} 个客户"
        lines.append(f"- **{name}** ← {client_str}")
    return _chapter_with_lines("5. 客户需求未覆盖", lines, page_break=False)


def build_content_package(reconcile_path: str | Path, doc_map_path: str | Path | None, output_dir: str | Path) -> Path:
    reconcile = _load_json(reconcile_path)
    doc_map = _load_json(doc_map_path) if doc_map_path else None
    capabilities = list(reconcile.get("capabilities", []))
    stats = _status_stats(capabilities)
    project = str(reconcile.get("project", "商管系统"))

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    content_path = output_dir / "产品PRD.word-content.md"

    sections = [
        *_frontmatter_lines(reconcile, doc_map),
        "",
        *_render_baseline_section(stats, capabilities),
        *_render_customer_section(doc_map),
        *_render_feature_section(capabilities),
        *_render_unmatched_section(capabilities),
        *_render_gap_section(capabilities),
        *_render_evidence_section(capabilities),
        *_render_version_section(capabilities),
        *_render_image_section(capabilities),
        *_render_risk_section(capabilities),
        "## 9. 附录",
        "",
        "- 差距分析详见 [差距分析.md](差距分析.md)",
        "- 证据表详见 [需求证据表.md](需求证据表.md)",
        "",
    ]
    content_path.write_text("\n".join(sections), encoding="utf-8")
    return content_path


def render_docx(content_package: str | Path, output_path: str | Path, word_master_root: str | Path | None = None) -> Path:
    root = Path(word_master_root) if word_master_root else Path(__file__).resolve().parents[3] / "word" / "word-master"
    content_package_path = Path(content_package).resolve()
    output_path = Path(output_path).resolve()
    cmd = ["uv", "run", "python", "-m", "src.main", str(content_package_path), "--output", str(output_path)]
    completed = subprocess.run(cmd, cwd=root, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"word-master render failed with exit code {completed.returncode}")
    return output_path
