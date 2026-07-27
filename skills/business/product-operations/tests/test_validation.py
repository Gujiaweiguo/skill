"""Validation tests for product-operations payloads.

Covers: client_authorized, required fields, forbidden domain terms,
absolute phrases, forbidden actions, AI Vision capability gating,
fixture mode, payload self-declared execution_mode rejection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from scripts.validate import SYNTHETIC_TEST_MODE, validate_product_payload

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _valid_base() -> dict[str, object]:
    """Return a copy of the synthetic fixture as a mutable dict."""
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


def _errors(
    payload: dict[str, object], **kw: object,
) -> list[dict[str, str]]:
    result = validate_product_payload(
        payload,
        execution_mode=cast("str | None", kw.get("execution_mode")),
    )
    return result.errors


# --- Client authorized ---


class TestClientAuthorized:
    def test_missing(self) -> None:
        p = _valid_base()
        del p["client_authorized"]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_or_false" in codes

    def test_false(self) -> None:
        p = _valid_base()
        p["client_authorized"] = False
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_or_false" in codes


# --- Required fields ---


class TestRequiredFields:
    @pytest.mark.parametrize("field_name", [
        "slug", "product_name", "category", "short_description",
        "description", "vendor", "capabilities",
    ])
    def test_missing(self, field_name: str) -> None:
        p = _valid_base()
        del p[field_name]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing" in codes


# --- Forbidden domain terms ---


class TestDomainTerms:
    @pytest.mark.parametrize(("term", "text"), [
        ("解决方案", "我们提供解决方案服务"),
        ("数字营销", "数字营销平台"),
        ("新零售", "新零售解决方案"),
        ("新商业", "新商业模式"),
        ("新营销", "新营销策略"),
        ("新消费", "新消费场景"),
    ])
    def test_forbidden_term_rejected(self, term: str, text: str) -> None:
        p = _valid_base()
        p["description"] = text
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        codes = [e["code"] for e in errors]
        assert "forbidden_term" in codes
        matched = [e for e in errors if e["code"] == "forbidden_term"]
        found = any(term in e["message"] for e in matched)
        assert found, f"expected term '{term}' in {[e['message'] for e in matched]}"


# --- Absolute marketing phrases ---


class TestAbsolutePhrases:
    def test_absolute_reject(self) -> None:
        p = _valid_base()
        p["short_description"] = "行业最领先的平台"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" in codes


class TestAbsoluteFalsePositives:
    @pytest.mark.parametrize("text", [
        "最近一次系统升级",
        "最后一个步骤",
        "最终用户确认了方案",
        "最高优先级任务是设备检测",
    ])
    def test_neutral_phrases_allowed(self, text: str) -> None:
        p = _valid_base()
        p["description"] = text
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" not in codes

    @pytest.mark.parametrize(("text", "term"), [
        ("行业最领先的平台", "最领先"),
        ("我们是最大供应商", "最大"),
        ("全国第一的视觉系统", "全国第一"),
        ("唯一的解决方案", "唯一"),
        ("遥遥领先于竞品", "遥遥领先"),
    ])
    def test_real_absolute_phrases_rejected(self, text: str, term: str) -> None:
        p = _valid_base()
        p["short_description"] = text
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        abs_errors = [e for e in errors if e["code"] == "absolute_marketing_term"]
        assert len(abs_errors) == 1
        assert term in abs_errors[0]["message"]


# --- Forbidden actions ---


class TestForbiddenActions:
    @pytest.mark.parametrize("key", [
        "product_publish", "product_unpublish", "product_delete",
        "direct_sql", "bulk_import",
    ])
    def test_action_key(self, key: str) -> None:
        p = _valid_base()
        p[key] = True
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_action" in codes


# --- AI Vision capability gating ---


class TestCapabilityGating:
    def test_mvp_capability_allowed(self) -> None:
        p = _valid_base()
        result = validate_product_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        cap_errors = [e for e in result.errors if e["code"] == "invalid_capability_status"]
        assert len(cap_errors) == 0

    def test_non_mvp_as_mvp_rejected(self) -> None:
        p = _valid_base()
        raw_caps = p["capabilities"]
        assert isinstance(raw_caps, list)
        caps: list[dict[str, object]] = list(raw_caps)  # Make type explicit
        caps.append({"name": "未知功能", "status": "mvp"})
        p["capabilities"] = caps
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        codes = [e["code"] for e in errors]
        assert "invalid_capability_status" in codes

    def test_mvp_capability_not_mvp_status_rejected(self) -> None:
        p = _valid_base()
        raw_caps = p["capabilities"]
        assert isinstance(raw_caps, list)
        caps: list[dict[str, object]] = list(raw_caps)  # Make type explicit
        caps[0] = {"name": "通道拥堵检测", "status": "roadmap"}
        p["capabilities"] = caps
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        codes = [e["code"] for e in errors]
        assert "invalid_capability_status" in codes

    def test_capabilities_not_list(self) -> None:
        p = _valid_base()
        p["capabilities"] = "invalid"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_type" in codes

    def test_capability_missing_name(self) -> None:
        p = _valid_base()
        caps = [{"status": "mvp"}]
        p["capabilities"] = caps
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing" in codes


# --- Fixture mode ---


class TestFixtureMode:
    def test_fixture_without_mode(self) -> None:
        p = _valid_base()
        codes = [e["code"] for e in _errors(p)]
        assert "fixture_requires_synthetic_mode" in codes

    def test_fixture_wrong_mode(self) -> None:
        p = _valid_base()
        r = validate_product_payload(p, execution_mode="production")
        assert not r.valid
        assert "fixture_requires_synthetic_mode" in {
            e["code"] for e in r.errors
        }


# --- Payload execution_mode ---


class TestPayloadExecutionMode:
    def test_rejected(self) -> None:
        p = _valid_base()
        p["execution_mode"] = "synthetic-test"
        r = validate_product_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        assert not r.valid
        assert "execution_mode_in_payload" in {
            e["code"] for e in r.errors
        }

    def test_rejected_even_without_fixture(self) -> None:
        p = _valid_base()
        del p["fixture"]
        p["execution_mode"] = "production"
        codes = [e["code"] for e in _errors(p)]
        assert "execution_mode_in_payload" in codes


# --- Synthetic fixture positive ---


class TestSyntheticFixturePositive:
    def test_passes(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        r = validate_product_payload(
            fixture, execution_mode=SYNTHETIC_TEST_MODE,
        )
        assert r.valid, f"errors: {r.errors}"
        assert all(r.checks.values())

    def test_markers(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        assert fixture["fixture"] is True
        assert "execution_mode" not in fixture
