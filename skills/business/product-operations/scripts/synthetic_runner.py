"""Reusable synthetic-test runner for product-operations.

Receives a fixture payload, an injected mock MCP server, and a temp
artifact directory.  Validates the payload, calls mock
``product_create``, and generates the 4 required artifacts.

Security:
- Only operates in synthetic-test mode (caller must pass
  ``execution_mode``).
- Only calls ``product_create`` on the injected mock -- never reaches
  real MCP.
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

from scripts.validate import SYNTHETIC_TEST_MODE, ValidationResult, validate_product_payload


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

    def product_create(
        self, payload: dict[str, object],
    ) -> dict[str, object]:
        """Create a draft product in the mock CMS."""
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
    draft_id: str
    draft_status: str
    mcp_calls: list[str]
    artifact_paths: dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "valid": self.valid,
            "draft_id": self.draft_id,
            "draft_status": self.draft_status,
            "mcp_calls": self.mcp_calls,
            "artifacts": {k: str(v) for k, v in self.artifact_paths.items()},
        }


def _build_cms_fields(payload: dict[str, object]) -> dict[str, object]:
    """Strip runner-internal keys from the payload for CMS submission."""
    skip_keys = frozenset({"fixture", "execution_mode"})
    return {k: v for k, v in payload.items() if k not in skip_keys}


@dataclass(frozen=True)
class _ArtifactContext:
    """Bundle for artifact generation inputs."""

    artifact_dir: Path
    payload: dict[str, object]
    validation: ValidationResult
    draft_id: str
    draft_status: str
    mcp_calls: list[str]
    ts: float


def _write_artifacts(ctx: _ArtifactContext) -> dict[str, Path]:
    """Generate and write all 4 required artifacts."""
    ctx.artifact_dir.mkdir(parents=True, exist_ok=True)

    product_name = str(ctx.payload.get("product_name", ""))
    description = str(ctx.payload.get("description", ""))
    vendor = str(ctx.payload.get("vendor", ""))

    # 4a. product-research-pack.md
    research_text = (
        f"# Product Research Pack -- {product_name}\n\n"
        "> **FIXTURE**: Synthetic test data. No real product.\n\n"
        f"## Vendor\n{vendor}\n\n"
        f"## Description\n{description}\n"
    )
    (ctx.artifact_dir / "product-research-pack.md").write_text(
        research_text, encoding="utf-8",
    )

    # 4b. product-payload.json
    (ctx.artifact_dir / "product-payload.json").write_text(
        json.dumps(ctx.payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4c. validation-report.json
    (ctx.artifact_dir / "validation-report.json").write_text(
        json.dumps({
            "skill": "product-operations",
            "skill_version": "0.1.0",
            "mode": SYNTHETIC_TEST_MODE,
            "timestamp": ctx.ts,
            **ctx.validation.to_dict(),
            "mcp_calls": ctx.mcp_calls,
            "forbidden_calls_detected": False,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4d. import-receipt.json
    (ctx.artifact_dir / "import-receipt.json").write_text(
        json.dumps({
            "skill": "product-operations",
            "fixture": True,
            "mcp_tool": "product_create",
            "draft_id": ctx.draft_id,
            "draft_status": ctx.draft_status,
            "timestamp": ctx.ts,
            "mcp_calls": ctx.mcp_calls,
            "forbidden_calls": [],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    artifact_names = (
        "product-research-pack.md",
        "product-payload.json",
        "validation-report.json",
        "import-receipt.json",
    )
    return {name: ctx.artifact_dir / name for name in artifact_names}


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
    result = validate_product_payload(
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

    # 2. Mock MCP product_create (the only MCP call)
    cms_fields = _build_cms_fields(payload)
    cms_fields["status"] = "draft"
    draft = mock_mcp.product_create(payload=cms_fields)
    mcp_calls = mock_mcp.get_call_tools()

    # 3. Verify no forbidden calls
    mock_mcp.assert_no_forbidden_calls()

    # 4. Generate artifacts
    draft_id = str(draft["id"])
    draft_status = str(draft["status"])
    ctx = _ArtifactContext(
        artifact_dir=artifact_dir,
        payload=payload,
        validation=result,
        draft_id=draft_id,
        draft_status=draft_status,
        mcp_calls=mcp_calls,
        ts=ts,
    )
    artifact_paths = _write_artifacts(ctx)

    return SyntheticRunResult(
        valid=True,
        validation=result,
        draft_id=draft_id,
        draft_status=draft_status,
        mcp_calls=mcp_calls,
        artifact_paths=artifact_paths,
    )
