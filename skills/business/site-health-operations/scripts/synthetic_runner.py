"""Reusable synthetic-test runner for site-health-operations.

Receives a fixture payload, an injected mock MCP server, and a temp
artifact directory.  Validates the payload, calls mock read-only
health-check tools, and generates the 3 required artifacts.

Security:
- Only operates in synthetic-test mode (caller must pass
  ``execution_mode``).
- Only calls ``endpoint_check`` and ``service_status`` on the
  injected mock -- never reaches real MCP.
- Writes artifacts only to a directory inside the system temp dir.
- Fail-closed if ``artifact_dir`` resolves outside
  ``tempfile.gettempdir()``.
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from scripts.validate import SYNTHETIC_TEST_MODE, ValidationResult, validate_health_payload


class ArtifactDirError(Exception):
    """Raised when artifact_dir is outside the system temp directory."""


def _assert_temp_dir(artifact_dir: Path) -> None:
    """Fail-closed if artifact_dir resolves outside system temp.

    Uses ``Path.resolve()`` to expand symlinks and ``..`` segments,
    then checks that the resolved path starts with
    ``tempfile.gettempdir()``.
    """
    tmp_root = Path(tempfile.gettempdir()).resolve()
    resolved = artifact_dir.resolve()
    if tmp_root not in resolved.parents and resolved != tmp_root:
        msg = (
            f"artifact_dir must resolve inside {tmp_root}, "
            f"got {resolved}"
        )
        raise ArtifactDirError(msg)


class MockMCPProtocol(Protocol):
    """Minimal protocol the injected mock must satisfy."""

    def endpoint_check(self, url: str) -> dict[str, object]:
        """Read-only HTTP endpoint probe."""
        ...

    def service_status(self, service_name: str) -> dict[str, object]:
        """Read-only systemd service status."""
        ...

    def get_call_tools(self) -> list[str]:
        """Return ordered list of all tool names called."""
        ...

    def assert_no_forbidden_calls(self) -> None:
        """Assert no forbidden tool was ever called."""
        ...


@dataclass
class SyntheticRunResult:
    """Result of a synthetic fixture run."""

    valid: bool
    validation: ValidationResult
    mcp_calls: list[str]
    artifact_paths: dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "valid": self.valid,
            "mcp_calls": self.mcp_calls,
            "artifacts": {
                k: str(v) for k, v in self.artifact_paths.items()
            },
        }


def _probe_endpoints(
    mock_mcp: MockMCPProtocol,
    endpoints: dict[str, object],
) -> list[dict[str, object]]:
    """Call mock endpoint_check for each endpoint entry."""
    results: list[dict[str, object]] = []
    for ep_name, ep_data in endpoints.items():
        if isinstance(ep_data, dict):
            url = str(ep_data.get("url", f"https://example.com/{ep_name}"))
            resp = mock_mcp.endpoint_check(url)
            results.append({
                "endpoint": ep_name,
                "http_code": resp.get("http_code"),
                "response_time_ms": resp.get("response_time_ms"),
            })
    return results


def _probe_services(
    mock_mcp: MockMCPProtocol,
    services: dict[str, object],
) -> list[dict[str, object]]:
    """Call mock service_status for each service entry."""
    results: list[dict[str, object]] = []
    for svc_name in services:
        resp = mock_mcp.service_status(svc_name)
        results.append({
            "service": svc_name,
            "status": resp.get("status"),
            "uptime_hours": resp.get("uptime_hours"),
        })
    return results


def run_synthetic_fixture(
    payload: dict[str, object],
    mock_mcp: MockMCPProtocol,
    artifact_dir: Path,
) -> SyntheticRunResult:
    """Run the synthetic fixture pipeline.

    Args:
        payload: Fixture payload (must contain ``fixture: true``).
        mock_mcp: Injected mock MCP server (test double).
        artifact_dir: Temp directory for artifact output.
            Must resolve inside ``tempfile.gettempdir()``.

    Returns:
        SyntheticRunResult with all paths and metadata.

    Raises:
        ArtifactDirError: If artifact_dir is outside system temp.

    """
    # 0. Fail-closed: artifact_dir must be inside system temp
    _assert_temp_dir(artifact_dir)

    ts = time.time()

    # 1. Validate -- caller-provided execution_mode
    result = validate_health_payload(
        payload, execution_mode=SYNTHETIC_TEST_MODE,
    )
    if not result.valid:
        return SyntheticRunResult(
            valid=False,
            validation=result,
            mcp_calls=[],
        )

    # 2. Probe services and endpoints via mock MCP
    services = payload.get("services", {})
    endpoints = payload.get("endpoints", {})

    svc_results = (
        _probe_services(mock_mcp, services)
        if isinstance(services, dict)
        else []
    )
    ep_results = (
        _probe_endpoints(mock_mcp, endpoints)
        if isinstance(endpoints, dict)
        else []
    )

    mcp_calls = mock_mcp.get_call_tools()

    # 3. Verify no forbidden calls
    mock_mcp.assert_no_forbidden_calls()

    # 4. Generate 3 artifacts
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # 4a. health-baseline-report.json
    baseline = {
        "skill": "site-health-operations",
        "skill_version": "0.1.0",
        "mode": SYNTHETIC_TEST_MODE,
        "check_date": str(payload.get("check_date", "")),
        "timestamp": ts,
        "services": services,
        "endpoints": endpoints,
        "resources": payload.get("resources", {}),
        "probed_services": svc_results,
        "probed_endpoints": ep_results,
        "drifts_detected": payload.get("drifts_detected", []),
        "auto_actions_taken": [],
    }
    (artifact_dir / "health-baseline-report.json").write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4b. validation-report.json
    (artifact_dir / "validation-report.json").write_text(
        json.dumps({
            "skill": "site-health-operations",
            "skill_version": "0.1.0",
            "mode": SYNTHETIC_TEST_MODE,
            "timestamp": ts,
            **result.to_dict(),
            "mcp_calls": mcp_calls,
            "forbidden_calls_detected": False,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4c. fixture-payload.json
    (artifact_dir / "fixture-payload.json").write_text(
        json.dumps({
            "skill": "site-health-operations",
            "fixture": True,
            "mode": SYNTHETIC_TEST_MODE,
            "timestamp": ts,
            "payload": payload,
            "mcp_calls": mcp_calls,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    paths = {
        name: artifact_dir / name
        for name in (
            "health-baseline-report.json",
            "validation-report.json",
            "fixture-payload.json",
        )
    }

    return SyntheticRunResult(
        valid=True,
        validation=result,
        mcp_calls=mcp_calls,
        artifact_paths=paths,
    )
