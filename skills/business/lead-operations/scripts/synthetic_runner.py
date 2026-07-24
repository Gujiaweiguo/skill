"""Synthetic-test runner for lead-operations.

Read-only triage: loads fixture leads, calls mock ``lead_list`` /
``lead_get``, generates a triage report artifact.

Security:
- Only operates in synthetic-test mode.
- Never calls write tools (lead_update, lead_status_change).
- Writes artifacts only inside system temp dir.
"""

from __future__ import annotations

import json
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from scripts.validate import SYNTHETIC_TEST_MODE, ValidationResult, validate_lead_payload


class ArtifactDirError(Exception):
    """Raised when artifact_dir is outside the system temp directory."""


def _assert_temp_dir(artifact_dir: Path) -> None:
    """Fail-closed if artifact_dir resolves outside temp dir."""
    tmp_root = Path(tempfile.gettempdir()).resolve()
    resolved = artifact_dir.resolve()
    if tmp_root not in resolved.parents and resolved != tmp_root:
        msg = f"artifact_dir must resolve inside {tmp_root}, got {resolved}"
        raise ArtifactDirError(msg)


class MockMCPProtocol(Protocol):
    """Minimal protocol the injected mock must satisfy."""

    def lead_list(self) -> list[dict[str, object]]:
        """List leads from mock."""
        ...

    def lead_get(self, lead_id: int) -> dict[str, object] | None:
        """Get a single lead from mock."""
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
    triage_entries: list[dict[str, object]]
    mcp_calls: list[str]
    artifact_paths: dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "valid": self.valid,
            "triage_entries": self.triage_entries,
            "mcp_calls": self.mcp_calls,
            "artifacts": {k: str(v) for k, v in self.artifact_paths.items()},
        }


def _classify_lead(lead: dict[str, object]) -> dict[str, object]:
    """Generate a triage suggestion for one lead."""
    message = str(lead.get("message", ""))
    source = str(lead.get("source", ""))

    if "AI" in message or "智能" in message:
        category = "high-priority-ai-solution"
    elif "物业" in message:
        category = "medium-priority-property-management"
    elif source == "referral":
        category = "medium-priority-referral"
    else:
        category = "standard"

    return {
        "lead_id": lead.get("id"),
        "category_suggestion": category,
        "follow_up_suggestion": "建议24h内联系(合成测试建议)",
        "risk_flags": [],
        "auto_actions_taken": [],
        "human_review_required": True,
    }


def run_synthetic_fixture(
    payload: dict[str, object],
    mock_mcp: MockMCPProtocol,
    artifact_dir: Path,
) -> SyntheticRunResult:
    """Run the synthetic fixture pipeline.

    Args:
        payload: Fixture payload (must contain ``fixture: true``).
        mock_mcp: Injected mock MCP server.
        artifact_dir: Temp directory for artifact output.

    Returns:
        SyntheticRunResult with paths and metadata.

    Raises:
        ArtifactDirError: If artifact_dir is outside temp dir.

    """
    _assert_temp_dir(artifact_dir)
    ts = time.time()

    result = validate_lead_payload(
        payload, execution_mode=SYNTHETIC_TEST_MODE,
    )
    if not result.valid:
        return SyntheticRunResult(
            valid=False, validation=result,
            triage_entries=[], mcp_calls=[],
        )

    leads = mock_mcp.lead_list()
    mcp_calls = mock_mcp.get_call_tools()

    triage_entries: list[dict[str, object]] = []
    for lead in leads:
        raw_id = lead.get("id", 0)
        if isinstance(raw_id, int):
            detail = mock_mcp.lead_get(raw_id)
            if detail is not None:
                triage_entries.append(_classify_lead(detail))

    mock_mcp.assert_no_forbidden_calls()

    artifact_dir.mkdir(parents=True, exist_ok=True)

    (artifact_dir / "lead-triage-report.json").write_text(
        json.dumps({
            "skill": "lead-operations",
            "skill_version": "0.1.0",
            "mode": SYNTHETIC_TEST_MODE,
            "timestamp": ts,
            "triage_entries": triage_entries,
            "auto_actions_taken": [],
            "human_review_required": True,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    (artifact_dir / "validation-report.json").write_text(
        json.dumps({
            "skill": "lead-operations",
            "mode": SYNTHETIC_TEST_MODE,
            "timestamp": ts,
            **result.to_dict(),
            "mcp_calls": mcp_calls,
            "forbidden_calls_detected": False,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    (artifact_dir / "fixture-payload.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    paths = {
        name: artifact_dir / name
        for name in (
            "lead-triage-report.json",
            "validation-report.json",
            "fixture-payload.json",
        )
    }

    return SyntheticRunResult(
        valid=True, validation=result,
        triage_entries=triage_entries,
        mcp_calls=mcp_calls, artifact_paths=paths,
    )
