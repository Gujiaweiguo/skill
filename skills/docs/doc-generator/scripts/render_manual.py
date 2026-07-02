#!/usr/bin/env python3
"""render_manual.py — Pure-function renderer for doc-generator skill."""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Template


class SchemaError(Exception):
    """Raised when an input file does not match the expected schema."""


class ConsistencyError(Exception):
    """Raised when generated outputs disagree with the shared IR."""


DEFAULT_FINGERPRINT = {
    "chapter_depth": 2,
    "step_density": "medium",
    "screenshot_frequency": "medium",
    "table_preference": "minimal",
    "faq_style": "short",
    "sources": {
        "chapter_depth": "default",
        "step_density": "default",
        "screenshot_frequency": "default",
        "table_preference": "default",
        "faq_style": "default",
    },
}

DISCOVERED_VIA = {"menu", "sidebar", "router_state", "source_hint"}
ELEMENT_TYPES = {"button", "input", "select", "table", "link", "modal"}
ACTION_STATUSES = {"success", "failed", "skipped"}
LOCATOR_STRATEGIES = {"text", "role", "placeholder", "label"}
FINGERPRINT_ENUMS = {
    "step_density": {"low", "medium", "high"},
    "screenshot_frequency": {"low", "medium", "high"},
    "table_preference": {"none", "minimal", "heavy"},
    "faq_style": {"none", "short", "detailed"},
}

MARKDOWN_TEMPLATE_STRING = """# {{ app_name }} 操作手册

> 版本：v{{ version }}
> 生成时间：{{ generated_at }}
> 适用于：{{ framework_hint or "Web 应用" }} 版本

---

## 一、快速开始

{{ app_purpose }}

---

{% if chapter_depth == 1 %}
{% for route in routes %}
## 模块{{ route.module_index }}：{{ route.title }}

访问路径：`{{ route.path }}`

{% if route.rendered_steps %}
{% for step in route.rendered_steps %}
**步骤{{ loop.index }}：{{ step.description }}**

{% if step.screenshot.status == "success" %}
![{{ step.description }}]({{ step.screenshot.path }})
> 图示：{{ step.description }}
{% elif step.screenshot.status == "failed" %}
> ⚠️ 截图失败：{{ step.screenshot.error }}（步骤 {{ loop.index }}）
{% endif %}

{% endfor %}
{% else %}
暂无可操作步骤。
{% endif %}
{% if table_preference != "none" and route.elements %}
{% if table_preference == "heavy" %}
| 元素 | 类型 | 用途 | 选择器提示 | 默认值 |
|------|------|------|------------|--------|
{% for element in route.elements %}| {{ element.text }} | {{ element.type }} | {{ element.action or "—" }} | {{ element.locator_hint or "—" }} | {{ element.default_value or "—" }} |
{% endfor %}
{% else %}
| 元素 | 类型 | 用途 |
|------|------|------|
{% for element in route.elements %}| {{ element.text }} | {{ element.type }} | {{ element.action or "—" }} |
{% endfor %}
{% endif %}
{% endif %}

---

{% endfor %}
{% else %}
## 二、功能模块详解

{% for route in routes %}
### 模块{{ route.module_index }}：{{ route.title }}

{% if chapter_depth >= 2 %}#### {{ route.module_index }}.1 页面入口{% endif %}

访问路径：`{{ route.path }}`

{% if chapter_depth >= 2 %}#### {{ route.module_index }}.2 操作步骤{% endif %}

{% if route.rendered_steps %}
{% for step in route.rendered_steps %}
{% if chapter_depth >= 3 %}#### 步骤{{ loop.index }}：{{ step.description }}{% else %}**步骤{{ loop.index }}：{{ step.description }}**{% endif %}

{% if step.screenshot.status == "success" %}
![{{ step.description }}]({{ step.screenshot.path }})
> 图示：{{ step.description }}
{% elif step.screenshot.status == "failed" %}
> ⚠️ 截图失败：{{ step.screenshot.error }}（步骤 {{ loop.index }}）
{% endif %}

{% endfor %}
{% else %}
暂无可操作步骤。
{% endif %}
{% if table_preference != "none" %}
{% if chapter_depth >= 2 %}#### {{ route.module_index }}.3 界面元素说明{% endif %}

{% if route.elements %}
{% if table_preference == "heavy" %}
| 元素 | 类型 | 用途 | 选择器提示 | 默认值 |
|------|------|------|------------|--------|
{% for element in route.elements %}| {{ element.text }} | {{ element.type }} | {{ element.action or "—" }} | {{ element.locator_hint or "—" }} | {{ element.default_value or "—" }} |
{% endfor %}
{% else %}
| 元素 | 类型 | 用途 |
|------|------|------|
{% for element in route.elements %}| {{ element.text }} | {{ element.type }} | {{ element.action or "—" }} |
{% endfor %}
{% endif %}
{% else %}
暂无界面元素说明。
{% endif %}
{% endif %}

---

{% endfor %}
{% endif %}
{% if faq_style != "none" %}
## 三、常见问题（FAQ）

{% for faq in faqs %}
**Q{{ loop.index }}：{{ faq.question }}**
A：{{ faq.answer }}
{% if faq_style == "detailed" %}

补充说明：可结合上述模块步骤与截图定位相关功能入口。
{% endif %}

{% endfor %}
---

{% endif %}
## 四、附录

### 4.1 快捷键说明
（若代码中绑定键盘事件，在此列出；否则本节为空）

### 4.2 环境要求
- 浏览器：Chrome 最新版 / Edge 最新版
- 分辨率建议：1920x1080
"""


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise SchemaError(f"{path}: JSON 解析失败: {e}") from e
    except OSError as e:
        raise SchemaError(f"{path}: 无法读取文件: {e}") from e
    if not isinstance(data, dict):
        raise SchemaError(f"{path}: 顶层必须是对象")
    return data


def require_type(data: dict[str, Any], key: str, typ: type | tuple[type, ...], ctx: str) -> Any:
    if key not in data:
        raise SchemaError(f"{ctx}: 缺少字段 {key}")
    value = data[key]
    if typ is bool:
        ok = isinstance(value, bool)
    elif typ is int:
        ok = isinstance(value, int) and not isinstance(value, bool)
    else:
        ok = isinstance(value, typ)
    if not ok:
        expected = typ.__name__ if isinstance(typ, type) else "/".join(t.__name__ for t in typ)
        raise SchemaError(f"{ctx}.{key}: 必须是 {expected}")
    return value


def require_optional_str(data: dict[str, Any], key: str, ctx: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise SchemaError(f"{ctx}.{key}: 必须是 string|null")
    return value


def element_text(element: dict[str, Any]) -> str:
    for key in ("text", "placeholder", "aria_label"):
        value = element.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def validate_locator(locator: Any, ctx: str, required: bool) -> None:
    if locator is None and not required:
        return
    if not isinstance(locator, dict):
        raise SchemaError(f"{ctx}: 必须是对象")
    strategy = require_type(locator, "strategy", str, ctx)
    require_type(locator, "value", str, ctx)
    if strategy not in LOCATOR_STRATEGIES:
        raise SchemaError(f"{ctx}.strategy: 非法值 {strategy}")


def validate_analysis(data: dict[str, Any]) -> None:
    ctx = "analysis"
    require_type(data, "app_name", str, ctx)
    require_type(data, "version", str, ctx)
    require_optional_str(data, "framework_hint", ctx)
    require_type(data, "dev_server_url", str, ctx)
    if "app_purpose" in data:
        require_type(data, "app_purpose", str, ctx)
    routes = require_type(data, "routes", list, ctx)
    for i, route in enumerate(routes, 1):
        rctx = f"analysis.routes[{i}]"
        if not isinstance(route, dict):
            raise SchemaError(f"{rctx}: 必须是对象")
        require_type(route, "path", str, rctx)
        require_type(route, "title", str, rctx)
        require_type(route, "accessible", bool, rctx)
        discovered = require_type(route, "discovered_via", str, rctx)
        if discovered not in DISCOVERED_VIA:
            raise SchemaError(f"{rctx}.discovered_via: 非法值 {discovered}")
        elements = require_type(route, "elements", list, rctx)
        element_ids: set[str] = set()
        for j, element in enumerate(elements, 1):
            ectx = f"{rctx}.elements[{j}]"
            if not isinstance(element, dict):
                raise SchemaError(f"{ectx}: 必须是对象")
            eid = require_type(element, "element_id", str, ectx)
            if eid in element_ids:
                raise SchemaError(f"{ectx}.element_id: 重复值 {eid}")
            element_ids.add(eid)
            etype = require_type(element, "type", str, ectx)
            if etype not in ELEMENT_TYPES:
                raise SchemaError(f"{ectx}.type: 非法值 {etype}")
            if not element_text(element):
                raise SchemaError(f"{ectx}: 必须包含 text/placeholder/aria_label 之一")
            require_optional_str(element, "action", ectx)
        flows = require_type(route, "flows", list, rctx)
        flow_ids: set[str] = set()
        for j, flow in enumerate(flows, 1):
            fctx = f"{rctx}.flows[{j}]"
            if not isinstance(flow, dict):
                raise SchemaError(f"{fctx}: 必须是对象")
            fid = require_type(flow, "flow_id", str, fctx)
            if fid in flow_ids:
                raise SchemaError(f"{fctx}.flow_id: 重复值 {fid}")
            flow_ids.add(fid)
            require_type(flow, "name", str, fctx)
            steps = require_type(flow, "steps", list, fctx)
            for k, step in enumerate(steps, 1):
                sctx = f"{fctx}.steps[{k}]"
                if not isinstance(step, dict):
                    raise SchemaError(f"{sctx}: 必须是对象")
                require_type(step, "action", str, sctx)
                eid = require_type(step, "element_id", str, sctx)
                if eid not in element_ids:
                    raise SchemaError(f"{sctx}.element_id: 未在 elements 中定义: {eid}")
                require_type(step, "expected_outcome", str, sctx)
    auth = data.get("auth")
    if auth is not None:
        if not isinstance(auth, dict):
            raise SchemaError("analysis.auth: 必须是对象或 null")
        require_type(auth, "login_route", str, "analysis.auth")
        require_type(auth, "post_login_route", str, "analysis.auth")
        fields = require_type(auth, "form_fields", list, "analysis.auth")
        for i, field in enumerate(fields, 1):
            fctx = f"analysis.auth.form_fields[{i}]"
            if not isinstance(field, dict):
                raise SchemaError(f"{fctx}: 必须是对象")
            require_type(field, "name", str, fctx)
            if "placeholder" in field:
                require_type(field, "placeholder", str, fctx)
            require_type(field, "type", str, fctx)
    faqs = require_type(data, "faqs", list, ctx)
    for i, faq in enumerate(faqs, 1):
        qctx = f"analysis.faqs[{i}]"
        if not isinstance(faq, dict):
            raise SchemaError(f"{qctx}: 必须是对象")
        require_type(faq, "question", str, qctx)
        require_type(faq, "answer", str, qctx)
    generated_at = require_type(data, "generated_at", str, ctx)
    try:
        datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except ValueError as e:
        raise SchemaError("analysis.generated_at: 必须是 ISO 8601 字符串") from e


def validate_manifest(data: dict[str, Any]) -> None:
    ctx = "manifest"
    require_type(data, "app_name", str, ctx)
    require_optional_str(data, "executor_error", ctx)
    tasks = require_type(data, "tasks", list, ctx)
    for i, task in enumerate(tasks, 1):
        tctx = f"manifest.tasks[{i}]"
        if not isinstance(task, dict):
            raise SchemaError(f"{tctx}: 必须是对象")
        require_type(task, "task_id", str, tctx)
        require_type(task, "page_title", str, tctx)
        require_type(task, "url", str, tctx)
        actions = require_type(task, "actions", list, tctx)
        for j, action in enumerate(actions, 1):
            actx = f"{tctx}.actions[{j}]"
            if not isinstance(action, dict):
                raise SchemaError(f"{actx}: 必须是对象")
            require_type(action, "action_id", str, actx)
            require_type(action, "type", str, actx)
            status = require_type(action, "status", str, actx)
            if status not in ACTION_STATUSES:
                raise SchemaError(f"{actx}.status: 非法值 {status}")
            atype = action.get("type")
            # Per screenshot-plan-schema.md: only fill/click/hover/select/assert
            # target a DOM element. navigate/screenshot/wait/scroll do not.
            LOCATOR_REQUIRED_TYPES = {"fill", "click", "hover", "select", "assert"}
            requires_locator = atype in LOCATOR_REQUIRED_TYPES
            if atype == "screenshot":
                require_type(action, "output_path", str, actx)
            elif "output_path" in action and action["output_path"] is not None:
                require_type(action, "output_path", str, actx)
            validate_locator(
                action.get("primary_locator"),
                f"{actx}.primary_locator",
                required=requires_locator,
            )
            validate_locator(
                action.get("resolved_locator"),
                f"{actx}.resolved_locator",
                required=False,
            )
            require_type(action, "elapsed_ms", int, actx)
            if status == "failed":
                require_type(action, "error", str, actx)
            elif "error" in action and action["error"] is not None:
                require_type(action, "error", str, actx)


def validate_fingerprint(data: dict[str, Any]) -> None:
    ctx = "style-fingerprint"
    depth = require_type(data, "chapter_depth", int, ctx)
    if depth not in {1, 2, 3}:
        raise SchemaError("style-fingerprint.chapter_depth: 必须是 1、2 或 3")
    for key, valid in FINGERPRINT_ENUMS.items():
        value = require_type(data, key, str, ctx)
        if value not in valid:
            raise SchemaError(f"style-fingerprint.{key}: 非法值 {value}")
    sources = require_type(data, "sources", dict, ctx)
    for key in ("chapter_depth", *FINGERPRINT_ENUMS.keys()):
        if key in sources and not isinstance(sources[key], str):
            raise SchemaError(f"style-fingerprint.sources.{key}: 必须是字符串")


def normalize_fingerprint(data: dict[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(DEFAULT_FINGERPRINT))
    for key in ("chapter_depth", "step_density", "screenshot_frequency", "table_preference", "faq_style"):
        if key in data:
            merged[key] = data[key]
    sources = data.get("sources")
    if isinstance(sources, dict):
        merged["sources"].update(sources)
    validate_fingerprint(merged)
    return merged


def slugify(text: str) -> str:
    """Kebab-case slug; preserve Chinese characters."""
    value = text.strip().lower().replace("_", "-")
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^0-9a-z\-\u4e00-\u9fff]+", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "section"


def anchor_slug(text: str) -> str:
    value = text.strip().lower()
    value = re.sub(r"\s+", "-", value)
    value = re.sub(r"[^0-9a-z\-\u4e00-\u9fff]+", "", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "section"


def is_low_importance(action: str) -> bool:
    lowered = action.lower()
    return any(token in lowered for token in ("hover", "scroll", "mousemove", "悬停", "滚动"))


def filtered_steps(steps: list[dict[str, Any]], density: str) -> list[dict[str, Any]]:
    if density == "low":
        return [step for step in steps if not is_low_importance(step["action"])] [:3]
    if density == "medium":
        return [step for step in steps if not is_low_importance(step["action"])]
    return steps


def screenshot_record(action: dict[str, Any], manifest: dict[str, Any], title: str) -> dict[str, Any]:
    return {
        "route_title": title,
        "status": action.get("status"),
        "path": action.get("output_path"),
        "error": action.get("error") or manifest.get("executor_error") or "截图失败",
        "action_id": action.get("action_id", ""),
    }


def screenshot_records(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_title: dict[str, dict[str, Any]] = {}
    for task in manifest.get("tasks", []):
        title = str(task.get("page_title", ""))
        for action in task.get("actions", []):
            if action.get("type") != "screenshot":
                continue
            by_title.setdefault(title, screenshot_record(action, manifest, title))
    return by_title


def task_by_route(route: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any] | None:
    route_title = route["title"]
    route_path = route["path"]
    for task in manifest.get("tasks", []):
        if task.get("page_title") == route_title:
            return task
    for task in manifest.get("tasks", []):
        url = str(task.get("url", ""))
        if url.endswith(route_path) or route_path in url:
            return task
    print(f"Warning: no manifest task matched route {route_title}", file=sys.stderr)
    return None


def page_load_screenshot(task: dict[str, Any] | None, manifest: dict[str, Any], title: str) -> dict[str, Any]:
    if task is None:
        return {"status": "failed", "path": None, "error": "未找到对应任务截图", "action_id": ""}
    for action in task.get("actions", []):
        if action.get("type") == "screenshot":
            return screenshot_record(action, manifest, title)
    return {"status": "failed", "path": None, "error": "未找到页面加载截图", "action_id": ""}


def step_screenshot(task: dict[str, Any] | None, manifest: dict[str, Any], title: str, step_number: int) -> dict[str, Any]:
    if task is None:
        return {"status": "failed", "path": None, "error": "未找到对应任务截图", "action_id": ""}
    non_screenshot_seen = 0
    last_success: dict[str, Any] | None = None
    first_failure: dict[str, Any] | None = None
    for action in task.get("actions", []):
        if action.get("type") == "screenshot":
            record = screenshot_record(action, manifest, title)
            if action.get("status") == "success":
                last_success = record
            elif first_failure is None:
                first_failure = record
            continue
        non_screenshot_seen += 1
        if non_screenshot_seen >= step_number:
            return last_success or first_failure or {"status": "none", "path": None, "error": "无前置截图", "action_id": ""}
    return last_success or first_failure or {"status": "none", "path": None, "error": "无前置截图", "action_id": ""}


def step_description(step: dict[str, Any], element_lookup: dict[str, dict[str, Any]]) -> str:
    element = element_lookup.get(step["element_id"], {})
    text = element.get("text", "")
    action = step["action"].strip()
    outcome = step["expected_outcome"].strip()
    if text and text not in action:
        return f"{action}（{text}），{outcome}"
    return f"{action}，{outcome}"


def build_ir(analysis: dict[str, Any], manifest: dict[str, Any], fingerprint: dict[str, Any]) -> dict[str, Any]:
    """Join routes × elements × flows × screenshot outcomes into one tree."""
    page_load_by_title = screenshot_records(manifest)
    routes_ir: list[dict[str, Any]] = []
    for index, route in enumerate(analysis["routes"], 1):
        matched_task = task_by_route(route, manifest)
        elements: list[dict[str, Any]] = []
        element_lookup: dict[str, dict[str, Any]] = {}
        for element in route["elements"]:
            normalized = {
                "element_id": element["element_id"],
                "type": element["type"],
                "text": element_text(element),
                "action": element.get("action"),
                "locator_hint": element_text(element),
                "default_value": element.get("default_value") if isinstance(element.get("default_value"), str) else None,
            }
            elements.append(normalized)
            normalized_id = str(normalized["element_id"])
            element_lookup[normalized_id] = normalized
        first_flow: dict[str, Any] = route["flows"][0] if route["flows"] else {"flow_id": "", "name": "页面浏览", "steps": []}
        steps_ir: list[dict[str, Any]] = []
        flow_steps = first_flow.get("steps", [])
        if not isinstance(flow_steps, list):
            flow_steps = []
        step_density = str(fingerprint["step_density"])
        for step_number, step in enumerate(filtered_steps(flow_steps, step_density), 1):
            shot = step_screenshot(matched_task, manifest, route["title"], step_number)
            element = element_lookup[step["element_id"]]
            steps_ir.append({
                "step_number": step_number,
                "action": step["action"],
                "expected_outcome": step["expected_outcome"],
                "description": step_description(step, element_lookup),
                "element_id": step["element_id"],
                "element_texts": [element["text"]],
                "screenshot": shot if shot.get("status") in {"success", "failed"} else {"status": "failed", "path": None, "error": "截图已跳过", "action_id": ""},
            })
        page_load = page_load_by_title.get(route["title"])
        if page_load is None:
            page_load = page_load_screenshot(matched_task, manifest, route["title"])
        routes_ir.append({
            "module_index": index,
            "path": route["path"],
            "title": route["title"],
            "accessible": route["accessible"],
            "discovered_via": route["discovered_via"],
            "elements": elements,
            "flow": {"flow_id": first_flow.get("flow_id", ""), "name": first_flow.get("name", "页面浏览")},
            "rendered_steps": steps_ir,
            "page_load_screenshot": page_load,
            "module_slug": slugify(route["title"]),
            "anchor": anchor_slug(f"模块{index}{route['title']}"),
        })
    app_purpose = analysis.get("app_purpose") or "本系统用于支撑日常业务操作与信息管理。"
    return {
        "app_name": analysis["app_name"],
        "version": analysis["version"],
        "framework_hint": analysis.get("framework_hint"),
        "generated_at": analysis["generated_at"],
        "app_purpose": app_purpose,
        "routes": routes_ir,
        "faqs": analysis["faqs"],
        "fingerprint": fingerprint,
        "chapter_depth": fingerprint["chapter_depth"],
        "step_density": fingerprint["step_density"],
        "screenshot_frequency": fingerprint["screenshot_frequency"],
        "table_preference": fingerprint["table_preference"],
        "faq_style": fingerprint["faq_style"],
    }


def render_markdown(ir: dict[str, Any], output_path: Path) -> int:
    """Returns line count."""
    content = Template(MARKDOWN_TEMPLATE_STRING).render(**ir)
    output_path.write_text(content, encoding="utf-8")
    return len(content.splitlines())


def screenshot_list(record: dict[str, Any]) -> list[str]:
    if record.get("status") == "success" and isinstance(record.get("path"), str) and record["path"]:
        return [record["path"]]
    return []


def make_chunk_id(app_name: str, module_slug: str, subsection: str, step: int | None) -> str:
    return f"{slugify(app_name)}_{module_slug}_{slugify(subsection)}_{step or 0}"


def question_keywords(question: str) -> list[str]:
    words = [w for w in re.split(r"[\s，。？！、,.!?;；：:（）()]+", question) if w]
    return words[:5] or [question]


def chunks_from_ir(ir: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for route in ir["routes"]:
        element_texts = [element["text"] for element in route["elements"]]
        chunks.append({
            "page_content": f"## {route['title']}\n\n本页面用于{route['flow']['name']}。",
            "metadata": {
                "app_name": ir["app_name"],
                "version": ir["version"],
                "module": route["title"],
                "subsection": "page_load",
                "step": None,
                "page_url": route["path"],
                "screenshots": screenshot_list(route["page_load_screenshot"]),
                "element_texts": element_texts,
                "chunk_id": make_chunk_id(ir["app_name"], route["module_slug"], "page_load", None),
            },
        })
        for step in route["rendered_steps"]:
            step_no = step["step_number"]
            chunks.append({
                "page_content": f"## {route['title']} → {route['flow']['name']}\n\n步骤{step_no}：{step['description']}",
                "metadata": {
                    "app_name": ir["app_name"],
                    "version": ir["version"],
                    "module": route["title"],
                    "subsection": "step",
                    "step": step_no,
                    "page_url": route["path"],
                    "screenshots": screenshot_list(step["screenshot"]),
                    "element_texts": step["element_texts"],
                    "chunk_id": make_chunk_id(ir["app_name"], route["module_slug"], "step", step_no),
                },
            })
    if ir["faq_style"] != "none":
        for i, faq in enumerate(ir["faqs"], 1):
            chunks.append({
                "page_content": f"**Q：{faq['question']}**\n\nA：{faq['answer']}",
                "metadata": {
                    "app_name": ir["app_name"],
                    "version": ir["version"],
                    "module": "常见问题",
                    "subsection": "faq",
                    "step": None,
                    "page_url": "",
                    "screenshots": [],
                    "element_texts": question_keywords(faq["question"]),
                    "chunk_id": make_chunk_id(ir["app_name"], "faq", "faq", i),
                },
            })
    return chunks


def render_chunks(ir: dict[str, Any], output_path: Path) -> int:
    """Returns chunk count."""
    chunks = chunks_from_ir(ir)
    with output_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n")
    return len(chunks)


def route_summary(route: dict[str, Any]) -> str:
    if route["flow"]["name"]:
        return route["flow"]["name"]
    if route["elements"]:
        return "、".join(element["text"] for element in route["elements"][:3])
    return "页面浏览与基础操作"


def render_llms_txt(ir: dict[str, Any], output_path: Path) -> int:
    """Returns line count."""
    lines = [
        f"# {ir['app_name']} 操作手册",
        "",
        f"> {ir['app_purpose']}",
        "",
        "## 快速开始",
        ir["app_purpose"],
        "[查看详情](操作手册.md#一快速开始)",
        "",
        "## 主要功能模块",
    ]
    for route in ir["routes"]:
        lines.append(f"- {route['title']}: {route_summary(route)}")
        lines.append(f"[查看详情](操作手册.md#{route['anchor']})")
    if ir["faq_style"] != "none":
        lines.extend([
            "",
            "## 常见问题",
            "常见问题汇总了用户在操作过程中的高频疑问。",
            "[查看详情](操作手册.md#三常见问题faq)",
        ])
    lines.extend(["", "详细文档请参阅 [操作手册.md](./操作手册.md)"])
    content = "\n".join(lines) + "\n"
    output_path.write_text(content, encoding="utf-8")
    return len(content.splitlines())


def parse_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def verify_consistency(md_path: Path, jsonl_path: Path, txt_path: Path, ir: dict[str, Any]) -> None:
    md = md_path.read_text(encoding="utf-8")
    txt = txt_path.read_text(encoding="utf-8")
    chunks = parse_jsonl(jsonl_path)
    route_count = len(ir["routes"])
    md_modules = len(re.findall(r"^#{2,3} 模块\d+：", md, flags=re.MULTILINE))
    jsonl_modules = {chunk["metadata"]["module"] for chunk in chunks if chunk["metadata"].get("subsection") == "page_load"}
    llms_links = len(re.findall(r"^\[查看详情\]\(操作手册\.md#模块\d+", txt, flags=re.MULTILINE))
    if not (route_count == md_modules == len(jsonl_modules) == llms_links):
        raise ConsistencyError(
            f"模块数量不一致: ir={route_count}, md={md_modules}, jsonl={len(jsonl_modules)}, llms={llms_links}"
        )
    chunk_ids = [chunk["metadata"].get("chunk_id") for chunk in chunks]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ConsistencyError("chunks.jsonl 中 chunk_id 不唯一")
    page_load_chunks = {chunk["metadata"]["module"]: chunk for chunk in chunks if chunk["metadata"].get("subsection") == "page_load"}
    for route in ir["routes"]:
        expected = {element["text"] for element in route["elements"]}
        actual = set(page_load_chunks[route["title"]]["metadata"].get("element_texts", []))
        if expected != actual:
            raise ConsistencyError(f"元素文本不一致: {route['title']}: md/ir={sorted(expected)}, jsonl={sorted(actual)}")
        if ir["table_preference"] != "none":
            for element_text_value in expected:
                if f"| {element_text_value} |" not in md:
                    raise ConsistencyError(f"Markdown 元素表缺少文本: {route['title']} / {element_text_value}")


def ensure_output_dir(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"无法创建输出目录 {path}: {e}") from e
    if not path.is_dir():
        raise OSError(f"输出路径不是目录: {path}")


def write_outputs_atomic(ir: dict[str, Any], output_dir: Path) -> tuple[int, int, int]:
    md_tmp = output_dir / "操作手册.md.tmp"
    jsonl_tmp = output_dir / "chunks.jsonl.tmp"
    txt_tmp = output_dir / "llms.txt.tmp"
    tmp_paths = [md_tmp, jsonl_tmp, txt_tmp]
    final_paths = [output_dir / "操作手册.md", output_dir / "chunks.jsonl", output_dir / "llms.txt"]
    try:
        md_lines = render_markdown(ir, md_tmp)
        chunk_count = render_chunks(ir, jsonl_tmp)
        txt_lines = render_llms_txt(ir, txt_tmp)
        verify_consistency(md_tmp, jsonl_tmp, txt_tmp, ir)
        for tmp, final in zip(tmp_paths, final_paths):
            tmp.rename(final)
        return md_lines, chunk_count, txt_lines
    except Exception:
        for path in tmp_paths:
            if path.exists():
                path.unlink()
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render doc-generator manual outputs from analysis, manifest, and style fingerprint JSON files.")
    parser.add_argument("--analysis", required=True, type=Path, help="Path to analysis.json input file.")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to manifest.json input file.")
    parser.add_argument("--style-fingerprint", required=True, type=Path, help="Path to style-fingerprint.json input file.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Directory for 操作手册.md, chunks.jsonl, and llms.txt outputs.")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    try:
        ensure_output_dir(args.output_dir)
    except OSError as e:
        print(str(e), file=sys.stderr)
        return 2
    try:
        analysis = load_json(args.analysis)
        manifest = load_json(args.manifest)
        fingerprint = normalize_fingerprint(load_json(args.style_fingerprint))
        validate_analysis(analysis)
        validate_manifest(manifest)
        validate_fingerprint(fingerprint)
        if manifest["app_name"] != analysis["app_name"]:
            raise SchemaError("analysis.app_name 与 manifest.app_name 不一致")
    except SchemaError as e:
        print(str(e), file=sys.stderr)
        return 3
    try:
        ir = build_ir(analysis, manifest, fingerprint)
        md_lines, chunk_count, txt_lines = write_outputs_atomic(ir, args.output_dir)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 4
    print(f"Generated: 操作手册.md ({md_lines} lines), chunks.jsonl ({chunk_count} chunks), llms.txt ({txt_lines} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
