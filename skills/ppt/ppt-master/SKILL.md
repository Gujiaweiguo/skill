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
4. 运行 `node compile.js`
5. 输出 `slides/output/presentation.pptx`
6. 如有需要，用 imageGen 补充视觉素材

### 3.6 PptxGenJS 关键陷阱

- **绝不复用选项对象** — PptxGenJS 会原地修改对象（如 shadow 值转 EMU）。用工厂函数生成新对象
- **createSlide 必须同步** — 不能是 async function
- **颜色不带 #** — `"FF0000"` 不是 `"#FF0000"`
- **正文不加粗** — bold 只用于标题和 heading
- **只用 theme 里的颜色** — 不要自己发明颜色

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

## 依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| pptxgenjs | PptxGenJS — 从零创建 PPTX | `npm install -g pptxgenjs` |
| markitdown | 读取已有 PPTX 内容 | `pip install "markitdown[pptx]"` |
