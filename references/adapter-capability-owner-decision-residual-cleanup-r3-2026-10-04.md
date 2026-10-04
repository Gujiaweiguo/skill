# RESIDUAL-CLEANUP-R3 执行记录 —— _paths.py:159 描述性引用 + lnkcrm ontology fixture 注释 + registry 规则 8 末句核对 + O3 follow_up B4/B5/B6/B7 补记（2026-10-04）

```text
STATUS: EXECUTED（目标 1/2/4 completed；目标 3 verified-no-change）
OWNER SIGN-OFF: NOT RECORDED（仅用户会话授权，无独立签署记录）
SCOPE: RESIDUAL-CLEANUP-R3 only（不延续已执行完毕的 MECH-BATCH-STANDING 或 RESIDUAL-CLEANUP-R2）
```

> **记录性质（必读）**：本文件是 RESIDUAL-CLEANUP-R3 的**执行记录**，由执行会话本身
> 落盘（非事后补录，验证结果均为本会话实测）。它记录的事实是：用户在本轮会话中
> 明确批准执行 RESIDUAL-CLEANUP-R3（含 4 个目标的逐条边界、允许文件清单、禁止
> 范围、验证命令与最终报告格式），并明文「本轮是新的用户会话授权，不继承已执行
> 完毕的 MECH-BATCH-STANDING 或 RESIDUAL-CLEANUP-R2」「除非发现真实独立签署
> 记录，否则保持 OWNER SIGN-OFF: NOT RECORDED」。它**不是**、也**不得被引用为**
> 一份独立签署的 owner 批准记录——与 B1/B2/B3/B5 系列/B4/B6/B7/
> lnkcrm-freeze-reconcile/MECH-BATCH-STANDING/R2 执行记录族同口径（§3 事实区分）。

---

## 1. 登记字段

```yaml
decision_id: RESIDUAL-CLEANUP-R3
decision_date: "2026-10-04"
record_date: "2026-10-04"
owner: "opc"
owner_basis: "本仓治理约定：一人公司，owner = opc（AGENTS.md；与既有决策记录口径一致）。owner 身份有依据，但 owner 独立签署记录不存在（见 §3）"
status: "已批准执行并已完成（1/2/4 completed；3 verified-no-change）"
authorization:
  type: "session_consent"
  source: "本轮用户会话明确批准「批准执行 RESIDUAL-CLEANUP-R3」的提示词（含 4 个目标定位、允许文件清单、严格禁止范围、逐项执行规则、验证命令清单、最终报告格式）"
  not_claimed: "不存在独立签署的 owner 批准记录（无 verbatim 签署块 / SIGN-OFF: RECORDED）"
  standing_continuity: "明确不继承已执行完毕的 MECH-BATCH-STANDING 或 RESIDUAL-CLEANUP-R2；本授权为新的、有明确边界的一次性授权"
targets:
  "1 _paths.py:159 描述性 product-registry 引用": completed
  "2 test_product_authority_fixtures.py lnkcrm ontology 行注释": completed
  "3 product-registry.yaml 规则 8 末句路径同步短语": verified-no-change
  "4 O3 follow_up B4/B5/B6/B7 完成指针": completed（四条均为追加，非已存在）
worktree_note: "三个 tracked 目标文件（_paths.py / test_product_authority_fixtures.py / product-registry.yaml）执行前已为 M 状态（未确认归属的未提交工作树修改）；目标行均位于既有 hunk 之间的未变区域（git diff --unified=0 实证），最小补丁不与任何既有 hunk 重叠，无 blocked-by-worktree-overlap。O3 记录为 untracked 新增文件，追加纯新行"
```

## 2. 逐项执行明细

### 目标 1：`_paths.py` :159（执行时实际行号 :161-163）描述性 product-registry 引用 —— completed

- **定位修正**：授权引用 R2 时代行号 :159；当前工作树该 docstring 位于
  `_legacy_fallback_enabled()`（:161-163，R2 后既有 hunk 使行号偏移）。引用对象为
  docs 仓 `30-products/product-registry-feedback.yaml`（回填反馈文件），与 skill 侧
  `product-registry.yaml` 是两个文件——R2 §6.1 登记该处语义仍有效但归属未明。
- **修改**（仅 docstring，`return False` 与函数行为零改动）：
  - 原：「证据：30-products/product-registry-feedback.yaml」，fallback 关闭。
  - 新：保留历史证据指针并明确两文件区分（「历史证据：docs 仓
    30-products/product-registry-feedback.yaml——回填反馈文件，非 skill 侧
    references/product-registry.yaml」）；追加「当前产品与路径事实来源 =
    company.yaml / resolver（本模块 resolve_product_paths，resolver-first）；skill 侧
    product-registry.yaml 仅为迁移期兼容元数据/历史镜像」。
- **重叠检查**：既有 hunk 为 `+59-69 / +202-215` 等，docstring :161-163 位于其间
  未变区域，本轮新增独立 hunk，无重叠。

### 目标 2：`tests/test_product_authority_fixtures.py` lnkcrm ontology 行注释 —— completed（非 verified-no-change）

- **核对**：原注释（:114）「ontology.yaml exists as draft v0.1; authority file
  resolvable, no accepted version yet」与当前基线不一致——registry 头部规则 9 已记
  lnkcrm 本体 accepted v1.0（release SEM-CRM-OPS-001，OPC 2026-10-02）；本会话
  live resolver 实测 `resolve_product('lnkcrm')`：ontology **status=complete，
  revision=v1.0，path=30-products/lnkcrm/ontology/ontology.yaml**，code
  **status=complete**（4323b8c，source=company.yaml）。注释过时实证成立 → 更新。
- **修改**（仅注释，5 行）：改为 lnkcrm ontology accepted v1.0（release
  SEM-CRM-OPS-001，OPC 2026-10-02，registry rule 9）+ resolver complete（revision
  v1.0，authority file 同 fixture authority_ref）+ code=complete per
  O5-lnkcrm-code reconciliation（指向下方 code fixture 注释）。
- **不变量**：fixture 数据（`authority_ref="30-products/lnkcrm/ontology/ontology.yaml"`
  与 resolver 实测 path 一致，无需改）、断言逻辑、其他产品/layer 的 reason 零改动；
  lnkcrm code fixture 块（R2 产物）未触碰。
- **重叠检查**：既有 hunk 边界 `+100-105 / +117-127`，:114 注释行位于其间未变
  区域，本轮新增独立 hunk，无重叠。

### 目标 3：`product-registry.yaml` 规则 8 末句 —— verified-no-change

- **核对**：规则 8 末句现为「本表路径字段为迁移期兼容快照/历史镜像，与代码解析
  （resolver）不构成同步义务（规则 6，B4 撤销）。」——即 B4/R2 已完成的对齐文案
  （R2 子项 A 第一行）。全文件 grep「保持同步 / 同步义务 / 路径同步」仅命中规则 6
  （B4 撤销表述本身）、规则 8 末句（撤销表述本身）与规则 10(c)（B5 对齐表述），
  **无任何残留路径同步短语**。授权要求的对齐口径已全部满足 → 零改动。
- **清单外未触碰**：规则 8 首句「以本表登记为准」（lnkvision canonical 本体历史
  登录事实，R2 §6.3 登记为清单外）与规则 6（B4 已完成内容）均未触碰；YAML 数据区
  零改动（本轮对该文件零写入）。

### 目标 4：O3 follow_up B4/B5/B6/B7 完成指针 —— completed（四条均追加）

- **核对**：follow_up 原有 7 条（3 原始 + B1 + B2 + lnkcrm 对账 + B3），逐条检索
  **无 B4/B5/B6/B7 任何条目**（R2 §6.4 登记的缺口实证仍成立）→ 四条均为追加，
  无重复。
- **追加**（follow_up 末尾纯新增 4 条，:93-96；每条含四要素：经用户会话授权执行
  并完成验证的最小事实、独立 owner 签署未记录（OWNER SIGN-OFF 仅覆盖 O3/Batch 2
  audit-only）、执行记录路径、不构成 registry 删除批准）：
  - **B4**：MECH-BATCH-STANDING 授权，规则 6 双源同步契约撤销，YAML 数据区零改动，
    相邻残留已由 R2/R3 后续授权清理；
  - **B5**：B5/B5-R1/B5-R2/B5-R5 多轮会话授权，全部目标 completed 或
    verified-no-change（含 B5-R5 对「其他会话未提交修改」表述的事实纠正），执行
    记录族路径，整体解除结论以 B5-R5 记录为准；
  - **B6**：MECH-BATCH-STANDING 授权，8 处 evidence 溯源迁移至迁移审计 §3，六态
    status / 8 产品键 / schema_version / verified_at 零变化；
  - **B7**：MECH-BATCH-STANDING 授权，C1 最小修改（docs 仓回填通道描述）+ C2
    verified-no-change（历史注记不重写）；末句附记「至此 B1-B7 全部解除；registry
    删除本身仍为独立 owner 批准动作，O4 字段删除与 O5-O11 仍冻结」。
- **不变量**：O3 原始批准块、verbatim 指令、OWNER SIGN-OFF 范围、既有 7 条历史
  条目（含 B3 条目原文）零改动——追加为纯新增行（条目计数 7 → 11）。

## 3. 事实区分（防误引）

| 命题 | 状态 | 依据 |
|---|---|---|
| 用户明确授权执行 RESIDUAL-CLEANUP-R3（会话同意，含 4 目标逐项边界与禁止范围） | **成立** | 本轮用户会话批准；指令原文明文「本轮是新的用户会话授权，不继承已执行完毕的 MECH-BATCH-STANDING 或 RESIDUAL-CLEANUP-R2」 |
| 存在独立签署的 owner 批准记录（verbatim 签署块 / SIGN-OFF: RECORDED） | **不成立，不得声称** | 全仓决策文档族中无本授权的独立签署记录；B1/B2/B3/B4/B5 系列/B6/B7/R2 记录已确立同口径区分 |

引述规则：后续任何文档引用本授权时，只能表述为「RESIDUAL-CLEANUP-R3 经用户
会话授权执行（2026-10-04，见本记录）」，不得表述为「经 owner 独立签署批准」。
**本轮完成不构成 registry 删除、adapter_status 删除、O4 字段删除或 O5-O11
任何子项的批准。**

## 4. 验证（本会话实测）

| 检查 | 结果 |
|---|---|
| prd-gen 全量（编辑后） | `uv run pytest -q`：169 passed / 3 skipped（与 B2/B4/B6/B7/R2 基线一致） |
| fixture 定向 | `tests/test_product_authority_fixtures.py`：4 passed |
| shared/product_context | `unittest discover`：Ran 53 tests, OK |
| `check_docs_consistency.sh` | FAIL=0 / WARN=0 / PASS=33（RESULT: PASS，exit 0，与历轮基线一致） |
| `git diff --check` | 通过（无 whitespace 错误） |
| registry 数据区不变性 | 本轮对该文件零写入（目标 3 verified-no-change）；`yaml.safe_load` 8 产品键完整 |
| resolver 生产逻辑 | `shared/product_context/**` 零改动（仅运行测试与只读 live 探测） |
| `_paths.py` LSP | 无新增诊断（改动仅 docstring；报错均为 AGENTS.md LSP Warning 节登记的既有环境误报类别，不在本轮编辑行） |
| `test_product_authority_fixtures.py` LSP | 仅既有环境误报（`referencing` 导入解析 / 隐式相对导入 / `in` 运算符 JsonValue 收窄，:17/:18/:20/:210——与 R2 §4 登记完全同集，均不在本轮编辑行；本轮未新增任何诊断，pytest 实测通过） |
| O3 follow_up 纯增量 | 4 条为末尾新增（:93-96），既有 7 条零改动；条目计数 7 → 11 |
| 冻结线 live 复核 | resolve_product('lnkcrm')：code=complete / ontology=complete(v1.0)；lnkgateway ontology=unresolved、lnkwebsite prd-only 由 shared 套件 53 tests OK（含 O4 门禁）背书 |

## 5. 冻结范围对账（全部未触碰）

- 未修改 product-registry.yaml（本轮零写入；数据区与头部注释均未改动）；
- 未修改 resolver 生产逻辑（`shared/product_context/**` 零改动，仅运行测试与只读探测）；
- 未修改 company.yaml、`30-products/**`、产品代码（docs 仓与产品仓零改动）；
- 未修改 capability 文件、status、evidence 或 verified_at（六份 adapter-capabilities.yaml 零改动）；
- 未删除或修改 adapter_status；未执行 O4 字段删除；未执行 O5 其他子项；未执行 O6-O11；
- 未处理 R3 清单外的 prose、测试或历史记录（含 registry 规则 8 首句「以本表登记为准」、B1-B7 各执行记录原文、迁移审计 §1/§2 快照）；
- 未使用 git add -A、未提交、未推送；
- 未回退/覆盖/清理既有未提交工作树修改。

## 6. 遗留与同步事项（清单外，登记不处理）

1. registry 规则 8 首句「以本表登记为准」（lnkvision canonical 本体历史登记事实）
   ——R2 §6.3 与本轮授权均未开放，维持未触碰。
2. B1-B7 状态条目现已全部补记 O3 follow_up（B1/B2/B3 by 原有，lnkcrm 对账 by
   原有，B4/B5/B6/B7 by 本轮）；后续阻塞项状态变化仍按审计 §7 同步。
3. registry 删除、O4 字段删除、O5 其余子项、O6-O11 全部维持冻结，各自需独立授权。
4. 版本控制：本记录 untracked 新增；全仓未提交、未推送；既有未提交工作树修改
   原样保留。

## 7. 证据路径索引（均已实物核验存在）

- `references/product-registry-迁移审计-2026-10-04.md` §4（B3/B4/B6/B7/O5-lnkcrm-code/R2 状态注记；本轮追加 R3 注记）
- `references/adapter-capability-owner-decision-residual-cleanup-r2-2026-10-04.md` §6（本轮 4 个目标的登记来源）
- `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md` follow_up（B4/B5/B6/B7 新条目 :93-96）
- `references/adapter-capability-owner-decision-b3/b4/b5/b5-r1/b5-r2/b5-r5/b6/b7-execution-2026-10-04.md`（各条目引用的执行记录）
- `references/adapter-capability-owner-decision-lnkcrm-freeze-reconcile-2026-10-04.md` §6.4（目标 2 登记来源）
- `skills/business/product-prd-generator/references/product-registry.yaml` 头部规则 8/9（目标 2/3 核对依据，零改动）
- 修改文件：`skills/business/product-prd-generator/product_prd_generator/_paths.py`（docstring）、`skills/business/product-prd-generator/tests/test_product_authority_fixtures.py`（注释）、`references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`（follow_up 追加）
