# O5-Q5 执行记录（lnkcrm 实现级评估解锁 / 最小验证集三 skill 行为层启用，2026-10-04）

```text
STATUS: EXECUTED（已批准执行并已完成）
DECISION RECORD: references/adapter-capability-owner-decision-o5-q5-2026-10-04.md
OWNER SIGN-OFF: RECORDED (OPC)（决策记录 :40，授权效力声明 :41）
SCOPE: O5-Q5 only（三 skill 行为层解锁 + 反漂移约束 + Q4 边界注记接续；不触 O6-O11、
       删除动作、定价、resolver/company.yaml/30-products/shared 生产代码）
```

## 1. 执行前授权核验

| 核验项 | 结果 | 出处（决策记录） |
|---|---|---|
| status | `approved` | :8 |
| decision | `unlock（最小验证集启动：实现级评估解锁）` | :9 |
| owner | `OPC（本治理域决策 owner）` | :5 |
| OWNER SIGN-OFF | `RECORDED (OPC)` | :40 |
| 授权效力声明 | 存在（OPC 明确授权即有效，无需独立第三方） | :41-42 |
| unlocked 清单含三 skill | 是（requirement-evaluator / strategy-brief-generator / product-prd-generator，:17-19） | :16-20 |
| anti_drift_constraints 存在 | 是（钉 revision + 漂移警示 + 适用面 = code authority complete 产品，:22-24） | :22-24 |
| explicitly_not_authorized 含 O6-O11/删除动作/定价挂起 | 是（:30-33） | :30-33 |
| 停止条件 | 未触发（owner=OPC 且记录齐全） | — |

前置事实核验：`company.yaml` lnkcrm `code_root: /opt/code/lnkcrm` 已配置
（O5-lnkcrm-code 落地，config/company.yaml:15）；lnkcrm HEAD=`4323b8c9`（活跃开发中，
反漂移约束的现实依据）。

## 2. 三 skill 解锁措辞前/后对比（含反漂移落位）

### 2.1 requirement-evaluator（解除「不得自动用观察 checkout」→ configured 口径）

文件 `skills/business/requirement-evaluator/SKILL.md`：

| 位置 | 前（关键句） | 后（关键句） |
|---|---|---|
| :79（resolver 状态表 lnkcrm 行） | 「实现级评估（deep 读码 / P2.5 全码验证）保持 blocked-by-code。scope 基线已纳入；实现级评估解锁待 O5-Q5」 | 「实现级评估（deep 读码 / P2.5 全码验证）O5-Q5 已解锁（2026-10-04）：lnkcrm 用 company.yaml 配置的 code root（/opt/code/lnkcrm）做实现级验证，按 lnkcre 同等口径，『不得自动用观察 checkout』限制解除（该限制属 present-unconfirmed 时代语义，configured 即 authority），无需再要求显式 --code-root 确认；implementation_status unknown 语义可开始收敛（承诺级→实现级）。反漂移约束：实现级结论必须记录评估时点 revision（git -C /opt/code/lnkcrm rev-parse HEAD）并注明漂移警示……适用面 = code authority complete 的产品（lnkcre、lnkcrm），其余产品维持上一行禁令」 |
| :287（Step 0 决策树 lnkcrm 分支） | 「实现级评估（deep 读码）保持 blocked-by-code——scope 基线已纳入；实现级评估解锁待 O5-Q5」 | 「实现级评估（deep 读码）O5-Q5 已解锁（2026-10-04）：代码根 = company.yaml 配置的 code root（/opt/code/lnkcrm），按 lnkcre 同等口径做实现级验证（P2.5 同理），不再要求显式 --code-root 确认；implementation_status unknown 可开始收敛（承诺级→实现级）；实现级结论必须钉评估时 revision（git -C /opt/code/lnkcrm rev-parse HEAD）+ 漂移警示（活跃开发会让结论过时）」 |

注：:78 通用行（present-unconfirmed / code_root null → 显式 --code-root 确认）**未动**——
lnkcrm 已不在该状态，该行为其余产品保留原禁令（anti_drift 适用面约束的组成部分）。

### 2.2 strategy-brief-generator（盘点深度 unconfirmed → 深盘点可用）

文件 `skills/business/strategy-brief-generator/SKILL.md`：

| 位置 | 前 | 后 |
|---|---|---|
| :254（P4 判定表 null/planned 行） | `code_root null / planned（如 lanlnk 的 lnkcrm）`（过时例——lnkcrm 已 code complete） | `code_root null / planned`（摘除过时例，通用行保留） |
| :264-270（表后新增注记） | 无 lnkcrm 深盘点表述 | 新增 blockquote：「lnkcrm 盘点深度已升级（O5-Q5 已解锁，2026-10-04）：code authority=complete（company.yaml 已配置 code root，O5-lnkcrm-code），盘点深度标注 unconfirmed → 深盘点可用——按 complete 行读源码盘点。反漂移约束：深盘点结论必须记录评估时点 revision（git -C /opt/code/lnkcrm rev-parse HEAD）并注明漂移警示；深盘点适用面 = code authority complete 的产品（lnkcre、lnkcrm），其余产品维持上表各行降级规则」 |

### 2.3 product-prd-generator（--code-root 显式确认收敛为 configured，登记性措辞）

文件 `skills/business/product-prd-generator/SKILL.md`：

| 位置 | 前 | 后 |
|---|---|---|
| :14（frontmatter compatibility） | `Reads code from an explicit --code-root (LnkCRE retains its historical default; other products must provide an explicit code root)` | 追加 lnkcrm 从句：`lnkcrm's code root is configured in company.yaml since O5-lnkcrm-code, so --code-root explicit confirmation has converged to configured — registered per O5-Q5, 2026-10-04; other products must provide an explicit code root` |

事实面（company.yaml code_root 配置 + `resolve_code_root('lnkcrm')` 免显式覆盖直接解析）
随 O5-lnkcrm-code 自然达成（backlog §3.1 O5-Q5 行「当前状态」注记）；本轮仅 skill 层
登记，无行为代码改动（shared 生产代码零改动，见 §7）。

## 3. Q4 边界注记接续（「待 O5-Q5」→「O5-Q5 已解锁」，预期接续非语义重写）

Q4 落地注记实测 6 文件 8 处（Q4 执行记录 §6 计数为 5 文件口径，实测 grep 全集如下；
授权 §二.4「5 文件约 6 处」为约数，本轮按 0 命中闸门全覆盖接续）：

| 文件:行 | 接续方式 |
|---|---|
| requirement-evaluator SKILL.md :79 / :287 | 随 §2.1 解锁编辑自然接续（两处均含「O5-Q5 已解锁（2026-10-04）」） |
| requirement-evaluator adapter-capabilities.yaml :36 | notes 随 §4 更新（含「实现级评估 O5-Q5 已解锁（2026-10-04）」） |
| competitor-product-analyzer SKILL.md :228-230 | 「保持 blocked（本 skill 未入 Q5 最小验证集）。scope 基线已纳入；实现级评估 O5-Q5 已解锁（2026-10-04，解锁集 = requirement-evaluator / strategy-brief-generator / product-prd-generator）」——判定输入语义零改动 |
| competitor-product-analyzer SKILL.md :578-579 | 「实现级评估（deep 读码）O5-Q5 已解锁（2026-10-04；解锁集 = 最小验证集三 skill，本 skill 不在集内）」 |
| competitor-product-analyzer adapter-capabilities.yaml :35 | notes 边界公式接续（同上口径，判定规则与「分析结论树未建」事实零改动） |
| openspec-practice SKILL.md :31-32 | 「实现级评估 O5-Q5 已解锁（2026-10-04，解锁集 = 最小验证集三 skill——…）」 |
| openspec-practice references/prd-writeback.md :107 | 「实现级评估 O5-Q5 已解锁（2026-10-04，解锁集 = 最小验证集三 skill）」——前句 Q4 规则「不得据此宣称实现级验证通过」保留 |

competitor / openspec-practice 非 Q5 consumer（决策记录 consumer_ids 仅三 skill，
:14）：其注记接续为闸门状态登记 + 解锁集显名，不宣称自身实现级行为启用（不越权扩大
解锁面）。Q4 已落地的 grep 面 / 判定输入 / 回写对照语义全部零重写。

## 4. capability 变更清单

| 文件 | 条目 | status | evidence/notes 变更 |
|---|---|---|---|
| requirement-evaluator adapter-capabilities.yaml | lnkcrm | **partial（不变）** | evidence +1（O5-Q5 unlock，指向决策记录）；notes 重写：实现级已解锁 + 反漂移（钉 revision + 漂移警示 + 适用面）+ scope 基线保留 |
| strategy-brief-generator adapter-capabilities.yaml | lnkcrm | **partial → implemented** | evidence +1（O5-Q5 解锁，深盘点可用）；notes 对齐 lnkcre implemented 模式 + 反漂移 |
| product-prd-generator adapter-capabilities.yaml | lnkcrm | **onboarding（不变）** | evidence +1（O5-Q5 登记，--code-root 收敛为 configured）；notes 重写：code root 已配置 + resolve_code_root 免显式覆盖 + 登记性措辞 + 无运行先例（onboarding 语义不变） |
| competitor-product-analyzer adapter-capabilities.yaml | lnkcrm | partial（不变） | 仅 notes 边界注记接续（§3） |

status 变更依据（strategy-brief×lnkcrm partial→implemented，唯一一处）：

1. 该 yaml 头部 implemented 语义注释（方案 B 红线下）：「本 skill 只消费公司/产品事实
   （company.yaml 台账 + resolver 状态）……implemented 表达的是『盘点维度』可用」——
   implemented 不要求运行先例，只要求维度可用；
2. 唯一 partial 理由「深读码需 owner 确认（O5 pending，冻结）」已被 Q5 裁决明文解除
   （「lnkcrm 盘点深度 unconfirmed → 深盘点可用」，决策记录 :18）；
3. 与 lnkcre（implemented，「盘点维度 implemented（深盘点可用）」）同构。

requirement-evaluator×lnkcrm 维持 partial 的依据：解锁是行为层授权，非运行证据
（「未经证据不得标 implemented」红线）；implementation_status 全 unknown 的收敛尚未
执行（决策记录 :17 明文「可开始收敛」——过程未完成）；lnkcre 的 implemented 有已演练
链路证据支撑，lnkcrm 实现级验证无运行先例。product-prd-generator×lnkcrm 维持
onboarding 的依据：Q5 对 prd-gen 明文「登记性措辞」（决策记录 :19）；onboarding 语义 =
「无运行先例，首次真实使用前不得宣称支持」（决策文档 :90），本轮无 generate /
coverage-validate 运行，语义未变。

钉线同批更新（`shared/product_context/tests/test_adapter_capabilities_schema.py`）：

- `EXPECTED_MATRIX["strategy-brief-generator"]["lnkcrm"]`: `"partial"` → `"implemented"`（:143）；
- `EXPECTED_DISTRIBUTION`: `implemented: 12→13`、`partial: 15→14`（:151-152）；
- 矩阵定义处追加 3 行修订注释（owner 决策出处，供审计追溯 pin 漂移）。

前后值汇总（供 OPC 复核）：strategy-brief×lnkcrm **partial → implemented**（唯一
status 变更）；requirement-evaluator×lnkcrm partial（不变）；prd-gen×lnkcrm
onboarding（不变）；competitor×lnkcrm partial（不变）。分布：implemented 12→13 /
partial 15→14，其余四态不变。

## 5. grep 冒烟证据（机械证明）

```bash
$ rg -n "待 O5-Q5" skills/
（0 命中，退出码 1——全部接续为已解锁）

$ rg -l "O5-Q5 已解锁" skills/   # 9 文件，覆盖全部原注记 6 文件 + 三 skill 新措辞落点
skills/meta/openspec-practice/references/prd-writeback.md
skills/meta/openspec-practice/SKILL.md
skills/business/requirement-evaluator/references/adapter-capabilities.yaml
skills/business/requirement-evaluator/SKILL.md
skills/business/competitor-product-analyzer/references/adapter-capabilities.yaml
skills/business/competitor-product-analyzer/SKILL.md
skills/business/strategy-brief-generator/references/adapter-capabilities.yaml
skills/business/strategy-brief-generator/SKILL.md
skills/business/product-prd-generator/references/adapter-capabilities.yaml
（prd-gen SKILL.md :14 为英文登记措辞 "registered per O5-Q5, 2026-10-04"，同义落位）

$ rg -n "blocked-by-code" skills/business/requirement-evaluator/
（0 命中——lnkcrm 行的 blocked-by-code 措辞已随解锁移除；:78 通用禁令行不含该词、未动）
```

## 6. 验证输出（本会话实测）

```bash
$ cd /opt/code/skill/shared/product_context && uv run python -m unittest discover -s tests
Ran 53 tests in 2.417s
OK                      # 钉线同批更新后仍 53 OK（矩阵/分布/文本禁令/schema 全绿）

$ cd /opt/code/skill/skills/business/product-prd-generator && uv run pytest -q
169 passed, 3 skipped in 36.88s

$ cd /opt/code/skill && bash references/scripts/check_docs_consistency.sh
FAIL: 0 / WARN: 0 / PASS: 33 — RESULT: PASS

$ git diff --check      # 退出码 0，无 whitespace 错误
$ git status --short / git diff --name-only   # 见 §7，全部在允许清单内

LSP：改动 .py 唯一文件 test_adapter_capabilities_schema.py → error 级 0 诊断。
（其余改动为 Markdown/YAML；yaml 合法性由 53 套件 schema 钉线机械覆盖）
```

## 7. 允许清单外零改动实证

执行前基线（快照 /tmp/opencode/o5q5-pre-status.txt）：Q4 批次 7 M + 3 ??（q4 决策 /
q4 执行 / q5 决策），与本轮 §一取证一致。执行后变更全集（tracked M 12 + untracked 4）：

```
 M references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md ← §四.5（Q4 批次文件 + Q5 末尾注记）
 M shared/product_context/tests/test_adapter_capabilities_schema.py            ← §四.3（status 变更钉线同批）
 M skills/business/competitor-product-analyzer/SKILL.md                        ← §二.4（Q4 批次文件注记接续）
 M skills/business/competitor-product-analyzer/references/adapter-capabilities.yaml ← §二.4（同上）
 M skills/business/product-prd-generator/SKILL.md                              ← §四.1
 M skills/business/product-prd-generator/references/adapter-capabilities.yaml   ← §四.2
 M skills/business/requirement-evaluator/SKILL.md                              ← §四.1（Q4 批次文件 + 解锁）
 M skills/business/requirement-evaluator/references/adapter-capabilities.yaml   ← §四.2（同上）
 M skills/business/strategy-brief-generator/SKILL.md                           ← §四.1
 M skills/business/strategy-brief-generator/references/adapter-capabilities.yaml ← §四.2
 M skills/meta/openspec-practice/SKILL.md                                      ← §二.4（Q4 批次文件注记接续）
 M skills/meta/openspec-practice/references/prd-writeback.md                   ← §二.4（同上）
?? references/adapter-capability-owner-decision-o5-q4-2026-10-04.md            ← 既有（Q4 批次）
?? references/adapter-capability-owner-decision-o5-q4-execution-2026-10-04.md  ← 既有（Q4 批次）
?? references/adapter-capability-owner-decision-o5-q5-2026-10-04.md            ← 既有（决策记录）
?? references/adapter-capability-owner-decision-o5-q5-execution-2026-10-04.md  ← §四.4（本文件）
```

其中 7 个 M 为 Q4 批次既有修改文件（本轮在其上叠加注记接续/解锁措辞），5 个 M + 1 个 ??
为本轮新增，= 授权 §四 允许清单的精确集合，无超出。未触碰：resolver /
shared 生产代码（仅测试钉线）/ company.yaml / 30-products/** / product-registry.yaml /
adapter_status / pricing-generator / docs 仓 / 业务系统代码仓。

## 8. 冻结项保持（未执行清单）

- O6-O11 全部未执行（O6 正祥 CRM 定价归属、O7-O11 各项维持 frozen）。
- 删除动作（D1 registry / D2 adapter_status 字段）、O4⑤、lnkreport 定价数值（挂起）全部冻结。
- Q4 已落地的 grep 面 / 判定输入 / 回写对照语义零重写（仅边界注记接续，§3）。
- competitor-product-analyzer / openspec-practice / pricing / company-intro 的实现级行为
  未解锁（Q5 consumer_ids 之外；competitor 注记明示「未入最小验证集」）。
- 版本控制：未 git add、未 commit、未 push、未用 git add -A——OPC 统一安排 Q4+Q5 提交批。
