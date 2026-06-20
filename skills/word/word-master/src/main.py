"""word-master CLI 入口

用法：
    python -m src.main <content-package-path> [--output OUTPUT] [--verbose]
"""

from __future__ import annotations

import argparse
import sys
import os
from pathlib import Path

from .parser import parse_content_package
from .renderer import render


def main():
    parser = argparse.ArgumentParser(
        description="word-master: Word 内容包 → .docx 文档渲染引擎"
    )
    parser.add_argument(
        "content_package",
        help="Word 内容包路径 (*.word-content.md)",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出 .docx 路径（默认根据内容包自动生成）",
        default=None,
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="输出详细日志",
    )

    args = parser.parse_args()

    # 1. 解析内容包
    cp_path = Path(args.content_package)
    if not cp_path.exists():
        print(f"❌ 内容包不存在: {cp_path}")
        sys.exit(1)

    if args.verbose:
        print(f"📖 解析内容包: {cp_path}")

    try:
        pkg = parse_content_package(cp_path)
    except Exception as e:
        print(f"❌ 内容包解析失败: {e}")
        sys.exit(1)

    # 统计
    sub_count = sum(len(c.sub_chapters) for c in pkg.chapters)
    table_count = sum(
        len(c.tables) + sum(len(s.tables) for s in c.sub_chapters)
        for c in pkg.chapters
    )

    if args.verbose:
        print(f"   ├─ 标题: {pkg.title}")
        print(f"   ├─ 项目: {pkg.project}")
        print(f"   ├─ 类型: {pkg.type}")
        print(f"   ├─ 模板: {pkg.template or pkg.type}")
        print(f"   └─ 章节: {len(pkg.chapters)} 章 / {sub_count} 子节 / {table_count} 表格")

    # 2. 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        stem = cp_path.stem
        if stem.endswith(".word-content"):
            stem = stem.replace(".word-content", "")
        output_path = cp_path.with_name(f"{stem}.docx")

    if args.verbose:
        print(f"📄 输出: {output_path}")

    # 3. 渲染
    try:
        result = render(pkg, output_path)
    except Exception as e:
        print(f"❌ 文档渲染失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 4. 结果
    file_size = os.path.getsize(result)
    size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / 1024 / 1024:.1f} MB"

    print(f"")
    print(f"✅ 文档生成成功!")
    print(f"📁 位置: {result}")
    print(f"📄 大小: {size_str}")
    print(f"📊 章节: {len(pkg.chapters)} 章 / {sub_count} 子节 / {table_count} 表格")
    print(f"🎨 模板: {pkg.template or pkg.type}")


if __name__ == "__main__":
    main()