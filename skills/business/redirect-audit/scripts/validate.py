"""Canonical validation for redirect-audit payloads.

READ-ONLY audit skill. Validates redirect drift reports and fixture
payloads. Enforces:

- Forbidden action rejection (auto_create / auto_modify / etc.)
- Forbidden term rejection (marketing jargon)
- Read-only MCP enforcement (no write tools allowed)
- Fixture mode isolation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final, cast

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

#: Forbidden actions - redirect-audit must NEVER attempt these.
FORBIDDEN_ACTION_KEYS: Final = (
    "auto_create_redirect",
    "auto_modify_redirect",
    "auto_enable_redirect",
    "auto_disable_redirect",
    "auto_modify_nginx",
    "sitemap_write",
)

#: Forbidden CJK marketing terms.
FORBIDDEN_CJK_TERMS: Final = (
    "解决方案",
    "数字营销",
    "新零售",
    "新商业",
    "新营销",
    "新消费",
)

#: Absolute marketing phrases - precise multi-character patterns.
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

_CJK_TERM_PATTERN: Final = re.compile(
    "|".join(re.escape(t) for t in FORBIDDEN_CJK_TERMS),
)

_ABSOLUTE_PATTERN: Final = re.compile(
    "|".join(re.escape(p) for p in ABSOLUTE_PHRASES),
)

VALID_AUDIT_SCOPES: Final = frozenset({
    "db-only",
    "nginx-only",
    "online-only",
    "cross-check",
})

#: Read-only MCP tools that redirect-audit may call.
ALLOWED_MCP_TOOLS: Final = frozenset({
    "redirect_list",
    "redirect_get",
    "url_check",
})

#: Write tools that redirect-audit must NEVER call.
FORBIDDEN_MCP_TOOLS: Final = frozenset({
    "redirect_create",
    "redirect_update",
    "redirect_enable",
    "redirect_disable",
    "redirect_delete",
    "nginx_write",
    "nginx_modify",
    "sitemap_write",
})


@dataclass
class ValidationResult:
    """Structured result of validating one redirect-audit payload."""

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


def _warn(field: str, code: str, message: str) -> dict[str, str]:
    """Build a single warning dict."""
    return {"field": field, "code": code, "message": message}


def _check_forbidden_actions(payload: dict[str, object], result: ValidationResult) -> None:
    """Check payload for forbidden action keys."""
    for action in FORBIDDEN_ACTION_KEYS:
        if action in payload:
            result.errors.append(_error(
                action,
                "forbidden_action",
                f"redirect-audit must not include '{action}'",
            ))
            result.valid = False


def _check_forbidden_cjk_terms(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Check all string values for forbidden CJK marketing terms."""
    for fname, value in payload.items():
        if isinstance(value, str):
            found = _CJK_TERM_PATTERN.search(value)
            if found:
                result.errors.append(_error(
                    str(fname),
                    "forbidden_cjk_term",
                    f"contains forbidden term: '{found.group()}'",
                ))
                result.valid = False


def _check_absolute_phrases(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Check all string values for absolute marketing phrases."""
    for fname, value in payload.items():
        if isinstance(value, str):
            found = _ABSOLUTE_PATTERN.search(value)
            if found:
                result.errors.append(_error(
                    str(fname),
                    "absolute_marketing_term",
                    f"contains absolute marketing term: '{found.group()}'",
                ))
                result.valid = False


def _check_audit_scope(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Validate audit_scope if present."""
    scope = payload.get("audit_scope")
    if scope is None:
        return
    if isinstance(scope, str) and scope not in VALID_AUDIT_SCOPES:
        result.errors.append(_error(
            "audit_scope",
            "invalid_audit_scope",
            f"must be one of {sorted(VALID_AUDIT_SCOPES)}, got '{scope}'",
        ))
        result.valid = False


def _check_fixture_mode(
    payload: dict[str, object],
    execution_mode: str | None,
    result: ValidationResult,
) -> None:
    """Enforce fixture mode isolation."""
    is_fixture = payload.get("fixture") is True
    if is_fixture and execution_mode != SYNTHETIC_TEST_MODE:
        result.errors.append(_error(
            "fixture",
            "fixture_requires_synthetic_mode",
            "fixture=true is only allowed with execution_mode=synthetic-test",
        ))
        result.valid = False


def _check_payload_execution_mode(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Reject payload self-declared execution_mode."""
    if "execution_mode" in payload:
        result.errors.append(_error(
            "execution_mode",
            "execution_mode_in_payload",
            "execution_mode must be provided by the caller, not declared in the payload",
        ))
        result.valid = False


def _check_redirects_structure(
    payload: dict[str, object], result: ValidationResult,
) -> None:
    """Validate the redirects list structure if present."""
    redirects = payload.get("redirects")
    if redirects is None:
        return
    if not isinstance(redirects, list):
        result.errors.append(_error(
            "redirects",
            "invalid_redirects_type",
            "redirects must be a list",
        ))
        result.valid = False
        return
    required_keys = frozenset({
        "source_url", "db_status", "doc_status",
        "nginx_status", "online_status_code", "drift_type",
    })
    for idx, item in enumerate(redirects):
        if not isinstance(item, dict):
            result.errors.append(_error(
                f"redirects[{idx}]",
                "invalid_redirect_entry_type",
                f"redirects[{idx}] must be a dict",
            ))
            result.valid = False
            continue
        entry = cast(dict[str, object], item)
        entry_keys = set(entry.keys())
        missing = required_keys - entry_keys
        if missing:
            result.errors.append(_error(
                f"redirects[{idx}]",
                "missing_redirect_fields",
                f"redirects[{idx}] missing fields: {sorted(missing)}",
            ))
            result.valid = False


def _build_checks(result: ValidationResult) -> None:
    """Build the checks summary from collected errors."""
    error_codes = {e["code"] for e in result.errors}
    result.checks = {
        "forbidden_actions": "forbidden_action" not in error_codes,
        "forbidden_cjk_terms": "forbidden_cjk_term" not in error_codes,
        "absolute_terms": "absolute_marketing_term" not in error_codes,
        "audit_scope_valid": "invalid_audit_scope" not in error_codes,
        "fixture_mode_safe": "fixture_requires_synthetic_mode" not in error_codes,
        "no_payload_execution_mode": "execution_mode_in_payload" not in error_codes,
        "redirects_structure": "invalid_redirects_type" not in error_codes
            and "missing_redirect_fields" not in error_codes
            and "invalid_redirect_entry_type" not in error_codes,
    }


def validate_redirect_payload(
    payload: dict[str, object],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate a redirect-audit payload.

    Args:
        payload: Raw decoded JSON dict.
            Must NOT contain ``execution_mode``.
        execution_mode: Caller-provided context kwarg only.

    Returns:
        ValidationResult with all errors, warnings, and check flags.

    """
    result = ValidationResult(valid=True)

    _check_payload_execution_mode(payload, result)
    _check_fixture_mode(payload, execution_mode, result)
    _check_forbidden_actions(payload, result)
    _check_forbidden_cjk_terms(payload, result)
    _check_absolute_phrases(payload, result)
    _check_audit_scope(payload, result)
    _check_redirects_structure(payload, result)

    # Warn if notes contain marketing-adjacent language
    redirects = payload.get("redirects")
    if isinstance(redirects, list):
        for idx, item in enumerate(redirects):
            if isinstance(item, dict):
                entry = cast(dict[str, object], item)
                notes = entry.get("notes")
                if isinstance(notes, str) and "营销" in notes:
                    result.warnings.append(_warn(
                        f"redirects[{idx}].notes",
                        "marketing_adjacent_language",
                        "notes contains marketing-adjacent language",
                    ))

    _build_checks(result)
    return result
