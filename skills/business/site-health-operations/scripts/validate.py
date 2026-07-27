"""Canonical validation for site-health-operations payloads.

READ-ONLY audit skill.  Validates health-check payloads for correctness
and safety.  Forbidden actions (auto-restart, nginx/systemd/cron/iptables
modification) are rejected with error codes.  Absolute marketing phrases
and banned CJK buzzwords are also caught.

Security model:
- ``execution_mode`` is caller-only, never declared in the payload.
- ``fixture=true`` requires ``execution_mode=synthetic-test``.
- All MCP tools are read-only by definition; validation ensures no
  write-action keys sneak into the payload.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

# --- Resource percentage bounds ---

RESOURCE_PERCENT_MAX: Final = 100

# --- Forbidden action keys (auto-fix / system-modification intents) ---

FORBIDDEN_ACTION_KEYS: Final = (
    "auto_restart_service",
    "auto_modify_nginx",
    "auto_modify_systemd",
    "auto_modify_cron",
    "auto_modify_iptables",
    "auto_send_alert",
)

# --- Banned CJK buzzword terms ---

BANNED_CJK_TERMS: Final = (
    "\u89e3\u51b3\u65b9\u6848",  # 解决方案
    "\u6570\u5b57\u8425\u9500",  # 数字营销
    "\u65b0\u96f6\u552e",          # 新零售
    "\u65b0\u5546\u4e1a",          # 新商业
    "\u65b0\u8425\u9500",          # 新营销
    "\u65b0\u6d88\u8d39",          # 新消费
)

_BANNED_CJK_PATTERN: Final = re.compile(
    "|".join(re.escape(t) for t in BANNED_CJK_TERMS),
)

# --- Absolute marketing phrases (multi-character, no bare single char) ---

ABSOLUTE_PHRASES: Final = (
    "\u6700\u9886\u5148",      # 最领先
    "\u6700\u4f18\u79c0",      # 最优秀
    "\u6700\u5927",            # 最大
    "\u6700\u5c0f",            # 最小
    "\u6700\u597d",            # 最好
    "\u6700\u5dee",            # 最差
    "\u6700\u5f3a",            # 最强
    "\u6700\u5f31",            # 最弱
    "\u6700\u4f18",            # 最优
    "\u6700\u5148\u8fdb",      # 最先进
    "\u6700\u5177",            # 最具
    "\u6700\u5b8c\u5584",      # 最完善
    "\u6700\u4e13\u4e1a",      # 最专业
    "\u6700\u6743\u5a01",      # 最权威
    "\u6700\u4e30\u5bcc",      # 最丰富
    "\u6700\u5168\u9762",      # 最全面
    "\u9996\u4e2a",            # 首个
    "\u9996\u5bb6",            # 首家
    "\u9996\u5c48\u4e00\u6307", # 首屈一指
    "\u552f\u4e00",            # 唯一
    "\u72ec\u5bb6",            # 独家
    "\u65e0\u4e0e\u4f26\u6bd4", # 无与伦比
    "\u9065\u9065\u9886\u5148", # 遥遥领先
    "\u884c\u4e1a\u7b2c\u4e00", # 行业第一
    "\u5168\u56fd\u7b2c\u4e00", # 全国第一
    "\u5168\u7403\u7b2c\u4e00", # 全球第一
)

_ABSOLUTE_PATTERN: Final = re.compile(
    "|".join(re.escape(p) for p in ABSOLUTE_PHRASES),
)

# --- Required top-level payload keys ---

REQUIRED_KEYS: Final = (
    "check_date",
    "services",
    "endpoints",
    "resources",
)

# --- Required service sub-fields per service ---

REQUIRED_SERVICE_FIELDS: Final = ("status", "uptime_hours", "main_pid")

# --- Valid service statuses ---

VALID_STATUSES: Final = ("active", "inactive", "failed", "restarting")

# --- Required endpoint sub-fields ---

REQUIRED_ENDPOINT_FIELDS: Final = ("http_code",)

# --- Required resource sub-fields ---

REQUIRED_RESOURCE_FIELDS: Final = (
    "disk_used_percent",
    "memory_used_percent",
    "swap_used_percent",
)


# --- Result type ---

@dataclass
class ValidationResult:
    """Structured result of validating one health-check payload."""

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


# --- Helpers ---


def _error(field_name: str, code: str, message: str) -> dict[str, str]:
    """Build a single error dict."""
    return {"field": field_name, "code": code, "message": message}


def _warn(field_name: str, code: str, message: str) -> dict[str, str]:
    """Build a single warning dict."""
    return {"field": field_name, "code": code, "message": message}


def _check_forbidden_actions(
    payload: dict[str, object],
    errors: list[dict[str, str]],
) -> bool:
    """Reject any forbidden auto-action keys in the payload."""
    clean = True
    for action in FORBIDDEN_ACTION_KEYS:
        if action in payload:
            errors.append(_error(
                action,
                "forbidden_action",
                f"site-health-operations must not include '{action}'",
            ))
            clean = False
    return clean


def _iter_string_values(
    obj: object,
    prefix: str = "",
) -> tuple[str, str]:
    """Yield (dotted_path, string_value) for every string in a nested dict."""
    if isinstance(obj, str):
        yield prefix, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            child = f"{prefix}.{k}" if prefix else str(k)
            yield from _iter_string_values(v, child)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            child = f"{prefix}[{i}]" if prefix else f"[{i}]"
            yield from _iter_string_values(v, child)


def _check_banned_cjk_terms(
    payload: dict[str, object],
    errors: list[dict[str, str]],
) -> bool:
    """Scan all string values (deeply nested) for banned CJK buzzword terms."""
    clean = True
    for path, text in _iter_string_values(payload):
        match = _BANNED_CJK_PATTERN.search(text)
        if match:
            errors.append(_error(
                path,
                "banned_cjk_term",
                f"contains banned CJK term: '{match.group()}'",
            ))
            clean = False
    return clean


def _check_absolute_phrases(
    payload: dict[str, object],
    errors: list[dict[str, str]],
) -> bool:
    """Scan all string values (deeply nested) for absolute marketing phrases."""
    clean = True
    for path, text in _iter_string_values(payload):
        match = _ABSOLUTE_PATTERN.search(text)
        if match:
            errors.append(_error(
                path,
                "absolute_marketing_term",
                f"contains absolute marketing term: '{match.group()}'",
            ))
            clean = False
    return clean


def _check_required_keys(
    payload: dict[str, object],
    errors: list[dict[str, str]],
) -> bool:
    """Verify required top-level keys are present."""
    clean = True
    for key in REQUIRED_KEYS:
        if key not in payload:
            errors.append(_error(
                key,
                "missing_field",
                f"required field '{key}' is missing",
            ))
            clean = False
    return clean


def _check_services_structure(
    payload: dict[str, object],
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> bool:
    """Validate the services dict structure."""
    services = payload.get("services")
    if not isinstance(services, dict):
        if services is not None:
            errors.append(_error(
                "services", "invalid_type",
                "'services' must be a dict",
            ))
        return services is not None

    clean = True
    if len(services) == 0:
        warnings.append(_warn(
            "services", "empty_services",
            "'services' dict is empty",
        ))

    for svc_name, svc_data in services.items():
        if not isinstance(svc_data, dict):
            errors.append(_error(
                f"services.{svc_name}",
                "invalid_type",
                f"service '{svc_name}' must be a dict",
            ))
            clean = False
            continue
        for sf in REQUIRED_SERVICE_FIELDS:
            if sf not in svc_data:
                errors.append(_error(
                    f"services.{svc_name}.{sf}",
                    "missing_field",
                    f"service '{svc_name}' missing required field '{sf}'",
                ))
                clean = False
            else:
                val = svc_data[sf]
                if sf == "status" and isinstance(val, str) and val not in VALID_STATUSES:
                    errors.append(_error(
                        f"services.{svc_name}.status",
                        "invalid_value",
                        f"invalid status '{val}' for service '{svc_name}'",
                    ))
                    clean = False
    return clean


def _check_endpoints_structure(
    payload: dict[str, object],
    errors: list[dict[str, str]],
) -> bool:
    """Validate the endpoints dict structure."""
    endpoints = payload.get("endpoints")
    if not isinstance(endpoints, dict):
        if endpoints is not None:
            errors.append(_error(
                "endpoints", "invalid_type",
                "'endpoints' must be a dict",
            ))
        return endpoints is not None

    clean = True
    for ep_name, ep_data in endpoints.items():
        if not isinstance(ep_data, dict):
            errors.append(_error(
                f"endpoints.{ep_name}",
                "invalid_type",
                f"endpoint '{ep_name}' must be a dict",
            ))
            clean = False
            continue
        for ef in REQUIRED_ENDPOINT_FIELDS:
            if ef not in ep_data:
                errors.append(_error(
                    f"endpoints.{ep_name}.{ef}",
                    "missing_field",
                    f"endpoint '{ep_name}' missing required field '{ef}'",
                ))
                clean = False
    return clean


def _check_resources_structure(
    payload: dict[str, object],
    errors: list[dict[str, str]],
) -> bool:
    """Validate the resources dict structure."""
    resources = payload.get("resources")
    if not isinstance(resources, dict):
        if resources is not None:
            errors.append(_error(
                "resources", "invalid_type",
                "'resources' must be a dict",
            ))
        return resources is not None

    clean = True
    for rf in REQUIRED_RESOURCE_FIELDS:
        if rf not in resources:
            errors.append(_error(
                f"resources.{rf}",
                "missing_field",
                f"required resource field '{rf}' is missing",
            ))
            clean = False
        else:
            val = resources[rf]
            if isinstance(val, (int, float)) and not (0 <= val <= RESOURCE_PERCENT_MAX):
                    errors.append(_error(
                        f"resources.{rf}",
                        "out_of_range",
                        f"resource '{rf}' value {val} is not in 0-100",
                    ))
                    clean = False
    return clean


# --- Public API ---


def validate_health_payload(
    payload: dict[str, object],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate a site-health payload.

    Args:
        payload: Raw decoded JSON health-check dict.
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
            "execution_mode must be provided by the caller, "
            "not declared in the payload",
        ))
        result.valid = False

    # 2. Fixture mode isolation
    if is_fixture and execution_mode != SYNTHETIC_TEST_MODE:
        result.errors.append(_error(
            "fixture",
            "fixture_requires_synthetic_mode",
            "fixture=true is only allowed with "
            "execution_mode=synthetic-test (caller-provided)",
        ))
        result.valid = False

    # 3. Forbidden auto-action keys
    _check_forbidden_actions(payload, result.errors)

    # 4. Banned CJK terms
    _check_banned_cjk_terms(payload, result.errors)

    # 5. Absolute marketing phrases
    _check_absolute_phrases(payload, result.errors)

    # 6. Required top-level keys
    _check_required_keys(payload, result.errors)

    # 7. Structure: services
    _check_services_structure(
        payload, result.errors, result.warnings,
    )

    # 8. Structure: endpoints
    _check_endpoints_structure(payload, result.errors)

    # 9. Structure: resources
    _check_resources_structure(payload, result.errors)

    # Update overall validity
    if result.errors:
        result.valid = False

    # Build check summary flags
    error_codes = {e["code"] for e in result.errors}
    result.checks = {
        "no_forbidden_actions": "forbidden_action" not in error_codes,
        "no_banned_cjk_terms": "banned_cjk_term" not in error_codes,
        "no_absolute_terms": "absolute_marketing_term" not in error_codes,
        "required_fields_present": "missing_field" not in error_codes,
        "structure_valid": "invalid_type" not in error_codes,
        "resource_ranges_valid": "out_of_range" not in error_codes,
        "status_values_valid": "invalid_value" not in error_codes,
        "fixture_mode_safe": (
            "fixture_requires_synthetic_mode" not in error_codes
        ),
        "no_payload_execution_mode": (
            "execution_mode_in_payload" not in error_codes
        ),
    }

    return result
