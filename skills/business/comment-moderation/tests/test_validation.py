"""Validation tests for comment-moderation payloads.

Covers: required fields, forbidden domain terms, absolute phrases,
forbidden actions (auto_approve/auto_reject/auto_delete/auto_reply/auto_ban),
fixture mode, payload self-declared ``execution_mode`` rejection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from scripts.validate import SYNTHETIC_TEST_MODE, validate_comment_payload

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
    result = validate_comment_payload(
        payload,
        execution_mode=cast("str | None", kw.get("execution_mode")),
    )
    return result.errors


class TestRequiredFields:
    @pytest.mark.parametrize("field_name", [
        "comment_id", "article_id", "content",
    ])
    def test_missing(self, field_name: str) -> None:
        p = _valid_base()
        del p[field_name]
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing" in codes

    @pytest.mark.parametrize("field_name", [
        "comment_id", "article_id", "content",
    ])
    def test_empty_string(self, field_name: str) -> None:
        p = _valid_base()
        p[field_name] = ""
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "missing" in codes


class TestForbiddenTerms:
    @pytest.mark.parametrize("term", [
        "\u89e3\u51b3\u65b9\u6848",
        "\u6570\u5b57\u8425\u9500",
        "\u65b0\u96f6\u552e",
        "\u65b0\u5546\u4e1a",
        "\u65b0\u8425\u9500",
        "\u65b0\u6d88\u8d39",
    ])
    def test_rejected(self, term: str) -> None:
        p = _valid_base()
        p["content"] = f"this comment mentions {term}"
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_term" in codes

    def test_no_forbidden_term_in_fixture(self) -> None:
        p = _valid_base()
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "forbidden_term" not in codes


class TestAbsoluteMarketingPhrases:
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
        p["content"] = text
        errors = _errors(p, execution_mode=SYNTHETIC_TEST_MODE)
        abs_errors = [e for e in errors if e["code"] == "absolute_marketing_term"]
        assert len(abs_errors) == 1
        assert term in abs_errors[0]["message"]


class TestAbsoluteFalsePositives:
    """Bare single-char patterns like bare '最' would false-positive on
    normal text.  Verify common neutral phrases containing '最' are allowed."""

    @pytest.mark.parametrize("text", [
        "\u6700\u8fd1\u4e00\u6b21\u7cfb\u7edf\u5347\u7ea7",
        "\u6700\u540e\u4e00\u4e2a\u6b65\u9aa4",
        "\u6700\u7ec8\u7528\u6237\u786e\u8ba4\u4e86\u65b9\u6848",
        "\u6700\u9ad8\u4f18\u5148\u7ea7\u4efb\u52a1\u662f\u62a5\u4fee",
    ])
    def test_neutral_phrases_allowed(self, text: str) -> None:
        p = _valid_base()
        p["content"] = text
        codes = [e["code"] for e in _errors(p, execution_mode=SYNTHETIC_TEST_MODE)]
        assert "absolute_marketing_term" not in codes


class TestForbiddenActions:
    @pytest.mark.parametrize("key", [
        "auto_approve", "auto_reject", "auto_delete",
        "auto_reply", "auto_ban",
        "comment_approve", "comment_reject", "comment_delete",
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
        r = validate_comment_payload(p, execution_mode="production")
        assert not r.valid
        assert "fixture_requires_synthetic_mode" in {
            e["code"] for e in r.errors
        }


class TestPayloadExecutionMode:
    def test_rejected(self) -> None:
        p = _valid_base()
        p["execution_mode"] = "synthetic-test"
        r = validate_comment_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
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
        r = validate_comment_payload(
            fixture, execution_mode=SYNTHETIC_TEST_MODE,
        )
        assert r.valid, f"errors: {r.errors}"
        assert all(r.checks.values())

    def test_markers(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        assert fixture["fixture"] is True
        assert "execution_mode" not in fixture
