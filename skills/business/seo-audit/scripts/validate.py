"""Validation for seo-audit payloads.

Enforces read-only audit safety:

- Forbidden marketing jargon rejection (precise multi-character patterns)
- Absolute marketing phrase rejection
- Forbidden action interception (auto_modify_nginx, auto_submit_sitemap,
  auto_modify_canonical, auto_modify_meta, sitemap_write)
- Fixture mode enforcement
- Payload self-declared execution_mode rejection
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final, cast

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

#: Forbidden jargon — precise multi-character patterns.
#: Each entry is a specific buzzword that signals marketing intent.
FORBIDDEN_JARGON: Final = (
    "解决方案",
    "数字营销",
    "新零售",
    "新商业",
    "新营销",
    "新消费",
)

_FORBIDDEN_JARGON_PATTERN: Final = re.compile(
    "|".join(re.escape(p) for p in FORBIDDEN_JARGON),
)

#: Absolute marketing phrases — precise multi-character patterns.
ABSOLUTE_PHRASES: Final = (
    "最领先",
    "最优秀",
    "最大",
    "最小",
    "最好",
    "最差",
    "最强",
    "最弱",
    "最优",
    "最先进",
    "最具",
    "最完善",
    "最专业",
    "最权威",
    "最丰富",
    "最全面",
    "首个",
    "首家",
    "首屈一指",
    "唯一",
    "独家",
    "无与伦比",
    "遥遥领先",
    "行业第一",
    "全国第一",
    "全球第一",
)

_ABSOLUTE_PATTERN: Final = re.compile(
    "|".join(re.escape(p) for p in ABSOLUTE_PHRASES),
)

FORBIDDEN_ACTION_KEYS: Final = (
    "auto_modify_nginx",
    "auto_submit_sitemap",
    "auto_modify_canonical",
    "auto_modify_meta",
    "sitemap_write",
)

_ALLOWED_AUDIT_SCOPES: Final = frozenset({"full", "sitemap-only", "canonical-only", "schema-only"})

_EXTENSION_KEYS: Final = frozenset({"fixture"})


@dataclass
class ValidationResult:
    """Structured result of validating one SEO audit payload."""

    valid: bool
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": self.checks,
        }


def _error(field: str, code: str, message: str) -> dict[str, str]:
    """Build a single error dict."""
    return {"field": field, "code": code, "message": message}


def _check_jargon(value: str, field_name: str) -> list[dict[str, str]]:
    """Check a single string value for forbidden jargon."""
    errors: list[dict[str, str]] = []
    found = _FORBIDDEN_JARGON_PATTERN.search(value)
    if found:
        errors.append(_error(
            field_name,
            "forbidden_term",
            f"contains forbidden marketing jargon: '{found.group()}'",
        ))
    return errors


def _check_absolute_phrases(value: str, field_name: str) -> list[dict[str, str]]:
    """Check a single string value for absolute marketing phrases."""
    errors: list[dict[str, str]] = []
    found = _ABSOLUTE_PATTERN.search(value)
    if found:
        errors.append(_error(
            field_name,
            "absolute_marketing_term",
            f"contains absolute marketing term: '{found.group()}'",
        ))
    return errors


def _check_forbidden_actions(payload: dict[str, object]) -> list[dict[str, str]]:
    """Check payload for forbidden action keys."""
    return [
        _error(action, "forbidden_action", f"seo-audit must not include '{action}'")
        for action in FORBIDDEN_ACTION_KEYS
        if action in payload
    ]


def _check_string_fields(payload: dict[str, object]) -> list[dict[str, str]]:
    """Scan all string values in payload for jargon and absolute phrases."""
    errors: list[dict[str, str]] = []
    for fname, value in payload.items():
        if isinstance(value, str):
            errors.extend(_check_jargon(value, str(fname)))
            errors.extend(_check_absolute_phrases(value, str(fname)))
        elif isinstance(value, dict):
            errors.extend(_check_string_fields(cast("dict[str, object]", value)))
        elif isinstance(value, list):
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    errors.extend(_check_string_fields(cast("dict[str, object]", item)))
                elif isinstance(item, str):
                    errors.extend(_check_jargon(item, f"{fname}[{idx}]"))
                    errors.extend(_check_absolute_phrases(item, f"{fname}[{idx}]"))
    return errors


def _check_scope(payload: dict[str, object]) -> list[dict[str, str]]:
    """Validate audit_scope value."""
    errors: list[dict[str, str]] = []
    scope = payload.get("audit_scope")
    if scope is not None and cast("str", scope) not in _ALLOWED_AUDIT_SCOPES:
        errors.append(_error(
            "audit_scope",
            "invalid_scope",
            f"audit_scope must be one of {sorted(_ALLOWED_AUDIT_SCOPES)}, got '{scope}'",
        ))
    return errors


_DATE_PATTERN: Final = re.compile(r"\d{4}-\d{2}-\d{2}")


def _check_date_field(payload: dict[str, object]) -> list[dict[str, str]]:
    """Validate audit_date format (YYYY-MM-DD)."""
    errors: list[dict[str, str]] = []
    date_val = payload.get("audit_date")
    if (
        date_val is not None
        and isinstance(date_val, str)
        and _DATE_PATTERN.fullmatch(date_val) is None
    ):
        errors.append(_error(
                "audit_date",
                "invalid_date_format",
                "audit_date must be in YYYY-MM-DD format",
            ))
    return errors


def validate_audit_payload(
    payload: dict[str, object],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate an SEO audit payload.

    Args:
        payload: Raw decoded JSON dict.
            Must NOT contain ``execution_mode``.
        execution_mode: Caller-provided context kwarg only.

    Returns:
        ValidationResult with all errors / warnings / check flags.

    """
    result = ValidationResult(valid=True)
    is_fixture = payload.get("fixture") is True

    # 1. Reject payload self-declared execution_mode
    if "execution_mode" in payload:
        result.errors.append(_error(
            "execution_mode",
            "execution_mode_in_payload",
            "execution_mode must be provided by the caller, not declared in the payload",
        ))
        result.valid = False

    # 2. Fixture mode isolation
    if is_fixture and execution_mode != SYNTHETIC_TEST_MODE:
        result.errors.append(_error(
            "fixture",
            "fixture_requires_synthetic_mode",
            "fixture=true is only allowed with execution_mode=synthetic-test (caller-provided)",
        ))
        result.valid = False

    # 3. Forbidden marketing jargon and absolute phrases
    result.errors.extend(_check_string_fields(payload))
    if result.errors:
        result.valid = False

    # 4. Forbidden actions
    action_errors = _check_forbidden_actions(payload)
    result.errors.extend(action_errors)
    if action_errors:
        result.valid = False

    # 5. Scope validation
    result.errors.extend(_check_scope(payload))

    # 6. Date format validation
    result.errors.extend(_check_date_field(payload))

    if any(e["code"] in {"invalid_scope", "invalid_date_format"} for e in result.errors):
        result.valid = False

    error_codes = {e["code"] for e in result.errors}
    result.checks = {
        "forbidden_terms": "forbidden_term" not in error_codes,
        "absolute_terms": "absolute_marketing_term" not in error_codes,
        "no_forbidden_actions": "forbidden_action" not in error_codes,
        "fixture_mode_safe": (
            "fixture_requires_synthetic_mode" not in error_codes
        ),
        "no_payload_execution_mode": (
            "execution_mode_in_payload" not in error_codes
        ),
        "valid_scope": "invalid_scope" not in error_codes,
        "valid_date": "invalid_date_format" not in error_codes,
    }

    return result
