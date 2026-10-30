# Evidence Ledger — 证据台账与置信度规则

本文件定义 `evidence-ledger.json` 的字段规范与置信度判定规则。SKILL.md 的 P3、P7 阶段强制遵循。

## 设计原则

**每条能力判断必须可追溯。** 证据台账是本 skill 的质量底线，防止把销售话术当产品事实、把 demo 看不到当竞品没有。

## 证据类型与强度

### source_type 强度分级

| source_type | 含义 | 默认强度 | 可达置信度上限 |
|---|---|---|---|
| `manual` | 操作手册 / 功能手册（实施与服务类）| 强 | high（需 ≥2 份互证）|
| `demo-runtime` | demo 运行时探测（亲见）| 强 | high（需 manual 互证）|
| `data-dictionary` | 数据字典 / 表结构 / SQL DDL | 强 | high（数据结构类能力的权威证据）|
| `screenshot` | 截图（已脱敏）| 中 | medium（单一来源）|
| `proposal` | 方案汇报 PPT / 售前方案 | 弱 | medium（汇报会夸大）|
| `sales-material` | 销售策略 / 培训资料 / 话术 | 极弱 | **low（强制上限）** |

**关键规则**：

- `sales-material` 类证据的 capability，`confidence` **强制上限为 low**，无论其他证据多少
- `proposal` 单独存在时置信度上限 medium，需 manual 或 demo-runtime 佐证才能升 high
- `manual` 与 `demo-runtime` 互证（描述同一能力且语义一致）可达 high
- 同类型的两份 manual 互证也可达 high（如操作手册 + 功能手册都描述同一字段）

## confidence 判定决策树

```
Step 1: 证据中是否含 sales-material？
    └── 是 → confidence = low（强制）

Step 2: 证据是否只有单一来源？
    └── 是 → confidence = medium

Step 3: 是否有 ≥2 条独立来源（不同 source_type 或不同文件）描述同一能力且语义一致？
    │  （互证计数前先按来源链折叠：同一原件派生的同链条目只计 1 条来源；
    │   independence=unknown 的并存证据不计入独立来源数）
    ├── 是（且均为独立来源链）→ confidence = high
    └── 独立性无法判定（unknown）→ 不得因并存升级，相关条目进 pending 待核实

Step 4: 仅 proposal 类？
    └── 是 → confidence = medium（不能升 high，除非有 manual/runtime 佐证）

Step 5: 运行时无法复现 manual 描述的能力？
    └── 是 → confidence = low + 进 review（可能是版本差异/权限不足/手册过旧）

Step 6: 资料日期 >2 年？
    └── 是 → confidence 降一级（high→medium, medium→low）+ 标注"基于 YYYY 版"
```

## Evidence 对象字段

`evidence-ledger.json` 顶层：

```json
{
  "schema_version": "1.0",
  "vendor": "qimao",
  "generated_at": "2026-07-06T11:30:00+08:00",
  "evidence": [
    { /* 见下方 Evidence 对象 */ }
  ]
}
```

Evidence 对象：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `evidence_id` | string | 是 | 全局唯一，格式 `EV-NNN`（如 `EV-001`）|
| `capability_id` | string | 是 | 关联的 capability_id（如 `CAP-合同管理-新合同申请`）|
| `claim` | string | 是 | 一句话声明，如"旗茂支持免租期分段（前 3 个月全免，后续 3 个月半免）"|
| `claim_type` | enum | 是 | `证据` / `判断` / `假设` |
| `source_type` | enum | 是 | 见上方强度分级 |
| `source_ref` | string | 是 | 文件路径 + 章节 + 页码，或 URL |
| `screenshot` | string \| null | 否 | 相对 `imgs/` 路径，已脱敏 |
| `url` | string \| null | 否 | demo-runtime 时必填，完整 URL |
| `probed_at` | string \| null | 否 | ISO 8601 时间戳，demo-runtime 时必填 |
| `account_role` | string \| null | 否 | demo-runtime 时必填，如"管理员"/"普通商户"|
| `source_date` | string \| null | 否 | 资料日期（YYYY-MM 或 YYYY），手册版本日期 |
| `confidence` | enum | 是 | `high` / `medium` / `low`（按决策树判定）|
| `notes` | string | 否 | 自由备注 |

## claim_type 三类标记

每条 evidence 必须标 `claim_type`：

| 标记 | 含义 | 要求 |
|---|---|---|
| `证据` | 来自资料或运行时的事实 | 必须有具体 source_ref |
| `判断` | 基于证据的推理 | 必须列出依据的 evidence_id |
| `假设` | 未证实的假设 | 必须说明如何验证 |

## 来源谱系

Evidence 对象在既有字段之外支持三个**可选** lineage 字段（`derived_from` / `independence` / `applies_to`）。三个字段均为可选增量：旧条目缺失这些字段时按 `independence=unknown` 解释，不破坏既有条目，也不要求回填。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `derived_from` | string[] | 否 | 本条目依据/派生自哪些证据（evidence_id 列表）；空/缺省 = 直接观察 |
| `independence` | enum | 否 | `independent` / `same-chain` / `unknown`；**缺省 = unknown（fail closed）**；`independent` 必须正向确认（确系不同原件）才可填，不得默认 |
| `applies_to` | string | 否 | 适用范围限定（产品/版本/客户/环境），如「客户蓝图：仅 X 项目」|

### 同源去重（来源链折叠）

- **来源链判定**：沿 `derived_from` 传递闭包折叠到根。同一原件派生的以下产物归入**同一来源链**：原文、转换 Markdown、OCR/图片投影、能力模型条目、分析摘要、PRD 交接、汇总 brief——互证计数只计一次。
- **折叠只影响计数语义**：各条目保留各自 `evidence_id` 与原始锚点，不静默删除。
- 下列派生产物**不得**反向作为原始主张的独立证据：转换文本、OCR 结果、统一能力模型、evidence index、S1 能力清单、S1 对比矩阵、产品改进建议、PRD、实施交接包、汇总 brief。
- **正例**：同一 PPT 主张同时出现在转换文本、能力模型条目、分析结果与交接包 → 折叠为同一来源链，互证计数仍只计一个原始来源。

### independence=unknown 三不等规则

`unknown` ≠ 独立（不得参与互证升级）、≠ 同链重复（不得据此合并或丢弃条目）、≠ verified/false（不得改变证据状态）。两条证据描述同一能力但独立性无法判定时：不得因并存提升 confidence、不得按重复丢弃、保持待核实语义。

## 来源类型认识论上限

每种来源类型只能证明其认识论边界内的结论，不得自动越界：

| 来源类型 | 只能证明 | 不得自动证明 |
|---|---|---|
| 操作手册 | 文档记载了该操作/功能 | 已部署/普遍交付 |
| Demo 运行时 | 被观察环境（URL/账号角色/探测时间）中的行为 | 生产部署/所有客户 |
| 数据字典/SQL/表结构 | 数据结构存在、实现线索 | 完整业务流程或业务能力 |
| 方案 PPT/厂商宣称 | 方案提出/厂商声称 | 标准产品已交付 |
| 客户蓝图/实施方案/验收交付材料 | 该客户项目中已设计/已交付 | 标准产品能力（不自动泛化）|

可执行正反例：

- **WHEN** 某能力仅有方案 PPT 主张 → **THEN** 只保持「方案提出/厂商声称」语义与弱证据置信上限，不得仅凭 PPT 变成已交付能力
- **WHEN** 某能力仅有操作手册记载 → **THEN** 结论停留在「文档记载」层级，不得自动变成普遍交付
- **WHEN** 某能力仅来自 demo 运行时观察 → **THEN** 结论限定被观察环境（URL/账号角色/探测时间），不得泛化到生产部署或所有客户
- **WHEN** 仅有数据字典/SQL 表结构线索 → **THEN** 结论限定数据结构层面，不得自动等于完整业务能力
- **WHEN** 同一 PPT 的转换文本、能力模型条目与交接包都出现同一主张 → **THEN** 三者只能算一条来源链，互证计数仍只计一个原始来源

## 缺失字段失败关闭（fail-closed）

Evidence 条目缺失溯源字段时严格按此映射处理，不得静默补齐：

| 缺失项 | 处理 |
|---|---|
| source_sha256 | 来源身份待核实 |
| slide/page 锚点 | 页面定位待核实 |
| evidence_id | 不作为完整可追溯证据消费 |
| evidence_state | 不得推断为 verified |
| source_type | 按弱解释（取最低证明力解释）|
| source_date/version | 适用范围未知 |
| lineage/independence | 不得重复计证（independence 按 unknown）|
| target scope | 不得泛化到标准产品 |

- `unknown` ≠ false ≠ missing ≠ verified ≠ not applicable——五者语义互不替代，不得混用。
- 处理动作 = `claim_type=假设` + `confidence` 降 `low`（导出共享契约时映射为 schema 合法值 `unassessed`）+ 强制进 pending-items（行类型 `missing-provenance`）。
- **禁止**静默补齐；**禁止**自动生成完整 ID 或用当前日期填 `source_date`。

## 证据状态继承与升级

- **只降不升**：文档转换、OCR、摘要、能力合并、能力矩阵生成、PRD 交接、归档或重新表述等下游产物，其证据状态只能**保持或降级**原值，不得自动升级；升级必须有明确新增证据。
- **升级条件**：新增证据 `independence=independent` 且支持同一主张，且 `applies_to`/产品/客户/版本/时间/验证范围与目标结论匹配。
- **升级留痕**（pending-items `upgrade` 行）：新增 evidence_id、升级前状态、升级后状态、升级理由、新增证据证明了什么、产品/客户/版本/时间、实际验证范围、**仍未证明的范围**、受影响的原 evidence_id。
- **范围不匹配 → 不升级**：记录不匹配原因，待人工裁决。

## 治理交接：导出为共享 source-reference

跨 skill 交接（PRD / ontology 工作流）挂接共享契约 `/opt/code/skill/skills/business/product-prd-generator/references/product-governance/`（owner 为 product-prd-generator；本 skill 只消费不修改，字段与枚举以共享 schema 为准，此处不重复定义），包括 `source-reference.schema.json` 与 `ontology-change-set.schema.json`。导出映射：

| 台账字段 | 共享 source-reference 字段 | 说明 |
|---|---|---|
| `evidence_id` | `evidence_id` | 原值透传；台账仍是唯一权威记录 |
| `capability_id` | `capability_id` | 原值透传 |
| `source_ref` | `source_ref` | 公司根（`$COMPANY_BASE` ∥ `$LANLNK_BASE`）相对路径；外部 URL 与代码仓引用保持原样 |
| `probed_at`（缺失时用 `source_date`） | `observed_at` | 运行时探测时间优先 |
| `confidence` | `confidence` | 按台账原值 |

`source_ref` 路径规范：materials/raw 内证据写公司根相对路径（如 `materials/13-competitors/qimao/05-实施与服务/合同模块操作手册.pdf`），demo-runtime 另填 `url`。不得改写为其他产品或其他公司的权威路径，也不得把未核实的绝对路径伪装成相对路径。

**决策不是证据（来源边界）**：

- `claim_type=证据` 导出为 `observed` 的竞品观察；`claim_type=判断` 导出为 `inferred`，且必须能回溯到依据的 `evidence_id`
- OPC/产品 owner 的 roadmap、优先级或 ontology 方向决策，在共享契约里是独立的 `product_decision`（decision 对象按共享 schema），由决策 owner 单独记录。这类决策不进本台账，也不抬高任何竞品观察的 `confidence`
- 只有单独记录的 owner decision 能批准路线图或 ontology 方向；本台账的【判断】条目最多作为决策的 supporting source
- 竞品观察可以支撑共享 `ontology-change-set` 的 `draft` 提案，但永不自动写入 canonical ontology，也不强制任何 PRD feature

## 禁止行为

- 禁止无 source_ref 的 evidence
- 禁止把 sales-material 当 `证据` 类（必须降级为 `判断` 或 `假设`）
- 禁止把 proposal PPT 的功能列表等同于实际能力（proposal 只能作弱证据）
- 禁止把"demo 账号看不到"等同于"竞品没有"——必须标 `claim_type=假设` + `notes="可能权限不足"`
- 禁止 source_date 不明时填当前日期（必须留空或填资料标注的版本日期）
- 禁止截图未脱敏就进 evidence

## 脱敏规则

截图写入 `imgs/` 前必须脱敏：

| 敏感类型 | 处理方式 |
|---|---|
| 客户/商户真实名称 | 替换为 `客户A` / `商户B` |
| 手机号 | 打码为 `138****1234` |
| 身份证号 | 打码为 `4401**********1234` |
| 金额 | 保留数量级，替换为 `X 万` |
| 邮箱 | 打码为 `z***@example.com` |
| 地址 | 保留城市，具体地址打码 |

**脱敏后必须在 evidence.notes 标注**："截图已脱敏：客户名/手机号/金额"。

## 待确认项规则

`review/pending-items.md` 必须记录以下情况：

| 类型 | 触发 | 处理 |
|---|---|---|
| 术语未映射 | standard_term=null | 列出 original_term + 候选映射，待用户确认 |
| demo 权限不足 | accessible=false 的页面/模块 | 列出模块名 + requires_role，标注"该模块能力未探测"|
| 手册版本过旧 | source_date >2 年前 | 列出文件 + 日期，建议补充新版 |
| 资料类型单一 | 只有 sales-material 或只有 proposal | 标注置信度上限，建议补充 manual |
| 能力冲突 | manual 与 runtime 描述不一致 | 列出冲突点，标注"可能是版本差异"，置信度降级 |
| 蓝联现状无法判断 | status_vs_lanlnk=unknown | 列出 capability + 原因（功能清单未覆盖/语义不清）|
| `missing-provenance` | 缺 SHA/锚点/evidence_id/状态/来源类型/版本/独立性 | 列出缺失字段与待核实影响，禁补齐 |
| `upgrade` | 有新增独立证据拟升级状态/置信度 | 按「证据状态继承与升级」的留痕字段逐项记录 |

## 复核建议

`evidence-ledger.md`（人类可读版）按 capability 分组列出全部证据，便于：

- 用户抽查关键能力的证据链
- product-prd-generator 复用改进建议时追溯依据
- strategy-brief-generator 引用竞品能力时核对置信度
