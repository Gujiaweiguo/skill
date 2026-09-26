# Incremental PRD Handoff

增量 PRD 是从 docs 规划层交给目标代码仓的变更包，不是代码实现说明书，也不是完整主 PRD 的重写。

## 必备章节

1. 文档元数据：`prd_id`、product、target_repo、本体版本、baseline PRD version。
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
- 代码/测试/spec 只能证明当前实现事实，不能自动改写产品目标。

## 状态分离

`evidence_state`：`observed | inferred | not_found | not_scanned | inaccessible | conflicting`

`implementation_status`：`existing | partial | missing | explicitly-not-do | unknown`

`not_scanned`、`inaccessible`、`not_found` 不得直接渲染为 `missing`。

## 推荐机器字段

```yaml
trace_id: PRD-CRE-2026-014
capability_id: CRE-LEASE-RENT-FREE-SEGMENTS
source_refs: [EV-023, REQ-014]
target_repo: /opt/code/lnkcre
target_spec_ids: [lease-contract-management]
suggested_change_ids: [cre-rent-free-period-model]
acceptance_ids: [AC-001, AC-002]
ui_refs: []
```

## 实施回写

目标仓库返回 `implementation-return-package`，至少说明：

- change 是否创建、实施、验证、归档；
- 测试和 gate 证据路径；
- blocked、partial 或 false-positive 项；
- 发现的模型偏差和待裁决项；
- 需要 docs 侧更新的 trace、PRD、能力台账和 Semantic Release 候选。

docs 侧只根据 reviewed return package 更新权威文档，不做静默覆盖。
