# PRD 差异消费

用于短口令：`消费 PRD 差异 <报告路径>`。

## 目标

把 PRD 差异报告转成目标项目可执行的 Implementation Plan。默认只出 Plan，不创建 change，不改代码。

## 输入

- PRD 差异报告或 gap 报告。
- 目标项目路径，默认 `mi` 为 `/opt/code/mi`。
- 可选：`suggested-openspec-changes.yaml`、PRD 实施交接包。

## 步骤

1. 读取目标项目 `AGENTS.md`、`openspec/specs/`、active changes、近期 archive。
2. 抽取 PRD 报告里的候选缺口。
3. 对每个候选缺口分类：
   - 真代码缺口
   - PRD 过时
   - code_map / ontology / term-aliases 漏判
   - 已被其他能力覆盖
   - 需要用户确认
4. 对真缺口输出 Implementation Plan v1：
   - `<CHANGE_ID>`
   - 依赖顺序
   - 验收标准
   - 回归范围
   - 是否需要先做 Prometheus plan
5. 等用户确认后，才进入 `/opsx-new` 或 `/opsx-ff`。

## 拆分原则

- 每个 change 只处理一个可验收缺口。
- 数据库迁移、权限模型、编号引擎、报表引擎类高风险项单独拆。
- PRD 过时和 code_map 漏判不创建功能 change。
- 被确认 blocked 的项只记录条件，不创建假进行中的 change。

## 输出

```text
Implementation Plan v1

过滤结论：
- 真缺口：
- PRD 过时：
- code_map 漏判：
- 需要确认：

推荐 change：
| CHANGE_ID | 优先级 | 依赖 | 范围 | 验收 |

执行顺序：
1. ...

需要确认：
- ...
```
