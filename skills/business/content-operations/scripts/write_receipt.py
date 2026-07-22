"""Write an audited receipt after MCP draft creation."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Final

from scripts.contracts import (
    PayloadValidationError,
    parse_article_payload,
    payload_sha256,
    write_json,
)
from scripts.import_artifacts import (
    ImportArtifactError,
    ImportPaths,
    ImportReceipt,
    validate_import_artifacts,
)

DEFAULT_CONTENT_OUTPUT_BASE: Final = Path("/opt/code/docs/lanlnk/lnkwebsite/content")


class ReceiptStatusError(Exception):
    """Raised when an MCP result does not confirm draft creation."""

    status: str

    def __init__(self, status: str) -> None:
        """Retain the rejected MCP status for boundary reporting."""
        self.status = status
        super().__init__(f"cms status must be draft, got {status!r}")


def write_receipt(
    paths: ImportPaths,
    cms_article_id: int,
    cms_status: str,
) -> ImportReceipt:
    """Validate import artifacts and record one confirmed MCP draft result."""
    payload = parse_article_payload(paths.payload.read_bytes())
    digest = payload_sha256(paths.payload)
    validate_import_artifacts(paths, digest)
    if cms_status != "draft":
        raise ReceiptStatusError(cms_status)
    receipt = ImportReceipt(
        source_draft=str(paths.source_draft.resolve()),
        payload_sha256=digest,
        cms_article_id=str(cms_article_id),
        slug=payload.slug,
        category=payload.category,
        status="draft",
    )
    write_json(paths.receipt, receipt.as_json())
    return receipt


def build_parser() -> argparse.ArgumentParser:
    """Build the receipt command-line parser."""
    parser = argparse.ArgumentParser(
        description="Write a receipt for one MCP-created CMS draft.",
    )
    parser.add_argument("payload", type=Path)
    parser.add_argument("--cms-article-id", type=int, required=True)
    parser.add_argument("--cms-status", required=True)
    parser.add_argument("--source-draft", type=Path, required=True)
    parser.add_argument("--review-record", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--receipt", type=Path)
    return parser


def main() -> int:
    """Validate CLI inputs and write one MCP draft receipt."""
    args = build_parser().parse_args()
    base = Path(os.environ.get("CONTENT_OUTPUT_BASE", DEFAULT_CONTENT_OUTPUT_BASE))
    payload: Path = args.payload
    paths = ImportPaths(
        content_output_base=base,
        payload=payload,
        validation_report=args.validation_report or payload.with_name("validation-report.json"),
        source_draft=args.source_draft,
        review_record=args.review_record,
        receipt=args.receipt or payload.with_name("import-receipt.json"),
    )
    try:
        write_receipt(paths, args.cms_article_id, args.cms_status)
    except (ImportArtifactError, PayloadValidationError, ReceiptStatusError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(paths.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
