"""Command-line triage runner for comment-moderation.

Reads pending comments from MCP (or a local JSON fixture for testing),
runs risk classification, and writes the triage report.

Usage (MCP mode)::

    uv run python -m scripts.triage \
        --output /tmp/comment-triage/<date>.json

Usage (fixture mode, for testing)::

    uv run python -m scripts.triage \
        --fixture fixtures/synthetic-fixture.json \
        --output /tmp/comment-triage/<date>.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from scripts.risk_engine import TriageItem, assess_batch


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Run comment moderation triage on pending comments.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output path for the triage report JSON.",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=None,
        help=(
            "Local fixture JSON file with comments (for testing). "
            "If omitted, reads from MCP server."
        ),
    )
    parser.add_argument(
        "--mcp-url",
        type=str,
        default=None,
        help="MCP server URL (default: http://127.0.0.1:5580/mcp).",
    )
    parser.add_argument(
        "--article-id-filter",
        type=int,
        default=None,
        help="Only triage comments for this article ID.",
    )
    return parser


def _load_from_fixture(
    fixture_path: Path,
) -> list[dict[str, object]]:
    """Load comments from a local fixture file.

    Handles both single-comment fixtures and list fixtures.
    """
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return [data]


def _load_from_mcp(
    mcp_url: str | None,
) -> list[dict[str, object]]:
    """Load pending comments from MCP server."""
    from scripts.mcp_reader import MCPCommentReader

    reader = MCPCommentReader(server_url=mcp_url)
    return reader.list_pending()


def _filter_by_article(
    comments: list[dict[str, object]],
    article_id: int | None,
) -> list[dict[str, object]]:
    """Filter comments by article_id if specified."""
    if article_id is None:
        return comments
    return [
        c for c in comments
        if c.get("article_id") == article_id
        or c.get("article_id") == str(article_id)
    ]


def build_report(
    items: list[TriageItem],
    source: str,
    article_filter: int | None,
) -> dict[str, object]:
    """Build the triage report dict."""
    risk_counts = {"low": 0, "medium": 0, "high": 0}
    suggestion_counts = {"approve": 0, "review": 0, "reject": 0}
    for item in items:
        risk_counts[item.risk_level] += 1
        suggestion_counts[item.moderation_suggestion] += 1

    return {
        "skill": "comment-moderation",
        "skill_version": "0.2.0",
        "source": source,
        "article_id_filter": article_filter,
        "timestamp": time.time(),
        "total_comments": len(items),
        "risk_summary": risk_counts,
        "suggestion_summary": suggestion_counts,
        "auto_actions_taken": [],
        "human_review_required": True,
        "triage": [item.to_dict() for item in items],
    }


def main(argv: list[str] | None = None) -> int:
    """Run the triage pipeline and write the report.

    Args:
        argv: Optional argument list. If None, reads from sys.argv.

    Returns:
        Exit code (0 = success, 2 = MCP connection failure).
    """
    args = build_parser().parse_args(argv)

    # Load comments
    if args.fixture is not None:
        comments = _load_from_fixture(args.fixture)
        source = f"fixture:{args.fixture.name}"
    else:
        try:
            comments = _load_from_mcp(args.mcp_url)
            source = "mcp:comment_list_pending"
        except Exception as exc:
            print(f"ERROR: MCP connection failed: {exc}", file=sys.stderr)
            return 2

    # Filter by article if requested
    comments = _filter_by_article(comments, args.article_id_filter)

    # Assess risk for each comment
    items = assess_batch(comments)

    # Build report
    report = build_report(items, source, args.article_id_filter)

    # Write report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Print summary
    print(
        f"Triage complete: {len(items)} comments → "
        f"low={report['risk_summary']['low']}, "  # type: ignore[index]
        f"medium={report['risk_summary']['medium']}, "  # type: ignore[index]
        f"high={report['risk_summary']['high']}",  # type: ignore[index]
    )
    print(f"Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
