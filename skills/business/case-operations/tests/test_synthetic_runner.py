"""Tests for the synthetic runner and mock MCP integration.

Verifies: runner produces 4 artifacts, only calls ``case_create``,
blocks forbidden tools, writes nothing to production paths,
and fail-closed when artifact_dir is outside the system temp dir.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
_TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))
sys.path.insert(0, str(_TESTS_DIR))

from mock_mcp_server import MockMCPError, MockMCPServer
from synthetic_runner import ArtifactDirError, run_synthetic_fixture

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _load_fixture() -> dict[str, object]:
    with FIXTURE_PATH.open() as f:
        return cast_dict(json.load(f))


def cast_dict(d: dict[str, object]) -> dict[str, object]:
    return d


class TestRunnerArtifacts:
    def test_generates_four_artifacts(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            result = run_synthetic_fixture(fixture, mock, Path(tmp))
            assert result.valid
            assert set(result.artifact_paths) == {
                "case-research-pack.md",
                "case-payload.json",
                "validation-report.json",
                "import-receipt.json",
            }
            for name, path in result.artifact_paths.items():
                assert path.exists(), f"missing: {name}"
                assert path.stat().st_size > 0, f"empty: {name}"

    def test_artifact_content(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
            receipt = json.loads(
                (Path(tmp) / "import-receipt.json").read_text(),
            )
            report = json.loads(
                (Path(tmp) / "validation-report.json").read_text(),
            )
            payload = json.loads(
                (Path(tmp) / "case-payload.json").read_text(),
            )
            research = (Path(tmp) / "case-research-pack.md").read_text()
        assert receipt["draft_status"] == "draft"
        assert receipt["fixture"] is True
        assert report["mode"] == "synthetic-test"
        assert payload["slug"] == fixture["slug"]
        assert "FIXTURE" in research


class TestRunnerMCPSafety:
    def test_only_calls_case_create(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        assert mock.get_call_tools() == ["case_create"]

    def test_no_forbidden_calls(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        mock.assert_no_forbidden_calls()

    def test_forbidden_blocked(self) -> None:
        mock = MockMCPServer()
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("case_publish", id="x")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("case_unpublish", id="x")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("case_delete", id="x")

    def test_zero_real_mcp(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        assert len(mock.calls) == 1
        assert mock.calls[0].tool == "case_create"


class TestRunnerDraftResult:
    def test_draft_id_and_status(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            result = run_synthetic_fixture(fixture, mock, Path(tmp))
        assert result.draft_id == "fixture-case-001"
        assert result.draft_status == "draft"


class TestRunnerProductionIsolation:
    def test_no_production_paths(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            tmp_path = Path(tmp)
            run_synthetic_fixture(fixture, mock, tmp_path)
            for f in tmp_path.iterdir():
                assert f.parent == tmp_path


class TestRunnerTempDirEnforcement:
    """Fail-closed when artifact_dir is outside the system temp dir."""

    def test_rejects_home_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path("/tmp/../home/ubuntu/case-ops-out")
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        # mock MCP must not have been called
        assert mock.get_call_tools() == []

    def test_rejects_etc_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path("/etc/case-ops-out")
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_dotdot_bypass(self) -> None:
        """Ensure ``..`` cannot escape the temp dir."""
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
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
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            nested = Path(tmp) / "nested" / "deeper"
            result = run_synthetic_fixture(fixture, mock, nested)
            assert result.valid
            assert all(p.exists() for p in result.artifact_paths.values())
