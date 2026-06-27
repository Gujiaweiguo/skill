# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "torch>=2.0",
#     "transformers>=4.40",
#     "pillow",
#     "einops",
#     "addict",
#     "easydict",
#     "accelerate",
#     "matplotlib",
#     "torchvision",
# ]
# ///
"""OCR 提取工具：用 DeepSeek-OCR-2 (VLM) 从图片型资料中提取结构化文本。

适用于 PPT/Word/Excel 转换后的 _media/ 目录中的图片，输出可直接用于
product-prd-generator 等下游 skill 的结构化 markdown 和 JSONL。

用法:
    uv run scripts/ocr_extract.py <input_dir> [<input_dir> ...] \
        [--sql-dir <dir>] [--output-dir <dir>] [--model <name>]

示例:
    # 提取海鼎业务逻辑 PPT 图片
    uv run scripts/ocr_extract.py \
        /path/to/raw/02-competitors/海鼎/业务逻辑 \
        --sql-dir /path/to/input/02-competitors/海鼎/数据结构 \
        --output-dir /path/to/raw/02-competitors/海鼎/业务逻辑/_extracted

输出文件:
    - slides.jsonl     每张图片的 OCR 结果（含 bbox、原始 markdown）
    - tables.jsonl     从 OCR 文本中提取的表名 + 中文释义 + SQL 校准状态
    - all-ocr.md       人类可读的汇总文档

技术方案:
    引擎: DeepSeek-OCR-2 (3B params, BF16, ~8GB VRAM)
    校准: 可选的 SQL DDL schema 索引，用于修正 OCR 形近字
    过滤: 自动跳过装饰性图片（页脚、logo 等，基于尺寸启发式）
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}

# 装饰性图片的典型尺寸（海鼎 PPT 页脚 logo 等）
_DECORATIVE_SIZES = {(128, 120)}

# 合同/财务/招商相关的表名前缀
_TABLE_PREFIXES = ("M3", "ACL", "AC", "m3", "acl", "ac")


@dataclass
class ImageRef:
    """待识别的图片引用。"""
    path: Path
    source_file: str  # 所属 markdown 文件名（不含路径）
    source_stem: str  # markdown 文件 stem


@dataclass
class OCRBlock:
    """OCR 输出的单个文本块。"""
    bbox: list[int]  # [x1, y1, x2, y2]
    text: str


@dataclass
class OCRResult:
    """单张图片的完整 OCR 结果。"""
    image_path: str
    source_file: str
    source_stem: str
    raw_markdown: str
    blocks: list[OCRBlock] = field(default_factory=list)
    duration_sec: float = 0.0
    error: str = ""


@dataclass
class TableRef:
    """从 OCR 文本中提取的表引用。"""
    table_name_raw: str  # OCR 原始识别（可能含形近字）
    table_name_calibrated: str  # SQL 校准后的表名（若匹配到）
    chinese_name: str  # 中文释义
    source_image: str
    source_file: str
    validation_status: str  # matched / fuzzy_matched / unmatched
    sql_fields: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 1: 图片扫描
# ---------------------------------------------------------------------------

def scan_images(input_dirs: list[Path]) -> list[ImageRef]:
    """扫描输入目录下的所有图片文件，自动过滤装饰性图片。

    扫描策略：
    - 递归搜索 *_media/ 子目录和直接图片文件
    - 通过 markdown 文件名（.pptx.md / .docx.md）推断来源
    - 跳过 128x120 等典型装饰尺寸的图片
    """
    from PIL import Image

    results: list[ImageRef] = []
    seen: set[str] = set()

    for input_dir in input_dirs:
        if not input_dir.exists():
            print(f"  ⚠️ 目录不存在: {input_dir}")
            continue

        # 收集所有图片
        for img_path in sorted(input_dir.rglob("*")):
            if img_path.suffix.lower() not in _IMAGE_EXTS:
                continue
            if not img_path.is_file():
                continue

            key = str(img_path.resolve())
            if key in seen:
                continue

            # 尺寸过滤：跳过装饰性图片
            try:
                with Image.open(img_path) as im:
                    w, h = im.size
                if (w, h) in _DECORATIVE_SIZES:
                    continue
                # 跳过极小图片（< 50x50）
                if w < 50 or h < 50:
                    continue
            except Exception:
                continue  # 无法打开的图片跳过

            # 推断来源 markdown 文件
            parent = img_path.parent
            media_stem = parent.name  # e.g. "CRE招商资料数据逻辑介绍_media"
            if media_stem.endswith("_media"):
                source_stem = media_stem[:-6]
            else:
                source_stem = img_path.stem

            results.append(ImageRef(
                path=img_path,
                source_file=f"{source_stem}.md",
                source_stem=source_stem,
            ))
            seen.add(key)

    return results


# ---------------------------------------------------------------------------
# Phase 2: SQL Schema 索引
# ---------------------------------------------------------------------------

def build_sql_index(sql_dir: Path | None) -> dict[str, list[str]]:
    """从 SQL DDL 文件构建表名→字段列表的索引（全部小写）。

    支持 MySQL dump 格式的 CREATE TABLE 语句。
    """
    index: dict[str, list[str]] = {}
    if sql_dir is None or not sql_dir.exists():
        return index

    sql_files = sorted(sql_dir.glob("*.sql"))
    if not sql_files:
        print(f"  ⚠️ SQL 目录下无 .sql 文件: {sql_dir}")
        return index

    # 匹配 CREATE TABLE `tablename` ( ... );
    create_re = re.compile(
        r"CREATE\s+TABLE\s+[`'\"]?(\w+)[`'\"]?\s*\((.*?)\)\s*(?:ENGINE|DEFAULT|;|$)",
        re.IGNORECASE | re.DOTALL,
    )
    # 匹配字段定义行：`fieldName` type ...
    field_re = re.compile(r"^[`'\"]?(\w+)[`'\"]?\s+", re.MULTILINE)

    for sql_file in sql_files:
        text = sql_file.read_text(encoding="utf-8", errors="replace")
        for m in create_re.finditer(text):
            table_name = m.group(1).lower()
            body = m.group(2)
            # 提取字段名（排除 KEY/PRIMARY/CONSTRAINT 等非字段行）
            fields = []
            for line in body.split("\n"):
                line = line.strip().rstrip(",")
                if not line:
                    continue
                # 跳过约束行
                upper = line.upper()
                if any(upper.startswith(kw) for kw in (
                    "PRIMARY KEY", "UNIQUE KEY", "KEY ", "CONSTRAINT",
                    "FOREIGN KEY", "INDEX ", "FULLTEXT", "CHECK",
                )):
                    continue
                fm = field_re.match(line)
                if fm:
                    fields.append(fm.group(1).lower())
            if fields:
                index[table_name] = fields

    print(f"  📊 SQL 索引: {len(index)} 张表，来自 {len(sql_files)} 个文件")
    return index


# ---------------------------------------------------------------------------
# Phase 3: 模型加载 + OCR
# ---------------------------------------------------------------------------

def load_model(model_name: str):
    """加载 DeepSeek-OCR-2 模型和 processor。

    使用 eager attention（兼容 Blackwell GPU，无需 flash-attn）。
    """
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    print(f"  🤖 加载模型: {model_name}")
    t0 = time.time()
    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForImageTextToText.from_pretrained(
        model_name,
        dtype=torch.bfloat16,
        device_map="cuda",
        trust_remote_code=True,
    )
    model = model.eval()
    vram_gb = 0.0
    try:
        import torch as _t
        free, total = _t.cuda.mem_get_info()
        vram_gb = (total - free) / 1e9
    except Exception:
        pass
    print(f"     加载完成 {time.time()-t0:.1f}s, VRAM {vram_gb:.1f}GB")
    return model, processor


def ocr_single_image(model, processor, image_path: Path) -> tuple[str, float]:
    """对单张图片执行 OCR，返回 (markdown文本, 耗时秒)。"""
    import torch

    prompt = "<image>\n<|grounding|>Convert the document to markdown."
    inputs = processor(
        images=str(image_path),
        text=prompt,
        return_tensors="pt",
    ).to(model.device, torch.bfloat16)

    t0 = time.time()
    with torch.no_grad():
        out = model.generate(**inputs, do_sample=False, max_new_tokens=4096)
    dt = time.time() - t0

    result = processor.decode(
        out[0, inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )
    return result, dt


# ---------------------------------------------------------------------------
# Phase 4: 表名提取与校准
# ---------------------------------------------------------------------------

# 匹配 OCR 文本中的表名（M3RDBC*, ACL*, AC* 等驼峰式标识符）
_TABLE_NAME_RE = re.compile(
    r"\b((?:M3|m3|M3RDB|m3rdb|ACL|acl|AC|ac)[A-Za-z]{2,30}\d?)\b"
)


def extract_table_refs(ocr_text: str, image_path: str, source_file: str,
                       sql_index: dict[str, list[str]]) -> list[TableRef]:
    """从 OCR 文本中提取表名引用，并用 SQL 索引校准。

    校准策略：
    1. 精确匹配（小写）→ matched
    2. 模糊匹配（difflib ratio > 0.85）→ fuzzy_matched
    3. 无匹配 → unmatched
    """
    refs: list[TableRef] = []
    seen_tables: set[str] = set()

    for m in _TABLE_NAME_RE.finditer(ocr_text):
        raw = m.group(1)
        if raw.lower() in seen_tables:
            continue
        seen_tables.add(raw.lower())

        # 提取附近的中文释义（表名后 30 字符内的中文）
        after = ocr_text[m.end():m.end() + 50]
        cn_match = re.search(r"[\u4e00-\u9fff]{2,20}", after)
        chinese_name = cn_match.group(0) if cn_match else ""

        # SQL 校准
        raw_lower = raw.lower()
        calibrated = raw
        status = "unmatched"
        sql_fields: list[str] = []

        if raw_lower in sql_index:
            calibrated = raw_lower
            status = "matched"
            sql_fields = sql_index[raw_lower]
        elif sql_index:
            # 模糊匹配
            candidates = difflib.get_close_matches(
                raw_lower, list(sql_index.keys()), n=1, cutoff=0.85
            )
            if candidates:
                calibrated = candidates[0]
                status = "fuzzy_matched"
                sql_fields = sql_index[calibrated]

        refs.append(TableRef(
            table_name_raw=raw,
            table_name_calibrated=calibrated,
            chinese_name=chinese_name,
            source_image=image_path,
            source_file=source_file,
            validation_status=status,
            sql_fields=sql_fields[:20],  # 限制字段数量
        ))

    return refs


# ---------------------------------------------------------------------------
# Phase 5: 输出
# ---------------------------------------------------------------------------

def write_slides_jsonl(results: list[OCRResult], output_dir: Path) -> Path:
    """写入 slides.jsonl — 每行一张图片的 OCR 结果。"""
    path = output_dir / "slides.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for r in results:
            # 解析 OCR 输出中的 bbox 块
            blocks = _parse_ocr_blocks(r.raw_markdown)
            record = {
                "image_path": str(r.image_path),
                "source_file": r.source_file,
                "source_stem": r.source_stem,
                "raw_markdown": r.raw_markdown,
                "blocks": [{"bbox": b["bbox"], "text": b["text"]} for b in blocks],
                "duration_sec": round(r.duration_sec, 1),
                "error": r.error,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _parse_ocr_blocks(text: str) -> list[dict]:
    """解析 DeepSeek-OCR-2 输出中的 text[[x1,y1,x2,y2]] bbox 块。"""
    blocks = []
    parts = re.split(r"text\[\[([0-9,\s]+)\]\]", text)
    for i in range(1, len(parts), 2):
        bbox_str = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        try:
            bbox = [int(x.strip()) for x in bbox_str.split(",")]
        except ValueError:
            continue
        if len(bbox) == 4:
            blocks.append({"bbox": bbox, "text": content.strip()})
    return blocks


def write_tables_jsonl(table_refs: list[TableRef], output_dir: Path) -> Path:
    """写入 tables.jsonl — 每行一个表名引用。"""
    path = output_dir / "tables.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for t in table_refs:
            f.write(json.dumps(asdict(t), ensure_ascii=False) + "\n")
    return path


def write_markdown_summary(results: list[OCRResult],
                           table_refs: list[TableRef],
                           output_dir: Path) -> Path:
    """写入 all-ocr.md — 人类可读的汇总文档。"""
    path = output_dir / "all-ocr.md"

    # 按来源文件分组
    by_source: dict[str, list[OCRResult]] = {}
    for r in results:
        by_source.setdefault(r.source_stem, []).append(r)

    lines = [
        "# OCR 提取结果汇总",
        "",
        f"- 图片总数: {len(results)}",
        f"- 表名引用: {len(table_refs)}",
        f"- 来源文件: {len(by_source)}",
        "",
    ]

    # 表名校准统计
    matched = sum(1 for t in table_refs if t.validation_status == "matched")
    fuzzy = sum(1 for t in table_refs if t.validation_status == "fuzzy_matched")
    unmatched = sum(1 for t in table_refs if t.validation_status == "unmatched")
    lines += [
        "## 表名校准统计",
        "",
        f"- ✅ 精确匹配: {matched}",
        f"- 🔶 模糊匹配: {fuzzy}",
        f"- ❓ 未匹配: {unmatched}",
        "",
    ]

    # 按来源文件输出
    for source_stem in sorted(by_source):
        items = by_source[source_stem]
        lines += [f"## {source_stem}", ""]
        for r in sorted(items, key=lambda x: x.image_path):
            img_name = Path(r.image_path).name
            lines += [f"### {img_name}", ""]
            if r.error:
                lines += [f"⚠️ 错误: {r.error}", ""]
            else:
                lines += [r.raw_markdown.strip(), ""]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_manifest(results: list[OCRResult], table_refs: list[TableRef],
                   image_refs: list[ImageRef], sql_table_count: int,
                   model_name: str, output_dir: Path) -> Path:
    """写入 manifest.json — 元数据。"""
    path = output_dir / "manifest.json"
    total_time = sum(r.duration_sec for r in results)
    manifest = {
        "tool": "ocr_extract.py",
        "model": model_name,
        "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "image_count": len(image_refs),
        "ocr_success_count": sum(1 for r in results if not r.error),
        "ocr_error_count": sum(1 for r in results if r.error),
        "table_ref_count": len(table_refs),
        "sql_table_count": sql_table_count,
        "total_ocr_time_sec": round(total_time, 1),
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _rebuild_from_slides(
    slides_path: Path, sql_index: dict[str, list[str]]
) -> tuple[list[OCRResult], list[TableRef]]:
    """从 slides.jsonl 重新载入所有结果，并重建表名引用。

    用于增量写入后的最终聚合阶段。
    """
    results: list[OCRResult] = []
    all_table_refs: list[TableRef] = []

    with slides_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            results.append(OCRResult(
                image_path=rec["image_path"],
                source_file=rec["source_file"],
                source_stem=rec["source_stem"],
                raw_markdown=rec.get("raw_markdown", ""),
                duration_sec=rec.get("duration_sec", 0.0),
                error=rec.get("error", ""),
            ))
            if rec.get("raw_markdown") and not rec.get("error"):
                tables = extract_table_refs(
                    rec["raw_markdown"],
                    rec["image_path"],
                    rec["source_file"],
                    sql_index,
                )
                all_table_refs.extend(tables)

    return results, all_table_refs


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="用 DeepSeek-OCR-2 从图片型资料中提取结构化文本",
    )
    parser.add_argument(
        "input_dirs", nargs="+", type=Path,
        help="输入目录（含 *_media/ 子目录或直接图片文件）",
    )
    parser.add_argument(
        "--sql-dir", type=Path, default=None,
        help="SQL DDL 文件目录（用于表名校准）",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="输出目录（默认: 第一个输入目录下的 _extracted/）",
    )
    parser.add_argument(
        "--model", default="deepseek-community/DeepSeek-OCR-2",
        help="模型名称（默认: deepseek-community/DeepSeek-OCR-2）",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="跳过已有 OCR 结果的图片（基于 slides.jsonl）",
    )
    args = parser.parse_args()

    # 输出目录
    output_dir = args.output_dir or args.input_dirs[0] / "_extracted"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("OCR 提取工具 (DeepSeek-OCR-2)")
    print("=" * 60)

    # Phase 1: 扫描图片
    print(f"\n📂 Phase 1: 扫描图片...")
    image_refs = scan_images(args.input_dirs)
    print(f"  发现 {len(image_refs)} 张待识别图片")

    if not image_refs:
        print("  ⚠️ 未找到图片，退出")
        sys.exit(1)

    # 已有结果处理
    existing: dict[str, str] = {}
    slides_path = output_dir / "slides.jsonl"
    if args.skip_existing and slides_path.exists():
        with slides_path.open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if not rec.get("error"):
                    existing[rec["image_path"]] = rec["raw_markdown"]
        print(f"  已有结果: {len(existing)} 张（将跳过）")

    # Phase 2: SQL 索引
    print(f"\n📊 Phase 2: 构建 SQL 索引...")
    sql_index = build_sql_index(args.sql_dir)

    # Phase 3: 加载模型
    print(f"\n🤖 Phase 3: 加载模型...")
    model, processor = load_model(args.model)

    # Phase 4: 批量 OCR（增量写入 checkpoint）
    to_process = [r for r in image_refs if str(r.path) not in existing]
    print(f"\n🔍 Phase 4: OCR 识别 ({len(to_process)}/{len(image_refs)} 张待处理)...")

    # 增量写入：每张图 OCR 完立即追加到 slides.jsonl
    slides_path = output_dir / "slides.jsonl"
    slides_fp = slides_path.open("a", encoding="utf-8")

    processed = len(existing)  # 已有的数量
    for i, ref in enumerate(image_refs, 1):
        img_str = str(ref.path)

        if img_str in existing:
            print(f"  [{i}/{len(image_refs)}] ⏭️ 跳过 {ref.path.name}")
            continue

        print(f"  [{i}/{len(image_refs)}] 🔍 {ref.path.name}...", end="", flush=True)
        try:
            raw_md, dt = ocr_single_image(model, processor, ref.path)
            blocks = _parse_ocr_blocks(raw_md)
            record = {
                "image_path": img_str,
                "source_file": ref.source_file,
                "source_stem": ref.source_stem,
                "raw_markdown": raw_md,
                "blocks": [{"bbox": b["bbox"], "text": b["text"]} for b in blocks],
                "duration_sec": round(dt, 1),
                "error": "",
            }
            slides_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            slides_fp.flush()
            n_tables = len(extract_table_refs(raw_md, img_str, ref.source_file, sql_index))
            processed += 1
            print(f" {dt:.1f}s, {n_tables} 表名 [✓已保存]")
        except Exception as e:
            record = {
                "image_path": img_str,
                "source_file": ref.source_file,
                "source_stem": ref.source_stem,
                "raw_markdown": "",
                "blocks": [],
                "duration_sec": 0.0,
                "error": str(e),
            }
            slides_fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            slides_fp.flush()
            print(f" ❌ {e}")

    slides_fp.close()
    print(f"  ✅ slides.jsonl 增量写入完成 ({processed} 条)")

    # Phase 5: 从 slides.jsonl 重建聚合输出
    print(f"\n📝 Phase 5: 重建聚合输出...")
    results, all_table_refs = _rebuild_from_slides(slides_path, sql_index)
    print(f"  ✅ 载入 {len(results)} 条 OCR 结果, {len(all_table_refs)} 条表名引用")

    tables_path = write_tables_jsonl(all_table_refs, output_dir)
    print(f"  ✅ {tables_path.name} ({len(all_table_refs)} 条)")

    md_path = write_markdown_summary(results, all_table_refs, output_dir)
    print(f"  ✅ {md_path.name}")

    manifest_path = write_manifest(
        results, all_table_refs, image_refs, len(sql_index), args.model, output_dir
    )
    print(f"  ✅ {manifest_path.name}")

    total_time = sum(r.duration_sec for r in results)
    print(f"\n✅ 完成! 总耗时 {total_time:.0f}s, 输出目录: {output_dir}")


if __name__ == "__main__":
    main()
