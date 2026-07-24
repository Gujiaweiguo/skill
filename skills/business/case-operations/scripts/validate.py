"""Canonical validation for case-operations payloads.

Delegates core case payload validation to content-operations case_payload.py.
Adds case-operations-specific safety:
- Absolute marketing term rejection
- publish/unpublish/delete intent interception
- Fixture mode enforcement (execution_mode is caller-only, never in payload)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

_CONTENT_OPS_ROOT = Path(__file__).resolve().parents[2] / "content-operations"
if str(_CONTENT_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONTENT_OPS_ROOT))

from scripts.case_payload import parse_case_payload, PayloadValidationError  # type: ignore

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

ABSOLUTE_TERMS: Final = (
    "最", "第一", "唯一", "独家", "首屈一指", "无与伦比", "遥遥领先",
)

FORBIDDEN_ACTION_KEYS: Final = (
    "publish", "unpublish", "delete",
    "case_publish", "case_unpublish", "case_delete",
)

#: Keys stripped before delegating to content-ops.
_CASE_OPS_EXTENSION_KEYS: Final = frozenset({"fixture"})


@dataclass
class ValidationResult:
    valid: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": self.checks,
        }


def validate_case_payload(
    payload: dict[str, Any],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate a case payload.

    Args:
        payload: Raw decoded JSON dict. Must NOT contain ``execution_mode``.
        execution_mode: Caller-provided context kwarg only.
    """
    result = ValidationResult(valid=True)
    is_fixture = payload.get("fixture") is True

    # 1. Reject payload self-declared execution_mode
    if "execution_mode" in payload:
        result.errors.append({
            "field": "execution_mode",
            "code": "execution_mode_in_payload",
            "message": "execution_mode must be provided by the caller, "
                       "not declared in the payload",
        })
        result.valid = False

    # 2. Fixture mode isolation (caller-provided mode only)
    if is_fixture and execution_mode != SYNTHETIC_TEST_MODE:
        result.errors.append({
            "field": "fixture",
            "code": "fixture_requires_synthetic_mode",
            "message": "fixture=true is only allowed with "
                       "execution_mode=synthetic-test (caller-provided)",
        })
        result.valid = False

    # 3. Absolute marketing terms
    for fname, value in payload.items():
        if isinstance(value, str):
            for term in ABSOLUTE_TERMS:
                if term in value:
                    result.errors.append({
                        "field": fname,
                        "code": "absolute_marketing_term",
                        "message": f"contains absolute marketing term: '{term}'",
                    })
                    result.valid = False

    # 4. Publish / unpublish / delete intent
    for action in FORBIDDEN_ACTION_KEYS:
        if action in payload:
            result.errors.append({
                "field": action,
                "code": "forbidden_action",
                "message": f"case-operations must not include '{action}'",
            })
            result.valid = False

    # 5. Delegate core validation to content-ops
    cleaned = {k: v for k, v in payload.items()
               if k not in _CASE_OPS_EXTENSION_KEYS and k != "execution_mode"}
    try:
        parse_case_payload(json.dumps(cleaned, ensure_ascii=False))
    except PayloadValidationError as exc:
        result.valid = False
        for issue in exc.issues:
            result.errors.append({
                "field": issue.field,
                "code": issue.code,
                "message": issue.message,
            })

    error_codes = {e["code"] for e in result.errors}
    result.checks = {
        "field_completeness": not error_codes & {
            "missing", "string_too_short", "missing_field", "empty_field",
        },
        "client_authorized": "missing_or_false" not in error_codes,
        "forbidden_terms": "forbidden_term" not in error_codes,
        "absolute_terms": "absolute_marketing_term" not in error_codes,
        "no_forbidden_actions": "forbidden_action" not in error_codes,
        "fixture_mode_safe": "fixture_requires_synthetic_mode" not in error_codes,
        "no_payload_execution_mode": "execution_mode_in_payload" not in error_codes,
    }

    return result
