# D1 执行记录 —— product-registry.yaml 退役（2026-10-04）

decision_basis: references/adapter-capability-owner-decision-d1-registry-retire-2026-10-04.md
status: executed（本文记录 = D1 approved_changes 第 4 条「执行记录落盘」）
executor: orchestrator（按 OPC 授权批执行）
owner_sign_off: "OWNER SIGN-OFF: RECORDED (OPC)（决策记录原文）"

## 1. 闸门核验

| 项 | 结果 |
|---|---|
| 决策记录存在 | ✓ references/adapter-capability-owner-decision-d1-registry-retire-2026-10-04.md |
| status | approved ✓ |
| decision | delete ✓ |
| owner | OPC ✓（OWNER SIGN-OFF: RECORDED (OPC)）|

## 2. 删除清单

- `skills/business/product-prd-generator/references/product-registry.yaml` —— `git rm`（staged 删除，文件自 git 索引与工作树移除；历史版本经 git 可恢复）

## 3. 引用清扫逐处（文件:行 前/后）

取证命令：`rg -n "product-registry" --glob '!references/product-registry-迁移审计*'` 整仓。
分类结果：**运行时读取 0**（`safe_load.*registry` / `exists().*product-registry` 零命中，与 backlog 盘点一致）、脚本引用 1、prose 9 处、测试注释 6 处。逐处最小修改：

| # | 文件:行（前） | 前 → 后（语义） |
|---|---|---|
| 1 | `product_prd_generator/_paths.py:41-42` | 「registry 为迁移期兼容元数据/历史镜像，不构成路径解析权威源或双源同步义务」→「registry 已退役（D1，2026-10-04 删除；产品与路径事实 = company.yaml + resolver）」 |
| 2 | `_paths.py:48` | 「registry 仅存迁移期兼容快照」→「registry 已退役，D1 2026-10-04」 |
| 3 | `_paths.py:162-166`（_legacy_fallback_enabled docstring） | 「非 skill 侧 references/product-registry.yaml…仅为迁移期兼容元数据/历史镜像」→「skill 侧已退役的 product-registry.yaml…已于 D1 2026-10-04 删除」（保留 docs 侧 feedback.yaml 历史证据辨析） |
| 4 | `_paths.py:327` | 「registry 仅存迁移期兼容快照」→「registry 已退役，D1 2026-10-04」 |
| 5 | `product-prd-generator/SKILL.md:36`（读文件表行） | 「迁移期兼容元数据…核对历史条目时读」→「已退役（D1，2026-10-04 删除）；产品与路径事实 = company.yaml + `_paths` resolver」 |
| 6 | `product-prd-generator/SKILL.md:54` | 「保留为本 skill 迁移期兼容元数据…」→「已退役（D1，2026-10-04 删除）；产品与路径事实 = company.yaml + shared.product_context resolver」 |
| 7 | `competitor-product-analyzer/SKILL.md:25-27` | 「仅是迁移期 adapter 元数据（其 adapter_status…）」→「已退役（D1，2026-10-04 删除）；产品与路径事实 = company.yaml + resolver」 |
| 8 | `pricing-generator/SKILL.md:88-90` | 「registry adapter_status 仅为迁移期冻结兼容元数据…保留，删除仍需独立 owner 批准」→「已退役（D1，2026-10-04 删除），产品与路径事实 = company.yaml + resolver」（该条 :85 resolver adapter_status 措辞归 D2 处理） |
| 9 | `AGENTS.md:221` | 「该表现保留为迁移期兼容元数据」→「该表已于 2026-10-04 D1 退役删除，产品与路径事实 = company.yaml + shared.product_context resolver」 |
| 10 | `references/scripts/check_docs_consistency.sh:216-218` | 「registry 保留为迁移期兼容快照」→「registry 已于 2026-10-04 D1 退役删除」 |
| 11 | `references/product-semantic-baseline.md:43` | 「保留为本 skill 迁移期兼容元数据…」→「已退役（D1，2026-10-04 删除；产品与路径事实 = company.yaml + shared.product_context resolver）」 |
| 12 | `references/product-governance/README.md:39,41` | :39 删「registry values frozen as a migration-period snapshot」括注；:41 迁移期注记改写为 closed by D1/D2（保留迁移审计指针） |
| 13 | `references/product-semantic-baseline.schema.json:5` | description「adapter_status here is the frozen registry compatibility vocabulary」→「follows the frozen registry compatibility vocabulary (the retired product-registry.yaml was deleted by owner decision D1, 2026-10-04)」 |
| 14 | `tests/test_product_governance_contracts.py:111-112,130-132,147` | 三处注释「冻结兼容快照」→「历史冻结快照／已随文件退役（D1 2026-10-04 删除）」 |
| 15 | `tests/test_product_authority_fixtures.py:104,174` | 两处注释同上语义 |
| 16 | `tests/test_product_semantic_contracts.py:47-49` | docstring 同上语义 |

## 4. 保留命中（不清理，逐类归因）

| 类 | 位置 | 理由 |
|---|---|---|
| 决策/执行记录与审计档案 | `references/adapter-capability-owner-decision-*.md`、`references/product-registry-迁移审计-2026-10-04.md`、`references/product-context-消费方审计-2026-10.md`、`references/adapter-capability-owner-recommendation-2026-10.md` | 历史档案不清理（授权明令） |
| 冻结 capability 文件 | `product-prd-generator/references/adapter-capabilities.yaml`（9 命中，均为指向迁移审计 §2/§3 的 evidence 溯源与 B6 头注） | 六份 capability 文件禁改（权威源非迁移垫片）；其指针指向仍存在的审计文件 |
| 指向仍存在审计文件的指针 | `product-semantic-baseline.md:81`、`test_product_governance_contracts.py:113`、governance README / schema.json 中迁移审计指针 | 被指审计文件保留在仓 |
| docs 侧 feedback 文件引用 | `_paths.py:163`「docs 仓 30-products/product-registry-feedback.yaml」 | docs 仓文件不删（D1 forbidden），引用合法 |
| shared 包（2 文件 3 处） | `shared/product_context/README.md:38`、`shared/product_context/tests/test_adapter_capabilities_schema.py:65,367` | D1 forbidden 明令不改 shared 包；README 段落改写与 shared 测试注释归 D2 同批处理 |

## 5. 迁移审计收官注记

- `references/product-registry-迁移审计-2026-10-04.md` §4 末追加「收官注记（D1，2026-10-04）——B 系列审计闭卷」：registry 物理退役、B1-B7 此前全部解除、§1-§3 自此为历史快照不再更新、D2 边界声明。

## 6. 阶段验证（全绿）

| 项 | 结果 |
|---|---|
| shared/product_context unittest | Ran 53 tests — OK |
| product-prd-generator pytest | 169 passed, 3 skipped |
| pricing-generator pytest | 31 passed |
| check_docs_consistency.sh | FAIL=0 / WARN=0 / PASS=33（RESULT: PASS） |
| git diff --check | CLEAN |
| 整仓 rg product-registry（排除 references/ 档案） | 仅剩退役标注、审计/feedback 指针、冻结 capability 文件、D2-scope shared 三处（见 §4） |

## 7. 未做事项（与 D1 forbidden 对账）

- 未删除/修改 docs 仓任何文件（product-registry-feedback.yaml 保留）；
- 未改 resolver / shared 包 / company.yaml / 30-products/** / capability 文件（六份零改动）；
- 未执行 D2（adapter_status 字段退役为独立动作，随后执行）；
- 未 git add -A、未提交、未推送（仅 `git rm` 产生的 staged 删除 + 工作树修改，提交批由 OPC 另行安排）。
