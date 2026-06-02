# PDF TOC Master — 工作流参考

## 完整流程速查

### 模式 A：有目录页（最常见）

```
P0: 环境检测
  → 检查 pypdf / pdf2image / OCR 是否可用
  → 不可用则降级或报错安装指引

P1: PDF 分析
  → 读取 PDF：页数、类型（扫描/文字）、元数据
  → 定位目录页（搜索「目录」或检测排版模式）
  → 计算页码偏移量

P2: 目录提取
  → 扫描版：pdf2image → OCR → 后处理
  → 文字版：pypdf.extract_text() → 正则解析
  → 输出结构化的 [{title, printed_page, level}, ...]

P3: 书签嵌入
  → PdfWriter.append(reader)
  → 递归创建 outline items（父节点不跳转，子节点跳转）
  → 写入输出文件

P4: QA 验证
  → 书签数量核对
  → 抽样跳转验证
  → 文件完整性检查
```

### 模式 C：无目录页（标题推断）

```
P0-P1: 同上

P2: 全文分析
  → 遍历所有页面
  → 按字号/字体聚类（需要提取文本或 OCR）
  → 收集大字号单行/简短标题
  → 构建推断的 TOC

P3: 用户确认
  → 输出推断的 TOC 结构
  → 用户确认或修正

P4: 书签嵌入（同模式 A）
```

---

## 页码偏移计算（核心难点）

### 问题

扫描版 PDF 的印刷页码通常与 PDF 页面索引不一致：

```
PDF 页码（0-indexed）:  0   1   2   3   4   5   6   7   8   9 ...
印刷页码:              封面 扉页 CIP 编委 前言 目录 目录 目录 001 002 ...
```

封面/前言/目录页占据了前 N 页但没有印刷页码，导致偏移。

### 计算方法

```python
def compute_offset(reader, toc_entries, pdf_start_page=0):
    """
    计算印刷页码到 PDF 页码的偏移量。

    原理：取 TOC 中第 1 条有页码的条目，找到它在 PDF 中的实际位置。
    """
    # 取第一条有页码的条目
    first_entry = next(e for e in toc_entries if e['printed_page'] is not None)
    expected_title = first_entry['title']
    expected_page = first_entry['printed_page']

    # 在预期页面附近查找（印刷页 N 应该在 PDF 的 N+offset 附近）
    # 通过抽样比对确定 offset

    # 简单方法：对比已知页面
    # 印刷页 p1 在 PDF 索引 i1 处 → offset = i1 - p1
    # 印刷页 p2 在 PDF 索引 i2 处 → offset = i2 - p2
    # 验证 offset 一致性

    return offset
```

### 偏移验证

- 取至少 3 个抽样点做交叉验证
- 偏移量通常在整份文档中恒定
- 若不一致（跳页/缺页），标记特殊页面做单独映射

---

## OCR 后处理规则

### 常见 OCR 错误模式（中文）

| 原始字符 | 常见 OCR 误识别 |
|---------|---------------|
| 千千阙歌 | 千千阙歇、千千阕歌 |
| 偏偏喜欢你 | 偏偏喜欢体 |
| 沧海一声笑 | 沧海一声关 |
| 数字 0-9 | 偶尔误识为字母 O/I/l |

### 后处理策略

1. **数字纠正**：`零一二三四五六七八九十` → `0123456789`（中式页码需要）
2. **标题去噪**：移除 OCR 引入的特殊字符、多余空格
3. **行合并**：因排版分栏导致的割裂行重新合并
4. **页码验证**：页码应当单调递增且不重复
5. **模式校验**：`标题 + 间隔 + 数字` 格式校验

### 置信度阈值

| 置信度 | 处理方式 |
|--------|---------|
| ≥ 0.9 | 自动接受 |
| 0.7 - 0.9 | 自动接受但标注 |
| < 0.7 | 输出给用户人工确认 |

---

## PDF 操作规范

### 文件处理

```python
# ✅ 正确：append 引用模式（不复制全部数据）
writer.append(reader)

# ✅ 正确：0-indexed 页码
writer.add_outline_item(title="传奇", page_number=65)  # PDF 第 66 页

# ❌ 错误：1-indexed
writer.add_outline_item(title="传奇", page_number=66)  # 跳到第 67 页
```

### 大文件注意事项

- 124MB 的 PDF：`append()` 引用原始文件，写入时只增加 outline 元数据
- 输出文件大小 ≈ 原始文件 + 几 KB
- 若原始文件被移动/删除前需要保持引用路径不变

### 中文编码

- PDF Outline 标题直接传 Unicode 字符串即可
- pypdf 内部会正确处理编码
- 不需要额外编码转换

---

## 交付物清单

每次完成后的标准交付物：

- `{原文件名}_toc.pdf` — 带书签的 PDF（默认命名）
- 或 `{用户指定的输出路径}`
- 目录提取报告（条目数量、章节结构、偏移量）
- QA 验证报告（抽样跳转结果）
- 低置信度条目列表（如有）

---

## 环境依赖检查

```bash
# 检查 pypdf
python3 -c "from pypdf import PdfReader; print('pypdf OK')"

# 检查 pdf2image
python3 -c "from pdf2image import convert_from_path; print('pdf2image OK')"

# 检查 easyocr
python3 -c "import easyocr; print('easyocr OK')"

# 检查 Pillow
python3 -c "from PIL import Image; print('Pillow OK')"
```

如缺少依赖，在执行过程中安装即可：

```bash
pip install pypdf pdf2image Pillow easyocr
```
