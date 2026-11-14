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

## 版本链与回写结构（2026-11-04 海鼎合同域全弧线实证）

增量 PRD 在吸收期内是**活文档**，以内部小版本链演进，不是每版新文件：

1. **文件与版本可辨**：一个增量一个活文档。字母版（如 v0.3-a）与点分版（如 v0.7.10）存量命名不强制迁移；同一增量内部命名规则应一致，版本可辨，版本史记录版本、日期、触发事件与触及章节。
2. **一次评审/吸收批次可包含多个相关事件**：owner 裁决登记、核验/实施回执吸收、实施包签发可以合并为一版，但版本史须逐项列明每个事件及来源；每版只改受影响章节，禁全文重写。
3. **事实判断可修正**：PRD 侧 implementation_status 初判如基于基线推断，必须如实标记 evidence_state=inferred 并给出依据。代码级核验可以修正初判；不能一概判为「无错」，须核对初判是否有依据、标注是否诚实，并保留原判定、新证据与修正原因。
4. **四个状态空间分离**：切片交付生命周期、implementation_status、evidence_state、开放问题状态分别记录。新证据可修正事实判断或重新打开问题，保留原判定及修正依据；不得用「只前进」拒绝合法勘误，也不得倒写已发生的授权、消费或验证历史。切片状态词表仍为 pending-owner-triage / pending-owner-ruling / pending-evidence / designer-track / 已授权（附 package_id）/ delivered（附回执与实际归档状态）；排除项标 not_applicable_this_batch 并记先决条件。未归档不得为满足 delivered 注记伪造 archive 名。
5. **增量范围收口**：owner 审阅后可晋升 accepted canonical；三对关系 ontology-code / ontology-prd / prd-code 逐项说明受影响、未受影响、未检查或不适用，未受影响/不适用须附依据；ontology 无变化可引用有依据的 impact check/no-change。受影响对按 `product-governance/reconciliation-record.schema.json` 记录 pair、scope、revision、coverage、limitations；增量新交付主动声明 reconciliation_scope=increment-scoped，不冒充产品级全量对账。旧记录缺省字段仅表示未声明，不自动推断。accepted canonical、代码已实现、已归档、已发布分别记录，互不推断。此后的新需求走新增量 PRD。

## 实施回写

目标仓库返回 `implementation-return-package`，至少说明：

- change 是否创建、实施、验证、归档；
- 测试和 gate 证据路径；
- blocked、partial 或 false-positive 项；
- 发现的模型偏差和待裁决项；
- 需要 docs 侧更新的 trace、PRD、能力台账和 Semantic Release 候选。

docs 侧只根据 reviewed return package 更新权威文档，不做静默覆盖。
