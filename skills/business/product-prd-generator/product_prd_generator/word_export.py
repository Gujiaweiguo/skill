from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_CONTROL_CHARS = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def _sanitize(text: str) -> str:
    return _CONTROL_CHARS.sub('', text)


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
    return [[_sanitize(str(cell)) for cell in row] for row in rows]


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


def _render_requirement_section(requirements: list[dict[str, Any]]) -> list[str]:
    if not requirements:
        return []
    priority_order = {"高": 0, "中": 1, "低": 2}
    reqs_sorted = sorted(
        requirements,
        key=lambda r: (
            priority_order.get(str(r.get("priority", "低")), 3),
            str(r.get("scenario", "")),
            str(r.get("sub_scenario", "")),
        ),
    )
    rows = []
    for req in reqs_sorted:
        nearby = _sanitize(str(req.get("nearby_text", "")) or "—")
        if len(nearby) > 60:
            nearby = nearby[:60] + "…"
        rows.append([
            _sanitize(str(req.get("scenario", "未分类"))),
            _sanitize(str(req.get("sub_scenario", "")) or "—"),
            _sanitize(str(req.get("function", ""))),
            nearby,
            _sanitize(str(req.get("source_customer", "")) or "—"),
            _sanitize(str(req.get("priority", "低"))),
            _sanitize(str(req.get("code_status", "unmatched"))),
        ])
    high = sum(1 for r in reqs_sorted if str(r.get("priority")) == "高")
    med = sum(1 for r in reqs_sorted if str(r.get("priority")) == "中")
    low = sum(1 for r in reqs_sorted if str(r.get("priority")) == "低")
    return _chapter_with_lines(
        "2.5 需求清单（六维框架）",
        [
            f"共 {len(reqs_sorted)} 条需求，优先级分布：高 {high} / 中 {med} / 低 {low}。",
            "",
            "```yaml",
            *_yaml_block({
                "style": "heading-1",
                "table": "requirement-matrix",
                "table_data": {
                    "header": ["场景", "子场景", "功能", "痛点/描述", "来源", "优先级", "代码状态"],
                    "rows": _stringify_table(rows),
                },
            }),
            "```",
        ],
        page_break=False,
    )


_STATUS_ICON_W = {"existing": "✅", "partial": "⚠️", "missing": "❌", "unmatched": "🔍"}

_ROLE_KW = [
    "招商专员", "招商经理", "招商总监",
    "财务专员", "财务经理", "财务总监",
    "物业专员", "物业经理", "营运经理",
    "工程部", "信息部", "项目总",
    "专员", "经理", "总监", "主管",
]


def _extract_roles_w(text: str) -> str:
    found = [r for r in _ROLE_KW if r in text]
    return "、".join(found[:3]) if found else "—"


def _load_ontology_w() -> dict[str, Any]:
    import os
    p = Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk")) / "knowledge" / "business-ontology.yaml"
    if not p.is_file():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _classify_mod_w(req: dict[str, Any], ontology: dict[str, Any]) -> str:
    modules = ontology.get("modules", {})
    if not isinstance(modules, dict):
        return "未分类"
    combined = str(req.get("scenario", "")) + " " + str(req.get("function", ""))
    best, best_score = "未分类", 0
    for name, data in modules.items():
        if not isinstance(data, dict):
            continue
        for alias in data.get("aliases", []):
            if isinstance(alias, str) and alias in combined:
                s = len(alias)
                if s > best_score:
                    best_score, best = s, name
    return best


def _render_blueprint_section(
    requirements: list[dict[str, Any]],
    capabilities: list[dict[str, Any]],
) -> list[str]:
    """Blueprint-style module breakdown for Word export."""
    ontology = _load_ontology_w()
    modules = ontology.get("modules", {})
    if not isinstance(modules, dict) or not modules:
        return _render_requirement_section(requirements)

    cap_by_id = {str(c.get("id", "")): c for c in capabilities}
    mod_reqs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for req in requirements:
        mod_reqs[_classify_mod_w(req, ontology)].append(req)

    lines: list[str] = []
    for idx, (mod_name, mod_data) in enumerate(modules.items()):
        if not isinstance(mod_data, dict):
            continue
        reqs = mod_reqs.get(mod_name, [])
        sub_funcs = mod_data.get("sub_functions", {})
        desc = str(mod_data.get("description", ""))
        aliases = mod_data.get("aliases", [])
        kw_str = ", ".join(str(a) for a in aliases[:5]) if aliases else ""

        mod_cap_ids: set[str] = set()
        for sub in sub_funcs.values():
            if isinstance(sub, dict):
                mod_cap_ids.update(str(c) for c in sub.get("capabilities", []))
        mod_caps = [cap_by_id[c] for c in mod_cap_ids if c in cap_by_id]
        existing = sum(1 for c in mod_caps if c.get("reconciled_status") == "existing")
        missing = sum(1 for c in mod_caps if c.get("reconciled_status") == "missing")

        lines.append(f"### 3.{idx + 1} {mod_name}")
        lines.append("")
        if desc:
            lines.append(f"> {desc}")
            lines.append("")
        if kw_str:
            lines.append(f"**关键词**：{kw_str}")
            lines.append("")
        lines.append(f"需求 {len(reqs)} 条 | 能力 {len(mod_caps)} 项（✅{existing} / ❌{missing}）")
        lines.append("")

        # Group by sub_function
        sub_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for req in reqs:
            ft = str(req.get("function", "")) + " " + str(req.get("nearby_text", ""))
            placed = False
            for sn, sd in sub_funcs.items():
                if not isinstance(sd, dict):
                    continue
                for term in sd.get("terms", []):
                    if isinstance(term, str) and term in ft:
                        sub_groups[sn].append(req)
                        placed = True
                        break
                if placed:
                    break

        for sn, sd in sub_funcs.items():
            if not isinstance(sd, dict):
                continue
            sr = sub_groups.get(sn, [])
            lines.append(f"**{sn}**")
            lines.append("")
            if sr:
                rows = []
                seen: set[str] = set()
                for req in sorted(sr, key=lambda r: r.get("priority", "低")):
                    term = req.get("normalized_term", "")
                    if term in seen:
                        continue
                    seen.add(term)
                    func = _sanitize(str(req.get("function", ""))[:30])
                    nearby = _sanitize(str(req.get("nearby_text", ""))[:45] or "—")
                    roles = _extract_roles_w(str(req.get("nearby_text", "")) + str(req.get("function", "")))
                    status = str(req.get("code_status", "unmatched"))
                    icon = _STATUS_ICON_W.get(status, "🔍")
                    customer = _sanitize(str(req.get("source_customer", "")) or "—")
                    rows.append([func, nearby, roles, f"{icon} {status}", customer])
                lines.append("```yaml")
                lines.extend(_yaml_block({
                    "style": "heading-2",
                    "table": f"sub-{sn}",
                    "table_data": {
                        "header": ["功能", "描述", "角色", "状态", "来源"],
                        "rows": _stringify_table(rows),
                    },
                }))
                lines.append("```")
                lines.append("")
                # Scenarios
                scenarios = [
                    req for req in sr
                    if len(str(req.get("nearby_text", ""))) > 30
                    and any(rk in str(req.get("nearby_text", "")) for rk in _ROLE_KW)
                ]
                for sc in scenarios[:2]:
                    nearby = _sanitize(str(sc.get("nearby_text", ""))[:120])
                    func = sc.get("function", "")
                    lines.append(f"> **{func}**: {nearby}")
                    lines.append("")
            else:
                cap_ids = sd.get("capabilities", [])
                if cap_ids:
                    cap = cap_by_id.get(str(cap_ids[0]))
                    if cap:
                        status = str(cap.get("reconciled_status", "missing"))
                        icon = _STATUS_ICON_W.get(status, "🔍")
                        lines.append(f"- {icon} {cap.get('name', cap_ids[0])[:30]}")
                        lines.append("")

        lines.append("---")
        lines.append("")

    return _chapter_with_lines("3. 业务模块详细设计", lines, page_break=False)


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
        *_render_blueprint_section(list(reconcile.get("requirements", [])), capabilities),
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
        "- 需求清单详见 [需求清单.md](需求清单.md)",
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
