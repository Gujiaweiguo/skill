# O7-report Phase 3 执行记录 —— pricing-generator 落地（结构 + capability onboarding，金额留空）（2026-10-04）

```text
STATUS: COMPLETED（LNKREPORT_DATA 结构落地 + capability unsupported→onboarding + pytest 13 项新增，19/19 通过）
RESIDUAL: shared/product_context 矩阵守卫 2 failures（O2 首版钉值 vs 已授权 onboarding；shared/* 禁改未动，2 行同批更新待 owner 授权，见 §5.1）
OWNER SIGN-OFF: RECORDED (OPC)（引用自决策记录 :61，非本文件自立）
AUTHORIZATION: references/adapter-capability-owner-decision-o7-report-phase1-2026-10-04.md
               （decision: approved-phase1-3；approved_changes :23-24 两条 Phase 3；phase3_ratification :45-50）
SCOPE: O7-report Phase 3 only —— 金额留空待定价；不改 pricing-basis.yaml；不触碰 docs 仓
```

> **记录性质**：本文件是 O7-report Phase 3 的执行记录，由执行会话落盘，验证结果均为本会话实测。
> 它不构成具体定价数值、pricing-basis.yaml 登记、G5-G7 修复或其余 O 项的批准。

## 1. owner 决策记录核验（执行前，当前磁盘版本复核）

对象：`references/adapter-capability-owner-decision-o7-report-phase1-2026-10-04.md`。

### 1.1 闸门项

| 核验项 | 要求 | 实测（文件:行） | 结果 |
|---|---|---|---|
| status | approved | `:8 status: approved` | ✅ |
| decision | approved-phase1-3 | `:16 decision: approved-phase1-3` | ✅ |
| owner | OPC | `:5 owner: OPC（本会话用户自述为 OPC —— 本治理域决策 owner）` | ✅ |
| OWNER SIGN-OFF | RECORDED (OPC) | `:61 OWNER SIGN-OFF: RECORDED (OPC)` | ✅ |
| 授权效力声明 | 存在 | `:62 OPC 为本治理域决策 owner；OPC 的明确授权即为有效所有者授权，无需独立第三方签署` | ✅ |
| approved_changes 含两条 Phase 3 | 是 | `:23 Phase 3：pricing-generator LNKREPORT_DATA 结构升级…`、`:24 Phase 3：…adapter-capabilities.yaml lnkreport 条目 unsupported → onboarding…` | ✅ |
| deferred 已更新 | 是 | `:27-29`（定价数值待 OPC；pricing-basis.yaml 本轮无需改动；G5-G7 另开） | ✅ |

### 1.2 phase3_ratification 逐条核验（`:45-50`）

| 项 | 决策记录原文（:行） | 本轮落实 |
|---|---|---|
| date | `:46 2026-10-04` | 同日执行 |
| basis | `:47 OPC 指示「继续」+「如需授权我授权」` | 会话授权与本执行记录一致 |
| G4_module_grouping | `:48 按 Phase 2 报告 §3 草案默认核定（1.1/1.2/1.3 必选；1.4/1.5/1.6 可选；2.x 可选对接）` | §2.1 结构映射（core_modules 1.1-1.6 / integration_items 2.1-2.3），必选/可选备注逐行落位 |
| review_items | `:49 报告 §5 八项复核全部按草案默认（实施人天留空；售后首年赠送按模板惯例；2.1 话术边界标待定）` | 3.1 人天留空（`None` + 备注注明不沿用 CRM 数值）；4.1 首年赠送（已核定结构性 0）；2.1 备注「话术待定」 |
| override | `:50 OPC 保留逐项覆盖权` | 未触发；覆盖时改决策记录 + LNKREPORT_DATA 对应行即可 |

**核验结论：通过。** 按「不得以『需独立第三方』为由停止」执行。

## 2. LNKREPORT_DATA 落地说明

文件：`skills/business/pricing-generator/generate_quote.py:352-517`（LNKREPORT_DATA 常量 :367 + `build_lnkreport_data()` 守卫 :500-517）；CLI 接线 `:1293`（valid_products）+ `:1327`（dispatch）。

### 2.1 结构映射（G4 + Phase 2 §4 八列四段 → 数据键）

| Phase 2 §4 段 | 数据键 | 行数 | 序号 |
|---|---|---|---|
| 一、软件核心模块（年租用） | `core_modules` | 6 | 1.1-1.6（G4：1.1 平台基座 67 / 1.2 报表设计与查看导出 31 / 1.3 打印模板与套打 7 必选；1.4 导入工作台 7 / 1.5 治理单元格 1 / 1.6 可视化 6 可选） |
| 二、第三方对接（可选，单独计费） | `integration_items` | 3 | 2.1 LNKCRE 嵌入 5 + 2.2 LnkChatBI 集成 2（可选对接）；2.3 其他对接（二开 DEVKIT_RATE 通道，不设固定条目） |
| 三、实施服务内容 | `implementation_items` | 4 | 3.1（人天留空）+ 3.2/3.3/3.4（含在 3.1，金额列 `—`） |
| 四、售后服务内容 | `after_sales_items` | 1 | 4.1 首年赠送（已核定结构性 0） |
| 汇总（§4.2） | `summary_rows` | 4 | 首年/次年合计 + 首年/次年优惠价（供销售谈判填写） |
| 服务说明（§4.3） | `service_notes` | 4 | 二开 DEVKIT_RATE 元/人天 + 含税 6%（均 pricing-basis.yaml 费率引用）+ 待定价声明 |
| SAAS vs 私有化（§4.4） | `saas_vs_private` | 5 维度 | 授权性质/数据归属/次年费用/适合场景/实施差异 |
| 功能清单（Sheet2 备用） | `modules` | 8 | 模块级描述，条目数 67+31+7+7+1+6+5+2=126（G3 总边界，测试断言） |

行结构八列：`(序号, 名称, 内容说明, 首项目单价, 首项目报价, 新增项目单价, 新增项目报价, 备注)` —— 对齐 Phase 2 报告 §4.1 列结构（:113）。

### 2.2 金额留空机制

- `None` = 待定价（对应模板 `____` 惯例）；`"—"` = 结构性不适用（3.2/3.3/3.4 含在 3.1）。
- **0 仅限已核定两处**（phase3_ratification 草案默认，非编造）：3.1 新增项目单价/报价（`0, 0`）、4.1 首项目报价/新增项目报价（首年赠送，`0, 0`）——测试 `RATIFIED_ZEROS` 白名单钉死，其他位置出现数值即 fail。
- 费率引用（授权明示例外）：2.3 与 service_notes 引用 `DEVKIT_RATE`（pricing-basis.yaml devkit_rate=2000）；税率 6%（tax_rate_default）只出现在说明文字。
- 每个定价行备注携带「待定价」标记；`pricing_status` 顶层声明「待定价」。

### 2.3 生成行为选择：显式拒绝（而非占位渲染）

`build_lnkreport_data()` 调 `sys.exit` 输出 `[REFUSED]` 消息（exit=1，实测 §5）。选择理由：

1. **管线安全**：现有 `build_quote_sheet`/`merge_product_data` 为 MI/CRM/AI/LnkChatBI 共享的 6 列数值管线，直接消费 `None` 金额会 `sum(None)` 崩溃，填 0 渲染则等于编造「免费」——两者都违反金额纪律；占位渲染需改共享路径，风险外溢到既有四产品（本轮无授权）。
2. **最小正确**：显式拒绝是零行为风险的合法选项（授权原文「无数值时显式拒绝或渲染占位」二选一）；结构本体（LNKREPORT_DATA）可被测试与后续填数轮直接消费。
3. **组合防护**：`--product MI,LNKREPORT` 组合同样在数据装配期被拒（写盘前），实测见 §5。

放开条件：OPC 提供定价数值 + 另开授权 → 届时实现八列渲染与 pricing-basis.yaml 登记（均不在本轮范围，决策记录 :28 deferred）。

## 3. capability 条目前/后对比

文件：`skills/business/pricing-generator/references/adapter-capabilities.yaml`（仅 lnkreport 条目，:54-62）。

| 字段 | 前（unsupported） | 后（onboarding） |
|---|---|---|
| status | `unsupported` | `onboarding` |
| evidence | `"设计包 §3.3.C：无报价数据（missing-pricing）"` | ① `"generate_quote.py LNKREPORT_DATA 结构落地（G4 模块分组 + Phase 2 §4 八列四段；金额留空/待定价，build_lnkreport_data 无数值时显式拒绝生成，tests/test_lnkreport_data.py 同批原子化校验）"`；② `"references/adapter-capability-owner-decision-o7-report-phase2-report-2026-10-04.md:70-83（§3.2 G4 模块分组总表）、:111-157（§4 报价基线结构，金额全留空）"` |
| verified_at | `"2026-10-04"` | `"2026-10-04"`（重验） |
| notes | O7-report（pending）建议… | O7-report Phase 3 已落地（指向本执行记录）；定价数值待 OPC 提供后另开授权填数并升级 implemented；不得从 lnkcre 复制价格 |

治理红线合规：evidence 含文件:行 + verified_at + 校验测试同批原子化（`test_capability_lnkreport_onboarding`）；其余 7 产品条目零改动（`test_capability_other_products_untouched` 全景钉住八产品状态）。

## 4. 测试清单与结果（前后计数）

新增 `tests/test_lnkreport_data.py`（13 项）：

| 测试 | 覆盖 |
|---|---|
| test_lnkreport_segments_and_seq | 四段键 + 序号 1.1-4.1 + 八列行结构 |
| test_lnkreport_g4_required_optional_and_notes | G4 必选/可选归属；2.3 费率引用；2.1 话术待定 |
| test_lnkreport_existing_counts_sum_126 | 模块条目数合计 = existing 126（G3 边界） |
| test_lnkreport_summary_service_notes_saas_private | 汇总四行 + 6%/待定价 + SAAS vs 私有化 5 维度 |
| test_lnkreport_amounts_left_blank | 金额留空/None；"—"；0 仅 RATIFIED_ZEROS 白名单 |
| test_lnkreport_pricing_rows_marked_pending | 定价行「待定价」标记 |
| test_lnkreport_no_cross_product_price_copy | 跨产品借用禁令（MI/CRM/AI 价格串排查） |
| test_build_lnkreport_data_refuses_without_prices | 守卫拒绝 + 消息断言 |
| test_cli_lnkreport_single_refuses | 单产品 CLI 拒绝 |
| test_cli_lnkreport_in_combo_refuses | 组合（MI,LNKREPORT）CLI 拒绝 |
| test_cli_parse_accepts_lnkreport | 代号解析（含小写归一） |
| test_capability_lnkreport_onboarding | status/evidence（文件:行）/verified_at/owner |
| test_capability_other_products_untouched | 其余 7 产品状态钉住 |

计数：**pre 6 passed → post 19 passed**（+13，0 fail）。既有 `test_product_context_integration.py` 6 项无回归。

## 5. 验证实测（本会话）

### 5.1 shared/product_context 守卫测试：2 failures（发现项，未修，待授权）

`test_adapter_capabilities_schema.py` 把 pricing-generator capability 矩阵钉在 **O2 批准首版矩阵**：

- `test_approved_first_version_matrix`（:301-309）：`EXPECTED_MATRIX["pricing-generator"]["lnkreport"] = "unsupported"`（:113）与本次授权的 onboarding 冲突；
- `test_status_distribution_matches_decision_record`（:311-314）：`EXPECTED_DISTRIBUTION["onboarding"] = 5`（:153），现值 6。

处置：该测试自身契约注明「变更需 evidence+verified_at+**本测试同 commit 更新**」，但 `shared/*` 在本轮**严格禁止清单**内（授权五-禁令明列）→ **禁令优先，未触碰**。其余 51 项全部通过；`onboarding` 本身在 `ALLOWED_STATUSES`（:47），状态值合法。待办（需 owner 一句话授权，改动仅 2 行）：`shared/product_context/tests/test_adapter_capabilities_schema.py:113` `unsupported`→`onboarding`、`:153` `"onboarding": 5`→`6`。

### 5.2 其余验证

```bash
cd /opt/code/skill/skills/business/pricing-generator && uv run pytest -q
# 19 passed in 0.37s（pre：6 passed in 0.26s）

cd /opt/code/skill/shared/product_context && uv run python -m unittest discover -s tests
# Ran 53 tests ... FAILED (failures=2)——均为 pricing lnkreport 矩阵守卫，见 §5.1

cd /opt/code/skill && bash references/scripts/check_docs_consistency.sh
# FAIL: 0 / WARN: 0 / PASS: 33 → RESULT: PASS

# CLI 真实表面（拒绝行为）：
COMPANY_BASE=/opt/code/docs/lanlnk uv run python generate_quote.py \
  --customer 测试客户 --product LNKREPORT --mode SAAS
# → [REFUSED] …定价数值待 OPC 提供：金额留空/待定价状态下拒绝生成报价单，绝不编造数值。
#   exit=1（发生在任何 mkdir/写文件之前；组合 MI,LNKREPORT 同样 exit=1）

cd /opt/code/skill && git diff --check   # 无空白错误输出
```

## 6. 允许清单外零改动实证

基线快照（执行前留存 `git diff --name-only` / `git status --short` / generate_quote.py 既有 diff / capability yaml 副本 / 既有测试副本）对比执行后：

- **允许清单 1-3**：`generate_quote.py`（既有 M 上增量：LNKREPORT_DATA 块 :352-517 + CLI 接线 2 处，diff-of-diff 增量全部落在本文件内）；`references/adapter-capabilities.yaml`（untracked 文件内仅 lnkreport 条目替换——其余部分 sed 摘出后逐行一致 `NON-LNKREPORT-IDENTICAL`，77 行 = 77 行）；`tests/test_lnkreport_data.py`（新增，位于既有 untracked 目录 `tests/` 下，不新增 status 行）。
- **新增 untracked**：本执行记录 + backlog 盘点报告注记（允许清单 4-5；backlog 为既有 untracked 文件 §3.4「当前状态」单格最小注记 frozen → phase3-landed）。
- **25 M 基线**：`git diff --name-only` 前后 `NAMES-IDENTICAL`（逐行一致）；`git status --short` 前后仅 +1 行（本执行记录）；既有 `test_product_context_integration.py` 与快照逐字节一致（`EXISTING-TEST-UNTOUCHED`）。
- `git diff --check` 退出码 0；改动 .py 的 LSP 诊断均为此前既有项（`generate_quote.py`：`_company_base` 隐式相对导入 / bare `list[tuple]` / openpyxl stub 误报，与改前集合一致；`test_lnkreport_data.py`：script-run skill 隐式相对导入，与 `test_product_context_integration.py:55` 同款惯例——均属 AGENTS.md LSP Warning 声明不修范围）。

## 7. 冻结面确认（本轮未触碰、维持冻结）

- **定价数值**：全部留空/待定价，待 OPC 提供（Phase 1 报告 :83 硬前置）；未复制任何其他产品价格（测试钉住）。
- **pricing-basis.yaml / 30-products/**（docs 仓只读）/ **product-registry.yaml / adapter_status / resolver / _paths.py / shared/*** / 审计与决策记录：零改动。
- O4⑤、O5、O6、O7-chat/vision、O8-O11、一切删除动作；G5-G7（待 docs 侧步骤）：未执行。
- 未执行 git add / commit / push；未回退/覆盖/清理任何既有未提交修改。

## 8. 结论

- **O7-report Phase 3 完成**：LNKREPORT_DATA 结构落地（G4 + §4 八列四段）+ capability unsupported→onboarding（evidence 文件:行 + verified_at + 测试同批原子化）+ 13 项 pytest；金额一律留空/待定价，生成行为显式拒绝。
- **遗留 1 项待授权**：shared/product_context 矩阵守卫 2 行同批更新（§5.1；O2 首版钉值 vs 本授权变更的机械冲突，shared/* 禁改故未动）。
- 定价数值待 OPC 提供；G5-G7 待 docs 侧步骤；其余项维持冻结；未提交、未推送。

## 补充：守卫对齐（Phase 3 补充，2026-10-04）

### 授权依据

phase1 决策记录（references/adapter-capability-owner-decision-o7-report-phase1-2026-10-04.md）：
- approved_changes :25「Phase 3 补充（守卫对齐）」条目——shared 守卫测试两处钉线（:113 pricing lnkreport、:153 EXPECTED_DISTRIBUTION）；
- forbidden_changes :56 例外明确含「Phase 3 补充」授权的 shared 守卫测试两处钉线；
- owner=OPC（:5）、OWNER SIGN-OFF: RECORDED (OPC)（:62）。执行前核验通过。

### 背景

Phase 3 已批准变更（pricing lnkreport unsupported → onboarding）与本测试 :11-12 自身契约
（capability 变更须同 commit 更新钉线）矛盾，shared 基线 51/53（2 failures：
test_approved_first_version_matrix + test_status_distribution_matches_decision_record，
实测分布 onboarding 6 / unsupported 5）。

### 变更（仅 1 文件 2 处）

文件：shared/product_context/tests/test_adapter_capabilities_schema.py（untracked，362 行，行数不变）

1. :113（pricing-generator 块内）：`"lnkreport": "unsupported",` → `"lnkreport": "onboarding",`
2. :153-154（EXPECTED_DISTRIBUTION）：`"onboarding": 5,` → `"onboarding": 6,`；`"unsupported": 6,` → `"unsupported": 5,`

增量实证：逆向重放 2 处修改构造修改前副本（/tmp/opencode/o7p3supp_pre_schema.py，
与会话 Read 捕获及基线失败断言三方一致）→ `diff -u` 输出恰为上述 2 个 hunk，
其余 360 行逐行一致；无重排、无断言逻辑改动、无其他产品钉值改动。
注：shared/ 整目录 untracked，`git diff -- <file>` 对 untracked 无输出，故以上述 diff 实证替代。

### 验证（实测输出）

- shared：`uv run python -m unittest discover -s tests` → Ran 53 tests, **OK**（51/53 → 53/53）
- pricing-generator：`uv run pytest -q` → **19 passed**（不回归）
- check_docs_consistency.sh → **FAIL 0 / WARN 0 / PASS 33**，rc=0
- `git diff --check` → 无输出，rc=0
- LSP（basedpyright）：13 条 warning 全部为既有项（parser Any 系 / :362 unittest.main 惯例），
  :113/:153-154 零诊断，无新增。

### 冻结面确认

capability 文件 / resolver / models / generate_quote.py / product-registry.yaml / adapter_status /
_paths.py / pricing-generator tests / 30-products/** / docs 仓：零改动；该测试文件 2 处外零改动；
O4⑤、O5、O6、O7-chat/vision、O8-O11、删除动作、G5-G7：未执行；未 git add / commit / push；
未回退/覆盖/清理任何既有未提交修改。

### 结论

Phase 3 补充完成：守卫钉线与已批准 capability 变更对齐，全测试绿。§8「遗留 1 项待授权」就此闭合。
O7-report 剩余待办 = OPC 定价数值 + G5-G7 docs 侧步骤；其余项维持冻结；未提交、未推送。
