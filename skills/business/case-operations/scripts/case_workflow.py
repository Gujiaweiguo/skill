r"""Case workflow CLI - orchestrates the case draft creation pipeline.

Four phases:
    1. Screen — fetch published cases and score them (optional)
    2. Validate — run deterministic validation on a case payload
    3. Generate — produce all 4 required artifacts from a payload
    4. Import — call MCP ``case_create`` to create a CMS draft

Synthetic test mode uses the bundled fixture.  Production mode requires
a live MCP server at ``http://127.0.0.1:5580/mcp``.

Usage (synthetic)::

    uv run python -m scripts.case_workflow validate \\
        --payload fixtures/synthetic-fixture.json

    uv run python -m scripts.case_workflow generate \\
        --payload fixtures/synthetic-fixture.json \\
        --output-dir /tmp/case-ops-run

Usage (screening)::

    uv run python -m scripts.case_workflow screen \\
        --output /tmp/case-screening-report.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from scripts.case_screening import CASES_API_URL, CaseScreener, HttpResponseError
from scripts.synthetic_runner import run_synthetic_fixture
from scripts.validate import SYNTHETIC_TEST_MODE, validate_case_payload
from tests.mock_mcp_server import MockMCPServer

DEFAULT_CASE_OUTPUT_BASE = Path("/opt/code/docs/lanlnk/lnkwebsite/content/cases")


# ---------------------------------------------------------------------------
# Phase commands
# ---------------------------------------------------------------------------


def _cmd_screen(args: argparse.Namespace) -> int:
    """Screen published cases from the website API."""
    screener = CaseScreener()
    try:
        report = screener.screen(api_url=args.api_url)
    except HttpResponseError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    report.top_candidates = report.all_scores[: args.top]
    screener.write_report(report, args.output)

    print(f"Screening complete: {report.published_cases} published cases")
    print(f"Report written to: {args.output}")

    if report.top_candidates:
        print(f"\nTop {len(report.top_candidates)} candidates:")
        for i, c in enumerate(report.top_candidates, 1):
            print(
                f"  {i}. {c['client_name']} ({c['slug']}) "
                f"— score: {c['combined_score']}"
            )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """Validate a single case payload JSON."""
    payload = json.loads(args.payload.read_text(encoding="utf-8"))

    execution_mode = SYNTHETIC_TEST_MODE if payload.get("fixture") else None

    result = validate_case_payload(payload, execution_mode=execution_mode)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(
                {
                    "skill": "case-operations",
                    "skill_version": "0.1.0",
                    "timestamp": time.time(),
                    **result.to_dict(),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"Report written to: {args.report}")

    if result.valid:
        print("VALID — payload passes all checks")
        return 0
    print("INVALID — payload has errors:", file=sys.stderr)
    for err in result.errors:
        print(f"  [{err['code']}] {err['field']}: {err['message']}", file=sys.stderr)
    return 1


def _cmd_generate(args: argparse.Namespace) -> int:
    """Generate all 4 required artifacts from a fixture payload."""
    payload = json.loads(args.payload.read_text(encoding="utf-8"))

    if not payload.get("fixture"):
        print("ERROR: --payload must be a fixture (fixture=true) for generate", file=sys.stderr)
        return 1

    output_dir = args.output_dir or Path(tempfile.mkdtemp(prefix="case-ops-"))
    mock = MockMCPServer()
    result = run_synthetic_fixture(payload, mock, output_dir)

    if result.valid:
        print(f"Generated 4 artifacts in: {output_dir}")
        for name, path in result.artifact_paths.items():
            print(f"  {name} → {path}")
        print(f"Draft ID: {result.draft_id} (status={result.draft_status})")
        return 0
    print("Generation failed — validation errors:", file=sys.stderr)
    for err in result.validation.errors:
        print(f"  [{err['code']}] {err['field']}: {err['message']}", file=sys.stderr)
    return 1


def _cmd_import(args: argparse.Namespace) -> int:
    """Import a validated case payload as a CMS draft via MCP.

    Production mode: requires live MCP server.
    For testing: use ``--mock`` to use the in-process mock MCP.
    """
    payload = json.loads(args.payload.read_text(encoding="utf-8"))

    execution_mode = SYNTHETIC_TEST_MODE if payload.get("fixture") else None
    result = validate_case_payload(payload, execution_mode=execution_mode)

    if not result.valid:
        print("Payload validation failed — cannot import:", file=sys.stderr)
        for err in result.errors:
            print(f"  [{err['code']}] {err['field']}: {err['message']}", file=sys.stderr)
        return 1

    if args.mock:
        # Use in-process mock MCP (for testing)
        mock = MockMCPServer()
        cms_fields = {
            k: v for k, v in payload.items()
            if k not in ("fixture", "execution_mode")
        }
        cms_fields["status"] = "draft"
        draft = mock.case_create(payload=cms_fields)
        draft_id = draft["id"]
        draft_status = draft["status"]
        print(f"[MOCK] Created case draft: id={draft_id}, status={draft_status}")
    else:
        # Production: agent calls MCP directly
        print(
            "Production MCP import: agent should call MCP case_create "
            "directly with validated payload fields. "
            "This CLI does not implement MCP transport.",
        )
        print(
            "Use --mock for in-process testing, or call MCP case_create "
            "from the agent context.",
        )
        return 0

    # Write receipt
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(
                {
                    "skill": "case-operations",
                    "fixture": payload.get("fixture", False),
                    "mcp_tool": "case_create",
                    "draft_id": draft_id,
                    "draft_status": draft_status,
                    "timestamp": time.time(),
                    "mcp_calls": ["case_create"],
                    "forbidden_calls": [],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"Receipt written to: {args.receipt}")

    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the case-workflow CLI parser."""
    parser = argparse.ArgumentParser(
        description="Case operations workflow (validate / generate / screen / import)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # screen
    p_screen = sub.add_parser("screen", help="Screen published cases from the API")
    p_screen.add_argument("--api-url", default=CASES_API_URL)
    p_screen.add_argument(
        "--output", type=Path,
        default=Path("/tmp/case-screening-report.json"),  # noqa: S108
    )
    p_screen.add_argument("--top", type=int, default=3)

    # validate
    p_validate = sub.add_parser("validate", help="Validate a case payload JSON")
    p_validate.add_argument("payload", type=Path)
    p_validate.add_argument("--report", type=Path, help="Write validation report to this path")

    # generate
    p_generate = sub.add_parser("generate", help="Generate all 4 artifacts from a fixture")
    p_generate.add_argument("payload", type=Path)
    p_generate.add_argument("--output-dir", type=Path, help="Output directory (default: temp dir)")

    # import
    p_import = sub.add_parser("import", help="Import validated payload as CMS draft")
    p_import.add_argument("payload", type=Path)
    p_import.add_argument("--receipt", type=Path, help="Write import receipt to this path")
    p_import.add_argument("--mock", action="store_true", help="Use in-process mock MCP")

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point.

    Args:
        argv: Optional argument list (for testing). If None, uses sys.argv.

    """
    args = build_parser().parse_args(argv)

    handlers = {
        "screen": _cmd_screen,
        "validate": _cmd_validate,
        "generate": _cmd_generate,
        "import": _cmd_import,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
