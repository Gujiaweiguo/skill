"""Verify an applied maintenance revision and write the evidence artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

from scripts.contracts import CONTRACT_VERSION, write_json

if TYPE_CHECKING:
    from scripts.article_payload import JsonValue

APPLIED: Final = "applied"


class PostApplyVerificationError(Exception):
    """Raised when a revision does not evidence a completed apply."""


def _read_json_object(path: Path, artifact: str) -> dict[str, JsonValue]:
    try:
        raw: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise PostApplyVerificationError(f"{artifact}: {error}") from error
    if not isinstance(raw, dict):
        raise PostApplyVerificationError(f"{artifact}: must be a JSON object")
    return raw


def verify_post_apply(
    revision: dict[str, JsonValue],
    receipt: dict[str, JsonValue],
) -> tuple[str, str]:
    """Assert applied status, snapshot, and receipt linkage.

    Returns the (revision_id, post_snapshot_id) pair on success.
    """
    if revision.get("status") != APPLIED:
        raise PostApplyVerificationError(
            f"revision status must be applied, got {revision.get('status')!r}",
        )
    post_snapshot_id = revision.get("post_snapshot_id")
    if not isinstance(post_snapshot_id, str) or not post_snapshot_id.strip():
        raise PostApplyVerificationError(
            "revision post_snapshot_id must be a non-empty string",
        )
    revision_id = revision.get("id")
    if not isinstance(revision_id, str) or not revision_id.strip():
        raise PostApplyVerificationError("revision id must be a non-empty string")
    if receipt.get("revision_id") != revision_id:
        raise PostApplyVerificationError(
            "receipt does not reference this revision",
        )
    return revision_id, post_snapshot_id


def write_post_apply_verification(
    revision_path: Path,
    receipt_path: Path,
    output_path: Path,
) -> dict[str, JsonValue]:
    """Verify one maintenance_revision_get result and write the artifact."""
    revision = _read_json_object(revision_path, "revision get result")
    receipt = _read_json_object(receipt_path, "create receipt")
    revision_id, post_snapshot_id = verify_post_apply(revision, receipt)
    artifact: dict[str, JsonValue] = {
        "contract_version": CONTRACT_VERSION,
        "revision_id": revision_id,
        "status": APPLIED,
        "post_snapshot_id": post_snapshot_id,
        "receipt": str(receipt_path.resolve()),
        "verified": True,
    }
    write_json(output_path, artifact)
    return artifact


def build_parser() -> argparse.ArgumentParser:
    """Build the post-apply verification command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Verify one applied maintenance revision via its read-only get result."
        ),
    )
    parser.add_argument(
        "--revision",
        type=Path,
        required=True,
        help="JSON result of MCP maintenance_revision_get, saved by the agent.",
    )
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    """Verify an applied revision and print the artifact path."""
    args = build_parser().parse_args()
    try:
        write_post_apply_verification(
            revision_path=args.revision,
            receipt_path=args.receipt,
            output_path=args.output,
        )
    except (PostApplyVerificationError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
