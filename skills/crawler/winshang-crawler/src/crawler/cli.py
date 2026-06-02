# -*- coding: utf-8 -*-
"""
赢商大数据爬虫 CLI 入口。

用法:
    # 爬取上海未开业项目
    uv run python -m src.crawler.cli --province 上海

    # 爬取全国已开业项目
    uv run python -m src.crawler.cli --status 已开业

    # 强制使用 Playwright 模式
    uv run python -m src.crawler.cli --province 北京 --driver playwright

    # 输出到自定义路径
    uv run python -m src.crawler.cli --province 广东 --output ./data/gd_projects.csv

    # 查询已爬取的数据
    uv run python -m src.crawler.cli query --city 上海
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


async def cmd_crawl(args: argparse.Namespace) -> None:
    """执行爬取"""
    from .service import crawl_and_save

    filepath = await crawl_and_save(
        province=args.province,
        status=args.status,
        output=args.output,
    )

    if filepath:
        print(f"\n✅ 数据已保存到: {filepath}")
        print(f"   执行: cat '{filepath}' 查看内容")
    else:
        print("\n⚠️  未获取到数据")


async def cmd_query(args: argparse.Namespace) -> None:
    """查询已爬取的 CSV 数据"""
    import pandas as pd

    filepath = args.file or "./data/winshang_data.csv"
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        print("   请先运行爬取命令生成数据文件")
        return

    df = pd.read_csv(filepath, encoding="utf-8-sig")
    print(f"\n📊 数据文件: {filepath}")
    print(f"   总记录数: {len(df)}")

    if args.province:
        from .service import _province_cities
        cities = _province_cities(args.province)
        if cities:
            mask = df["所在城市"].isin(cities)
            df = df[mask]
            print(f"   筛选省份「{args.province}」({len(cities)}市): {len(df)} 条")
        else:
            mask = df["所在城市"].str.contains(args.province, na=False)
            df = df[mask]
            print(f"   模糊筛选「{args.province}」: {len(df)} 条")

    if args.city:
        mask = df["所在城市"].str.contains(args.city, na=False)
        df = df[mask]
        print(f"   筛选城市「{args.city}」: {len(df)} 条")

    if args.status:
        mask = df["项目状态"].str.contains(args.status, na=False)
        df = df[mask]
        print(f"   筛选状态「{args.status}」: {len(df)} 条")

    if args.year:
        mask = df["开业时间"].astype(str).str.contains(args.year, na=False)
        df = df[mask]
        print(f"   筛选年份「{args.year}」: {len(df)} 条")

    if args.year_after:
        year_val = int(args.year_after)
        def _year_match(val: str) -> bool:
            if not val or val == "nan":
                return False
            import re
            nums = re.findall(r"\d{4}", str(val))
            return any(int(n) >= year_val for n in nums)
        mask = df["开业时间"].astype(str).apply(_year_match)
        df = df[mask]
        print(f"   筛选「{args.year_after}年之后」: {len(df)} 条")

    if args.limit:
        df = df.head(args.limit)

    if len(df) == 0:
        print("   无匹配数据")
        return

    # 显示概览
    cols = [c for c in ["项目名称", "项目状态", "所在城市", "商业面积", "项目类型", "开业时间"] if c in df.columns]
    if cols:
        print(f"\n   前 {min(len(df), args.limit or 10)} 条预览:")
        for i, row in df.head(args.limit or 10).iterrows():
            parts = [f"{row.get(c, '')}" for c in cols]
            print(f"   {i+1}. {' | '.join(parts)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="赢商大数据爬虫 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s crawl
  %(prog)s query --province 广东
  %(prog)s query --city 广州 --status 已开业 --year 2025 --limit 20
  %(prog)s query --status 未开业 --year-after 2020
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── crawl 子命令 ──
    crawl_parser = subparsers.add_parser("crawl", help="爬取项目数据")
    crawl_parser.add_argument(
        "--province", "-p",
        default="",
        help="省份/城市名，如 上海、北京、广东（空=全国）",
    )
    crawl_parser.add_argument(
        "--status", "-s",
        default="未开业",
        choices=["未开业", "已开业", ""],
        help="项目状态（默认: 未开业）",
    )
    crawl_parser.add_argument(
        "--output", "-o",
        default="./data/winshang_data.csv",
        help="输出 CSV 路径（默认: ./data/winshang_data.csv）",
    )
    crawl_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志输出",
    )

    # ── query 子命令 ──
    query_parser = subparsers.add_parser("query", help="查询已爬取的数据")
    query_parser.add_argument(
        "--file", "-f",
        default="./data/winshang_data.csv",
        help="CSV 文件路径",
    )
    query_parser.add_argument(
        "--province", "-p",
        default="",
        help="按省份筛选（如 广东、浙江、江苏）",
    )
    query_parser.add_argument(
        "--city", "-c",
        default="",
        help="按城市筛选",
    )
    query_parser.add_argument(
        "--status", "-s",
        default="",
        help="按项目状态筛选",
    )
    query_parser.add_argument(
        "--year", "-y",
        default="",
        help="按开业年份筛选（如 2025）",
    )
    query_parser.add_argument(
        "--year-after", "-ya",
        default="",
        help="开业年份在指定年份之后（如 2020）",
    )
    query_parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="显示条数上限（默认: 10）",
    )
    query_parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细日志输出",
    )

    args = parser.parse_args()

    if args.command == "query":
        setup_logging(args.verbose)
        asyncio.run(cmd_query(args))
    else:
        # 默认执行 crawl
        setup_logging(getattr(args, "verbose", False))
        asyncio.run(cmd_crawl(args))


if __name__ == "__main__":
    main()
