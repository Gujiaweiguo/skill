# Frontend Slides — 设计系统详细参考

## 配色方案库

### 深色演讲（Dark Conference）
GitHub Dark 系配色，适合技术大会、Live Demo、线下 Meetup。

```javascript
{ primary: "0d1117",    // 背景深色
  secondary: "c9d1d9",  // 正文浅灰
  accent: "58a6ff",     // 亮蓝强调
  light: "21262d",      // 卡片/代码块背景
  bg: "0d1117" }         // 整体背景
```

### 浅色分享（Light Tech）
GitHub Light 系配色，适合内部分享、培训、文档说明。

```javascript
{ primary: "1b1f23",    // 标题深色
  secondary: "24292f",  // 正文
  accent: "0969da",     // GitHub Blue
  light: "f6f8fa",      // 代码块背景
  bg: "ffffff" }         // 白色
```

### 现代渐变（Modern Gradient）
深色 + 亮色强调，适合产品发布、技术品牌宣传。

```javascript
{ primary: "1a1a2e",    // 深紫黑
  secondary: "e0e0e0",  // 浅色正文
  accent: "e94560",     // 珊瑚红强调
  light: "16213e",      // 卡片背景
  bg: "0f3460" }         // 中蓝背景
```

### 清新极简（Minimal Clean）
高可读性配色，适合技术文档、培训手册、新人 onboarding。

```javascript
{ primary: "2c3e50",    // 深蓝灰
  secondary: "34495e",  // 中灰
  accent: "1abc9c",     // 绿松石
  light: "ecf0f1",      // 浅灰背景
  bg: "ffffff" }         // 白色
```

### 暖色分享（Warm Tech）
低视觉疲劳，适合长时间培训、工作坊。

```javascript
{ primary: "3e2723",    // 深棕
  secondary: "4e342e",  // 中棕
  accent: "ff7043",     // 橙色强调
  light: "efebe9",      // 暖灰背景
  bg: "fafafa" }         // 极浅灰
```

## 代码块设计与高亮

### 标准代码块
```javascript
// 圆角卡片 + 等宽字体 + 缩进保留
slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
  x: 0.5, y: 1.5, w: 9, h: 2.8,
  fill: { color: theme.light },
  line: { color: theme.accent, width: 0.5 },
  rectRadius: 0.08
});

slide.addText(codeContent, {
  x: 0.7, y: 1.6, w: 8.6, h: 2.6,
  fontSize: 11, fontFace: "Consolas",
  color: theme.secondary, lineSpacing: 15,
  valign: "top"
});
```

### 行高亮标记
对于关键代码行，在左侧添加标记：

```javascript
// 高亮行标记（左侧竖条或小色块）
const highlightLines = [3, 5, 7]; // 行号从 1 开始
highlightLines.forEach(lineNum => {
  const lineY = 1.6 + (lineNum - 1) * 0.3; // 根据行间距计算
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.55, y: lineY, w: 0.04, h: 0.2,
    fill: { color: theme.accent }
  });
});
```

### 代码行号
```javascript
// 添加行号（可选，代码行较多时）
const totalLines = codeContent.split('\n').length;
let lineNumbers = '';
for (let i = 1; i <= totalLines; i++) {
  lineNumbers += i + '\n';
}
slide.addText(lineNumbers, {
  x: 0.65, y: 1.6, w: 0.3, h: 2.6,
  fontSize: 10, fontFace: "Consolas",
  color: theme.accent, align: "right",
  transparency: 50
});
```

## 页面布局模板

### Title Slide（深色大会风格）

```javascript
function createTitleSlide(pres, theme, talkTitle, speaker, event, date) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  // 装饰线条
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.2, w: 2, h: 0.05,
    fill: { color: theme.accent }
  });
  
  // 标题
  slide.addText(talkTitle, {
    x: 0.5, y: 1.5, w: 9, h: 1.5,
    fontSize: 38, fontFace: "Arial",
    color: theme.secondary, bold: true
  });
  
  // 演讲者 + 场合
  slide.addText([{ text: speaker, options: { fontSize: 16, color: theme.accent, bold: true } },
                 { text: `\n${event} · ${date}`, options: { fontSize: 12, color: theme.secondary } }], {
    x: 0.5, y: 3.5, w: 9, h: 0.8
  });
  
  return slide;
}
```

### Code Slide

```javascript
function createCodeSlide(pres, theme, title, code, explanation, lang, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  // 标题
  slide.addText(title, {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 语言标签
  slide.addText(lang || "JS", {
    x: 8.5, y: 0.4, w: 1, h: 0.3,
    fontSize: 9, fontFace: "Consolas",
    color: theme.accent, align: "right"
  });
  
  // 代码块
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.1, w: 9, h: 3.0,
    fill: { color: theme.light },
    rectRadius: 0.08
  });
  
  slide.addText(code, {
    x: 0.7, y: 1.2, w: 8.6, h: 2.8,
    fontSize: 11, fontFace: "Consolas",
    color: theme.secondary, lineSpacing: 15,
    valign: "top"
  });
  
  // 说明文字
  if (explanation) {
    slide.addText(explanation, {
      x: 0.5, y: 4.3, w: 9, h: 0.6,
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

### Concept Slide（概念说明）

```javascript
function createConceptSlide(pres, theme, title, definition, details, icon, pageNum) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  slide.addText(title, {
    x: 0.5, y: 0.3, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  // 核心定义（大白话一句话）
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 1.1, w: 9, h: 1.0,
    fill: { color: theme.light },
    rectRadius: 0.08
  });
  
  slide.addText(definition, {
    x: 0.7, y: 1.2, w: 8.6, h: 0.8,
    fontSize: 16, fontFace: "Arial",
    color: theme.accent, valign: "middle"
  });
  
  // 详情要点
  if (details && details.length > 0) {
    const points = details.map(d => `• ${d}`).join('\n\n');
    slide.addText(points, {
      x: 0.5, y: 2.4, w: 9, h: 2.4,
      fontSize: 14, fontFace: "Arial",
      color: theme.secondary, lineSpacing: 20,
      valign: "top"
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

### Agenda Slide

```javascript
function createAgendaSlide(pres, theme, items, totalDuration) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  slide.addText("Agenda", {
    x: 0.5, y: 0.3, w: 9, h: 0.7,
    fontSize: 30, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  const startY = 1.3;
  items.forEach((item, i) => {
    const y = startY + i * 0.7;
    
    // 编号
    slide.addShape(pres.shapes.OVAL, {
      x: 0.8, y: y + 0.1, w: 0.35, h: 0.35,
      fill: { color: theme.accent }
    });
    slide.addText(String(i + 1), {
      x: 0.8, y: y + 0.1, w: 0.35, h: 0.35,
      fontSize: 12, fontFace: "Arial",
      color: "FFFFFF", align: "center", valign: "middle",
      bold: true
    });
    
    // 标题
    slide.addText(item.title, {
      x: 1.4, y, w: 6, h: 0.35,
      fontSize: 16, fontFace: "Arial",
      color: theme.primary, valign: "middle"
    });
    
    // 时长
    if (item.duration) {
      slide.addText(item.duration, {
        x: 7.5, y, w: 2, h: 0.35,
        fontSize: 12, fontFace: "Arial",
        color: theme.accent, align: "right", valign: "middle"
      });
    }
    
    // 分隔线
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: y + 0.55, w: 8.7, h: 0.005,
      fill: { color: theme.light }
    });
  });
  
  if (totalDuration) {
    slide.addText(`总计: ${totalDuration}`, {
      x: 7.5, y: 4.5, w: 2, h: 0.3,
      fontSize: 11, fontFace: "Arial",
      color: theme.secondary, align: "right"
    });
  }
  
  return slide;
}
```

### QA / Ending Slide

```javascript
function createQASlide(pres, theme, contactInfo, resources) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };
  
  slide.addText("Q&A", {
    x: 0.5, y: 1.0, w: 9, h: 1.0,
    fontSize: 48, fontFace: "Arial",
    color: theme.primary, bold: true
  });
  
  slide.addText("Thanks! 🙌", {
    x: 0.5, y: 2.0, w: 9, h: 0.8,
    fontSize: 24, fontFace: "Arial",
    color: theme.accent
  });
  
  if (contactInfo) {
    slide.addText(contactInfo, {
      x: 0.5, y: 3.2, w: 9, h: 0.5,
      fontSize: 14, fontFace: "Arial",
      color: theme.secondary
    });
  }
  
  if (resources) {
    slide.addText(resources, {
      x: 0.5, y: 3.8, w: 9, h: 0.8,
      fontSize: 11, fontFace: "Arial",
      color: theme.secondary, lineSpacing: 16
    });
  }
  
  return slide;
}
```

## 通用工具函数

```javascript
// 页码
function addPageNumber(slide, theme, num) {
  slide.addText(String(num), {
    x: 9, y: 5.2, w: 0.6, h: 0.3,
    fontSize: 10, fontFace: "Arial",
    color: theme.accent, align: "right"
  });
}

// 章节标签（左上角）
function addSectionLabel(slide, theme, label) {
  slide.addText(label, {
    x: 0.5, y: 0.1, w: 4, h: 0.25,
    fontSize: 10, fontFace: "Arial",
    color: theme.accent
  });
}

// 页面标题
function addSlideTitle(slide, theme, title) {
  slide.addText(title, {
    x: 0.5, y: 0.35, w: 9, h: 0.6,
    fontSize: 26, fontFace: "Arial",
    color: theme.primary, bold: true
  });
}
```
