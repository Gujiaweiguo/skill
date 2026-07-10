"""扫描 raw/ 目录，重建 _index.json。

用法:
  uv run scripts/scan_raw_index.py [--raw-dir <path>] [--materials-dir <path>] [--merge]

功能:
  - 遍历 raw/ 下所有 .md 文件（排除 _media/ 目录）
  - 对每个 raw 文件，扫描 materials/ 检测是否被引用（consumed_by）
  - 推断 imported_from（从目录结构反推 incoming/ 源路径）
  - 默认与现有 _index.json 合并（保留手动维护的字段）
  - --no-merge 时完全覆盖

输出:
  raw/_index.json
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def find_raw_md_files(raw_dir: Path) -> list[Path]:
    """遍历 raw/ 目录，收集所有 .md 文件（排除 _media/）。"""
    results: list[Path] = []
    for root, dirs, files in os.walk(raw_dir):
        dirs[:] = [d for d in dirs if d != "_media" and not d.startswith(".")]
        for f in files:
            if f.endswith(".md") and f != "_index.json":
                results.append(Path(root) / f)
    return sorted(results)


def load_materials_content(materials_dir: Path) -> dict[str, str]:
    """加载 materials/ 下所有 .md 文件内容，返回 {relative_path: content}。"""
    contents: dict[str, str] = {}
    if not materials_dir.is_dir():
        return contents
    for root, _, files in os.walk(materials_dir):
        for f in files:
            if f.endswith(".md"):
                p = Path(root) / f
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    rel = str(p.relative_to(materials_dir.parent))
                    contents[rel] = text
                except Exception:
                    pass
    return contents


def find_consumers(raw_filename: str, materials_content: dict[str, str]) -> list[str]:
    """检测哪些 materials 文件引用了该 raw 文件。

    匹配策略（从精确到宽松）：
    1. 完整文件名（含扩展名，如 report.xlsx.md）
    2. 去掉 .md 后缀的文件名（如 report.xlsx）
    3. 去掉所有扩展名的文件名（如 report）
    """
    consumers: list[str] = []

    stems = set()
    stems.add(raw_filename)
    name_no_md = raw_filename.removesuffix(".md")
    stems.add(name_no_md)
    name_no_ext = name_no_md
    while "." in name_no_ext:
        name_no_ext = name_no_ext.rsplit(".", 1)[0]
    if name_no_ext and len(name_no_ext) >= 4:
        stems.add(name_no_ext)

    for mat_path, content in materials_content.items():
        for stem in stems:
            if stem in content:
                consumers.append(mat_path)
                break

    return sorted(set(consumers))


def infer_imported_from(raw_path: Path, raw_dir: Path) -> str:
    """从 raw/ 子目录结构推断 incoming/ 源路径。"""
    rel = raw_path.relative_to(raw_dir)
    parts = rel.parts
    if len(parts) > 1:
        source_dir = parts[0]
        filename = raw_path.name
        orig_name = filename.removesuffix(".md")
        return f"incoming/{source_dir}/{orig_name}"
    return ""


def build_entry(
    raw_path: Path,
    raw_dir: Path,
    materials_content: dict[str, str],
) -> dict:
    """为单个 raw 文件构建索引条目。"""
    consumers = find_consumers(raw_path.name, materials_content)
    mtime = datetime.fromtimestamp(raw_path.stat().st_mtime)
    return {
        "imported_at": mtime.strftime("%Y-%m-%d"),
        "imported_from": infer_imported_from(raw_path, raw_dir),
        "consumed_by": consumers,
        "unconsumed_sections": [] if consumers else ["未检测到 materials 引用，需人工确认是否可清理"],
        "needs_review": len(consumers) == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描 raw/ 重建 _index.json")
    parser.add_argument("--raw-dir", default=None, help="raw/ 目录路径（默认 $LANLNK_BASE/raw）")
    parser.add_argument("--materials-dir", default=None, help="materials/ 目录路径（默认 $LANLNK_BASE/materials）")
    parser.add_argument("--merge", action="store_true", default=True, help="与现有索引合并（默认开启）")
    parser.add_argument("--no-merge", dest="merge", action="store_false", help="完全覆盖现有索引")
    args = parser.parse_args()

    lanlnk_base = Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk"))
    raw_dir = Path(args.raw_dir) if args.raw_dir else lanlnk_base / "raw"
    materials_dir = Path(args.materials_dir) if args.materials_dir else lanlnk_base / "materials"

    if not raw_dir.is_dir():
        print(f"[ERROR] raw/ 目录不存在: {raw_dir}", file=sys.stderr)
        return 1

    index_path = raw_dir / "_index.json"

    existing: dict[str, dict] = {}
    if args.merge and index_path.is_file():
        try:
            existing = json.loads(index_path.read_text(encoding="utf-8"))
            print(f"[INFO] 加载现有索引: {len(existing)} 条", file=sys.stderr)
        except Exception:
            print(f"[WARN] 现有 _index.json 解析失败，将完全重建", file=sys.stderr)

    print(f"[INFO] 扫描 raw/ 目录: {raw_dir}", file=sys.stderr)
    raw_files = find_raw_md_files(raw_dir)
    print(f"[INFO] 发现 {len(raw_files)} 个 .md 文件", file=sys.stderr)

    print(f"[INFO] 加载 materials/ 内容: {materials_dir}", file=sys.stderr)
    materials_content = load_materials_content(materials_dir)
    print(f"[INFO] 加载 {len(materials_content)} 个 materials 文件", file=sys.stderr)

    new_index: dict[str, dict] = {}
    consumed_count = 0
    for i, raw_path in enumerate(raw_files):
        rel_name = str(raw_path.relative_to(raw_dir))
        entry = build_entry(raw_path, raw_dir, materials_content)
        if entry["consumed_by"]:
            consumed_count += 1

        if args.merge and rel_name in existing:
            old = existing[rel_name]
            entry["imported_from"] = old.get("imported_from") or entry["imported_from"]
            if old.get("unconsumed_sections") and not entry["unconsumed_sections"]:
                entry["unconsumed_sections"] = old["unconsumed_sections"]
            if "needs_review" in old:
                entry["needs_review"] = old["needs_review"] or entry["needs_review"]

        new_index[rel_name] = entry

        if (i + 1) % 200 == 0:
            print(f"[INFO] 进度: {i + 1}/{len(raw_files)}", file=sys.stderr)

    index_path.write_text(
        json.dumps(new_index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    unconsumed = len(new_index) - consumed_count
    print(f"\n[OK] 索引重建完成: {index_path}", file=sys.stderr)
    print(f"     总条目: {len(new_index)}", file=sys.stderr)
    print(f"     已消费: {consumed_count} ({consumed_count / len(new_index) * 100:.1f}%)" if new_index else "", file=sys.stderr)
    print(f"     待确认: {unconsumed}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
