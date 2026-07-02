# config.yaml Schema

This document defines the data contract for `_input/{name}/config.yaml`, the per-app override file. The config is OPTIONAL: if absent, the skill proceeds with defaults and reference-derived values. When present, only the fields listed below are honored. Unknown fields are tolerated but ignored (with a warning), to keep the schema stable as new features are added.

The config is the user's escape hatch for the three things that cannot be auto-detected reliably: where the demo credentials live, which modules to exclude, and how aggressive screenshots should be. It is intentionally narrow; per Q3 of the design, the MVP schema is fixed at four top-level fields.

## 文件位置

- 路径：`$USERGUIDE_BASE/_input/{name}/config.yaml`
- 编码：UTF-8
- 格式：YAML 1.2 子集（key-value + 简单 list，不使用 YAML 锚点、多文档、流式语法等高级特性）
- 不存在时：skill MUST 按"全部默认值"运行，不报错

## 字段一览

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `auth.hint` | string \| null | OPTIONAL | `null` | 演示凭据来源的人类可读提示。 |
| `ignore_modules` | array<string> | OPTIONAL | `[]` | 需要排除的模块（按 route title 精确匹配）。 |
| `screenshot_density` | enum | OPTIONAL | （不覆盖指纹） | 截图密度覆盖，覆盖 `style-fingerprint.screenshot_frequency`。 |
| `branding.primary_color` | string | OPTIONAL | `"#1890ff"` | 截图标注卡片的主色（hex 字符串）。 |

## 字段详解

### `auth.hint`

```yaml
auth:
  hint: "管理员账号在 .env 的 DEMO_USER/DEMO_PASS"
```

| 属性 | 值 |
|------|-----|
| 类型 | string 或 null |
| 默认 | `null` |
| 作用 | 当 P2.5 向用户索要凭据时，将该提示一并打印，帮助用户找到凭据。skill 本身 MUST NOT 解析该字符串去自动读取凭据（避免任意外部文件读取风险）。 |
| 安全约束 | 该字段 MUST NOT 直接包含用户名/密码。MUST 是"指引人类去哪里找"的描述。 |
| 替代输入 | 用户仍可在 P2.5 交互式输入凭据，或预先写入 `.auth.json`（参考 `screenshot-plan-schema.md`）。 |

### `ignore_modules`

```yaml
ignore_modules:
  - "实验性功能"
  - "内部调试页"
```

| 属性 | 值 |
|------|-----|
| 类型 | string 数组 |
| 默认 | `[]`（不排除任何模块） |
| 匹配规则 | 精确字符串匹配 route 的 `title` 字段（大小写敏感、不 trim）。 |
| 作用阶段 | 在 P1 生成 `analysis.json` 时执行排除，被排除的 route 不写入 `routes[]`，下游 P2/P3/P4 都看不到它们。 |
| 与 P5 的关系 | P5 交互确认时仍可看到被排除的模块列表（标注"已排除"），方便用户调整 config 后重跑。 |

### `screenshot_density`

```yaml
screenshot_density: "high"
```

| 属性 | 值 |
|------|-----|
| 类型 | enum：`"low"` / `"medium"` / `"high"` |
| 默认 | 未设置时不覆盖指纹；指纹也未提取到时由 renderer 兜底为 `"medium"` |
| 作用 | 直接覆盖 `style-fingerprint.json.screenshot_frequency`，`sources.screenshot_frequency` 标记为 `"config"` |
| 设计原因 | 截图密度是用户最常想调的维度（截图耗时长、文件大），单独暴露；其他维度通过参考资料控制 |

### `branding.primary_color`

```yaml
branding:
  primary_color: "#1890ff"
```

| 属性 | 值 |
|------|-----|
| 类型 | string（hex 颜色，`#` + 6 位 hex） |
| 默认 | `"#1890ff"`（Ant Design 蓝） |
| 格式校验 | MUST 匹配 `^#[0-9a-fA-F]{6}$`，否则 P0 阶段警告并回退默认值 |
| 作用 | Playwright executor 在截图前可选叠加一张半透明"标注卡片"（高亮当前操作元素），卡片用此色作为强调色 |
| MVP 范围 | MVP 是否实现卡片叠加视 executor 而定；该字段先入 schema，executor 不读时无效但不报错 |

## 完整示例

```yaml
# _input/admin-portal/config.yaml
# 注释行以 # 开头，YAML 1.2 标准注释。

auth:
  hint: "管理员账号在 .env 的 DEMO_USER/DEMO_PASS"

ignore_modules:
  - "实验性功能"
  - "内部调试页"

screenshot_density: "high"

branding:
  primary_color: "#722ed1"
```

## 最小示例

仅含一个字段的合法 config：

```yaml
ignore_modules:
  - "实验性功能"
```

## 合并规则

config.yaml 与 `style-fingerprint.json`、内置默认值共同决定最终行为。优先级（高 → 低）：

```
config.yaml  >  style-fingerprint.json  >  内置默认值
```

具体到每个字段：

| 字段 | 来源 | 备注 |
|------|------|------|
| `auth.hint` | 仅 config.yaml | 不参与指纹合并，是独立 config 字段 |
| `ignore_modules` | 仅 config.yaml | 不参与指纹合并 |
| `screenshot_density` | config.yaml 覆盖 `style-fingerprint.screenshot_frequency` | 合并写入 `style-fingerprint.json`，sources 标 `"config"` |
| `branding.primary_color` | 仅 config.yaml | 不参与指纹合并 |

`style-fingerprint.json` 在生成阶段就完成与 config 的合并；下游 `render_manual.py` 只读合并后的指纹，不需要二次合并。这是为了保证 renderer 的纯函数性质（决策 D7）。

## 校验规则

P0 阶段 MUST 在读取 config.yaml 时校验：

1. **YAML 可解析**：YAML 语法错误 MUST 报错并终止（用户必须修复 config 才能继续）。
2. **未知字段容忍**：未知字段 MUST 仅发出 warning（不终止），warning 消息格式 `"Unknown config field: {field}, ignored"`。
3. **screenshot_density 取值合法**：MUST 是 `"low"` / `"medium"` / `"high"` 之一。非法值报错并要求修正。
4. **branding.primary_color 格式**：MUST 匹配 `^#[0-9a-fA-F]{6}$`。不匹配时 warning 并回退默认值。
5. **ignore_modules 类型**：MUST 是 string 数组。每个元素 MUST 是非空字符串。
6. **auth.hint 类型**：MUST 是 string 或 null。
7. **凭据安全**：扫描 config.yaml 全文，若出现疑似密码模式（如 `password:` 后跟非空值），MUST warning 提示"凭据应放 .auth.json，不建议放 config.yaml"。不强制终止。

## 待确认

- 是否需要为 `ignore_modules` 支持 glob 或正则匹配？MVP 仅精确匹配，复杂匹配规则推迟。
- `branding.primary_color` 在 MVP 是否被 executor 实际使用？若 executor 未实现卡片叠加，此字段为预留位。
