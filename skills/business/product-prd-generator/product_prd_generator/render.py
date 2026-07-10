from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .data_model import (
    TableMeta,
    get_unmatched,
    group_by_module,
    parse_data_dict_files,
    pick_key_fields,
)
from .review_format import ReviewBriefInput, render_review_brief


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
    docs_root: str = ""


def _load_json(path: str) -> dict[str, Any]:  # noqa: ANY_OK
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_inputs(reconcile_path: str, doc_map_path: str | None, docs_root: str = "") -> RenderInputs:
    return RenderInputs(
        reconcile=_load_json(reconcile_path),
        doc_map=_load_json(doc_map_path) if doc_map_path else None,
        docs_root=docs_root,
    )


def _status_stats(capabilities: list[dict[str, Any]]) -> Counter[str]:  # noqa: ANY_OK
    return Counter(cap.get("reconciled_status", "missing") for cap in capabilities)


def _render_project_context(project: str, stats: Counter[str]) -> str:
    total = sum(stats.values())
    return f"""## 1. 背景

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


def _approval_flows_from_file(docs_root: str) -> list[tuple[str, str, str, str, str]]:
    path = Path(docs_root) / "02-competitors/海鼎/业务流程/ERP业务权限审批-结构化.md"
    if not path.is_file():
        return []
    flows: list[tuple[str, str, str, str, str]] = []
    module = "跨模块流程"
    menu = "—"
    document = "—"
    pending = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            module = line.removeprefix("## ").strip()
        elif line.startswith("### "):
            menu = line.removeprefix("### ").strip()
        elif line.startswith("#### "):
            document = line.removeprefix("#### ").strip()
        elif line.startswith("**") and line.endswith("**") and "审批链" in line:
            pending = line.strip("*")
        elif pending and line.startswith("审批流程："):
            flows.append((module, menu, document, pending, line))
            pending = ""
    return flows


def _render_approval_flow_evidence(requirements: list[dict[str, Any]], docs_root: str) -> str:  # noqa: ANY_OK
    file_flows = _approval_flows_from_file(docs_root)
    if file_flows:
        file_grouped: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
        for module, menu, document, name, flow in file_flows:
            file_grouped[module].append((menu, document, name, flow))
        lines = [
            "## 3B. 海鼎 ERP 审批流证据",
            "",
            "本节来自 `ERP业务权限审批.xlsx` 的结构化派生文件，用于补充流程、权限和审批链设计；原始 xlsx 与 markitdown 转换结果均已保留。",
            "",
            f"共 {len(file_flows)} 条审批链。",
            "",
        ]
        for module, items in sorted(file_grouped.items()):
            lines.extend([f"### {module}", ""])
            lines.append("| 二级菜单 | 单据/对象 | 审批事项 | 审批流程 | 来源 |")
            lines.append("| --- | --- | --- | --- | --- |")
            for menu, document, name, flow in sorted(items):
                lines.append(
                    f"| {menu.replace('|', '／')} | {document.replace('|', '／')} | {name.replace('|', '／')} | {flow.replace('|', '／')} | `02-competitors/海鼎/业务流程/ERP业务权限审批-结构化.md` |"
                )
            lines.append("")
        lines.extend(["---", ""])
        return "\n".join(lines)

    flows = [
        req for req in requirements
        if "ERP业务权限审批-结构化" in str(req.get("source_file", ""))
        and "审批链" in str(req.get("function", ""))
    ]
    if not flows:
        return ""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)  # noqa: ANY_OK
    for req in flows:
        scenario = str(req.get("scenario", "跨模块流程")) or "跨模块流程"
        grouped[scenario].append(req)
    lines = [
        "## 3B. 海鼎 ERP 审批流证据",
        "",
        "本节来自 `ERP业务权限审批.xlsx` 的结构化派生文件，用于补充流程、权限和审批链设计；原始 xlsx 与 markitdown 转换结果均已保留。",
        "",
        f"共 {len(flows)} 条审批链。",
        "",
    ]
    for scenario, items in sorted(grouped.items()):
        lines.extend([f"### {scenario}", ""])
        lines.append("| 审批事项 | 审批流程 | 来源 |")
        lines.append("| --- | --- | --- |")
        for req in sorted(items, key=lambda r: str(r.get("function", ""))):
            name = str(req.get("function", "")).replace("|", "／")
            nearby = str(req.get("nearby_text", "")).replace("|", "／").replace("\n", " ")
            source = str(req.get("source_file", "")).replace("|", "／")
            lines.append(f"| {name} | {nearby or '—'} | `{source}` |")
        lines.append("")
    lines.extend(["---", ""])
    return "\n".join(lines)


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


def _structure_kind_label(kind: str) -> str:
    return {
        "clause-group": "合同条款组",
        "clause-field": "合同字段",
        "data-structure": "数据结构",
        "workflow": "流程",
        "permission": "权限",
        "feature": "功能",
    }.get(kind, kind or "功能")


def _render_structure_summary(requirements: list[dict[str, Any]]) -> str:  # noqa: ANY_OK
    if not requirements:
        return ""
    counts: Counter[str] = Counter(_structure_kind_label(str(req.get("kind", "feature"))) for req in requirements)
    lines = ["## 3.2 结构类型概览", "", "| 类型 | 数量 |", "|---|---|"]
    for label in ("合同条款组", "合同字段", "数据结构", "流程", "权限", "功能"):
        lines.append(f"| {label} | {counts.get(label, 0)} |")
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


def _md_cell(value: object) -> str:
    return str(value or "—").replace("|", "／").replace("\n", " ").strip() or "—"


def _customer_refs(cap: dict[str, Any]) -> list[str]:  # noqa: ANY_OK
    refs: list[str] = []
    for ev in cap.get("evidence", []):
        if ev.get("kind") != "doc":
            continue
        ref = str(ev.get("ref", "")).strip()
        if ref.startswith("customer:"):
            ref = ref.replace("customer:", "", 1).strip()
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _handoff_priority(cap: dict[str, Any]) -> str:  # noqa: ANY_OK
    status = str(cap.get("reconciled_status", "missing"))
    customers = _customer_refs(cap)
    evidence_count = len(cap.get("evidence", []))
    if status == "missing" and len(customers) >= 2:
        return "P0"
    if status == "partial" and len(customers) >= 2:
        return "P1"
    if status == "missing" and evidence_count >= 1:
        return "P1"
    if status == "partial":
        return "P1"
    return "P2"


def _slugify_change_id(raw: str, fallback_index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if slug:
        return slug[:64]
    return f"prd-gap-{fallback_index:02d}"


def _build_handoff_changes(capabilities: list[dict[str, Any]]) -> list[dict[str, Any]]:  # noqa: ANY_OK
    candidates = [
        cap for cap in capabilities
        if cap.get("gaps") and str(cap.get("reconciled_status", "")) in {"missing", "partial"}
    ]
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    changes: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for idx, cap in enumerate(candidates, 1):
        cap_id = str(cap.get("id") or cap.get("name") or "")
        name = str(cap.get("name") or cap_id or f"gap-{idx}")
        priority = _handoff_priority(cap)
        change_id = _slugify_change_id(cap_id or name, idx)
        base_id = change_id
        suffix = 2
        while change_id in seen_ids:
            tail = f"-{suffix}"
            change_id = f"{base_id[:64 - len(tail)]}{tail}"
            suffix += 1
        seen_ids.add(change_id)
        changes.append({
            "change_id": change_id,
            "title": name,
            "priority": priority,
            "current_status": str(cap.get("reconciled_status", "missing")),
            "confidence": str(cap.get("confidence", "low")),
            "customers": _customer_refs(cap),
            "evidence_count": len(cap.get("evidence", [])),
            "gaps": [str(g) for g in cap.get("gaps", [])],
            "mi_action": (
                "目标项目确认后优先进入本轮 OpenSpec"
                if priority == "P0"
                else "目标项目确认后进入后续 OpenSpec 或 backlog"
            ),
        })
    return sorted(changes, key=lambda c: (priority_rank.get(str(c["priority"]), 9), str(c["change_id"])))


def _render_prd_handoff(inputs: RenderInputs, output_dir: Path) -> str:
    project = str(inputs.reconcile.get("project", "商管系统"))
    capabilities = inputs.reconcile.get("capabilities", [])
    stats = _status_stats(capabilities)
    changes = _build_handoff_changes(capabilities)
    by_priority: dict[str, list[dict[str, Any]]] = {"P0": [], "P1": [], "P2": []}
    for change in changes:
        by_priority.setdefault(str(change["priority"]), []).append(change)

    lines = [
        f"# {project} PRD 实施交接包",
        "",
        "> 本文件由 product-prd-generator 自动生成，供目标业务系统项目（如 `/opt/code/mi`）评估并拆 OpenSpec change。PRD 侧只提供证据、优先级和建议拆分；最终是否新建 change、如何实现、如何验证，由目标项目会话决定。",
        "",
        "## 1. 交接边界",
        "",
        "- PRD 侧负责：目标蓝图、客户/竞品证据、当前能力差距、建议优先级、建议 change 粒度。",
        "- 目标项目侧负责：读取本项目 `AGENTS.md`、`openspec/specs/`、代码和测试基线，确认是否已有覆盖，创建并执行 OpenSpec change。",
        "- 禁止在 PRD 会话中直接修改目标项目代码或创建目标项目 change。",
        "",
        "## 2. 源产物",
        "",
        f"- `产品PRD.md`：{(output_dir / '产品PRD.md').resolve()}",
        f"- `功能清单.md`：{(output_dir / '功能清单.md').resolve()}",
        f"- `差距分析.md`：{(output_dir / '差距分析.md').resolve()}",
        f"- `需求证据表.md`：{(output_dir / '需求证据表.md').resolve()}",
        f"- `suggested-openspec-changes.yaml`：{(output_dir / 'suggested-openspec-changes.yaml').resolve()}",
        f"- `mi-consumption-prompt.md`：{(output_dir / 'mi-consumption-prompt.md').resolve()}",
        "",
        "## 3. 当前能力概览",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
        f"| existing | {stats.get('existing', 0)} |",
        f"| partial | {stats.get('partial', 0)} |",
        f"| missing | {stats.get('missing', 0)} |",
        f"| explicitly-not-do | {stats.get('explicitly-not-do', 0)} |",
        "",
        "## 4. 目标项目执行入口",
        "",
        "| 场景 | 目标项目 Agent | 做法 |",
        "|---|---|---|",
        "| 首版 PRD / 大差异 / 多 change | Prometheus | 先输出 Implementation Plan v1，不直接 `/opsx-ff` |",
        "| 增量 gap / 单个明确缺口 | Sisyphus | 先核对现有 spec/code，再创建一个普通 change |",
        "| change 执行 | Atlas | `/opsx-apply` 后补齐实现、测试、证据 |",
        "| verify 失败 / 根因复杂 | Hephaestus - Deep Agent | 只修当前 change 的失败项 |",
        "",
        "## 5. 建议 OpenSpec 拆分",
        "",
    ]
    if not changes:
        lines.append("当前未发现需要交接给目标项目的 missing/partial gap。")
    for priority in ("P0", "P1", "P2"):
        items = by_priority.get(priority, [])
        lines.extend([f"### {priority}（{len(items)} 项）", ""])
        if not items:
            lines.extend(["- （无）", ""])
            continue
        lines.append("| 建议 change id | 能力 | 当前状态 | 客户证据 | gap 摘要 |")
        lines.append("|---|---|---|---|---|")
        for item in items:
            customers = ", ".join(item["customers"][:4]) if item["customers"] else "—"
            gap_summary = "; ".join(item["gaps"])[:120] or "—"
            lines.append(
                f"| `{_md_cell(item['change_id'])}` | {_md_cell(item['title'])} | {_md_cell(item['current_status'])} | {_md_cell(customers)} | {_md_cell(gap_summary)} |"
            )
        lines.append("")
    lines.extend([
        "## 6. 回写要求",
        "",
        "目标项目 change 归档后，PRD 侧应回写：",
        "",
        "1. 更新 `功能清单.md` / 覆盖度矩阵中的状态。",
        "2. 在 `差距分析.md` 或增量 gap 报告中标注已处理、合并、暂缓或误判。",
        "3. 如发现 code_map 漏扫，优先修 code_map / ontology 映射，不把漏扫误写成新需求。",
        "",
    ])
    return "\n".join(lines)


def _render_mi_consumption_prompt(project: str, output_dir: Path) -> str:
    handoff = (output_dir / "PRD实施交接包.md").resolve()
    changes = (output_dir / "suggested-openspec-changes.yaml").resolve()
    return f"""# MI / 目标项目消费提示词

在目标项目目录（如 `/opt/code/mi`）启动 OpenCode 后使用。

```text
请先读取当前项目 AGENTS.md、openspec/specs/、相关代码和测试基线，再消费 PRD 交接包，不要直接创建 change。

PRD 项目：{project}
PRD 实施交接包：{handoff}
建议 OpenSpec 拆分：{changes}

请先输出目标项目 Implementation Plan v1：
1) 哪些 gap 已被现有 spec/code 覆盖，只是 PRD code_map 漏判
2) 哪些是真缺口，按 P0/P1/P2 分级
3) 哪些建议合并成一个 change，哪些必须拆开
4) 建议的普通 <CHANGE_ID> 清单、依赖顺序、验收标准和回归范围
5) 哪些问题需要我确认

如果 P0/P1 项超过 3 个、存在跨模块依赖或需要多轮迁移，请使用 Prometheus 先规划；如果只是单个明确缺口，请切 Sisyphus 创建普通 OpenSpec change。
等我确认 Plan 后，再创建或更新 OpenSpec change。
```
"""


def _write_handoff_outputs(inputs: RenderInputs, output_dir: Path) -> None:
    project = str(inputs.reconcile.get("project", "商管系统"))
    capabilities = inputs.reconcile.get("capabilities", [])
    changes = _build_handoff_changes(capabilities)
    payload = {
        "project": project,
        "generated_by": "product-prd-generator",
        "handoff_boundary": "PRD side provides evidence and suggested grouping; target project owns OpenSpec decisions and implementation.",
        "source_files": {
            "prd": "产品PRD.md",
            "feature_list": "功能清单.md",
            "gap_analysis": "差距分析.md",
            "evidence_table": "需求证据表.md",
        },
        "changes": changes,
    }
    (output_dir / "PRD实施交接包.md").write_text(
        _render_prd_handoff(inputs, output_dir), encoding="utf-8"
    )
    (output_dir / "suggested-openspec-changes.yaml").write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (output_dir / "mi-consumption-prompt.md").write_text(
        _render_mi_consumption_prompt(project, output_dir), encoding="utf-8"
    )


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
    kind_order = {"合同条款组": 0, "合同字段": 1, "数据结构": 2, "流程": 3, "权限": 4, "功能": 5}
    reqs_sorted = sorted(
        requirements,
        key=lambda r: (
            kind_order.get(_structure_kind_label(str(r.get("kind", "feature"))), 4),
            priority_order.get(r.get("priority", "低"), 3),
            r.get("scenario", ""),
            r.get("sub_scenario", ""),
        ),
    )
    kind_counts = Counter(_structure_kind_label(str(r.get("kind", "feature"))) for r in reqs_sorted)
    high = sum(1 for r in reqs_sorted if r.get("priority") == "高")
    med = sum(1 for r in reqs_sorted if r.get("priority") == "中")
    low = sum(1 for r in reqs_sorted if r.get("priority") == "低")
    lines = [
        "## 3.5 需求清单（六维框架）",
        "",
        f"结构分布：合同条款组 {kind_counts.get('合同条款组', 0)} / 合同字段 {kind_counts.get('合同字段', 0)} / 数据结构 {kind_counts.get('数据结构', 0)} / 流程 {kind_counts.get('流程', 0)} / 权限 {kind_counts.get('权限', 0)} / 功能 {kind_counts.get('功能', 0)}。",
        f"共 {len(reqs_sorted)} 条需求。优先级分布：高 {high} / 中 {med} / 低 {low}。",
        f"本节列出前 100 条（按优先级排序），完整清单见 [需求清单.md](需求清单.md)。",
        "",
        "| 类型 | 场景 | 子场景 | 功能 | 条款路径 | 痛点/描述 | 来源 | 优先级 | 代码状态 | 匹配能力 |",
        "|------|------|--------|------|------|-----------|------|--------|---------|---------|",
    ]
    for req in reqs_sorted[:100]:
        kind = _structure_kind_label(str(req.get("kind", "feature")))
        scenario = req.get("scenario", "未分类")
        sub = req.get("sub_scenario", "") or "—"
        func = req.get("function", "")
        clause_path = req.get("clause_path", "") or "—"
        nearby = req.get("nearby_text", "") or "—"
        if len(nearby) > 60:
            nearby = nearby[:60] + "…"
        customer = req.get("source_customer", "") or "—"
        priority = req.get("priority", "低")
        status = req.get("code_status", "unmatched")
        matched = req.get("matched_capability", "") or "—"
        lines.append(f"| {kind} | {scenario} | {sub} | {func} | {clause_path} | {nearby} | {customer} | {priority} | {status} | {matched} |")
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
        "| 类型 | 场景 | 子场景 | 功能 | 条款路径 | 痛点/描述 | 来源 | 优先级 | 代码状态 | 匹配能力 |",
        "|------|------|--------|------|------|-----------|------|--------|---------|---------|",
    ]
    for req in reqs_sorted:
        kind = _structure_kind_label(str(req.get("kind", "feature")))
        scenario = req.get("scenario", "未分类")
        sub = req.get("sub_scenario", "") or "—"
        func = req.get("function", "")
        clause_path = req.get("clause_path", "") or "—"
        nearby = req.get("nearby_text", "") or "—"
        if len(nearby) > 80:
            nearby = nearby[:80] + "…"
        customer = req.get("source_customer", "") or "—"
        priority = req.get("priority", "低")
        status = req.get("code_status", "unmatched")
        matched = req.get("matched_capability", "") or "—"
        lines.append(f"| {kind} | {scenario} | {sub} | {func} | {clause_path} | {nearby} | {customer} | {priority} | {status} | {matched} |")
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
        kind = _structure_kind_label(str(req.get("kind", "feature")))
        func = req.get("function", "")
        scenario = req.get("scenario", "未分类")
        sub = req.get("sub_scenario", "")
        clause_path = req.get("clause_path", "")
        nearby = req.get("nearby_text", "")
        customer = req.get("source_customer", "") or "未知"
        status = req.get("code_status", "unmatched")
        matched = req.get("matched_capability", "") or "未匹配"
        lines.append(f"## {i}. {func}")
        lines.append(f"- 类型：{kind}")
        lines.append(f"- 场景：{scenario}" + (f" > {sub}" if sub else ""))
        if clause_path:
            lines.append(f"- 条款路径：{clause_path}")
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


def _render_mod_tables(mod_tables: list[TableMeta]) -> list[str]:
    if not mod_tables:
        return []
    lines = [
        f"**数据模型**（{len(mod_tables)} 张表）：",
        "",
        "| 表名 | 中文名 | 字段数 | 关键字段 |",
        "| --- | --- | --- | --- |",
    ]
    for t in sorted(mod_tables, key=lambda x: x.name):
        kf = pick_key_fields(t.fields)
        lines.append(f"| `{t.name}` | {t.cn} | {len(t.fields)} | {kf or '—'} |")
    lines.append("")
    return lines


def _render_blueprint_modules(
    requirements: list[dict[str, Any]],  # noqa: ANY_OK
    capabilities: list[dict[str, Any]],  # noqa: ANY_OK
    ontology: dict[str, Any],  # noqa: ANY_OK
    tables_by_module: dict[str, list[TableMeta]] | None = None,
) -> str:
    """Render PRD by business module — blueprint style with field-level specs."""
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

    # Load field specs for resource management
    field_specs = _load_field_specs()

    for idx, (mod_name, mod_data) in enumerate(modules.items()):
        if not isinstance(mod_data, dict):
            continue
        reqs = module_reqs.get(mod_name, [])
        sub_funcs = mod_data.get("sub_functions", {})
        mod_cap_ids: set[str] = set()
        for sub in sub_funcs.values():
            if isinstance(sub, dict):
                mod_cap_ids.update(str(c) for c in sub.get("capabilities", []))
        mod_caps = [cap_by_id[c] for c in mod_cap_ids if c in cap_by_id]
        existing_count = sum(1 for c in mod_caps if c.get("reconciled_status") == "existing")
        missing_count = sum(1 for c in mod_caps if c.get("reconciled_status") == "missing")
        mod_tables = (tables_by_module or {}).get(mod_name, [])
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
        header = f"**需求**：{len(reqs)} 条 | **能力**：{len(mod_caps)} 项（✅{existing_count} / ❌{missing_count}）"
        if mod_tables:
            header += f" | **数据表**：{len(mod_tables)} 张"
        lines.append(header)
        lines.append("")
        if reqs:
            kind_counts = Counter(_structure_kind_label(str(req.get("kind", "feature"))) for req in reqs)
            lines.append(
                f"**结构类型**：数据结构 {kind_counts.get('数据结构', 0)} / 流程 {kind_counts.get('流程', 0)} / 权限 {kind_counts.get('权限', 0)} / 功能 {kind_counts.get('功能', 0)}"
            )
            lines.append("")

        # If field specs exist for this module's sub_functions, render field-level tables
        mod_has_specs = field_specs and any(
            sub_name in field_specs or sub_name.removesuffix("管理") in field_specs
            for sub_name in sub_funcs
        )
        if mod_has_specs:
            for sub_name, sub_data in sub_funcs.items():
                if not isinstance(sub_data, dict):
                    continue
                spec = field_specs.get(sub_name) or field_specs.get(sub_name.removesuffix("管理"))
                if spec and isinstance(spec, dict):
                    lines.extend(_render_field_spec_module(sub_name, spec, cap_by_id))
                else:
                    cap_ids = sub_data.get("capabilities", [])
                    if cap_ids:
                        cap = cap_by_id.get(str(cap_ids[0]))
                        if cap:
                            status = str(cap.get("reconciled_status", "missing"))
                            icon = _STATUS_ICON.get(status, "✅")
                            lines.append(f"#### {sub_name}")
                            lines.append(f"- {icon} {cap.get('name', cap_ids[0])[:30]}")
                            lines.append("")
            lines.extend(_render_mod_tables(mod_tables))
            lines.append("---")
            lines.append("")
            continue

        # Otherwise: group requirements by sub_function (existing approach)
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
            sub_role = str(sub_data.get("role", "—"))
            curated = sub_data.get("scenarios", [])
            lines.append(f"#### {sub_name}" + (f"（{sub_role}）" if sub_role != "—" else ""))
            lines.append("")

            if curated and isinstance(curated, list):
                for sc in curated:
                    if not isinstance(sc, dict):
                        continue
                    sc_name = str(sc.get("name", ""))
                    sc_desc = str(sc.get("description", ""))
                    sc_source = str(sc.get("source", ""))
                    cap_ids = sub_data.get("capabilities", [])
                    cap = cap_by_id.get(str(cap_ids[0])) if cap_ids else None
                    status = str(cap.get("reconciled_status", "existing")) if cap else "existing"
                    icon = _STATUS_ICON.get(status, "✅")
                    lines.append(f"> **{sc_name}**")
                    lines.append(f"> {sc_desc}")
                    if sc_source:
                        lines.append(f"> — 来源：{sc_source} | 状态：{icon} {status}")
                    lines.append("")
                if sub_r:
                    lines.append("*客户需求证据*：")
                    seen_t: set[str] = set()
                    for req in sorted(sub_r, key=lambda r: r.get("priority", "低"))[:5]:
                        term = req.get("normalized_term", "")
                        if term in seen_t:
                            continue
                        seen_t.add(term)
                        func = str(req.get("function", ""))[:30]
                        customer = str(req.get("source_customer", "")) or "—"
                        lines.append(f"- {func}（{customer}）")
                    lines.append("")
            elif sub_r:
                lines.append("| 类型 | 角色 | 场景 | 场景描述 | 状态 | 来源 | 端点 |")
                lines.append("|------|------|------|---------|------|------|------|")
                seen_t2: set[str] = set()
                for req in sorted(sub_r, key=lambda r: r.get("priority", "低")):
                    term = req.get("normalized_term", "")
                    if term in seen_t2:
                        continue
                    seen_t2.add(term)
                    kind = _structure_kind_label(str(req.get("kind", "feature")))
                    func = str(req.get("function", ""))[:30].replace("|", "／")
                    nearby = str(req.get("nearby_text", ""))[:50].replace("|", "／").replace("\n", " ") or "—"
                    combined_text = str(req.get("nearby_text", "")) + " " + str(req.get("function", ""))
                    depts = _extract_depts(combined_text)
                    desc_s = f"{func}：{nearby[:40]}" if nearby != "—" else func
                    status = str(req.get("code_status", "unmatched"))
                    icon = _STATUS_ICON.get(status, "🔍")
                    customer = str(req.get("source_customer", "")) or "—"
                    platform = _infer_platform(combined_text)
                    lines.append(f"| {kind} | {depts} | {sub_name} | {desc_s} | {icon} {status} | {customer} | {platform} |")
                lines.append("")
                gaps = [req for req in sub_r if req.get("code_status") in ("missing", "unmatched")]
                if gaps:
                    gap_funcs = sorted(set(str(r.get("function", ""))[:25] for r in gaps))[:8]
                    if gap_funcs:
                        lines.append(f"**差距**：{', '.join(gap_funcs)}")
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

        if ungrouped:
            ungrouped_funcs = sorted(set(str(r.get("function", ""))[:25] for r in ungrouped))[:10]
            if ungrouped_funcs:
                lines.append(f"**其他**：{', '.join(ungrouped_funcs)}")
                lines.append("")
        lines.extend(_render_mod_tables(mod_tables))
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def _load_field_specs() -> dict[str, Any]:  # noqa: ANY_OK
    import os
    base = Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk")) / "knowledge"
    specs: dict[str, Any] = {}  # noqa: ANY_OK
    # Source 1: resource-field-specs.yaml (flat entity keys)
    p1 = base / "resource-field-specs.yaml"
    if p1.is_file():
        data = yaml.safe_load(p1.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            specs.update(data)
    # Source 2: module-field-specs.yaml (nested module→entity, flatten)
    p2 = base / "module-field-specs.yaml"
    if p2.is_file():
        data = yaml.safe_load(p2.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for entities in data.values():
                if isinstance(entities, dict):
                    specs.update(entities)
    return specs


def _render_field_spec_module(
    resource_name: str,
    spec: dict[str, Any],  # noqa: ANY_OK
    cap_by_id: dict[str, dict[str, Any]],  # noqa: ANY_OK
) -> list[str]:
    """Render document-driven field specs: 实体→部门→单据→字段→约束→流程."""
    lines: list[str] = []
    role = str(spec.get("role", "—"))
    documents = spec.get("documents", {})

    lines.append(f"#### {resource_name}")
    lines.append(f"相关部门：{role}")
    lines.append("")

    if not documents:
        fields = spec.get("fields", [])
        if fields:
            lines.extend(_render_field_table(fields))
        return lines

    for doc_name, doc_data in documents.items():
        if not isinstance(doc_data, dict):
            continue
        scenario = str(doc_data.get("scenario", ""))
        fields = doc_data.get("fields", [])
        constraints = doc_data.get("constraints", [])
        workflow = str(doc_data.get("workflow", ""))

        lines.append(f"##### {doc_name}")
        lines.append("")
        if scenario:
            lines.append(f"**场景**：{scenario}")
            lines.append("")

        if fields:
            lines.extend(_render_field_table(fields))

        markdown_blocks = doc_data.get("markdown", [])
        if markdown_blocks:
            for block in markdown_blocks:
                if isinstance(block, str):
                    lines.append(block)
            lines.append("")

        if constraints:
            lines.append("**约束**：")
            lines.append("")
            for c in constraints:
                if isinstance(c, str):
                    lines.append(f"- {c}")
            lines.append("")

        delete_rule = str(doc_data.get("delete_rule", spec.get("delete_rule", "")))
        if delete_rule:
            lines.append(f"**删除规则**：{delete_rule}")
            lines.append("")

        doc_sources = doc_data.get("sources", [])
        if doc_sources:
            lines.append("**来源参考**：")
            for s in doc_sources:
                lines.append(f"- {s}")
            lines.append("")

        if workflow:
            lines.append(f"**流程**：{workflow}")
            lines.append("")

    return lines


def _render_field_table(fields: list[dict[str, Any]]) -> list[str]:  # noqa: ANY_OK
    lines = [
        "| 字段 | 类型 | 必填 | 可修改 | 用途 |",
        "|------|------|------|--------|------|",
    ]
    for f in fields:
        if not isinstance(f, dict):
            continue
        fname = str(f.get("name", ""))
        ftype = str(f.get("type", ""))
        req = "✅" if f.get("required") else "选填"
        edit = "✅" if f.get("editable") else "❌"
        fdesc = str(f.get("desc", ""))[:55]
        lines.append(f"| {fname} | {ftype} | {req} | {edit} | {fdesc} |")
    lines.append("")
    return lines


def _render_data_model_index(tables_by_module: dict[str, list[TableMeta]], unmatched: list[TableMeta]) -> str:
    if not tables_by_module and not unmatched:
        return ""
    total = sum(len(v) for v in tables_by_module.values()) + len(unmatched)
    lines = [
        "## 3A. 数据模型汇总",
        "",
        f"> 海鼎 CRE 4.1.0 数据字典共 {total} 张表，已融合到各业务模块（3.1-3.12）。本节为索引。",
        "",
        "| 模块 | 表数 |",
        "| --- | --- |",
    ]
    for mod, tables in sorted(tables_by_module.items(), key=lambda x: -len(x[1])):
        lines.append(f"| {mod} | {len(tables)} |")
    if unmatched:
        lines.append(f"| 其他（未归类） | {len(unmatched)} |")
    lines.extend(["", "---", ""])
    return "\n".join(lines)


def render_prd(inputs: RenderInputs) -> str:
    project = inputs.reconcile.get("project", "商管系统")
    capabilities = inputs.reconcile.get("capabilities", [])
    requirements = inputs.reconcile.get("requirements", [])
    stats = _status_stats(capabilities)
    ontology = _load_ontology()
    all_tables = parse_data_dict_files(inputs.docs_root)
    tables_by_mod = group_by_module(all_tables)
    unmatched_tables = get_unmatched(all_tables)
    review_brief = render_review_brief(ReviewBriefInput(
        project=str(project),
        status_stats=stats,
        requirement_count=len(requirements),
        tables_by_module=tables_by_mod,
        unmatched_table_count=len(unmatched_tables),
    ))
    parts = [
        f"# {project} 产品 PRD\n",
        review_brief,
        _render_project_context(str(project), stats),
        _render_customer_summary(inputs.doc_map),
        _render_structure_summary(requirements),
        _render_blueprint_modules(requirements, capabilities, ontology, tables_by_mod) if ontology else _render_requirement_list(requirements),
        _render_data_model_index(tables_by_mod, unmatched_tables),
        _render_approval_flow_evidence(requirements, inputs.docs_root),
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
    parser.add_argument("--docs-root", default="")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    doc_map_path = args.doc_map if args.doc_map else None
    inputs = _load_inputs(args.reconcile, doc_map_path, args.docs_root)
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
    _write_handoff_outputs(inputs, output_dir)

    print(f"rendered 9 files to {output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
