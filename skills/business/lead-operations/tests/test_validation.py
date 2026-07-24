"""Validation tests for lead-operations payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from scripts.validate import SYNTHETIC_TEST_MODE, ValidationResult, validate_lead_payload

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _valid_base() -> dict[str, object]:
    """Return a copy of the synthetic fixture as a mutable dict."""
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


def _validate(
    payload: dict[str, object], **kw: object,
) -> ValidationResult:
    return validate_lead_payload(
        payload,
        execution_mode=cast("str | None", kw.get("execution_mode")),
    )


def _errors(
    payload: dict[str, object], **kw: object,
) -> list[dict[str, str]]:
    return _validate(payload, **kw).errors


class TestForbiddenLeadIds:
    def test_rejects_id_1(self) -> None:
        p = _valid_base()
        p["lead_ids"] = [1, 3]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_lead_id" in codes

    def test_rejects_id_2(self) -> None:
        p = _valid_base()
        p["lead_ids"] = [2, 4]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_lead_id" in codes


class TestRequiredFields:
    def test_missing_lead_ids(self) -> None:
        p = _valid_base()
        del p["lead_ids"]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing" in codes

    def test_empty_lead_ids(self) -> None:
        p = _valid_base()
        p["lead_ids"] = []
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing" in codes


class TestForbiddenActions:
    @pytest.mark.parametrize("key", [
        "send_email", "send_sms", "send_im",
        "lead_update", "lead_status_change", "lead_assign",
    ])
    def test_action_key(self, key: str) -> None:
        p = _valid_base()
        p[key] = True
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_action" in codes


class TestForbiddenTerms:
    def test_domain_forbidden(self) -> None:
        p = _valid_base()
        p["triage_context"] = "提供数字营销服务"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_term" in codes

    def test_absolute_marketing(self) -> None:
        p = _valid_base()
        p["triage_context"] = "行业最领先的服务"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" in codes


class TestFixtureMode:
    def test_fixture_without_mode(self) -> None:
        p = _valid_base()
        result = validate_lead_payload(p)
        assert not result.valid
        assert "fixture_requires_synthetic_mode" in {
            e["code"] for e in result.errors
        }


class TestPayloadExecutionMode:
    def test_rejected(self) -> None:
        p = _valid_base()
        p["execution_mode"] = "synthetic-test"
        r = validate_lead_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        assert not r.valid
        assert "execution_mode_in_payload" in {
            e["code"] for e in r.errors
        }


class TestSyntheticFixturePositive:
    def test_passes(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        r = validate_lead_payload(
            fixture, execution_mode=SYNTHETIC_TEST_MODE,
        )
        assert r.valid, f"errors: {r.errors}"
        assert all(r.checks.values())
