"""Schema conformance test for the six per-skill adapter-capabilities.yaml files.

Approved by owner decisions O1/O2 on 2026-10-04:
``references/adapter-capability-owner-decision-2026-10-04.md``（正式批准记录）。

本测试是**只读**的 schema/首版矩阵一致性校验：
- 不是 registry，不做运行时解析，不接入生产路径——resolver 永不读取 capability 文件
  （方案 B 红线，decision record D-O1）；
- 零第三方依赖（与 product_context 包哲学一致），解析器只接受六个已批准文件的
  统一严格语法；
- 首版 48 格矩阵（含 3 处 ★ 改判 → not-applicable）内嵌于本测试。任何状态变更必须
  同时更新对应 capability 文件的 evidence/verified_at 与本测试矩阵（同 commit 原子化）。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

CONSUMERS = (
    "product-prd-generator",
    "requirement-evaluator",
    "pricing-generator",
    "competitor-product-analyzer",
    "company-intro-generator",
    "strategy-brief-generator",
)

PRODUCTS = (
    "lnkcre",
    "lnkcrm",
    "lnkchat",
    "lnkchatbi",
    "lnkreport",
    "lnkvision",
    "lnkgateway",
    "lnkwebsite",
)

ALLOWED_STATUSES = {
    "implemented",
    "partial",
    "onboarding",
    "unsupported",
    "not-applicable",
    "blocked",
}

REQUIRED_UNIT_KEYS = {
    "consumer_id",
    "product_id",
    "status",
    "evidence",
    "verified_at",
    "owner",
    "notes",
}

# 方案 B 红线：capability 文件不得出现产品路径/revision/authority 事实字段（键级禁令）；
# adapter_status 键级禁令来自 O4 步骤 4（禁止新增 adapter_status 依赖）——evidence 文本
# 引用 product-registry.yaml 条目作溯源不属于依赖（registry 自有字段；该溯源例外已随
# B6 于 2026-10-04 消除，evidence 现指向迁移审计与 owner decision 记录）。
FORBIDDEN_KEYS = {
    "docs_root",
    "code_root",
    "ontology_path",
    "prd_root",
    "ontology_root",
    "ontology_entry",
    "prd_entry",
    "revision",
    "authority",
    "layers",
    "product_status",
    "adapter_status",
}

DECISION_RECORD = "references/adapter-capability-owner-decision-2026-10-04.md"
AUDIT_DATE = "2026-10-04"

# O2 批准的首版 48 格矩阵（含 3 处 ★ 改判：prd-gen×lnkwebsite、pricing×lnkgateway、
# company-intro×lnkgateway → not-applicable）。统计必须等于 EXPECTED_DISTRIBUTION。
# 修订（O5-Q5，2026-10-04）：strategy-brief-generator×lnkcrm partial→implemented
# （owner decision references/adapter-capability-owner-decision-o5-q5-2026-10-04.md，
# 盘点深度 unconfirmed→深盘点可用；evidence 同批更新）。
# 修订（O8，2026-10-04）：pricing-generator×lnkchatbi partial→implemented
# （owner decision references/adapter-capability-owner-decision-o8-2026-10-04.md，
# rejected-registration：随单赠送/打包策略为设计语义，env 人工输入非缺口，
# 不登记标准价；evidence 同批更新）。
EXPECTED_MATRIX: dict[str, dict[str, str]] = {
    "product-prd-generator": {
        "lnkcre": "implemented",
        "lnkcrm": "onboarding",
        "lnkchat": "partial",
        "lnkchatbi": "partial",
        "lnkreport": "partial",
        "lnkvision": "unsupported",
        "lnkgateway": "blocked",
        "lnkwebsite": "not-applicable",
    },
    "requirement-evaluator": {
        "lnkcre": "implemented",
        "lnkcrm": "partial",
        "lnkchat": "partial",
        "lnkchatbi": "partial",
        "lnkreport": "partial",
        "lnkvision": "partial",
        "lnkgateway": "blocked",
        "lnkwebsite": "not-applicable",
    },
    "pricing-generator": {
        "lnkcre": "implemented",
        "lnkcrm": "partial",
        "lnkchat": "unsupported",
        "lnkchatbi": "implemented",
        "lnkreport": "onboarding",
        "lnkvision": "unsupported",
        "lnkgateway": "not-applicable",
        "lnkwebsite": "not-applicable",
    },
    "competitor-product-analyzer": {
        "lnkcre": "implemented",
        "lnkcrm": "partial",
        "lnkchat": "onboarding",
        "lnkchatbi": "onboarding",
        "lnkreport": "onboarding",
        "lnkvision": "onboarding",
        "lnkgateway": "blocked",
        "lnkwebsite": "not-applicable",
    },
    "company-intro-generator": {
        "lnkcre": "implemented",
        "lnkcrm": "partial",
        "lnkchat": "partial",
        "lnkchatbi": "partial",
        "lnkreport": "unsupported",
        "lnkvision": "unsupported",
        "lnkgateway": "not-applicable",
        "lnkwebsite": "not-applicable",
    },
    "strategy-brief-generator": {
        "lnkcre": "implemented",
        "lnkcrm": "implemented",
        "lnkchat": "implemented",
        "lnkchatbi": "implemented",
        "lnkreport": "implemented",
        "lnkvision": "implemented",
        "lnkgateway": "implemented",
        "lnkwebsite": "implemented",
    },
}

EXPECTED_DISTRIBUTION = {
    "implemented": 14,
    "partial": 13,
    "onboarding": 6,
    "unsupported": 5,
    "not-applicable": 7,
    "blocked": 3,
}

_HEX_REVISION_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def capability_path(consumer: str) -> Path:
    return (
        _REPOSITORY_ROOT / "skills" / "business" / consumer
        / "references" / "adapter-capabilities.yaml"
    )


def _value(raw: str) -> str:
    text = raw.strip()
    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    return text


def parse_capability_file(path: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Parse the strict uniform grammar of the approved capability files.

    语法：indent-0 ``key: value`` 顶层标量；``capabilities:`` 开启单元块；
    indent-2 ``- key: value`` 新单元；indent-4 ``key: value`` 单元字段；
    空值 ``evidence:`` 开启 indent-6 ``- item`` 子列表。禁止 tab；跳过注释行。
    任何偏离该语法的行都直接 AssertionError（文件由 O2 批准固定，不允许自由发挥）。
    """
    top: dict[str, str] = {}
    units: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    list_key: str | None = None
    in_capabilities = False
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if "\t" in raw:
            raise AssertionError(f"{path.name}:{lineno}: 禁止 tab 字符")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            current = None
            list_key = None
            key, _, rest = stripped.partition(":")
            key = key.strip()
            if key == "capabilities" and not rest.strip():
                in_capabilities = True
                continue
            if in_capabilities:
                raise AssertionError(
                    f"{path.name}:{lineno}: capabilities 块内不允许再出现顶层键 {key!r}"
                )
            if not rest.strip():
                raise AssertionError(f"{path.name}:{lineno}: 顶层键 {key!r} 缺值")
            top[key] = _value(rest)
            continue
        if not in_capabilities:
            raise AssertionError(f"{path.name}:{lineno}: capabilities 块之前的缩进行: {raw!r}")
        if indent == 2 and stripped.startswith("- "):
            current = {}
            units.append(current)
            list_key = None
            key, _, rest = stripped[2:].partition(":")
            current[key.strip()] = _value(rest)
            continue
        if indent == 4 and current is not None:
            key, _, rest = stripped.partition(":")
            key = key.strip()
            if not rest.strip():
                if key != "evidence":
                    raise AssertionError(
                        f"{path.name}:{lineno}: 仅 evidence 允许子列表，收到 {key!r}"
                    )
                list_key = key
                current[key] = []
                continue
            current[key] = _value(rest)
            list_key = None
            continue
        if indent == 6 and list_key == "evidence" and stripped.startswith("- "):
            assert current is not None
            evidence = current["evidence"]
            evidence.append(_value(stripped[2:]))
            continue
        raise AssertionError(f"{path.name}:{lineno}: 语法违规: {raw!r}")
    return top, units


def load_all() -> dict[str, tuple[dict[str, str], list[dict[str, Any]]]]:
    return {consumer: parse_capability_file(capability_path(consumer)) for consumer in CONSUMERS}


class AdapterCapabilityFilesTest(unittest.TestCase):
    """O2 批准的六个 capability 文件 schema + 首版矩阵一致性。"""

    def test_all_six_files_exist(self) -> None:
        for consumer in CONSUMERS:
            path = capability_path(consumer)
            self.assertTrue(
                path.is_file(),
                f"缺少已批准的 capability 声明文件: {path}",
            )

    def test_file_metadata_matches_decision_record(self) -> None:
        for consumer, (top, _units) in load_all().items():
            self.assertEqual(top.get("schema_version"), "1", consumer)
            self.assertEqual(top.get("consumer_id"), consumer)
            self.assertEqual(top.get("owner"), "opc", consumer)
            self.assertEqual(top.get("verified_at"), AUDIT_DATE, consumer)
            self.assertEqual(top.get("decision_record"), DECISION_RECORD, consumer)

    def test_exactly_eight_units_covering_all_products(self) -> None:
        for consumer, (_top, units) in load_all().items():
            product_ids = [unit.get("product_id") for unit in units]
            self.assertEqual(len(units), 8, consumer)
            self.assertEqual(set(product_ids), set(PRODUCTS), consumer)
            self.assertEqual(len(product_ids), len(set(product_ids)), f"{consumer}: 产品重复")

    def test_unit_contract_all_required_keys_non_empty(self) -> None:
        for consumer, (_top, units) in load_all().items():
            for unit in units:
                self.assertEqual(set(unit), REQUIRED_UNIT_KEYS, f"{consumer}: {unit.get('product_id')}")
                for key in ("consumer_id", "product_id", "status", "verified_at", "owner", "notes"):
                    self.assertTrue(
                        isinstance(unit[key], str) and unit[key].strip(),
                        f"{consumer}/{unit.get('product_id')}: {key} 不能为空",
                    )
                evidence = unit["evidence"]
                self.assertIsInstance(evidence, list, f"{consumer}/{unit.get('product_id')}")
                self.assertGreaterEqual(len(evidence), 1, f"{consumer}/{unit.get('product_id')}: 证据至少 1 条")
                for item in evidence:
                    self.assertTrue(isinstance(item, str) and item.strip(), f"{consumer}: 证据条目为空")

    def test_status_enum_and_dates(self) -> None:
        for consumer, (_top, units) in load_all().items():
            for unit in units:
                label = f"{consumer}/{unit['product_id']}"
                self.assertIn(unit["status"], ALLOWED_STATUSES, label)
                self.assertTrue(_DATE_RE.match(unit["verified_at"]), label)
                self.assertEqual(unit["verified_at"], AUDIT_DATE, label)
                self.assertEqual(unit["owner"], "opc", label)
                self.assertEqual(unit["consumer_id"], consumer, label)

    def test_approved_first_version_matrix(self) -> None:
        for consumer, (_top, units) in load_all().items():
            observed = {unit["product_id"]: unit["status"] for unit in units}
            self.assertEqual(
                observed,
                EXPECTED_MATRIX[consumer],
                f"{consumer}: 状态偏离 O2 批准首版矩阵（变更需 evidence+verified_at+本测试同 commit 更新）",
            )

    def test_status_distribution_matches_decision_record(self) -> None:
        counts: dict[str, int] = {}
        for _consumer, (_top, units) in load_all().items():
            for unit in units:
                counts[unit["status"]] = counts.get(unit["status"], 0) + 1
        self.assertEqual(counts, EXPECTED_DISTRIBUTION)

    def test_no_product_fact_keys_anywhere(self) -> None:
        """方案 B 红线：capability 文件内禁止产品路径/revision/authority 字段（键级）。"""
        for consumer, (top, units) in load_all().items():
            keys = set(top)
            for unit in units:
                keys |= set(unit)
            offending = keys & FORBIDDEN_KEYS
            self.assertFalse(
                offending,
                f"{consumer}: capability 文件出现产品事实字段 {sorted(offending)}（产品事实一律经 resolver）",
            )

    def test_no_absolute_paths_or_revision_hashes_in_text(self) -> None:
        """原始文本禁令：不写本机绝对路径、不写 commit hash（revision 是产品事实）。"""
        for consumer in CONSUMERS:
            text = capability_path(consumer).read_text(encoding="utf-8")
            self.assertNotIn(
                "/opt/code",
                text,
                f"{consumer}: capability 文件禁止本机绝对路径",
            )
            match = _HEX_REVISION_RE.search(text)
            self.assertIsNone(
                match,
                f"{consumer}: capability 文件禁止 commit hash/revision 值，命中 {match and match.group(0)!r}",
            )

    def test_new_files_do_not_depend_on_adapter_status(self) -> None:
        """O4 禁令自检（键级）：六个 capability 文件不携带、不依赖 adapter_status 字段。

        依赖 = 以 adapter_status 为键或消费该字段。evidence 文本曾引用
        product-registry.yaml 条目（registry 自有字段）作溯源不构成依赖；该例外
        已随 B6（2026-10-04）消除——evidence 现指向迁移审计与 owner decision 记录。
        """
        for consumer, (top, units) in load_all().items():
            keys = set(top)
            for unit in units:
                keys |= set(unit)
            self.assertNotIn(
                "adapter_status",
                keys,
                f"{consumer}: capability 文件不得携带 adapter_status 字段（O4 步骤 4 禁令）",
            )


if __name__ == "__main__":
    unittest.main()
