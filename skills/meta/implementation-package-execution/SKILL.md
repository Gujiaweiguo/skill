---
name: implementation-package-execution
description: 一次性实施交接包（implementation-package）的项目仓侧标准执行入口 Skill。用于目标项目仓会话收到 docs 侧 released 实施包后，一行触发全流程执行：四要素校验（package_status=released、目标仓匹配、公司/产品上下文、无既有 return）、preflight 门禁自读、权限宣告、按波次自主实施、发射 implementation-return 回执。适用全部公司（lanlnk / lianyou，经 resolver 解析）全部产品；产品差异只出现在包体配置，不出现在协议结构。触发场景：“执行实施包 <绝对路径>”、“检查本产品 released 未消费实施包”、“实施包 preflight”、“输出实施包回执”。
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
   - 目标仓内**不存在**同 `package_id` 的既有 `implementation-return`（一次性消费守卫）。
3. **preflight**：HEAD / origin 指针、工作区干净度、输入锚点（docs 文件 SHA-256）核对；门禁命令与证据路径**从本仓 AGENTS.md / Makefile 自读**——不硬编码任何产品的命令或路径。
4. **宣告权限**：按包权限表逐项列 granted / denied（至少覆盖 commit / archive / push / docs 写入），权限优先级按契约 v1.4（released 包授权 > 仓默认规则；push 仅显式授予；docs 写入永不获得）。
5. **执行**：按包内依赖波次与授权推进，**一次一个 apply**，尊重仓内 OpenSpec 纪律（`/opsx-*` 或既有工作流）。
6. **自主推进**：仅在包内异常回呼条件命中时暂停对应行并回呼 docs（格式见协议），其余自主推进，**不向 docs 请求步骤级提示**。
7. **回执**：按包内 `checkpoint_policy` 发射 `implementation-return` JSON 并自校验字段（schema 自检清单见协议）。

## 硬门禁

- 四要素校验失败 → 立即拒绝执行并说明缺口，不做「部分执行」。
- 权限表驱动一切写动作：表内未列即 denied；push 不得由「自主执行」推断。
- return 发射前做 schema 自检（逐字段对照契约附录）。
- 不写 docs 仓；不改产品语义 / S6 判据 / Owner 决策。
- 消费守卫：同 `package_id` 既有 return 已存在 → 拒绝重跑，提示重新出包授权。

## 维护

- 协议唯一权威 = 本 skill `references/execution-protocol.md` + 契约 `skills/meta/openspec-practice/references/implementation-package.md`（v1.4+）。
- 本 skill 不复制契约正文；契约升级时只核对协议文件与新版契约不矛盾。
