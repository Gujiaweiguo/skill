"""27 件真实 implementation-return 回执的脱敏形态回归（fixture 数据驱动）。

fixture 为对 /opt/code/docs/lanlnk/30-products/*/reconciliation/
implementation-return-*.json（lnkcre 5 / lnkcrm 12 / lnkreport 10，2026-10-21
第二波全量盘点）的最小化脱敏投影：每件只保留决定校验与归一化行为的键形态
（product / review_status / changes 标识键与 status / feature 提交键 / trace_ids
类型 / proposed_updates 类型 / follow_ups 类型 / origin_flow / schema_version）。
docs 仓另有 2 件 out/prd/lnkchat 旧式件（顶层 status="done-pending-owner-review"）
不在 27 件基线内，schema 已为其声明 optional `status` 字段。

断言分两组：
  组一（重点）：27 件真实形态经放宽后 schema 直接 validate 通过，无需归一化。
    仅以下「过渡例外」允许失败点（逐条理由，非静默放行）：
      - review_status 野值：2026-10-21 owner 裁决批（A+B+C）已把 10 件真野值/
        缺失迁为 absorbed（原值保留在 review_status_superseded）；现基线中仅剩
        report-structure-authoring-parity 一件顶层缺失（文件被并行会话占用，
        落地后补迁）。野值保留语义由合成用例锚定；
      - absorbed / code-evidence-reverse 件缺 absorbed 门槛字段
        （open_spec_change_id / verification_refs / source_revision / scan_coverage /
        review_owner）：存量件早于「吸收完成必须有证据锚」门槛落地，收紧需
        owner 裁决后回填，不由测试猜测。
  组二：compat helper 归一化断言——不抛异常、change 标识与 feature 提交键统一
    识别、schema_version 折叠 '1.0'、ch status archived→done、pu 双键集归一
    {target, update, disposition}、野值/缺失只产生 warning。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Final

import pytest

# 与 tests/test_paths.py 同款环境兜底：resolver 需要 COMPANY_BASE / LANLNK_BASE。
if not (os.environ.get("COMPANY_BASE") or os.environ.get("LANLNK_BASE")):
    os.environ["LANLNK_BASE"] = "/opt/code/docs/lanlnk"

from product_prd_generator.implementation_return_compat import (  # noqa: E402
    REVIEW_STATUS_VOCAB,
    normalize_implementation_return,
)
from tests.test_product_governance_contracts import _validate  # noqa: E402  复用 Registry/$ref 解析

SCHEMA_NAME: Final = "implementation-return.schema.json"

# ---------------------------------------------------------------------------
# 脱敏 fixture：27 件真实回执的键形态投影（2026-10-21 第二波实测签名）。
# 字段：(product, slug, review_status, id_key, fc_key, trace, pu, fu, ch_status, origin_flow, sv)
#   id_key: change 标识键（'' = 无 changes）；fc_key: '' | 'feature_commit' | 'feature_commits'
#   trace: 'list' | 'dict' | 'miss'（实测 list×16 / dict×3 / miss×8，无裸字符串）
#   pu: 'str-list' | 'obj-list' | 'obj-legacy' | 'empty' | 'miss'（miss×6）
#   fu: 'str' | 'obj' | 'miss'（字符串主流 + 对象键集×4 件）
#   ch_status: None | 'done' | 'archived' | 'pending'（archived≡done 同义）
#   origin_flow: None = 键缺失；sv: None = 键缺失（verify-hygiene 为数字 1）
# ---------------------------------------------------------------------------
INVENTORY: Final = [
    # --- lnkcre (5) ---
    ("lnkcre", "location-asof-query-20261018", "absorbed", "change", "", "list", "str-list", "str", "archived", "implementation-package-execution", "1.0"),
    ("lnkcre", "masterdata-deferred-closeout", "absorbed", "change_id", "feature_commits", "dict", "obj-list", "obj", None, "implementation-package-execution", "1.0"),
    ("lnkcre", "masterdata-fullwidth-workspace-20261018", "absorbed", "change_id", "feature_commits", "dict", "str-list", "str", None, "implementation-package-execution", "1.0"),
    ("lnkcre", "rent-plan-haiding-20261021", "pending", "id", "feature_commits", "list", "empty", "str", "pending", "implementation-package-execution", "1.0"),
    ("lnkcre", "tax-export-dev-fixtures-20261019", "absorbed", "change_id", "feature_commits", "dict", "obj-list", "obj", "done", "implementation-package-execution", "1.0"),
    # --- lnkcrm (12) ---
    ("lnkcrm", "admin-nav-hierarchy", "absorbed", "change", "", "list", "miss", "str", "done", "implementation-package-execution", "1"),
    ("lnkcrm", "crosscut", "absorbed", "change_id", "feature_commits", "miss", "str-list", "str", None, "implementation-package-execution", "1.0"),
    ("lnkcrm", "e2e-smoke-hardening", "absorbed", "change", "feature_commit", "list", "miss", "str", "done", "implementation-package-execution", "1"),
    ("lnkcrm", "member-freeze-unfreeze", "absorbed", "", "", "list", "obj-list", "miss", None, "code-evidence-reverse", "1.0"),
    ("lnkcrm", "nav-followups", "absorbed", "change", "feature_commit", "list", "miss", "str", "done", "implementation-package-execution", "1"),
    ("lnkcrm", "s6-d1b", "absorbed", "", "", "miss", "miss", "str", None, "implementation-package-execution", "1.0"),
    ("lnkcrm", "s6-platform-002", "absorbed", "", "", "list", "obj-list", "miss", None, "code-evidence-reverse", "1.0"),
    ("lnkcrm", "verify-hygiene", "absorbed", "change", "feature_commit", "list", "empty", "str", "done", "implementation-package-execution", 1),
    ("lnkcrm", "w1-c2c3c4", "absorbed", "change_id", "feature_commits", "list", "obj-list", "str", None, "implementation-package-execution", "1.0"),
    ("lnkcrm", "w2a", "absorbed", "change_id", "feature_commits", "miss", "miss", "str", None, "implementation-package-execution", "1.0"),
    ("lnkcrm", "w3a-w1s", "absorbed", "change_id", "feature_commits", "miss", "str-list", "str", None, "implementation-package-execution", "1.0"),
    ("lnkcrm", "w3b", "absorbed", "change_id", "feature_commits", "miss", "str-list", "str", None, "implementation-package-execution", "1.0"),
    # --- lnkreport (10) ---
    ("lnkreport", "backlog-cleanup-20261019", "pending", "", "", "list", "empty", "str", None, "implementation-package-execution", "1.0"),
    ("lnkreport", "backlog-remaining-20261020", "absorbed", "change_id", "feature_commits", "list", "obj-list", "obj", "done", "implementation-package-execution", "1.0"),
    ("lnkreport", "chart-read-tenant-guard-20261021", "reviewed", "change_id", "feature_commit", "miss", "empty", "str", "done", "implementation-package-execution", "implementation-return/1.7"),
    ("lnkreport", "embedded-viewer-shell-20261019", "pending", "change", "feature_commits", "list", "obj-list", "str", "done", "implementation-package-execution", "1.0"),
    ("lnkreport", "epviewer-w1-20261018", "pending", "change", "feature_commits", "list", "str-list", "str", "done", "implementation-package-execution", "1.0"),
    ("lnkreport", "render-reliability-followups-20261020", "absorbed", "change_id", "feature_commits", "list", "obj-legacy", "str", "done", "implementation-package-execution", "1.0"),
    ("lnkreport", "report-grid-paste-format-virgin-target-persistence-20261019", "absorbed", "", "", "list", "obj-list", "obj", None, "implementation-package-execution", "1.0"),
    # 2026-10-21 迁移批唯一未迁件：目标文件被并行 docs 会话占用（在途未提交），
    # 落地后补迁（计划见 docs 仓 lnkcrm reconciliation review-status-migration-plan-20261021.md）。
    ("lnkreport", "report-structure-authoring-parity-20261018", None, "", "", "miss", "miss", "miss", None, None, None),
    ("lnkreport", "visualization-family-remediation-20261021", "reviewed", "change_id", "feature_commit", "miss", "str-list", "str", "done", "implementation-package-execution", "implementation-return/1.7"),
    ("lnkreport", "visualization-tenant-isolation-20261021", "absorbed", "change", "feature_commits", "list", "str-list", "str", "done", "implementation-package-execution", "1.0"),
]

# 过渡例外（理由见模块 docstring）：这些字段的缺失不判 FAIL。
_LEGACY_GATED_FIELDS: Final = {
    "open_spec_change_id", "verification_refs", "source_revision", "scan_coverage", "review_owner",
}


def _build_fixture(spec: tuple[Any, ...]) -> dict[str, Any]:
    (product, slug, review_status, id_key, fc_key, trace, pu, fu, ch_status, origin_flow, sv) = spec
    ret: dict[str, Any] = {
        "return_id": f"RET-FIX-{slug.upper()[:40]}",
        "product_id": product,
    }
    if sv is not None:
        ret["schema_version"] = sv
    if origin_flow is not None:
        ret["origin_flow"] = origin_flow
    if review_status is not None:
        ret["review_status"] = review_status
    if trace == "list":
        ret["trace_ids"] = ["REC-FIX-001", "REC-FIX-002"]
    elif trace == "dict":
        # 实测 dict 键：waves / changes / owner_decisions（+audit_items/package_id 变体）
        ret["trace_ids"] = {"waves": ["W1-fix-a", "W2-fix-b"], "owner_decisions": ["OD-1", "OD-2"]}
    if id_key:
        change: dict[str, Any] = {id_key: f"fix-{slug[:24]}"}
        if fc_key == "feature_commits":
            change["feature_commits"] = ["ee5c6251", "0f1e2d3c"]
        elif fc_key == "feature_commit":
            change["feature_commit"] = "c974360adc"  # 存量标量形态
        if ch_status is not None:
            change["status"] = ch_status
        ret["changes"] = [change, {**change, id_key: f"fix-{slug[:24]}-2"}]
    if pu == "str-list":
        ret["proposed_updates"] = ["docs 走查文档登记批次完成", "S6 ledger 登记三行 accepted"]
    elif pu == "obj-list":
        if origin_flow == "code-evidence-reverse":
            # 真实反向件的 pu 为 {target, update} 形态（无 status，避免触发反向约束）
            ret["proposed_updates"] = [{"target": "docs §3-Q2", "update": "引用计数更正为已交付"}]
        else:
            # lnkcre/lnkcrm 风格键集 {target, update, status}
            ret["proposed_updates"] = [{"target": "docs 走查文档 §3", "update": "品牌合同引用计数更正", "status": "done"}]
    elif pu == "obj-legacy":
        # lnkreport/lnkchat 风格键集 {destination_layer, summary, status}
        ret["proposed_updates"] = [{
            "destination_layer": "prd", "summary": "报表结构一致性说明补齐", "status": "proposed",
        }]
    elif pu == "str":
        ret["proposed_updates"] = "S6 ledger 登记一行 accepted"
    elif pu == "empty":
        ret["proposed_updates"] = []
    if fu == "str":
        ret["follow_ups"] = ["W4 下载中心底座按裁决推进"]
    elif fu == "obj":
        ret["follow_ups"] = [{"id": "FU-1", "item": "上传中心联调", "status": "open"}]
    return ret


def _is_legacy_exception(message: str, ret: dict[str, Any]) -> bool:
    """仅放过 docstring 列明的过渡例外：野值 enum / absorbed 与反向件的门槛字段缺失。"""
    raw_status = ret.get("review_status")
    if raw_status is not None and raw_status not in REVIEW_STATUS_VOCAB:
        if "is not one of" in message and str(raw_status) in message:
            return True
    gated = raw_status == "absorbed" or ret.get("origin_flow") == "code-evidence-reverse"
    if gated and "is a required property" in message:
        field = message.split("'")[1]
        return field in _LEGACY_GATED_FIELDS
    return False


def test_inventory_covers_27_real_returns() -> None:
    assert len(INVENTORY) == 27
    products: dict[str, int] = {}
    for spec in INVENTORY:
        products[spec[0]] = products.get(spec[0], 0) + 1
    assert products == {"lnkcre": 5, "lnkcrm": 12, "lnkreport": 10}
    # 第二波实测分布锚点
    assert sum(1 for s in INVENTORY if s[5] == "dict") == 3
    assert sum(1 for s in INVENTORY if s[5] == "miss") == 8
    assert sum(1 for s in INVENTORY if s[6] == "miss") == 6
    assert sum(1 for s in INVENTORY if s[7] == "obj") == 4
    assert sum(1 for s in INVENTORY if s[8] == "archived") == 1
    assert sum(1 for s in INVENTORY if s[10] == 1) == 1  # 数字 1 ×1


@pytest.mark.parametrize("spec", INVENTORY, ids=[s[1] for s in INVENTORY])
def test_real_return_shape_passes_relaxed_schema_directly(spec: tuple[Any, ...]) -> None:
    """组一（重点）：真实形态直接过放宽后 schema，无需归一化（过渡例外除外）。"""
    ret = _build_fixture(spec)
    errors = _validate(SCHEMA_NAME, ret)
    unexpected = [m for m in errors if not _is_legacy_exception(m, ret)]
    assert not unexpected, f"{spec[1]}: 过渡例外之外的 schema 错误: {unexpected}"


@pytest.mark.parametrize("spec", INVENTORY, ids=[s[1] for s in INVENTORY])
def test_normalize_real_return_shapes(spec: tuple[Any, ...]) -> None:
    """组二：helper 归一化——不抛异常、标识/提交键统一识别、形态折叠、野值只 warning。"""
    ret = _build_fixture(spec)
    (_product, _slug, review_status, id_key, _fc_key, trace, pu, _fu, ch_status, _origin_flow, sv) = spec

    view, warnings = normalize_implementation_return(ret)
    assert isinstance(view, dict) and isinstance(warnings, list)
    # schema_version 统一折叠为 "1.0"，非目标值/缺失记 warning
    assert view["schema_version"] == "1.0"
    if sv != "1.0":
        assert any("schema_version" in w for w in warnings)
    if id_key:
        assert view["changes"], "changes 应被识别"
        for change in view["changes"]:
            assert change["change_id"] and isinstance(change["change_id"], str)
            assert isinstance(change["feature_commits"], list)
            assert all(isinstance(c, str) for c in change["feature_commits"])
        # ch status archived 折叠为 done，其余原样
        if ch_status == "archived":
            assert all(c["status"] == "done" for c in view["changes"])
        elif ch_status is not None:
            assert all(c["status"] == ch_status for c in view["changes"])
    # trace_ids 归一为字符串列表
    assert isinstance(view["trace_ids"], list)
    assert all(isinstance(t, str) for t in view["trace_ids"])
    if trace == "dict":
        assert view["trace_ids"] == ["waves.W1-fix-a", "waves.W2-fix-b", "owner_decisions.OD-1", "owner_decisions.OD-2"]
        assert any("对象形态" in w for w in warnings)
    elif trace == "miss":
        assert any("trace_ids" in w for w in warnings)
    # pu 归一为 {target, update, disposition}（status 缺省 proposed）
    if pu == "str-list":
        assert view["proposed_updates"] == [
            {"target": None, "update": "docs 走查文档登记批次完成", "disposition": None},
            {"target": None, "update": "S6 ledger 登记三行 accepted", "disposition": None},
        ]
    elif pu == "obj-list":
        src = ret["proposed_updates"][0]
        assert view["proposed_updates"] == [{
            "target": src.get("target"), "update": src.get("update"),
            "disposition": src.get("status") or "proposed",
        }]
    elif pu == "obj-legacy":
        src = ret["proposed_updates"][0]
        assert view["proposed_updates"] == [{
            "target": src["destination_layer"], "update": src["summary"],
            "disposition": src["status"],
        }]
    elif pu == "miss":
        assert any("proposed_updates" in w for w in warnings)

    # 词表值直接通过；野值/缺失只产生 warning，view 不含野值
    if review_status in REVIEW_STATUS_VOCAB:
        assert view["review_status"] == review_status
    elif review_status is None:
        assert "review_status" not in view
        assert any("review_status" in w for w in warnings)
    else:
        assert "review_status" not in view
        assert any(review_status in w for w in warnings)

    # 归一化视图也过 schema（同样只允许过渡例外）
    errors = _validate(SCHEMA_NAME, view)
    unexpected = [m for m in errors if not _is_legacy_exception(m, view)]
    assert not unexpected, f"{spec[1]}: 归一化视图出现过渡例外之外的 schema 错误: {unexpected}"


def test_wild_review_status_vocabulary_is_preserved_not_mapped() -> None:
    """野值必须保留原文（warning），不得猜测映射到词表。

    2026-10-21 owner 裁决批（A+B+C）已把 10 件真野值/缺失迁为 absorbed
    （原值保留在回执 review_status_superseded），真件基线中现仅剩
    report-structure-authoring-parity 一件缺失（被并行会话占用待补迁）。
    本用例改为合成驱动：锚定 helper 对未来新野值的保留语义。
    """
    for wild in (
        "closed-registered-and-pushed",
        "docs-evidence-review-passed-project-ledger-accepted-local-unpushed",
        "approved-and-archived",
    ):
        ret = {
            "schema_version": "1.0",
            "return_id": f"RET-FIX-WILD-{wild[:12]}",
            "product_id": "lnkcrm",
            "origin_flow": "implementation-package-execution",
            "trace_ids": ["REC-FIX-WILD"],
            "review_status": wild,
            "proposed_updates": [],
        }
        view, warnings = normalize_implementation_return(ret)
        assert "review_status" not in view
        assert any(wild in w and "野值" in w for w in warnings)
        # 野值导致的 schema enum 失败属于已声明的过渡例外（组一），其余必须干净
        errors = _validate(SCHEMA_NAME, view)
        unexpected = [m for m in errors if not (_is_legacy_exception(m, view) or ("is not one of" in m and wild in m))]
        assert unexpected == []


def test_findings_variant_does_not_fabricate_changes() -> None:
    """findings 变体（无 changes、以 findings 承载）：不伪造 changes，只记 warning。

    注：2026-10-21 直查 27 件 reconciliation 实件中 findings 变体实为 2 件
    （lnkcrm member-freeze-unfreeze / s6-platform-002，均无 changes、有 trace_ids；
    第二波盘点点名的 crosscut/nav-followups 实际仍带 changes，名单有误）。
    本用例为能力锚定，fixture 表中上述 2 件真件行同样走该分支。
    """
    ret = {
        "schema_version": "1.0",
        "return_id": "RET-FIX-FINDINGS",
        "product_id": "lnkchatbi",
        "origin_flow": "code-evidence-reverse",
        "findings": ["FND-1: code evidence awaits decision"],
        "reconciliation_ids": ["REC-1"],
        "verification_refs": ["verification.md"],
        "target_repo": "/opt/code/lnkchatbi",
        "source_revision": "abc123",
        "scan_coverage": {"status": "partial", "scope": ["src/reports"], "limitations": ["tests not scanned"]},
        "review_status": "reviewed",
        "proposed_updates": [],
    }
    view, warnings = normalize_implementation_return(ret)
    assert view["changes"] == []
    assert any("findings-variant" in w for w in warnings)
    assert _validate(SCHEMA_NAME, view) == []


def test_helper_does_not_mutate_input() -> None:
    ret = _build_fixture(INVENTORY[1])
    snapshot = json.dumps(ret, sort_keys=True, ensure_ascii=False)
    normalize_implementation_return(ret)
    assert json.dumps(ret, sort_keys=True, ensure_ascii=False) == snapshot


# ---------------------------------------------------------------------------
# strict_validation_report 三段报告（change align-governance-handoff-contracts
# 6.1/6.2/6.3，2026-11-13）：source 与 normalized 各自独立校验，均可失败并
# 报告全部剩余错误；输入不可变；warnings/actions 保留原始值；不补造事实。
# ---------------------------------------------------------------------------

from product_prd_generator.implementation_return_report import (  # noqa: E402
    ReportDependencyError,
    strict_validation_report,
)

_SKILL_ROOT: Final = Path(__file__).resolve().parents[1]

# 脱敏 7-error 形态（对应 2026-11 两件 schema_version:'1.1' 历史漂移回执的
# 复测签名）：source 侧 7 个 schema 错误——schema_version '1.1'（anyOf×1）、
# trace_ids 裸字符串（anyOf×1）、phase_record.created 纯字符串（phaseFact×1）、
# absorbed 门槛字段缺失（required×4：open_spec_change_id / source_revision /
# verification_refs / review_owner）。
_SEVEN_ERROR_RETURN: Final[dict[str, Any]] = {
    "return_id": "RET-REPORT-7ERR",
    "product_id": "lnkreport",
    "schema_version": "1.1",
    "origin_flow": "implementation-package-execution",
    "review_status": "absorbed",
    "trace_ids": "REC-7ERR-single-trace",
    "changes": [{
        "id": "chg-7err",
        "feature_commit": "abc1234",
        "phase_record": {"created": "created"},
    }],
}


def test_strict_validation_report_seven_error_source_vs_normalized() -> None:
    """6.2：source 按路径/计数报告 7 errors；normalized 独立校验并按实际剩余
    错误断言（规范化不补造 review_owner 等事实，absorbed 门槛仍失败）。"""
    raw = json.loads(json.dumps(_SEVEN_ERROR_RETURN))  # 深拷贝隔离
    snapshot = json.dumps(raw, sort_keys=True, ensure_ascii=False)

    report = strict_validation_report(raw)

    # 输入不可变（深比较）
    assert json.dumps(raw, sort_keys=True, ensure_ascii=False) == snapshot

    src = report["source"]
    assert src["ok"] is False
    assert src["error_count"] == 7
    assert len(src["errors"]) == 7
    assert all(e["path"] and e["message"] for e in src["errors"])
    # 7 个错误各自带路径（required 锚在 "$"，字段级错误锚在字段路径）
    paths = [e["path"] for e in src["errors"]]
    assert paths.count("$") == 4  # absorbed 门槛 required×4
    assert "$.schema_version" in paths
    assert "$.trace_ids" in paths
    assert "$.changes[0].phase_record.created" in paths

    normalized = report["normalized"]
    # normalized 独立校验：归一化修复了 schema_version/trace_ids/phase_record
    # 形态，但不补造 absorbed 门槛事实——4 个 required 仍失败。
    assert normalized["ok"] is False
    assert normalized["error_count"] == 4
    missing = {
        e["message"].split("'")[1]
        for e in normalized["errors"]
        if "is a required property" in e["message"]
    }
    assert missing == {"open_spec_change_id", "source_revision", "verification_refs", "review_owner"}
    assert normalized["error_count"] < src["error_count"]

    # warnings/动作保留原始值（'1.1'、裸字符串 trace、phase_record 不补造）
    warnings = report["normalization"]["warnings"]
    assert any("1.1" in w for w in warnings)
    assert any("trace_ids" in w for w in warnings)
    actions = report["normalization"]["actions"]
    by_field = {a["field"]: a for a in actions}
    assert by_field["schema_version"]["source_value"] == "1.1"
    assert by_field["schema_version"]["view_value"] == "1.0"
    assert by_field["trace_ids"]["source_value"] == "REC-7ERR-single-trace"
    # 4 个 required 剩余错误本身就是「未补造 absorbed 门槛事实」的机械证明


def test_strict_validation_report_legitimate_normalized_pass_source_fail() -> None:
    """合法的「normalized 通过 / source 失败」形态：'1.1' 折叠 + 缺 trace 兜底
    后视图通过，但 source 的 '1.1' 严格失败——不得冒称源件通过。"""
    raw = {
        "return_id": "RET-REPORT-NORMPASS",
        "product_id": "lnkcre",
        "schema_version": "1.1",
        "origin_flow": "implementation-package-execution",
        "review_status": "pending",
    }
    report = strict_validation_report(raw)
    assert report["source"]["ok"] is False
    assert report["source"]["error_count"] == 1
    assert "$.schema_version" in [e["path"] for e in report["source"]["errors"]]
    assert report["normalized"]["ok"] is True
    assert report["normalized"]["error_count"] == 0


def test_strict_validation_report_review_status_vocabulary() -> None:
    """6.3：词表四值过严格校验（absorbed 需带门槛事实）；accepted/incomplete
    严格失败且兼容读取保留原值 + warning（不映射）。"""
    gated_facts = {
        "open_spec_change_id": "report-vocab-change",
        "source_revision": "abc123",
        "verification_refs": ["verification-report.md"],
        "review_owner": "OPC",
    }
    for status in ("pending", "reviewed", "rejected"):
        raw = {
            "schema_version": "1.0",
            "return_id": f"RET-REPORT-VOCAB-{status}",
            "product_id": "lnkcrm",
            "origin_flow": "implementation-package-execution",
            "review_status": status,
            "proposed_updates": [],
        }
        report = strict_validation_report(raw)
        assert report["source"]["ok"] is True, (status, report["source"]["errors"])
        assert report["normalized"]["ok"] is True
    absorbed = {
        "schema_version": "1.0",
        "return_id": "RET-REPORT-VOCAB-absorbed",
        "product_id": "lnkcrm",
        "origin_flow": "implementation-package-execution",
        "review_status": "absorbed",
        **gated_facts,
        "proposed_updates": [],
    }
    report = strict_validation_report(absorbed)
    assert report["source"]["ok"] is True, report["source"]["errors"]
    # compat 归一化视图不透传 review_owner（不补造事实）→ normalized 按实际
    # 剩余错误失败，而非被伪装通过；且通用 diff 必须把这一被投影丢弃的
    # 原值显式记为 projected-out 动作，不得静默消失。
    assert report["normalized"]["ok"] is False
    assert any("review_owner" in e["message"] for e in report["normalized"]["errors"])
    owner_action = next(
        a for a in report["normalization"]["actions"] if a["field"] == "review_owner"
    )
    assert owner_action["action"] == "projected-out"
    assert owner_action["source_present"] is True
    assert owner_action["view_present"] is False
    assert owner_action["source_value"] == "OPC"

    for wild in ("accepted", "incomplete"):
        raw = {
            "schema_version": "1.0",
            "return_id": f"RET-REPORT-WILD-{wild}",
            "product_id": "lnkcrm",
            "origin_flow": "implementation-package-execution",
            "review_status": wild,
            "proposed_updates": [],
        }
        report = strict_validation_report(raw)
        # source：enum 严格失败
        assert report["source"]["ok"] is False
        assert any("is not one of" in e["message"] and wild in e["message"]
                   for e in report["source"]["errors"])
        # 兼容读取：野值不映射，保留原值 + warning
        view, warnings = normalize_implementation_return(raw)
        assert "review_status" not in view
        assert any(wild in w and "野值" in w for w in warnings)


def test_strict_validation_report_wild_statuses_are_not_mapped() -> None:
    """真实存量野值形态经报告通道同样不映射：source 失败、warning 保留原文。"""
    for wild in ("closed-registered-and-pushed", "approved-and-archived"):
        raw = {
            "schema_version": "1.0",
            "return_id": f"RET-REPORT-WILD-REAL-{wild[:10]}",
            "product_id": "lnkreport",
            "origin_flow": "implementation-package-execution",
            "review_status": wild,
            "proposed_updates": [],
        }
        report = strict_validation_report(raw)
        assert report["source"]["ok"] is False
        assert any(wild in e["message"] for e in report["source"]["errors"])
        # 野值不映射：通用 diff 中 review_owner…此处 review_status 为
        # projected-out（源有/视图无），source 保留原值，view_present=False
        status_action = next(
            a for a in report["normalization"]["actions"] if a["field"] == "review_status"
        )
        assert status_action["action"] == "projected-out"
        assert status_action["source_present"] is True
        assert status_action["view_present"] is False
        assert status_action["source_value"] == wild


def test_actions_distinguish_missing_sentinel_from_literal_string() -> None:
    """通用 diff 的存在性布尔必须区分「键缺失」与「字面量 '<missing>' 字符串」：
    哨兵 source_value 同为 '<missing>'，但 source_present 布尔是权威判据。"""
    base = {
        "return_id": "RET-REPORT-MISSING-SENTINEL",
        "product_id": "lnkcre",
        "origin_flow": "implementation-package-execution",
        "review_status": "pending",
        "schema_version": "1.0",
    }
    # 形态一：trace_ids 键缺失（视图兜底 []）
    absent = strict_validation_report(dict(base))
    a1 = next(a for a in absent["normalization"]["actions"] if a["field"] == "trace_ids")
    assert a1["source_present"] is False
    assert a1["view_present"] is True
    assert a1["source_value"] == "<missing>"  # 哨兵
    assert a1["action"] == "added-by-normalization"

    # 形态二：trace_ids 恰为字面量 "<missing>" 字符串（真实源值，非哨兵）
    literal = strict_validation_report({**base, "return_id": "RET-REPORT-MISSING-LITERAL", "trace_ids": "<missing>"})
    a2 = next(a for a in literal["normalization"]["actions"] if a["field"] == "trace_ids")
    assert a2["source_present"] is True
    assert a2["view_present"] is True
    assert a2["source_value"] == "<missing>"  # 与哨兵同形
    assert a2["source_present"] != a1["source_present"]  # 布尔可区分
    assert a2["action"] == "changed"
    assert a2["label"] == "shape-normalized"


def test_actions_cover_all_projected_out_keys_deterministically() -> None:
    """所有被投影丢弃的源键（findings / review_owner / package_ref 等）都必须
    出现在动作清单里（projected-out），不静默消失；排序确定性。"""
    raw = {
        "return_id": "RET-REPORT-PROJECTED",
        "product_id": "lnkcre",
        "schema_version": "1.0",
        "origin_flow": "implementation-package-execution",
        "review_status": "reviewed",
        "trace_ids": ["REC-1"],
        "findings": ["FND-1: observed fact"],
        "review_owner": "OPC",
        "package_ref": "/sample/pkg.md",
        "docs_anchoring": True,
        "proposed_updates": [],
    }
    report = strict_validation_report(raw)
    actions = report["normalization"]["actions"]
    fields = [a["field"] for a in actions]
    # 字段序确定性（sorted）
    assert fields == sorted(fields)
    projected = {a["field"] for a in actions if a["action"] == "projected-out"}
    # compat 视图不透传这些键 → 全部显式登记为 projected-out
    assert {"findings", "review_owner", "package_ref", "docs_anchoring"} <= projected
    for a in actions:
        if a["action"] == "projected-out":
            assert a["source_present"] is True and a["view_present"] is False


def test_compat_stdlib_import_and_normalize_under_python_S() -> None:
    """6.1：python -S 隔离环境（无 site-packages → 无 jsonschema）下，普通
    compat 导入与 normalize 调用仍工作，证明 compat 模块不依赖 jsonschema。"""
    code = (
        "import sys\n"
        "try:\n"
        "    import jsonschema\n"
        "    sys.exit(3)\n"  # 隔离失效（jsonschema 仍可见）→ 3
        "except ImportError:\n"
        "    pass\n"
        "from product_prd_generator.implementation_return_compat import (\n"
        "    normalize_implementation_return,\n"
        ")\n"
        "view, warnings = normalize_implementation_return({\n"
        "    'return_id': 'R-S', 'product_id': 'lnkcre',\n"
        "    'schema_version': '1.1', 'review_status': 'accepted',\n"
        "})\n"
        "assert view['schema_version'] == '1.0'\n"
        "assert 'review_status' not in view and warnings\n"
        "print('OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-S", "-c", code],
        cwd=_SKILL_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"


def test_cli_exit_codes_source_failure_and_dependency_errors() -> None:
    """CLI：exit 0 iff source 通过；source 失败=1（即使 normalized 通过）；
    输入不可读=2。输出必须是可解析的 JSON 报告。"""
    import tempfile

    def _run(content: str, name: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            path = Path(tmp) / name
            path.write_text(content, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-m", "product_prd_generator.implementation_return_report", str(path)],
                cwd=_SKILL_ROOT, capture_output=True, text=True, timeout=60,
            )

    valid = {
        "schema_version": "1.0",
        "return_id": "RET-CLI-OK",
        "product_id": "lnkcre",
        "origin_flow": "implementation-package-execution",
        "review_status": "pending",
        "proposed_updates": [],
    }
    result = _run(json.dumps(valid, ensure_ascii=False), "ok.json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["source"]["ok"] is True

    # source 失败（'1.1' 严格失败）但 normalized 折叠后通过 → 退出码必须是 1
    invalid = {**valid, "return_id": "RET-CLI-FAIL", "schema_version": "1.1"}
    result = _run(json.dumps(invalid, ensure_ascii=False), "fail.json")
    assert result.returncode == 1, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["source"]["ok"] is False
    assert report["normalized"]["ok"] is True

    # 操作性错误（文件不存在）→ 2，且不伪装为校验结论
    missing = subprocess.run(
        [sys.executable, "-m", "product_prd_generator.implementation_return_report",
         "/tmp/opencode/__no_such_return__.json"],
        cwd=_SKILL_ROOT, capture_output=True, text=True, timeout=60,
    )
    assert missing.returncode == 2
    assert "operational_error" in json.loads(missing.stdout)

    # 输入 JSON 解析失败 → 操作性错误 exit 2（非校验结论、非 traceback）
    result = _run("{not valid json!!", "bad.json")
    assert result.returncode == 2
    assert "operational_error" in json.loads(result.stdout)


def test_report_dependency_error_is_explicit_not_validation_result() -> None:
    """缺 jsonschema 时报告为显式依赖错误（monkeypatch 移除依赖可见性），
    不是校验通过/失败。"""
    import builtins
    import product_prd_generator.implementation_return_report as report_mod

    real_import = builtins.__import__

    def _blocked(name: str, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        if name == "jsonschema" or name == "referencing":
            raise ImportError(f"blocked for test: {name}")
        return real_import(name, *args, **kwargs)

    builtins.__import__ = _blocked
    try:
        try:
            strict_validation_report({"return_id": "R", "product_id": "lnkcre"})
        except ReportDependencyError as exc:
            assert "jsonschema" in str(exc)
            assert "依赖" in str(exc)
        else:
            raise AssertionError("缺依赖时应抛 ReportDependencyError，而非校验结论")
    finally:
        builtins.__import__ = real_import

