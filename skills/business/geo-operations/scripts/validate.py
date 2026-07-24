"""Canonical validation for geo-operations payloads.

Read-only audit skill for lnkwebsite GEO profile drift detection.
Validates GEO profile consistency, llms.txt content freshness, and
Baidu verification status.

Forbidden actions (this skill MUST NOT perform):
- auto_modify_llms_txt
- auto_publish_geo_content
- auto_submit_search_engine
- auto_modify_geo_profile

Forbidden content terms:
- CJK marketing jargon: specific domain spam phrases
- Absolute marketing superlatives
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final, cast

SYNTHETIC_TEST_MODE: Final = "synthetic-test"

FORBIDDEN_ACTION_KEYS: Final = (
    "auto_modify_llms_txt",
    "auto_publish_geo_content",
    "auto_submit_search_engine",
    "auto_modify_geo_profile",
)

#: CJK marketing jargon - precise multi-character patterns.
CJK_MARKETING_TERMS: Final = (
    "解决方案",
    "数字营销",
    "新零售",
    "新商业",
    "新营销",
    "新消费",
)

_CJK_PATTERN: Final = re.compile(
    "|".join(re.escape(t) for t in CJK_MARKETING_TERMS),
)

#: Absolute marketing superlatives - precise multi-character patterns.
#: Bare single characters like "最" would false-positive on "最近",
#: "最后", etc.  Each entry is a specific superlative claim.
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


def _error(field_name: str, code: str, message: str) -> dict[str, str]:
    """Build a single error dict."""
    return {"field": field_name, "code": code, "message": message}


def _warning(field_name: str, code: str, message: str) -> dict[str, str]:
    """Build a single warning dict."""
    return {"field": field_name, "code": code, "message": message}


def _extract_dict(
    payload: dict[str, object], key: str,
) -> dict[str, object] | None:
    """Safely extract a dict from payload by key."""
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    return None


def _extract_string_list(
    d: dict[str, object], key: str,
) -> list[str] | None:
    """Safely extract a list of strings from a dict."""
    value = d.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, str)]
    return None


def _check_baidu_verification(
    baidu: dict[str, object] | None,
) -> list[dict[str, str]]:
    """Validate Baidu verification fields."""
    errors: list[dict[str, str]] = []
    if baidu is None:
        errors.append(_error(
            "baidu_verification", "missing_baidu",
            "baidu_verification is required",
        ))
        return errors
    if baidu.get("status") != "verified":
        errors.append(_error(
            "baidu_verification.status", "not_verified",
            "Baidu verification must be verified",
        ))
    if "verified_date" not in baidu:
        errors.append(_error(
            "baidu_verification.verified_date", "missing_field",
            "verified_date is required",
        ))
    return errors


def _check_geo_profile(
    profile: dict[str, object] | None,
) -> list[dict[str, str]]:
    """Validate GEO profile required fields."""
    errors: list[dict[str, str]] = []
    if profile is None:
        errors.append(_error(
            "geo_profile", "missing_field", "geo_profile is required",
        ))
        return errors
    required_keys = ("name", "description", "capabilities", "contact_email", "website")
    errors.extend([
        _error(f"geo_profile.{key}", "missing_field", f"geo_profile.{key} is required")
        for key in required_keys
        if key not in profile
    ])
    caps = profile.get("capabilities")
    if caps is not None and not isinstance(caps, list):
        errors.append(_error(
            "geo_profile.capabilities", "invalid_type",
            "capabilities must be a list",
        ))
    return errors


def _check_llms_txt(
    llms: dict[str, object] | None,
    capabilities: list[str] | None,
) -> list[dict[str, str]]:
    """Validate llms.txt freshness and capability consistency."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    if llms is None:
        errors.append(_error(
            "llms_txt", "missing_field", "llms_txt is required",
        ))
        return errors
    if "last_updated" not in llms:
        errors.append(_error(
            "llms_txt.last_updated", "missing_field",
            "llms_txt.last_updated is required",
        ))
    if "content_lines" not in llms:
        errors.append(_error(
            "llms_txt.content_lines", "missing_field",
            "content_lines is required",
        ))
    caps = capabilities or []
    cap_pages = llms.get("capability_pages")
    if cap_pages is not None and isinstance(cap_pages, list):
        page_slugs = {
            cast("str", page.get("slug", ""))
            for page in cap_pages
            if isinstance(page, dict)
        }
        missing_caps = set(caps) - page_slugs
        if missing_caps:
            warnings.append(_warning(
                "llms_txt.capability_pages", "capability_drift",
                f"Capabilities without pages: {sorted(missing_caps)}",
            ))
    return errors + warnings


def _check_forbidden_actions(
    payload: dict[str, object],
) -> list[dict[str, str]]:
    """Reject any forbidden action keys in payload."""
    return [
        _error(action, "forbidden_action", f"geo-operations must not include '{action}'")
        for action in FORBIDDEN_ACTION_KEYS
        if action in payload
    ]


def _scan_string_for_terms(text: str, field_name: str) -> list[dict[str, str]]:
    """Check a single string for forbidden CJK and absolute terms."""
    errors: list[dict[str, str]] = []
    found_cjk = _CJK_PATTERN.search(text)
    if found_cjk:
        errors.append(_error(
            field_name, "forbidden_term",
            f"contains forbidden marketing term: '{found_cjk.group()}'",
        ))
    found_abs = _ABSOLUTE_PATTERN.search(text)
    if found_abs:
        errors.append(_error(
            field_name, "absolute_marketing_term",
            f"contains absolute marketing term: '{found_abs.group()}'",
        ))
    return errors


def _check_forbidden_terms(
    payload: dict[str, object],
) -> list[dict[str, str]]:
    """Reject CJK marketing jargon and absolute superlatives.

    Recursively scans all string values in the payload, including
    nested dicts and lists.
    """
    errors: list[dict[str, str]] = []

    def _walk(obj: object, path: str) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                _walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                _walk(item, f"{path}[{idx}]")
        elif isinstance(obj, str):
            errors.extend(_scan_string_for_terms(obj, path))

    _walk(payload, "")
    return errors


def _check_execution_mode(
    payload: dict[str, object],
    execution_mode: str | None,
) -> list[dict[str, str]]:
    """Reject payload self-declared execution_mode."""
    errors: list[dict[str, str]] = []
    if "execution_mode" in payload:
        errors.append(_error(
            "execution_mode", "execution_mode_in_payload",
            "execution_mode must be caller-provided, not in payload",
        ))
    is_fixture = payload.get("fixture") is True
    if is_fixture and execution_mode != SYNTHETIC_TEST_MODE:
        errors.append(_error(
            "fixture", "fixture_requires_synthetic_mode",
            "fixture=true only allowed with execution_mode=synthetic-test",
        ))
    return errors


@dataclass
class ValidationResult:
    """Structured result of validating one GEO payload."""

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


def validate_geo_payload(
    payload: dict[str, object],
    *,
    execution_mode: str | None = None,
) -> ValidationResult:
    """Validate a GEO operations payload.

    Args:
        payload: Raw decoded JSON dict.
            Must NOT contain ``execution_mode``.
        execution_mode: Caller-provided context kwarg only.

    Returns:
        ValidationResult with all errors, warnings, and check flags.

    """
    result = ValidationResult(valid=True)

    baidu = _extract_dict(payload, "baidu_verification")
    profile = _extract_dict(payload, "geo_profile")
    llms = _extract_dict(payload, "llms_txt")
    capabilities = (
        _extract_string_list(profile, "capabilities") if profile else None
    )

    result.errors.extend(_check_execution_mode(payload, execution_mode))
    result.errors.extend(_check_forbidden_actions(payload))
    result.errors.extend(_check_forbidden_terms(payload))
    result.errors.extend(_check_baidu_verification(baidu))
    result.errors.extend(_check_geo_profile(profile))

    llms_results = _check_llms_txt(llms, capabilities)
    for item in llms_results:
        target = result.errors if item.get("code", "").startswith("missing") else result.warnings
        target.append(item)

    if result.errors:
        result.valid = False

    error_codes = {e["code"] for e in result.errors}
    result.checks = {
        "baidu_verified": "not_verified" not in error_codes and "missing_baidu" not in error_codes,
        "geo_profile_complete": "missing_field" not in {
            e["code"] for e in result.errors if e["field"].startswith("geo_profile")
        },
        "llms_txt_fresh": "missing_field" not in {
            e["code"] for e in result.errors if e["field"].startswith("llms_txt")
        },
        "no_forbidden_terms": "forbidden_term" not in error_codes,
        "absolute_terms": "absolute_marketing_term" not in error_codes,
        "no_forbidden_actions": "forbidden_action" not in error_codes,
        "fixture_mode_safe": "fixture_requires_synthetic_mode" not in error_codes,
        "no_payload_execution_mode": "execution_mode_in_payload" not in error_codes,
    }

    return result
