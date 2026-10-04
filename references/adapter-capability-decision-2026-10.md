# 业务 skill adapter capability 治理设计 —— owner 决策包（2026-10-04）

> 阶段定位：**分析、设计、验证与决策包形成**。本文档不执行任何 owner 决策；所有
> `owner_decision_required: true` 的事项在 owner 批准前保持现状。
>
> 前置：公共 `product_context` resolver 八产品验收、`openspec-practice` 跨仓治理编排、
> `product-prd-generator` resolver-first 迁移、五个消费方审计与迁移（审计报告
> `references/product-context-消费方审计-2026-10.md`）均已完成。本包处理剩余问题：
> **产品三层 authority 状态与每个业务 skill 对每个产品的实际能力支持状态之间的治理方式**。
>
> 本文即 §三 所指「设计文档」：两类状态的正式语义在 §2 固定。
>
> 证据基线：resolver 实测输出（2026-10-04，`resolve_context.py --all`，见附录 B 复现命令）、
> 功能基线文件存在性实测、pricing-generator 源码定价数据实测、materials 叙事资产实测。

---

## 1. 当前问题

### 1.1 两类状态已经分家，但第二类状态没有治理载体

公共契约（`00-governance/product-context-contract.md`）已定义 authority status 与
adapter capability status 两套语义，消费方迁移已完成。但 adapter capability status
目前**没有统一载体**，散落在三处且互相矛盾：

| 载体 | 语义 | 实测状态 |
|---|---|---|
| `product-registry.yaml` 的 `adapter_status` | 仅描述 product-prd-generator 一家 | lnkcre=implemented，其余 partial/onboarding/unsupported |
| resolver 输出的 `product.adapter_status` 字段 | 读 `company.yaml products[].adapter_status`（schema 未定义该字段），缺省回落 `unsupported` | **8 产品全部输出 unsupported**，与 registry 的 lnkcre=implemented 直接矛盾 |
| 各消费方 SKILL.md 的契约表 | 描述各自支持面 | 结构各异，无 status 枚举，无 verified_at，无法机读 |

### 1.2 状态漂移已有实证

- **审计报告 §4 的 lnkchat/lnkcrm 行已过时**：报告称两产品「未登记评估基线清单」，
  实测 `30-products/lnkchat/prd/功能清单.md`（2026-08-06，200 项）与
  `30-products/lnkcrm/prd/功能清单.md`（confirmed v1.0，2026-09-29 OPC 裁决）均已存在。
  capability 信息靠人工快照维护必然漂移——这是方案 A（维持现状类）的直接反证。
- **resolver `adapter_status` 字段全错**：字段单一 per-product 值无法表达 per-consumer
  语义，且当前所有值都是缺省回落的 `unsupported`。pricing-generator SKILL.md 已被迫
  写免责声明（「不得据此判定清单可用性」）——字段的存在本身在制造混淆。

### 1.3 「八产品可解析」被误读为「八产品已支持」的风险

resolver 对 8 产品全部返回 resolved context（八产品上下文可解析），但六个业务 skill
对八个产品的实际能力参差（见 §3 矩阵：48 格中 implemented 仅 12 格）。缺一个显式的
per-consumer×per-product 状态层，「resolver 能解析」与「skill 能干活」就会被混读。

---

## 2. 两类状态的正式定义

### 2.1 authority status（产品三层事实）

描述**产品自身**的 ontology/PRD/code 三层事实，与任何 skill 无关：

```yaml
authority:
  ontology:
    status: complete | partial | unresolved | not-found | planned | present-unconfirmed | inaccessible | prd-only | not-applicable | unsupported
  prd:
    status: <同上>
  code:
    status: <同上>
```

**事实来源**（唯一）：`company.yaml` + `30-products/<product>/{INDEX.md, ontology/README.md, prd/README.md}`，
经公共 `shared.product_context` resolver 解析。任何 skill 不得自算、缓存或改写。

### 2.2 adapter capability status（业务 skill 对产品的能力）

描述**某个业务 skill 对某个产品**的可用能力，必须带消费方维度：

```yaml
adapter_capabilities:
  <consumer_id>:            # 如 requirement-evaluator
    <product_id>:           # 如 lnkchat
      status: implemented | partial | onboarding | unsupported | not-applicable | blocked
      evidence: <路径或指针>   # 支持该状态的证据（SKILL.md 段落 / 脚本 / 基线文件）
      verified_at: <日期>    # 最后一次实测验证
      owner: <维护者>         # 该 capability 行的归属维护方
      notes: <补充说明>
```

允许值语义：

| 值 | 含义 |
|---|---|
| `implemented` | 该 skill 对该产品已具备完整可用能力（有基线/数据/规则 + 至少一次成功运行先例） |
| `partial` | 部分可用（如基线在位但新鲜度/语义校准未核；或有历史先例但基线未产品化登记） |
| `onboarding` | 结构在位（ontology/清单等输入已可解析），但无运行先例，首次真实使用前不得宣称支持 |
| `unsupported` | 该 skill 对该产品无 adapter 实现（缺基线、缺定价资料、缺叙事资产等） |
| `not-applicable` | 该产品对该 skill 无业务场景（如官网不做售前报价） |
| `blocked` | 被 authority 状态阻塞（如 ontology unresolved 阻塞术语归一；code present-unconfirmed 阻塞实现级评估） |

细分原因标签（与 status 正交，进 notes）：`缺少产品基线` / `缺少定价资料` / `缺少
adapter 实现` / `缺少产品叙事资产` / `被 authority 状态阻塞` / `基线过期`。

### 2.3 不等式（防混用核心规则）

```text
authority.status  !=  adapter_capability.status
```

示例：

```yaml
lnkchat:
  code:
    status: complete                    # authority：代码层事实完整
  requirement-evaluator:
    lnkchat:
      status: partial                   # capability：评估基线在位但已过期
```

这表示代码 authority 完整，但需求评估 skill 的 lnkchat 功能清单过期（落后 commits）。
**不能**解释为代码或 resolver 缺陷；**反向**也不成立（skill 支持某产品不提升该产品
任何 authority 层的状态）。

配套禁令（承接 `product-context-contract.md` 消费规则）：

1. 禁止把 capability 状态写入 resolver 的 authority 字段或 company.yaml；
2. 禁止把 authority 状态（如 prd complete）自动推导为 capability（如评估 implemented）；
3. 禁止把业务 skill 的「未登记基线」报告为 resolver 缺口；
4. 缺少产品基线时不得从其他产品借用（lnkcrm 缺报价基线不得借 lnkcre/历史 CRM 叙事自动顶替）；
5. resolver 不读取、不输出 capability 状态（§9-O4 处置现存 `adapter_status` 字段）。

---

## 3. 六消费方 × 八产品 adapter capability 矩阵

### 3.1 authority 事实基线（resolver 实测 2026-10-04）

| product | ontology | prd | code | code 事实 |
|---|---|---|---|---|
| lnkcre | complete | complete | complete | configured `/opt/code/lnkcre` @8e74a3b7 |
| lnkcrm | complete | complete | **present-unconfirmed** | configured null；observed `/opt/code/lnkcrm` @ad6f0c0b |
| lnkchat | complete | complete | complete | configured `/opt/code/lnkchat` @662123c9 |
| lnkchatbi | complete | complete | complete | configured `/opt/code/lnkchatbi` @72e96a71 |
| lnkreport | complete | complete | complete | configured `/opt/code/lnkreport` @86d5fefc |
| lnkvision | complete | complete | complete | configured `/opt/code/lnkvision` @fa5050f4 |
| lnkgateway | **unresolved** | **unresolved** | complete | configured `/opt/code/lnkgateway` @2659233a |
| lnkwebsite | **not-applicable** | complete | complete | configured `/opt/code/lnkwebsite` @5c3f7bf7；prd-only 产品 |

### 3.2 主矩阵（current_status；★ = recommended 与 current 不同）

| consumer \ product | lnkcre | lnkcrm | lnkchat | lnkchatbi | lnkreport | lnkvision | lnkgateway | lnkwebsite |
|---|---|---|---|---|---|---|---|---|
| product-prd-generator | implemented | onboarding | partial | partial | partial | unsupported | blocked | unsupported ★not-applicable |
| requirement-evaluator | implemented | partial | partial | partial | partial | partial | blocked | not-applicable |
| pricing-generator | implemented | partial | unsupported | partial | unsupported | unsupported | unsupported ★not-applicable | not-applicable |
| competitor-product-analyzer | implemented | partial | onboarding | onboarding | onboarding | onboarding | blocked | not-applicable |
| company-intro-generator | implemented（V5 域） / 全模式 | partial | partial | partial | unsupported | unsupported | unsupported ★not-applicable | not-applicable |
| strategy-brief-generator | implemented | partial | implemented | implemented | implemented | implemented | implemented | implemented |

统计（current 值，逐格重数核对）：**implemented 12 / partial 15 / onboarding 5 /
unsupported 9 / not-applicable 4 / blocked 3 = 48**。三处 ★ 改判生效后：unsupported 6 /
not-applicable 7。**绝不能表述为「六 skill 已支持八产品」**——八产品 resolver 上下文
可解析 ≠ 六 skill 具备完整 adapter 能力（implemented 仅 12/48 格）。

> strategy-brief-generator 的 implemented 语义：该 skill 只消费公司/产品事实
> （company.yaml 台账 + resolver 状态），不依赖任何产品业务基线，故结构上全产品可用；
> 深度分级见 3.3.F（lnkcrm 浅盘点、lnkgateway 叙事层薄）。

### 3.3 按消费方明细（每格字段契约）

§四要求的每格字段映射：`consumer_id` + `status_source` = 各小节标题（A-F，来源为该
skill 的契约文件/脚本/实测）；`product_id` + `current_status` + `evidence`（=evidence_path）
+ `missing_inputs` + `recommended`（=recommended_status）+ `owner_decision`
（=owner_decision_required）= 表格各行；**`authority_status_summary` = §3.1 表中该
product 行的三层状态**（避免同一 authority 摘要在 48 格中重复 48 次，需要逐格阅读时
按 product 做 join）。blocked / blocked-by-code 等与 authority 相关的格内说明均在
missing_inputs 或 notes 中显式回指 §3.1 状态。

#### A. product-prd-generator（status_source：product-registry.yaml + `_paths.py` + tests）

| product | current | evidence | missing_inputs | recommended | owner_decision |
|---|---|---|---|---|---|
| lnkcre | implemented | registry；`prd/baseline/feature-baseline.yaml` 全链路 + tier-4 兜底所有权 | — | implemented | 否 |
| lnkcrm | onboarding | registry；30-products 三层在位 + 功能清单 confirmed v1.0 | code authority 未配置：`resolve_code_root` 一律报错要显式 `--code-root` | onboarding | 否（维持；升级条件见 §12-O5） |
| lnkchat | partial | registry；`ontology.yaml` 扁平布局 + PRD-LC-* 40+ 文件 | — | partial | 否 |
| lnkchatbi | partial | registry；ontology accepted v2.0 + As-is-PRD | — | partial | 否 |
| lnkreport | partial | registry；ontology.yaml + PRD baseline | — | partial | 否 |
| lnkvision | unsupported | registry；canonical 本体为 `域知识.md`（无机器 ontology.yaml） | 缺 yaml 机器本体（capability schema 链路） | unsupported（升 partial 需一次验证 run + registry 登记，skill 自治） | 否 |
| lnkgateway | blocked | registry `ontology: null`（owner-confirmed unresolved）+ `_paths` 显式拒绝回落 | **被 authority 阻塞**：ontology+prd unresolved，需要 ontology 的链路不可用 | blocked | 否（解除阻塞 = 产品层 owner 决策，非 skill 侧） |
| lnkwebsite | unsupported | registry：仅路径登记消 `check_docs_consistency` Check 4 漂移信号 | 无 PRD 生成场景（产品 out of software product contract） | ★not-applicable（语义更准确） | 否（registry 归 prd-gen 自治维护） |

#### B. requirement-evaluator（status_source：SKILL.md 契约表 + 功能基线存在性实测）

| product | current | evidence | missing_inputs | recommended | owner_decision |
|---|---|---|---|---|---|
| lnkcre | implemented | `feature-baseline.yaml`（270 项）+ Step 0/P2.5 code 验证链 + 新鲜度门 | — | implemented | 否 |
| lnkcrm | partial | `30-products/lnkcrm/prd/功能清单.md` confirmed v1.0（109 REQ / 70 F，S6 147 行首发矩阵） | ①清单全部 `implementation_status: unknown`（承诺基线≠实现基线，✅existing 语义不可用）；②Step 0 code 验证被 present-unconfirmed 阻塞，需显式 `--code-root` | partial（承诺级评估可用；实现级 blocked-by-code） | **是**（实现级评估依赖 O-lnkcrm code 确认，见 §12） |
| lnkchat | partial | canonical `功能清单.md`（2026-08-06，200 existing，commit 33daf6a6） | **基线过期**：HEAD 已前进至 662123c9，新鲜度门将警告/标红 | partial（重跑 prd-gen 刷新即属运行时动作） | 否 |
| lnkchatbi | partial | canonical `功能清单.md` 存在 | 无评估先例；新鲜度未核；问数类需求语义与商管差异大，通用 7 类规则未经该产品校准 | partial（首个真实评估后可升 implemented，skill 自治） | 否 |
| lnkreport | partial | canonical `功能清单.md`（79 项，2026-08-21）+ 生成区双份 | 同上 | partial | 否 |
| lnkvision | partial | canonical `功能清单.md` 存在 | 同上 | partial | 否 |
| lnkgateway | blocked | prd unresolved → 无功能清单 | **缺少产品基线**（需先建 PRD/功能基线）；ontology unresolved 同时阻塞术语归一 | blocked | 否（解除靠产品层决策） |
| lnkwebsite | not-applicable | owner 2026-09-27 prd-only 裁定；生成区清单自证「未经 owner 审不构成 canonical」 | 无售前评估商业场景（官网不外卖） | not-applicable | 否 |

> **审计报告勘误**：`product-context-消费方审计-2026-10.md` §4 称 requirement-evaluator
> 对 lnkchat/lnkcrm「未登记评估基线清单」——实测两产品 canonical 功能清单均已存在
> （lnkchat 2026-08-06 生成、lnkcrm 2026-09-29 confirmed）。审计快照基于
> requirement-evaluator SKILL.md 产品表（该表未列这两个产品）而非文件系统实测。
> capability 状态必须挂文件级证据，不能挂叙述级清单——此发现同时是 §1.2 漂移实证。

#### C. pricing-generator（status_source：`generate_quote.py` 定价数据 + `pricing-basis.yaml`）

| product | current | evidence | missing_inputs | recommended | owner_decision |
|---|---|---|---|---|---|
| lnkcre | implemented | `MI_DATA` + resolver-first baseline + `pricing-basis.yaml` 费率 | 私有化模式定价待补（SKILL.md ⏳） | implemented | 否 |
| lnkcrm | partial | `CRM_DATA`（正祥交付物受管副本：`materials/03-products/CRM功能清单.xlsx`） | ①历史「CRM 会员营销系统」定价基线与 lnkcrm 产品实体的对应关系**未登记**（正祥定价 ≠ 已确认的 lnkcrm 报价基线）；②`30-products/lnkcrm/prd/功能清单.md` 未接入报价链 | partial（历史 CRM 报价可出，归属未登记 = drift 风险） | **是**（O6：正祥 CRM 定价是否追认为 lnkcrm 报价基线） |
| lnkchat | unsupported | 无报价数据 | **缺少定价资料** + 功能清单未接入 | unsupported | **是**（O7：是否为 lnkchat 建报价基线——AI 知识库工作流当前以「AI 岗位 Skill 服务」打包售卖，是否单列产品报价需 owner 定） |
| lnkchatbi | partial | `LNKCHATBI_DATA` 结构 + `LNKCHATBI_PRICE_Y1/Y2` 环境变量 | **标准定价未登记**（默认 0，每次需人工输入；`pricing-basis.yaml` 只有费率无产品定价） | partial | **是**（O8：标准定价入 pricing-basis.yaml） |
| lnkreport | unsupported | 无 | 缺少定价资料 | unsupported | **是**（O7 同类：是否建基线） |
| lnkvision | unsupported | 无 | 缺少定价资料 | unsupported | **是**（同上） |
| lnkgateway | unsupported | 无 | 内部 AI 网关无独立售卖场景（待 owner 确认定位） | ★not-applicable | **是**（O9：轻确认——网关是否永不独立面客） |
| lnkwebsite | not-applicable | 官网非商品 | — | not-applicable | 否 |

> 注：CLI 产品代号 `AI`（岗位 Skill 报价）不是 company.yaml 产品条目，是跨
> langchat+LnkChatBI+OrchestratorAgent 的编排服务打包，不占矩阵行，在
> `adapter-capabilities.yaml` 中以 notes 记录归属。

#### D. competitor-product-analyzer（status_source：SKILL.md S1.2/S1.3 表 + 基线实测）

| product | current | evidence | missing_inputs | recommended | owner_decision |
|---|---|---|---|---|---|
| lnkcre | implemented | ontology + feature-baseline + `evidence/competitors/` 先例（旗茂/海鼎） | — | implemented | 否 |
| lnkcrm | partial | ontology accepted v1.0 + `prd/竞品覆盖矩阵.md`（S13-S17 五源竞品证据已入 PRD 包） | ①`status_vs_lanlnk` 的 existing/partial/missing 判定不可用（实现全 unknown，只能标 unknown）；②`evidence/competitors/<vendor>/` 分析结论树未建 | partial | 否 |
| lnkchat | onboarding | `ontology.yaml` + 功能清单（200 existing）结构在位 | 无对照先例；目标能力模型未按该产品校准 | onboarding | 否 |
| lnkchatbi | onboarding | ontology v2.0 + 功能清单 | 同上 | onboarding | 否 |
| lnkreport | onboarding | ontology + 功能清单 79 项 | 同上 | onboarding | 否 |
| lnkvision | onboarding | `域知识.md` 本体 + 功能清单 | 同上；域知识非机器本体，术语归一走域知识入口 | onboarding | 否 |
| lnkgateway | blocked | SKILL.md 降级契约（unresolved 时标注不回落商管） | **被 authority 阻塞**：ontology unresolved → S1.2 术语归一无法进行（owner-confirmed 不从网关代码反推本体） | blocked | 否（解除 = 产品层决策：登记本体或裁定 not-applicable） |
| lnkwebsite | not-applicable | SKILL.md 明确不进 ontology-change-set 契约（owner 2026-09-27） | 无竞品对照场景 | not-applicable | 否 |

#### E. company-intro-generator（status_source：SKILL.md 模式 C/E + materials 叙事实测）

| product | current | evidence | missing_inputs | recommended | owner_decision |
|---|---|---|---|---|---|
| lnkcre | implemented | V5 领域包（`ontology/architecture/domain-model/`，resolver-first 检查）+ 商管叙事 + 案例库；V1-V4 全模式 | — | implemented | 否 |
| lnkcrm | partial | `materials/03-products/商圈会员CRM系统.md` + `CRM会员系统功能清单.md`（模式 C D 路线会员切口） | 产品特定架构包无（V5 仅 lnkcre）；案例属历史 CRM 交付叙事 | partial | 否 |
| lnkchat | partial | `materials/03-products/AI知识库与工作流平台.md`（模式 C AI 切口） | 产品特定架构包无 | partial | 否 |
| lnkchatbi | partial | `materials/03-products/AI智能问数系统.md` | 同上 | partial | 否 |
| lnkreport | unsupported | materials grep 无专属叙事命中 | **缺少产品叙事资产** | unsupported | **是**（O10：是否补叙事） |
| lnkvision | unsupported | materials grep 无 MallSenseAI/LnkVision 命中（更名前后均无） | 缺少产品叙事资产 | unsupported | **是**（O10 同类） |
| lnkgateway | unsupported | 无叙事 | 内部基础设施，无面客叙事场景（待确认） | ★not-applicable | **是**（O9 联动：网关定位） |
| lnkwebsite | not-applicable | 官网是公司门面，非叙事对象产品 | — | not-applicable | 否 |

> V5 领域驱动模式适用范围：**仅 lnkcre**（MI 工程领域架构包，基于 MI 代码反推的
> Bounded Context，非 prd-gen 产物）。其他产品的「领域页」无架构包来源，不得用
> lnkcre 领域包顶替。

#### F. strategy-brief-generator（status_source：SKILL.md P4 判定表）

| product | current | evidence | missing_inputs | recommended | owner_decision |
|---|---|---|---|---|---|
| lnkcre/lnkchat/lnkchatbi/lnkreport/lnkvision/lnkgateway/lnkwebsite（7 产品） | implemented | P4 台账驱动：company.yaml products + resolver code 状态；code complete 产品可源码级盘点 | lnkgateway 叙事层薄（ontology/prd unresolved 不阻断盘点，只降深度） | implemented（盘点维度） | 否 |
| lnkcrm | partial | P4 判定表 present-unconfirmed 行：浅盘点（标注 unconfirmed），观察 checkout 只作证据登记 | 深度读码需 owner 确认 | partial | **是**（联动 O-lnkcrm，§12） |

### 3.4 特核对项逐项结论（prompt §四要求）

1. **requirement-evaluator 评估基线覆盖范围**：implemented 1（lnkcre）；partial 5
   （lnkcrm/lnkchat/lnkchatbi/lnkreport/lnkvision，清单在位但 unknown 语义/过期/无先例）；
   blocked 1（lnkgateway）；not-applicable 1（lnkwebsite）。**修正审计报告 §4**（见 3.3.B 勘误）。
2. **pricing-generator 功能与定价覆盖**：MI/CRM/AI 实现（AI 为服务打包非产品行）；
   LNKCHATBI 结构在位但标准定价未登记（env 默认 0）；lnkchat/lnkreport/lnkvision 缺定价资料；
   lnkgateway/lnkwebsite 无商业场景。
3. **competitor-product-analyzer ontology/能力对照基线**：lnkcre implemented；lnkcrm partial
   （竞品覆盖矩阵先例，existing 判定不可用）；4 工具产品 onboarding；lnkgateway blocked；
   lnkwebsite not-applicable。
4. **company-intro-generator V5 适用范围**：仅 lnkcre；V1-V4/模式 C 不消费产品路径事实；
   叙事资产覆盖 4 产品域（商管/CRM/AI 工作流/AI 问数）。
5. **strategy-brief-generator 是否需要产品代码**：**不需要**——只消费公司/产品事实
   （台账 + resolver 状态），代码是可选深度增强（code complete → 深盘点；
   present-unconfirmed → 浅盘点）。故 8/8 结构可用，与「业务基线缺口」无关。
6. **product-prd-generator adapter 支持范围**：implemented 1 / partial 4 / onboarding 1 /
   unsupported 2（其中 lnkwebsite 推荐改 not-applicable）/ blocked 0（lnkgateway 在
   registry 未单列 blocked，按 `_paths` 显式拒绝行为判 blocked）。
7. **lnkcrm present-unconfirmed 对各消费方的影响**：prd-gen（报错要显式 --code-root）/
   requirement-evaluator（承诺级可评，实现级需显式确认，**不得自动用观察 checkout**）/
   pricing（无影响，不消费 code 层）/ competitor（checkout 只作只读证据定位）/
   company-intro（无影响）/ strategy（浅盘点 unconfirmed）。
8. **lnkwebsite prd-only/not-applicable 识别**：resolver 实测 ontology=not-applicable +
   prd=complete + code=complete，**正确**；各消费方正确标注（唯一残留：prd-gen registry
   仍标 unsupported，推荐改 not-applicable，属其自治维护项）。
9. **lnkgateway ontology unresolved 是否阻塞需要 ontology 的消费方**：**是**——直接阻塞
   competitor S1.2（术语归一）、prd-gen ontology 链路（`_paths` 显式拒绝）、
   requirement-evaluator 术语归一（不阻断其主链路，因其 blocked 在功能基线层）；
   不阻塞 pricing/company-intro/strategy（不消费 ontology）。阻塞表现为**显式降级报错**，
   非 resolver 缺陷。

---

## 4. product-registry.yaml 当前职责

`skills/business/product-prd-generator/references/product-registry.yaml`（155 行）当前承担
**四重职责**：

| # | 职责 | 现状评估 |
|---|---|---|
| 1 | prd-gen 的 adapter 元数据（adapter_status / product_class / ontology_profile） | 语义已收敛（头部规则 10，2026-10-04）；但只覆盖一个消费方 |
| 2 | 路径登记（docs_root/code_root/ontology/prd_root/term_aliases） | 与 resolver（company.yaml）双源；resolver-first 迁移后 registry 是同步镜像（规则 6：改一边必须改另一边） |
| 3 | 历史 decision 记录（规则 7/8/9：方案 B 迁移、OPC 六项裁决） | 只读历史，有价值，无 drift 风险 |
| 4 | `check_docs_consistency` Check 4 的对账面（产品目录 ↔ registry 条目） | 消 drift 信号用；lnkwebsite 条目即为此存在 |

**问题**：职责 1 的单消费方限制使其他 5 个消费方无法统一查询 capability；职责 2 的
双源同步是长期维护税。registry 本身不删（禁令），但其 capability 维度需要一个去处。

---

## 5. 方案 A / B / C 比较

### 方案 A：保留 registry 为 product-prd-generator 私有 adapter 元数据（现状延伸）

- ✅ 改动最小；不引入新公共注册表；prd-gen 继续兼容。
- ❌ 其他 5 个消费方 capability 无处登记（SKILL.md 叙述即漂移温床，§1.2 已实证）；
- ❌ resolver `adapter_status` 字段与 registry 的矛盾无人治理；
- ❌ 「八产品已支持」误读风险不降反升（信息越分散，汇总越靠人工快照）。

### 方案 B：每个业务 skill 自声明能力（`skills/business/<skill>/references/adapter-capabilities.yaml`）

- ✅ capability 归属清晰：skill 拥有并维护自己的支持边界，与「skill 自治」治理方向一致；
- ✅ 声明与证据同仓同目录（SKILL.md 契约/脚本/测试就在旁边），改行为与改声明可同 commit 原子化；
- ✅ 不形成跨 skill 中心注册表（不触碰「company.yaml 是唯一产品台账」「不建第二套注册表」红线）；
- ✅ 天然不含产品路径事实（capability 文件只挂 status + evidence 指针），混用面最小。
- ❌ 全局矩阵需聚合 → 用只读聚合校验脚本解决（skill 仓已有 `check_skill_ecosystem.sh` /
  `check_docs_consistency.sh` 先例生态，脚本不拥有数据只校验）；
- ❌ owner 审计多一步脚本依赖；产品×skill 交叉查询成本略高（一次性聚合输出即可）。

### 方案 C：公共 adapter capability registry（候选：`/opt/code/skill/references/adapter-capabilities.yaml` 或 `/opt/code/docs/00-governance/adapter-capabilities.yaml`）

八个治理问题的分析：

| 问题 | 分析 |
|---|---|
| 谁拥有该文件 | 两处候选都归 OPC，但内容横跨 6 个 skill 的自治边界——任一 skill 的能力变更都要动共享文件，owner 成为所有 skill 能力变更的串行瓶颈 |
| 谁能修改 | 同上：6 消费方共用一个可写面，commit 冲突与「顺手动别人的行」风险常驻 |
| 是否按公司区分 | capability 是 skill×product 二维，product 已按公司（company.yaml）；中心文件要么按公司拆文件（膨胀为 N 公司×1 文件树），要么单文件加公司维度（复杂化） |
| 是否按 skill 版本区分 | skill 无 semver 体系（SKILL.md 无版本号），只能靠 verified_at + evidence 指针——这一点 B/C 等价，C 无增量优势 |
| 如何记录证据 | 中心文件里 evidence 必然是二手引用（指向各 skill 侧文件），比 B 的一手同目录引用更易断链 |
| 如何防止变成第二套产品 authority | 需要常备防混用校验（cross-check resolver 输出）。若放 `docs/00-governance/`（该目录现全部是事实契约），「靠近产品事实」的位置暗示本身即风险；放 skill references 根则与 `product-registry.yaml` 形成两个中心文件的叠加混淆 |
| 如何与 product-registry.yaml 迁移兼容 | C 可一次性收编 registry 的 capability 维度，但收编后 registry 职责 2（路径双源）依旧，省不了同步税 |
| 如何避免把业务 capability 错当产品事实 | 依赖 §2 语义契约 + 校验脚本——B/C 等价，C 无增量优势 |

结论：C 的三个理论优点（单点查询、一次迁移、全局视图）全部可用「B + 只读聚合脚本」
以更小的治理代价获得，而 C 的中心化写面、位置暗示风险与多公司扩展成本是结构性缺点。

### 对比总表

| 维度 | A | B | C |
|---|---|---|---|
| 改动量 | 零 | 中（6 文件 + 1 脚本） | 中（1 文件 + 收编迁移） |
| capability 归属清晰 | ✗（仅 prd-gen） | ✅（skill 自治） | ✗（中心所有权） |
| 全局矩阵可聚合 | ✗ | 脚本聚合 | ✅（天然） |
| 第二注册表风险 | 低（但无能力面） | 低 | **中-高**（位置暗示 + 中心写面） |
| 多公司扩展 | n/a | ✅（skill 文件按产品行引用 company.yaml 公司） | 需拆文件或加维度 |
| 与现有红线相容 | ✅ | ✅ | ⚠️（需 owner 明示豁免「不建第二套注册表」惯例） |
| 漂移治理（§1.2 实证） | ✗ | ✅（evidence 同仓 + 校验） | ✅（靠纪律） |

---

## 6. 推荐方案：B + 只读聚合校验脚本

**推荐方案 B**，理由：skill 自治一致性、证据一手性、红线相容性（§5 对比）。
方案 C 不推荐，但若 owner 出于「单一查询面压倒一切」选择 C，批准条件见 §9-O3。

**owner 批准条件（B 方案）**：

1. 批准 §2.2 状态语义与附录 A schema 草案（含 blocked/not-applicable 枚举扩展）；
2. 批准 6 个消费方按 §3 矩阵首版落 `references/adapter-capabilities.yaml`；
3. 批准 product-registry.yaml 的 capability 维度收敛路径（§7-S2）；
4. 批准 resolver `ProductContext.adapter_status` 字段的废弃处置（§9-O4）。

**明确不因本方案改变的**：company.yaml 仍只登记产品事实（不写 capability）；
resolver 仍不读任何 capability 文件；跨产品借用禁令不变。

---

## 7. 推荐方案的迁移阶段（owner 批准后执行，本阶段不启动）

| 阶段 | 内容 | 产出 | 风险 |
|---|---|---|---|
| S1 schema 定稿 | 附录 A 草案 → 正式 schema（JSON Schema + 枚举校验），挂 `product-prd-generator/references/product-governance/` 或 skill 仓 `references/docspec/` 邻域（owner 定） | schema 文件 + 校验函数 | 低 |
| S2 六消费方首版落盘 | 按 §3 矩阵逐 skill 建 `references/adapter-capabilities.yaml`（verified_at=本包日期，evidence 指针按 3.3 各表） | 6 个 capability 文件 | 低（纯新增，不接生产路径） |
| S3 registry capability 维度收敛 | prd-gen 的 `adapter_status` 迁至自己的 capability 文件；registry 头部规则 10 改指向；职责 2（路径双源）是否随后退役另立 owner 决策（O5 尾项） | registry 修订 + capability 文件 | 中（动 tracked 文件，需回归 `tests/test_product_governance_contracts.py`） |
| S4 resolver 字段废弃 | `ProductContext.adapter_status` 弃用（§9-O4），消费方 prose 同步 | resolver PR + 测试 | 中（API 变更，见 §11 回滚） |
| S5 聚合校验脚本 | `references/scripts/` 新增只读聚合：校验 6 文件 schema → 输出全局矩阵 → 与 resolver authority 输出交叉检查（capability 文件不得含 authority 字段值）；挂 `check_docs_consistency.sh` 或独立 | 聚合脚本 + CI 挂点 | 低 |
| S6 文档回写 | AGENTS.md「Shared files」表、消费方审计报告 §8、各 SKILL.md 引用句更新 | 文档修订 | 低 |

---

## 8. 对现有 skill 的改动范围（S 阶段全景，本阶段全部未执行）

| 对象 | 改动 | 性质 |
|---|---|---|
| 6 个业务 skill | 各新增 `references/adapter-capabilities.yaml` | 新增（非生产路径，prompt/SKILL.md 引用为「支持面查询入口」） |
| product-prd-generator | registry capability 维度收敛 + `test_product_governance_contracts.py` 断言更新 | 修订（tracked） |
| shared/product_context | `adapter_status` 字段废弃（models/resolver/tests） | 修订（API 变更） |
| pricing/requirement/competitor/company-intro/strategy | SKILL.md 中 capability 相关 prose 改为指向各自 capability 文件 | 修订（轻） |
| openspec-practice | 不改（它是治理编排层，capability 文件聚合脚本的运行宿主候选，S5 定） | — |
| docs 仓 | **零改动**（capability 全在 skill 侧；company.yaml/30-products/00-governance 不动） | — |

---

## 9. owner 必须确认的事项（汇总编号）

| # | 事项 | 影响 | 不确认则 |
|---|---|---|---|
| O1 | 批准方案 B + §2 语义 + 附录 A schema | 全局 | 维持现状漂移（§1.2） |
| O2 | 批准 §3 矩阵的 48 格现状判定（含 3 处 ★ 改判建议） | 全局 | recommended 不生效 |
| O3 | （仅当拒 B 选 C）明示豁免「不建第二套中心注册表」惯例 + 定文件位置与所有权 | 方案 C 前置 | C 不可落盘 |
| O4 | resolver `adapter_status` 字段处置：**建议废弃**（单一 per-product 值无法表达 per-consumer，当前全默认 unsupported 且与 registry 矛盾）；备选：保留但文档钉死「仅 company.yaml 原样透传、缺省 unsupported、不得消费」 | resolver API | 字段继续输出误导值 |
| O5 | lnkcrm code authority 晋升（§12 五连问） | lnkcrm 全部消费方 | lnkcrm 各消费方维持现降级行为 |
| O6 | 正祥 CRM 定价基线是否追认为 lnkcrm 报价基线（pricing `CRM_DATA` 归属登记） | pricing×lnkcrm | CRM_DATA 继续无主使用 |
| O7 | lnkchat / lnkreport / lnkvision 是否建报价基线（含「AI 岗位 Skill 服务打包是否替代 lnkchat 单列报价」） | pricing×3 产品 | 三产品报价 unsupported 维持 |
| O8 | LnkChatBI 标准定价是否登记入 `pricing-basis.yaml`（替换 env 默认 0） | pricing×lnkchatbi | 每次报价人工输入维持 |
| O9 | lnkgateway 定位确认：是否永不独立面客（→ pricing/company-intro 记 not-applicable） | 2 消费方×lnkgateway | 维持 unsupported |
| O10 | lnkreport / lnkvision 是否补产品叙事资产（company-intro 面） | company-intro×2 产品 | 维持 unsupported |
| O11 | lnkgateway ontology unresolved 的远期处置方向（登记本体 / 裁定 not-applicable / 维持） | 解除 blocked 的唯一路径 | prd-gen/competitor 链路维持 blocked |

---

## 10. 不同决策下的后续工作清单

**若 owner 批准 B（推荐）**：按 §7 S1→S6 执行；每阶段收尾跑全量回归（附录 B）。

**若 owner 选 A（维持）**：不建 capability 文件；接受 §1.2 漂移现状；唯一必做止血是
O4（resolver 字段至少文档钉死），否则误导持续。

**若 owner 选 C**：先满足 O3；然后 S1/S2 改为建中心文件（位置 owner 定）+ S3 收编
registry + S4/S5/S6 不变；需额外出「防第二 authority」校验（capability 文件 schema
禁止出现 path/revision/authority 字段值，S5 脚本强制）。

**若 owner 暂不决策**：本包即基线快照；后续任何 skill 声称「支持某产品」时以 §3 矩阵
为准反驳；lnkcrm/lnkgateway 阻塞项维持。

---

## 11. 风险和回滚

| 风险 | 缓解 | 回滚 |
|---|---|---|
| capability 文件与实际行为漂移（声明 implemented 实则不可用） | evidence 强制指针 + verified_at + S5 聚合脚本与测试交叉 | 单文件回退（git revert 该 skill 的 capability 文件） |
| capability 被误读为产品事实 | §2.3 禁令 + schema 禁 path/revision 字段 + S5 cross-check | 同上 |
| S4 resolver 字段废弃破坏消费方 | 事前 grep 消费面：当前无程序化分支消费（仅 prose 引用，见 §1.1），变更前重扫 | resolver 单 commit revert；字段恢复无数据损失（company.yaml 本就无人设置） |
| S3 registry 收敛破坏 `test_product_governance_contracts.py` | 断言随迁移同步更新；先跑测试再合并 | registry 单 commit revert |
| 中心化诱惑复发（有人往 capability 文件里加路径事实） | S5 脚本 hard-fail + pre-commit hook（`pre-commit.sh` 生态已有） | 删违例行 |

---

## 12. lnkcrm owner 决策包（不自动执行晋升）

### 12.1 当前状态（resolver + 实测）

```yaml
product_id: lnkcrm
configured_code_root: null                    # company.yaml products[].code_root
observed_code_path: /opt/code/lnkcrm          # resolver 观察证据（仅证据，非 authority）
code_status: present-unconfirmed              # resolver 判定
observed_revision: ad6f0c0b112210f9a13b55d2b11bdeac8eb32481
observed_last_commit: 2026-10-03T18:10:19+08:00 "chore(spec): archive points expiry and clearance"
observed_openspec_scopes: 27 个（member-*/coupon-*/points-*/merchant-*/platform-*/tenancy 等）
docs_side_declared: "代码仓：无（code_root: null）"（INDEX.md）；code/README.md 状态 unresolved
```

**事实张力**：docs 侧三处（company.yaml / INDEX.md / code/README.md）仍声明「无代码仓」，
而外部 checkout 活跃（最近提交 2026-10-03，含 27 个 spec scope 与 backend/admin-web/
双 miniapp 工作区）。present-unconfirmed 是该张力的正确中间态，晋升与否是 owner 事实决策。

### 12.2 owner 最小确认问题（对应 prompt §七的 5 问）

1. **`/opt/code/lnkcrm` 是否是正式 code authority？**（判定依据可参考：工作区含未提交
   修改——属其他会话，本包未触碰；27 scope OpenSpec 活跃度；S9/S10 运行时证据 partial）
2. 若是：**是否允许将 `company.yaml.products[].code_root` 改为 `/opt/code/lnkcrm`？**
   （一行配置变更；COMPANIES.md 禁 `yaml.safe_dump` 重写，须 marker 定位纯文本插入）
3. 是否同步更新：`30-products/lnkcrm/INDEX.md`（代码行：unresolved→configured）、
   `30-products/lnkcrm/code/README.md`、`reconciliation/three-layer-ledger.yaml`
   （现三条 entry 的 `code_status: absent` 需新增一条晋升决策 entry，不涂改历史行）？
4. **lnkcrm 的 OpenSpec（27 scope）是否作为产品实现基线参与后续评估？**
   （影响 requirement-evaluator Step 0 的 grep 面、competitor 的 status_vs_lanlnk 判定、
   openspec-practice 回写链路）
5. **code authority 晋升后，哪些业务 skill adapter 纳入验证？**
   建议最小集：requirement-evaluator（实现级评估解锁，功能清单 unknown 语义可开始收敛）+
   strategy-brief-generator（浅盘点→深盘点）+ product-prd-generator（--code-root 显式
   确认路径收敛为 configured）；pricing/company-intro 不消费 code 层，无验证需求。

### 12.3 owner 未确认前的冻结线（各消费方现行行为，全部维持）

```yaml
layers.code_root: null
authority.code.status: present-unconfirmed
```

- requirement-evaluator：不得自动用观察 checkout 做代码验证（需显式 `--code-root` 等价确认）；
- product-prd-generator：`resolve_code_root` 维持报错；
- competitor-product-analyzer：checkout 仅只读证据定位；
- strategy-brief-generator：浅盘点（unconfirmed 标注）；
- pricing / company-intro：不消费 code 层，无变化。

---

## 13. 产品基线缺口决策（lnkchat / lnkgateway / lnkwebsite / lnkcrm）

状态规则：缺以下资料时只能 `blocked` / `unsupported` / `onboarding`，**不得自动从
lnkcre 借用**（跨域污染禁令）；「历史 CRM materials 文档」不得自动顶替 lnkcrm 产品基线
（O6 裁决前）。

### 13.1 lnkchat

| 消费方 | 缺口判定 | 需要的输入 | 现状证据 |
|---|---|---|---|
| requirement-evaluator | partial（基线过期） | 功能清单刷新（重跑 prd-gen）；问数/工作流类需求语义校准 | canonical 功能清单 2026-08-06（落后 HEAD） |
| pricing-generator | unsupported（O7） | 标准产品报价、功能项与价格映射、SaaS/私有化规则、续费规则、定制报价规则、产品功能清单接入 | 无报价数据；当前以「AI 岗位 Skill 服务」打包（跨产品编排） |
| competitor-product-analyzer | onboarding | 产品 ontology 对照先例、目标能力模型、竞品对照基线、差异映射规则 | ontology.yaml + 功能清单在位，无先例 |
| company-intro-generator | partial | 产品叙事资产已有；产品特定架构包无（V5 类扩展可选） | `AI知识库与工作流平台.md` |

### 13.2 lnkgateway

| 消费方 | 缺口判定 | 需要的输入 | 备注 |
|---|---|---|---|
| requirement-evaluator | blocked | 先有 PRD/功能基线（prd unresolved）；术语归一需 ontology（unresolved，O11） | 主阻塞在产品层非 skill 层 |
| pricing-generator | unsupported →（O9 确认不面客）not-applicable | 若面客：全套报价输入 | 内部 AI 网关 |
| competitor-product-analyzer | blocked | ontology 基线（owner-confirmed 不从代码反推） | S1.2 术语归一被阻 |
| company-intro-generator | unsupported →（O9）not-applicable | 若面客：产品叙事资产 | 同上 |

### 13.3 lnkwebsite

| 消费方 | 缺口判定 | 说明 |
|---|---|---|
| requirement-evaluator / pricing-generator / competitor-product-analyzer / company-intro-generator | 全部 not-applicable | 官网非对外软件商品（owner 2026-09-27 prd-only 裁定）；生成区功能清单自证非 canonical。唯一持续动作：content-operations 系 skill 的站点运营（矩阵外） |

### 13.4 lnkcrm

| 消费方 | 缺口判定 | 需要的输入 | 关联决策 |
|---|---|---|---|
| requirement-evaluator | partial（承诺级可用，实现级 blocked-by-code） | 功能清单实现状态收敛（依赖 code authority 晋升 + OpenSpec 基线确认）；需求匹配规则/差距分类/二开复杂度规则为通用件已就绪 | O5 |
| pricing-generator | partial（历史 CRM 报价无主使用） | lnkcrm 报价基线登记（正祥定价追认或另建）；lnkcrm 功能清单接入报价链 | O6 |
| competitor-product-analyzer | partial | `evidence/competitors/<vendor>/` 分析结论树；status_vs_lanlnk 判定依赖实现状态收敛 | O5（间接） |
| company-intro-generator | partial | 产品叙事资产已有（历史 CRM 叙事 + 正祥案例）；产品特定架构包可选；案例归属登记随 O6 | O6（叙事侧轻确认） |

---

## 附录 A：`adapter-capabilities.yaml` schema 草案（S1 定稿基础，未接生产路径）

```yaml
# schema: adapter-capabilities/v1（草案 2026-10-04，owner 批准前不落地）
# 归属：skills/business/<skill>/references/adapter-capabilities.yaml（每 skill 一份）
# 禁令：本文件只描述 <skill> 对产品的能力，禁止出现产品路径/revision/authority
#       字段值（产品事实一律经 shared.product_context resolver 解析）。
consumer_id: <skill-name>          # 必填，= 所在 skill 目录名
verified_at: <YYYY-MM-DD>          # 必填，最后实测日期
owner: opc                         # 必填，capability 行维护者
products:
  <product_id>:
    status: implemented | partial | onboarding | unsupported | not-applicable | blocked
    reason: []                     # 可选标签：missing-baseline | missing-pricing | missing-narrative |
                                   #   missing-adapter | blocked-by-authority | stale-baseline
    evidence:                      # 必填，≥1 条指针（本 skill 内文件段落 / 脚本符号 / docs 基线文件）
      - <path#anchor 或 file:symbol>
    notes: <可选说明>
# 跨产品服务打包（如 AI 岗位 Skill）不占产品行，写 service_packaging: 注释段
```

校验规则（S5 聚合脚本强制）：①schema 合法；②product_id 必须存在于某公司 company.yaml
（否则 unknown-product hard-fail）；③evidence 路径必须可解析（file 存在）；④文件内
不得出现 `code_root|docs_root|ontology:|prd_root` 等路径事实键；⑤`implemented` 必须有
运行先例指针（测试/交付物）。

## 附录 B：复现命令（本包证据链）

```bash
# 8 产品 authority 实测（§3.1 表）
export COMPANY_BASE=/opt/code/docs/lanlnk
cd /opt/code/skill/skills/meta/openspec-practice
uv run python scripts/resolve_context.py --all

# 功能基线存在性（§3.3.B）
ls /opt/code/docs/lanlnk/30-products/{lnkcre,lnkreport,lnkvision,lnkchatbi,lnkchat,lnkcrm}/prd/功能清单.md
head -12 /opt/code/docs/lanlnk/30-products/{lnkchat,lnkcrm}/prd/功能清单.md   # frontmatter/裁决头

# pricing 定价覆盖（§3.3.C）
grep -n "MI_DATA\|CRM_DATA\|AI_POSITION_SKILLS\|LNKCHATBI_DATA\|LNKCHATBI_PRICE" \
  /opt/code/skill/skills/business/pricing-generator/generate_quote.py
cat /opt/code/docs/lanlnk/config/pricing/pricing-basis.yaml

# 叙事资产（§3.3.E）
ls /opt/code/docs/lanlnk/materials/03-products/   # AI智能问数系统.md / AI知识库与工作流平台.md / 商圈会员CRM系统.md …

# lnkcrm 观察 checkout（§12.1，只读）
git -C /opt/code/lnkcrm rev-parse HEAD && git -C /opt/code/lnkcrm log -1 --format='%cI %s'
ls /opt/code/lnkcrm/openspec/specs | wc -l

# 回归（每阶段收尾必跑）
cd /opt/code/skill/shared/product_context && uv run python -m unittest discover -s tests -p "test_*.py"
cd /opt/code/skill/skills/meta/openspec-practice && uv run python -m unittest discover -s tests -p "test_*.py"
cd /opt/code/skill/skills/business/product-prd-generator && uv run pytest -q
cd /opt/code/skill/skills/business/pricing-generator && uv run pytest -q
cd /opt/code/skill && git diff --check && git status --short && git diff --name-only
```

## 附录 C：本包未做的事（门禁自检）

未修改：company.yaml、30-products/**（含 lnkcrm 全部）、/opt/code/lnkcrm、
product-registry.yaml、resolver、任何 SKILL.md/脚本/测试；未创建第二注册表；
未伪造任何评估/报价基线；未提交、未推送。唯一产出：本决策包文档（skill 仓
`references/` 审计位置，是否长期归档到 docs `00-governance/skills/` 由 owner 决定）。
