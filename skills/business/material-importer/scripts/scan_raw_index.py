"""扫描 raw/ 目录，重建 _index.json。

用法:
  uv run scripts/scan_raw_index.py [--raw-dir <path>] [--materials-dir <path>] [--merge]

功能:
  - 遍历 raw/ 下所有 .md 与 .csv 文件（排除 _media/ 目录）
  - 对每个 raw 文件，扫描 materials/ 检测是否被引用（consumed_by）
  - 推断 imported_from（从目录结构反推 incoming/ 源路径；csv 推断为无扩展名）
  - 默认与现有 _index.json 合并（保留手动维护的字段）
  - --no-merge 时完全覆盖

输出:
  raw/_index.json
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
from fnmatch import fnmatchcase
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).parent))
from _company_base import resolve_company_base  # noqa: E402

RAW_EXTENSIONS = (".md", ".csv")


class ScanFailure(NamedTuple):
    """一次扫描中无法访问的位置（目录不可进入 / 文件不可读）。"""

    location: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - 展示格式
        return f"{self.location}: {self.message}"


def find_raw_files(raw_dir: Path) -> tuple[list[Path], list[ScanFailure]]:
    """遍历 raw/ 目录，收集所有 .md 与 .csv 文件（排除 _media/ 与隐藏目录）。

    返回 (文件列表, 无法访问的位置清单)。os.walk 对不可读目录默认静默跳过，
    这里通过 onerror 显式收集——绝不把「没扫到」当「不存在」。
    """
    results: list[Path] = []
    failures: list[ScanFailure] = []

    def record_error(err: OSError) -> None:
        failures.append(
            ScanFailure(
                location=getattr(err, "filename", None) or str(raw_dir),
                message=err.strerror or str(err),
            )
        )

    for root, dirs, files in os.walk(raw_dir, onerror=record_error):
        dirs[:] = [d for d in dirs if d != "_media" and not d.startswith(".")]
        for f in files:
            if f.endswith(RAW_EXTENSIONS) and f != "_index.json":
                results.append(Path(root) / f)
    return sorted(results), failures


def load_materials_content(
    materials_dir: Path,
) -> tuple[dict[str, str], list[ScanFailure]]:
    """加载 materials/ 下所有 .md 文件内容，返回 ({relative_path: content}, 读取失败清单)。

    读取失败的文件不参与 consumed_by 检测，必须显式上报；
    否则「读不到」会被下游当成「没有引用」，进而误判 needs_review。
    """
    contents: dict[str, str] = {}
    failures: list[ScanFailure] = []
    if not materials_dir.is_dir():
        return contents, failures

    def record_error(err: OSError) -> None:
        failures.append(
            ScanFailure(
                location=getattr(err, "filename", None) or str(materials_dir),
                message=err.strerror or str(err),
            )
        )

    for root, _, files in os.walk(materials_dir, onerror=record_error):
        for f in files:
            if f.endswith(".md"):
                p = Path(root) / f
                try:
                    text = p.read_text(encoding="utf-8", errors="replace")
                except OSError as e:
                    failures.append(
                        ScanFailure(location=str(p), message=e.strerror or str(e))
                    )
                    continue
                rel = str(p.relative_to(materials_dir.parent))
                contents[rel] = text
    return contents, failures


def find_consumers(raw_filename: str, materials_content: dict[str, str]) -> list[str]:
    """检测哪些 materials 文件引用了该 raw 文件。

    来源字段匹配完整 raw 文件名、原始文件名或来源字段中的通配引用；正文只匹配明确的 raw media 目录。
    """
    consumers: list[str] = []
    original_filename = raw_filename.removesuffix(".md")
    filename_pattern = re.compile(
        rf"(?<![\w.-])(?:{re.escape(raw_filename)}|{re.escape(original_filename)})(?![\w.-])"
    )
    glob_token_pattern = re.compile(r"[^\s;；\"'()（）]*\*[^\s;；\"'()（）]*")
    media_stem = original_filename.rsplit(".", 1)[0] if "." in original_filename else original_filename
    media_pattern = re.compile(
        rf"(?:^|/)raw/(?:[^/\s)\"']*/)*{re.escape(media_stem)}_media/"
    )

    def references(source_text: str, content: str) -> bool:
        if filename_pattern.search(source_text):
            return True
        for token in glob_token_pattern.findall(source_text):
            if "*" in token and fnmatchcase(raw_filename, token.rsplit("/", 1)[-1]):
                return True
        return bool(media_pattern.search(content))

    for mat_path, content in materials_content.items():
        frontmatter = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|\Z)", content, re.DOTALL)
        source_text = ""
        if frontmatter:
            source_lines = re.findall(
                r"(?m)^\s*(?:source|source_file)\s*:\s*(.*?)\s*$",
                frontmatter.group(1),
            )
            source_text = "\n".join(source_lines)
        if references(source_text, content):
            consumers.append(mat_path)

    return sorted(set(consumers))


def infer_imported_from(raw_path: Path, raw_dir: Path) -> str:
    """从 raw/ 子目录结构推断 incoming/ 源路径。"""
    rel = raw_path.relative_to(raw_dir)
    parts = rel.parts
    if len(parts) > 1:
        source_dir = parts[0]
        filename = raw_path.name
        orig_name = filename.removesuffix(".md")
        # csv 是 convert_excel 的产物，原始扩展名（.xls/.xlsx）无法从文件名推断，输出无扩展名形式
        orig_name = orig_name.removesuffix(".csv")
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
    raw_identity = raw_path.relative_to(raw_dir).as_posix()
    return {
        "imported_at": mtime.strftime("%Y-%m-%d"),
        "imported_from": infer_imported_from(raw_path, raw_dir),
        "consumed_by": consumers,
        "unconsumed_sections": [] if consumers else ["未检测到 materials 引用，需人工确认是否可清理"],
        "needs_review": len(consumers) == 0,
        "source_id": f"raw:{raw_identity}",
        "content_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
    }


def _under_inaccessible(rel_name: str, raw_dir: Path, failures: list[ScanFailure]) -> bool:
    """判断 raw 相对路径是否位于本次扫描无法访问的位置之下。"""
    target = raw_dir / rel_name
    for failure in failures:
        try:
            target.relative_to(Path(failure.location))
            return True
        except ValueError:
            continue
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描 raw/ 重建 _index.json")
    parser.add_argument("--raw-dir", default=None, help="raw/ 目录路径（默认 $COMPANY_BASE/raw）")
    parser.add_argument("--materials-dir", default=None, help="materials/ 目录路径（默认 $COMPANY_BASE/materials）")
    parser.add_argument("--merge", action="store_true", default=True, help="与现有索引合并（默认开启）")
    parser.add_argument("--no-merge", dest="merge", action="store_false", help="完全覆盖现有索引")
    args = parser.parse_args()

    base = resolve_company_base()
    raw_dir = Path(args.raw_dir) if args.raw_dir else base / "raw"
    materials_dir = Path(args.materials_dir) if args.materials_dir else base / "materials"

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
    raw_files, raw_failures = find_raw_files(raw_dir)
    for failure in raw_failures:
        print(f"[WARN] raw/ 无法访问（该子树未纳入索引）: {failure}", file=sys.stderr)
    if raw_failures:
        print(f"[WARN] raw/ 共 {len(raw_failures)} 处无法访问", file=sys.stderr)
    print(f"[INFO] 发现 {len(raw_files)} 个 .md 文件", file=sys.stderr)

    print(f"[INFO] 加载 materials/ 内容: {materials_dir}", file=sys.stderr)
    materials_content, material_failures = load_materials_content(materials_dir)
    for failure in material_failures:
        print(f"[WARN] materials 无法读取（consumed_by 检测未覆盖该文件）: {failure}", file=sys.stderr)
    if material_failures:
        print(
            f"[WARN] materials 共 {len(material_failures)} 处读取失败",
            file=sys.stderr,
        )
    print(f"[INFO] 加载 {len(materials_content)} 个 materials 文件", file=sys.stderr)

    # materials 不完整 → 所有条目的 consumed_by/needs_review 都基于部分证据，必须标记；
    # 仅 raw 子树失败 → 已发现条目自身证据完整，不标记（缺失条目在下方合并保留时单独标记）。
    materials_complete = not material_failures

    new_index: dict[str, dict] = {}
    consumed_count = 0
    for i, raw_path in enumerate(raw_files):
        rel_name = str(raw_path.relative_to(raw_dir))
        entry = build_entry(raw_path, raw_dir, materials_content)
        if entry["consumed_by"]:
            consumed_count += 1

        if args.merge and rel_name in existing:
            old = existing[rel_name]
            generated_entry = entry.copy()
            entry.update(old)
            entry["imported_from"] = old.get("imported_from") or entry["imported_from"]
            entry["consumed_by"] = find_consumers(raw_path.name, materials_content)
            entry["source_id"] = f"raw:{Path(rel_name).as_posix()}"
            entry["content_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
            entry["unconsumed_sections"] = generated_entry["unconsumed_sections"]
            if old.get("unconsumed_sections") and not generated_entry["unconsumed_sections"]:
                entry["unconsumed_sections"] = old["unconsumed_sections"]
            if "needs_review" in old:
                entry["needs_review"] = old["needs_review"] or generated_entry["needs_review"]

        if materials_complete:
            entry.pop("scan_incomplete", None)
        else:
            entry["scan_incomplete"] = True

        new_index[rel_name] = entry

        if (i + 1) % 200 == 0:
            print(f"[INFO] 进度: {i + 1}/{len(raw_files)}", file=sys.stderr)

    # 合并模式下，未能重新发现、且位于本次无法访问子树之下的旧条目：
    # 保留并标记 scan_incomplete——不能因为「扫不到」而丢弃仍有效的索引记录。
    preserved_count = 0
    if args.merge:
        for rel_name, old in existing.items():
            if rel_name in new_index:
                continue
            if _under_inaccessible(rel_name, raw_dir, raw_failures):
                preserved = dict(old)
                preserved["scan_incomplete"] = True
                new_index[rel_name] = preserved
                preserved_count += 1
                print(
                    f"[WARN] 旧条目位于无法访问的子树，保留并标记 scan_incomplete: {rel_name}",
                    file=sys.stderr,
                )

    index_path.write_text(
        json.dumps(new_index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    unconsumed = len(new_index) - consumed_count
    print(f"\n[OK] 索引重建完成: {index_path}", file=sys.stderr)
    print(f"     总条目: {len(new_index)}", file=sys.stderr)
    print(f"     已消费: {consumed_count} ({consumed_count / len(new_index) * 100:.1f}%)" if new_index else "", file=sys.stderr)
    print(f"     待确认: {unconsumed}", file=sys.stderr)
    if preserved_count:
        print(f"     保留(不可访问子树): {preserved_count}", file=sys.stderr)
    if not materials_complete or raw_failures:
        flagged = sum(1 for e in new_index.values() if e.get("scan_incomplete"))
        print(
            f"     ⚠️ 扫描不完整: raw {len(raw_failures)} 处 / materials "
            f"{len(material_failures)} 处失败，{flagged} 个条目标记 scan_incomplete；"
            "人工清理 raw 前必须先消除访问失败并重扫",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
