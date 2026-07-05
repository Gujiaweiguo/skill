# ppt-master Troubleshooting

ppt-master / PptxGenJS 渲染层已知坑与修复方案。新增坑请按"症状 → 根因 → 修复 → 验证"四段式追加。

---

## 1. 多行文本框（`text\nline2\nline3`）转 PDF 后正文消失或挤压

### 症状

`addText` 用单字符串 + `\n` 拼接多行（常见于卡片正文、表格单元格、路线图 bullet），生成 `.pptx` 后：

- PowerPoint 直接打开：多数情况能看见，但行间距/基线异常。
- LibreOffice 转 PDF（`libreoffice --headless --convert-to pdf`）：**部分或全部正文行消失**，只剩标题或徽章；视觉检查看起来"卡片是空的"。
- 即使 `pptx-render-fix` 模块已 patch，仍会发生。

典型出现位置：

- 竞对卡片：标题 + 威胁徽章 + 三行正文，正文整段消失。
- 表格行：每格 2-3 行内容，部分行不可见。
- 时间线/阶段卡片：阶段标题 + 时间 + 4 条 bullet，bullet 全部消失。
- 路线对比卡：标题 + 4-5 行属性，属性消失。

### 根因

PptxGenJS v4 的 `\n` 处理 + LibreOffice 渲染层 + `pptx-render-fix` 三者交互不稳定。`pptx-render-fix` 会拆分 `\n`，但拆分后的多个 `addText` 调用共享原始 `(x, y, w, h)`，导致行叠在同一 Y 位置或被裁出文本框。PowerPoint 容错强、LibreOffice 严格，所以同一文件在两个引擎表现不同。

### 修复：用独立 addText 行替代 `\n` 拼接

不要依赖 `\n`。写一个 `addStackedText` 辅助函数，每行独立 `addText`，自行控制 `y` 增量：

```javascript
function addStackedText(slide, lines, opts) {
  opts = opts || {};
  var lineH = opts.lineH || 0.28;
  for (var i = 0; i < lines.length; i++) {
    slide.addText(lines[i], {
      x: opts.x,
      y: opts.y + i * lineH,
      w: opts.w,
      h: opts.h || 0.24,
      fontSize: opts.fontSize || 9,
      fontFace: opts.fontFace || "Microsoft YaHei",
      bold: opts.bold || false,
      color: opts.color || theme.secondary,
      margin: 0,
      valign: opts.valign || "top"
    });
  }
}
```

调用方式：

```javascript
// 错误：\n 拼接
slide.addText("代表: " + reps + "\nAI能力: " + ai + "\n蓝联差异: " + gap, {
  x, y, w, h, lineSpacing: 1.4, ...
});

// 正确：独立 addText 行
addStackedText(slide, [
  "代表: " + reps,
  "AI能力: " + ai,
  "蓝联差异: " + gap
], { x, y, w, h: 0.24, fontSize: 9.5, color: theme.secondary, lineH: 0.31 });
```

### 验证

`node compile.js` 生成后，**必须用 LibreOffice 转 PDF 再 OCR/视觉检查**，不能只看 PPTX zip 完整性：

```bash
libreoffice --headless --convert-to pdf --outdir /tmp/ppt-qa output.pptx
pdftoppm -png -r 160 -f <slideN> -l <slideN> /tmp/ppt-qa/output.pdf /tmp/ppt-qa/slide
# 用 OCR 或图像检查工具确认每行正文可见、无重叠、无裁切
```

只检查 PPTX zip 完整性或 `node --check` **不能**发现这个坑——OOXML 结构合法，但渲染层丢字。

### 何时仍可用 `\n`

- 单行短文本（无 `\n`）不受影响。
- 仅在 PowerPoint 内使用、永不转 PDF 的场景可保留 `\n`，但仍建议统一改 `addStackedText` 避免后续踩坑。

---

## 2.5 代码绘制示意图（addShape）视觉质量参数

### 症状

用 `addShape`（rect/line/ellipse）代码绘制示意图（流程图/状态图/架构图/漏斗等）时，生成 PPTX 转 PDF 后：

- 色块内文字挤压，部分字看不到
- 色块之间间距过小，视觉拥挤
- 示意图整体不美观，缺乏层次感
- 右侧 PSV 文字与左侧示意图元素重叠

### 根因

PptxGenJS 的 `addShape` + `addText` 默认不留内边距，色块尺寸和文字字号没有最小约束。代码绘制时如果只按"逻辑布局"给坐标，不校验视觉可读性，就会挤压。

### 修复：用最小视觉参数约束

代码绘制示意图时，强制遵守以下最小参数：

| 参数 | 最小值 | 说明 |
|---|---|---|
| 色块间距 | ≥ 0.15 英寸 | 色块之间留白，避免拥挤 |
| 文字字号 | ≥ 10pt（一般文字）/ ≥ 12pt（关键标注）/ ≥ 14pt（示意图标题，加粗） | 字号过小转 PDF 后模糊 |
| 色块高度 | ≥ 0.5 英寸 | 确保文字有足够垂直空间 |
| 色块圆角 | radius ≥ 0.05 | 圆角矩形比直角更美观 |
| 左右版式分隔 | 左侧 x+w ≤ 6.5，右侧 x ≥ 6.7 | 避免左右元素重叠 |
| 右侧卡片段间距 | ≥ 0.2 英寸 | PSV 三段不挤 |
| 右侧每段卡片高度 | ≥ 0.9 英寸 | 确保文字不溢出 |

### 配色统一

示意图不要随意用颜色，统一用 theme 色系：
- 主色（标题/重点）：theme.primary
- 辅色（说明）：theme.secondary
- 强调（痛点/警告）：theme.accent
- 正向（达标/已租）：theme.green
- 浅底（卡片背景）：theme.light

### 验证

生成后用 LibreOffice 转 PDF，`pdftoppm` 抽取示意图页，用 OCR 或图像检查工具确认：
- 每个色块内文字完整可读
- 色块之间有清晰间距
- 左右版式无重叠
- 整体视觉层次分明

---

## 3. 检查清单（生成 PPT 后必跑）

1. `node compile.js` 成功。
2. `node --check compile.js` 通过（语法）。
3. PPTX zip 完整性：`unzip -t output.pptx`。
4. **LibreOffice 转 PDF 成功**：`libreoffice --headless --convert-to pdf`。
5. **重点页 OCR/视觉抽查**：正文可见、无重叠、无裁切、标签与正文有间距。
6. 页数与预期一致：`pdfinfo output.pdf | grep Pages`。

只做 1-3 会漏掉渲染层丢字；4-5 是必做项。
