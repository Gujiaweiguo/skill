# 执行协议（implementation-package-execution）

> 契约权威：`skills/meta/openspec-practice/references/implementation-package.md`（v1.4+；执行模式与 change 策略按 v2.0，read-only-verification 分支、mode×policy 矩阵与版本三分按 v2.1）。本文件是项目仓侧执行协议的展开，不复制契约正文；两者矛盾时以契约为准。

## 1. Preflight checklist（逐项可勾选）

```markdown
- [ ] 1. 包路径已解析为绝对路径，并向用户复述路径与 package_id
- [ ] 2. package_status = released（draft/candidate 拒绝）
- [ ] 3. 包体「目标仓」绝对路径 == 当前仓根目录
- [ ] 4. resolver 公司/产品上下文：company_id / company_base / product_id 与包一致
- [ ] 5. 同 package_id 的 implementation-return 消费守卫已判定（权威规则见契约「一次性消费守卫」）：pending 且 `package_consumed=false`、无 feature commit / verification SHA / archive commit/path 的预创建空桩仅作 reservation，可继续**仅当**同时按契约 v2.1 核对目标侧证据渠道（同 package_id 既有回执 / 目标仓 active changes / feature commits）无已实施迹象——空桩本身不证明未实施；已消费、含执行完成证据或目标侧有已实施迹象则拒绝重跑并回呼 Owner
- [ ] 6. git 状态已采集：当前 HEAD、origin/main 指针、工作区干净度（脏文件逐一登记）
- [ ] 7. 输入锚点核对（基线漂移判定树）：包内列出的 docs 文件 SHA-256 逐个重算比对；不一致时按判定树处置——① 锚点哈希是否可在 docs 仓**提交历史**中复验（逐可考历史版本重算比对）？可考历史不全、无法穷尽核对 → 如实记「无法判定」，升级回呼签发侧，不得把核对能力不足当成「瞬态未提交」证明；确认不可复验 = 签发侧瞬态锚点缺陷，同样升级回呼，不得对当前工作区重试匹配；② 可复验时，当前 HEAD / 工作区是否已前进超过锚点版本？已前进 → 内容级等价比对：**仅当既有授权与包适用条件仍覆盖当前输入**时才可记 discrepancy 后放行；等价但授权/适用条件不覆盖、不等价或无法判定 → 暂停回呼 docs 重新出包；未前进（锚点即当前字节）→ 记录后放行；③ 处置分支与证据（比对命令输出、diff 摘要）逐项记录进回执。**字节匹配不跳过②**——锚点在历史中字节匹配 ≠ 当前输入仍适用于继续执行（包可能已在更新版本重新签发）
- [ ] 8. 门禁命令自读：从本仓 AGENTS.md / Makefile 读出验证/测试命令与证据路径（禁止沿用其他产品的硬编码）
- [ ] 9. OpenSpec 概况：active changes、archive 概况、涉及的 scopes 与包内波次对得上；**执行模式/change 策略解析按契约 v2.1「mode × policy 语义矩阵」（唯一权威）逐格判定**：先解析 `execution_mode`（含只读分支短路——不存在先于只读分支评估的创建模式通用条件），再解析 `change_policy`；未知/null/畸形 mode 或 policy 一律拒绝。执行要点：两字段缺省 = 兼容默认 `autonomous-batch` + `consume-existing`；`plan-and-apply` / `create-or-consume` 必须附封闭 `allowed_change_ids`（缺失即停在 preflight 回呼，fail closed）；`read-only-verification` 接受 `none` + `[]` 封闭空集、拒绝创建策略与非空集、缺省按 `none`/`[]` 解释、`consume-existing` 仅作无写权限旧别名
- [ ] 10. 独占边界确认：包内声明的 tracked 文件/数据库/权限/路由/共享组件无他会话在途冲突
- [ ] 11. fail closed 预判：无越权（change ID/scope 超清单或波次）、无语义待决（包 Owner 决策覆盖全部范围内切片）、无环境边界问题（依赖/权限/共享环境可隔离）——任一命中 → 停在 preflight 按异常回呼格式上报
```

任何一项无法勾选 → 停在 preflight，输出缺口，不进入执行。

## 2. 权限宣告输出模板

preflight 通过后、首个写动作前，必须输出一次：

```markdown
## 权限宣告（package_id: <id>）

| 权限位 | 状态 | 来源 |
|---|---|---|
| OpenSpec change 创建/补齐（proposal/design/tasks/spec） | granted（仅 plan-and-apply / create-or-consume 且 change ID ∈ allowed_change_ids、scope ∈ 波次 scope 集合）/ denied | 包执行模式与 change 策略；任一条件不满足即 denied |
| 范围内代码与测试（先写可失败测试） | granted | 包 §3 批次授权 |
| 精确 pathspec commit | granted/denied | 权限表（独立权限位，不得由 released/autonomous/plan-and-apply 推断） |
| 归档 + delta specs 同步 | granted/denied | 权限表（过门禁后，独立权限位） |
| push | granted/denied | 权限表（默认 denied，独立权限位，仅显式授予） |
| docs 仓写入 | denied | 永不可授予 |
| 产品语义 / S6 判据 / Owner 决策变更 | denied | 永不可授予 |

权限优先级：用户当前会话指令 > released 包批次授权 > 本仓默认规则（含「默认不提交 Git」）> 只读。
本宣告覆盖本仓默认不提交条款的范围 = 上表 granted 各项，且仅限包内 scope。
```

**read-only-verification 变体模板**（包 `execution_mode: read-only-verification` 时必须整体替换上表输出——实现模式模板中的 granted 行在只读模式不得保留）：

```markdown
## 权限宣告（package_id: <id>，execution_mode: read-only-verification）

| 权限位 | 状态 | 来源 |
|---|---|---|
| OpenSpec change 创建/补齐 | denied | execution_mode: read-only-verification |
| 代码与测试修改 | denied | execution_mode: read-only-verification |
| 数据库写入 / 迁移 | denied | 永不可授予 |
| commit | denied | 独立权限位，未授予 |
| archive | denied | 独立权限位，未授予 |
| push | denied | 独立权限位，未授予 |
| docs 仓写入 | denied | 永不可授予 |
| 产品语义 / S6 判据 / Owner 决策变更 | denied | 永不可授予 |
| 目标仓文件读取、无持久副作用的检查 | granted（仅限包内核验范围） | 包核验范围 |
| 数据库只读查询 | 须另行范围授权 + 连接授权（文件读取权限不隐含 DB 访问；DB 只读与 DB 写入是不同权限面，前者授权不放宽后者） | 包内显式授权 |
| 有副作用的测试/核验命令 | 默认 denied；仅包内显式列举且事前明确授权时，在该批准边界内可执行；授权不放宽 DB 写入/迁移 | OQ-2 裁决口径 |

只读模式授权边界 = 上表 granted 各项且仅限包内核验范围。执行前后的状态核对只是证据采集，不构成任何授权、不替代事前授权。
```

## 3. 执行循环状态

**仅适用实现模式**（`autonomous-batch` / `plan-and-apply`，含缺省解释）；`read-only-verification` 包跳过本节全部循环（不 apply、不记录 phase_record / feature_commits / gates），按 §2 只读宣告与 §5 findings 分支输出核验结论。

- 一次一个 change apply；每次 apply 前后记录实际 revision。
- **plan-and-apply 三段（仅当执行模式授权）**：每个 change 按「创建/补齐工件（仅 allowed_change_ids 内、scope 在波次集合内）→ strict validate（不过不得 apply）→ apply」推进；逐 change 记录 `phase_record`：`created`（含新建 change ID 与工件清单）/ `planned` / `validated`（含命令与结果）/ `implemented`，未发生阶段如实标 `skipped(附原因)`。apply-existing 单纯模式（默认）无此三段，行为与 v1.x 完全一致。
- 波次仅用于调度：无依赖切片可并行准备/验证，被阻塞切片不得拖停独立切片。
- 每 change 完成 → 记录 `feature_commits` / `verification_sha` / `gates`；过门禁且权限授予 → archive + delta spec 同步（保留未受影响 requirement/scenario）。
- 状态词只用：`pending / in-progress / blocked / done / skipped(附原因)`；不得把 blocked 写成 done。
- **fail closed 触发点**（执行中持续判定）：越权（清单/波次外 change 或 scope）、语义待决（Owner 决策不足以裁决当前切片）、环境边界问题（依赖/权限/共享环境无法隔离）→ 停对应 change，按 §4 格式回呼；其余切片不受影响继续推进。

## 4. 异常回呼输出格式

仅当包内「异常回呼条件」命中时回呼 docs，格式：

```markdown
## 异常回呼（package_id: <id>）
- 事实：<观察到什么，含 revision/命令输出摘要>
- 受影响 change：<change id 与波次>
- 最小决策请求：<一句话，可选项 + 推荐>
- 可独立继续切片：<不受影响、将继续推进的 change 清单>
```

不得因无关切片阻塞已授权且依赖独立的工作；其余一切自主推进，不向 docs 请求步骤级提示。

## 5. Return JSON 发射与自校验清单

按包内 `checkpoint_policy`（`track-close-or-N-s6-rows` / `per-batch`）发射 `implementation-return` JSON 到包体指定回执路径。发射前逐项自检：

```markdown
- [ ] schema_version / return_id / product_id / origin_flow 填写且 origin_flow = implementation-package-execution
- [ ] package_ref 指向本包 MD 绝对路径
- [ ] trace_ids 覆盖全部 wave/change/REQ
- [ ] source_revision / head_revision / commits_ahead_of_origin_main / pushed 与实际 git 状态一致
- [ ] changes[] 每 change 含 s6_rows / feature_commits / verification_sha / gates；plan-and-apply / create-or-consume 包还须含 phase_record（created / planned / validated / implemented，未发生阶段如实 skipped）
- [ ] read-only-verification 包的回执分支（最小显式字段见契约 v2.1 约束 7）：`execution_mode: "read-only-verification"`、`changes=[]` + 空集原因、核验范围与限度、findings（字符串 + 证据锚点：命令/路径/revision）、`schema_version: "1.0"`、初始 `review_status: "pending"`；引用的 gate/test 结论必须归因于抄录来源（archived evidence），不得伪称核验会话自身运行；不得伪造 feature commit / archive path / 已运行测试；`package_consumed` 语义与执行包一致（核验完成发射完整回执时置 true，空桩保持 false）；交付只落包内授权的本地回执路径——该路径在 docs 仓时仅在会话内交付内容、绝不写入
- [ ] **发射前必须实际运行 Draft202012 严格校验**（可复制命令形态：`cd /opt/code/skill/skills/business/product-prd-generator && uv run --extra dev python -m product_prd_generator.implementation_return_report '<absolute-return.json>'`，jsonschema 在 dev extra）。退出码语义：`0` = 源件严格校验通过；`1` = 源件存在校验错误（即使规范化视图通过——规范化通过不得追溯为源件通过）；`2` = 运行性问题（用法/文件读取/JSON 解析/依赖缺失），不是校验结论，修正运行条件后重跑。`1` 不得发射；不得以宽松自检脚本替代——历次形状违规回执均自称「自检 OK」而严格校验失败（见契约形状红线）
- [ ] s6_ledger_untouched / docs_anchoring / protected_workspace_preserved 三项硬边界均为核验事实
- [ ] incidents[] / follow_ups[] / docs_side_audit / review_status / proposed_updates[] 齐备
- [ ] package_consumed = true（首次执行完成的完整 return 才标记消费；预创建 pending 空桩保持 false）
```

## 6. 常见拒绝原因表

| 拒绝原因 | 表现 | 处置 |
|---|---|---|
| candidate/draft 包误当正式包 | `package_status ≠ released` | 退回 docs 侧走 Owner 确认 + release |
| 目标仓不匹配 | 包体「目标仓」≠ 当前仓 | 确认应在哪个仓执行；不迁移执行 |
| 基线漂移 | 输入锚点 SHA-256 重算不一致 | 回呼 docs 重新出包或确认工作区版本 |
| 包已消费 | 同 package_id 的 return 已标记 `package_consumed=true`、进入 reviewed/absorbed，或含执行完成证据 | 拒绝重跑；需重新出包授权 |
| 上下文不可解析 | company/product resolver 失败 | 停在四要素校验，说明缺口，不静默默认 |
| change 创建越权 | `plan-and-apply`/`create-or-consume` 但 `allowed_change_ids` 缺失，或要创建的 change ID 不在清单内 / scope 超出波次 | 停在 preflight 或对应 change，回呼 docs 补授权；不得自行扩权 |
| 语义待决 | 包内 Owner 决策不足以裁决当前切片产品语义 | 停对应 change 回呼（最小决策请求）；独立切片继续 |
| 环境边界问题 | 依赖/权限/共享环境无法隔离 | 停对应 change 回呼；不得静默变通 |
| read-only 模式组合冲突 | `read-only-verification` 搭配 `create-or-consume` 或非空 `allowed_change_ids`，或 `change_policy`/`allowed_change_ids` 显式 null / 畸形值 | 停在 preflight 拒绝并回呼 docs 修正包体；无任何实现模式默认可覆盖只读模式 |
| 只读越权（试图写面动作） | 只读模式下尝试创建 change、修改代码/测试、commit、archive、push、写 docs 仓、DB 写入/迁移，或执行未事前授权的有副作用命令 | 立即停止该动作并按 §4 异常回呼格式上报；状态核对与回执发射不构成授权 |
