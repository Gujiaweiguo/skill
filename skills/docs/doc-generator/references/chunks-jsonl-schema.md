# chunks.jsonl Schema

This document defines the data contract for `chunks.jsonl`, one of the three outputs of P4 (Manual Rendering). Each line is a self-contained JSON object conforming to the LangChain `Document` shape: `{page_content, metadata}`. The file is line-delimited JSON (JSONL / NDJSON), not a JSON array. Downstream RAG pipelines ingest it directly with no parsing customization.

The chunk boundaries are deliberately aligned with `manual-template.md` sections: one chunk per page-load, one chunk per step, one chunk per FAQ. This alignment means a user query that retrieves a step chunk can be surfaced alongside the exact screenshot for that step, and the same chunk also appears as a paragraph in the human-readable Markdown manual.

## 文件格式

| 属性 | 取值 |
|------|------|
| 文件编码 | UTF-8（无 BOM） |
| 行分隔符 | `\n`（LF） |
| 每行 JSON | 严格合法 JSON 对象，无尾随逗号，无多行字符串 |
| 字段顺序 | `page_content` 在前，`metadata` 在后（不强制，但建议一致） |
| 末尾换行 | 文件 MUST 以单个 `\n` 结束（最后一行也有换行） |

**关键约束**：每行 MUST 独立通过 `json.loads`。MUST NOT 出现跨行 JSON（如多行字符串）。需要换行的文本（如 `page_content` 中的多段落）MUST 使用 `\n` 转义符嵌入字符串内部，而不是物理换行。

## 顶层对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page_content` | string | MUST | 文本内容。对齐 LangChain `Document.page_content`。中文为主，含本 chunk 描述的全部文本（步骤说明、元素表格文本、FAQ 问答等）。 |
| `metadata` | object | MUST | 元数据对象，结构见下表。对齐 LangChain `Document.metadata`。 |

## metadata 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `app_name` | string | MUST | 应用名称，与 `analysis.json.app_name` 一致。 |
| `version` | string | MUST | 应用版本，与 `analysis.json.version` 一致。 |
| `module` | string | MUST | 该 chunk 所属模块名，对应 route 的 `title`（如 `"用户管理"`）。 |
| `subsection` | enum | MUST | chunk 在模块内的子位置：`"page_load"` / `"step"` / `"element_table"` / `"faq"`。 |
| `step` | int \| null | MUST | 仅 `subsection: "step"` 时为正整数（从 1 起）；其他 subsection MUST 为 `null`。 |
| `page_url` | string | MUST | 该模块的完整 URL（拼接 `analysis.dev_server_url` 与 `route.path`），如 `"http://localhost:5173/users"`。 |
| `screenshots` | array<string> | MUST | 本 chunk 关联的截图相对路径列表（从输出目录起算），如 `["imgs/users_2_create-modal.png"]`。无关联截图时为空数组 `[]`。**失败截图 MUST 不出现在此列表中**。 |
| `element_texts` | array<string> | MUST | 本 chunk 源文本涉及的所有可见元素文案，用于提升文本召回率。例如创建用户步骤 chunk 应包含 `["新建", "保存"]`，这样查询"怎么保存用户"也能命中。无元素时为空数组。 |
| `chunk_id` | string | MUST | 全文件唯一 chunk ID，格式 `{app_name}_{module_slug}_{subsection}_{step_or_zero}`。详见下文。 |

### chunk_id 构造规则

格式：`{app_name}_{module_slug}_{subsection_slug}_{step_or_zero}`

- `app_name`：原样使用，如 `admin-portal`。
- `module_slug`：route title slug 化。中文保留（GitHub anchor 规则的扩展应用），空格与标点替换为 `-`，连续 `-` 合并。如 `"用户管理"` → `"用户管理"`、`"实验性 功能"` → `"实验性-功能"`。
- `subsection_slug`：英文小写：`page_load` / `step` / `element_table` / `faq`。
- `step_or_zero`：`subsection: "step"` 时为步骤号（`1`、`2`...）；其他 subsection 为 `0`。

示例：`admin-portal_用户管理_step_2`、`admin-portal_仪表盘_page_load_0`、`admin-portal_通用_faq_3`。

### subsection 枚举语义

| 取值 | 含义 | chunk 数量 |
|------|------|-----------|
| `page_load` | 模块首次加载后的概览说明（对应 `#### N.1 页面入口` 与模块标题段落）| 每模块 1 个 |
| `step` | 操作步骤（对应 `#### N.2 操作步骤` 中的单个步骤）| 每步骤 1 个 |
| `element_table` | 元素说明表格（对应 `#### N.3 界面元素说明`）| 每模块 1 个 |
| `faq` | FAQ 单条问答 | 每条 FAQ 1 个 |

**与 manual-template.md 对齐**：每个模块至少产出 `1 (page_load) + N (step) + 1 (element_table)` 共 `N+2` 个 chunk，加上全局 FAQ 章节 `M` 个 faq chunk。这是与 Markdown 手册结构对齐的核心保证。

## 示例

下列三行 JSONL 分别展示 `page_load`、`step`、`faq` 三种 subsection。每行独立合法，可直接 `json.loads`。

### 示例 1：page_load chunk

```json
{"page_content": "用户管理模块提供创建、编辑、删除用户以及分配角色的功能。访问路径：/users。登录后从左侧菜单进入。", "metadata": {"app_name": "admin-portal", "version": "1.4.2", "module": "用户管理", "subsection": "page_load", "step": null, "page_url": "http://localhost:5173/users", "screenshots": ["imgs/users_1_page-load.png"], "element_texts": ["新建", "用户名", "邮箱", "角色", "操作", "保存"], "chunk_id": "admin-portal_用户管理_page_load_0"}}
```

### 示例 2：step chunk

```json
{"page_content": "步骤 2：在弹出的新建用户表单中填写用户名与邮箱，点击保存按钮提交。表单校验通过后，列表会新增一行。", "metadata": {"app_name": "admin-portal", "version": "1.4.2", "module": "用户管理", "subsection": "step", "step": 2, "page_url": "http://localhost:5173/users", "screenshots": ["imgs/users_2_create-modal.png"], "element_texts": ["新建", "用户名", "邮箱", "保存"], "chunk_id": "admin-portal_用户管理_step_2"}}
```

### 示例 3：faq chunk

```json
{"page_content": "Q1：忘记管理员密码怎么办？A：请联系系统运维人员通过后端命令重置密码，重置后首次登录需要修改。", "metadata": {"app_name": "admin-portal", "version": "1.4.2", "module": "通用", "subsection": "faq", "step": null, "page_url": "", "screenshots": [], "element_texts": ["管理员", "密码", "重置"], "chunk_id": "admin-portal_通用_faq_0"}}
```

## LangChain 摄入示例

下列 Python 代码片段是推荐的摄入方式，无需任何自定义 parser：

```python
from langchain_core.documents import Document
import json

docs = [Document(**json.loads(line)) for line in open("chunks.jsonl")]
```

`Document` 接受 `page_content` 与 `metadata` 两个关键字参数，与本文件的顶层对象结构完全一致。`metadata` 中的 `screenshots` 字段可被前端按需渲染为图片，实现"文本召回 + 图文并展"的多模态体验，而不需要为图片单独建向量索引（与决策 D10 一致：MVP 不做多模态 captioning）。

下游若需要把同一模块的 chunk 聚合展示，可以按 `metadata.module` 字段过滤；若需要按步骤顺序回放，可以按 `metadata.module` + `metadata.step` 排序。

## 校验规则

renderer 写出 `chunks.jsonl` 后 MUST 自校验。任一失败 MUST 触发 partial-failure rollback，删除已写的输出文件。

1. **每行合法 JSON**：每行 MUST 能通过 `json.loads` 解析，否则校验失败。
2. **顶层字段**：每行对象 MUST 仅包含 `page_content` 与 `metadata` 两个字段。多余字段 MUST 触发校验失败（严格性高于 `analysis.json`）。
3. **metadata 完整性**：`app_name` / `version` / `module` / `subsection` / `step` / `page_url` / `screenshots` / `element_texts` / `chunk_id` 全部存在。
4. **subsection 取值**：MUST 是 `page_load` / `step` / `element_table` / `faq` 之一。
5. **step 字段条件**：`subsection: "step"` 时 `step` MUST 是正整数；其他 subsection `step` MUST 为 `null`。
6. **chunk_id 唯一**：全文件所有 `metadata.chunk_id` 互不相同。
7. **chunk_id 格式**：符合 `^{app_name}_{module_slug}_{subsection_slug}_\d+$`。
8. **失败截图排除**：`manifest.json` 中标记为 failed 的截图路径 MUST NOT 出现在任何 chunk 的 `metadata.screenshots` 中。
9. **模块数量一致**：`chunks.jsonl` 中出现的不同 `metadata.module` 数量 MUST 等于 `analysis.routes` 长度（对应 spec 中 Single-Source Multi-Output Consistency Requirement）。
10. **元素文本一致**：每个模块所有 chunk 的 `metadata.element_texts` 合集 MUST 等于 `analysis.routes[i].elements` 中所有元素可见文本的集合（对应 spec scenario: Element texts consistent across outputs）。
11. **末尾换行**：文件 MUST 以 `\n` 结尾，且不包含空行。

## 待确认

无。schema 已覆盖 spec manual-rendering Requirement: Chunks JSONL Schema 的全部场景需求。
