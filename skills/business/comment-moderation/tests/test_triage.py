"""Tests for the triage CLI runner (scripts.triage).

Covers: argument parsing, fixture loading, article filtering,
report structure, MCP fallback error handling, and end-to-end CLI execution.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.triage import (
    build_parser,
    build_report,
    main,
    _filter_by_article,
    _load_from_fixture,
)
from scripts.risk_engine import TriageItem, assess_risk


class TestArgParser:
    def test_required_output(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["--output", "/tmp/out.json"])
        assert args.output == Path("/tmp/out.json")
        assert args.fixture is None
        assert args.mcp_url is None
        assert args.article_id_filter is None

    def test_all_args(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "--output", "/tmp/out.json",
            "--fixture", "fixtures/test.json",
            "--mcp-url", "http://localhost:9999/mcp",
            "--article-id-filter", "42",
        ])
        assert args.fixture == Path("fixtures/test.json")
        assert args.mcp_url == "http://localhost:9999/mcp"
        assert args.article_id_filter == 42


class TestLoadFromFixture:
    def test_single_object(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as f:
            json.dump({"comment_id": 1, "content": "hi"}, f)
            path = Path(f.name)
        try:
            result = _load_from_fixture(path)
            assert len(result) == 1
            assert result[0]["comment_id"] == 1
        finally:
            path.unlink()

    def test_list(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as f:
            json.dump([
                {"comment_id": 1, "content": "a"},
                {"comment_id": 2, "content": "b"},
            ], f)
            path = Path(f.name)
        try:
            result = _load_from_fixture(path)
            assert len(result) == 2
        finally:
            path.unlink()


class TestFilterByArticle:
    def test_no_filter(self) -> None:
        comments = [{"article_id": 1}, {"article_id": 2}]
        assert _filter_by_article(comments, None) == comments

    def test_with_filter(self) -> None:
        comments = [
            {"article_id": 1},
            {"article_id": 2},
            {"article_id": 1},
        ]
        filtered = _filter_by_article(comments, 1)
        assert len(filtered) == 2

    def test_str_article_id(self) -> None:
        """Article ID stored as string should still match int filter."""
        comments = [{"article_id": "42"}, {"article_id": 1}]
        filtered = _filter_by_article(comments, 42)
        assert len(filtered) == 1


class TestBuildReport:
    def test_structure(self) -> None:
        items = [
            assess_risk(1, "normal"),
            assess_risk(2, "数字营销"),
            assess_risk(3, "http://spam.com"),
        ]
        report = build_report(items, "fixture:test.json", None)
        assert report["skill"] == "comment-moderation"
        assert report["total_comments"] == 3
        assert report["risk_summary"]["low"] == 1
        assert report["risk_summary"]["high"] == 1
        assert report["risk_summary"]["medium"] == 1
        assert report["suggestion_summary"]["approve"] == 1
        assert report["suggestion_summary"]["reject"] == 1
        assert report["suggestion_summary"]["review"] == 1
        assert report["auto_actions_taken"] == []
        assert report["human_review_required"] is True
        assert "timestamp" in report

    def test_article_filter_recorded(self) -> None:
        report = build_report([], "mcp:test", 99)
        assert report["article_id_filter"] == 99

    def test_empty_items(self) -> None:
        report = build_report([], "fixture:empty", None)
        assert report["total_comments"] == 0
        assert all(v == 0 for v in report["risk_summary"].values())


class TestMainCLIFixture:
    """End-to-end CLI test using --fixture mode."""

    def test_run_with_synthetic_fixture(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parent.parent
            / "fixtures" / "synthetic-fixture.json"
        )
        with tempfile.TemporaryDirectory(prefix="triage-test-") as tmp:
            output = Path(tmp) / "report.json"
            exit_code = main([
                "--fixture", str(fixture_path),
                "--output", str(output),
            ])
            assert exit_code == 0
            assert output.exists()
            report = json.loads(output.read_text())
            assert report["skill"] == "comment-moderation"
            assert report["total_comments"] == 1
            assert report["auto_actions_taken"] == []

    def test_run_with_multiple_comments(self) -> None:
        """Create a multi-comment fixture and run triage."""
        comments = [
            {"comment_id": 1, "article_id": 10, "content": "好文章"},
            {"comment_id": 2, "article_id": 10, "content": "数字营销推广"},
            {"comment_id": 3, "article_id": 11, "content": "看 http://spam.com"},
        ]
        with tempfile.TemporaryDirectory(prefix="triage-test-") as tmp:
            fixture = Path(tmp) / "comments.json"
            fixture.write_text(json.dumps(comments, ensure_ascii=False))
            output = Path(tmp) / "report.json"
            exit_code = main([
                "--fixture", str(fixture),
                "--output", str(output),
            ])
            assert exit_code == 0
            report = json.loads(output.read_text())
            assert report["total_comments"] == 3
            assert report["risk_summary"]["low"] == 1
            assert report["risk_summary"]["high"] == 1
            assert report["risk_summary"]["medium"] == 1

    def test_article_filter(self) -> None:
        """Test --article-id-filter limits comments in report."""
        comments = [
            {"comment_id": 1, "article_id": 10, "content": "a"},
            {"comment_id": 2, "article_id": 11, "content": "b"},
        ]
        with tempfile.TemporaryDirectory(prefix="triage-test-") as tmp:
            fixture = Path(tmp) / "comments.json"
            fixture.write_text(json.dumps(comments, ensure_ascii=False))
            output = Path(tmp) / "report.json"
            exit_code = main([
                "--fixture", str(fixture),
                "--output", str(output),
                "--article-id-filter", "10",
            ])
            assert exit_code == 0
            report = json.loads(output.read_text())
            assert report["total_comments"] == 1
            assert report["triage"][0]["comment_id"] == 1


class TestMainCLIMCPError:
    """When MCP is unreachable and no fixture provided, exit code 2."""

    def test_mcp_connection_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="triage-test-") as tmp:
            output = Path(tmp) / "report.json"
            with patch.dict("os.environ", {}, clear=True):
                exit_code = main([
                    "--output", str(output),
                    "--mcp-url", "http://127.0.0.1:1/mcp",
                ])
                assert exit_code == 2
                assert not output.exists()
