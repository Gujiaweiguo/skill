---
name: pdf-toc-master
description: >
  PDF 目录书签生成 Skill。基于 pdf + ocr 方案，自动识别 PDF 目录结构
  （从已有目录页提取标题与页码，或从正文标题自动推断），嵌入可导航的
  分层书签（PDF Outline）以供点击跳转。支持扫描版与文字版 PDF。
  触发场景："给这个 PDF 生成目录书签"、"把目录提取出来做成可跳转的"、
  "给 PDF 加一个可导航的目录"、"PDF 没有书签，帮我加一下"、
  "帮我把这本书的目录做成点击跳转"、"提取这个 PDF 的目录结构"。
compatibility: >
  Requires Python 3.9+ and uv.
  Provides a `pyproject.toml` with pinned dependencies for deterministic setup.

  Quick start:
  ```bash
  cd skills/pdf/pdf-toc-master
  uv sync                  # install core deps (pypdf, pdf2image, Pillow)
  uv sync --extra ocr      # include easyocr for scanned PDFs

  # Extract TOC + per-page index, merge into one outline (recommended)
  uv run pdf-toc-extract input.pdf --offset 8 --toc-start 6 --toc-end 8 --gpu auto --mode merged
  ```

  Parameters:
  - `--offset N`     PDF page index = printed_page + N (critical for correct jumps)
  - `--toc-start M`  First page of TOC in PDF, 1-indexed
  - `--toc-end K`    Last page of TOC in PDF, 1-indexed
  - `--dpi N`        OCR resolution (default: 200)
  - `--gpu MODE`     EasyOCR device selection: `auto` / `on` / `off`

  System requirement: poppler-utils (for pdf2image)

  Requires at least one OCR engine for scanned PDFs:
  - easyocr (recommended, Chinese-ready out of the box)
  - pytesseract + tesseract-ocr + Chinese language pack
  - paddleocr (best Chinese accuracy but heavy)
  Degrades gracefully: text-based PDFs work without OCR.
---

# PDF TOC Master — PDF 目录书签生成 Agent Pipeline

基于 `pdf + ocr` 方案，用户给 PDF，Agent 去识别目录结构并嵌入可导航书签，你只管 Plan 和验收。

## Architecture

```
用户输入 PDF 文件路径
        ↓
P0: 环境检测 + 任务类型判断
        ↓
Lead Agent (你 — 总体规划与决策)
        │
  ┌─────┼─────┐
  │     │     │
  P1   P2    P3
  分析  提取  嵌入
  PDF   目录  书签
        │
        ↓
P4: QA 验收 + 交付
```

---

## P0: 环境检测与任务分类

### 0.1 环境检测

先设置 uv 环境（一次性）：
```bash
cd skills/pdf/pdf-toc-master
uv sync
# 如需 OCR 支持（扫描版 PDF）：
uv sync --all-extras
```

然后确认依赖就绪：
```
1. pypdf ≥ 6.0 可用?  →  PDF 读写与书签操作  (uv run python -c "from pypdf import PdfReader")
2. pdf2image 可用?    →  扫描版 PDF 转图片 (uv run python -c "import pdf2image")
3. OCR 引擎可用?       →  扫描版提取目录文字
   - easyocr (推荐)    →  uv run python -c "import easyocr"
   - pytesseract       →  uv run python -c "import pytesseract"
   - paddleocr         →  uv run python -c "import paddleocr"
4. CUDA 可用?          →  uv run python -c "import torch; print(torch.cuda.is_available())"
5. 参考脚本可用?       →  uv run pdf-toc-extract --help
```

### 0.2 任务类型判断

| 输入类型 | 处理方式 |
|---------|---------|
| **扫描版 PDF + 有目录页** | OCR 目录页 → 提取标题+页码 → 嵌入书签 |
| **文字版 PDF + 有目录页** | 文本提取 → 解析标题+页码 → 嵌入书签 |
| **文字版 PDF + 无目录页** | 遍历全文，按字号/字体聚类 → 自动推断章节 → 嵌入书签 |
| **扫描版 PDF + 无目录页** | 全文 OCR → NLP 识别章节标题 → 嵌入书签（慢，需用户确认） |
| **已有书签的 PDF** | 检查书签完整性，询问是否替换或补充 |

### 0.3 三种 CLI 模式（`--mode`）

| 模式 | 说明 | 速度 | 适用场景 |
|------|------|------|---------|
| **merged**（推荐） | TOC 干净标题 + 逐页索引补齐，每页都有书签 | 中（需 OCR 全部页面） | 日常使用，导航最完整 |
| **toc** | 只从目录页提取书签，标题最干净 | 最快（秒级） | 只需曲目/章节跳转，不需要逐页覆盖 |
| **index** | 每页 OCR 顶部文本作为书签，不依赖目录页 | 中 | 无目录页或目录页质量极差时 |

**选择建议**：优先 `merged`；如果只需要精简目录或 PDF 页数很多想省时间，用 `toc`；目录页完全不可用时回退 `index`。

---

## P1: PDF 分析

### 1.1 基础检测

```python
from pypdf import PdfReader

reader = PdfReader(pdf_path)
page_count = len(reader.pages)
metadata = reader.metadata
existing_outlines = reader.outline  # 是否已有书签
```

### 1.2 扫描版检测

取前 5 页 + 中段 3 页 + 末页，提取文本：
- 总文本 < 500 字符 → 判定为扫描版
- 扫描版 → 依赖 OCR | 文字版 → 直接文本提取

### 1.3 目录页定位

文字版 — 搜索关键词：
- 遍历页面文本，匹配 `目录` / `Contents` / `目錄` / `目次`
- 取最先出现的匹配页作为目录页范围起点

扫描版 — 图像特征检测：
- 在前 15%-20% 页面范围内检测「密集短行 + 右侧数字」的排版模式
- 这类页面大概率是目录页
- 若无法自动定位，提示用户指定目录页页码范围

### 1.4 页码偏移计算

印刷页码 ≠ PDF 页面索引（常见于扫描版，因封面/前言占页无编号）。

**计算方法（核心）：**

```
1. 取 TOC 中第 1-3 条含页码的条目
2. 在 PDF 中抽样定位这些条目的实际页面
3. 计算 offset = pdf_page_index - printed_page
4. 验证：用第 4-5 条条目验证 offset 一致性
5. offset 通常在整个文档中恒定
```

---

## P2: 目录提取 + 逐页索引（merged 流程）

merged 模式分两阶段执行：先提取目录页（干净标题），再逐页 OCR 补齐。

### 2.1 Phase 1 — 从目录页提取（toc 路径）

#### 扫描版（OCR 路径）

```python
from pdf2image import convert_from_path
import easyocr
import torch

# 1. 目录页转图片
images = convert_from_path(pdf_path, dpi=300,
                           first_page=toc_start, last_page=toc_end)

# 2. OCR 识别
reader = easyocr.Reader(['ch_sim', 'en'], gpu=torch.cuda.is_available())
for img in images:
    results = reader.readtext(np.array(img))

# 3. 后处理：按行合并、数字纠正
# 4. 正则匹配：「标题 + 空格 + 页码」
```

#### 文字版（文本提取路径）

```python
# 1. 提取目录页文本
text = reader.pages[i].extract_text()

# 2. 正则解析
import re
pattern = r'^[\s　]*([^\d]+?)[\s　]+(\d{1,4})[\s　]*$'
matches = re.findall(pattern, text, re.MULTILINE)
```

### 2.2 Phase 2 — 逐页索引（index 路径）

对 PDF 每一页裁剪顶部 1/3，OCR 识别第一个非数字文本块作为页面标题。

```python
for page_idx, img in enumerate(all_images):
    top = img.crop((0, 0, img.width, img.height // 3))
    results = reader.readtext(np.array(top), detail=1)
    title = first_qualifying_text(results)  # 跳过纯数字、括号符号
    bookmarks.append({"pdf_page": page_idx + 1, "title": f"{title} (P. {page_idx+1})"})
```

### 2.3 合并策略

```
Phase 1 输出: 202 个 TOC 书签（标题干净，来自目录页）
Phase 2 输出: 405 个索引书签（每页一个，标题可能有噪声）
合并:
  1. covered = {Phase 1 的 pdf_page 集合}
  2. extras = Phase 2 中 pdf_page 不在 covered 的条目
  3. merged = Phase 1 + extras
  4. 按 pdf_page 排序，去重（每页只保留一个书签）
```

结果：每页都有书签；TOC 页的书签标题更干净，其余页面用索引标题兜底。

### 2.4 结构解析

OCR / 提取后的原始文本需要转换为结构化 TOC：

```
原始文本:
  流行歌曲
  传奇 58
  匆匆那年 60
  南山南 62
  弹唱经典
  兄弟 132
  真心英雄 134

解析后:
  [{"title": "流行歌曲", "type": "section"},
   {"title": "传奇", "printed_page": 58},
   {"title": "匆匆那年", "printed_page": 60},
   ...
   {"title": "弹唱经典", "type": "section"},
   {"title": "兄弟", "printed_page": 132}, ...]
```

**分层规则：**
- 有页码的条目 → 叶子节点（可跳转）
- 无页码的条目 → 父节点（章节分组）
- 通过缩进或前后文推断层级

**输出格式（JSON）：**

```json
{
  "pdf_path": "input.pdf",
  "page_offset": 8,
  "total_toc_entries": 215,
  "entries": [
    {
      "title": "认识吉他",
      "level": 0,
      "printed_page": 1,
      "pdf_page_index": 8
    },
    {
      "title": "吉他部位名称图",
      "level": 1,
      "printed_page": 1,
      "pdf_page_index": 8
    },
    {
      "title": "流行歌曲",
      "level": 0,
      "printed_page": null,
      "pdf_page_index": null
    },
    {
      "title": "传奇",
      "level": 1,
      "printed_page": 58,
      "pdf_page_index": 65
    }
  ]
}
```

---

## P3: 书签嵌入（合并后写入）

### 3.1 pypdf Outline 操作

**核心 API：**

```python
from pypdf import PdfWriter

writer = PdfWriter()
writer.append(reader)  # 引用原文件，不复制全部数据

# 创建顶级书签
section_bookmark = writer.add_outline_item(
    title="流行歌曲",
    page_number=None,      # 章节父节点可不传 page_number
    parent=None
)

# 创建子级书签（可跳转）
song_bookmark = writer.add_outline_item(
    title="传奇",
    page_number=65,        # 0-indexed PDF 页码
    parent=section_bookmark
)

# 输出
with open(output_path, "wb") as f:
    writer.write(f)
```

### 3.2 层级策略

| 类型 | 层级 | 是否跳转 | 示例 |
|------|------|---------|------|
| 章节/分类 | 父级 (level 0) | ❌ 不跳转，用于折叠 | 流行歌曲、弹唱经典 |
| 歌曲/小节 | 子级 (level 1-2) | ✅ 跳转到内容页 | 传奇 → p.58 |
| 子分类 | 中子级 | 可选 | 影视经典下的各电影歌曲 |

**展示效果（Adobe Acrobat / Chrome PDF 阅读器）：**

```
📖 吉他指弹曲200首大合集
  ├─ 认识吉他
  │  ├─ 吉他部位名称图
  │  └─ 认识六线谱
  ├─ 流行歌曲
  │  ├─ 传奇
  │  ├─ 匆匆那年
  │  └─ 南山南
  ├─ 弹唱经典
  │  ├─ 兄弟
  │  └─ 真心英雄
  └─ 双吉他指弹
     └─ 四季歌
```

### 3.3 技术约束

| 项目 | 说明 |
|------|------|
| **页码** | pypdf 使用 0-indexed 页码（0 = 第一页） |
| **append 模式** | `writer.append(reader)` 引用原始 PDF，不会复制全部 124MB 数据 |
| **中文标题** | PDF 规范原生支持 Unicode，中文标题无需特殊处理 |
| **嵌套深度** | 建议 ≤ 3 层，过深在阅读器中体验不佳 |
| **文件大小** | Outline 是轻量元数据，增加的体积通常 < 10KB |

---

## P4: QA 验收

### 验收清单

- [ ] 书签数量 = PDF 页数（merged 模式）或 ≈ TOC 条目数（toc 模式）
- [ ] 目录章节与正文结构一致
- [ ] 随机选取 5 个书签 → OCR 目标页验证跳转内容与书签标题匹配
- [ ] 输出的 PDF 可在浏览器 / PDF 阅读器中正常打开
- [ ] 文件未损坏（写入后可被重新读取、解析）

### 自动化验证

```python
def verify_toc(output_path, expected_count):
    reader = PdfReader(output_path)
    outlines = reader.outline
    assert len(outlines) == expected_count, \
        f"书签数量不符: 期望 {expected_count}, 实际 {len(outlines)}"

    # 抽样验证 3 个书签的 page_number 指向
    samples = [outlines[0], outlines[len(outlines)//2], outlines[-1]]
    for s in samples:
        assert '/Page' in s or '/A' in s, \
            f"书签缺少跳转目标: {s['/Title']}"
```

### 手工验证

- 在 Chrome / Edge 中打开生成的 PDF
- 点击左侧大纲面板的书签 → 确认跳转正确
- 检查书签层级是否与原始目录一致
- 检查是否有遗漏或错误的条目

---

## 降级策略

| 条件 | 行为 |
|------|------|
| 无 OCR 引擎 + 扫描版 | 报错并给出安装指引：`cd skills/pdf/pdf-toc-master && uv sync --extra ocr` |
| 无 OCR 引擎 + 文字版 | 正常处理（文字版不需要 OCR） |
| 找不到目录页 + 文字版 | 回退「标题推断」模式 |
| 找不到目录页 + 扫描版 | 提示用户指定目录页范围，或回退全文 OCR（需用户确认） |
| OCR 置信度 < 70% | 输出结果并标注低置信度条目，让用户手动修正 |
| 大文件 OOM | 分块处理 |

---

## 依赖清单

| 工具 | 版本 | 用途 | uv 安装 |
|------|------|------|---------|
| pypdf | ≥ 6.0 | PDF 读写与书签操作 | `uv sync`（核心依赖） |
| pdf2image | ≥ 1.16 | PDF 页转图片（OCR 用） | `uv sync`（核心依赖） |
| Pillow | ≥ 9.0 | 图片处理 | `uv sync`（核心依赖） |
| easyocr | ≥ 1.7 | 中文 OCR（推荐） | `uv sync --all-extras` |
| 可选: pytesseract | ≥ 0.3 | Tesseract 封装 | `pip install pytesseract`（手动） |
| 可选: pdf-lib | ≥ 1.17 | Node.js 端辅助 | `npm install -g pdf-lib` |

---

## 最小可用 Prompt

```
用 pdf-toc-master 给 PDF 生成目录书签（merged 模式）。

输入 PDF 路径：{pdf_path}
输出 PDF 路径：{output_path（可选，默认在输入文件旁生成）}

先做 PDF 分析，输出：
1) 总页数、是否为扫描版
2) 是否有目录页（页码范围）
3) 印刷页码与 PDF 页码的偏移量
4) 现有书签情况

确认后再执行书签嵌入（merged 模式）：
1) Phase 1: 从目录页 OCR 提取标题+页码 → 干净 TOC 书签
2) Phase 2: 逐页 OCR 顶部文本 → 索引书签（补齐无 TOC 条目的页面）
3) 合并：TOC 书签优先，索引书签填空，去重后嵌入
4) 嵌入到 PDF Outline

完成后执行验证：
1) 读取书签数量 = PDF 页数
2) 抽样 5 个书签，OCR 目标页确认跳转正确
3) 确认文件可正常打开

推荐命令：
uv run pdf-toc-extract {pdf_path} --offset {N} --toc-start {M} --toc-end {K} --gpu auto --mode merged
```
