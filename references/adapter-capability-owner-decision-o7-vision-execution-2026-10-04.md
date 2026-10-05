# O7-vision 执行记录 —— lnkvision 面客定判 + 报价基线结构建设（金额留空，定价挂起）（2026-10-04 裁决 / 2026-10-05 执行）

```text
STATUS: COMPLETED（LNKVISION_DATA 结构落地 + capability unsupported→onboarding + evidence/notes
更新；shared 钉线矩阵格与分布同批（unsupported 4→3 / onboarding 6→7）+ pricing 本地八产品
全景钉同批；pricing pytest 19→31 passed；shared 53 tests OK；consistency 0/0/33）
RESIDUAL: 模块分组草案待 OPC 复核（§3.2 八项，草案默认生效中）；定价数值挂起（待 OPC 提供）
OWNER SIGN-OFF: RECORDED (OPC)（引用自决策记录 :43，非本文件自立）
AUTHORIZATION: references/adapter-capability-owner-decision-o7-vision-2026-10-04.md
SCOPE: O7-vision only —— 金额一律留空待定价；不写 pricing-basis.yaml；不改 30-products/**
（只读）/ resolver / company.yaml / registry / shared 生产代码（钉线除外）/ 其他产品条目；
不构成 O10-* / O11、删除动作、lnkreport 定价的批准
```

> **记录性质**：本文件是 O7-vision 的执行记录，由执行会话落盘，验证结果均为本会话实测。
> 它不构成 O10-* / O11、任何删除动作、lnkreport/lnkvision 定价数值的批准。

## 1. owner 决策记录核验（执行前，当前磁盘版本复核）

对象：`references/adapter-capability-owner-decision-o7-vision-2026-10-04.md`。

| 核验项 | 要求 | 实测（文件:行） | 结果 |
|---|---|---|---|
| status | decided | `:8 status: decided` | ✅ |
| decision | customer-facing | `:9 decision: customer-facing（lnkvision 为独立面客产品；启动 pricing 报价基线建设——结构先行、金额留空、定价数值挂起，完全复用 O7-report 已核定模式）` | ✅ |
| owner | OPC | `:5 owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）` | ✅ |
| OWNER SIGN-OFF | RECORDED (OPC) | `:43 OWNER SIGN-OFF: RECORDED (OPC)` | ✅ |
| 授权效力声明 | 存在 | `:44 授权效力声明: OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署` | ✅ |
| approved_changes 含 LNKVISION_DATA | 是 | `:19-21 generate_quote.py：新增 LNKVISION_DATA（对齐 LNKREPORT_DATA 模式：四段结构、八列行结构、金额一律留空/None + 「待定价」标记、RATIFIED_ZEROS 白名单外零值、无数值时显式拒绝）+ CLI 接线 + 配套最小测试` | ✅ |
| approved_changes 含 capability onboarding | 是 | `:16-17 pricing capability lnkvision 条目：status unsupported → onboarding…+ evidence/notes` | ✅ |
| approved_changes 含钉线同批 | 是 | `:18 shared 钉线同批：EXPECTED_MATRIX pricing×lnkvision + EXPECTED_DISTRIBUTION（unsupported −1 / onboarding +1），报前后值` | ✅ |
| forbidden 含填单价/金额禁令 | 是 | `:36 填任何具体单价/金额（pricing-basis.yaml 费率引用除外）；从 lnkcre/lnkchat/其他产品复制价格` | ✅ |
| 边界声明 | 存在 | `:48 本记录仅覆盖 O7-vision；不构成 O10-* / O11、删除动作或 lnkreport 定价的批准` | ✅ |

**前置顺序核验**：SKILL-COMMIT-BATCH-5 治理提交批已落库（git log HEAD `b74a60c` O9 收口及其前序批次）；O7-chat 落地完成（执行记录 `references/adapter-capability-owner-decision-o7-chat-execution-2026-10-04.md` STATUS: COMPLETED，shared 53 OK / pricing 19 passed / consistency 0/0/33；工作区增量与其 §5.2 逐行一致，按设计未提交待统一提交批）。

**核验结论：通过。** 按批准的变更执行；核验失败即停止的中止条件未触发。

## 2. 裁决内容（未扩大）

- **O7-vision = customer-facing**：lnkvision 为独立面客产品；本轮建**结构**不建**价格**（金额一律留空/None + 「待定价」标记）。
- 完全复用 lnkreport 已核定模式（LNKREPORT_DATA 先例，`d9c5352` 已落库）：四段结构（核心模块/第三方对接/实施/售后）+ 八列行 + RATIFIED_ZEROS 白名单外零值 + 无数值显式拒绝。
- capability：pricing×lnkvision unsupported → onboarding（定价数值未登记前不升 implemented）。
- 定价数值挂起；pricing-basis.yaml 不写；30-products/** 只读取证。

## 3. 模块分组草案（待 OPC 复核；沿 O7-report G4 模式）

### 3.1 分组方法

功能清单 15 个功能域按业务域归并到报价模块，保留「功能域 → 模块 → 行号」完整审计链（§3.3）。
canonical 输入：`/opt/code/docs/lanlnk/30-products/lnkvision/prd/功能清单.md`（全 31 行：
existing 18 / partial 3 / missing 6 / explicitly-not-do 4，行数审计见 §3.3 求和闭合）。

### 3.2 模块分组总表（模块 × 条目数 × 必选/可选草案）

| 编号 | 报价模块（草案命名） | 来源功能域 | existing 条目数 | 代表性条目（功能清单.md:行） | 必选/可选（草案） | 边界备注 |
|---|---|---|---|---|---|---|
| 1.1 | LnkVision 平台基座（认证权限/摄像头/场景与 ROI） | 认证与权限+摄像头+场景与 ROI | 5 | JWT 登录与刷新/限流（:7）；admin/operator/viewer RBAC（:8）；摄像头 CRUD/状态/截图（:10）；HTTP/Mock 接入（:11）；场景/基线图/ROI（:13） | **必选** | 多租户/SSO/LDAP（:9）与 RTSP/视频流/边缘网关（:12）missing 不在范围，需要时走二开 |
| 1.2 | AI 检测引擎 | 检测 | 5 | 障碍物（:14）；YOLO-World 开放词表（:15）；火灾/烟雾（:16，质量未量化）；地面脏污对比（:17）；模型上传/指派/热加载（:18） | **必选** | 检测治理（模型卡/评测集/分场景指标，:19）missing 不在范围；火灾/烟雾置信度 medium 已在行备注披露 |
| 1.3 | 规则引擎与告警工单中心 | 规则+告警+工单 | 5 | 规则与标准模板（:20）；冷却限流/告警抑制（:21）；告警四态生命周期（:22）；证据图/CSV 导出（:23）；告警确认后工单流转（:25） | **必选** | 告警操作审计/变更历史/申诉（:24）missing 不在范围 |
| 1.4 | 通知与实时协同 | 通知+实时协同 | 2 | 通知组路由/测试发送（:27）；EventBus/JWT WebSocket 实时推送（:28） | **必选** | 短信通道（:26 partial，国内服务商待确认）补齐走二开；企业微信/邮件已含 |
| 1.5 | 运营看板 | 看板 | 1 | 告警趋势/置信度/设备/worker 状态（:29） | **可选** | 独立可选模块（沿 lnkreport 1.6 可视化可选先例） |
| 2.1 | 其他系统对接 | — | 0（通道） | 视频平台、工单系统等未列入目录的对接 | **可选**（第三方对接） | 按二开 2,000 元/人天（pricing-basis.yaml 唯一权威源）；封闭系统边界——capability/MCP/OpenClaw 接入（:37 explicitly-not-do）需单独评审 |
| **合计（标准范围）** | | | **18** | | 必选 17 / 可选 1 | = existing 18 项全量分配 |

### 3.3 功能域 → 模块分配审计表（逐域可对账，求和闭合）

| 功能域（功能清单.md:行） | 行数 | 分配去向（模块 → 行数） | 校验 |
|---|---|---|---|
| 认证与权限（:7-:9） | 3（existing 2 / missing 1） | 1.1 ← 2（:7,:8）；定制候补 ← 1 missing（:9 多租户/SSO/LDAP） | 2+1 = 3 ✅ |
| 摄像头（:10-:12） | 3（existing 2 / missing 1） | 1.1 ← 2（:10,:11）；定制候补 ← 1 missing（:12 RTSP/视频流/边缘网关） | 2+1 = 3 ✅ |
| 场景与 ROI（:13） | 1（existing 1） | 1.1 ← 1 | 1 ✅ |
| 检测（:14-:18） | 5（existing 5） | 1.2 ← 5 | 5 ✅ |
| 检测治理（:19） | 1（missing 1） | 定制候补 ← 1 missing（模型卡/评测集/分场景指标） | 1 ✅ |
| 规则（:20-:21） | 2（existing 2） | 1.3 ← 2 | 2 ✅ |
| 告警（:22-:24） | 3（existing 2 / missing 1） | 1.3 ← 2（:22,:23）；定制候补 ← 1 missing（:24 操作审计/变更历史/申诉） | 2+1 = 3 ✅ |
| 工单（:25） | 1（existing 1） | 1.3 ← 1 | 1 ✅ |
| 通知（:26-:27） | 2（existing 1 / partial 1） | 1.4 ← 1（:27）；定制候补 ← 1 partial（:26 短信国内通道） | 1+1 = 2 ✅ |
| 实时协同（:28） | 1（existing 1） | 1.4 ← 1 | 1 ✅ |
| 看板（:29） | 1（existing 1） | 1.5 ← 1 | 1 ✅ |
| 运维（:30-:31） | 2（partial 1 / missing 1） | 定制候补 ← 2（:30 partial——Docker Compose/离线安装 B6.1 验证期移除，私有化重建期恢复；:31 missing 多商场复制/远程升级） | 2 ✅ |
| 数据治理（:32） | 1（partial 1） | 定制候补 ← 1 partial（图像留存生命周期策略） | 1 ✅ |
| 隐私（:33） | 1（missing 1） | 定制候补 ← 1 missing（人脸脱敏/公共场所告知/DPIA；service_notes 第 4 条披露） | 1 ✅ |
| 产品边界（:34-:37） | 4（explicitly-not-do 4） | 边界外 ← 4（service_notes 第 3 条 + 2.1 行备注声明） | 4 ✅ |
| **合计** | **31** | 标准 18（1.1=5, 1.2=5, 1.3=5, 1.4=2, 1.5=1）+ 定制候补 9（partial 3 + missing 6）+ 边界外 4 | 18+9+4 = 31 ✅ |

状态计数交叉校验：existing 18 = 2+2+1+5+2+2+1+1+1+1 ✅；partial 3（:26,:30,:32）；missing 6（:9,:12,:19,:24,:31,:33）；explicitly-not-do 4（:34-:37）。

### 3.4 定制候补清单（不计入标准范围，走二开）

| 类别 | 条目（功能清单.md:行） | 处置口径 |
|---|---|---|
| partial 3 项 | :26 短信国内通道；:30 Docker Compose/离线安装（B6.1 重建期）；:32 图像留存生命周期 | 补齐按二开 2,000 元/人天（pricing-basis.yaml devkit_rate） |
| missing 6 项 | :9 多租户/SSO/LDAP；:12 RTSP/视频流/边缘网关；:19 检测治理（模型卡/评测集）；:24 告警操作审计/申诉；:31 多商场复制/远程升级；:33 隐私（人脸脱敏/DPIA） | 客户需要时走二开 2,000 元/人天；范围由 requirement-evaluator 评估 |
| 新需求 | —（需求清单.md 自注无可信专属需求） | 一律二开 2,000 元/人天 |
| 边界外 not-do 4 项 | :34 客流/访问者分析；:35 人脸识别/身份追踪；:36 消防联动/门禁控制；:37 capability/MCP/OpenClaw 接入 | 显式声明不在报价范围（service_notes 第 3 条；:37 另在 2.1 行备注声明「需单独评审」） |

### 3.5 待 OPC 复核项（草案默认生效中，OPC 可逐项覆盖）

| # | 复核项 | 草案立场 | 影响 |
|---|---|---|---|
| R1 | 模块分组整体（5 实体模块 + 1 二开通道；功能域归并粒度） | §3.2 | 报价单结构与租用费拆分粒度 |
| R2 | 1.5 运营看板可选 vs 随 1.1 随附 | 草案可选（沿 lnkreport 1.6 先例） | 可选集边界（若随附 1.1 → 6 项、可选 → 0 项核心） |
| R3 | 1.4 通知与实时协同是否必选 | 草案必选（告警→通知→工单闭环核心） | 必选集 17 项边界 |
| R4 | 实施服务 3.1 人天数 | 留空 None（不沿用 CRM 模板数值） | 实施费定价 |
| R5 | 售后 4.1「首年赠送」是否沿用 | 草案沿用模板惯例 | 次年费用结构 |
| R6 | 私有化交付载体（:30 B6.1 重建期）可用性 | saas_vs_private 实施差异行如实声明「恢复时间待 OPC 确认」 | 私有化模式话术与可售性 |
| R7 | 隐私合规（:33 missing）是否升标准义务 | 草案走二开/专项评审（service_notes 披露） | 面客风险与合规边界 |
| R8 | 火灾/烟雾检测（:16 置信度 medium）话术 | 1.2 行备注披露「模型质量未量化」 | 面客承诺边界 |

## 4. LNKVISION_DATA 落地说明

文件：`skills/business/pricing-generator/generate_quote.py`——LNKVISION_DATA 常量（:543-:663）+
`build_lnkvision_data()` 守卫（:665-:690）；CLI 接线 `:1458`（valid_products）+ `:1494-:1495`（dispatch）。

### 4.1 结构映射（模块分组草案 §3.2 → 数据键，对齐 LNKREPORT_DATA）

| 数据键 | 行数 | 内容 |
|---|---|---|
| `core_modules` | 5 | 1.1 平台基座（5）/ 1.2 AI 检测引擎（5）/ 1.3 规则与告警工单（5）/ 1.4 通知与实时协同（2）必选；1.5 运营看板（1）可选 |
| `integration_items` | 1 | 2.1 其他系统对接（二开 DEVKIT_RATE 通道，不设固定条目；封闭系统边界备注） |
| `implementation_items` | 4 | 3.1（人天留空 None + 新增项目已核定 0/0）+ 3.2/3.3/3.4（含在 3.1，金额列 `—`） |
| `after_sales_items` | 1 | 4.1 首年赠送（已核定结构性 0：首/新增项目报价 0/0） |
| `summary_rows` | 4 | 首年/次年合计 + 首年/次年优惠价（供销售谈判填写） |
| `service_notes` | 5 | 二开费率 + 税率 6%（费率引用）+ 产品边界 not-do 4 项声明 + 隐私缺口披露 + 待定价声明 |
| `saas_vs_private` | 5 维度 | 授权性质/数据归属/次年费用/适合场景/实施差异（私有化交付载体 B6.1 重建期如实声明） |
| `modules` | 5 | Sheet2 模块级描述，条目数 5+5+5+2+1=18（§3.3 总边界，测试断言） |

行结构八列：`(序号, 名称, 内容说明, 首项目单价, 首项目报价, 新增项目单价, 新增项目报价, 备注)`。

### 4.2 金额留空机制（同 LNKREPORT_DATA）

- `None` = 待定价（对应模板 `____` 惯例）；`"—"` = 结构性不适用（3.2/3.3/3.4 含在 3.1）。
- **0 仅限已核定两处**（沿 O7-report phase3_ratification 草案默认，非编造）：3.1 新增项目单价/报价（`0, 0`）、4.1 首项目报价/新增项目报价（首年赠送，`0, 0`）——测试 `RATIFIED_ZEROS` 白名单钉死，其他位置出现数值即 fail。
- 费率引用（授权明示例外）：2.1 与 service_notes 引用 `DEVKIT_RATE`（pricing-basis.yaml devkit_rate=2000）；税率 6%（tax_rate_default）只出现在说明文字。
- 每个定价行备注携带「待定价」标记；`pricing_status` 顶层声明「待定价（金额留空；O7-vision 面客定判后结构落地）」。

### 4.3 生成行为：显式拒绝（完全复用 build_lnkreport_data 模式）

`build_lnkvision_data()` 调 `sys.exit` 输出 `[REFUSED]` 消息（exit=1，实测 §7）。理由同 lnkreport
Phase 3：现有 `build_quote_sheet`/`merge_product_data` 为 6 列数值管线，消费 `None` 金额会
`sum(None)` 崩溃、填 0 渲染等于编造「免费」；显式拒绝是零行为风险的合法选项。组合防护：
`--product MI,LNKVISION` 组合同样在数据装配期被拒（写盘前，测试实测）。放开条件：OPC 提供
定价数值 + 另开授权 → 届时实现八列渲染与 pricing-basis.yaml 登记（均不在本轮范围）。

## 5. capability 前后值 + 钉线前后值

### 5.1 pricing capability lnkvision 条目（`skills/business/pricing-generator/references/adapter-capabilities.yaml`，改前 :67-74 / 改后 :67-77）

| 字段 | 前 | 后 |
|---|---|---|
| status | `unsupported`（:69） | `onboarding`（:70）——**status 值变更（本裁决授权的权威动作）** |
| evidence | 1 条：`"设计包 §3.3.C：无报价数据（missing-pricing）"`（:71） | 3 条：原条目保留（:72）+ O7-vision 定判条目（:73，customer-facing + 决策记录 :9 行号）+ LNKVISION_DATA 结构落地条目（:74，含守卫/测试/执行记录 §3 指针） |
| verified_at | `"2026-10-04"` | `"2026-10-04"`——零变更（shared schema 测试钉 AUDIT_DATE） |
| owner | `opc` | `opc`——零变更 |
| notes | `"O7-vision（pending）先确认产品定位与是否面客；不得从 lnkcre 复制价格。"` | `"O7-vision 已定判（2026-10-04 decided / customer-facing）：独立面客产品；报价基线结构在位（LNKVISION_DATA 四段八列，金额一律留空），定价数值待 OPC 提供后另开授权填数并升级 implemented；不得从 lnkcre 或其他产品复制价格。"` |

notes 更新口径：原「O7-vision（pending）」为陈旧预判状态，与「已定判」语义直接矛盾，按裁决
核心语义原位升级（沿 O7-chat/O9 执行记录审计口径）；status / verified_at / owner / 键集均为
授权内变更或零触碰。

### 5.2 shared 钉线（`shared/product_context/tests/test_adapter_capabilities_schema.py`）

| 钉点 | 前 | 后 |
|---|---|---|
| EXPECTED_MATRIX pricing-generator×lnkvision | `"unsupported"`（:125） | `"onboarding"`（:129） |
| EXPECTED_DISTRIBUTION unsupported | `4`（:165） | `3`（:169） |
| EXPECTED_DISTRIBUTION onboarding | `6`（:164） | `7`（:168） |
| 修订注释 | O2★/O5-Q5/O8/O7-chat 四条 | +O7-vision 第五条（:98-101，引决策记录） |

分布总和 48 不变（implemented 14 / partial 13 / onboarding 7 / unsupported 3 / not-applicable 8 / blocked 3）。

### 5.3 pricing 本地八产品全景钉（`skills/business/pricing-generator/tests/test_lnkreport_data.py`）

| 钉点 | 前 | 后 |
|---|---|---|
| `test_capability_other_products_untouched` 全景 dict lnkvision | `"unsupported"`（:227） | `"onboarding"`（:231） |
| 该测试 docstring | O8 / O7-chat 两条修订注记 | + O7-vision 同批修订注记（引决策记录；注明 shared 钉线同 commit） |

**同批必要性说明（审计口径，沿 O7-chat §3.3）**：该测试加载真实 capability yaml 钉八产品全景，
且文件内「capability 条目（与 yaml 修改同批原子化）」契约在位；验证门「pricing pytest 全过」
在不更新本地钉时机械不可满足，故本地钉属「钉线同批」的必要组成，非允许清单外扩。

## 6. 测试新增清单与前后计数

新增 `tests/test_lnkvision_data.py`（12 项，镜像 test_lnkreport_data.py 四类覆盖）：

| 测试 | 覆盖 |
|---|---|
| test_lnkvision_segments_and_seq | 四段键 + 序号 1.1-4.1 + 八列行结构 |
| test_lnkvision_required_optional_and_notes | 分组草案必选（1.1-1.4）/可选（1.5）；2.1 费率引用；封闭系统边界声明 |
| test_lnkvision_existing_counts_sum_18 | 模块条目数合计 = existing 18（§3.3 总边界） |
| test_lnkvision_summary_service_notes_saas_private | 汇总四行 + 6%/待定价 + not-do 边界/DPIA 披露 + SAAS vs 私有化 5 维度 |
| test_lnkvision_amounts_left_blank | 金额留空/None；"—"；0 仅 RATIFIED_ZEROS 白名单 |
| test_lnkvision_pricing_rows_marked_pending | 定价行「待定价」标记 |
| test_lnkvision_no_cross_product_price_copy | 跨产品借用禁令（MI/CRM/AI 价格串排查） |
| test_build_lnkvision_data_refuses_without_prices | 守卫拒绝 + 消息断言 |
| test_cli_lnkvision_single_refuses | 单产品 CLI 拒绝 |
| test_cli_lnkvision_in_combo_refuses | 组合（MI,LNKVISION）CLI 写盘前拒绝 |
| test_cli_parse_accepts_lnkvision | 代号解析（含小写归一） |
| test_capability_lnkvision_onboarding | status/evidence（决策记录文件:行）/verified_at/owner |

计数：**pre 19 passed → post 31 passed**（+12，0 fail）。既有 test_lnkreport_data.py（含全景钉
新值）与 test_product_context_integration.py 6 项无回归。

## 7. 验证实测（本会话）

### 7.1 测试与一致性门

```bash
cd /opt/code/skill/skills/business/pricing-generator && uv run pytest -q
# 执行前：19 passed（基线实测）；执行后：31 passed in 0.20s

cd /opt/code/skill/shared/product_context && uv run python -m unittest discover -s tests
# Ran 53 tests ... OK

cd /opt/code/skill && bash references/scripts/check_docs_consistency.sh
# FAIL: 0 / WARN: 0 / PASS: 33 → RESULT: PASS
```

### 7.2 git 面实测

```text
git diff --check    # 无输出，rc=0
git status --short
 M references/adapter-capability-owner-decision-backlog-inventory-2026-10-04.md   # §15 注记（本轮）+ §14（O7-chat 既有）
 M shared/product_context/tests/test_adapter_capabilities_schema.py               # 钉线同批（本轮）+ O7-chat 既有
 M skills/business/pricing-generator/generate_quote.py                            # LNKVISION_DATA + CLI（本轮）
 M skills/business/pricing-generator/references/adapter-capabilities.yaml         # lnkvision 条目（本轮）+ O7-chat 既有
 M skills/business/pricing-generator/tests/test_lnkreport_data.py                 # 全景钉同批（本轮）+ O7-chat 既有
 ?? references/adapter-capability-owner-decision-o7-chat-2026-10-04.md            # O7-chat 既有
 ?? references/adapter-capability-owner-decision-o7-chat-execution-2026-10-04.md  # O7-chat 既有
 ?? references/adapter-capability-owner-decision-o7-vision-2026-10-04.md          # 决策记录（Phase 1 前已存在）
 ?? references/adapter-capability-owner-decision-o7-vision-execution-2026-10-04.md # 本文件
 ?? skills/business/pricing-generator/tests/test_lnkvision_data.py                # 本轮新增测试
```

本轮增量 = generate_quote.py + yaml lnkvision 条目 hunk + shared 钉线（矩阵格/分布/注释）+
本地全景钉 + test_lnkvision_data.py + backlog §15 + 本文件；其余为 O7-chat 既有未提交增量
（待 OPC 统一提交批）。

### 7.3 允许清单外零改动实证

- pricing yaml 同文件其余 7 个产品条目零改动（diff hunk 落在 lnkvision 条目内，§5.1）；
- company-intro-generator / 其他四个 consumer 的 capability 文件零改动（不在 git status）；
- pricing-basis.yaml 未写（docs 仓零改动，不在 git status）；30-products/** 只读取证；
- resolver / company.yaml / registry / shared 生产代码（钉线测试文件除外）零改动；
- generate_quote.py 其余产品数据（MI/CRM/AI/LNKCHATBI/LNKREPORT）与共享渲染管线零改动
  （diff hunk 仅 LNKVISION_DATA 块 + valid_products 一行 + dispatch 两行）。

### 7.4 LSP 甄别（改动 .py）

- `generate_quote.py`：诊断均为既有项——`_company_base`/`generate_quote` 隐式相对导入
  （script-run skill 惯例）、`list[tuple]` 裸泛型（merge_product_data 既有代码）、openpyxl
  stub「not a known attribute」与 `min` 形参（AGENTS.md 明示假错类）；本轮改动行零新增诊断。
- `tests/test_lnkvision_data.py`：仅 `import generate_quote` 同款既有惯例诊断（与
  test_lnkreport_data.py :65 完全同构）。

## 8. 冻结面确认（本轮未触碰、维持冻结）

- **未填任何单价/金额/人天数**：全部 None/「待定价」/已核定结构性 0（forbidden :36 例外仅
  费率引用——DEVKIT_RATE 与 6% 税率均 pricing-basis.yaml 权威源引用）。
- **未从 lnkcre/lnkchat/其他产品复制价格**（test_lnkvision_no_cross_product_price_copy 钉住）。
- **未写 pricing-basis.yaml / docs 仓**；**30-products/** 只读**（功能清单仅取证实测行数）。
- **未改** resolver / company.yaml / registry / shared 生产代码（钉线测试文件除外）/ 其他产品
  capability 条目。
- **未执行** O10-report / O10-vision（叙事面定位依据已由本定判解锁，但启动仍为独立签署项，
  决策记录 :31-33 narrative_linkage 明示「本记录不构成其批准」）/ O11 / 删除动作 / lnkreport
  定价（挂起）；lnkvision 定价数值挂起（deferred :28-29）。
- 未执行 git add / commit / push（OPC 随后统一安排提交批）。

## 9. 结论

- **O7-vision 完成（面客定判落地）**：LNKVISION_DATA 结构在位（四段八列、金额留空待定价、
  无数值显式拒绝 + 组合写盘前拒绝）；模块分组草案（existing 18 = 5+5+5+2+1，31 行全量分配
  闭合）待 OPC 复核；capability lnkvision unsupported→onboarding（evidence/notes 同批）；
  shared 钉线（矩阵格 + 分布 unsupported 4→3 / onboarding 6→7）与 pricing 本地八产品全景钉
  同批；pricing 19→31 passed / shared 53 OK / consistency 0/0/33。
- **O10-vision 定位依据就绪**（面客口径），启动仍为独立签署项；其余项维持冻结。
- 未提交、未推送。
