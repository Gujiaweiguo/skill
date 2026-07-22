"""Versioned Article payload schema and parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal

_HTML_TAG: Final = re.compile(r"<[A-Za-z][^>]*>")
_SLUG: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_REQUIRED_FIELDS: Final = ("title", "body", "slug", "category")
_OPTIONAL_FIELDS: Final = ("summary", "source_name", "commentary")
_ALLOWED_FIELDS: Final = frozenset((*_REQUIRED_FIELDS, *_OPTIONAL_FIELDS, "status"))
_PUBLICATION_INTENT_FIELDS: Final = frozenset(
    {
        "is_published",
        "publication_status",
        "publish",
        "publish_at",
        "published",
        "published_at",
    }
)

JsonValue = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


class ArticleCategory(str, Enum):
    """Article categories supported by the lnkwebsite CMS contract."""

    AI_TRENDS = "ai-trends"
    INDUSTRY_INSIGHTS = "industry-insights"
    CASE_STUDIES = "case-studies"
    COMMUNITY = "community"


@dataclass(frozen=True, slots=True)
class ArticlePayload:
    """Validated Article JSON payload."""

    title: str
    body: str
    slug: str
    category: ArticleCategory
    summary: str | None = None
    source_name: str | None = None
    commentary: str | None = None
    status: Literal["draft"] = "draft"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One deterministic Article payload validation issue."""

    field: str
    code: str
    message: str

    def as_json(self) -> dict[str, JsonValue]:
        """Return the issue as a JSON-compatible mapping."""
        return {"field": self.field, "code": self.code, "message": self.message}


class PayloadValidationError(Exception):
    """Raised when Article JSON does not satisfy the v1 contract."""

    issues: tuple[ValidationIssue, ...]

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        """Retain structured issues while preserving normal exception mutation."""
        self.issues = issues
        message = "; ".join(
            f"{issue.field}: {issue.code} ({issue.message})" for issue in self.issues
        )
        super().__init__(message)


def _load_json(raw_json: str | bytes) -> JsonValue:
    try:
        return json.loads(raw_json)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise PayloadValidationError((ValidationIssue("$", "json_invalid", str(error)),)) from error


def _required_string(
    values: dict[str, JsonValue],
    field: str,
) -> tuple[str | None, ValidationIssue | None]:
    value = values.get(field)
    if value is None:
        return None, ValidationIssue(field, "missing", "field is required")
    if not isinstance(value, str):
        return None, ValidationIssue(field, "string_type", "value must be a string")
    stripped = value.strip()
    if not stripped:
        return None, ValidationIssue(field, "string_too_short", "value must be non-empty")
    return stripped, None


def _collect_strings(
    raw: dict[str, JsonValue],
    issues: list[ValidationIssue],
) -> tuple[dict[str, str], dict[str, str | None]]:
    required: dict[str, str] = {}
    for field in _REQUIRED_FIELDS:
        value, issue = _required_string(raw, field)
        if issue is not None:
            issues.append(issue)
        elif value is not None:
            required[field] = value

    optional: dict[str, str | None] = {}
    for field in _OPTIONAL_FIELDS:
        if field not in raw:
            optional[field] = None
            continue
        value, issue = _required_string(raw, field)
        if issue is not None:
            issues.append(issue)
        optional[field] = value
    return required, optional


def _validate_body_and_slug(
    required: dict[str, str],
    issues: list[ValidationIssue],
) -> None:
    body = required.get("body")
    if body is not None and _HTML_TAG.search(body) is None:
        issues.append(
            ValidationIssue("body", "html_body_required", "body must contain HTML markup")
        )
    slug = required.get("slug")
    if slug is not None and _SLUG.fullmatch(slug) is None:
        issues.append(
            ValidationIssue(
                "slug",
                "string_pattern_mismatch",
                "slug must be lowercase ASCII kebab-case",
            )
        )


def _parse_category(
    category_value: str | None,
    issues: list[ValidationIssue],
) -> ArticleCategory:
    try:
        return ArticleCategory(category_value or "")
    except ValueError:
        if category_value is not None:
            issues.append(ValidationIssue("category", "enum", "category is not supported"))
        return ArticleCategory.AI_TRENDS


def parse_article_payload(raw_json: str | bytes) -> ArticlePayload:
    """Parse untrusted JSON bytes into a validated draft Article payload."""
    raw = _load_json(raw_json)
    if not isinstance(raw, dict):
        raise PayloadValidationError(
            (ValidationIssue("$", "json_object_required", "payload must be a JSON object"),)
        )

    issues: list[ValidationIssue] = []
    publication_fields = sorted(_PUBLICATION_INTENT_FIELDS.intersection(raw))
    issues.extend(
        ValidationIssue(
            field,
            "publication_intent",
            "publication intent is outside this contract",
        )
        for field in publication_fields
    )
    issues.extend(
        ValidationIssue(field, "extra_forbidden", "unknown field is not permitted")
        for field in sorted(set(raw).difference(_ALLOWED_FIELDS, publication_fields))
    )

    required, optional = _collect_strings(raw, issues)
    _validate_body_and_slug(required, issues)
    category = _parse_category(required.get("category"), issues)

    status_value = raw.get("status", "draft")
    if status_value != "draft":
        issues.append(ValidationIssue("status", "literal_error", "status must be draft"))

    if issues:
        raise PayloadValidationError(
            tuple(sorted(issues, key=lambda issue: (issue.field, issue.code)))
        )
    return ArticlePayload(
        title=required["title"],
        body=required["body"],
        slug=required["slug"],
        category=category,
        summary=optional["summary"],
        source_name=optional["source_name"],
        commentary=optional["commentary"],
    )
