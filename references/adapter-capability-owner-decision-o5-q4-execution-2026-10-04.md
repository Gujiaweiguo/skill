# O5-Q4 执行记录（lnkcrm OpenSpec scope 集纳入产品实现基线，2026-10-04）

```text
STATUS: EXECUTED（已批准执行并已完成）
DECISION RECORD: references/adapter-capability-owner-decision-o5-q4-2026-10-04.md
OWNER SIGN-OFF: RECORDED (OPC)（决策记录 :33-35，授权效力声明存在）
SCOPE: O5-Q4 only（三消费面措辞/evidence 接线；不触 O5-Q5、O6-O11、删除动作）
```

## 1. 执行前授权核验

| 核验项 | 结果 | 出处 |
|---|---|---|
| status | `approved` | 决策记录 :8 |
| decision | `include` | 决策记录 :9 |
| owner | `OPC（本治理域决策 owner）` | 决策记录 :5 |
| OWNER SIGN-OFF | `RECORDED (OPC)` | 决策记录 :33 |
| 授权效力声明 | 存在（OPC 明确授权即有效，无需独立第三方） | 决策记录 :34-35 |
| explicitly_not_authorized 含 O5-Q5 全部内容 | 是（实现级评估解锁/deep 读码、strategy-brief 浅→深、行为层启用；Q4 不自动解锁 Q5） | 决策记录 :22-25 |
| 停止条件 | 未触发（owner=OPC 且记录齐全） | — |

## 2. 纳入对象实测（锚定集合，不钉数量）

```bash
$ ls /opt/code/lnkcrm/openspec/specs/ | wc -l
28
```

实测 scope 集合（2026-10-04，`ls` 原始输出）：business-type, coupon-application-review,
coupon-claim, coupon-redemption-linkage, coupon-targeted-push, coupon-template,
member-credential, member-identity, member-level, member-level-benefit, member-level-rule,
member-profile, member-tags, merchant-h5, merchant-statistics, merchant-verification,
operation-audit, platform-authn, platform-authz, points-account,
points-expiry-and-clearance, points-ledger, points-member-query, points-rule,
points-self-service-review, product-baseline, repository-foundation, tenancy。

结构事实（本轮措辞断言只依赖这些，不写死 27/28）：非空；scope 族实测计数
member-* 7 / coupon-* 5 / points-* 6 / merchant-* 3 / platform-* 2 / tenancy 单例 1
（设计包观察 27，决策记录落盘实测 28，活跃开发允许增长——与决策记录 :11 口径一致）。

## 3. 三个消费面措辞前/后对比

### 3.1 requirement-evaluator（Step 0 代码 grep 面纳入）

文件 `skills/business/requirement-evaluator/SKILL.md`：

| 位置 | 前 | 后 |
|---|---|---|
| :78（resolver 状态表） | `code present-unconfirmed（如 lnkcrm）或 code_root null → …不得自动采用观察 checkout`（lnkcrm 作 present-unconfirmed 例——O5-lnkcrm-code 对账后已过时） | 该行保留通用规则、摘除过时例；**新增一行** `code complete + OpenSpec scope 基线（lnkcrm，O5-Q4 后）`：grep 面纳入 `/opt/code/lnkcrm` 的 OpenSpec scope 集（非空、含 member-*/coupon-* 族、锚定集合不钉数量、以实测 `ls` 为准）；scope 命中 = 基线层证据（引用 scope 名）；实现级评估（deep 读码 / P2.5 全码验证）保持 blocked-by-code——scope 基线已纳入；实现级评估解锁待 O5-Q5 |
| :285→:287（Step 0 决策树） | `code_root null / present-unconfirmed（如 lnkcrm）→ 必须用户显式确认 --code-root…` | 同上摘除过时例；**新增分支** `lnkcrm（O5-Q4，2026-10-04 owner include）：grep 面纳入 /opt/code/lnkcrm 的 OpenSpec scope 集（openspec/specs/，实测非空、含 member-*/coupon-*/points-*/merchant-*/platform-*/tenancy 等 scope 族；锚定集合不钉数量，以实测 ls 为准）——scope 命中 = 基线层「该域已覆盖」证据…；实现级评估（deep 读码）保持 blocked-by-code——scope 基线已纳入；实现级评估解锁待 O5-Q5` |

### 3.2 competitor-product-analyzer（status_vs_lanlnk 判定输入纳入）

文件 `skills/business/competitor-product-analyzer/SKILL.md`：

| 位置 | 前 | 后 |
|---|---|---|
| :222-225（authority 状态显式处理） | `code authority 为 present-unconfirmed（如 lnkcrm）时，观察到的 checkout 只作只读证据定位`（过时例） | 通用规则保留、摘除例；**追加** lnkcrm（code authority=complete，O5-lnkcrm-code 对账后）：status_vs_lanlnk 判定输入纳入 lnkcrm OpenSpec scope 基线（`/opt/code/lnkcrm/openspec/specs/` 非空、含 member-*/coupon-* 族、不钉数量、以实测 `ls` 为准）；scope 命中 = 基线层证据（引用 scope 名）；实现级验证保持 blocked——scope 基线已纳入；实现级评估解锁待 O5-Q5 |
| :565+（S1.3 蓝联现状映射） | 无 lnkcrm scope 输入说明 | **新增段**「lnkcrm scope 基线输入（O5-Q4，2026-10-04 owner include）」：判定输入额外纳入 scope 集；命中 scope → 可判 existing/partial 并引用 scope 名；未命中且清单无 existing 证据 → 维持 unknown 进 review；scope 基线已纳入；实现级评估（deep 读码）解锁待 O5-Q5 |

### 3.3 openspec-practice（回写链路产品基线对照纳入）

| 位置 | 前 | 后 |
|---|---|---|
| `skills/meta/openspec-practice/SKILL.md` 定位与上下文（:25 后） | 无 lnkcrm 基线表述 | **新增段**「lnkcrm scope 基线（O5-Q4，2026-10-04 owner include 裁决）」：scope 集合（`/opt/code/lnkcrm/openspec/specs/`，实测非空、含 member-*/coupon-*/points-*/merchant-*/platform-*/tenancy 族）已纳入产品实现基线，回写链路把它作为 lnkcrm 实现基线层对照输入；锚定集合不钉数量、以实测 `ls` 为准；scope 基线已纳入；实现级评估解锁待 O5-Q5（Q4 不自动解锁 Q5） |
| `skills/meta/openspec-practice/references/prd-writeback.md` 回写规则（末条后） | 无 lnkcrm 对照规则 | **新增条**「lnkcrm scope 基线」：目标产品为 lnkcrm 时，PRD gap 状态判断（步骤 6）与「晋升后 pairwise 对账」的 `prd-code` 对照纳入 scope 集；scope 命中 = 「实现基线层已覆盖」证据并引用 scope 名，**不得据此宣称实现级验证通过**；scope 基线已纳入；实现级评估解锁待 O5-Q5 |

## 4. capability evidence/notes 更新清单（status 零变更）

| 文件 | 条目 | 变更 | status |
|---|---|---|---|
| `skills/business/requirement-evaluator/references/adapter-capabilities.yaml` :26-35 | lnkcrm | evidence +1 条（O5-Q4 include，指向决策记录）；notes 重写：实现级 blocked-by-code 保留，新增「O5-Q4 已纳入…scope 基线已纳入；实现级评估（deep 读码）解锁待 O5-Q5——Q4 纳入不自动解锁 Q5」 | `partial`（不变） |
| `skills/business/competitor-product-analyzer/references/adapter-capabilities.yaml` :26-34 | lnkcrm | evidence +1 条（同上）；notes 重写：判定输入已纳入 scope 基线 + 判定规则；实现级判定解锁待 O5-Q5；`evidence/competitors/<vendor>/ 分析结论树未建` 事实保留 | `partial`（不变） |

status 零变更实证：`shared/product_context` 53 套件全绿（含
`test_adapter_capabilities_schema.py` 的 `test_approved_first_version_matrix` /
`test_status_distribution_matches_decision_record` 首版 48 格矩阵钉线——status 值或
分布任何变动都会红）。措辞遵守 schema 钉线：两份 yaml 文本均无 `/opt/code` 绝对路径、
无 hex revision（`test_no_absolute_paths_or_revision_hashes_in_text` 前提）；键集合不变
（仅 evidence 列表项与 notes 字符串）。其余四份 yaml（product-prd-generator /
strategy-brief-generator / pricing-generator / company-intro-generator）**零改动**——
非 Q4 consumer，其 lnkcrm 条目措辞属 O5-Q5 或 O6 范围，不越界。openspec-practice 无
capability 文件（meta skill，六份 yaml 均在 business 下）。

## 5. grep 面冒烟证据（机械证明）

```bash
$ grep -n "/opt/code/lnkcrm" skills/business/requirement-evaluator/SKILL.md
79:| code complete + OpenSpec scope 基线（lnkcrm，O5-Q4 后） | Step 0 的 grep 面纳入
   `/opt/code/lnkcrm` 的 OpenSpec scope 集（`openspec/specs/` 下非空 scope 集合，含
   member-*/coupon-* 等 scope 族；…）…实现级评估解锁待 O5-Q5 |
287:    └── lnkcrm（O5-Q4，2026-10-04 owner include）：grep 面纳入 /opt/code/lnkcrm 的
   OpenSpec scope 集（openspec/specs/，实测非空、含 member-*/coupon-*/points-*/
   merchant-*/platform-*/tenancy 等 scope 族；…）…实现级评估解锁待 O5-Q5
```

措辞 scope 族 ↔ 实测集合对应：member-* 7 / coupon-* 5 / points-* 6 / merchant-* 3 /
platform-* 2 / tenancy 1（`ls /opt/code/lnkcrm/openspec/specs/ | grep -c "^<族>-"` 逐一
验证，全部 >0）——措辞引用的每个族在实测集合中存在；反向不要求（集合允许增长）。

## 6. Q5 边界保留实证

- 边界公式「scope 基线已纳入；实现级评估解锁待 O5-Q5」单行可 grep（`grep -c` 实测）：
  requirement-evaluator SKILL.md ×2、competitor SKILL.md ×1、openspec-practice
  SKILL.md ×1、prd-writeback.md ×1、requirement-evaluator capability yaml ×1、
  competitor capability yaml ×1。
- `blocked-by-code` 语义仍在：requirement-evaluator SKILL.md :79/:287 + capability
  notes（实现级 blocked-by-code（清单 implementation_status 全 unknown））。
- 未解锁行为实证：无任何 deep 读码启用措辞；strategy-brief-generator 零改动（不升深
  盘点）；product-prd-generator 零改动（行为层不动）；resolver/company.yaml/
  30-products/product-registry.yaml 零改动。

## 7. 验证输出（本会话实测）

```bash
$ ls /opt/code/lnkcrm/openspec/specs/ | wc -l
28

$ cd /opt/code/skill/shared/product_context && uv run python -m unittest discover -s tests
Ran 53 tests in 1.765s
OK

$ cd /opt/code/skill/skills/business/product-prd-generator && uv run pytest -q
169 passed, 3 skipped in 36.21s

$ cd /opt/code/skill && bash references/scripts/check_docs_consistency.sh
FAIL: 0 / WARN: 0 / PASS: 33 — RESULT: PASS

$ git diff --check        # 无 whitespace 错误（退出码 0，无输出）
$ git status --short      # 见 §8 允许清单，无清单外条目
$ git diff --name-only    # 6 个 tracked 文件，全部在允许清单内
```

LSP：改动文件均为 Markdown/YAML（无代码符号），`lsp_diagnostics` 不适用；yaml 合法性
由 schema 钉线测试（53 套件内）机械覆盖，markdown 由 check_docs_consistency 的
SKILL.md 解析检查覆盖。

## 8. 允许清单外零改动实证

执行前基线：工作区仅 `?? references/adapter-capability-owner-decision-o5-q4-2026-10-04.md`
（决策记录本身，untracked）+ 0 个 tracked 修改（快照留档 /tmp/opencode/o5q4-pre-status.txt）。

执行后变更全集（tracked M + untracked ??）：

```
 M skills/business/competitor-product-analyzer/SKILL.md                     ← 允许清单 §四.1
 M skills/business/competitor-product-analyzer/references/adapter-capabilities.yaml ← §四.2
 M skills/business/requirement-evaluator/SKILL.md                           ← §四.1
 M skills/business/requirement-evaluator/references/adapter-capabilities.yaml ← §四.2
 M skills/meta/openspec-practice/SKILL.md                                   ← §四.1
 M skills/meta/openspec-practice/references/prd-writeback.md                ← §四.1
 M references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md ← §四.4（末尾追加注记）
?? references/adapter-capability-owner-decision-o5-q4-2026-10-04.md         ← 既有（决策记录）
?? references/adapter-capability-owner-decision-o5-q4-execution-2026-10-04.md ← §四.3（本文件）
```

= 授权 §四 允许清单的精确集合，无超出。

## 9. 冻结项保持（未执行清单）

- O5-Q5 全部内容未解锁：requirement-evaluator 实现级评估（deep 读码）保持
  blocked-by-code；strategy-brief-generator 不升深盘点；prd-gen 行为层不动。
- O6-O11、删除动作（D1 registry 删除 / D2 adapter_status 删除）、定价挂起项
  （pricing-generator lnkcrm 条目未触碰）全部维持冻结。
- 未改：capability status 值、resolver、company.yaml、30-products/**、
  product-registry.yaml、adapter_status、shared 门禁与测试、pricing-generator、docs 仓。
- 未把 scope 数量写死为断言（措辞均为「非空 + 含族 + 以实测 ls 为准」）。
- 版本控制：未 `git add`、未 commit、未 push、未用 `git add -A`——OPC 另行安排提交批。
