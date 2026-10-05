# PRD 回写

用于短口令：`回写 PRD`。可选精确筛选：`回写 PRD <项目名/时间范围/change...>`。

## 目标

目标项目 change 归档后，用 archived change 的证据刷新 PRD 侧状态、覆盖矩阵和下一轮 suggested changes。回写证据按共享治理契约组织成 proposal；canonical 更新必须经 destination owner 审核后执行。

## 档位（L3）

本文件承载 **L3** 流程：交付回写、canonical 晋升或正式对账。

- L0 现场查询、L1 单个 PRD/gap 或单个 change 消费不要求完整交付三元组与回写协议。
- L2 多 change / 跨 scope 按场景要求 docs 产物绝对路径、稳定 ID、docs commit SHA 与目标仓 revision/commit；除非同时发生交付回写或 canonical 晋升，不要求完整三元组。
- L3 强制完整三元组、implementation-return proposal 与晋升后 pairwise 对账。跨仓字段与收尾报告模板见 `cross-repo-handoff.md`。

## 共享治理契约

回写证据的结构和语义以 product-prd-generator 拥有的共享契约为准，本 skill 只引用不复制：

- 契约目录：`/opt/code/skill/skills/business/product-prd-generator/references/product-governance/`（owner：product-prd-generator）。
- `implementation-return.schema.json`：回写证据本体。`trace_ids`、`target_repo`、`open_spec_change_id`、`verification_refs` 描述证据来源；`proposed_updates[].destination_layer` 指向 ontology/prd/code/reconciliation，状态从 `proposed` 起。
- `layer-reference.schema.json`：标识被回写目标层的 authority 与版本；解析不到时显式记 `unresolved` / `unsupported` / `inaccessible` 及原因，不用其他产品的 authority 顶替。
- `reconciliation-record.schema.json`：单次 pairwise 对账记录（见下文「晋升后 pairwise 对账」）。
- 涉及 ontology 变更时，另按 `ontology-change-set.schema.json` 记 draft/delta 提案。

契约是 skill 间接口，不是产品数据存储，也不是任何产品 canonical ontology/PRD/code 的权威；适用产品范围以该目录 README 为准（7 个软件产品，lnkwebsite 站点运营不在此契约内）。本 skill 所在的 skill 仓库不拥有任何外部 canonical 层产物。

## 读取清单（L3）

按以下清单读取，缺哪项就显式标注哪项，不得跳过也不得编造：

- 目标项目 `AGENTS.md`
- archived change（proposal / tasks / specs / design）
- verification-report
- 相关 canonical specs 与代码落点
- 测试证据

## 交付三元组与逐 change 记录（L3）

docs 侧必须记录：

- docs 产物绝对路径
- 稳定 ID
- docs commit SHA

项目仓侧必须记录指针三元组（三者缺一，回写只能标「归档受阻/未提交」）：

- feature 提交 SHA（实现落点）
- archive 提交 SHA（archive 目录与 verification-report 所在提交）
- origin 远端指针（对账基线锚点）

每个 change 单独一行记录：

- change ID
- feature SHA
- archive SHA
- archive 路径
- verification-report 路径；没有 verification report 的 change 必须显式标注，docs 对账时不可引验证报告

字段没有提供时写明 `unknown`、`not-found` 或 `not-applicable`，不得编造；编号映射无法唯一解析时如实报告，按 docs 侧台账对号入座，不杜撰。

## 输入

- 默认只需短口令 `回写 PRD`，由 agent 从当前目录、最近对话和项目名默认解析推断目标项目。
- 可选：产品 ID 或绝对项目路径；产品 ID 经公共 resolver 定位，绝对路径无法映射时保持 product unresolved。
- 可选：时间范围，例如 `今天` / `最近一次` / `本周归档`。
- 可选：一个或多个 archived change id/path，用于精确指定回写对象。
- 可选：PRD 输出目录。LnkCRE 当前 canonical 根为 `$LANLNK_BASE/30-products/lnkcre/prd/`（细分：baseline/increments/requirements/decisions/handoffs，回写件落 `prd/handoffs/`）。
- 可选：项目仓收尾报告（按 `cross-repo-handoff.md` 模板带回三元组、逐 change 记录与排除项清单）。
- 可选：`verification-report.md`、实现摘要、暂缓/合并/误判结论。
- 可选：已有 implementation-return / reconciliation-record 记录；存在时做增量更新，不重写、不静默删除既有 finding。

> 路径口径：`mi` / `lnkcre` / `LnkCRE` / `MI-CRE` 指同一产品（canonical id `lnkcre`）。`30-products/mi-cre/` 是历史路径和 source_ref 前缀（目录已于 2026-09 合并删除）——回写产物一律写入 `30-products/lnkcre/prd/`。docs 仓的 product registry / INDEX / OpenSpec change 只留在 docs 仓消费，不镜像进目标项目仓。

## 步骤

1. 读取目标项目 `AGENTS.md`。
2. 自动发现候选 archived changes：
   - 如果用户给了 change id/path，优先使用指定对象。
   - 如果用户给了项目名、项目路径或时间范围，在对应 OpenSpec archive 中筛选。
   - 如果用户只说 `回写 PRD`，根据当前目录、最近对话、项目名默认解析和最近归档时间找候选。
   - 候选过多或无法判断目标 PRD 时，先输出候选列表和需要用户确认的最小问题。
3. 读取候选 archived change 的 proposal/tasks/specs/design/verification-report（按「读取清单」执行）。
4. 反查 PRD 侧资料：
   - PRD 输出目录、`review/` 诊断报告、`suggested-openspec-changes.yaml`、`mi-consumption-prompt.md`。
   - change proposal / spec / verification 中提到的 PRD gap、feature、capability、module 名称。
5. 读取必要代码落点和测试证据；按「交付三元组与逐 change 记录」登记 docs 侧与项目仓侧指针。
6. 判断 PRD gap 状态：已实现 / 已合并到其他能力 / 暂缓 / code_map 漏判 / 仍未处理。
7. 更新前先列出候选 changes、目标 PRD、将修改的 PRD 文件和范围，以及按 `implementation-return.schema.json` 组织的 `proposed_updates` 清单，等用户确认。
8. 用户确认后再进入回写；canonical 更新仍须由 destination owner 审核接受。用户确认仅在其身份为 destination owner 或获授权代理时才满足该审核门。不改目标项目代码，不创建目标项目 change。

## 回写规则

- 目标治理顺序：未来增量先做 ontology impact check（记录变更或有依据的无变更），再形成 PRD delta，最后交目标代码仓实施。已存在的代码领先场景可反向形成带 revision/coverage 的实现事实与 reconciliation/candidate，但不得将实现现状自动升级为产品意图。
- OPC 为产品及 ontology 决策审核 owner。OPC 批准语义候选后才可晋升 ontology/PRD canonical；代码实现事实仍须记录目标仓、revision、扫描范围与验证证据，OPC 决策本身不构成技术验证。
- origin flow 是单次 change/return 的字段，不是产品属性。产品完整状态、ontology/PRD 内容覆盖成熟度、adapter 支持度（capability 文件口径）分开记录。
- 回写证据是 proposal：`proposed_updates[].status` 起始为 `proposed`；canonical 更新（PRD 资料库文件、ontology 基线）须经 destination owner 审核接受后执行。`review_status: accepted` 必须有 `verification_refs` 和 `review_owner`；证据不齐时保留 `incomplete`，不凑数接受。
- ontology draft/delta 保持 review-gated：涉及 ontology 变更只产出 `ontology-change-set` 提案（draft / under-review），canonical 晋升前必须获得 approval；回写流程不得直接改写 ontology 权威文件。
- 未实施、暂缓、排除项必须保留底稿原文带回并按原文登记，不得改写成已实施；项目仓不转述改写，docs 侧不替项目仓补口径。
- 所有权边界：目标仓库拥有自己的 OpenSpec changes 和验证；回写只消费 archived change 证据，不替目标仓库 apply、verify，不写产品代码仓库。
- 无强制顺序管道：回写与对账按短口令独立触发，不要求「消费 → 实施 → 回写」全链齐备才能执行。
- lnkcrm scope 基线（O5-Q4，2026-10-04 owner include 裁决）：目标产品为 lnkcrm 时，PRD gap
  状态判断（步骤 6）与「晋升后 pairwise 对账」的 `prd-code` 对照纳入 lnkcrm OpenSpec scope 集
  （`/opt/code/lnkcrm/openspec/specs/`，实测非空、含 member-*/coupon-* 等 scope 族；锚定
  scope 集合不钉数量，以实测 `ls` 为准）——scope 命中可作「实现基线层已覆盖」证据并引用
  scope 名，不得据此宣称实现级验证通过。scope 基线已纳入；实现级评估 O5-Q5 已解锁（2026-10-04，解锁集 = 最小验证集三 skill）。

## 证据红线

- 没有实施证据，不能把 PRD 标为已交付。
- 没有 verification report，不能声称验证通过。
- 没有 destination owner 审核，不能晋升 canonical。

## 晋升后 pairwise 对账

canonical 晋升（ontology 或 PRD 任一侧更新落地）之后，三对关系各自独立对账，每对一条 `reconciliation-record`：

- `ontology-prd`：ontology ↔ PRD
- `prd-code`：PRD ↔ code
- `ontology-code`：ontology ↔ code

规则：

- 三对独立检查，不得用一对的结论推断另一对。
- `coverage.status` 如实保留 `complete` / `partial` / `not-scanned` / `inaccessible`；未扫描或不可访问区域不得推断为缺失（对应 outcome 不得记 `missing`）。
- 证实为误判的历史 drift finding，用 outcome `false-positive-corrected` 修正并留痕，不静默删除。

## 输出文件建议

- LnkCRE：`30-products/lnkcre/prd/handoffs/实施回写-<YYYYMMDD>.md`（canonical 写入；历史 run 的 `output/review/实施回写-*.md` 与 `mi-cre/` 旧位置原位保留）
- 必要时更新 `功能清单.md`、覆盖度矩阵、`suggested-openspec-changes.yaml`、`mi-consumption-prompt.md`（历史文件名保持不变）。

## 完成标准

- 状态变化都有 archived change / spec / code / test 证据。
- 回写证据与对账记录符合共享契约；canonical 变更只出现在 destination owner 接受之后。
- 下一轮 suggested changes 不再包含已完成或误判项。
- code_map / ontology / term-aliases 问题进入单独修复清单（ontology 侧走 review-gated 提案，不直接改权威文件）。
