"""Regression tests proving the content-ops shared parser is invoked.

These tests verify that validation errors originating from
``content-operations/scripts/case_payload.py`` (forbidden terms,
slug patterns, industry enums) actually surface through the
case-operations validator — proving the shared parser is called
at runtime, not shadowed by a local reimplementation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from validate import SYNTHETIC_TEST_MODE, validate_case_payload

_FIXTURE_BASE: dict[str, object] = {
    "slug": "case-ops-synthetic-fixture",
    "client_name": "星河智创中心（测试案例）",
    "industry": "office",
    "client_authorized": True,
    "fixture": True,
    "problem": "虚构场景：需要统一物业服务入口。",
    "solution": "虚构方案：部署智慧物业平台。",
    "outcome": "虚构结果：效率提升50%。",
    "testimonial": "虚构评价。",
    "seo_title": "测试",
    "seo_description": "fixture",
    "image": "/cases/test.webp",
    "product": "office-building",
}


def _base() -> dict[str, object]:
    return dict(_FIXTURE_BASE)


class TestSharedParserInvoked:
    """Regression: prove the content-ops parser is actually called at
    runtime, not shadowed by a local reimplementation."""

    def test_forbidden_term_surfaces_from_shared_parser(self) -> None:
        """'数字营销' is a content-ops forbidden term, not defined
        anywhere in case-operations.  If it surfaces, the shared
        parser was called."""
        p = _base()
        p["solution"] = "提供数字营销服务"
        r = validate_case_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        shared_errors = [
            e for e in r.errors
            if e["code"] == "forbidden_term"
        ]
        assert len(shared_errors) >= 1
        assert "数字营销" in shared_errors[0]["message"]

    def test_slug_pattern_from_shared_parser(self) -> None:
        """Slug pattern error ('string_pattern_mismatch') originates
        from content-ops, not case-operations."""
        p = _base()
        p["slug"] = "UPPERCASE-BAD"
        r = validate_case_payload(p, execution_mode=SYNTHETIC_TEST_MODE)
        assert "string_pattern_mismatch" in {e["code"] for e in r.errors}

    def test_industry_enum_from_shared_parser(self) -> None:
        """Industry enum validation lives in content-ops."""
        p = _base()
        p["industry"] = "nonexistent-industry"
        r = validate_case_payload(p, execution_mode=cast(str, SYNTHETIC_TEST_MODE))
        assert "enum" in {e["code"] for e in r.errors}

    def test_shared_parser_is_real_module(self) -> None:
        """The loader's parse_case_payload must come from the real
        content-operations package, not a local copy."""
        import content_ops_loader

        source_mod = getattr(content_ops_loader, "_runtime_mod", None)
        assert source_mod is not None
        source_file = getattr(source_mod, "__file__", None)
        assert source_file is not None
        assert "content-operations" in str(source_file), (
            f"expected content-operations in path, got: {source_file}"
        )
