"""Validation for lead-operations payloads.

Read-only triage skill: classifies leads and generates suggestions.
Never sends external messages or modifies lead status.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final, cast

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

FORBIDDEN_LEAD_IDS: Final = frozenset({1, 2})

ABSOLUTE_PHRASES: Final = (
    "最领先", "最优秀", "最大", "最小", "最好", "最差",
    "最强", "最弱", "最优", "最先进", "最具", "最完善",
    "最专业", "最权威", "最丰富", "最全面",
    "首个", "首家", "首屈一指", "唯一", "独家",
    "无与伦比", "遥遥领先", "行业第一", "全国第一", "全球第一",
)

_ABSOLUTE_PATTERN: Final = re.compile(
    "|".join(re.escape(p) for p in ABSOLUTE_PHRASES),
)

FORBIDDEN_DOMAIN_TERMS: Final = (
    "解决方案", "数字营销", "新零售", "新商业", "新营销", "新消费",
)

FORBIDDEN_ACTION_KEYS: Final = (
    "send_email", "send_sms", "send_im", "send_webhook",
    "lead_update", "lead_status_change", "lead_assign",
    "auto_assign", "auto_reply",
)


@dataclass
class ValidationResult:
    """Structured result of validating a lead triage payload."""

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


def _check_execution_mode(
    payload: dict[str, object],
    execution_mode: str | None,
    result: ValidationResult,
) -> None:
    """Reject payload-declared execution_mode and validate fixture mode."""
    if "execution_mode" in payload:
        result.errors.append(_error(
            "execution_mode", "execution_mode_in_payload",
            "execution_mode must be provided by the caller, not in payload",
        ))
        result.valid = False

    is_fixture = payload.get("fixture") is True
    if is_fixture and execution_mode != SYNTHETIC_TEST_MODE:
        result.errors.append(_error(
            "fixture", "fixture_requires_synthetic_mode",
            "fixture=true requires execution_mode=synthetic-test",
        ))
        result.valid = False


def _check_forbidden_actions(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Reject any forbidden action keys."""
    for action in FORBIDDEN_ACTION_KEYS:
        if action in payload:
            result.errors.append(_error(
                action, "forbidden_action",
                f"lead-operations must not include '{action}'",
            ))
            result.valid = False


def _check_lead_ids(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Validate lead_ids list contents."""
    lead_ids_raw = payload.get("lead_ids", [])
    if not isinstance(lead_ids_raw, list) or not lead_ids_raw:
        result.errors.append(_error(
            "lead_ids", "missing",
            "lead_ids must be a non-empty list",
        ))
        result.valid = False
        return

    lead_ids = cast("list[object]", lead_ids_raw)
    for lid in lead_ids:
        if not isinstance(lid, int) or lid < 1:
            result.errors.append(_error(
                "lead_ids", "invalid_id",
                f"invalid lead id: {lid}",
            ))
            result.valid = False
        elif lid in FORBIDDEN_LEAD_IDS:
            result.errors.append(_error(
                "lead_ids", "forbidden_lead_id",
                f"lead id {lid} is forbidden (protected/test data)",
            ))
            result.valid = False


def _check_text_fields(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Scan string values for forbidden terms and absolute phrases."""
    for fname, value in payload.items():
        if not isinstance(value, str):
            continue
        found = _ABSOLUTE_PATTERN.search(value)
        if found:
            result.errors.append(_error(
                str(fname), "absolute_marketing_term",
                f"contains absolute marketing term: '{found.group()}'",
            ))
            result.valid = False
        for term in FORBIDDEN_DOMAIN_TERMS:
            if term in value:
                result.errors.append(_error(
                    str(fname), "forbidden_term",
                    f"contains forbidden term: '{term}'",
                ))
                result.valid = False


def _build_checks(result: ValidationResult) -> dict[str, bool]:
    """Derive check flags from collected errors."""
    error_codes = {e["code"] for e in result.errors}
    return {
        "lead_ids_valid": not error_codes & {
            "missing", "invalid_id", "forbidden_lead_id",
        },
        "no_forbidden_actions": "forbidden_action" not in error_codes,
        "no_absolute_terms": "absolute_marketing_term" not in error_codes,
        "no_forbidden_terms": "forbidden_term" not in error_codes,
        "fixture_mode_safe": "fixture_requires_synthetic_mode" not in error_codes,
        "no_payload_execution_mode": "execution_mode_in_payload" not in error_codes,
    }


def validate_lead_payload(
    payload: dict[str, object],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate a lead-operations triage payload.

    Args:
        payload: Raw decoded JSON dict.
        execution_mode: Caller-provided context kwarg only.

    Returns:
        ValidationResult with all errors / warnings / check flags.

    """
    result = ValidationResult(valid=True)

    _check_execution_mode(payload, execution_mode, result)
    _check_forbidden_actions(payload, result)
    _check_lead_ids(payload, result)
    _check_text_fields(payload, result)

    result.checks = _build_checks(result)
    return result
