#!/usr/bin/env python3
"""关联 materials 里的图片引用到可达的 media/ 目录。

把 markitdown 转换后残留的断引用 ![alt](xxx.jpg) 修复为 ![alt](media/xxx.jpg)，
对应图片从 raw/<stem>_media/ 复制到 materials 各文件旁的 media/。
找不到图片源的转文字占位 [图片:alt]，杜绝断引用。

用法:
  uv run scripts/link_images.py <materials目录> [--raw-dir <raw目录>] [--dry-run]

策略（按优先级）:
  1. source 字段指向 raw md → 该 md 对应 _media → 数字匹配
  2. 文件名匹配 raw md → _media → 数字匹配
  3. 引用文件名全局搜所有 _media
  4. 全局数字匹配
  5. 都失败 → 文字占位 [图片:alt]

幂等：已修为 media/ 路径的跳过；只处理断引用。
"""
import os
import re
import shutil
import sys

import yaml


def parse_frontmatter(content: str) -> tuple[dict, str, str, str]:
    """返回 (data, fm_text, before, body)。before+fm_text+body 可重组文件。"""
    if not content.startswith("---"):
        return {}, "", "", content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, "", "", content
    try:
        data = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        data = {}
    return data, parts[1], parts[0], parts[2]


def build_raw_index(raw_dir: str) -> tuple[dict, dict]:
    """返回 (corename→[(raw_md,media_dir)], filename→path 全局图片索引)。"""
    raw_index: dict = {}
    global_media: dict = {}
    if not os.path.isdir(raw_dir):
        return raw_index, global_media
    for f in os.listdir(raw_dir):
        if not f.endswith(".md"):
            continue
        stem = f
        for ext in (".pptx.md", ".pdf.md", ".docx.md", ".xlsx.md", ".ppt.md", ".xls.md"):
            if stem.endswith(ext):
                stem = stem[: -len(ext)]
                break
        core = stem.split("_", 1)[-1] if "_" in stem else stem
        media_dir = os.path.join(raw_dir, stem + "_media")
        raw_index.setdefault(core, []).append((os.path.join(raw_dir, f), media_dir))
        if os.path.isdir(media_dir):
            for mf in os.listdir(media_dir):
                global_media.setdefault(mf, os.path.join(media_dir, mf))
    return raw_index, global_media


def find_raw_source(name: str, raw_index: dict) -> tuple[str | None, str | None]:
    """文件名 → (raw_md, media_dir)。"""
    n = name.replace("明源-", "")
    n = os.path.splitext(n)[0]
    if n in raw_index:
        for md, mdr in raw_index[n]:
            if os.path.isdir(mdr):
                return md, mdr
    for core, lst in raw_index.items():
        if n == core or (len(n) > 3 and (n in core or core in n)):
            for md, mdr in lst:
                if os.path.isdir(mdr):
                    return md, mdr
    return None, None


def main():
    if len(sys.argv) < 2:
        print("用法: uv run scripts/link_images.py <materials目录> [--raw-dir <raw目录>] [--dry-run]")
        sys.exit(1)
    mat_dir = sys.argv[1]
    raw_dir = os.path.join(os.path.dirname(mat_dir), "raw")
    dry_run = "--dry-run" in sys.argv
    if "--raw-dir" in sys.argv:
        raw_dir = sys.argv[sys.argv.index("--raw-dir") + 1]

    raw_index, global_media = build_raw_index(raw_dir)
    fixed = noraw = 0
    copied = 0

    for root, _, files in os.walk(mat_dir):
        if "/media" in root or root.endswith("media"):
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            try:
                content = open(p, encoding="utf-8").read()
            except Exception:
                continue
            # 只处理断引用（路径不以 media/ 开头）
            if not re.search(r"!\[[^\]]*\]\((?!media/)[^)]+\)", content):
                continue
            data, fm_text, before, body = parse_frontmatter(content)
            src = data.get("source", "")
            raw_md = None
            sm = re.search(r"raw/([^/\s]+\.md)", src)
            if sm and os.path.isfile(os.path.join(raw_dir, sm.group(1))):
                raw_md = os.path.join(raw_dir, sm.group(1))
            media_src = None
            if raw_md:
                stem = os.path.basename(raw_md)
                for ext in (".pptx.md", ".pdf.md", ".docx.md", ".xlsx.md", ".ppt.md", ".xls.md", ".md"):
                    if stem.endswith(ext):
                        stem = stem[: -len(ext)]
                        break
                media_src = os.path.join(raw_dir, stem + "_media")
            else:
                raw_md, media_src = find_raw_source(f, raw_index)

            media_by_num: dict = {}
            if media_src and os.path.isdir(media_src):
                for mf in os.listdir(media_src):
                    nums = re.findall(r"\d+", mf)
                    if nums:
                        media_by_num[int(nums[-1])] = mf

            media_dest = os.path.join(root, "media")
            if not dry_run:
                os.makedirs(media_dest, exist_ok=True)
            stats = {"copied": 0}

            def fix(m):
                alt, ref = m.group(1), m.group(2)
                refname = os.path.basename(ref)
                # 策略1: _media 数字匹配
                nums = re.findall(r"\d+", refname)
                if media_by_num and nums and int(nums[-1]) in media_by_num:
                    src_f = os.path.join(media_src, media_by_num[int(nums[-1])])
                    dst = os.path.join(media_dest, refname)
                    if not dry_run and not os.path.exists(dst):
                        shutil.copy2(src_f, dst)
                    stats["copied"] += 1
                    return f"![{alt}](media/{refname})"
                # 策略2: 全局文件名
                if refname in global_media:
                    dst = os.path.join(media_dest, refname)
                    if not dry_run and not os.path.exists(dst):
                        shutil.copy2(global_media[refname], dst)
                    stats["copied"] += 1
                    return f"![{alt}](media/{refname})"
                # 策略3: 全局数字
                if nums:
                    n = int(nums[-1])
                    for gf, gp in global_media.items():
                        gnums = re.findall(r"\d+", gf)
                        if gnums and int(gnums[-1]) == n:
                            dst = os.path.join(media_dest, refname)
                            if not dry_run and not os.path.exists(dst):
                                shutil.copy2(gp, dst)
                            stats["copied"] += 1
                            return f"![{alt}](media/{refname})"
                return f"[图片:{alt}]" if alt else "[图片]"

            new_body = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", fix, body)
            copied += stats["copied"]
            if not dry_run:
                open(p, "w", encoding="utf-8").write(f"---{fm_text}---{new_body}")
            fixed += 1

    tag = "[DRY-RUN] " if dry_run else ""
    print(f"{tag}修复 {fixed} 个文件, 复制 {copied} 张图, 转占位若干")


if __name__ == "__main__":
    main()
