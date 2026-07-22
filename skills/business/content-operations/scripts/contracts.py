"""Compatibility exports plus deterministic Article digest and report I/O."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Final

from scripts.article_payload import (
    ArticleCategory,
    ArticlePayload,
    CmsCreateFields,
    CmsRequiredFields,
    JsonValue,
    PayloadValidationError,
    ValidationIssue,
    cms_create_fields,
    parse_article_payload,
)

if TYPE_CHECKING:
    from pathlib import Path

CONTRACT_VERSION: Final = "1.0.0"

__all__ = [
    "CONTRACT_VERSION",
    "ArticleCategory",
    "ArticlePayload",
    "CmsCreateFields",
    "CmsRequiredFields",
    "JsonValue",
    "PayloadValidationError",
    "ValidationIssue",
    "cms_create_fields",
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


def validate_payload_file(payload_path: Path, report_path: Path) -> ArticlePayload:
    """Validate one payload file and write its deterministic report."""
    digest = payload_sha256(payload_path)
    try:
        payload = parse_article_payload(payload_path.read_bytes())
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
