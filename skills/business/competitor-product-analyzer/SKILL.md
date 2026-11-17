---
name: competitor-product-analyzer
description: |-
  竞品产品能力分析与产品优化建议 Skill。基于「证据型能力抽取 + 加权对比矩阵 + 蓝联现状映射 + 分级改进建议」方案，
  把一份竞品资料（操作手册 / 产品手册 / 截图 / 数据字典 / 方案汇报）、一个授权 demo 账号、
  或一个已授权且合法持有的竞品安装包，评估成「竞品有哪些产品能力、证据来自哪里、蓝联该补什么、借鉴什么、观察什么」。
  证据来源分四类互补（document 文档 / structure 结构 / runtime 运行时 / implementation 实现），
  支持安装包静态盘点、问题驱动的定点逆向（宽盘点、窄深读）与授权 demo 取证，
  统一归档为带 usage_scope 使用范围约束、可供 OPC 消费的证据摘要。
  触发场景："分析一下旗茂商管系统"、"用这个 demo 账号看看竞品有什么功能"、"对比 XX 竞品给出产品改进建议"、
  "把这份竞品操作手册转成能力清单和借鉴建议"、"竞品 demo 探测 + 文档对照"、
  "静态分析这个竞品安装包"、"对这个已授权的安装包做定点反编译取证"、"竞品包 + demo 交叉核对"。
  仅面向内部产品规划与产品优化决策，不生成完整 PRD、不生成报价/方案/投标文件、不做战略定位判断。

  不做的事情：
  - 不生成完整 PRD（交给 product-prd-generator）
  - 不做战略定位/市场判断（交给 strategy-brief-generator）
  - 不写方案/报价/投标（交给 company-intro-generator / pricing-generator / bid-doc-master）
  - 不评估客户需求满足度（交给 requirement-evaluator）
  - 不修改业务系统代码（/opt/code/lnkcre）
  - 不绕过登录/验证码/权限/反爬，不做漏洞测试
  - 不做未授权获取或破解（源代码/安装包/账号/许可证）
  - 不把受限研究结论自动用于对外方案、投标或宣传
compatibility: >
  纯提示词 skill，无 Python 依赖。
  文档转换复用 material-importer（markitdown + 图片提取 + OCR）。
  Demo 探测复用 doc-generator 的 Playwright 模式与文本/角色 locator 规范。
  安装包静态分析/定点逆向的操作纪律见本 skill
  references/static-analysis-and-reverse-engineering.md（工具为系统级 unzip/jar/javap/
  反编译器等，无新增 Python 依赖）。
   能力对齐参考目标产品的三层基线（本体层 ontology/aliases）；产品路径事实（产品 ID 归一、
   ontology/PRD/code 三层 authority、code_root 状态）来自公共 shared.product_context resolver
   （company.yaml 为唯一产品台账，2026-10 迁移），不得在非 CRE 产品上静默回退到商管 ontology。
   product-prd-generator 的 references/product-registry.yaml 已退役（D1，2026-10-04
   删除）；产品与路径事实 = company.yaml + shared.product_context resolver，不得据此
   解析路径或判定 authority 状态。
   商管域知识仅在目标产品为 LnkCRE/MI-CRE 时经 lnkcre ontology 入口解析（resolver 的
   ontology authority；mi-cre 目录已于 2026-09 合并删除）。
   统一竞品关系上下文（workspace_company / target_company / target_product /
   competitor_company / competitor_product / source_version / product_version /
   account_role / permission_scope / captured_at / usage_scope）唯一权威源：
   skills/business/material-importer/references/material-classification.md（本 skill 引用
   不复制）。竞品关系是多对多（target_company+target_product ↔ competitor_company+
   competitor_product）：同一竞品公司多个产品分别记录、同一竞品产品在不同目标产品下分别
   建映射，不自动共享差距/优先级/PRD 结论。授权 demo 登录、只读探测与快照归档归
   material-importer 采集层；本 skill 消费已归档快照，不重复登录。无目标产品
   （target=unknown）时只输出竞品资料索引/能力清单/证据台账/待验证问题，不输出相对
   目标产品的差距或 PRD 需求。
   跨 skill 交接契约：product-prd-generator 的 `references/product-governance/`（共享 source-reference / ontology-change-set；本 skill 只消费不修改）。

  Quick start:
  ```bash
  export LANLNK_BASE=/opt/code/docs/lanlnk
  ```

  用户只需告诉 Agent 竞品名、资料来源（手册路径 / demo URL / 授权安装包路径 / 任意组合）和对照产品，Agent 自动完成：
  - "分析一下旗茂商管系统，操作手册在 materials/13-competitors/qimao/"
  - "用 demo 账号 llkj/llkj123 探测 http://oa.1qmall.cn/SMallTest/，对比 LnkCRE 给改进建议"
  - "这份竞品手册 + 这个 demo 账号，做交叉验证，输出能力矩阵和借鉴清单"
  - "这个安装包是客户交付的授权件，做静态盘点 + 免租期分段问题的定点深读"
---

# Competitor Product Analyzer — 竞品产品能力分析与产品优化建议 Agent Pipeline

## DocSpec 质量基线

本 skill 生成的竞品能力清单、证据台账、对比矩阵、产品优化建议和 review 清单必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `DocSpec-通用文档质量规范.md`、`PRD质量规范.md` 和 `文档验收清单.md`。竞品证据必须可追溯，不得把 demo 看不到写成竞品没有。

基于「证据型能力抽取 + 加权对比矩阵 + 蓝联现状映射 + 分级改进建议」方案。

## 核心定位

这个 skill 是 **PRD 之前、战略简报之后的产品情报层**。它输出可被增量 PRD 消费的证据和稳定能力记录。

它回答的是：

- 竞品实际有哪些产品能力（不是销售话术）？
- 每条能力的证据来自哪里？属于哪一类来源（document / structure / runtime / implementation），可信度多高？
- 四类证据来源各自能证明什么、不能证明什么（文档记载 ≠ 已部署；表结构存在 ≠ 功能可用；路由代码存在 ≠ 已启用；代码分支存在 ≠ 实际执行）？
- 蓝联当前产品（LnkCRE / CRM / AI）相对竞品是 existing / partial / missing / better？
- 竞品的哪些设计值得蓝联借鉴？哪些必须补齐？哪些只是观察？
- 产品改进建议如何排优先级（P0/P1/P2/P3）？
- 哪些结论仍是未扫描、不可访问、不可分析或冲突，不能被写成 missing？

它不回答：

- 蓝联整体战略怎么定位（→ strategy-brief-generator）
- 具体功能字段/接口/页面怎么设计（→ product-prd-generator）
- 客户方案怎么写、投标怎么响应（→ company-intro-generator / bid-doc-master）
- 客户需求满足度多少（→ requirement-evaluator）

## 统一竞品关系上下文与多对多竞品关系

字段定义**唯一权威源**：`skills/business/material-importer/references/material-classification.md`（本节只留简例，不复制定义）。本 skill 的能力记录、证据台账、对比矩阵与交接导出必须携带同一组上下文字段：

```yaml
workspace_company: <资料归档公司>
target_company: <目标公司或 unknown>
target_product: <目标产品或 unknown>
competitor_company: <竞品公司>
competitor_product: <竞品产品或 unknown>
source_version: <证据版本或 unknown>
product_version: <目标产品版本或 unknown>
account_role: <demo 角色或 not-applicable>
permission_scope: <demo 权限或 not-applicable>
captured_at: <采集时间或 not-applicable>
usage_scope: internal-product-research
```

**多对多关系**（不是 `target_product → competitor_company`）：

- 独立映射一：`target_company=lanlnk + target_product=lnkcre ↔ competitor_company=haiding + competitor_product=海鼎 CRE`（source_version 如 4.1.0）
- 独立映射二：`target_company=lanlnk + target_product=lnkcrm ↔ competitor_company=haiding + competitor_product=海鼎 CRM 产品`（source_version unknown）
- 独立映射三：`target_company=lanlnk + target_product=lnkcrm ↔ competitor_company=maoku + competitor_product=猫酷会员/CRM 产品`

规则：

- 同一竞品公司多个产品（如 mingyuan → 云资管/云物业/云公寓）**不得合并为一个能力清单**；每个 competitor_product 分别记录证据、版本、能力和限制。
- 同一竞品产品被多个目标产品引用时（lnkcre↔X 与 lnkcrm↔X），**两条映射分别建立**，不自动共享差距、优先级或 PRD 结论。
- 只知道竞品公司、不知道具体产品（`competitor_product: unknown`）：允许输出公司级待确认线索（资料索引/版本线索），**不得生成具体产品能力结论**。
- 历史字段 `vendor` 只表示竞品公司（legacy 别名，兼容读取），不能替代 competitor_product；`status_vs_lanlnk` 是历史字段名，语义 = 相对 `target_company + target_product` 的现状（不假定蓝联）。

## 与兄弟 Skill 的边界

```
material-importer（文档转换/OCR/授权 demo 快照归档） ←─ 复用 markitdown+图片提取；demo 采集与快照按其归档契约落位（material-classification.md）
        ↓
doc-generator（demo 探测/截图）    ←─ 你复用它的运行时探测/locator 规范（不直接调用）
        ↓
competitor-product-analyzer（能力分析 + 改进建议）  ←─ 你在这里（消费已归档快照，不重复登录）
        ↓
product-prd-generator（PRD / 功能清单 / 差距分析）  ←─ 你的改进建议交给它落地
        ↓
strategy-brief-generator（战略定位 / 竞对打法）     ←─ 你的能力矩阵作为战略证据之一
```

**严格不做的事：**

- 不登录 demo 采集快照（登录/只读探测/归档 = material-importer 采集层职责；本 skill 只消费已归档快照，重登仅限证据缺口/冲突/最新状态并在 pending 登记）
- 不写字段、接口、页面、数据模型（→ PRD）
- 不写战略定位、市场判断、客户路线（→ strategy）
- 不写方案汇报、报价、投标（→ company-intro / pricing / bid-doc）
- 不评估客户需求满足度（→ requirement-evaluator）
- 不直接修改业务系统代码（/opt/code/lnkcre）
- 不绕过登录/验证码/权限/反爬，不做漏洞测试或压力测试
- 不做未授权获取或破解（源代码/安装包/账号/许可证）
- 不把竞品截图/UI 文字直接用于客户材料；不把受限研究结论（usage_scope=internal-product-research）自动用于对外方案、投标或宣传
- 不把 OPC/产品 owner 的决策当竞品证据；不自动写 canonical ontology（只允许 draft 提案）

## 输入模式（manual / demo / package）

| 模式 | 触发条件 | 主证据来源 | 弱证据来源 |
|---|---|---|---|
| `manual-only` | 只有手册/产品文档/截图/PPT | 操作手册、功能手册、数据字典、蓝图方案 | 销售策略、方案汇报 |
| `demo-only` | 只有 demo URL 或测试账号 | 运行时探测（菜单/页面/流程/截图） | 无 |
| `package-only` | 只有已授权且合法持有的安装包/交付包 | 静态结构盘点 + 问题驱动定点深读（structure / implementation 观察） | 无 |
| `manual-plus-demo` | 手册 + demo 都有 | 手册与 demo 一致的能力 | 仅手册提及或仅 demo 可见的能力（需交叉验证）|
| 多来源组合 | manual / demo / package 任意组合 | 各来源在其认识论边界内的主张 + 来源间交叉核对 | 越界主张（降级为待验证问题） |

**模式自动判定**：Agent 根据用户输入自动判定模式，无需用户显式指定。两者都有时默认 `manual-plus-demo`，做交叉验证；有授权安装包时纳入 package 维度。**来源组合不改变 S0/S1 边界**，交叉核对按 evidence-ledger 的独立性与版本一致性规则执行——不因多一份同源摘要或多一种载体自动升级 confidence。

**package 模式前提**：安装包必须已获授权且合法持有（竞品方提供 / 客户合同范围内交付 / 公开渠道），EULA/保密冲突先核对（见 `references/safety-and-ethics.md`、`references/static-analysis-and-reverse-engineering.md`）。

## 方法论

### 能力矩阵，不是功能打勾表

行业最佳实践明确：100 行的"有/没有"打勾表对决策无价值。本 skill 强制使用**加权能力矩阵**：

- 每条能力记录**实现质量**（Leading / Competitive / Behind / Missing），不是 binary yes/no
- 每条能力挂**证据链**（文件路径 + 章节/页码 + 截图 + URL + 探测时间）
- 每条能力标**置信度**（high / medium / low）
- 每条能力映射**蓝联现状**（existing / partial / missing / better-than-lanlnk / unknown）
- 改进建议分四类：**补齐 / 增强 / 借鉴 / 观察**，并标注 P0/P1/P2/P3

### 证据纪律

**每条能力判断必须可追溯。** 战略简报的证据纪律在此同样适用，三类标记：

| 标记 | 含义 | 要求 |
|---|---|---|
| `【证据】` | 来自资料或运行时的事实 | 必须引用具体来源（文件 + 章节/页码 或 URL + 截图 + 探测时间）|
| `【判断】` | 基于证据的推理 | 必须列出依据的证据 ID |
| `【假设】` | 未证实的假设 | 必须标注，并说明如何验证 |

**四类证据来源互补，不是由弱到强的等级**（evidence_kind：document / structure / runtime / implementation，唯一权威定义见 `references/evidence-ledger.md`）。每种来源限定可证明范围：文档记载 ≠ 功能已部署；表/字段存在 ≠ 完整业务功能可用；路由/菜单代码存在 ≠ 已授权、已启用或运行成功；代码分支存在 ≠ 当前环境实际执行该分支；demo 实测仅适用于被观察版本、角色、配置、时间和场景；安装包与 demo 版本未确认一致时分别记录，不拼接成同一部署状态。

禁止的行为：

- 禁止把销售策略材料当产品事实（只能作弱证据，置信度 low）
- 禁止把"demo 账号看不到"等同于"竞品没有"
- 禁止把方案汇报 PPT 的功能列表等同于实际能力（汇报材料会夸大）
- 禁止无来源的能力断言
- 禁止把竞品宣传话术直接抄进蓝联产品建议
- 禁止把同一原件的派生产物（转换文本/OCR/能力模型/摘要/交接包）当多份独立证据累计——同源只计一次（来源链）；**同一安装包内的 DDL、路由与代码同链**，不因载体不同计独立
- 独立性未知（`independence=unknown`）不得默认独立，不得据此提升 confidence；不同文件 / 不同 source_type / 不同 evidence_kind 本身不构成独立性依据
- 禁止把 evidence_kind 当强弱等级（implementation ≠ "最强证据"，structure ≠ "功能全集"）；来源类别改变不得自动提升 confidence
- 禁止把静态路由/菜单代码当功能全集，把代码分支当实际运行
- 禁止按 JS/JAR 文件总数推断产品规模——第三方依赖、运维组件与业务代码必须先区分
- 禁止"不落库、不留来源"的隐性研究——任何分析结论必须入三层归档并挂台账锚点（见 `references/static-analysis-and-reverse-engineering.md`）
- 缺 SHA/页码锚点/evidence ID/证据状态/来源类型/版本 → 失败关闭：`claim_type=假设` + confidence 降级 + 进 pending 待核实，禁静默补齐
- 来源类型默认解释：PPT 方案=厂商声称、操作手册=文档记载、Demo=被观察环境、SQL/数据字典=结构线索、客户蓝图不泛化为标准产品能力
- 图片 / text-sparse / OCR 投影的证据边界规则（检测三态语义、`undetermined` ≠ `none`、页级锚点 `source_sha256 + slide N`、OCR=检索线索、图片缺失≠证据不存在、fresh-clone 三项要求、evidence_state 映射）**唯一权威源**：`skills/business/material-importer/references/provenance-evidence-boundary.md`（material-importer 拥有，本 skill 引用不复制）；material-importer 的 `text-sparse` 页级信号 = 回看该页原件的复核提示，按需回看该页原图，不自动全量 OCR
- 判「版本演进/术语变更」必须先对照文档链当前版本——单链（仅 demo 或仅单一客户旧版实拍）判演进不可靠，客户环境用词≠产品演进（2026-10-31 海鼎实证：demo「已结束」vs 东苑 2021「已结案」，经手册 L190 纠正）
- 厂商材料截图可见调试工具痕迹（如 vConsole 调试按钮）= 演示环境/原型证据，佐证「方案宣称≠生产交付」的认识论上限（2026-10-31 海鼎移动方案 PPT 多屏实证）
- **口径勘误纪律**：数量/清单类口径错误（如合同族 13→12 类清点笔误）的修正三原则——①原文件留勘误注记（不静默改正，保留「原 N 系清点笔误」痕迹）；②同步全部引用处（INDEX、下游 PRD、包表）；③已归档历史件（回执、已 released 包）不回溯改，差异在下游登记。与「状态只降不升」互补：那是能力状态维度，这是口径数字维度，两者都要求留痕（2026-11-01 海鼎合同域实证）

详细规则见 `references/evidence-ledger.md`（来源谱系/升级留痕/失败关闭）。

### 能力身份与状态纪律

每条新能力或修订能力必须保留稳定 `trace_id`/`capability_id`、`source_refs`、`target_product` 和 `target_repo`（若已知）。必须区分：

- `evidence_state`: `observed | inferred | not_found | not_scanned | inaccessible | conflicting`
- `implementation_status`: `existing | partial | missing | explicitly-not-do | unknown`

demo 账号看不到、目标仓代码扫描器未覆盖或资料缺页，只能进入对应证据状态，不得直接判断竞品或蓝联缺少能力。

### 共享产品治理契约集成（handoff contract）

竞品证据流向 PRD 与 ontology 工作流时，统一挂接共享契约目录：
`/opt/code/skill/skills/business/product-prd-generator/references/product-governance/`（owner 为 product-prd-generator；本 skill 只消费、不修改，也不向该目录写入任何文件）。契约的字段与枚举以该目录下各 schema 为准，本 skill 文档不复制定义；本文件出现的取值表仅约束本 skill 自身产物。

**ID 映射（本 skill 保留所有权，共享 schema 只链接不取代）**：

| 本 skill 字段 | 共享 source-reference 字段 | 说明 |
|---|---|---|
| `evidence_id`（`EV-NNN`） | `evidence_id` | 原值透传；`evidence-ledger.json` 仍是唯一权威记录 |
| `capability_id`（`CAP-<module>-<slug>`） | `capability_id` | 原值透传；`capability-map.json` 仍是唯一权威记录 |
| `trace_id` | `trace_id` | 竞品分析、增量 PRD、OpenSpec change、实施回写全程复用同一 ID |
| `source_ref` | `source_ref` | 公司根相对路径（如 `materials/13-competitors/<vendor>/05-实施与服务/…`）；外部 URL 与代码仓引用除外 |

导出时每条竞品观察对应一条 `competitor_observation` 类型的共享 source reference，`evidence_id`/`capability_id`/`trace_id` 按上表透传，`evidence_state` 与 `confidence` 按本 skill 台账原值填写。交接导出保留谱系（lineage：derived_from/independence/applies_to）关联与验证范围；断链/缺 ID 显式待核实、禁伪造 ID；摘要/归并/映射不改变证据状态。

**来源边界（provenance boundary）**：

| 层 | 本 skill 标记 | 共享契约对应 | 记录者 |
|---|---|---|---|
| 竞品事实/观察 | `claim_type=证据` | `competitor_observation` + `evidence_state=observed` | 本 skill，必须挂 `evidence_id` |
| 基于证据的推理 | `claim_type=判断` | `evidence_state=inferred` | 本 skill，必须列出依据的 `evidence_id` |
| 产品决策 | 不进 evidence-ledger | `product_decision` + decision 对象 | 仅 OPC/产品 owner 单独记录 |

OPC/产品 owner 的决策**不是竞品证据**。roadmap 方向、改进建议优先级、ontology 变更是否采纳，只能由一条单独记录的 owner decision 批准（decision 对象按共享 schema，含 owner 与 status）。本 skill 输出的 P0/P1/P2 建议只是这类决策的输入，`【判断】`条目最多作为 supporting source，永远不能替 owner 拍板。

**ontology 增量是提案，不是写入**：`standard_term=null` 的未映射术语、或映射存疑的观察，可按共享 `ontology-change-set` 契约打包为 `draft` 提案（`changes[].source_ids` 指向上述 source reference）。约束：

- 永不自动进入 canonical ontology，晋升必须经 owner decision 审批
- 永不构成"某条 PRD feature 必须做"的依据；competitor observation 只是 source，不是需求
- 目标产品仅限共享 README 列出的产品 ID；lnkwebsite 不在该契约范围

### 与增量 PRD 的交接

`lanlnk-product-improvement-recommendations.md` 的 P0/P1/P2 项进入 `product-prd-generator` 后，必须携带原始 evidence IDs 和 trace IDs。每个 Gap 应提供目标仓库可复核的反证入口（OpenSpec spec、代码路径、路由、表或符号），避免把 code-map 漏扫写成新需求。实施完成后由目标仓库返回回写包，docs 侧再更新能力基线。交接载体按上节「共享产品治理契约集成」的 source-reference 映射执行，evidence IDs 与 trace IDs 原值透传。

链路边界：**竞品观察 → PRD 分析输入 → 产品决策 → 正式需求**。竞品分析结果不构成 PRD 需求授权，不得自动变成正式 PRD 需求；采纳与否由既有 owner decision 流程决定。product-prd-generator 若消费运行时快照：图片/快照只作辅助证据，关键页面字段/流程仍需 OPC 视觉回看并带源锚点；不得假设 PRD 的自动 doc_map 会读取图片内容（见 `references/runtime-snapshot-protocol.md`「下游消费约定」）。

### 合规与凭据安全（红线）

| 红线 | 说明 |
|---|---|
| 只使用授权访问 | demo 账号必须由竞品方主动提供或公开渠道获得，不得伪造身份、不得盗用账号 |
| 安装包必须合法持有且授权 | 来源 = 竞品方提供 / 客户合同范围内交付 / 公开渠道；EULA/保密冲突先核对（单列记录，按冲突流程处理）；合法持有 ≠ 拥有所有分析与传播权利 |
| 逆向只读且最小必要 | 宽盘点 + 问题驱动窄深读；不运行包内服务/脚本作默认步骤；不破解许可证、不修改授权判断 |
| 不复制实现代码 | 第三方实现代码（依赖库或竞品业务代码）不得直接复制进蓝联业务代码；分析结论可借鉴 |
| 不绕过任何控制 | 不破解验证码、不绕过权限、不破解反爬、不绕过接口限流 |
| 不做攻击性测试 | 不做漏洞扫描、SQL 注入、压力测试、批量数据导出 |
| demo 默认只读 | 不默认执行会写入业务数据的新增、提交、审批、删除等操作 |
| 凭据只进 .auth.json | 用户名密码只写入 `$ANALYSIS_ROOT/.auth.json`（mode 0600，gitignored），不进日志/报告/截图说明/git |
| 密钥/连接串/个人数据不落材料 | 许可证密钥、序列号、数据库连接串、API token、个人数据不进 materials、台账 notes 或日志 |
| 最小数据采集 | 只采集能力分析必需的页面/字段/截图，不抓取客户数据、个人隐私、交易明细 |
| 截图默认脱敏 | 截图中的客户名、手机号、金额等敏感信息在写入证据前必须打码或替换为占位符 |
| 留来源与时间戳 | 每条证据记录 URL + 探测时间 + 账号权限等级（或包哈希 + 工具 + 锚点），便于复核 |

详细规则见 `references/safety-and-ethics.md`。

## OPC 消费与使用范围（usage_scope）

- 证据与摘要**默认 `usage_scope=internal-product-research`**（字段定义唯一权威：`references/evidence-ledger.md`）。
- 内部研究材料可以用于**形成假设、比较和待验证问题**。
- **不得自动**把竞品代码、UI 文本、截图或受限结论用于对外方案、投标或宣传。
- 对外能力陈述需有适当、可引用的**独立证据**支撑（如公开手册、公开评测、招标公示），且明确陈述主体与适用范围。
- 导出共享契约时 `usage_scope`/`limitations` 不得静默丢失——接收方无法保留使用限制时停止该项导出并说明原因（规则见 `references/evidence-ledger.md`「导出纪律」）。
- materials 中 implementation 摘要按内部研究材料管理；单一消费者（仅 OPC）不是实际访问控制，也不消除许可或保密义务。

## 目录契约

### 两阶段分离：采集入库（S0）+ 能力分析（S1/S5）

本 skill 的产物分两个阶段，目录严格分离：

| 阶段 | 触发 | 产物位置 | 性质 |
|---|---|---|---|
| **S0 采集入库** | 用户提供手册路径或 demo 账号 | `incoming/` + `raw/` + `materials/13-competitors/` | 竞品素材沉淀（三层归属；demo 快照归档按 material-importer 归档契约执行）|
| **S1/S5 能力分析** | 需要做能力矩阵/改进建议/PRD 时 | `$ANALYSIS_ROOT`（按 target_product 解析，见下节；**不是无条件 lnkcre**） | 目标产品视角对竞品的分析结论 |

> **为什么分离**：采集入库是"竞品有什么"（事实层，可被多个 skill 复用）；能力分析是"蓝联该怎么改进"（判断层，依赖蓝联功能清单和客户优先级）。混在一起会导致采集产物被分析结论淹没，且 materials 层缺失导致其他 skill 无法复用竞品素材。

### 产品代号与竞品证据隔离

- 对照产品代号按**目标公司产品台账**归一：lanlnk 的 **LnkCRE / MI / MI-CRE / lnkcre / 商管系统**
  统一经公共 resolver 按 company.yaml 归一为 canonical product id **`lnkcre`**（同一产品；MI-* 文档 ID
  稳定不变，不代表目录仍叫 mi-cre）；`lnkcrm` / `lnkcard` / `lnkreport` 等同理。gdcreia / lianyou
  等其他公司只能通过各自 `config/company.yaml` 的 products 解析目标产品（如 `cre-association-platform`
  / `溯源APP`）——**公司 slug 不是产品 id，不得把公司当 target_product**。本 skill 不自维护第二套产品列表，
  不按产品 ID 拼接 `/opt/code/<id>`（resolver 边界：`openspec-practice/scripts/resolve_context.py`）。
- **竞品分析写入根 `$ANALYSIS_ROOT`（按 target_product 解析）**：resolver context 的 `layers.docs_root`
  下 `evidence/competitors/<competitor_company>/<competitor_product>/`。lnkcre 命中时即
  `$LANLNK_BASE/30-products/lnkcre/evidence/competitors/<competitor_company>/<competitor_product>/`
  （canonical，唯一写入位置；mi-cre 旧根已随 2026-09 目录合并删除，无迁移期读取）。**多对多落位**：
  同一竞品公司多个产品分目录存放（`…/competitors/haiding/海鼎 CRE/` 与 `…/competitors/haiding/海鼎 CRM 产品/`
  互不合并）；同一竞品产品在不同 target_product 的 docs_root 下分别成册，不共享差距/优先级。
  历史已归档的 `evidence/competitors/<vendor>/` 一级路径继续有效、原位消费，不强制迁移；新产物按
  `<competitor_company>/<competitor_product>/` 两级落位（competitor_product 为 unknown 时先落
  `<competitor_company>/_unknown-product/` 待确认线索目录，不出能力结论）。
- **S0 raw 落位按目标产品所属业务域的项目根**：lnkcre 历史为 `raw/prd-商管系统/02-competitors/<vendor>/<6类>/`；
  其他目标产品按其 raw 项目根解析（如 CRM 竞品走会员/CRM 项目根），**不默认商管路径**。
- **跨产品隔离**：LnkReport / LnkChat / LnkChatBI / LnkCard 等产品的竞品资料与分析结论不得混入
  其他产品的 evidence 树（反之亦然）；目标产品不是 lnkcre 时不读取商管 ontology / LnkCRE
  feature-baseline。
- **authority 状态显式处理**：目标产品 ontology authority 为 not-applicable（lnkwebsite）
  或 unresolved（lnkgateway）时，术语归一明确降级标注、不回落商管 ontology；code authority
  为 present-unconfirmed 时，观察到的 checkout 只作只读证据定位，不当作
  configured code authority。lnkcrm（code authority=complete，O5-lnkcrm-code 对账后）：
  status_vs_lanlnk 判定输入纳入 lnkcrm OpenSpec scope 基线（`/opt/code/lnkcrm/openspec/specs/`
  非空 scope 集，含 member-*/coupon-* 等 scope 族；锚定集合不钉数量，以实测 `ls` 为准）——
  scope 命中可作「蓝联该域已有实现基线」的基线层证据（引用 scope 名）；实现级验证
  （deep 读码、实现质量判定）保持 blocked（本 skill 未入 Q5 最小验证集）。scope 基线已
  纳入；实现级评估 O5-Q5 已解锁（2026-10-04，解锁集 = requirement-evaluator /
  strategy-brief-generator / product-prd-generator）。

### S0 采集入库：三层归属（遵循 lanlnk 统一素材库规范）

> 下图以 **lnkcre（商管域）为例**：`prd-商管系统` 是 lnkcre 的 raw 项目根。其他目标产品按其业务域项目根落位（如 CRM 竞品走会员/CRM 项目根），**不默认商管路径**；`<vendor>` 目录按 `<competitor_company>` 组织，多竞品产品分子目录。

```text
$LANLNK_BASE/
├── incoming/competitor-<vendor>/              ← 🟢 原始证据入口
│   ├── runtime-snapshots/                     demo 探测原始证据（HTML 快照/登录响应/导航响应）
│   ├── manuals/                               手册原始文件（PPTX/DOCX/XLSX/PDF）
│   ├── proposals/                             方案汇报原始文件
│   └── packages/                              安装包/交付包原件（授权持有；不因转换完成自动删除）
│
├── raw/<目标产品业务域项目根>/02-competitors/<competitor_company>/   ← 🟡 转换产物（gitignored，百度盘；lnkcre = raw/prd-商管系统/02-competitors/…）
│   ├── 01-销售策略/                           markitdown 转换的 md + 提取图片
│   ├── 02-方案汇报/
│   ├── 03-报价商务/
│   ├── 04-产品功能/
│   │   ├── page-fields/                       从 demo HTML 提取的页面字段/按钮 JSON
│   │   └── package-analysis/                  安装包静态分析产物（结构清单/反编译投影/工具输出/取证记录；完整反编译代码只留此层）
│   ├── 05-实施与服务/
│   │   └── demo-runtime/                      demo 运行时探测记录（capture-manifest/runtime-probe）
│   └── 06-行业洞察/
│
└── materials/13-competitors/<vendor>/          ← 🔵 权威精华（进 Git）
    ├── README.md                              素材库入口（资料状态+目录结构+关键发现）
    ├── source-inventory.md                    资料盘点（来源/日期/证据强度/缺口）
    ├── demo-page-inventory.md                 demo 页面/菜单/字段/按钮/截图清单
    ├── 04-产品功能/包结构盘点摘要.md           宽盘点摘要（模块/载体/第三方标记/锚点；structure 层）
    ├── 04-产品功能/定点代码分析.md             定点深读结论摘要（implementation 层，usage_scope=internal-product-research；不复制大量反编译代码全文）
    ├── 01-销售策略/ ~ 06-行业洞察/             6类分类精华
    └── imgs/                                  脱敏截图（百度盘，gitignored）
```

> **implementation 摘要可入 materials**（可检索、可复核，保留来源/锚点/范围/限制），完整反编译代码只留 raw。**不采用"不落库、不留来源"的隐性研究方式**；单一消费者（仅 OPC）不是实际访问控制，也不消除许可或保密义务。详见 `references/static-analysis-and-reverse-engineering.md`「三层归档」。

**6类分类体系**（所有竞品统一，证据强度标注）：

| 分类 | 证据强度 | 典型内容 |
|---|---|---|
| `01-销售策略/` | 极弱（销售话术，不作产品事实）| 市场定位、培训资料、星狼营 |
| `02-方案汇报/` | 弱（汇报会夸大，需运行时或手册佐证）| 通用售前方案、汇报 PPT |
| `03-报价商务/` | 仅作定价参考，不进能力矩阵 | 报价单、商务条款、合同模板 |
| `04-产品功能/` | **强**（功能清单、数据字典、业务逻辑）| 功能清单、demo 页面字段、数据字典 |
| `05-实施与服务/` | **强**（操作手册、功能手册、蓝图方案）| 操作手册、demo 探测记录、蓝图 |
| `06-行业洞察/` | 仅作背景，不进能力矩阵 | 行业最佳实践、业务标准化、趋势 |

### S1/S5 能力分析：competitor-analysis 输出

```text
$ANALYSIS_ROOT = <target_product docs_root>/evidence/competitors/<competitor_company>/<competitor_product>/
                 # lnkcre 命中时即 $LANLNK_BASE/30-products/lnkcre/evidence/competitors/<cc>/<cp>/
                 # 历史已归档 evidence/competitors/<vendor>/ 一级路径原位消费，不迁移
├── .auth.json                          ← demo 凭据（mode 0600，gitignored；采集归 material-importer 时由其管理）
├── capability-map.json                 ← 竞品能力结构化清单（从 materials 素材抽取）
├── competitor-capability-map.md        ← 人类可读版
├── ability-comparison-matrix.json      ← 加权对比矩阵（含蓝联现状 + 改进建议）
├── ability-comparison-matrix.md
├── lanlnk-product-improvement-recommendations.md  ← 主交付件：产品改进建议
├── evidence-ledger.json                ← 证据台账（引用 materials/raw 路径）
├── evidence-ledger.md
└── review/
    └── pending-items.md                ← 待确认/冲突/缺口
```

> **competitor-analysis 不存原始素材**：只存分析结论。原始素材和转换产物在 S0 阶段已入三层。competitor-analysis 中的 evidence-ledger 通过路径引用 materials/raw 中的证据，不复制原文。

## 处理流程

### S0 采集入库阶段（手册/demo 采集 → 三层归属）

```
S0.1: 输入解析 → 判定模式（manual-only / demo-only / manual-plus-demo）
      ↓
S0.2: 原始证据入库 → incoming/competitor-<vendor>/
      ├── manual: 复制原始文件（PPTX/DOCX/XLSX/PDF）
      └── demo: 抓取 HTML 快照 + 登录响应(脱敏) + 导航响应 + 页面 HTML
      ↓
S0.3: 转换产物入库 → raw/<目标产品业务域项目根>/02-competitors/<competitor_company>/<6类>/
      （lnkcre = raw/prd-商管系统/02-competitors/…；其他目标产品按各自项目根，不默认商管路径）
      ├── manual: markitdown 转 md + extract_images 提取图片 + OCR
      └── demo: 正则解析页面字段/按钮 → page-fields JSON + demo-runtime 记录
      ↓
S0.3P（条件触发：有授权安装包）: 安装包静态分析与定点逆向（宽盘点 → 问题登记 → 窄深读）
      ├── 宽盘点: 包/模块/DDL/静态路由/配置清单 + 第三方依赖区分 → raw 04-产品功能/package-analysis/
      ├── 问题登记: 每次深读先登记明确业务问题（S1 待验证项 / 来源冲突 / 宽盘点候选）
      └── 窄深读: 最小必要只读反编译，记录问题/目标模块/工具版本/原件哈希/锚点/结果/未解决项
      ↓ 详见 references/static-analysis-and-reverse-engineering.md
S0.4: 权威精华入库 → materials/13-competitors/<vendor>/<6类>/
      ├── README.md（素材库入口）
      ├── source-inventory.md（资料盘点）
      ├── demo-page-inventory.md（demo 页面/菜单/字段/按钮/截图清单）
      ├── 04-产品功能/能力清单.md（从 page-fields 提炼的人类可读能力清单）
      ├── 05-实施与服务/截图索引.md（截图清单 + 脱敏规则）
      └── imgs/（脱敏截图，百度盘）
      ↓
S0.5: 资料盘点交付 → 用户确认素材完整性和缺口
      ↓
S0.6: 竞品内部自对齐（可选，条件触发）→ unified-capability-map.md
      ↓ 触发条件：原始 .md > 30 个 或 来源类型 ≥ 3 种 或 有跨模块交叉
```

**S0 阶段边界**：只做入库和素材沉淀，不做能力矩阵、不做产品改进建议、不做 PRD。这些进入 S1/S5。

### S0.6 竞品内部自对齐（可选，条件触发）

当竞品资料量大、来源多时，直接从散文件逐条对齐 MI 容易遗漏、重复和跨模块混乱。S0.6 在 S1 之前产出**竞品单一权威能力视图**，作为 S1 的唯一输入。

**触发条件**（满足任一即建议启用）：

| 条件 | 阈值 | 理由 |
|---|---|---|
| 原始 .md 文件数 | > 30 | 文件多 → 跨文件重复概率高 |
| 来源类型数 | ≥ 3 种（如手册 + PPT + 数据字典 + 方案汇报）| 来源多 → 同一能力多版本描述 |
| 跨模块交叉 | 同一实体（如"合同"）在 3+ 模块中出现 | 交叉多 → 模块边界不清 |

**不触发时**：S1 直接从 materials/raw 抽取能力（原始流程不变）。

**S0.6 产出**：`materials/13-competitors/<vendor>/<vendor>-unified-capability-map.md`

包含 4 部分：

1. **模块树**：竞品自有的菜单结构（不是 MI 的），画完整模块边界
2. **跨来源合并表**：同一能力在 PPT / 手册 / 数据字典中的描述合并为一条，标注权威来源
3. **术语词典**：竞品内部同义词别名表（如"商户流程 = 进场管理 = 移交登记"）
4. **实体关系图**：核心实体跨模块引用关系

**S0.6 产物层次标注**：每条能力标注 DM（数据模型）/ BL（业务逻辑）/ OP（操作），并标注权威来源文件。

**S0.6 → S1 的关系**：S1.1 能力抽取以 `unified-capability-map.md` 为唯一输入，不再直接引用各逻辑文件。S1.2 术语归一复用 S0.6 的术语词典 + ontology。

**验证案例**：海鼎（80+ md，7 逻辑文件，4 种来源类型），S0.6 将 97 项散能力合并为 111 项统一能力，17 组术语归一，解决了合同管理在 7 个文件中重复描述的问题。

### S1/S5 能力分析阶段（从 materials 抽取 → 分析结论）

```
S1.1: 能力抽取（从 materials/raw 统一 schema 合并）→ capability-map.json
      ↓ 引用 materials/13-competitors/<vendor>/04-产品功能/ + raw/ page-fields
S1.2: 术语归一（对齐商管域知识 + ontology）
      ↓
S1.3: 蓝联现状映射（读 product-prd-generator 的功能清单）
      ↓
S1.4: 加权对比矩阵 + 改进建议分级
      ↓ ability-comparison-matrix.json + improvement-recommendations.md
S1.5: 证据台账 + 待确认项
      ↓ evidence-ledger.json（引用 materials/raw 路径，不复制原文）+ review/pending-items.md
S1.6: 交互确认与交付
```

**S1 阶段产物全部写入 canonical `$ANALYSIS_ROOT`（按 target_product 解析，见「产品代号与竞品证据隔离」）**，不回写 materials（避免分析结论污染素材库）。

### S0.1 输入解析

从用户描述中提取：

| 参数 | 说明 | 示例 |
|---|---|---|
| 竞品公司 | 用于目录命名与 competitor_company | 旗茂 / 海鼎 / 明源（kebab: qimao / haiding / mingyuan）|
| 竞品产品（可选）| 竞品公司的具体产品，未知即 unknown | 海鼎 CRE / 海鼎 CRM 产品 / 猫酷会员（unknown 时只存公司级线索）|
| 资料来源 | manual 路径 / demo URL / 授权安装包路径 / 任意组合 | `incoming/competitor-qimao/manuals/` + `http://oa.1qmall.cn/SMallTest/` + `incoming/competitor-qimao/packages/qimao-3.2.zip` |
| demo 凭据（如有）| 用户名/密码 | llkj / llkj123（只进 .auth.json 或会话临时使用；采集归档按 material-importer 契约）|
| 安装包授权来源（如有）| 竞品方提供 / 客户合同范围交付 / 公开渠道 | 客户交付实施件，EULA 已核对 |
| 目标公司 + 对照产品（S1 阶段用）| 被分析产品属于哪家公司哪个产品（company.yaml products 归一）| lanlnk + LnkCRE（lnkcre）/ lanlnk + CRM（lnkcrm）/ gdcreia + cre-association-platform；未指定 → 无目标产品模式 |
| 客户业态（可选）| 辅助理解能力语义 | 购物中心 / 写字楼 / 产业园区 |

判定模式：

- 只提供路径 → `manual-only`
- 只提供 URL → `demo-only`
- 只提供授权安装包 → `package-only`
- 两者及以上 → 对应组合模式（默认做来源间交叉核对，按独立性与版本一致性规则，不自动互证升级）

输出 `materials/13-competitors/<vendor>/source-inventory.md`：每份资料记录 `来源 / 采集日期 / 证据强度 / 转换状态 / 缺口`。

### 无目标产品模式（target_company / target_product = unknown）

用户未指定对照产品、或上下文无法解析目标产品时，本 skill 退化为**纯竞品情报模式**，仍可完整执行 S0 采集与能力抽取。

允许输出：

- 竞品公司/竞品产品资料索引（含 `competitor_product: unknown` 的公司级待确认线索）
- 竞品能力清单（capability-map，`status_vs_lanlnk` 全部置空/不输出）
- 证据台账（evidence-ledger）
- 版本、角色、权限和采集限制
- 待验证问题（pending-items）
- 可借鉴设计观察（不绑定目标产品优先级）

禁止输出：

- 相对我方产品的 existing / partial / missing（无目标产品基线，状态 `target-context-missing` / `baseline-unavailable`）
- 目标公司产品差距
- PRD 需求
- 目标产品版本规划
- 目标公司改进优先级（P0/P1/P2/P3 改进建议分级依赖目标产品功能清单与权重，无目标产品时只输出未分级的观察）

### S0.2 原始证据入库（incoming 层）

**manual 模式**：将用户提供的原始文件复制到 `incoming/competitor-<vendor>/manuals/`（或 proposals/）。

**demo 模式**：抓取运行时证据到 `incoming/competitor-<vendor>/runtime-snapshots/`：
- 登录页 HTML、主框架 HTML、关键 JS 文件
- 登录响应（**必须脱敏**：移除密码、加密密钥 EncryptionKey、权限原文 RoleFunctionality，只保留元数据）
- 导航接口响应（LoadNav / 菜单结构 JSON）
- 各页面 HTML 快照

**凭据安全红线**：用户名和密码只用于授权采集，**不写入 incoming/raw/materials 任何文件**。登录响应脱敏后只保留 `result / msg / MainPage / login_meta(不含密钥) / role_functionality_count`。

### S0.3 转换产物入库（raw 层）

**manual 模式**——复用 `material-importer` 的 markitdown + 图片提取 + OCR：

```bash
cd /opt/code/skill/skills/business/material-importer
uv run scripts/extract_images.py "<incoming/competitor-<vendor>/manuals/>"
markitdown "<原始文件>" -o "<raw 目录>/<6类>/<同名>.md"
```

转换规则与 material-importer 一致：PPTX/DOCX/XLSX/PDF → markdown，图片提取到 `raw/<6类>/<filename>_media/`，空章节清理。按 6 类分类归档到 `raw/<目标产品业务域项目根>/02-competitors/<competitor_company>/<01~06>/`（lnkcre = `raw/prd-商管系统/02-competitors/…`）。

**OCR**：图片型资料（扫描手册、PPT 截图）用 DeepSeek-OCR-2，复用 material-importer 的 `scripts/ocr_extract.py`。

**demo 模式**——从 incoming 层的 HTML 快照提取结构化字段：
- 正则解析 layui table cols 的 title / 表单 label / placeholder → 页面字段清单
- 从登录响应的 RoleFunctionality 权限矩阵提取按钮清单（比 HTML toolbar 模板解析更完整）
- 产物：`raw/<项目根>/02-competitors/<competitor_company>/04-产品功能/page-fields/page-fields-*.json` + `05-实施与服务/demo-runtime/capture-manifest.json`

### S0.4 权威精华入库（materials 层）

从 raw 层提炼可复用精华到 `materials/13-competitors/<vendor>/`：

| 文件 | 来源 | 内容 |
|---|---|---|
| `README.md` | 新建 | 素材库入口（资料状态+目录结构+关键发现+三层归属）|
| `source-inventory.md` | S0.1 产出 | 资料盘点 |
| `demo-page-inventory.md` | 从 page-fields JSON 提炼 | demo 页面/菜单/字段/按钮/截图清单（人类可读总览）|
| `04-产品功能/包结构盘点摘要.md` | 从 package-analysis 提炼 | 宽盘点摘要（模块/载体/第三方标记/锚点，structure 层）|
| `04-产品功能/定点代码分析.md` | 从窄深读取证记录提炼 | 定点代码分析结论（implementation 层；usage_scope=internal-product-research；不含大量反编译代码全文）|
| `04-产品功能/能力清单.md` | 从 page-fields JSON 提炼 | 竞品能力结构化清单（按模块分组）|
| `05-实施与服务/截图索引.md` | 从 capture-manifest 提炼 | 截图清单 + 脱敏规则 |
| `imgs/*.png` | demo 截图 | 脱敏截图（百度盘，gitignored）|

**manual 精华**：从 raw 的 markitdown md 中提炼业务逻辑要点，写入对应分类子目录（如 `05-实施与服务/操作手册摘要.md`）。

> **materials 层是 Git 跟踪的权威精华**，其他 skill（product-prd-generator / strategy-brief-generator / company-intro-generator）从这里读取竞品素材。raw 和 incoming 是百度盘（gitignored）。

### S0.2/S0.3 Demo 运行时探测（demo 模式，入 incoming + raw 层）

**复用 `doc-generator` 的运行时探测与截图规范**。详细页面抽取策略见 `references/page-extraction-strategy.md`。

**demo 与静态分析分工**（有安装包分析并存时强制执行，详见 `references/static-analysis-and-reverse-engineering.md`）：

- 静态分析产出候选模块、实体、规则和**待验证问题**；demo 核对实际菜单、关键页面字段、联动、流程与报表结构。
- 包内菜单与 demo 可见菜单**分别记录并对照**（menu-parity），不假定任何一边天然完整。
- 优先复用既有取证，只补真正的缺口；demo 默认只读，不默认执行新增/提交/审批/删除等写操作。
- 代码观察与运行行为交叉核对；无法复现时保留静态限定（`verification_status=static-only`），不自动判功能不存在。
- demo 观察窗口紧时优先保全授权范围内的只读观察，但不得提前标 cross-checked。
- 安装包版本与 demo 环境版本未确认一致时分别记录，不拼接、不互证升级。

**运行时快照复用原则（快照一次，离线消费）**：授权 demo 登录一次 → 定点只读探测 → 保存脱敏快照证据包（`raw/.../runtime-snapshots/<batch>/`）→ 清理会话凭据 → 后续 S0.6/S1 与复核**优先离线消费快照**，不默认重新登录；仅证据缺口、来源冲突或需最新状态时重登（并在 pending-items 登记）。快照是**脱敏运行时证据包**，不是可交互 demo 的替代，"保存 HTML"≠万能离线恢复。**采集与归档契约（标准流程/manifest 上下文字段/哈希/脱敏门禁）归 material-importer**（唯一权威源：`skills/business/material-importer/references/material-classification.md` §6）；分析侧消费约定与失败模式见本 skill `references/runtime-snapshot-protocol.md`。

**S0.2/S0.3 demo 探测执行顺序**：

1. **凭据写入** `.auth.json`（mode 0600，gitignored），首次询问用户，二次复用。**密码不写入任何其他文件**。
2. **加载 playwright skill**：`skill(name="playwright")`
3. **半自动登录**（如登录页有验证码）：Playwright 启动浏览器 + 填账号密码 + **暂停让用户人工识别验证码** + 检测登录成功
4. **菜单加载机制探测**：读 `<a>` 标签的 onclick handler，判定是 accordion / CreateLeftNav 替换式 / 异步加载 / SPA 路由切换（4 种机制详见 page-extraction-strategy.md）
5. **菜单结构收集**：按机制选脚本，循环点击顶级菜单 + sleep + 读 divSide 容器，拿到全部二级菜单文本
6. **二级菜单 URL 提取**：从 `<a onclick>` 用正则 `/addTab\(['"]([^'"]+)/` 拿到每个页面的 URL
7. **页面字段抽取**（三档降级）：
   - **模式 A（同源 fetch + 正则）**：默认起点，一次 evaluate 批量抓 10-20 页，每页 50ms。HTML 含字段名/按钮文本的 layui/服务器渲染站点最有效
   - **模式 B（addTab + iframe.contentDocument）**：模式 A 失败（fields=[] 或全是噪音）时升级，每页 3-5s。⚠️ **禁止在 iframe 内调用 element.click()**——会触发跳转导致 page URL 重置为 about:blank，会话失效
   - **模式 C（Playwright snapshot）**：兜底，每页 5-10s，仅用于 P0 必补的重点页面
8. **流程推断**：从按钮组合识别 CRUD/查询/导出/审批等典型流程
9. **截图**：每模块选 1-3 张关键页面（首页 + 重点表单/报表），脱敏后存到 `materials/13-competitors/<vendor>/imgs/`
10. **locator 规范**：只用 text/role/placeholder/label，禁用 CSS/XPath（与 doc-generator 一致）
11. **单页失败容忍**：一个页面 timeout 或 fetch 失败不阻塞整体，记入 capture-manifest
12. **权限标记**：demo 账号无法访问的页面标 `accessible: false` + `requires_role`，**不判定为竞品没有此功能**
13. **按钮清单交叉验证**：从登录响应的 RoleFunctionality 权限矩阵提取每个页面的按钮列表，比 HTML toolbar 模板解析更完整
14. **原始证据入 incoming**：HTML 快照/登录响应(脱敏)/导航响应 → `incoming/competitor-<vendor>/runtime-snapshots/`；同时按 `references/runtime-snapshot-protocol.md` 与 material-importer 归档契约保存快照证据包（manifest.json + pages/<page-id>/{page.html, screenshot.png, accessibility.json, observation.md}）→ `raw/<项目根>/02-competitors/<competitor_company>/runtime-snapshots/<batch>/`
15. **转换产物入 raw**：page-fields JSON + capture-manifest → `raw/<项目根>/02-competitors/<competitor_company>/04-产品功能/page-fields/` + `05-实施与服务/demo-runtime/`
16. **会话清理与离线复用**：登出并清理会话材料（Cookie/Token/storage/profile 不落盘）；后续分析优先离线消费快照，重登仅限缺口/冲突/最新状态（见 `references/runtime-snapshot-protocol.md`）

**关键约束**：

- 不绕过任何权限控制
- 不做漏洞测试或压力测试
- 截图中的客户名/手机号/金额必须脱敏后再写入证据
- 探测时间精确到分钟，记录账号角色（如"普通商户账号"/"管理员账号"）
- **预算控制**：模式 A/B/C 性能差 100 倍以上，永远从 A 开始；80 页全用 A 仅 4s，全用 C 需 7-13 分钟

### S1.1 能力抽取（从 materials/raw 合并）

**若 S0.6 已触发**：以 `<vendor>-unified-capability-map.md` 为唯一输入（已完成跨来源合并、术语归一、层次标注），S1.1 转为"格式转换"——将统一能力模型转换为 capability-map.json schema。

**若 S0.6 未触发**（小竞品）：从文档（S0.3 raw 层）和运行时（S0.2/S0.3 page-fields）直接合并抽取能力。

从文档（S0.3 raw 层）和运行时（S0.2/S0.3 page-fields）合并抽取能力，统一 schema（详见 `references/capability-schema.md`）：

```json
{
  "target_company": "lanlnk",
  "target_product": "lnkcre",
  "competitor_company": "qimao",
  "competitor_product": "旗茂 BS 商管系统",
  "vendor": "qimao",
  "product": "旗茂 BS 商管系统",
  "module": "合同管理",
  "capability_name": "新合同申请",
  "original_term": "新合同申请单",
  "standard_term": "lease-contract-management",
  "capability_type": "功能",
  "scenario": "招商定稿后发起合同审批",
  "role": ["招商经理", "法务"],
  "workflow": ["选铺位", "录条款", "上传附件", "提交审批"],
  "fields": ["铺位号", "租期", "租金", "免租期", "审批人"],
  "permissions": ["招商经理可建", "法务可审"],
  "reports": [],
  "integrations": [],
  "data_structures": [],
  "evidence": [
    {
      "source_type": "manual",
      "evidence_kind": "document",
      "source_ref": "materials/13-competitors/qimao/05-实施与服务/合同模块操作手册.pdf §3.2 p.45",
      "screenshot": null,
      "url": null,
      "probed_at": null,
      "account_role": null
    },
    {
      "source_type": "demo-runtime",
      "evidence_kind": "runtime",
      "source_ref": "合同管理 → 新合同申请 页面",
      "screenshot": "imgs/合同管理_3_新合同申请表单.png",
      "url": "http://oa.1qmall.cn/SMallTest/contract/new",
      "probed_at": "2026-07-06T11:30:00+08:00",
      "account_role": "管理员"
    },
    {
      "source_type": "package-static",
      "evidence_kind": "structure",
      "source_ref": "incoming/competitor-qimao/packages/qimao-3.2.zip → sql/contract_init.sql",
      "source_version": "3.2",
      "source_sha256": "<package-archive-sha256>",
      "artifact_locator": { "archive": "qimao-3.2.zip", "inner_path": "sql/contract_init.sql", "table": "T_CONTRACT_FREE_PERIOD", "anchor": "约束名/语句位置" },
      "verification_status": "static-only",
      "screenshot": null,
      "url": null,
      "probed_at": null,
      "account_role": null
    }
  ],
  "confidence": "high",
  "status_vs_lanlnk": "partial",
  "quality_assessment": "Competitive",
  "notes": "旗茂的免租期支持分段，蓝联目前只支持整段"
}
```

**capability_type 取值**：`功能 | 流程 | 字段 | 权限 | 数据结构 | 报表 | 集成 | AI/BI`

**上下文字段与多对多注意**（完整定义见 capability-schema.md 与 material-classification.md）：

- `vendor` / `product` 是 legacy 字段：`vendor` = competitor_company（竞品公司）、`product` = competitor_product（竞品产品），兼容保留，不得再当合并概念使用。
- `module` 取**竞品产品语境下的模块**（竞品自己的菜单/模块名），不是目标产品模块；目标产品对齐发生在 `standard_term` 映射（S1.2）。
- `implementation_status` 只描述**竞品实现观察**，不等于目标产品状态（目标产品状态是 `status_vs_lanlnk`，且仅在有目标产品基线时输出）。
- `evidence_state=not_scanned` 或 `inaccessible` 不得转成竞品没有能力。
- 只看到一个竞品产品，不能推断整个竞品公司产品线；同一竞品公司的不同产品不能合并为一个能力清单。
- 不同目标产品（lnkcre / lnkcrm / …）必须分别生成映射和比较矩阵，两条映射不自动共享差距、优先级或 PRD 结论。

**quality_assessment 取值**（实现质量，不是有没有）：

| 取值 | 含义 |
|---|---|
| `Leading` | 业界最佳实现，是购买理由 |
| `Competitive` | 满足买家预期，不是差异化 |
| `Behind` | 功能存在但有明显短板 |
| `Missing` | 未观察到（不等于竞品没有，可能是权限/版本未覆盖）|

**confidence 取值**：

| 取值 | 判定 |
|---|---|
| `high` | 手册 + 运行时一致，或多份独立资料互证 |
| `medium` | 单一来源（仅手册 或 仅运行时）|
| `low` | 仅销售材料，或运行时无法复现，或资料日期不明 |

**status_vs_lanlnk 取值**：

| 取值 | 含义 |
|---|---|
| `existing` | 蓝联已有且证据充分 |
| `partial` | 蓝联有但不完整 |
| `missing` | 蓝联未见实现 |
| `better-than-lanlnk` | 竞品实现质量优于蓝联（重点借鉴对象）|
| `unknown` | 蓝联现状无法判断（进 review）|

### S1.2 术语归一

把竞品的原始术语映射到蓝联标准功能名。入口路径来自 resolver 的 ontology authority
（lnkcre 命中时的优先序）：

- resolver `ontology_entry`（LnkCRE 域知识入口：优先 `30-products/lnkcre/ontology/domain-knowledge.md` → `ontology/README.md` → `INDEX.md`；商管域术语别名表）
- `$LANLNK_BASE/config/ontology/business-ontology.yaml`（8 模块 482 术语；lnkcre 的注册入口本体）
- `product-prd-generator/references/term-aliases.yaml`

ontology authority 为 not-applicable（lnkwebsite）/ unresolved（lnkgateway）时：不回落
商管 ontology，未映射术语全部进 review 并在报告标注该状态。

找不到映射的术语进 `review/pending-items.md`，不强行归一。

### S1.3 蓝联现状映射

「蓝联现状」是历史命名：`status_vs_lanlnk` 的语义 = 相对 **target_company + target_product** 的现状，不假定蓝联/lanlnk。读**目标产品**的功能清单（路径来自 resolver 的 prd authority；下表为 lnkcre/CRM/AI 命中时的当前值）：

| 对照产品 | 功能清单路径（当前值） |
|---|---|
| LnkCRE / MI / MI-CRE / 商管系统（canonical id `lnkcre`） | `$LANLNK_BASE/30-products/lnkcre/prd/baseline/feature-baseline.yaml` |
| CRM / 会员系统 | `$LANLNK_BASE/materials/03-products/CRM会员系统功能清单.md` |
| AI Skills | `$LANLNK_BASE/materials/11-cre-ai-skills/02_机会与产品/岗位 AI Skills 增强性与摩擦消除分析矩阵.md` |

逐条把竞品能力映射到蓝联功能清单的 `existing/partial/missing`，填 `status_vs_lanlnk`。

**lnkcrm scope 基线输入（O5-Q4，2026-10-04 owner include）**：对照产品为 lnkcrm 时，
status_vs_lanlnk 的判定输入额外纳入 lnkcrm OpenSpec scope 集
（`/opt/code/lnkcrm/openspec/specs/`，实测非空、含 member-*/coupon-*/points-*/merchant-*/
platform-*/tenancy 等 scope 族；锚定 scope 集合不钉数量，以实测 `ls` 为准）：竞品能力
命中 scope → 蓝联基线层已有该域，可判 existing/partial 并引用 scope 名；scope 未命中且
功能清单无 existing 证据 → 维持 unknown 进 review。scope 基线已纳入；实现级评估（deep
读码）O5-Q5 已解锁（2026-10-04；解锁集 = 最小验证集三 skill，本 skill 不在集内）。

功能清单不存在时提示：

```
未找到 <产品> 的功能清单。请先运行 product-prd-generator 生成，或提供功能清单路径。
本 skill 在缺功能清单时会退化为只输出竞品能力清单，不做蓝联现状映射（状态 baseline-unavailable，
不因缺基线回退到其他产品的功能清单或商管 ontology）。
```

### S1.4 加权对比矩阵 + 改进建议

详见 `references/comparison-matrix.md`。核心：

**权重来自客户/买家重要性**，不是内部拍脑袋。**权重来源降级路径**（按优先级，前一个不可用时降级到下一个）：

1. **用户在 P0 显式提供**——最高优先级
2. **`requirement-evaluator` 的客户需求汇总**（频率高的能力维度加权）——最理想来源
3. **`$LANLNK_BASE/materials/10-methodology/methodology/15-商业地产岗位病药矩阵.md`**（多岗位共同痛点加权）——长期参考
4. **产品功能清单的 missing/partial 项分布**（canonical-first：`$COMPANY_BASE/30-products/<产品>/prd/功能清单.md`，回退 `$COMPANY_BASE/out/prd/<项目>/output/功能清单.md` 生成区；$LANLNK_BASE 为兼容别名）——反向推断客户痛点（missing 多的维度 = 蓝联弱项 = 应加权）
5. **默认均匀分布**——仅当以上都缺失时，且必须在 `ability-comparison-matrix.json` 的 `weight_source` 标注 `"unweighted-fallback"`，并在 review/pending-items.md 提示"权重未校准"

**降级规则**：每降一级，结果报告的"管理层摘要"必须显式标注权重来源和置信度。**禁止**把降级路径 4-5 的结果当作"客户真实优先级"陈述。

**改进建议四类**：

| 建议 | 触发条件 | 优先级 |
|---|---|---|
| `补齐` | 蓝联 missing 且客户会关心 | P0/P1 |
| `增强` | 蓝联 partial 或竞品 Leading 而蓝联 Behind | P1/P2 |
| `借鉴` | 竞品设计好但不一定立刻做 | P2/P3 |
| `观察` | 证据弱、账号权限不足、或仅销售宣传 | 不进路线图 |

输出 `ability-comparison-matrix.md`（人类可读）+ `lanlnk-product-improvement-recommendations.md`（主交付件）。

### S1.5 证据台账 + 待确认项

详见 `references/evidence-ledger.md`。每条证据记录：

```text
- ID: EV-001
- 能力ID: CAP-合同管理-新合同申请
- 声明: 旗茂支持免租期分段（前 3 个月全免，后续 3 个月半免）
- 类型: 证据
- 来源: materials/13-competitors/qimao/05-实施与服务/合同模块操作手册.pdf §3.2 p.45 + 运行时截图 imgs/合同管理_3_新合同申请表单.png
- 探测时间: 2026-07-06T11:30:00+08:00（运行时）/ 2024-08（手册版本）
- 置信度: high（手册 + 运行时一致）
- 账号权限: 管理员
```

`review/pending-items.md` 记录：

- 术语映射不清
- demo 账号权限不足导致的能力盲区
- 手册版本日期过旧（>2 年）
- 资料类型单一（只有销售策略，无产品手册）
- 竞品能力与蓝联冲突无法判定

### S1.6 交互确认与交付

1. 展示能力统计：发现 N 项能力，按类型/置信度/蓝联现状分布
2. 展示改进建议统计：补齐 X 项 / 增强 Y 项 / 借鉴 Z 项 / 观察 W 项
3. 展示证据覆盖度：high X% / medium Y% / low Z%
4. 列出 `review/pending-items.md` 中需用户确认的关键问题
5. 提示后续动作：
   - 改进建议交给 `product-prd-generator` 落地 PRD
   - 能力矩阵作为 `strategy-brief-generator` 的竞品证据
   - 待确认项可与竞品方/销售/客户复核

## 使用示例

### 示例 1：manual + demo（旗茂）

> 用户："分析旗茂 BS 商管系统，手册在 materials/13-competitors/qimao/，demo 账号 llkj/llkj123，URL http://oa.1qmall.cn/SMallTest/Login.html，对比 LnkCRE"

```
Agent:
  [S0.1] 模式: manual-plus-demo | 竞品: qimao | 对照产品: MI（S1阶段用）
       资料盘点: 12 份手册（操作手册 5 + 功能手册 4 + 数据字典 1 + 蓝图 2）
       demo: http://oa.1qmall.cn/SMallTest/ | 账号角色待探测

  [S0.2] 原始证据入库 → incoming/competitor-qimao/
       ├── manuals/（12份原始文件）
       └── runtime-snapshots/（HTML快照 + 登录响应(脱敏) + 导航响应）

  [S0.3] 转换产物入库 → raw/prd-商管系统/02-competitors/qimao/<6类>/
       ├── 12 份手册 markitdown 转 md + 138 张提取图片
       └── demo: page-fields JSON + capture-manifest

  [S0.4] 权威精华入库 → materials/13-competitors/qimao/
       ├── README.md + source-inventory.md + demo-page-inventory.md
       ├── 04-产品功能/能力清单.md
       ├── 05-实施与服务/截图索引.md + 操作手册摘要
       └── imgs/（47张脱敏截图）

  --- 用户确认素材完整性后，进入 S1 能力分析 ---

  [S1.1] 抽取能力 86 项（功能 52 + 流程 18 + 字段 12 + 权限 4）
  [S1.2] 术语归一: 79 项匹配 ontology，7 项进 review
  [S1.3] 蓝联现状映射: existing 41 / partial 23 / missing 18 / better-than-lanlnk 4
  [S1.4] 加权矩阵 → 改进建议: 补齐 12 / 增强 19 / 借鉴 8 / 观察 47
  [S1.5] 证据台账 142 条（引用 materials/raw 路径）| high 68% / medium 24% / low 8%
         review: 7 项术语未映射 + 2 项 demo 权限未知 + 3 项手册版本过旧

  [S1.6] 交付: evidence/competitors/qimao/（canonical；历史 run 交付于 competitor-analysis/qimao/，原位保留）
       主交付件: lanlnk-product-improvement-recommendations.md
       后续: 改进建议交给 product-prd-generator 落地 PRD
```

### 示例 2：demo-only

> 用户："用这个 demo 账号探测一下 XX 竞品，URL xxx，账号 yyy/zzz"

```
Agent:
  [S0.1] 模式: demo-only | 竞品: xx | 警告: 无手册佐证，能力清单置信度上限 medium，建议补充手册

  [S0.2] 原始证据入库 → incoming/competitor-xx/runtime-snapshots/
  [S0.3] 转换产物入库 → raw/<项目根>/02-competitors/xx/04-产品功能/page-fields/
  [S0.4] 权威精华入库 → materials/13-competitors/xx/{README, source-inventory, demo-page-inventory, 04-产品功能/能力清单}

  --- 用户确认后，进入 S1 能力分析（仅基于运行时可见部分）---

  [S1.1] 抽取能力（仅运行时可见部分）
  [S1.3] 蓝联现状映射（仅对运行时可见能力）
  [S1.4] 改进建议（标注"仅基于运行时探测，建议补充手册复核"）
  [S1.6] 交付 + 提示: manual 模式补完后可重跑 manual-plus-demo 提升置信度
```

### 示例 3：明确拒绝越界

> 用户："顺便帮我做一份竞品对比 PPT 给客户看"

```
Agent:
  我只做内部能力分析和产品改进建议。
  客户面向的竞品对比 PPT 请交给 company-intro-generator（模式B 供应商入围方案）。
  我的能力矩阵可作为那份方案的内部证据，但不直接生成客户材料。
```

## 配置读取

```bash
export LANLNK_BASE=/opt/code/docs/lanlnk
```

| 变量 | 路径 | 说明 |
|---|---|---|
| `$MATERIALS_DIR` | `$LANLNK_BASE/materials` | 素材库根 |
| `$COMPETITORS_DIR` | `$MATERIALS_DIR/13-competitors` | 竞品库（6 类分类）|
| `$INCOMING_VENDOR_DIR` | `$LANLNK_BASE/incoming/competitor-<vendor>/` | **S0 原始证据入口**（百度盘）|
| `$RAW_VENDOR_DIR` | `$LANLNK_BASE/raw/<目标产品业务域项目根>/02-competitors/<competitor_company>/`（lnkcre 当前值 = `raw/prd-商管系统/02-competitors/<vendor>/`，历史档原位消费） | **S0 转换产物**（gitignored，百度盘）|
| `$MATERIALS_VENDOR_DIR` | `$COMPETITORS_DIR/<vendor>/` | **S0 权威精华**（进 Git）|
| `$PRD_DIR` | `<target_product docs_root>`（lnkcre 当前值 = `$LANLNK_BASE/30-products/lnkcre`；= resolver context 的 `layers.docs_root`） | 目标产品 canonical 产品根 |
| `$ANALYSIS_ROOT` | `<target_product docs_root>/evidence/competitors/<competitor_company>/<competitor_product>/`（docs_root 下推导；lnkcre 示例 = `$LANLNK_BASE/30-products/lnkcre/evidence/competitors/haiding/海鼎 CRE/`；历史 `<vendor>/` 一级路径原位消费） | **S1 能力分析输出根**（不含原始素材）|
| `$USERGUIDE_BASE` | `$LANLNK_BASE/materials/03-products/user-guides` | doc-generator 的输出根（如需生成竞品操作手册）|

## 已知限制

- **demo 账号权限决定可见性**：管理员账号能看到的能力 ≠ 普通账号能看到的能力。分析报告必须标注账号角色，"未观察到"≠"竞品没有"。
- **手册版本可能过旧**：手册日期 >2 年时必须提示，能力清单标注"基于 YYYY 版手册"。
- **销售策略类材料不能当产品事实**：`01-销售策略` 和 `02-方案汇报` 只能作弱证据，置信度上限 low。
- **截图脱敏可能丢信息**：客户名/手机号/金额打码后，部分字段证据强度下降。
- **术语归一依赖 ontology 完整度**：当前 ontology 572+ 术语，覆盖率约 19%，未映射术语会进 review。
- **不做定量市场预测**：不评估竞品市场份额、收入、客户数等需第三方调研机构的指标。
- **不评估竞品技术栈性能**：不测响应时间、并发、可用性等技术指标（属运维范畴）。
- **Playwright 依赖**：demo 模式需要 playwright skill 可用 + 目标站点可访问。不可用时退化为 manual-only。
- **不直接生成 PRD/方案/报价**：改进建议是 Markdown，落地交给 product-prd-generator；客户方案交给 company-intro-generator。
- **JS 渲染页面静态解析可能失败**：纯 SPA（Vue/React）的字段在运行时才渲染，模式 A（同源 fetch + 正则）拿不到。必须升级到模式 B（addTab + iframe.contentDocument）或模式 C（Playwright snapshot）。详见 `references/page-extraction-strategy.md`。
- **菜单加载机制差异大**：不同竞品站的菜单加载机制不同（accordion / CreateLeftNav 替换式 / 异步加载 / SPA 路由），必须先探测 onclick handler 才能选择正确的菜单收集脚本，不能假设所有站点都是 accordion。
- **iframe 内 evaluate 高风险**：在 iframe.contentDocument 里调用 element.click() 可能触发跳转或打开新窗口，导致整个 Playwright page 的 URL 被重置为 about:blank，会话失效。**iframe 内只读 DOM，交互操作放回主 document 上下文**。
- **权重来源降级可能误导**：当 requirement-evaluator 输入缺失时，权重只能从功能清单 missing 分布推导，这是反向推断不是客户真实优先级。报告必须显式标注权重来源。
- **改进建议的"客户必需"标记依赖外部输入**：本 skill 自己无法判断某项能力是否"客户必需"，必须借助 requirement-evaluator 或用户在 P0 显式提供。无外部输入时，"P0 必补"标记只能基于"购买理由级领先"的主观判断，置信度 medium。
- **lineage 字段首版人工标注**：`derived_from`/`independence`/`applies_to` 不自动识别全部来源关系，靠人工/半自动标注。
- **`independence=unknown` 是合法稳态**：fail closed，不参与互证升级；不填 lineage 字段即按 unknown 解释。
- **text-sparse 页回看纪律（2026-10-30 海鼎试点实证）**：被标记页的业务语义可能与正文标签显著不同（实证：标签"线上商城商品录入"回看实为"商品数量录入单移动端，类型含库存/退还、带审批流"），不回看会错判业务域；无视觉通道的会话可用外部视觉工具辅助回看，但结果必须标注 `extraction_method=vision_assisted`（辅助转写可能有误，原图人工复核优先级更高）；回看修正主张内容，**不改变证据层级上限**（proposal 仍 medium）。回看入口优先 raw 层 `_media` 投影。回看结论的证据边界（OCR 仅检索线索、页级锚点、图片缺失≠证据不存在等）按 `skills/business/material-importer/references/provenance-evidence-boundary.md` 执行，本节只记录操作细节。
- **text-sparse 回看执行细则（2026-10-31 海鼎 73 页收尾实证）**：①每页选图须剔除跨页固定装饰图（同一 media 文件逐页重复出现，如数据逻辑 PPT 的 `_44`），只取真实信息图；②信息由 PPT 动画承载的页（无静态信息图且 OCR 零命中）标 `not_scanned（图形态缺失）`，需人工播放动画记录，不得判「无信息」；③「清单型图可采信 OCR」假设被 4 页抽验推翻（所谓清单页实为操作规则/状态机/域模型图）——sparse 页内容凡需引用一律以 vision 回看为准，OCR 产物仅作页内实体名检索索引。
- **structure / implementation 的认识论上限**：表结构、静态路由、反编译代码只证明"该版本包内存在"，不证明已部署、已启用、实际执行或完整业务功能可用。结论表述必须限定在被分析的 source_version 内。
- **包版本与 demo/手册版本一致性**：未确认一致时三条来源各自记录版本与适用范围，结论不跨版本拼接，互证不升级（`version-mismatch` 进 pending）。
- **反编译投影非原始代码**：行号、变量名是工具投影，可能失真；锚点用类/方法/描述符 + 归档哈希，反编译行号仅作辅助。反编译失败标不可分析（not-analyzable），不判功能缺失。
- **第三方依赖膨胀**：不区分第三方库与业务代码就按 JS/JAR 文件总数推断产品规模必然高估——宽盘点必须先做依赖区分。
- **demo 写操作盲区**：默认只读探测看不到审批流中段、写后联动等行为，相关能力保持"未观察"而非推断没有。
- **运行时快照的证据边界**：快照只证明"某版本/角色/时间/场景看到的行为"，不证明当前仍可访问；离线快照消费标 `snapshot-observed`，不得标记为当前 runtime re-verified。快照失败模式（动态内容未保存/资源缺失/截图与 HTML 不同状态/脱敏失败/版本角色未知/快照过期/与 demo 当前冲突）见 `references/runtime-snapshot-protocol.md`。
- **失败状态（分类与关系层，与 evidence_state 正交）**：`target-context-missing`（目标公司/产品缺失或无法解析——不套默认产品，走无目标产品模式）；`competitor-context-missing`（缺竞品公司/产品——字段 unknown，公司级线索单列）；`baseline-unavailable`（目标产品功能清单/基线缺失——只输出能力清单，不做现状映射）；`entity-conflict`（同名产品/公司不能自动合并，进 pending 人工裁决）；`version-mismatch`（多版本未确认一致——分别记录不拼接）；`runtime-scope-unknown`（demo 角色/权限未知——不得泛化到其他角色）；`same-source-chain`（同一来源链不重复计证，见来源链折叠规则）；`term-context-conflict`（同名术语不能自动证明语义相同——跨产品语境的术语映射存疑进 pending）；`snapshot-stale`（快照过期不得声称当前行为）；`runtime-conflict`（快照与 demo 当前行为冲突——重登复核留痕）；`workspace-context-missing` / `cross-company-context` / `projection-unverified` 归 material-importer 分类层（见 material-classification.md §5），本 skill 消费材料时遇这些状态按其语义降级处理。

## 设计决策

### 三档页面抽取策略（A/B/C 降级）

P2 阶段不直接走 doc-generator 的"运行时探测 + Playwright snapshot"，而是先用低成本的"同源 fetch + 正则解析"批量抓取，失败才升级到 addTab+iframe，最后才用 Playwright snapshot。**理由**：性能差 100 倍以上（A 4s vs C 7-13 分钟），且大部分 layui/服务器渲染站点用模式 A 已能拿到 60% 以上字段。详见 `references/page-extraction-strategy.md`。

**拒绝的替代方案**：直接用 doc-generator 的 Playwright snapshot 模式——对 80+ 页面站点不现实（耗时 + token 爆炸）。

### 权重来源五级降级

权重不是"客户重要性"的客观度量，而是来源置信度的体现。从"用户显式提供"到"默认均匀"共五级，每级降级必须在报告中显式标注。**理由**：避免把"基于功能清单 missing 分布的反向推断"误陈述为"客户真实优先级"。

**拒绝的替代方案**：所有降级都用均匀分布——会让改进建议失去优先级意义，客户无法判断"先做什么"。

### iframe 内禁止 click

在 iframe.contentDocument 里调用 element.click() 会让 Playwright page 失去对主上下文的控制（实测 URL 重置为 about:blank）。**理由**：iframe click 可能触发 `_blank` 跳转或站点导航逻辑，绕过 Playwright 的事件循环。

**正确做法**：iframe 内只 querySelector 读 DOM 文本/属性，交互操作回到主 document 上下文用 Playwright API（browser_click with ref）。

### 半自动登录（验证码场景）

登录页有验证码时，不用 OCR 自动识别（合规违规），改为"Playwright 启动浏览器 + 填账号密码 + 暂停让用户人工识别验证码 + 检测登录成功"。**理由**：合规优先，用户体验损失可接受（只损失 30 秒）。

**拒绝的替代方案**：OCR 自动识别验证码——违反 ToS，可能违法。

### 宽盘点、窄深读（逆向方法论）

对授权安装包的分析采用"宽盘点（全量结构清单 + 第三方依赖区分）→ 问题登记 → 窄深读（最小必要只读反编译）"三层，而不是全量反编译或按需零散查看。**理由**：全量反编译超出最小必要范围（成本、噪声、合规暴露都最大化）；零散查看会退化成"不落库、不留来源"的隐性研究，无法复核。Java/C# 优先只是工具与成本选择，不写成其他语言的永久禁令。

**拒绝的替代方案**：
- 全量反编译入库——超出问题所需的最小必要范围，且大量第三方依赖代码污染结论。
- 按 JS/JAR 文件总数评估产品规模——第三方依赖与运维组件必须先剥离，否则规模必然高估。

## 维护规则

修改本 skill 时：

1. **判断归属**：通用能力分析方法论 → 留在本文件；商管域专属知识 → 写入 `$LANLNK_BASE/30-products/lnkcre/ontology/domain-knowledge.md`
2. **更新本文件**的「已知限制」章节
3. **能力 schema 变更**同步更新 `references/capability-schema.md`
4. **证据规则变更**同步更新 `references/evidence-ledger.md`
5. **合规规则变更**同步更新 `references/safety-and-ethics.md`，并检查与 `doc-generator` 的凭据规范一致
6. **新增竞品**时，在 S0 阶段建立三层目录：`incoming/competitor-<vendor>/`、`raw/prd-商管系统/02-competitors/<vendor>/<6类>/`、`materials/13-competitors/<vendor>/<6类>/`；S1 阶段再建 `30-products/lnkcre/evidence/competitors/<vendor>/`
7. **改对比矩阵权重模型**时，同步 `references/comparison-matrix.md` 并检查与 `requirement-evaluator` 的客户需求优先级口径一致
8. **遇到新菜单加载机制**（如新的 SPA 框架/新的导航模式）时，更新 `references/page-extraction-strategy.md` 的"4 种典型机制"表，并补充实战经验
9. **共享治理契约改版**时（`product-governance/` 下 schema 变更），核对「共享产品治理契约集成」一节及 `references/capability-schema.md`、`references/evidence-ledger.md` 的映射说明是否仍成立；映射语义变更须三处同步
10. **安装包静态分析/逆向操作纪律变更**时，同步 `references/static-analysis-and-reverse-engineering.md`；字段与枚举改动只改 `references/evidence-ledger.md`（唯一权威），本文件与 `references/capability-schema.md` 只保留链接与简例，不复制定义
11. **统一竞品关系上下文字段（workspace/target/competitor 公司与产品、版本、角色等）变更**时，以 `skills/business/material-importer/references/material-classification.md` 为唯一权威源修改，本文件、`references/capability-schema.md`、`references/evidence-ledger.md`、`references/runtime-snapshot-protocol.md` 只同步链接与简例，并检查 product-prd-generator 侧消费规则仍成立

**判断标准**：如果一个分析行为或合规坑"下次的我"读到不一定能立刻理解为什么这么做，就应该记录。
