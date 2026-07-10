---
name: mckinsey-pptx
description: >
  麦肯锡风格专业演示文稿创作 Skill。基于 slides + imagegen 方案，
  严格遵循麦肯锡视觉规范：深蓝 header 栏、结构化版式、数据驱动叙事、
  MECE 原则与金字塔结构。通过 PptxGenJS 生成可继续编辑的 .pptx 文件。
  适合战略咨询、管理咨询、投资分析、行业研究等专业商务场景。
  触发场景："做一份麦肯锡风格的PPT"、"咨询风格演示"、"战略咨询PPT"、
  "McKinsey style"、"consulting deck"、"战略汇报"、"投研报告"、
  "行业研究PPT"、"管理咨询方案"、"给客户的提案"、"pitch deck"、
  "要做一份给老板看的汇报"、"对标分析"、"竞品研究"。
  当用户需要高度结构化、数据驱动、专业视觉的演示文稿时，同样触发此 skill。
compatibility: >
  Requires Node.js + pptxgenjs for .pptx generation.
  Requires web_search / web_fetch for content research.
  Requires imageGen for visual material supplementation.
  Degrades gracefully: text-only outline if pptxgenjs unavailable.
---

# McKinsey PPT — 麦肯锡风格专业演示文稿创作

## DocSpec 质量基线

本 skill 生成的战略咨询类 PPT、内容包和数据化叙事必须遵守 `/opt/code/skill/references/docspec/`，重点执行 `DocSpec-通用文档质量规范.md`、`方案与投标文档质量规范.md`、`PPT与Word内容包质量规范.md` 和 `文档验收清单.md`。结论、证据、图表和建议必须可追溯。

严格遵循麦肯锡视觉规范与咨询叙事逻辑。用户给需求，Agent 去结构化 + 设计 + 生成。

## 麦肯锡风格三核心

### 1. 金字塔结构（Pyramid Principle）
- 结论先行：每页标题就是核心结论（而非主题标签）
- MECE 分解：Mutually Exclusive, Collectively Exhaustive
- 论据层层支撑：主论点 → 分论点 → 数据/事实

### 2. 结构化叙事（SCQA Framework）
- **S**ituation：背景/现状
- **C**omplication：挑战/问题
- **Q**uestion：关键问题
- **A**nswer：解决方案/建议

### 3. 视觉规范
- 深蓝 header + 白色内容区，干净利落
- 标题即结论（而非描述）
- 大量数据图表，少用复杂装饰
- 来源标注严谨

---

## P0: 环境检测与任务分类

### 环境检测
```
1. Node.js + pptxgenjs 可用? → 可生成 .pptx
2. web_search / web_fetch 可用? → 可做内容研究
3. imageGen 可用? → 可补充视觉素材
4. markitdown 可用? → 可读取已有 PPTX
```

### 任务类型
| 输入类型 | 处理方式 |
|---------|---------|
| 已有 PPT 文件 → 改为麦肯锡风格 | 分析 → 重新设计 → 生成 |
| 分析需求/主题 → 新建 | 结构化 → 研究 → 设计 → 生成 |
| 数据/报告 → 转演示 | 提炼核心发现 → 按金字塔结构组织 |

---

## P1: 内容结构化（麦肯锡方法）

### 1.1 定义核心信息
明确这份 PPT 要传递的唯一核心结论。所有页面围绕这个结论展开。

### 1.2 SCQA 框架搭建叙事线
```
S — 行业/客户当前处于什么状态
C — 面临什么关键挑战/发生了什么变化
Q — 需要回答的核心战略问题是什么
A — 我们的分析结论/建议方案是什么
```

### 1.3 MECE 分解
每个论点拆解为 3-5 个 MECE 子论点。检查标准：
- **Mutually Exclusive**：子论点之间不重叠
- **Collectively Exhaustive**：子论点覆盖全部可能性

### 1.4 页面结构规划
典型咨询 deck 结构（10-20 页）：

| 序号 | 页面类型 | 内容 |
|------|---------|------|
| 1 | **Title** | 报告标题 + 客户 + 日期 + 保密声明 |
| 2 | **Executive Summary** | 核心结论 + 关键发现要点 |
| 3 | **Table of Contents** | 章节概览 |
| 4-5 | **Situation** | 市场/行业/客户现状分析 |
| 6-8 | **Complication** | 关键问题与挑战分析 |
| 9-12 | **Analysis** | 深度分析（数据、对标、趋势） |
| 13-15 | **Recommendation** | 方案建议与实施路径 |
| 16 | **Appendix** | 附录索引 |

---

## P2: 设计决策 — 麦肯锡视觉系统

### 2.1 配色方案

#### 经典麦肯锡蓝（Default McKinsey）
```javascript
{ primary: "003c71",    // 麦肯锡深蓝 - 标题、header 栏
  secondary: "1a1a1a",  // 正文黑色
  accent: "0077b6",     // 强调蓝 - 图表、标注
  light: "e8edf2",      // 浅灰蓝 - 背景/表格间隔
  bg: "ffffff" }         // 白色背景
```

#### 深色专业（Dark Consulting）
```javascript
{ primary: "0d1b2a",    // 极深蓝黑 - 强调
  secondary: "1a1a2e",  // 正文
  accent: "e94560",     // 亮红强调 - 关键数据
  light: "e0e1dd",      // 浅灰
  bg: "ffffff" }         // 白色
```

#### 沉稳商务（Executive Blue）
```javascript
{ primary: "1b2838",    // 深蓝灰 - header
  secondary: "2c3e50",  // 正文
  accent: "3498db",     // 亮蓝 - 图表
  light: "ecf0f1",      // 浅灰背景
  bg: "ffffff" }         // 白色
```

### 2.2 版式系统

#### 标准 Content 页布局
```
┌──────────────────────────────────────┐
│ ████████████████████████████████████ │  Header Bar（primary 色）
│ ████  标题即结论（大号加粗）   ████ │  高 0.6"-0.7"
└──────────────────────────────────────┘
                                        ← 0.2"-0.3" 间距
┌──────────────────────────────────────┐
│                                      │
│   核心内容区域                        │
│   - 图表 / 数据可视化                 │
│   - 要点列表（MECE 结构）             │
│   - 对比分析 / 矩阵 / 框架            │
│                                      │
│                                      │
└──────────────────────────────────────┘
┌──────────────────────────────────────┐
│ 来源: [数据来源]              页码 N  │  底栏 0.3"-0.4"
└──────────────────────────────────────┘
```

#### 标题页布局
```
│  客户 Logo（左上角，如有）
│
│             报告主标题（36-44pt）
│             副标题 / 报告类型（20-24pt）
│
│             客户名称 | 日期 | 保密级别
│
│             底部装饰线（primary 色）
```

### 2.3 页面类型定义

| 类型 | 说明 | Header 栏 | 页码 |
|------|------|-----------|------|
| **Title** | 封面 | 无（或 logo 栏） | 无 |
| **Executive Summary** | 核心结论摘要 | 有 | 有 |
| **Section** | 章节过渡 | 无 header，全色背景 | 有 |
| **Content** | 标准内容 | 有 | 有 |
| **Chart** | 图表为主 | 有，标题简洁 | 有 |
| **Framework** | 框架/模型展示 | 有 | 有 |
| **Appendix** | 附录 | 有，标注 Appendix | 有 |

### 2.4 排版规范

| 层级 | 字号(pt) | 加粗 | 颜色 | 字体 |
|------|---------|------|------|------|
| 标题即结论 | 18-24 | 是 | primary | Arial / Microsoft YaHei |
| 正文要点 | 12-14 | 否 | secondary | Arial / Microsoft YaHei |
| 图表标题 | 10-12 | 否 | accent | Arial |
| 来源标注 | 7-9 | 否 | secondary | Arial |
| 页码 | 8-10 | 否 | accent | Arial |
| Header 栏文字 | 10-12 | 否 | white | Arial / Microsoft YaHei |

### 2.5 Header 栏实现（PptxGenJS）

```javascript
// 标准 Header 栏
function addHeader(slide, theme, titleText) {
  // 蓝色 header bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.65,
    fill: { color: theme.primary }
  });
  // Header 中的标题
  slide.addText(titleText, {
    x: 0.3, y: 0.12, w: 9.4, h: 0.4,
    fontSize: 12, fontFace: "Arial",
    color: "FFFFFF", bold: false
  });
}

// 页码
function addPageNumber(slide, theme, num) {
  slide.addText(String(num), {
    x: 9.2, y: 5.25, w: 0.5, h: 0.3,
    fontSize: 9, fontFace: "Arial",
    color: theme.accent, align: "right"
  });
}

// 来源标注
function addSource(slide, theme, source) {
  slide.addText(source, {
    x: 0.4, y: 5.25, w: 8.5, h: 0.3,
    fontSize: 8, fontFace: "Arial",
    color: theme.secondary
  });
}
```

---

## P3: 内容生成与验证

### 3.1 标题即结论（Headline Rule）
麦肯锡最重要规则：**每页标题必须是一个完整的结论句，而非主题标签。**

| ❌ 错误示例 | ✅ 正确示例 |
|-----------|-----------|
| "市场规模分析" | "全球云计算市场2026年将突破$1万亿，CAGR 17%" |
| "竞品对比" | "竞争对手A在价格上占优，B在技术上领先" |
| "用户痛点" | "用户的核心痛点是数据孤岛，而非功能不足" |

### 3.2 数据呈现原则
- 有数据必有图表：能用图说明的不用表，能用表说明的不用文字
- 图表简洁：去除网格线、3D 效果、多余颜色
- 关键数据高亮：用 accent 色标记关键数据点
- 标注来源：每个数据图表底部标注来源和年份

### 3.3 常用图表类型匹配
| 数据类型 | 推荐图表 | 说明 |
|---------|---------|------|
| 趋势/时间序列 | 折线图 | 简洁线条，标注关键节点 |
| 占比/构成 | 横向条形图 | 禁用饼图（3D 饼图严格禁止） |
| 对比/排名 | 条形图 | 关键对比项用 accent 色高亮 |
| 相关性/分布 | 散点图 | 加趋势线和 R² |
| 流程/路径 | 时间轴/流程箭头 | 水平排列，颜色编码阶段 |

### 3.4 框架图规范
咨询常用框架图：
- **2×2 矩阵**（波士顿矩阵形式）— 横纵轴定义清晰
- **价值链** — 水平流程，区分主活动/支持活动
- **金字塔** — 结论在顶，论据在下
- **流程图** — 步骤清晰，箭头连接
- **树状图** — Issue tree 结构

所有框架图使用 theme 配色，不自创颜色。

---

## P4: QA 验收 — 麦肯锡标准

### 结构验收
- [ ] 整份 deck 围绕一个核心结论展开
- [ ] 叙事线符合 SCQA 框架
- [ ] 每个论点按 MECE 分解
- [ ] 页面组织逻辑连贯（Situation → Analysis → Recommendation）
- [ ] Executive Summary 覆盖所有核心发现

### 标题验收
- [ ] 每页标题是完整结论句（不是短语标签）
- [ ] 标题能在 3 秒内传达该页核心信息
- [ ] 标题与正文内容一致，不夸大

### 视觉验收
- [ ] Header 栏一致（位置、颜色、字号）
- [ ] 所有颜色来自 theme 配色素
- [ ] 无 3D 效果、无多余装饰
- [ ] 数据图表标注来源和年份
- [ ] 页码连续、位置统一
- [ ] 连续页无相同布局

### 内容验收
- [ ] 所有数据有来源标注
- [ ] 关键数据在图表中高亮
- [ ] 建议方案有可操作性和时间节点
- [ ] 无冗余页面（每页传递一个信息）

---

## 最小可用 Prompt

```
用 slides 和 imagegen 创建一份麦肯锡风格的演示文稿。

需求：{主题/需求描述}
受众：{受众角色}
页数建议：{8-15 页}
已有数据/报告：{如有}

请按以下流程执行：
1) 先输出叙事结构（SCQA + 页面规划）
2) 确认后再逐页生成
3) 每页标题必须是结论句
4) 使用麦肯锡经典蓝配色方案
5) 数据图表标注来源
6) 最终输出 .pptx + 生成脚本
```

## 依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| pptxgenjs | PptxGenJS — 生成 PPTX | `npm install -g pptxgenjs` |
| markitdown | 读取已有 PPTX | `pip install "markitdown[pptx]"` |
