# 执行协议（implementation-package-execution）

> 契约权威：`skills/meta/openspec-practice/references/implementation-package.md`（v1.4+；执行模式与 change 策略按 v2.0）。本文件是项目仓侧执行协议的展开，不复制契约正文；两者矛盾时以契约为准。

## 1. Preflight checklist（逐项可勾选）

```markdown
- [ ] 1. 包路径已解析为绝对路径，并向用户复述路径与 package_id
- [ ] 2. package_status = released（draft/candidate 拒绝）
- [ ] 3. 包体「目标仓」绝对路径 == 当前仓根目录
- [ ] 4. resolver 公司/产品上下文：company_id / company_base / product_id 与包一致
- [ ] 5. 同 package_id 的 implementation-return 消费守卫已判定：pending 且 `package_consumed=false`、无 feature commit / verification SHA / archive commit/path 的预创建空桩仅作 reservation，可继续；已消费或含执行完成证据则拒绝重跑
- [ ] 6. git 状态已采集：当前 HEAD、origin/main 指针、工作区干净度（脏文件逐一登记）
- [ ] 7. 输入锚点核对：包内列出的 docs 文件 SHA-256 逐个重算比对（漂移即暂停回呼）
- [ ] 8. 门禁命令自读：从本仓 AGENTS.md / Makefile 读出验证/测试命令与证据路径（禁止沿用其他产品的硬编码）
- [ ] 9. OpenSpec 概况：active changes、archive 概况、涉及的 scopes 与包内波次对得上；**执行模式/change 策略已解析**：包未写 `execution_mode`/`change_policy` → 按兼容默认 `autonomous-batch` + `consume-existing`（等价 v1.x apply-existing）；写了 `plan-and-apply` / `create-or-consume` → `allowed_change_ids` 封闭清单必须存在且覆盖波次中所有需创建的 change，缺失即停在 preflight 回呼（fail closed）
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

## 3. 执行循环状态

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
