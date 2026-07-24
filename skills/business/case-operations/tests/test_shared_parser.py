"""Regression tests proving the content-ops shared parser is invoked.

These tests verify that validation errors originating from
``content-operations/scripts/case_payload.py`` (forbidden terms,
slug patterns, industry enums) actually surface through the
case-operations validator — proving the shared parser is called
at runtime, not shadowed by a local reimplementation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from content_ops_loader import get_shared_parser_source
from validate import SYNTHETIC_TEST_MODE, validate_case_payload

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _base() -> dict[str, object]:
    """Return a copy of the synthetic fixture as a mutable dict."""
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


class TestSharedParserInvoked:
    """Regression: prove the content-ops parser is actually called."""

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
        r = validate_case_payload(p, execution_mode=cast("str", SYNTHETIC_TEST_MODE))
        assert "enum" in {e["code"] for e in r.errors}

    def test_shared_parser_is_real_module(self) -> None:
        """The loader's parse_case_payload must come from the real
        content-operations package, not a local copy."""
        source_file = get_shared_parser_source()
        assert source_file is not None
        assert "content-operations" in source_file, (
            f"expected content-operations in path, got: {source_file}"
        )
