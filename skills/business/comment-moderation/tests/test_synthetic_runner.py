"""Tests for the synthetic runner and mock MCP integration.

Verifies: runner produces 3 artifacts, only calls read-only MCP tools,
blocks forbidden tools, writes nothing to production paths,
and fail-closed when artifact_dir is outside the system temp dir.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import cast

import pytest

from scripts.synthetic_runner import ArtifactDirError, run_synthetic_fixture
from tests.mock_mcp_server import MockMCPServer

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _load_fixture() -> dict[str, object]:
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


def _mock_with_comments(
    comments: list[dict[str, object]],
) -> MockMCPServer:
    """Create a MockMCPServer pre-loaded with given comments."""
    mock = MockMCPServer()
    for rec in comments:
        cid = cast("int", rec.get("comment_id", 0))
        db = getattr(mock, "_db")
        db[cid] = dict(rec)
    return mock


class TestRunnerArtifacts:
    def test_generates_three_artifacts(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            result = run_synthetic_fixture(fixture, mock, Path(tmp))
            assert result.valid
            assert set(result.artifact_paths) == {
                "comment-triage-report.json",
                "validation-report.json",
                "fixture-payload.json",
            }
            for name, path in result.artifact_paths.items():
                assert path.exists(), f"missing: {name}"
                assert path.stat().st_size > 0, f"empty: {name}"

    def test_artifact_content(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
            report = json.loads(
                (Path(tmp) / "validation-report.json").read_text(),
            )
            payload = json.loads(
                (Path(tmp) / "fixture-payload.json").read_text(),
            )
        assert report["mode"] == "synthetic-test"
        assert payload["comment_id"] == fixture["comment_id"]


class TestRunnerTriageReport:
    def test_triage_report_structure(self) -> None:
        fixture = _load_fixture()
        comments: list[dict[str, object]] = [
            {"comment_id": 1, "article_id": 10, "content": "normal comment"},
            {"comment_id": 2, "article_id": 10, "content": "has a link http://example.com"},
        ]
        mock = _mock_with_comments(comments)
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
            triage = json.loads(
                (Path(tmp) / "comment-triage-report.json").read_text(),
            )
        assert triage["total_comments"] == 2
        assert len(triage["triage"]) == 2
        assert triage["triage"][0]["comment_id"] == 1
        assert triage["triage"][0]["auto_actions_taken"] == []

    def test_triage_detects_forbidden_terms(self) -> None:
        fixture = _load_fixture()
        comments: list[dict[str, object]] = [
            {"comment_id": 1, "article_id": 10, "content": "normal comment"},
            {
                "comment_id": 2, "article_id": 10,
                "content": "check out our \u6570\u5b57\u8425\u9500 solutions",
            },
        ]
        mock = _mock_with_comments(comments)
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
            triage = json.loads(
                (Path(tmp) / "comment-triage-report.json").read_text(),
            )
        high_items = [t for t in triage["triage"] if t["risk_level"] == "high"]
        assert len(high_items) == 1
        assert high_items[0]["comment_id"] == 2
        assert "forbidden_term:" in high_items[0]["risk_flags"][0]


class TestRunnerMCPSafety:
    def test_only_calls_read_only_tools(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        tools = mock.get_call_tools()
        for tool in tools:
            assert tool in ("comment_list", "comment_get")

    def test_no_forbidden_calls(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        mock.assert_no_forbidden_calls()

    def test_zero_real_mcp(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        assert len(mock.calls) > 0
        for c in mock.calls:
            assert c.tool in ("comment_list", "comment_get")


class TestRunnerTempDirEnforcement:
    """Fail-closed when artifact_dir is outside the system temp dir."""

    def test_rejects_home_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path.home() / "comment-mod-out"
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_etc_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path("/etc/comment-mod-out")
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_dotdot_bypass(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            bad_dir = Path(tmp) / ".." / ".." / "opt" / "code"
            with pytest.raises(ArtifactDirError, match="must resolve inside"):
                run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_absolute_opt_path(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path("/opt/code/lnkwebsite/artifacts/runs")
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_accepts_nested_temp_subdir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            nested = Path(tmp) / "nested" / "deeper"
            result = run_synthetic_fixture(fixture, mock, nested)
            assert result.valid
            assert all(p.exists() for p in result.artifact_paths.values())


class TestRunnerInvalidation:
    def test_invalid_payload_no_artifacts(self) -> None:
        fixture = _load_fixture()
        del fixture["comment_id"]
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="comment-mod-") as tmp:
            result = run_synthetic_fixture(fixture, mock, Path(tmp))
            assert not result.valid
            assert len(list(Path(tmp).iterdir())) == 0
