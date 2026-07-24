"""Canonical validation for case-operations payloads.

Delegates core case payload validation (field completeness, client_authorized
fail-closed, domain forbidden terms, slug pattern, industry enum) to the
shared content-operations/scripts/case_payload.py — the single source of
truth for case payload rules.

Adds case-operations-specific safety on top:
- Absolute marketing term rejection (editorial policy)
- publish / unpublish / delete intent interception
- fixture mode enforcement (synthetic-test isolation)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

# ---------------------------------------------------------------------------
# Import the shared case-payload rules from content-operations.
# This is the canonical source for: required fields, client_authorized
# fail-closed, domain forbidden terms, slug pattern, industry enum, status.
# ---------------------------------------------------------------------------
_CONTENT_OPS_ROOT = Path(__file__).resolve().parents[2] / "content-operations"
if str(_CONTENT_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONTENT_OPS_ROOT))

from scripts.case_payload import parse_case_payload, PayloadValidationError  # type: ignore

# ---------------------------------------------------------------------------
# Case-operations-specific constants (NOT in content-ops)
# ---------------------------------------------------------------------------

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

#: Absolute / superlative marketing terms banned by editorial policy.
ABSOLUTE_TERMS: Final = (
    "最", "第一", "唯一", "独家", "首屈一指", "无与伦比", "遥遥领先",
)

#: Payload keys that indicate a publish / unpublish / delete intent.
FORBIDDEN_ACTION_KEYS: Final = (
    "publish", "unpublish", "delete",
    "case_publish", "case_unpublish", "case_delete",
)

#: Fields stripped before delegating to content-ops (case-ops extensions).
_CASE_OPS_EXTENSION_KEYS: Final = frozenset({"fixture", "execution_mode"})


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Structured result of validating one case payload."""

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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_case_payload(
    payload: dict[str, Any],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate a case payload.

    Args:
        payload: Raw decoded JSON dict.
        execution_mode: Caller's execution context. Must be
            ``"synthetic-test"`` when ``fixture`` is ``True``.

    Returns:
        ValidationResult with all errors / warnings / check flags.
    """
    result = ValidationResult(valid=True)

    is_fixture = payload.get("fixture") is True

    # --- Case-ops-specific pre-checks ---

    # 1. Fixture mode isolation
    # execution_mode is a CALLER-PROVIDED context, not a payload self-declaration.
    # A payload must NOT bypass fixture safety by declaring its own mode.
    if is_fixture and execution_mode != SYNTHETIC_TEST_MODE:
        result.errors.append({
            "field": "fixture",
            "code": "fixture_requires_synthetic_mode",
            "message": "fixture=true is only allowed with execution_mode=synthetic-test",
        })
        result.valid = False

    # 2. Absolute marketing terms (case-ops editorial policy)
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

    # 3. Publish / unpublish / delete intent interception
    for action in FORBIDDEN_ACTION_KEYS:
        if action in payload:
            result.errors.append({
                "field": action,
                "code": "forbidden_action",
                "message": f"case-operations must not include '{action}'",
            })
            result.valid = False

    # --- Delegate core validation to content-ops case_payload.py ---
    # Strip case-ops extension keys so content-ops sees a clean CMS payload.
    cleaned = {k: v for k, v in payload.items() if k not in _CASE_OPS_EXTENSION_KEYS}
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

    # --- Summary check flags ---
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
    }

    return result
