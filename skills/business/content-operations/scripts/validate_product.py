"""Command-line validator for one versioned Product JSON payload."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.contracts import PayloadValidationError, validate_payload_file
from scripts.product_payload import parse_product_payload


def build_parser() -> argparse.ArgumentParser:
    """Build the Product payload validation command-line parser."""
    parser = argparse.ArgumentParser(
        description="Validate one Content Operations Product JSON payload."
    )
    parser.add_argument("payload", type=Path)
    parser.add_argument(
        "--report", type=Path, help="Validation report path (default: beside payload)."
    )
    return parser


def main() -> int:
    """Validate one Product payload and print the generated report path."""
    args = build_parser().parse_args()
    payload_path: Path = args.payload
    report_path: Path = args.report or payload_path.with_name("validation-report.json")
    try:
        validate_payload_file(payload_path, report_path, parse_fn=parse_product_payload)
    except PayloadValidationError as error:
        print(str(error), file=sys.stderr)
        print(report_path)
        return 1
    print(report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
