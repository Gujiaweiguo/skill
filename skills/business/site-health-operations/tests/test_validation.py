"""Comprehensive validation tests for site-health-operations payloads.

Covers: required fields, service structure, endpoint structure,
resource ranges, forbidden actions, banned CJK terms, absolute
marketing phrases, fixture mode, payload self-declared
``execution_mode`` rejection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from scripts.validate import SYNTHETIC_TEST_MODE, validate_health_payload

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures" / "synthetic-fixture.json"
)


def _valid_base() -> dict[str, object]:
    """Return a copy of the synthetic fixture as a mutable dict."""
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


def _errors(
    payload: dict[str, object], **kw: object,
) -> list[dict[str, str]]:
    """Shortcut: validate and return errors list."""
    result = validate_health_payload(
        payload,
        execution_mode=cast("str | None", kw.get("execution_mode")),
    )
    return result.errors


# --- Required fields ---


class TestRequiredKeys:
    @pytest.mark.parametrize("field", ["check_date", "services", "endpoints", "resources"])
    def test_missing(self, field: str) -> None:
        p = _valid_base()
        del p[field]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_field" in codes


# --- Service structure ---


class TestServicesStructure:
    def test_valid_services_pass(self) -> None:
        p = _valid_base()
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_field" not in codes
        assert "invalid_type" not in codes

    def test_invalid_status(self) -> None:
        p = _valid_base()
        svc = cast("dict", p["services"])
        backend = dict(cast("dict", svc["lnkwebsite-backend"]))
        backend["status"] = "exploding"
        svc["lnkwebsite-backend"] = backend
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_value" in codes

    def test_missing_service_field(self) -> None:
        p = _valid_base()
        svc = cast("dict", p["services"])
        backend = dict(cast("dict", svc["lnkwebsite-backend"]))
        del backend["main_pid"]
        svc["lnkwebsite-backend"] = backend
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_field" in codes

    def test_empty_services_warns(self) -> None:
        p = _valid_base()
        p["services"] = {}
        r = validate_health_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        warn_codes = [w["code"] for w in r.warnings]
        assert "empty_services" in warn_codes

    def test_non_dict_services(self) -> None:
        p = _valid_base()
        p["services"] = "not a dict"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_type" in codes


# --- Endpoint structure ---


class TestEndpointsStructure:
    def test_valid_endpoints_pass(self) -> None:
        p = _valid_base()
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_field" not in codes
        assert "invalid_type" not in codes

    def test_missing_http_code(self) -> None:
        p = _valid_base()
        eps = cast("dict", p["endpoints"])
        homepage = dict(cast("dict", eps["homepage"]))
        del homepage["http_code"]
        eps["homepage"] = homepage
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_field" in codes

    def test_non_dict_endpoint(self) -> None:
        p = _valid_base()
        eps = cast("dict", p["endpoints"])
        eps["broken"] = "not a dict"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_type" in codes


# --- Resource ranges ---


class TestResourcesStructure:
    @pytest.mark.parametrize("field", [
        "disk_used_percent",
        "memory_used_percent",
        "swap_used_percent",
    ])
    def test_missing_resource(self, field: str) -> None:
        p = _valid_base()
        res = cast("dict", p["resources"])
        del res[field]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_field" in codes

    def test_resource_out_of_range(self) -> None:
        p = _valid_base()
        res = cast("dict", p["resources"])
        res["disk_used_percent"] = 150
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "out_of_range" in codes

    def test_resource_negative(self) -> None:
        p = _valid_base()
        res = cast("dict", p["resources"])
        res["memory_used_percent"] = -5
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "out_of_range" in codes


# --- Forbidden actions ---


class TestForbiddenActions:
    @pytest.mark.parametrize("key", [
        "auto_restart_service",
        "auto_modify_nginx",
        "auto_modify_systemd",
        "auto_modify_cron",
        "auto_modify_iptables",
        "auto_send_alert",
    ])
    def test_forbidden_key(self, key: str) -> None:
        p = _valid_base()
        p[key] = True
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_action" in codes


# --- Banned CJK terms ---


class TestBannedCJKTerms:
    @pytest.mark.parametrize("term", [
        "\u89e3\u51b3\u65b9\u6848",  # 解决方案
        "\u6570\u5b57\u8425\u9500",  # 数字营销
        "\u65b0\u96f6\u552e",          # 新零售
        "\u65b0\u5546\u4e1a",          # 新商业
        "\u65b0\u8425\u9500",          # 新营销
        "\u65b0\u6d88\u8d39",          # 新消费
    ])
    def test_banned_term_rejected(self, term: str) -> None:
        p = _valid_base()
        p["note"] = f"some text with {term} inside"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "banned_cjk_term" in codes

    def test_banned_term_in_nested(self) -> None:
        p = _valid_base()
        svc = cast("dict", p["services"])
        backend = dict(cast("dict", svc["lnkwebsite-backend"]))
        backend["note"] = "check \u89e3\u51b3\u65b9\u6848 config"
        svc["lnkwebsite-backend"] = backend
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "banned_cjk_term" in codes


# --- Absolute marketing phrases ---


class TestAbsolutePhrases:
    @pytest.mark.parametrize(("text", "term"), [
        ("\u884c\u4e1a\u6700\u9886\u5148\u7684\u5e73\u53f0", "\u6700\u9886\u5148"),
        ("\u6211\u4eec\u662f\u6700\u5927\u4f9b\u5e94\u5546", "\u6700\u5927"),
        ("\u5168\u56fd\u7b2c\u4e00\u7684\u7269\u4e1a\u7cfb\u7edf", "\u5168\u56fd\u7b2c\u4e00"),
        ("\u552f\u4e00\u7684\u89e3\u51b3\u65b9\u6848", "\u552f\u4e00"),
        ("\u9065\u9065\u9886\u5148\u4e8e\u7ade\u54c1", "\u9065\u9065\u9886\u5148"),
    ])
    def test_real_absolute_phrases_rejected(
        self, text: str, term: str,
    ) -> None:
        p = _valid_base()
        p["summary"] = text
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        abs_errors = [e for e in errors if e["code"] == "absolute_marketing_term"]
        assert len(abs_errors) >= 1
        assert any(term in e["message"] for e in abs_errors)

    @pytest.mark.parametrize("text", [
        "\u6700\u8fd1\u4e00\u6b21\u7cfb\u7edf\u5347\u7ea7",
        "\u6700\u540e\u4e00\u4e2a\u6b65\u9aa4",
        "\u6700\u7ec8\u7528\u6237\u786e\u8ba4\u4e86\u65b9\u6848",
        "\u6700\u9ad8\u4f18\u5148\u7ea7\u4efb\u52a1\u662f\u62a5\u4fee",
    ])
    def test_neutral_phrases_allowed(self, text: str) -> None:
        p = _valid_base()
        p["summary"] = text
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" not in codes


# --- Fixture mode ---


class TestFixtureMode:
    def test_fixture_without_mode(self) -> None:
        p = _valid_base()
        codes = [e["code"] for e in _errors(p)]
        assert "fixture_requires_synthetic_mode" in codes

    def test_fixture_wrong_mode(self) -> None:
        p = _valid_base()
        r = validate_health_payload(p, execution_mode="production")
        assert not r.valid
        assert "fixture_requires_synthetic_mode" in {
            e["code"] for e in r.errors
        }


# --- Payload execution_mode ---


class TestPayloadExecutionMode:
    def test_rejected(self) -> None:
        p = _valid_base()
        p["execution_mode"] = "synthetic-test"
        r = validate_health_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
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
        r = validate_health_payload(
            fixture, execution_mode=SYNTHETIC_TEST_MODE,
        )
        assert r.valid, f"errors: {r.errors}"
        assert all(r.checks.values())

    def test_markers(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        assert fixture["fixture"] is True
        assert "execution_mode" not in fixture
