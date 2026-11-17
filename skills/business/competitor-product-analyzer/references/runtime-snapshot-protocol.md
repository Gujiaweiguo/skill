# Runtime Snapshot Protocol — 授权 demo 运行时快照规范

本文件是**授权 demo 运行时快照**的唯一详细规范：授权登录一次 → 定点只读探测 → 保存脱敏快照证据包 → 清理会话凭据 → 后续优先离线消费快照，避免每次分析都重新登录 demo。SKILL.md 只保留流程步骤与本文件链接，规则以本文件为准。

**职责分层（2026-11-17 起）**：授权 demo 登录、只读探测与快照**归档**（标准流程、manifest 上下文字段、哈希、脱敏门禁、清理）属于 **material-importer 采集入库层**——归档契约唯一权威源：`skills/business/material-importer/references/material-classification.md` §6；本文件保留**分析侧消费约定与失败模式**规范，两者不冲突（本文件的 manifest 字段表与 material-classification.md §6.1 保持同步，字段语义以后者为准）。competitor-product-analyzer 是快照的消费者，不重复登录。

核心定位：快照是**证据**，不是可交互 demo 的替代品。我们保存的不是"离线恢复的 demo"，而是**脱敏运行时证据包**——`page.html` 只是证据包的组成部分之一，动态 SPA HTML 不保证可离线恢复交互；不得把"保存 HTML"当作万能离线恢复方案。

## 标准流程（demo 模式采集与复用）

1. **授权登录一次**：凭据经 `.auth.json`（见 safety-and-ethics.md），首次采集会话登录一次；验证码场景走半自动登录。
2. **定点只读探测**：按 S0.2/S0.3 的页面抽取策略（A/B/C 三档），只读、最小必要，不执行写操作。
3. **保存快照证据包**：按下文目录契约与 manifest 规范落 `raw/.../runtime-snapshots/<batch>/`，逐文件登记哈希与脱敏状态。
4. **清理会话凭据**：采集会话结束即登出；浏览器 profile、LocalStorage/sessionStorage、Cookie、Token 不落盘；`.auth.json` 按既有规则管理/删除。
5. **后续优先离线消费**：后续分析、S0.6 自对齐、S1 能力抽取优先读 runtime snapshot + raw/materials 投影，不默认重新登录。
6. **仅以下情形重新登录**：证据缺口（关键页面未采）、来源冲突需裁决、或需要最新行为（且需在 pending-items 登记重登理由与新增观察时间）。

## 快照证据包目录契约

推荐形态（与既有项目目录兼容，历史快照不强制迁移，仍按旧路径消费）：

```text
raw/prd-商管系统/02-competitors/<vendor>/runtime-snapshots/<batch>/
├── manifest.json                          ← 批次级清单（见下）
└── pages/<page-id>/
    ├── page.html                          ← 页面 HTML 或脱敏 DOM
    ├── screenshot.png                     ← 已脱敏截图
    ├── accessibility.json                 ← 结构化控件快照（表单控件/按钮/表格列）
    └── observation.md                     ← 操作步骤/前置条件/结果/异常/未验证项
```

- `<batch>` 命名建议含日期与角色（如 `2026-11-17-admin`），同一批次 = 同一登录会话、同版本、同角色。
- `flow.md` 可选：跨页面流程（步骤序列 + 每步 page-id 引用）。
- 历史路径 `incoming/competitor-<vendor>/runtime-snapshots/` 与 `raw/.../05-实施与服务/demo-runtime/` 的既有产物继续有效，不迁移；新批次按本契约落位。

## manifest.json 字段

统一竞品关系上下文字段定义唯一权威源：`skills/business/material-importer/references/material-classification.md`。

| 字段 | 必填 | 说明 |
|---|---|---|
| `workspace_company` | 是 | 资料归档公司（= `$COMPANY_BASE` 公司 slug）|
| `target_company` / `target_product` | 是 | 目标公司/目标产品，或 `unknown`（不猜默认产品）|
| `competitor_company` / `competitor_product` | 是 | 竞品公司/竞品产品（产品未知填 `unknown`，不得把公司当产品）|
| `base_url` | 是 | demo 根 URL |
| `source_version` | 是 | demo/竞品环境版本（历史字段 `product_version` 同义兼容）；无法确认时填 `unknown` 并进 pending |
| `product_version` | 否 | 目标产品版本（语义见 material-classification.md；不填 = unknown）|
| `captured_at` | 是 | ISO 8601 时间戳（精确到分钟）|
| `account_role` / `permission_scope` | 是 | 观察角色与可见权限范围（如"管理员/全菜单"或"商户/仅本商户模块"）；未知填 `unknown`（状态 `runtime-scope-unknown`，不得泛化）|
| `scenario` | 是 | 采集场景（如"菜单+关键表单页定点探测"）|
| `pages[].page_id` | 是 | 页面稳定 ID |
| `pages[].url` / `pages[].locator` | 是 | 页面 URL 与菜单定位路径 |
| `pages[].artifacts` | 是 | 各产物相对路径 + `sha256` + `redaction_status`（`redacted` / `no-sensitive-content` / `pending-redaction`）|
| `limitations` | 是 | 本批次限制（SPA 动态渲染、未登录页面、写操作未验证等）|
| `login_evidence` | 否 | 脱敏登录响应元数据（沿用既有脱敏规则，不含密钥/Token）|

## 产物边界

| 产物 | 用途 | 不保证 |
|---|---|---|
| `page.html` / 脱敏 DOM | 页面文本/字段/按钮/表格结构检索 | 动态 SPA 的离线交互恢复 |
| `screenshot.png` | 布局、字段分组、流程箭头、图标、报表视觉上下文 | 像素级数据准确性（脱敏后）|
| `accessibility.json` | 表单控件/按钮/表格列的可检索结构 | 交互行为 |
| `observation.md` / `flow.md` | 操作步骤、前置条件、页面结果、异常、未验证项 | — |
| 脱敏接口响应 | 与证据直接相关的最小响应 | 不得保存全量 HAR、Cookie、Token、LocalStorage、浏览器 profile |

## 证据边界

快照**可证明**：某版本 / 某角色 / 某时间 / 某场景下，该账号看到了这些页面与行为。

快照**不可证明**：当前仍可访问、所有角色可见、后台算法、数据库结构、实现路径。

- 快照优先消费；需要陈述"当前行为"时必须重新登录核实并单独标记新 `probed_at`。
- **离线消费快照的证据不得标记为当前 runtime re-verified**：`verification_status=snapshot-observed` 表示"仅基于历史快照"，不得自动升级为 `runtime-observed` / `cross-checked`（见 evidence-ledger.md）。

## 脱敏与会话凭据门禁（红线）

- 不得保存：密码、Cookie、Token、授权码、LocalStorage/sessionStorage、浏览器 profile、个人/客户敏感数据。
- 截图 / HTML / 接口响应入库前必须脱敏（规则沿用 evidence-ledger.md「脱敏规则」）；HTML 中内联的 Token/session 参数一并清理。
- **无法确认已脱敏的产物不进入 materials**：留在待处理原件区（raw/incoming），`redaction_status=pending-redaction` 并登记风险；不消费、不导出。
- 不把凭据文件路径或内容写入日志、manifest、observation。
- 会话结束登出并清理会话材料（storage/cookie/profile）。

## 失败模式与处理

| 失败模式 | 状态标记 | 处理 |
|---|---|---|
| 动态内容未保存（SPA 渲染时机错过） | `not_scanned（动态渲染缺失）` | limitations 注明；关键页升级模式 C 重采；不判"无内容" |
| 资源缺失（screenshot/HTML 缺失或哈希不符） | manifest 该产物标 `missing` | 不消费缺失产物；补采或仅用现存产物并降级表述 |
| 截图与 HTML 不同状态（不同时刻/不同页态） | manifest `state_mismatch: true` | observation.md 说明差异；结论只引用各自可证部分 |
| 脱敏失败 / 无法确认脱敏 | `pending-redaction` | 留待处理原件区，不进 materials；登记风险 |
| 版本或角色未知 | `product_version/account_role=unknown` | 进 pending（missing-provenance 口径）；不得猜测回填 |
| 快照过期（>合理观察窗口，参照手册 >2 年同级提示） | limitations 标"基于 YYYY-MM-DD 快照" | 陈述当前行为前必须重登核实 |
| 快照与 demo 当前行为冲突 | `conflicting` | 进 pending-items（能力冲突行）；重登复核后在 upgrade 行留痕裁决 |

## 下游消费约定

- **material-importer（采集归档方）**：授权 demo 登录、只读探测与快照保存归档按其 `references/material-classification.md` §6 契约执行（manifest 上下文字段 + 逐产物哈希 + 脱敏门禁 + 会话清理）；本文件是其分析侧的消费规范补充。
- **competitor-product-analyzer**：S0.6 / S1 优先读 runtime snapshot + raw/materials 投影；重新登录仅限上文第 6 步情形。
- **product-prd-generator**：消费快照时，图片/快照只作辅助证据；关键页面字段/流程仍需 OPC 视觉回看，并带源锚点（manifest + page-id + 哈希）；**不得假设 PRD 的自动 doc_map 会读取图片内容**。
