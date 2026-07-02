# 操作手册.md Jinja2 Template

This document is the canonical Jinja2 template skeleton for `操作手册.md`. `render_manual.py` loads this template (or a hard-coded equivalent) and renders it against a context built from `analysis.json` + `manifest.json` + `style-fingerprint.json`. The renderer is a pure function: identical inputs produce byte-identical outputs modulo the `generated_at` timestamp.

The template uses Chinese section headers (对齐 spec manual-rendering Requirement: Markdown Manual Template). Every module section is generated from one route in `analysis.json.routes[]`. Failed screenshots render as visible placeholders, never as broken image links.

## Context 变量

renderer 向模板注入以下变量。模板 MUST NOT 假设存在其他变量。

| 变量 | 类型 | 说明 |
|------|------|------|
| `app_name` | string | 来自 `analysis.app_name`。 |
| `version` | string | 来自 `analysis.version`。 |
| `framework_hint` | string | 来自 `analysis.framework_hint`。 |
| `generated_at` | string | 来自 `analysis.generated_at`，ISO 8601 字符串。 |
| `app_purpose` | string | 一句话应用简介。来自 `analysis.app_purpose`；缺失时由 renderer 推断（如 `"{{ app_name }} 是一套 Web 管理系统"`）。 |
| `routes` | array | 经过 renderer 加工的 route 列表。每项结构见下文"Route context"。 |
| `faqs` | array<{question, answer}> | 来自 `analysis.faqs`。renderer 不生成 FAQ，agent 在 P1 阶段写入 `analysis.faqs`。 |
| `shortcuts` | array<{key, action}> | 来自 `analysis.shortcuts`，可为空数组。 |
| `env_requirements` | array<string> | 来自 `analysis.env_requirements`，可为空数组。 |

### Route context

每个 route 在模板中可访问：

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 模块标题，如 `"用户管理"`。 |
| `path` | string | 路由路径。 |
| `accessible` | boolean | 是否可访问。 |
| `accessibility_note` | string \| null | 不可访问时的中文说明，如 `"需管理员权限"`。 |
| `elements` | array<{type, label, usage}> | 渲染好的元素表格行数据。`label` 是元素的可见文本/placeholder。 |
| `flows` | array<Flow context> | 见下文。 |

### Flow context

每个 flow 在模板中可访问：

| 字段 | 类型 | 说明 |
|------|------|------|
| `flow_id` | string | flow ID。 |
| `name` | string | 流程名。 |
| `steps` | array<Step context> | 见下文。 |

### Step context

每个 step 在模板中可访问：

| 字段 | 类型 | 说明 |
|------|------|------|
| `index` | int | 步骤序号，从 1 开始。 |
| `description` | string | 中文操作描述（如 `"点击新建按钮，弹出创建表单"`）。 |
| `screenshot` | string \| null | 截图相对路径（从输出目录起算），如 `"imgs/users_2_create-modal.png"`。截图失败时为 `null`。 |
| `failure_reason` | string \| null | 截图失败时的原因（来自 `manifest.json`），成功时为 `null`。 |

## 模板正文

下列 Jinja2 模板对齐 spec manual-rendering spec 中描述的结构。`{# ... #}` 是 Jinja2 注释，renderer 输出时不会保留。

```jinja2
{# ========== 文档头部 ========== #}
{# H1 标题：app_name + "操作手册"。blockquote 元信息行包含版本/生成日期/框架。 #}
# {{ app_name }} 操作手册

> 版本：{{ version }} | 生成日期：{{ generated_at }} | 框架：{{ framework_hint }}

{# ========== 一、快速开始 ========== #}
{# 一句话介绍应用用途，来自 analysis.app_purpose 或 renderer 推断。 #}
## 一、快速开始

{{ app_purpose }}

{# ========== 二、功能模块详解 ========== #}
{# 遍历 routes，每个 route 生成一个模块章节。loop.index 从 1 开始。 #}
## 二、功能模块详解

{% for route in routes %}
### 模块{{ loop.index }}：{{ route.title }}

{% if not route.accessible %}
> 当前账号无法访问此模块：{{ route.accessibility_note }}

{% endif %}

{# --- N.1 页面入口 --- #}
{# 给出路由路径，方便用户复制粘贴或在浏览器中直接打开。 #}
#### {{ loop.index }}.1 页面入口

访问路径：`{{ route.path }}`

{# --- N.2 操作步骤 --- #}
{# 每个 route 默认展示第一个 flow 的步骤；其他 flow 作为子小节列出（可选，受 step_density 影响）。 #}
{# 步骤循环：对每个 step，若 screenshot 存在则展示图片 + 图示说明，否则展示失败占位符。 #}
#### {{ loop.index }}.2 操作步骤

{% for flow in route.flows %}
{% if route.flows | length > 1 %}
**流程：{{ flow.name }}**

{% endif %}
{% for step in flow.steps %}
**步骤 {{ step.index }}：{{ step.description }}**

{% if step.screenshot %}
![{{ step.description }}]({{ step.screenshot }})

> 图示：{{ step.description }}
{% else %}
> ⚠️ 截图失败：{{ step.failure_reason }}（步骤 {{ step.index }}）
{% endif %}

{% endfor %}
{% endfor %}

{# --- N.3 界面元素说明 --- #}
{# Markdown 表格：元素 / 类型 / 用途。元素来自 route.elements。 #}
#### {{ loop.index }}.3 界面元素说明

| 元素 | 类型 | 用途 |
|------|------|------|
{% for el in route.elements %}
| {{ el.label }} | {{ el.type }} | {{ el.usage }} |
{% endfor %}

{% endfor %}

{# ========== 三、常见问题（FAQ） ========== #}
{# FAQ 来自 agent 在 P1 阶段写入的 analysis.faqs，renderer 不生成内容。 #}
{# 受 style-fingerprint.faq_style 影响："none" 时不输出此章节。 #}
## 三、常见问题（FAQ）

{% for faq in faqs %}
**Q{{ loop.index }}：{{ faq.question }}**

{{ faq.answer }}

{% endfor %}

{# ========== 四、附录 ========== #}
## 四、附录

### 4.1 快捷键说明

{% if shortcuts %}
| 快捷键 | 功能 |
|--------|------|
{% for s in shortcuts %}
| {{ s.key }} | {{ s.action }} |
{% endfor %}
{% else %}
本文档暂未记录快捷键。
{% endif %}

### 4.2 环境要求

{% if env_requirements %}
{% for req in env_requirements %}
- {{ req }}
{% endfor %}
{% else %}
- 现代浏览器（Chrome / Edge / Firefox 最新两个稳定版本）
{% endif %}
```

## 渲染示例（片段）

给定 `app_name = "admin-portal"`、`routes = [{"title": "用户管理", "path": "/users", ...}]`、一个含截图的步骤、一个失败步骤，渲染后片段：

```markdown
# admin-portal 操作手册

> 版本：1.4.2 | 生成日期：2026-06-21T08:30:00Z | 框架：vue3

## 一、快速开始

admin-portal 是一套面向运营团队的用户与权限管理 Web 系统。

## 二、功能模块详解

### 模块1：用户管理

#### 1.1 页面入口

访问路径：`/users`

#### 1.2 操作步骤

**步骤 1：点击"新建"按钮，弹出创建表单**

![点击"新建"按钮，弹出创建表单](imgs/users_1_open-create-modal.png)

> 图示：点击"新建"按钮，弹出创建表单

**步骤 2：填写表单并保存**

> ⚠️ 截图失败：selector timeout（步骤 2）

#### 1.3 界面元素说明

| 元素 | 类型 | 用途 |
|------|------|------|
| 新建 | button | 打开新建用户表单 |
| 请输入用户名 | input | 输入新用户的登录名 |
| 保存 | button | 提交表单并写入后端 |
```

## 校验规则

1. **章节顺序固定**：H2 章节顺序为 `一、快速开始` → `二、功能模块详解` → `三、常见问题（FAQ）` → `四、附录`。MUST NOT 调整顺序。
2. **模块数量一致**：`## 二、功能模块详解` 下 `### 模块N：` 数量 MUST 等于 `analysis.routes` 的长度。
3. **每个模块三个子章节**：每个 `### 模块N` 下 MUST 包含 `#### N.1 页面入口` / `#### N.2 操作步骤` / `#### N.3 界面元素说明` 三个 H4 子章节。
4. **失败截图占位符**：当 `step.screenshot` 为 `null` 时 MUST 输出 `> ⚠️ 截图失败：{reason}（步骤 {index}）`，MUST NOT 输出 `![](...)` 空链接。
5. **成功截图带说明**：成功截图 MUST 同时输出图片语法与 `> 图示：{description}` 引用块。
6. **元素表格列名**：`#### N.3 界面元素说明` 下表格列名 MUST 是 `| 元素 | 类型 | 用途 |`，不可调整。
7. **FAQ 章节受指纹控制**：`style-fingerprint.faq_style === "none"` 时此章节 MUST 不输出（受 renderer 控制，模板配合 `{% if fingerprint.faq_style != "none" %}` 包裹）。
8. **无残留 Jinja2 语法**：渲染输出 MUST NOT 包含 `{{ }}` 或 `{% %}` 等未渲染标记。

## 待确认

- 多 flow 场景的渲染方式：当前模板默认遍历 `route.flows`，多 flow 时输出"**流程：name**"小标题。是否需要为每个 flow 单独建 H4 子章节（如 `#### N.2.1 流程：创建用户`）？MVP 保持当前实现，复杂场景推迟。
