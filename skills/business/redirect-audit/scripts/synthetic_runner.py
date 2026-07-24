"""Reusable synthetic-test runner for redirect-audit.

Receives a fixture payload, an injected mock MCP server, and a temp
artifact directory. Validates the payload, calls mock read-only MCP
tools, and generates 3 required artifacts:

- redirect-drift-report.json
- validation-report.json
- fixture-payload.json

Security:
- Only operates in synthetic-test mode.
- Only calls read-only MCP tools on the injected mock.
- Writes artifacts only inside the system temp dir.
- Fail-closed if artifact_dir resolves outside tempfile.gettempdir().
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, cast

from scripts.validate import SYNTHETIC_TEST_MODE, ValidationResult, validate_redirect_payload


class ArtifactDirError(Exception):
    """Raised when artifact_dir is outside the system temp directory."""


def _assert_temp_dir(artifact_dir: Path) -> None:
    """Fail-closed if artifact_dir resolves outside the system temp dir."""
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

    def redirect_list(self) -> list[dict[str, object]]:
        """List all redirects in the mock DB."""
        ...

    def url_check(self, url: str) -> dict[str, object]:
        """Check a URL via mock curl."""
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
            "artifacts": {k: str(v) for k, v in self.artifact_paths.items()},
        }


def run_synthetic_fixture(
    payload: dict[str, object],
    mock_mcp: MockMCPProtocol,
    artifact_dir: Path,
) -> SyntheticRunResult:
    """Run the synthetic fixture pipeline.

    Args:
        payload: Fixture payload (must contain fixture: true).
        mock_mcp: Injected mock MCP server (test double).
        artifact_dir: Temp directory for artifact output.
            Must resolve inside tempfile.gettempdir().

    Returns:
        SyntheticRunResult with all paths and metadata.

    Raises:
        ArtifactDirError: If artifact_dir is outside the system temp dir.

    """
    _assert_temp_dir(artifact_dir)
    ts = time.time()

    result = validate_redirect_payload(
        payload, execution_mode=SYNTHETIC_TEST_MODE,
    )
    if not result.valid:
        return SyntheticRunResult(
            valid=False,
            validation=result,
            mcp_calls=[],
        )

    redirect_list_result = mock_mcp.redirect_list()
    mcp_calls = mock_mcp.get_call_tools()
    mock_mcp.assert_no_forbidden_calls()

    artifact_dir.mkdir(parents=True, exist_ok=True)

    redirects_raw = payload.get("redirects", [])
    audit_date = str(payload.get("audit_date", "unknown"))
    total_db = str(payload.get("total_redirects_in_db", 0))
    total_doc = str(payload.get("total_redirects_in_doc", 0))

    drifts: list[dict[str, object]] = []
    if isinstance(redirects_raw, list):
        for item in redirects_raw:
            if isinstance(item, dict):
                entry = cast(dict[str, object], item)
                drift = {
                    "source_url": entry.get("source_url", ""),
                    "db_status": entry.get("db_status", ""),
                    "doc_status": entry.get("doc_status", ""),
                    "nginx_status": entry.get("nginx_status", ""),
                    "drift_type": entry.get("drift_type", ""),
                }
                drifts.append(drift)

    drift_report: dict[str, object] = {
        "audit_date": audit_date,
        "total_redirects_in_db": total_db,
        "total_redirects_in_doc": total_doc,
        "drifts": drifts,
    }
    (artifact_dir / "redirect-drift-report.json").write_text(
        json.dumps(drift_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    validation_report: dict[str, object] = {
        "skill": "redirect-audit",
        "skill_version": "0.1.0",
        "mode": SYNTHETIC_TEST_MODE,
        "timestamp": ts,
        **result.to_dict(),
        "mcp_calls": mcp_calls,
        "forbidden_calls_detected": False,
        "redirect_count_from_mcp": len(redirect_list_result),
    }
    (artifact_dir / "validation-report.json").write_text(
        json.dumps(validation_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    clean_payload = {k: v for k, v in payload.items() if k != "execution_mode"}
    (artifact_dir / "fixture-payload.json").write_text(
        json.dumps(clean_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    paths = {
        name: artifact_dir / name
        for name in (
            "redirect-drift-report.json",
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
