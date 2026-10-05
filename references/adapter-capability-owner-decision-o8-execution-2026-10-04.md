# O8 执行记录（驳回标准价登记后的语义对齐：随单赠送策略口径，行为零改动，2026-10-04）

```text
STATUS: EXECUTED（已授权执行并已完成）
DECISION RECORD: references/adapter-capability-owner-decision-o8-2026-10-04.md
OWNER SIGN-OFF: RECORDED (OPC)（决策记录 :38，授权效力声明 :39）
SCOPE: O8 only（语义对齐 + capability 收口；不写 pricing-basis.yaml / docs 仓；
       不触 env 读取逻辑、默认值行为、LNKCHATBI_DATA 结构、其他产品条目、
       O6/O7-*/O9/O10-*/O11、删除动作、lnkreport 定价；未提交、未推送）
```

## 1. 执行前授权核验

| 核验项 | 结果 | 出处（决策记录） |
|---|---|---|
| status | `decided` | :8 |
| decision | `rejected-registration（驳回标准价登记；lnkchatbi 不设标准价，维持随单赠送/打包）` | :9 |
| owner | `OPC（本治理域决策 owner）` | :5 |
| OWNER SIGN-OFF | `RECORDED (OPC)` | :38 |
| 授权效力声明 | 存在（OPC 明确授权即为有效所有者授权，无需独立第三方签署） | :39 |
| strategy_semantics 含行为零改动 | 是（「仅注释/帮助/备注文本，env 覆盖逻辑与默认行为零改动」） | :17 |
| forbidden_changes 含改 env 读取逻辑或默认值行为 | 是（:33） | :30-34 |
| 停止条件 | 未触发（owner=OPC 且记录齐全） | — |

## 2. generate_quote.py 文案前/后（行为零改动实证）

| 位置 | 前 | 后 |
|---|---|---|
| :621-622（build_lnkchatbi_data docstring 帮助文本） | 「定价：默认战略赠送（首年 0 / 次年 0，用于云泰等试水/赠送场景），可通过环境变量覆盖：」 | 「定价：随单赠送策略（O8 裁决 2026-10-04 rejected-registration）——默认 0/0 为设计语义（非占位待定价）；打包/单独定价经环境变量人工输入：」 |
| :714（service_notes 第 5 条报价备注） | `"5. 定价：本次报价" + note + "，可通过环境变量 LNKCHATBI_PRICE_Y1/Y2 覆盖；"` | `"5. 定价：本次报价" + note + "（随单赠送策略，O8 裁决 2026-10-04）；打包/单独定价经环境变量 LNKCHATBI_PRICE_Y1/Y2 人工输入；"` |

**行为零改动实证**（git diff，该文件执行前为 clean 基线，diff 全量归本轮）：
仅两个 hunk——`@@ -618,8 +618,8 @@`（docstring 帮助文本行）与 `@@ -711,7 +711,7 @@`
（:714 备注字符串行）。`_price()`（:629-637）、env 读取 `p1/p2`（:639-640）、
`free`/`note` 构造（:641-646）、LNKCHATBI_DATA 数据结构（:648-719）全部未触。

测试断言面核查：pricing-generator tests 无帮助文本/:714 备注文案断言
（grep「战略赠送/LNKCHATBI_PRICE/可通过环境变量/本次报价」仅命中源文件与
capability yaml，无测试命中）——无需断言字符串更新，行为断言未动。

## 3. capability 条目变更（pricing-generator × lnkchatbi）

文件 `skills/business/pricing-generator/references/adapter-capabilities.yaml` :45-55。

**status：partial → implemented**（升级判定理由）：

1. 决策记录 :28 的三项条件全满足：结构在位（LNKCHATBI_DATA + env 机制，
   evidence 第 1 条）；默认 0 为设计语义（O8 裁决 :18「现状机制即设计语义，非缺口」）；
   完整报价能力（随单赠送默认 0/0 可直接出单，实证 = 云泰荔园已交付报价单
   LnkChatBI 0/0 战略赠送；打包/单独定价 env 通道在位）。
2. yaml 自身语义先例：lnkcre implemented 仍注「私有化模式定价待补」——
   implemented = 主线报价能力在既定口径下完整，非「零待办」。
3. 维持 partial 反而语义错误：原 partial 理由「标准定价未登记（O8 pending 批准后
   可 partial→implemented）」的前提（登记建设路线）已被 rejected-registration 撤销，
   owner 已裁决现状机制即终态设计。

evidence 前/后：

| 前 | 后 |
|---|---|
| `generate_quote.py LNKCHATBI_DATA 结构 + LNKCHATBI_PRICE_Y1/Y2 环境变量` | `generate_quote.py LNKCHATBI_DATA 结构 + LNKCHATBI_PRICE_Y1/Y2 环境变量（默认 0/0 = 随单赠送设计语义；打包/单独定价经 env 人工输入）` |
| `设计包 §3.3.C` | `O8 裁决 rejected-registration（references/adapter-capability-owner-decision-o8-2026-10-04.md）：不登记标准价，现状机制即设计语义非缺口` |
| （无第三条） | `云泰荔园报价单 LnkChatBI 首年/次年 0/0 战略赠送实证（lanlnk/out/proposals/广州云泰荔园/报价单_MI+LnkChatBI+接口_SAAS_云泰park荔园_20260806.xlsx）` |

notes 前/后：

| 前 | 后 |
|---|---|
| `结构在位、标准定价未登记（env 默认 0，每次人工输入；pricing-basis.yaml 只有费率无产品定价）；O8（pending）批准后可 partial→implemented。` | `O8 已裁决（2026-10-04 rejected-registration）：随单赠送/打包策略，env 人工输入为设计语义非缺口；pricing-basis.yaml 不设 lnkchatbi 定价段（费率三键不动）。` |

`verified_at` 保持 `"2026-10-04"`（与 O8 决策日期及 schema 测试 AUDIT_DATE 钉值一致，
无漂移）；`owner: opc` 不变。

## 4. 钉线同批更新（status 变更原子化）

| 钉线 | 前 | 后 |
|---|---|---|
| `shared/product_context/tests/test_adapter_capabilities_schema.py` EXPECTED_MATRIX `pricing-generator.lnkchatbi` | `"partial"` | `"implemented"` |
| 同上 EXPECTED_DISTRIBUTION `implemented` / `partial` | `13` / `14`（O5-Q5 在途值） | `14` / `13` |
| 同上矩阵修订溯源注释 | 无 O8 条目 | 新增 O8 修订注释（:87-90，随 O5-Q5 注释同款式） |
| `skills/business/pricing-generator/tests/test_lnkreport_data.py` test_capability_other_products_untouched 八产品全景钉 `"lnkchatbi"` | `"partial"` | `"implemented"`（docstring 补 O8 同批修订说明） |

注：schema 测试 diff 对 HEAD 显示 12/15→14/13，系 O5-Q5 在途修订（12/15→13/14）
与本轮 O8（13/14→14/13）叠加视图；本轮增量前值 = 13/14。pricing 本地八产品
全景钉（test_lnkreport_data.py:210-223，:186 注释明示「与 yaml 修改同批原子化」）
为 status 变更的第三处必同批钉线，属授权允许清单「测试断言同批」范围；行为断言未动。

## 5. 验证输出

```text
cd /opt/code/skill/skills/business/pricing-generator && uv run pytest -q
→ 19 passed in 0.39s                        # 不回归 ✓

cd /opt/code/skill/shared/product_context && uv run python -m unittest discover -s tests
→ Ran 53 tests in 1.544s / OK               # 含 strict 语法解析 + 矩阵/分布钉 + 禁绝对路径/禁 hash ✓

cd /opt/code/skill && bash references/scripts/check_docs_consistency.sh
→ FAIL: 0 / WARN: 0 / PASS: 33 / RESULT: PASS ✓

git diff --check → rc=0（无空白错误）✓
```

行为零改动：pytest 19 passed 全绿（报价生成、merge、拒生成等行为断言未动未破）；
generate_quote.py diff hunk 仅落 docstring/:714 备注行（§2 实证）。

## 6. 允许清单外零改动实证

本轮触碰文件（全部在授权允许清单内）：

1. `skills/business/pricing-generator/generate_quote.py`（清单四.1）
2. `skills/business/pricing-generator/references/adapter-capabilities.yaml`（清单四.2）
3. `shared/product_context/tests/test_adapter_capabilities_schema.py`（清单四.3，status 变更钉线同批）
4. `skills/business/pricing-generator/tests/test_lnkreport_data.py`（清单四.1 测试断言同批：八产品全景钉中 lnkchatbi 单值 + docstring 注记）
5. `references/adapter-capability-owner-decision-o8-execution-2026-10-04.md`（清单四.4，本文件新增）
6. `references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md`（清单四.5，末尾追加 §11 最小注记）

Q4+Q5 在途改动原样共存、未触碰（仅 schema 测试与 backlog 盘点两文件在既有在途
修改之上叠加本轮允许清单内增量，增量 hunk 见 §4）：competitor-product-analyzer
SKILL+yaml、product-prd-generator SKILL+yaml、requirement-evaluator SKILL+yaml、
strategy-brief-generator SKILL+yaml、openspec-practice SKILL+prd-writeback、
o5-q4/q5 决策与执行记录 4 个 untracked——diff 内容未动。

## 7. 冻结维持与未提交声明

- pricing-basis.yaml / docs 仓：零写入（本仓 diff 范围外，未越仓）。
- env 读取逻辑、默认值行为、LNKCHATBI_DATA 结构：零改动（§2 实证）。
- 未套用 lnkchat/lnkcre 价格；未改其他产品 capability 条目（八产品全景钉同批验证通过）。
- O6/O7-*/O9/O10-*/O11、删除动作、lnkreport 定价：**维持冻结**（O8 记录 :43 明示本记录不构成其批准）。
- 未使用 git add -A；**未提交、未推送**（OPC 统一安排 Q4+Q5+O8 提交批）。
