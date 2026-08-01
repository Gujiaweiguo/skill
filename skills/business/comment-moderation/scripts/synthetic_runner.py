"""Reusable synthetic-test runner for comment-moderation.

Receives fixture comments, an injected mock MCP server, and a temp
artifact directory.  Validates comments, reads them via mock
``comment_list`` / ``comment_get``, and generates 3 required artifacts.

Security:
- Only operates in synthetic-test mode (caller must pass ``execution_mode``).
- Only calls read-only MCP tools on the injected mock -- never reaches real MCP.
- Writes artifacts only to a directory inside the system temp dir.
- Fail-closed if ``artifact_dir`` resolves outside ``tempfile.gettempdir()``.
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, cast

from scripts.risk_engine import TriageItem, assess_batch
from scripts.validate import SYNTHETIC_TEST_MODE, ValidationResult, validate_comment_payload


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

    def comment_list(self) -> list[dict[str, object]]:
        """List all comments in the mock CMS."""
        ...

    def comment_get(self, comment_id: int) -> dict[str, object] | None:
        """Get a single comment by ID."""
        ...

    def get_call_tools(self) -> list[str]:
        """Return ordered list of all tool names called."""
        ...

    def assert_no_forbidden_calls(self) -> None:
        """Assert no forbidden tool was ever called."""
        ...


# CommentTriageItem and _assess_risk are now in scripts.risk_engine
# as TriageItem and assess_risk, re-exported here for backward compat.
CommentTriageItem = TriageItem


@dataclass
class SyntheticRunResult:
    """Result of a synthetic fixture run."""

    valid: bool
    validation: ValidationResult
    triage_count: int
    mcp_calls: list[str]
    artifact_paths: dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "valid": self.valid,
            "triage_count": self.triage_count,
            "mcp_calls": self.mcp_calls,
            "artifacts": {k: str(v) for k, v in self.artifact_paths.items()},
        }


def run_synthetic_fixture(
    payload: dict[str, object],
    mock_mcp: MockMCPProtocol,
    artifact_dir: Path,
) -> SyntheticRunResult:
    """Run the synthetic comment-moderation pipeline.

    Args:
        payload: Fixture payload (must contain ``fixture: true``).
        mock_mcp: Injected mock MCP server (test double).
        artifact_dir: Temp directory for artifact output.

    Returns:
        SyntheticRunResult with all paths and metadata.

    Raises:
        ArtifactDirError: If artifact_dir is outside system temp.

    """
    _assert_temp_dir(artifact_dir)

    ts = time.time()

    # 1. Validate -- caller-provided execution_mode, never from payload
    result = validate_comment_payload(
        payload, execution_mode=SYNTHETIC_TEST_MODE,
    )
    if not result.valid:
        return SyntheticRunResult(
            valid=False,
            validation=result,
            triage_count=0,
            mcp_calls=[],
        )

    # 2. Mock MCP read-only calls
    comments = mock_mcp.comment_list()
    mcp_calls = mock_mcp.get_call_tools()

    # Also exercise comment_get for each comment
    triage_items: list[TriageItem] = []
    for comment in comments:
        cid = cast("int", comment.get("comment_id", comment.get("id", 0)))
        fetched = mock_mcp.comment_get(cid)
        if fetched is not None:
            triage_items.append(
                assess_batch([fetched])[0],
            )
    mcp_calls = mock_mcp.get_call_tools()

    # 3. Verify no forbidden calls
    mock_mcp.assert_no_forbidden_calls()

    # 4. Generate 3 artifacts
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # 4a. comment-triage-report.json
    triage_report = {
        "skill": "comment-moderation",
        "skill_version": "0.1.0",
        "mode": SYNTHETIC_TEST_MODE,
        "timestamp": ts,
        "total_comments": len(triage_items),
        "triage": [item.to_dict() for item in triage_items],
    }
    (artifact_dir / "comment-triage-report.json").write_text(
        json.dumps(triage_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4b. validation-report.json
    (artifact_dir / "validation-report.json").write_text(
        json.dumps({
            "skill": "comment-moderation",
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
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    paths = {
        name: artifact_dir / name
        for name in (
            "comment-triage-report.json",
            "validation-report.json",
            "fixture-payload.json",
        )
    }

    return SyntheticRunResult(
        valid=True,
        validation=result,
        triage_count=len(triage_items),
        mcp_calls=mcp_calls,
        artifact_paths=paths,
    )
