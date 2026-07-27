"""Reusable synthetic-test runner for geo-operations.

Receives a fixture payload, an injected mock MCP server, and a temp
artifact directory.  Validates the payload, reads mock GEO profile
data, and generates 3 required artifacts:

- geo-drift-report.json
- validation-report.json
- fixture-payload.json

Security:
- Only operates in synthetic-test mode (caller must pass
  ``execution_mode``).
- Only calls ``geo_profile_get`` / ``geo_profile_list`` on the
  injected mock -- never reaches real MCP.
- Writes artifacts only to a directory inside the system temp dir.
- Fail-closed if ``artifact_dir`` resolves outside ``tempfile.gettempdir()``.
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from scripts.validate import SYNTHETIC_TEST_MODE, ValidationResult, validate_geo_payload


class ArtifactDirError(Exception):
    """Raised when artifact_dir is outside the system temp directory."""


def _assert_temp_dir(artifact_dir: Path) -> None:
    """Fail-closed if artifact_dir resolves outside the system temp dir.

    Uses ``Path.resolve()`` to expand symlinks and ``..`` segments,
    then checks that the resolved path starts with
    ``tempfile.gettempdir()``.
    """
    tmp_root = Path(tempfile.gettempdir()).resolve()
    resolved = artifact_dir.resolve()
    if tmp_root not in resolved.parents and resolved != tmp_root:
        msg = f"artifact_dir must resolve inside {tmp_root}, got {resolved}"
        raise ArtifactDirError(msg)


class MockMCPProtocol(Protocol):
    """Minimal protocol the injected mock must satisfy."""

    def geo_profile_get(self, profile_id: str) -> dict[str, object] | None:
        """Fetch a single GEO profile by ID."""
        ...

    def geo_profile_list(self) -> list[dict[str, object]]:
        """List all GEO profiles."""
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
    profile_id: str
    mcp_calls: list[str]
    artifact_paths: dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "valid": self.valid,
            "profile_id": self.profile_id,
            "mcp_calls": self.mcp_calls,
            "artifacts": {k: str(v) for k, v in self.artifact_paths.items()},
        }


def _build_drift_report(
    payload: dict[str, object],
    profile_data: dict[str, object] | None,
    ts: float,
) -> dict[str, object]:
    """Build the geo-drift-report artifact."""
    report: dict[str, object] = {
        "skill": "geo-operations",
        "skill_version": "0.1.0",
        "mode": SYNTHETIC_TEST_MODE,
        "timestamp": ts,
        "profile_id": str(payload.get("geo_profile_id", "")),
        "baidu_status": "unknown",
        "llms_txt_freshness": "unknown",
        "capability_drift": [],
        "profile_consistency": "unknown",
    }

    baidu = payload.get("baidu_verification")
    if isinstance(baidu, dict):
        report["baidu_status"] = str(baidu.get("status", "unknown"))

    llms = payload.get("llms_txt")
    if isinstance(llms, dict):
        report["llms_txt_freshness"] = str(llms.get("last_updated", "unknown"))
        cap_pages = llms.get("capability_pages")
        geo_profile = payload.get("geo_profile")
        if isinstance(cap_pages, list) and isinstance(geo_profile, dict):
            geo_caps = geo_profile.get("capabilities", [])
            page_slugs = {
                str(p.get("slug", "")) for p in cap_pages if isinstance(p, dict)
            }
            missing = [
                str(c) for c in geo_caps if str(c) not in page_slugs
            ]
            report["capability_drift"] = missing

    if profile_data is not None:
        report["profile_consistency"] = "consistent"

    return report


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
        ArtifactDirError: If ``artifact_dir`` is outside the system
            temp directory.

    """
    _assert_temp_dir(artifact_dir)
    ts = time.time()

    # 1. Validate -- caller-provided execution_mode, never from payload
    result = validate_geo_payload(
        payload, execution_mode=SYNTHETIC_TEST_MODE,
    )
    if not result.valid:
        return SyntheticRunResult(
            valid=False,
            validation=result,
            profile_id="",
            mcp_calls=[],
        )

    # 2. Mock MCP geo_profile_get (read-only)
    profile_id = str(payload.get("geo_profile_id", ""))
    profile_data = mock_mcp.geo_profile_get(profile_id)
    mcp_calls = mock_mcp.get_call_tools()

    # 3. Verify no forbidden calls
    mock_mcp.assert_no_forbidden_calls()

    # 4. Generate 3 artifacts
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # 4a. geo-drift-report.json
    drift_report = _build_drift_report(payload, profile_data, ts)
    (artifact_dir / "geo-drift-report.json").write_text(
        json.dumps(drift_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4b. validation-report.json
    (artifact_dir / "validation-report.json").write_text(
        json.dumps({
            "skill": "geo-operations",
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
            "skill": "geo-operations",
            "fixture": True,
            "profile_id": profile_id,
            "timestamp": ts,
            "payload": payload,
            "mcp_calls": mcp_calls,
            "forbidden_calls": [],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    paths = {
        name: artifact_dir / name
        for name in (
            "geo-drift-report.json",
            "validation-report.json",
            "fixture-payload.json",
        )
    }

    return SyntheticRunResult(
        valid=True,
        validation=result,
        profile_id=profile_id,
        mcp_calls=mcp_calls,
        artifact_paths=paths,
    )
