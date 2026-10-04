# RESIDUAL-CLEANUP-R4 执行记录 —— registry 规则 8 首句「以本表登记为准」对齐 + 有界复扫 + 迁移期 prose 残留族关闭宣告（2026-10-04）

```text
STATUS: EXECUTED（目标 1 completed，非 verified-no-change；有界复扫 0 新残留）
OWNER SIGN-OFF: NOT RECORDED（仅用户会话授权，无独立签署记录）
SCOPE: RESIDUAL-CLEANUP-R4 only（不延续已执行完毕的 MECH-BATCH-STANDING、R2、R3）
```

> **记录性质（必读）**：本文件是 RESIDUAL-CLEANUP-R4 的**执行记录**，由执行会话本身
> 落盘（非事后补录，验证结果均为本会话实测）。它记录的事实是：用户在本轮会话中
> 明确批准执行 RESIDUAL-CLEANUP-R4（含唯一已登记残留的逐条边界、有界复扫关键词
> 清单与判定规则、允许文件清单、禁止范围、验证命令与最终报告格式），并明文
> 「本轮是新的用户会话授权，不继承已执行完毕的 MECH-BATCH-STANDING、R2、R3」
> 「除非发现真实独立签署记录，否则保持 OWNER SIGN-OFF: NOT RECORDED」。它**不是**、
> 也**不得被引用为**一份独立签署的 owner 批准记录——与 B1-B7 系列/
> lnkcrm-freeze-reconcile/MECH-BATCH-STANDING/R2/R3 执行记录族同口径（§4 事实区分）。

---

## 1. 登记字段

```yaml
decision_id: RESIDUAL-CLEANUP-R4
decision_date: "2026-10-04"
record_date: "2026-10-04"
owner: "opc"
owner_basis: "本仓治理约定：一人公司，owner = opc（AGENTS.md；与既有决策记录口径一致）。owner 身份有依据，但 owner 独立签署记录不存在（见 §4）"
status: "已批准执行并已完成（目标 1 completed；有界复扫 6 命中全部 intended/不构成，0 新残留，0 needs-separate-authorization）"
authorization:
  type: "session_consent"
  source: "本轮用户会话明确批准「批准执行 RESIDUAL-CLEANUP-R4」的提示词（含唯一目标定位、有界复扫关键词与判定规则、允许文件清单、严格禁止范围、验证命令、最终报告九项格式）"
  not_claimed: "不存在独立签署的 owner 批准记录（无 verbatim 签署块 / SIGN-OFF: RECORDED）"
  standing_continuity: "明确不继承已执行完毕的 MECH-BATCH-STANDING、R2、R3；本授权为新的、有明确边界的一次性授权，目的是结束「逐条补残留」循环并宣告关闭"
targets:
  "1 product-registry.yaml 规则 8 首句「以本表登记为准」": completed
rescan:
  scope: "仅 skills/business/product-prd-generator/references/product-registry.yaml 单一文件"
  keywords: "以本表为准 / 以本表登记为准 / 保持同步 / 同步对 / 双源 / 改一边必须改另一边 / 唯一权威源（指本表）/ 本表为权威"
  hits: 6
  verdicts: "5 intended + 1 关键词语义不构成（规则 7「双源不并存」指 out/prd 生成区 vs canonical 晋升机制，非本表义务）；0 新残留；0 needs-separate-authorization"
worktree_note: "目标文件执行前已为 M 状态（未确认归属的未提交工作树修改，含 B3/B4/O3/R2 各轮 hunk）。既有 hunk 边界（git diff --unified=0 实证）：+4,7（B3 规则 1）/ +17,5（B4 规则 6）/ +31,2（R2 规则 8 末句，旧行 22）/ +39,28（O3 规则 10）。本轮目标行为旧行 21（HEAD 未变行），位于既有 hunk 改动行之外；编辑后合并显示 hunk @@ -21,2 +30,4 @@ 中旧行 21 的变化属本轮、旧行 22 的变化属 R2 既有工作，逐行归属可分离，无 blocked-by-worktree-overlap"
```

## 2. 目标 1 执行明细：规则 8 首句「以本表登记为准」—— completed（非 verified-no-change）

- **前置核对（排除 verified-no-change）**：R3 执行记录 §6.1 明确登记该短语为清单外
  「维持未触碰」残留；本会话编辑前 grep 实证短语仍存在于 :30（R4 前行号）。该短语
  **未在任何既有轮次被处理** → 执行实际修改。
- **修改**（仅注释区 1 行扩为 2 行，YAML 数据区零改动）：

  原文（:30）：

  ```yaml
  #    以本表登记为准）。未注册产品 tier-4 商管兜底带跨域污染闸门（非 lanlnk 公司
  ```

  改为（:30-31）：

  ```yaml
  #    现行事实来源 = company.yaml / 治理 README / resolver，本表仅为迁移期兼容元数据/
  #    历史镜像）。未注册产品 tier-4 商管兜底带跨域污染闸门（非 lanlnk 公司
  ```

  语义对齐（授权三点全落）：撤除「以本表登记为准」的 registry 权威源表述；对齐
  B4/B3 口径（产品与路径/canonical 布局现行事实来源 = company.yaml / 治理 README /
  resolver；本表仅为迁移期兼容元数据/历史镜像）。
- **保留的既有事实**（:28-29 未触碰）：「_PRODUCT_CANONICAL_DIR 已登记
  lnkreport/lnkchatbi/lnkvision（2026-09-26 同日修复，回归闸 tests/test_paths.py；
  lnkvision 无 ontology.yaml，canonical 本体为域知识.md」全部保留。
- **未触碰范围**：规则 6（B4 产物）、规则 8 其余句子（:32-33 R2 产物原样）、规则 9、
  规则 10 全部未改；新措辞不含任何复扫关键词（无「唯一权威源/双源/同步/以本表为准」
  字样），不引入新残留。

## 3. 有界复扫结果（单一文件，授权关键词清单，6 命中 0 新残留）

| 行 | 命中关键词 | 判定 | 依据 |
|---|---|---|---|
| :17 | 唯一权威源 | intended | 规则 6 B4 撤销表述；「唯一权威源」指 resolver，非本表 |
| :20 | 双源 / 改一边必须改另一边 | intended | B4 撤销声明本体（「契约已撤销（B4，2026-10-04）」） |
| :25 | 双源 | 不构成（关键词语义外） | 规则 7 方案 B「双源不并存」指 out/prd 生成区与 canonical 晋升机制，非本表权威/同步义务表述；不改动 |
| :50 | 唯一权威源 | intended | 规则 10(b) O3/Batch 2 对齐表述；权威源已外迁 capability 文件，非本表 |
| :60 | 同步对 | intended | 规则 10(c) R2 对齐表述（「本表与 _paths **不构成**路径同步对」否定式） |
| （无） | 以本表为准 / 以本表登记为准 / 保持同步 / 本表为权威 | **零命中** | 目标本轮已撤；全文件无本表权威源/同步义务来源措辞残留 |

**结论**：授权复扫范围内 **0 项 needs-separate-authorization**，无「与目标 1 同一
措辞」的可一并处理项（不存在第二处）。

## 4. 事实区分（防误引）

| 命题 | 状态 | 依据 |
|---|---|---|
| 用户明确授权执行 RESIDUAL-CLEANUP-R4（会话同意，含目标边界、复扫规则与禁止范围） | **成立** | 本轮用户会话批准；指令原文明文「本轮是新的用户会话授权，不继承已执行完毕的 MECH-BATCH-STANDING、R2、R3」 |
| 存在独立签署的 owner 批准记录（verbatim 签署块 / SIGN-OFF: RECORDED） | **不成立，不得声称** | 全仓决策文档族中无本授权的独立签署记录；B1-B7/R2/R3 记录已确立同口径区分 |

引述规则：后续任何文档引用本授权时，只能表述为「RESIDUAL-CLEANUP-R4 经用户
会话授权执行（2026-10-04，见本记录）」，不得表述为「经 owner 独立签署批准」。
**本轮完成不构成 registry 删除、adapter_status 删除、O4 字段删除或 O5-O11
任何子项的批准。**

## 5. 验证（本会话实测）

| 检查 | 结果 |
|---|---|
| prd-gen 全量 | `uv run pytest -q`：**169 passed / 3 skipped**（与 B2/B4/B6/B7/R2/R3 基线一致） |
| shared/product_context | `unittest discover`：**Ran 53 tests, OK** |
| `check_docs_consistency.sh` | **FAIL=0 / WARN=0 / PASS=33（RESULT: PASS）**（历轮基线一致） |
| `git diff --check` | 通过（无 whitespace 错误） |
| 数据区解析前后一致性 | 编辑前后各 `yaml.safe_load` + `json.dumps(sort_keys=True)` 双 dump：**逐字节一致**（sha256 `041b6c704a76bf4be219ca17f3a476b786d5581b22f1758085047208f6385145` 同值）；8 产品键完整（lnkchat/lnkchatbi/lnkcre/lnkcrm/lnkgateway/lnkreport/lnkvision/lnkwebsite） |
| 冻结快照值不变 | lnkcrm `code_root: null` / `adapter_status: onboarding`；lnkgateway `ontology: null`；lnkwebsite `ontology: null`（lnkvision ontology=域知识.md 维持登记事实） |
| 改动纯注释实证 | `git diff -U0` 全文件非注释 +/- 行 = 0（全部变更行以 `#` 开头，含既有 B3/B4/O3/R2 hunk 在内） |
| 既有工作树修改保留 | 执行前 git status 的 25 个 M 文件与全部 untracked 条目原样保留；本轮仅新增本记录 + 迁移审计注记，registry 仅增本轮 hunk |

## 6. 冻结范围对账（全部未触碰）

- 未修改 registry YAML 数据区（任何字段、任何产品条目）；未删除/重命名 registry 或
  adapter_status；
- 未执行 O4 字段删除、O5 其余子项、O6-O11；
- 未修改 resolver 生产逻辑（`shared/product_context/**` 零改动，仅运行测试）、
  company.yaml、`30-products/**`、产品代码；
- 未修改 capability 文件、status、evidence、verified_at；
- 未修改 `_paths.py`、tests、其他 skill 的 references；
- 未处理（也不存在）复扫标记 needs-separate-authorization 的项；
- 未使用 git add -A、未提交、未推送；未回退/覆盖/清理既有未提交工作树修改。

## 7. 迁移期 prose 残留族关闭宣告

**宣告**：product-registry.yaml「迁移期 prose 残留族」——即把本表表述为权威源或
双源同步义务来源的注释措辞族——就此**关闭**。依据：

1. 唯一已登记残留（规则 8 首句「以本表登记为准」，R3 §6.1 登记）本轮已对齐；
2. 授权关键词有界复扫：6 命中全部为 intended 撤销表述或不构成本表义务的关键词
   语义外命中，0 新残留，0 needs-separate-authorization；
3. 前序轮次已闭合的族内项：规则 6（B4）、规则 8 末句（R2）、规则 10(c)（R2）、
   规则 1（B3）、规则 10 整体（O3）均为已完成对齐文案。

**关闭边界**：本宣告仅覆盖本文件 prose 残留族（授权范围内的「逐条补残留」循环就此
结束）；registry 删除本身、adapter_status 删除、O4 字段删除、O5 其余子项、O6-O11
均为独立 owner 批准动作，**维持冻结**，不因本宣告解冻。

## 8. 证据路径索引（均已实物核验存在）

- `references/product-registry-迁移审计-2026-10-04.md` §4（R3 状态注记 + 本轮追加 R4 注记）
- `references/adapter-capability-owner-decision-residual-cleanup-r3-2026-10-04.md` §6.1（唯一已登记残留的登记来源）
- `references/adapter-capability-owner-decision-b4-execution-2026-10-04.md`（B4 口径依据）
- `skills/business/product-prd-generator/references/product-registry.yaml` 头部规则 8（:28-33，本轮 :30-31 修改）
- 修改文件：`skills/business/product-prd-generator/references/product-registry.yaml`（仅注释 1 行→2 行）、本记录、迁移审计（纯追加 R4 注记）
