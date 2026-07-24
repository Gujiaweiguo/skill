"""Validation tests for seo-audit payloads.

Covers: forbidden jargon, absolute marketing phrases, forbidden actions,
fixture mode, payload self-declared execution_mode rejection,
audit_scope validation, audit_date validation, and synthetic fixture
positive path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from scripts.validate import SYNTHETIC_TEST_MODE, validate_audit_payload

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
    result = validate_audit_payload(
        payload,
        execution_mode=cast("str | None", kw.get("execution_mode")),
    )
    return result.errors


class TestForbiddenJargon:
    """Verify forbidden marketing jargon is rejected."""

    @pytest.mark.parametrize("jargon", [
        "解决方案",
        "数字营销",
        "新零售",
        "新商业",
        "新营销",
        "新消费",
    ])
    def test_rejects_jargon(self, jargon: str) -> None:
        p = _valid_base()
        p["audit_note"] = f"客户提供{jargon}服务"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_term" in codes

    @pytest.mark.parametrize("jargon", [
        "解决方案",
        "数字营销",
    ])
    def test_rejects_jargon_in_nested(self, jargon: str) -> None:
        """Jargon in nested dict values should also be rejected."""
        p = _valid_base()
        meta = {
            "audit_summary": f"涉及{jargon}策略",
        }
        p["custom_fields"] = meta
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_term" in codes


class TestAbsolutePhrases:
    """Verify absolute marketing phrases are rejected."""

    @pytest.mark.parametrize(("text", "term"), [
        ("行业最领先的平台", "最领先"),
        ("我们是最大供应商", "最大"),
        ("全国第一的物业系统", "全国第一"),
        ("唯一的解决方案", "唯一"),
        ("遥遥领先于竞品", "遥遥领先"),
    ])
    def test_rejects_absolute(self, text: str, term: str) -> None:
        p = _valid_base()
        p["audit_note"] = text
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        abs_errors = [e for e in errors if e["code"] == "absolute_marketing_term"]
        assert len(abs_errors) == 1
        assert term in abs_errors[0]["message"]


class TestAbsoluteFalsePositives:
    """Bare '最' should not false-positive on normal text."""

    @pytest.mark.parametrize("text", [
        "最近一次系统升级",
        "最后一个步骤",
        "最终用户确认了方案",
        "最高优先级任务是报修",
    ])
    def test_neutral_phrases_allowed(self, text: str) -> None:
        p = _valid_base()
        p["audit_note"] = text
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" not in codes


class TestForbiddenActions:
    """Verify forbidden write/modify actions are rejected."""

    @pytest.mark.parametrize("key", [
        "auto_modify_nginx",
        "auto_submit_sitemap",
        "auto_modify_canonical",
        "auto_modify_meta",
        "sitemap_write",
    ])
    def test_rejects_action_key(self, key: str) -> None:
        p = _valid_base()
        p[key] = True
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_action" in codes


class TestFixtureMode:
    """Verify fixture mode isolation."""

    def test_fixture_without_mode(self) -> None:
        p = _valid_base()
        codes = [e["code"] for e in _errors(p)]
        assert "fixture_requires_synthetic_mode" in codes

    def test_fixture_wrong_mode(self) -> None:
        p = _valid_base()
        r = validate_audit_payload(p, execution_mode="production")
        assert not r.valid
        assert "fixture_requires_synthetic_mode" in {
            e["code"] for e in r.errors
        }


class TestPayloadExecutionMode:
    """Verify payload self-declared execution_mode is rejected."""

    def test_rejected(self) -> None:
        p = _valid_base()
        p["execution_mode"] = "synthetic-test"
        r = validate_audit_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
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


class TestScopeValidation:
    """Verify audit_scope validation."""

    def test_valid_scopes(self) -> None:
        for scope in ("full", "sitemap-only", "canonical-only", "schema-only"):
            p = _valid_base()
            p["audit_scope"] = scope
            r = validate_audit_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
            assert "invalid_scope" not in {e["code"] for e in r.errors}, f"scope={scope}"

    def test_invalid_scope(self) -> None:
        p = _valid_base()
        p["audit_scope"] = "production"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_scope" in codes


class TestDateFormat:
    """Verify audit_date format validation."""

    def test_valid_date(self) -> None:
        p = _valid_base()
        p["audit_date"] = "2026-07-24"
        r = validate_audit_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        assert "invalid_date_format" not in {e["code"] for e in r.errors}

    def test_invalid_date(self) -> None:
        p = _valid_base()
        p["audit_date"] = "07/24/2026"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "invalid_date_format" in codes

    def test_missing_date_ok(self) -> None:
        p = _valid_base()
        del p["audit_date"]
        r = validate_audit_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        assert "invalid_date_format" not in {e["code"] for e in r.errors}


class TestSyntheticFixturePositive:
    """Verify the synthetic fixture passes all validation."""

    def test_passes(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = dict(json.load(f))
        r = validate_audit_payload(
            fixture, execution_mode=SYNTHETIC_TEST_MODE,
        )
        assert r.valid, f"errors: {r.errors}"
        assert all(r.checks.values())

    def test_markers(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        assert fixture["fixture"] is True
        assert "execution_mode" not in fixture


class TestValidationResultChecks:
    """Verify all check flags are present."""

    def test_all_check_keys(self) -> None:
        p = _valid_base()
        r = validate_audit_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        expected_keys = {
            "forbidden_terms",
            "absolute_terms",
            "no_forbidden_actions",
            "fixture_mode_safe",
            "no_payload_execution_mode",
            "valid_scope",
            "valid_date",
        }
        assert set(r.checks) == expected_keys
