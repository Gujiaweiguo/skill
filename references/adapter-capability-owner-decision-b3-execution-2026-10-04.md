# B3 执行记录 —— product-registry 删除阻塞项 B3（产品注册入口迁移 onboarding 契约）执行记录（2026-10-04）

```text
STATUS: EXECUTED（已批准执行并已完成）
OWNER SIGN-OFF: NOT RECORDED（仅会话授权，无独立签署记录）
SCOPE: B3 only（注册入口迁移 _paths.py 错误引导 + A5 断言 + registry 头部规则 1 + 审计 §4-B3 状态回写）
```

> **记录性质（必读）**：本文件是 B3 的**执行记录**，由 B3 执行会话本身落盘（非事后补录，
> 验证结果均为本会话实测）。它记录的事实是：**用户在 B3 实施前的会话中明确批准执行
> B3**，并随附 owner 决定（会话授权，指令原文含「批准执行 B3」、owner 决定核心、
> 逐条允许/禁止边界，且明文「授权来源为本轮用户会话明确授权；除非发现真实独立签署
> 记录，否则保持 OWNER SIGN-OFF: NOT RECORDED」）。它**不是**、也**不得被引用为**
> 一份独立签署的 owner 批准记录——与
> `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`
> （owner 指令 verbatim 落盘 + `OWNER SIGN-OFF: RECORDED`）那种签署记录不同，
> B3 **不存在**同类型的独立签署证据（见 §3 事实区分）。

---

## 1. 登记字段

```yaml
decision_id: B3
decision_date: "2026-10-04"
record_date: "2026-10-04"
owner: "opc"
owner_basis: "本仓治理约定：一人公司，owner = opc（AGENTS.md；与既有决策记录口径一致）。注意：owner 身份有依据，但 owner 独立签署记录不存在（见 §3）"
status: "已批准执行并已完成"
owner_decision: |
  产品注册的唯一入口 = 既有 docs 侧 onboarding 契约：
    bash scripts/onboard.sh product <company> <pid> --name "<产品名>"
  该命令写 company.yaml products 台账并创建 30-products/<pid>/{prd,ontology} 骨架。
  product-registry.yaml 不再作为新产品注册入口（保留为迁移期兼容元数据）。
  代码侧若 canonical 目录名与该 pid 不同，仍在 _paths._PRODUCT_CANONICAL_DIR 补映射
  （先例 lnkcrm，acbae37）——此映射是代码实现细节，不是产品台账来源。
authorization:
  type: "session_consent"
  source: "B3 实施前用户明确批准「批准执行 B3」的提示词（会话授权；含 owner 决定核心、四、允许修改范围 / 五、严格禁止 逐条边界、六、验证命令清单）"
  not_claimed: "不存在独立签署的 owner 批准记录（无 verbatim 指令落盘、无签署块）"
scope:
  approved: "审计 §4-B3 解除条件：owner 定义替代登记流程（company.yaml onboarding 契约）并同步改错误引导与断言"
  basis: "references/product-registry-迁移审计-2026-10-04.md §4-B3 + §1-A5"
files_implemented:
  - path: "skills/business/product-prd-generator/product_prd_generator/_paths.py"
    change: "_guard_unregistered_fallback() 的 stderr 警告（lanlnk 分支）与 MissingProductDataError 报错引导（非 lanlnk 分支）改指 onboarding 契约：bash scripts/onboard.sh product <company> <pid> --name \"<产品名>\"（写 company.yaml products 台账并创建 30-products/<pid>/{prd,ontology} 骨架）；_PRODUCT_CANONICAL_DIR 映射仍按需补（先例 lnkcrm，acbae37）。纯文案替换，解析逻辑 / resolver / authority 行为零改动，未新增 registry 读取"
  - path: "skills/business/product-prd-generator/tests/test_paths.py"
    change: "A5 断言（test_ontology_unregistered_product_on_non_lanlnk_company_raises）由 assert \"product-registry.yaml\" in msg 改为 assert \"onboard.sh product\" / assert \"company.yaml\"，并保留原 # 引导注册 注释意图 + B3 溯源注记一行。测试意图（未注册+非 lanlnk → 报错引导注册）不弱化、不删除"
  - path: "skills/business/product-prd-generator/references/product-registry.yaml"
    change: "仅头部规则 1 注释：由「新产品加入 = 补一条 entry」改为指向 docs 仓 onboarding 契约（含 _PRODUCT_CANONICAL_DIR 按需补映射说明与规则 10(c) 指针）。YAML 数据区（products: 块及全部条目字段）零改动"
  - path: "references/product-registry-迁移审计-2026-10-04.md"
    change: "§4-B3 行内联「已解除」标记 + B3 状态注记（授权 §四.5 最小回写；§1/§2 保持快照原文未重写，B1/B2 同口径）"
  - path: "references/adapter-capability-owner-decision-b3-execution-2026-10-04.md"
    change: "本执行记录（新增）"
forbidden_unchanged:
  - "product-registry.yaml 数据区（git diff 实证仅头部注释 hunk；products: 块零改动；registry 文件保留在仓，删除仍需独立 owner 批准）"
  - "resolver / shared/product_context（零改动）"
  - "company.yaml、30-products/**、产品代码（docs 仓与产品仓零改动）"
  - "adapter_status 与任何 capability 文件（六份 adapter-capabilities.yaml 零改动）"
  - "B4、B6、B7（未批准、未执行，仍为删除阻塞项）"
  - "O4 实际迁移、O5-O11（全部保持冻结）"
  - "_paths.py 其余 product-registry 引用（:40 / :44 / :319 docstring/注释与 :159 product-registry-feedback.yaml 引用——授权 §四.1 仅开放 :397/:407 两处，其余不在本轮清单，未触碰）"
results:
  source: "B3 执行会话实测（本记录即执行会话，非引用）"
  tests_scoped: "tests/test_paths.py 58 passed / 1 failed——唯一失败为 test_unconfirmed_lnkcrm_code_root_requires_explicit_override，经 /tmp 镜像回退本轮全部编辑后复跑同样失败（DID NOT RAISE），实证为既有失败（见 §5），与 B3 修改无因果；A5 目标测试与警告路径测试均通过"
  tests_full: "product-prd-generator 全量 168 passed / 3 skipped / 1 failed（同一既有失败；总数 172 与 B2 基线 169+3 一致，差值恰为该过时测试）"
  script_run: "check_docs_consistency.sh FAIL=0 / WARN=0 / PASS=33（RESULT: PASS，与 B2/B5-R5 基线一致）"
  rg_check: "rg product-registry 于 _paths.py 剩 :40/:44/:159/:319（docstring/注释，清单外）+ test_paths.py 归零；:397/:407 注册引导引用已消除"
  format_checks: "git diff --check 通过；_paths.py LSP 无 error；test_paths.py 仅既有 line-16 隐式相对导入提示（AGENTS.md LSP Warning 节登记的误报，pytest 实测通过）"
not_executed:
  - "B4、B6、B7 未批准、未执行（仍阻塞 registry 删除）"
  - "O4 实际迁移与 O5-O11 全部保持冻结"
version_control:
  committed: false
  pushed: false
  this_record: "untracked 新增文件"
  worktree: "工作区保留多处既有未提交修改（归属未确认），本轮未回退/未覆盖/未清理/未使用 git add -A；本轮编辑叠加在既有工作树状态之上（三个目标文件本已为 M 状态）"
```

## 2. 日期与 owner 的确认依据

**decision_date = 2026-10-04**：B3 执行会话日期（环境时区 Asia/Shanghai）；与前置链
（O1/O2 Batch 1、O3/Batch 2 audit、B1、B2、B5 系列）同日，用户前置状态指令确认
B1、B2、B5 已解除，B3 未批准未执行（本轮批准执行）。**owner = opc**：依据本仓治理
约定（AGENTS.md 一人公司）与既有决策记录一致口径。授权行为主体（会话中批准执行 B3
并给出 owner 决定的用户）按该治理约定即 repo operator = opc。**但** owner 身份可确认
≠ 存在 owner 独立签署记录——后者不存在（授权提示词明文要求保持 NOT RECORDED）。

## 3. 事实区分（防误引）

| 命题 | 状态 | 依据 |
|---|---|---|
| 用户明确授权执行 B3（会话同意「批准执行 B3」提示词，含 owner 决定核心与逐条边界） | **成立** | B3 实施前用户会话批准；指令原文明文「授权来源为本轮用户会话明确授权；除非发现真实独立签署记录，否则保持 OWNER SIGN-OFF: NOT RECORDED」 |
| 存在独立签署的 owner 批准记录（verbatim 指令落盘 / 签署块 / SIGN-OFF: RECORDED） | **不成立，不得声称** | 全仓决策文档族中无 B3 的独立签署记录；O3 记录的签署仅覆盖 O3 / Batch 2（audit-only），B1/B2 记录 §3 已确立同口径区分 |

引述规则：后续任何文档引用 B3 授权时，只能表述为「B3 经用户会话授权执行
（2026-10-04，见本记录）」，不得表述为「B3 经 owner 独立签署批准」。**B3 完成亦不
构成 product-registry.yaml 删除批准**（删除 = 独立 owner 批准动作，B4/B6/B7 仍阻塞）。

## 4. 批准范围与实际实施对账

| 审计 §4-B3 / 授权 §四 列出的目标 | 实施 | 载体文件 |
|---|---|---|
| `_paths.py` 未注册报错引导（:397 警告 / :407 报错）改指 onboarding 契约 | ✅ 纯文案替换，引导指 `scripts/onboard.sh product`（写 company.yaml products 台账 + 30-products/<pid>/{prd,ontology} 骨架）+ `_PRODUCT_CANONICAL_DIR` 按需补映射说明 | product_prd_generator/_paths.py |
| A5 文案断言（test_paths.py:210）改指新注册引导关键词 | ✅ 断言 `onboard.sh product` / `company.yaml`，不再断言 product-registry.yaml；测试意图保持 | tests/test_paths.py |
| registry 头部规则 1（注释）改为指向 onboarding 契约 | ✅ 数据区零改动（git diff 仅头部注释 hunk） | references/product-registry.yaml |
| 新增执行记录 | ✅ 本文件 | references/adapter-capability-owner-decision-b3-execution-2026-10-04.md |
| 审计 §4-B3 状态回写 | ✅ 行内「已解除」标记 + 状态注记 | references/product-registry-迁移审计-2026-10-04.md |

范围对账结论：实际实施 = 批准范围，无超出。授权 §五 禁止项全部未触碰（registry
数据区 / resolver / company.yaml / 30-products / 产品代码 / adapter_status /
capability 文件 / B4 / B6 / B7 / O5-O11 / 既有未提交修改）。

## 5. 既有失败登记（与 B3 无因果，未修复）

`tests/test_paths.py::test_unconfirmed_lnkcrm_code_root_requires_explicit_override`
（:337-342，**另一会话未提交 diff 新增的测试**，不在本轮 hunk 内）失败：DID NOT RAISE。

- **根因**：docs 仓 `company.yaml` 已为 lnkcrm 登记 `code_root: /opt/code/lnkcrm`
  （真实代码仓已存在），`resolve_code_root` 经 shared resolver 解析为 complete 后正常
  返回，该测试「code_root 未确认须显式覆盖」的预期已过时。
- **与 B3 无因果的三重实证**：(1) 本轮 `_paths.py` 修改仅为 `_guard_unregistered_fallback`
  内字符串字面量，不在 `resolve_code_root` 调用链上；(2) 该测试位于另一会话的
  git diff hunk（@328-330），本轮未触碰；(3) /tmp 镜像工作树回退本轮全部三处编辑后
  复跑，同样失败。
- **处置**：不修复（修复须改该测试或等待其归属会话处理，超出 B3 清单；授权 §五
  禁止修改清单外内容）。登记于此，供该测试归属会话或后续授权处理。

## 6. 遗留与同步事项

1. **O3 follow_up 的 B3 状态条目未同步**：审计 §7 要求阻塞项状态变化同步至 O3 决策
   记录 follow_up（B1/B2 先例），但本轮授权清单（§四）不含
   `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`，授权 §五
   明文禁止修改 B3 清单外内容——该同步留待后续授权补记（届时参照 B1/B2 follow_up
   条目格式）。
2. **`_paths.py` 残留 3 处 product-registry 描述性引用**（:40 / :44 / :319 docstring/
   注释；:159 为 docs 侧 product-registry-feedback.yaml 引用）：授权 §四.1 仅开放
   :397/:407 两处，其余未触碰。其表述（「canonical 布局登记见 registry」类）在 B3
   后语义偏旧（registry 降为兼容快照），属文档级迁移候选，建议随 B4（头部规则 6
   双源同步契约撤销）或后续文档批次处理。
3. **审计 §1-A5 行保持快照原文**：与 B1（§1-A1/A2/A3）、B2（§1-A4）同口径，快照
   不重写，状态由 §4 注记承载。
4. **§5 既有失败**：见上节，待该测试归属会话处理。
5. **B4、B6、B7 保持冻结**：registry 删除的其余阻塞项全部未批准、未执行；任何后续
   解除仍需对应独立授权（审计 §4 口径）。
6. **版本控制**：本记录 untracked；全仓未提交、未推送；其他会话工作区修改原样保留。

## 7. 证据路径索引（均已实物核验存在）

- `references/product-registry-迁移审计-2026-10-04.md` §1-A5、§4-B3、§7
- `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`（O3 签署记录，非 B3 授权来源）
- `references/adapter-capability-owner-decision-b1-execution-2026-10-04.md`、
  `.../adapter-capability-owner-decision-b2-execution-2026-10-04.md`（B1/B2 执行记录，
  本记录的格式与口径先例）
- `/opt/code/docs/scripts/onboard.sh`（product 子命令：company.yaml products 台账写入
  + `create_product_dirs` 创建 `30-products/<pid>/{prd,ontology}` 骨架，幂等；docs 仓，零改动）
- `/opt/code/docs/lanlnk/config/company.yaml`（products 块 8 产品 + `# --- products-end ---`
  marker；lnkcrm `code_root: /opt/code/lnkcrm` 为 §5 既有失败根因；docs 仓，零改动）
- `skills/business/product-prd-generator/product_prd_generator/_paths.py`
  `_guard_unregistered_fallback()`（本轮文案落点）
