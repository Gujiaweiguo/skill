# Incremental PRD Handoff

增量 PRD 是从 docs 规划层交给目标代码仓的变更包，不是代码实现说明书，也不是完整主 PRD 的重写。治理有两个 task-scoped 模式：initial/full 建立 ontology 与 PRD 初始基线；incremental 记录相对已识别 ontology baseline 的 ontology delta 和相对 PRD baseline 的 PRD delta。模式不要求串行调用多个 skill。

Ontology 定义产品领域概念、关系与规则；PRD 定义产品目标、需求和本轮变更。Ontology synthesis 可以综合 customer requirements、competitor information、code facts 与 OPC product ideas，但必须逐项保留 provenance，且 product decision 不能冒充 evidence。候选 ontology 只有经 owner approval 才能晋升 canonical；本 skill 不自动写入 canonical ontology。

共享机器契约见 `product-governance/` 下的 schemas。它们描述跨层引用和记录，不是产品 authority；不确定的 authority/version/revision/release 需显式标为 unresolved，不得猜测。

## 必备章节

1. 文档元数据：`prd_id`、`product_id`、product class/profile、target_repo、本体 authority/version/revision/release 或 unresolved 状态、baseline PRD authority/version 或 unresolved 状态。
2. 变更摘要和来源：区分 `competitor`、`customer`、`product_decision`。
3. 关联本体层引用：对象、能力、术语；UI 约束写入 PRD 内容，不另设产品层。
4. 当前状态：代码/spec/test evidence、`evidence_state`、`implementation_status`。
5. 产品目标与非目标。
6. Given/When/Then 验收场景。
7. OpenSpec change 拆分、负责仓库、依赖序和 ownership。
8. 目标仓库验证门禁：从目标仓库 `AGENTS.md` 读取，不由本 Skill 猜测。
9. 已定决策、开放问题和需要业务裁决的枚举/阈值。
10. 消费提示词、回写要求和归档进度。

## 输入来源纪律

```yaml
source_type: competitor | customer | product_decision | code | spec | test
```

- 竞品证据证明“竞品观察到什么”，不自动证明“必须建设”。
- 客户需求记录客户的明确要求和优先级。
- 产品判断必须带 decision owner、reason 和 decision status。
- `product_decision` 记录需走独立 decision provenance（decision id/owner/status/rationale），不能作为观察证据或替代 supporting sources。
- 代码/测试/spec 只能证明当前实现事实，不能自动改写产品目标。

## 状态分离

`evidence_state`：`observed | inferred | not_found | not_scanned | inaccessible | conflicting`

`implementation_status`：`existing | partial | missing | explicitly-not-do | unknown`

`not_scanned`、`inaccessible`、`not_found` 不得直接渲染为 `missing`。

## 推荐机器字段

```yaml
product_id: lnkcre
product_class: business
ontology_profile: business-ontology
ontology_baseline:
  product_id: lnkcre
  product_class: business
  ontology_profile: business-ontology
  layer: ontology
  status: resolved
  authority_ref: 30-products/lnkcre/ontology/README.md
  version: <owner-confirmed-version>
prd_baseline:
  product_id: lnkcre
  product_class: business
  ontology_profile: business-ontology
  layer: prd
  status: resolved
  authority_ref: 30-products/lnkcre/prd/baseline/
  version: <owner-confirmed-version>
trace_id: PRD-CRE-2026-014
capability_id: CRE-LEASE-RENT-FREE-SEGMENTS
source_refs: [EV-023, REQ-014]
target_repo: /opt/code/lnkcre
target_spec_ids: [lease-contract-management]
suggested_change_ids: [cre-rent-free-period-model]
acceptance_ids: [AC-001, AC-002]
ui_refs: []
```

`<owner-confirmed-version>` is illustrative and must be replaced by a verified value; when unavailable, use `status: unresolved` plus `reason` and omit authority/version fields that are not known.

## 实施回写

目标仓库返回 `implementation-return-package`，至少说明：

- change 是否创建、实施、验证、归档；
- 测试和 gate 证据路径；
- blocked、partial 或 false-positive 项；
- 发现的模型偏差和待裁决项；
- 需要 docs 侧更新的 trace、PRD、能力台账和 Semantic Release 候选。

docs 侧只根据 reviewed return package 更新权威文档，不做静默覆盖。
