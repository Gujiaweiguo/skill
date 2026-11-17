# Material Classification — 资料分类与统一竞品关系上下文契约

本文件是 material-importer **资料分类契约的唯一权威源**：统一竞品关系上下文字段（三 skill 共用）、
资料分类字段、分类判断边界、授权 demo 快照归档契约、分类层失败状态。SKILL.md 只保留入口与链接。

competitor-product-analyzer 与 product-prd-generator 消费本文件的上下文字段（引用不复制；
字段语义以本文件为准）。旧材料缺字段时一律保持 `unknown`，不批量猜测、不自动回填（单条人工
核实后可补写并在 notes 留痕，口径同 provenance 回填纪律）。

## 1. 统一竞品关系上下文（三 skill 共用，唯一权威源）

三个 skill（material-importer / competitor-product-analyzer / product-prd-generator）必须使用
一致的竞品关系上下文：

| 字段 | 语义 | 取值示例 |
|---|---|---|
| `workspace_company` | 资料实际归档到哪家公司资料库（= `$COMPANY_BASE` 解析出的公司 slug） | `lanlnk` / `gdcreia` / `lianyou` |
| `target_company` | 被分析或规划的产品属于哪家公司 | 公司 slug 或 `unknown` |
| `target_product` | 目标公司的具体产品 | 产品 id（以该公司 `config/company.yaml` products 台账为准，如 `lnkcre` / `lnkcrm` / `lnkcard` / `lnkreport` / `cre-association-platform`）或 `unknown` |
| `competitor_company` | 竞品所属公司或供应商 | 如 `haiding` / `mingyuan` / `qimao` / `maoku`，或 `unknown` |
| `competitor_product` | 竞品公司的具体产品 | 如 海鼎 CRE / 海鼎 CRM 产品 / 猫酷会员/CRM 产品 / 云资管，或 `unknown` |
| `source_version` | 当前证据对应版本（竞品资料 / 安装包 / demo 环境的版本） | 版本串（如 `4.1.0`）或 `unknown` |
| `product_version` | 目标产品版本 | 版本串或 `unknown` |
| `account_role` | demo 角色 | 角色名 / `not-applicable` |
| `permission_scope` | demo 权限范围 | 权限描述 / `not-applicable` |
| `captured_at` | 运行时采集时间 | ISO 8601 或 `not-applicable` |
| `usage_scope` | 使用范围 | `internal-product-research`（默认） |

语义红线（必须严格区分）：

- **公司不是产品**：`lanlnk` / `gdcreia` / `lianyou` 是公司标识；`lnkcre` / `lnkcrm` /
  `lnkcard` / `lnkreport` 等是产品标识。不得把公司 slug 填进 `target_product` /
  `competitor_product`。
- **`workspace_company` ≠ `target_company`**：资料归档在哪家库 ≠ 被分析产品属于哪家。跨公司
  资料按 `cross-company-context` 状态单列（见 §5），不静默合并。
- **`source_version` ≠ `product_version`**：前者是竞品证据版本，后者是目标产品版本；多版本
  不得拼成同一部署状态。
- **`competitor_company` 与 `competitor_product` 不得合并为单一 vendor 字段**：历史 `vendor`
  字段可兼容读取，但它只能表示竞品公司，不能替代竞品产品。只知道竞品公司、不知道具体产品时
  写 `competitor_product: unknown`，允许保存为公司级待确认线索，**不能直接生成具体产品能力
  结论**。

## 2. 竞品关系是多对多

竞品关系不是 `target_product → competitor_company`，而是：

```
target_company + target_product
        ↕
competitor_company + competitor_product
```

- 同一竞品公司可有多个竞品产品（`mingyuan` → 云资管 / 云物业 / 云公寓），但**每个
  competitor_product 必须分别记录**证据、版本、能力和限制；同一竞品公司的不同产品不得合并
  为一个能力清单。
- 同一竞品产品可被多个目标产品引用（`target_product=lnkcre + competitor_product=X` 与
  `target_product=lnkcrm + competitor_product=X`），但**两条映射必须分别建立**，不自动共享
  差距、优先级或 PRD 结论（映射的生成与对比矩阵归 competitor-product-analyzer /
  product-prd-generator，见各自 SKILL.md）。
- 只看到一个竞品产品，不能推断整个竞品公司产品线。

## 3. 资料分类字段（material-importer 采集入库层）

每批资料入库时至少区分：

```yaml
workspace_company: <归档公司>
target_company: <目标公司或 unknown>
target_product: <目标产品或 unknown>
competitor_company: <竞品公司或 unknown>
competitor_product: <竞品产品或 unknown>
material_kind: document | screenshot | database | package | demo-runtime | code | other
source_format: pptx | docx | xlsx | pdf | html | image | sql | zip | jar | other
topic: <资料主题>
source_version: <版本或 unknown>
usage_scope: internal-product-research
```

- `material_kind` 判定的是**载体性质**（这是文档/截图/数据库/安装包/demo 运行时材料/代码/
  其他），不是业务能力判断。
- 旧材料缺字段时保持 `unknown`，不批量猜测、不自动回填。

## 4. 分类判断边界

material-importer **可以判断**：

- 这是什么文件（格式 / material_kind）
- 来自哪个公司资料库（workspace_company）
- 属于哪个目标产品或竞品产品（上下文字段，未知即 unknown）
- 是文档、截图、数据库、安装包还是 demo 运行时材料
- 应该放入 incoming / raw / materials 哪一层
- 是否需要 OCR、视觉回看或原件升级（text-sparse / 表格守卫信号）
- 是否存在重复、缺来源、版本未知或脱敏风险

material-importer **不应判断**（下游 skill 职责）：

- 竞品是否具备完整能力（→ competitor-product-analyzer）
- 竞品与目标产品谁更强（→ competitor-product-analyzer 对比矩阵）
- 目标产品是 existing / partial / missing（→ product-prd-generator）
- 是否应进入 PRD（→ product-prd-generator + owner decision）
- 竞品能力是否构成产品需求（→ product-prd-generator + owner decision）

## 5. 分类层失败状态

| 状态 | 含义 | 处理 |
|---|---|---|
| `workspace-context-missing` | 无法确定归档公司 | 走 P0.0 公司确定流程（question 询问），不猜公司 |
| `target-context-missing` | 无法确定目标公司/产品 | 字段保持 `unknown`，不套默认产品 |
| `competitor-context-missing` | 无法确定竞品公司/产品 | 字段保持 `unknown`；公司级线索单列，不出能力结论 |
| `version-mismatch` | 多版本来源未确认一致 | 分别记录各自 `source_version`，不拼成同一部署状态 |
| `cross-company-context` | 资料的 workspace 公司与 target/competitor 公司不一致 | 单列标注，不静默合并进任一家权威库 |
| `projection-unverified` | 投影（md/OCR/截图）未经原件核验且可能失真 | 沿用 provenance-evidence-boundary 的证据边界，不把投影当原件事实 |

状态语义总纲：缺公司不能猜公司；缺产品不能套默认产品；缺竞品产品不能把竞品公司当产品；
同名产品不能自动合并（`entity-conflict`，判定归下游 skill）；投影失真不能当原件事实。

## 6. 授权 demo 快照归档（material-importer 采集职责）

**授权 demo 登录、只读探测和运行时快照的保存归档属于 material-importer（采集入库层）。**
competitor-product-analyzer 消费已归档快照与 raw/materials 投影，不重复登录 demo。
页面抽取的操作方法（A/B/C 三档、locator 纪律、菜单机制探测）沿用 competitor-product-analyzer
的 `references/page-extraction-strategy.md`；**归档契约（目录、manifest、哈希、脱敏门禁、
清理）以本节为准**，分析侧消费与失败模式见 competitor-product-analyzer 的
`references/runtime-snapshot-protocol.md`。

标准流程：

```
确认授权（账号来源合法，凭据只进 .auth.json，mode 0600）
→ 登录一次（验证码走半自动登录）
→ 定点只读探测（不执行写操作）
→ 保存脱敏 runtime snapshot（本节契约落位）
→ 记录公司/产品/竞品上下文（manifest §6.1 字段）
→ 计算哈希（逐产物 sha256）
→ 清理 Cookie/Token/storage/profile（不落盘）
→ 后续离线消费（不默认重登）
```

### 6.1 快照 manifest 必须记录

```yaml
workspace_company: <归档公司>
target_company: <目标公司或 unknown>
target_product: <目标产品或 unknown>
competitor_company: <竞品公司>
competitor_product: <竞品产品>
base_url: <demo URL>
source_version: <demo 版本或 unknown>
captured_at: <ISO 8601>
account_role: <角色或 unknown>
permission_scope: <权限或 unknown>
scenario: <探测场景>
pages:
  - page_id: <稳定 ID>
    url: <页面 URL>
    locator: <菜单/路由/页面定位>
    artifacts:
      - path: <相对路径>
        sha256: <哈希>
        redaction_status: redacted | no-sensitive-content | pending-redaction
limitations:
  - <版本、角色、动态渲染、未验证项>
```

版本/角色/权限未知时填 `unknown` 并进下游 pending，不猜测回填。

### 6.2 快照内容包括

```text
<快照包根>/
├── manifest.json
├── flow.md                        # 可选：跨页面流程（步骤序列 + page-id 引用）
└── pages/<page-id>/
    ├── page.html
    ├── screenshot.png             # 已脱敏
    ├── accessibility.json
    └── observation.md
```

落位：快照包放在公司基座 raw 层的竞品目录下（如
`raw/<项目>/02-competitors/<competitor_company>/runtime-snapshots/<batch>/`；`<batch>` 建议含
日期与角色）。历史路径（`incoming/competitor-<vendor>/runtime-snapshots/`、
`raw/.../05-实施与服务/demo-runtime/`）的既有产物继续有效、不迁移。

边界：**HTML 只是证据包的一部分，不能恢复完整离线 demo**——快照是脱敏运行时证据包，
不是可交互 demo 的替代品。脱敏门禁与会话清理红线沿用 competitor-product-analyzer
`references/safety-and-ethics.md` 与 `runtime-snapshot-protocol.md`：无法确认已脱敏的产物
不进 materials（`pending-redaction`），凭据/Token/Cookie/storage/profile 不落盘。
