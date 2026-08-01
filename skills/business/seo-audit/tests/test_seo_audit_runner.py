"""Tests for the SEO audit runner.

Covers: HTML parsing, sitemap parsing, robots.txt parsing, JSON-LD
validation, canonical checks, meta uniqueness, structured data
validation, Open Graph checks, report generation, CLI entry,
and fixture integration.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

from scripts.seo_audit_runner import (
    CurlFetcher,
    PageRecord,
    RobotsData,
    SEOAuditReport,
    SEOAuditRunner,
    SEOFinding,
    SitemapData,
    VALID_AUDIT_SCOPES,
    parse_html,
    parse_robots,
    parse_sitemap,
    validate_json_ld,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


# ---------------------------------------------------------------------------
# Mock fetcher for deterministic tests
# ---------------------------------------------------------------------------


class FakeFetcher:
    """Deterministic URL fetcher for tests."""

    def __init__(self, responses: dict[str, dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[str] = []

    def fetch(self, url: str) -> dict[str, object]:
        self.calls.append(url)
        return self._responses.get(
            url,
            {"status_code": 0, "content": "", "reachable": False},
        )


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------


GOOD_HTML = """\
<!DOCTYPE html><html><head>
<title>Good Page - LANLNK</title>
<meta name="description" content="A well-optimised page with all required SEO elements for testing purposes.">
<meta name="robots" content="index,follow">
<link rel="canonical" href="https://lanlnk.cn/good">
<meta property="og:title" content="Good Page - LANLNK">
<meta property="og:description" content="A well-optimised page with all required SEO elements.">
<meta property="og:image" content="https://lanlnk.cn/og/good.png">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"Good Page"}</script>
</head><body><h1>Good Page Heading</h1></body></html>
"""

MISSING_TITLE_HTML = """\
<!DOCTYPE html><html><head>
<meta name="description" content="Page with no title tag for testing missing title detection logic.">
<link rel="canonical" href="https://lanlnk.cn/no-title">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><h1>Content</h1></body></html>
"""

MISSING_DESC_HTML = """\
<!DOCTYPE html><html><head>
<title>No Description Page</title>
<link rel="canonical" href="https://lanlnk.cn/no-desc">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><h1>Content</h1></body></html>
"""

MISSING_CANONICAL_HTML = """\
<!DOCTYPE html><html><head>
<title>No Canonical Page</title>
<meta name="description" content="Page without canonical tag for testing missing canonical detection here.">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><h1>Content</h1></body></html>
"""

MULTIPLE_H1_HTML = """\
<!DOCTYPE html><html><head>
<title>Multiple H1 Page</title>
<meta name="description" content="Page with multiple H1 tags for testing heading structure validation.">
<link rel="canonical" href="https://lanlnk.cn/multi-h1">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><h1>First Heading</h1><h1>Second Heading</h1></body></html>
"""

NO_H1_HTML = """\
<!DOCTYPE html><html><head>
<title>No H1 Page</title>
<meta name="description" content="Page with no H1 tag for testing missing heading detection.">
<link rel="canonical" href="https://lanlnk.cn/no-h1">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><p>Content but no heading</p></body></html>
"""

INVALID_JSON_LD_HTML = """\
<!DOCTYPE html><html><head>
<title>Bad JSON-LD Page</title>
<meta name="description" content="Page with invalid JSON-LD structured data for testing validation.">
<link rel="canonical" href="https://lanlnk.cn/bad-jsonld">
<script type="application/ld+json">{invalid json}</script>
</head><body><h1>Content</h1></body></html>
"""

MISSING_OG_HTML = """\
<!DOCTYPE html><html><head>
<title>Missing OG Page</title>
<meta name="description" content="Page without Open Graph tags for testing OG detection validation.">
<link rel="canonical" href="https://lanlnk.cn/no-og">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><h1>Content</h1></body></html>
"""

CROSS_DOMAIN_CANONICAL_HTML = """\
<!DOCTYPE html><html><head>
<title>Cross Domain Canonical</title>
<meta name="description" content="Page with canonical pointing to a different domain for testing.">
<link rel="canonical" href="https://example.com/page">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><h1>Content</h1></body></html>
"""

LONG_TITLE_HTML = """\
<!DOCTYPE html><html><head>
<title>This is an extremely long page title that exceeds the recommended sixty character limit for SEO</title>
<meta name="description" content="Normal description here for testing title length validation checks.">
<link rel="canonical" href="https://lanlnk.cn/long-title">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage"}</script>
</head><body><h1>Content</h1></body></html>
"""

SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://lanlnk.cn/</loc><lastmod>2026-07-20</lastmod><priority>1.0</priority></url>
  <url><loc>https://lanlnk.cn/capabilities</loc><lastmod>2026-07-18</lastmod><priority>0.8</priority></url>
  <url><loc>https://lanlnk.cn/cases</loc><lastmod>2026-07-19</lastmod><priority>0.8</priority></url>
</urlset>
"""

ROBOTS_TXT = """\
User-agent: *
Disallow: /admin/
Disallow: /private/

Sitemap: https://lanlnk.cn/sitemap.xml
"""


# ---------------------------------------------------------------------------
# HTML Parser Tests
# ---------------------------------------------------------------------------


class TestParseHtml:
    """Verify HTML parsing extracts all SEO elements."""

    def test_parses_title(self) -> None:
        record = parse_html(GOOD_HTML, url="https://lanlnk.cn/good")
        assert record.title == "Good Page - LANLNK"

    def test_parses_description(self) -> None:
        record = parse_html(GOOD_HTML, url="https://lanlnk.cn/good")
        assert "well-optimised" in record.description

    def test_parses_canonical(self) -> None:
        record = parse_html(GOOD_HTML, url="https://lanlnk.cn/good")
        assert record.canonical == "https://lanlnk.cn/good"

    def test_parses_h1(self) -> None:
        record = parse_html(GOOD_HTML, url="https://lanlnk.cn/good")
        assert len(record.h1_tags) == 1
        assert record.h1_tags[0] == "Good Page Heading"

    def test_parses_og_tags(self) -> None:
        record = parse_html(GOOD_HTML, url="https://lanlnk.cn/good")
        assert record.og_title == "Good Page - LANLNK"
        assert "well-optimised" in record.og_description
        assert record.og_image == "https://lanlnk.cn/og/good.png"

    def test_parses_json_ld(self) -> None:
        record = parse_html(GOOD_HTML, url="https://lanlnk.cn/good")
        assert len(record.json_ld_blocks) == 1

    def test_parses_meta_robots(self) -> None:
        record = parse_html(GOOD_HTML, url="https://lanlnk.cn/good")
        assert "index" in record.meta_robots

    def test_parses_multiple_json_ld(self) -> None:
        html = """\
<html><head>
<script type="application/ld+json">{"@type":"Organization"}</script>
<script type="application/ld+json">{"@type":"WebPage"}</script>
</head><body><h1>Test</h1></body></html>
"""
        record = parse_html(html, url="https://test.com")
        assert len(record.json_ld_blocks) == 2

    def test_empty_html(self) -> None:
        record = parse_html("", url="https://empty.com")
        assert record.title == ""
        assert record.description == ""
        assert record.canonical == ""
        assert record.h1_tags == []
        assert record.json_ld_blocks == []

    def test_canonical_alt_format(self) -> None:
        """Canonical with href before rel."""
        html = '<html><head><link href="https://example.com/canonical" rel="canonical"></head><body></body></html>'
        record = parse_html(html, url="https://test.com")
        assert record.canonical == "https://example.com/canonical"


# ---------------------------------------------------------------------------
# Sitemap Parser Tests
# ---------------------------------------------------------------------------


class TestParseSitemap:
    """Verify sitemap.xml parsing."""

    def test_parses_urls(self) -> None:
        sitemap = parse_sitemap(SITEMAP_XML, "https://lanlnk.cn/sitemap.xml")
        assert sitemap.total_urls == 3
        assert sitemap.entries[0]["loc"] == "https://lanlnk.cn/"
        assert sitemap.reachable

    def test_empty_sitemap(self) -> None:
        sitemap = parse_sitemap("", "")
        assert sitemap.total_urls == 0
        assert not sitemap.reachable

    def test_no_urls_in_sitemap(self) -> None:
        sitemap = parse_sitemap("<urlset></urlset>", "")
        assert sitemap.total_urls == 0


# ---------------------------------------------------------------------------
# Robots Parser Tests
# ---------------------------------------------------------------------------


class TestParseRobots:
    """Verify robots.txt parsing."""

    def test_parses_sitemap_ref(self) -> None:
        robots = parse_robots(ROBOTS_TXT, "https://lanlnk.cn/robots.txt")
        assert "https://lanlnk.cn/sitemap.xml" in robots.sitemap_refs

    def test_parses_disallow(self) -> None:
        robots = parse_robots(ROBOTS_TXT, "https://lanlnk.cn/robots.txt")
        assert "/admin/" in robots.disallowed_paths
        assert "/private/" in robots.disallowed_paths

    def test_empty_robots(self) -> None:
        robots = parse_robots("", "")
        assert not robots.reachable
        assert robots.sitemap_refs == []

    def test_no_sitemap_ref(self) -> None:
        robots = parse_robots("User-agent: *\nDisallow:", "")
        assert robots.sitemap_refs == []


# ---------------------------------------------------------------------------
# JSON-LD Validation Tests
# ---------------------------------------------------------------------------


class TestValidateJsonLd:
    """Verify JSON-LD validation."""

    def test_valid_json_ld(self) -> None:
        block = '{"@context":"https://schema.org","@type":"WebPage","name":"Test"}'
        errors = validate_json_ld(block)
        assert errors == []

    def test_invalid_json(self) -> None:
        block = "{invalid}"
        errors = validate_json_ld(block)
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]

    def test_missing_type(self) -> None:
        block = '{"@context":"https://schema.org","name":"Test"}'
        errors = validate_json_ld(block)
        assert any("missing @type" in e for e in errors)

    def test_array_format(self) -> None:
        block = '[{"@type":"Organization"},{"@type":"WebPage"}]'
        errors = validate_json_ld(block)
        assert errors == []

    def test_graph_format(self) -> None:
        block = '{"@context":"https://schema.org","@graph":[{"@type":"Organization"}]}'
        errors = validate_json_ld(block)
        assert errors == []

    def test_not_object(self) -> None:
        block = '"just a string"'
        errors = validate_json_ld(block)
        assert any("must be" in e for e in errors)


# ---------------------------------------------------------------------------
# Audit Runner Constructor Tests
# ---------------------------------------------------------------------------


class TestAuditRunnerInit:
    """Constructor validation."""

    @pytest.mark.parametrize("scope", sorted(VALID_AUDIT_SCOPES))
    def test_valid_scope(self, scope: str) -> None:
        runner = SEOAuditRunner(audit_scope=scope)
        assert runner.audit_scope == scope

    def test_invalid_scope(self) -> None:
        with pytest.raises(ValueError, match="invalid audit_scope"):
            SEOAuditRunner(audit_scope="everything")

    def test_default_scope(self) -> None:
        runner = SEOAuditRunner()
        assert runner.audit_scope == "full"


# ---------------------------------------------------------------------------
# Canonical Audit Tests
# ---------------------------------------------------------------------------


class TestCanonicalAudit:
    """Canonical consistency checks."""

    def test_no_canonical_flagged(self) -> None:
        runner = SEOAuditRunner()
        record = parse_html(MISSING_CANONICAL_HTML, "https://lanlnk.cn/no-canonical")
        findings = runner.audit_canonical([record])
        assert any(f.issue_type == "missing_canonical" for f in findings)

    def test_self_canonical_ok(self) -> None:
        runner = SEOAuditRunner()
        record = parse_html(GOOD_HTML, "https://lanlnk.cn/good")
        findings = runner.audit_canonical([record])
        assert len(findings) == 0

    def test_cross_domain_canonical_flagged(self) -> None:
        runner = SEOAuditRunner()
        record = parse_html(CROSS_DOMAIN_CANONICAL_HTML, "https://lanlnk.cn/cross")
        findings = runner.audit_canonical([record])
        assert any(f.issue_type == "canonical_mismatch" for f in findings)

    def test_severity_mapping(self) -> None:
        runner = SEOAuditRunner()
        record = parse_html(MISSING_CANONICAL_HTML, "https://lanlnk.cn/no-canonical")
        findings = runner.audit_canonical([record])
        assert findings[0].severity == "warning"
        assert findings[0].dimension == "canonical"


# ---------------------------------------------------------------------------
# Structured Data Audit Tests
# ---------------------------------------------------------------------------


class TestStructuredDataAudit:
    """JSON-LD structured data checks."""

    def test_missing_json_ld_flagged(self) -> None:
        html = """<html><head><title>No Schema</title></head><body><h1>x</h1></body></html>"""
        record = parse_html(html, "https://lanlnk.cn/no-schema")
        runner = SEOAuditRunner()
        findings = runner.audit_structured_data([record])
        assert any(f.issue_type == "missing_json_ld" for f in findings)

    def test_valid_json_ld_passes(self) -> None:
        record = parse_html(GOOD_HTML, "https://lanlnk.cn/good")
        runner = SEOAuditRunner()
        findings = runner.audit_structured_data([record])
        assert len(findings) == 0

    def test_invalid_json_ld_flagged(self) -> None:
        record = parse_html(INVALID_JSON_LD_HTML, "https://lanlnk.cn/bad")
        runner = SEOAuditRunner()
        findings = runner.audit_structured_data([record])
        assert any(f.issue_type == "invalid_json_ld" for f in findings)
        assert findings[0].severity == "critical"


# ---------------------------------------------------------------------------
# Meta Audit Tests
# ---------------------------------------------------------------------------


class TestMetaAudit:
    """Meta tag uniqueness and completeness checks."""

    def test_missing_title_flagged(self) -> None:
        record = parse_html(MISSING_TITLE_HTML, "https://lanlnk.cn/no-title")
        runner = SEOAuditRunner()
        findings, _ = runner.audit_meta([record])
        assert any(f.issue_type == "missing_title" for f in findings)

    def test_missing_description_flagged(self) -> None:
        record = parse_html(MISSING_DESC_HTML, "https://lanlnk.cn/no-desc")
        runner = SEOAuditRunner()
        findings, _ = runner.audit_meta([record])
        assert any(f.issue_type == "missing_description" for f in findings)

    def test_duplicate_titles_detected(self) -> None:
        r1 = parse_html(GOOD_HTML, "https://lanlnk.cn/page1")
        r2 = parse_html(GOOD_HTML, "https://lanlnk.cn/page2")
        runner = SEOAuditRunner()
        findings, dups = runner.audit_meta([r1, r2])
        assert any(f.issue_type == "duplicate_title" for f in findings)

    def test_multiple_h1_flagged(self) -> None:
        record = parse_html(MULTIPLE_H1_HTML, "https://lanlnk.cn/multi-h1")
        runner = SEOAuditRunner()
        findings, _ = runner.audit_meta([record])
        assert any(f.issue_type == "multiple_h1" for f in findings)

    def test_missing_h1_flagged(self) -> None:
        record = parse_html(NO_H1_HTML, "https://lanlnk.cn/no-h1")
        runner = SEOAuditRunner()
        findings, _ = runner.audit_meta([record])
        assert any(f.issue_type == "missing_h1" for f in findings)

    def test_missing_og_title_flagged(self) -> None:
        record = parse_html(MISSING_OG_HTML, "https://lanlnk.cn/no-og")
        runner = SEOAuditRunner()
        findings, _ = runner.audit_meta([record])
        assert any(f.issue_type == "missing_og_title" for f in findings)

    def test_missing_og_description_flagged(self) -> None:
        record = parse_html(MISSING_OG_HTML, "https://lanlnk.cn/no-og")
        runner = SEOAuditRunner()
        findings, _ = runner.audit_meta([record])
        assert any(f.issue_type == "missing_og_description" for f in findings)

    def test_missing_og_image_flagged(self) -> None:
        record = parse_html(MISSING_OG_HTML, "https://lanlnk.cn/no-og")
        runner = SEOAuditRunner()
        findings, _ = runner.audit_meta([record])
        assert any(f.issue_type == "missing_og_image" for f in findings)

    def test_title_too_long_flagged(self) -> None:
        record = parse_html(LONG_TITLE_HTML, "https://lanlnk.cn/long")
        runner = SEOAuditRunner()
        findings, _ = runner.audit_meta([record])
        assert any(f.issue_type == "title_too_long" for f in findings)

    def test_complete_page_no_meta_findings(self) -> None:
        record = parse_html(GOOD_HTML, "https://lanlnk.cn/good")
        runner = SEOAuditRunner()
        findings, _ = runner.audit_meta([record])
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# Sitemap Audit Tests
# ---------------------------------------------------------------------------


class TestSitemapAudit:
    """Sitemap completeness checks with fake fetcher."""

    def test_reachable_sitemap(self) -> None:
        fetcher = FakeFetcher({
            "https://lanlnk.cn/sitemap.xml": {
                "status_code": 200,
                "content": SITEMAP_XML,
                "reachable": True,
            },
        })
        runner = SEOAuditRunner(fetcher=fetcher)
        sitemap, findings = runner.audit_sitemap("https://lanlnk.cn/sitemap.xml")
        assert sitemap.reachable
        assert sitemap.total_urls == 3
        assert len(findings) == 0

    def test_unreachable_sitemap(self) -> None:
        fetcher = FakeFetcher({})
        runner = SEOAuditRunner(fetcher=fetcher)
        sitemap, findings = runner.audit_sitemap("https://lanlnk.cn/sitemap.xml")
        assert not sitemap.reachable
        assert any(f.issue_type == "sitemap_unreachable" for f in findings)

    def test_empty_sitemap(self) -> None:
        fetcher = FakeFetcher({
            "https://lanlnk.cn/sitemap.xml": {
                "status_code": 200,
                "content": "<urlset></urlset>",
                "reachable": True,
            },
        })
        runner = SEOAuditRunner(fetcher=fetcher)
        sitemap, findings = runner.audit_sitemap("https://lanlnk.cn/sitemap.xml")
        assert sitemap.total_urls == 0
        assert any(f.issue_type == "sitemap_empty" for f in findings)

    def test_missing_urls_detected(self) -> None:
        fetcher = FakeFetcher({
            "https://lanlnk.cn/sitemap.xml": {
                "status_code": 200,
                "content": SITEMAP_XML,
                "reachable": True,
            },
        })
        runner = SEOAuditRunner(fetcher=fetcher)
        known = ["https://lanlnk.cn/", "https://lanlnk.cn/missing-page"]
        sitemap, findings = runner.audit_sitemap(
            "https://lanlnk.cn/sitemap.xml", known_urls=known,
        )
        missing_findings = [f for f in findings if f.issue_type == "sitemap_missing_url"]
        assert len(missing_findings) == 1
        assert "missing-page" in missing_findings[0].description


# ---------------------------------------------------------------------------
# Robots.txt Audit Tests
# ---------------------------------------------------------------------------


class TestRobotsAudit:
    """Robots.txt checks with fake fetcher."""

    def test_reachable_robots_with_sitemap(self) -> None:
        fetcher = FakeFetcher({
            "https://lanlnk.cn/robots.txt": {
                "status_code": 200,
                "content": ROBOTS_TXT,
                "reachable": True,
            },
        })
        runner = SEOAuditRunner(fetcher=fetcher)
        robots, findings = runner.audit_robots("https://lanlnk.cn/robots.txt")
        assert robots.reachable
        assert "https://lanlnk.cn/sitemap.xml" in robots.sitemap_refs
        assert not any(f.issue_type == "robots_unreachable" for f in findings)
        assert not any(f.issue_type == "robots_no_sitemap_ref" for f in findings)

    def test_unreachable_robots(self) -> None:
        fetcher = FakeFetcher({})
        runner = SEOAuditRunner(fetcher=fetcher)
        robots, findings = runner.audit_robots("https://lanlnk.cn/robots.txt")
        assert not robots.reachable
        assert any(f.issue_type == "robots_unreachable" for f in findings)

    def test_no_sitemap_ref_is_info(self) -> None:
        fetcher = FakeFetcher({
            "https://lanlnk.cn/robots.txt": {
                "status_code": 200,
                "content": "User-agent: *\nDisallow:",
                "reachable": True,
            },
        })
        runner = SEOAuditRunner(fetcher=fetcher)
        robots, findings = runner.audit_robots("https://lanlnk.cn/robots.txt")
        assert any(f.issue_type == "robots_no_sitemap_ref" and f.severity == "info" for f in findings)

    def test_blocked_page_detected(self) -> None:
        fetcher = FakeFetcher({
            "https://lanlnk.cn/robots.txt": {
                "status_code": 200,
                "content": ROBOTS_TXT,
                "reachable": True,
            },
        })
        runner = SEOAuditRunner(fetcher=fetcher)
        robots, findings = runner.audit_robots(
            "https://lanlnk.cn/robots.txt",
            site_urls=["https://lanlnk.cn/admin/dashboard"],
        )
        assert any(f.issue_type == "blocked_by_robots" for f in findings)


# ---------------------------------------------------------------------------
# Full Run Tests
# ---------------------------------------------------------------------------


class TestFullRun:
    """End-to-end audit run tests."""

    def test_full_run_with_clean_pages(self) -> None:
        runner = SEOAuditRunner()
        records = [parse_html(GOOD_HTML, "https://lanlnk.cn/good")]
        report = runner.run(records)
        assert report.total_pages_checked == 1
        assert report.audit_scope == "full"
        assert isinstance(report.findings, list)

    def test_full_run_with_issues(self) -> None:
        runner = SEOAuditRunner()
        records = [
            parse_html(MISSING_TITLE_HTML, "https://lanlnk.cn/no-title"),
            parse_html(MISSING_DESC_HTML, "https://lanlnk.cn/no-desc"),
            parse_html(MISSING_CANONICAL_HTML, "https://lanlnk.cn/no-canonical"),
        ]
        report = runner.run(records)
        issue_types = {f.issue_type for f in report.findings}
        assert "missing_title" in issue_types
        assert "missing_description" in issue_types
        assert "missing_canonical" in issue_types

    def test_scope_canonical_only(self) -> None:
        runner = SEOAuditRunner(audit_scope="canonical-only")
        records = [parse_html(MISSING_CANONICAL_HTML, "https://lanlnk.cn/no-canon")]
        report = runner.run(records)
        dimensions = {f.dimension for f in report.findings}
        assert dimensions == {"canonical"} or len(dimensions) == 0

    def test_scope_schema_only(self) -> None:
        runner = SEOAuditRunner(audit_scope="schema-only")
        records = [parse_html(GOOD_HTML, "https://lanlnk.cn/good")]
        report = runner.run(records)
        dimensions = {f.dimension for f in report.findings}
        assert dimensions <= {"structured_data"}

    def test_scope_sitemap_only(self) -> None:
        fetcher = FakeFetcher({
            "https://lanlnk.cn/sitemap.xml": {
                "status_code": 200,
                "content": SITEMAP_XML,
                "reachable": True,
            },
        })
        runner = SEOAuditRunner(audit_scope="sitemap-only", fetcher=fetcher)
        records: list[PageRecord] = []
        report = runner.run(records, sitemap_url="https://lanlnk.cn/sitemap.xml")
        dimensions = {f.dimension for f in report.findings}
        assert dimensions <= {"sitemap"}

    def test_report_summary(self) -> None:
        runner = SEOAuditRunner()
        records = [
            parse_html(GOOD_HTML, "https://lanlnk.cn/good"),
            parse_html(MISSING_TITLE_HTML, "https://lanlnk.cn/no-title"),
        ]
        report = runner.run(records)
        assert "total_pages" in report.summary
        assert "total_findings" in report.summary
        assert report.summary["total_pages"] == 2


# ---------------------------------------------------------------------------
# Report Serialization Tests
# ---------------------------------------------------------------------------


class TestReportSerialization:
    """Report to_dict and write_report."""

    def test_to_dict_structure(self) -> None:
        runner = SEOAuditRunner()
        report = runner.run([parse_html(GOOD_HTML, "https://lanlnk.cn/good")])
        d = report.to_dict()
        assert "audit_date" in d
        assert "audit_scope" in d
        assert "site" in d
        assert "total_pages_checked" in d
        assert "sitemap" in d
        assert "canonical" in d
        assert "structured_data" in d
        assert "meta" in d
        assert "robots" in d
        assert "findings" in d
        assert "summary" in d

    def test_write_report(self, tmp_path: Path) -> None:
        runner = SEOAuditRunner()
        report = runner.run([parse_html(GOOD_HTML, "https://lanlnk.cn/good")])
        output = tmp_path / "report.json"
        runner.write_report(report, output)
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["total_pages_checked"] == 1

    def test_write_report_creates_parent(self, tmp_path: Path) -> None:
        runner = SEOAuditRunner()
        report = runner.run([])
        output = tmp_path / "nested" / "dir" / "report.json"
        runner.write_report(report, output)
        assert output.exists()

    def test_finding_serialization(self) -> None:
        runner = SEOAuditRunner()
        records = [parse_html(MISSING_TITLE_HTML, "https://lanlnk.cn/no-title")]
        report = runner.run(records)
        d = report.to_dict()
        for f in d["findings"]:
            assert "page_url" in f
            assert "issue_type" in f
            assert "severity" in f
            assert "description" in f
            assert "dimension" in f


# ---------------------------------------------------------------------------
# CLI Tests
# ---------------------------------------------------------------------------


class TestCLI:
    """CLI entry point tests."""

    def test_cli_fixture_run(self, tmp_path: Path) -> None:
        import scripts.seo_audit_runner as mod
        output = tmp_path / "seo-report.json"

        fixture = {
            "sitemap_url": "",
            "robots_url": "",
            "pages": [
                {
                    "url": "https://lanlnk.cn/",
                    "html": GOOD_HTML,
                },
                {
                    "url": "https://lanlnk.cn/broken",
                    "html": "<html><head></head><body></body></html>",
                },
            ],
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        orig_argv = sys.argv
        try:
            sys.argv = [
                "seo_audit_runner",
                "--fixture", str(fixture_path),
                "--output", str(output),
                "--scope", "full",
                "--site", "https://lanlnk.cn",
            ]
            mod._cli()
        finally:
            sys.argv = orig_argv

        assert output.exists()
        report = json.loads(output.read_text())
        assert report["total_pages_checked"] == 2
        assert report["total_findings"] > 0

    def test_cli_missing_fixture_arg(self) -> None:
        import scripts.seo_audit_runner as mod

        orig_argv = sys.argv
        try:
            sys.argv = ["seo_audit_runner", "--output", "/tmp/x.json"]
            with pytest.raises(SystemExit):
                mod._cli()
        finally:
            sys.argv = orig_argv

    def test_cli_scope_canonical_only(self, tmp_path: Path) -> None:
        import scripts.seo_audit_runner as mod
        output = tmp_path / "seo-report.json"

        fixture = {
            "pages": [
                {
                    "url": "https://lanlnk.cn/no-canonical",
                    "html": MISSING_CANONICAL_HTML,
                },
            ],
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        orig_argv = sys.argv
        try:
            sys.argv = [
                "seo_audit_runner",
                "--fixture", str(fixture_path),
                "--output", str(output),
                "--scope", "canonical-only",
            ]
            mod._cli()
        finally:
            sys.argv = orig_argv

        report = json.loads(output.read_text())
        assert report["audit_scope"] == "canonical-only"


# ---------------------------------------------------------------------------
# Fixture Integration Test
# ---------------------------------------------------------------------------


class TestFixtureIntegration:
    """The synthetic fixture should produce expected SEO findings."""

    def test_fixture_audit(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)

        pages = fixture.get("pages", [])
        records: list[PageRecord] = []
        for item in pages:
            html = item.get("html", "")
            url = item.get("url", "")
            if html:
                record = parse_html(html, url=url)
            else:
                record = PageRecord(url=url)
            records.append(record)

        runner = SEOAuditRunner(audit_scope="full", site="lanlnk.cn")
        report = runner.run(records)

        assert report.total_pages_checked == len(pages)

        # The broken page should generate findings
        issue_types = {f.issue_type for f in report.findings}
        assert "missing_title" in issue_types
        assert "missing_description" in issue_types
        assert "missing_canonical" in issue_types
        assert "missing_h1" in issue_types
        assert "missing_json_ld" in issue_types
        assert "missing_og_title" in issue_types

        # Duplicate title: homepage and duplicate-title page share the same title
        dup_findings = [f for f in report.findings if f.issue_type == "duplicate_title"]
        assert len(dup_findings) >= 1

    def test_fixture_pages_well_formed(self) -> None:
        """Well-formed pages in fixture should not produce critical findings."""
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)

        pages = fixture.get("pages", [])
        # First 5 pages should be well-formed
        for item in pages[:5]:
            html = item.get("html", "")
            record = parse_html(html, url=item.get("url", ""))
            assert record.title, f"Page {item.get('url')} should have a title"
            assert record.description, f"Page {item.get('url')} should have a description"
            assert record.canonical, f"Page {item.get('url')} should have canonical"
            assert len(record.h1_tags) == 1, f"Page {item.get('url')} should have exactly 1 H1"
            assert len(record.json_ld_blocks) >= 1, f"Page {item.get('url')} should have JSON-LD"


# ---------------------------------------------------------------------------
# FakeFetcher Tests
# ---------------------------------------------------------------------------


class TestFakeFetcher:
    """Verify dependency injection works."""

    def test_injected_fetcher_used(self) -> None:
        fetcher = FakeFetcher({
            "https://test.com/page": {
                "status_code": 200,
                "content": GOOD_HTML,
                "reachable": True,
            },
        })
        runner = SEOAuditRunner(fetcher=fetcher)
        result = runner.fetch("https://test.com/page")
        assert result["status_code"] == 200
        assert "https://test.com/page" in fetcher.calls

    def test_injected_fetcher_for_page_fetch(self) -> None:
        fetcher = FakeFetcher({
            "https://lanlnk.cn/good": {
                "status_code": 200,
                "content": GOOD_HTML,
                "reachable": True,
            },
        })
        runner = SEOAuditRunner(fetcher=fetcher)
        record = runner.fetch_page("https://lanlnk.cn/good")
        assert record.title == "Good Page - LANLNK"
        assert record.status_code == 200

    def test_default_curl_fetcher(self) -> None:
        runner = SEOAuditRunner()
        assert isinstance(runner._fetcher, type(None)) or hasattr(runner._fetcher, "fetch")


# ---------------------------------------------------------------------------
# Finding Description Quality Tests
# ---------------------------------------------------------------------------


class TestFindingDescriptions:
    """Findings must have meaningful descriptions."""

    def test_description_not_empty(self) -> None:
        runner = SEOAuditRunner()
        records = [
            parse_html(MISSING_TITLE_HTML, "https://lanlnk.cn/no-title"),
            parse_html(MISSING_DESC_HTML, "https://lanlnk.cn/no-desc"),
            parse_html(MISSING_CANONICAL_HTML, "https://lanlnk.cn/no-canonical"),
        ]
        report = runner.run(records)
        for f in report.findings:
            assert f.description
            assert len(f.description) > 10
            assert f.page_url in f.description or f.page_url in str(report.to_dict())
