"""Write an audited receipt after MCP maintenance_revision_create."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from scripts.contracts import (
    CONTRACT_VERSION,
    PayloadValidationError,
    payload_sha256,
    write_json,
)
from scripts.maintenance_payload import parse_maintenance_payload

if TYPE_CHECKING:
    from scripts.article_payload import JsonValue

PENDING_REVIEW: Final = "pending-review"


class ReceiptStatusError(Exception):
    """Raised when an MCP create result is not a pending-review revision."""

    status: str

    def __init__(self, status: str) -> None:
        """Retain the rejected MCP status for boundary reporting."""
        self.status = status
        super().__init__(
            f"maintenance revision status must be pending-review, got {status!r}",
        )


class ReceiptDigestError(Exception):
    """Raised when the MCP-returned base_digest does not match the payload."""


def write_maintenance_receipt(
    payload_path: Path,
    receipt_path: Path,
    revision_id: str,
    cms_status: str,
    cms_base_digest: str,
    filtered_fields: list[str],
) -> dict[str, JsonValue]:
    """Validate the payload and record one confirmed pending-review result."""
    payload = parse_maintenance_payload(payload_path.read_bytes())
    if cms_status != PENDING_REVIEW:
        raise ReceiptStatusError(cms_status)
    if cms_base_digest != payload.base_digest:
        raise ReceiptDigestError(
            "returned base_digest does not match the payload base_digest",
        )
    digest = payload_sha256(payload_path)
    filtered: list[JsonValue] = [*filtered_fields]
    receipt: dict[str, JsonValue] = {
        "contract_version": CONTRACT_VERSION,
        "entity_type": payload.entity_type.value,
        "entity_id": payload.entity_id,
        "revision_id": revision_id,
        "payload_sha256": digest,
        "base_digest": payload.base_digest,
        "filtered_fields": filtered,
        "status": PENDING_REVIEW,
    }
    write_json(receipt_path, receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    """Build the maintenance receipt command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Write a receipt for one MCP-created pending-review maintenance revision."
        ),
    )
    parser.add_argument("payload", type=Path)
    parser.add_argument("--revision-id", required=True)
    parser.add_argument("--cms-status", required=True)
    parser.add_argument("--base-digest", required=True)
    parser.add_argument(
        "--filtered-fields",
        default="[]",
        help="JSON array of server-filtered fields returned by MCP (default: []).",
    )
    parser.add_argument("--receipt", type=Path)
    return parser


def main() -> int:
    """Validate CLI inputs and write one maintenance create receipt."""
    args = build_parser().parse_args()
    receipt_path: Path = (
        args.receipt or args.payload.with_name("create-receipt.json")
    )
    try:
        loaded = json.loads(args.filtered_fields)
    except json.JSONDecodeError as error:
        print(f"invalid --filtered-fields: {error}", file=sys.stderr)
        return 1
    if not isinstance(loaded, list) or not all(
        isinstance(item, str) for item in loaded  # pyright: ignore[reportUnknownVariableType]
    ):
        print("filtered fields must be a JSON array of strings", file=sys.stderr)
        return 1
    filtered_fields = cast("list[str]", loaded)
    try:
        write_maintenance_receipt(
            payload_path=args.payload,
            receipt_path=receipt_path,
            revision_id=args.revision_id,
            cms_status=args.cms_status,
            cms_base_digest=args.base_digest,
            filtered_fields=filtered_fields,
        )
    except (
        PayloadValidationError,
        ReceiptStatusError,
        ReceiptDigestError,
        OSError,
    ) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(receipt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
