#!/usr/bin/env python3
"""规范化 OCR / markitdown 产出的 Markdown，避免 LSP parser 栈溢出。

问题：
  DeepSeek-OCR-2 等 VLM 模型经常产出单行长 HTML 表格（<table><td>...</table>）
  或 OCR 幻觉重复行（如 "1. 1. 1. ..." 占数千字符），让 marksman 等
  Markdown LSP 的 parser 触发 "depth limit exceeded" 栈溢出。

方案：
  把以下三类"污染行"包进 ```html fenced code block（内容字节不变，
  仅前后加 fence 标记），让 parser 跳过解析：
    1. 含 HTML 表格标签（<table>/<td>/<tr>/<th>）的行
    2. 超长行（>500 字符，可能是 OCR 幻觉重复模式）
    3. 深嵌套引用（行首 ≥3 个 >）

  已在原有 fence 内的行不重复包（避免嵌套破坏结构）。

用法（被其他脚本 import）：
    from sanitize_markdown import sanitize_content, sanitize_file
    new_text, wraps = sanitize_content(original_text)
    wraps = sanitize_file(path)  # 原地覆盖

用法（独立 CLI）：
    python3 scripts/sanitize_markdown.py <dir>            # 批量原地修复
    python3 scripts/sanitize_markdown.py <dir> --dry-run  # 只报告不写
    python3 scripts/sanitize_markdown.py <file>           # 单文件
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# HTML 表格标签（marksman parser 对这些标签的嵌套结构最敏感）
_HTML_TABLE_RE = re.compile(r"<(?:td|tr|th|table)\b", re.IGNORECASE)

# 超长行阈值：超过此值的行可能是 OCR 幻觉重复模式（如 "1. 1. 1. ..."）
_LENGTH_THRESHOLD = 500

# 深嵌套引用阈值：行首 ≥3 个 > 会被 parser 解析为深层嵌套
_QUOTE_DEPTH_THRESHOLD = 3


def _needs_fencing(line: str) -> bool:
    """判断一行是否需要被包进 fence。

    判定规则（满足任一即触发）：
      1. 含 HTML 表格标签（<table>/<td>/<tr>/<th>）
      2. 行长 > 500 字符
      3. 行首 ≥3 个 > （深嵌套引用）
    """
    if _HTML_TABLE_RE.search(line):
        return True
    if len(line) > _LENGTH_THRESHOLD:
        return True
    stripped = line.lstrip()
    if stripped.startswith(">"):
        # 计算行首连续 > 的数量
        depth = 0
        for ch in stripped:
            if ch == ">":
                depth += 1
            elif ch in (" ", "\t"):
                continue
            else:
                break
        if depth >= _QUOTE_DEPTH_THRESHOLD:
            return True
    return False


def sanitize_content(content: str) -> tuple[str, int]:
    """对 Markdown 内容做 sanitize，返回 (新内容, 添加的 fence 数)。

    - 已在原有 fence 内的污染行不重复包（识别原有 ``` 标记）
    - 连续的污染行合并到一个 fence（紧凑）
    - 内容字节不变，仅添加 fence 行
    """
    lines = content.split("\n")

    # 第一遍：标记每行是否在原有 fence 内
    in_original_fence = [False] * len(lines)
    inside = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_original_fence[i] = True
            inside = not inside
        else:
            in_original_fence[i] = inside

    # 第二遍：构造新内容
    new_lines: list[str] = []
    in_new_block = False
    wraps = 0

    for i, line in enumerate(lines):
        polluted = _needs_fencing(line)
        already_fenced = in_original_fence[i]

        if polluted and already_fenced:
            # 已在原有 fence 内，不需要处理
            new_lines.append(line)
        elif polluted and not already_fenced and not in_new_block:
            # 进入新 fence block
            new_lines.append("```html")
            new_lines.append(line)
            in_new_block = True
            wraps += 1
        elif polluted and in_new_block:
            # 延续当前 fence block
            new_lines.append(line)
        elif not polluted and in_new_block:
            # 退出当前 fence block
            new_lines.append("```")
            new_lines.append(line)
            in_new_block = False
        else:
            new_lines.append(line)

    # 文件末尾若仍在 fence 内，补上闭合
    if in_new_block:
        new_lines.append("```")

    return "\n".join(new_lines), wraps


def sanitize_file(path: Path) -> int:
    """对单个文件做 sanitize（原地覆盖），返回添加的 fence 数。

    若文件无需修改（wraps=0），不写文件（保留原 mtime）。
    """
    content = path.read_text(encoding="utf-8")
    new_content, wraps = sanitize_content(content)
    if wraps > 0:
        path.write_text(new_content, encoding="utf-8")
    return wraps


def _main() -> int:
    parser = argparse.ArgumentParser(
        description="规范化 OCR/markitdown 产出的 Markdown，避免 LSP parser 栈溢出",
    )
    parser.add_argument(
        "path", type=Path,
        help="目标文件或目录（目录则递归处理 *.md）",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="只报告会修改什么，不实际写文件",
    )
    parser.add_argument(
        "--exclude", action="append", default=None,
        help="排除的路径模式（可多次指定，grep -E 风格）",
    )
    args = parser.parse_args()

    if not args.path.exists():
        print(f"❌ 路径不存在: {args.path}", file=sys.stderr)
        return 1

    if args.path.is_file():
        files = [args.path]
    else:
        files = sorted(args.path.rglob("*.md"))

    # 排除模式
    if args.exclude:
        patterns = [re.compile(p) for p in args.exclude]
        files = [f for f in files if not any(p.search(str(f)) for p in patterns)]

    total_files = 0
    total_wraps = 0
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  ⚠️ 读取失败 {f}: {e}", file=sys.stderr)
            continue

        if args.dry_run:
            _, wraps = sanitize_content(content)
        else:
            wraps = sanitize_file(f)

        if wraps > 0:
            total_files += 1
            total_wraps += wraps
            action = "DRY " if args.dry_run else "FIX "
            print(f"  {action} {wraps:4d} wraps | {f}")

    print(f"\n{'DRY-RUN' if args.dry_run else 'DONE'}: "
          f"{total_files}/{len(files)} 文件，{total_wraps} 处 fence")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
