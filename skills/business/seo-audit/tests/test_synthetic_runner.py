"""Tests for the synthetic runner and mock MCP integration.

Verifies: runner produces 3 artifacts, only calls read-only MCP tools
(``redirect_list``, ``url_check``), blocks forbidden tools, writes
nothing to production paths, and fail-closed when artifact_dir is
outside the system temp dir.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.synthetic_runner import ArtifactDirError, run_synthetic_fixture
from tests.mock_mcp_server import MockMCPError, MockMCPServer

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _load_fixture() -> dict[str, object]:
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


class TestRunnerArtifacts:
    """Verify runner generates all 3 required artifacts."""

    def test_generates_three_artifacts(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="seo-audit-") as tmp:
            result = run_synthetic_fixture(fixture, mock, Path(tmp))
            assert result.valid
            assert set(result.artifact_paths) == {
                "seo-drift-report.json",
                "validation-report.json",
                "fixture-payload.json",
            }
            for name, path in result.artifact_paths.items():
                assert path.exists(), f"missing: {name}"
                assert path.stat().st_size > 0, f"empty: {name}"

    def test_artifact_content(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="seo-audit-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
            drift = json.loads(
                (Path(tmp) / "seo-drift-report.json").read_text(),
            )
            report = json.loads(
                (Path(tmp) / "validation-report.json").read_text(),
            )
            payload = json.loads(
                (Path(tmp) / "fixture-payload.json").read_text(),
            )
        assert drift["audit_date"] == fixture["audit_date"]
        assert report["mode"] == "synthetic-test"
        assert report["skill"] == "seo-audit"
        assert payload["fixture"] is True


class TestRunnerMCPSafety:
    """Verify MCP tool call safety."""

    def test_calls_read_only_tools(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="seo-audit-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        tools = mock.get_call_tools()
        assert tools[0] == "redirect_list"
        assert "url_check" in tools

    def test_no_forbidden_calls(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="seo-audit-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        mock.assert_no_forbidden_calls()

    def test_forbidden_blocked(self) -> None:
        mock = MockMCPServer()
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("sitemap_write", path="safe-test.xml")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("auto_modify_nginx", rule="test")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("auto_modify_canonical", url="https://example.com")


class TestRunnerProductionIsolation:
    """Verify no writes to production paths."""

    def test_no_production_paths(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="seo-audit-") as tmp:
            tmp_path = Path(tmp)
            run_synthetic_fixture(fixture, mock, tmp_path)
            for f in tmp_path.iterdir():
                assert f.parent == tmp_path


class TestRunnerTempDirEnforcement:
    """Fail-closed when artifact_dir is outside the system temp dir."""

    def test_rejects_home_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path.home() / "seo-audit-out"
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_etc_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path("/etc/seo-audit-out")
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_dotdot_bypass(self) -> None:
        """Ensure ``..`` cannot escape the temp dir."""
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="seo-audit-") as tmp:
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
        """A subdir under the system temp dir should be accepted."""
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="seo-audit-") as tmp:
            nested = Path(tmp) / "nested" / "deeper"
            result = run_synthetic_fixture(fixture, mock, nested)
            assert result.valid
            assert all(p.exists() for p in result.artifact_paths.values())
