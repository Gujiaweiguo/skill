"""O7-report Phase 3 落地校验：LNKREPORT_DATA 结构 + 金额留空 + capability not-applicable。

依据：references/adapter-capability-owner-decision-o7-report-phase1-2026-10-04.md
（decision: approved-phase1-3；phase3_ratification）+ Phase 2 报告
references/adapter-capability-owner-decision-o7-report-phase2-report-2026-10-04.md
§3.2（G4 模块分组）/ §4（八列四段，金额全留空）。
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
    （同 test_product_context_integration.py 惯例）。"""
    base = tmp_path_factory.mktemp("lnkreport-company")
    (base / "config").mkdir()
    (base / "config" / "company.yaml").write_text(
        "schema_version: 1\n"
        f"id: {base.name}\n"
        "brand: Test\n"
        "products:\n"
        "  - id: lnkreport\n"
        "    name: LnkReport Test\n"
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


# ── LNKREPORT_DATA 结构完整性 ────────────────────────────────────────


def test_lnkreport_segments_and_seq():
    data = _gq().LNKREPORT_DATA
    assert data["product_label"] == "LnkReport"
    assert "不单独售卖" in data["pricing_status"]
    assert [r[0] for r in data["core_modules"]] == [f"1.{i}" for i in range(1, 7)]
    assert [r[0] for r in data["integration_items"]] == ["2.1", "2.2", "2.3"]
    assert [r[0] for r in data["implementation_items"]] == [f"3.{i}" for i in range(1, 5)]
    assert [r[0] for r in data["after_sales_items"]] == ["4.1"]
    for seg in AMOUNT_SEGS:  # 八列行结构（Phase 2 报告 §4.1 列结构）
        for row in data[seg]:
            assert len(row) == 8, (seg, row[0])


def test_lnkreport_g4_required_optional_and_notes():
    gq = _gq()
    data = gq.LNKREPORT_DATA
    core_notes = {r[0]: r[7] for r in data["core_modules"]}
    for seq in ("1.1", "1.2", "1.3"):
        assert "必选" in core_notes[seq], seq
    for seq in ("1.4", "1.5", "1.6"):
        assert "可选" in core_notes[seq], seq
    integ_notes = {r[0]: r[7] for r in data["integration_items"]}
    # 2.3 二开通道 = 费率引用（pricing-basis.yaml 唯一权威源）
    assert f"{gq.DEVKIT_RATE:,}" in integ_notes["2.3"] and "元/人天" in integ_notes["2.3"]
    # 2.1 话术边界标待定（八项复核草案默认）
    assert "话术待定" in integ_notes["2.1"]


def test_lnkreport_existing_counts_sum_126():
    """G4 分组条目数合计 = existing 126（G3 标准范围总边界，Phase 2 §3.3）。"""
    data = _gq().LNKREPORT_DATA
    counts = [67, 31, 7, 7, 1, 6, 5, 2]
    assert len(data["modules"]) == len(counts)
    for (name, desc), n in zip(data["modules"], counts):
        assert f"existing {n} 项" in desc, (name, n)
    assert sum(counts) == 126


def test_lnkreport_summary_service_notes_saas_private():
    data = _gq().LNKREPORT_DATA
    assert [r[0] for r in data["summary_rows"]] == [
        "首年费用合计", "次年费用合计", "首年优惠价", "次年优惠价",
    ]
    notes = "\n".join(data["service_notes"])
    assert "6%" in notes  # 税率引用（pricing-basis.yaml tax_rate_default）
    assert "不单独售卖" in notes
    assert [r[0] for r in data["saas_vs_private"]] == [
        "软件授权性质", "数据归属", "次年费用", "适合场景", "实施差异",
    ]


# ── 金额留空纪律 ─────────────────────────────────────────────────────


def test_lnkreport_amounts_left_blank():
    """金额一律留空/None（不单独售卖，无独立标准价）；"—"=结构性不适用；0 仅限已核定两处。"""
    data = _gq().LNKREPORT_DATA
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


def test_lnkreport_pricing_rows_marked_not_sold():
    """每个定价行的备注携带「不单独售卖（终裁 2026-10-05），无独立标准价」标记（费率通道 2.3 与含在 3.1 的行除外）。"""
    data = _gq().LNKREPORT_DATA
    for seg in AMOUNT_SEGS:
        for row in data[seg]:
            if row[0] == "2.3":
                continue
            assert "不单独售卖" in row[7] or "含在 3.1" in row[7], (seg, row[0])


def test_lnkreport_no_cross_product_price_copy():
    """跨产品借用禁令：不携带 MI/CRM/AI/LnkChatBI 的任何价格数值。"""
    text = repr(_gq().LNKREPORT_DATA)
    for banned in ("50000", "60000", "100000", "110000", "130000", "20000", "30000"):
        assert banned not in text, banned


# ── 生成行为：无数值时显式拒绝 ────────────────────────────────────────


def test_build_lnkreport_data_refuses_without_prices():
    with pytest.raises(SystemExit) as ei:
        _gq().build_lnkreport_data()
    msg = str(ei.value.code)
    assert "待定价" in msg and "拒绝" in msg


def test_cli_lnkreport_single_refuses():
    with pytest.raises(SystemExit):
        _gq().main(["--customer", "测试客户", "--product", "LNKREPORT", "--mode", "SAAS"])


def test_cli_lnkreport_in_combo_refuses():
    with pytest.raises(SystemExit):
        _gq().main(["--customer", "测试客户", "--product", "MI,LNKREPORT", "--mode", "SAAS"])


def test_cli_parse_accepts_lnkreport():
    args = _gq().parse_args(
        ["--customer", "X", "--product", "lnkreport", "--mode", "SAAS"]
    )
    assert args.product_codes == ["LNKREPORT"]


# ── capability 条目（与 yaml 修改同批原子化）──────────────────────────


def _capabilities() -> dict[str, Any]:
    import yaml

    with open(CAP_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_capability_lnkreport_not_applicable():
    caps = _capabilities()
    entry = next(c for c in caps["capabilities"] if c["product_id"] == "lnkreport")
    assert entry["status"] == "not-applicable"
    assert entry["verified_at"] == "2026-10-04"
    assert entry["owner"] == "opc"
    evidence = " ".join(entry["evidence"])
    assert "LNKREPORT_DATA" in evidence
    assert (
        "adapter-capability-owner-decision-o7-report-phase2-report-2026-10-04.md" in evidence
    )
    assert re.search(r"phase2-report-2026-10-04\.md:\d+", evidence)
    # PRICING-FINAL 终裁（2026-10-05）：不单独售卖 → not-applicable
    assert (
        "adapter-capability-owner-decision-pricing-final-2026-10-05.md" in evidence
        and "not-sold-independently" in evidence
    )


def test_capability_other_products_untouched():
    """禁改其他产品条目：八产品状态全景钉住（lnkreport 除外七项不变）。

    lnkchatbi partial→implemented 为 O8 同批修订（rejected-registration，
    2026-10-04，references/adapter-capability-owner-decision-o8-2026-10-04.md）。
    lnkchat unsupported→not-applicable 为 O7-chat 同批修订（bundled-not-listed，
    2026-10-04，references/adapter-capability-owner-decision-o7-chat-2026-10-04.md；
    shared 钉线 EXPECTED_MATRIX/EXPECTED_DISTRIBUTION 同 commit）。
    lnkvision unsupported→onboarding 为 O7-vision 同批修订（customer-facing，
    2026-10-04，references/adapter-capability-owner-decision-o7-vision-2026-10-04.md；
    shared 钉线同 commit）；lnkreport/lnkvision onboarding→not-applicable 为
    PRICING-FINAL 终裁同批修订（not-sold-independently，2026-10-05，
    references/adapter-capability-owner-decision-pricing-final-2026-10-05.md；
    shared 钉线同 commit）。
    """
    caps = _capabilities()
    statuses = {c["product_id"]: c["status"] for c in caps["capabilities"]}
    assert statuses == {
        "lnkcre": "implemented",
        "lnkcrm": "partial",
        "lnkchat": "not-applicable",
        "lnkchatbi": "implemented",
        "lnkreport": "not-applicable",
        "lnkvision": "not-applicable",
        "lnkgateway": "not-applicable",
        "lnkwebsite": "not-applicable",
    }
