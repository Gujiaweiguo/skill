"""Runtime artifact verification and receipt contracts for draft imports."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from scripts.contracts import CONTRACT_VERSION, ArticleCategory, JsonValue

_SHA256: Final = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class ImportPaths:
    """Runtime paths consumed and produced by one draft import."""

    content_output_base: Path
    payload: Path
    validation_report: Path
    source_draft: Path
    review_record: Path
    receipt: Path


@dataclass(frozen=True, slots=True)
class ImportReceipt:
    """Auditable result of one successful CMS draft creation."""

    source_draft: str
    payload_sha256: str
    cms_article_id: str
    slug: str
    category: ArticleCategory
    status: Literal["draft"] = "draft"

    def as_json(self) -> dict[str, JsonValue]:
        """Return the receipt as a JSON-compatible mapping."""
        return {
            "contract_version": CONTRACT_VERSION,
            "source_draft": self.source_draft,
            "payload_sha256": self.payload_sha256,
            "cms_article_id": self.cms_article_id,
            "slug": self.slug,
            "category": self.category.value,
            "status": self.status,
        }


class ImportArtifactError(Exception):
    """Raised when runtime artifacts do not satisfy the v1 handoff contract."""

    artifact: str
    reason: str

    def __init__(self, artifact: str, reason: str) -> None:
        """Retain the artifact name and machine-readable failure reason."""
        self.artifact = artifact
        self.reason = reason
        super().__init__(f"{artifact}: {reason}")


def _require_within(path: Path, root: Path, artifact: str) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ImportArtifactError(artifact, f"must be under {root}") from error


def _read_json_object(path: Path, artifact: str) -> dict[str, JsonValue]:
    try:
        raw: JsonValue = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ImportArtifactError(artifact, str(error)) from error
    if not isinstance(raw, dict):
        raise ImportArtifactError(artifact, "must be a JSON object")
    return raw


def _require_string(
    values: dict[str, JsonValue],
    field: str,
    artifact: str,
) -> str:
    value = values.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ImportArtifactError(artifact, f"{field} must be a non-empty string")
    return value.strip()


def _validate_report(report: dict[str, JsonValue], digest: str) -> None:
    expected_fields = {
        "contract_version",
        "valid",
        "payload_sha256",
        "issues",
    }
    if set(report) != expected_fields:
        raise ImportArtifactError(
            "validation report",
            "fields do not match the v1 contract",
        )
    report_digest = _require_string(
        report,
        "payload_sha256",
        "validation report",
    )
    if (
        report.get("contract_version") != CONTRACT_VERSION
        or report.get("valid") is not True
        or report.get("issues") != []
        or report_digest != digest
        or _SHA256.fullmatch(report_digest) is None
    ):
        raise ImportArtifactError(
            "validation report",
            "must be valid and match the exact payload digest",
        )


def _validate_review(
    review: dict[str, JsonValue],
    digest: str,
    source_draft: Path,
) -> None:
    expected_fields = {
        "contract_version",
        "source_draft",
        "payload_sha256",
        "decision",
        "slug_available",
    }
    if set(review) != expected_fields:
        raise ImportArtifactError(
            "review record",
            "fields do not match the v1 contract",
        )
    review_digest = _require_string(review, "payload_sha256", "review record")
    review_source = _require_string(review, "source_draft", "review record")
    if (
        review.get("contract_version") != CONTRACT_VERSION
        or review.get("decision") != "approved"
        or review.get("slug_available") is not True
        or review_digest != digest
        or _SHA256.fullmatch(review_digest) is None
    ):
        raise ImportArtifactError(
            "review record",
            "must approve the exact payload with an available slug",
        )
    if Path(review_source).resolve() != source_draft.resolve():
        raise ImportArtifactError("review record", "source draft does not match")


def validate_import_artifacts(paths: ImportPaths, digest: str) -> None:
    """Verify runtime locations, validation evidence, and human approval."""
    base = paths.content_output_base.resolve()
    _require_within(paths.source_draft, base / "drafts", "source draft")
    _require_within(paths.review_record, base / "review", "review record")
    _require_within(paths.payload, base / "publish-jobs", "payload")
    _require_within(
        paths.validation_report,
        base / "publish-jobs",
        "validation report",
    )
    _require_within(paths.receipt, base / "publish-jobs", "receipt")

    _validate_report(
        _read_json_object(paths.validation_report, "validation report"),
        digest,
    )
    _validate_review(
        _read_json_object(paths.review_record, "review record"),
        digest,
        paths.source_draft,
    )
    try:
        source_text = paths.source_draft.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ImportArtifactError("source draft", str(error)) from error
    if not source_text.strip():
        raise ImportArtifactError("source draft", "must be non-empty")
