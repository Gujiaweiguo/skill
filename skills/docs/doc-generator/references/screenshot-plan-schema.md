# screenshot-plan.json Schema

This document defines the data contract for `screenshot-plan.json`, the output of P2 (Screenshot Planning). It describes a deterministic list of browser tasks the built-in `playwright` skill will execute in P3. Every action targets DOM elements via text/role/placeholder/label locators only. CSS selectors and XPath are forbidden because they break under scoped styles, CSS modules, and component-library internal class names.

The plan is the only contract between doc-generator and the `playwright` skill. As long as both sides honor this schema, the playwright executor can be swapped or upgraded without touching doc-generator.

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `app_name` | string | MUST | 与 `analysis.json.app_name` 完全一致。 |
| `generated_at` | string | MUST | ISO 8601 时间戳（UTC），从 `analysis.json.generated_at` 复用。 |
| `auth_task` | Task \| null | MUST | 鉴权前置任务。`analysis.json.auth` 为 `null` 时此字段为 `null`。非 `null` 时 MUST 是 `tasks[]` 的第一个元素。 |
| `tasks` | array<Task> | MUST | 页面级任务列表。一个 accessible route 对应一个 task（鉴权场景下 `tasks[0]` 是 auth_task，其后是页面任务）。 |

## Task 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | MUST | 全 plan 内唯一 ID，格式 `task_NNN`（3 位零填充），如 `task_001`。auth_task 固定取 `task_000`。 |
| `page_title` | string | MUST | 页面中文标题，来自对应 route 的 `title`。auth_task 用 `"登录"`。 |
| `url` | string | MUST | 任务起始 URL，完整路径，如 `"http://localhost:5173/users"`。 |
| `requires_auth` | boolean | MUST | 该任务是否依赖 authenticated context。auth_task 本身为 `false`（它是建立 context 的步骤）；其他任务根据 route 的 `accessible` 与 `auth` 决定。 |
| `actions` | array<Action> | MUST | 有序动作列表，按执行顺序排列。至少 1 个 action。 |

## Locator 对象

凡需定位 DOM 元素的 action（`wait` / `fill` / `click` / `hover` / `scroll`（非 null 形态）/ `select` / `assert`）MUST 携带 `locator` 字段，其结构如下：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `strategy` | enum | MUST | 定位策略：`"text"` / `"role"` / `"placeholder"` / `"label"`。 |
| `value` | string | MUST | 策略对应的值。`strategy: "text"` 时为可见文本；`strategy: "placeholder"` 时为 placeholder 文本；`strategy: "label"` 时为表单 label 文本；`strategy: "role"` 时为可读名称（如按钮的 `aria-label` 或文本）。 |
| `role` | string | OPTIONAL | 仅 `strategy: "role"` 时提供，取值如 `"button"` / `"link"` / `"textbox"` / `"dialog"`，对齐 ARIA role 规范。 |

### 策略语义与禁用项

| 策略 | 对应 Playwright API | 典型用途 |
|------|---------------------|---------|
| `text` | `getByText(value)` | 按可见文本定位按钮、链接、菜单项 |
| `role` | `getByRole(role, name=value)` | 按无障碍角色定位，特别是图标按钮 |
| `placeholder` | `getByPlaceholder(value)` | 定位输入框、下拉框 |
| `label` | `getByLabel(value)` | 按表单 label 定位输入控件 |

**FORBIDDEN**：`strategy` 字段 MUST NOT 取 `"css"` 或 `"xpath"`。任何包含 CSS 选择器（`.`-前缀类名、`#`-前缀 id）或 XPath 表达式（`//`、`/`）的 locator MUST 在 P2 校验阶段被拒绝并打印错误。这是为了对齐决策 D2：文本/角色定位器跨重构稳定，CSS 选择器在 scoped styles 与组件库内部类名下大概率失效。

## Action 类型

下列 9 种 `type` 是 P2 校验允许的全部取值。未知 `type` MUST 在 P2 校验阶段被拒绝，错误消息格式 `"Unsupported action type: {type}"`，不进入 P3。

### 1. `navigate`

导航到指定 URL。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"navigate"` | MUST | 固定字面量。 |
| `url` | string | MUST | 目标 URL，完整路径。 |

示例：

```json
{
  "type": "navigate",
  "url": "http://localhost:5173/users"
}
```

### 2. `wait`

等待元素出现或满足条件后再继续。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"wait"` | MUST | 固定字面量。 |
| `locator` | Locator | MUST | 等待的目标元素。 |
| `timeout_ms` | number | MUST | 超时毫秒数，正整数。建议 5000-30000。 |

示例：

```json
{
  "type": "wait",
  "locator": {
    "strategy": "text",
    "value": "用户管理"
  },
  "timeout_ms": 10000
}
```

### 3. `screenshot`

截取当前页面状态。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"screenshot"` | MUST | 固定字面量。 |
| `name` | string | MUST | 截图短描述（中文），用作文件名一部分，如 `"新建用户弹窗"`。 |
| `description` | string | MUST | 中文长描述，用于 `操作手册.md` 的图示说明文字。 |

文件名按 spec 约定：`{module_slug}_{step_index}_{description_slug}.png`。renderer 与 playwright executor 协商 slug 化规则；中文文件名在支持 Unicode 的文件系统上原样保留，ASCII-only 文件系统使用拼音或英文 slug。

示例：

```json
{
  "type": "screenshot",
  "name": "新建用户弹窗",
  "description": "点击新建按钮后弹出的表单对话框"
}
```

### 4. `fill`

向输入控件填入值。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"fill"` | MUST | 固定字面量。 |
| `locator` | Locator | MUST | 目标输入控件。 |
| `value` | string | MUST | 填入值。凭据类字段（password）的值在 P2 plan 中以占位符 `"<from .auth.json>"` 表示，executor 在 P3 从 `.auth.json` 读取真实值替换。 |

示例：

```json
{
  "type": "fill",
  "locator": {
    "strategy": "placeholder",
    "value": "用户名"
  },
  "value": "<from .auth.json>"
}
```

### 5. `click`

点击元素。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"click"` | MUST | 固定字面量。 |
| `locator` | Locator | MUST | 目标元素。 |

示例：

```json
{
  "type": "click",
  "locator": {
    "strategy": "text",
    "value": "新建"
  }
}
```

### 6. `hover`

鼠标悬停（用于触发下拉菜单、tooltip 等）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"hover"` | MUST | 固定字面量。 |
| `locator` | Locator | MUST | 目标元素。 |

### 7. `scroll`

滚动页面或容器。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"scroll"` | MUST | 固定字面量。 |
| `locator` | Locator \| null | MUST | 滚动目标的容器元素；为 `null` 表示滚动主滚动条（window）。 |
| `y_offset_px` | number | MUST | 纵向滚动像素偏移，可为负值。 |

示例（滚动到表格底部）：

```json
{
  "type": "scroll",
  "locator": {
    "strategy": "role",
    "role": "table",
    "value": "用户列表"
  },
  "y_offset_px": 500
}
```

示例（滚动主页面）：

```json
{
  "type": "scroll",
  "locator": null,
  "y_offset_px": 300
}
```

### 8. `select`

在下拉选择控件中选中选项。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"select"` | MUST | 固定字面量。 |
| `locator` | Locator | MUST | 目标 select 控件。 |
| `value` | string | MUST | 选中项的可见文本（不是 value 属性）。 |

### 9. `assert`

断言元素处于预期状态。失败时该 action 标记为 `failed`，剩余同 task 内的 action 标记 `skipped`，下一 task 继续。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"assert"` | MUST | 固定字面量。 |
| `locator` | Locator | MUST | 断言目标元素。 |
| `expected_state` | string | MUST | 中文短句描述预期状态，如 `"可见且文本包含 '欢迎'"`、`"存在且可点击"`。executor 按"可见 + 文本匹配"两种最常见情况判断，复杂断言在 executor 层降级为"可见即通过"。 |

示例：

```json
{
  "type": "assert",
  "locator": {
    "strategy": "text",
    "value": "欢迎"
  },
  "expected_state": "可见"
}
```

## 完整示例

下列 plan 包含 1 个 auth_task 与 2 个页面任务。JSON 合法，可直接用 `json.loads` 解析。

```json
{
  "app_name": "admin-portal",
  "generated_at": "2026-06-21T08:30:00Z",
  "auth_task": {
    "id": "task_000",
    "page_title": "登录",
    "url": "http://localhost:5173/login",
    "requires_auth": false,
    "actions": [
      {
        "type": "navigate",
        "url": "http://localhost:5173/login"
      },
      {
        "type": "fill",
        "locator": {
          "strategy": "placeholder",
          "value": "用户名"
        },
        "value": "<from .auth.json>"
      },
      {
        "type": "fill",
        "locator": {
          "strategy": "placeholder",
          "value": "密码"
        },
        "value": "<from .auth.json>"
      },
      {
        "type": "click",
        "locator": {
          "strategy": "role",
          "role": "button",
          "value": "登录"
        }
      },
      {
        "type": "assert",
        "locator": {
          "strategy": "text",
          "value": "欢迎"
        },
        "expected_state": "可见"
      }
    ]
  },
  "tasks": [
    {
      "id": "task_000",
      "page_title": "登录",
      "url": "http://localhost:5173/login",
      "requires_auth": false,
      "actions": [
        {
          "type": "navigate",
          "url": "http://localhost:5173/login"
        },
        {
          "type": "fill",
          "locator": {
            "strategy": "placeholder",
            "value": "用户名"
          },
          "value": "<from .auth.json>"
        },
        {
          "type": "fill",
          "locator": {
            "strategy": "placeholder",
            "value": "密码"
          },
          "value": "<from .auth.json>"
        },
        {
          "type": "click",
          "locator": {
            "strategy": "role",
            "role": "button",
            "value": "登录"
          }
        },
        {
          "type": "assert",
          "locator": {
            "strategy": "text",
            "value": "欢迎"
          },
          "expected_state": "可见"
        }
      ]
    },
    {
      "id": "task_001",
      "page_title": "用户管理",
      "url": "http://localhost:5173/users",
      "requires_auth": true,
      "actions": [
        {
          "type": "navigate",
          "url": "http://localhost:5173/users"
        },
        {
          "type": "wait",
          "locator": {
            "strategy": "text",
            "value": "新建"
          },
          "timeout_ms": 10000
        },
        {
          "type": "screenshot",
          "name": "用户列表页",
          "description": "进入用户管理模块后的初始列表页面"
        },
        {
          "type": "click",
          "locator": {
            "strategy": "text",
            "value": "新建"
          }
        },
        {
          "type": "wait",
          "locator": {
            "strategy": "role",
            "role": "dialog",
            "value": "新建用户"
          },
          "timeout_ms": 5000
        },
        {
          "type": "screenshot",
          "name": "新建用户弹窗",
          "description": "点击新建按钮后弹出的表单对话框"
        }
      ]
    },
    {
      "id": "task_002",
      "page_title": "仪表盘",
      "url": "http://localhost:5173/dashboard",
      "requires_auth": true,
      "actions": [
        {
          "type": "navigate",
          "url": "http://localhost:5173/dashboard"
        },
        {
          "type": "wait",
          "locator": {
            "strategy": "text",
            "value": "总览"
          },
          "timeout_ms": 10000
        },
        {
          "type": "screenshot",
          "name": "仪表盘首页",
          "description": "登录后默认进入的运营总览页面"
        }
      ]
    }
  ]
}
```

## 校验规则

P2 plan generator 在写出 `screenshot-plan.json` 后 MUST 自校验。P3 executor 在读取时 MUST 二次校验。任一失败 MUST 终止流程。

1. **顶层字段**：`app_name` / `generated_at` / `auth_task` / `tasks` 全部存在且类型正确。
2. **Task ID 唯一**：所有 `tasks[].id` 与 `auth_task.id` 互不相同；auth_task 固定 `task_000`。
3. **Task ID 格式**：符合 `^task_\d{3}$`。
4. **auth_task 一致性**：`auth_task` 非 `null` 时 MUST 等于 `tasks[0]`；`auth_task` 为 `null` 时所有 task 的 `requires_auth` MUST 为 `false`。
5. **Action type 取值**：MUST 是 `navigate` / `wait` / `screenshot` / `fill` / `click` / `hover` / `scroll` / `select` / `assert` 之一。未知值 MUST 触发错误 `"Unsupported action type: {type}"`。
6. **Locator 策略**：`strategy` MUST 是 `text` / `role` / `placeholder` / `label` 之一。`css` 与 `xpath` MUST 被拒绝。
7. **Action 字段完整性**：每种 action type MUST 携带上文表格中要求的全部字段。多余字段 MUST 被容忍但 executor MUST 忽略。
8. **Action 顺序合理性**：每个页面 task 的第一个非 wait action SHOULD 是 `navigate`。Executor SHOULD NOT 强制（容忍 plan generator 的特殊情形）。
9. **凭据占位符**：`fill` action 携带 `"<from .auth.json>"` 时，其 `locator.strategy` MUST 为 `placeholder` 或 `label`，且对应字段在 `analysis.json.auth.form_fields` 中存在。

## 待确认

无。schema 已覆盖 spec 中所有 action type 与 locator 策略需求。
