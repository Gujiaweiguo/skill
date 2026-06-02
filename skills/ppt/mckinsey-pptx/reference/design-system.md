# McKinsey PPT — 设计系统详细参考

## 配色方案库

### 经典麦肯锡蓝（McKinsey Classic）
最通用的咨询风格，适用于战略项目、管理咨询、行业研究。

```javascript
{ primary: "003c71",    // 麦肯锡深蓝
  secondary: "1a1a1a",  // 正文黑色
  accent: "0077b6",     // 强调蓝
  light: "e8edf2",      // 浅灰蓝底
  bg: "ffffff" }         // 白色
```

### 金融投资（Financial / IBD）
适用于投资分析、尽职调查、财务建模呈现。

```javascript
{ primary: "0a1628",    // 深蓝黑
  secondary: "1e293b",  // 深灰
  accent: "3b82f6",     // 亮蓝
  light: "f1f5f9",      // 极浅灰
  bg: "ffffff" }         // 白色
```

### 科技战略（Tech Strategy）
适用于数字化战略、科技行业分析。

```javascript
{ primary: "0f172a",    // 暗夜蓝
  secondary: "334155",  // 石板灰
  accent: "06b6d4",     // 青色强调
  light: "f0f9ff",      // 浅蓝底
  bg: "ffffff" }         // 白色
```

## Header 栏完整实现

```javascript
function addMcKinseyHeader(slide, theme, sectionTitle, pageNum, totalPages) {
  // 顶部全宽 header 栏
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.65,
    fill: { color: theme.primary }
  });
  
  // 标题文字（header 栏内）
  slide.addText(sectionTitle, {
    x: 0.4, y: 0.1, w: 6.5, h: 0.45,
    fontSize: 11, fontFace: "Arial",
    color: "FFFFFF", bold: false
  });
  
  // 右侧装饰元素（可选细分标签）
  slide.addText("CONFIDENTIAL", {
    x: 7.5, y: 0.1, w: 2.1, h: 0.45,
    fontSize: 8, fontFace: "Arial",
    color: "FFFFFF", align: "right",
    transparency: 40
  });
}

function addMcKinseyFooter(slide, theme, source, pageNum) {
  // 底部细线分隔
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 5.15, w: 9.2, h: 0.01,
    fill: { color: theme.light }
  });
  
  // 来源
  if (source) {
    slide.addText(source, {
      x: 0.4, y: 5.2, w: 7.5, h: 0.3,
      fontSize: 7.5, fontFace: "Arial",
      color: theme.secondary
    });
  }
  
  // 页码
  slide.addText(String(pageNum), {
    x: 8.5, y: 5.2, w: 1.1, h: 0.3,
    fontSize: 8.5, fontFace: "Arial",
    color: theme.accent, align: "right"
  });
}
```

## 页面布局模板

### Title Slide

```javascript
function createTitleSlide(pres, theme, reportTitle, subtitle, client, date) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  // 顶部色块装饰
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 0.12,
    fill: { color: theme.primary }
  });
  
  // 主标题
  slide.addText(reportTitle, {
    x: 0.8, y: 1.5, w: 8.4, h: 1.2,
    fontSize: 36, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 副标题
  slide.addText(subtitle, {
    x: 0.8, y: 2.7, w: 8.4, h: 0.6,
    fontSize: 20, fontFace: "Arial",
    color: theme.secondary
  });
  
  // 客户信息 + 日期
  slide.addText([{ text: client, options: { fontSize: 12, color: theme.secondary } },
                 { text: "\n" + date, options: { fontSize: 11, color: theme.accent } }], {
    x: 0.8, y: 4.2, w: 4, h: 0.7
  });
  
  // 底部装饰线
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.8, y: 5.0, w: 3, h: 0.04,
    fill: { color: theme.primary }
  });
  
  return slide;
}
```

### Executive Summary Slide

```javascript
function createExecSummarySlide(pres, theme, findings, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  addMcKinseyHeader(slide, theme, "Executive Summary", pageNum);
  
  // 核心结论（大字）
  slide.addText("核心结论", {
    x: 0.5, y: 0.9, w: 9, h: 0.4,
    fontSize: 16, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 关键发现列表
  const findingsText = findings.map((f, i) => 
    `${i + 1}. ${f}`
  ).join("\n\n");
  
  slide.addText(findingsText, {
    x: 0.5, y: 1.4, w: 9, h: 2.5,
    fontSize: 13, fontFace: "Arial",
    color: theme.secondary, lineSpacing: 22,
    valign: "top"
  });
  
  // 底部分隔线
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.2, w: 9, h: 0.01,
    fill: { color: theme.light }
  });
  
  // 建议行动（如有）
  slide.addText("建议下一步：", {
    x: 0.5, y: 4.4, w: 9, h: 0.3,
    fontSize: 11, fontFace: "Arial",
    color: theme.accent, bold: true
  });
  
  addMcKinseyFooter(slide, theme, null, pageNum);
  return slide;
}
```

### Content Slide with Header Bar

```javascript
function createContentSlide(pres, theme, headline, bodyItems, source, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  addMcKinseyHeader(slide, theme, "", pageNum);
  
  // 标题即结论
  slide.addText(headline, {
    x: 0.4, y: 0.8, w: 9.2, h: 0.5,
    fontSize: 18, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 分隔线
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.35, w: 9.2, h: 0.01,
    fill: { color: theme.light }
  });
  
  // 正文内容
  const bodyText = Array.isArray(bodyItems)
    ? bodyItems.map(item => `• ${item}`).join("\n\n")
    : bodyItems;
  
  slide.addText(bodyText, {
    x: 0.4, y: 1.5, w: 9.2, h: 3.4,
    fontSize: 13, fontFace: "Arial",
    color: theme.secondary, lineSpacing: 20,
    valign: "top"
  });
  
  addMcKinseyFooter(slide, theme, source, pageNum);
  return slide;
}
```

### Section Divider (全色背景)

```javascript
function createSectionSlide(pres, theme, sectionNum, sectionTitle, subtitle) {
  const slide = pres.addSlide();
  slide.background = { color: theme.primary };
  
  // 章节编号
  slide.addText(`0${sectionNum}`, {
    x: 0.8, y: 1.5, w: 2, h: 1.0,
    fontSize: 60, fontFace: "Arial",
    color: "FFFFFF", transparency: 30
  });
  
  // 章节标题
  slide.addText(sectionTitle, {
    x: 0.8, y: 2.8, w: 8.4, h: 0.8,
    fontSize: 30, fontFace: "Arial",
    color: "FFFFFF", bold: true
  });
  
  // 副标题/描述
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.8, y: 3.7, w: 8.4, h: 0.5,
      fontSize: 14, fontFace: "Arial",
      color: "FFFFFF", transparency: 20
    });
  }
  
  return slide;
}
```

### Chart / Data Slide

```javascript
function createChartSlide(pres, theme, headline, chartDescription, dataSource, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  addMcKinseyHeader(slide, theme, "", pageNum);
  
  // 标题即结论
  slide.addText(headline, {
    x: 0.4, y: 0.8, w: 9.2, h: 0.5,
    fontSize: 18, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 图表区域（占位注释：此处用 PptxGenJS 图表 API 或插入图片）
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.5, w: 5.8, h: 3.4,
    fill: { color: theme.light },
    line: { color: theme.light, width: 0 }
  });
  
  // 图表右侧 - 关键洞察
  slide.addText("关键洞察", {
    x: 6.5, y: 1.5, w: 3.1, h: 0.3,
    fontSize: 11, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  slide.addText(chartDescription, {
    x: 6.5, y: 1.9, w: 3.1, h: 3.0,
    fontSize: 11, fontFace: "Arial",
    color: theme.secondary, lineSpacing: 16,
    valign: "top"
  });
  
  addMcKinseyFooter(slide, theme, dataSource, pageNum);
  return slide;
}
```

### 2x2 Matrix Slide

```javascript
function createMatrixSlide(pres, theme, headline, matrixData, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  addMcKinseyHeader(slide, theme, "", pageNum);
  
  slide.addText(headline, {
    x: 0.4, y: 0.8, w: 9.2, h: 0.5,
    fontSize: 18, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 横纵轴标签
  const quadSize = 4.2;
  const startX = 0.8;
  const startY = 1.5;
  
  const quadrants = [
    { x: startX, y: startY, label: matrixData.q1 },
    { x: startX + quadSize + 0.2, y: startY, label: matrixData.q2 },
    { x: startX, y: startY + quadSize + 0.2, label: matrixData.q3 },
    { x: startX + quadSize + 0.2, y: startY + quadSize + 0.2, label: matrixData.q4 }
  ];
  
  quadrants.forEach(q => {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: q.x, y: q.y, w: quadSize, h: quadSize,
      fill: { color: theme.light },
      line: { color: theme.accent, width: 0.5 }
    });
    slide.addText(q.label, {
      x: q.x + 0.2, y: q.y + 0.2, w: quadSize - 0.4, h: quadSize - 0.4,
      fontSize: 11, fontFace: "Arial",
      color: theme.secondary, valign: "top",
      lineSpacing: 14
    });
  });
  
  addMcKinseyFooter(slide, theme, null, pageNum);
  return slide;
}
```

## 内容框架参考

### 常用分析框架

| 框架 | 用途 | 页面数 | 说明 |
|------|------|--------|------|
| SWOT | 战略定位 | 1-2 | 优势/劣势/机会/威胁 |
| Porter's Five Forces | 行业竞争分析 | 2-3 | 进入壁垒/替代品/供应商/买家/同业竞争 |
| Value Chain | 价值链分析 | 2-3 | 主活动+支持活动 |
| BCG Matrix | 业务组合分析 | 1-2 | 明星/现金牛/问号/瘦狗 |
| 3C | 战略三角 | 2-3 | 客户/竞争者/公司自身 |
| 7S | 组织诊断 | 2-3 | 战略/结构/系统/风格/技能/员工/共享价值观 |
| Ansoff Matrix | 增长策略 | 1 | 市场渗透/市场开发/产品开发/多元化 |

### 附录规范
- 附录页 Header 栏标注 "Appendix"
- 附录页码以 A-1, A-2 格式编号
- 每个附录页标注对应的正文页码
- 附录内容：详细数据表、方法论说明、访谈名单、参考文献
