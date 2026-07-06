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
  "schema_version": "1.0",
  "vendor": "qimao",
  "product": "旗茂 BS 商管系统",
  "generated_at": "2026-07-06T11:30:00+08:00",
  "input_mode": "manual-plus-demo",
  "account_role_observed": "管理员",
  "manual_version_date": "2024-08",
  "capabilities": [
    { /* 见下方 Capability 对象 */ }
  ]
}
```

## Capability 对象

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `capability_id` | string | 是 | 全局唯一，格式 `CAP-<module>-<capability_slug>`，如 `CAP-合同管理-新合同申请` |
| `vendor` | string | 是 | 竞品代号（kebab-case），如 `qimao` |
| `product` | string | 是 | 竞品全名，如 `旗茂 BS 商管系统` |
| `module` | string | 是 | 业务模块名（中文，对齐商管 8 模块：招商/合同/财务/营运/物业/系统/推广/资源）|
| `capability_name` | string | 是 | 能力名（中文，原词保留）|
| `original_term` | string | 是 | 竞品原始术语，如 `新合同申请单` |
| `standard_term` | string | 否 | 归一后的蓝联标准 ID（如 `lease-contract-management`）；未映射时为 null 并进 review |
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
| `confidence` | enum | 是 | `high` / `medium` / `low` |
| `status_vs_lanlnk` | enum | 是 | `existing` / `partial` / `missing` / `better-than-lanlnk` / `unknown` |
| `quality_assessment` | enum | 是 | `Leading` / `Competitive` / `Behind` / `Missing` |
| `notes` | string | 否 | 自由备注（脱敏后的观察）|

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

每条 Capability 的 `evidence[]` 是简化引用，完整证据在 `evidence-ledger.json`：

```json
{
  "source_type": "manual | demo-runtime | screenshot | data-dictionary | proposal | sales-material",
  "source_ref": "materials/13-competitors/qimao/05-实施与服务/合同模块操作手册.pdf §3.2 p.45",
  "screenshot": "imgs/合同管理_3_新合同申请表单.png",
  "url": "http://oa.1qmall.cn/SMallTest/contract/new",
  "probed_at": "2026-07-06T11:30:00+08:00",
  "account_role": "管理员"
}
```

**字段约束**：

- `source_type=manual` 时：`source_ref` 必填（文件路径 + 章节 + 页码）
- `source_type=demo-runtime` 时：`url` + `probed_at` + `account_role` 必填
- `source_type=screenshot` 时：`screenshot` 必填（相对 `imgs/` 路径）
- `source_type=sales-material` 时：自动将所属 Capability 的 `confidence` 上限设为 `low`
- 所有 `screenshot` 必须已脱敏（客户名/手机号/金额打码）

## 校验规则（P3 必须自检）

1. 每条 capability 至少 1 条 evidence
2. `capability_id` 全局唯一
3. `capability_type` 取值合法
4. `confidence` 与 evidence 一致：
   - `high` 需要 ≥2 条独立来源互证，或 manual + demo-runtime 一致
   - `medium` 单一来源
   - `low` 仅 sales-material 或无法复现
5. `status_vs_lanlnk=unknown` 时必须进 `review/pending-items.md`
6. `quality_assessment=Missing` 不等于"竞品没有"，仅表示"未观察到"
7. `standard_term=null` 时必须进 `review/pending-items.md`

## 去重规则

同一业务能力在多份资料出现时，合并为 1 条 capability，evidence 数组累加。去重 key：

- 优先用 `standard_term`（已归一的）
- 未归一时用 `(module, original_term)`

**不用 `original_term` 单独做 key**：不同厂商/不同手册可能用同一名指代不同业务能力。

## 与 product-prd-generator 的兼容

`standard_term` 必须对齐 product-prd-generator 的 `term-aliases.yaml` 和 `business-ontology.yaml` 中的英文 spec capability ID，否则 P5 蓝联现状映射会失败。

找不到映射时：

1. 在 `review/pending-items.md` 记录"术语未映射：`<original_term>` 拟映射到 `<候选>`，待确认"
2. `standard_term` 暂填 null
3. 不强行编一个新 ID
