# RESIDUAL-CLEANUP-R2 执行记录 —— B4 文案残留 + lnkcrm authority fixture 旧 reason + O3 follow_up B3 状态补记（2026-10-04）

```text
STATUS: EXECUTED（已批准执行；子项 A/B/C 全部 completed）
OWNER SIGN-OFF: NOT RECORDED（仅用户会话授权，无独立签署记录）
SCOPE: RESIDUAL-CLEANUP-R2 only（子项 A/B/C；不延续 MECH-BATCH-STANDING）
```

> **记录性质（必读）**：本文件是 RESIDUAL-CLEANUP-R2 的**执行记录**，由执行会话本身
> 落盘（非事后补录，验证结果均为本会话实测）。它记录的事实是：用户在本轮会话中
> 明确批准执行 RESIDUAL-CLEANUP-R2（含子项 A/B/C 逐条边界、允许文件清单、禁止
> 范围、验证命令与最终报告格式），并明文「本授权为用户会话授权，不代表独立 owner
> 签署。除非有真实签署证据，否则记录为 OWNER SIGN-OFF: NOT RECORDED」与「不延续
> 已经执行完毕的 MECH-BATCH-STANDING」。它**不是**、也**不得被引用为**一份独立
> 签署的 owner 批准记录——与 B1/B2/B5/B3/lnkcrm-freeze-reconcile/MECH-BATCH-STANDING
> 执行记录族同口径（§3 事实区分）。

---

## 1. 登记字段

```yaml
decision_id: RESIDUAL-CLEANUP-R2
decision_date: "2026-10-04"
record_date: "2026-10-04"
owner: "opc"
owner_basis: "本仓治理约定：一人公司，owner = opc（AGENTS.md；与既有决策记录口径一致）。owner 身份有依据，但 owner 独立签署记录不存在（见 §3）"
status: "已批准执行并已完成（A/B/C 全部 completed）"
authorization:
  type: "session_consent"
  source: "本轮用户会话明确批准「批准执行 RESIDUAL-CLEANUP-R2」的提示词（含子项 A/B/C 目标定位、允许文件清单、禁止范围、执行记录与审计回写要求、验证命令清单、最终报告格式）"
  not_claimed: "不存在独立签署的 owner 批准记录（无 verbatim 签署块 / SIGN-OFF: RECORDED）"
  standing_continuity: "明确不延续已执行完毕的 MECH-BATCH-STANDING；本授权为新的、有明确边界的一次性批量授权"
subitems:
  A: completed
  B: completed
  C: completed
worktree_note: "三个目标 tracked 文件（product-registry.yaml / _paths.py / test_product_authority_fixtures.py）执行前已为 M 状态（既有未提交修改，归属未确认）；本轮以最小补丁叠加，未回退/未覆盖/未清理/未整文件重写，无 blocked-by-worktree-overlap（目标段落可安全分离）"
```

## 2. 子项执行明细

### 子项 A：撤除 B4 范围外的过时同步措辞 —— completed

B4 状态注记与 B4 执行记录登记的相邻残留，按授权对齐到现行事实
（company.yaml/resolver 为路径与 authority 来源；`_PRODUCT_CANONICAL_DIR` 为代码侧
目录别名/映射实现细节、非产品台账来源、需补时仍维护；registry 为迁移期兼容
元数据/历史镜像，无路径解析权威源或双源同步义务；注册入口 = `scripts/onboard.sh
product` + company.yaml products）：

| 位置 | 修改 |
|---|---|
| `product-registry.yaml` 头部规则 8 末句 | 「本表与代码解析保持同步。」→「本表路径字段为迁移期兼容快照/历史镜像，与代码解析（resolver）不构成同步义务（规则 6，B4 撤销）。」 |
| `product-registry.yaml` 头部规则 10(c) 括注 | 「（含注册入口、规则 6 与 _paths 的路径同步对）」→ 注册入口改指 onboard.sh product + company.yaml products（规则 1）、撤销路径同步对表述（规则 6）、补 `_PRODUCT_CANONICAL_DIR` 实现细节定性（非台账来源，canonical 目录名与 pid 不同时仍需代码侧补映射，先例 lnkcrm）。规则 10(c) 其余部分（Check 4 对账面 = company.yaml products 等，B2/B5 已对齐）未动 |
| `_paths.py` 模块 docstring（原 :40） | 「canonical 布局登记见 references/product-registry.yaml」→ canonical 布局与路径事实以 company.yaml / resolver（`resolve_product_paths`，resolver-first）为准；registry 为迁移期兼容元数据/历史镜像，不构成路径解析权威源或双源同步义务 |
| `_paths.py` 模块 docstring（原 :44） | 「登记在 product-registry.yaml」→ 路径事实以 company.yaml / resolver 为准（registry 仅存迁移期兼容快照）；同段 `_PRODUCT_CANONICAL_DIR` 句补「代码侧目录别名/映射实现细节，非产品台账来源（产品台账 = company.yaml products）」定性 |
| `_paths.py` `_PRODUCT_CANONICAL_DIR` 注释（原 :319） | 「登记在 product-registry.yaml」→ 路径事实以 company.yaml / resolver 为准，registry 仅存迁移期兼容快照 |

- 规则 6（B4 已完成改写）未触碰；未扩展到其他旧引用。`_paths.py` :159
  （product-registry-feedback.yaml，docs 侧回填反馈文件引用）与规则 8 句中
  「以本表登记为准」（lnkvision 历史登记事实描述，授权仅开放末句）均为清单外，
  未触碰（见 §6 遗留）。
- 行为零改动：仅注释/docstring；test_paths.py 58 项随全量套件通过。

### 子项 B：对齐 authority fixture 的 lnkcrm code 基线 —— completed

**语义判定**：fixture 为**当前产品 authority 基线镜像**，非有意构造的历史/负例——
依据：(1) 文件 docstring「Seven-product layer fixtures **mirroring** the
product-semantic-baseline contract … plus per-layer authority or an explicit
unresolved state」；(2) B1 已把镜像对账面迁至 baseline 契约
（`test_fixture_profiles_match_baseline_contract_and_business_tool_split`，
2026-10-04）；(3) lnkcrm-freeze-reconcile 执行记录 §6.4 明确登记 lnkcrm 旧 reason
字符串「如需对齐属后续授权」——本轮授权即该后续授权。故按 ratified 基线修改，
非 verified-no-change。

| 修改 | 内容 |
|---|---|
| `_ref()` helper | 新增可选 `revision` 参数（resolved 时写入；schema `layer-reference.schema.json` 本就声明 `revision` 字段，`additionalProperties: false` 下合法） |
| lnkcrm code fixture | `reason="Code repository unresolved: no repo yet (planned, named 2026-09-26)"` → `authority_ref="/opt/code/lnkcrm"` + `revision="4323b8c9f6f195dd82083348dd6e854e7360afa3"`（status → resolved），注释记录 source = company.yaml code_root（docs c41a978 ratified）、code authority complete per resolver、revision 为 ratify 时点快照 |
| `test_registry_nulls_stay_unresolved_without_invented_authority` | unresolved_expectations 移除 `("lnkcrm", "code"): "no repo"`（依据测试当前结构的最小语义正确调整），同测试内补三条正向断言钉新基线（status=resolved + authority_ref=/opt/code/lnkcrm + revision 非空，防静默回退） |

- 未弱化任何 unresolved reason 检查：lnkcrm prd="planned"、lnkgateway
  ontology="no owner-confirmed"、lnkgateway prd="no prd_root" 三条断言原样保留；
  跨产品 fallback 检查原样保留（"/opt/code/lnkcrm" 无撞车）。
- lnkcrm fixture 的 ontology 行注释（"no accepted version yet"）为 ontology 维度，
  不在本轮 code 维度授权内，未触碰（见 §6 遗留）。
- registry YAML 数据区不动：registry lnkcrm `code_root: null` 保持冻结快照原值
  （现行基线经 company.yaml/resolver 表达，registry 不承担该职责——授权禁止项
  「修改 registry YAML 数据区」遵守，本会话实测 yaml.safe_load 确认）。

### 子项 C：核对并补齐 O3 follow_up 中的 B3 状态 —— completed（追加，非 verified-no-change）

- **核对**：O3 决策记录 follow_up 原有 6 条（3 条原始 + B1 + B2 + lnkcrm code 对账），
  **无 B3 条目**；lnkcrm 条目末尾明文「B3 follow_up 补记缺口仍待独立授权」；
  迁移审计 §4 已有 B3 状态注记（已解除）与 B3 执行记录 §6.1 登记该缺口——缺失实证成立。
- **追加**：follow_up 末尾新增一条简洁状态指针（现 :92），含四要素：B3 经用户
  会话授权执行并验证通过（注册入口迁移 onboard.sh product + company.yaml
  products，YAML 数据区零改动，细节以执行记录为准）；独立 owner 签署未记录
  （OWNER SIGN-OFF 仅覆盖 O3/Batch 2 audit-only，不得表述为经 owner 独立签署批准）；
  执行记录路径 `references/adapter-capability-owner-decision-b3-execution-2026-10-04.md`；
  B3 完成不构成 registry 删除批准。
- O3 原始批准块、verbatim 指令、OWNER SIGN-OFF 范围、既有 follow_up 历史条目
  （含 lnkcrm 条目原文）零改动——追加为纯新增行。

## 3. 事实区分（防误引）

| 命题 | 状态 | 依据 |
|---|---|---|
| 用户明确授权执行 RESIDUAL-CLEANUP-R2（会话同意，含 A/B/C 逐项边界与禁止范围） | **成立** | 本轮用户会话批准；指令原文明文「本授权为用户会话授权，不代表独立 owner 签署」 |
| 存在独立签署的 owner 批准记录（verbatim 签署块 / SIGN-OFF: RECORDED） | **不成立，不得声称** | 全仓决策文档族中无本授权的独立签署记录；B1/B2/B5/B3/lnkcrm/MECH-BATCH-STANDING 记录已确立同口径区分 |

引述规则：后续任何文档引用本授权时，只能表述为「RESIDUAL-CLEANUP-R2 经用户
会话授权执行（2026-10-04，见本记录）」，不得表述为「经 owner 独立签署批准」。
**A/B/C 完成不构成 registry 删除、adapter_status 删除、O4 字段删除或 O5-O11
任何子项的批准。**

## 4. 验证（本会话实测）

| 检查 | 结果 |
|---|---|
| 前置基线（编辑前先跑，用于归因） | prd-gen `uv run pytest -q`：169 passed / 3 skipped；shared `unittest discover`：53 tests OK |
| prd-gen 全量（编辑后） | 169 passed / 3 skipped（与前基线一致，零回归零新增） |
| fixture 定向 | `tests/test_product_authority_fixtures.py`：4 passed |
| shared/product_context | 53 tests OK |
| `check_docs_consistency.sh` | FAIL=0 / WARN=0 / PASS=33（RESULT: PASS，exit 0，与 B2/B4/B6/B7 基线一致） |
| `git diff --check` | 通过（无 whitespace 错误） |
| registry 数据区不变性 | `git diff -U0` 全部非注释变更行 = **0**（纯注释）；`yaml.safe_load` 8 产品键完整；lnkcrm `code_root: null` / `adapter_status: onboarding`、lnkgateway `ontology: null`、lnkwebsite `ontology: null` 冻结快照原值 |
| `_paths.py` LSP | 无 error（改动仅注释/docstring） |
| `test_product_authority_fixtures.py` LSP | 仅既有环境误报（`referencing` 导入解析、隐式相对导入、`in` 运算符 JsonValue 收窄——均在既有代码行，AGENTS.md LSP Warning 节登记类别；本轮未新增任何诊断，pytest 实测通过） |
| O3 follow_up 纯增量 | B3 条目为末尾新增（:92），既有 6 条含 lnkcrm 原文零改动；批注项计数 6 → 7 |
| docs 仓 | 零改动（只读检查；本轮全部目标均在 skill 仓） |

## 5. 冻结范围对账（全部未触碰）

- 未删除 product-registry.yaml 或任何字段；未修改 registry YAML 数据区（git 实证纯注释 diff）；
- 未修改 resolver 生产逻辑（`shared/product_context/**` 零改动，本轮仅运行其测试）；
- 未修改 capability 状态、evidence 或 verified_at（六份 adapter-capabilities.yaml 零改动）；
- 未修改 company.yaml、`30-products/**`、产品代码（docs 仓与产品仓零改动）；
- 未删除/重命名 adapter_status；未执行 O4 字段删除；未执行 O5 其他子项或 O6-O11；
- 未处理未列入本授权的残留（见 §6）；未使用 git add -A、未提交、未推送；
- 未回退/覆盖/清理两仓既有未提交修改。

## 6. 遗留与同步事项（清单外，登记不处理）

1. `_paths.py` :159 —— docs 侧 `product-registry-feedback.yaml`（回填反馈通道）引用，
   指向 docs 仓另一文件，语义仍有效，未触碰。
2. `test_product_authority_fixtures.py` lnkcrm ontology 行注释（"no accepted version
   yet"）—— registry 规则 9 已记 ontology accepted v1.0（OPC 2026-10-02），该注释
   属 ontology 维度旧事实，不在本轮 code 维度授权内。
3. registry 规则 8 句中「以本表登记为准」（lnkvision canonical 本体历史登记事实）——
   授权仅开放规则 8 **末句**，该短语未触碰。
4. B4/B6/B7 各自 follow_up 条目与 B5 系列 follow_up 条目是否补记 O3 follow_up ——
   本授权仅涵盖 B3，其余不代行（如需补记属后续授权）。
5. 版本控制：本记录 untracked 新增；全仓未提交、未推送；既有未提交工作树修改原样保留。

## 7. 证据路径索引（均已实物核验存在）

- `references/product-registry-迁移审计-2026-10-04.md` §4（B3/B4/B6/B7/O5-lnkcrm-code 状态注记）
- `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md` follow_up（B3 新条目 :92）
- `references/adapter-capability-owner-decision-b3-execution-2026-10-04.md` §6.1（补记缺口登记，本轮闭合对象）
- `references/adapter-capability-owner-decision-lnkcrm-freeze-reconcile-2026-10-04.md` §6.4（fixture 旧 reason 登记为后续授权，本轮授权即其落地）
- `references/adapter-capability-owner-decision-mechanical-batch-standing-2026-10-04.md`（B4 残留登记来源；本轮不延续）
- `skills/business/product-prd-generator/references/product-governance/layer-reference.schema.json`（fixture `revision` 字段合法性）
- 修改文件：`skills/business/product-prd-generator/references/product-registry.yaml`（注释）、`skills/business/product-prd-generator/product_prd_generator/_paths.py`（注释/docstring）、`skills/business/product-prd-generator/tests/test_product_authority_fixtures.py`
