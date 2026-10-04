# B2 执行记录 —— product-registry 删除阻塞项 B2（Check 4 对账面迁移）执行记录（2026-10-04）

```text
STATUS: EXECUTED（已批准执行并已完成）
OWNER SIGN-OFF: NOT RECORDED（仅会话授权，无独立签署记录）
SCOPE: B2 only（审计 §4-B2 列明的 Check 4 对账源迁移 + 审计 §7 状态回写）
```

> **记录性质（必读）**：本文件是 B2 的**执行记录**，由 B2 执行会话本身落盘（非事后补录，
> 验证结果均为本会话实测）。它记录的事实是：**用户在 B2 实施前的会话中明确批准执行
> B2**（会话授权，指令原文含「批准执行 B2」及逐条允许/禁止边界）。它**不是**、也
> **不得被引用为**一份独立签署的 owner 批准记录——与
> `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`
> （owner 指令 verbatim 落盘 + `OWNER SIGN-OFF: RECORDED`）那种签署记录不同，
> B2 **不存在**同类型的独立签署证据（见 §3 事实区分）。

---

## 1. 登记字段

```yaml
decision_id: B2
decision_date: "2026-10-04"
record_date: "2026-10-04"
owner: "opc"
owner_basis: "本仓治理约定：一人公司，owner = opc（AGENTS.md；与既有决策记录口径一致）。注意：owner 身份有依据，但 owner 独立签署记录不存在（见 §3）"
status: "已批准执行并已完成"
authorization:
  type: "session_consent"
  source: "B2 实施前用户明确批准「批准执行 B2」的提示词（会话授权；该提示词明文规定『该授权视为本轮会话执行授权，不得自动表述为独立 owner 签署』）"
  corroboration:
    - "references/scripts/check_docs_consistency.sh Check 4 注释块自记「B2 迁移（2026-10-04）…… 用户会话授权」（代码级溯源注记，授权本体即上述会话同意，不构成独立签署文件）"
  not_claimed: "不存在独立签署的 owner 批准记录（无 verbatim 指令落盘、无签署块）"
scope:
  approved: "仅迁移审计 §4-B2 明确列出的消费方（check_docs_consistency.sh Check 4 以 registry 为对账面），对账源改为 company.yaml products（或 resolver 产品清单），保持 WARN 语义"
  basis: "references/product-registry-迁移审计-2026-10-04.md §4-B2 解除条件：对账源改为 company.yaml products（或 resolver 产品清单），保持 WARN 语义"
files_implemented:
  - path: "references/scripts/check_docs_consistency.sh"
    change: "Check 4 对账面自 product-registry.yaml（map 形态 `  <pid>:` grep）改为 company.yaml products（list 形态 `  - id: <pid>`，awk 抽取 products: 块后 grep，块边界含 # --- products-end --- marker 与顶层键，防其他 section 同形 list 误判；[[:space:]]*($|#) 锚定防 lnkchat/lnkchatbi 前缀撞车）。WARN 级别、WARN 文案语义（ontology 静默回落商管提示）、skip 分支语义均保持"
  - path: "references/product-registry-迁移审计-2026-10-04.md"
    change: "§4-B2 行内联「已解除」标记 + B2 状态注记（审计 §7 维护规则要求的状态回写；§1/§2 保持快照原文未重写，B1 同口径）"
  - path: "references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md"
    change: "follow_up 追加 B2 已解除条目（审计 §7：阻塞项状态变化同步至 O3 follow_up；B1 同口径）"
  - path: "references/adapter-capability-owner-decision-b2-execution-2026-10-04.md"
    change: "本执行记录（新增）"
forbidden_unchanged:
  - "B3-B7（全部未批准、未执行，仍为删除阻塞项；其中 B5 覆盖的 AGENTS.md:221 Check 4 机制说明 prose 因 B2 实施现已过时——属 B2 明确排除的文档级迁移，留待 B5/Batch 3 处理）"
  - "registry 数据区（product-registry.yaml 字段零改动；registry 文件保留在仓）"
  - "resolver / models（shared/product_context 运行时语义零改动）"
  - "adapter_status（任何文件均未删除/重命名/改值；O4「兼容保留 + 禁止新增依赖」状态不变）"
  - "六份 capability 文件（adapter-capabilities.yaml 内容零改动）"
  - "B1 已迁移的测试断言（未回流 product-registry.yaml 读取；product-prd-generator 全量测试通过实证）"
  - "company.yaml、30-products/**（docs 仓零改动，合成 WARN 验证使用 /tmp 副本目录）、产品代码"
results:
  source: "B2 执行会话实测（本记录即执行会话，非引用）"
  tests: "product-prd-generator 169 passed / 3 skipped；shared/product_context（含 O4 门禁 test_adapter_status_migration_gate.py 与 capability schema 测试）53 passed"
  script_run: "check_docs_consistency.sh 全量运行与迁移前基线逐项一致（FAIL=0 / WARN=0 / PASS=33，exit 0）"
  synthetic_qa: "合成未注册目录（/tmp 副本 30-products/zzz-fake-prod）触发 WARN 且文案指向 company.yaml products；8 个真实 pid 全部命中；zzz-fake/lnkcha/lnkcre2/lnkchatX/LnKcre 五个负向探针全部正确拒绝（无前缀/大小写撞车）"
  format_checks: "git diff --check 通过"
not_executed:
  - "B3-B7 未批准、未执行（仍阻塞 registry 删除）"
  - "O4 实际迁移与 O5-O11 全部保持冻结"
version_control:
  committed: false
  pushed: false
  this_record: "untracked 新增文件"
  worktree: "工作区保留其他会话既有未提交修改，本轮未回退/未覆盖/未清理/未使用 git add -A"
```

## 2. 日期与 owner 的确认依据

**decision_date = 2026-10-04**：B2 执行会话日期（环境时区 Asia/Shanghai）；与前置链
（O1/O2 Batch 1、O3/Batch 2 audit、B1）同日，用户前置状态指令确认 O1-O4 与 B1 均
已完成。**owner = opc**：依据本仓治理约定（AGENTS.md 一人公司）与既有决策记录一致
口径。授权行为主体（会话中批准执行 B2 的用户）按该治理约定即 repo operator = opc。
**但** owner 身份可确认 ≠ 存在 owner 独立签署记录——后者不存在。

## 3. 事实区分（防误引）

| 命题 | 状态 | 依据 |
|---|---|---|
| 用户明确授权执行 B2（会话同意「批准执行 B2」提示词，含逐条边界） | **成立** | B2 实施前用户会话批准；指令原文明文「该授权视为本轮会话执行授权，不得自动表述为独立 owner 签署」 |
| 存在独立签署的 owner 批准记录（verbatim 指令落盘 / 签署块 / SIGN-OFF: RECORDED） | **不成立，不得声称** | 全仓决策文档族中无 B2 的独立签署记录；O3 记录的签署仅覆盖 O3 / Batch 2（audit-only），B1 记录 §3 已确立同口径区分 |

引述规则：后续任何文档引用 B2 授权时，只能表述为「B2 经用户会话授权执行
（2026-10-04，见本记录）」，不得表述为「B2 经 owner 独立签署批准」。

## 4. 批准范围与实际实施对账

审计 §4-B2 解除条件允许的迁移目标：company.yaml products（或 resolver 产品清单）。
实际实施选择 **company.yaml products**（bash 脚本内可 grep 的唯一产品台账；resolver
为 Python 运行时，不适配本 bash 脚本的最小改动）。对账：

| 审计列出的消费（§1-A4 / §0-职责4） | 迁移至 | 载体文件 |
|---|---|---|
| Check 4 `grep -qE "^  ${pid}:" product-registry.yaml` 对账（缺条目 → WARN） | company.yaml `products:` list 块 `  - id: <pid>` | references/scripts/check_docs_consistency.sh |
| （治理同步）§4-B2 状态回写 | 审计 §4 行标记 + 状态注记 | references/product-registry-迁移审计-2026-10-04.md |
| （治理同步）O3 follow_up B2 状态 | follow_up 追加条目 | references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md |

范围对账结论：实际实施 = 批准范围 + 审计 §7 明文要求的状态同步，无超出。超出范围者
（registry 数据区、registry 删除、resolver、models、adapter_status、capability 文件、
company.yaml、30-products/**、产品代码、公共 capability registry、B3-B7、O4 实际迁移、
O5-O11）均未触碰。

## 5. 实施结果与验证证据（本会话实测）

- 迁移前基线：check_docs_consistency.sh 全量 FAIL=0 / WARN=0 / PASS=33（exit 0）；
- 迁移后全量运行：FAIL=0 / WARN=0 / PASS=33（exit 0）——逐项一致，WARN 语义保持；
- 合成故障 QA（/tmp 副本，未触碰 docs 仓）：未注册目录 → `[WARN] Unregistered
  product dir: 30-products/zzz-fake-prod (company.yaml products 无条目…)`，已注册
  目录 → PASS；
- 正向探针 8/8 命中（lnkcre/lnkcrm/lnkchat/lnkchatbi/lnkreport/lnkvision/lnkgateway/
  lnkwebsite）；负向探针 5/5 正确拒绝（zzz-fake/lnkcha/lnkcre2/lnkchatX/LnKcre）；
- `git diff --check` 通过；
- product-prd-generator：169 passed / 3 skipped；shared/product_context（含 O4 门禁）：
  53 passed——B1 断言未回流、O4 门禁保持通过。

## 6. 遗留与同步事项

1. **B5 范围 prose 残留两处（有意保留，待 Batch 3 处理）**：
   - `AGENTS.md:221` Check 4 机制说明仍描述对账面为 product-registry.yaml（审计 §1-B8 /
     §4-B5 口径，且 B2 批准明文禁止扩大到 B5）；
   - `product-registry.yaml` 头部规则 10(c) 仍把「Check 4 对账面」列为本表迁移期职责
     之一（registry 头部与数据区冻结，B2 禁改，B2 后该句过时）。
   两处本会话均未改，登记于此待 B5 处理。
2. **审计 §1-A4 行保持快照原文**：与 B1 处理 §1-A1/A2/A3 同口径（快照不重写，状态
   由 §4 注记承载）。§7 维护规则要求的 §4/O3 同步已完成。
3. **B3-B7 保持冻结**：registry 删除的其余阻塞项全部未批准、未执行；任何后续解除
   仍需对应独立授权（审计 §4 口径）。
4. **版本控制**：本记录 untracked；全仓未提交、未推送；其他会话工作区修改原样保留。

## 7. 证据路径索引（均已实物核验存在）

- `references/product-registry-迁移审计-2026-10-04.md` §0-职责4、§1-A4、§4-B2、§7
- `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`（O3 签署记录，非 B2 授权来源；follow_up 含 B2 状态条目）
- `references/adapter-capability-owner-decision-b1-execution-2026-10-04.md`（B1 执行记录，本记录的格式与口径先例）
- `references/scripts/check_docs_consistency.sh`（Check 4 当前内容，含「B2 迁移（2026-10-04）」注记）
- `/opt/code/docs/lanlnk/config/company.yaml`（products 块：8 产品 list 形态，含 # --- products-end --- marker；docs 仓，零改动）
