# 跨仓交接与收尾（L2/L3 共用）

本文件承载 docs 仓与目标项目仓之间的交接字段、启用规则和收尾报告模板。不对应单独短口令：被 `artifact-to-changes.md`、`prd-diff-consume.md`、`active-change-triage.md`、`multi-scope.md`（L2）和 `prd-writeback.md`（L3）在需要跨仓协同时引用。

## 适用条件

- **L2**：多 change、跨 scope、依赖排序或批次交付。典型：多个 PRD gap、多个 active changes、根 scope 与子 scope 并存、数据库/权限/路由/共享组件存在独占边界、多 change 波次或欠账清理。
- **L3**：交付回写、canonical 晋升、正式对账或可审计基线。典型：回写 PRD、change 已归档并需要回写 docs、ontology/PRD canonical 晋升、多 change 波次正式收尾。

## 公共产品上下文

跨仓交接必须消费 resolver 输出，不得从产品名拼接代码路径。交接包至少保留：

```text
公司：
- company_id：
- company_base：

产品：
- product_id：
- product_name：

三层 authority：
- ontology：path / status / revision
- prd：path / status / revision
- code：path / status / revision

解析状态：
- company：
- product：
- ontology：
- prd：
- code：
```

`code` 为 `planned`、`unresolved` 或 `not-available` 时，可以继续做 docs/ontology/PRD 侧分类，
但不得发起目标项目 OpenSpec 操作。`prd-only` 或 `ontology` 为 `not-applicable` 时，不得从其他产品借 authority。

## L0-L3 启用规则

| 档位 | 启用的跨仓字段 | 说明 |
|---|---|---|
| L0 现场查询 | 无 | 只读扫描；不要求五分类、三元组、implementation-return、回写、canonical 晋升 |
| L1 单个 PRD/gap 或单个 change | docs 产物绝对路径（必须）；稳定 ID、requirement/feature IDs、docs commit SHA（产物已携带则必须保留） | 五分类门禁 + 候选拆分方案；默认只出 Plan |
| L2 多 change 或跨 scope | L1 全部字段 + 目标仓 revision/commit | 另需：全部相关 scope 清单、每个 scope 的验证命令、change 依赖/冲突/执行顺序、独占边界标注（数据库/权限/路由/共享组件）、一次只推进一个 apply。不默认要求完整三元组 |
| L3 交付回写 / canonical 晋升 / 正式对账 | L2 全部字段 + 完整三元组（feature SHA / archive SHA / origin 远端指针）+ implementation-return proposal | 目标项目仓逐项复核后才能创建对应 change；canonical 晋升必须 destination owner 审核 |

## docs 侧交接字段（输出给项目仓）

- docs artifact absolute path（docs 产物绝对路径）
- stable ID（稳定 ID）
- docs commit SHA
- requirement / feature IDs
- classification（五分类，定义见 `artifact-to-changes.md`）
- evidence paths（证据路径）

字段没有提供时必须写明 `unknown`、`not-found` 或 `not-applicable`，不得编造。

## 项目仓收尾字段（带回 docs）

- feature SHA（feature 提交，实现落点）
- archive SHA（归档提交，archive 目录与 verification-report 所在）
- origin 远端指针（对账基线锚点）
- change ID
- archive 路径
- verification-report 路径（无则显式标注，docs 对账时不可引验证报告）
- exclusion list（排除项清单：未实施 / 暂缓 / 排除项按底稿原文带回，不转述改写）

## 边界与门禁

- `confirmed-implementation` 是进入目标项目仓二次复核的门，不是自动创建 change 的授权。
- destination owner 审核是 canonical 晋升门；没有审核不能晋升 canonical ontology/PRD。
- L2 不默认要求完整三元组；L3 才要求完整三元组和 implementation-return。
- 项目仓始终拥有自己的 OpenSpec changes、代码和验证事实；docs 侧只记录交付状态与证据指针，不复制证据正文，不镜像 per-change 登记。
- 一次只推进一个 apply；多 change 按依赖顺序逐个闭环，独占边界（数据库/权限/路由/共享组件）不并行。
- 没有实施证据，不能把 PRD 标为已交付；没有 verification report，不能声称验证通过。

## 标准收尾报告模板

```text
项目仓交付收尾报告：

项目：
目标 revision：
origin 远端指针：

docs 产物：
- 路径：
- 稳定 ID：
- docs commit SHA：

归档 changes：
| change ID | feature SHA | archive SHA | archive 路径 | verification-report 路径 | 状态 |

排除项清单：
- 原文：

验证摘要：
- 命令：
- 结果：
- 覆盖范围：
- 未扫描范围：

回写建议：
- ...
```

模板说明：

- 无 verification-report 的 change 在「状态」列显式标注（如「已归档-无VR」）；验证摘要不得为它声称验证通过。
- 排除项清单带底稿原文；docs 侧编号映射无法唯一解析时如实报告，由 docs 会话按台账对号入座，项目仓不杜撰映射。
- 三元组缺项时收尾报告仍可带回，但回写只能标「归档受阻/未提交」。
- 字段没有提供时写明 `unknown`、`not-found` 或 `not-applicable`，不得编造。
