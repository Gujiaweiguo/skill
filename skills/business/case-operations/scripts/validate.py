"""Canonical validation for case-operations payloads.

Delegates core case payload validation to
:mod:`content-operations.scripts.case_payload`.
Adds case-operations-specific safety:

- Absolute marketing term rejection
- ``publish`` / ``unpublish`` / ``delete`` intent interception
- Fixture mode enforcement (``execution_mode`` is caller-only,
  never declared inside the payload)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

_CONTENT_OPS_ROOT = Path(__file__).resolve().parents[2] / "content-operations"
if str(_CONTENT_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONTENT_OPS_ROOT))

from scripts.case_payload import (  # type: ignore[import-not-found]
    PayloadValidationError,
    parse_case_payload,
)

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

ABSOLUTE_TERMS: Final = (
    "最", "第一", "唯一", "独家", "首屈一指", "无与伦比", "遥遥领先",
)

FORBIDDEN_ACTION_KEYS: Final = (
    "publish", "unpublish", "delete",
    "case_publish", "case_unpublish", "case_delete",
)

_CASE_OPS_EXTENSION_KEYS: Final = frozenset({"fixture"})


@dataclass
class ValidationResult:
    """Structured result of validating one case payload."""

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


def _error(field: str, code: str, message: str) -> dict[str, str]:  # noqa: A002
    """Build a single error dict."""
    return {"field": field, "code": code, "message": message}


def validate_case_payload(
    payload: dict[str, object],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate a case payload.

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

    # 3. Absolute marketing terms
    for fname, value in payload.items():
        if isinstance(value, str):
            for term in ABSOLUTE_TERMS:
                if term in value:
                    result.errors.append(_error(
                        str(fname),
                        "absolute_marketing_term",
                        f"contains absolute marketing term: '{term}'",
                    ))
                    result.valid = False

    # 4. Publish / unpublish / delete intent
    for action in FORBIDDEN_ACTION_KEYS:
        if action in payload:
            result.errors.append(_error(
                action,
                "forbidden_action",
                f"case-operations must not include '{action}'",
            ))
            result.valid = False

    # 5. Delegate core validation to content-ops
    cleaned = {
        k: v for k, v in payload.items()
        if k not in _CASE_OPS_EXTENSION_KEYS and k != "execution_mode"
    }
    try:
        parse_case_payload(json.dumps(cleaned, ensure_ascii=False))
    except PayloadValidationError as exc:
        result.valid = False
        for issue in exc.issues:
            result.errors.append(_error(
                issue.field,
                issue.code,
                issue.message,
            ))

    error_codes = {e["code"] for e in result.errors}
    result.checks = {
        "field_completeness": not error_codes & {
            "missing", "string_too_short", "missing_field", "empty_field",
        },
        "client_authorized": "missing_or_false" not in error_codes,
        "forbidden_terms": "forbidden_term" not in error_codes,
        "absolute_terms": "absolute_marketing_term" not in error_codes,
        "no_forbidden_actions": "forbidden_action" not in error_codes,
        "fixture_mode_safe": (
            "fixture_requires_synthetic_mode" not in error_codes
        ),
        "no_payload_execution_mode": (
            "execution_mode_in_payload" not in error_codes
        ),
    }

    return result
