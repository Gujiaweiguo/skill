#!/usr/bin/env python3
"""批量将 raw/ 竞品转换产物创建为 materials .md（带 frontmatter）。

用法:
  python3 scripts/batch_competitor_import.py

处理 yueshang/ifca/capgemini 三家（materials/ 下 0 个 .md），
从 raw/prd-商管系统/02-competitors/ 的转换产物创建结构化 materials .md。
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

LANLNK_BASE = Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk"))
RAW_COMPETITORS = LANLNK_BASE / "raw" / "prd-商管系统" / "02-competitors"
MATERIALS_COMPETITORS = LANLNK_BASE / "materials" / "13-competitors"

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


def process_vendor(vendor_cn: str, vendor_en: str, domain: str) -> int:
    raw_dir = RAW_COMPETITORS / vendor_cn
    mat_dir = MATERIALS_COMPETITORS / vendor_en

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

        content = raw_file.read_text(encoding="utf-8", errors="replace")
        if not has_content(content):
            print(f"  [SKIP] 内容太少: {rel}")
            continue

        raw_rel = f"raw/prd-商管系统/02-competitors/{vendor_cn}/{rel}"
        name = infer_name(rel.name)
        fm = build_frontmatter(vendor_en, vendor_cn, domain, seq, name, raw_rel)

        mat_file.write_text(fm + content, encoding="utf-8")
        print(f"  [OK] {mat_file.relative_to(MATERIALS_COMPETITORS)}")
        seq += 1
        created += 1

    return created


def main() -> int:
    total = 0
    for vendor_cn, (vendor_en, domain) in VENDOR_MAP.items():
        print(f"\n=== {vendor_cn} ({vendor_en}) ===")
        count = process_vendor(vendor_cn, vendor_en, domain)
        print(f"  创建 {count} 个 .md")
        total += count

    print(f"\n总计创建 {total} 个 materials .md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
