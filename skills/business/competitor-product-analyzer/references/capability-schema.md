# Capability Schema — 竞品能力抽取字段规范

本文件定义 `capability-map.json` 中每条能力的字段规范。SKILL.md 的 P3 阶段强制遵循此 schema。

## 设计原则

1. **可追溯**：每条能力必须挂至少 1 条 evidence
2. **可对齐**：每条能力必须有 standard_term 用于与蓝联对齐
3. **可分级**：quality_assessment 描述实现质量，不是有没有
4. **可对比**：status_vs_lanlnk 描述与蓝联的相对关系

## 顶层结构

```json
{
  "schema_version": "1.3",
  "workspace_company": "lanlnk",
  "target_company": "lanlnk",
  "target_product": "lnkcre",
  "competitor_company": "qimao",
  "competitor_product": "旗茂 BS 商管系统",
  "vendor": "qimao",
  "product": "旗茂 BS 商管系统",
  "generated_at": "2026-07-06T11:30:00+08:00",
  "input_mode": "manual-plus-demo",
  "account_role_observed": "管理员",
  "target_repo": "/opt/code/lnkcre",
  "manual_version_date": "2024-08",
  "package_version": "3.2.1",
  "capabilities": [
    { /* 见下方 Capability 对象 */ }
  ]
}
```

> **统一竞品关系上下文**（workspace_company / target_company / target_product / competitor_company / competitor_product / source_version / product_version / account_role / permission_scope / captured_at / usage_scope）字段定义唯一权威源：`skills/business/material-importer/references/material-classification.md`。`vendor` / `product` 是 legacy 字段：`vendor` = competitor_company（竞品公司）、`product` = competitor_product（竞品产品），兼容保留；**不得把 vendor 当合并的"竞品公司+产品"概念使用**。`target_repo` 未知时进 review；目标产品未知时 target_company/target_product 填 `unknown` 并走「无目标产品模式」。`schema_version=1.3` = 新增统一上下文字段（向后兼容，旧档按 unknown 解释，不批量回填）。
>
> `package_version`（可选）：存在授权安装包分析时的包版本；与 demo 环境版本、手册版本分别记录，未确认一致时不得在 capability 结论中拼接为同一部署状态（规则见 `evidence-ledger.md`）。`schema_version=1.2` = Evidence 简版新增可选引用字段，向后兼容。

## Capability 对象

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `capability_id` | string | 是 | 全局唯一，格式 `CAP-<module>-<capability_slug>`，如 `CAP-合同管理-新合同申请`；同一 competitor_product 在不同 target_product 下的映射分别建册时，capability_id 各自独立（不跨目标产品复用结论） |
| `trace_id` | string | 是 | 跨竞品分析、增量 PRD、OpenSpec 和回写的稳定追踪 ID |
| `workspace_company` | string | 否 | 资料归档公司（material-classification.md 定义；缺省按解析出的公司基座解释）|
| `target_company` | string | 否 | 目标产品所属公司（legacy 档缺省按 lanlnk 历史语境解释，新采集必填）|
| `target_product` | string | 是 | 目标产品 ID（company.yaml products 归一），如 `lnkcre`、`lnkcrm`、`lnkreport`；无目标产品模式填 `unknown` |
| `target_repo` | string | 否 | 目标产品代码仓路径；未知时进 review |
| `competitor_company` | string | 是 | 竞品公司（legacy 字段 `vendor` 同义，二选一必填）|
| `competitor_product` | string | 是 | 竞品公司的具体产品（legacy 字段 `product` 同义）；只知道公司时填 `unknown`，只能存公司级待确认线索 |
| `vendor` | string | 否 | legacy = competitor_company，兼容保留 |
| `product` | string | 否 | legacy = competitor_product，兼容保留 |
| `module` | string | 是 | **竞品产品语境下的模块**（竞品自己的菜单/模块名，如合同管理）；目标产品模块对齐发生在 `standard_term` 映射，不在此字段 |
| `capability_name` | string | 是 | 能力名（中文，原词保留）|
| `original_term` | string | 是 | 竞品原始术语，如 `新合同申请单` |
| `standard_term` | string | 否 | 归一后的**目标产品**标准 ID（如 `lease-contract-management`）；未映射时为 null 并进 review；无目标产品模式不归一（恒 null）|
| `capability_type` | enum | 是 | 见下方取值表 |
| `scenario` | string | 否 | 业务场景一句话，如 `招商定稿后发起合同审批` |
| `role` | string[] | 否 | 涉及角色，如 `["招商经理", "法务"]` |
| `workflow` | string[] | 否 | 流程步骤（按顺序），如 `["选铺位", "录条款", "提交审批"]` |
| `fields` | string[] | 否 | 涉及字段名（仅字段型能力必填）|
| `permissions` | string[] | 否 | 权限规则，如 `["招商经理可建", "法务可审"]` |
| `reports` | string[] | 否 | 涉及报表名（仅报表型能力）|
| `integrations` | string[] | 否 | 集成接口/系统，如 `["POS", "财务系统"]` |
| `data_structures` | string[] | 否 | 涉及数据表/实体（仅数据结构型能力）|
| `evidence` | Evidence[] | 是 | 至少 1 条，见 evidence-ledger.md |
| `evidence_ids` | string[] | 否 | 指向 evidence-ledger 的 `EV-NNN` 列表（与 evidence[] 简版引用并存，台账仍是唯一权威记录）|
| `confidence` | enum | 是 | `high` / `medium` / `low` |
| `status_vs_lanlnk` | enum | 条件必填 | `existing` / `partial` / `missing` / `better-than-lanlnk` / `unknown`；语义 = 相对 target_company+target_product 的现状（历史字段名）。**仅在有目标产品基线时输出**；无目标产品模式不填（null）|
| `evidence_state` | enum | 是 | `observed` / `inferred` / `not_found` / `not_scanned` / `inaccessible` / `conflicting` |
| `implementation_status` | enum | 是 | `existing` / `partial` / `missing` / `explicitly-not-do` / `unknown`；**只描述竞品实现观察，不等于目标产品状态** |
| `quality_assessment` | enum | 是 | `Leading` / `Competitive` / `Behind` / `Missing` |
| `source_version` | string \| null | 否 | 当前证据对应版本（竞品资料/安装包/demo 版本）；缺失 = unknown，禁止猜测回填 |
| `usage_scope` | string | 否 | 缺省 = `internal-product-research` |
| `limitations` | string[] \| null | 否 | 本条能力的限制（版本/角色/配置/未复现等）|
| `notes` | string | 否 | 自由备注（脱敏后的观察）|

> `evidence_state`/`confidence` 的 capability 级取值表达「该能力的观察状态」，与成员 evidence 原值冲突时以成员原值为准，并进 pending-items。capability 摘要必须可回溯到原始 claim 与来源证据；`standard_term`/`target_product` 目标产品映射不得替代原始主张。

## capability_type 取值

| 取值 | 含义 | 典型场景 |
|---|---|---|
| `功能` | 用户可见的产品功能 | 新建合同、铺位建档、报表导出 |
| `流程` | 跨角色的业务流程 | 招商洽谈 → 报价 → 意向 → 合同审批 |
| `字段` | 业务对象的字段定义 | 合同.免租期（支持分段）、铺位.多经点位类型 |
| `权限` | 角色/数据/模块权限模型 | 招商经理只能看自己负责的铺位 |
| `数据结构` | 表结构/字段/约束 | 合同主表、铺位主表、结算明细表 |
| `报表` | 报表/看板/驾驶舱 | 招商漏斗周报、租金实收月报、集团驾驶舱 |
| `集成` | 与外部系统的对接 | POS、停车、客流、电子签、支付网关 |
| `AI/BI` | AI 问数、RAG、BI Copilot | 经营数据自然语言查询、制度问答 |

## Evidence 对象（指向证据台账的简版）

每条 Capability 的 `evidence[]` 是简化引用，完整证据与字段定义在 `evidence-ledger.json`（**字段与枚举唯一权威：`evidence-ledger.md`**）：

```json
{
  "source_type": "manual | demo-runtime | screenshot | data-dictionary | proposal | sales-material | package-static | code-analysis",
  "evidence_kind": "document | structure | runtime | implementation",
  "source_ref": "materials/13-competitors/qimao/05-实施与服务/合同模块操作手册.pdf §3.2 p.45",
  "source_version": "3.2.1",
  "source_sha256": "<归档或原件 SHA-256，可选>",
  "artifact_locator": { "…": "结构化锚点，规范见 evidence-ledger.md，可选" },
  "verification_status": "unverified | static-only | runtime-observed | snapshot-observed | cross-checked",
  "screenshot": "imgs/合同管理_3_新合同申请表单.png",
  "url": "http://oa.1qmall.cn/SMallTest/contract/new",
  "probed_at": "2026-07-06T11:30:00+08:00",
  "account_role": "管理员"
}
```

**字段约束**：

- `source_type=manual` 时：`source_ref` 必填（文件路径 + 章节 + 页码）
- `source_type=demo-runtime` 时：`url` + `probed_at` + `account_role` 必填；来自离线快照证据包时另挂 `verification_status=snapshot-observed`，`artifact_locator` 指向快照包 manifest + page-id + 产物哈希（兼容示例见下，规范见 `evidence-ledger.md` 与 `runtime-snapshot-protocol.md`，不批量回填历史条目）

```json
{
  "source_type": "demo-runtime",
  "evidence_kind": "runtime",
  "source_ref": "raw/prd-商管系统/02-competitors/qimao/runtime-snapshots/2026-11-17-admin/pages/contract-new/observation.md",
  "source_version": "3.2.1（demo 环境版本）",
  "artifact_locator": { "batch": "runtime-snapshots/2026-11-17-admin", "page_id": "contract-new", "manifest": "manifest.json", "artifact": "page.html", "sha256": "<page.html sha256>" },
  "verification_status": "snapshot-observed",
  "limitations": "仅证明该版本/角色/时间/场景；SPA 动态交互未离线恢复",
  "probed_at": "2026-11-17T10:30:00+08:00",
  "account_role": "管理员"
}
```
- `source_type=screenshot` 时：`screenshot` 必填（相对 `imgs/` 路径）
- `source_type=package-static` / `code-analysis` 时：`source_version` + `source_sha256`（归档哈希）+ `artifact_locator` 必填；code-analysis 另须在取证记录登记工具及版本与业务问题（见 `static-analysis-and-reverse-engineering.md`）
- `source_type=sales-material` 时：自动将所属 Capability 的 `confidence` 上限设为 `low`
- 所有 `screenshot` 必须已脱敏（客户名/手机号/金额打码）
- 所有 `evidence_kind` 的判定与其"不得自动证明"边界按 `evidence-ledger.md`「认识论上限」执行

## 多对多竞品映射规则

竞品关系是 `target_company + target_product ↔ competitor_company + competitor_product` 的多对多：

- **同一竞品公司多个产品不得合并**：haiding 的 海鼎 CRE 与 海鼎 CRM 产品、mingyuan 的 云资管/云物业/云公寓，各自独立建 capability-map（分目录、分清单），证据、版本、能力、限制分别记录。只看到一个竞品产品不能推断整个竞品公司产品线。
- **同一竞品产品被多个目标产品引用时分别建映射**：`target_product=lnkcre + competitor_product=X` 与 `target_product=lnkcrm + competitor_product=X` 是两份 capability-map / 两套对比矩阵，不自动共享差距、优先级或 PRD 结论；结论按各自目标产品的 ontology/功能清单重新归一与映射。
- **公司不是产品**：不得把 lanlnk / gdcreia / lianyou 等公司 slug 填进 target_product / competitor_product；gdcreia / lianyou 的目标产品经各自 company.yaml products 解析。
- `competitor_product: unknown` 时只允许公司级待确认线索（资料索引/版本线索），不得生成具体产品能力结论（进 pending，行类型 `competitor-context-missing`）。
- 同名竞品产品/公司不得自动合并（`entity-conflict` 进 pending 人工裁决）。

## 无目标产品模式（target_company / target_product = unknown）

无目标产品时允许输出：竞品公司/产品资料索引、竞品能力清单（`status_vs_lanlnk` 全部不填）、证据台账、版本/角色/权限/采集限制、待验证问题、可借鉴设计观察（不绑定目标产品优先级）。禁止输出：相对我方产品的 existing/partial/missing、目标公司产品差距、PRD 需求、目标产品版本规划、目标公司改进优先级。`standard_term` 恒为 null（无目标 ontology 可归一）；术语归一与现状映射整段跳过并标注 `target-context-missing`。

## 校验规则（P3 必须自检）

1. 每条 capability 至少 1 条 evidence
2. `capability_id` 全局唯一
3. `capability_type` 取值合法
4. `confidence` 与 evidence 一致：
   - `high` 需要 ≥2 条独立来源互证（独立 = 经来源链折叠后仍分属不同链，且版本/适用范围确认一致），或 manual + demo-runtime 版本匹配时一致
   - `medium` 单一来源
   - `low` 仅 sales-material 或无法复现
5. `status_vs_lanlnk=unknown` 时必须进 `review/pending-items.md`
6. `quality_assessment=Missing` 不等于"竞品没有"，仅表示"未观察到"
7. `standard_term=null` 时必须进 `review/pending-items.md`
8. `evidence_state=not_scanned|inaccessible|not_found` 时不得把 `implementation_status` 自动设为 `missing`；**反编译失败/不可分析（not-analyzable）同此**，标 `not_scanned`/`inaccessible` + limitations，不判缺失
9. 新增或修订能力必须有 `trace_id`、`target_product` 和至少一个 `source_ref`
10. 摘要/归并/`standard_term` 映射不得修改任何成员 evidence 的 `evidence_state`/`confidence` 原值；冲突以成员原值为准并进 pending-items
11. 断链或缺 `evidence_id`/`trace_id` 的观察不得导出为 verified；禁止伪造或静默补齐 ID，显式标待核实
12. 同一来源链（同一原件的转换文本/OCR/能力模型/交接包，及同一安装包内的 DDL/路由/代码）互证只计一次；`independence=unknown` 不得参与互证；不同文件/source_type/evidence_kind 本身不构成独立性依据
13. `standard_term`/`target_product` 目标产品映射是描述性参考，**不是需求授权**；采纳与否由 owner decision 决定
14. `evidence_kind=structure` 的证据只支撑结构层主张（存在表/路由/配置），`evidence_kind=implementation` 只支撑实现层主张（该版本代码含该实现）；capability 的 `quality_assessment`/`notes` 表述不得越层（"已部署/已启用/实际执行"需 runtime 或 document 在匹配版本内佐证）
15. 安装包版本与 demo/手册版本未确认一致时，capability 结论按来源分别限定（`applies_to`/`source_version`），不得拼接为同一部署状态或据此互证升级
16. `verification_status` 不得自动映射为 `evidence_state=observed`（过程维度与主张状态维度分离，见 `evidence-ledger.md`）
17. `competitor_company` 与 `competitor_product` 语义不得合并：legacy `vendor` 只表示竞品公司；`competitor_product=unknown` 时不得输出具体产品能力结论
18. 同一竞品公司多个产品的能力不得合并为一份清单；同一 competitor_product 在不同 target_product 下必须分别建册，capability_id / status / 结论不跨目标产品复用
19. `target_company`/`target_product` = unknown（无目标产品模式）时：`status_vs_lanlnk` 必须为空、`standard_term` 必须为 null，禁止输出目标产品差距或 PRD 需求（状态 `target-context-missing`）
20. `module` 必须取竞品产品语境的模块名；把目标产品模块名（如商管 8 模块）直接写进 `module` 而未经 `standard_term` 映射属校验失败

## 去重规则

同一业务能力在多份资料出现时，合并为 1 条 capability，evidence 数组累加。去重 key：

- 优先用 `standard_term`（已归一的）
- 未归一时用 `(module, original_term)`

**不用 `original_term` 单独做 key**：不同厂商/不同手册可能用同一名指代不同业务能力。

**合并去重只合并 capability 表达，不合并证据计数**：同链 evidence 互证只计一次（见 `evidence-ledger.md`「来源谱系」），各 evidence 条目保留 evidence_id；evidence 数组累加规则不变。

## 与 product-prd-generator 的兼容

`standard_term` 必须对齐目标产品 adapter 的 aliases/ontology；只有 LnkCRE/MI-CRE 才默认参考商管 `business-ontology.yaml`，其他产品不得静默复用商管术语。

找不到映射时：

1. 在 `review/pending-items.md` 记录"术语未映射：`<original_term>` 拟映射到 `<候选>`，待确认"
2. `standard_term` 暂填 null
3. 不强行编一个新 ID

## 与共享产品治理契约的映射

跨 skill 交接使用共享契约 `/opt/code/skill/skills/business/product-prd-generator/references/product-governance/`（owner 为 product-prd-generator；本 skill 只消费不修改，字段与枚举以共享 schema 为准，此处不重复定义），包括 `source-reference.schema.json` 与 `ontology-change-set.schema.json`。映射关系：

- `capability_id`、`trace_id`、`target_product` 原值透传到共享 source-reference 的同名字段；`capability-map.json` 仍是这些 ID 的唯一权威记录，共享 schema 只链接不取代
- `evidence[].source_ref` 透传为共享 `source_ref`（公司根相对路径，如 `materials/13-competitors/<vendor>/…`；外部 URL 与代码仓引用除外），并由消费方回链 `evidence_id` 指向 `evidence-ledger.json` 的台账条目
- 竞品能力观察导出为 `competitor_observation` 类型的 source reference；`evidence_state`、`confidence` 按本 schema 记录的原值填写
- 交接导出每条竞品观察须保留 evidence_id、capability_id、trace_id、source_ref、slide/page 锚点、claim_type、evidence_state、confidence、谱系关联（derived_from/independence/applies_to）与 pending/review 状态；缺失或断链显式待核实；旧条目缺 lineage 字段按 unknown 解释（向后兼容）

`standard_term=null` 的术语要进 ontology 治理流程，只能作为共享 `ontology-change-set` 的 `draft` 提案输入（`changes[].source_ids` 指向上述 source reference）。提案不会自动晋升 canonical ontology，也不构成 PRD 必须实现的 feature；采纳与否由单独记录的 owner decision 决定（来源边界详见 `evidence-ledger.md`）。
