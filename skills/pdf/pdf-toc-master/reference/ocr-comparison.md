# OCR 引擎选型参考

为 PDF TOC Master 选择 OCR 引擎的决策参考。重点评估中文识别能力。

---

## 横向对比

| 特性 | EasyOCR | PaddleOCR | Tesseract |
|------|---------|-----------|-----------|
| **安装复杂度** | 低（pip install） | 中（需装 PaddlePaddle 框架） | 中（需系统安装 + 语言包） |
| **中文识别** | ✅ 优秀（开箱即用） | ✅ 最佳（专为中文优化） | ⚠ 一般（需额外下载 chi_sim 包） |
| **模型大小** | ~100MB | ~150MB | ~50MB（中文包额外 ~100MB） |
| **GPU 加速** | 支持 | 支持 | 不支持 |
| **CPU 速度** | 中等 | 中等 | 快 |
| **竖排文字** | ⚠ 有限 | ✅ 支持 | ❌ 不支持 |
| **表格识别** | ❌ | ✅ | ❌ |
| **置信度输出** | ✅ 有 | ✅ 有 | ✅ 有 |
| **维护状态** | 活跃 | 活跃 | 稳定（更新较少） |
| **许可证** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

---

## 推荐方案

### 首选：EasyOCR

**理由：**
- 在本仓库中可通过 `uv sync --extra ocr` 安装，无需单独手工配环境
- 开箱支持 `ch_sim`（简体中文）+ `en`（英文/数字）
- 准确率 > 90% 足够处理目录页
- 置信度评分可用于后处理过滤

**安装：**
```bash
cd skills/pdf/pdf-toc-master
uv sync --extra ocr
```

**使用：**
```python
import easyocr
import torch

reader = easyocr.Reader(['ch_sim', 'en'], gpu=torch.cuda.is_available())
results = reader.readtext(image_array)     # 返回 [(bbox, text, confidence), ...]
```

### 备选：PaddleOCR

**适合场景：**
- 中文识别率要求极高（> 95%）
- 需要处理竖排中文
- 能接受更重的依赖

**安装：**
```bash
pip install paddlepaddle paddleocr
```

### 兜底：Tesseract

**适合场景：**
- 系统已安装 tesseract
- CPU 速度要求高
- 英语 PDF 为主，中文偶发

**安装：**
```bash
# 系统安装
apt-get install tesseract-ocr tesseract-ocr-chi-sim

# Python 包
pip install pytesseract
```

---

## 针对 PDF TOC 的实测建议

### 测试结果预期（中文书籍目录）

| OCR 引擎 | 数字识别 | 中文标题 | 排版误识 | 速度（3 页目录） |
|---------|---------|---------|---------|---------------|
| EasyOCR | ✅ 高 | ✅ 高 | ⚠ 偶尔多字 | ~10s |
| PaddleOCR | ✅ 很高 | ✅ 很高 | ✅ 少 | ~10s |
| Tesseract | ⚠ 中等 | ⚠ 中等 | ⚠ 行合并错误多 | ~3s |

### 关键优化点

1. **提高 dpi**：pdf2image 时用 300-400 dpi 显著提高识别率
2. **二值化**：对 OCR 图片做自适应二值化可减少噪声
3. **版面分析**：目录常为双栏排版，OCR 后需要按阅读顺序重排行
4. **词典约束**：歌曲名通常为 2-6 个中文字，可用长度约束过滤

### 降级策略

如果用户环境没有安装任何 OCR 引擎：

1. 提示安装 EasyOCR（推荐）：`cd skills/pdf/pdf-toc-master && uv sync --extra ocr`
2. 对于文字版 PDF，直接走文本提取路径（不需要 OCR）
3. 仅扫描版 PDF 需要 OCR，可以提前检测并提示
