# PRD 差异消费

用于短口令：`消费 PRD 差异 <报告路径>`。

## 档位

默认 **L1**（单个 PRD/gap 报告）。报告展开为多个 gap、涉及多个目标 scope、或候选 change 之间存在数据库/权限/路由/共享组件依赖时升 **L2**（补 scope 清单、验证命令与依赖排序，见 `cross-repo-handoff.md`）。发生交付回写或 canonical 晋升时按 **L3** 走 `prd-writeback.md`。

## 目标

把 PRD 差异报告转成目标项目可执行的 Implementation Plan。默认只出 Plan，不创建 change，不改代码。

## 输入

- PRD 差异报告或 gap 报告（docs 产物绝对路径）。
- 目标产品 ID 或绝对项目路径。产品 ID 必须通过公共 resolver 解析；不得按 ID 推测路径。绝对路径可直接扫描，无法映射产品时显式标记 unresolved。
- 可选：`suggested-openspec-changes.yaml`、PRD 实施交接包。

## 五分类门禁

对报告里每个候选缺口分类。分类定义与 `artifact-to-changes.md` 一致，此处按差异报告语境映射：

| 报告语境 | 分类 | 能否创建功能 change |
|---|---|---|
| 真代码缺口（有证据的真实运行时缺口，且上游范围已 accepted） | `confirmed-implementation` | 是候选；仍必须经目标项目仓二次复核，不自动创建 |
| PRD 过时 | `docs-only` | 否；回 docs 修 PRD |
| code_map / ontology / term-aliases 漏判 | `already-covered` | 否；记录覆盖的 spec/code ID，回 PRD 侧修映射 |
| 已被其他能力覆盖 | `already-covered` | 否；记录覆盖的 spec/code ID |
| 代码/spec 已存在但缺当前测试或运行证据 | `verification-only` | 否；项目仓补验证并回写证据 |
| 弱证据 / 术语未匹配 / 待用户确认 | `low-confidence-excluded` | 否；保留待复核 |

分类规则：

- 弱证据项归入 `low-confidence-excluded` 或「需要确认」，不得直接当 `confirmed-implementation`。
- 只有 `confirmed-implementation` 输出项目仓消费路径；它只是进入目标项目仓二次复核的门，不是自动创建 change 的授权。

## Implementation Plan 门禁

- Implementation Plan v1 的每一项必须标注：分类、证据路径、验收标准、验证命令。
- 没有目标项目仓复核结果时，不得直接进入 `/opsx-new` 或 `/opsx-ff`。
- 保留默认行为：只出 Plan，用户确认后、目标项目仓复核完成，才创建 change。

## 步骤

1. 读取目标项目 `AGENTS.md`、`openspec/specs/`、active changes、近期 archive。
2. 抽取 PRD 报告里的候选缺口，逐项标五分类（见上表）。
3. 对 `confirmed-implementation` 缺口输出 Implementation Plan v1：每项标注分类、证据路径、验收标准、验证命令，另含 `<CHANGE_ID>`、依赖顺序、回归范围、是否需要先做 Prometheus plan。
4. 等用户确认、且目标项目仓复核结果回来后，才进入 `/opsx-new` 或 `/opsx-ff`。

## 拆分原则

- 每个 change 只处理一个可验收缺口。
- 数据库迁移、权限模型、编号引擎、报表引擎类高风险项单独拆。
- PRD 过时和 code_map 漏判不创建功能 change。
- 被确认 blocked 的项只记录条件，不创建假进行中的 change。

## 输出

```text
Implementation Plan v1

过滤结论：
- confirmed-implementation：
- docs-only（PRD 过时）：
- already-covered（code_map / term-aliases 漏判 / 已覆盖）：
- verification-only：
- low-confidence-excluded / 需要确认：

推荐 change：
| CHANGE_ID | 分类 | 证据路径 | 优先级 | 依赖 | 范围 | 验收 | 验证 |

执行顺序：
1. ...

需要确认：
- ...
```

字段没有提供时写明 `unknown`、`not-found` 或 `not-applicable`，不得编造。
