# analysis.json Schema

This document defines the data contract for `analysis.json`, the output of P1 (App Discovery). It captures the application's runtime navigation structure, interactive elements, inferred user flows, and authentication requirements. Every downstream phase (P2 plan generation, P3 screenshot execution, P4 manual rendering) reads this file, so its shape is the single source of truth for what the app contains.

The schema is framework-agnostic. The same shape is produced whether the target is Vue 3 + Element Plus, React + Ant Design, or an unrecognized framework. The `framework_hint` field records the detection result for diagnostic purposes only.

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `app_name` | string | MUST | 应用名称，用作输出目录名与 `chunk_id` 前缀。值与 `$USERGUIDE_BASE/{app_name}/` 的目录名一致。 |
| `version` | string | MUST | 应用语义版本，从 `package.json` 读取；读不到时为 `"unknown"`。 |
| `framework_hint` | string \| null | MUST | 框架检测的结果，取值为 `"vue3"` / `"react"` / `"next"` / `"nuxt"` / `"unknown"` 之一。仅作诊断用，不影响 pipeline 行为。 |
| `dev_server_url` | string | MUST | dev server 完整 base URL，如 `"http://localhost:5173"`。不含尾斜杠。 |
| `routes` | array<Route> | MUST | 应用路由列表。可访问与不可访问的路由都包含在内（用 `accessible` 区分）。 |
| `auth` | Auth \| null | MUST | 登录流程描述。应用无鉴权时为 `null`，此时 P2.5 被跳过。 |
| `generated_at` | string | MUST | ISO 8601 时间戳（UTC），格式 `YYYY-MM-DDTHH:mm:ssZ`。同时被 renderer 写入输出文件的生成时间字段，保证三者一致。 |

字段顺序按上表排列，但解析器 MUST NOT 依赖顺序。未知字段（如调试用的 `_debug_notes`）MUST 被容忍：校验通过，renderer 忽略它们。

## Route 对象

每条 `route` 描述应用的一个可达页面或权限受限页面。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path` | string | MUST | 路由路径，以 `/` 开头。示例：`"/users"`、`"/admin/settings"`。 |
| `title` | string | MUST | 页面标题，来自菜单项文本或路由 meta 的 `title` 字段。用作手册中的"模块N：标题"。 |
| `accessible` | boolean | MUST | 当前 demo 凭据能否访问该路由。`false` 表示权限受限（如需 admin 角色），renderer 在手册中标注"需 X 权限"。 |
| `elements` | array<Element> | MUST | 该页面的用户可见交互元素列表。可以为空数组。 |
| `flows` | array<Flow> | MUST | 从该页面元素组合推断出的用户流程列表。可以为空数组。 |
| `discovered_via` | enum | MUST | 路由发现途径：`"menu"` / `"sidebar"` / `"router_state"` / `"source_hint"`。 |

`discovered_via` 枚举含义：

| 取值 | 含义 |
|------|------|
| `"menu"` | 来自顶部导航菜单或主菜单项。 |
| `"sidebar"` | 来自侧边栏导航。 |
| `"router_state"` | 通过读取 SPA router 全局实例（Vue Router / React Router）发现，未在可见菜单中暴露。 |
| `"source_hint"` | 源码分析提示存在但运行时未被探测到的路由（如动态注册、权限受限）。 |

## Element 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `element_id` | string | MUST | 全 route 内唯一 ID，格式 `el_NNN`（3 位零填充），如 `el_001`、`el_012`。 |
| `type` | enum | MUST | 元素类型：`"button"` / `"input"` / `"select"` / `"table"` / `"link"` / `"modal"`。 |
| `text` | string | OPTIONAL | 按钮或链接的可见文本。`type` 为 `button`/`link` 时 MUST 二选一提供（`text` 或 `aria_label`）。 |
| `placeholder` | string | OPTIONAL | 输入框的 placeholder。`type` 为 `input`/`select` 时提供。 |
| `aria_label` | string | OPTIONAL | 元素的 `aria-label`。当元素无可见文本时使用。 |
| `action` | string \| null | MUST | 推断出的处理器名（如 `"open_create_modal"`、`"submit_form"`）。无法推断时为 `null`。 |
| `columns` | array<string> | OPTIONAL | `type` 为 `table` 时提供，列出列标题。其他 type MUST NOT 携带此字段。 |

`text` / `placeholder` / `aria_label` 三者按 `type` 决定使用哪一个：

| type | 主用字段 | 备用字段 |
|------|---------|---------|
| `button` | `text` | `aria_label` |
| `link` | `text` | `aria_label` |
| `input` | `placeholder` | `aria_label` |
| `select` | `placeholder` | `aria_label` |
| `table` | （无）| `columns` 列表 |
| `modal` | `text`（弹窗标题）| `aria_label` |

## Flow 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `flow_id` | string | MUST | 全 route 内唯一 ID，格式 `flow_NNN`（3 位零填充），如 `flow_001`。 |
| `name` | string | MUST | 流程名称，中文短句，如 `"创建用户"`、`"批量导出"`。 |
| `steps` | array<Step> | MUST | 流程步骤序列，按执行顺序排列。至少 1 步。 |

### Step 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `action` | string | MUST | 动作描述，对应推断出的 handler 名（如 `"open_create_modal"`）。 |
| `element_id` | string | MUST | 引用本 route 内的 `elements[].element_id`。MUST NOT 重复写元素文本。 |
| `expected_outcome` | string | MUST | 预期结果的中文短句，如 `"弹出新建用户表单"`、`"列表新增一行"`。 |

## Auth 对象

`auth` 非 `null` 时 MUST 遵循以下结构：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `login_route` | string | MUST | 登录页路径，如 `"/login"`。 |
| `form_fields` | array<FormField> | MUST | 登录表单字段列表，通常至少包含 `username` 与 `password`。 |
| `post_login_route` | string | MUST | 登录成功后的目标路由，如 `"/dashboard"`。 |
| `post_login_assertion` | string | MUST | 中文断言语句，描述如何确认登录成功（如 `"页面上显示当前用户名"`）。供 P2 plan 生成 assert 动作。 |

### FormField 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | MUST | 字段名，HTML `name` 属性或推断出的语义名（`username`/`password`）。 |
| `placeholder` | string | OPTIONAL | 输入框 placeholder，用作 P2 locator 的备选策略。 |
| `type` | enum | OPTIONAL | 字段类型：`"text"` / `"password"` / `"email"` / `"tel"`。缺省按 `"text"` 处理。 |

## 完整示例

下列示例展示一个含鉴权的"用户管理"路由与一个无鉴权的"仪表盘"路由。JSON 合法，可直接用 `json.loads` 解析。

```json
{
  "app_name": "admin-portal",
  "version": "1.4.2",
  "framework_hint": "vue3",
  "dev_server_url": "http://localhost:5173",
  "generated_at": "2026-06-21T08:30:00Z",
  "auth": {
    "login_route": "/login",
    "form_fields": [
      {
        "name": "username",
        "placeholder": "用户名",
        "type": "text"
      },
      {
        "name": "password",
        "placeholder": "密码",
        "type": "password"
      }
    ],
    "post_login_route": "/dashboard",
    "post_login_assertion": "页面上显示当前用户名"
  },
  "routes": [
    {
      "path": "/dashboard",
      "title": "仪表盘",
      "accessible": true,
      "discovered_via": "router_state",
      "elements": [
        {
          "element_id": "el_001",
          "type": "link",
          "text": "查看明细",
          "action": "navigate_to_detail"
        }
      ],
      "flows": []
    },
    {
      "path": "/users",
      "title": "用户管理",
      "accessible": true,
      "discovered_via": "sidebar",
      "elements": [
        {
          "element_id": "el_001",
          "type": "button",
          "text": "新建",
          "action": "open_create_modal"
        },
        {
          "element_id": "el_002",
          "type": "input",
          "placeholder": "请输入用户名",
          "action": null
        },
        {
          "element_id": "el_003",
          "type": "input",
          "placeholder": "请输入邮箱",
          "action": null
        },
        {
          "element_id": "el_004",
          "type": "button",
          "text": "保存",
          "action": "submit_form"
        },
        {
          "element_id": "el_005",
          "type": "table",
          "action": null,
          "columns": ["用户名", "邮箱", "角色", "操作"]
        }
      ],
      "flows": [
        {
          "flow_id": "flow_001",
          "name": "创建用户",
          "steps": [
            {
              "action": "open_create_modal",
              "element_id": "el_001",
              "expected_outcome": "弹出新建用户表单"
            },
            {
              "action": "fill_form",
              "element_id": "el_002",
              "expected_outcome": "用户名输入完成"
            },
            {
              "action": "submit_form",
              "element_id": "el_004",
              "expected_outcome": "列表新增一行"
            }
          ]
        }
      ]
    }
  ]
}
```

## 无鉴权场景

当应用不要求登录时，`auth` 字段为 `null`，`routes[]` 中所有路由的 `accessible` 都为 `true`：

```json
{
  "app_name": "static-landing",
  "version": "0.1.0",
  "framework_hint": "unknown",
  "dev_server_url": "http://localhost:3000",
  "generated_at": "2026-06-21T08:30:00Z",
  "auth": null,
  "routes": [
    {
      "path": "/",
      "title": "首页",
      "accessible": true,
      "discovered_via": "menu",
      "elements": [],
      "flows": []
    }
  ]
}
```

## 校验规则

renderer 与 P2 plan generator 在读取 `analysis.json` 时 MUST 执行以下校验。任一失败 MUST 立即终止 pipeline 并打印错误。

1. **顶层字段完整性**：`app_name` / `version` / `framework_hint` / `dev_server_url` / `routes` / `auth` / `generated_at` 全部存在且类型正确。
2. **ID 格式**：所有 `element_id` 符合 `^el_\d{3}$`，所有 `flow_id` 符合 `^flow_\d{3}$`。
3. **ID 唯一性**：同一 route 内的 `element_id` 互不相同；同一 route 内的 `flow_id` 互不相同。
4. **Step 引用合法性**：每个 `step.element_id` MUST 等于本 route 内某个 `elements[].element_id`。
5. **Element 字段匹配 type**：`type: "table"` 的元素 MUST 携带 `columns`，非 table 类型 MUST NOT 携带 `columns`。
6. **Auth 形状**：`auth` 非 `null` 时 MUST 包含 `login_route` / `form_fields` / `post_login_route` / `post_login_assertion` 四个字段。
7. **discovered_via 取值**：MUST 是 `"menu"` / `"sidebar"` / `"router_state"` / `"source_hint"` 之一。
8. **未知字段容忍**：未知字段 MUST NOT 触发校验失败，但 renderer MUST 忽略它们。

## 待确认

无。schema 已覆盖 spec 中所有 Requirement 的字段需求。新增字段需求应先在本文件登记，再写入实现。
