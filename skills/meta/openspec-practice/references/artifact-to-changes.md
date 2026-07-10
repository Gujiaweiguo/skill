# PRD / 方案产物转 changes

用于短口令：

- `消费增量 PRD <路径>，目标 <项目>`
- `消费 PRD <路径>，目标 <项目>`
- `消费模块 PRD <路径>，目标 <项目>`
- `消费 UI 方案 <路径>，目标 <项目>`
- `消费治理 Plan <路径>，目标 <项目>`

## 目标

把 docs 仓库里的已确认产物转成目标项目 OpenSpec change 拆分。默认先出拆分方案；用户明确要求“创建 changes”时，再落盘到目标项目 `openspec/changes/`。

## 输入

- 产物绝对路径：PRD / 交接包、增量 PRD、模块 PRD、UI backlog / 优化方案、治理 Plan / 审计报告。
- 目标项目：项目名或绝对路径。默认解析 `mi`、`langchat`、`docs`、`skill`。
- 可选：指定优先级、时间范围、只处理某一章节或某几个需求编号。

## 步骤

1. 校验产物路径存在；若用户给相对路径，先按当前工作目录解析成绝对路径并复述。
2. 读取目标项目 `AGENTS.md`、`openspec/specs/`、active changes、近期 archive。
3. 抽取产物中的候选需求，按以下类型分类：
   - 应创建 change
   - 已被现有 spec / code / active change 覆盖
   - PRD 或方案过时
   - 不适用于目标项目
   - 需要用户确认
4. 对“应创建 change”给出拆分：
   - `<CHANGE_ID>`
   - 影响 spec
   - 代码范围
   - 验收标准
   - 验证命令
   - 依赖顺序
5. 用户确认后再创建 proposal / tasks / spec delta；不要直接 apply。

## 拆分原则

- 每个 change 只做一个可验收目标。
- 已覆盖项不重复建 change。
- 部分具备的能力只补差异。
- UI changes 按页面 / 流程 / 组件边界拆，并写截图或视觉验收标准。
- 技术债 changes 不混入业务 PRD changes。

## 输出

```text
消费产物：
- <绝对路径>

目标项目：
- <路径>

过滤结论：
- 应创建 change：
- 已覆盖：
- 过时 / 不适用：
- 需要确认：

建议 changes：
| CHANGE_ID | 来源章节 | 范围 | 验收 | 验证 |

下一步：
- 等用户确认后创建 changes / 或先补充确认问题。
```
