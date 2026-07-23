"""Versioned Case payload schema and parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

from scripts.article_payload import JsonValue, PayloadValidationError, ValidationIssue

_SLUG: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FORBIDDEN_TERMS: Final = ("解决方案", "数字营销", "新零售", "新商业", "新营销", "新消费")
_REQUIRED_FIELDS: Final = ("slug", "client_name", "industry", "problem", "solution", "outcome")
_OPTIONAL_FIELDS: Final = ("testimonial", "image", "seo_title", "seo_description", "product")
_ALLOWED_FIELDS: Final = frozenset(
    (*_REQUIRED_FIELDS, *_OPTIONAL_FIELDS, "client_authorized", "status")
)
_AI_VISION_MVP_CAPABILITIES: Final = frozenset({"通道拥堵", "火灾烟雾", "地面脏污"})


class CaseIndustry(str, Enum):
    """Case industries supported by the lnkwebsite CMS contract."""

    COMMERCIAL_REAL_ESTATE = "commercial-real-estate"
    OFFICE = "office"
    SHOPPING_CENTER = "shopping-center"
    PROPERTY = "property"
    PARK = "park"
    COMMUNITY = "community"
    COMPLEX = "complex"


@dataclass(frozen=True, slots=True)
class CasePayload:
    """Validated Case JSON payload."""

    slug: str
    client_name: str
    industry: CaseIndustry
    problem: str
    solution: str
    outcome: str
    client_authorized: bool
    testimonial: str | None = None
    image: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    product: str | None = None


def _load_json(raw_json: str | bytes) -> JsonValue:
    try:
        return json.loads(raw_json)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise PayloadValidationError((ValidationIssue("$", "json_invalid", str(error)),)) from error


def _required_string(
    values: dict[str, JsonValue], field: str
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


def _check_forbidden_terms(values: dict[str, JsonValue], issues: list[ValidationIssue]) -> None:
    for field, value in values.items():
        if isinstance(value, str):
            found = [
                ValidationIssue(field, "forbidden_term", f"contains banned term: {term}")
                for term in _FORBIDDEN_TERMS
                if term in value
            ]
            issues.extend(found)


def _collect_optional(
    raw: dict[str, JsonValue],
    issues: list[ValidationIssue],
) -> dict[str, str | None]:
    optional: dict[str, str | None] = {}
    for field in _OPTIONAL_FIELDS:
        if field not in raw:
            optional[field] = None
            continue
        value, issue = _required_string(raw, field)
        if issue is not None:
            issues.append(issue)
        optional[field] = value
    return optional


def parse_case_payload(raw_json: str | bytes) -> CasePayload:
    """Parse untrusted JSON bytes into a validated draft Case payload."""
    raw = _load_json(raw_json)
    if not isinstance(raw, dict):
        raise PayloadValidationError(
            (ValidationIssue("$", "json_object_required", "payload must be a JSON object"),)
        )

    issues: list[ValidationIssue] = []
    issues.extend(
        ValidationIssue(field, "extra_forbidden", "unknown field is not permitted")
        for field in sorted(set(raw).difference(_ALLOWED_FIELDS))
    )

    required: dict[str, str] = {}
    for field in _REQUIRED_FIELDS:
        value, issue = _required_string(raw, field)
        if issue is not None:
            issues.append(issue)
        elif value is not None:
            required[field] = value

    industry_raw = required.get("industry")
    try:
        industry = CaseIndustry(industry_raw or "")
    except ValueError:
        issues.append(ValidationIssue("industry", "enum", "industry is not supported"))
        industry = CaseIndustry.OFFICE

    slug = required.get("slug")
    if slug is not None and _SLUG.fullmatch(slug) is None:
        issues.append(
            ValidationIssue(
                "slug", "string_pattern_mismatch", "slug must be lowercase ASCII kebab-case"
            )
        )

    if raw.get("client_authorized") is not True:
        issues.append(
            ValidationIssue(
                "client_authorized", "missing_or_false", "client authorization must be true"
            )
        )

    optional = _collect_optional(raw, issues)
    _check_forbidden_terms(raw, issues)

    if raw.get("status", "draft") != "draft":
        issues.append(ValidationIssue("status", "literal_error", "status must be draft"))

    if issues:
        raise PayloadValidationError(tuple(sorted(issues, key=lambda i: (i.field, i.code))))

    return CasePayload(
        slug=required["slug"],
        client_name=required["client_name"],
        industry=industry,
        problem=required["problem"],
        solution=required["solution"],
        outcome=required["outcome"],
        client_authorized=True,
        testimonial=optional["testimonial"],
        image=optional["image"],
        seo_title=optional["seo_title"],
        seo_description=optional["seo_description"],
        product=optional["product"],
    )
