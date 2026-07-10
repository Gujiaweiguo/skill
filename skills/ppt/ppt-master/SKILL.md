---
name: ppt-master
description: >
  专业 PPT 演示文稿创作 Skill。基于 slides + imagegen 方案，通过 PptxGenJS
  编程生成可继续编辑的 .pptx 文件。支持从已有模板修改、基于大纲新建、
  以及补充视觉素材。适合商务汇报、技术方案、客户演示等正式交付场景。
  触发场景："做个PPT"、"做演示文稿"、"帮我把这个改成PPT"、"帮我做一份汇报"、
  "把这个大纲做成 slide"、"slides"、"presentation"、"deck"、"pptx"、
  "演示文稿"、"汇报PPT"、"提案"、"方案演示"、"路演PPT"、
  "帮我改一下这个PPT"、"给这个PPT加几页"、"美化这个PPT"。
  当用户提供大纲、文稿或已有 PPT 文件并要求转化为演示文稿时，同样触发此 skill。
compatibility: >
  Requires Node.js + pptxgenjs for .pptx generation.
  Requires web_search / web_fetch for content research.
  Requires imageGen for visual material supplementation.
  Degrades gracefully: text-only outline if pptxgenjs unavailable.
---

# PPT Master — 专业演示文稿创作 Agent Pipeline

## DocSpec 质量基线

本 skill 生成的 PPT、PPT 内容包、视觉素材引用和渲染说明必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `PPT与Word内容包质量规范.md` 和 `文档验收清单.md`。每页观点、数据来源、素材路径、编译结果和文本溢出必须可检查。

基于 `slides + imagegen` 方案，用户给需求，Agent 去设计 + 生成，你只管 Plan 和验收。

## Architecture

```
用户需求 / 大纲 / 已有 PPT
        ↓
P0: 环境检测 + 任务类型判断
        ↓
Lead Agent (你 — 总体规划与设计决策)
        │
  ┌─────┼─────┐
  │     │     │
  P1   P2    P3
  分析  设计  生成
  现有  决策  输出
  内容
        │
        ↓
P4: QA 验收 + 交付
```

---

## P0: 环境检测与任务分类

### 0.1 环境检测

```
1. Node.js + pptxgenjs 可用?  →  可生成 .pptx
2. web_search / web_fetch 可用?  →  可做内容研究
3. imageGen 可用?  →  可补充视觉素材
4. markitdown 可用?  →  可读取已有 PPTX
```

### 0.2 任务类型判断

| 输入类型 | 处理方式 |
|---------|---------|
| **已有 PPT 文件** → 修改/扩充 | 先读取分析现有内容，再执行修改 |
| **大纲/要点列表** → 新建 | 按要点规划页面，研究补充 |
| **文稿/文章** → 提取转演示 | 提炼核心观点后新建 |
| **纯主题/关键词** → 从0研究新建 | 先研究后规划 |
| **结构化内容包 `*.content.md`** → 视觉设计 | 解析内容包，按页面类型+layout 自动生成（详见 0.4） |

### 0.4 内容包输入模式

当输入为结构化内容包（`*.content.md`）时，表示上游业务 Skill（如 project-proposal-generator、company-intro-generator）已完成内容编排，ppt-master 只负责视觉设计。

内容包格式规范见 [reference/content-package-spec.md](reference/content-package-spec.md)。

**处理流程：**
1. 解析 frontmatter → 获取元数据（title/style/target_pages/colors）
2. 解析页面大纲 → 获取每页 type + layout + 内容
3. 根据 style 字段选择配色方案（如"咨询风格"→ 深蓝+灰）
4. 逐页按 type + layout 选择版式生成
5. 根据 sources 引用检查素材是否存在，存在则引用
6. 按目标页数范围控制详细程度

**页面类型 → 版式映射：**

| content type | ppt-master 版式 |
|-------------|----------------|
| `cover` | 封面页（大标题+副标题+日期+品牌） |
| `toc` | 目录页（章节列表） |
| `section` | 章节过渡页（标题+装饰） |
| `content` + `left-right` | 左右分栏 |
| `content` + `comparison` | 多列对比 |
| `content` + `feature-grid` | 功能网格 |
| `content` + `data-table` | 数据表格 |
| `content` + `timeline` | 时间轴 |
| `content` + `big-number` | 大数字页 |
| `content` + `bullet-list` | 列表页 |
| `summary` | 总结页 |
| `end` | 结尾页 |

**无内容包时的后备行为：**
如果未收到内容包，ppt-master 沿用原有流程——自己研究内容 + 自己设计生成。

### 0.3 方案选型

| 场景 | 推荐方案 |
|------|---------|
| 商务汇报 / 技术方案 / 客户演示 / 正式交付 | `slides + imagegen`（默认） |
| 需要反复修改的正式 PPT | `slides + imagegen` |
| 快速出风格化初稿 / 文章转演示 | 可选 `baoyu-slide-deck` |

---

## P1: 内容分析（修改场景）或 研究规划（新建场景）

### 修改场景：分析已有 PPT

执行以下检查并输出：

1. **幻灯片尺寸与宽高比**
2. **母版 / 版式结构**
3. **主题字体、主题色、常用页边距与对齐规则**
4. **每页主要元素位置与可编辑对象类型**

使用 markitdown 读取 PPTX 内容结构。

### 新建场景：内容研究与规划

根据主题/大纲，研究并规划页面结构：

1. 拆解大纲为 3-8 个核心页面
2. 每个页面确定页面类型和核心观点
3. 需要数据支撑的观点 → 用 web_search 查找

#### 页面类型

| 类型 | 用途 | 典型内容 |
|------|------|---------|
| **Cover** | 开场定调 | 大标题 + 副标题 + 日期 + 品牌元素 |
| **TOC** | 导航预期 | 章节列表 (3-6 节) |
| **Section** | 章节过渡 | 章节标题 + 核心数据 / 引用 |
| **Content** | 核心内容 | 观点 + 数据 + 图表 |
| **Summary** | 总结收束 | 核心回顾 + CTA / 联系方式 |

---

## P2: 设计决策

### 2.1 配色方案选择

根据主题和受众选择：

| 场景 | 推荐色板 |
|------|---------|
| 商务 / 年报 / 财务 | 深蓝 + 灰色系（#1a1a2e, #16213e, #0f3460, #e94560, #f5f5f5） |
| 科技 / 产品发布 | 深色 + 亮色强调（#0a0a0a, #1a1a2e, #00d4ff, #ff006e, #f0f0f0） |
| 教育 / 培训 | 暖色 + 舒适（#2d6a4f, #52b788, #95d5b2, #d8f3dc, #fefae0） |
| 数据分析 / 咨询 | 保守专业（#1b263b, #415a77, #778da9, #e0e1dd, #ffffff） |
| 创意 / 时尚 / 品牌 | 大胆个性化（可根据品牌色定制） |

### 2.2 布局多样性原则

- **严禁**连续使用相同布局
- 主动切换：左右分栏、大数字突出、时间轴、对比图、引用卡片、图标网格
- 内容类型匹配版式：关键数据 → 大数字页，对比 → 左右分栏，流程 → 时间轴

### 2.3 排版规范

| 规则 | 说明 |
|------|------|
| 标题 | 正文的 2-3 倍字号，加粗 |
| 正文 | 不加粗，保持可读字号 |
| 配色 ≤ 5 色 | 使用配色方案，不自创颜色 |
| 一页一观点 | 每页只传达一个核心信息 |
| 留白 ≥ 30% | 不要撑满每个角落 |

---

## P3: 生成输出（slides + imagegen）

### 3.1 PptxGenJS 技术约束

| 项目 | 值 |
|------|---|
| **尺寸** | 10" x 5.625" (LAYOUT_16x9) |
| **颜色格式** | 6 位 hex 不带 #（如 `"1a1a2e"`） |
| **英文字体** | Arial（默认） |
| **中文字体** | Microsoft YaHei（微软雅黑） |
| **页码位置** | 右下角，与边缘保持安全距离 |
| **\n 换行符** | pptxgenjs v4 不支持 `\n` — 所有行渲染在同一 Y 位置 |

### 3.2 Theme 对象规范

```javascript
// 所有颜色来自 theme，不自创颜色
// key 名称固定，不可更改
const theme = {
  primary: "1a1a2e",    // 最深色，标题用
  secondary: "16213e",  // 深色辅助，正文
  accent: "0f3460",     // 强调色
  light: "e94560",      // 浅色强调/高亮
  bg: "f5f5f5"          // 背景色
};
```

**不允许**使用其他 key 名如 `background`、`text`、`muted`、`darkest`。

### 3.3 工作流

```
slides/                    # 生成脚本目录
├── slide-01.js           # 每页一个文件，export 同步函数
├── slide-02.js
├── ...
└── compile.js            # 编排所有页，生成最终 .pptx
```

每页文件模板：

```javascript
// slide-XX.js
function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  // ... 构建页面内容
  return slide;
}
module.exports = { createSlide };
```

### 3.4 ImageGen 边界

- **适合生成**：抽象插图、封面视觉、背景纹理、装饰元素
- **不适合替代**：logo、图标系统、原生图表、公司品牌标识
- 优先复用现有品牌视觉资产，imageGen 只作为补充

### 3.5 生成步骤

1. 创建 `slides/` 目录
2. 每页一个 JS 文件，export `createSlide(pres, theme)` 同步函数
3. 创建 `compile.js` 编排所有页
4. **引入渲染修复模块**：`var fix = require('./lib/pptx-render-fix')`，创建 `pres` 后立即调用 `fix.patchPresentation(pres)`
5. 运行 `node compile.js`
6. 输出 `slides/output/presentation.pptx`
7. 如有需要，用 imageGen 补充视觉素材

### 3.6 PptxGenJS 关键陷阱

- **绝不复用选项对象** — PptxGenJS 会原地修改对象（如 shadow 值转 EMU）。用工厂函数生成新对象
- **createSlide 必须同步** — 不能是 async function
- **颜色不带 #** — `"FF0000"` 不是 `"#FF0000"`
- **正文不加粗** — bold 只用于标题和 heading
- **只用 theme 里的颜色** — 不要自己发明颜色
- **\n 换行符不生效** — pptxgenjs v4 把 `\n` 所有行渲染在同一 Y 位置，永远不要直接使用 `\n`

### 3.7 渲染修复模块（必用）

`lib/pptx-render-fix.js` 提供 pptxgenjs 渲染层修复，每次 compile.js **必须引入**：

```javascript
var fix = require('../../lib/pptx-render-fix');
fix.patchPresentation(pres);
```

修复内容：
1. **文本内边距**：OOXML 默认 L/R 0.1"、T/B 0.05" 过大，改为 2pt（25400 EMU）
2. **\n 自动拆分**：自动检测 `addText` 中的 `\n`，拆分为独立 `addText` 调用

### 3.8 布局组件库

`lib/pptx-layouts.js` 提供可复用的布局组件，支持 LAYOUT_WIDE（13.333×7.5）：

```javascript
var layouts = require('../../lib/pptx-layouts');
var L = layouts.createLayouts(pptx);

L.addTopBand(slide, "标题", "徽章", 1);
L.addCard(slide, { x, y, w, h, title, body, accent });
L.addMetricCard(slide, x, y, w, h, tone, num, title, desc);
L.addFlowDiagram(slide, { x, y, w, h, title, steps, tone, soft, footerTags });
L.addThreeExplainCards(slide, { x, y, w, cardH, accent, cards });
L.addBottomStatement(slide, "金句", "coral");
```

内置 20 色调色板（`L.C.deep/blue/teal/amber/coral/...`），详见 `reference/design-system.md` 核心闭环版式。

### 3.9 模板库

`templates/` 目录提供按场景的完整 PPT 模板：

| 模板 | 位置 | 引擎 | 说明 |
|------|------|------|------|
| 立项报告 | `templates/proposal-template/compile.js` | PptxGenJS | 13页标准立项 PPT（含4个核心闭环场景） |
| 方案介绍 | `templates/proposal-pptx/compile.py` | python-pptx | 基于参考PPT + YAML内容包，插入定制分析页 |

**立项报告模板**（PptxGenJS）：复制模板目录 → 修改 CONFIG 和文本内容 → `node compile.js`

**方案介绍模板**（python-pptx）：

适用于「公司已有标准产品PPT（含产品截图/案例照片），需要为不同客户生成定制方案介绍」的场景。支持两种模式：

| 模式 | YAML `mode` | 用途 | 输出页数 |
|------|------------|------|---------|
| 方案汇报 | `proposal`（默认） | 完整方案介绍（公司+需求理解+产品方案+实施服务） | ~59页 |
| 公司介绍 | `intro` | 公司介绍（公司简介+案例+客户定制内容） | ~30页 |
| 投标述标 | `tender` | 述标答辩（公司资质+需求理解+重点响应+实施服务） | ~17页 |

架构：
```
参考 PPT (固定基底, 产品截图/案例) + YAML 内容包 (客户定制数据)
    ↓ compile.py (python-pptx)
完整方案 PPT (基底 + 定制页)
```

**proposal 模式**定制页型：
1. `requirement-understanding` — 需求理解（分类卡片 + 核心洞察）
2. `coverage-analysis` — 功能覆盖度（三大指标卡）
3. `core-scenario` — 核心场景（双行闭环流, 核心闭环版式）
4. `pricing-comparison` — 报价对比（双方案卡片）
5. `implementation-plan` — 实施计划（阶段时间线）

**intro 模式**定制页型：
1. `text-bullets` — 标题+正文+要点列表
2. `feature-cards` — 标题+卡片网格（columns: 2/3/4）

**tender 模式**定制页型（与 intro 共用）：
1. `text-bullets` — 标题+正文+要点列表
2. `feature-cards` — 标题+卡片网格（columns: 2/3/4）

3 母版约定：首尾页 → 标题幻灯片(0)，目录页 → 节标题(1)，内容页 → 标题和内容(2)

使用方式：
```bash
cd templates/proposal-pptx && uv sync
uv run python compile.py <content-package.yaml>
```

内容包 YAML 示例：
- proposal 模式：`proposals/正祥会员系统/content-packages/正祥会员系统_proposal-pptx.yaml`
- intro 模式：`proposals/广州海港地产/content-packages/广州海港地产_intro-pptx.yaml`
- tender 模式：`bidding/果正商业会员营销系统采购服务/content-packages/sz_gz_tender_述标PPT.yaml`

渲染前校验（可选）：
```bash
cd skills/ppt/ppt-master/templates/proposal-pptx
uv run ../../scripts/validate_ppt_package.py <YAML配置> --verbose
```
校验项：mode 枚举、base_ppt 存在性、slide type 合法性（8 种）、TOC 标题数量（≤4）、theme 颜色格式、cover/theme 未知字段。

---

## P4: QA 验收

### 验收清单

- [ ] 每页分类为五种页面类型之一
- [ ] 连续页无相同布局
- [ ] Theme 对象 key 正确（primary/secondary/accent/light/bg）
- [ ] 所有颜色来自 theme，无自创颜色
- [ ] 正文不加粗，bold 仅用于标题
- [ ] Cover 外每页有页码
- [ ] `node compile.js` 成功运行
- [ ] 生成 .pptx 可正常打开

### 内容验证

- [ ] 每页只传达一个核心观点
- [ ] 数据来自研究或已有内容，无编造
- [ ] 统计数据标注年份和来源
- [ ] 所有页面内容保持一致的设计语言

### 视觉验证

- [ ] 渲染每页 PNG 审核
- [ ] 检查元素是否越界或重叠
- [ ] 检查字体缺失或替换
- [ ] 检查留白是否充足

---

## 最小可用 Prompt

```
用 slides 和 imagegen 编辑/创建幻灯片。

先不要直接修改，先检查并输出：
1) 幻灯片尺寸与宽高比
2) 母版 / 版式结构
3) 主题字体、主题色、常用页边距与对齐规则
4) 每页主要元素位置与可编辑对象类型

确认后再执行修改：
1) 保持品牌风格一致性
2) 文本保持文本对象，不把整页做成图片
3) 简单图表保持为 PowerPoint 原生图表
4) imagegen 仅用于补充视觉素材（抽象插图、封面、背景）

完成后执行验证：
1) 渲染每页 PNG 审核
2) 检查元素是否越界或重叠
3) 检查字体缺失或替换
4) 输出修改后的 .pptx、生成脚本 .js、所用插图资产
```

## 已知坑与排障

生成 PPT 后正文消失/挤压、表格行丢字、bullet 不可见 → 见 [`references/troubleshooting.md`](references/troubleshooting.md)。

核心规则：**不要用 `text\nline2\nline3` 拼接多行**，改用 `addStackedText` 辅助函数每行独立 `addText`；生成后必须用 LibreOffice 转 PDF + OCR 视觉抽查，不能只检查 PPTX zip 完整性。

## 依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| pptxgenjs | PptxGenJS — 从零创建 PPTX | `npm install -g pptxgenjs` |
| markitdown | 读取已有 PPTX 内容 | `pip install "markitdown[pptx]"` |
