# O3 / Batch 2 Owner Decision Record —— product-registry 迁移期整理（2026-10-04）

```text
STATUS: APPROVED
OWNER SIGN-OFF: RECORDED
SCOPE: O3 / Batch 2 only（audit-only）
```

> **签署来源**：2026-10-04 owner 会话明确批准指令（本轮）。该指令是对 O3 的
> **独立批准**，满足 `references/adapter-capability-owner-decision-2026-10-04.md`
> 附录三「未批准事项重申」对 O3 的冻结要求（任何后续实施均需对应 decision_id 的
> 独立批准——本记录即该独立批准）。owner = opc（本仓 AGENTS.md，一人公司）。
>
> **语义重定义（重要）**：原建议包 §3.3 中 O3 = 「方案 C 豁免」（条件性，仅拒 B 选 C
> 时触发）。方案 B 已由 D-O1 批准，原 O3 语义**不触发**。本轮 owner 指令将 O3 / Batch 2
> 重定义为：**product-registry.yaml 迁移期审计与兼容说明整理（audit-only）**。
> 本记录按 owner 指令口径落盘。
>
> **批次编号口径**：沿用 2026-10-04 决策记录口径——Batch 2 = 等待 O3 的批次（本记录
> 解锁）。建议包 §4.1 的「Batch 2（registry/resolver 迁移）」= 决策记录口径的
> **Batch 3**，其内容（registry capability 维度收敛实施、resolver `adapter_status`
> 迁移实施）**不在本批准范围**。
>
> **范围限定（audit-only）**：原 Batch 2 建议含义中的「registry capability 维度收敛」
> 在本批准下限定为**仅审计**——registry 全部字段（含 `adapter_status`）不动；收敛实施
> （改字段 / 删字段）保持冻结，删除 registry 是独立 owner 批准动作。

---

## D-O3 方案 B 下 product-registry 迁移期整理（audit-only）—— APPROVED

owner 指令原文（正式写法，verbatim）：

```yaml
O3:
  status: approved
  owner: opc
  decision_date: 2026-10-04
  approved_batch:
    - Batch 2
  approved_changes:
    - "审计 product-registry.yaml 的现有消费方和字段"
    - "记录替代来源、迁移状态和删除阻塞项"
    - "更新 product-prd-generator 的迁移兼容说明"
  forbidden_changes:
    - "不删除 product-registry.yaml"
    - "不建立公共 adapter capability registry"
    - "不修改 resolver"
    - "不修改 company.yaml"
    - "不修改 30-products/**"
    - "不执行 O4 实际迁移"
    - "不执行 O5-O11"
    - "不提交、不推送"
```

补充登记字段（与既有决策记录格式对齐）：

```yaml
decision_id: O3
decision_date: "2026-10-04"
owner: "opc"
status: approved
scope: "方案 B 下 product-registry.yaml 迁移期审计与兼容说明（audit-only；registry 保留为迁移期兼容元数据）"
company_ids:
  - lanlnk
product_ids:
  - lnkcre
  - lnkchatbi
  - lnkchat
  - lnkcrm
  - lnkgateway
  - lnkreport
  - lnkvision
  - lnkwebsite
consumer_ids:
  - product-prd-generator   # registry 属主；其余 5 个业务 skill 仅 prose 引用（见审计 §1）
schema_version: "1"
evidence:
  - path: "references/product-registry-迁移审计-2026-10-04.md"
    description: "本批准的执行产物：消费方/字段/替代来源/迁移状态/删除阻塞项审计"
  - path: "references/adapter-capability-owner-decision-2026-10-04.md"
    description: "前置决策（O1/O2/O4）：Batch 1 六个 capability 文件已落地；O4 仅盘点"
  - path: "references/adapter-capability-decision-2026-10.md"
    description: "设计包 §4 registry 四重职责分析"
follow_up:
  - "删除阻塞项 B1-B7（见审计 §4）解除前，product-registry.yaml 保持在仓"
  - "registry 字段级收敛与删除 = 独立 owner 批准动作，未包含在本批准内"
  - "其他 skill 的 2 处 registry prose 引用（pricing/competitor SKILL.md）列为后续文档级迁移候选，本轮未触碰（存在其他会话未提交修改）"
  - "B1 已解除（2026-10-04 状态回写，授权会话补记）：B1 经用户会话授权执行并已通过复核；独立 owner 签署未记录——本记录的 OWNER SIGN-OFF 仅覆盖 O3/Batch 2（audit-only），不覆盖 B1 实施，不得将 B1 表述为经 owner 独立签署批准。执行记录见 references/adapter-capability-owner-decision-b1-execution-2026-10-04.md（验证结果、范围对账、未提交状态均以该记录为准）。B2-B7 仍为 pending/冻结，各自需独立授权；B1 完成不构成 registry 字段删除批准。本状态回写不改变 registry 数据区、authority 或产品事实"
  - "B2 已解除（2026-10-04 状态回写）：B2 经用户会话授权执行并已通过验证（check_docs_consistency.sh Check 4 对账面改为 company.yaml products，WARN 语义保持）；独立 owner 签署未记录——本记录的 OWNER SIGN-OFF 仅覆盖 O3/Batch 2（audit-only），不覆盖 B2 实施，不得将 B2 表述为经 owner 独立签署批准。执行记录见 references/adapter-capability-owner-decision-b2-execution-2026-10-04.md（验证结果、范围对账、未提交状态均以该记录为准）。遗留：AGENTS.md Check 4 机制说明与 product-registry.yaml 头部规则 10(c)「Check 4 对账面」两处 prose 属 B5（Batch 3），B2 未触碰。B3-B7 仍为 pending/冻结，各自需独立授权；B2 完成不构成 registry 删除批准"
  - "lnkcrm code 冻结线已对账（2026-10-04 状态回写，O5-lnkcrm-code 路线 A）：经用户会话授权 ratify docs 提交事实 c41a978 为现行基线（lnkcrm code_root=/opt/code/lnkcrm，revision 4323b8c…，code authority=complete）；lnkgateway ontology=unresolved 与 lnkwebsite prd-only/not-applicable 冻结线不变。独立 owner 签署未记录——本记录的 OWNER SIGN-OFF 仅覆盖 O3/Batch 2（audit-only），不覆盖该对账实施，不得表述为经 owner 独立签署批准。执行记录见 references/adapter-capability-owner-decision-lnkcrm-freeze-reconcile-2026-10-04.md。该对账仅 ratify lnkcrm code 维度，不构成 registry 删除、O4 字段删除或 O5 其余子项批准；B1-B7 阻塞项状态不变（B3 follow_up 补记缺口仍待独立授权）；B4/B6/B7 与 O6-O11 仍冻结"
  - "B3 已解除（2026-10-04 状态回写，RESIDUAL-CLEANUP-R2 补记）：B3 经用户会话授权执行并通过验证（产品注册入口迁移 docs 仓 onboarding 契约 onboard.sh product + company.yaml products；_paths 错误引导、A5 断言、registry 头部规则 1 注释同步，YAML 数据区零改动；实施与验证细节以执行记录为准）；独立 owner 签署未记录——本记录的 OWNER SIGN-OFF 仅覆盖 O3/Batch 2（audit-only），不覆盖 B3 实施，不得将 B3 表述为经 owner 独立签署批准。执行记录见 references/adapter-capability-owner-decision-b3-execution-2026-10-04.md。B3 完成不构成 registry 删除批准"
  - "B4 已解除（2026-10-04 状态回写，RESIDUAL-CLEANUP-R3 补记）：B4 经用户会话授权（MECH-BATCH-STANDING 一次性批量放行）执行并通过验证（product-registry.yaml 头部规则 6 双源同步契约撤销：路径解析运行时唯一权威源 = resolver / _paths.resolve_product_paths()，本表保留为迁移期兼容元数据/历史镜像，不构成双源同步义务；YAML 数据区零改动；相邻残留已由 R2/R3 后续授权清理）；独立 owner 签署未记录——本记录的 OWNER SIGN-OFF 仅覆盖 O3/Batch 2（audit-only），不覆盖 B4 实施，不得将 B4 表述为经 owner 独立签署批准。执行记录见 references/adapter-capability-owner-decision-b4-execution-2026-10-04.md（验证结果、范围对账、未提交状态均以该记录为准）。B4 完成不构成 registry 删除或 adapter_status 删除批准"
  - "B5 已解除（2026-10-04 状态回写，RESIDUAL-CLEANUP-R3 补记）：B5 经用户会话授权（B5、B5-R1、B5-R2、B5-R5 多轮）执行并通过验证，全部目标已完成或 verified-no-change（两处 Check 4 prose = AGENTS.md:221 + registry 头部规则 10(c)；B5-R1 = prd-gen SKILL.md×2 + schema.json，competitor:25 / shared README:38 verified-no-change；B5-R2 = baseline.md + governance README；B5-R5 = pricing SKILL.md:85，并对 B5-R2/R3/R4「其他会话未提交修改」表述作出事实纠正：未确认归属的工作树修改）；独立 owner 签署未记录——本记录的 OWNER SIGN-OFF 仅覆盖 O3/Batch 2（audit-only），不覆盖 B5 实施，不得将 B5（或任何轮次）表述为经 owner 独立签署批准。执行记录见 references/adapter-capability-owner-decision-b5-execution-2026-10-04.md 及 b5-r1/b5-r2/b5-r5-execution-2026-10-04.md（B5 整体解除结论与证据以 B5-R5 记录为准）。B5 完成不构成 registry 删除批准"
  - "B6 已解除（2026-10-04 状态回写，RESIDUAL-CLEANUP-R3 补记）：B6 经用户会话授权（MECH-BATCH-STANDING）执行并通过验证（prd-gen adapter-capabilities.yaml 8 处 evidence 首条自 registry 条目改指迁移审计 §3，头部 3 行迁移说明注释；六态 status、8 产品键、schema_version、verified_at 零变化；其余 5 个 capability 文件零改动）；独立 owner 签署未记录——本记录的 OWNER SIGN-OFF 仅覆盖 O3/Batch 2（audit-only），不覆盖 B6 实施，不得将 B6 表述为经 owner 独立签署批准。执行记录见 references/adapter-capability-owner-decision-b6-execution-2026-10-04.md（验证结果、范围对账、未提交状态均以该记录为准）。B6 完成不构成 registry 删除、adapter_status 删除或 O4 字段删除批准"
  - "B7 已解除（2026-10-04 状态回写，RESIDUAL-CLEANUP-R3 补记）：B7 经用户会话授权（MECH-BATCH-STANDING）执行并通过验证（C1：docs 仓 30-products/external-owner-decisions-2026-10-02.md:5 回填通道描述改指当前有效路径，原 registry/_paths 通道标注为 2026-10-04 起迁移期兼容元数据/历史镜像，历史证据指针未删除；C2：domain-architecture-migration-2026-09-26.md:33 verified-no-change，不重写历史注记）；独立 owner 签署未记录——本记录的 OWNER SIGN-OFF 仅覆盖 O3/Batch 2（audit-only），不覆盖 B7 实施，不得将 B7 表述为经 owner 独立签署批准。执行记录见 references/adapter-capability-owner-decision-b7-execution-2026-10-04.md（验证结果、范围对账、未提交状态均以该记录为准）。B7 完成不构成 registry 删除或 adapter_status 删除批准。至此 B1-B7 全部解除；registry 删除本身仍为独立 owner 批准动作，O4 字段删除与 O5-O11 仍冻结"
```

### O3 允许（本轮已执行的全部范围）

1. **审计 product-registry.yaml 的现有消费方和字段** ——
   产出 `references/product-registry-迁移审计-2026-10-04.md` §1（消费方清单，
   程序化 / prose / 跨仓三类）+ §2（字段清单与替代来源）。
2. **记录替代来源、迁移状态和删除阻塞项** —— 审计 §2（per-field 替代来源与迁移
   状态）、§3（adapter_status 与 capability 文件对齐矩阵）、§4（删除阻塞项 B1-B7）。
3. **更新 product-prd-generator 的迁移兼容说明** —— 三处、全部为文档/注释级：
   - `skills/business/product-prd-generator/references/product-registry.yaml` 头部
     规则 10 更新（YAML **数据零改动**，仅注释）；
   - `references/product-semantic-baseline.md` §3 追加迁移期注记；
   - `references/product-governance/README.md` 追加迁移期注记一句。

### O3 禁止（approved 后持续生效）

- 不删除 `product-registry.yaml`（任何字段级删除/改名亦不允许）；
- 不建立公共 adapter capability registry（含 skill 仓 `references/` 或 docs
  `00-governance/` 下的中心 capability 文件）；
- 不修改 resolver（`shared/product_context/**` 语义零改动）；
- 不修改 `company.yaml`；
- 不修改 `30-products/**`（docs 仓零改动）；
- 不修改产品代码仓；
- 不执行 O4 实际迁移（adapter_status 字段级迁移实施保持冻结；
  D-O4 已批准的「兼容保留 + 禁止新增依赖」状态不变）；
- 不执行 O5-O11（全部保持 pending / 冻结）；
- 不提交、不推送。

### 本轮触碰文件清单（全部为上述 approved_changes 的直接产物）

| 文件 | 动作 | 依据 |
|---|---|---|
| `references/adapter-capability-owner-decision-o3-batch2-2026-10-04.md`（本文件） | 新增 | 批准落盘 |
| `references/product-registry-迁移审计-2026-10-04.md` | 新增 | approved_changes 1+2 |
| `skills/business/product-prd-generator/references/product-registry.yaml` | 头部规则 10 注释更新（数据零改动） | approved_changes 3 |
| `skills/business/product-prd-generator/references/product-semantic-baseline.md` | §3 迁移期注记 | approved_changes 3 |
| `skills/business/product-prd-generator/references/product-governance/README.md` | 迁移期注记一句 | approved_changes 3 |

本轮**未触碰**（与其他会话未提交修改共存，未回退/覆盖）：
`_paths.py`、`test_paths.py`、`product-registry.yaml` 数据区、
prd-gen / pricing-generator / competitor-product-analyzer 的 `SKILL.md`、
resolver 与 `shared/product_context/**`、company.yaml、`30-products/**`、产品代码仓。

---

## Batch 状态更新（本记录签署后）

| Batch | 状态 | 触发条件 |
|---|---|---|
| Batch 1 | 已执行（六个 capability 文件 + schema 校验测试，2026-10-04） | O1+O2 ✅ |
| Batch 2 | **解锁并已执行（本记录，audit-only）** | O3 ✅（本轮重定义口径） |
| Batch 3 | 仅完成盘点（D-O4 附录一）；实际迁移「兼容保留，无新增调用方」 | registry 字段收敛 / resolver 迁移实施 = 独立批准 |
| Batch 4 | 冻结 | O5（lnkcrm 五问齐答） |
| Batch 5 | 冻结 | O6-O11 各子项具体批准 |

## 未批准事项重申（本记录后仍然有效）

O4 实际迁移（字段级）、registry 删除、O5、O6、O7-chat、O7-report、O7-vision、O8、
O9、O10-report、O10-vision、O11 —— **全部 pending，全部冻结**。任何后续实施均需
对应 decision_id 的独立批准。
