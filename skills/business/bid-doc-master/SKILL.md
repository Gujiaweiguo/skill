---
name: bid-doc-master
description: |-
  投标文件制作 Skill。基于 tender + template + docx/xlsx 方案，解析招标文件要求，
  复用既有投标模板素材，生成或改写商务标、技术标、报价清单、响应表、偏离表、
  资格证明与交付检查清单等投标文件。适合政府采购、企业采购、系统建设、软件服务、
  集成实施、运维服务等正式投标场景。
  触发场景："做投标文件"、"根据招标文件生成投标文件"、"商务标"、"技术标"、
  "报价清单"、"投标模板"、"招标响应"、"投标响应文件"、"偏离表"、"资格审查"、
  "中旅招投标"、"会员系统采购文件"、"帮我用已有模板做标书"。
  当用户提供招标文件、采购文件、投标模板、历史投标文件或报价表，并要求生成/改写/
  检查投标材料时，同样触发此 skill。
compatibility: >
  Requires Python 3.10+ and uv.
  Provides a `pyproject.toml` for deterministic dependency setup.

  Requires `LANLNK_BASE` env var set to the materials directory (used for bid output paths).

  Quick start:
  ```bash
  export LANLNK_BASE=/opt/code/docs/lanlnk
  cd skills/business/bid-doc-master
  uv sync                  # install openpyxl (for XLSX 报价清单)
  ```

  商务标/技术标通过 Word 内容包 → word-master 排版生成。
  报价清单直接使用 openpyxl 生成（xlsx 不在 word-master 处理范围内）。

  Also recommends (system): pandoc, libreoffice for advanced document conversion.
  Degrades gracefully: produce structured Markdown drafts with content packages if generation unavailable.

  Example bid case: see `references/case-example.md`.
---

# Bid Doc Master — 投标文件制作 Agent Pipeline

## DocSpec 质量基线

本 skill 生成的商务标、技术标、述标 PPT、响应矩阵、偏离表、报价清单和交付检查清单必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `方案与投标文档质量规范.md`、`PPT与Word内容包质量规范.md` 和 `文档验收清单.md`。招标要求响应矩阵是交付前置产物，不得跳过。

基于 `招标文件解析 + 模板素材复用 + 响应性校验` 的方案，用户给招标文件和已有投标模板，Agent 负责拆解要求、编制内容、生成文件、检查响应完整性。

## References 索引（按需读，不要全读）

| 文件 | 何时读 |
|---|---|
| `references/troubleshooting.md` | 第一次跑本 skill、踩坑时、修改 SKILL.md 前。必读 |
| `references/case-example.md` | 第一次跑、不确定完整流程时。演示一个投标案例从招标文件到交付的完整路径 |
| `../../word/word-master/reference/word-content-package-spec.md` | 写 `.word-content.md` 内容包时。word-master 的字段规范（注意路径是单数 `reference/`） |

默认示例素材目录：

```text
$BIDDING_DIR/中旅招投标/
├── 招标文件/
│   ├── 会员系统采购文件.docx
│   └── 附件2：会员合同模板.docx
└── 投标文件/
    ├── 商务标（终稿）.docx
    ├── 技术标(终稿).docx
    └── 报价清单（终稿）.xlsx
```

---

## Architecture

```text
用户需求 / 招标文件 / 模板素材
        ↓
P0: 环境检测 + 文件盘点
        ↓
Lead Agent（你 — 合规判断与交付编排）
        │
   ┌────┼────┬────┐
   │    │    │    │
  P1   P2   P3   P4
解析  映射  编制  校验
招标  模板  文件  交付
要求  素材
        ↓
P5: 输出投标包 + 响应检查清单
```

---

## P0: 环境检测与输入分类

### 0.1 环境检测

```text
1. markitdown / pandoc / libreoffice 可用?     → 可抽取 DOCX/PDF 内容
2. openpyxl 可用?                               → 可编辑 XLSX 报价清单
3. pypdf / OCR 可用?                            → 可处理 PDF 或扫描件
4. 现有模板是否可读?                             → 可复用版式、章节、措辞
5. word-master 是否可用?                        → 可生成 DOCX（否则输出内容包待处理）
```

### 0.2 输入类型判断

| 输入类型 | 处理方式 |
|---------|---------|
| **招标文件/采购文件** | 提取项目概况、资格要求、评分办法、响应格式、递交要求 |
| **合同模板/附件** | 提取商务条款、服务边界、付款方式、违约责任、验收要求 |
| **历史商务标模板** | 复用资质证明、公司介绍、授权承诺、项目经验、格式版式 |
| **历史技术标模板** | 复用技术方案结构、实施方法、项目组织、质量保障、运维服务 |
| **历史报价清单** | 复用表结构、计价口径、税率、公式和汇总方式 |
| **用户补充信息** | 合并公司信息、产品参数、团队履历、报价策略、项目差异化内容 |

### 0.3 输出类型

| 输出文件 | 典型内容 | 生成方式 |
|---------|---------|---------|
| **商务标** | 投标函、法定代表人授权、资格证明、商务响应、合同条款响应、业绩、承诺函 | **Word 内容包 → word-master** |
| **技术标** | 需求理解、总体方案、功能响应、实施计划、项目团队、质量保障、培训与运维 | **Word 内容包 → word-master** |
| **述标PPT** | 公司资质、需求理解、方案蓝图、重点响应、实施服务、选择理由 | **YAML 内容包 → proposal-pptx compile.py（mode=tender）** |
| **报价清单** | 分项报价、总价汇总、税率、服务周期、报价说明、可选项/备品备件 | openpyxl 直接生成 |
| **响应矩阵** | 招标要求 → 响应章节 → 响应状态 → 风险/缺口 | Markdown 直接输出 |
| **交付检查清单** | 签字盖章、格式、页码、目录、密封/上传、文件命名、截止时间 | Markdown 直接输出 |

---

## P1: 招标文件解析

### 1.1 先抽取结构化信息

必须先读取招标文件，形成 `tender-analysis.md` 或等价结构化摘要：

```yaml
项目名称:
采购人/招标人:
项目编号:
采购内容:
预算/最高限价:
服务期限:
交付地点:
投标截止时间:
文件组成要求:
资格要求:
实质性条款:
评分办法:
报价要求:
格式要求:
签字盖章要求:
```

### 1.2 标注强制要求

按风险等级标注：

| 等级 | 判断标准 | 处理要求 |
|------|---------|---------|
| **红色 — 废标风险** | “必须”“不得”“无效投标”“实质性响应”“资格审查” | 必须逐条覆盖，禁止遗漏 |
| **橙色 — 评分影响** | 评分办法、技术参数、业绩、团队、方案完整性 | 优先强化，有证据支撑 |
| **蓝色 — 格式规范** | 目录、页码、装订、命名、份数、签章 | 生成检查清单 |
| **灰色 — 背景信息** | 项目背景、采购目标、参考描述 | 用于技术方案叙事 |

### 1.3 建立响应矩阵

所有招标要求都要进入矩阵，禁止凭印象写标书。

| 招标要求 | 类型 | 响应文件 | 响应章节/表格 | 当前状态 | 风险 |
|---------|------|---------|--------------|---------|------|
| 资格条件 | 商务 | 商务标 | 资格证明文件 | 已覆盖/缺材料 | 高 |
| 技术需求 | 技术 | 技术标 | 功能响应章节 | 已覆盖/需补充 | 中 |
| 报价格式 | 报价 | 报价清单 | 分项报价表 | 已覆盖/需确认 | 高 |

---

## P2: 模板素材映射

### 2.1 分析已有模板

对商务标、技术标、报价清单分别分析：

1. 文档标题、目录层级、章节顺序
2. 可复用章节与需替换章节
3. 公司固定信息、资质、承诺、业绩等通用素材
4. 项目特定内容、客户名称、项目名称、日期、金额等变量
5. 表格结构、页眉页脚、编号样式、签章位置

### 2.2 建立变量表

```yaml
project_name: 项目名称
tenderer: 招标人/采购人
bidder: 投标人
bid_date: 投标日期
service_period: 服务期限
total_price: 投标总价
tax_rate: 税率
contact_person: 联系人
legal_representative: 法定代表人
authorized_representative: 授权代表
```

未知变量必须显式标记为 `待确认`，不得编造。

### 2.3 素材复用原则

- **优先复用**已有终稿模板的结构、语气、格式、章节命名。
- **只替换必要内容**，避免无关重写导致格式或合规风险。
- **保留原有证明材料占位**，缺材料时写入缺口清单，而不是删除章节。
- **报价表优先保留公式**，修改单元格前先识别公式、合并单元格、汇总逻辑。
- **合同条款响应**应逐条写“响应/无偏离/正偏离/负偏离”，不得模糊表述。

---

## P3: 文件编制工作流

### 3.0 生成策略

**商务标、技术标：不再使用 python-docx 自行生成 Word。**
改为按 [Word 内容包规范](../../word/word-master/reference/word-content-package-spec.md) 输出 `.word-content.md`，交给 word-master 做专业排版。
**述标PPT：统一使用 proposal-pptx 模板编译器（mode=tender）。**
基于标准参考 PPT + 三母版约定（首尾=标题幻灯片，目录=节标题，内容=标题和内容）生成，不再使用旧的轻量默认母版。
**报价清单：保持 openpyxl 直接生成**（xlsx 不在 word-master 处理范围内）。

```
投标内容编排完成
    ↓
商务标：输出 Word 内容包 → word-master → 商务标.docx
技术标：输出 Word 内容包 → word-master → 技术标.docx
述标PPT：输出 YAML 内容包(mode=tender) → proposal-pptx compile.py → 述标PPT.pptx
报价清单：openpyxl 直接生成 → 报价清单.xlsx
响应矩阵：Markdown 直接输出 → response-matrix.md
交付清单：Markdown 直接输出 → delivery-checklist.md
```

### 3.0.1 CLI 工具：自动化内容包生成（推荐）

bid-doc-master 内置 CLI 工具，可自动化招标文件解析和内容包生成。比 Agent 手写内容包更标准化。

**两步工作流：**

```bash
cd skills/business/bid-doc-master

# Step 1: 提取招标文件原始数据 → JSON
uv run python -m src.main extract "招标文件.docx" "功能清单.xlsx" -o tender_raw.json -v

# Step 2: Agent 分析 JSON，填充 TenderInfo 字段后生成内容包
uv run python -m src.main generate tender_info.json \
  --bidder "广州市蓝联科技有限公司" \
  --type technical \
  --slide \
  -v
```

**Step 1 输出**：`tender_raw.json`（招标文件全文 + 表格 + 功能清单）

**Step 2 输出**：
- `{项目}_{技术标|商务标}.word-content.md` — 交给 word-master 排版
- `{项目}_述标PPT.content.md`（`--slide` 时）— 述标 PPT 内容包

**TenderInfo JSON 关键字段**（Agent 从 Step 1 的 raw JSON 分析后填充）：

```json
{
  "project_name": "项目名称",
  "purchaser": "采购人",
  "qualification_requirements": ["资质要求..."],
  "technical_requirements": ["技术要求..."],
  "scoring_items": ["评分项..."],
  "function_list": [{"module": "", "function": "", "description": ""}],
  "personnel_requirements": ["人员要求..."],
  "service_level_requirements": ["SLA要求..."],
  "timeline_requirements": ["里程碑..."],
  "key_response_items": ["重点响应..."],
  "format_overrides": {"font": {}, "margins": {}, "page": {}}
}
```

> 未知字段留空数组 `[]`，不得编造。Agent 也可选择不用 CLI，直接手写 `.word-content.md`。

### 3.1 商务标 → Word 内容包

商务标按 [Word 内容包规范](../../word/word-master/reference/word-content-package-spec.md) 输出 `.word-content.md`，交给 word-master 排版。

**商务标章节 → 内容包映射：**

| 商务标章节 | 内容包元素 | 说明 |
|-----------|-----------|------|
| 封面 | `cover:` 元数据 + `template: bidding-commercial` | 自动选择投标商务标封面模板 |
| 投标函 | `heading-1` + 正式函件文本 | 分页，函件格式 |
| 法定代表人证明 | `heading-1` + 函件文本 | 分页 |
| 授权委托书 | `heading-1` + 函件文本 | 分页 |
| 投标人基本情况 | `heading-1` + `table: default-table` | 公司信息表 |
| 资格证明文件 | `heading-1` + 资质引用列表 | 分页，逐项列明 |
| 商务条款响应表 | `heading-1` + `table: comparison-table` | 招标条款→响应情况 |
| 合同条款响应/偏离表 | `heading-1` + `table: comparison-table` | 条款→偏离说明 |
| 类似项目业绩 | `heading-1` + `table: default-table` | 项目清单表，可用 case_matcher 自动筛选同类案例 |
| 服务承诺 | `heading-1` + 承诺文本 | 分页 |
| 其他商务材料 | `heading-1` + 按需 | 招标文件要求 |

**流程：**
1. 文件编排完成后，按 Word 内容包规范生成 `.word-content.md`
2. 放入 `$BIDDING_DIR/{项目名称}/content-packages/{项目名称}_商务标_{YYYYMMDD}.word-content.md`
3. 告知用户："商务标内容已编排完成，正在调用 word-master 排版..."
4. word-master 读取内容包后生成 `.docx`，输出到 `$BIDDING_DIR/{项目名称}/output/`

### 3.2 技术标 → Word 内容包

技术标同样按 Word 内容包规范输出 `.word-content.md`，交给 word-master 排版。

**技术标章节 → 内容包映射：**

| 技术标章节 | 内容包元素 | 说明 |
|-----------|-----------|------|
| 封面 | `cover:` + `template: bidding-technical` | 投标技术标封面 |
| 项目背景与需求理解 | `heading-1` + `heading-2` 小节 | 分页 |
| 总体建设思路 | `heading-1` + 架构描述 | 可选架构图引用 |
| 功能需求响应方案 | `heading-1` + `table: function-matrix` | 功能矩阵表 |
| 系统架构设计 | `heading-1` + 技术描述 | 分页 |
| 实施计划 | `heading-1` + `table: implementation-plan` | 实施计划表 |
| 项目组织与人员配置 | `heading-1` + `table: personnel-matrix` | 人员配置表 |
| 质量保障与风险控制 | `heading-1` + bullet list | 分页 |
| 培训与运维方案 | `heading-1` + 服务描述 | 分页 |
| 技术偏离表/响应表 | `heading-1` + `table: comparison-table` | 技术参数响应 |
| 验收方案 | `heading-1` + 交付物清单 | 不分页 |

**流程：**
1. 文件编排完成后，按 Word 内容包规范生成 `.word-content.md`
2. 放入 `$BIDDING_DIR/{项目名称}/content-packages/{项目名称}_技术标_{YYYYMMDD}.word-content.md`
3. 告知用户："技术标内容已编排完成，正在调用 word-master 排版..."
4. word-master 读取内容包后生成 `.docx`，输出到 `$BIDDING_DIR/{项目名称}/output/`

> **2026-07-05 补充：商管/经营类投标的特殊处理**。当投标对象是商业地产商管 ERP / 经营管控平台 / 资管系统时：
> - **项目背景与需求理解**：可引用 `$LANLNK_BASE/materials/10-methodology/methodology/15-商业地产岗位病药矩阵.md`，按岗位（招商总/财务总/营运总/企划总/物业总/IT总）拆需求理解，比泛泛的功能需求清单更有针对性。
> - **功能需求响应方案**：功能矩阵表可用"岗位 × 病点 × 功能响应"组织，而非纯功能点逐条响应。
> - **业绩/案例证明**：遵循证明口径分级（Z1 实证/Z2 竞品行业对标/Z3 蓝联产品状态/Z4 待试点验证）。开发中产品不把关联产品（如会员 CRM）的客户案例冒充本产品（如商管 ERP）实证。案例引用前必须确认产品边界。

### 3.3 述标PPT → proposal-pptx YAML 内容包

述标PPT 统一输出 YAML 内容包，调用 `skills/ppt/ppt-master/templates/proposal-pptx/compile.py` 的 `mode=tender` 模式。

**推荐4段式目录：**
1. 公司简介与资质
2. 需求理解与方案蓝图
3. 重点功能响应
4. 实施服务与选择理由

**YAML骨架：**

```yaml
mode: tender
base_ppt: "/opt/code/docs/lanlnk/incoming/正祥选型方案/蓝联科技CRM商圈会员数智营销方案_202604.pptx"
output: "$BIDDING_DIR/{项目名称}/{项目简称}_述标PPT.pptx"
cover:
  title: "{项目名称}述标答辩"
  subtitle: "{采购人/招标人}"
  date: "{YYYY年MM月}"
toc:
  titles:
    - 公司简介与资质
    - 需求理解与方案蓝图
    - 重点功能响应
    - 实施服务与选择理由
sections:
  - slides:        # Section 1
      - type: text-bullets
        title: "公司概况"
        body: "..."
        items: ["...", "..."]
  - slides: []     # Section 2
  - slides: []     # Section 3
  - slides: []     # Section 4
```

**可用页型：**
- `text-bullets`：标题 + 正文 + 要点列表
- `feature-cards`：标题 + 2/3/4列卡片网格

**流程：**
1. 将投标技术标内容提炼为 4 个述标章节
2. 生成 `$BIDDING_DIR/{项目名称}/content-packages/{项目简称}_述标PPT.yaml`
3. 执行：`cd skills/ppt/ppt-master/templates/proposal-pptx && uv run python compile.py <yaml>`
4. 输出 PPT 到 `$BIDDING_DIR/{项目名称}/`

### 3.4 报价清单（openpyxl）

报价文件必须先识别招标口径，再生成或修改报价表。

检查项：

1. 是否有最高限价或预算控制价
2. 报价是否含税、税率是否明确
3. 是否要求分项报价、单价、数量、总价
4. 是否要求大小写金额一致
5. 是否要求服务期、免费维护期、付款节点说明
6. 是否存在不可竞争费用或固定价格项

处理原则：

- 保留模板中的公式和汇总关系。
- 金额未知时用 `待报价` 占位，并生成报价待确认清单。
- 大写金额必须由小写金额转换，不得手工随意填写。
- 输出前检查分项合计与总价一致。

**标准化报价单生成（推荐）：**

```bash
cd skills/business/bid-doc-master
uv run scripts/pricing_compiler.py <报价配置.yaml> --output <输出路径.xlsx> -v
```

YAML 格式支持 4 分类（软件核心/开发交付/实施服务/售后服务）、可选模块标记、SAAS/私有化模式、税率、服务说明。详见 `materials/references/报价模板_SAAS.md`。

---

## P4: 合规与质量校验

### 4.0 Common Rationalizations — 禁止跳步的反借口表

| 常见跳步理由 | 真实风险 | 正确动作 |
|-------------|---------|---------|
| “模板已经是终稿，直接替换项目名就行” | 历史模板不会自动覆盖本次招标新增要求，可能漏响应或残留旧项目信息 | 先做招标要求响应矩阵，再映射模板章节 |
| “资格要求都是标准材料，可以后面补” | 资格审查缺项通常直接废标 | 先列资格材料清单，缺失项进入待确认事项 |
| “报价可以最后随便填一个数” | 最高限价、税率、分项合计、大小写金额不一致会导致无效或扣分 | 先识别报价口径和公式，再生成报价待确认清单 |
| “技术方案写通用内容就够了” | 评分项需要逐条响应，通用方案无法拿分 | 按评分办法和技术需求逐条强化章节 |
| “合同条款不用逐条看” | 付款、验收、违约、服务期等条款可能产生商务风险 | 建立商务/合同条款响应表，标注偏离与风险 |
| “没有信息就帮用户补一个合理值” | 编造资质、业绩、人员、金额会造成严重合规风险 | 未知信息统一标记为 `待确认`，不得臆造 |

### 4.1 响应完整性校验

每次交付前必须输出响应检查：

```text
✅ 已覆盖：招标文件明确要求且已在投标文件中响应
⚠️ 待确认：需要用户补充公司/报价/资质/人员/业绩信息
❌ 缺失：招标要求存在但模板或输入材料没有对应内容
🚫 风险：可能导致废标、扣分或商务风险的内容
```

### 4.2 一致性校验

必须检查：

- 项目名称、项目编号、采购人、投标人全文一致
- 商务标、技术标、报价清单的服务期限一致
- 报价小写、大写、分项合计、总价一致
- 页眉页脚、目录、页码、章节编号连续
- 签字盖章位置完整
- 附件、证明材料、承诺函无遗漏
- 文件名符合招标文件要求

### 4.3 禁止事项

- 不得编造资质证书、人员证书、业绩合同、报价金额、授权文件。
- 不得删除招标文件要求的章节或表格。
- 不得把模板中的旧项目名称、旧客户名称、旧日期残留到新文件。
- 不得忽略“实质性响应”“无效投标”“资格审查”条款。
- 不得在未核对公式的情况下直接覆盖报价表汇总单元格。

---

## P5: 交付物规范

### 5.1 推荐输出目录

```text
$BIDDING_DIR/<项目名>/output/
├── 01-招标文件解析-tender-analysis.md
├── 02-响应矩阵-response-matrix.md
├── 03-商务标-终稿.docx             （由 word-master 根据内容包生成）
├── 04-技术标-终稿.docx             （由 word-master 根据内容包生成）
├── 05-报价清单-终稿.xlsx           （openpyxl 直接生成）
├── 06-待确认事项-confirmation-list.md
├── 07-交付检查清单-delivery-checklist.md
└── content-packages/               （中间产物，提交给 word-master）
    ├── 项目名称_商务标_YYYYMMDD.word-content.md
    └── 项目名称_技术标_YYYYMMDD.word-content.md
```

### 5.2 无法直接生成 Office 文件时

如果当前环境缺少 openpyxl 或 word-master 不可用，仍需交付：

1. 商务标 Markdown 草稿（含内容包 YAML frontmatter）
2. 技术标 Markdown 草稿（含内容包 YAML frontmatter）
3. 报价清单 CSV/Markdown 草稿
4. 响应矩阵
5. 待确认事项清单
6. 手工套版说明：哪些内容复制到哪个模板章节

### 5.3 最终回复格式

交付时说明：

```text
已完成：
- 商务标：路径（由 word-master 根据内容包排版）
- 技术标：路径（由 word-master 根据内容包排版）
- 报价清单：路径
- 响应矩阵：路径
- 待确认事项：路径

📦 内容包（已提交给 word-master）：
- content-packages/项目名称_商务标_YYYYMMDD.word-content.md
- content-packages/项目名称_技术标_YYYYMMDD.word-content.md

关键风险：
- 风险 1
- 风险 2

验证方式：
- 已检查招标要求覆盖率
- 已检查报价公式/合计
- 已检查项目名称/编号一致性
```

---

> 快速启动示例见 `references/case-example.md`。
