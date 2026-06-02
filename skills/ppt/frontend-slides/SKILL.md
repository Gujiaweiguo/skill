---
name: frontend-slides
description: >
  前端与技术分享幻灯片创作 Skill。基于 slides + imagegen 方案，
  专为技术演讲、内部分享、架构评审、团队周会等场景设计。
  支持代码高亮、架构图示意、性能数据图表、API 演示等前端开发
  常见内容类型。通过 PptxGenJS 生成可继续编辑的 .pptx 文件。
  适合技术分享、技术大会演讲、团队内部培训、开源项目介绍、
  Code Review 总结、技术方案评审、Sprint 回顾等场景。
  触发场景："帮我做一份技术分享的PPT"、"前端技术演讲"、"团队内部分享"、
  "技术会议 slides"、"code review 总结"、"架构方案评审"、
  "技术方案演示"、"sprint 回顾 PPT"、"技术培训课件"、
  "开源项目介绍"、"前端技术选型对比"、"技术大会演讲"。
  当用户提供技术主题、代码片段、架构图草稿并要求做成演示文稿时触发此 skill。
compatibility: >
  Requires Node.js + pptxgenjs for .pptx generation.
  Requires web_search / web_fetch for content research.
  Requires imageGen for visual material supplementation.
  Degrades gracefully: text-only outline if pptxgenjs unavailable.
---

# Frontend Slides — 技术演讲与前端分享幻灯片创作

专为前端和技术场景设计的演示文稿 Skill，兼顾技术严谨性与视觉表达。

## 设计理念

### 技术演讲三大原则
1. **代码即内容** — 代码块是核心内容载体，保持语法高亮和可读性
2. **一概念一页** — 每个技术概念/API/模式单独一页，不多页混讲
3. **渐进式揭示** — 复杂概念用多页递进，不在单页堆砌

### 常见场景与基调

| 场景 | 色调 | 风格特征 |
|------|------|---------|
| 技术大会演讲 | 深色背景 + 亮色强调 | 冲击力强、大字、少文字 |
| 内部分享/培训 | 浅色/白底 + 品牌色 | 可读性优先、适中信息密度 |
| 架构评审 | 浅色底 + 结构化 | 图表多、层次清晰、严谨 |
| 开源项目介绍 | 项目色 + 深色/浅色均可 | 品牌化、社区感 |
| Sprint 回顾 | 轻松色调 | 简洁、要点化、氛围轻松 |

---

## P0: 环境检测与任务分类

### 环境检测
```
1. Node.js + pptxgenjs 可用? → 可生成 .pptx
2. web_search / web_fetch 可用? → 可做技术调研
3. imageGen 可用? → 可生成架构示意/封面
4. markitdown 可用? → 可读取已有 PPTX
```

### 任务类型
| 输入类型 | 处理方式 |
|---------|---------|
| 技术主题 + 要点 → 新建 | 规划结构 → 研究补充 → 生成 |
| 代码/仓库 → 转演示 | 提取关键架构/API → 按主题组织 |
| 已有 PPT → 改技术风格 | 分析 → 重构 → 生成 |
| 纯技术概念讲解 | 分解知识点 → 渐进式页面 |

---

## P1: 内容结构规划

### 1.1 技术演讲典型结构

```
┌─ 开场 (1-2页)
│   Title / 自我介绍 + 大纲
│
├─ 背景 (1-2页)
│   为什么讲这个 / 现状与问题
│
├─ 核心内容 (3-8页)
│   概念介绍 / 关键 API / 架构设计
│   代码示例 / 性能数据 / 前后对比
│
├─ 最佳实践 (1-2页)
│   经验总结 / 踩坑记录 / 建议
│
└─ 结尾 (1-2页)
    总结 / Q&A / 联系方式 / 资源链接
```

### 1.2 页面类型

| 类型 | 用途 | 内容特点 |
|------|------|---------|
| **Title** | 开场定调 | 标题 + 演讲者 + 场合 + 日期 |
| **Agenda** | 演讲大纲 | 章节列表，带时间分配建议 |
| **Concept** | 技术概念讲解 | 定义 + 图示 + 要点，避免大段文字 |
| **Code** | 代码展示 | 代码块 + 关键行高亮 + 说明 |
| **Architecture** | 架构/流程图 | 图示意 + 关键组件说明 |
| **Data** | 性能/数据 | 数据图表 + 关键指标高亮 |
| **Comparison** | 技术选型对比 | 表格/并列对比，带推荐标注 |
| **Best Practice** | 经验总结 | 要点列表 + 代码示例 |
| **QA** | 结尾 | Q&A + 联系方式 + 资源 |

### 1.3 代码高亮规则
- 代码块使用等宽字体（Consolas / Fira Code / Courier New）
- 代码段 ≤ 25 行，超过则分段展示
- 关键行用 accent 色高亮标注
- 代码上方/下方附加 1-2 句说明（而非大段注释）

---

## P2: 设计决策 — 技术风格视觉

### 2.1 配色方案

#### 深色演讲（Dark Conference — 推荐技术大会）
```javascript
{ primary: "0d1117",    // GitHub Dark 背景
  secondary: "c9d1d9",  // 正文浅灰
  accent: "58a6ff",     // 亮蓝强调 - 代码高亮/链接
  light: "21262d",      // 深灰卡片 - 代码块背景
  bg: "0d1117" }         // 整体背景
```

#### 浅色分享（Light Tech — 推荐内部分享）
```javascript
{ primary: "1b1f23",    // 标题深色
  secondary: "24292f",  // 正文
  accent: "0969da",     // GitHub Blue - 强调
  light: "f6f8fa",      // 浅灰 - 代码块背景
  bg: "ffffff" }         // 白色背景
```

#### 现代渐变（Modern Gradient — 技术大会备选）
```javascript
{ primary: "1a1a2e",    // 深紫黑
  secondary: "e0e0e0",  // 正文浅色
  accent: "e94560",     // 珊瑚红强调
  light: "16213e",      // 深蓝卡片
  bg: "0f3460" }         // 中蓝背景
```

#### 清新极简（Minimal Clean — 培训/文档类）
```javascript
{ primary: "2c3e50",    // 深蓝灰
  secondary: "34495e",  // 中灰
  accent: "1abc9c",     // 绿松石强调
  light: "ecf0f1",      // 浅灰背景
  bg: "ffffff" }         // 白色
```

### 2.2 版式规范

#### 页面布局
```
┌──────────────────────────────────────┐
│ 左上角: 章节标签（小字，accent色）    │
│ 右上角: 页码                          │
├──────────────────────────────────────┤
│                                      │
│  页面标题（24-30pt，加粗）            │
│                                      │
│  ┌─ 核心内容区域 ─────────────────┐  │
│  │  代码 / 图示 / 要点 / 架构图    │  │
│  │                                 │  │
│  └─────────────────────────────────┘  │
│                                      │
│  底部: 脚注/关键提示（小字，可选）    │
└──────────────────────────────────────┘
```

#### 排版规范
| 层级 | 字号(pt) | 加粗 | 颜色 | 字体 |
|------|---------|------|------|------|
| 页面标题 | 24-30 | 是 | primary | Arial / Microsoft YaHei |
| 正文要点 | 16-20 | 否 | secondary | Arial / Microsoft YaHei |
| 代码文字 | 10-14 | 否 | accent | Consolas / Fira Code |
| 图表示例 | 14-16 | 否 | secondary | Arial |
| 章节标签 | 10-12 | 否 | accent | Arial |
| 页码 | 9-11 | 否 | accent | Arial |
| 脚注/来源 | 8-10 | 否 | secondary | Arial |

#### 代码块样式
```javascript
// 代码建议使用独立的 addText 区域，背景色 = theme.light
// 等宽字体，保留缩进，关键行用 theme.accent 标注或添加标记
slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 0.5, y: 1.8, w: 9, h: 2.5,
  fill: { color: theme.light },
  rectRadius: 0.1
});

slide.addText(codeSnippet, {
  x: 0.7, y: 1.95, w: 8.6, h: 2.2,
  fontSize: 12, fontFace: "Consolas",
  color: theme.secondary, lineSpacing: 16,
  valign: "top"
});
```

---

## P3: 常见内容模板

### 3.1 技术选型对比页

```javascript
function createComparisonSlide(pres, theme, title, items, recommendation, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  // 标题
  slide.addText(title, {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 对比表格用形状绘制
  const headers = ["", "方案 A", "方案 B"];
  const startY = 1.2;
  
  // 表头
  headers.forEach((h, i) => {
    slide.addText(h, {
      x: 0.5 + i * 3.2, y: startY, w: 3, h: 0.4,
      fontSize: 12, fontFace: "Arial",
      color: theme.primary, bold: true
    });
  });
  
  // 行
  items.forEach((item, rowIdx) => {
    const y = startY + 0.5 + rowIdx * 0.5;
    const cols = [item.label, item.a, item.b];
    cols.forEach((val, colIdx) => {
      slide.addText(val, {
        x: 0.5 + colIdx * 3.2, y, w: 3, h: 0.4,
        fontSize: 11, fontFace: "Arial",
        color: colIdx === 0 ? theme.primary : theme.secondary
      });
    });
    // 行分隔线
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: y + 0.45, w: 9.5, h: 0.005,
      fill: { color: theme.light }
    });
  });
  
  // 推荐标注
  if (recommendation) {
    slide.addText(`✅ 推荐: ${recommendation}`, {
      x: 0.5, y: startY + 0.5 + items.length * 0.5 + 0.3,
      w: 9, h: 0.4,
      fontSize: 13, fontFace: "Arial",
      color: theme.accent, bold: true
    });
  }
  
  // 页码
  slide.addText(String(pageNum), {
    x: 9, y: 5.2, w: 0.6, h: 0.3,
    fontSize: 10, fontFace: "Arial",
    color: theme.accent, align: "right"
  });
  
  return slide;
}
```

### 3.2 架构图页

```javascript
function createArchitectureSlide(pres, theme, title, components, connections) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  // 标题
  slide.addText(title, {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 以水平布局放置组件方块
  const boxW = 1.8;
  const boxH = 1.0;
  const totalW = components.length * (boxW + 0.3) - 0.3;
  const startX = (10 - totalW) / 2;
  
  components.forEach((comp, i) => {
    const x = startX + i * (boxW + 0.3);
    const y = 2.0;
    
    // 组件方块
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: boxW, h: boxH,
      fill: { color: theme.light },
      line: { color: theme.accent, width: 1 },
      rectRadius: 0.1
    });
    
    // 组件名称
    slide.addText(comp.name, {
      x, y: y + 0.1, w: boxW, h: 0.4,
      fontSize: 11, fontFace: "Arial",
      color: theme.primary, bold: true,
      align: "center"
    });
    
    // 组件描述
    slide.addText(comp.desc, {
      x: x + 0.1, y: y + 0.5, w: boxW - 0.2, h: 0.4,
      fontSize: 8, fontFace: "Arial",
      color: theme.secondary, align: "center"
    });
    
    // 连接箭头（两个组件之间）
    if (i < components.length - 1) {
      const arrowX = x + boxW + 0.05;
      slide.addShape(pres.shapes.RIGHT_ARROW, {
        x: arrowX, y: y + boxH / 2 - 0.1, w: 0.2, h: 0.2,
        fill: { color: theme.accent }
      });
    }
  });
  
  // 补充说明
  if (connections) {
    slide.addText(connections, {
      x: 0.5, y: 3.5, w: 9, h: 1.2,
      fontSize: 12, fontFace: "Arial",
      color: theme.secondary, lineSpacing: 18
    });
  }
  
  return slide;
}
```

### 3.3 性能数据页

```javascript
function createDataSlide(pres, theme, title, dataPoints, insight, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  slide.addText(title, {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 大数字展示关键指标
  dataPoints.forEach((dp, i) => {
    const cols = Math.min(dataPoints.length, 3);
    const colW = 2.8;
    const startX = (10 - cols * colW - (cols - 1) * 0.3) / 2;
    const row = Math.floor(i / 3);
    const col = i % 3;
    const x = startX + col * (colW + 0.3);
    const y = 1.3 + row * 1.6;
    
    // 数字卡片
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: colW, h: 1.4,
      fill: { color: theme.light },
      rectRadius: 0.08
    });
    
    // 大数字
    slide.addText(dp.value, {
      x, y: y + 0.1, w: colW, h: 0.7,
      fontSize: 36, fontFace: "Arial",
      color: theme.accent, bold: true,
      align: "center"
    });
    
    // 指标名
    slide.addText(dp.label, {
      x, y: y + 0.85, w: colW, h: 0.4,
      fontSize: 11, fontFace: "Arial",
      color: theme.secondary, align: "center"
    });
  });
  
  // 底部洞察
  if (insight) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 4.2, w: 9, h: 0.005,
      fill: { color: theme.light }
    });
    slide.addText(insight, {
      x: 0.5, y: 4.4, w: 9, h: 0.5,
      fontSize: 13, fontFace: "Arial",
      color: theme.primary
    });
  }
  
  slide.addText(String(pageNum), {
    x: 9, y: 5.2, w: 0.6, h: 0.3,
    fontSize: 10, fontFace: "Arial",
    color: theme.accent, align: "right"
  });
  
  return slide;
}
```

### 3.4 代码对比页（Before/After）

```javascript
function createCodeComparisonSlide(pres, theme, title, beforeCode, afterCode, insight, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  slide.addText(title, {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // Before
  slide.addText("Before", {
    x: 0.5, y: 1.1, w: 4.3, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: "#d73a49", bold: true // GitHub red tone
  });
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.4, w: 4.3, h: 2.5,
    fill: { color: theme.light },
    rectRadius: 0.08
  });
  slide.addText(beforeCode, {
    x: 0.6, y: 1.5, w: 4.1, h: 2.3,
    fontSize: 10, fontFace: "Consolas",
    color: theme.secondary, lineSpacing: 14
  });
  
  // After
  slide.addText("After", {
    x: 5.2, y: 1.1, w: 4.3, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: "#22863a", bold: true // GitHub green tone
  });
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 5.2, y: 1.4, w: 4.3, h: 2.5,
    fill: { color: theme.light },
    rectRadius: 0.08
  });
  slide.addText(afterCode, {
    x: 5.3, y: 1.5, w: 4.1, h: 2.3,
    fontSize: 10, fontFace: "Consolas",
    color: theme.primary, lineSpacing: 14
  });
  
  // 洞察
  if (insight) {
    slide.addText(insight, {
      x: 0.5, y: 4.1, w: 9, h: 0.6,
      fontSize: 13, fontFace: "Arial",
      color: theme.accent
    });
  }
  
  slide.addText(String(pageNum), {
    x: 9, y: 5.2, w: 0.6, h: 0.3,
    fontSize: 10, fontFace: "Arial",
    color: theme.accent, align: "right"
  });
  
  return slide;
}
```

---

## P4: QA 验收

### 内容验收
- [ ] 每页传达一个技术概念/观点
- [ ] 代码块可读（≤ 25 行，关键行高亮）
- [ ] 技术术语准确一致
- [ ] 无过度简化导致的技术事实扭曲

### 视觉验收
- [ ] 配色符合所选方案（不自创颜色）
- [ ] 代码使用等宽字体
- [ ] 深色模式和浅色模式不混用
- [ ] 架构图组件间距一致
- [ ] 数据指标使用大数字突出显示
- [ ] 页码位置统一

### 演讲适配验收
- [ ] 页面文字密度适中（非满屏文字）
- [ ] 关键信息可以用大字一眼获取
- [ ] 渐进式复杂概念拆页合理
- [ ] 结尾包含 Q&A 或联系方式

---

## 最小可用 Prompt

```
用 slides 和 imagegen 创建一份技术分享幻灯片。

主题：{技术主题}
场景：{技术大会 / 内部分享 / 培训 / 架构评审}
受众：{前端开发者 / 全栈 / 管理层 / 初学者}
页数建议：{8-20 页}
核心内容：{技术要点 / 代码示例 / 架构描述}

请按以下流程执行：
1) 先输出页面规划和内容结构
2) 确认后再逐页生成
3) 代码块使用等宽字体，关键行高亮
4) 选择适合场景的配色方案
5) 最终输出 .pptx + 生成脚本
```

## 依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| pptxgenjs | PptxGenJS — 生成 PPTX | `npm install -g pptxgenjs` |
| markitdown | 读取已有 PPTX | `pip install "markitdown[pptx]"` |
