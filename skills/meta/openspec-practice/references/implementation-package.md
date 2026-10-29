# 一次性实施交接包（implementation-package，全公司契约）

> 定位：docs → 目标代码仓的**可执行授权形态**。当一次批次交接需要「Owner 决策前置 + 范围内受限自主执行 + 完成后统一回写」时使用。
>
> 上游字段契约：[`cross-repo-handoff.md`](./cross-repo-handoff.md)（L2/L3 交接字段与收尾报告）。本文件是其中「授权边界」维度的展开：把会话级实施提示词固化为正式包（Markdown）+ 机器可读回执（JSON）。
>
> 适用：全部公司（经 `COMPANY_BASE` / resolver 解析，当前 lanlnk、lianyou）与全部产品。产品差异只出现在包体配置（路径、门禁、S6/台账键），不出现在协议结构。
>
> 溯源：LnkCRE《MI-CRE-一次性实施交接总包》R1-R5 实证 + LnkCRM W1 C2/C3/C4 首次正式执行（2026-10-09：三 change 实施→门禁→归档，回执含 docs 只读抽查与偏差登记）。

## 何时使用

- 批次含 2+ change 或跨 scope（L2），或交付后需要回写/正式对账（L3）；
- Owner 业务决策已在 docs 侧收敛，实施会话需要「一次授权、范围内自主」的执行权限；
- 单个 change 的常规交接仍走 `cross-repo-handoff.md` 字段即可，不必升级为本包。

## 包体大小分级（与 L0-L3 正交）

S/M/L 只控制交接信息的密度和执行材料的详细程度，不改变 L0-L3 的治理要求。涉及正式回写、canonical 晋升或可审计交付的任务，即使 change 数量少，也仍按 L3 要求提供完整证据。

| 级别 | 适用 | 包体与回执策略 |
|---|---|---|
| S | 单 change、单 scope、无独占边界、无正式回写 | 优先使用 `cross-repo-handoff.md`；若仍需本包，只渲染目标、范围、非目标、验收和回执字段，不复制背景正文 |
| M | 2-5 个 change、存在依赖排序或需要批次回执 | 使用标准实施包；共享一次批次 preflight，逐 change 复核可变状态 |
| L | 5 个以上 change、跨 scope、数据库/权限/路由/共享组件、正式对账或高风险并发环境 | 使用完整实施包、逐 change evidence、verification-report、三元组和 docs-side audit |

会话在生成包时先给出 `package_size: S | M | L` 及判定理由。包体大小不能降低已有 L0-L3、Owner 决策、权限、证据或回写门禁。

## 批次执行效率规则

1. **批次 preflight 只做一次**：同一批次共享 AGENTS.md、OpenSpec scope、目标 revision、active/archive 概况和验证入口等稳定事实；项目仓仍需在每个 change 前复核工作区、依赖、独占边界和可归因证据等可变事实。
2. **依赖波次用于调度**：先按依赖和独占边界编排 Wave；无依赖的切片可以继续准备或验证，被阻塞的切片不得拖停其他独立切片。
3. **apply 保持一次一个**：波次不是并发 apply 授权。涉及相同 tracked 文件、数据库、权限、路由或共享组件的 change 必须串行；每次 apply 前后都记录实际 revision。
4. **提示词只渲染执行面**：实施提示词携带目标、范围、非目标、Owner 决策、依赖波次、验证命令、权限和停止条件；完整 PRD、历史背景和全部 follow-up 只通过输入锚点引用，不复制进提示词。
5. **证据要求不因提速省略**：JSON 回执、verification-report、evidence 和最终 SHA 绑定仍按 L0-L3 与包体大小要求执行；人读摘要只补充 JSON 没有表达的事实，不重复复制回执内容。
6. **Preflight 事实断言必须全量实读（P5 教训，2026-10-18 实证）**：包内 preflight 表的每条事实断言（尤其**否定性断言**如「Makefile 无 X 目标」「仓内无 Y」）必须来自完整输出——禁止 grep/head/tail 截断后下结论（实证：`grep '^[a-z-]+:' Makefile | head -20` 截断漏看 L91-95 的 smoke 目标，误判写进包 P5，被实施方 preflight 纠正，偏差登记于回执）。否定性断言须以完整清单或反向枚举复核；实施方 preflight 对包事实的修正按偏差如实登记并回执，不静默改写。
7. **released 包 preflight 可变事实刷新（2026-10-21 实证）**：包生成到执行之间目标仓推进时，允许且建议对 released 包做**仅限 preflight 可变事实**的版本刷新（执行区间/active changes/工作区禁触清单/测试门禁提示），Owner 决策表与授权边界一字不动；刷新后版本行递增并重新同条输出摘要+路径+启动段。实证：asof 包 v1.0（10-18）→ v1.1（10-21，目标仓 2934e881→ed8a981a 期间 40+ 提交：active changes 4→2、他会话脏文件全部提交、测试基建合入），刷新消解三处过时断言，执行侧零回呼。
8. **docs 侧回执吸收 SOP（2026-10-21 实证）**：`proposed_updates` 必须**先核验再吸收**——逐条对照归档 verification-report/feature SHA/提交区间实证后才写 PRD；回执生命周期 reviewed→absorbed 需补齐：`docs_side_audit`（verified + 未独立复跑项 + discrepancies 如实保留）、PRD SHA 双锚定（输入版/回写版）、包状态推进 reconciled + 版本行。禁止把「门禁零新增失败」表述为「全绿」（known_failed/flaky 台账事实保留）。
9. **吸收收尾义务与时序（2026-10-21 pilot 实证，lnkcre tax-export + masterdata-fullwidth 双例）**：吸收会话完成 PRD/状态板/包体回写后，**必须同批把回执 `review_status` 推进到 `absorbed` 并补 absorption 处置记录**（dispositions 逐项 done-verified + 证据锚点 + not_independently_verified 如实保留）——双例均出现「包体已标 reconciled 而回执停留 reviewed」的滞后，吸收闭环以回执 absorbed 为准。附带惯例三条：①released 包发布时预创建的空桩回执（全 pending、`package_consumed=false`）= 执行中占位，属合法形态；②docs 侧吸收写入应**尽快提交**（或先在状态板/包体留 in-flight 标记），避免与并行 docs 会话在同一 reconciliation 目录碰撞（2026-10-21 lnkreport 实证：在途未提交吸收 + 第二会话险些重复写入）；③**接手判断（2026-10-21/22 lnkreport 双实证）**：接手 reviewed 停驻回执的 absorbed 收尾前，必须先核对其吸收证据（ledger / pending-decisions / 包体回填）是 **HEAD 已提交态还是工作区在途态**——在途态属活跃会话半成品（其 proposed_updates 常自述「absorbed this return file」），不得接管，避免同文件双写；只有证据已在提交历史中才可安全接手收尾。

## 一步触发（默认入口）

出包请求**一步触发**，不要求先单独跑 PRD 生成或前置确认。最简触发语：**「出实施包」**——会话从上下文推断产品与批次（不明确时问一次），完整形态如下：

```text
"按 implementation-package 契约为 <批次> 出实施包。
需求基线够就直接生成 released 正式包，同一条回复里给我交接包摘要、包绝对路径和项目仓启动段；不够就把缺口连同 OQ 待裁决表和建议一起列出来，我一次确认。"
```

会话据此二选一返回（v1.7 默认规则）：

- **基线已就绪，且无真正阻塞的未决 Owner 决策或授权边界问题** → **直接生成 `package_status=released` 的正式交接包**，不再要求先单独出草案/单独 release；**同一条回复同时输出**「交接包摘要 + 交接包绝对路径 + 项目仓启动段」，不等待、不要求用户回复「同意」——同意不是必需步骤，用户可直接对摘要提出修改意见。注意（v2.0）：canonical ontology/PRD 尚未晋升、目标仓 change 尚未创建，**都不是** released 的阻塞项——前者走输入锚定如实记录 authority 状态，后者用 `execution_mode: plan-and-apply` + `change_policy: create-or-consume` + `allowed_change_ids` 显式授权目标仓创建；
- **存在范围内未决业务决策（未按 not_applicable_this_batch 豁免排除）、授权边界未定，或用户明确说「先出草案/先讨论」** → 生成 `draft` 包 + OQ 待裁决表（每项：现有约束、可选方案、**推荐方案及理由**、影响的行/验收门禁）——Owner 一次裁决后回填再 release；确需新需求域时才转入 PRD 生成流程。

Owner 对交接包摘要提出修改意见时：修改后重新生成/更新 released 包，并**再次同条输出摘要 + 路径 + 启动段**，不降级回 draft 流程（除非出现新的未决业务决策）。

两条红线不变：release 时点 `owner_decisions` 禁 `pending`；**推荐不是裁决**，不得默认采纳。

### 默认交付物（released 时）

released 实施包（含默认直接 released 的正式包）交付**同一条回复同时输出**：

1. **交接包路径**：包本体（`implementation-package-<batch>.md`）+ 配套回执约定（`implementation-return-<batch>.json`，executed 后由项目侧回填）的绝对路径；
2. **项目仓启动段**：目标项目仓会话启动用的入口内容，按目标仓是否接入标准 skill 二选一——
   - **已接入 `implementation-package-execution`**：一行「执行实施包 <包绝对路径>」；
   - **未接入**：渲染可直接复制的会话级完整实施提示词（按「提示词只渲染执行面」规则裁剪）。

启动段只随包交付在会话中输出，**不归档**（与硬规则 6「会话级实施提示词不归档」一致）；包本体 + `implementation-return` 回执仍是唯一权威记录。不得因目标仓已接入 skill 就省略启动段——「只给包路径、不给启动段」不是合格交付。

## 硬规则

1. **交接单位是切片，不是 PRD**：一个批次一个包。PRD confirmed ≠ 实施授权；PRD draft 中被单独授权的切片同样可用本包。「产品方向已裁决 / canonical ontology·PRD authority 状态 / 实施授权已授予 / change 已创建 / 已实施 / 已归档 / archive 已进提交历史 / 已 push」是相互独立的事实，不得互相冒充。**三重解耦（v2.0）**：①canonical ontology/PRD authority（docs 侧晋升状态）②change 是否已在目标仓创建 ③执行授权（本包批次授权）三者互不推断——**基线/PRD unresolved（如增量 PRD 仍 draft、ontology 变更集未晋升）不自动阻塞 released**；只有存在**真正阻塞的未决 Owner 决策**或**授权边界本身未定**时才降 draft。
2. **决策前置**：包内 `owner_decisions` 不允许 `pending` 阻塞项——存在未决产品问题不得放行该切片（可拆出留后续，并在后续追踪登记）。未决项**唯一的豁免形态**：显式标记为「本批不适用（not_applicable_this_batch）」并在批次范围/非目标中**明确排除**，才不构成阻塞；任何仍落在批次范围内的未决项照旧阻止 release。
3. **权限分层**：范围内技术动作一次授权；归档、S6/台账升级、push、docs canonical 回写、真实外部联调是**独立权限位**，默认不授予。**commit / archive / push 三个权限位永远独立判定**，不得从 `package_status=released`、`execution_mode`（含 autonomous / plan-and-apply）或「自主执行」推断获得——权限表没写就是 denied。
4. **输入锚定**：docs 工作区有未提交内容时，逐文件记 SHA-256 + 采集时间 + 「工作区版本」属性；禁止只用 docs HEAD 冒充实际消费版本。**锚点哈希必须取最终提交字节**：完成包体与被锚文件的全部编辑（含空白/EOF 规范化）并提交后，再计算或回填锚点；禁止锚定从未提交的瞬态工作区状态（2026-10-26 lnkcre 实证：包锚 `de56d349` 为签发后 EOF 规范化产生的瞬态哈希，不在任何 git 历史版本中，目标仓 preflight 匹配失败，只能内容级兜底并登记 discrepancy）。
5. **证据绑定**：evidence 绑定包含最终实现的真实 commit SHA；证据 SHA 之后的修复提交须重新生成受影响证据，不得跨 SHA 拼接。
6. **单一权威**：会话级实施提示词不归档；以正式包 + `implementation-return` 回执为唯一权威记录，落在 `<company_base>/30-products/<product>/reconciliation/`（命名 `implementation-package-<batch>.md` / `implementation-return-<batch>.json`）。
7. **公司解析**：生成包前经 resolver 确定 company_base（cwd 推断 → 用户点名 → 询问），绝不静默默认公司。

## 执行模式与 change 策略（v2.0）

包体两个字段声明执行形态，二者独立于权限位，**不隐含授予任何 commit/archive/push 权限**：

| 字段 | 取值 | 语义 |
|---|---|---|
| `execution_mode` | `autonomous-batch`（默认，兼容既有 apply-existing 单纯模式） | change 已在目标仓创建完毕，项目侧直接按波次 apply |
| | `plan-and-apply` | 允许项目侧在**明确授权的 change ID 清单内**先创建/补齐 OpenSpec proposal/design/tasks/spec，strict validate 通过后再 apply |
| `change_policy` | `consume-existing`（默认） | 只消费目标仓已存在的 change；发现缺失即回呼，不自行创建 |
| | `create-or-consume` | 存在则消费、缺失则在授权清单内创建/补齐 |

约束：

1. **`allowed_change_ids` 是硬约束（fail closed）**：`plan-and-apply` / `create-or-consume` 必须附带**封闭的 `allowed_change_ids` 清单**——项目侧只可对该清单内的 change ID 做 OpenSpec 工件创建/补齐；清单缺失、或要创建的 change ID 不在清单内 → 一律拒绝并回呼，不得自行扩权。新建 change 的 scope 必须落在包内波次声明的 scope 集合内。
2. **创建/规划 ≠ 实施**：plan-and-apply 下每个 change 走「创建/补齐工件 → strict validate → apply」三段，strict validate 失败不得 apply；三段结果逐 change 记入回执（见附录 `phase_record`）。
3. **兼容默认**：包体未写这两个字段时，按 `autonomous-batch` + `consume-existing` 解释，行为与 v1.x apply-existing 单纯模式完全一致——既有包零迁移即可继续执行（migration note：新出包建议显式写两字段；旧包不需要改）。
4. **项目侧 fail closed 清单**（命中即停该 change 并按异常回呼格式上报，不得静默变通）：越权（change ID / scope 超出授权清单或波次）、语义待决（实施中发现包内 Owner 决策不足以裁决当前切片的产品语义）、环境边界问题（依赖/权限/共享环境无法隔离）。

## 权限优先级与项目侧执行入口（v1.4）


目标项目仓的默认规则（如 AGENTS.md「不提交 Git，除非用户明确要求」类条款）与本包的批次授权在项目侧执行会话中并存，按以下**权威优先级（高→低）**裁决：

1. **用户在当前会话的新指令**——最高权威，可覆盖以下一切；
2. **released 实施包的批次授权**——仅限包内 scope 与权限表列明的动作；
3. **目标仓默认规则**——含 AGENTS.md「默认不提交 Git」类条款；
4. **无授权默认**——只读。

由此推论：

- released 包权限表**明确授予**的 commit / archive / push，在该批次范围内覆盖目标仓「默认不提交」规则——项目侧会话不得再以仓默认规则为由逐步索要步骤级提示或确认；
- **push 仅当权限表显式授予**，不得由「自主执行」推断获得；默认不授予（`push_policy: explicit`）；
- **docs 写入、产品语义 / S6 判据 / Owner 决策变更永远不因批次授权获得**——它们不在批次授权的可授予集合内，任何包都授不了。

**一次性消费守卫**：项目侧执行前必须校验 `package_status = released`，并检查同 `package_id` 的 `implementation-return`。released 包预创建的 pending 空桩是合法 reservation，不构成已消费，不得因此阻断首次执行；该空桩必须同时保持 `package_consumed=false` 且不含 feature commit、verification SHA 或 archive commit/path 等执行完成证据。若回执已标记 `package_consumed=true`、已进入 `reviewed`/`absorbed` 等终态，或已包含执行完成证据，则拒绝重跑并要求重新出包授权。首次执行完成后必须回填同一回执并设置 `package_consumed=true`，此后同一包不得重复执行。

**标准项目侧入口**：项目仓会话收到 released 包后，一行触发「**执行实施包 <绝对路径>**」，由 `implementation-package-execution` skill（项目仓侧标准执行入口）驱动全流程（四要素校验 → preflight → 权限宣告 → 波次执行 → return 回执）。历史上的「启动用长提示词」模式**降级为可选回退**：仅在目标仓未接入标准 skill 时使用；推荐迁移路径 = 目标仓接入 `implementation-package-execution` 软链后，一律改用一行触发。**出包会话的默认义务**：released 交付时必须同时输出交接包路径与项目仓启动段（已接入 skill 用一行触发，未接入用完整回退提示词），不得只交付包本体。

## 包体骨架（复制后填写）

```markdown
# <产品> <批次标识> 一次性实施交接包

| 项 | 值 |
|---|---|
| package_id | <product>-<batch>-<yyyymmdd> |
| package_size | S / M / L |
| 产品 / 类型 / 状态 | <product_id> / 跨仓一次性实施交接包 / draft → released → executed → reconciled |
| 配套回执 | ./implementation-return-<batch>.json |
| 目标仓 | <resolver 给出的 code_root 绝对路径> |
| 执行区间 | <origin 指针> → <本地 HEAD>；push 状态与授权按回执和权限表填写 |
| execution_mode / execution_owner | autonomous-batch（默认）或 plan-and-apply / target-repository |
| change_policy / allowed_change_ids | consume-existing（默认）或 create-or-consume + 封闭 change ID 清单（plan-and-apply/create-or-consume 必填）|
| commit_policy / archive_policy | autonomous（包授权范围内）/ autonomous（过门禁后，若权限表授予）|
| push_policy | explicit（默认不授予）|
| checkpoint_policy | track-close-or-N-s6-rows / per-batch（回执频率）|

## 1. 输入锚定
<逐个列出实际消费的 docs 文件路径 + 完整 SHA-256 + 采集时间；docs 工作区版本属性；公共产品上下文（公司/产品/三层 authority/解析状态）>

## 2. Owner 决策（执行前确认，非建议）
| 决策 ID | 裁定 | 影响 |
<只写已确认项；沿用既有裁决的注明出处不重新提问；未决项不得出现在放行切片——唯一豁免：显式标 not_applicable_this_batch 且已从范围/非目标排除>

## 3. 批次授权（一次性授予）
- 补齐 OpenSpec artifacts 并 strict validation；
- 按依赖顺序 apply（一次一个 change）；
- <plan-and-apply / create-or-consume 时额外一行：在 allowed_change_ids 清单内创建/补齐 OpenSpec proposal/design/tasks/spec 并 strict validate，validate 不过不得 apply；清单外 change 一律回呼>
- 范围内代码与测试；先写可失败测试再实现；
- 本批直接导致失败的配套测试维护（保持断言强度，禁删/跳/弱化）；
- 精确 pathspec 普通 commit（禁 add -A / 裸 commit -a / amend / 历史重写）；
- 干净可归因工作区上生成 SHA 绑定 evidence 与 verification-report；
- 过门禁后，如权限表明确授予，才可归档并同步 delta specs（保留未受影响 requirement/scenario）。

## 4. 明确不授予
<标准五项 + 产品特有禁止：S6/台账升级、push、docs 写入、范围外业务、他会话文件与共享环境（含杀他会话进程/删共享库）>

## 5. 异常回呼条件（仅此回呼，其余自主推进）
1. 需更改已确认产品语义 / S6 行映射 / 验收目标；
2. 出现未覆盖的 Owner 业务规则；
3. 突破批准边界或触碰禁止路径；
4. 依赖、外部环境或权限不满足；
5. 共享环境无法隔离、提交或证据不能可靠归因，或验证不能证明原定目标；
6. 门禁失败无法在授权内安全修复，或 spec 同步会损失既有内容。
<回呼格式：事实 + 受影响 change + 最小决策请求 + 可独立继续切片；不得因无关切片阻塞停掉已授权且依赖独立的工作>

## 6. 执行结果摘要（executed 后填写）
<一句话 + 指向 return JSON；draft/released 阶段保留为空>

## 7. 执行披露
<实施会话主动报告的越界/事故与补救；docs 标注哪些未独立复核>

**生成物全量再生的披露纪律**（2026-10-29 lnkcre Change C 实证）：包授权更新生成物路径（如 swagger/docs.go）时，全量再生会把**既有欠账**一并带入——Change C 一次补入 21 个既有路由 operation 并全局改 `$ref` 命名。处置三原则：①不阻断（路由/handler 已存在、零代码语义变化、模块钉定版本生成零错误即放行）；②必须作为回执 `docs_side_audit.discrepancies` 显式披露，不得描述成仅本 change 的 diff，也不得隐瞒规模；③不构成后续包扩大范围的先例（下一个包仍按自己的授权边界重新判定）。docs 吸收时核对生成物 diff 的路径/操作级增量（对比新旧 JSON path-method 集合），不采信「只是重新生成」的笼统说法。

## 8. 后续追踪
<S6 正式验收、deferred 补证、部署风险、docs 回写归属——均不由本包自动完成>

## 9. 版本
<package schema/version、修订日期、修订说明>
```

## 生命周期

```text
包：draft（仅范围内未决业务决策（未豁免排除）、授权边界未定或明确草案请求时）→ released（默认直接到达：基线充分且无真正阻塞项时一步生成，摘要+路径+启动段同条输出，不设 Owner 同意中间状态）→ executed（目标仓返回回执）→ reconciled（docs 回写完成）
回执：review_status pending → reviewed → absorbed（proposed_updates 逐项处置）
```

## 附录：implementation-return JSON 字段

| 字段 | 说明 |
|---|---|
| `schema_version` / `return_id` / `product_id` | `1.0`；`<product>-<batch>-<yyyymmdd>` |
| `origin_flow` | `implementation-package-execution`（区别于 `code-evidence-reverse`） |
| `package_ref` | 指向本包 MD 的绝对路径 |
| `trace_ids` | wave/change/REQ/F/GAP 追溯键 |
| `source_revision` / `head_revision` / `commits_ahead_of_origin_main` / `pushed` | 目标仓执行区间事实 |
| `owner_decisions_executed` | 实际执行的决策记录 |
| `changes[]` | 每 change：`s6_rows`（含状态注记）、`feature_commits`、`verification_sha`、`archive_commit`、`archive_path`、`gates`、`notes` |
| `changes[].phase_record` | v2.0 新增，plan-and-apply/create-or-consume 时必填、apply-existing 可省略：逐 change 记录 `created`（工件创建/补齐，含新建 change ID 与工件清单）、`planned`（proposal/design/tasks 定稿）、`validated`（strict validate 结果与命令）、`implemented`（apply 与 feature commits）四阶段事实；某阶段未发生则如实标 skipped + 原因，不得留空冒充已发生 |
| `push_evidence` | 发布证据对象：推送区间、逐 commit、ancestry 结论、diffstat 与域检查、工作区状态、受保护工件哈希。由目标仓**发布会话**在 push 核验后回填（ls-remote 真远端查询 + merge-base --is-ancestor 逐 commit），W5 起多轮固化；`pushed=false` 的原始事实保留在回执历史，闭合由本对象承载 |
| `delta_spec_merge` | 各 capability 合并计数与既有保留情况 |
| `s6_ledger_untouched` / `docs_anchoring` / `protected_workspace_preserved` | 三项硬边界核验 |

**形状红线（高频违规，发射前严格校验）**——两处目标会话反复写成纯字符串导致 schema 违规（2026-10-26 lnkcre 两会话三批次实证，其中一次自称"schema 自检通过"实际未过）：

- `phase_record.<阶段>` 必须是**对象**（自由键值 + `summary`），不得写纯字符串；
- `protected_workspace_preserved` 必须是 boolean / 对象 / 数组 / null，不得写纯字符串——需叙述时用对象包裹键值；
- 回执发射前的自检必须用共享 `implementation-return.schema.json` 做**严格** jsonschema 校验，不得以宽松自检脚本替代。

最小合规示例：

```json
"phase_record": {
  "created":     {"summary": "工件四件套创建", "change_id": "…"},
  "implemented": {"summary": "…", "feature_commit": "…"}
},
"protected_workspace_preserved": {
  "design_docs_unchanged": "sha256 前后一致",
  "workspace_clean": true
}
```
| `incidents[]` | 越界/事故披露 + 补救 |
| `follow_ups[]` | 后续追踪清单 |
| `docs_side_audit` | docs 只读抽查：verified / discrepancies / not_independently_verified |
| `review_status` / `proposed_updates[]` | 按共享 schema 的状态词表记录；destination owner 审核后逐项处置，全部吸收后才能标记包 `reconciled` |
| `package_consumed` | 布尔；released 阶段预创建的 pending 空桩固定为 `false`，仅作 reservation；首次执行完成并发射完整回执时设为 `true`，之后重复执行需重新出包授权 |

> 收尾报告如同时适用 `cross-repo-handoff.md` 的标准模板，以本回执 JSON 为机器可读层、标准收尾报告为人读层，两者字段不得矛盾。

## 版本

| 版本 | 日期 | 说明 |
|---|---|---|
| v1.0 | 2026-10-09 | 首版：从 LnkCRE 总包先例（R1-R5）+ LnkCRM W1 C2/C3/C4 首次正式执行提炼；由 lanlnk 产品域模板晋升为全公司契约 |
| v1.1 | 2026-10-09 | 新增「一步触发」默认入口：出包请求自动二分（包草案 / 缺口+OQ 待裁决表+建议），不要求先跑 PRD 生成 |
| v1.2 | 2026-10-10 | 修正包体骨架状态：交接包不预填“已执行记录”，执行事实由 implementation-return 回执记录 |
| v1.3 | 2026-10-10 | 增加与 L0-L3 正交的 S/M/L 包体分级、批次 preflight 复用、依赖波次调度和执行提示词信息裁剪规则 |
| v1.4 | 2026-10-14 | 新增权限优先级与项目侧标准执行入口（implementation-package-execution skill）、执行策略字段、一次性消费守卫；启动提示词降级为未接入 skill 时的回退形态 |
| v1.5 | 2026-10-16 | 新增「默认交付物」：released 交付默认同时输出交接包路径 + 项目仓启动段（已接入 skill 用一行，未接入用完整回退提示词）；启动段仍只在会话中输出、不归档 |
| v1.6 | 2026-10-16 | 「出实施包」默认直接生成 released 正式包（基线充分、Owner 决策已明确、无阻塞未决项时），先输出交接包摘要供 Owner 审阅，Owner「同意」后输出项目仓启动段——「同意」是执行确认而非第二次 release；draft 仅用于缺口/未决业务决策或用户明确要求草案 |
| v1.7 | 2026-10-16 | 取消「同意」中间步骤：released 包的摘要、绝对路径与项目仓启动段**同一条回复输出**，同意不是必需步骤；Owner 有异议时直接提修改意见，更新 released 包后再次同条输出；生命周期改为基线充分时 draft→released→executed，不设 Owner 同意中间状态 |
| v1.8 | 2026-10-21 | 新增批次执行效率规则 7/8（asof 批实证）：released 包 preflight 可变事实刷新模式（决策/授权边界不动、版本行递增）；docs 侧回执吸收 SOP（先核验再吸收、SHA 双锚定、discrepancies 保留、「零新增失败≠全绿」表述纪律） |
| v1.9 | 2026-10-21 | 新增规则 9（吸收收尾义务与时序，rule-8 SOP pilot 双例实证）：吸收以回执 absorbed 为准、空桩回执=执行中占位、docs 吸收尽快提交防并行碰撞。pilot 同步发现：回执 JSON 形状跨产品三套并存（changes[] 键名/feature_commits 单复数/proposed_updates 自由文本 vs 结构体）、review_status 存在野值、共享 schema `implementation-return.schema.json` enum（incomplete/pending/accepted/rejected）与本契约生命周期词表（pending→reviewed→absorbed）不一致——schema 归属 product-prd-generator 治理域，待 owner 对齐 |
| v1.9.1 | 2026-10-22 | 规则 9 补惯例③接手判断：接手 reviewed 停驻回执收尾前先核对吸收证据是 HEAD 提交态还是工作区在途态，在途态属活跃会话半成品不得接管（2026-10-21/22 lnkreport 双实证：VTI 证据已提交可安全接手，chart-read/family-remediation ledger 在途属他会话） |
| v2.0 | 2026-10-26 | 授权模型解耦与 plan-and-apply：①三重解耦——canonical ontology/PRD authority、change 是否已创建、执行授权互不推断，基线/PRD unresolved 不自动阻塞 released，仅真正阻塞的 Owner 决策或授权边界问题才 draft；②硬规则 2 豁免形态：未决项显式标 not_applicable_this_batch 并从范围排除后才不阻塞；③新增「执行模式与 change 策略」：`execution_mode: plan-and-apply` / `change_policy: create-or-consume` + 封闭 `allowed_change_ids`（fail closed），允许目标仓先创建/补齐 OpenSpec 工件、strict validate 再 apply；④commit/archive/push 独立权限位，不得从 released/autonomous/plan-and-apply 推断；⑤项目侧 fail closed 清单（越权/语义待决/环境边界回呼）；⑥回执 `changes[].phase_record` 记录 created/planned/validated/implemented；⑦兼容默认：未写两字段按 autonomous-batch + consume-existing 解释，v1.x apply-existing 既有包零迁移（LnkCRM released 包实际使用驱动，未照搬产品语义） |
| v2.0.1 | 2026-10-26 | 两条实证红线 + 一个字段：①硬规则 4 补「锚点哈希取最终提交字节」（lnkcre de56d349 瞬态哈希实证）；②附录补回执形状红线与最小示例（phase_record 对象 / protected_workspace_preserved 非字符串 / 严格 jsonschema 自检）；③附录补 `push_evidence` 字段行。v2.0 plan-and-apply 首跑实证：lnkcre GAP-PC-04 P2 封闭清单零越权、phase_record 三段齐全 |
