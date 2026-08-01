# word-master 排障手册

> 本文件记录 word-master 的非显而易见行为。跨 skill 通用规则见 `AGENTS.md`，不在此重复。

## 调用契约（5 个消费方必读）

word-master 被 product-prd-generator / company-intro-generator / bid-doc-master / project-proposal-generator / strategy-brief-generator 调用。调用方**必须**：

```python
# 必须在 word-master 目录用 uv run，不能用 python3（venv mismatch）
subprocess.run(
    ["uv", "run", "python", "-m", "src.main", str(content_path.resolve()), "--output", str(output)],
    cwd=str(word_master_dir),  # skills/word/word-master
)
# content_path 必须 .resolve() 转绝对路径——subprocess cwd 改变后相对路径失效
```

**违反症状**：`ModuleNotFoundError: docx`（没在 word-master 目录跑 / 没用 uv）或 `FileNotFoundError`（相对路径在 subprocess cwd 下找不到）。

## 模板映射规则

`renderer.py` 按 doc_type 选择 base template，调用 `_clear_template_body()` 清除占位符：

| doc_type | base template |
|---|---|
| `bidding-technical` / `bidding-commercial` | 专用 base template（独立） |
| `proposal` / `report` / `intro` / `bidding-standard` / `bidding-compilation` | 全部 alias 到 `bidding-technical-base.docx` |

**坑**：新增 doc_type 不在映射表里 → 静默 fallback 到 bidding-technical-base，不报错但样式可能不符预期。新增类型必须同步更新映射表。

## nearby_text 控制字符

`nearby_text`（从素材提取的关联文本）可能含控制字符（`\x00-\x1f`），直接写入 docx 会产生损坏段落。**必须**经 `_sanitize` 处理后才能写入。症状：生成的 docx 在 Word 打开报「文件已损坏」或段落消失。

## TOC field 不自动更新

python-docx 写入 TOC field（目录占位），但**页码在 Word 打开前是空的或过期的**。生成后需在 Word 里手动「更新域」或用户首次打开时 Word 提示更新。这不是 bug，是 python-docx 的限制（无法触发 Word 的域计算引擎）。

## LSP 假错误（忽略）

LSP 对 `renderer.py` 报大量「not a known attribute」错误——这是 `docx` / `openpyxl` 类型 stub 缺失导致的假错误，**不是真实问题**。验证真实行为用 `uv run python -m src.main`，不要试图「修复」这些 LSP 报错。

## 产品PRD.word-content.md 格式

内容包格式见 `src/parser.py`。关键字段：frontmatter 的 `doc_type` / `title` / 正文按 `## 章节标题` 组织。验证内容包合法性：

```bash
cd skills/word/word-master
uv run scripts/validate_package.py <file-or-dir> [--verbose] [--json]
```
