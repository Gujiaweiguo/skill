# Active Change 整理

用于短口令：`整理 active changes`。

## 目标

在项目已有多个 `openspec/changes/<CHANGE_ID>/` 时，判断哪些继续、哪些拆分、哪些补验证、哪些废弃重开，并给出下一步执行顺序。

## 步骤

1. 运行：

```bash
openspec list --json
openspec validate --changes --strict --json --no-interactive
```

2. 读取每个 active change 的 `proposal.md`、`tasks.md`、`specs/`，必要时读 `design.md` 和 `verification-report.md`。
3. 判断状态：
   - 未开始
   - 部分实现
   - 待验证
   - 可归档
   - 应拆分
   - 应废弃重开
4. 标出冲突点：数据库迁移、权限、路由、共享组件、测试门禁。
5. 推荐一次只推进一个 change。

## 状态决策表

按证据组合判断，证据冲突时按表格从上到下取第一个命中行。证据字段来自 `scan_openspec.py` 的 `active_evidence`（`tasks_status` / `verification_status` + `verification_reasons` / `artifact_status`），validate 结果来自 `openspec validate` CLI，不由扫描器推断：

| 证据组合 | 状态 |
|---|---|
| `openspec validate` 失败 | 阻塞：先修 artifacts，不进入实施判断 |
| tasks 未开始且无代码证据 | 未开始 |
| tasks 部分勾选，或代码已部分落地 | 部分实现 |
| tasks 全勾选但 verification report 非 present（missing / unreadable / empty / placeholder） | 待验证 |
| tasks 全勾选且 verification report 为 present、验证通过 | 可归档 |
| 需求与当前 PRD / canonical spec 已冲突 | 应废弃重开（不直接删，保留提案记录） |
| 与其他 active change 改同一边界（数据库迁移 / 权限 / 路由 / 共享组件） | 应拆分或排序，不并行 apply |

## 并行判断

| 类型 | 建议 |
|---|---|
| 纯文档、只读报表、小前端页面 | 可并行准备，但 apply 仍逐个闭环 |
| 数据库迁移、权限模型、编号引擎 | 独占执行 slot |
| 共享路由、共享组件、全局配置 | 先排序，避免并行改同一层 |
| 长期未动且需求已变 | 不直接删，先建议废弃重开 |

## 输出

```text
Active changes 现场：
| CHANGE_ID | 状态 | 风险 | 建议动作 |

依赖与冲突：
- ...

推荐执行顺序：
1. <CHANGE_ID>：<原因>

本轮建议处理：
- <CHANGE_ID>
```
