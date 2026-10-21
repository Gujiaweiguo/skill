# implementation-return 存量形态盘点（2026-10-21）

## 范围与方法

- 扫描 `$COMPANY_BASE/lanlnk/30-products/*/reconciliation/implementation-return-*.json`。
- 共发现 27 个 JSON 回执，全部成功解析。
- 只统计实际字段形态，不把缺失字段自动判为非法；历史回执与新契约的兼容边界另行裁决。
- 该盘点是 schema 收口前的事实基线，不是回执验收报告。

## 顶层形态

| 字段 | 观测结果 |
|---|---|
| `review_status` | `absorbed` 9、`pending` 4、`reviewed` 3；缺失 8；其他值 3（`closed-registered-and-pushed`、`docs-evidence-review-passed-project-ledger-accepted-local-unpushed`、`approved-and-archived` 各 1） |
| `trace_ids` | 数组 16、对象 3、缺失 8 |
| `proposed_updates` | 结构体列表 9、字符串列表 8、缺失 6、空列表 4 |
| `changes` | 结构体列表为空 6；非空项的标识键使用 `change_id`、`change`、`id` 三种命名 |

## `changes[]` 内部形态

非空 `changes[]` 中观察到：

- 标识键：`change_id` 为主，但 `change` 与 `id` 同时存在历史变体。
- 提交键：`feature_commits` 与 `feature_commit` 并存；部分回执另有 `supporting_commits`。
- 验证键：`verification_sha`、`verification` 两种形态并存；部分 change 没有提交/验证键。
- 状态键并不稳定：部分条目有 `status`，部分只有 change 标识与证据字段。

## 异常与兼容清单

`review_status` 缺失或使用非当前契约词表的回执：

- `lnkcrm`: `crosscut`、`nav-followups`、`verify-hygiene`、`admin-nav-hierarchy`、`e2e-smoke-hardening`、`w2a`、`w3b`（缺失）；`s6-d1b` 使用 `closed-registered-and-pushed`；`w3a-w1s` 使用 `docs-evidence-review-passed-project-ledger-accepted-local-unpushed`。
- `lnkreport`: `report-structure-authoring-parity-20261018`（缺失）；`report-grid-paste-format-virgin-target-persistence-20261019` 使用 `approved-and-archived`。

空 `changes[]` 或缺少 `proposed_updates` 不应直接视为损坏：部分旧回执采用 package/return 以外的状态板或交接文件完成收尾，需逐项确认后再迁移。

## 建议收口顺序

1. 先定义兼容读取层：同时读取 `id/change/change_id`、`feature_commit/feature_commits`，保留 `supporting_commits`，并把字符串 `proposed_updates` 规范化为 `{target, update, disposition}` 的候选结构。
2. 再裁决生命周期词表：当前 implementation-package 契约使用 `pending → reviewed → absorbed`；存量野值先建立映射表，不能用 schema 收紧直接删除历史语义。
3. 补齐 `trace_ids` 数组/对象的归一化规则，并明确缺失值的历史兼容策略。
4. 最后更新 `implementation-return.schema.json` 与校验测试；迁移完成前，schema 校验应支持 legacy 形态并输出 drift warning，而不是直接阻断历史回执。

## 责任边界

- schema 与校验器 owner：`product-prd-generator`。
- 实施包生命周期与 docs 吸收流程 owner：`openspec-practice`。
- 本报告只提供事实盘点和迁移顺序，不替两个 owner 预先裁决字段或状态。
