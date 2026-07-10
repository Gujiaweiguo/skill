#!/usr/bin/env python3
"""批量修复素材 frontmatter（双模式）。

模式A insert：无 frontmatter → 插入完整 frontmatter（type/domain 按目录映射）
模式B patch ：有 frontmatter 缺字段 → 文本级插入缺失必填字段，保留所有现有字段

用法:
  uv run scripts/fix_frontmatter.py <目录> [--dry-run]
幂等：重复运行只处理仍不合规的文件。
"""
import os
import re
import sys
import yaml
from datetime import date

REQUIRED = ["id", "type", "name", "domain", "status", "created"]

# 目录前缀(最长匹配) → (insert_type, insert_domain, patch_domain, id_prefix)
# insert_* 仅模式A用；patch_domain 仅模式B补 domain 用；id_prefix 生成缺失 id 用
CAT_CONFIG = {
    "11-cre-ai-skills": ("产品方案", ["AI问数"], None, "creai"),
    "03-products/user-guides": ("产品方案", ["AI问数"], None, "guide"),
    "12-bi-platform": ("产品方案", ["AI问数"], None, "bi"),
    "16-customers": ("客户资料", ["通用"], None, "customer"),
    "14-proposals": ("产品方案", ["商管"], ["商管"], "proposal"),
    "15-bidding": ("产品方案", ["商管"], ["商管"], "bid"),
    "08-asset-mgmt": (None, None, ["资管"], "asset"),
    "09-market-expansion": (None, None, ["商管"], "mkt"),
}


def match_config(rel_path: str):
    """最长前缀匹配目录配置。"""
    best = None
    best_len = -1
    for prefix, cfg in CAT_CONFIG.items():
        rp = rel_path.replace("\\", "/")
        if rp.startswith(prefix) and len(prefix) > best_len:
            best = cfg
            best_len = len(prefix)
    return best


def extract_name(content: str, filename: str) -> str:
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("# "):
            name = s[2:].strip()
            name = re.sub(r"^\*\*", "", name)  # 去加粗
            name = name.replace("---", "-")
            return name[:80]
    return os.path.splitext(filename)[0].replace("---", "-")[:80]


def parse_fm(content: str):
    """返回 (data_dict_or_None, before, fm_text, after)。"""
    if not content.startswith("---"):
        return None, content, "", ""
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content, "", ""
    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, content, "", ""
    if not isinstance(data, dict):
        return None, content, "", ""
    return data, parts[0], parts[1], parts[2]


def fmt_val(v):
    """格式化 frontmatter 值为 YAML 行内形式。"""
    if isinstance(v, list):
        return "[" + ", ".join(fmt_scalar(x) for x in v) + "]"
    return fmt_scalar(v)


def fmt_scalar(v):
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return str(v)


def quote(s: str) -> str:
    """YAML 双引号字符串转义（用于 f-string 生成 name 等字段）。"""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def gen_id(prefix: str, seq: int) -> str:
    return f"{prefix}-{date.today().strftime('%Y%m%d')}-{seq:03d}"


def process(target: str, root: str, dry_run: bool):
    counters = {}
    log = []
    for dirpath, _, fnames in os.walk(target):
        if os.sep + "raw" in dirpath or "/raw" in dirpath:
            continue
        for fn in sorted(fnames):
            if not fn.endswith(".md"):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace("\\", "/")
            cfg = match_config(rel)
            if not cfg:
                continue
            ins_type, ins_dom, patch_dom, id_prefix = cfg
            try:
                content = open(p, encoding="utf-8").read()
            except Exception:
                continue
            data, before, fm_text, after = parse_fm(content)
            name = extract_name(content, fn)

            if data is None:
                # === 模式A insert ===
                counters[id_prefix] = counters.get(id_prefix, 0) + 1
                vid = gen_id(id_prefix, counters[id_prefix])
                fm = (
                    f'id: "{vid}"\n'
                    f'type: "{ins_type}"\n'
                    f'name: "{quote(name)}"\n'
                    f'domain: {fmt_val(ins_dom)}\n'
                    f'status: "complete"\n'
                    f'created: "{date.today().isoformat()}"\n'
                )
                new_content = f"---\n{fm}---\n{before}"
                mode = "insert"
            else:
                # === 模式B patch：补缺失必填字段 ===
                missing = [f for f in REQUIRED
                           if f not in data or data.get(f) in (None, "", [])]
                if not missing:
                    continue
                # 计数 id（仅当需要生成 id 时）
                need_id_gen = "id" in missing
                if need_id_gen:
                    counters[id_prefix] = counters.get(id_prefix, 0) + 1
                adds = []
                for f in missing:
                    if f == "name":
                        adds.append(f'name: "{quote(name)}"')
                    elif f == "domain":
                        adds.append(f"domain: {fmt_val(patch_dom or ['通用'])}")
                    elif f == "status":
                        adds.append('status: "complete"')
                    elif f == "created":
                        # 优先用已有 date 字段
                        dval = data.get("date") or date.today().isoformat()
                        adds.append(f'created: "{dval}"')
                    elif f == "id":
                        adds.append(f'id: "{gen_id(id_prefix, counters.get(id_prefix,1))}"')
                    elif f == "type":
                        adds.append(f'type: "{ins_type or "产品方案"}"')
                # 文本级插入：在 fm_text 末尾追加缺失字段
                addition = "\n".join(adds) + "\n"
                new_fm = fm_text.rstrip("\n") + "\n" + addition
                new_content = f"---\n{new_fm}---\n{after}"
                mode = f"patch(+{','.join(missing)})"
            if not dry_run:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(new_content)
            log.append((mode, rel, name[:36]))
    return log, counters


def main():
    if len(sys.argv) < 2:
        print("用法: python fix_frontmatter.py <目录> [--dry-run]")
        sys.exit(1)
    target = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    root = os.path.dirname(os.path.abspath(target)) if os.path.basename(os.path.abspath(target)) != "materials" else os.path.abspath(target)
    if os.path.basename(os.path.abspath(target)) == "materials":
        root = os.path.abspath(target)
        target = os.path.join(root, "materials") if False else target
    # root 应为 materials 目录
    log, counters = process(target, root, dry_run)
    from collections import Counter
    mode_c = Counter(m.split("(")[0] for m, _, _ in log)
    tag = "[DRY-RUN] " if dry_run else ""
    print(f"{tag}处理 {len(log)} 个 | insert={mode_c.get('insert',0)} patch={mode_c.get('patch',0)}")
    print(f"{tag}id计数: {counters}")
    # 按 mode 分组预览
    for grp in ["insert", "patch"]:
        items = [(m, r, n) for m, r, n in log if m.startswith(grp)]
        if items:
            print(f"\n{tag}=== {grp} 前8条 ===")
            for m, r, n in items[:8]:
                print(f"  {m:22s} {n:36s} {r}")


if __name__ == "__main__":
    main()
