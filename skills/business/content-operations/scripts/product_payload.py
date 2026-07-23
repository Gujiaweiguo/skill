"""Versioned Product payload schema and parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Final

from scripts.article_payload import JsonValue, PayloadValidationError, ValidationIssue

_SLUG: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_FORBIDDEN_TERMS: Final = ("解决方案", "数字营销", "新零售", "新商业", "新营销", "新消费")
_REQUIRED_FIELDS: Final = ("product_type", "slug", "title")
_OPTIONAL_FIELDS: Final = ("headline", "description", "seo_title", "seo_description", "image")
_ALLOWED_FIELDS: Final = frozenset((*_REQUIRED_FIELDS, *_OPTIONAL_FIELDS, "details", "status"))
_AI_VISION_SLUG_KEYWORDS: Final = ("mallsense", "vision")
_AI_VISION_MVP_CAPABILITIES: Final = frozenset({"通道拥堵", "火灾烟雾", "地面脏污"})


class ProductType(str, Enum):
    """Product types supported by the lnkwebsite CMS contract."""

    INDUSTRY = "industry"
    SKILL = "skill"
    AI_PAGE = "ai-page"


@dataclass(frozen=True, slots=True)
class ProductPayload:
    """Validated Product JSON payload."""

    product_type: ProductType
    slug: str
    title: str
    headline: str | None = None
    description: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    image: str | None = None
    details: dict[str, JsonValue] | None = None


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


def _check_ai_vision_boundaries(
    slug: str, details: dict[str, JsonValue] | None, issues: list[ValidationIssue]
) -> None:
    slug_lower = slug.lower()
    if not any(kw in slug_lower for kw in _AI_VISION_SLUG_KEYWORDS):
        return
    if details is None:
        return
    capabilities = details.get("capabilities")
    if not isinstance(capabilities, list):
        return
    for cap in capabilities:
        if isinstance(cap, dict):
            title = str(cap.get("title", ""))
        elif isinstance(cap, str):
            title = cap
        else:
            continue
        if title and title not in _AI_VISION_MVP_CAPABILITIES:
            issues.append(
                ValidationIssue(
                    "details.capabilities",
                    "ai_vision_mvp_boundary",
                    f"'{title}' is a roadmap item, not an MVP capability",
                )
            )


def _collect_required(
    raw: dict[str, JsonValue],
    issues: list[ValidationIssue],
) -> dict[str, str]:
    required: dict[str, str] = {}
    for field in _REQUIRED_FIELDS:
        value, issue = _required_string(raw, field)
        if issue is not None:
            issues.append(issue)
        elif value is not None:
            required[field] = value
    return required


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


def _parse_details(
    raw: dict[str, JsonValue],
    issues: list[ValidationIssue],
) -> dict[str, JsonValue] | None:
    if "details" not in raw or raw["details"] is None:
        return None
    if isinstance(raw["details"], dict):
        return raw["details"]
    issues.append(ValidationIssue("details", "dict_type", "details must be a JSON object"))
    return None


def parse_product_payload(raw_json: str | bytes) -> ProductPayload:
    """Parse untrusted JSON bytes into a validated draft Product payload."""
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

    required = _collect_required(raw, issues)

    product_type_raw = required.get("product_type")
    try:
        product_type = ProductType(product_type_raw or "")
    except ValueError:
        issues.append(
            ValidationIssue(
                "product_type", "enum", "product_type must be industry, skill, or ai-page"
            )
        )
        product_type = ProductType.INDUSTRY

    slug = required.get("slug")
    if slug is not None and _SLUG.fullmatch(slug) is None:
        issues.append(
            ValidationIssue(
                "slug", "string_pattern_mismatch", "slug must be lowercase ASCII kebab-case"
            )
        )

    optional = _collect_optional(raw, issues)
    details = _parse_details(raw, issues)

    if slug is not None:
        _check_ai_vision_boundaries(slug, details, issues)

    _check_forbidden_terms(raw, issues)
    if details is not None:
        _check_forbidden_terms(details, issues)

    if raw.get("status", "draft") != "draft":
        issues.append(ValidationIssue("status", "literal_error", "status must be draft"))

    if issues:
        raise PayloadValidationError(tuple(sorted(issues, key=lambda i: (i.field, i.code))))

    return ProductPayload(
        product_type=product_type,
        slug=required["slug"],
        title=required["title"],
        headline=optional["headline"],
        description=optional["description"],
        seo_title=optional["seo_title"],
        seo_description=optional["seo_description"],
        image=optional["image"],
        details=details,
    )
