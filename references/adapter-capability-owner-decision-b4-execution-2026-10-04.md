# B4 执行记录 —— 撤销 product-registry.yaml 头部规则 6 双源同步义务（2026-10-04）

```text
STATUS: COMPLETED
OWNER SIGN-OFF: NOT RECORDED（仅会话授权，无独立签署记录）
AUTHORIZATION: MECH-BATCH-STANDING（一次性批量放行，用户会话授权）
SCOPE: B4 only（product-registry.yaml 头部规则 6 注释改写）
```

> **记录性质（必读）**：本文件是 B4 的**执行记录**，由执行会话落盘，验证结果均为本会话
> 实测。授权来源 = `references/adapter-capability-owner-decision-mechanical-batch-standing-2026-10-04.md`
> （MECH-BATCH-STANDING，session_consent）。它不是、也不得被引用为独立签署的 owner
> 批准记录（与 B1/B2/B5/B3/lnkcrm-freeze-reconcile 同口径）。B4 完成**不构成**
> product-registry.yaml 删除批准或 adapter_status 删除批准。

## 1. 依据

- 迁移审计 `references/product-registry-迁移审计-2026-10-04.md` §2（路径字段行：
  「双源同步税仍在 → §4-B4」）、§4-B4（解除条件：路径解析收敛为单一来源后撤销同步义务）；
- `product-registry.yaml` 头部规则 6 原文（「本表与其保持同步（改一边必须改另一边）」）。

## 2. 执行前确认（本会话实测）

| 前置条件 | 证据 |
|---|---|
| `_paths.resolve_product_paths()` 已是 resolver-first | 函数在 `_paths.py:192`，经 `_shared_product_context()` 解析；生产路径不加载 registry |
| 生产代码不读取 product-registry.yaml | `rg "yaml.safe_load\|safe_load\|import yaml" _paths.py` 零命中（exit 1）；「product-registry」全部 4 处命中（:40/:44/:159/:319）均为 module docstring / 注释 / 报错引导文案 |
| registry 路径字段只是兼容镜像 | 迁移审计 §1「生产代码零读取」结论复核一致；`check_docs_consistency.sh` Check 4 对账面已迁移 company.yaml（B2） |
| 不需要修改 resolver 生产逻辑 | 本轮 `shared/product_context/**` 生产代码零改动（仅 schema 测试两处说明性注释属 B6） |

## 3. 实际修改

唯一目标文件：`skills/business/product-prd-generator/references/product-registry.yaml`
——仅头部规则 6 注释（YAML 数据区零改动）。

原文：

```yaml
# 6. 代码侧路径解析唯一权威源是 skill 的 _paths.resolve_product_paths()，
#    本表与其保持同步（改一边必须改另一边）。
```

改为：

```yaml
# 6. 路径解析的运行时唯一权威源是 resolver——skill 的 _paths.resolve_product_paths()
#    （resolver-first，经 shared.product_context，未配置/null 一律显式报错）。本表不
#    承担运行时路径解析，保留为迁移期兼容元数据/历史镜像；路径字段与 resolver 不
#    构成双源同步义务——原「改一边必须改另一边」契约已撤销（B4，2026-10-04，见
#    references/product-registry-迁移审计-2026-10-04.md §4-B4）。
```

改写覆盖授权要求的三点语义：resolver 为运行时唯一权威源；本表为迁移期兼容元数据/
历史镜像；不构成双源同步义务。

**数据区核验**：`git diff -U0` 全文件非注释 +/- 行数 = **0**（含既往会话的 B3 规则 1、
O3 规则 10 注释 hunk 在内，全部改动均为 `#` 注释行）；`yaml.safe_load` 解析成功，
8 产品键完整（lnkchat/lnkchatbi/lnkcre/lnkcrm/lnkgateway/lnkreport/lnkvision/lnkwebsite），
lnkcre docs_root 等字段值不变。

## 4. 发现的相邻同步表述（登记未改，均不在授权「仅规则 6」范围内）

| 位置 | 表述 | 处置 |
|---|---|---|
| 同文件规则 8 末句 | 「本表与代码解析保持同步。」 | 未改——审计 §4-B4 只登记规则 6；按授权「只处理迁移审计明确属于 B4 的引用」，此句不属 B4 登记范围，登记为残留 |
| 同文件规则 10(c) 括注 | 「（含注册入口、规则 6 与 _paths 的路径同步对）」 | 未改——「路径同步对」措辞在 B4 后语义过时，但规则 6 指针仍可解析；规则 10 不在授权范围，登记为残留 |
| `_paths.py` :40/:44/:319 | 「登记见/登记在 product-registry.yaml」 | 未改——描述性登记指针（canonical 布局说明），非同步义务契约 |
| 迁移审计 §2 路径字段行 | 「registry 按头部规则 6 与 _paths 保持同步（双源同步税仍在 → §4-B4）」 | 未重写——快照原文按 B1/B2 惯例保留，B4 状态由 §4 注记承载 |

以上残留不构成现行「修改 registry 必须同步 _paths」的强制契约主体（主体即规则 6，
已撤销）；如需清理属后续独立授权（可并入 B5 类文档级批次）。

## 5. 验证（本会话实测）

- `uv run pytest -q`（product-prd-generator）：**169 passed / 3 skipped**（B2/B5-R5/
  lnkcrm-freeze 基线一致）；
- `uv run python -m unittest discover -s tests -p "test_*.py"`（shared/product_context）：
  **Ran 53 tests, OK**；
- `bash references/scripts/check_docs_consistency.sh`：**FAIL=0 / WARN=0 / PASS=33
  （RESULT: PASS）**；
- `git diff --check`（skill 仓）：通过；
- registry YAML 解析 + 8 产品键核验：通过（§3）。

## 6. 未触碰的冻结范围

resolver 生产逻辑（`shared/product_context/**` 生产代码）、company.yaml、
`30-products/**`、产品代码仓、registry YAML 数据区（含路径字段与 adapter_status）、
O4 字段删除、O5 其他子项、O6-O11、B6/B7 目标文件、两仓既有未提交修改（全部原样
保留）。未提交、未推送、未使用 git add -A。

## 7. 状态

**completed**。B4 解除依据成立：实际修改（规则 6 注释改写）与验证（全 suite 绿 +
数据区零改动核验）均完成。授权来源 MECH-BATCH-STANDING（用户会话授权），独立 owner
签署不存在（OWNER SIGN-OFF: NOT RECORDED）。
