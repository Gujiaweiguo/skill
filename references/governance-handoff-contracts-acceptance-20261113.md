# align-governance-handoff-contracts 实施验证记录（2026-11-13/14）

> 本件原位于 change 目录 verification-notes.md，归档前按「archive 五坑 1」移入 tracked references/；change 工件（proposal/design/tasks/specs/samples）随目录进入 gitignored archive/。

## 授权与范围

本轮用户「按照推荐执行」接受 OQ-1/2/3 并授权 apply，签署见 design.md。无 commit/archive/push；不写外部 docs 或产品仓，不改历史回执。

## 验证责任

- 报告函数/schema：代码 lane 聚焦单测；协调者检查代码后运行最终四文件测试集。
- 协议：协调者人工对照出包正文与执行协议，不伪称已实现自动协议检查器。
- 仓治理：协调者最终运行 docs consistency、skill ecosystem、OpenSpec strict validate。

## 人工协议验收场景（最终工件核对后填写结论）

| 输入/观察 | 应有结论 | 验收层 |
|---|---|---|
| 只读 none + [] | 接受，不因空列表字段存在误拒 | 人工协议 |
| 显式只读缺省 policy/list | 缺省字段解释 none/[]，无写面授权 | 人工协议 |
| 只读 consume-existing | 仅历史无写别名，不执行 change | 人工协议 |
| 只读 create-or-consume 或非空授权集 | 拒绝；null/畸形字段亦拒绝 | 人工协议 |
| 文件读取/无持久副作用检查 | 限包范围，不推出 DB 连接权 | 人工协议 |
| DB 只读查询 | 包范围与连接均须授权 | 人工协议 |
| 有副作用测试 | 默认拒绝，事前明确授权后限批准边界；前后状态非授权 | 人工协议 |
| DB 写入/迁移 | denied | 人工协议 |
| 执行完成 | 执行侧发完整回执，docs 核验后更新包体 executed | 人工协议 |
| docs 逐项处置完成 | 回执 absorbed 后包 reconciled，不因停驻天数推进 | 人工协议 |
| 两样例 changes=[] | schema 可均通过；实施负例仍判缺执行证据 | schema 与人工协议分别记录 |
| 历史哈希匹配/当前文件前进 | 不能自动放行，复核适用性及原授权条件 | 人工协议 |
| 已消费后勘误 | 保留消费版本与锚点，独立勘误，不追认偏差 | 人工协议 |

## 最终命令结果

### 代码/schema lane（已完成并核对）

- `cd skills/business/product-prd-generator && uv run pytest tests/test_implementation_return_inventory.py tests/test_product_governance_contracts.py tests/test_reconciliation_guards.py tests/test_prd_handoff_contract.py -q` → exit 0，**113 passed**（8.1 的四文件命令，测试面已稳定）。
- 聚焦选择：`-k "strict_validation_report or stdlib_import"` 6 passed；`-k "review_status"` 2 passed；`tests/test_product_governance_contracts.py -q` 23 passed。
- 真实证据端到端（只读，`uv run python -m product_prd_generator.implementation_return_report <file>`）：
  - `implementation-return-contract-lifecycle-w0-readonly-20261108.json` → **exit 1**，source 3 errors / normalized 0（normalized 通过不冒称源件通过）；
  - `implementation-return-wave1-finance-f1-cancelled-payable-guard-20261107.json` → **exit 1**，source 7 errors / normalized **仍 2 errors**（absorbed 门槛事实 review_owner/open_spec_change_id 未被补造，剩余错误如实报告）。
- change 样例 CLI：`findings-return-readonly.sample.json` exit 0；`execution-empty-changes.negative.sample.json` exit 0（形状合法；实施模式空 changes 属人工协议判负，非 schema 拒绝）。
- schema 语义边界核验：implementation-return.schema.json 仅 `schema_version.$comment` 变化（enum/anyOf 零改动）；reconciliation-record.schema.json 仅新增可选 `reconciliation_scope`（const `1.0` 不动，缺省=未声明）。
- 仓级门禁（中间检查点）：`check_docs_consistency.sh` exit 0（36 PASS）；`check_skill_ecosystem.sh` exit 0；`openspec validate --strict` exit 0。
- 跟踪文件改动核对：本轮 tracked 改动共 10 个文件，全部在 tasks 实施清单内，无越界写入；compat helper 与 pyproject 零改动。

### 协议 lane（已完成并核对，8 处复审修正全部落盘）

## 8.3 契约 vs 执行协议人工对照结论

- **矩阵单一权威**：mode × policy 语义矩阵（含 `none` 枚举、只读缺省 none/[]、分支短路、未知/null/畸形拒绝、W1 兼容 none+[]）只存在于 implementation-package.md 约束 6；execution-protocol §1 第 9 项引用判定、不复制；SKILL.md 仅链接（组合枚举 grep=0）。无状态机复制。
- **词表一致**：prd-writeback 回写规则唯一词表=schema enum；`机械修正` 表述 grep=0；协议/契约/SKILL 无第二词表。历史性提及（troubleshooting.md 2026-10-21 现象记录、external-owner-follow-up 旧清单、return-shape-inventory 盘点、README 英文 scan/ontology 语境）非规则文本，按原样保留。
- **严格校验命令一致**：协议 §5 与 prd-writeback 均为 `cd /opt/code/skill/skills/business/product-prd-generator && uv run --extra dev python -m product_prd_generator.implementation_return_report '<绝对路径>'`，退出码 0/1/2 语义与模块 `main()` 实测一致（0=source 通过、1=source 失败即使 normalized 通过、2=操作性错误非校验结论）。
- **生命周期责任一致**：契约生命周期行（executed=目标仓发射完整回执，docs 核验后由 docs 写入包体，执行侧不改包体）+ 规则 9 + 协议 §5 findings 分支三者一致，无执行侧获得 docs 写面路径。
- **findings 最小字段一致**：契约约束 7 与协议 §5 字段清单逐项一致（execution_mode/changes_empty_reason/scope/limitations/findings+锚点/1.0/初始 pending；交付只落包内授权本地路径，docs 仓路径时会话内交付不写入）。
- **漂移判定树**：协议 §1 第 7 项含「仅当既有授权与包适用条件仍覆盖当前输入才可放行」「无法判定≠瞬态证明」两处修正；契约版本三分第 5 条引用一致。

## 6.5 人工协议验收结论（逐项）

| 输入/观察 | 结论 | 依据 |
|---|---|---|
| 只读 none + [] | **接受**（矩阵：合法；字段存在不构成拒绝） | 契约约束 6 矩阵 read-only × none 格 |
| 显式只读缺省 policy/list | **按 none/[] 解释，不授予写面** | 矩阵 read-only × 缺省格 |
| 只读 consume-existing | **仅无写权限旧别名，不据此 apply** | 矩阵格 + 协议 §1.9 |
| 只读 create-or-consume / 非空集 / null / 畸形 | **拒绝**（含未知 mode/policy 整行整列拒绝） | 矩阵 + 协议 §6 拒绝表 |
| 文件读取 / 无持久副作用检查 | granted 限包核验范围，不隐含 DB 访问 | 协议 §2 只读模板 |
| DB 只读查询 | 须范围授权 + 连接授权（与 DB 写入分权限面） | 同上 |
| 有副作用测试/核验命令 | 默认 denied；事前明确授权 + 批准边界内才可执行；状态核对只是证据 | 同上（OQ-2 裁决口径） |
| DB 写入 / 迁移 | denied（永不可授予） | 同上 |
| 执行完成 | 执行侧发完整回执报告事实；docs 核验后写包体 executed | 契约生命周期行 + 规则 9 |
| absorbed/reconciled | 逐项处置完成后推进；不因停驻天数自动吸收 | 契约规则 9 v2.1 句 |
| 两样例 changes=[] | CLI 均 exit 0（0 errors）；实施负例**人工判缺执行证据**，未宣称 schema 机械拒绝 | 本文件代码 lane 实测 |
| 历史哈希匹配/工作区前进 | 内容等价 + 既有授权与适用条件覆盖才放行，否则回呼；无法判定如实记录 | 协议 §1 第 7 项判定树 |
| 已消费后勘误 | 独立勘误保留实际消费锚点，不倒写 | 契约版本三分第 3 条 |

## 最终门禁汇总

`check_docs_consistency.sh` exit 0（36 PASS）｜`check_skill_ecosystem.sh` exit 0｜四文件 pytest 113 passed exit 0｜`openspec validate --strict` exit 0｜tracked 改动 = 授权清单 10 文件，无越界；compat helper 与 pyproject 零改动；未 commit/archive/push。


## 最终收尾状态（2026-11-14 追加）

- **适用时点声明**：上文「实施验证记录」全部命令与计数（pytest 113 passed、双 script exit 0、strict validate exit 0、真实回执 CLI exit 1×2、样例 exit 0×2）是 2026-11-13/14 归档前工作区时点的实测，其内容对应实施提交 `111c9c0` 的树；本节追加时**未在新 HEAD 上重新执行**全套测试，不将旧证据改述为新 HEAD 复跑结果。
- **实施提交**：`111c9c0b4820eeb2ba29f4116a24a63dd8674ba7`（feat(governance)：契约实施 12 文件 +879/−24，pre-commit 生态审计 PASS）。
- **规格同步提交**：`70c83d952128754125726d7644b74d6c6e18e762`（docs(openspec)：主规格同步 3 文件 +190；111c9c0 为其祖先）。
- **归档目录**：`openspec/changes/archive/2026-11-14-align-governance-handoff-contracts/`（gitignored 本地历史）；五坑后检全绿（Purpose 逐字带入、无 delta 头残留、MODIFIED 逐字承接）。
- **推送状态**：本节写入时 push 尚未执行（上文「未 commit/archive/push」检查点适用于 2026-11-13/14 归档前时点，此后已被本节记录的提交与归档超越）；实际推送结果以会话内推后核验报告为准，不在本件预填。
