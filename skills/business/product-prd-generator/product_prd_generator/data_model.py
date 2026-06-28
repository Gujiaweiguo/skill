from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_DATA_DICT_GLOB = "**/_extracted/haiding-*-model.md"
_HEADING_RE = re.compile(r"^###\s+`(\w+)`（(.+?)）")
_FIELD_RE = re.compile(r"^\|\s*(\w+)\s*\|\s*\S+\s*\|\s*(.+?)\s*\|")
_DOMAIN_TITLE_RE = re.compile(r"^##\s+(.+?)（(\d+)\s*张表）")
_NOISE_CN = {"—", "nan", "null", "None", ""}

_PREFIX_TO_MODULE: list[tuple[tuple[str, ...], str]] = [
    (("m3contract", "m3rdbc", "m3newcontract", "m3modifycontract",
      "m3cancelcontract", "m3finishcontract", "m3collect"), "合同管理"),
    (("m3position", "blp", "m3countermand", "m3delivery"), "资源管理"),
    (("m3tenant", "m3brand", "m3merchant", "m3assistant"), "招商管理"),
    (("ac", "acl", "acsubject"), "财务管理"),
    (("m3sale", "m3gift", "m3product", "m3coupons"), "运营管理"),
]


@dataclass(frozen=True, slots=True)
class TableMeta:
    name: str
    cn: str
    domain: str
    source: str
    fields: list[dict[str, str]] = field(default_factory=list)


def _classify_table(table_name: str) -> str:
    for prefixes, module in _PREFIX_TO_MODULE:
        if any(table_name.startswith(p) for p in prefixes):
            return module
    return ""


def parse_data_dict_files(docs_root: str) -> list[TableMeta]:
    if not docs_root:
        return []
    root = Path(docs_root)
    tables: list[TableMeta] = []
    for f in sorted(root.glob(_DATA_DICT_GLOB)):
        short = f.stem.replace("haiding-", "").replace("-model", "")
        cur_domain = ""
        cur: TableMeta | None = None
        for line in f.read_text(encoding="utf-8").splitlines():
            dm = _DOMAIN_TITLE_RE.match(line)
            if dm:
                cur_domain = dm.group(1)
                continue
            hm = _HEADING_RE.match(line)
            if hm:
                if cur:
                    tables.append(cur)
                cur = TableMeta(
                    name=hm.group(1), cn=hm.group(2),
                    domain=cur_domain, source=short,
                )
                continue
            fm = _FIELD_RE.match(line)
            if fm and cur is not None:
                cn = fm.group(2).strip()
                if cn not in _NOISE_CN:
                    cur.fields.append({"name": fm.group(1), "cn": cn})
        if cur:
            tables.append(cur)
    return tables


def group_by_module(tables: list[TableMeta]) -> dict[str, list[TableMeta]]:
    result: dict[str, list[TableMeta]] = {}
    for t in tables:
        mod = _classify_table(t.name)
        if mod:
            result.setdefault(mod, []).append(t)
    return result


def get_unmatched(tables: list[TableMeta]) -> list[TableMeta]:
    return [t for t in tables if not _classify_table(t.name)]


def pick_key_fields(fields: list[dict[str, str]], n: int = 5) -> str:
    seen: set[str] = set()
    picked: list[str] = []
    for f in fields:
        cn = f.get("cn", "").strip()
        if cn and cn not in seen and cn not in _NOISE_CN:
            picked.append(cn)
            seen.add(cn)
        if len(picked) >= n:
            break
    return "、".join(picked)
