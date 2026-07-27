"""Tests for the synthetic runner and mock MCP integration.

Verifies: runner produces 3 artifacts, only calls read-only MCP tools,
blocks forbidden tools, writes nothing to production paths, and
fail-closed when artifact_dir is outside the system temp dir.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import cast

import pytest

from scripts.synthetic_runner import ArtifactDirError, run_synthetic_fixture
from tests.mock_mcp_server import MockMCPError, MockMCPServer

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _load_fixture() -> dict[str, object]:
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


def _get_redirects(
    payload: dict[str, object],
) -> list[dict[str, object]]:
    """Extract and type-narrow the redirects list from a payload."""
    raw = payload.get("redirects", [])
    return cast("list[dict[str, object]]", raw)


def _setup_mock_with_redirects(
    fixture: dict[str, object],
) -> MockMCPServer:
    """Create a mock MCP server pre-loaded with fixture redirects."""
    mock = MockMCPServer()
    mock.load_redirects(_get_redirects(fixture))
    return mock


class TestRunnerArtifacts:
    def test_generates_three_artifacts(self) -> None:
        fixture = _load_fixture()
        mock = _setup_mock_with_redirects(fixture)
        with tempfile.TemporaryDirectory(prefix="redirect-audit-") as tmp:
            result = run_synthetic_fixture(fixture, mock, Path(tmp))
            assert result.valid
            assert set(result.artifact_paths) == {
                "redirect-drift-report.json",
                "validation-report.json",
                "fixture-payload.json",
            }
            for name, path in result.artifact_paths.items():
                assert path.exists(), f"missing: {name}"
                assert path.stat().st_size > 0, f"empty: {name}"

    def test_artifact_content(self) -> None:
        fixture = _load_fixture()
        mock = _setup_mock_with_redirects(fixture)
        with tempfile.TemporaryDirectory(prefix="redirect-audit-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
            drift_report = json.loads(
                (Path(tmp) / "redirect-drift-report.json").read_text(),
            )
            validation_report = json.loads(
                (Path(tmp) / "validation-report.json").read_text(),
            )
            payload_out = json.loads(
                (Path(tmp) / "fixture-payload.json").read_text(),
            )
        assert validation_report["mode"] == "synthetic-test"
        assert validation_report["skill"] == "redirect-audit"
        assert "drifts" in drift_report
        assert payload_out["fixture"] is True


class TestRunnerMCPSafety:
    def test_only_calls_redirect_list(self) -> None:
        fixture = _load_fixture()
        mock = _setup_mock_with_redirects(fixture)
        with tempfile.TemporaryDirectory(prefix="redirect-audit-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        assert "redirect_list" in mock.get_call_tools()

    def test_no_forbidden_calls(self) -> None:
        fixture = _load_fixture()
        mock = _setup_mock_with_redirects(fixture)
        with tempfile.TemporaryDirectory(prefix="redirect-audit-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        mock.assert_no_forbidden_calls()

    def test_forbidden_blocked(self) -> None:
        mock = MockMCPServer()
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("redirect_create")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("auto_modify_nginx")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("sitemap_write")

    def test_zero_real_mcp(self) -> None:
        fixture = _load_fixture()
        mock = _setup_mock_with_redirects(fixture)
        with tempfile.TemporaryDirectory(prefix="redirect-audit-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        assert mock.calls[0].tool == "redirect_list"


class TestRunnerInvalidPayload:
    def test_invalid_returns_no_artifacts(self) -> None:
        fixture = _load_fixture()
        fixture["auto_create_redirect"] = True
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="redirect-audit-") as tmp:
            result = run_synthetic_fixture(fixture, mock, Path(tmp))
            assert not result.valid
            assert len(result.artifact_paths) == 0
            assert mock.get_call_tools() == []


class TestRunnerTempDirEnforcement:
    """Fail-closed when artifact_dir is outside the system temp dir."""

    def test_rejects_home_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path.home() / "redirect-audit-out"
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_etc_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path("/etc/redirect-audit-out")
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_dotdot_bypass(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="redirect-audit-") as tmp:
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
        mock = _setup_mock_with_redirects(fixture)
        with tempfile.TemporaryDirectory(prefix="redirect-audit-") as tmp:
            nested = Path(tmp) / "nested" / "deeper"
            result = run_synthetic_fixture(fixture, mock, nested)
            assert result.valid
            assert all(p.exists() for p in result.artifact_paths.values())


class TestMockMCPReadOperations:
    """Mock MCP read-only operations work correctly."""

    def test_redirect_list(self) -> None:
        mock = MockMCPServer()
        mock.load_redirects([
            {"source_url": "test.com", "status": "active"},
        ])
        result = mock.redirect_list()
        assert len(result) == 1
        assert result[0]["source_url"] == "test.com"

    def test_url_check(self) -> None:
        mock = MockMCPServer()
        mock.load_redirects([
            {"source_url": "test.com", "online_status_code": 301},
        ])
        result = mock.url_check("test.com")
        assert result["status_code"] == 301
        assert result["reachable"] is True

    def test_url_check_unknown(self) -> None:
        mock = MockMCPServer()
        result = mock.url_check("unknown.example.com")
        assert result["status_code"] == 404
