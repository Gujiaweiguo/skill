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
