# Adapter Capability Owner Decision Record —— 2026-10-04

```text
STATUS: APPROVED
OWNER SIGN-OFF: RECORDED
SCOPE: O1, O2, O4 only
```

> **签署来源**：2026-10-04 owner 会话明确批准指令。本轮 owner 的「同意」按该指令解释为
> 且仅解释为对 O1、O2、O4 三项建议的批准。owner 身份依据：本仓 AGENTS.md（一人公司，
> 业务 owner = opc）与决策草稿全局字段待填项（`owner: # 待填（opc）`）——可从当前上下文
> 确定，故不标记 MISSING_OWNER；日期取本记录落盘日（与建议包/设计包/审计同为 2026-10-04），
> 不标记 MISSING_DATE。
>
> **解释边界（硬边界）**：本批准不扩展到 O3、O5、O6、O7-chat、O7-report、O7-vision、O8、
> O9、O10-report、O10-vision、O11——上述事项全部保持 pending。任何一轮「同意」都不得
> 被解释为 O1-O11 全部批准。
>
> **批次编号口径**：以本批准指令为准——Batch 1 = 首版 capability 文件（O1+O2）；
> Batch 2 = 等待 O3（冻结）；Batch 3 = adapter_status 迁移（O4，本轮仅盘点）；
> Batch 4 = 等待 O5（冻结）；Batch 5 = 等待 O6-O11 子项批准（冻结）。建议包 §4.1 批次表
> 中的「Batch 2（registry/resolver 迁移）」对应本记录口径的 **Batch 3**。

---

## D-O1 方案 B（capability 消费方自声明）—— APPROVED

```yaml
decision_id: O1
decision_date: "2026-10-04"
owner: "opc"
status: approved
scope: "方案 B；六个业务 skill 私有 adapter capability"
company_ids:
  - lanlnk
product_ids:
  - lnkchat
  - lnkchatbi
  - lnkcre
  - lnkcrm
  - lnkgateway
  - lnkreport
  - lnkvision
  - lnkwebsite
consumer_ids:
  - product-prd-generator
  - requirement-evaluator
  - pricing-generator
  - competitor-product-analyzer
  - company-intro-generator
  - strategy-brief-generator
decision: "批准方案 B"
approved_batch:
  - Batch 1
approved_changes:
  - "创建六个业务 skill 私有 adapter capability 声明"
forbidden_changes:
  - "不修改 resolver"
  - "不修改 company.yaml"
  - "不修改 30-products/**"
  - "不创建公共 capability registry"
schema_version: "1"
evidence:
  - path: "references/adapter-capability-owner-recommendation-2026-10.md"
    description: "owner 决策建议包"
follow_up:
  - "Batch 1 完成后复核 authority/capability 隔离"
```

### O1 允许

- 创建上述六个业务 skill 私有 capability 声明文件
  （`skills/business/<skill>/references/adapter-capabilities.yaml`）；
- 使用 O2 批准的 schema（`schema_version: 1`）；
- 记录产品支持状态、证据路径、验证时间、owner 和备注；
- 保持 capability 与产品 authority 分离（`authority.status != adapter_capability.status`）。

### O1 禁止（approved 后持续生效）

- 修改公共 resolver（`shared/product_context/**` 的 resolver/models 语义）；
- 修改 `company.yaml`；
- 修改 `30-products/**` canonical authority；
- 修改产品代码仓；
- 建立公共 adapter capability registry（含 `/opt/code/skill/references/` 或
  docs `00-governance/` 下的中心 capability 文件）；
- 将某个 skill 的 capability 解释为产品事实；
- 无证据将产品标记为 implemented；
- 删除或重写 `product-registry.yaml`。

### O1 红线（capability 文件内容，来自建议包 §3.1）

- capability 属于消费方，不是产品事实；
- 不复制产品 authority（capability 文件内禁止出现 `docs_root` / `code_root` /
  `ontology_path` / `prd_root` / revision 等产品事实**字段**）；
- `product_id` 必须使用 company.yaml canonical ID；
- 每个 capability 状态必须带证据路径、验证时间（verified_at）、owner 和备注。

---

## D-O2 Batch 1 首版 schema 与 6×8 矩阵 —— APPROVED

```yaml
decision_id: O2
decision_date: "2026-10-04"
owner: "opc"
status: approved
scope: "Batch 1 首版 schema（schema_version: 1）与六消费方×八产品首版矩阵"
company_ids:
  - lanlnk
product_ids:
  - lnkchat
  - lnkchatbi
  - lnkcre
  - lnkcrm
  - lnkgateway
  - lnkreport
  - lnkvision
  - lnkwebsite
consumer_ids:
  - product-prd-generator
  - requirement-evaluator
  - pricing-generator
  - competitor-product-analyzer
  - company-intro-generator
  - strategy-brief-generator
decision: "批准 Batch 1 首版 schema 与 6×8 矩阵"
approved_batch:
  - Batch 1
approved_changes:
  - "固化当前审计所得的 48 格首版状态（含 3 处 ★ 改判：product-prd-generator×lnkwebsite、
     pricing-generator×lnkgateway、company-intro-generator×lnkgateway → not-applicable，
     口径与决策草稿 D-O2 scope 一致）"
  - "为每个状态附证据路径与说明（verified_at=2026-10-04，owner=opc）"
  - "新增 capability 文件 schema 校验测试
     （shared/product_context/tests/test_adapter_capabilities_schema.py，纯新增只读测试）"
forbidden_changes:
  - "不将 48 格矩阵解释为八产品均已支持"
  - "不将 unsupported 自动升级为 implemented"
  - "不从 lnkcre 复制其他产品的功能、报价或叙事资产"
  - "不修改 authority status"
  - "不修改 code_root、ontology root 或 PRD authority"
  - "不修改产品 canonical 文档"
  - "不修改 /opt/code/lnkcrm"
schema_version: "1"
evidence:
  - path: "references/adapter-capability-decision-2026-10.md"
    description: "设计包 §2 状态语义、§3 六消费方×八产品矩阵、附录 A schema 草案"
  - path: "references/adapter-capability-owner-recommendation-2026-10.md"
    description: "owner 决策建议包 §3.2（首版矩阵含 ★ 改判口径）"
  - path: "references/adapter-capability-owner-decision-draft-2026-10.md"
    description: "决策表单草案 D-O2（含 3 处 ★ 改判的 scope 定义）"
follow_up:
  - "首版后任何状态变更必须同时更新证据、verified_at 与校验测试内嵌矩阵（同 commit 原子化）"
  - "lnkgateway 两格 ★ 改判与 O9 联动：O9 裁决前 not-applicable 表达的是当前无商业场景证据；
     若未来裁定面客，须凭证据重评"
```

### O2 schema（每个 capability 单元至少包含）

```yaml
consumer_id:      # = 所在 skill 目录名
product_id:       # company.yaml canonical ID（8 产品之一）
status:           # implemented | partial | onboarding | unsupported | not-applicable | blocked
evidence:         # ≥1 条证据指针（skill 内文件 / docs 基线文件 / 设计包锚点）
verified_at:      # YYYY-MM-DD
owner:            # opc
notes:            # 补充说明（含阻塞原因 / ★ 改判 / pending 决策联动）
```

### O2 首版矩阵固化值（★ 改判后；统计与设计包 §3.2 一致）

implemented 12 / partial 15 / onboarding 5 / unsupported 6 / not-applicable 7 / blocked 3 = 48。
逐格值固化于 schema 校验测试内嵌矩阵（机器可核）与六个 capability 文件（人读权威源）。
**绝不能表述为「六 skill 已支持八产品」**——八产品 resolver 上下文可解析 ≠ 六 skill 具备
完整 adapter 能力（implemented 仅 12/48 格）。

---

## D-O4 adapter_status 五步迁移 —— APPROVED（保留兼容期，本批次不删除字段）

```yaml
decision_id: O4
decision_date: "2026-10-04"
owner: "opc"
status: approved
scope: "adapter_status 五步迁移方向批准；保留兼容期；本批次不删除字段；本轮仅执行调用方盘点"
company_ids:
  - lanlnk
product_ids:
  - lnkchat
  - lnkchatbi
  - lnkcre
  - lnkcrm
  - lnkgateway
  - lnkreport
  - lnkvision
  - lnkwebsite
consumer_ids:
  - product-prd-generator
  - requirement-evaluator
  - pricing-generator
  - competitor-product-analyzer
  - company-intro-generator
  - strategy-brief-generator
decision: "批准五步迁移策略，保留兼容期，暂不删除字段"
approved_batch:
  - Batch 3（本轮仅完成调用方盘点；实际迁移待盘点确认兼容范围后进行）
approved_changes:
  - "盘点实际读取 resolver.adapter_status 的调用方（本轮已执行，见附录一盘点证据）"
  - "允许：迁移确实存在的读取方；增加兼容读取、迁移提示和相关测试"
  - "允许：更新 skill 文档使 capability 成为业务支持度来源（本轮因目标 SKILL.md 存在
     其他会话未提交修改而未触碰，列为 Batch 3 后续动作）"
  - "允许：在不改变输出兼容性的前提下减少新代码对 adapter_status 的依赖"
forbidden_changes:
  - "本批次不删除 resolver.adapter_status"
  - "本批次不重命名或不改变 authority 字段语义"
  - "不将 capability 状态写回 resolver authority"
  - "不修改 lnkcrm 的 present-unconfirmed"
  - "不修改 company.yaml 或 30-products/**"
  - "不删除 product-registry.yaml"
  - "不执行 Batch 4 或 Batch 5"
schema_version: "1"
evidence:
  - path: "references/adapter-capability-decision-2026-10.md"
    description: "设计包 §1.1/§9-O4/§11（8 产品全输出 unsupported 实测；无程序化分支消费结论）"
  - path: "references/adapter-capability-owner-recommendation-2026-10.md"
    description: "建议包 §1.3/§3.4（五步迁移顺序）"
follow_up:
  - "五步顺序：①建 capability 声明（Batch 1，已完成）→ ②迁移实际读取方（盘点结论：无程序化
     调用方，仅 prose 引用）→ ③兼容告警/迁移提示（文档级，Batch 3）→ ④禁止新增依赖（即刻生效）→
     ⑤owner 确认无消费方后另行批准删除字段"
```

### O4 本轮盘点结论（2026-10-04，盘点于新文件创建前取干净基线）

**结论：兼容保留，无（程序化）调用方。** resolver 零修改；字段保留；不为了「完成迁移」
修改 resolver。完整 rg 证据与逐条归类见附录一。

---

## Batch 解锁判定（批准时点核验）

| 条件 | 结果 |
|---|---|
| O1 = approved | ✅ |
| O2 = approved | ✅ |
| owner 已明确 | ✅ opc（来源见「签署来源」） |
| decision_date 已明确 | ✅ 2026-10-04 |
| 六个消费方范围明确 | ✅ 见 consumer_ids |
| schema_version = 1 | ✅ |
| approved_changes / forbidden_changes 已明确 | ✅ 见三个 decision block |

**判定：Batch 1 解锁。** 本轮依据批准指令第六节的明确执行顺序（「第一步落盘决策记录 →
第二步执行 Batch 1 → 第三步执行 O4 迁移盘点」）实施；该指令即「执行已批准的 Batch 1」
的明确要求。

### 各 Batch 状态（本记录签署后）

| Batch | 状态 | 触发条件 |
|---|---|---|
| Batch 1 | **解锁并已执行**（六个 capability 文件 + schema 校验测试） | O1+O2 ✅ |
| Batch 2 | **冻结** | 等待 O3（方案 C 豁免；B 方案批准下不触发，保持 pending） |
| Batch 3 | **仅完成盘点**（本附录一）；实际迁移无程序化调用方可迁，进入「兼容保留，无新增调用方」状态 | O4 ✅（方向）；删除字段另行批准 |
| Batch 4 | **冻结** | 等待 O5（lnkcrm 五问齐答） |
| Batch 5 | **冻结** | 等待 O6-O11 各子项具体批准 |

## lnkcrm 冻结线（本轮全程维持）

```yaml
company_yaml_code_root: null          # 未修改
layers_code_root: null                # 未修改
authority_code_status: present-unconfirmed   # 未修改
observed_revision: 仅证据登记（1d5ebb6b，2026-10-04 复核），不升级状态
```

本轮未修改：company.yaml、30-products/**（含 lnkcrm 全部 canonical 文档）、
/opt/code/lnkcrm 及任何产品代码仓、product-registry.yaml、resolver、目标项目 OpenSpec。
docs 仓零改动。

---

## 附录一：O4 调用方盘点证据（2026-10-04，新文件创建前基线）

盘点命令（与批准指令第六步一致）：

```bash
cd /opt/code/skill
rg -n "adapter_status|product\.adapter_status|adapter capability|adapter-capabilities" \
  shared skills references
```

逐条归类：

| 类别 | 位置 | 判定 |
|---|---|---|
| 定义位（非调用方） | `shared/product_context/resolver.py:434,456`；`shared/product_context/models.py:45,69` | 字段定义与序列化，保持原样 |
| 序列化透传（非分支消费） | `skills/meta/openspec-practice/scripts/resolve_context.py`（经 `as_dict()` 透传，自身无 adapter_status 字面引用） | 兼容保留，无需迁移 |
| registry 自有字段（prd-gen 私有 adapter 元数据，非 resolver 字段调用方；收敛属 Batch 2/S3 冻结范围） | `product-registry.yaml` 8 处；`tests/test_product_governance_contracts.py:130,140`；`references/product-semantic-baseline.md` + `.schema.json`；`references/product-governance/README.md:39` | 不动（本批次禁改 registry） |
| prose 引用（非调用方，Batch 3 文档级迁移提示候选） | `skills/business/pricing-generator/SKILL.md:85`（直接指 resolver 字段的免责声明）；`skills/business/competitor-product-analyzer/SKILL.md:26`（指 registry 字段）；`skills/meta/openspec-practice/references/prd-writeback.md:97`（泛指） | 本轮未触碰（其中两文件存在其他会话未提交修改） |
| 治理文档（本决策族文档自身） | `references/adapter-capability-*.md` 多处 | 记录性引用，非调用方 |

**程序化调用方计数：0。** 与设计包 §11「事前 grep 消费面：当前无程序化分支消费（仅 prose
引用）」一致。处置：不修改 resolver；字段保留；「禁止新增 adapter_status 依赖」禁令自本
记录起生效。实施后复扫（键级）：本轮新增的六个 capability 文件与校验测试 **0 处以
adapter_status 为键或消费该字段**（校验测试并将其纳入键级禁令常量）；文本级仅存的命中为
evidence 对 product-registry.yaml 条目的溯源引用与本文/测试自身的禁令表述，非依赖。

## 附录二：本轮实施清单（全部纯新增，skill 仓；docs 仓零改动）

| 文件 | 依据 |
|---|---|
| `references/adapter-capability-owner-decision-2026-10-04.md`（本文件） | 批准指令第三节 |
| `skills/business/product-prd-generator/references/adapter-capabilities.yaml` | O1+O2 |
| `skills/business/requirement-evaluator/references/adapter-capabilities.yaml` | O1+O2 |
| `skills/business/pricing-generator/references/adapter-capabilities.yaml` | O1+O2 |
| `skills/business/competitor-product-analyzer/references/adapter-capabilities.yaml` | O1+O2 |
| `skills/business/company-intro-generator/references/adapter-capabilities.yaml` | O1+O2 |
| `skills/business/strategy-brief-generator/references/adapter-capabilities.yaml` | O1+O2 |
| `shared/product_context/tests/test_adapter_capabilities_schema.py` | O2（schema 校验测试；只读、零第三方依赖、非 registry、resolver 不读 capability 文件） |

## 附录三：未批准事项重申

O3、O5、O6、O7-chat、O7-report、O7-vision、O8、O9、O10-report、O10-vision、O11 —— 
**全部 pending，全部冻结**。任何后续实施均需对应 decision_id 的独立批准。
