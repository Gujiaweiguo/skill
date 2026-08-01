r"""Production product-operations workflow.

Orchestrates the full product draft creation pipeline:
    1. Parse a product research pack (markdown PRD) into a structured payload
    2. Validate the payload (brand-guardrail + AI Vision MVP + field checks)
    3. Submit to MCP ``product_create`` (always ``status=draft``)
    4. Generate all 4 required artifacts

**Never** calls ``product_publish`` / ``product_unpublish`` / ``product_delete``.
All MCP writes are draft-only.

Usage (programmatic)::

    runner = ProductOpsRunner()
    result = runner.run(payload, mock_mcp, artifact_dir)

Usage (CLI, synthetic mode)::

    uv run python -m scripts.product_ops \\
        --fixture fixtures/synthetic-fixture.json \\
        --output /tmp/product-operations/runs/<slug>/
"""

from __future__ import annotations

import json
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from scripts.validate import SYNTHETIC_TEST_MODE, ValidationResult, validate_product_payload

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PRODUCT_CATEGORIES = frozenset({
    "ai_vision",
    "ai_customer_service",
    "data_analytics",
    "smart_device",
    "other",
})

DRAFT_STATUS = "draft"

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class PRDParseResult:
    """Result of parsing a PRD markdown document."""

    product_name: str = ""
    slug: str = ""
    category: str = ""
    short_description: str = ""
    description: str = ""
    vendor: str = ""
    capabilities: list[dict[str, str]] = field(default_factory=list)
    parse_warnings: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        """Convert to a product payload dict (without fixture/authorization flags)."""
        return {
            "product_name": self.product_name,
            "slug": self.slug,
            "category": self.category,
            "short_description": self.short_description,
            "description": self.description,
            "vendor": self.vendor,
            "capabilities": self.capabilities,
        }


@dataclass
class ProductOpsResult:
    """Result of a full product-operations pipeline run."""

    valid: bool
    validation: ValidationResult
    draft_id: str = ""
    draft_status: str = ""
    mcp_calls: list[str] = field(default_factory=list)
    artifact_paths: dict[str, Path] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "valid": self.valid,
            "draft_id": self.draft_id,
            "draft_status": self.draft_status,
            "mcp_calls": self.mcp_calls,
            "artifacts": {k: str(v) for k, v in self.artifact_paths.items()},
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Protocol for MCP server (production or mock)
# ---------------------------------------------------------------------------


class ProductMCProtocol(Protocol):
    """Minimal protocol the injected MCP server must satisfy."""

    def product_create(self, payload: dict[str, object]) -> dict[str, object]:
        """Create a draft product. Must return ``{"id": ..., "status": "draft"}``."""
        ...

    def product_get(self, product_id: str) -> dict[str, object] | None:
        """Get a product by ID."""
        ...

    def product_list(self) -> list[dict[str, object]]:
        """List all products."""
        ...

    def product_update(
        self, product_id: str, updates: dict[str, object],
    ) -> dict[str, object]:
        """Update a draft product."""
        ...

    def get_call_tools(self) -> list[str]:
        """Return ordered list of all tool names called."""
        ...

    def assert_no_forbidden_calls(self) -> None:
        """Assert no forbidden tool was ever called."""
        ...


# ---------------------------------------------------------------------------
# PRD Parser
# ---------------------------------------------------------------------------

# Heading patterns for PRD sections
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_SLUG_RE = re.compile(r"[^\w-]+", re.UNICODE)


def _slugify(text: str) -> str:
    r"""Convert text to a URL-friendly slug.

    Retains CJK characters and other Unicode letters so that
    non-ASCII product names get a readable slug.
    """
    slug = text.lower().strip()
    slug = _SLUG_RE.sub("-", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "untitled"


def _parse_capability_line(line: str) -> dict[str, str] | None:
    """Parse a single capability line from a PRD.

    Recognised formats:
        - ``- 通道拥堵检测 (mvp)``
        - ``- [MVP] 通道拥堵检测``
        - ``- 通道拥堵检测 [roadmap]``
        - ``- **通道拥堵检测** — MVP``
    """
    # Strip bullet / checkbox
    line = re.sub(r"^[-*]\s*(\[[ x]\]\s*)?", "", line.strip())
    if not line:
        return None

    # Try (mvp) or (roadmap) suffix
    status_match = re.search(r"\((mvp|roadmap)\)", line, re.IGNORECASE)
    if status_match:
        name = line[: status_match.start()].strip(" *—-")
        status = status_match.group(1).lower()
        return {"name": name, "status": status} if name else None

    # Try [MVP] or [roadmap] prefix
    bracket_match = re.match(r"\[(mvp|roadmap)\]\s*(.+)", line, re.IGNORECASE)
    if bracket_match:
        return {
            "name": bracket_match.group(2).strip(" *—-"),
            "status": bracket_match.group(1).lower(),
        }

    # Try suffix [roadmap] / [mvp]
    bracket_suffix = re.search(r"\[(mvp|roadmap)\]$", line, re.IGNORECASE)
    if bracket_suffix:
        name = line[: bracket_suffix.start()].strip(" *—-")
        return {
            "name": name,
            "status": bracket_suffix.group(1).lower(),
        } if name else None

    # Try **Name** — MVP
    bold_match = re.match(r"\*\*(.+?)\*\*\s*[—-]\s*(mvp|roadmap)", line, re.IGNORECASE)
    if bold_match:
        return {"name": bold_match.group(1).strip(), "status": bold_match.group(2).lower()}

    # Default: treat as roadmap
    name = line.strip(" *—-")
    return {"name": name, "status": "roadmap"} if name else None


def parse_prd(markdown_text: str) -> PRDParseResult:  # noqa: C901, PLR0912
    """Parse a product research pack markdown into a structured payload.

    Expected PRD structure::

        # Product Name

        - **slug**: ai-vision-system
        - **category**: ai_vision
        - **vendor**: TechCorp

        ## Short Description

        One-line summary.

        ## Description

        Full product description.

        ## Capabilities

        - 通道拥堵检测 (mvp)
        - 设备预测维护 (roadmap)

    Args:
        markdown_text: Raw PRD markdown content.

    Returns:
        PRDParseResult with all parsed fields.

    """
    result = PRDParseResult()

    # Extract main title (first H1)
    h1_match = re.search(r"^#\s+(.+)$", markdown_text, re.MULTILINE)
    if h1_match:
        result.product_name = h1_match.group(1).strip()
    else:
        result.parse_warnings.append("No H1 title found")

    # Extract metadata fields (bullet points with **key**: value)
    meta_pattern = re.compile(
        r"^[-*]\s*\*\*([^*]+)\*\*\s*[:：]\s*(.+)$",  # noqa: RUF001
        re.MULTILINE,
    )
    meta_map: dict[str, str] = {}
    for match in meta_pattern.finditer(markdown_text):
        key = match.group(1).strip().lower().replace(" ", "_")
        value = match.group(2).strip()
        meta_map[key] = value

    result.slug = meta_map.get("slug", "")
    if not result.slug and result.product_name:
        result.slug = _slugify(result.product_name)
        result.parse_warnings.append("slug auto-generated from product name")

    result.category = meta_map.get("category", "")
    result.vendor = meta_map.get("vendor", "")

    # Extract sections by heading
    sections: dict[str, str] = {}
    heading_positions: list[tuple[int, str, str]] = []
    for match in _HEADING_RE.finditer(markdown_text):
        level = len(match.group(1))
        title = match.group(2).strip().lower()
        heading_positions.append((match.start(), title, f"{'#' * level} {match.group(2)}"))

    for i, (pos, title, _full) in enumerate(heading_positions):
        nl_pos = markdown_text.find("\n", pos)
        body_start = nl_pos + 1 if nl_pos != -1 else len(markdown_text)
        if i + 1 < len(heading_positions):
            body_end = heading_positions[i + 1][0]
        else:
            body_end = len(markdown_text)
        sections[title] = markdown_text[body_start:body_end].strip()

    # Short description
    for key in ("short description", "short_description", "summary"):
        if key in sections:
            result.short_description = sections[key].strip()
            break

    # Full description
    for key in ("description", "overview", "product description"):
        if key in sections:
            result.description = sections[key].strip()
            break

    # Capabilities
    for key in ("capabilities", "capability", "features"):
        if key in sections:
            for line in sections[key].splitlines():
                cap = _parse_capability_line(line)
                if cap:
                    result.capabilities.append(cap)
            break

    # Validate category
    if result.category and result.category not in VALID_PRODUCT_CATEGORIES:
        result.parse_warnings.append(
            f"category '{result.category}' is not in valid set: "
            f"{sorted(VALID_PRODUCT_CATEGORIES)}",
        )

    return result


# ---------------------------------------------------------------------------
# Artifact directory safety
# ---------------------------------------------------------------------------


class ArtifactDirError(Exception):
    """Raised when artifact_dir is outside the system temp directory."""


def _assert_temp_dir(artifact_dir: Path) -> None:
    """Fail-closed if artifact_dir resolves outside the system temp dir."""
    tmp_root = Path(tempfile.gettempdir()).resolve()
    resolved = artifact_dir.resolve()
    if tmp_root not in resolved.parents and resolved != tmp_root:
        msg = f"artifact_dir must resolve inside {tmp_root}, got {resolved}"
        raise ArtifactDirError(msg)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


class ProductOpsRunner:
    """Orchestrates the product-operations workflow.

    Validates payloads, creates drafts via MCP (never publishes),
    and generates required artifacts.
    """

    def __init__(self) -> None:
        """Initialise the runner."""

    # ------------------------------------------------------------------
    # PRD → draft pipeline
    # ------------------------------------------------------------------

    def run(
        self,
        payload: dict[str, object],
        mcp: ProductMCProtocol,
        artifact_dir: Path,
        *,
        execution_mode: str = SYNTHETIC_TEST_MODE,
    ) -> ProductOpsResult:
        """Run the full product-operations pipeline.

        Args:
            payload: Product payload dict.
            mcp: Injected MCP server (production or mock).
            artifact_dir: Temp directory for artifact output.
                Must resolve inside ``tempfile.gettempdir()``.
            execution_mode: Caller-provided context. Must be
                ``synthetic-test`` for fixture mode.

        Returns:
            ProductOpsResult with draft info and artifact paths.

        Raises:
            ArtifactDirError: If ``artifact_dir`` is outside temp dir.

        """
        _assert_temp_dir(artifact_dir)
        ts = time.time()

        # 1. Validate
        result = validate_product_payload(payload, execution_mode=execution_mode)
        if not result.valid:
            return ProductOpsResult(
                valid=False,
                validation=result,
                errors=[e["message"] for e in result.errors],
            )

        # 2. Create draft via MCP (the only write call)
        cms_fields = self._build_cms_fields(payload)
        cms_fields["status"] = DRAFT_STATUS
        draft = mcp.product_create(payload=cms_fields)
        mcp.assert_no_forbidden_calls()
        mcp_calls = mcp.get_call_tools()

        draft_id = str(draft.get("id", ""))
        draft_status = str(draft.get("status", DRAFT_STATUS))

        # 3. Verify draft status is draft (never published)
        if draft_status != DRAFT_STATUS:
            return ProductOpsResult(
                valid=False,
                validation=result,
                draft_id=draft_id,
                draft_status=draft_status,
                mcp_calls=mcp_calls,
                errors=[f"MCP returned status='{draft_status}', expected 'draft'"],
            )

        # 4. Generate artifacts
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_paths = self._write_artifacts(
            artifact_dir, payload, result, draft_id, draft_status, mcp_calls, ts,
        )

        return ProductOpsResult(
            valid=True,
            validation=result,
            draft_id=draft_id,
            draft_status=draft_status,
            mcp_calls=mcp_calls,
            artifact_paths=artifact_paths,
        )

    # ------------------------------------------------------------------
    # Draft update (for existing drafts only)
    # ------------------------------------------------------------------

    def update_draft(
        self,
        product_id: str,
        updates: dict[str, object],
        mcp: ProductMCProtocol,
    ) -> dict[str, object]:
        """Update an existing draft product.

        Raises if the product is not in draft status.
        """
        existing = mcp.product_get(product_id)
        if existing is None:
            msg = f"product not found: {product_id}"
            raise ValueError(msg)
        if existing.get("status") != DRAFT_STATUS:
            msg = f"cannot update non-draft product: {product_id} (status={existing.get('status')})"
            raise ValueError(msg)

        # Validate the updated fields if they contain known validation keys
        merged: dict[str, object] = {**existing, **updates}
        validation = validate_product_payload(merged, execution_mode=SYNTHETIC_TEST_MODE)
        if not validation.valid:
            msg = f"validation failed for update: {[e['message'] for e in validation.errors]}"
            raise ValueError(msg)

        return mcp.product_update(product_id, updates)

    # ------------------------------------------------------------------
    # List products (read-only)
    # ------------------------------------------------------------------

    def list_products(self, mcp: ProductMCProtocol) -> list[dict[str, object]]:
        """List all products from the MCP server (read-only)."""
        products = mcp.product_list()
        mcp.assert_no_forbidden_calls()
        return products

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_cms_fields(payload: dict[str, object]) -> dict[str, object]:
        """Strip runner-internal keys from the payload for CMS submission."""
        skip_keys = frozenset({"fixture", "execution_mode", "client_authorized"})
        return {k: v for k, v in payload.items() if k not in skip_keys}

    @staticmethod
    def _write_artifacts(  # noqa: PLR0913, PLR0917
        artifact_dir: Path,
        payload: dict[str, object],
        validation: ValidationResult,
        draft_id: str,
        draft_status: str,
        mcp_calls: list[str],
        ts: float,
    ) -> dict[str, Path]:
        """Generate and write all 4 required artifacts."""
        artifact_dir.mkdir(parents=True, exist_ok=True)

        product_name = str(payload.get("product_name", ""))
        description = str(payload.get("description", ""))
        vendor = str(payload.get("vendor", ""))
        slug = str(payload.get("slug", ""))

        # 4a. product-research-pack.md
        research_text = (
            f"# Product Research Pack — {product_name}\n\n"
            f"> **Slug**: {slug}\n\n"
            f"> **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}\n\n"
            f"## Vendor\n{vendor}\n\n"
            f"## Description\n{description}\n"
        )
        (artifact_dir / "product-research-pack.md").write_text(research_text, encoding="utf-8")

        # 4b. product-payload.json
        (artifact_dir / "product-payload.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # 4c. validation-report.json
        (artifact_dir / "validation-report.json").write_text(
            json.dumps(
                {
                    "skill": "product-operations",
                    "skill_version": "0.2.0",
                    "mode": SYNTHETIC_TEST_MODE,
                    "timestamp": ts,
                    **validation.to_dict(),
                    "mcp_calls": mcp_calls,
                    "forbidden_calls_detected": False,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # 4d. import-receipt.json
        (artifact_dir / "import-receipt.json").write_text(
            json.dumps(
                {
                    "skill": "product-operations",
                    "fixture": payload.get("fixture", False),
                    "mcp_tool": "product_create",
                    "draft_id": draft_id,
                    "draft_status": draft_status,
                    "timestamp": ts,
                    "mcp_calls": mcp_calls,
                    "forbidden_calls": [],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return {
            name: artifact_dir / name
            for name in (
                "product-research-pack.md",
                "product-payload.json",
                "validation-report.json",
                "import-receipt.json",
            )
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _cli() -> None:
    """CLI entry point for fixture-based product-operations runs."""
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        description="Product operations runner (draft-only, never publishes)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        required=True,
        help="Path to a fixture JSON file with a product payload",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/product-operations/runs/latest"),  # noqa: S108
        help="Output directory for artifacts (default: /tmp/product-operations/runs/latest)",
    )
    parser.add_argument(
        "--prd",
        type=Path,
        help="Path to a PRD markdown file to parse (alternative to fixture)",
    )
    args = parser.parse_args()

    # Build payload from fixture or PRD
    if args.prd:
        prd_text = args.prd.read_text(encoding="utf-8")
        parsed = parse_prd(prd_text)
        payload: dict[str, object] = parsed.to_payload()
        payload["fixture"] = True
        payload["client_authorized"] = True
        if parsed.parse_warnings:
            print("PRD parse warnings:")
            for w in parsed.parse_warnings:
                print(f"  - {w}")
    else:
        payload = dict(json.loads(args.fixture.read_text(encoding="utf-8")))

    # Use mock MCP server in CLI/synthetic mode
    from tests.mock_mcp_server import MockMCPServer  # noqa: PLC0415

    mock = MockMCPServer()
    runner = ProductOpsRunner()

    try:
        result = runner.run(payload, mock, args.output)
    except ArtifactDirError as exc:
        print(f"Error: {exc}")
        raise SystemExit(1) from exc

    if result.valid:
        print(f"Draft created: id={result.draft_id}, status={result.draft_status}")
        print(f"MCP calls: {', '.join(result.mcp_calls)}")
        print(f"Artifacts written to: {args.output}")
        for name in result.artifact_paths:
            print(f"  - {name}")
    else:
        print("Validation failed:")
        for err in result.errors:
            print(f"  - {err}")
        raise SystemExit(1)


if __name__ == "__main__":
    _cli()
