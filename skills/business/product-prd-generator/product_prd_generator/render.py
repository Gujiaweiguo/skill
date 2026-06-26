from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


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


def _render_requirement_list(requirements: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    """Six-dimension requirement table with auto-suggested priority (Rule 3B)."""
    if not requirements:
        return ""
    priority_order = {"高": 0, "中": 1, "低": 2}
    reqs_sorted = sorted(
        requirements,
        key=lambda r: (
            priority_order.get(r.get("priority", "低"), 3),
            r.get("scenario", ""),
            r.get("sub_scenario", ""),
        ),
    )
    high = sum(1 for r in reqs_sorted if r.get("priority") == "高")
    med = sum(1 for r in reqs_sorted if r.get("priority") == "中")
    low = sum(1 for r in reqs_sorted if r.get("priority") == "低")
    lines = [
        "## 3.5 需求清单（六维框架）",
        "",
        f"共 {len(reqs_sorted)} 条需求。优先级分布：高 {high} / 中 {med} / 低 {low}。",
        f"本节列出前 100 条（按优先级排序），完整清单见 [需求清单.md](需求清单.md)。",
        "",
        "| 场景 | 子场景 | 功能 | 痛点/描述 | 来源 | 优先级 | 代码状态 | 匹配能力 |",
        "|------|--------|------|-----------|------|--------|---------|---------|",
    ]
    for req in reqs_sorted[:100]:
        scenario = req.get("scenario", "未分类")
        sub = req.get("sub_scenario", "") or "—"
        func = req.get("function", "")
        nearby = req.get("nearby_text", "") or "—"
        if len(nearby) > 60:
            nearby = nearby[:60] + "…"
        customer = req.get("source_customer", "") or "—"
        priority = req.get("priority", "低")
        status = req.get("code_status", "unmatched")
        matched = req.get("matched_capability", "") or "—"
        lines.append(f"| {scenario} | {sub} | {func} | {nearby} | {customer} | {priority} | {status} | {matched} |")
    return "\n".join(lines) + "\n"


def _render_requirement_list_file(requirements: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    """Standalone 需求清单.md with groupable six-dimension table."""
    if not requirements:
        return "# 需求清单\n\n（暂无结构化需求）\n"
    priority_order = {"高": 0, "中": 1, "低": 2}
    reqs_sorted = sorted(
        requirements,
        key=lambda r: (
            r.get("scenario", ""),
            r.get("sub_scenario", ""),
            priority_order.get(r.get("priority", "低"), 3),
        ),
    )
    lines = [
        "# 需求清单（六维框架）",
        "",
        f"共 {len(reqs_sorted)} 条需求。",
        "",
        "| 场景 | 子场景 | 功能 | 痛点/描述 | 来源 | 优先级 | 代码状态 | 匹配能力 |",
        "|------|--------|------|-----------|------|--------|---------|---------|",
    ]
    for req in reqs_sorted:
        scenario = req.get("scenario", "未分类")
        sub = req.get("sub_scenario", "") or "—"
        func = req.get("function", "")
        nearby = req.get("nearby_text", "") or "—"
        if len(nearby) > 80:
            nearby = nearby[:80] + "…"
        customer = req.get("source_customer", "") or "—"
        priority = req.get("priority", "低")
        status = req.get("code_status", "unmatched")
        matched = req.get("matched_capability", "") or "—"
        lines.append(f"| {scenario} | {sub} | {func} | {nearby} | {customer} | {priority} | {status} | {matched} |")
    return "\n".join(lines) + "\n"


def _load_ontology() -> dict[str, Any]:  # noqa: ANY_OK
    ontology_path = Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk")) / "knowledge" / "business-ontology.yaml"
    if not ontology_path.is_file():
        return {}
    return yaml.safe_load(ontology_path.read_text(encoding="utf-8")) or {}


def _classify_module(req: dict[str, Any], ontology: dict[str, Any]) -> str:  # noqa: ANY_OK
    modules = ontology.get("modules", {})
    if not isinstance(modules, dict):
        return "未分类"
    scenario = str(req.get("scenario", ""))
    function = str(req.get("function", ""))
    combined = scenario + " " + function
    best_module = "未分类"
    best_score = 0
    for mod_name, mod_data in modules.items():
        if not isinstance(mod_data, dict):
            continue
        for alias in mod_data.get("aliases", []):
            if isinstance(alias, str) and alias in combined:
                score = len(alias)
                if score > best_score:
                    best_score = score
                    best_module = mod_name
    return best_module


def _render_module_summary(requirements: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    ontology = _load_ontology()
    if not ontology:
        return ""
    module_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"total": 0, "matched": 0, "unmatched": 0, "高": 0, "中": 0, "低": 0}
    )
    for req in requirements:
        module = _classify_module(req, ontology)
        stats = module_stats[module]
        stats["total"] += 1
        if req.get("matched_capability"):
            stats["matched"] += 1
        else:
            stats["unmatched"] += 1
        stats[req.get("priority", "低")] += 1
    lines = [
        "## 3.6 需求模块汇总",
        "",
        f"按业务模块聚合 {len(requirements)} 条需求：",
        "",
        "| 模块 | 需求数 | 已匹配 | 未匹配 | 高 | 中 | 低 |",
        "|------|--------|--------|--------|---|---|---|",
    ]
    for module in sorted(module_stats, key=lambda m: -module_stats[m]["total"]):
        s = module_stats[module]
        lines.append(f"| {module} | {s['total']} | {s['matched']} | {s['unmatched']} | {s['高']} | {s['中']} | {s['低']} |")
    return "\n".join(lines) + "\n"


def _render_priority_review(requirements: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    """高优先级需求 review 清单 — standalone file for human review."""
    high_reqs = sorted(
        [r for r in requirements if r.get("priority") == "高"],
        key=lambda r: (r.get("scenario", ""), r.get("source_customer", "")),
    )
    if not high_reqs:
        return "# 高优先级需求 review 清单\n\n当前无高优先级需求。\n"
    lines = [
        "# 高优先级需求 review 清单",
        "",
        f"共 {len(high_reqs)} 条高优先级需求，请逐条确认：",
        "",
    ]
    for i, req in enumerate(high_reqs, 1):
        func = req.get("function", "")
        scenario = req.get("scenario", "未分类")
        sub = req.get("sub_scenario", "")
        nearby = req.get("nearby_text", "")
        customer = req.get("source_customer", "") or "未知"
        status = req.get("code_status", "unmatched")
        matched = req.get("matched_capability", "") or "未匹配"
        lines.append(f"## {i}. {func}")
        lines.append(f"- 场景：{scenario}" + (f" > {sub}" if sub else ""))
        lines.append(f"- 来源：{customer}")
        lines.append(f"- 代码状态：{status}")
        lines.append(f"- 匹配能力：{matched}")
        if nearby:
            lines.append(f"- 描述：{nearby[:120]}")
        lines.append("- [ ] 确认为真实需求")
        lines.append("- [ ] 优先级合理")
        lines.append("- [ ] 备注：")
        lines.append("")
    return "\n".join(lines) + "\n"


# ── Blueprint rendering ───────────────────────────────────────────────────

_BLUEPRINT_FILES = [
    "蓝图方案", "蓝图规划", "华侨城集团资产数字化",
    "创鸿集团", "创鸿商业管理", "奥克斯商管",
]


def _classify_doc_type(source_file: str) -> str:
    for p in _BLUEPRINT_FILES:
        if p in source_file:
            return "blueprint"
    if "功能手册" in source_file or "功能清单" in source_file:
        return "manual"
    if "操作手册" in source_file or "操作指引" in source_file:
        return "operation"
    if "管理制度" in source_file:
        return "management"
    return "reference"


_ROLE_KEYWORDS = [
    "招商专员", "招商经理", "招商总监",
    "财务专员", "财务经理", "财务总监",
    "物业专员", "物业经理", "物业总监",
    "营运专员", "营运经理", "营运总监",
    "工程部", "信息部", "项目管理", "项目总",
    "专员", "经理", "总监", "主管",
]


def _extract_roles(text: str) -> list[str]:
    found: list[str] = []
    for role in _ROLE_KEYWORDS:
        if role in text and role not in found:
            if role in ("专员", "经理", "总监", "主管"):
                if not any(r != role and r.endswith(role) for r in found):
                    found.append(role)
            else:
                found.append(role)
    return found[:3]


_STATUS_ICON = {"existing": "✅", "partial": "⚠️", "missing": "❌", "unmatched": "🔍"}

_DEPT_MAP: dict[str, list[str]] = {
    "招商": ["招商", "招商专员", "招商经理", "招商总监", "招商中心", "租赁部"],
    "营运": ["营运", "营运专员", "营运经理", "营运总监", "运营", "经营"],
    "物业": ["物业", "物业专员", "物业经理", "物业总监", "物管", "工程部"],
    "财务": ["财务", "财务专员", "财务经理", "财务总监", "财务管理部"],
    "推广": ["推广", "企划", "市场推广", "策划"],
    "信息": ["信息", "信息部", "IT", "系统管理员"],
    "项目": ["项目总", "副总", "项目管理"],
}


def _extract_depts(text: str) -> str:
    found: list[str] = []
    for dept, keywords in _DEPT_MAP.items():
        if any(kw in text for kw in keywords) and dept not in found:
            found.append(dept)
    return "、".join(found) if found else "—"


def _infer_platform(text: str) -> str:
    if any(kw in text for kw in ["移动", "APP", "手机", "微信", "小程序", "移动端", "租户服务平台"]):
        return "移动端"
    return "PC端"


def _render_blueprint_modules(
    requirements: list[dict[str, Any]],  # noqa: ANY_OK
    capabilities: list[dict[str, Any]],  # noqa: ANY_OK
    ontology: dict[str, Any],  # noqa: ANY_OK
) -> str:
    """Render PRD by business module — blueprint style with scenarios."""
    modules = ontology.get("modules", {})
    if not isinstance(modules, dict) or not modules:
        return ""
    cap_by_id: dict[str, dict[str, Any]] = {str(c.get("id", "")): c for c in capabilities}  # noqa: ANY_OK
    module_reqs: dict[str, list[dict[str, Any]]] = defaultdict(list)  # noqa: ANY_OK
    for req in requirements:
        mod = _classify_module(req, ontology)
        module_reqs[mod].append(req)
    mod_names = list(modules.keys())
    lines = ["## 3. 业务模块详细设计", ""]
    for idx, (mod_name, mod_data) in enumerate(modules.items()):
        if not isinstance(mod_data, dict):
            continue
        reqs = module_reqs.get(mod_name, [])
        sub_funcs = mod_data.get("sub_functions", {})
        mod_cap_ids: set[str] = set()
        for sub in sub_funcs.values():
            if isinstance(sub, dict):
                for cap_id in sub.get("capabilities", []):
                    mod_cap_ids.add(str(cap_id))
        mod_caps = [cap_by_id[c] for c in mod_cap_ids if c in cap_by_id]
        existing_count = sum(1 for c in mod_caps if c.get("reconciled_status") == "existing")
        missing_count = sum(1 for c in mod_caps if c.get("reconciled_status") == "missing")
        lines.append(f"### 3.{idx + 1} {mod_name}")
        lines.append("")
        desc = mod_data.get("description", "")
        if desc:
            lines.append(f"> {desc}")
            lines.append("")
        aliases = mod_data.get("aliases", [])
        if aliases:
            lines.append(f"**关键词**：{', '.join(str(a) for a in aliases[:6])}")
            lines.append("")
        lines.append(f"**需求**：{len(reqs)} 条 | **能力**：{len(mod_caps)} 项（✅{existing_count} / ❌{missing_count}）")
        lines.append("")

        # Group requirements by sub_function
        sub_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)  # noqa: ANY_OK
        ungrouped: list[dict[str, Any]] = []
        for req in reqs:
            func_text = str(req.get("function", "")) + " " + str(req.get("nearby_text", ""))
            matched_sub = False
            for sub_name, sub_data in sub_funcs.items():
                if not isinstance(sub_data, dict):
                    continue
                for term in sub_data.get("terms", []):
                    if isinstance(term, str) and term in func_text:
                        sub_groups[sub_name].append(req)
                        matched_sub = True
                        break
                if matched_sub:
                    break
            if not matched_sub:
                ungrouped.append(req)

        for sub_name, sub_data in sub_funcs.items():
            if not isinstance(sub_data, dict):
                continue
            sub_r = sub_groups.get(sub_name, [])
            lines.append(f"#### {sub_name}")
            lines.append("")
            if sub_r:
                lines.append("| 角色 | 场景 | 场景描述 | 状态 | 来源 | 端点 |")
                lines.append("|------|------|---------|------|------|------|")
                seen_t: set[str] = set()
                for req in sorted(sub_r, key=lambda r: r.get("priority", "低")):
                    term = req.get("normalized_term", "")
                    if term in seen_t:
                        continue
                    seen_t.add(term)
                    func = str(req.get("function", ""))[:30].replace("|", "／")
                    nearby = str(req.get("nearby_text", ""))[:50].replace("|", "／").replace("\n", " ") or "—"
                    combined_text = str(req.get("nearby_text", "")) + " " + str(req.get("function", ""))
                    depts = _extract_depts(combined_text)
                    desc = f"{func}：{nearby[:40]}" if nearby != "—" else func
                    status = str(req.get("code_status", "unmatched"))
                    icon = _STATUS_ICON.get(status, "🔍")
                    customer = str(req.get("source_customer", "")) or "—"
                    platform = _infer_platform(combined_text)
                    lines.append(f"| {depts} | {sub_name} | {desc} | {icon} {status} | {customer} | {platform} |")
                lines.append("")
                # Scenarios
                scenarios = [
                    req for req in sub_r
                    if len(str(req.get("nearby_text", ""))) > 30
                    and any(role in str(req.get("nearby_text", "")) for role in _ROLE_KEYWORDS)
                ]
                if scenarios:
                    lines.append("**用户场景**：")
                    lines.append("")
                    seen_s: set[str] = set()
                    for req in scenarios[:3]:
                        nearby = str(req.get("nearby_text", ""))[:150]
                        if nearby in seen_s:
                            continue
                        seen_s.add(nearby)
                        func = req.get("function", "")
                        customer = req.get("source_customer", "")
                        doc_type = _classify_doc_type(req.get("source_file", ""))
                        lines.append(f"> **{func}**")
                        lines.append(f"> {nearby}")
                        if customer:
                            lines.append(f"> — {customer}（{doc_type}）")
                        lines.append("")
            else:
                cap_ids = sub_data.get("capabilities", [])
                if cap_ids:
                    cap = cap_by_id.get(str(cap_ids[0]))
                    if cap:
                        status = str(cap.get("reconciled_status", "missing"))
                        icon = _STATUS_ICON.get(status, "🔍")
                        lines.append(f"- {icon} **{cap.get('name', cap_ids[0])[:30]}** ({cap_ids[0]})")
                        terms = sub_data.get("terms", [])
                        if terms:
                            lines.append(f"  术语：{', '.join(str(t) for t in terms[:5])}")
                        lines.append("")
            # Gaps
            gaps = [req for req in sub_r if req.get("code_status") in ("missing", "unmatched")]
            if gaps:
                gap_funcs = sorted(set(str(r.get("function", ""))[:25] for r in gaps))[:8]
                if gap_funcs:
                    lines.append(f"**差距**：{', '.join(gap_funcs)}")
                    lines.append("")

        if ungrouped:
            ungrouped_funcs = sorted(set(str(r.get("function", ""))[:25] for r in ungrouped))[:10]
            if ungrouped_funcs:
                lines.append(f"**其他**：{', '.join(ungrouped_funcs)}")
                lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def render_prd(inputs: RenderInputs) -> str:
    project = inputs.reconcile.get("project", "商管系统")
    capabilities = inputs.reconcile.get("capabilities", [])
    requirements = inputs.reconcile.get("requirements", [])
    stats = _status_stats(capabilities)
    ontology = _load_ontology()
    parts = [
        _render_header(project, stats),
        _render_customer_summary(inputs.doc_map),
        _render_blueprint_modules(requirements, capabilities, ontology) if ontology else _render_requirement_list(requirements),
        _render_module_summary(requirements),
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
        "- 需求清单详见 [需求清单.md](需求清单.md)",
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
    requirements = inputs.reconcile.get("requirements", [])

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "产品PRD.md").write_text(render_prd(inputs), encoding="utf-8")
    (output_dir / "功能清单.md").write_text(_render_feature_list(capabilities), encoding="utf-8")
    (output_dir / "差距分析.md").write_text(_render_gap_analysis(capabilities), encoding="utf-8")
    (output_dir / "需求证据表.md").write_text(_render_evidence_table(capabilities), encoding="utf-8")
    (output_dir / "需求清单.md").write_text(_render_requirement_list_file(requirements), encoding="utf-8")
    (output_dir / "高优先级需求review清单.md").write_text(_render_priority_review(requirements), encoding="utf-8")

    print(f"rendered 6 files to {output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
