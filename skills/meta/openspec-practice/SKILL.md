---
name: openspec-practice
description: OpenSpec 实战工作流 Skill。用于用短口令处理真实项目里的 OpenSpec 现场扫描、PRD 差异消费、PRD/增量 PRD/模块 PRD/UI 方案/治理 Plan 转 changes、多 active change 管理、多 OpenSpec scope、archive 漂移审计、PRD 回写，以及把 verified 经验通过复利工程持续回灌到手册或 skill。触发场景：“现场扫描 mi/langchat”、“消费 PRD 差异”、“消费 PRD 路径，目标 langchat”、“消费增量 PRD 路径，目标 langchat”、“消费模块 PRD 路径，目标 mi”、“消费 UI 方案 路径，目标项目”、“消费治理 Plan 路径，目标项目”、“整理 active changes”、“检查多 scope”、“归档漂移审计”、“回写 PRD”、“用 OpenSpec 实战 skill”。
---

# OpenSpec Practice

## 目标

把 OpenSpec 实战里的长提示词压缩成短口令：先识别任务意图，再读取对应参考流程，必要时运行轻量扫描脚本，最后输出可执行的下一步建议或按用户确认落盘。

兼容性：prompt-first skill，可选 `uv run` Python 辅助脚本；Python 脚本只用标准库。

## 适用

- 接手已有 OpenSpec 项目，扫描 specs / active changes / archive / 验证入口。
- 消费 PRD 差异报告，先出 Implementation Plan，不直接创建 change。
- 消费 docs 仓库里的 PRD、增量 PRD、模块 PRD、UI 优化方案或治理 Plan，转成目标项目 OpenSpec changes。
- 整理多个 active changes，判断继续、拆分、补验证、废弃重开。
- 识别根目录和子目录多个 OpenSpec scope，并给出验证顺序。
- 审计 archived change 与当前 code/spec/test 是否漂移。
- 目标项目 change 归档后，回写 PRD 侧状态。
- 把已验证的新经验通过 `compound-learning` 复利回流。

## 不适用

- 直接生成 PRD：用 `product-prd-generator`。
- 直接执行单个 OpenSpec change：用已有 `/opsx-*` 命令或 `openspec-*` skills。
- 修业务代码但没有 OpenSpec/PRD/归档语境：按项目 `AGENTS.md` 和普通编码流程处理。
- 为了统一格式补造历史 change 或重写不可变 archive。

## 输入

用户可以只给短口令和路径：

| 短口令 | 最少输入 | 参考流程 |
|---|---|---|
| `现场扫描 <项目路径或项目名>` | 项目路径，或 `mi` / `langchat` | `references/site-scan.md` |
| `消费 PRD 差异 <报告路径>` | PRD diff / gap 报告路径，目标项目路径 | `references/prd-diff-consume.md` |
| `消费 PRD <路径>，目标 <项目>` | PRD / 交接包绝对路径，目标项目名或路径 | `references/artifact-to-changes.md` |
| `消费增量 PRD <路径>，目标 <项目>` | 增量 PRD 绝对路径，目标项目名或路径 | `references/artifact-to-changes.md` |
| `消费模块 PRD <路径>，目标 <项目>` | 模块 PRD 绝对路径，目标项目名或路径 | `references/artifact-to-changes.md` |
| `消费 UI 方案 <路径>，目标 <项目>` | UI 方案 / backlog 绝对路径，目标项目名或路径 | `references/artifact-to-changes.md` |
| `消费治理 Plan <路径>，目标 <项目>` | 治理 Plan / 审计报告绝对路径，目标项目名或路径 | `references/artifact-to-changes.md` |
| `整理 active changes` | 项目路径 | `references/active-change-triage.md` |
| `检查多 scope` | 仓库路径 | `references/multi-scope.md` |
| `归档漂移审计 <change>` | archived change 路径或 change id | `references/archive-drift.md` |
| `回写 PRD` / `回写 PRD <项目名/时间范围/change...>` | 默认从项目上下文自动发现最近 archived changes；项目名、时间范围、change id/path 可作精确筛选 | `references/prd-writeback.md` |
| `复利工程` / `沉淀这次经验` | 本次已验证经验 | `references/maintenance.md` |

项目名默认解析：

- `mi` → `/opt/code/mi`
- `langchat` → `/opt/code/langchat`
- `docs` → `/opt/code/docs`
- `skill` → `/opt/code/skill`

## 快速流程

1. 解析用户短口令，确定 intent 和项目路径。
2. 先读目标项目 `AGENTS.md`；如当前在 `/opt/code/docs`，同时遵守其会话启动检查。
3. 跨仓库消费 docs 产物时，必须保留并复述输入文件的绝对路径；不要只在目标项目仓库内搜索 PRD。
4. 按 intent 读取一个对应 `references/*.md`，不要把所有参考流程一次性加载。
5. 如果是扫描类任务，可运行：

```bash
cd /opt/code/skill/skills/meta/openspec-practice
uv run python scripts/scan_openspec.py <PROJECT_ROOT>
```

6. 输出“发现 → 判断 → 建议下一步”。除非用户明确要求，不创建 change、不改代码、不归档。

## 输出格式

默认输出中文，保持短而可执行：

```text
结论：
- <项目类型/现场状态>

关键发现：
- <spec/active/archive/scope/验证入口>

建议下一步：
- <继续哪个 change / 先出 Plan / 做漂移审计 / 回写 PRD>

需要确认：
- <只列真正阻塞的问题>
```

如果用户要求落盘，先给“目录/文件清单/修改范围”，得到确认后再写。

## 质量门禁

- 不把历史 archive 当成可随意重写的当前事实。
- 不把 PRD 过时或 code_map 漏判转成代码 change。
- 不因目标项目仓库内找不到 PRD 就判定 PRD 不存在；先核对用户给出的 docs 绝对路径。
- 多 active changes 时，一次只推进一个 apply。
- 多 scope 项目必须列出每个 scope 的验证命令。
- 新流程优先要求 `verification-report.md`；历史项目缺报告时按 proposal/tasks/specs/code/tests 做证据审计。
- Python 一律用 `uv run`，不使用 `pip`。

## 维护

本 skill 的持续改进走 `references/maintenance.md`。用户说“复利工程”时，优先使用 `compound-learning` 的三通道规则：项目内复利、公共 OpenCode 手册复利、skill 自身复利。
