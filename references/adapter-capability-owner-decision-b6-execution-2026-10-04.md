# B6 执行记录 —— 迁移 capability evidence 溯源（2026-10-04）

```text
STATUS: COMPLETED
OWNER SIGN-OFF: NOT RECORDED（仅会话授权，无独立签署记录）
AUTHORIZATION: MECH-BATCH-STANDING（一次性批量放行，用户会话授权）
SCOPE: B6 only（prd-gen adapter-capabilities.yaml 8 处 registry evidence 溯源迁移）
```

> **记录性质（必读）**：本文件是 B6 的**执行记录**，由执行会话落盘，验证结果均为本会话
> 实测。授权来源 = `references/adapter-capability-owner-decision-mechanical-batch-standing-2026-10-04.md`
> （MECH-BATCH-STANDING，session_consent）。它不是、也不得被引用为独立签署的 owner
> 批准记录（与 B1/B2/B5/B3/B4/lnkcrm-freeze-reconcile 同口径）。B6 完成**不构成**
> registry 删除、adapter_status 删除或 O4 字段删除批准。

## 1. 依据

- 迁移审计 §1-B9（adapter-capabilities.yaml evidence 溯源引用 registry 条目 8 处；
  schema 测试 :65/:346 已界定「引用 ≠ 依赖」）、§3（对齐矩阵）、§4-B6（解除条件：
  evidence 改指本审计 + owner decision 文档族，历史证据可追溯）。

## 2. 执行前扫描（本会话实测）

```bash
cd /opt/code/skill
rg -n "product-registry.yaml|adapter_status" skills/business/*/references/adapter-capabilities.yaml
```

结果：**8 处命中全部集中在 `skills/business/product-prd-generator/references/adapter-capabilities.yaml`**
（:21/:30/:39/:48/:57/:66/:75/:84）；其余 5 个 skill 的 capability 文件零命中——与
审计 §1-B9 口径一致，无需扩大处理面。

## 3. 实际修改

### 3.1 `skills/business/product-prd-generator/references/adapter-capabilities.yaml`

(a) 头部注释追加 3 行（治理红线清单末尾）：登记 evidence 溯源自 B6 起不引用
product-registry.yaml 条目，改指迁移审计 §2/§3 与 O3/Batch 2 决策记录。

(b) 8 处 evidence 首条逐一迁移（每产品证据语义保留——registry 冻结快照值 + 一致性/
差异说明均取自审计 §3 对应行）：

| product | 原首条 evidence | 新首条 evidence |
|---|---|---|
| lnkcre | `product-registry.yaml lnkcre 条目（adapter_status: implemented）` | `迁移审计-2026-10-04.md §3（registry 冻结快照 lnkcre=implemented ↔ capability 权威源一致）` |
| lnkcrm | 同型（onboarding） | §3（lnkcrm=onboarding ↔ 一致） |
| lnkchat | 同型（partial） | §3（lnkchat=partial ↔ 一致） |
| lnkchatbi | 同型（partial） | §3（lnkchatbi=partial ↔ 一致） |
| lnkreport | 同型（partial） | §3（lnkreport=partial ↔ 一致） |
| lnkvision | 同型（unsupported） | §3（lnkvision=unsupported ↔ 一致） |
| lnkgateway | `lnkgateway 条目（ontology: null，owner-confirmed unresolved）` | §3（lnkgateway：ontology+prd unresolved owner-confirmed、O11 pending 阻塞；registry 枚举不可表达 blocked，以本文件为权威） |
| lnkwebsite | `lnkwebsite 条目（仅路径登记消 Check 4 漂移信号）` | §3（lnkwebsite：2026-09-27 owner prd-only 裁定、O2 改判 not-applicable；registry 枚举不可表达，以本文件为权威） |

（新首条均以 `references/` 相对路径书写，不含 `/opt/code` 绝对路径与 commit hash，
满足 schema 测试静态禁令。）

### 3.2 `shared/product_context/tests/test_adapter_capabilities_schema.py`（确有 B6 直接需要）

两处**说明性注释**更新（授权允许项：「使其不再将 registry evidence 例外描述为当前
迁移目标」）：

- `FORBIDDEN_KEYS` 上方块注释（原 :65）：「（registry 自有字段，Batch 2 收敛范围）」
  → 「（registry 自有字段；该溯源例外已随 B6 于 2026-10-04 消除，evidence 现指向
  迁移审计与 owner decision 记录）」；
- `test_new_files_do_not_depend_on_adapter_status` docstring（原 :345-347）：同口径
  改写，删除「registry capability 维度收敛属 Batch 2（冻结）」的当前迁移目标表述。

**测试逻辑、状态矩阵（EXPECTED_MATRIX）、静态禁令（FORBIDDEN_KEYS）、全部断言零改动**
——diff 仅涉 2 处注释/docstring 文本。

## 4. 不变量核验（本会话实测）

- capability 六态状态零变化：implemented×1 / onboarding×1 / partial×3 / unsupported×1 /
  blocked×1 / not-applicable×1（schema 测试 `test_approved_first_version_matrix` +
  `test_status_distribution_matches_decision_record` 通过即证）；
- 8 产品键、`schema_version: 1`、顶层与 per-unit `verified_at: "2026-10-04"`、
  consumer_id、notes、各 unit 第二条 evidence（设计包 §3.3.A 等）零变化；
- 「product-registry」字样在 capability 文件中仅剩头部 3 行迁移说明注释（parser 跳过
  注释行）；evidence 数据区对 registry 条目的引用清零（`rg -c "迁移审计-2026-10-04.md §3"` = 8）；
- 其余 5 个 skill 的 capability 文件零改动。

## 5. 验证（本会话实测）

- capability schema：`test_adapter_capabilities_schema.py` **10 tests OK**（含
  六文件存在 / 48 格矩阵 / 8 units / 元数据契约 / O4 键级禁令自检 / 绝对路径与
  revision hash 禁令）；
- O4 门禁与冻结线：`test_adapter_status_migration_gate.py` **12 tests OK**——
  `test_lnkgateway_ontology_stays_unresolved_without_fallback`（lnkgateway 仍
  unresolved，无跨产品 fallback）、`test_lnkwebsite_stays_prd_only_not_applicable`
  （lnkwebsite 仍 prd-only / not-applicable）、
  `test_lnkcrm_code_authority_complete_under_configured_root`（lnkcrm 对账基线
  complete 保持）、`test_no_programmatic_consumer_outside_allowlist`（O4 白名单扫描）
  全部 ok；authority 冻结线不变；
- 全 suite：shared/product_context **Ran 53 tests, OK**；product-prd-generator
  `pytest -q` **169 passed / 3 skipped**（基线一致）；
- `bash references/scripts/check_docs_consistency.sh`：**FAIL=0 / WARN=0 / PASS=33**；
- `git diff --check`（skill 仓）：通过。

## 6. 未触碰的冻结范围

六态 capability status 与 verified_at、B6 清单外的任何 capability 文件、公共
capability registry（未创建）、resolver 生产逻辑、product-registry.yaml（B4 目标
文件本轮仅由 B4 授权触碰规则 6 注释，B6 未再触碰）、company.yaml、
`30-products/**`、产品代码仓、O4 字段删除、O5 其他子项、O6-O11、两仓既有未提交
修改。未提交、未推送、未使用 git add -A。

## 7. 状态

**completed**。B6 解除依据成立：8 处 evidence 溯源迁移完成（指向审计 §3 + O3/Batch 2
决策记录，历史 registry 值经审计 §3 可追溯），全部验证绿。授权来源
MECH-BATCH-STANDING（用户会话授权），独立 owner 签署不存在（OWNER SIGN-OFF:
NOT RECORDED）。
