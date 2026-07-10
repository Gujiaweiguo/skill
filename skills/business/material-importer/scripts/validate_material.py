"""素材文件校验 — 检查 frontmatter 字段完整性。

用法:
  uv run {baseDir}/scripts/validate_material.py <文件/目录>
  uv run {baseDir}/scripts/validate_material.py <文件/目录> --json

校验规则:
  - 必须有 YAML frontmatter
  - 必须包含必填字段 (id, type, name, domain, status, created)
  - type 必须是合法值
  - domain 必须是合法标签（可配置）
  - status 必须是 complete/incomplete
  - 日期字段格式必须正确
  - created/updated 不能是未来日期
  - 素材类型特有字段检查（资质→expires, 案例→client 等）
"""

import json
import os
import re
import sys
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

import yaml


# --- 配置（可按需调整） ---
VALID_TYPES = {
    "公司概况", "资质荣誉", "产品方案", "案例", "实施方法论", "服务体系",
    "人员", "竞品资料", "客户资料",
    "业务知识", "方法论", "工具模板", "市场洞察",
}
VALID_DOMAINS = {"商管", "会员", "AI客服", "AI问数", "ChatBI", "通用", "资管"}
VALID_STATUSES = {"complete", "incomplete"}

REQUIRED_FIELDS = {"id", "type", "name", "domain", "status", "created"}
TYPE_SPECIFIC_FIELDS = {
    "资质荣誉": {"issued", "expires", "issuer", "cert_no"},
    "案例": {"client", "project"},
    "人员": {"role"},
}

DATE_FIELDS = {"created", "updated", "issued", "expires", "contract_period"}


def parse_frontmatter(file_path: str) -> tuple[dict[str, Any] | None, str | None]:
    """解析 frontmatter，返回 (data, error)。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return None, f"无法读取文件: {e}"

    if not content.startswith("---"):
        return None, "缺少 YAML frontmatter（不以 --- 开头）"

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, "YAML frontmatter 未闭合"

    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return None, f"YAML 解析错误: {e}"

    if not isinstance(data, dict):
        return None, "frontmatter 不是合法的键值对"

    return data, None


def validate_date(value: str, field_name: str) -> str | None:
    """验证日期字段格式，返回错误信息或 None。"""
    if not isinstance(value, str):
        return f"{field_name} 必须是字符串（当前: {type(value).__name__}）"

    # permanent 用于永久有效的资质（如软著）
    if value.strip().lower() == "permanent" and field_name in ("expires",):
        return None

    # contract_period 特殊处理
    if field_name == "contract_period":
        # 接受占位符（不报格式错误）
        if value.strip() in ("待补充", "有待补充", "待确认"):
            return None
        # 接受 "至" 分隔的日期范围
        if "至" in value:
            parts = value.split("至")
            if len(parts) == 2:
                for p in parts:
                    p = p.strip()
                    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
                        try:
                            datetime.strptime(p, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        return f"{field_name} 格式错误: {value}"
                return None
        # 接受 "-" 分隔的旧格式 YYYY.MM-YYYY.MM
        if "-" in value:
            parts = value.split("-")
            if len(parts) == 2:
                for p in parts:
                    if not re.match(r"\d{4}\.\d{1,2}", p.strip()):
                        return f"{field_name} 格式错误: {value}（期望如 2025.1-2026.1）"
                return None

    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%Y年%m月%d日", "%Y年%m月%d号",
    ]
    for fmt in formats:
        try:
            datetime.strptime(str(value).strip(), fmt)
            return None
        except ValueError:
            continue
    return f"{field_name} 日期格式无法解析: {value}"


def validate_file(file_path: str) -> dict[str, Any]:
    """校验单个素材文件，返回校验结果。"""
    rel_path = os.path.relpath(file_path)
    result = {
        "file": rel_path,
        "valid": False,
        "errors": [],
        "warnings": [],
        "fields": {},
    }

    data, error = parse_frontmatter(file_path)
    if error:
        result["errors"].append(error)
        return result
    if data is None:
        result["errors"].append("frontmatter 解析返回空")
        return result

    result["fields"] = {k: data.get(k) for k in REQUIRED_FIELDS}

    # 检查必填字段
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None or (isinstance(data[field], str) and data[field].strip() == ""):
            result["errors"].append(f"缺少必填字段: {field}")

    if result["errors"]:
        return result

    # 检查 type 合法性
    mat_type = data.get("type", "")
    if mat_type not in VALID_TYPES:
        result["warnings"].append(f"type 值不在已知类型中: {mat_type}（期望之一: {', '.join(sorted(VALID_TYPES))}）")

    # 检查 domain 合法性
    domains = data.get("domain", [])
    if isinstance(domains, str):
        domains = [domains]
    for d in domains:
        if d not in VALID_DOMAINS:
            result["warnings"].append(f"domain 值不在已知标签中: {d}（期望之一: {', '.join(sorted(VALID_DOMAINS))}）")

    # 检查 status 合法性
    status = data.get("status", "")
    if status not in VALID_STATUSES:
        result["warnings"].append(f"status 值不合法: {status}（期望: complete 或 incomplete）")

    # 检查日期字段
    for field in DATE_FIELDS:
        value = data.get(field)
        if value:
            error_msg = validate_date(value, field)
            if error_msg:
                result["warnings"].append(error_msg)

    # 检查未来日期
    today = date.today()
    for field in ("created", "updated"):
        value = data.get(field)
        if value:
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
                try:
                    parsed = datetime.strptime(str(value).strip(), fmt).date()
                    if parsed > today:
                        result["warnings"].append(f"{field} 是未来日期: {value}")
                    break
                except ValueError:
                    continue

    # 类型特有字段检查
    if mat_type in TYPE_SPECIFIC_FIELDS:
        for field in TYPE_SPECIFIC_FIELDS[mat_type]:
            if field not in data or not data[field]:
                result["warnings"].append(f"类型 '{mat_type}' 建议包含字段: {field}")

    # 通过校验
    result["valid"] = len(result["errors"]) == 0
    return result


def print_text_report(results: list[dict]) -> None:
    """输出文本格式校验报告。"""
    total = len(results)
    valid = sum(1 for r in results if r["valid"])
    invalid = total - valid

    print(f"\n{'=' * 60}")
    print(f"  素材文件校验报告")
    print(f"{'=' * 60}")
    print(f"  检查文件: {total}")
    print(f"  ✅ 通过: {valid}")
    print(f"  ❌ 未通过: {invalid}")
    print(f"{'-' * 60}")

    for r in results:
        icon = "✅" if r["valid"] else "❌"
        print(f"\n  {icon} {r['file']}")

        if r["errors"]:
            for e in r["errors"]:
                print(f"    🔴 {e}")

        if r["warnings"]:
            for w in r["warnings"]:
                print(f"    🟡 {w}")

    print(f"\n{'-' * 60}")
    print(f"  统计: ✅ {valid} 通过 | ❌ {invalid} 未通过")
    print(f"{'=' * 60}\n")


def print_json_report(results: list[dict]) -> None:
    """输出 JSON 格式校验报告（供 Agent 程序化读取）。"""
    report = {
        "tool": "validate_material",
        "timestamp": str(date.today()),
        "summary": {
            "total": len(results),
            "valid": sum(1 for r in results if r["valid"]),
            "invalid": sum(1 for r in results if not r["valid"]),
        },
        "files": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 2:
        print("用法: uv run scripts/validate_material.py <文件/目录> [--json]")
        sys.exit(1)

    target = sys.argv[1]
    use_json = "--json" in sys.argv

    results = []

    if os.path.isdir(target):
        for root, dirs, files in os.walk(target):
            if "/raw" in root or "\\raw" in root:
                continue
            for f in files:
                if f.endswith(".md"):
                    results.append(validate_file(os.path.join(root, f)))
    elif os.path.isfile(target):
        results.append(validate_file(target))
    else:
        print(f"文件不存在: {target}")
        sys.exit(1)

    if use_json:
        print_json_report(results)
    else:
        print_text_report(results)

    # 有错误时返回非零退出码
    if any(not r["valid"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
