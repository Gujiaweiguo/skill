"""Reusable synthetic-test runner for seo-audit.

Receives a fixture payload, an injected mock MCP server, and a temp
artifact directory. Validates the payload, calls mock read-only MCP
tools (``redirect_list``, ``url_check``), runs the SEO audit engine
on fixture pages, and generates the required artifacts.

Security:
- Only operates in synthetic-test mode (caller must pass
  ``execution_mode``).
- Only calls ``redirect_list`` and ``url_check`` on the injected
  mock — never reaches real MCP.
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

from scripts.seo_audit_runner import (
    PageRecord,
    SEOAuditRunner,
    parse_html,
)
from scripts.validate import SYNTHETIC_TEST_MODE, ValidationResult, validate_audit_payload


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
        msg = (
            f"artifact_dir must resolve inside {tmp_root}, "
            f"got {resolved}"
        )
        raise ArtifactDirError(msg)


class MockMCPProtocol(Protocol):
    """Minimal protocol the injected mock must satisfy."""

    def redirect_list(self) -> list[dict[str, str]]:
        """List all configured redirects."""
        ...

    def url_check(self, url: str) -> dict[str, str]:
        """Check a single URL status."""
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


def _build_seo_drift_report(
    payload: dict[str, object],
    redirects: list[dict[str, str]],
) -> dict[str, object]:
    """Build the SEO drift report from fixture pages and redirect data.

    Parses fixture HTML pages through the SEO audit engine to produce
    real findings rather than just echoing fixture data.
    """
    pages = payload.get("pages", [])
    if not isinstance(pages, list):
        pages = []

    records: list[PageRecord] = []
    for item in pages:
        if not isinstance(item, dict):
            continue
        html = item.get("html", "")
        url = item.get("url", "")
        if isinstance(html, str) and html:
            record = parse_html(html, url=str(url))
        else:
            record = PageRecord(url=str(url))
        records.append(record)

    # Use SEOAuditRunner in full scope to generate real findings
    audit_scope = str(payload.get("audit_scope", "full"))
    runner = SEOAuditRunner(audit_scope=audit_scope, site="lanlnk.cn")
    report = runner.run(records)

    result = report.to_dict()
    result["redirects"] = redirects
    return result


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
    # 0. Fail-closed: artifact_dir must be inside system temp
    _assert_temp_dir(artifact_dir)

    ts = time.time()

    # 1. Validate — caller-provided execution_mode, never from payload
    result = validate_audit_payload(
        payload, execution_mode=SYNTHETIC_TEST_MODE,
    )
    if not result.valid:
        return SyntheticRunResult(
            valid=False,
            validation=result,
            mcp_calls=[],
        )

    # 2. Mock MCP read-only calls
    redirects = mock_mcp.redirect_list()

    # Check a URL from sitemap entries if available
    sitemap_data = payload.get("sitemap")
    checked_urls: list[dict[str, object]] = []
    if isinstance(sitemap_data, dict):
        entries = sitemap_data.get("entries")
        if isinstance(entries, list) and len(entries) > 0:
            first_entry = entries[0]
            if isinstance(first_entry, dict):
                loc = first_entry.get("loc")
                if isinstance(loc, str):
                    url_result = mock_mcp.url_check(loc)
                    checked_urls.append(dict(url_result))

    mcp_calls = mock_mcp.get_call_tools()

    # 3. Verify no forbidden calls
    mock_mcp.assert_no_forbidden_calls()

    # 4. Generate 3 artifacts
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # 4a. seo-drift-report.json (with real audit findings)
    drift_report = _build_seo_drift_report(payload, redirects)
    (artifact_dir / "seo-drift-report.json").write_text(
        json.dumps(drift_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4b. validation-report.json
    (artifact_dir / "validation-report.json").write_text(
        json.dumps({
            "skill": "seo-audit",
            "skill_version": "0.1.0",
            "mode": SYNTHETIC_TEST_MODE,
            "timestamp": ts,
            **result.to_dict(),
            "mcp_calls": mcp_calls,
            "forbidden_calls_detected": False,
            "url_checks": checked_urls,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4c. fixture-payload.json
    (artifact_dir / "fixture-payload.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    paths = {
        name: artifact_dir / name
        for name in (
            "seo-drift-report.json",
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
