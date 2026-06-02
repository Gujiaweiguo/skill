# PPT Master — 工作流参考

## 完整流程速查

### 修改已有 PPT

```
步骤 1: markitdown 读取 PPTX 内容结构
步骤 2: 检查尺寸、宽高比、母版、字体、颜色、边距
步骤 3: 设计决策（保持现有风格）
步骤 4: 生成修改脚本 → pptxgenjs
步骤 5: 用 imageGen 补充视觉素材（如需要）
步骤 6: QA 验收
```

### 从大纲新建 PPT

```
步骤 1: 解析大纲 → 规划页面结构
步骤 2: 需要研究的观点 → web_search
步骤 3: 设计决策（配色、版式）
步骤 4: 逐页生成 → pptxgenjs
步骤 5: imageGen 补充封面 / 插图
步骤 6: QA 验收
```

### 从文章转 PPT

```
步骤 1: 阅读文章 → 提炼 3-8 个核心观点
步骤 2: 每个观点分配一个页面
步骤 3: 设计决策（根据主题和受众）
步骤 4: 生成 → slides + imagegen
步骤 5: QA 验收
```

---

## ImageGen 使用边界

### ✅ 适合生成
- 抽象插图
- 封面视觉 / 背景纹理
- 装饰性图形元素
- 概念图（如"数字化转型"的可视化表达）

### ❌ 不适合替代
- 公司 logo / 品牌标识（使用现有资产）
- 图标系统（使用现有图标库）
- 原生图表（使用 pptxgenjs 图表 API）
- 产品截图 / 真实照片（使用实际素材）

### Prompt 模板
```
生成一张商务风格的抽象插图，用于{页面主题/场景}。
风格：简洁、专业、使用{配色方案名}色调。
包含元素：{具体视觉元素}
尺寸：16:9 宽屏
不要包含文字。
```

---

## 交付物清单

每次完成后的标准交付物：

- `presentation.pptx` — 最终可编辑的 PPT 文件
- `slides/*.js` — 每页的生成脚本（可复现）
- `slides/compile.js` — 总编排脚本
- `slides/output/` — 输出目录
- 所用插图资产（imageGen 生成的图片文件）
- 可复用的 Prompt（适用于后续类似场景）

---

## 环境依赖检查

```bash
# 检查 pptxgenjs
node -e "require('pptxgenjs'); console.log('pptxgenjs OK')"

# 检查 markitdown
python3 -c "from markitdown import MarkItDown; print('markitdown OK')"
```

如缺少依赖，在执行过程中安装即可。
