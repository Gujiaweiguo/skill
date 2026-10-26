---
name: implementation-package-execution
description: 一次性实施交接包（implementation-package）的项目仓侧标准执行入口 Skill。用于目标项目仓会话收到 docs 侧 released 实施包后，一行触发全流程执行：四要素校验（package_status=released、目标仓匹配、公司/产品上下文、消费状态判定）、执行模式/change 策略解析（autonomous-batch/plan-and-apply、consume-existing/create-or-consume + allowed_change_ids fail closed）、preflight 门禁自读、权限宣告、按波次自主实施（plan-and-apply 下先创建/补齐 OpenSpec 工件并 strict validate 再 apply）、发射 implementation-return 回执（含逐 change phase_record）。预创建的 pending 空桩仅作 reservation，不阻断首次执行；已消费回执拒绝重跑。commit/archive/push 独立权限位，永不从 released/autonomous 推断。适用全部公司（lanlnk / lianyou，经 resolver 解析）全部产品；产品差异只出现在包体配置，不出现在协议结构。触发场景：“执行实施包 <绝对路径>”、“检查本产品 released 未消费实施包”、“实施包 preflight”、“输出实施包回执”。
compatibility: Pure prompt skill，无运行时脚本依赖。在目标项目仓会话内触发；协议唯一权威见本 skill references/execution-protocol.md 与 openspec-practice/references/implementation-package.md（本 skill 不复制契约正文）。
---

# Implementation Package Execution / 实施包项目侧执行入口

## 定位

docs → 项目仓 released implementation-package 的**项目仓侧标准执行入口**。docs 侧出包、Owner 决策与 release 审核仍归 `openspec-practice`；本 skill 只负责项目仓侧消费：校验、preflight、权限宣告、执行、回执。

适用全部公司（经 `COMPANY_BASE` / resolver 解析，当前 lanlnk、lianyou）与全部产品。产品差异只出现在包体配置（路径、门禁、S6/台账键），不出现在协议结构。

触发语（标准一行形态）：**「执行实施包 <绝对路径>」**。

## 快速流程

1. **解析包路径**：解析实施包绝对路径，**必须先复述**该路径与 `package_id` 再进入下一步。
2. **校验四要素**（任一失败立即拒绝并说明缺口）：
   - `package_status = released`（draft / candidate 包不得执行）；
   - 包体「目标仓」= 当前仓（resolver 给出的 `code_root` 绝对路径比对）；
   - resolver 公司/产品上下文可解析且与包一致（company_id / product_id）；
   - 同 `package_id` 的回执通过消费状态判定：pending 且 `package_consumed=false`、无执行完成证据的预创建空桩可继续；已消费、终态或含执行完成证据的回执拒绝重跑。
3. **preflight**：HEAD / origin 指针、工作区干净度、输入锚点（docs 文件 SHA-256）核对；门禁命令与证据路径**从本仓 AGENTS.md / Makefile 自读**——不硬编码任何产品的命令或路径。
4. **解析执行模式/change 策略**（缺字段按兼容默认 `autonomous-batch` + `consume-existing`，与 v1.x apply-existing 行为一致）：
   - `execution_mode: plan-and-apply` 和/或 `change_policy: create-or-consume` 时，包体**必须**附带封闭 `allowed_change_ids` 清单——缺失即拒绝执行并回呼（fail closed）；清单内 change 可在包内波次 scope 集合内创建/补齐 OpenSpec proposal/design/tasks/spec；
   - `consume-existing`（默认）下发现波次声明的 change 不存在 → 回呼，不自行创建。
5. **宣告权限**：按包权限表逐项列 granted / denied（至少覆盖 OpenSpec change 创建/补齐、commit / archive / push / docs 写入），权限优先级按契约（released 包授权 > 仓默认规则；commit/archive/push 各自独立判定，push 与 commit 均不得由 released/autonomous/plan-and-apply 推断；docs 写入永不获得）。
6. **执行**：按包内依赖波次与授权推进，**一次一个 apply**，尊重仓内 OpenSpec 纪律（`openspec-*` skills / `opsx apply` 短语或既有工作流）。plan-and-apply 下每个 change 按「创建/补齐工件 → strict validate → apply」三段推进：validate 不过不得 apply；逐 change 记录 `phase_record`（created / planned / validated / implemented，未发生阶段如实标 skipped+原因）。
7. **fail closed**：越权（change ID / scope 超出 allowed_change_ids 或波次）、语义待决（包内 Owner 决策不足以裁决当前切片产品语义）、环境边界问题（依赖/权限/共享环境无法隔离）→ 停对应 change 并按异常回呼格式上报，不静默变通。
8. **自主推进**：仅在包内异常回呼条件或上一条 fail closed 命中时暂停对应行并回呼 docs（格式见协议），其余自主推进，**不向 docs 请求步骤级提示**。
9. **回执**：按包内 `checkpoint_policy` 发射 `implementation-return` JSON 并自校验字段（schema 自检清单见协议；plan-and-apply/create-or-consume 包必须含逐 change `phase_record`）。

## 硬门禁

- 四要素校验失败 → 立即拒绝执行并说明缺口，不做「部分执行」。
- 权限表驱动一切写动作：表内未列即 denied；push 与 commit 不得由「自主执行 / released / plan-and-apply」推断，各自独立权限位。
- OpenSpec change 创建/补齐仅在 `plan-and-apply` / `create-or-consume` + 封闭 `allowed_change_ids` 同时成立时 granted，且 change scope 必须落在包内波次 scope 集合内；三者任一不满足 → fail closed 回呼。
- 语义待决、环境边界问题 → 停对应 change 回呼，不静默变通。
- return 发射前做 schema 自检（逐字段对照契约附录）。
- 不写 docs 仓；不改产品语义 / S6 判据 / Owner 决策。
- 消费守卫：同 `package_id` 的 return 只有在已消费、已进入终态或含执行完成证据时才拒绝重跑；pending 且 `package_consumed=false` 的合法空桩 reservation 不阻断首次执行。

## 维护

- 协议唯一权威 = 本 skill `references/execution-protocol.md` + 契约 `skills/meta/openspec-practice/references/implementation-package.md`（v1.4+；执行模式/change 策略/allowed_change_ids 见契约 v2.0「执行模式与 change 策略」）。
- 本 skill 不复制契约正文；契约升级时只核对协议文件与新版契约不矛盾。
