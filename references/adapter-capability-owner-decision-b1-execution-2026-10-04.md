# B1 执行记录 —— product-registry 删除阻塞项 B1（测试断言迁移）补录（2026-10-04）

```text
STATUS: EXECUTED（已批准执行并已完成）
OWNER SIGN-OFF: NOT RECORDED（仅会话授权，无独立签署记录）
SCOPE: B1 only（审计 §4-B1 列明的测试断言迁移 + 必要辅助门禁）
```

> **记录性质（必读）**：本文件是 B1 的**执行补录**，用于闭合审批链中的执行授权证据。
> 它记录的事实是：**用户在 B1 实施前的会话中明确同意执行 B1**（会话授权）。
> 它**不是**、也**不得被引用为**一份独立签署的 owner 批准记录——与
> `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`
> （含 owner 指令 verbatim 落盘 + `OWNER SIGN-OFF: RECORDED`）那种签署记录不同，
> B1 **不存在**同类型的独立签署证据（见 §3 事实区分）。

---

## 1. 登记字段

```yaml
decision_id: B1
decision_date: "2026-10-04"
record_date: "2026-10-04"
owner: "opc"
owner_basis: "本仓治理约定：一人公司，owner = opc（AGENTS.md；与既有决策记录口径一致）。注意：owner 身份有依据，但 owner 独立签署记录不存在（见 §3）"
status: "已批准执行并已完成"
authorization:
  type: "session_consent"
  source: "B1 实施前用户明确同意「执行 B1」的提示词（会话授权）"
  corroboration:
    - "O4 门禁 allowlist 基线注释（shared/product_context/tests/test_adapter_status_migration_gate.py:44）记载「B1 迁移（2026-10-04）…… owner 批准执行 B1」——该注释为 B1 实施会话对授权的事实陈述，其授权本体即上述会话同意，不构成独立签署文件"
  not_claimed: "不存在独立签署的 owner 批准记录（无 verbatim 指令落盘、无签署块）"
scope:
  approved: "仅迁移审计 §4-B1 明确列出的测试断言（三组回归测试中的 adapter_status 断言、code_root/docs_root 存在性断言、product_class/ontology_profile 镜像断言）及必要辅助门禁（O4 门禁 allowlist 基线更新）"
  basis: "references/product-registry-迁移审计-2026-10-04.md §4-B1 解除条件：断言迁移改指 company.yaml / resolver 输出 / capability 文件 / baseline 契约"
files_implemented:
  - path: "skills/business/product-prd-generator/tests/test_product_governance_contracts.py"
    change: "adapter_status 等 registry 读取断言改读 skill 私有 capability 文件（references/adapter-capabilities.yaml）"
  - path: "skills/business/product-prd-generator/tests/test_product_semantic_contracts.py"
    change: "code_root/docs_root 存在性断言自 product-registry.yaml 改指 company.yaml products + shared.product_context resolver（resolver-first 唯一权威源；测试更名为 test_resolver_paths_cover_registered_products）"
  - path: "skills/business/product-prd-generator/tests/test_product_authority_fixtures.py"
    change: "product_class/ontology_profile 镜像对账面自 product-registry.yaml 改指 product-semantic-baseline 契约"
  - path: "shared/product_context/tests/test_adapter_status_migration_gate.py"
    change: "ALLOWED_ADAPTER_STATUS_SOURCES 中 test_product_governance_contracts.py 基线清零（0，保留条目防 adapter_status token 回流）"
forbidden_unchanged:
  - "B2-B7（全部未批准、未执行，仍为删除阻塞项）"
  - "registry 数据区（product-registry.yaml 字段零改动）"
  - "resolver / models（shared/product_context 运行时语义零改动）"
  - "capability 文件（六份 adapter-capabilities.yaml 内容零改动）"
  - "company.yaml、30-products/**、产品代码"
results:
  source: "引自 B1 完成报告（本轮补录未重跑任何测试，见 §5）"
  tests: "相关测试通过（三组迁移后回归测试 + O4 门禁测试）"
  schema_checks: "schema 校验通过"
  format_checks: "格式检查通过"
not_executed:
  - "B2-B7 未批准、未执行（仍阻塞 registry 删除）"
  - "O5-O11 全部保持冻结"
version_control:
  committed: false
  pushed: false
  this_record: "untracked 新增文件"
  worktree: "工作区保留其他会话既有未提交修改，本轮未回退/未覆盖/未清理"
```

## 2. 日期与 owner 的确认依据

**decision_date = 2026-10-04**，由以下可核验证据链确认（非猜测）：

| 证据 | 内容 |
|---|---|
| 文件 mtime | 三个 B1 测试文件 2026-10-04 11:46:11–11:47:31 (+0800)；门禁文件 11:46:43 |
| 代码内注记 | 门禁 allowlist 注释与测试 diff 均自记「B1 迁移（2026-10-04）」 |
| 前置链时间 | O3 决策记录 10:32、迁移审计 10:33（同日）；B1 实施晚于审计产出，同日闭环 |
| 本轮会话 | 补录会话日期 2026-10-04（环境时区 Asia/Shanghai） |

**owner = opc**：依据本仓治理约定（AGENTS.md 一人公司）与既有决策记录一致口径
（O3 记录同款表述）。授权行为主体（会话中同意执行 B1 的用户）按该治理约定即
repo operator = opc。**但** owner 身份可确认 ≠ 存在 owner 独立签署记录——后者不存在。

## 3. 事实区分（防误引）

| 命题 | 状态 | 依据 |
|---|---|---|
| 用户明确授权执行 B1（会话同意「执行 B1」提示词） | **成立** | B1 实施前用户会话同意；由本轮用户指令（2026-10-04）确认并授权补录 |
| 存在独立签署的 owner 批准记录（verbatim 指令落盘 / 签署块 / SIGN-OFF: RECORDED） | **不成立，不得声称** | 全仓决策文档族中无 B1 的独立签署记录；O3 记录的签署仅覆盖 O3 / Batch 2（audit-only），其 forbidden_changes 未包含 B1 实施 |

引述规则：后续任何文档引用 B1 授权时，只能表述为「B1 经用户会话授权执行
（2026-10-04，见本记录）」，不得表述为「B1 经 owner 独立签署批准」。

## 4. 批准范围与实际实施对账

审计 §4-B1 解除条件允许的迁移目标：company.yaml / resolver 输出 / capability
文件 / baseline 契约。实际实施 4 个文件（§1 files_implemented）全部落在该目标集内：

| 审计列出的断言（§1-A1/A2/A3） | 迁移至 | 载体文件 |
|---|---|---|
| adapter_status 2 处断言（A1） | capability 文件 | test_product_governance_contracts.py |
| code_root/docs_root 存在性断言（A2） | company.yaml + resolver | test_product_semantic_contracts.py |
| product_class/ontology_profile 镜像断言（A3） | baseline 契约 | test_product_authority_fixtures.py |
| （辅助门禁）allowlist 基线防回流 | 基线清零 + 保留 0 条目 | test_adapter_status_migration_gate.py |

范围对账结论：实际实施 = 批准范围，无超出。超出范围者（registry 数据区、resolver、
models、capability 文件、company.yaml、30-products/**、产品代码、公共 capability
registry、B2-B7、O5-O11）均未触碰（引 B1 完成报告；本轮补录亦未触碰）。

## 5. 实施结果与验证证据（引自完成报告，本轮未重跑）

- 三组迁移后回归测试 + O4 门禁测试通过；
- schema 校验通过；
- 格式检查通过。

> 本轮为**补录会话**：上述结果系引用 B1 完成报告的记载，本轮未重跑、未改断言、
> 未验证性执行任何测试（遵守「只补记录」边界）。如需复核，须在获授权的会话中重跑。

## 6. 遗留与同步事项

1. **B2-B7 保持冻结**：registry 删除的其余阻塞项全部未批准、未执行；任何后续解除
   仍需对应独立授权（审计 §4 口径）。
2. **审计/O3 回写未做（有意）**：审计 §7 要求阻塞项状态变化同步至审计 §4 与 O3
   follow_up；本轮受「仅补记录、不改 O3 / Batch 2 决策记录」边界约束未回写。
   该同步作为后续待办登记于此，需在获授权触碰上述文件的会话中执行。
3. **版本控制**：本记录 untracked；全仓未提交、未推送；其他会话工作区修改原样保留。

## 7. 证据路径索引（均已实物核验存在）

- `references/product-registry-迁移审计-2026-10-04.md` §1-A1/A2/A3、§4-B1、§7
- `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`（O3 签署记录，非 B1 授权来源）
- `shared/product_context/tests/test_adapter_status_migration_gate.py`（allowlist 基线 :40-45，授权佐证注释 :44）
- 三个 B1 测试文件工作树当前内容（含「B1 迁移（2026-10-04）」注记）
