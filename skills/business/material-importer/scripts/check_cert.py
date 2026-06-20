"""证照有效期检查 — 扫描素材库 frontmatter，输出有效期状态报告。支持 --json 输出供 Agent 程序化读取。"""

import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml


def parse_frontmatter(file_path: str) -> dict | None:
    """解析 Markdown 文件中的 YAML frontmatter。"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def parse_date(date_str: str) -> date | None:
    """解析日期字符串，支持多种格式。"""
    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%Y年%m月%d日", "%Y年%m月%d号",
        "%m/%d/%Y", "%d/%m/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def extract_date_from_text(text: str) -> date | None:
    """从文本中提取日期 - 简单的正则匹配。"""
    patterns = [
        r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})",
        r"(\d{4}年\d{1,2}月\d{1,2}[日号])",
        r"有效期[至到：:]\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})",
        r"发证日期[：:]\s*(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return parse_date(match.group(1))
    return None


def check_status(expires: date, today: date | None = None) -> tuple[str, str]:
    """检查有效期状态。"""
    if today is None:
        today = date.today()

    days = (expires - today).days

    if days < 0:
        return "❌ 已过期", "expired"
    elif days <= 30:
        return f"⚠️ 即将过期（{days}天后）", "critical"
    elif days <= 90:
        return f"⚠️ 即将过期（{days}天后）", "warning"
    else:
        return f"✅ 有效（{days}天后）", "valid"


def scan_materials(materials_dir: str) -> list[dict]:
    """扫描素材库中所有证照类文件，检查有效期。"""
    results = []
    today = date.today()

    for root, dirs, files in os.walk(materials_dir):
        if "raw" in root:
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            file_path = os.path.join(root, f)
            fm = parse_frontmatter(file_path)
            if not fm:
                continue

            item = {
                "file": os.path.relpath(file_path, materials_dir),
                "name": fm.get("name", f),
                "type": fm.get("type", ""),
                "expires": fm.get("expires"),
                "issued": fm.get("issued"),
                "issuer": fm.get("issuer"),
                "status": "",
                "status_label": "",
                "days_left": None,
            }

            if item["expires"]:
                expire_date = parse_date(str(item["expires"]))
                if expire_date:
                    label, status = check_status(expire_date, today)
                    item["status"] = status
                    item["status_label"] = label
                    item["days_left"] = (expire_date - today).days

            results.append(item)

    return results


def print_json_report(results: list[dict]) -> None:
    """输出 JSON 格式报告供 Agent 程序化读取。"""
    cert_results = [r for r in results if r["expires"]]
    no_expiry = [r for r in results if not r["expires"]]
    expired = sum(1 for r in cert_results if r["status"] == "expired")
    critical = sum(1 for r in cert_results if r["status"] == "critical")
    warning = sum(1 for r in cert_results if r["status"] == "warning")
    valid = sum(1 for r in cert_results if r["status"] == "valid")

    report = {
        "tool": "check_cert",
        "timestamp": str(date.today()),
        "summary": {
            "total": len(cert_results),
            "no_expiry": len(no_expiry),
            "expired": expired,
            "critical": critical,
            "warning": warning,
            "valid": valid,
        },
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def print_report(results: list[dict]) -> None:
    """打印有效期检查报告。"""
    cert_results = [r for r in results if r["expires"]]
    no_expiry = [r for r in results if not r["expires"]]

    print("\n" + "=" * 60)
    print("  证照有效期检查报告")
    print("=" * 60)
    print(f"  检查日期: {date.today()}")
    print(f"  证照总数: {len(cert_results)}")
    print(f"  无有效期: {len(no_expiry)} 条")
    print("-" * 60)

    if not cert_results:
        print("  ℹ️ 所有证照均未设置有效期")
        return

    status_order = {"expired": 0, "critical": 1, "warning": 2, "valid": 3}
    cert_results.sort(key=lambda x: status_order.get(x["status"], 99))

    for r in cert_results:
        print(f"\n  {r['status_label']}")
        print(f"    文件: {r['file']}")
        if r["name"]:
            print(f"    名称: {r['name']}")
        if r["expires"]:
            print(f"    有效期至: {r['expires']}")
        if r["issuer"]:
            print(f"    发证机构: {r['issuer']}")

    expired = sum(1 for r in cert_results if r["status"] == "expired")
    critical = sum(1 for r in cert_results if r["status"] == "critical")
    warning = sum(1 for r in cert_results if r["status"] == "warning")
    valid = sum(1 for r in cert_results if r["status"] == "valid")

    print("\n" + "-" * 60)
    print(f"  统计: ❌ {expired} 已过期 | ⚠️ {critical} 紧急 | ⚠️ {warning} 提醒 | ✅ {valid} 有效")
    print("=" * 60 + "\n")


def suggest_expiry(file_path: str) -> None:
    """分析素材文件内容，尝试提取有效期信息。"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    fm = parse_frontmatter(file_path)
    if fm and fm.get("expires"):
        return  # 已有有效期

    dates = []
    for line in content.split("\n"):
        d = extract_date_from_text(line)
        if d:
            dates.append(d)

    if dates:
        print(f"  💡 发现可能的日期: {', '.join(str(d) for d in dates)}")
        print(f"     请手动确认并添加到 frontmatter: expires: YYYY-MM-DD")


def main():
    use_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        materials_dir = "materials"
    else:
        materials_dir = args[0]

    if "--suggest" in sys.argv and len(args) >= 1:
        file_path = sys.argv[1]
        print(f"🔍 分析文件: {file_path}")
        suggest_expiry(file_path)
        return

    results = scan_materials(materials_dir)

    if use_json:
        print_json_report(results)
        return

    print(f"🔍 扫描素材库: {materials_dir}")
    print_report(results)

    # 对没有有效期的证照类文件，尝试提取日期
    print("💡 以下证照类文件未设置有效期，尝试自动发现：")
    for r in results:
        if not r["expires"] and r["type"] in ("资质荣誉", "证照"):
            full_path = os.path.join(materials_dir, r["file"])
            print(f"\n  📄 {r['file']}")
            suggest_expiry(full_path)


if __name__ == "__main__":
    main()