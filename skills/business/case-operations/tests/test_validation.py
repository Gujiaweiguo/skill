"""Validation tests for case-operations payloads.

Covers: ``client_authorized``, required fields, forbidden terms,
absolute phrases, publish/delete intent, fixture mode,
payload self-declared ``execution_mode`` rejection,
and shared-parser runtime invocation proof.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from content_ops_loader import (
    PayloadValidationError as SharedPayloadValidationError,
    parse_case_payload as shared_parse_case_payload,
)
from validate import SYNTHETIC_TEST_MODE, validate_case_payload

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _valid_base() -> dict[str, object]:
    return {
        "slug": "case-ops-synthetic-fixture",
        "client_name": "星河智创中心（测试案例）",
        "industry": "office",
        "client_authorized": True,
        "fixture": True,
        "problem": "虚构场景：需要统一物业服务入口。",
        "solution": "虚构方案：部署智慧物业平台。",
        "outcome": "虚构结果：效率提升50%。",
        "testimonial": "虚构评价。",
        "seo_title": "测试",
        "seo_description": "fixture",
        "image": "/cases/test.webp",
        "product": "office-building",
    }


def _errors(
    payload: dict[str, object], **kw: object,
) -> list[dict[str, str]]:
    result = validate_case_payload(
        payload,
        execution_mode=cast(str | None, kw.get("execution_mode")),
    )
    return result.errors


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


class TestRequiredFields:
    @pytest.mark.parametrize("field", [
        "slug", "client_name", "industry", "problem", "solution", "outcome",
    ])
    def test_missing(self, field: str) -> None:
        p = _valid_base()
        del p[field]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing" in codes


class TestTerms:
    def test_domain_forbidden(self) -> None:
        p = _valid_base()
        p["solution"] = "提供数字营销服务"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_term" in codes

    def test_absolute_marketing_reject(self) -> None:
        """Superlative phrases must be rejected."""
        p = _valid_base()
        p["outcome"] = "行业最领先的平台"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" in codes


class TestAbsoluteFalsePositives:
    """Bare "最" would false-positive on normal text.  Verify
    common neutral phrases containing "最" are allowed."""

    @pytest.mark.parametrize("text", [
        "最近一次系统升级",
        "最后一个步骤",
        "最终用户确认了方案",
        "最高优先级任务是报修",
    ])
    def test_neutral_most_phrases_allowed(self, text: str) -> None:
        p = _valid_base()
        p["problem"] = text
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" not in codes

    @pytest.mark.parametrize("text,term", [
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
        p["outcome"] = text
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        abs_errors = [e for e in errors if e["code"] == "absolute_marketing_term"]
        assert len(abs_errors) == 1
        assert term in abs_errors[0]["message"]


class TestForbiddenActions:
    @pytest.mark.parametrize("key", ["publish", "unpublish", "delete"])
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
        r = validate_case_payload(p, execution_mode="production")
        assert not r.valid
        assert "fixture_requires_synthetic_mode" in {
            e["code"] for e in r.errors
        }


class TestPayloadExecutionMode:
    def test_rejected(self) -> None:
        p = _valid_base()
        p["execution_mode"] = "synthetic-test"
        r = validate_case_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
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


class TestContentOpsCross:
    def test_rejects_missing_authorized(self) -> None:
        p = _valid_base()
        del p["client_authorized"]
        with pytest.raises(SharedPayloadValidationError) as ei:
            shared_parse_case_payload(json.dumps(p, ensure_ascii=False))
        assert "missing_or_false" in {i.code for i in ei.value.issues}

    def test_rejects_false_authorized(self) -> None:
        p = _valid_base()
        p["client_authorized"] = False
        with pytest.raises(SharedPayloadValidationError) as ei:
            shared_parse_case_payload(json.dumps(p, ensure_ascii=False))
        assert "missing_or_false" in {i.code for i in ei.value.issues}


class TestSyntheticFixturePositive:
    def test_passes(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        r = validate_case_payload(
            fixture, execution_mode=SYNTHETIC_TEST_MODE,
        )
        assert r.valid, f"errors: {r.errors}"
        assert all(r.checks.values())

    def test_markers(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        assert fixture["fixture"] is True
        assert "execution_mode" not in fixture
