---
name: openspec-practice
description: OpenSpec 实战工作流 Skill。用于用短口令处理真实项目里的 OpenSpec 现场扫描、PRD 差异消费、PRD/增量 PRD/模块 PRD/UI 方案/治理 Plan 转 changes、多 active change 管理、多 OpenSpec scope、archive 漂移审计、PRD 回写，以及把 verified 经验通过复利工程持续回灌到手册或 skill。触发场景：“现场扫描 mi/lnkchat”、“消费 PRD 差异”、“消费 PRD 路径，目标 lnkchat”、“消费增量 PRD 路径，目标 lnkchat”、“消费模块 PRD 路径，目标 lnkchat”、“消费 UI 方案 路径，目标项目”、“消费治理 Plan 路径，目标项目”、“整理 active changes”、“检查多 scope”、“归档漂移审计”、“回写 PRD lnkchat”、“用 OpenSpec 实战 skill”。
---

# OpenSpec Practice

## 定位与上下文

本 skill 是 docs 仓与目标项目仓之间的跨仓治理编排层，不是产品注册表、PRD 生成器或代码执行器。
产品事实由公共 `shared/product_context` resolver 读取当前公司的 `config/company.yaml`、
`30-products/<product>/INDEX.md`、`ontology/README.md`、`prd/README.md` 和台账中的
`code_root` 提供。resolver 只返回事实与显式状态；本 skill 负责短口令、L0-L3、扫描、分类、
交接、门禁和回写编排。

每次处理产品上下文时必须保留并输出：

- 公司：`company_id`、`company_base`
- 产品：`product_id`、`product_name`
- 三层 authority：ontology、prd、code 的 path/status/revision
- 解析状态：company、product、ontology、prd、code
- 目标项目仓：path、revision、OpenSpec scopes

`unresolved`、`not-found`、`planned`、`prd-only`、`inaccessible`、`unsupported`、
`partial`、`not-applicable` 都是事实状态，不得被改写成“已解决”或静默降级。

**lnkcrm scope 基线（O5-Q4，2026-10-04 owner include 裁决）**：lnkcrm 的 OpenSpec spec
scope 集合（`/opt/code/lnkcrm/openspec/specs/`，实测非空、含 member-*/coupon-*/points-*/
merchant-*/platform-*/tenancy 等 scope 族）已纳入产品实现基线——回写链路
（`references/prd-writeback.md`）把它作为 lnkcrm 实现基线层对照输入；基线锚定 scope
集合本身、不钉数量，对照时以实测 `ls` 为准。scope 基线已纳入；实现级评估 O5-Q5 已解锁
（2026-10-04，解锁集 = 最小验证集三 skill——requirement-evaluator / strategy-brief-generator / product-prd-generator）。

## 目标

把 OpenSpec 实战里的长提示词压缩成短口令：先识别任务意图和复杂度档位（L0-L3），再读取对应参考流程，必要时运行轻量扫描脚本，最后输出可执行的下一步建议或按用户确认落盘。

分层原则：完整治理规范在手册 `/opt/code/docs/opencode/10-实战手册/README.md`；本 SKILL.md 只保留最小硬门禁和短口令路由；详细流程按任务类型放 `references/`。不得把 L3 交付协议强加给 L0 现场扫描和 L1 单个 change。

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
| `现场扫描 <项目路径或产品 ID>` | 项目路径，或 resolver 可解析的产品 ID | `references/site-scan.md` |
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

跨仓交接字段与项目仓收尾报告模板由 L2/L3 流程共用：`references/cross-repo-handoff.md`。

项目路径解析：

- 绝对路径可以直接扫描，但仍要尝试通过 resolver 建立公司、产品和三层 authority；无法映射时标记 unresolved。
- 产品 ID 必须经 resolver 按当前公司的 `company.yaml` 解析；不得按产品 ID 猜 `/opt/code/<id>`，不得维护 skill 内第二套产品列表。
- `docs` 与 `skill` 是仓级治理目标，不冒充产品上下文。
- `mi` / `MI-CRE` 只可作为 resolver 或历史文档中的明确 alias；实际目标路径必须来自当前公司产品台账的 `code_root`。

resolver 的标准导入和字段契约见 `shared/product_context/README.md`。本 skill 的显式 JSON 边界为：

```bash
uv run python scripts/resolve_context.py <product-id> [--company-id <id> | --company-base <path>]
uv run python scripts/resolve_context.py --all [--company-id <id> | --company-base <path>]
```

`--all` 按 company.yaml 登记顺序逐项解析全部产品：每个产品要么是 resolved 的完整
context，要么是显式 `unresolved` 错误条目（不静默跳过）；任一产品失败时 exit 1。
产品清单本身只来自 company.yaml，脚本与 SKILL.md 均不维护第二套产品列表。

脚本通过明确的仓库根路径导入公共包，不依赖业务 skill venv 或隐式 `PYTHONPATH` 副作用。

## 复杂度分档（L0-L3）

先判档再读 reference：档位决定治理负载，只加载当前任务需要的参考流程。

| 档位 | 适用 | 不要求的重负载 | 详细规则 |
|---|---|---|---|
| **L0 现场查询** | `现场扫描`、`检查多 scope`、只读查看 specs / active changes / archive / 验证入口 / 风险 | 五分类门禁、完整交付三元组、implementation-return、PRD 回写、canonical 晋升 | `references/site-scan.md`、`references/multi-scope.md` |
| **L1 单个 PRD/gap 或单个 change** | `消费 PRD 差异`、`消费 PRD / 增量 PRD / 模块 PRD / UI 方案 / 治理 Plan`（单个） | 完整交付三元组、回写协议、canonical 晋升 | `references/prd-diff-consume.md`、`references/artifact-to-changes.md` |
| **L2 多 change 或跨 scope** | 多个 PRD gap、多个 active changes、根 scope 与子 scope 并存、数据库/权限/路由/共享组件依赖、多 change 波次或欠账清理 | 完整交付三元组（除非同时发生交付回写或 canonical 晋升） | `references/active-change-triage.md`、`references/multi-scope.md`、`references/cross-repo-handoff.md` |
| **L3 交付回写、canonical 晋升或正式对账** | `回写 PRD`、change 归档后回写 docs、ontology/PRD canonical 晋升、多 change 波次正式收尾、可审计交付基线 | — | `references/prd-writeback.md`、`references/cross-repo-handoff.md` |

- L0 只读：默认禁止创建 change、修改代码、修改 spec、修改 archive。
- L1 起启用五分类（docs-only / verification-only / already-covered / low-confidence-excluded / confirmed-implementation，定义与输出模板见 `references/artifact-to-changes.md`）；默认只输出 Plan 或拆分方案。
- L2 在 L1 之上补：全部相关 scope 清单、每个 scope 的验证命令、change 依赖/冲突/执行顺序、独占边界（数据库、权限、路由、共享组件）、一次只推进一个 apply；可要求 docs commit SHA 与目标仓 revision/commit。
- L3 才强制完整交付三元组（feature SHA / archive SHA / origin 远端指针）、implementation-return proposal 和 canonical 晋升后 pairwise 对账。

## 快速流程

1. 解析用户短口令，确定 intent、项目路径和复杂度档位（L0-L3）。
2. 先读目标项目 `AGENTS.md`；如当前在 `/opt/code/docs`，同时遵守其会话启动检查。
3. 跨仓库消费 docs 产物时，必须保留并复述输入文件的绝对路径；不要只在目标项目仓库内搜索 PRD。
4. 在目标项目仓创建任何 change 前，必须重新读取该仓自己的 `AGENTS.md`、`openspec/specs/`、当前 active changes、代码和测试基线；docs 侧候选不能直接视为实施授权。
5. 按 intent 读取一个对应 `references/*.md`，不要把所有参考流程一次性加载。
6. 如果是扫描类任务，可运行：

```bash
cd /opt/code/skill/skills/meta/openspec-practice
uv run python scripts/scan_openspec.py <PROJECT_ROOT>
```

7. 输出“发现 → 判断 → 建议下一步”。除非用户明确要求，不创建 change、不改代码、不归档。

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

## 质量门禁（最小硬门禁）

- 默认先分类或出 Plan，不直接创建 change；用户明确要求后才落盘。
- 跨仓消费必须保留 docs 产物绝对路径。
- docs 侧候选不能直接视为实施授权：`confirmed-implementation` 只表示允许进入目标项目仓二次复核，不等于自动创建 change，也不等于实施授权。
- 只有目标项目仓复核后才能创建实现 change；复核可以把候选重新判为 already-covered 或 verification-only。
- 多 active changes 时，一次只推进一个 apply。
- 多 scope 项目必须列出每个 scope 的验证命令。
- 不修改历史 archive，不补造历史 change / 评审 / 验收。
- 不直接修改产品代码、canonical ontology 或 canonical PRD；skill 仓库不拥有任何产品的 canonical 层，不写产品代码仓库，目标仓库始终拥有自己的 OpenSpec changes 与验证。
- 不把 PRD 过时或 code_map / term-aliases 漏判转成代码 change；不因目标项目仓库内找不到 PRD 就判定 PRD 不存在，先核对用户给出的 docs 绝对路径。
- 完整交付三元组与回写协议仅 L3 启用。PRD 消费与回写遵循 product-prd-generator 的共享 product-governance 契约（`skills/business/product-prd-generator/references/product-governance/`）；proposal 起始状态、destination owner 审核、review-gated ontology 提案、晋升后 pairwise 对账等细则以 `references/prd-writeback.md` 为本 skill 内唯一权威描述，入口不复制。
- 新流程优先要求 `verification-report.md`；历史项目缺报告时按 proposal/tasks/specs/code/tests 做证据审计。
- Python 一律用 `uv run`，不使用 `pip`。

## 维护

本 skill 的持续改进走 `references/maintenance.md`。用户说“复利工程”时，优先使用 `compound-learning` 的三通道规则：项目内复利、公共 OpenCode 手册复利、skill 自身复利。
