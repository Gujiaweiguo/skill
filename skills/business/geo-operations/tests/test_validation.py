"""Validation tests for geo-operations payloads.

Covers: Baidu verification, GEO profile fields, llms.txt freshness,
forbidden CJK marketing terms, absolute superlatives, forbidden
actions, fixture mode, payload self-declared ``execution_mode``
rejection, and capability drift warnings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from scripts.validate import SYNTHETIC_TEST_MODE, validate_geo_payload

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
    result = validate_geo_payload(
        payload,
        execution_mode=cast("str | None", kw.get("execution_mode")),
    )
    return result.errors


def _warnings(
    payload: dict[str, object], **kw: object,
) -> list[dict[str, str]]:
    result = validate_geo_payload(
        payload,
        execution_mode=cast("str | None", kw.get("execution_mode")),
    )
    return result.warnings


def _profile_mut(
    payload: dict[str, object],
) -> dict[str, object]:
    """Deep-copy and return the mutable geo_profile dict from payload."""
    raw = payload["geo_profile"]
    if not isinstance(raw, dict):
        new: dict[str, object] = {}
        payload["geo_profile"] = new
        return new
    new = dict(raw)
    payload["geo_profile"] = new
    return new


class TestBaiduVerification:
    def test_missing(self) -> None:
        p = _valid_base()
        del p["baidu_verification"]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_baidu" in codes

    def test_not_verified(self) -> None:
        p = _valid_base()
        p["baidu_verification"] = {"status": "pending"}
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "not_verified" in codes

    def test_verified_passes(self) -> None:
        p = _valid_base()
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "not_verified" not in codes
        assert "missing_baidu" not in codes


class TestGeoProfile:
    def test_missing(self) -> None:
        p = _valid_base()
        del p["geo_profile"]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_field" in codes

    @pytest.mark.parametrize("key", [
        "name", "description", "capabilities", "contact_email", "website",
    ])
    def test_missing_field(self, key: str) -> None:
        p = _valid_base()
        profile = _profile_mut(p)
        del profile[key]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_field" in codes

    def test_capabilities_not_list(self) -> None:
        p = _valid_base()
        profile = _profile_mut(p)
        profile["capabilities"] = "not-a-list"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_type" in codes


class TestLlmsTxt:
    def test_missing(self) -> None:
        p = _valid_base()
        del p["llms_txt"]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_field" in codes

    def test_capability_drift_warning(self) -> None:
        p = _valid_base()
        profile = _profile_mut(p)
        profile["capabilities"] = [
            "property-management", "visitor-control",
            "repair-portal", "nonexistent-cap",
        ]
        warns = _warnings(p, execution_mode=SYNTHETIC_TEST_MODE)
        drift_warns = [w for w in warns if w["code"] == "capability_drift"]
        assert len(drift_warns) == 1
        assert "nonexistent-cap" in drift_warns[0]["message"]


class TestForbiddenTerms:
    def test_cjk_marketing_reject(self) -> None:
        p = _valid_base()
        profile = _profile_mut(p)
        profile["description"] = "提供数字营销解决方案"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_term" in codes

    @pytest.mark.parametrize("term", [
        "解决方案", "数字营销", "新零售", "新商业", "新营销", "新消费",
    ])
    def test_each_cjk_term_rejected(self, term: str) -> None:
        p = _valid_base()
        profile = _profile_mut(p)
        profile["description"] = f"我们提供{term}服务"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_term" in codes

    def test_absolute_marketing_reject(self) -> None:
        p = _valid_base()
        profile = _profile_mut(p)
        profile["description"] = "行业最领先的平台"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" in codes


class TestAbsoluteFalsePositives:
    """Bare '最' would false-positive. Verify common neutral phrases pass."""

    @pytest.mark.parametrize("text", [
        "最近一次系统升级",
        "最后一个步骤",
        "最终用户确认了方案",
        "最高优先级任务是报修",
    ])
    def test_neutral_most_phrases_allowed(self, text: str) -> None:
        p = _valid_base()
        profile = _profile_mut(p)
        profile["description"] = text
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" not in codes

    @pytest.mark.parametrize(("text", "term"), [
        ("行业最领先的平台", "最领先"),
        ("我们是最大供应商", "最大"),
        ("全国第一的物业系统", "全国第一"),
        ("唯一的解决方案", "唯一"),
        ("遥遥领先于竞品", "遥遥领先"),
    ])
    def test_real_absolute_phrases_rejected(
        self, text: str, term: str,
    ) -> None:
        p = _valid_base()
        profile = _profile_mut(p)
        profile["description"] = text
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        abs_errors = [e for e in errors if e["code"] == "absolute_marketing_term"]
        assert len(abs_errors) == 1
        assert term in abs_errors[0]["message"]


class TestForbiddenActions:
    @pytest.mark.parametrize("key", [
        "auto_modify_llms_txt",
        "auto_publish_geo_content",
        "auto_submit_search_engine",
        "auto_modify_geo_profile",
    ])
    def test_action_key(self, key: str) -> None:
        p = _valid_base()
        p[key] = True
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_action" in codes


class TestFixtureMode:
    def test_fixture_without_mode(self) -> None:
        p = _valid_base()
        codes = [e["code"] for e in _errors(p)]
        assert "fixture_requires_synthetic_mode" in codes

    def test_fixture_wrong_mode(self) -> None:
        p = _valid_base()
        r = validate_geo_payload(p, execution_mode="production")
        assert not r.valid
        assert "fixture_requires_synthetic_mode" in {
            e["code"] for e in r.errors
        }


class TestPayloadExecutionMode:
    def test_rejected(self) -> None:
        p = _valid_base()
        p["execution_mode"] = "synthetic-test"
        r = validate_geo_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
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


class TestSyntheticFixturePositive:
    def test_passes(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        r = validate_geo_payload(
            fixture, execution_mode=SYNTHETIC_TEST_MODE,
        )
        assert r.valid, f"errors: {r.errors}"
        assert all(r.checks.values())

    def test_markers(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        assert fixture["fixture"] is True
        assert "execution_mode" not in fixture
