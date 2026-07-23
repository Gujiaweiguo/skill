"""Compatibility exports plus deterministic payload digest and report I/O."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Final, TypeVar

from scripts.article_payload import (
    ArticleCategory,
    ArticlePayload,
    JsonValue,
    PayloadValidationError,
    ValidationIssue,
    parse_article_payload,
)

if TYPE_CHECKING:
    from pathlib import Path

CONTRACT_VERSION: Final = "1.0.0"

T = TypeVar("T")
PayloadParser = Callable[[bytes], T]

__all__ = [
    "CONTRACT_VERSION",
    "ArticleCategory",
    "ArticlePayload",
    "JsonValue",
    "PayloadParser",
    "PayloadValidationError",
    "ValidationIssue",
    "parse_article_payload",
    "payload_sha256",
    "validate_payload_file",
    "write_json",
]


def payload_sha256(path: Path) -> str:
    """Return the SHA-256 digest of the exact payload bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: JsonValue) -> None:
    """Atomically write deterministic UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(f"{encoded}\n", encoding="utf-8")
    temporary.replace(path)


def validate_payload_file(
    payload_path: Path,
    report_path: Path,
    parse_fn: PayloadParser[T] = parse_article_payload,
) -> T:
    """Validate one payload file and write its deterministic report."""
    digest = payload_sha256(payload_path)
    try:
        payload = parse_fn(payload_path.read_bytes())
    except PayloadValidationError as error:
        write_json(
            report_path,
            {
                "contract_version": CONTRACT_VERSION,
                "valid": False,
                "payload_sha256": digest,
                "issues": [issue.as_json() for issue in error.issues],
            },
        )
        raise
    write_json(
        report_path,
        {
            "contract_version": CONTRACT_VERSION,
            "valid": True,
            "payload_sha256": digest,
            "issues": [],
        },
    )
    return payload
