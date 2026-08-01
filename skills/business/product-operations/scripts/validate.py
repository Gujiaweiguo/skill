"""Canonical validation for product-operations payloads.

Supports DRAFT creation only.  All product_create results must remain
in ``status=draft``; publishing is a separate human workflow.

Safety checks:
- Forbidden marketing terms (domain-specific + absolute superlatives)
- Forbidden actions (publish/unpublish/delete/direct_sql/bulk_import)
- AI Vision MVP capability gating (only 3 MVP caps allowed)
- Fixture mode enforcement (``execution_mode`` is caller-only)
- Required field completeness
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final, cast

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

# --- Forbidden domain terms ---

DOMAIN_FORBIDDEN_TERMS: Final = frozenset({
    "解决方案",
    "数字营销",
    "新零售",
    "新商业",
    "新营销",
    "新消费",
})

# --- Absolute marketing phrases ---

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

# --- Forbidden action keys ---

FORBIDDEN_ACTION_KEYS: Final = (
    "product_publish",
    "product_unpublish",
    "product_delete",
    "direct_sql",
    "bulk_import",
)

# --- AI Vision MVP capabilities ---

AI_VISION_MVP_CAPABILITIES: Final = frozenset({
    "通道拥堵检测",
    "火灾烟雾识别",
    "地面脏污识别",
})

# --- Required fields ---

REQUIRED_FIELDS: Final = frozenset({
    "slug",
    "product_name",
    "category",
    "short_description",
    "description",
    "vendor",
    "capabilities",
})

_PRODUCT_OPS_EXTENSION_KEYS: Final = frozenset({"fixture"})


def _error(field: str, code: str, message: str) -> dict[str, str]:
    """Build a single error dict."""
    return {"field": field, "code": code, "message": message}


def _check_domain_terms(
    payload: dict[str, object],
) -> list[dict[str, str]]:
    """Check all string values for forbidden domain terms."""
    errors: list[dict[str, str]] = []
    for fname, value in payload.items():
        if isinstance(value, str):
            errors.extend(_error(
                str(fname),
                "forbidden_term",
                f"contains forbidden term: '{term}'",
            ) for term in DOMAIN_FORBIDDEN_TERMS if term in value)
    return errors


def _check_absolute_phrases(
    payload: dict[str, object],
) -> list[dict[str, str]]:
    """Check all string values for absolute marketing phrases."""
    errors: list[dict[str, str]] = []
    for fname, value in payload.items():
        if isinstance(value, str):
            found = _ABSOLUTE_PATTERN.search(value)
            if found:
                errors.append(_error(
                    str(fname),
                    "absolute_marketing_term",
                    f"contains absolute marketing term: '{found.group()}'",
                ))
    return errors


def _check_forbidden_actions(
    payload: dict[str, object],
) -> list[dict[str, str]]:
    """Check for forbidden action keys."""
    errors: list[dict[str, str]] = []
    errors.extend(_error(
        action,
        "forbidden_action",
        f"product-operations must not include '{action}'",
    ) for action in FORBIDDEN_ACTION_KEYS if action in payload)
    return errors


def _check_required_fields(
    payload: dict[str, object],
) -> list[dict[str, str]]:
    """Check that all required fields are present and non-empty."""
    errors: list[dict[str, str]] = []
    for fname in REQUIRED_FIELDS:
        value = payload.get(fname)
        if value is None:
            errors.append(_error(fname, "missing", f"missing required field: '{fname}'"))
        elif isinstance(value, str) and len(value.strip()) == 0:
            errors.append(_error(fname, "empty_field", f"field '{fname}' is empty"))
    return errors


def _check_capabilities(
    payload: dict[str, object],
) -> list[dict[str, str]]:
    """Validate AI Vision capability list structure and MVP gating.

    Rules:
    - capabilities must be a list of dicts with 'name' and 'status'
    - Only AI_VISION_MVP_CAPABILITIES may have status=mvp
    - All other capabilities must have status=roadmap
    """
    errors: list[dict[str, str]] = []
    caps = payload.get("capabilities")
    if not isinstance(caps, list):
        errors.append(_error(
            "capabilities", "invalid_type",
            "capabilities must be a list",
        ))
        return errors

    for idx, cap in enumerate(cast("list[object]", caps)):
        cap_field = f"capabilities[{idx}]"
        if not isinstance(cap, dict):
            errors.append(_error(cap_field, "invalid_type", "each capability must be a dict"))
            continue

        cap_dict: dict[str, object] = cast("dict[str, object]", cap)

        if "name" not in cap_dict:
            errors.append(_error(cap_field, "missing", f"capability {idx} missing 'name'"))
            continue

        cap_name = str(cap_dict["name"])
        cap_status = str(cap_dict.get("status", ""))

        if cap_name in AI_VISION_MVP_CAPABILITIES:
            if cap_status != "mvp":
                errors.append(_error(
                    cap_field,
                    "invalid_capability_status",
                    f"MVP capability '{cap_name}' must have status='mvp'",
                ))
        elif cap_status == "mvp":
            errors.append(_error(
                cap_field,
                "invalid_capability_status",
                f"non-MVP capability '{cap_name}' must have status='roadmap', not 'mvp'",
            ))
    return errors


def _check_client_authorized(
    payload: dict[str, object],
) -> list[dict[str, str]]:
    """Verify client_authorized is present and True."""
    errors: list[dict[str, str]] = []
    authorized = payload.get("client_authorized")
    if authorized is not True:
        errors.append(_error(
            "client_authorized",
            "missing_or_false",
            "client_authorized must be True",
        ))
    return errors


def _check_execution_mode_isolation(
    payload: dict[str, object],
    *,
    execution_mode: str | None = None,
    is_fixture: bool,
) -> list[dict[str, str]]:
    """Reject payload self-declared execution_mode and enforce fixture mode."""
    errors: list[dict[str, str]] = []

    if "execution_mode" in payload:
        errors.append(_error(
            "execution_mode",
            "execution_mode_in_payload",
            "execution_mode must be provided by the caller, not declared in the payload",
        ))

    if is_fixture and execution_mode != SYNTHETIC_TEST_MODE:
        errors.append(_error(
            "fixture",
            "fixture_requires_synthetic_mode",
            "fixture=true is only allowed with execution_mode=synthetic-test (caller-provided)",
        ))

    return errors


@dataclass
class ValidationResult:
    """Structured result of validating one product payload."""

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


def validate_product_payload(
    payload: dict[str, object],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate a product payload.

    Args:
        payload: Raw decoded JSON dict.
            Must NOT contain ``execution_mode``.
        execution_mode: Caller-provided context kwarg only.

    Returns:
        ValidationResult with all errors, warnings, and check flags.

    """
    result = ValidationResult(valid=True)
    is_fixture = payload.get("fixture") is True

    # Collect errors from all checks
    check_errors: list[list[dict[str, str]]] = [
        _check_execution_mode_isolation(
            payload, execution_mode=execution_mode, is_fixture=is_fixture,
        ),
        _check_client_authorized(payload),
        _check_required_fields(payload),
        _check_domain_terms(payload),
        _check_absolute_phrases(payload),
        _check_forbidden_actions(payload),
        _check_capabilities(payload),
    ]

    all_errors: list[dict[str, str]] = []
    for errs in check_errors:
        all_errors.extend(errs)
        result.errors.extend(errs)

    if all_errors:
        result.valid = False

    error_codes = {e["code"] for e in result.errors}
    result.checks = {
        "field_completeness": not error_codes & {
            "missing", "empty_field", "invalid_type",
        },
        "client_authorized": "missing_or_false" not in error_codes,
        "forbidden_terms": "forbidden_term" not in error_codes,
        "absolute_terms": "absolute_marketing_term" not in error_codes,
        "no_forbidden_actions": "forbidden_action" not in error_codes,
        "fixture_mode_safe": "fixture_requires_synthetic_mode" not in error_codes,
        "no_payload_execution_mode": "execution_mode_in_payload" not in error_codes,
        "capability_gating": "invalid_capability_status" not in error_codes,
    }

    return result
