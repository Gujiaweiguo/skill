"""Tests for the main product-operations workflow.

Covers: PRD parsing, full pipeline (parse → validate → create draft →
artifacts), draft updates, product listing, CLI safety, and
artifact-dir enforcement.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from scripts.product_ops import (
    VALID_PRODUCT_CATEGORIES,
    ArtifactDirError,
    ProductOpsRunner,
    _parse_capability_line,
    _slugify,
    parse_prd,
)
from scripts.validate import SYNTHETIC_TEST_MODE
from tests.mock_mcp_server import MockMCPServer

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _load_fixture() -> dict[str, object]:
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


# ---------------------------------------------------------------------------
# PRD Parser tests
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic(self) -> None:
        assert _slugify("AI Vision System") == "ai-vision-system"

    def test_special_chars(self) -> None:
        assert _slugify("AI Vision! @System #1") == "ai-vision-system-1"

    def test_empty(self) -> None:
        assert _slugify("") == "untitled"

    def test_chinese(self) -> None:
        assert _slugify("智能视觉系统") == "智能视觉系统"

    def test_collapse_dashes(self) -> None:
        assert _slugify("a---b") == "a-b"


class TestParseCapabilityLine:
    def test_paren_mvp(self) -> None:
        result = _parse_capability_line("- 通道拥堵检测 (mvp)")
        assert result == {"name": "通道拥堵检测", "status": "mvp"}

    def test_paren_roadmap(self) -> None:
        result = _parse_capability_line("- 设备预测维护 (roadmap)")
        assert result == {"name": "设备预测维护", "status": "roadmap"}

    def test_bracket_prefix(self) -> None:
        result = _parse_capability_line("- [MVP] 火灾烟雾识别")
        assert result == {"name": "火灾烟雾识别", "status": "mvp"}

    def test_bracket_suffix(self) -> None:
        result = _parse_capability_line("- 人员行为分析 [roadmap]")
        assert result == {"name": "人员行为分析", "status": "roadmap"}

    def test_bold_em_dash(self) -> None:
        result = _parse_capability_line("- **地面脏污识别** — MVP")
        assert result == {"name": "地面脏污识别", "status": "mvp"}

    def test_default_roadmap(self) -> None:
        result = _parse_capability_line("- 某新功能")
        assert result == {"name": "某新功能", "status": "roadmap"}

    def test_empty_line(self) -> None:
        assert _parse_capability_line("") is None

    def test_whitespace_only(self) -> None:
        assert _parse_capability_line("   ") is None

    def test_checkbox_format(self) -> None:
        result = _parse_capability_line("- [x] 已完成功能 (roadmap)")
        assert result is not None
        assert result["status"] == "roadmap"


class TestParsePRD:
    def test_full_prd(self) -> None:
        prd = """\
# AI Vision System

- **slug**: ai-vision-system
- **category**: ai_vision
- **vendor**: TechCorp

## Short Description

AI-powered vision analytics for retail.

## Description

Comprehensive computer vision platform for retail intelligence,
including customer traffic analysis and safety monitoring.

## Capabilities

- 通道拥堵检测 (mvp)
- 火灾烟雾识别 (mvp)
- 地面脏污识别 (mvp)
- 人员行为分析 (roadmap)
- 设备预测维护 (roadmap)
"""
        result = parse_prd(prd)
        assert result.product_name == "AI Vision System"
        assert result.slug == "ai-vision-system"
        assert result.category == "ai_vision"
        assert result.vendor == "TechCorp"
        assert "AI-powered vision analytics" in result.short_description
        assert "Comprehensive computer vision" in result.description
        assert len(result.capabilities) == 5
        assert result.capabilities[0] == {"name": "通道拥堵检测", "status": "mvp"}
        assert result.capabilities[3] == {"name": "人员行为分析", "status": "roadmap"}

    def test_auto_slug_from_title(self) -> None:
        prd = """\
# Smart Retail Analytics

## Description

Some description.
"""
        result = parse_prd(prd)
        assert result.slug == "smart-retail-analytics"
        assert any("auto-generated" in w for w in result.parse_warnings)

    def test_missing_title(self) -> None:
        prd = "Just some text without a title."
        result = parse_prd(prd)
        assert result.product_name == ""
        assert any("No H1" in w for w in result.parse_warnings)

    def test_invalid_category_warns(self) -> None:
        prd = """\
# Test Product

- **category**: fake_category

## Description

Test.
"""
        result = parse_prd(prd)
        assert result.category == "fake_category"
        assert any("not in valid set" in w for w in result.parse_warnings)

    def test_to_payload(self) -> None:
        prd = """\
# Test

- **slug**: test
- **category**: other
- **vendor**: VendorInc

## Description

Description text.
"""
        result = parse_prd(prd)
        payload = result.to_payload()
        assert payload["product_name"] == "Test"
        assert payload["slug"] == "test"
        assert payload["category"] == "other"
        assert payload["vendor"] == "VendorInc"

    def test_valid_categories_constant(self) -> None:
        assert "ai_vision" in VALID_PRODUCT_CATEGORIES
        assert "other" in VALID_PRODUCT_CATEGORIES


# ---------------------------------------------------------------------------
# ProductOpsRunner.run() — full pipeline
# ---------------------------------------------------------------------------


class TestRunPipelineArtifacts:
    def test_generates_four_artifacts(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert result.valid
            assert set(result.artifact_paths) == {
                "product-research-pack.md",
                "product-payload.json",
                "import-receipt.json",
                "validation-report.json",
            }
            for name, path in result.artifact_paths.items():
                assert path.exists(), f"missing: {name}"
                assert path.stat().st_size > 0, f"empty: {name}"

    def test_artifact_content(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert result.valid

            receipt = json.loads(
                (Path(tmp) / "import-receipt.json").read_text(),
            )
            report = json.loads(
                (Path(tmp) / "validation-report.json").read_text(),
            )
            payload = json.loads(
                (Path(tmp) / "product-payload.json").read_text(),
            )
            research = (Path(tmp) / "product-research-pack.md").read_text()

        assert receipt["draft_status"] == "draft"
        assert receipt["mcp_tool"] == "product_create"
        assert report["mode"] == SYNTHETIC_TEST_MODE
        assert report["skill"] == "product-operations"
        assert payload["slug"] == fixture["slug"]
        assert "Product Research Pack" in research

    def test_research_pack_has_vendor(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert result.valid
            research = (Path(tmp) / "product-research-pack.md").read_text()
        assert "SyntheticTech" in research


class TestRunPipelineMCPSafety:
    def test_only_calls_product_create(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert result.valid
        assert mock.get_call_tools() == ["product_create"]

    def test_no_forbidden_calls(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert result.valid
        mock.assert_no_forbidden_calls()

    def test_zero_real_mcp(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert result.valid
        assert len(mock.calls) == 1
        assert mock.calls[0].tool == "product_create"

    def test_draft_status_is_draft(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert result.valid
            assert result.draft_status == "draft"


class TestRunPipelineValidation:
    def test_invalid_payload_returns_invalid(self) -> None:
        fixture = _load_fixture()
        del fixture["slug"]
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert not result.valid
            assert any("missing" in e for e in result.errors)

    def test_forbidden_term_rejected(self) -> None:
        fixture = _load_fixture()
        fixture["description"] = "这是一个解决方案平台"
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert not result.valid

    def test_no_mcp_call_when_invalid(self) -> None:
        fixture = _load_fixture()
        del fixture["product_name"]
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert not result.valid
            assert mock.get_call_tools() == []


class TestRunPipelineNonDraftStatus:
    def test_rejects_non_draft_status(self) -> None:
        """If MCP returns a non-draft status, runner should flag it."""
        fixture = _load_fixture()
        mock = MockMCPServer()
        # Tamper with mock to return published status

        def bad_create(payload: dict[str, object]) -> dict[str, object]:
            # Record the call properly then return bad status
            mock.calls.append(type(mock.calls[0])(
                tool="product_create",
                arguments=dict(payload),
                timestamp=__import__("time").time(),
                result={"id": "bad-001", "status": "published"},
            )) if mock.calls else None
            return {"id": "bad-001", "status": "published"}

        mock.product_create = bad_create  # type: ignore[method-assign]
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert not result.valid
            assert any("published" in e for e in result.errors)



class TestUpdateDraft:
    def test_update_existing_draft(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        # Create a draft first
        draft = mock.product_create(
            {k: v for k, v in fixture.items() if k != "fixture"},
        )
        product_id = draft["id"]
        # Update it
        updated = runner.update_draft(product_id, {"short_description": "Updated"}, mock)
        assert updated["short_description"] == "Updated"

    def test_update_nonexistent_raises(self) -> None:
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with pytest.raises(ValueError, match="not found"):
            runner.update_draft("nonexistent-id", {"description": "x"}, mock)



class TestListProducts:
    def test_empty_list(self) -> None:
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        products = runner.list_products(mock)
        assert products == []

    def test_after_create(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        mock.product_create({k: v for k, v in fixture.items() if k != "fixture"})
        products = runner.list_products(mock)
        assert len(products) == 1
        assert products[0]["status"] == "draft"


# ---------------------------------------------------------------------------
# Artifact dir safety
# ---------------------------------------------------------------------------


class TestArtifactDirSafety:
    def test_rejects_home_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            runner.run(fixture, mock, Path.home() / "prod-ops-out")
        assert mock.get_call_tools() == []

    def test_rejects_etc_dir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            runner.run(fixture, mock, Path("/etc/prod-ops-out"))
        assert mock.get_call_tools() == []

    def test_rejects_dotdot_bypass(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            bad_dir = Path(tmp) / ".." / ".." / "opt" / "code"
            with pytest.raises(ArtifactDirError, match="must resolve inside"):
                runner.run(fixture, mock, bad_dir)
        assert mock.get_call_tools() == []

    def test_rejects_absolute_opt_path(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with pytest.raises(ArtifactDirError, match="must resolve inside"):
            runner.run(fixture, mock, Path("/opt/code/lnkwebsite/artifacts/runs"))
        assert mock.get_call_tools() == []

    def test_accepts_nested_temp_subdir(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            nested = Path(tmp) / "nested" / "deeper"
            result = runner.run(fixture, mock, nested)
            assert result.valid
            assert all(p.exists() for p in result.artifact_paths.values())


# ---------------------------------------------------------------------------
# CMS field isolation
# ---------------------------------------------------------------------------


class TestCMSFieldIsolation:
    def test_strips_internal_keys(self) -> None:
        fields = ProductOpsRunner._build_cms_fields({
            "fixture": True,
            "execution_mode": "synthetic-test",
            "client_authorized": True,
            "product_name": "Test",
            "slug": "test",
        })
        assert "fixture" not in fields
        assert "execution_mode" not in fields
        assert "client_authorized" not in fields
        assert fields["product_name"] == "Test"
        assert fields["slug"] == "test"


# ---------------------------------------------------------------------------
# PRD → pipeline integration
# ---------------------------------------------------------------------------


class TestPRDToPipelineIntegration:
    def test_prd_parsed_then_validated(self) -> None:
        prd = """\
# AI Customer Service

- **slug**: ai-customer-service
- **category**: ai_customer_service
- **vendor**: LangChat Inc.

## Short Description

AI-powered customer service platform.

## Description

Intelligent customer service with natural language understanding
and multi-channel support.

## Capabilities

- 通道拥堵检测 (mvp)
- 火灾烟雾识别 (mvp)
- 地面脏污识别 (mvp)
- 智能对话 (roadmap)
"""
        parsed = parse_prd(prd)
        payload: dict[str, object] = {
            **parsed.to_payload(),
            "fixture": True,
            "client_authorized": True,
        }
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(payload, mock, Path(tmp))
            assert result.valid
            assert result.draft_status == "draft"
            assert result.draft_id == "fixture-product-001"


# ---------------------------------------------------------------------------
# Result serialization
# ---------------------------------------------------------------------------


class TestResultSerialization:
    def test_to_dict(self) -> None:
        fixture = _load_fixture()
        mock = MockMCPServer()
        runner = ProductOpsRunner()
        with tempfile.TemporaryDirectory(prefix="prod-ops-") as tmp:
            result = runner.run(fixture, mock, Path(tmp))
            assert result.valid
            d = result.to_dict()
        assert d["valid"] is True
        assert d["draft_id"] == "fixture-product-001"
        assert d["draft_status"] == "draft"
        assert "product_create" in d["mcp_calls"]
        assert isinstance(d["artifacts"], dict)
        assert isinstance(d["errors"], list)
