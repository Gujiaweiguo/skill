# PRD / 方案产物转 changes

用于短口令：

- `消费增量 PRD <路径>，目标 <项目>`
- `消费 PRD <路径>，目标 <项目>`
- `消费模块 PRD <路径>，目标 <项目>`
- `消费 UI 方案 <路径>，目标 <项目>`
- `消费治理 Plan <路径>，目标 <项目>`

## 档位

默认 **L1**（单个 PRD/gap 或单个 change）。命中以下任一条件升 **L2**：产物展开为多个 gap、涉及多个目标 scope、change 之间存在数据库/权限/路由/共享组件依赖、需要多 change 波次或欠账清理——届时按 `cross-repo-handoff.md` 补交接字段与依赖排序。发生交付回写或 canonical 晋升时按 **L3** 走 `prd-writeback.md`。

## 目标

把 docs 仓库里的已确认产物转成目标项目 OpenSpec change 拆分。默认先出拆分方案；用户明确要求“创建 changes”时，再落盘到目标项目 `openspec/changes/`。

## 共享治理契约

PRD 类产物的层引用、对账与回流语义以 product-prd-generator 拥有的共享契约为准，本 skill 只引用不复制：

- 契约目录：`/opt/code/skill/skills/business/product-prd-generator/references/product-governance/`（owner：product-prd-generator）。
- `layer-reference.schema.json`：消费前先解析产物指向的层 authority（ontology/prd/code）及版本；解析不到时显式记 `unresolved` / `unsupported` / `inaccessible` 及原因，不用其他产品的 authority 顶替，也不因未扫描而推断缺失。
- `reconciliation-record.schema.json`：已有 pairwise 对账记录（ontology-prd / prd-code / ontology-code）可作为「已覆盖 / 过时 / 漏判」分类的证据输入。
- `implementation-return.schema.json`：change 归档后的实施证据回流格式，由 `prd-writeback.md` 侧消费；本流程不替目标仓库执行回流。

契约是 skill 间接口，不是产品数据存储，也不是任何产品 canonical ontology/PRD/code 的权威；适用产品范围以该目录 README 为准（7 个软件产品，lnkwebsite 站点运营不在此契约内）。涉及回写、审批与晋升后对账的操作细则，以本 skill `prd-writeback.md` 为唯一权威描述；本文件只保留消费侧动作。

## 输入

- 产物绝对路径：PRD / 交接包、增量 PRD、模块 PRD、UI backlog / 优化方案、治理 Plan / 审计报告。
- 产物标识（若已有必须保留，不得丢弃）：稳定 ID、requirement / feature IDs、docs commit SHA。
- 目标项目：产品 ID 或绝对路径。产品 ID 通过公共 resolver 解析；绝对路径可直接扫描，不能据此猜测产品。
- 可选：指定优先级、时间范围、只处理某一章节或某几个需求编号。

## 五分类门禁

所有候选必须先分类，未分类的候选不得进入「建议 changes」。分类是交接局部标签（handoff-local），不替代 `document_status` / `delivery_status` / `evidence_status`：

| 分类 | 含义 | 后续动作 |
|---|---|---|
| `docs-only` | 需要修正 PRD、架构或领域模型，项目代码无需变化（含 PRD/方案过时、不适用于目标项目） | 创建 docs Change，不输出项目实现路径 |
| `verification-only` | 代码/spec 已存在，但缺当前测试或运行证据 | 项目仓补验证并回写证据，不创建实现 change |
| `already-covered` | 工具或术语误判（code_map / ontology / term-aliases 漏判），项目已有覆盖 | 记录覆盖的 spec/code ID，不创建 change |
| `low-confidence-excluded` | 只有弱证据或术语未匹配，暂不能确认（含「需要用户确认」项） | 保留待复核，不进入项目 backlog |
| `confirmed-implementation` | 有证据的真实运行时缺口，且上游范围已 accepted | 允许进入目标项目仓二次复核；复核通过才创建实现 change |

分类规则：

- 只有 `confirmed-implementation` 才允许进入目标项目仓二次复核。
- `confirmed-implementation` 不等于自动创建 change，也不等于实施授权。
- 目标项目仓复核可以把候选重新判为 `already-covered` 或 `verification-only`，并回写 docs。
- 弱证据项归入 `low-confidence-excluded`，不得凭推测升级为 `confirmed-implementation`。

## ontology 边界

- 不在消费流程中直接修改 ontology 权威文件。
- 消费中发现的 ontology 影响，只能按 `ontology-change-set.schema.json` 记为 draft/delta 提案（review-gated）；canonical 晋升需 approval，走 `prd-writeback.md` 的 L3 流程。

## 步骤

1. 校验产物路径存在；若用户给相对路径，先按当前工作目录解析成绝对路径并复述。
2. 读取目标项目 `AGENTS.md`、`openspec/specs/`、active changes、近期 archive。
3. 按 `layer-reference.schema.json` 解析产物指向的层 authority 与版本；解析不到就显式记录 unresolved 状态和原因，继续分类时如实标注证据缺口。
4. 抽取产物中的候选需求，逐项标五分类（见上表）。
5. 对 `confirmed-implementation` 候选给出拆分：`<CHANGE_ID>`、来源、分类、影响 spec、代码范围、验收标准、验证命令、依赖顺序。
6. 用户明确要求“创建 changes”、且目标项目仓已完成二次复核后，才创建 proposal / tasks / spec delta；不要直接 apply。

## 拆分原则

- 治理顺序与 origin flow（未来增量先做 ontology impact check、代码领先只形成带 revision 的 reconciliation 候选、实现事实不自动升级为产品意图、OPC 为决策审核 owner）见 `prd-writeback.md`「回写规则」，此处不复制。
- 每个 change 只做一个可验收目标。
- 已覆盖项（`already-covered`）不重复建 change。
- 部分具备的能力只补差异。
- UI changes 按页面 / 流程 / 组件边界拆，并写截图或视觉验收标准。
- 技术债 changes 不混入业务 PRD changes。

## 所有权与边界

- 拆分方案和落盘的 changes 归目标仓库所有：apply、验证、归档都由目标仓库推进，本 skill 只做拆分与确认。
- 本 skill 所在的 skill 仓库不拥有任何产品的 canonical ontology/PRD/code；不写产品代码仓库，也不替 docs 仓改 canonical 层（docs 侧更新走 `prd-writeback.md` 的 review-gated 回写）。
- 无强制顺序管道：消费、实施、回写按短口令独立触发，互不阻塞。

## 输出

```text
消费产物：
- 绝对路径：
- 稳定 ID：
- docs commit SHA：

目标项目：
- 路径：
- 目标 scope：

候选分类：
- docs-only：
- verification-only：
- already-covered：
- low-confidence-excluded：
- confirmed-implementation：

证据：
- ...

建议 changes：
| CHANGE_ID | 来源 | 分类 | 影响 spec | 范围 | 验收 | 验证 | 依赖 |

下一步：
- ...
```

字段缺省规则：字段没有提供时必须写明 `unknown`、`not-found` 或 `not-applicable`，不得编造。稳定 ID / docs commit SHA 未随产物提供时，向用户或 docs 侧索取；索取不到就如实标注，不用猜测值顶替。
