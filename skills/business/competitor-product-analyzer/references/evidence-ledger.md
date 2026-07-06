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
    └── 是 → confidence = high

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

## 复核建议

`evidence-ledger.md`（人类可读版）按 capability 分组列出全部证据，便于：

- 用户抽查关键能力的证据链
- product-prd-generator 复用改进建议时追溯依据
- strategy-brief-generator 引用竞品能力时核对置信度
