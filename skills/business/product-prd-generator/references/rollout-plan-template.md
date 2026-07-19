# Rollout Plan Template（建议实施计划模板）

> **文档性质**：product-prd-generator 在 S10-A 战略级架构调整 + S5 高复杂度增量 PRD 场景下产出"建议实施切片"的标准模板
> **创建日期**：2026-07-19
> **状态**：可用（v1.0）
> **样例**：`/opt/code/docs/.omo/plans/langchat-v2-implementation-master-plan.md`（LangChat v2 实施总计划，架构级战略调整样例）

---

## 1. 何时使用本模板

### 1.1 触发场景

| 触发条件 | 走本模板 | 走其它产物 |
|---|---|---|
| S10-A 架构级战略调整（产品重新定位、核心架构换代） | ✅ 必用 | — |
| S10-A 大型功能扩展（新增模块、跨模块重塑） | ✅ 建议 | 或仅用 `suggested-openspec-changes.yaml` |
| S5 增量 PRD 涉及 ≥ 3 个 P0/P1 gap 且跨模块 | ✅ 建议 | 或仅用 `suggested-openspec-changes.yaml` |
| S5 增量 PRD 仅 1-2 个 P0 gap | ❌ 不用 | 走 `suggested-openspec-changes.yaml` 即可 |
| S7 单个产品开发 | ❌ 不用 | 走 `PRD实施交接包.md` + `consumption-prompt` |
| S10 工程治理（重构/CI/测试/部署） | ❌ 不用 | 走 `技术债治理 Plan` 即可 |

### 1.2 三种规模的 WP 数量建议

| 规模 | 典型 WP 数 | 典型 Gate 数 | 示例 |
|---|---|---|---|
| 架构级战略调整 | 8-12 | 4-6 | LangChat v2（10 WP / 6 Gate） |
| 大型功能扩展 | 4-8 | 2-4 | 新增会员 CRM 模块 |
| 高复杂度增量 | 1-4 | 1-2 | 跨模块安全合规加固 |

### 1.3 不适用场景（强制降级到清单）

- WP 数量 < 2 → 用 `suggested-openspec-changes.yaml` 清单即可，不要套本模板
- 没有显式 Gate 需求 → 不要造 Gate
- 改动只在单个模块 → 走 S5/S7 标准流程

---

## 2. 输入前提

使用本模板前必须已冻结：

| 输入 | 类型 | 路径示例 |
|---|---|---|
| 战略/架构文集 | stable | `lanlnk/out/prd/<产品>/output/review/v2-strategy/*.md` |
| 当前 PRD | stable | `lanlnk/out/prd/<产品>/output/产品PRD.md` |
| 当前代码基线 | 事实 | `/opt/code/<project>` |
| ADR 已冻结（可选） | stable | `lanlnk/out/prd/<产品>/output/review/ADR-*.md` |
| 待起草 ADR 编号清单 | 待定 | 由本计划在 WP 中定义 |

**前置硬规则**：如果战略/PRD 还没冻结，**先回到 S1/S2/S10-A 上游场景**，不要直接套本模板做实施计划。

---

## 3. 输出位置（关键：避免 docs 仓库漂移）

| 文件类型 | 默认输出路径 | 备注 |
|---|---|---|
| **建议实施计划本身** | `<目标代码仓库>/docs/handoff/<YYYYMMDD>/建议实施计划-<主题>.md` | living 文档，归项目侧 |
| 状态账本 | `<目标代码仓库>/.openspec/state/<主题>-state.md` | 项目侧执行时维护 |
| ADR 草案 | `<目标代码仓库>/docs/adr/ADR-<NNN>-*.md` | 项目侧 OpenSpec change 驱动 |
| Gate 证据 | `<目标代码仓库>/docs/handoff/<YYYYMMDD>/gate-G<NN>-<主题>.<ext>` | 项目侧执行时产出 |
| PRD/战略文集 | `lanlnk/out/prd/<产品>/output/`（docs 仓库） | stable，不漂移 |

**禁止**：把建议实施计划、状态账本、ADR 草案写到 docs 仓库的 `lanlnk/out/prd/` 下——会污染漂移检测、模糊所有权、违反"docs 出 stable，目标代码仓出 living"原则（参考 Kubernetes KEP / Rust RFC / Martin Fowler Strangler Fig 行业惯例）。

---

## 4. 模板骨架（建议实施计划主文档）

```markdown
# <主题> 建议实施计划

> status: draft | approved | in-progress | completed | superseded
> 创建日期：YYYY-MM-DD
> 上位约束：
> - 战略/架构文集：<绝对路径>
> - 当前 PRD：<绝对路径>
> - 当前代码基线：<绝对路径>

## TL;DR

<一句话目标>。<一句话当前事实>。<3-5 句话总体路线>。

## 总览

### 三种规模分流判断

| 维度 | 判断 |
|---|---|
| 规模 | 架构级 / 大型功能 / 高复杂度增量 |
| 触发原因 | <为什么走本模板而非清单> |
| WP 数量 | <N> |
| Gate 数量 | <M> |

### 依赖矩阵

| WP | 前置 | 后置 | 可并行 |
|---|---|---|---|
| WP-00 | — | WP-01, WP-02 | ADR 草案起草 |
| WP-01 | WP-00 | WP-02..N | — |
| ... | | | |

### Wave 划分

- Wave 1 = Gate G<NN>（foundation）：WP-00 + ADR 起草并行
- Wave 2 = Gate G<NN+1>：WP-02..N
- ...

## WP 清单

### WP-00: <标题>

- **Outcome**: <一句话目标>
- **OpenSpec change id**: `<project>-wp00-<slug>`
- **前置依赖**: <列出>
- **路径范围**:
  - current: <`/opt/code/<project>/...`>
  - target: <`/opt/code/<project>/...`>
- **必须做的**（≤5 条）:
  1. ...
- **禁止做的**（≤5 条）:
  1. ...
- **验收门**（agent-executable）:
  ```bash
  cd /opt/code/<project> && <具体命令>
  ```
- **失败场景**（负向测试）:
  - <场景> → <预期拒绝行为>
- **前向回滚**: <如何撤销或回退>
- **退出条件**: <解锁下一 WP 的具体条件>

### WP-01: ...

（同结构）

## Gate 清单

### Gate G<NN>: <名称>

- **触发点**: WP-XX 完成后
- **验证项**（agent-executable）:
  ```bash
  <命令 1>
  <命令 2>
  ```
- **通过条件**: <具体可检查条件>
- **失败处理**: <如何回到 WP>

## 跨仓库所有权表

| 产物 | 仓库 | 路径 | 谁维护 |
|---|---|---|---|
| 战略/架构文集 | docs | `lanlnk/out/prd/<产品>/output/review/` | 架构师 |
| PRD / 功能清单 / 差距分析 | docs | `lanlnk/out/prd/<产品>/output/` | 产品 |
| 建议实施计划（本文档） | 目标代码仓 | `docs/handoff/<YYYYMMDD>/` | 工程 |
| ADR 草案 | 目标代码仓 | `docs/adr/` | 工程 |
| OpenSpec changes | 目标代码仓 | `.openspec/changes/` | 工程 |
| 状态账本 | 目标代码仓 | `.openspec/state/` | 工程 |
| 代码 | 目标代码仓 | — | 工程 |
| 回写 PRD 状态 | docs | `lanlnk/out/prd/<产品>/output/` | 工程 → 产品 |

## START prompt

<复制到目标代码仓库的新会话使用。包含：读取哪些文件、执行规则、Wave 顺序、停止条件>

## RESUME prompt

<复制到目标代码仓库的续跑会话使用。包含：状态账本读取、当前 WP 判断、下一步动作>

## 完成定义（DoD）

1. 所有 WP 通过退出条件
2. 所有 Gate 通过验证
3. 状态账本更新到 completed
4. PRD 状态在 docs 仓库回写
5. ADR 草案在目标代码仓库归档
6. 战略文集的状态行更新（如"v1.x 已落地"）
```

---

## 5. WP 字段说明（每个字段必填，不允许"无"）

| 字段 | 含义 | 常见错误 |
|---|---|---|
| **Outcome** | 一句话目标，可验收 | 写成"实现 X 功能"——不可验收；应写"系统能在 Y 场景下做 Z" |
| **OpenSpec change id** | 该 WP 对应的 OpenSpec change 命名约定 | 不约定命名 → 项目侧各 change 命名混乱 |
| **前置依赖** | 哪些 WP 必须先完成 | 漏写隐性依赖（如代码 review、数据库迁移、训练数据） |
| **路径范围** | current/target 文件级路径 | 只写"前端"/"后端"——不可执行 |
| **必须做的** | ≤5 条具体行为 | 写成模糊原则（如"优化性能"） |
| **禁止做的** | ≤5 条边界 | 漏写"不动 X" → 项目侧可能误改 |
| **验收门** | agent-executable 命令 | 写成"通过测试"——不可执行；应写 `pytest tests/xxx.py -v` |
| **失败场景** | 负向测试（输入 → 拒绝） | 只写正向测试，遗漏负向 |
| **前向回滚** | 如何撤销（不是反向改历史，是前向物化新版本） | 写成"git revert"——不是回滚语义 |
| **退出条件** | 解锁下一 WP 的具体条件 | 写成"完成本 WP"——同义反复 |

---

## 6. Gate 字段说明

| 字段 | 含义 |
|---|---|
| **触发点** | 哪个 WP 完成后触发本 Gate |
| **验证项** | agent-executable 命令（必须可机器执行） |
| **通过条件** | 具体可检查条件（不是"看起来 OK"） |
| **失败处理** | 如何回到 WP（修复 / 重做 / 拆分） |

**Gate 设计原则**：
- Gate 是**质量门**，不是进度标记
- 每个 Gate 必须有失败处理路径
- Gate 数量宁少勿多（4-6 个为宜，>8 个说明 WP 拆分有问题）

---

## 7. START / RESUME prompt 模板

### 7.1 START prompt 模板

```text
你是 <产品> 实施执行者。工作目录是 /opt/code/<project>。

唯一实施计划：
<目标代码仓库>/docs/handoff/<YYYYMMDD>/建议实施计划-<主题>.md

执行状态账本：
<目标代码仓库>/.openspec/state/<主题>-state.md

先完整读取：
1. 实施计划主文档
2. 上位约束：<战略/PRD 绝对路径>
3. AGENTS.md / OpenSpec 既有规则

执行规则：
- 严格按 Wave 顺序执行：<列出>
- 不允许跳过 Gate
- 不允许在 Gate 失败时继续下一 Wave
- 每个 WP 完成后更新状态账本
- 不修改上位约束（战略/PRD/ADR-已冻结）
- 不允许 type suppression / `Any` / `type: ignore`
- 不提交 Git，除非用户明确要求
- 遇真实阻塞（计划外技术问题 / 3 次验收失败 / 用户变更范围）才停止并报告

现在执行 Wave 1：<具体 WP>
```

### 7.2 RESUME prompt 模板

```text
续跑 <产品> 实施。

第一步：读取状态账本：<目标代码仓库>/.openspec/state/<主题>-state.md
第二步：根据状态账本判断当前 WP 和 Wave
第三步：按实施计划继续执行

规则：状态账本是唯一状态源；不要从文件名顺序或 git log 推断状态。
如果状态账本和计划主文档冲突，计划主文档赢（顺序），状态账本赢（决策记录）；冲突要 surface 给用户。
```

---

## 8. 与现有产物的关系

| 产物 | 复杂度 | WP/Gate | 适用场景 | 关系 |
|---|---|---|---|---|
| `suggested-openspec-changes.yaml` | 低 | 无 | 1-3 个独立 change | 清单，最轻量 |
| `PRD实施交接包.md` + `consumption-prompt` | 中 | 无 | 单个 PRD 的标准 handoff | S5/S7 默认产物 |
| **`建议实施计划-*.md`（本模板）** | **高** | **有** | **战略级/高复杂度** | **本模板** |

**升级路径**：
- 增量 PRD 简单 → `suggested-openspec-changes.yaml` 清单
- 增量 PRD 中等复杂度 → `PRD实施交接包.md`
- 增量 PRD 高复杂度或战略级 → 本模板

**禁止**：所有场景都套本模板（会过度文档化简单任务）；只用本模板跳过 `suggested-openspec-changes.yaml`（清单是基础产物，不应跳过）。

---

## 9. 样例：LangChat v2 实施总计划

**路径**：`/opt/code/docs/.omo/plans/langchat-v2-implementation-master-plan.md`

**规模**：架构级战略调整，10 WP / 6 Gate（G19-G24）

**学习要点**：
- WP-00 基线 + strangler seam 与 ADR 起草并行
- Gate 数量适中（6 个），每个 Gate 都有失败处理
- WP-05 实现了 evaluation-only 部署，先于 Release Gate——避免 Candidate 在 Gate 前无法执行
- 跨仓库所有权表清晰：docs 出 stable，langchat 出 living
- START/RESUME prompt 自带状态账本机制（避免从文件名推断状态）

**反例（从该计划学到的教训）**：
- 手工起草被 Oracle 抓出 4 个阻断（evaluation-only 缺 canonical entry / Wave 1 数量错 / 所有权冲突 / Resume 状态错）→ 这些已固化到本模板字段必填规则
- 过渡产物写在 docs 仓库 `.omo/plans/` → 违反本模板第 3 节，应在目标代码仓库

---

## 10. 维护规则

修改本模板时：
1. 字段增减必须同步更新 §5（WP 字段说明）和 §6（Gate 字段说明）
2. 样例引用必须保持路径有效（如 LangChat v2 计划迁移后要更新引用）
3. 三种规模分流（§1.2）的 WP/Gate 数量建议根据实战经验调整
4. 行业最佳实践对照（Kubernetes KEP / Rust RFC / etc）更新时同步 §3 的"禁止"理由

**判断标准**：如果"下次的我"读到本模板不能直接套用产出一个可执行的 WP，就需要补字段说明。
