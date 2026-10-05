# PRICING-FINAL 执行记录 —— lnkreport / lnkvision 不单独售卖终裁落地（2026-10-05）

decision_basis: references/adapter-capability-owner-decision-pricing-final-2026-10-05.md
status: executed（本文记录 = PRICING-FINAL approved_changes 全部落地；含同批 O10 Stage-2b 收口）
executor: orchestrator（按 OPC 授权执行；OPC 身份依据决策记录 :44-45）
owner_sign_off: "OWNER SIGN-OFF: RECORDED (OPC)（决策记录原文 :43）"

## 1. 闸门核验（决策记录 :34-39 forbidden 生效前置）

| 项 | 结果 |
|---|---|
| 决策记录存在 | ✓ references/adapter-capability-owner-decision-pricing-final-2026-10-05.md |
| status / decision / owner | decided / not-sold-independently / OPC ✓ |
| OWNER SIGN-OFF | RECORDED (OPC)（:43）✓ |
| resolves 覆盖 | O7-report deferred「定价数值」+ O7-vision deferred「定价数值」+ backlog 定价挂起 ✓ |
| forbidden 含「填任何独立单价」 | ✓（:35 Y1/Y2 永不登记；:36 结构/拒单行为/白名单注释性更新除外；:39 禁 add-A/推送） |
| docs 事实 | ✓ git -C /opt/code/docs log --oneline -1 = e15274e（O10 Stage-2 入库在位，兼作 O10 Stage-2b 闸门） |

## 2. capability 两格 + shared 钉线（前后值）

### 2.1 矩阵两格（pricing-generator/references/adapter-capabilities.yaml）

| 格 | 前（工作树现值） | 后 |
|---|---|---|
| pricing × lnkreport | **onboarding** | **not-applicable**（evidence 增补终裁条目：PRICING-FINAL 2026-10-05 decided / not-sold-independently，沿 O7-chat 先例；DATA 结构保留 + 拒单行为即策略执行；notes 同步改判关闭表述） |
| pricing × lnkvision | **onboarding** | **not-applicable**（同上） |

verified_at/owner 保持 2026-10-04 / opc（schema AUDIT_DATE 契约）。既有 O7-report Phase 2 /
O7-vision 证据条目原文保留（结构出处不灭失），终裁条目追加。

### 2.2 schema 钉线（shared/product_context/tests/test_adapter_capabilities_schema.py，同批；含 O10 Stage-2b 合并调整）

| 钉线 | 前（工作树现值） | 后 | 归属 |
|---|---|---|---|
| EXPECTED_MATRIX["pricing-generator"]["lnkreport"] | "onboarding" | **"not-applicable"** | PRICING-FINAL |
| EXPECTED_MATRIX["pricing-generator"]["lnkvision"] | "onboarding" | **"not-applicable"** | PRICING-FINAL |
| EXPECTED_MATRIX["company-intro-generator"]["lnkreport" / "lnkvision"] | "onboarding" ×2 | **"implemented"** ×2 | O10 Stage-2b |
| EXPECTED_DISTRIBUTION["implemented"] | 14 | **16**（+2） | O10 Stage-2b |
| EXPECTED_DISTRIBUTION["onboarding"] | 9 | **5**（−4：−2 Stage-2b / −2 PRICING-FINAL） | 两批合并 |
| EXPECTED_DISTRIBUTION["not-applicable"] | 10 | **12**（+2） | PRICING-FINAL |
| 修订注记 | 止于 O10 Stage-1 | O10 注记更新为两阶段收口 + 新增 PRICING-FINAL 修订块 | 两批合并 |

合计校验：16+13+5+1+12+1 = 48 ✓（6 消费方 × 8 产品）。

### 2.3 pricing 本地全景钉（tests/，同批原子化）

- test_lnkreport_data.py：test_capability_lnkreport_onboarding → **test_capability_lnkreport_not_applicable**
  （status 断言 onboarding→not-applicable；新增终裁记录 + not-sold-independently evidence 断言；
  既有 LNKREPORT_DATA / phase2-report 断言保留）；全景钉 map 两格 onboarding→not-applicable + 注记。
- test_lnkvision_data.py：test_capability_lnkvision_onboarding → **test_capability_lnkvision_not_applicable**
  （同构；既有 LNKVISION_DATA / o7-vision / customer-facing 断言保留）。
- 计数不变：31 passed（重命名 2 项、新增断言 2 组、无增删测试函数）。

## 3. 注释性措辞更新（行为零改动）

范围：generate_quote.py 与两测试文件中 lnkreport/lnkvision 相邻的「待定价」措辞 →
「不单独售卖（终裁 2026-10-05），无独立标准价」。diff hunk 落点逐类：

| 类别 | 落点 | hunk 数 | 性质 |
|---|---|---|---|
| 块头注释 | LNKREPORT_DATA / LNKVISION_DATA 金额纪律 + 终裁注记（含决策记录路径引用） | 4 | 纯注释 |
| pricing_status | 两 DATA 的 status 元数据串 | 2 | 静态数据（备注性；仅被拒绝门与内容断言消费） |
| 行尾备注 | 「；待定价」行尾 ×15 + 「单价与次年费待定价」×2 | 17 | 静态数据（八列第 8 列备注） |
| 服务说明 | service_notes 末条 ×2（lnkreport 第 4 条 / lnkvision 第 5 条） | 2 | 静态数据（备注性） |
| 测试文案断言 | pricing_status/notes/行备注断言 ×6 + 相应 docstring/函数名（marked_pending→marked_not_sold） | 8 | 内容断言 + 帮助文本（行为断言零触碰） |

**行为边界（零改动实证）**：build_lnkreport_data / build_lnkvision_data 两函数体内
（docstring 中的机制描述 + sys.exit 拒绝消息文本）零 hunk——拒绝消息为运行时输出 = 行为面，
PRICING-FINAL 仅授权注释性更新；行为断言 `assert "待定价" in msg and "拒绝" in msg`
（两测试文件各 1 处）原样保留并通过。LNKCHATBI 相关注释（generate_quote.py :794）非本批目标，未触碰。
数据结构（四段八列、RATIFIED_ZEROS 白名单、汇总行、模块清单）、控制流、CLI、env 机制：零 hunk。

## 4. 拒单行为复测（策略执行实证，2026-10-05 实跑）

环境：COMPANY_BASE=/opt/code/docs/lanlnk，uv run python generate_quote.py。

| 场景 | 输出 | 退出码 |
|---|---|---|
| --product LNKREPORT（单卖） | [REFUSED] LnkReport 报价结构已落地…金额留空/待定价状态下拒绝生成报价单，绝不编造数值 | 1 |
| --product LNKVISION（单卖） | [REFUSED] LnkVision 报价结构已落地…拒绝生成报价单，绝不编造数值 | 1 |
| --product MI,LNKREPORT（组合） | [REFUSED] 同 LNKREPORT（写盘前拒绝） | 1 |
| --product MI,LNKVISION（组合） | [REFUSED] 同 LNKVISION（写盘前拒绝） | 1 |
| --product LNKREPORT,LNKVISION（组合） | [REFUSED] 同 LNKREPORT（首个无价产品即拒） | 1 |

零写盘复验：全部场景运行后无任何 .xlsx 新产物；git status 无新增未跟踪产物。

## 5. backlog 终态注记

backlog-inventory 追加 §18：lnkreport / lnkvision 定价（挂起）→ **decided-not-sold-independently
（关闭）**；O10（report + vision）→ Stage-2 收口；「其余维持冻结」清空（治理主线全部收口，
唯一剩余 = 终推）。O7-report / O7-vision 决策记录 deferred「定价数值」项由本终裁终结（改判关闭，
非填数关闭）。

## 6. 验证（终局，全绿）

| 项 | 结果 |
|---|---|
| shared/product_context unittest | Ran 52 tests — OK |
| product-prd-generator pytest | 169 passed, 3 skipped |
| pricing-generator pytest | 31 passed（计数与 O10 批一致：重命名 2 项、无增删；文案断言更新不改变计数） |
| check_docs_consistency.sh | FAIL=0 / WARN=0 / PASS=33（RESULT: PASS） |
| git diff --check | CLEAN |

## 7. 未做事项（与 PRICING-FINAL forbidden :34-39 对账）

- 未填任何单价/金额（Y1/Y2 未登记）；未写 pricing-basis.yaml（docs 仓零写入）；
- 未改 LNKREPORT_DATA / LNKVISION_DATA 结构、拒单行为、RATIFIED_ZEROS 白名单
  （build_* 函数体零 hunk，§3 行为边界实证）；未从任何产品复制价格；
- 未改 resolver / shared 生产代码（钉线测试除外）/ company.yaml / 30-products/** / 其他 capability 条目
  （pricing 其余 6 格、company-intro 其余 6 格零触碰——后者仅 O10 Stage-2b 授权范围内两格）；
- 未 git add -A、未推送（收官提交按授权另批执行，pathspec 逐一列名）。
