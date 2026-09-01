#!/usr/bin/env python3
"""批量将 raw/ 竞品转换产物创建为 materials .md（带 frontmatter）。

用法:
  python3 scripts/batch_competitor_import.py

处理 yueshang/ifca/capgemini 三家（materials/ 下 0 个 .md），
从 raw/prd-商管系统/02-competitors/ 的转换产物创建结构化 materials .md。
"""

import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _company_base import resolve_company_base
from sanitize_markdown import sanitize_content


def read_text_auto(path: Path) -> str:
    """自动探测编码读取文本文件。

    优先级：UTF-8 → GB18030（GBK 超集，覆盖中文 Windows 文件）→ UTF-16 → 兜底 replace。
    避免 GBK 等非 UTF-8 源文件被强制按 UTF-8 读取产生乱码（U+FFFD）。
    """
    raw = path.read_bytes()
    for enc in ("utf-8", "gb18030", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")

# 子路径解析优先级：CLI 参数 > 目录存在性守卫的兼容默认（prd-商管系统，lanlnk 存量行为）> 报错列候选
_LEGACY_RAW_SUBDIR = "prd-商管系统"


@dataclass(frozen=True, slots=True)
class ImportContext:
    """一次批量导入的路径上下文（由 main 解析后向下传递）。"""

    base: Path
    raw_dir: Path
    mat_dir: Path


def resolve_competitor_dirs(base: Path, raw_flag: str | None, materials_flag: str | None) -> tuple[Path, Path]:
    if raw_flag:
        raw_dir = Path(raw_flag)
        if not raw_dir.is_dir():
            sys.exit(f"错误: --raw-competitors 指定的目录不存在: {raw_flag}")
    else:
        legacy = base / "raw" / _LEGACY_RAW_SUBDIR / "02-competitors"
        if legacy.is_dir():
            raw_dir = legacy
        else:
            candidates = sorted(p.parent.name for p in (base / "raw").glob("prd-*/02-competitors") if p.is_dir()) \
                if (base / "raw").is_dir() else []
            hint = f"  候选: {', '.join(candidates)}\n" if candidates else ""
            sys.exit(
                "错误: 无法定位竞品 raw 目录（raw/prd-*/02-competitors）。\n"
                f"{hint}"
                "  请用 --raw-competitors <dir> 显式指定。"
            )
    materials_dir = Path(materials_flag) if materials_flag else base / "materials" / "13-competitors"
    return raw_dir, materials_dir


VENDOR_MAP = {
    "悦商": ("yueshang", "商管"),
    "ifca": ("ifca", "商管"),
    "凯捷": ("capgemini", "商管"),
}

CATEGORY_MAP = {
    "01-销售策略": "01-销售策略",
    "02-方案汇报": "02-方案汇报",
    "03-报价商务": "03-报价商务",
    "04-产品功能": "04-产品功能",
    "05-实施与服务": "05-实施与服务",
    "06-行业洞察": "06-行业洞察",
    "00-未分类": "00-未分类",
}

DOMAIN_TAGS = {
    "商管": ["商管"],
}


def generate_id(vendor_en: str, seq: int) -> str:
    return f"competitor-{vendor_en}-{seq:03d}"


def infer_name(filename: str) -> str:
    name = filename
    for ext in [".pptx.md", ".docx.md", ".xlsx.md", ".pdf.md", ".ppt.md", ".md"]:
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    return name.replace("_", " ").replace("-", " ")


def has_content(text: str) -> bool:
    stripped = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL).strip()
    return len(stripped) > 100


def build_frontmatter(vendor_en: str, vendor_cn: str, domain: str, seq: int, name: str, raw_path: str) -> str:
    status = "complete" if True else "incomplete"
    today = date.today().isoformat()
    return f"""---
id: "{generate_id(vendor_en, seq)}"
type: "竞品资料"
name: "{name}"
domain: [{", ".join(f'"{d}"' for d in DOMAIN_TAGS[domain])}]
status: "{status}"
created: "{today}"
updated: "{today}"
competitor: "{vendor_cn}"
tags: ["竞品", "{vendor_cn}"]
source_file: "{raw_path}"
---

"""


def process_vendor(ctx: ImportContext, vendor_cn: str, vendor_en: str, domain: str) -> int:
    raw_dir = ctx.raw_dir / vendor_cn
    mat_dir = ctx.mat_dir / vendor_en

    if not raw_dir.is_dir():
        print(f"  [SKIP] raw/ 不存在: {raw_dir}")
        return 0

    raw_files = sorted(
        f for f in raw_dir.rglob("*.md")
        if "_media" not in f.parts and f.name != "_index.json"
    )

    if not raw_files:
        print(f"  [SKIP] raw/ 无 .md 文件: {raw_dir}")
        return 0

    existing_ids = set()
    for existing in mat_dir.rglob("*.md"):
        text = existing.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'^id:\s*"([^"]+)"', text, re.MULTILINE)
        if m:
            existing_ids.add(m.group(1))

    seq = 1
    while generate_id(vendor_en, seq) in existing_ids:
        seq += 1

    created = 0
    for raw_file in raw_files:
        rel = raw_file.relative_to(raw_dir)
        parts = list(rel.parts)

        if parts[0] in CATEGORY_MAP:
            parts[0] = CATEGORY_MAP[parts[0]]

        mat_file = mat_dir.joinpath(*parts)
        mat_file.parent.mkdir(parents=True, exist_ok=True)

        if mat_file.exists():
            continue

        content = read_text_auto(raw_file)
        if not has_content(content):
            print(f"  [SKIP] 内容太少: {rel}")
            continue

        raw_rel = str(raw_file.relative_to(ctx.base))
        name = infer_name(rel.name)
        fm = build_frontmatter(vendor_en, vendor_cn, domain, seq, name, raw_rel)

        content, _ = sanitize_content(content)
        mat_file.write_text(fm + content, encoding="utf-8")
        print(f"  [OK] {mat_file.relative_to(ctx.mat_dir)}")
        seq += 1
        created += 1

    return created


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="批量将 raw/ 竞品转换产物创建为 materials .md")
    parser.add_argument("--raw-competitors", help="竞品 raw 目录（默认: 目录存在性守卫的 prd-商管系统，否则报错列候选）")
    parser.add_argument("--materials-competitors", help="竞品 materials 目录（默认: <base>/materials/13-competitors）")
    args = parser.parse_args(argv)

    base = resolve_company_base()
    raw_dir, mat_dir = resolve_competitor_dirs(base, args.raw_competitors, args.materials_competitors)
    ctx = ImportContext(base=base, raw_dir=raw_dir, mat_dir=mat_dir)
    print(f"公司基座: {ctx.base}")
    print(f"竞品 raw: {ctx.raw_dir}")
    print(f"竞品 materials: {ctx.mat_dir}")

    total = 0
    for vendor_cn, (vendor_en, domain) in VENDOR_MAP.items():
        print(f"\n=== {vendor_cn} ({vendor_en}) ===")
        count = process_vendor(ctx, vendor_cn, vendor_en, domain)
        print(f"  创建 {count} 个 .md")
        total += count

    print(f"\n总计创建 {total} 个 materials .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
