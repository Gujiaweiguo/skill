"""海鼎数据字典 HTML → 结构化数据模型 Markdown。

从 CRE 4.1.0 版本数据字典.html 提取合同相关表的完整字段定义（含中文说明），
生成带字段级中文描述的数据模型文档，替代 OCR 简陋版本。
"""
import sys
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd


def parse_data_dict(html_path: str) -> dict:
    """解析数据字典 HTML，返回 {table_name: {desc, fields: [...]}}"""
    tables = pd.read_html(html_path, encoding="utf-8")
    idx = tables[0]
    index_dict = dict(zip(idx["表名"], idx["说明"]))

    result = {}
    for tname, tdesc in index_dict.items():
        pos = idx[idx["表名"] == tname].index[0]
        field_table_idx = int(pos) + 1
        if field_table_idx >= len(tables):
            continue
        ft = tables[field_table_idx]
        if "名称" not in ft.columns or "说明" not in ft.columns:
            continue
        fields = []
        for _, row in ft.iterrows():
            fields.append({
                "name": str(row.get("名称", "")),
                "type": str(row.get("数据类型", "")),
                "len": str(row.get("长度", "")),
                "nullable": str(row.get("允许空值", "")),
                "pk": str(row.get("主键", "")),
                "desc": str(row.get("说明", "")),
            })
        result[tname] = {"desc": tdesc, "fields": fields}
    return result


def split_hierarchy(desc) -> list[str]:
    """拆分管道分隔的描述层次。"""
    if not desc or (isinstance(desc, float)) or desc == "nan":
        return []
    return [p.strip() for p in str(desc).split("|")]


def classify_domain(tname: str, desc) -> str:
    """根据表名和描述判断业务域。"""
    desc_str = str(desc) if desc and not (isinstance(desc, float)) else ""
    parts = split_hierarchy(desc)
    last = parts[-1] if parts else desc_str

    if tname.startswith("m3newcontract") or tname.startswith("m3modifycontract") or \
       tname.startswith("m3cancelcontract") or tname.startswith("m3finishcontract"):
        return "合同申请单"
    if "结算周期" in last or "结算" in desc_str:
        return "结算周期"
    if "调租" in last or "调整" in last:
        return "调租条款"
    if "免租" in last:
        return "免租条款"
    if "预存款" in last or "deposit" in tname.lower():
        return "预存款条款"
    if "固定" in last and ("账款" in desc or "金额" in desc_str):
        return "固定账款"
    if "扣率" in last or "扣点" in last or "提成" in last:
        return "扣率提成"
    if "保底" in last:
        return "保底条款"
    if "清算" in last or "结清" in last:
        return "清算条款"
    if "滞纳金" in last or "逾期" in last:
        return "滞纳金条款"
    if "进场" in last or "入场" in last:
        return "进场条款"
    if "附件" in last:
        return "附件条款"
    if "自定义" in last:
        return "自定义条款"
    if "免租条件" in desc_str:
        return "免租条件"
    if "会员" in last or "积分" in last:
        return "会员折扣"
    if "银行" in last and "手续费" in desc_str:
        return "银行手续费"
    if "科目" in last and ("分摊" in desc or "比较" in desc_str):
        return "科目配置"
    if tname.startswith("m3rdbc"):
        return "其他条款"
    if tname.startswith("m3contract"):
        return "合同主数据"
    return "其他"


def generate_markdown(data: dict, output_path: Path, prefixes: list[str]):
    """生成结构化数据模型 Markdown。"""
    # Filter to specified prefixes
    tables = {k: v for k, v in data.items()
              if any(k.startswith(p) for p in prefixes)}

    # Group by domain
    by_domain = defaultdict(list)
    for tname, info in sorted(tables.items()):
        domain = classify_domain(tname, info["desc"])
        by_domain[domain].append((tname, info))

    # Domain display order
    domain_order = [
        "合同主数据", "合同申请单",
        "结算周期", "固定账款", "保底条款", "扣率提成",
        "调租条款", "免租条款", "免租条件", "预存款条款",
        "滞纳金条款", "进场条款", "清算条款", "银行手续费",
        "会员折扣", "附件条款", "自定义条款", "科目配置",
        "其他条款", "其他",
    ]

    lines = [
        "# 海鼎合同数据模型（数据字典）",
        "",
        f"> 从 CRE 4.1.0 数据字典提取的 {len(tables)} 张合同相关表，",
        "> 含字段级中文说明、数据类型、约束条件。",
        "> 本文由 datadict_to_features.py 自动生成。",
        "",
    ]

    for domain in domain_order:
        entries = by_domain.get(domain, [])
        if not entries:
            continue
        lines.append(f"## {domain}（{len(entries)} 张表）")
        lines.append("")

        for tname, info in entries:
            desc = info["desc"]
            fields = info["fields"]
            # Skip audit fields (uuid, fversion, lastModified, etc.)
            audit_fields = {"uuid", "fversion", "lastmodified", "lastmodifierid",
                          "lastmodifierns", "lastmodifier", "versiontime",
                          "created", "creatorid", "creatorns", "creator",
                          "permgrouptitle", "permgroupid", "discriminator"}
            business_fields = [f for f in fields if f["name"].lower() not in audit_fields]

            lines.append(f"### `{tname}`（{desc}）")
            lines.append(f"共 {len(fields)} 字段（其中业务字段 {len(business_fields)}）")
            lines.append("")

            if business_fields:
                lines.append("| 字段名 | 类型 | 说明 |")
                lines.append("| --- | --- | --- |")
                for f in business_fields:
                    name = f["name"]
                    dtype = f["type"]
                    if f["len"] and f["len"] != "0":
                        dtype = f"{dtype}({f['len']})"
                    desc_text = f["desc"].replace("|", "／") if f["desc"] else "—"
                    lines.append(f"| {name} | {dtype} | {desc_text} |")
                lines.append("")

        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ {output_path.name}: {len(tables)} 张表, {len(by_domain)} 个域")
    return len(tables)


if __name__ == "__main__":
    html = sys.argv[1]
    output = Path(sys.argv[2])
    prefixes = sys.argv[3].split(",") if len(sys.argv) > 3 else ["m3contract", "m3rdbc", "m3newcontract", "m3modifycontract", "m3cancelcontract", "m3finishcontract"]
    data = parse_data_dict(html)
    generate_markdown(data, output, prefixes)
