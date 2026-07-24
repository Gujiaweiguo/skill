"""Canonical test suite for case-operations synthetic fixture.

Merges all negative, positive, and end-to-end scenarios from the
original two parallel implementations into one non-redundant suite.

Run:
    cd /opt/code/skill
    python3 -m pytest skills/business/case-operations/tests/test_case_operations.py -v
    # or standalone:
    python3 skills/business/case-operations/tests/test_case_operations.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(TESTS_DIR))

from validate import validate_case_payload, SYNTHETIC_TEST_MODE  # noqa: E402
from mock_mcp_server import MockMCPServer, MockMCPError  # noqa: E402

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_base() -> dict:
    """Return a valid synthetic-test payload that tests mutate."""
    return {
        "slug": "case-ops-synthetic-fixture",
        "client_name": "星河智创中心（测试案例）",
        "industry": "office",
        "client_authorized": True,
        "fixture": True,
        "execution_mode": "synthetic-test",
        "problem": "虚构场景：大厦管理方希望统一分散的物业服务入口。",
        "solution": "虚构方案：部署智慧物业服务平台。",
        "outcome": "虚构结果：报修响应时间缩短50%。",
        "testimonial": "虚构评价。",
        "seo_title": "测试fixture",
        "seo_description": "技术验证fixture",
        "image": "/cases/test.webp",
        "product": "office-building",
    }


def _validate(payload: dict, **kwargs) -> list[dict]:
    """Validate and return the errors list."""
    return validate_case_payload(payload, **kwargs).errors


# ---------------------------------------------------------------------------
# Negative: client_authorized fail-closed
# ---------------------------------------------------------------------------

class TestClientAuthorizedFailClosed:

    def test_missing_client_authorized(self):
        payload = _valid_base()
        del payload["client_authorized"]
        errors = _validate(payload, execution_mode=SYNTHETIC_TEST_MODE)
        assert any(e["code"] == "missing_or_false" for e in errors)

    def test_client_authorized_false(self):
        payload = _valid_base()
        payload["client_authorized"] = False
        errors = _validate(payload, execution_mode=SYNTHETIC_TEST_MODE)
        assert any(e["code"] == "missing_or_false" for e in errors)


# ---------------------------------------------------------------------------
# Negative: required fields missing
# ---------------------------------------------------------------------------

class TestRequiredFieldsMissing:

    @pytest.mark.parametrize("field_name", [
        "slug", "client_name", "industry", "problem", "solution", "outcome",
    ])
    def test_missing_field(self, field_name):
        payload = _valid_base()
        del payload[field_name]
        errors = _validate(payload, execution_mode=SYNTHETIC_TEST_MODE)
        assert any(e["code"] == "missing" for e in errors), (
            f"should fail when {field_name} is missing"
        )


# ---------------------------------------------------------------------------
# Negative: forbidden / absolute terms
# ---------------------------------------------------------------------------

class TestForbiddenAndAbsoluteTerms:

    def test_domain_forbidden_term(self):
        payload = _valid_base()
        payload["solution"] = "提供数字营销服务"
        errors = _validate(payload, execution_mode=SYNTHETIC_TEST_MODE)
        assert any(e["code"] == "forbidden_term" and "数字营销" in e["message"]
                   for e in errors)

    def test_absolute_marketing_term(self):
        payload = _valid_base()
        payload["outcome"] = "行业最领先的物业管理平台"
        errors = _validate(payload, execution_mode=SYNTHETIC_TEST_MODE)
        assert any(e["code"] == "absolute_marketing_term" and "最" in e["message"]
                   for e in errors)


# ---------------------------------------------------------------------------
# Negative: publish / unpublish / delete intent
# ---------------------------------------------------------------------------

class TestForbiddenActions:

    @pytest.mark.parametrize("action_key", [
        "publish", "unpublish", "delete",
    ])
    def test_forbidden_action_key(self, action_key):
        payload = _valid_base()
        payload[action_key] = True
        errors = _validate(payload, execution_mode=SYNTHETIC_TEST_MODE)
        assert any(e["code"] == "forbidden_action" for e in errors)


# ---------------------------------------------------------------------------
# Negative: fixture mode enforcement
# ---------------------------------------------------------------------------

class TestFixtureModeEnforcement:

    def test_fixture_without_execution_mode_fails(self):
        """fixture=true outside synthetic-test mode must fail closed."""
        payload = _valid_base()
        # Simulate production caller: no execution_mode passed
        errors = _validate(payload)  # execution_mode defaults to None
        assert any(e["code"] == "fixture_requires_synthetic_mode" for e in errors)

    def test_fixture_with_wrong_execution_mode_fails(self):
        payload = _valid_base()
        result = validate_case_payload(
            payload, execution_mode="production"
        )
        assert not result.valid
        assert any(e["code"] == "fixture_requires_synthetic_mode"
                   for e in result.errors)


# ---------------------------------------------------------------------------
# Negative: cross-validation with content-ops case_payload.py
# ---------------------------------------------------------------------------

class TestContentOpsCrossValidation:
    """Verify the shared case_payload.py also enforces fail-closed."""

    def test_content_ops_rejects_missing_authorized(self):
        from scripts.case_payload import parse_case_payload, PayloadValidationError
        payload = _valid_base()
        del payload["client_authorized"]
        with pytest.raises(PayloadValidationError) as exc_info:
            parse_case_payload(json.dumps(payload, ensure_ascii=False))
        codes = [i.code for i in exc_info.value.issues]
        assert "missing_or_false" in codes

    def test_content_ops_rejects_false_authorized(self):
        from scripts.case_payload import parse_case_payload, PayloadValidationError
        payload = _valid_base()
        payload["client_authorized"] = False
        with pytest.raises(PayloadValidationError) as exc_info:
            parse_case_payload(json.dumps(payload, ensure_ascii=False))
        codes = [i.code for i in exc_info.value.issues]
        assert "missing_or_false" in codes


# ---------------------------------------------------------------------------
# Positive: synthetic fixture
# ---------------------------------------------------------------------------

class TestSyntheticFixture:

    def test_fixture_passes_validation(self):
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        result = validate_case_payload(fixture, execution_mode=SYNTHETIC_TEST_MODE)
        assert result.valid, f"errors: {result.errors}"
        assert all(result.checks.values()), f"checks: {result.checks}"

    def test_fixture_markers(self):
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        assert fixture["fixture"] is True
        assert fixture["execution_mode"] == "synthetic-test"


# ---------------------------------------------------------------------------
# E2E: mock MCP + artifact generation
# ---------------------------------------------------------------------------

class TestEndToEnd:

    def test_e2e_full_flow(self):
        """fixture → validate → mock case_create → artifacts → verify."""
        # 1. Load fixture
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)

        # 2. Validate
        result = validate_case_payload(fixture, execution_mode=SYNTHETIC_TEST_MODE)
        assert result.valid, f"validation failed: {result.errors}"

        # 3. Mock MCP case_create
        mock = MockMCPServer()
        draft = mock.case_create(payload={
            "slug": fixture["slug"],
            "client_name": fixture["client_name"],
            "industry": fixture["industry"],
            "problem": fixture["problem"],
            "solution": fixture["solution"],
            "outcome": fixture["outcome"],
            "testimonial": fixture.get("testimonial"),
            "seo_title": fixture.get("seo_title"),
            "seo_description": fixture.get("seo_description"),
            "image": fixture.get("image"),
            "product": fixture.get("product"),
            "status": "draft",
        })
        assert draft["status"] == "draft"
        assert draft["id"] == "fixture-case-001"

        # 4. MCP call log: only case_create
        tools_called = mock.get_call_tools()
        assert tools_called == ["case_create"]
        mock.assert_no_forbidden_calls()

        # 5. Forbidden calls blocked
        for forbidden_tool in ("case_publish", "case_unpublish", "case_delete"):
            with pytest.raises(MockMCPError, match="FORBIDDEN"):
                mock.call(forbidden_tool, id=draft["id"])

        # 6. Generate 4 artifacts to temp dir
        artifact_dir = Path(tempfile.mkdtemp(prefix="case-ops-test-"))
        ts = time.time()

        # 6a. case-research-pack.md
        (artifact_dir / "case-research-pack.md").write_text(
            f"# Case Research Pack — {fixture['client_name']}\n\n"
            "> **FIXTURE**: Synthetic test data. No real client.\n\n"
            f"## Problem\n{fixture['problem']}\n\n"
            f"## Solution\n{fixture['solution']}\n\n"
            f"## Outcome\n{fixture['outcome']}\n",
            encoding="utf-8",
        )
        # 6b. case-payload.json
        (artifact_dir / "case-payload.json").write_text(
            json.dumps(fixture, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # 6c. validation-report.json
        report = {
            "skill": "case-operations",
            "skill_version": "0.1.0",
            "mode": "synthetic-test",
            "timestamp": ts,
            **result.to_dict(),
            "mcp_calls": tools_called,
            "forbidden_calls_detected": False,
        }
        (artifact_dir / "validation-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        # 6d. import-receipt.json
        receipt = {
            "skill": "case-operations",
            "fixture": True,
            "mcp_tool": "case_create",
            "draft_id": draft["id"],
            "draft_status": draft["status"],
            "timestamp": ts,
            "mcp_calls": tools_called,
            "forbidden_calls": [],
        }
        (artifact_dir / "import-receipt.json").write_text(
            json.dumps(receipt, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # 7. Verify artifact completeness
        for name in (
            "case-research-pack.md",
            "case-payload.json",
            "validation-report.json",
            "import-receipt.json",
        ):
            path = artifact_dir / name
            assert path.exists(), f"missing artifact: {name}"
            assert path.stat().st_size > 0, f"empty artifact: {name}"

    def test_no_real_mcp_calls(self):
        """The mock MCP server must be the only 'MCP' used."""
        mock = MockMCPServer()
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)
        mock.case_create(payload=fixture)
        # No real MCP was reachable — this is an in-process mock.
        assert mock.get_call_tools() == ["case_create"]


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Allow running without pytest: collect and run all test methods.
    import traceback

    test_classes = [
        TestClientAuthorizedFailClosed,
        TestRequiredFieldsMissing,
        TestForbiddenAndAbsoluteTerms,
        TestForbiddenActions,
        TestFixtureModeEnforcement,
        TestContentOpsCrossValidation,
        TestSyntheticFixture,
        TestEndToEnd,
    ]

    # Parametrize manually for standalone mode
    parametrize_fields = [
        "slug", "client_name", "industry", "problem", "solution", "outcome",
    ]
    parametrize_actions = ["publish", "unpublish", "delete"]

    total = 0
    passed = 0
    failed = 0

    for cls in test_classes:
        instance = cls()
        for name in dir(instance):
            if not name.startswith("test_"):
                continue
            method = getattr(instance, name)

            # Handle parametrized tests manually
            if name == "test_missing_field":
                for field_name in parametrize_fields:
                    total += 1
                    try:
                        method(field_name)
                        print(f"  ✅ PASS  {cls.__name__}.{name}[{field_name}]")
                        passed += 1
                    except Exception:
                        print(f"  ❌ FAIL  {cls.__name__}.{name}[{field_name}]")
                        traceback.print_exc()
                        failed += 1
                continue

            if name == "test_forbidden_action_key":
                for action_key in parametrize_actions:
                    total += 1
                    try:
                        method(action_key)
                        print(f"  ✅ PASS  {cls.__name__}.{name}[{action_key}]")
                        passed += 1
                    except Exception:
                        print(f"  ❌ FAIL  {cls.__name__}.{name}[{action_key}]")
                        traceback.print_exc()
                        failed += 1
                continue

            total += 1
            try:
                method()
                print(f"  ✅ PASS  {cls.__name__}.{name}")
                passed += 1
            except Exception:
                print(f"  ❌ FAIL  {cls.__name__}.{name}")
                traceback.print_exc()
                failed += 1

    print(f"\n{'=' * 60}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print(f"{'=' * 60}")
    sys.exit(1 if failed else 0)
