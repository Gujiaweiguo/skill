"""OCR 结果 → 结构化 Markdown 转换器。

读取 _extracted/tables.jsonl，按业务域分组生成 .md 文件，
使 product-prd-generator 的 _parse_markdown() 能自动提取表结构作为功能需求。

放置在 _extracted/ 目录下，_iter_markdown_files() 会自动发现。
"""
import json
import sys
from collections import defaultdict
from pathlib import Path


# 业务域分组规则（表名前缀 → 业务域中文名）
_DOMAIN_GROUPS = [
    ("合同主数据",     ["m3contract", "m3rdbcontract"]),
    ("合同申请单",     ["m3newcontract", "m3modifycontract", "m3cancelcontract", "m3finishcontract"]),
    ("合同条款",       ["m3rdbc"]),
    ("铺位管理",       ["m3position", "m3countermandposition", "m3deliverybill"]),
    ("商户租户",       ["m3tenant", "m3merchant", "m3assistant", "m3typetag"]),
    ("品牌管理",       ["m3brand", "m3tenantbrand"]),
    ("财务账款",       ["acacc", "aclaccount", "aclsettle"]),
    ("财务基础",       ["acsubject", "acbank", "acpayment"]),
    ("销售管理",       ["m3sale", "m3gift", "m3product"]),
    ("组织用户",       ["m3org", "m3user", "m3role"]),
]

# 表名中文名修正（OCR 识别的中文有时不准确）
_NAME_OVERRIDES = {
    "m3rdbcsettleterm": "结算周期条款",
    "m3rdbcsettleperiod": "结算周期明细",
    "m3rdbccustomterm": "自定义条款",
    "m3rdbccustomproperty": "自定义属性",
    "m3rdbcdepositterm": "预存款条款",
    "m3rdbcdepositdtl": "预存款明细",
    "m3rdbcattterm": "附件条款",
    "m3rdbcattachment": "附件条款附件",
    "m3rdbcadjaccterm": "调租条款",
    "m3rdbcadjaccdtl": "调租明细",
    "m3rdbcadjustaccamount": "科目调租明细",
    "m3rdbcfreeaccterm": "免租条款",
    "m3rdbcfreeaccdtl": "免租明细",
    "m3rdbcfreeaccamount": "科目免租明细",
    "m3rdbcoverdueterm": "滞纳金条款",
    "m3rdbcoverduesubject": "滞纳金明细",
    "m3rdbcnonexpenseterm": "一次性费用条款",
    "m3rdbcnonexpensedtl": "一次性费用条款明细",
    "m3rdbcfreecondterm": "免租条件条款",
    "m3rdbcfreeconddtl": "免租条件明细",
    "m3rdbcfreecondsubject": "免租条件科目明细",
    "m3rdbcenteryterm": "进场条款",
    "m3rdbccontract": "合同表(关系数据库)",
    "m3rdbccontractbrand": "合同品牌",
    "m3rdbccontractcategory": "合同商品类别",
    "m3rdbccontractposition": "合同地理位置",
    "m3contract": "合同表(主数据)",
    "m3contractbrand": "合同品牌",
    "m3contractcategory": "合同商品类别",
    "m3contractposition": "合同地理位置",
    "m3contractcontent": "合同内容",
    "m3contracthistory": "合同历史记录",
    "m3contractparticipant": "合同参与者",
    "m3newcontractrequest": "新合同申请",
    "m3modifycontractrequest": "变更合同申请",
    "m3cancelcontractrequest": "作废合同申请",
    "m3finishcontractrequest": "结束合同申请",
    "m3contractrequestbrand": "合同申请品牌",
    "m3contractrequestcategory": "合同申请商品类别",
    "m3contractrequestcontent": "合同申请内容",
    "m3contractrequestposition": "合同申请位置",
}


def _classify_domain(table_name_lower: str) -> str:
    """根据表名前缀判断业务域。"""
    for domain, prefixes in _DOMAIN_GROUPS:
        for prefix in prefixes:
            if table_name_lower.startswith(prefix):
                return domain
    return "其他"


def convert(tables_jsonl: Path, output_md: Path, source_label: str = "海鼎业务逻辑OCR"):
    """将 tables.jsonl 转换为结构化 markdown。"""
    tables = []
    with tables_jsonl.open(encoding="utf-8") as f:
        for line in f:
            tables.append(json.loads(line))

    # 只保留 matched 和 fuzzy_matched 的表
    valid = [t for t in tables if t["validation_status"] in ("matched", "fuzzy_matched")]

    # 去重：同一张表只保留一条（优先 matched）
    seen: dict[str, dict] = {}
    for t in valid:
        key = t["table_name_calibrated"]
        if key not in seen or t["validation_status"] == "matched":
            seen[key] = t
    unique = list(seen.values())

    # 按业务域分组
    by_domain: dict[str, list[dict]] = defaultdict(list)
    for t in unique:
        domain = _classify_domain(t["table_name_calibrated"])
        by_domain[domain].append(t)

    # 按固定顺序输出域
    domain_order = [d for d, _ in _DOMAIN_GROUPS] + ["其他"]

    lines = [
        f"# {source_label}",
        "",
        f"> 从图片型资料中 OCR 提取的表结构（共 {len(unique)} 张表），",
        "> 已用 SQL DDL 校准表名和字段。",
        "> 本文由 ocr_to_features.py 自动生成，请勿手工编辑。",
        "",
    ]

    for domain in domain_order:
        entries = by_domain.get(domain, [])
        if not entries:
            continue
        entries.sort(key=lambda t: t["table_name_calibrated"])

        lines += [
            f"## {domain}",
            "",
        ]
        # Bold-heading format: _BOLD_HEADING regex captures **text** as heading,
        # text after it becomes nearby_text. This preserves field info.
        for t in entries:
            name = t["table_name_calibrated"]
            cn = _NAME_OVERRIDES.get(name, t.get("chinese_name", ""))
            fields = t.get("sql_fields", [])
            nfields = len(fields)
            status = "✅" if t["validation_status"] == "matched" else "🔶"
            field_str = ", ".join(fields[:12])
            if len(fields) > 12:
                field_str += f" ... (+{len(fields)-12})"
            cn_display = f"（{cn}）" if cn else ""
            lines.append(f"**数据结构 {name}{cn_display}**")
            lines.append("")
            lines.append(f"{nfields}字段 {status} {field_str}")
            lines.append("")

        lines.append("")

    output_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ {output_md.name}: {len(unique)} 张表, {len(by_domain)} 个业务域")
    return len(unique)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"用法: {sys.argv[0]} <tables.jsonl> <output.md> [source_label]")
        sys.exit(1)
    convert(Path(sys.argv[1]), Path(sys.argv[2]),
            sys.argv[3] if len(sys.argv) > 3 else "海鼎业务逻辑OCR")
