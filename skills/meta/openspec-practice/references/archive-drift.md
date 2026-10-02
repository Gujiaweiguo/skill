# Archive 漂移审计

用于短口令：`归档漂移审计 <change>`。

## 目标

判断 archived change 的记录与当前 code/spec/test 是否一致，避免被陈旧 checklist 或缺失验证报告误导。

## 原则

- 不直接改历史 archive。
- 不为历史补造新的 change。
- 先证据审计，再建议动作。
- 当前代码是实现事实，canonical specs 是意图事实，archive 是历史证据。

## 漂移类型

| 类型 | 判断 | 建议 |
|---|---|---|
| tasks 未勾选但代码和测试已实现 | checklist 陈旧 | 做 evidence-first reconciliation |
| tasks 已勾选但代码缺失 | 真实缺口 | 创建新补实现 change |
| archive 缺 verification-report | 历史证据不完整 | 用 proposal/tasks/specs/code/tests 审计，不补造 |
| spec 已合并但代码已演进 | 当前行为变化 | 如需固化，创建补 spec change |
| PRD/code_map 判错 | 上游映射问题 | 回 PRD 侧修 code_map / ontology |

## 步骤

1. 读取 archived change 的 `proposal.md`、`tasks.md`、`specs/`、`design.md`、`verification-report.md`（如存在）。
2. 读取相关 canonical specs。
3. 查找代码、测试、文档证据。
4. 输出漂移类型和证据路径。
5. 建议：无需处理 / 更新 PRD 判断 / 创建新 change / 做 archive reconciliation。

## 执行回执

每次审计必须记录可复现证据；正式结构化记录沿用共享治理契约 `reconciliation-record.schema.json` 的字段语义，此处不复制 schema：

- `target_repo` 与 revision / commit
- 扫描范围（比对了哪些模块 / 路径；未扫描区域如实记 not-scanned，不推断为缺失）
- 实际执行的测试 / 验证命令及结果
- `coverage.status`（complete / partial / not-scanned / inaccessible）
- 证实误判的历史 finding 是否按 `false-positive-corrected` 修正留痕（不静默删除）

## 输出

```text
Archive 漂移审计：
- change:
- 结论:

证据：
- spec:
- code:
- test:
- docs:

执行回执：
- target_repo / revision:
- 扫描范围:
- 命令与结果:
- coverage:

建议动作：
- ...

不应改写的历史：
- ...
```
