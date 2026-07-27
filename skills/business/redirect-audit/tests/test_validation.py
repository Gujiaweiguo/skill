"""Validation tests for redirect-audit payloads.

Covers: forbidden actions, forbidden CJK terms, absolute marketing
phrases, audit scope, fixture mode, payload execution_mode rejection,
redirects structure, and synthetic fixture positive path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from scripts.validate import (
    FORBIDDEN_ACTION_KEYS,
    SYNTHETIC_TEST_MODE,
    validate_redirect_payload,
)

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
    result = validate_redirect_payload(
        payload,
        execution_mode=cast("str | None", kw.get("execution_mode")),
    )
    return result.errors


class TestForbiddenActions:
    """Forbidden action keys must be rejected."""

    @pytest.mark.parametrize("key", list(FORBIDDEN_ACTION_KEYS))
    def test_action_key(self, key: str) -> None:
        p = _valid_base()
        p[key] = True
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_action" in codes

    def test_multiple_forbidden_actions(self) -> None:
        p = _valid_base()
        p["auto_create_redirect"] = True
        p["auto_modify_nginx"] = True
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert codes.count("forbidden_action") == 2


class TestForbiddenCjkTerms:
    """Forbidden CJK marketing terms must be rejected."""

    @pytest.mark.parametrize("term", [
        "解决方案", "数字营销", "新零售", "新商业", "新营销", "新消费",
    ])
    def test_rejected(self, term: str) -> None:
        p = _valid_base()
        p["notes"] = f"提供{term}服务"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_cjk_term" in codes

    def test_normal_cjk_allowed(self) -> None:
        p = _valid_base()
        p["notes"] = "这是一个正常的重定向审计备注"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_cjk_term" not in codes


class TestAbsolutePhrases:
    """Absolute marketing phrases must be rejected."""

    @pytest.mark.parametrize(("text", "term"), [
        ("行业最领先的平台", "最领先"),
        ("我们是最大供应商", "最大"),
        ("全国第一的物业系统", "全国第一"),
        ("唯一的解决方案", "唯一"),
        ("遥遥领先于竞品", "遥遥领先"),
    ])
    def test_rejected(self, text: str, term: str) -> None:
        p = _valid_base()
        p["notes"] = text
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        abs_errors = [e for e in errors if e["code"] == "absolute_marketing_term"]
        assert len(abs_errors) == 1
        assert term in abs_errors[0]["message"]

    @pytest.mark.parametrize("text", [
        "最近一次系统升级",
        "最后一个步骤",
        "最终用户确认了方案",
    ])
    def test_neutral_most_phrases_allowed(self, text: str) -> None:
        p = _valid_base()
        p["notes"] = text
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" not in codes


class TestAuditScope:
    """Audit scope validation."""

    @pytest.mark.parametrize("scope", [
        "db-only", "nginx-only", "online-only", "cross-check",
    ])
    def test_valid_scope(self, scope: str) -> None:
        p = _valid_base()
        p["audit_scope"] = scope
        r = validate_redirect_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        scope_errors = [e for e in r.errors if e["code"] == "invalid_audit_scope"]
        assert len(scope_errors) == 0

    def test_invalid_scope(self) -> None:
        p = _valid_base()
        p["audit_scope"] = "production-write"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_audit_scope" in codes

    def test_missing_scope_ok(self) -> None:
        p = _valid_base()
        del p["audit_scope"]
        r = validate_redirect_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        scope_errors = [e for e in r.errors if e["code"] == "invalid_audit_scope"]
        assert len(scope_errors) == 0


class TestFixtureMode:
    """Fixture mode isolation."""

    def test_fixture_without_mode(self) -> None:
        p = _valid_base()
        codes = [e["code"] for e in _errors(p)]
        assert "fixture_requires_synthetic_mode" in codes

    def test_fixture_wrong_mode(self) -> None:
        p = _valid_base()
        r = validate_redirect_payload(p, execution_mode="production")
        assert not r.valid
        assert "fixture_requires_synthetic_mode" in {
            e["code"] for e in r.errors
        }


class TestPayloadExecutionMode:
    """Payload must not self-declare execution_mode."""

    def test_rejected(self) -> None:
        p = _valid_base()
        p["execution_mode"] = "synthetic-test"
        r = validate_redirect_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        assert not r.valid
        assert "execution_mode_in_payload" in {
            e["code"] for e in r.errors
        }

    def test_rejected_without_fixture(self) -> None:
        p = _valid_base()
        del p["fixture"]
        p["execution_mode"] = "production"
        codes = [e["code"] for e in _errors(p)]
        assert "execution_mode_in_payload" in codes


class TestRedirectsStructure:
    """Redirects list structure validation."""

    def test_invalid_type(self) -> None:
        p = _valid_base()
        p["redirects"] = "not-a-list"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_redirects_type" in codes

    def test_invalid_entry_type(self) -> None:
        p = _valid_base()
        p["redirects"] = ["string-entry"]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_redirect_entry_type" in codes

    def test_missing_redirect_fields(self) -> None:
        p = _valid_base()
        p["redirects"] = [{"source_url": "example.com"}]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing_redirect_fields" in codes

    def test_complete_redirect_passes(self) -> None:
        p = _valid_base()
        r = validate_redirect_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        struct_errors = [
            e for e in r.errors
            if e["code"] in ("invalid_redirects_type", "missing_redirect_fields")
        ]
        assert len(struct_errors) == 0

    def test_no_redirects_field_ok(self) -> None:
        p = _valid_base()
        del p["redirects"]
        r = validate_redirect_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        struct_errors = [e for e in r.errors if "redirect" in e.get("code", "")]
        assert len(struct_errors) == 0


class TestSyntheticFixturePositive:
    """The synthetic fixture must pass all validation."""

    def test_passes(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = dict(json.load(f))
        r = validate_redirect_payload(
            fixture, execution_mode=SYNTHETIC_TEST_MODE,
        )
        assert r.valid, f"errors: {r.errors}"
        assert all(r.checks.values())

    def test_markers(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        assert fixture["fixture"] is True
        assert "execution_mode" not in fixture


class TestChecksSummary:
    """Verify the checks dict is populated correctly."""

    def test_clean_payload_all_checks_true(self) -> None:
        p = _valid_base()
        r = validate_redirect_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        assert all(r.checks.values())

    def test_forbidden_action_flags_check(self) -> None:
        p = _valid_base()
        p["auto_create_redirect"] = True
        r = validate_redirect_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        assert not r.checks["forbidden_actions"]
        assert r.checks["forbidden_cjk_terms"]

    def test_cjk_term_flags_check(self) -> None:
        p = _valid_base()
        p["notes"] = "数字营销服务"
        r = validate_redirect_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        assert not r.checks["forbidden_cjk_terms"]
        assert r.checks["forbidden_actions"]


class TestMarketingAdjacentWarning:
    """Marketing-adjacent language in notes should produce warnings."""

    def test_marketing_in_notes_warns(self) -> None:
        p = _valid_base()
        redirects = p.get("redirects")
        assert isinstance(redirects, list)
        redirects[0]["notes"] = "这是一个包含营销的备注"
        r = validate_redirect_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        warn_codes = [w["code"] for w in r.warnings]
        assert "marketing_adjacent_language" in warn_codes
