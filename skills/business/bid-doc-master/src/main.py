"""
bid-doc-master CLI — 招标文件解析 + 内容包生成

用法:
    # 提取模式：读取招标文件，输出结构化 JSON 供 Agent 分析
    uv run python -m src.main extract <招标文件路径> [功能清单.xlsx] -o tender_raw.json

    # 生成模式：基于 TenderInfo JSON 生成内容包
    uv run python -m src.main generate tender_info.json --bidder "广州市蓝联科技有限公司" --slide

    # 一键模式（兼容旧用法，使用默认模板）
    uv run python -m src.main <招标文件路径> --bidder "广州市蓝联科技有限公司"
"""

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from .generator import generate_commercial_bid, generate_slide_content, generate_technical_bid
from .models import TenderInfo
from .reader import read_document


def _resolve_output_dir(bidding_path: str, project_name: str) -> Path:
    """确定输出目录"""
    lanlnk_base = os.environ.get("LANLNK_BASE", "")
    if lanlnk_base:
        base = Path(lanlnk_base) / "bidding" / (project_name or Path(bidding_path).stem)
    else:
        base = Path(bidding_path).parent.resolve()
    content_dir = base / "content-packages"
    content_dir.mkdir(parents=True, exist_ok=True)
    return content_dir


def _read_function_list(path: str) -> list[dict]:
    """读取功能清单 Excel"""
    items = []
    try:
        fl_doc = read_document(path)
        for table in fl_doc.tables:
            for row in table.rows:
                if len(row) >= 3:
                    items.append({
                        "module": row[0] if len(row) > 0 else "",
                        "function": row[1] if len(row) > 1 else "",
                        "description": row[2] if len(row) > 2 else "",
                        "priority": row[3] if len(row) > 3 else "",
                    })
    except Exception as e:
        print(f"⚠️ 读取功能清单失败: {e}", file=sys.stderr)
    return items


# ── 子命令: extract ──────────────────────────────────────────────

def cmd_extract(args):
    """提取招标文件原始数据 → JSON"""
    if args.verbose:
        print(f"📄 招标文件: {args.bidding_file}")
        if args.function_list:
            print(f"📊 功能清单: {args.function_list}")

    doc = read_document(args.bidding_file)
    function_items = _read_function_list(args.function_list) if args.function_list else []

    if args.verbose:
        print(f"   ✅ 读取成功: {doc.file_type} 格式")
        print(f"   📝 标题: {doc.title}")
        print(f"   📄 文本长度: {len(doc.text_content)} 字符")
        print(f"   📊 表格: {len(doc.tables)} 个")

    # 构建输出 JSON
    raw = {
        "file_path": doc.file_path,
        "file_type": doc.file_type,
        "title": doc.title,
        "text_content": doc.text_content,
        "tables": [
            {"headers": t.headers, "rows": t.rows}
            for t in doc.tables
        ],
        "function_list": function_items,
        "images": [
            {"path": img.path, "alt_text": img.alt_text, "source": img.source}
            for img in doc.images
        ],
    }

    output = args.output or str(Path(args.bidding_file).with_suffix(".raw.json"))
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ 原始数据已提取: {output}")
    print(f"   📝 文本: {len(doc.text_content)} 字符")
    print(f"   📊 表格: {len(doc.tables)} 个")
    print(f"   📋 功能清单: {len(function_items)} 项")
    print(f"\n下一步: Agent 分析此 JSON，填充 TenderInfo 后调用 generate 子命令")


# ── 子命令: generate ─────────────────────────────────────────────

def _load_tender_info(path: str) -> TenderInfo:
    """从 JSON 文件加载 TenderInfo"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return TenderInfo(
        project_name=data.get("project_name", ""),
        purchaser=data.get("purchaser", ""),
        project_no=data.get("project_no", ""),
        budget=data.get("budget", ""),
        service_period=data.get("service_period", ""),
        deadline=data.get("deadline", ""),
        delivery_place=data.get("delivery_place", ""),
        qualification_requirements=data.get("qualification_requirements", []),
        substantive_clauses=data.get("substantive_clauses", []),
        technical_requirements=data.get("technical_requirements", []),
        scope=data.get("scope", ""),
        scoring_method=data.get("scoring_method", ""),
        scoring_items=data.get("scoring_items", []),
        function_list=data.get("function_list", []),
        pricing_requirements=data.get("pricing_requirements", ""),
        format_requirements=data.get("format_requirements", ""),
        format_overrides=data.get("format_overrides", {}),
        personnel_requirements=data.get("personnel_requirements", []),
        service_level_requirements=data.get("service_level_requirements", []),
        timeline_requirements=data.get("timeline_requirements", []),
        required_documents=data.get("required_documents", []),
        raw_text=data.get("raw_text", ""),
        key_response_items=data.get("key_response_items", []),
    )


def cmd_generate(args):
    """基于 TenderInfo JSON 生成内容包"""
    tender = _load_tender_info(args.tender_info)

    if args.verbose:
        print(f"📖 招标信息: {tender.project_name}")
        print(f"🏢 采购人: {tender.purchaser}")
        print(f"📋 资质要求: {len(tender.qualification_requirements)} 项")
        print(f"👥 人员要求: {len(tender.personnel_requirements)} 项")
        print(f"🛠️ SLA要求: {len(tender.service_level_requirements)} 项")
        print(f"📅 里程碑: {len(tender.timeline_requirements)} 项")
        print(f"🎯 重点响应: {len(tender.key_response_items)} 项")

    content_dir = _resolve_output_dir(
        args.tender_info,
        tender.project_name or Path(args.tender_info).stem,
    )

    stem = Path(args.tender_info).stem
    type_suffix = "技术标" if args.type == "technical" else "商务标"
    output_path = str(content_dir / f"{stem}_{type_suffix}.word-content.md")

    template = args.template or (
        "bidding-technical" if args.type == "technical" else "bidding-commercial"
    )

    if args.type == "technical":
        result_path = generate_technical_bid(
            tender, output_path, bidder=args.bidder, template=template,
        )
    else:
        result_path = generate_commercial_bid(
            tender, output_path, bidder=args.bidder, template=template,
        )

    print(f"\n✅ Word 内容包生成成功!")
    print(f"📁 {result_path}")

    if args.slide:
        slide_path = str(content_dir / f"{stem}_述标PPT.content.md")
        slide_result = generate_slide_content(
            tender, slide_path, bidder=args.bidder or "投标人",
        )
        print(f"\n✅ 述标 PPT 内容包生成成功!")
        print(f"📁 {slide_result}")


# ── 子命令: full（兼容旧用法）────────────────────────────────────

def cmd_full(args):
    """一键模式：读取文件 + 默认模板生成"""
    if args.verbose:
        print(f"📄 招标文件: {args.bidding_file}")
        if args.function_list:
            print(f"📊 功能清单: {args.function_list}")
        print(f"🏢 投标人: {args.bidder or '未指定'}")

    doc = read_document(args.bidding_file)
    function_items = _read_function_list(args.function_list) if args.function_list else []

    if args.verbose:
        print(f"   ✅ 读取成功: {doc.file_type} 格式")
        print(f"   📝 标题: {doc.title}")

    tender = TenderInfo(
        project_name=doc.title,
        raw_text=doc.text_content,
        function_list=function_items,
    )

    content_dir = _resolve_output_dir(args.bidding_file, doc.title)
    stem = Path(args.bidding_file).stem
    type_suffix = "技术标" if args.type == "technical" else "商务标"
    output_path = str(content_dir / f"{stem}_{type_suffix}.word-content.md")
    template = args.template or (
        "bidding-technical" if args.type == "technical" else "bidding-commercial"
    )

    if args.type == "technical":
        result_path = generate_technical_bid(
            tender, output_path, bidder=args.bidder, template=template,
        )
    else:
        result_path = generate_commercial_bid(
            tender, output_path, bidder=args.bidder, template=template,
        )

    print(f"\n✅ Word 内容包生成成功!")
    print(f"📁 {result_path}")

    if args.slide:
        slide_path = str(content_dir / f"{stem}_述标PPT.content.md")
        slide_result = generate_slide_content(
            tender, slide_path, bidder=args.bidder or "投标人",
        )
        print(f"\n✅ 述标 PPT 内容包生成成功!")
        print(f"📁 {slide_result}")


# ── 入口 ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="bid-doc-master: 招标文件解析 → 内容包生成",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # extract 子命令
    p_extract = subparsers.add_parser("extract", help="提取招标文件原始数据 → JSON")
    p_extract.add_argument("bidding_file", help="招标文件路径 (.docx/.pdf/.pptx)")
    p_extract.add_argument("function_list", nargs="?", help="功能清单文件路径 (.xlsx)")
    p_extract.add_argument("-o", "--output", help="输出 JSON 路径")
    p_extract.add_argument("-v", "--verbose", action="store_true")

    # generate 子命令
    p_generate = subparsers.add_parser("generate", help="基于 TenderInfo JSON 生成内容包")
    p_generate.add_argument("tender_info", help="TenderInfo JSON 文件路径")
    p_generate.add_argument("--bidder", default="", help="投标人名称")
    p_generate.add_argument("--type", choices=["technical", "commercial"], default="technical")
    p_generate.add_argument("--slide", action="store_true", help="同时生成述标 PPT 内容包")
    p_generate.add_argument("--template", default="", help="word-master 模板名称")
    p_generate.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.command == "extract":
        cmd_extract(args)
    elif args.command == "generate":
        cmd_generate(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()