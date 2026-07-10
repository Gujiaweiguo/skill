#!/usr/bin/env python3
"""批量给无 frontmatter 的竞品资料 .md 补标准 frontmatter。

用法:
  uv run scripts/add_frontmatter.py <目录> [--dry-run] [--created YYYY-MM-DD]

规则:
  - 已有 frontmatter（以 --- 开头）→ 跳过
  - name: 首个 H1 标题 → 否则文件名（去 .md）
  - id: competitor-<vendor>-<3位序号>
  - type: 竞品资料  domain: [商管]  status: complete
  - created: 默认今天
幂等：重复运行只处理新增的无 frontmatter 文件。
"""
import os
import re
import sys
from datetime import date

VENDOR_CN = {
    "qimao": "旗茂", "mingyuan": "明源", "haiding": "海鼎",
    "xuewei": "学纬", "capgemini": "凯捷", "ifca": "IFCA", "yueshang": "粤商",
}


def extract_name(content: str, filename: str) -> str:
    """从首个 H1 标题推断 name，否则用文件名。"""
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("# "):
            name = s[2:].strip()
            # 清理常见前缀噪音
            name = re.sub(r"^OCR 提取结果:\s*", "", name)
            name = name.replace("---", "-")  # 防止值内 --- 破坏 frontmatter split
            return name[:80]  # 限长
    return os.path.splitext(filename)[0]


def find_vendor(path: str, root: str) -> str:
    """从路径里 13-competitors/<vendor>/ 取 vendor。"""
    rel = os.path.relpath(path, root)
    parts = rel.split(os.sep)
    for i, p in enumerate(parts):
        if p == "13-competitors" and i + 1 < len(parts):
            return parts[i + 1]
    return "unknown"


def has_frontmatter(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read(4).startswith("---")
    except Exception:
        return False


def process_dir(target: str, root: str, created: str, dry_run: bool):
    # 收集所有无 frontmatter 的 md，按 vendor 分组编序号
    files = []
    for dirpath, _, fnames in os.walk(target):
        if "/raw" in dirpath or os.sep + "raw" in dirpath:
            continue
        for fn in sorted(fnames):
            if fn.endswith(".md"):
                p = os.path.join(dirpath, fn)
                if not has_frontmatter(p):
                    files.append(p)
    files.sort()

    counters = {}
    done = []
    skipped = []
    for p in files:
        vendor = find_vendor(p, root)
        counters[vendor] = counters.get(vendor, 0) + 1
        seq = counters[vendor]
        vid = f"competitor-{vendor}-{seq:03d}"
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
        name = extract_name(content, os.path.basename(p))
        vendor_cn = VENDOR_CN.get(vendor, vendor)
        # name 加竞品中文前缀（若 name 本身不含）
        if vendor_cn not in name:
            disp_name = f"{vendor_cn}-{name}"
        else:
            disp_name = name
        fm = (
            "---\n"
            f'id: "{vid}"\n'
            f'type: "竞品资料"\n'
            f'name: "{disp_name}"\n'
            f'domain: ["商管"]\n'
            f'status: "complete"\n'
            f'created: "{created}"\n'
            f'source: "incoming/competitor-{vendor}/"\n'
            "---\n\n"
        )
        if dry_run:
            done.append((p, vid, disp_name))
        else:
            with open(p, "w", encoding="utf-8") as f:
                f.write(fm + content)
            done.append((p, vid, disp_name))
    return done, skipped, counters


def main():
    if len(sys.argv) < 2:
        print("用法: python add_frontmatter.py <目录> [--dry-run] [--created DATE]")
        sys.exit(1)
    target = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    created = date.today().isoformat()
    if "--created" in sys.argv:
        i = sys.argv.index("--created")
        created = sys.argv[i + 1]
    # root = 含 13-competitors 的 materials 根
    root = target
    while "13-competitors" not in os.listdir(root) and os.path.dirname(target) != target:
        target_is_13 = os.path.basename(os.path.abspath(target)) == "13-competitors"
        if target_is_13:
            root = os.path.dirname(os.path.abspath(target))
            break
        root = os.path.dirname(os.path.abspath(root))
        if root == os.path.dirname(root):
            break
    done, skipped, counters = process_dir(target, root, created, dry_run)
    tag = "[DRY-RUN] " if dry_run else ""
    print(f"{tag}处理 {len(done)} 个文件，跳过(已有frontmatter) {len(skipped)}")
    print(f"{tag}各竞品计数: {counters}")
    print(f"\n{tag}前 15 条预览:")
    for p, vid, name in done[:15]:
        rel = os.path.relpath(p)
        print(f"  {vid}  {name[:40]:40s}  {rel}")
    if len(done) > 15:
        print(f"  ... 还有 {len(done)-15} 条")


if __name__ == "__main__":
    main()
