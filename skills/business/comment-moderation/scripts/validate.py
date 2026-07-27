"""Canonical validation for comment-moderation payloads.

Rejects:
- Forbidden domain terms (precise multi-character patterns)
- Absolute marketing phrases (superlative claims)
- Forbidden action keys (auto_approve, auto_reject, auto_delete, etc.)
- Payload self-declared ``execution_mode``
- Fixture mode without caller-provided synthetic-test mode
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

#: Forbidden domain terms — precise multi-character patterns used in
#: spam / low-quality comments in Chinese-language contexts.
FORBIDDEN_TERMS: Final = (
    "\u89e3\u51b3\u65b9\u6848",  # \u89e3\u51b3\u65b9\u6848
    "\u6570\u5b57\u8425\u9500",  # \u6570\u5b57\u8425\u9500
    "\u65b0\u96f6\u552e",  # \u65b0\u96f6\u552e
    "\u65b0\u5546\u4e1a",  # \u65b0\u5546\u4e1a
    "\u65b0\u8425\u9500",  # \u65b0\u8425\u9500
    "\u65b0\u6d88\u8d39",  # \u65b0\u6d88\u8d39
)

_FORBIDDEN_TERM_PATTERN: Final = re.compile(
    "|".join(re.escape(t) for t in FORBIDDEN_TERMS),
)

#: Absolute marketing phrases — precise multi-character superlative claims.
ABSOLUTE_PHRASES: Final = (
    "\u6700\u9886\u5148",  # \u6700\u9886\u5148
    "\u6700\u4f18\u79c0",
    "\u6700\u5927",
    "\u6700\u5c0f",
    "\u6700\u597d",
    "\u6700\u5dee",
    "\u6700\u5f3a",
    "\u6700\u5f31",
    "\u6700\u4f18",
    "\u6700\u5148\u8fdb",
    "\u6700\u5177",
    "\u6700\u5b8c\u5584",
    "\u6700\u4e13\u4e1a",
    "\u6700\u6743\u5a01",
    "\u6700\u4e30\u5bcc",
    "\u6700\u5168\u9762",
    "\u9996\u4e2a",
    "\u9996\u5bb6",
    "\u9996\u5c48\u4e00\u6307",
    "\u552f\u4e00",
    "\u72ec\u5bb6",
    "\u65e0\u4e0e\u4f26\u6bd4",
    "\u9065\u9065\u9886\u5148",
    "\u884c\u4e1a\u7b2c\u4e00",
    "\u5168\u56fd\u7b2c\u4e00",
    "\u5168\u7403\u7b2c\u4e00",
)

_ABSOLUTE_PATTERN: Final = re.compile(
    "|".join(re.escape(p) for p in ABSOLUTE_PHRASES),
)

#: Forbidden action keys — must NEVER appear in a comment-moderation payload.
FORBIDDEN_ACTION_KEYS: Final = (
    "auto_approve",
    "auto_reject",
    "auto_delete",
    "auto_reply",
    "auto_ban",
    "comment_approve",
    "comment_reject",
    "comment_delete",
    "comment_ban",
    "comment_update",
)

_ALLOWED_COMMENT_FIELDS: Final = frozenset({
    "comment_id",
    "article_id",
    "author_name",
    "content",
    "status",
    "risk_level",
    "risk_flags",
    "moderation_suggestion",
    "human_review_required",
    "fixture",
})

_COMMENT_OPS_EXTENSION_KEYS: Final = frozenset({"fixture"})


@dataclass
class ValidationResult:
    """Structured result of validating a comment payload."""

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


def _check_forbidden_terms(
    value: str, fname: str, result: ValidationResult,
) -> None:
    """Scan a string value for forbidden domain terms."""
    found = _FORBIDDEN_TERM_PATTERN.search(value)
    if found:
        result.errors.append(_error(
            fname,
            "forbidden_term",
            f"contains forbidden term: '{found.group()}'",
        ))
        result.valid = False


def _check_absolute_phrases(
    value: str, fname: str, result: ValidationResult,
) -> None:
    """Scan a string value for absolute marketing phrases."""
    found = _ABSOLUTE_PATTERN.search(value)
    if found:
        result.errors.append(_error(
            fname,
            "absolute_marketing_term",
            f"contains absolute marketing term: '{found.group()}'",
        ))
        result.valid = False


def _check_forbidden_actions(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Reject any forbidden action key in the payload."""
    for action in FORBIDDEN_ACTION_KEYS:
        if action in payload:
            result.errors.append(_error(
                action,
                "forbidden_action",
                f"comment-moderation must not include '{action}'",
            ))
            result.valid = False


def _check_required_comment_fields(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Verify required comment fields are present and non-empty."""
    required = ("comment_id", "article_id", "content")
    for field_name in required:
        value = payload.get(field_name)
        if value is None or (isinstance(value, str) and not value.strip()):
            result.errors.append(_error(
                field_name,
                "missing",
                f"required field '{field_name}' is missing or empty",
            ))
            result.valid = False


def validate_comment_payload(
    payload: dict[str, object],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate a comment-moderation payload.

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

    # 2. Fixture mode isolation (caller-provided mode only)
    if is_fixture and execution_mode != SYNTHETIC_TEST_MODE:
        result.errors.append(_error(
            "fixture",
            "fixture_requires_synthetic_mode",
            "fixture=true is only allowed with execution_mode=synthetic-test (caller-provided)",
        ))
        result.valid = False

    # 3. Required comment fields
    _check_required_comment_fields(payload, result)

    # 4. Forbidden domain terms in string values
    for fname, value in payload.items():
        if isinstance(value, str):
            _check_forbidden_terms(value, fname, result)
            _check_absolute_phrases(value, fname, result)

    # 5. Forbidden action keys
    _check_forbidden_actions(payload, result)

    # 6. Compute check summary
    error_codes = {e["code"] for e in result.errors}
    result.checks = {
        "field_completeness": not error_codes & {"missing"},
        "forbidden_terms": "forbidden_term" not in error_codes,
        "absolute_terms": "absolute_marketing_term" not in error_codes,
        "no_forbidden_actions": "forbidden_action" not in error_codes,
        "fixture_mode_safe": "fixture_requires_synthetic_mode" not in error_codes,
        "no_payload_execution_mode": "execution_mode_in_payload" not in error_codes,
    }

    return result
