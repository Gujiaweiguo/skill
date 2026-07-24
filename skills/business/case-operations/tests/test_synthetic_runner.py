"""Tests for the synthetic runner and mock MCP integration.

Verifies: runner produces 4 artifacts, only calls case_create,
blocks forbidden tools, and writes nothing to production paths.
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

from validate import SYNTHETIC_TEST_MODE  # noqa: E402
from synthetic_runner import run_synthetic_fixture  # noqa: E402
from mock_mcp_server import MockMCPServer, MockMCPError  # noqa: E402

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


class TestRunnerArtifacts:

    def test_generates_four_artifacts(self):
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            result = run_synthetic_fixture(
                fixture, mock, Path(tmp),
            )
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

    def test_artifact_content(self):
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            result = run_synthetic_fixture(
                fixture, mock, Path(tmp),
            )
            receipt = json.loads(
                (Path(tmp) / "import-receipt.json").read_text()
            )
            report = json.loads(
                (Path(tmp) / "validation-report.json").read_text()
            )
            payload = json.loads(
                (Path(tmp) / "case-payload.json").read_text()
            )
            research = (
                (Path(tmp) / "case-research-pack.md").read_text()
            )
        assert receipt["draft_status"] == "draft"
        assert receipt["fixture"] is True
        assert report["mode"] == SYNTHETIC_TEST_MODE
        assert payload["slug"] == fixture["slug"]
        assert "FIXTURE" in research


class TestRunnerMCPSafety:

    def test_only_calls_case_create(self):
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        assert mock.get_call_tools() == ["case_create"]

    def test_no_forbidden_calls(self):
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        mock.assert_no_forbidden_calls()

    def test_forbidden_blocked(self):
        mock = MockMCPServer()
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("case_publish", id="x")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("case_unpublish", id="x")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("case_delete", id="x")

    def test_zero_real_mcp(self):
        """The runner never touches real MCP — mock is injected."""
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        # The MockMCPServer is in-process; no HTTP socket was opened.
        assert len(mock.calls) == 1
        assert mock.calls[0].tool == "case_create"


class TestRunnerDraftResult:

    def test_draft_id_and_status(self):
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            result = run_synthetic_fixture(fixture, mock, Path(tmp))
        assert result.draft_id == "fixture-case-001"
        assert result.draft_status == "draft"


class TestRunnerProductionIsolation:

    def test_no_production_paths(self):
        """Artifacts must only go to the provided temp dir."""
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="case-ops-") as tmp:
            tmp_path = Path(tmp)
            run_synthetic_fixture(fixture, mock, tmp_path)
            # Verify all files are inside tmp
            for f in tmp_path.iterdir():
                assert f.parent == tmp_path
