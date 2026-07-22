"""CLI and orchestration for one validated, draft-only CMS import."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Final

from scripts.cms_client import ENDPOINT_ENV, TOKEN_ENV, CmsConfig, create_cms_draft
from scripts.contracts import (
    cms_create_fields,
    parse_article_payload,
    payload_sha256,
    write_json,
)
from scripts.import_artifacts import (
    ImportPaths,
    ImportReceipt,
    validate_import_artifacts,
)

DEFAULT_CONTENT_OUTPUT_BASE: Final = Path("/opt/code/docs/lanlnk/lnkwebsite/content")


def import_draft(paths: ImportPaths, config: CmsConfig) -> ImportReceipt:
    """Create one confirmed CMS draft from validated and approved artifacts."""
    payload = parse_article_payload(paths.payload.read_bytes())
    digest = payload_sha256(paths.payload)
    validate_import_artifacts(paths, digest)
    request_body = json.dumps(
        cms_create_fields(payload),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    article_id, status = create_cms_draft(config, request_body)
    receipt = ImportReceipt(
        source_draft=str(paths.source_draft.resolve()),
        payload_sha256=digest,
        cms_article_id=article_id,
        slug=payload.slug,
        category=payload.category,
        status=status,
    )
    write_json(paths.receipt, receipt.as_json())
    return receipt


def build_parser() -> argparse.ArgumentParser:
    """Build the draft import command-line parser."""
    parser = argparse.ArgumentParser(
        description="Create one CMS draft from validated Content Operations artifacts.",
    )
    parser.add_argument("payload", type=Path)
    parser.add_argument("--source-draft", type=Path, required=True)
    parser.add_argument("--review-record", type=Path, required=True)
    parser.add_argument("--validation-report", type=Path)
    parser.add_argument("--receipt", type=Path)
    return parser


def main() -> int:
    """Read runtime configuration and execute one draft import."""
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
    config = CmsConfig(
        endpoint=os.environ.get(ENDPOINT_ENV, ""),
        token=os.environ.get(TOKEN_ENV, ""),
    )
    import_draft(paths, config)
    print(paths.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
