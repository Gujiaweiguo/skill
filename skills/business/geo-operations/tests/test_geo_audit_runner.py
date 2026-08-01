"""Tests for the GEO audit runner.

Covers: HTML parsing, all six audit dimensions (Baidu verification,
llms.txt, capability drift, NAP consistency, sitemap status, map
annotation), report generation, CLI interface, fixture loading,
and scope filtering.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

from scripts.geo_audit_runner import (
    GEOAuditRunner,
    GEOPageRecord,
    GEODriftReport,
    GEOFinding,
    LlmsTxtData,
    _make_finding,
    load_fixture,
    main,
    parse_html,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


# ---------------------------------------------------------------------------
# HTML Parsing Tests
# ---------------------------------------------------------------------------


class TestParseHtml:
    def test_extracts_title(self) -> None:
        html = "<html><head><title>Test Page</title></head><body></body></html>"
        rec = parse_html(html, "https://example.com/")
        assert rec.title == "Test Page"

    def test_extracts_description(self) -> None:
        html = (
            '<html><head><meta name="description" content="A test page">'
            "</head></html>"
        )
        rec = parse_html(html, "https://example.com/")
        assert rec.description == "A test page"

    def test_extracts_baidu_verification(self) -> None:
        html = (
            '<html><head>'
            '<meta name="baidu-site-verification" content="baidu-abc123">'
            "</head></html>"
        )
        rec = parse_html(html, "https://example.com/")
        assert rec.baidu_verification_tag == "baidu-abc123"

    def test_no_baidu_tag(self) -> None:
        html = "<html><head><title>Test</title></head></html>"
        rec = parse_html(html, "https://example.com/")
        assert rec.baidu_verification_tag == ""

    def test_extracts_baidu_map(self) -> None:
        html = (
            '<html><body>'
            '<script src="https://api.map.baidu.com/api?v=3.0"></script>'
            "</body></html>"
        )
        rec = parse_html(html, "https://example.com/")
        assert rec.has_baidu_map is True
        assert rec.has_amap is False

    def test_extracts_amap(self) -> None:
        html = (
            '<html><body>'
            '<script src="https://webapi.amap.com/maps?v=2.0"></script>'
            "</body></html>"
        )
        rec = parse_html(html, "https://example.com/")
        assert rec.has_amap is True
        assert rec.has_baidu_map is False

    def test_extracts_nap_from_json_ld(self) -> None:
        json_ld = (
            '{"@type":"LocalBusiness",'
            '"name":"TestCorp",'
            '"address":"123 Test St",'
            '"telephone":"+86-21-9999"}'
        )
        html = (
            f'<html><body><script type="application/ld+json">{json_ld}'
            "</script></body></html>"
        )
        rec = parse_html(html, "https://example.com/")
        assert rec.nap_name == "TestCorp"
        assert rec.nap_address == "123 Test St"
        assert rec.nap_phone == "+86-21-9999"

    def test_no_nap_without_json_ld(self) -> None:
        html = "<html><body><p>No NAP data</p></body></html>"
        rec = parse_html(html, "https://example.com/")
        assert rec.nap_name == ""
        assert rec.nap_address == ""
        assert rec.nap_phone == ""

    def test_empty_html(self) -> None:
        rec = parse_html("", "https://example.com/")
        assert rec.title == ""
        assert rec.description == ""
        assert rec.baidu_verification_tag == ""

    def test_multiple_json_ld_blocks(self) -> None:
        html = (
            '<html><body>'
            '<script type="application/ld+json">'
            '{"@type":"WebSite","name":"Site"}'
            "</script>"
            '<script type="application/ld+json">'
            '{"@type":"LocalBusiness","name":"Biz","address":"Addr",'
            '"telephone":"Tel"}'
            "</script>"
            "</body></html>"
        )
        rec = parse_html(html, "https://example.com/")
        assert len(rec.json_ld_blocks) == 2
        # NAP should be extracted from whichever block has it
        assert rec.nap_name == "Site"  # First match wins

    def test_baidu_tag_case_insensitive(self) -> None:
        html = (
            '<html><head>'
            '<META NAME="BAIDU-SITE-VERIFICATION" CONTENT="code-xyz">'
            "</head></html>"
        )
        rec = parse_html(html, "https://example.com/")
        assert rec.baidu_verification_tag == "code-xyz"


# ---------------------------------------------------------------------------
# Baidu Verification Tests
# ---------------------------------------------------------------------------


class TestBaiduVerification:
    def test_verified_homepage(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/",
                baidu_verification_tag="baidu-code-123",
                status_code=200,
            ),
        ]
        runner = GEOAuditRunner(audit_scope="baidu-only")
        report = runner.run(pages)
        assert report.baidu_verification["verified"] is True
        assert report.baidu_verification["verification_tag"] == "baidu-code-123"
        assert len(report.findings) == 0

    def test_missing_tag(self) -> None:
        pages = [
            GEOPageRecord(url="https://lanlnk.cn/", status_code=200),
        ]
        runner = GEOAuditRunner(audit_scope="baidu-only")
        report = runner.run(pages)
        assert report.baidu_verification["verified"] is False
        assert any(
            f.issue_type == "baidu_verification_missing_tag" for f in report.findings
        )

    def test_no_pages(self) -> None:
        pages: list[GEOPageRecord] = []
        runner = GEOAuditRunner(audit_scope="baidu-only")
        report = runner.run(pages)
        assert report.baidu_verification["verified"] is False
        assert any(
            f.issue_type == "baidu_not_verified" for f in report.findings
        )

    def test_tag_on_non_homepage(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/about",
                baidu_verification_tag="code-x",
                status_code=200,
            ),
        ]
        runner = GEOAuditRunner(audit_scope="baidu-only")
        report = runner.run(pages)
        assert report.baidu_verification["verified"] is True


# ---------------------------------------------------------------------------
# llms.txt Tests
# ---------------------------------------------------------------------------


class TestLlmsTxt:
    def test_reachable_with_capabilities(self) -> None:
        llms = LlmsTxtData(
            url="https://lanlnk.cn/llms.txt",
            reachable=True,
            content_lines=["# lnlnk", "## Capabilities"],
            last_updated="2026-07-18",
            capability_sections=["property-management", "visitor-control"],
        )
        runner = GEOAuditRunner(audit_scope="llms-only")
        report = runner.run([], llms_txt=llms)
        assert report.llms_txt["reachable"] is True
        assert len(report.findings) == 0

    def test_unreachable(self) -> None:
        runner = GEOAuditRunner(audit_scope="llms-only")
        report = runner.run([], llms_txt=None)
        assert report.llms_txt["reachable"] is False
        assert any(
            f.issue_type == "llms_txt_unreachable" for f in report.findings
        )

    def test_empty_content(self) -> None:
        llms = LlmsTxtData(
            url="https://lanlnk.cn/llms.txt",
            reachable=True,
            content_lines=[],
            last_updated="2026-07-18",
        )
        runner = GEOAuditRunner(audit_scope="llms-only")
        report = runner.run([], llms_txt=llms)
        assert any(f.issue_type == "llms_txt_empty" for f in report.findings)

    def test_no_capabilities(self) -> None:
        llms = LlmsTxtData(
            url="https://lanlnk.cn/llms.txt",
            reachable=True,
            content_lines=["# lnlnk"],
            last_updated="2026-07-18",
            capability_sections=[],
        )
        runner = GEOAuditRunner(audit_scope="llms-only")
        report = runner.run([], llms_txt=llms)
        assert any(
            f.issue_type == "llms_txt_no_capabilities" for f in report.findings
        )

    def test_stale_content(self) -> None:
        llms = LlmsTxtData(
            url="https://lanlnk.cn/llms.txt",
            reachable=True,
            content_lines=["# lnlnk"],
            last_updated="2025-01-01",
            capability_sections=["cap1"],
        )
        runner = GEOAuditRunner(audit_scope="llms-only")
        report = runner.run([], llms_txt=llms)
        assert any(f.issue_type == "llms_txt_stale" for f in report.findings)

    def test_invalid_date_skips_staleness(self) -> None:
        llms = LlmsTxtData(
            url="https://lanlnk.cn/llms.txt",
            reachable=True,
            content_lines=["# lnlnk"],
            last_updated="not-a-date",
            capability_sections=["cap1"],
        )
        runner = GEOAuditRunner(audit_scope="llms-only")
        report = runner.run([], llms_txt=llms)
        assert not any(f.issue_type == "llms_txt_stale" for f in report.findings)


# ---------------------------------------------------------------------------
# Capability Drift Tests
# ---------------------------------------------------------------------------


class TestCapabilityDrift:
    def test_no_drift(self) -> None:
        pages = [
            GEOPageRecord(url=f"https://lanlnk.cn/{cap}", status_code=200)
            for cap in ["property-management", "visitor-control"]
        ]
        llms = LlmsTxtData(
            reachable=True,
            capability_sections=["property-management", "visitor-control"],
        )
        profile = {"capabilities": ["property-management", "visitor-control"]}
        runner = GEOAuditRunner(audit_scope="capability-only")
        report = runner.run(pages, llms_txt=llms, geo_profile=profile)
        assert report.capability_drift["missing_in_llms"] == []
        assert report.capability_drift["extra_in_llms"] == []
        assert len(report.findings) == 0

    def test_missing_in_llms(self) -> None:
        pages = [
            GEOPageRecord(url="https://lanlnk.cn/cap-a", status_code=200),
            GEOPageRecord(url="https://lanlnk.cn/cap-b", status_code=200),
            GEOPageRecord(url="https://lanlnk.cn/cap-c", status_code=200),
        ]
        llms = LlmsTxtData(reachable=True, capability_sections=["cap-a", "cap-b"])
        profile = {"capabilities": ["cap-a", "cap-b", "cap-c"]}
        runner = GEOAuditRunner(audit_scope="capability-only")
        report = runner.run(pages, llms_txt=llms, geo_profile=profile)
        assert "cap-c" in report.capability_drift["missing_in_llms"]
        assert any(
            f.issue_type == "capability_missing_page" for f in report.findings
        )

    def test_extra_in_llms(self) -> None:
        pages: list[GEOPageRecord] = []
        llms = LlmsTxtData(
            reachable=True,
            capability_sections=["cap-a", "cap-extra"],
        )
        profile = {"capabilities": ["cap-a"]}
        runner = GEOAuditRunner(audit_scope="capability-only")
        report = runner.run(pages, llms_txt=llms, geo_profile=profile)
        assert "cap-extra" in report.capability_drift["extra_in_llms"]
        assert any(
            f.issue_type == "capability_extra_in_llms" for f in report.findings
        )

    def test_missing_live_page(self) -> None:
        pages = [
            GEOPageRecord(url="https://lanlnk.cn/cap-a", status_code=200),
        ]
        llms = LlmsTxtData(reachable=True, capability_sections=["cap-a", "cap-b"])
        profile = {"capabilities": ["cap-a", "cap-b"]}
        runner = GEOAuditRunner(audit_scope="capability-only")
        report = runner.run(pages, llms_txt=llms, geo_profile=profile)
        assert "cap-b" in report.capability_drift["missing_pages"]
        assert any(
            f.issue_type == "capability_profile_mismatch" for f in report.findings
        )

    def test_no_profile(self) -> None:
        runner = GEOAuditRunner(audit_scope="capability-only")
        report = runner.run([], llms_txt=None, geo_profile=None)
        assert report.capability_drift["profile_capabilities"] == []

    def test_profile_capabilities_not_list(self) -> None:
        profile: dict[str, object] = {"capabilities": "not-a-list"}
        runner = GEOAuditRunner(audit_scope="capability-only")
        report = runner.run([], geo_profile=profile)
        assert report.capability_drift["profile_capabilities"] == []


# ---------------------------------------------------------------------------
# NAP Consistency Tests
# ---------------------------------------------------------------------------


class TestNAPConsistency:
    def test_consistent_nap(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/",
                nap_name="Corp",
                nap_address="Addr",
                nap_phone="123",
            ),
            GEOPageRecord(
                url="https://lanlnk.cn/about",
                nap_name="Corp",
                nap_address="Addr",
                nap_phone="123",
            ),
        ]
        runner = GEOAuditRunner(audit_scope="nap-only")
        report = runner.run(pages)
        assert len(report.findings) == 0
        assert report.nap_consistency["canonical_name"] == "Corp"

    def test_missing_name(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/",
                nap_name="",
                nap_address="Addr",
                nap_phone="123",
            ),
        ]
        runner = GEOAuditRunner(audit_scope="nap-only")
        report = runner.run(pages)
        assert any(f.issue_type == "nap_missing_name" for f in report.findings)

    def test_missing_address(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/",
                nap_name="Corp",
                nap_address="",
                nap_phone="123",
            ),
        ]
        runner = GEOAuditRunner(audit_scope="nap-only")
        report = runner.run(pages)
        assert any(f.issue_type == "nap_missing_address" for f in report.findings)

    def test_missing_phone(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/",
                nap_name="Corp",
                nap_address="Addr",
                nap_phone="",
            ),
        ]
        runner = GEOAuditRunner(audit_scope="nap-only")
        report = runner.run(pages)
        assert any(f.issue_type == "nap_missing_phone" for f in report.findings)

    def test_inconsistent_name(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/",
                nap_name="CorpA",
                nap_address="Addr",
                nap_phone="123",
            ),
            GEOPageRecord(
                url="https://lanlnk.cn/about",
                nap_name="CorpB",
                nap_address="Addr",
                nap_phone="123",
            ),
        ]
        runner = GEOAuditRunner(audit_scope="nap-only")
        report = runner.run(pages)
        assert any(
            f.issue_type == "nap_inconsistent_name" for f in report.findings
        )

    def test_inconsistent_phone(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/",
                nap_name="Corp",
                nap_address="Addr",
                nap_phone="111",
            ),
            GEOPageRecord(
                url="https://lanlnk.cn/about",
                nap_name="Corp",
                nap_address="Addr",
                nap_phone="222",
            ),
        ]
        runner = GEOAuditRunner(audit_scope="nap-only")
        report = runner.run(pages)
        assert any(
            f.issue_type == "nap_inconsistent_phone" for f in report.findings
        )

    def test_inconsistent_address(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/",
                nap_name="Corp",
                nap_address="AddrA",
                nap_phone="123",
            ),
            GEOPageRecord(
                url="https://lanlnk.cn/about",
                nap_name="Corp",
                nap_address="AddrB",
                nap_phone="123",
            ),
        ]
        runner = GEOAuditRunner(audit_scope="nap-only")
        report = runner.run(pages)
        assert any(
            f.issue_type == "nap_inconsistent_address" for f in report.findings
        )

    def test_no_nap_data(self) -> None:
        pages = [GEOPageRecord(url="https://lanlnk.cn/")]
        runner = GEOAuditRunner(audit_scope="nap-only")
        report = runner.run(pages)
        assert len(report.findings) == 0
        assert report.nap_consistency["canonical_name"] == ""


# ---------------------------------------------------------------------------
# Sitemap Tests
# ---------------------------------------------------------------------------


class TestSitemapStatus:
    def test_referenced_in_robots(self) -> None:
        runner = GEOAuditRunner(audit_scope="sitemap-only")
        report = runner.run(
            [],
            sitemap_url="https://lanlnk.cn/sitemap.xml",
            robots_sitemap_refs=["https://lanlnk.cn/sitemap.xml"],
        )
        assert report.sitemap_status["referenced_in_robots"] is True
        assert len(report.findings) == 0

    def test_not_referenced(self) -> None:
        runner = GEOAuditRunner(audit_scope="sitemap-only")
        report = runner.run(
            [],
            sitemap_url="https://lanlnk.cn/sitemap.xml",
            robots_sitemap_refs=[],
        )
        assert report.sitemap_status["referenced_in_robots"] is False
        assert any(
            f.issue_type == "sitemap_no_robots_ref" for f in report.findings
        )

    def test_partial_match_in_robots(self) -> None:
        runner = GEOAuditRunner(audit_scope="sitemap-only")
        report = runner.run(
            [],
            sitemap_url="https://lanlnk.cn/sitemap.xml",
            robots_sitemap_refs=["https://lanlnk.cn/sitemap-index.xml"],
        )
        # Partial match on "sitemap" keyword
        assert report.sitemap_status["referenced_in_robots"] is True

    def test_null_refs(self) -> None:
        runner = GEOAuditRunner(audit_scope="sitemap-only")
        report = runner.run(
            [],
            sitemap_url="https://lanlnk.cn/sitemap.xml",
            robots_sitemap_refs=None,
        )
        assert report.sitemap_status["referenced_in_robots"] is False


# ---------------------------------------------------------------------------
# Map Annotation Tests
# ---------------------------------------------------------------------------


class TestMapAnnotation:
    def test_all_pages_have_baidu_map(self) -> None:
        pages = [
            GEOPageRecord(url="https://lanlnk.cn/", has_baidu_map=True),
            GEOPageRecord(url="https://lanlnk.cn/about", has_baidu_map=True),
        ]
        runner = GEOAuditRunner(audit_scope="map-only")
        report = runner.run(pages)
        assert len(report.map_annotation["pages_without_map"]) == 0
        assert len(report.findings) == 0

    def test_missing_map(self) -> None:
        pages = [
            GEOPageRecord(url="https://lanlnk.cn/", has_baidu_map=True),
            GEOPageRecord(url="https://lanlnk.cn/about", has_baidu_map=False),
        ]
        runner = GEOAuditRunner(audit_scope="map-only")
        report = runner.run(pages)
        assert any(
            f.issue_type == "map_annotation_missing" for f in report.findings
        )

    def test_inconsistent_providers(self) -> None:
        pages = [
            GEOPageRecord(url="https://lanlnk.cn/", has_baidu_map=True),
            GEOPageRecord(url="https://lanlnk.cn/about", has_amap=True),
        ]
        runner = GEOAuditRunner(audit_scope="map-only")
        report = runner.run(pages)
        assert any(
            f.issue_type == "map_annotation_inconsistent" for f in report.findings
        )

    def test_no_pages(self) -> None:
        runner = GEOAuditRunner(audit_scope="map-only")
        report = runner.run([])
        assert len(report.findings) == 0


# ---------------------------------------------------------------------------
# Full Audit Tests
# ---------------------------------------------------------------------------


class TestFullAudit:
    def test_full_scope_runs_all_dimensions(self) -> None:
        pages = [GEOPageRecord(url="https://lanlnk.cn/", status_code=200)]
        runner = GEOAuditRunner(audit_scope="full")
        report = runner.run(
            pages,
            llms_txt=LlmsTxtData(reachable=True, content_lines=["# test"]),
            geo_profile={"capabilities": ["test-cap"]},
        )
        # All dimension dicts should be populated
        assert report.baidu_verification != {}
        assert report.llms_txt != {}
        assert report.capability_drift != {}
        assert report.nap_consistency != {}
        assert report.sitemap_status != {}
        assert report.map_annotation != {}

    def test_summary_counts(self) -> None:
        pages = [
            GEOPageRecord(url="https://lanlnk.cn/", status_code=200),
        ]
        runner = GEOAuditRunner(audit_scope="full")
        report = runner.run(pages, llms_txt=None)
        total = report.summary["total_findings"]
        critical = report.summary.get("severity_critical", 0)
        warning = report.summary.get("severity_warning", 0)
        info = report.summary.get("severity_info", 0)
        assert total == critical + warning + info

    def test_report_to_dict(self) -> None:
        pages = [GEOPageRecord(url="https://lanlnk.cn/", status_code=200)]
        runner = GEOAuditRunner()
        report = runner.run(pages)
        d = report.to_dict()
        assert "audit_date" in d
        assert "site" in d
        assert "findings" in d
        assert "summary" in d
        assert isinstance(d["findings"], list)


# ---------------------------------------------------------------------------
# Scope Filtering Tests
# ---------------------------------------------------------------------------


class TestScopeFiltering:
    def test_invalid_scope(self) -> None:
        with pytest.raises(ValueError, match="Invalid audit_scope"):
            GEOAuditRunner(audit_scope="invalid-scope")

    def test_baidu_only_skips_others(self) -> None:
        pages = [GEOPageRecord(url="https://lanlnk.cn/", status_code=200)]
        runner = GEOAuditRunner(audit_scope="baidu-only")
        report = runner.run(pages)
        assert report.llms_txt == {}
        assert report.nap_consistency == {}

    def test_nap_only_skips_others(self) -> None:
        pages = [
            GEOPageRecord(
                url="https://lanlnk.cn/",
                nap_name="Corp",
                nap_address="Addr",
                nap_phone="123",
            ),
        ]
        runner = GEOAuditRunner(audit_scope="nap-only")
        report = runner.run(pages)
        assert report.baidu_verification == {}
        assert report.nap_consistency["canonical_name"] == "Corp"

    def test_all_valid_scopes(self) -> None:
        for scope in [
            "full", "baidu-only", "llms-only", "capability-only",
            "nap-only", "sitemap-only", "map-only",
        ]:
            runner = GEOAuditRunner(audit_scope=scope)
            assert runner.audit_scope == scope


# ---------------------------------------------------------------------------
# Severity & Finding Tests
# ---------------------------------------------------------------------------


class TestSeverityMap:
    def test_critical_finding(self) -> None:
        f = _make_finding("https://example.com", "baidu_not_verified", "test")
        assert f.severity == "critical"
        assert f.dimension == "baidu"

    def test_warning_finding(self) -> None:
        f = _make_finding("https://example.com", "llms_txt_stale", "test")
        assert f.severity == "warning"
        assert f.dimension == "llms_txt"

    def test_info_finding(self) -> None:
        f = _make_finding("https://example.com", "capability_extra_in_llms", "test")
        assert f.severity == "info"
        assert f.dimension == "capability_drift"

    def test_unknown_issue_type_defaults(self) -> None:
        f = _make_finding("https://example.com", "nonexistent_type", "test")
        assert f.severity == "warning"
        assert f.dimension == "unknown"


# ---------------------------------------------------------------------------
# Fixture Loading Tests
# ---------------------------------------------------------------------------


class TestLoadFixture:
    def test_loads_pages(self) -> None:
        pages, _, _, _, _ = load_fixture(FIXTURE_PATH)
        assert len(pages) > 0
        assert pages[0].url.startswith("https://")

    def test_loads_llms_txt(self) -> None:
        _, llms, _, _, _ = load_fixture(FIXTURE_PATH)
        assert llms.reachable is True
        assert len(llms.content_lines) > 0
        assert len(llms.capability_sections) > 0

    def test_loads_geo_profile(self) -> None:
        _, _, profile, _, _ = load_fixture(FIXTURE_PATH)
        assert "capabilities" in profile
        assert isinstance(profile["capabilities"], list)

    def test_loads_sitemap(self) -> None:
        _, _, _, sitemap_url, robots_refs = load_fixture(FIXTURE_PATH)
        assert sitemap_url != ""
        assert len(robots_refs) > 0

    def test_page_fields_populated(self) -> None:
        pages, _, _, _, _ = load_fixture(FIXTURE_PATH)
        homepage = pages[0]
        assert homepage.baidu_verification_tag != ""
        assert homepage.nap_name != ""
        assert homepage.has_baidu_map is True


# ---------------------------------------------------------------------------
# Report Output Tests
# ---------------------------------------------------------------------------


class TestReportOutput:
    def test_write_report(self) -> None:
        runner = GEOAuditRunner()
        report = runner.run([])
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as f:
            output_path = f.name
        path = GEOAuditRunner.write_report(report, output_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert "audit_date" in data
        assert "findings" in data

    def test_write_report_creates_parent_dirs(self) -> None:
        runner = GEOAuditRunner()
        report = runner.run([])
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "nested" / "deep" / "report.json"
            path = GEOAuditRunner.write_report(report, output)
            assert path.exists()


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------


class TestCLI:
    def test_fixture_mode(self, capsys: pytest.CaptureFixture[str]) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as f:
            output_path = f.name
        rc = main([
            "--fixture", str(FIXTURE_PATH),
            "--output", output_path,
        ])
        assert rc == 0
        captured = capsys.readouterr()
        assert "GEO drift report" in captured.out
        assert Path(output_path).exists()

    def test_missing_fixture(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main(["--fixture", "/nonexistent/path.json"])
        assert rc != 0
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_no_fixture(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = main([])
        assert rc != 0
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_custom_scope(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as f:
            output_path = f.name
        rc = main([
            "--fixture", str(FIXTURE_PATH),
            "--output", output_path,
            "--scope", "baidu-only",
        ])
        assert rc == 0
        data = json.loads(Path(output_path).read_text())
        # baidu-only scope should only have baidu dimension findings
        assert data["baidu_verification"] != {}
        assert data["nap_consistency"] == {}

    def test_default_site(self) -> None:
        """Verify CLI defaults to lanlnk.cn."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as f:
            output_path = f.name
        rc = main([
            "--fixture", str(FIXTURE_PATH),
            "--output", output_path,
        ])
        assert rc == 0
        data = json.loads(Path(output_path).read_text())
        assert data["site"] == "lanlnk.cn"


# ---------------------------------------------------------------------------
# Integration: Fixture → Runner → Report
# ---------------------------------------------------------------------------


class TestIntegrationFixtureRun:
    def test_full_run_from_fixture(self) -> None:
        """Load the synthetic fixture and run a full audit."""
        pages, llms_txt, geo_profile, sitemap_url, robots_refs = load_fixture(
            FIXTURE_PATH,
        )
        runner = GEOAuditRunner(site="lanlnk.cn", audit_scope="full")
        report = runner.run(
            pages=pages,
            llms_txt=llms_txt,
            geo_profile=geo_profile,
            sitemap_url=sitemap_url,
            robots_sitemap_refs=robots_refs,
        )
        assert report.total_pages_checked > 0
        assert report.baidu_verification["verified"] is True
        assert report.llms_txt["reachable"] is True
        assert report.sitemap_status["referenced_in_robots"] is True
        # Capabilities should match between profile and llms.txt
        assert len(report.capability_drift["missing_in_llms"]) == 0

    def test_fixture_report_has_no_unexpected_criticals(self) -> None:
        """The synthetic fixture should be clean for critical findings."""
        pages, llms_txt, geo_profile, sitemap_url, robots_refs = load_fixture(
            FIXTURE_PATH,
        )
        runner = GEOAuditRunner()
        report = runner.run(
            pages=pages,
            llms_txt=llms_txt,
            geo_profile=geo_profile,
            sitemap_url=sitemap_url,
            robots_sitemap_refs=robots_refs,
        )
        critical_findings = [
            f for f in report.findings if f.severity == "critical"
        ]
        assert len(critical_findings) == 0, (
            f"Unexpected critical findings: "
            f"{[(f.issue_type, f.description) for f in critical_findings]}"
        )
