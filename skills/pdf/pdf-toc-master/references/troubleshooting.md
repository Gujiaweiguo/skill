# pdf-toc-master 排障手册

> 本文件记录 pdf-toc-master 的非显而易见行为。OCR 引擎选择见 `AGENTS.md`（DeepSeek-OCR-2 首选，PaddleOCR 在 Blackwell sm_120 不可用），不在此重复。

## offset 参数（最致命）

`--offset N` 定义 **PDF 物理页索引 = 书籍印刷页码 + N**。错了 offset，所有书签跳转到错误页面。

- 印刷页码 = 书上印的数字（不含前言/目录的页数）
- PDF 物理页 = PDF 阅读器里的页序号（从封面算起）
- offset = 前言 + 目录占的页数

**验证方法**：先取一个已知章节（如「第 1 章」印刷页码 10），在 PDF 里翻到该章实际位置（可能是物理页 18），则 offset = 18 - 10 = 8。

**症状**：offset 错了不会报错，但点击书签跳到错误页面，且无任何错误提示。必须人工抽样验证 3-5 个书签。

## toc-start / toc-end 定位

`--toc-start M --toc-end K` 定义目录页在 PDF 中的范围（**1-indexed，PDF 物理页**）。

- 定位错误 → OCR 提取到错误内容（正文页被当目录解析），或漏掉真实目录页
- 目录跨多页时必须完整覆盖，漏页导致部分章节不出现在书签里

## 扫描版 vs 文字版 PDF

- **文字版**（pdftotext 能提取文本）：不需要 OCR，`pypdf` 直接提取，速度快、准确
- **扫描版**（图片型 PDF）：必须 OCR。流程是 `pdf2image` 转图 → OCR 识别 → 解析目录结构

**判断方法**：`pdftotext input.pdf - | head` 有文本输出 = 文字版；空或乱码 = 扫描版。文字版用 OCR 是浪费且可能更差。

## PEP 723 inline deps

脚本（`pdf-toc-extract`）用 PEP 723 内联依赖声明（脚本头部的 `# /// script` 块）。这意味着：

- 不需要修改 `pyproject.toml` 就能加运行时依赖
- `uv run pdf-toc-extract` 会自动解析内联依赖
- **不要**把 OCR 依赖（torch / transformers / easyocr）加到主 `pyproject.toml`——那是 material-importer 的 OCR 脚本约定，本 skill 独立

## --skip-existing checkpoint 续跑

OCR 耗时长，中断后用 `--skip-existing` 从 `slides.jsonl` checkpoint 续跑：

- 每张图 OCR 完立即 append 到 `slides.jsonl`（flush 后继续）
- `--skip-existing` 从已有 `slides.jsonl` 读取已处理图片，跳过不重跑
- 聚合输出（`tables.jsonl` / `all-ocr.md` / `manifest.json`）只在最后从 `slides.jsonl` 重建

**症状**：中断后不传 `--skip-existing` → 全部重跑，浪费时间。`slides.jsonl` 丢失 → 无法续跑，必须从头。

## poppler-utils 前置

`pdf2image` 依赖系统级 `poppler-utils`（`apt install poppler-utils`）。无 sudo 权限时 `pdf2image` 报错，扫描版 PDF 无法处理。文字版不受影响（pypdf 不依赖 poppler）。

## 推荐运行命令

```bash
# merged 模式（提取目录 + 逐页索引 + 合并书签，推荐）
uv run pdf-toc-extract input.pdf --offset 8 --toc-start 6 --toc-end 8 --gpu auto --mode merged
```

`--gpu auto` 自动选择设备；`--mode merged` 一步到位（vs split 分两步）。
