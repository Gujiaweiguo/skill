"""Tests for the synthetic runner and mock MCP integration.

Verifies: runner produces 3 artifacts, only calls read-only MCP tools,
blocks forbidden tools, writes nothing to production paths,
and fail-closed when artifact_dir is outside the system temp dir.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.synthetic_runner import ArtifactDirError, run_synthetic_fixture
from tests.mock_mcp_server import MockMCPError, MockMCPServer

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures" / "synthetic-fixture.json"
)


def _load_fixture() -> dict[str, object]:
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


class TestRunnerArtifacts:
    def test_generates_three_artifacts(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="site-health-ops-") as tmp:
            result = run_synthetic_fixture(fixture, mock, Path(tmp))
            assert result.valid
            assert set(result.artifact_paths) == {
                "health-baseline-report.json",
                "validation-report.json",
                "fixture-payload.json",
            }
            for name, path in result.artifact_paths.items():
                assert path.exists(), f"missing: {name}"
                assert path.stat().st_size > 0, f"empty: {name}"

    def test_artifact_content(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="site-health-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
            baseline = json.loads(
                (Path(tmp) / "health-baseline-report.json").read_text(),
            )
            report = json.loads(
                (Path(tmp) / "validation-report.json").read_text(),
            )
            fpayload = json.loads(
                (Path(tmp) / "fixture-payload.json").read_text(),
            )
        assert baseline["mode"] == "synthetic-test"
        assert baseline["auto_actions_taken"] == []
        assert report["valid"] is True
        assert report["mode"] == "synthetic-test"
        assert fpayload["fixture"] is True


class TestRunnerMCPSafety:
    def test_only_calls_read_only_tools(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="site-health-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        tools = mock.get_call_tools()
        assert all(t in {"endpoint_check", "service_status"} for t in tools)

    def test_no_forbidden_calls(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="site-health-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        mock.assert_no_forbidden_calls()

    def test_forbidden_blocked(self) -> None:
        mock = MockMCPServer()
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("restart_service", service_name="x")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("modify_nginx", vhost="x")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("modify_systemd", unit="x")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("modify_cron", job="x")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("modify_iptables", rule="x")
        with pytest.raises(MockMCPError, match="FORBIDDEN"):
            mock.call("send_alert", message="x")

    def test_zero_real_mcp(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="site-health-ops-") as tmp:
            run_synthetic_fixture(fixture, mock, Path(tmp))
        # 4 services + 6 endpoints (homepage, www, openclaw, chatbi, api, sitemap)
        svc_count = sum(
            1 for name in fixture.get("services", {})
            if isinstance(fixture.get("services", {}), dict)
        )
        ep_count = sum(
            1 for name in fixture.get("endpoints", {})
            if isinstance(fixture.get("endpoints", {}), dict)
        )
        expected_total = svc_count + ep_count
        assert len(mock.calls) == expected_total


class TestRunnerTempDirEnforcement:
    """Fail-closed when artifact_dir is outside the system temp dir."""

    def test_rejects_home_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path.home() / "site-health-ops-out"
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_etc_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        bad_dir = Path("/etc/site-health-ops-out")
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            run_synthetic_fixture(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_dotdot_bypass(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        with tempfile.TemporaryDirectory(prefix="site-health-ops-") as tmp:
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
        with tempfile.TemporaryDirectory(prefix="site-health-ops-") as tmp:
            nested = Path(tmp) / "nested" / "deeper"
            result = run_synthetic_fixture(fixture, mock, nested)
            assert result.valid
            assert all(p.exists() for p in result.artifact_paths.values())
