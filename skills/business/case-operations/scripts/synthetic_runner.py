"""Reusable synthetic-test runner for case-operations.

Receives a fixture payload, an injected mock MCP server, and a temp artifact
directory. Validates the payload, calls mock case_create, and generates the
4 required artifacts.

Security:
- Only operates in synthetic-test mode (caller must pass execution_mode).
- Only calls case_create on the injected mock — never reaches real MCP.
- Writes artifacts only to the provided temp directory.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

# --------------------------------------------------------------------------- #
# Path setup — make validate.py importable                                    #
# --------------------------------------------------------------------------- #
_SCRIPTS_DIR = Path(__file__).resolve().parent
import sys
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from validate import validate_case_payload, SYNTHETIC_TEST_MODE, ValidationResult  # noqa: E402


# --------------------------------------------------------------------------- #
# Protocol for the injected mock MCP — no real HTTP / token here.              #
# --------------------------------------------------------------------------- #

class MockMCPProtocol(Protocol):
    def case_create(self, payload: dict[str, Any]) -> dict[str, Any]: ...
    def get_call_tools(self) -> list[str]: ...
    def assert_no_forbidden_calls(self) -> None: ...


# --------------------------------------------------------------------------- #
# Result                                                                       #
# --------------------------------------------------------------------------- #

@dataclass
class SyntheticRunResult:
    valid: bool
    validation: ValidationResult
    draft_id: str
    draft_status: str
    mcp_calls: list[str]
    artifact_paths: dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "draft_id": self.draft_id,
            "draft_status": self.draft_status,
            "mcp_calls": self.mcp_calls,
            "artifacts": {k: str(v) for k, v in self.artifact_paths.items()},
        }


# --------------------------------------------------------------------------- #
# Public runner                                                                #
# --------------------------------------------------------------------------- #

def run_synthetic_fixture(
    payload: dict[str, Any],
    mock_mcp: MockMCPProtocol,
    artifact_dir: Path,
) -> SyntheticRunResult:
    """Run the synthetic fixture pipeline.

    Args:
        payload: Fixture payload (must contain ``fixture: true``).
        mock_mcp: Injected mock MCP server (test double).
        artifact_dir: Temp directory for artifact output.

    Returns:
        SyntheticRunResult with all paths and metadata.
    """
    ts = time.time()

    # 1. Validate — caller-provided execution_mode, never from payload
    result = validate_case_payload(
        payload, execution_mode=SYNTHETIC_TEST_MODE,
    )
    if not result.valid:
        return SyntheticRunResult(
            valid=False,
            validation=result,
            draft_id="",
            draft_status="",
            mcp_calls=[],
        )

    # 2. Mock MCP case_create (the only MCP call)
    cms_fields = {
        k: v for k, v in payload.items()
        if k not in ("fixture", "execution_mode")
    }
    cms_fields["status"] = "draft"
    draft = mock_mcp.case_create(payload=cms_fields)
    mcp_calls = mock_mcp.get_call_tools()

    # 3. Verify no forbidden calls
    mock_mcp.assert_no_forbidden_calls()

    # 4. Generate 4 artifacts
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # 4a. case-research-pack.md
    (artifact_dir / "case-research-pack.md").write_text(
        f"# Case Research Pack — {payload['client_name']}\n\n"
        "> **FIXTURE**: Synthetic test data. No real client.\n\n"
        f"## Problem\n{payload['problem']}\n\n"
        f"## Solution\n{payload['solution']}\n\n"
        f"## Outcome\n{payload['outcome']}\n",
        encoding="utf-8",
    )

    # 4b. case-payload.json
    (artifact_dir / "case-payload.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4c. validation-report.json
    (artifact_dir / "validation-report.json").write_text(
        json.dumps({
            "skill": "case-operations",
            "skill_version": "0.1.0",
            "mode": SYNTHETIC_TEST_MODE,
            "timestamp": ts,
            **result.to_dict(),
            "mcp_calls": mcp_calls,
            "forbidden_calls_detected": False,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4d. import-receipt.json
    (artifact_dir / "import-receipt.json").write_text(
        json.dumps({
            "skill": "case-operations",
            "fixture": True,
            "mcp_tool": "case_create",
            "draft_id": draft["id"],
            "draft_status": draft["status"],
            "timestamp": ts,
            "mcp_calls": mcp_calls,
            "forbidden_calls": [],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    paths = {
        name: artifact_dir / name
        for name in (
            "case-research-pack.md",
            "case-payload.json",
            "validation-report.json",
            "import-receipt.json",
        )
    }

    return SyntheticRunResult(
        valid=True,
        validation=result,
        draft_id=draft["id"],
        draft_status=draft["status"],
        mcp_calls=mcp_calls,
        artifact_paths=paths,
    )
