# Product Baseline（三层模型：本体 / PRD / 代码）

> 文件名保留 `product-semantic-baseline.md` 以维持引用稳定；术语以本文三层表述为准。

所有产品只保留三层用户可见结构。不要求用户理解任何"模型分类学"：

| 层 | 英文 | 回答 | 典型内容 |
|---|---|---|---|
| 本体 | ontology | 这个产品世界里有什么 | 对象、关系、生命周期、状态、业务规则、术语别名、能力目录、指标口径、权限边界 |
| PRD | prd | 产品要做什么、本轮改变什么 | 主 PRD、增量 PRD、客户需求、竞品证据、产品决策、UI 约束、验收场景、版本规划 |
| 代码 | codebase | 现在实际上实现了什么 | 业务代码、数据库迁移、API、前端、测试、OpenSpec specs/changes、验证与归档证据 |

## 1. 三层规则

1. 本体层内部可由多个文件组成（如 LnkCRE 的 `business-ontology.yaml` + `30-products/lnkcre/ontology/architecture/domain-model/`），概念上仍是一层。
2. 业务系统（lnkcre/lnkcrm）与平台/AI 产品（lnkreport/lnkchatbi/lnkchat/lnkvision/lnkgateway）的本体**内容不同**，但**层数相同**——平台产品的本体是产品对象（Skill/Workflow/Dataset/Chart/Capability/Execution），不是业务实体。
3. 三层之间用对账同步，不互相覆盖：代码证据 → PRD 状态回写；实施发现 → 本体变更候选（人工确认后回写）。本体回答领域概念、关系和规则是什么；PRD 回答产品目标和本轮要改变什么。PRD 不拥有本体语义，代码也不能单凭实现事实决定产品目标。

## 0. Two Governance Modes

- **Initial/full mode** establishes an initial ontology baseline and a full PRD baseline. Record each layer's authority/version or explicitly mark it unresolved/absent; do not invent versions, revisions, releases, paths, or owners.
- **Incremental mode** records an ontology delta against its identified baseline and a PRD delta against its identified PRD baseline. Missing baselines remain explicitly unresolved; do not treat an incremental proposal as a replacement baseline.
- These are task-scoped modes within product-prd-generator. They are not mandatory serial skill chaining or a requirement to invoke other skills for every task.
- Ontology synthesis may use customer requirements, competitor information, code facts, and OPC product ideas as separately identified inputs. Evidence and product judgment remain distinct provenance. A proposed ontology change requires owner approval before canonical promotion; this skill does not automatically write canonical ontology.
- Shared machine-readable contracts are in `references/product-governance/`. They define references and governance records, not product authorities.

## 2. 非独立层产物的归属

以下产物**不是架构层**，分别归属某一层的工作产物：

| 产物 | 归属 |
|---|---|
| OpenSpec change / tasks / 归档 | 代码层的实施机制 |
| 测试 / 验证回执 / implementation-return-package | 代码层的证据 |
| Semantic Release | 本体层的发布快照（见 §4） |
| UI 设计系统 / 页面模式 / 视觉验收 | PRD 的内容（见 ui-design-system-handoff.md） |
| 竞品分析 / 客户需求 / 产品意见 | PRD 的输入（competitor-product-analyzer 产出证据与 trace_id） |
| `config/ontology/business-ontology.yaml` | 本体层的**共享机器本体特殊输入**（永久留在 `config/ontology/`，不迁移；不是第二个 LnkCRE 产品根） |
| `out/prd/<项目>/output/` | PRD 的**纯生成区**（不得直接作为 canonical PRD；经 owner 审后晋升并入 `30-products/<产品>/prd/`，双源不并存） |

## 3. 产品注册表

已注册产品以 company.yaml products（唯一产品台账）为准：lnkcre / lnkcrm / lnkreport / lnkchatbi / lnkchat / lnkvision / lnkgateway / lnkwebsite。`references/product-registry.yaml` 已退役（D1，2026-10-04 删除；产品与路径事实 = company.yaml + shared.product_context resolver）；adapter 支持度权威源见 `references/adapter-capabilities.yaml`。路径、状态和权威仍由产品 owner 所有。规则：

- 新产品加入 = 补一条 entry；路径未确认写 `null` + `*_note` 说明，不编造。
- 未知/未注册产品必须显式降级说明，**不得静默回退到商管 ontology**。
- `model_kind` 等旧分类字段仅为可选内部提示，不作为入口概念。

### 产品适配器契约（保留）

每个产品 entry 至少声明：

```yaml
project: lnkcre
docs_root: /opt/code/docs/lanlnk/30-products/lnkcre   # canonical（mi-cre 目录已于 2026-09 合并删除）
code_root: /opt/code/lnkcre
source_of_truth:
  - openspec/specs
  - openspec/changes/archive
  - AGENTS.md
  - current_code
ontology: <本体层主入口文件>
term_aliases: <术语别名文件，可 null>
adapter_status: implemented | partial | unsupported
product_status: complete | in-development | unknown
unsupported_areas: []
verification:
  commands: []
```

> LnkCRE 别名口径：MI / MI-CRE / LnkCRE / lnkcre / 商管系统 是同一产品（canonical id `lnkcre`）。MI-* / MI-CRE-* 是历史稳定文档 ID，不代表目录仍叫 mi-cre。路径解析唯一权威源是 skill 的 `_paths.resolve_product_paths()`。

`product_status` 描述产品本身的成熟/完整状态；`adapter_status` 描述本 Skill 对产品 authority、扫描和验证能力的支持状态，两者不得互相推导。产品完整不表示其 ontology/PRD 内容完整，也不自动批准未审核的 ontology baseline。Flow direction 是单次治理任务的属性，不按产品注册。未来增量变更默认先做 ontology impact check，再形成 PRD delta，最后交由目标代码仓实施；对于已有代码领先文档的情况，可反向收集代码事实并形成 ontology/PRD 对账候选，但不得直接改写 canonical 内容。

> **迁移期注记（2026-10-04，owner O3/Batch 2 批准；D1/D2 同日收口）**：per-consumer adapter capability
> 的唯一权威源已迁移至 `references/adapter-capabilities.yaml`（方案 B，Batch 1 落地）。
> 原注册表 `product-registry.yaml` 已退役删除（D1，2026-10-04），其 `adapter_status`
> 冻结快照随之消失；resolver `ProductContext.adapter_status` 兼容字段亦已删除
> （D2 / O4 步骤 ⑤，2026-10-04）；状态变更一律写 capability 文件
> （evidence/verified_at/校验测试随 capability 文件同 commit 原子化）；capability 文件的
> `blocked` / `not-applicable` 两态本表枚举不可表达（lnkgateway / lnkwebsite），以 capability
> 文件为准。消费方、字段替代来源与退役收口见 skill 仓
> `references/product-registry-迁移审计-2026-10-04.md`（§4 D1 收官注记）。

规则：

1. 共享 Skill 不得把 CRE 专属模块当成其他产品的默认模块。
2. 缺失 adapter 时必须标记 `adapter_status=unsupported` 或明确降级，不得静默回退。
3. `source_of_truth` 只描述事实来源顺序，不代表文档之间可以自动覆盖。

## 4. Semantic Release = 本体层发布快照

PRD、代码 map、未验证本体都不是 AI 运行时语义契约。只有 `status=accepted` 且带版本和源 revision 的 Semantic Release 才能作为 lnkchat/lnkchatbi 等下游的消费入口。最小字段：

```yaml
id: SEM-CRE-OPS-002
product: lnkcre
version: 0.2.0
status: accepted
source_model_version: <本体版本>
source_repository: /opt/code/lnkcre
source_revision: <full-git-sha>
objects: []
events: []
metrics: []
commands: []
```

`objects/events/metrics/commands` 只声明下游需要的语义切片，从本体派生，不复制完整本体。

## 5. 变更规则

- 新增业务术语或对象：先进本体变更候选，经 owner 确认后回写本体，再进增量 PRD。
- 新增产品能力：进增量 PRD；平台产品不因此被迫创建业务实体。
- 实施结果：回写实现状态和证据；不自动改写本体正文。
- 本体的最终更新必须有 reviewed decision 或 owner ruling。
