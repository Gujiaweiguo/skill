# PRD 回写

用于短口令：`回写 PRD`。可选精确筛选：`回写 PRD <项目名/时间范围/change...>`。

## 目标

目标项目 change 归档后，用 archived change 的证据刷新 PRD 侧状态、覆盖矩阵和下一轮 suggested changes。

## 输入

- 默认只需短口令 `回写 PRD`，由 agent 从当前目录、最近对话和项目名默认解析推断目标项目。
- 可选：项目名或项目路径，例如 `mi` / `langchat` / `/opt/code/mi`。
- 可选：时间范围，例如 `今天` / `最近一次` / `本周归档`。
- 可选：一个或多个 archived change id/path，用于精确指定回写对象。
- 可选：PRD 输出目录，例如 `$LANLNK_BASE/out/prd/商管系统/output/`。
- 可选：`verification-report.md`、实现摘要、暂缓/合并/误判结论。

## 步骤

1. 读取目标项目 `AGENTS.md`。
2. 自动发现候选 archived changes：
   - 如果用户给了 change id/path，优先使用指定对象。
   - 如果用户给了项目名、项目路径或时间范围，在对应 OpenSpec archive 中筛选。
   - 如果用户只说 `回写 PRD`，根据当前目录、最近对话、项目名默认解析和最近归档时间找候选。
   - 候选过多或无法判断目标 PRD 时，先输出候选列表和需要用户确认的最小问题。
3. 读取候选 archived change 的 proposal/tasks/specs/design/verification-report。
4. 反查 PRD 侧资料：
   - PRD 输出目录、`review/` 诊断报告、`suggested-openspec-changes.yaml`、`mi-consumption-prompt.md`。
   - change proposal / spec / verification 中提到的 PRD gap、feature、capability、module 名称。
5. 读取必要代码落点和测试证据。
6. 判断 PRD gap 状态：
   - 已实现
   - 已合并到其他能力
   - 暂缓
   - code_map 漏判
   - 仍未处理
7. 更新前先列出候选 changes、目标 PRD、将修改的 PRD 文件和范围，等用户确认。
8. 确认后再更新 PRD 资料库，不改目标项目代码，不创建目标项目 change。

## 输出文件建议

- `output/review/实施回写-<YYYYMMDD>.md`
- 必要时更新 `功能清单.md`、覆盖度矩阵、`suggested-openspec-changes.yaml`、`mi-consumption-prompt.md`。

## 完成标准

- 状态变化都有 archived change / spec / code / test 证据。
- 下一轮 suggested changes 不再包含已完成或误判项。
- code_map / ontology / term-aliases 问题进入单独修复清单。
