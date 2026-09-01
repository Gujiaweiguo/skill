---
name: strategy-brief-generator
description: |-
  通用战略简报生成 Skill（多公司）。以四看方法论（看市场/看竞对/看自己/看机会 → 定战略 → 执行计划）
  为通用框架，看市场内含政策与监管环境子项（政策驱动型行业升格为独立分析），整合战略参考资料、
  竞品材料、行业 SOP、市场趋势和公司自身资产（company.yaml products），生成证据型内部战略简报，
  并输出「产品机会清单」反哺公司产品台账（onboard.sh product）。
  触发场景："做战略分析"、"基于模板分析我们公司怎么定位"、"整理一份XX行业战略简报"、
  "分析竞品给出产品路线和差异化建议"、"做一份四看战略分析"、"政策驱动型行业机会分析"、
  "通过战略分析看还有哪些产品机会"。
  当用户提供战略参考资料、竞品材料、行业 SOP，并要求做战略层面的分析判断（不是 PRD、
  不是客户方案、不是投标文件）时，触发此 skill。
  仅面向内部产品/经营决策，不生成 PRD、不生成客户方案、不生成投标文件、不生成报价。
compatibility: >
  纯提示词 skill，无 Python 依赖。
  资料转换复用 material-importer（markitdown + 图片提取）。
  市场趋势资料可通过 web search 补充；政策驱动型行业必须联网检索政府文件。
  多公司契约（company.yaml schema / 变量协议）见 /opt/code/docs/COMPANIES.md。
  后续如需战略汇报 PPT/Word，通过内容包调用 mckinsey-pptx / word-master，不在本 skill
  内嵌入渲染逻辑。

  Quick start:
  ```bash
  export COMPANY_BASE=/opt/code/docs/<company>   # 如 lanlnk / lianyou
  # 兼容变量 LANLNK_BASE 等价；路径下必须有 config/company.yaml
  ```
---

# Strategy Brief Generator — 战略简报 Agent Pipeline（多公司通用引擎）

## DocSpec 质量基线

本 skill 生成的战略简报、机会分析、竞品判断和路线建议必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `DocSpec-通用文档质量规范.md`、`方案与投标文档质量规范.md` 和 `文档验收清单.md`。事实、判断、建议必须分层；假设和资料缺口必须进入 review。

基于 `四看方法论（通用引擎）+ 多源资料整合 + 证据型分析 + Markdown 输出 + 产品机会反哺` 的方案。

## P0 公司确定（多公司路由，必跑第一步）

按优先级确定当前公司，绝不猜默认：

| 顺序 | 判定 | 动作 |
|---|---|---|
| ① | cwd 位于 `/opt/code/docs/<company>/` 下 | 该公司 |
| ② | 用户消息点名公司（如「给 lianyou 做战略分析」） | 该公司 |
| ③ | 均无法判定 | 用 question 询问（列出已发现公司：`ls /opt/code/docs/*/config/company.yaml`） |

```bash
export COMPANY_BASE=/opt/code/docs/<company> COMPANY_ID=<id>
```

**公司叙事加载**：P0 确定公司后，立即检查 `$COMPANY_BASE/config/sales-playbook/strategy-brief.md`；存在则通读全文作为本项目的写作约束（如 lanlnk 的 B/D 路线、岗位病药矩阵、内部汇报视角、交付口径）；不存在则跳过，按通用引擎执行。

**配置读取**（company.yaml 驱动，schema 见 `/opt/code/docs/COMPANIES.md` §2）：

| 变量 | 来源 | 说明 |
|------|------|------|
| `$BRAND` | company.yaml `brand` | 报告主语（如 广州联友 / 蓝联科技） |
| `$STRATEGY_ROOT` | `<COMPANY_BASE>/<strategy.root>/<主题>` | out 平铺根，主题默认 `<domain>战略`（domain 取自 company.yaml），用户可指定 |
| `$INCOMING_DIR` | `<COMPANY_BASE>/incoming/<主题>/` | 全部原始输入 +《资料来源清单》（**无主题级 input/**） |
| `$RAW_WORKDIR` | `<COMPANY_BASE>/raw/<主题>/` | 转换件、OCR、四看工作底稿、PPT 生成脚本等可再生工具 |
| `$MATERIALS_DIR` | `<COMPANY_BASE>/materials` | 可复用结构化素材（含本 skill 直产的分析产物） |
| `$METHODOLOGY_REF` | company.yaml `strategy.methodology_ref` | null=内置四看；否则指向方法论资料目录 |
| `$POLICY_DRIVEN` | company.yaml `industry_profile.policy_driven` | true=政策维度升格（见 P5） |
| `$PRODUCTS` | company.yaml `products[]` | 自身盘点与机会清单的产品台账 |

**四锚点纪律（COMPANIES.md §6）**：输入一律 incoming、中间一律 raw/<主题>/、复用件直产 materials（带 frontmatter）、交付物平铺 `$STRATEGY_ROOT`（零子目录）。**唯一例外**：`evidence-ledger.json` 是 CLM 溯源根，随 git 分发，平铺在 `$STRATEGY_ROOT/` 下。

## 核心定位

这个 skill 是 **PRD 和售前方案之前的战略判断层**。

它回答的是：

- 当前公司在目标行业应该怎么定位？
- 相对竞品，差异化在哪？
- 产品怎么组合、先做什么后做什么？
- AI/数据能力应该嵌入哪些业务场景？
- **还有哪些产品机会值得进入产品台账？**（输出产品机会清单 → 反哺 onboard.sh product）

它不回答：

- 具体功能怎么设计（→ product-prd-generator）
- 客户方案怎么写（→ company-intro-generator）
- 投标文件怎么做（→ bid-doc-master）
- 项目要不要立项（→ project-proposal-generator）

## 与兄弟 Skill 的边界

```
material-importer（资料入库）
        ↓
strategy-brief-generator（战略判断）← 你现在在这里
        ↓ (战略方向确定后)
product-prd-generator（产品 PRD）
        ↓
company-intro-generator（客户方案）/ bid-doc-master（投标）
```

**严格不做的事：**

- 不写字段、接口、页面、数据模型（那是 PRD）
- 不写客户面向的方案叙事（那是 company-intro）
- 不写投标响应、报价、偏离表（那是 bid-doc）
- 不写具体项目立项的 ROI 测算（那是 project-proposal）
- 不直接修改业务系统代码
- 不生成 PPT/Word（MVP 只输出 Markdown；后续如需汇报材料，输出内容包交给 mckinsey-pptx / word-master）

## 方法论：通用四看框架

```
一、看市场（Market）
   ├── 行业趋势与宏观环境
   ├── 客户变化与需求演变
   ├── 技术变化（含 AI/RAG/BI 趋势）
   └── 政策与监管环境（政府行业政策 / 监管趋势 / 合规压力 / 政策机会窗口）
        ★ $POLICY_DRIVEN=true 时升格：独立分析小节 + 专项信号文件（见 P5）

二、看竞对（Competitors）
   ├── 竞品定位与产品矩阵
   ├── 核心能力与特色打法
   ├── 客户打法与生态策略
   ├── 价格/交付/服务模式
   └── AI/数据能力对比

三、看自己（Self）
   ├── 现有产品能力盘点（company.yaml products）
   ├── 客户案例与交付能力
   ├── 技术资产与可复用资源
   └── 组织/资源短板

四、看机会（Opportunity）
   ├── 市场缺口与空白
   ├── 竞品弱点
   ├── 自身优势交叉点
   ├── AI/RAG 新机会窗口
   └── ★ 产品机会清单（输出反哺，见 P8）

五、定战略（Strategy）
   ├── 战略定位
   ├── 产品组合策略
   ├── 目标客户画像
   └── 差异化打法

六、执行计划（Execution）
   ├── 阶段目标与路线图
   ├── 产品动作
   ├── 市场与售前动作
   └── 交付能力建设
```

### 方法论实例化（methodology_ref 机制）

- `$METHODOLOGY_REF = null`（如 lianyou）：P2 跳过方法论归纳，直接使用上方内置四看框架。
- `$METHODOLOGY_REF ≠ null`（如 lanlnk → 明源战略模板资料位）：P2 从该目录归纳实例化框架。
  **双重角色管理**：同一份资料可能既是方法论模板又是竞品证据——归纳框架时它是模板，P3 竞品抽取时它是证据之一，必须严格分开，且「模板是参考框架不是真理」，公司战略判断必须基于自身优势和客户实际。

## 输入与落盘规范（公司级四锚点，无主题流水线）

战略分析不建主题级目录树。输入走公司级 incoming，中间产物进 raw/<主题>/，可复用分析产物直产 materials（带 frontmatter），最终交付平铺 $STRATEGY_ROOT：

```text
<COMPANY_BASE>/
├── incoming/<主题>/                 # 全部原始文件 + 《资料来源清单.md》（指针登记，指向 raw 实际转换件）
├── raw/<主题>/                      # markitdown/OCR 转换件、SOP 映射底稿、PPT 生成脚本（方法论归纳已升格 materials）
├── materials/                       # 可复用产物直产位：
│   ├── 13-competitors/              #   ← P3 竞品能力矩阵（frontmatter）
│   ├── 03-products/政策与市场/       #   ← P5 市场信号 + 政策监管信号（frontmatter）
│   └── 10-methodology/              #   ← P2 方法论归纳产物（frontmatter，仅 methodology_ref 非空时）
└── out/<类型>/<主题>/ = $STRATEGY_ROOT   # 平铺零子目录：总报告、产品机会清单、待确认事项、
                                       # 自身能力盘点、evidence-ledger.json（唯一 json 例外）、pptx
```

> lanlnk 存量主题（如 out/strategy/商业地产信息化战略/）的旧五层树按原样保留可读，不做迁移；新主题一律按本契约。

### 资料放置规则

| 资料类型 | 放在哪里 | 说明 |
|---------|---------|------|
| 方法论模板（$METHODOLOGY_REF 非空） | 其配置的资料目录（多为 `incoming/<主题>/` 或既有 materials 位） | P2 归纳产物入库 materials/10-methodology/ |
| 政策/监管文件、市场报告 | `incoming/<主题>/` | 政策驱动型行业的关键输入 |
| 行业运营 SOP | `incoming/<主题>/` | 真实业务流程证据 |
| 竞品原始资料 | `incoming/prd-<pid>/02-competitors/` 或 `incoming/<主题>/` | 抽取结果由 P3 直产到 materials/13-competitors/ |
| 自身源码资产 | 不复制；`source-ref.md` 记录 code_root 路径，放 `incoming/<主题>/` | 路径取自 company.yaml products[].code_root |
| 自身产品资料 | 引用 `$MATERIALS_DIR/` 已分解资料，在《资料来源清单》登记 | 不建 04-self 目录 |

### 源码类资料处理

产品资产以源码为主的（code_root 非空）：不复制。处理方式：

1. 在《资料来源清单.md》登记源码根路径（来自 company.yaml）与盘点范围
2. 后续由 Agent 读取源码，抽取能力清单写入自身能力盘点（P4）
3. 有 PRD 产物的产品（prd_ready: true）直接复用其 PRD/功能清单作盘点输入

## 处理流程

```
P0: 公司确定 + 叙事加载 + 配置读取
    ↓
P1: 资料转换（复用 material-importer：markitdown + 图片提取）
    ↓ raw/<主题>/（markdown + 图片）
P2: 方法论归纳（$METHODOLOGY_REF 非空时；null 则跳过，用内置四看）
    ↓ materials/10-methodology/（带 frontmatter，可复用资产；仅归纳工作过程稿留 raw）
P3: 竞品能力抽取（按 incoming 实际分类）
    ↓ materials/13-competitors/<名称>.md（带 frontmatter，直产入库）
P4: 自身能力盘点（company.yaml products + materials + PRD）
    ↓ $STRATEGY_ROOT/自身能力盘点.md（平铺交付件）
P5: 市场信号整理（本地资料 + 联网搜索；$POLICY_DRIVEN=true 时政策信号独立成文）
    ↓ materials/03-products/政策与市场/*.md（带 frontmatter，直产入库）
P6: SOP → 业务场景映射（流程清单 + AI问数/RAG 机会）
    ↓ raw/<主题>/SOP场景映射底稿
P7: 四看综合分析 + 证据台账
    ↓ $STRATEGY_ROOT/evidence-ledger.json（唯一 json 例外，随 git 分发）
P8: 战略简报生成 + 产品机会清单
    ↓ $STRATEGY_ROOT/ 平铺（总报告、产品机会清单、待确认事项 等，零子目录）
```

### P1 资料转换

复用 `material-importer` 的 markitdown 能力（该 skill 遵循同一 COMPANY_BASE 协议）：

```bash
# 批量转换 incoming/<主题>/ 下的文档到 raw/<主题>/，保持目录结构一致
cd skills/business/material-importer
uv run scripts/extract_images.py "$INCOMING_DIR"
# markitdown 逐文件转换，输出到 raw/<主题>/ 对应子目录
```

转换规则与 material-importer 一致：PPTX/DOCX/XLSX/PDF → markdown；图片提取到 `raw/…_media/`；空章节清理、base64 噪音清理；保持来源目录层级。同时在 `incoming/<主题>/` 维护《资料来源清单.md》：每个原始文件 ↔ 实际转换件（含合并文件名，如 all-ocr.md）的指针。

### P2 方法论归纳（条件执行）

仅当 `$METHODOLOGY_REF` 非空。归纳 `$METHODOLOGY_REF` 指向的多份资料成**一个统一的方法论框架**，产物分两层：

- **入库层（materials/10-methodology/，带 frontmatter）**：`方法论归纳-<来源>-<日期>.md` —— 统一框架、共同分析维度、来源映射。可复用资产，随 git 分发，后续主题直接复用不必重归纳。
- **过程层（raw/<主题>/）**：归纳工作稿（逐份资料的差异记录、被舍弃的框架版本、冲突标注）。可再生的中间产物。

归纳要点：提取章节结构 → 找共同分析维度 → 合并统一框架 → 标注来源。frontmatter `status` 如实表达归纳完整度（资料只有大纲时用 partial）。

### P3 竞品能力抽取

按 `incoming/` 中竞品原始资料的实际分类分组整理（如 lanlnk 分商管/会员两组；lianyou 可分溯源/监管科技等）。**直产入库** `$MATERIALS_DIR/13-competitors/`，带完整 frontmatter（id/type/name/domain/tags/status/created/source；status 如实表达核验程度）：分类能力矩阵 + 每家竞品结构化主张。若该公司已形成 `13-competitors/<vendor>/<分类>/` 目录体系（如 lanlnk 的明源/海鼎/凯捷等 7 家），矩阵与结构化文件落入对应分组位，不强求根目录平铺。

每个竞品抽取维度：公司/产品定位、目标客户、核心模块、特色能力、AI/数据能力、行业打法、优势、短板、**可借鉴点（当前公司可以学什么）**、**对当前公司威胁**。

### P4 自身能力盘点

按 `$PRODUCTS`（company.yaml products）逐产品盘点，**平铺交付** `$STRATEGY_ROOT/自身能力盘点.md`（属四看正式产物，供总报告链接，不沉 raw）：

| 资产来源 | 判定 | 盘点内容 |
|------|------|---------|
| code_root 非空 | 读源码（source-ref.md 指路） | 已有模块、能力成熟度、技术栈 |
| code_root 空 + materials 有资料 | 引用 `$MATERIALS_DIR/03-products/` 等 | 产品功能、案例、行业覆盖 |
| prd_ready: true | 复用 PRD/功能清单 | 权威能力基线 |

### P5 市场信号整理（含政策升格）

市场资料来自两个来源：**本地资料**（`incoming/<主题>/`）+ **联网搜索**（补充最新趋势）。

**政策驱动型行业（`$POLICY_DRIVEN: true`）必须单独产出** `$MATERIALS_DIR/03-products/政策与市场/政策监管信号.md`（带 frontmatter，直产入库）：

- 本地政策文件逐份摘录（发文字号、发布单位、核心条款、与公司的关联）
- 联网检索补充（政府官网、征求意见稿、行业解读），逐条带 URL
- 提炼：监管趋势、合规压力、**政策机会窗口**（如政策要求 XX 系统化 → 产品机会）
- 每条信号必须标注来源

非政策驱动型（false）：政策并入常规市场信号文件，不独立成文（维度保留、权重降低）。

输出到 `$MATERIALS_DIR/03-products/政策与市场/`：`<行业>市场信号.md` +（政策驱动时）`政策监管信号.md`，均带 frontmatter。

### P6 SOP → 业务场景映射

行业 SOP 是推导 AI问数和 RAG 场景的关键输入。输出到 `raw/<主题>/SOP场景映射底稿.md`：流程清单、角色与岗位、SOP 痛点与系统化机会、SOP 到 AI问数/RAG 场景映射。底稿结论由总报告「看机会」承载。

### P7 四看综合分析 + 证据台账

把前面所有产物综合成四看分析。输出 **`$STRATEGY_ROOT/evidence-ledger.json`**（唯一 json 例外：随 git 分发，保证克隆后所有 CLM 编号可回查）：

```json
{
  "claims": [
    {
      "id": "CLM-001",
      "claim": "<一句话声明>",
      "section": "看市场",
      "source_type": "market_report | policy_document | competitor_material | self_asset | sop | web_search",
      "source_ref": "incoming/<主题>/xxx.pdf §3.2、materials/13-competitors/yyy.md 或 URL",
      "confidence": "high | medium | low",
      "notes": ""
    }
  ]
}
```

### P8 战略简报生成 + 产品机会清单

最终**平铺**输出到 `$STRATEGY_ROOT/`（零子目录）：

```text
战略分析总报告.md          # 完整战略简报（管理层可读）
产品机会清单.md           # ★ 必产出：反哺公司产品台账
待确认事项.md             # 假设验证 / 证据升级 / 缺口跟踪（原 review/pending-items）
自身能力盘点.md           # P4 产物平铺
evidence-ledger.json      # P7 台账（唯一 json 例外）
```

**产品机会清单.md 结构**（反哺闭环的入口）：

```markdown
# 产品机会清单（战略分析产出）
> 操作指引：用户确认某机会后，在 docs 仓库执行
> `scripts/onboard.sh product <company> <pid> --name "<机会名>"` 加入 company.yaml 产品台账。

| # | 机会名 | 证据 ID | 目标客户 | 建议优先级 | 与现有产品关系 |
|---|--------|---------|----------|-----------|---------------|
| 1 | <如：监管检查报告自动生成> | CLM-0xx, CLM-0yy | <目标客群> | P1 | 新产品（与 溯源APP 互补） |
```

每条机会的证据 ID 必须能在 evidence-ledger 中查到（证据纪律同样约束机会清单）；「与现有产品关系」对照 `$PRODUCTS` 台账填写（新/扩展/替代）。

## 战略简报标准结构

```markdown
# <行业>战略简报（$BRAND）

## 1. 管理层摘要
## 2. 方法论说明（内置四看 / 实例化来源、资料覆盖度）
## 3. 看市场
   3.1 <行业>市场趋势
   3.2 客户需求演变
   3.3 AI 与技术趋势
   3.4 政策与监管环境（$POLICY_DRIVEN=true 时为独立小节，false 时并入趋势）
## 4. 看竞对（按公司竞品分组）
## 5. 看自己（按 $PRODUCTS 逐产品）
## 6. 看机会（含产品机会摘要，指向产品机会清单.md）
## 7. 战略定位
## 8. 产品组合策略
## 9. 执行计划
## 10. 风险与待确认问题
## 11. 证据台账
```

## 证据纪律（核心规则）

**每条战略判断必须可追溯。**

### 三类声明标记

| 标记 | 含义 | 要求 |
|------|------|------|
| `【证据】` | 来自资料的事实 | 必须引用具体来源（文件 + 章节/页码，政策文件含发文字号） |
| `【判断】` | 基于证据的推理 | 必须列出依据的证据 ID |
| `【假设】` | 未证实的假设 | 必须标注，并说明如何验证 |

### 禁止的行为

- 禁止无来源的战略断言
- 禁止把竞品宣传话术当事实
- 禁止把方法论模板结论当公司结论
- 禁止"所有企业都在做 AI"这类空话
- 禁止在不看 SOP 的情况下推荐 AI/RAG 场景
- 禁止政策驱动型行业不做政策文件分析就下市场判断

### 证据台账必填字段

每条证据：ID（CLM-XXX）/ 声明 / 类型（证据/判断/假设）/ 来源（文件路径+章节 或 URL）/ 置信度（high/medium/low）/ 用于章节。

## AI问数 / RAG 分析的分层框架

战略分析中涉及 AI 能力时，按以下分层讨论，不要泛化成"加个 AI"：

| AI 能力类型 | 战略价值 | 场景来源 |
|------------|---------|---------|
| **AI问数** | 经营/监管数据的自然语言查询 | SOP 中的管理动作和指标 |
| **AI RAG** | 制度、法规、SOP、操作手册问答 | SOP/政策文档库 |
| **AI 助手** | 面向岗位的业务操作辅助 | SOP 中的高频操作 |
| **AI 决策** | 预警、预测、建议 | SOP 中的管理决策点 |

**MVP 建议**：AI问数和 RAG 优先；AI 决策不过度承诺。

## 公司专属叙事（外置加载）

本 skill 只保留通用引擎。各公司专属写作约束在 P0 加载 `$COMPANY_BASE/config/sales-playbook/strategy-brief.md`（存在时）。

当前已沉淀：

| 公司 | 文件 | 内容 |
|---|---|---|
| lanlnk | `lanlnk/config/sales-playbook/strategy-brief.md` | B/D 客户路线分层、岗位病药矩阵对齐、需求表四类拆分、蓝联整体视角、30/60 天交付口径、可达度表述规则 |

新公司沉淀自己的叙事：在公司库建同名文件即可，零 skill 修改。

## 使用示例

### 示例 1：lianyou 完整战略分析（政策驱动型 + 机会发现）

> 用户："给 lianyou 做战略分析，素材在 incoming/战略分析素材"

```
Agent:
  0. 公司=lianyou（用户点名）；加载 company.yaml（广州联友/policy_driven=true/1 产品/四看内置）
     检查 sales-playbook → 无，用通用引擎
  1. 原始素材在 incoming/战略分析素材；建《资料来源清单》（政策文件、证书、截图 ↔ raw/_extracted/all-ocr.md 指针）
  2. 转换到 raw/<主题>/（PDF 政策件 markitdown + 截图 OCR）
  3. P2 跳过（methodology_ref=null）
  4. P3 竞品抽取（incoming 竞品资料按实际目录；暂无竞品资料则在待确认事项标注缺口）
  5. P4 自身盘点 → $STRATEGY_ROOT/自身能力盘点.md
  6. P5 市场信号 + ★政策监管信号.md 直产 materials（联网检索药监局/广东省 AI 政策补充）
  7. P7 四看 + evidence-ledger.json 平铺（政策文件引用带发文字号）
  8. $STRATEGY_ROOT 平铺：总报告 + 产品机会清单 + 待确认事项
     提示用户确认机会后 onboard.sh product lianyou <pid> 反哺
```

### 示例 2：lanlnk 竞品专项

> 用户："先帮我分析商管竞品，明源海鼎安盛旗酆泽科传这几家"

```
Agent: 公司=lanlnk；加载 sales-playbook；只跑 P1+P3，竞品矩阵直产 materials/13-competitors/商管竞品能力矩阵.md
```

### 示例 3：明确拒绝越界

> 用户："顺便帮我做一份客户方案 PPT"

```
Agent: 我只做战略分析。客户方案请交给 company-intro-generator。
```

## 后续渲染（可选）

| 输出格式 | 处理方式 |
|---------|---------|
| 战略汇报 PPT | 输出 YAML 内容包 → 调用 mckinsey-pptx |
| 战略 Word 报告 | 输出 `.word-content.md` → 调用 word-master |
| RAG 可查的战略知识 | 复用 doc-generator 的 chunks.jsonl 模式 |

**不在本 skill 内嵌入渲染逻辑。** MVP 阶段只输出 Markdown。

## 已知限制

- **方法论归纳质量依赖原始资料完整度**（$METHODOLOGY_REF 模式）：资料只有大纲没有正文时归纳较粗。
- **市场资料需联网搜索补充**；政策驱动型行业的政策信号质量依赖 web search 与政府官网检索。
- **源码类资产盘点较浅**：第一版只做模块级能力盘点，不做字段/接口级。
- **不生成 PPT/Word**：后续通过内容包委托渲染 skill。
- **不做定量市场预测**：不预测市场规模、份额、增长率等需专业调研机构数据的指标。
- **AI 能力建议是定性的**：不评估模型性能、token 成本、延迟等技术指标。
- **竞品资料缺失时**：P3 在待确认事项登记缺口，不虚构竞品能力。

## 维护规则

修改本 skill 时：

1. **判断归属**：通用战略方法论 → 留在本文件；公司专属叙事 → 写入对应公司 `config/sales-playbook/strategy-brief.md`；特定项目域知识 → 写入 `$STRATEGY_ROOT/域知识.md`
2. **更新本文件**的「已知限制」章节
3. **如是诊断流程**，更新 `references/troubleshooting.md`
4. **方法论框架变更**（如四看结构调整），同步更新 `references/four-look-framework.md` 与 COMPANIES.md §7
5. **新增公司叙事**时，在公司库建 sales-playbook 文件并在本文件「公司专属叙事」表登记

**判断标准**：如果一个战略分析行为或坑"下次的我"读到不一定能立刻理解为什么这么做，就应该记录。
