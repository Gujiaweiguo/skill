"""Tests for the risk assessment engine (scripts.risk_engine).

Covers: assess_risk for all risk levels, forbidden terms, absolute phrases,
URLs, repeated chars, batch processing, TriageItem serialization, and
edge cases (empty, unicode, mixed content).
"""

from __future__ import annotations

import pytest

from scripts.risk_engine import (
    ABSOLUTE_PHRASES,
    FORBIDDEN_TERMS,
    TriageItem,
    _get_int,
    _get_str,
    _has_repeated_chars,
    assess_batch,
    assess_risk,
)


class TestAssessRiskLow:
    """Low-risk comments — normal user feedback."""

    @pytest.mark.parametrize("content", [
        "这篇文章写得很好，对智慧物业的分析很深入。",
        "感谢分享，学到了很多。",
        "请问什么时候更新下一期？",
        "Great article, very insightful.",
        "",  # empty string — no flags, still low
    ])
    def test_low_risk(self, content: str) -> None:
        item = assess_risk(1, content)
        assert item.risk_level == "low"
        assert item.risk_flags == []
        assert item.moderation_suggestion == "approve"
        assert item.human_review_required is True

    def test_basic_fields(self) -> None:
        item = assess_risk(42, "normal comment", article_id=10)
        assert item.comment_id == 42
        assert item.article_id == 10
        assert item.content_snippet == "normal comment"


class TestAssessRiskHigh:
    """High-risk — forbidden domain terms present."""

    @pytest.mark.parametrize("term", list(FORBIDDEN_TERMS))
    def test_forbidden_term_triggers_high(self, term: str) -> None:
        item = assess_risk(1, f"推荐{term}服务")
        assert item.risk_level == "high"
        assert any(f.startswith("forbidden_term:") for f in item.risk_flags)
        assert item.moderation_suggestion == "reject"

    def test_forbidden_and_absolute_both_flagged(self) -> None:
        """When both forbidden term and absolute phrase are present,
        risk stays high but both flags appear."""
        content = f"我们是{ABSOLUTE_PHRASES[0]}的数字营销平台"
        item = assess_risk(1, content)
        assert item.risk_level == "high"
        flag_codes = [f.split(":")[0] for f in item.risk_flags]
        assert "forbidden_term" in flag_codes
        assert "absolute_phrase" in flag_codes


class TestAssessRiskMedium:
    """Medium-risk — absolute phrases or URLs without forbidden terms."""

    @pytest.mark.parametrize("phrase", [
        "最领先",
        "最大",
        "唯一",
        "行业第一",
        "遥遥领先",
    ])
    def test_absolute_phrase_triggers_medium(self, phrase: str) -> None:
        item = assess_risk(1, f"我们是{phrase}的平台")
        assert item.risk_level == "medium"
        assert any(f.startswith("absolute_phrase:") for f in item.risk_flags)
        assert item.moderation_suggestion == "review"

    def test_url_triggers_medium(self) -> None:
        item = assess_risk(1, "看这个链接 https://spam-site.example")
        assert item.risk_level == "medium"
        assert "contains_url" in item.risk_flags
        assert item.moderation_suggestion == "review"

    def test_http_url_triggers_medium(self) -> None:
        item = assess_risk(1, "visit http://example.com today")
        assert item.risk_level == "medium"
        assert "contains_url" in item.risk_flags

    def test_repeated_chars_triggers_medium(self) -> None:
        item = assess_risk(1, "啊啊啊啊啊啊啊太好了")
        assert item.risk_level == "medium"
        assert "repeated_chars" in item.risk_flags

    def test_medium_upgraded_to_high_by_forbidden(self) -> None:
        """If both medium and high triggers present, high wins."""
        content = "最领先的数字营销"
        item = assess_risk(1, content)
        assert item.risk_level == "high"
        assert item.moderation_suggestion == "reject"


class TestTriageItemSerialization:
    def test_to_dict_keys(self) -> None:
        item = assess_risk(5, "test", article_id=3)
        d = item.to_dict()
        expected_keys = {
            "comment_id", "article_id", "risk_level", "risk_flags",
            "moderation_suggestion", "auto_actions_taken",
            "human_review_required", "content_snippet",
        }
        assert set(d.keys()) == expected_keys

    def test_auto_actions_always_empty(self) -> None:
        item = assess_risk(1, "数字营销最领先")
        assert item.to_dict()["auto_actions_taken"] == []

    def test_content_snippet_truncation(self) -> None:
        long_text = "x" * 300
        item = assess_risk(1, long_text)
        assert len(item.content_snippet) == 200


class TestAssessBatch:
    def test_batch_consistency(self) -> None:
        comments = [
            {"comment_id": 1, "content": "normal"},
            {"comment_id": 2, "content": "数字营销"},
            {"comment_id": 3, "content": "看 http://spam.com"},
        ]
        items = assess_batch(comments)
        assert len(items) == 3
        assert items[0].risk_level == "low"
        assert items[1].risk_level == "high"
        assert items[2].risk_level == "medium"

    def test_batch_with_alternate_keys(self) -> None:
        """Batch handles 'id' instead of 'comment_id' and 'body' instead of 'content'."""
        comments = [
            {"id": 10, "body": "normal comment"},
        ]
        items = assess_batch(comments)
        assert len(items) == 1
        assert items[0].comment_id == 10

    def test_batch_skips_missing_fields(self) -> None:
        comments = [
            {"comment_id": 1, "content": "ok"},
            {"comment_id": 2},  # missing content — skipped
            {"content": "no id"},  # missing id — skipped
        ]
        items = assess_batch(comments)
        assert len(items) == 1

    def test_batch_empty(self) -> None:
        assert assess_batch([]) == []

    def test_batch_with_article_id(self) -> None:
        comments = [
            {"comment_id": 1, "content": "hi", "article_id": 5},
        ]
        items = assess_batch(comments)
        assert items[0].article_id == 5


class TestHelpers:
    def test_has_repeated_chars_true(self) -> None:
        assert _has_repeated_chars("啊啊啊啊啊啊") is True

    def test_has_repeated_chars_false(self) -> None:
        assert _has_repeated_chars("正常评论") is False

    def test_has_repeated_chars_boundary(self) -> None:
        """Exactly 5 repeated chars triggers (4 repetitions + 1 match)."""
        assert _has_repeated_chars("AAAAA") is True

    def test_has_repeated_chars_below_threshold(self) -> None:
        """4 chars is below threshold."""
        assert _has_repeated_chars("AAAA") is False

    def test_get_int_from_int(self) -> None:
        assert _get_int({"x": 42}, ("x",)) == 42

    def test_get_int_from_numeric_str(self) -> None:
        assert _get_int({"x": "42"}, ("x",)) == 42

    def test_get_int_missing(self) -> None:
        assert _get_int({"x": 1}, ("y",)) is None

    def test_get_int_non_numeric_str(self) -> None:
        assert _get_int({"x": "abc"}, ("x",)) is None

    def test_get_str_present(self) -> None:
        assert _get_str({"x": "hello"}, ("x",)) == "hello"

    def test_get_str_empty(self) -> None:
        assert _get_str({"x": "  "}, ("x",)) is None

    def test_get_str_missing(self) -> None:
        assert _get_str({"x": 1}, ("y",)) is None

    def test_get_str_fallback_key(self) -> None:
        assert _get_str({"a": "first", "b": "second"}, ("b", "a")) == "second"
