# D2 执行记录 —— adapter_status 字段退役 / O4 步骤⑤（2026-10-04）

decision_basis: references/adapter-capability-owner-decision-d2-adapter-status-retire-2026-10-04.md
status: executed（本文记录 = D2 approved_changes「执行记录落盘」）
executor: orchestrator（按 OPC 授权批执行；D1 已先行完成）
owner_sign_off: "OWNER SIGN-OFF: RECORDED (OPC)（决策记录原文）"

## 1. 闸门核验

| 项 | 结果 |
|---|---|
| 决策记录存在 | ✓ references/adapter-capability-owner-decision-d2-adapter-status-retire-2026-10-04.md |
| status / decision / owner | approved / delete-field / OPC（OWNER SIGN-OFF: RECORDED (OPC)）✓ |
| 前置 D1 | 已完成（见 d1-execution 记录；registry 侧对象随文件删除自然消失——D2 approved_changes c 项「若 D1 已先行删除则自然消失」成立，无数据区 8 行需删）|

## 2. 字段删除面（models / resolver / README diff 摘要）

| 文件 | 删除内容 |
|---|---|
| `shared/product_context/models.py` | ① dataclass 字段声明 `adapter_status: str`（原 :45）；② `as_dict()` product 区序列化键 `"adapter_status": self.adapter_status`（原 :69）。ProductContext 字段序：company/id/name/product_status/**~adapter_status~**/layers/… |
| `shared/product_context/resolver.py` | ① 透传赋值 `adapter_status = str(item.get("adapter_status") or "unsupported")`（原 :434，unsupported 回落随之消灭）；② ProductContext 构造位置参数 `adapter_status,`（原 :456）。构造点全仓唯一（resolver.py:451，grep `ProductContext\(` 实证）|
| `shared/product_context/README.md` | registry 段（原 :38-39）→ 「never read or merged the retired product-registry.yaml; deleted by owner decision D1」；垫片段（原 :42-56）→ **已退役登记**：字段 retired（D2 / O4 step 5，引 D2 记录）+ 保留 O4 决策历史指引（迁移期透传语义、8 产品恒 unsupported 无信息量）+ 新禁令（dataclass 无字段、as_dict 不输出、company.yaml 残留键不透传、恢复需 owner 独立批准+门禁同批更新）+ 冻结线与门禁指针保留 |

AST 校验：models.py / resolver.py 解析通过；`lsp_diagnostics` 两文件 + 门禁测试 = **0 error**（仅 basedpyright 风格 warning，与仓内既有模式一致）。

## 3. 字段删除前后 resolver 输出对比样例（COMPANY_BASE=/opt/code/docs/lanlnk 实测）

前（git archive HEAD 提取旧版包运行）——8 产品 product 区均含：

```json
"lnkcre":     {"id": "lnkcre",     "name": "LnkCRE 商业地产经营管理平台", "product_status": "complete",  "adapter_status": "unsupported"},
"lnkcrm":     {"id": "lnkcrm",     "name": "商圈会员 CRM 系统",            "product_status": "partial",   "adapter_status": "unsupported"},
"lnkchat":    {"id": "lnkchat",    "name": "LnkChat 工作流平台",           "product_status": "complete",  "adapter_status": "unsupported"},
"lnkchatbi":  {"id": "lnkchatbi",  "name": "LnkChatBI 智能问数",           "product_status": "complete",  "adapter_status": "unsupported"},
"lnkreport":  {"id": "lnkreport",  "name": "LnkReport 报表",               "product_status": "complete",  "adapter_status": "unsupported"},
"lnkvision":  {"id": "lnkvision",  "name": "LnkVision（原 MallSenseAI）",  "product_status": "complete",  "adapter_status": "unsupported"},
"lnkgateway": {"id": "lnkgateway", "name": "LnkGateway AI 网关（AIPlat）", "product_status": "partial",   "adapter_status": "unsupported"},
"lnkwebsite": {"id": "lnkwebsite", "name": "蓝联科技官网",                 "product_status": "prd-only",  "adapter_status": "unsupported"}
```

后（工作树现行代码运行）——同 8 产品 product 区统一为三键（id / name / product_status），**无 adapter_status 键**；product_status / authority / layers 全部不变（除该键外逐键一致）。

## 4. 门禁改写前后结构（test_adapter_status_migration_gate.py）

| 门禁 | 前（O4 兼容期） | 后（D2 退役后） |
|---|---|---|
| 模块定位 | 「证明 resolver 仍输出 adapter_status 兼容字段」 | 「证明字段已删除 + 全仓零消费 + 冻结线」；依据区引 O4 → D2 两份记录 |
| 门禁 1 CompatFieldRetainedTest（4 测试） | assertIn 字段存在；缺省回落=unsupported；company.yaml 值原样透传；live 8 产品输出该键 | **FieldRetiredTest（3 测试）**：assertNotIn 字段（`ProductContext.__dataclass_fields__`）；as_dict 无该键（fixture company.yaml 显式写 `adapter_status: partial` 也不透传）；live 8 产品 as_dict 无该键 |
| 门禁 2/3 CapabilityLayeringTest | resolver/models 源码不引用 capability 文件；解析不读 capability 文件；blocked 不泄入 authority | **逐字保留**（与字段删除无涉，方案 B 红线继续有效）|
| 门禁 4/5/6 AuthorityFreezeLineTest | lnkcrm code=complete（含 revision 断言）/ lnkgateway ontology=unresolved+ontology_entry=null / lnkwebsite prd-only+not-applicable | **逐字保留（D2 明令冻结线原样保绿）**；FREEZE_LINES 常量与注释原样 |
| 门禁 7 NoNewConsumerScanTest → **ZeroConsumerScanTest** | `ALLOWED_ADAPTER_STATUS_SOURCES` 白名单 4 文件精确计数（models=2 / resolver=2 / capabilities_schema=7 / prd-gen contracts=0），白名单外违规 | **白名单废除**：任何 .py/.sh 命中即违规；唯一豁免 = 两个禁令执行文件自身（本门禁自指 + test_adapter_capabilities_schema.py 键级禁令自检，后者命中数钉基线 7 防夹带）；扫描根/后缀/跳过目录集不变 |

常量侧：删 `COMPAT_DEFAULT`、`CAPABILITY_FILENAME`（改写后无消费者）；`DECISION_RECORD` → `O4_DECISION_RECORD` + 新增 `D2_DECISION_RECORD` + `RETIRED_FIELD`（断言消息内引用，保留溯源）。

**冻结线保绿实证**：改写后 shared 全套 52 OK；live 实测三连断言通过（lnkcrm `authority[code].status=complete` 且 `layers[code_root]=/opt/code/lnkcrm` 且 revision 非空 / lnkgateway `authority[ontology].status=unresolved` 且 `layers[ontology_entry]=None` / lnkwebsite `product_status=prd-only` 且 `authority[ontology].status=not-applicable`）。

## 5. 清扫清单（grep adapter_status 全仓取证后逐处最小更新）

| # | 文件:行 | 变更 |
|---|---|---|
| 1 | `skills/business/pricing-generator/SKILL.md:85-88` | 「resolver 输出的 adapter_status 是 adapter capability 元数据…」→「resolver 不再输出 adapter_status（字段已退役，D2 2026-10-04 删除）」 |
| 2 | `skills/meta/openspec-practice/references/prd-writeback.md:97` | 「adapter_status 分开记录」→「adapter 支持度（capability 文件口径）分开记录」 |
| 3 | `skills/business/product-prd-generator/references/product-semantic-baseline.md:75-81`（迁移期注记） | 「注册表 adapter_status 冻结为迁移期兼容快照」→「registry 已退役删除（D1），冻结快照消失；resolver ProductContext.adapter_status 亦已删除（D2/O4⑤）」；注记头标 closed by D1/D2 |
| 4 | `shared/product_context/README.md` | §2（本记录 §2 第三行）|

**测试基线变化清单**：
- shared：53 → **52 OK**（-1：门禁 1 由 4 测试收窄为 3——「缺省回落」「原样透传」两测试在字段删除后语义不可能，合并为一个「company.yaml 残留键不透传」断言；属 D2 预期内计数变化，非删测试过关）
- prd-gen：**169 passed / 3 skipped 不变**（注释级 D1 改写 + 字段删除零波及——prd-gen 测试对 product 区无 adapter_status 键断言）
- pricing：**31 passed 不变**
- `test_adapter_capabilities_schema.py`：零改动（O4 键级禁令自检，7 命中基线由新门禁钉死）

**保留命中归因（终局 rg adapter_status，排除 references/ 档案后全部命中分类）**：
1. 两个禁令执行测试自身（gate + 键级自检）——D2 明令门禁同批存在的执行机制，token 为断言/扫描所必需；
2. `shared/product_context/README.md` 退役登记段——D2 明令「垫片语义 → 已退役登记，引 D2 记录」；
3. `product-semantic-baseline.md` / `.schema.json` / `product-governance/README.md:39`——**baseline 契约自有 adapter_status 字段**（schema required + enum，B1 迁移后的断言面），非 ProductContext 字段，D2 未授权删除，已带 D1/D2 收口标注；
4. `pricing-generator/SKILL.md:85`——已带退役标注的否定式表述。
生产 .py 代码（models/resolver/全仓 skills+references/scripts .sh）**零命中**。

## 6. 验证（终局，全绿）

| 项 | 结果 |
|---|---|
| shared/product_context unittest | Ran 52 tests — OK（前 53，见 §5 计数说明）|
| product-prd-generator pytest | 169 passed, 3 skipped |
| pricing-generator pytest | 31 passed |
| check_docs_consistency.sh | FAIL=0 / WARN=0 / PASS=33（RESULT: PASS）|
| git diff --check | CLEAN |
| live resolver（COMPANY_BASE 实测） | 8 产品 as_dict 无 adapter_status 键；冻结线三连 ✓ |
| LSP（改动 .py 三文件） | 0 error（仅风格 warning）|

## 7. 未做事项（与 D2 forbidden 对账）

- 三条 authority 冻结线语义零触碰（断言逐字保留并实测保绿）；
- 六份 capability 文件零改动；company.yaml / 30-products/** / docs 仓零改动；
- docs 侧 product-registry-feedback.yaml 未删；审计/决策历史档案未删；
- baseline 契约自有 adapter_status 字段未动（超出 D2 授权面，见 §5 归因 3）；
- 未 git add -A（除 D1 的 `git rm` staged 删除外全部为工作树修改）、未提交、未推送。
