"""O7-vision 落地校验：LNKVISION_DATA 结构 + 金额留空 + capability not-applicable。

依据：references/adapter-capability-owner-decision-o7-vision-2026-10-04.md
（decision: customer-facing——独立面客产品；结构先行、金额留空、定价数值挂起，
完全复用 LNKREPORT_DATA 已核定模式）+ 执行记录
references/adapter-capability-owner-decision-o7-vision-execution-2026-10-04.md
§3（模块分组草案 + 功能清单行数审计：existing 18 = 5+5+5+2+1，全 31 行闭合）。
金额纪律：不填任何单价/金额/人天数；例外仅已核定结构性 0（3.1 新增项目、
4.1 首年赠送）与费率引用（二开 DEVKIT_RATE 元/人天、含税 6%）。
PRICING-FINAL（2026-10-05 decided / not-sold-independently，
references/adapter-capability-owner-decision-pricing-final-2026-10-05.md）：不单独售卖、
无独立标准价；结构保留，无价拒单行为即策略执行，capability onboarding→not-applicable。
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import pytest

SKILL_DIR = Path(__file__).resolve().parents[1]
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

CAP_YAML = SKILL_DIR / "references" / "adapter-capabilities.yaml"

AMOUNT_SEGS = (
    "core_modules",
    "integration_items",
    "implementation_items",
    "after_sales_items",
)
# 已核定结构性 0 的唯一合法位置（八列行下标 3-6 = 四个金额列）
RATIFIED_ZEROS = {("3.1", 5), ("3.1", 6), ("4.1", 4), ("4.1", 6)}


@pytest.fixture(scope="module", autouse=True)
def _company_env(tmp_path_factory):
    """generate_quote 导入即触发 _load_devkit_rate → get_company_base
    （COMPANIES.md §3 无静默默认），须先备好公司基座再首次导入
    （同 test_lnkreport_data.py 惯例）。"""
    base = tmp_path_factory.mktemp("lnkvision-company")
    (base / "config").mkdir()
    (base / "config" / "company.yaml").write_text(
        "schema_version: 1\n"
        f"id: {base.name}\n"
        "brand: Test\n"
        "products:\n"
        "  - id: lnkvision\n"
        "    name: LnkVision Test\n"
        "    code_root: null\n"
        "    prd_ready: false\n",
        encoding="utf-8",
    )
    old = os.environ.get("COMPANY_BASE")
    os.environ["COMPANY_BASE"] = str(base)
    yield
    if old is None:
        os.environ.pop("COMPANY_BASE", None)
    else:
        os.environ["COMPANY_BASE"] = old


def _gq():
    import generate_quote  # noqa: E402 - script-run skill（无包结构），同既有测试惯例

    return generate_quote


# ── LNKVISION_DATA 结构完整性 ────────────────────────────────────────


def test_lnkvision_segments_and_seq():
    data = _gq().LNKVISION_DATA
    assert data["product_label"] == "LnkVision"
    assert "不单独售卖" in data["pricing_status"]
    assert [r[0] for r in data["core_modules"]] == [f"1.{i}" for i in range(1, 6)]
    assert [r[0] for r in data["integration_items"]] == ["2.1"]
    assert [r[0] for r in data["implementation_items"]] == [f"3.{i}" for i in range(1, 5)]
    assert [r[0] for r in data["after_sales_items"]] == ["4.1"]
    for seg in AMOUNT_SEGS:  # 八列行结构（对齐 LNKREPORT_DATA）
        for row in data[seg]:
            assert len(row) == 8, (seg, row[0])


def test_lnkvision_required_optional_and_notes():
    gq = _gq()
    data = gq.LNKVISION_DATA
    core_notes = {r[0]: r[7] for r in data["core_modules"]}
    for seq in ("1.1", "1.2", "1.3", "1.4"):
        assert "必选" in core_notes[seq], seq
    assert "可选" in core_notes["1.5"]
    integ_notes = {r[0]: r[7] for r in data["integration_items"]}
    # 2.1 二开通道 = 费率引用（pricing-basis.yaml 唯一权威源）
    assert f"{gq.DEVKIT_RATE:,}" in integ_notes["2.1"] and "元/人天" in integ_notes["2.1"]
    # 边界诚实性：封闭系统边界（explicitly-not-do）在 2.1 备注声明
    assert "explicitly-not-do" in integ_notes["2.1"]


def test_lnkvision_existing_counts_sum_18():
    """模块分组条目数合计 = existing 18（功能清单全 31 行审计闭合，
    执行记录 §3：18 = 5+5+5+2+1）。"""
    data = _gq().LNKVISION_DATA
    counts = [5, 5, 5, 2, 1]
    assert len(data["modules"]) == len(counts)
    for (name, desc), n in zip(data["modules"], counts):
        assert f"existing {n} 项" in desc, (name, n)
    assert sum(counts) == 18


def test_lnkvision_summary_service_notes_saas_private():
    data = _gq().LNKVISION_DATA
    assert [r[0] for r in data["summary_rows"]] == [
        "首年费用合计", "次年费用合计", "首年优惠价", "次年优惠价",
    ]
    notes = "\n".join(data["service_notes"])
    assert "6%" in notes  # 税率引用（pricing-basis.yaml tax_rate_default）
    assert "不单独售卖" in notes
    # 产品边界诚实声明（explicitly-not-do 4 项）与隐私缺口披露
    assert "客流" in notes and "人脸识别" in notes
    assert "DPIA" in notes
    assert [r[0] for r in data["saas_vs_private"]] == [
        "软件授权性质", "数据归属", "次年费用", "适合场景", "实施差异",
    ]


# ── 金额留空纪律 ─────────────────────────────────────────────────────


def test_lnkvision_amounts_left_blank():
    """金额一律留空/None（不单独售卖，无独立标准价）；"—"=结构性不适用；0 仅限已核定两处。"""
    data = _gq().LNKVISION_DATA
    for seg in AMOUNT_SEGS:
        for row in data[seg]:
            for idx in (3, 4, 5, 6):
                v = row[idx]
                if isinstance(v, (int, float)):
                    assert v == 0 and (row[0], idx) in RATIFIED_ZEROS, (seg, row[0], idx, v)
                else:
                    assert v is None or v == "—", (seg, row[0], idx, v)
    for row in data["summary_rows"]:
        assert row[1] is None and row[2] is None, row[0]


def test_lnkvision_pricing_rows_marked_not_sold():
    """每个定价行的备注携带「不单独售卖（终裁 2026-10-05），无独立标准价」标记（费率通道 2.1 与含在 3.1 的行除外）。"""
    data = _gq().LNKVISION_DATA
    for seg in AMOUNT_SEGS:
        for row in data[seg]:
            if row[0] == "2.1":
                continue
            assert "不单独售卖" in row[7] or "含在 3.1" in row[7], (seg, row[0])


def test_lnkvision_no_cross_product_price_copy():
    """跨产品借用禁令：不携带 MI/CRM/AI/LnkChatBI 的任何价格数值。"""
    text = repr(_gq().LNKVISION_DATA)
    for banned in ("50000", "60000", "100000", "110000", "130000", "20000", "30000"):
        assert banned not in text, banned


# ── 生成行为：无数值时显式拒绝 ────────────────────────────────────────


def test_build_lnkvision_data_refuses_without_prices():
    with pytest.raises(SystemExit) as ei:
        _gq().build_lnkvision_data()
    msg = str(ei.value.code)
    assert "待定价" in msg and "拒绝" in msg


def test_cli_lnkvision_single_refuses():
    with pytest.raises(SystemExit):
        _gq().main(["--customer", "测试客户", "--product", "LNKVISION", "--mode", "SAAS"])


def test_cli_lnkvision_in_combo_refuses():
    with pytest.raises(SystemExit):
        _gq().main(["--customer", "测试客户", "--product", "MI,LNKVISION", "--mode", "SAAS"])


def test_cli_parse_accepts_lnkvision():
    args = _gq().parse_args(
        ["--customer", "X", "--product", "lnkvision", "--mode", "SAAS"]
    )
    assert args.product_codes == ["LNKVISION"]


# ── capability 条目（与 yaml 修改同批原子化）──────────────────────────


def _capabilities() -> dict[str, Any]:
    import yaml

    with open(CAP_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_capability_lnkvision_not_applicable():
    caps = _capabilities()
    entry = next(c for c in caps["capabilities"] if c["product_id"] == "lnkvision")
    assert entry["status"] == "not-applicable"
    assert entry["verified_at"] == "2026-10-04"
    assert entry["owner"] == "opc"
    evidence = " ".join(entry["evidence"])
    assert "LNKVISION_DATA" in evidence
    assert (
        "adapter-capability-owner-decision-o7-vision-2026-10-04.md" in evidence
    )
    assert re.search(r"o7-vision-2026-10-04\.md:\d+", evidence)
    assert "customer-facing" in evidence
    # PRICING-FINAL 终裁（2026-10-05）：不单独售卖 → not-applicable
    assert (
        "adapter-capability-owner-decision-pricing-final-2026-10-05.md" in evidence
        and "not-sold-independently" in evidence
    )
