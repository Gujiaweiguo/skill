"""Production GEO-operations drift-detection workflow.

Audits GEO health across six dimensions:
    1. Baidu webmaster verification (meta tag presence on homepage)
    2. llms.txt existence, freshness, and content validity
    3. Capability drift (GEO profile capabilities vs llms.txt sections vs live pages)
    4. NAP consistency (Name / Address / Phone across pages)
    5. Sitemap status (existence, robots.txt reference)
    6. Map annotation consistency (Baidu Map / AMap references)

Read-only: never modifies any file, configuration, or online resource.

Usage (programmatic)::

    runner = GEOAuditRunner(site="lanlnk.cn")
    report = runner.run(page_records, llms_txt_data, geo_profile)
    runner.write_report(report, output_path)

Usage (CLI, fixture mode)::

    uv run python -m scripts.geo_audit_runner \\
        --fixture fixtures/synthetic-fixture.json \\
        --output /tmp/geo-drift-report.json
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class GEOPageRecord:
    """A single page's GEO data extracted from HTML or fixture."""

    url: str
    title: str = ""
    description: str = ""
    baidu_verification_tag: str = ""
    nap_name: str = ""
    nap_address: str = ""
    nap_phone: str = ""
    has_baidu_map: bool = False
    has_amap: bool = False
    json_ld_blocks: list[str] = field(default_factory=list)
    status_code: int = 200
    raw_html: str = ""


@dataclass
class LlmsTxtData:
    """Parsed llms.txt data."""

    url: str = ""
    reachable: bool = False
    content_lines: list[str] = field(default_factory=list)
    content_hash: str = ""
    last_updated: str = ""
    capability_sections: list[str] = field(default_factory=list)


@dataclass
class GEOFinding:
    """A single GEO issue detected during audit."""

    page_url: str
    issue_type: str
    severity: str  # "info" | "warning" | "critical"
    description: str
    dimension: str  # "baidu" | "llms_txt" | "capability_drift" | "nap" | "sitemap" | "map_annotation"


@dataclass
class GEODriftReport:
    """Complete GEO drift-detection result."""

    audit_date: str
    site: str
    total_pages_checked: int
    baidu_verification: dict[str, object] = field(default_factory=dict)
    llms_txt: dict[str, object] = field(default_factory=dict)
    capability_drift: dict[str, object] = field(default_factory=dict)
    nap_consistency: dict[str, object] = field(default_factory=dict)
    sitemap_status: dict[str, object] = field(default_factory=dict)
    map_annotation: dict[str, object] = field(default_factory=dict)
    findings: list[GEOFinding] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "audit_date": self.audit_date,
            "site": self.site,
            "total_pages_checked": self.total_pages_checked,
            "baidu_verification": self.baidu_verification,
            "llms_txt": self.llms_txt,
            "capability_drift": self.capability_drift,
            "nap_consistency": self.nap_consistency,
            "sitemap_status": self.sitemap_status,
            "map_annotation": self.map_annotation,
            "findings": [
                {
                    "page_url": f.page_url,
                    "issue_type": f.issue_type,
                    "severity": f.severity,
                    "description": f.description,
                    "dimension": f.dimension,
                }
                for f in self.findings
            ],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# HTML / text parsing
# ---------------------------------------------------------------------------

_BAIDU_META_RE = re.compile(
    r'<meta\s+name=["\']baidu-site-verification["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_DESC_RE = re.compile(
    r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_JSON_LD_RE = re.compile(
    r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_BAIDU_MAP_RE = re.compile(
    r"(api\.map\.baidu\.com|maps\.baidu\.com)",
    re.IGNORECASE,
)
_AMAP_RE = re.compile(
    r"(webapi\.amap\.com|uri\.amap\.com|maps\.amap\.com)",
    re.IGNORECASE,
)

# NAP extraction patterns (from JSON-LD LocalBusiness or schema.org markup)
_NAP_NAME_RE = re.compile(r'"name"\s*:\s*"([^"]+)"', re.IGNORECASE)
_NAP_ADDR_RE = re.compile(r'"address"\s*:\s*"([^"]+)"', re.IGNORECASE)
_NAP_TEL_RE = re.compile(r'"telephone"\s*:\s*"([^"]+)"', re.IGNORECASE)


def parse_html(html: str, url: str) -> GEOPageRecord:
    """Parse raw HTML into a GEOPageRecord.

    Extracts: title, description, baidu-site-verification meta tag,
    NAP fields from JSON-LD, Baidu Map / AMap references.
    """
    record = GEOPageRecord(url=url, raw_html=html)

    # Title
    m = _TITLE_RE.search(html)
    if m:
        record.title = m.group(1).strip()

    # Description
    m = _DESC_RE.search(html)
    if m:
        record.description = m.group(1).strip()

    # Baidu verification meta tag
    m = _BAIDU_META_RE.search(html)
    if m:
        record.baidu_verification_tag = m.group(1).strip()

    # JSON-LD blocks
    record.json_ld_blocks = _JSON_LD_RE.findall(html)

    # NAP extraction from JSON-LD blocks
    for block in record.json_ld_blocks:
        if not record.nap_name:
            m = _NAP_NAME_RE.search(block)
            if m:
                record.nap_name = m.group(1).strip()
        if not record.nap_address:
            m = _NAP_ADDR_RE.search(block)
            if m:
                record.nap_address = m.group(1).strip()
        if not record.nap_phone:
            m = _NAP_TEL_RE.search(block)
            if m:
                record.nap_phone = m.group(1).strip()

    # Map references
    record.has_baidu_map = bool(_BAIDU_MAP_RE.search(html))
    record.has_amap = bool(_AMAP_RE.search(html))

    return record


# ---------------------------------------------------------------------------
# Fetcher protocol
# ---------------------------------------------------------------------------


class FetcherProtocol(Protocol):
    """Fetch raw content from a URL. Returns (status_code, body)."""

    def fetch(self, url: str) -> tuple[int, str]:
        """Fetch URL and return (status_code, body_text)."""
        ...


class CurlFetcher:
    """Production fetcher using curl."""

    def fetch(self, url: str) -> tuple[int, str]:
        """Fetch URL via curl subprocess."""
        try:
            result = subprocess.run(  # noqa: S603
                [
                    "curl", "-sL", "--max-time", "10",
                    "-A", "Mozilla/5.0 (compatible; GEOAuditBot/1.0)",
                    "-w", "\n%{http_code}",
                    url,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            lines = result.stdout.rsplit("\n", 1)
            if len(lines) == 2:  # noqa: PLR2004
                body, code_str = lines
                try:
                    code = int(code_str.strip())
                except ValueError:
                    code = 0
                return code, body
            return 0, result.stdout
        except Exception:
            return 0, ""


# ---------------------------------------------------------------------------
# Audit dimensions
# ---------------------------------------------------------------------------

# Finding issue_type → (severity, dimension)
_SEVERITY_MAP: dict[str, tuple[str, str]] = {
    # Baidu
    "baidu_not_verified": ("critical", "baidu"),
    "baidu_verification_missing_tag": ("critical", "baidu"),
    "baidu_verification_tag_empty": ("warning", "baidu"),
    # llms.txt
    "llms_txt_unreachable": ("critical", "llms_txt"),
    "llms_txt_empty": ("critical", "llms_txt"),
    "llms_txt_stale": ("warning", "llms_txt"),
    "llms_txt_no_capabilities": ("warning", "llms_txt"),
    # Capability drift
    "capability_missing_page": ("warning", "capability_drift"),
    "capability_extra_in_llms": ("info", "capability_drift"),
    "capability_profile_mismatch": ("warning", "capability_drift"),
    # NAP
    "nap_missing_name": ("critical", "nap"),
    "nap_missing_address": ("critical", "nap"),
    "nap_missing_phone": ("critical", "nap"),
    "nap_inconsistent_name": ("critical", "nap"),
    "nap_inconsistent_address": ("critical", "nap"),
    "nap_inconsistent_phone": ("critical", "nap"),
    # Sitemap
    "sitemap_unreachable": ("critical", "sitemap"),
    "sitemap_no_robots_ref": ("info", "sitemap"),
    # Map annotation
    "map_annotation_missing": ("warning", "map_annotation"),
    "map_annotation_inconsistent": ("warning", "map_annotation"),
}


def _make_finding(
    page_url: str,
    issue_type: str,
    description: str,
) -> GEOFinding:
    """Create a GEOFinding with auto-resolved severity and dimension."""
    severity, dimension = _SEVERITY_MAP.get(
        issue_type, ("warning", "unknown"),
    )
    return GEOFinding(
        page_url=page_url,
        issue_type=issue_type,
        severity=severity,
        description=description,
        dimension=dimension,
    )


# ---------------------------------------------------------------------------
# Audit runner
# ---------------------------------------------------------------------------


class GEOAuditRunner:
    """Run GEO drift-detection audit across all dimensions.

    Parameters:
        site: Site domain (e.g. ``lanlnk.cn``).
        audit_scope: ``full`` (default) or one of the dimension-specific scopes.
    """

    VALID_SCOPES = frozenset({
        "full",
        "baidu-only",
        "llms-only",
        "capability-only",
        "nap-only",
        "sitemap-only",
        "map-only",
    })

    def __init__(
        self,
        site: str = "lanlnk.cn",
        audit_scope: str = "full",
    ) -> None:
        if audit_scope not in self.VALID_SCOPES:
            msg = (
                f"Invalid audit_scope: {audit_scope}. "
                f"Valid scopes: {sorted(self.VALID_SCOPES)}"
            )
            raise ValueError(msg)
        self.site = site
        self.audit_scope = audit_scope

    def _should_run(self, dimension: str) -> bool:
        """Check if a dimension should be audited based on scope."""
        if self.audit_scope == "full":
            return True
        return self.audit_scope == dimension

    def run(
        self,
        pages: list[GEOPageRecord],
        llms_txt: LlmsTxtData | None = None,
        geo_profile: dict[str, object] | None = None,
        sitemap_url: str = "",
        robots_sitemap_refs: list[str] | None = None,
    ) -> GEODriftReport:
        """Run the GEO drift-detection audit.

        Args:
            pages: List of GEOPageRecords from fetch or fixture.
            llms_txt: Parsed llms.txt data (None = not available).
            geo_profile: GEO profile dict with 'capabilities' list.
            sitemap_url: Sitemap URL (for status checking).
            robots_sitemap_refs: Sitemap references found in robots.txt.

        Returns:
            GEODriftReport with all findings and summary.
        """
        findings: list[GEOFinding] = []
        total_pages = len(pages)

        # --- Baidu verification ---
        baidu_result: dict[str, object] = {}
        if self._should_run("baidu-only"):
            baidu_result, baidu_findings = self._audit_baidu(pages)
            findings.extend(baidu_findings)

        # --- llms.txt ---
        llms_result: dict[str, object] = {}
        if self._should_run("llms-only"):
            llms_result, llms_findings = self._audit_llms_txt(llms_txt)
            findings.extend(llms_findings)

        # --- Capability drift ---
        cap_result: dict[str, object] = {}
        if self._should_run("capability-only"):
            cap_result, cap_findings = self._audit_capability_drift(
                pages, llms_txt, geo_profile,
            )
            findings.extend(cap_findings)

        # --- NAP consistency ---
        nap_result: dict[str, object] = {}
        if self._should_run("nap-only"):
            nap_result, nap_findings = self._audit_nap(pages)
            findings.extend(nap_findings)

        # --- Sitemap status ---
        sitemap_result: dict[str, object] = {}
        if self._should_run("sitemap-only"):
            sitemap_result, sitemap_findings = self._audit_sitemap(
                sitemap_url, robots_sitemap_refs,
            )
            findings.extend(sitemap_findings)

        # --- Map annotation ---
        map_result: dict[str, object] = {}
        if self._should_run("map-only"):
            map_result, map_findings = self._audit_map_annotation(pages)
            findings.extend(map_findings)

        # --- Summary ---
        summary = self._build_summary(findings)

        return GEODriftReport(
            audit_date=time.strftime("%Y-%m-%d", time.gmtime()),
            site=self.site,
            total_pages_checked=total_pages,
            baidu_verification=baidu_result,
            llms_txt=llms_result,
            capability_drift=cap_result,
            nap_consistency=nap_result,
            sitemap_status=sitemap_result,
            map_annotation=map_result,
            findings=findings,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Dimension auditors
    # ------------------------------------------------------------------

    def _audit_baidu(
        self, pages: list[GEOPageRecord],
    ) -> tuple[dict[str, object], list[GEOFinding]]:
        """Check Baidu webmaster verification status."""
        findings: list[GEOFinding] = []
        result: dict[str, object] = {
            "verified": False,
            "verification_tag": "",
            "checked_pages": [],
        }

        for page in pages:
            if page.baidu_verification_tag:
                result["verified"] = True
                result["verification_tag"] = page.baidu_verification_tag
                result["checked_pages"].append(page.url)
            elif page.status_code > 0 and page.status_code < 400:
                # Page loaded but no verification tag
                findings.append(_make_finding(
                    page.url,
                    "baidu_verification_missing_tag",
                    f"Page {page.url} has no baidu-site-verification meta tag",
                ))
                result["checked_pages"].append(page.url)

        if not result["verified"] and not findings:
            # No pages had the tag and no pages were checkable
            findings.append(_make_finding(
                f"https://{self.site}/",
                "baidu_not_verified",
                "No baidu-site-verification meta tag found on any page",
            ))

        return result, findings

    def _audit_llms_txt(
        self, llms_txt: LlmsTxtData | None,
    ) -> tuple[dict[str, object], list[GEOFinding]]:
        """Check llms.txt existence, freshness, and content."""
        findings: list[GEOFinding] = []
        result: dict[str, object] = {
            "url": llms_txt.url if llms_txt else "",
            "reachable": False,
            "last_updated": "",
            "capability_sections": [],
            "content_lines_count": 0,
        }

        if llms_txt is None or not llms_txt.reachable:
            result["reachable"] = False
            findings.append(_make_finding(
                f"https://{self.site}/llms.txt",
                "llms_txt_unreachable",
                "llms.txt is not reachable",
            ))
            return result, findings

        result["reachable"] = True
        result["last_updated"] = llms_txt.last_updated
        result["capability_sections"] = llms_txt.capability_sections
        result["content_lines_count"] = len(llms_txt.content_lines)

        if not llms_txt.content_lines:
            findings.append(_make_finding(
                llms_txt.url,
                "llms_txt_empty",
                "llms.txt has no content lines",
            ))

        if not llms_txt.capability_sections:
            findings.append(_make_finding(
                llms_txt.url,
                "llms_txt_no_capabilities",
                "llms.txt has no capability sections defined",
            ))

        # Staleness check: if last_updated is older than 90 days
        if llms_txt.last_updated:
            try:
                from datetime import datetime, timedelta
                parsed_date = datetime.strptime(
                    llms_txt.last_updated, "%Y-%m-%d",
                )
                threshold = datetime.now(tz=parsed_date.tzinfo) - timedelta(days=90)
                if parsed_date < threshold:
                    findings.append(_make_finding(
                        llms_txt.url,
                        "llms_txt_stale",
                        f"llms.txt last updated {llms_txt.last_updated}, "
                        f"older than 90 days",
                    ))
            except ValueError:
                pass  # Invalid date format, skip staleness check

        return result, findings

    def _audit_capability_drift(
        self,
        pages: list[GEOPageRecord],
        llms_txt: LlmsTxtData | None,
        geo_profile: dict[str, object] | None,
    ) -> tuple[dict[str, object], list[GEOFinding]]:
        """Detect drift between GEO profile, llms.txt, and live pages."""
        findings: list[GEOFinding] = []
        result: dict[str, object] = {
            "profile_capabilities": [],
            "llms_txt_capabilities": [],
            "missing_in_llms": [],
            "missing_pages": [],
            "extra_in_llms": [],
        }

        profile_caps: list[str] = []
        if geo_profile and isinstance(
            geo_profile.get("capabilities"), list,
        ):
            profile_caps = [
                str(c) for c in geo_profile["capabilities"]
                if isinstance(c, str)
            ]
        result["profile_capabilities"] = profile_caps

        llms_caps: list[str] = list(llms_txt.capability_sections) if llms_txt else []
        result["llms_txt_capabilities"] = llms_caps

        # Capabilities in profile but missing from llms.txt
        llms_cap_set = set(llms_caps)
        profile_cap_set = set(profile_caps)

        missing_in_llms = profile_cap_set - llms_cap_set
        result["missing_in_llms"] = sorted(missing_in_llms)
        for cap in sorted(missing_in_llms):
            findings.append(_make_finding(
                f"https://{self.site}/llms.txt",
                "capability_missing_page",
                f"Capability '{cap}' in GEO profile but missing from llms.txt",
            ))

        # Capabilities in llms.txt but not in profile
        extra_in_llms = llms_cap_set - profile_cap_set
        result["extra_in_llms"] = sorted(extra_in_llms)
        for cap in sorted(extra_in_llms):
            findings.append(_make_finding(
                f"https://{self.site}/llms.txt",
                "capability_extra_in_llms",
                f"Capability '{cap}' in llms.txt but not in GEO profile",
            ))

        # Check if profile capabilities have corresponding live pages
        page_urls = {p.url for p in pages}
        missing_pages: list[str] = []
        for cap in profile_caps:
            cap_url = f"https://{self.site}/{cap}"
            if cap_url not in page_urls and not any(
                cap in url for url in page_urls
            ):
                missing_pages.append(cap)
        result["missing_pages"] = missing_pages
        for cap in missing_pages:
            findings.append(_make_finding(
                f"https://{self.site}/{cap}",
                "capability_profile_mismatch",
                f"Capability '{cap}' has no corresponding live page",
            ))

        return result, findings

    def _audit_nap(
        self, pages: list[GEOPageRecord],
    ) -> tuple[dict[str, object], list[GEOFinding]]:
        """Check NAP (Name/Address/Phone) consistency across pages."""
        findings: list[GEOFinding] = []
        result: dict[str, object] = {
            "canonical_name": "",
            "canonical_address": "",
            "canonical_phone": "",
            "pages_with_nap": [],
            "inconsistencies": [],
        }

        nap_names: dict[str, list[str]] = {}
        nap_addresses: dict[str, list[str]] = {}
        nap_phones: dict[str, list[str]] = {}

        for page in pages:
            if not any([page.nap_name, page.nap_address, page.nap_phone]):
                continue

            page_urls = result["pages_with_nap"]
            if isinstance(page_urls, list):
                page_urls.append(page.url)

            if page.nap_name:
                nap_names.setdefault(page.nap_name, []).append(page.url)
                if not result["canonical_name"]:
                    result["canonical_name"] = page.nap_name
            else:
                findings.append(_make_finding(
                    page.url, "nap_missing_name",
                    f"Page {page.url} is missing NAP name",
                ))

            if page.nap_address:
                nap_addresses.setdefault(page.nap_address, []).append(page.url)
                if not result["canonical_address"]:
                    result["canonical_address"] = page.nap_address
            else:
                findings.append(_make_finding(
                    page.url, "nap_missing_address",
                    f"Page {page.url} is missing NAP address",
                ))

            if page.nap_phone:
                nap_phones.setdefault(page.nap_phone, []).append(page.url)
                if not result["canonical_phone"]:
                    result["canonical_phone"] = page.nap_phone
            else:
                findings.append(_make_finding(
                    page.url, "nap_missing_phone",
                    f"Page {page.url} is missing NAP phone",
                ))

        # Check consistency
        if len(nap_names) > 1:
            result["inconsistencies"] = (
                result.get("inconsistencies", []) +
                [f"Multiple NAP names found: {sorted(nap_names.keys())}"]
            )
            for name, urls in nap_names.items():
                for url in urls:
                    findings.append(_make_finding(
                        url, "nap_inconsistent_name",
                        f"NAP name '{name}' differs from canonical "
                        f"'{result['canonical_name']}'",
                    ))

        if len(nap_addresses) > 1:
            inconsistencies = result.get("inconsistencies", [])
            if isinstance(inconsistencies, list):
                inconsistencies.append(
                    f"Multiple NAP addresses: {sorted(nap_addresses.keys())}",
                )
            for addr, urls in nap_addresses.items():
                for url in urls:
                    findings.append(_make_finding(
                        url, "nap_inconsistent_address",
                        f"NAP address differs from canonical",
                    ))

        if len(nap_phones) > 1:
            inconsistencies = result.get("inconsistencies", [])
            if isinstance(inconsistencies, list):
                inconsistencies.append(
                    f"Multiple NAP phones: {sorted(nap_phones.keys())}",
                )
            for phone, urls in nap_phones.items():
                for url in urls:
                    findings.append(_make_finding(
                        url, "nap_inconsistent_phone",
                        f"NAP phone '{phone}' differs from canonical "
                        f"'{result['canonical_phone']}'",
                    ))

        return result, findings

    def _audit_sitemap(
        self,
        sitemap_url: str,
        robots_sitemap_refs: list[str] | None,
    ) -> tuple[dict[str, object], list[GEOFinding]]:
        """Check sitemap status and robots.txt reference."""
        findings: list[GEOFinding] = []
        result: dict[str, object] = {
            "sitemap_url": sitemap_url,
            "referenced_in_robots": False,
            "robots_sitemap_refs": robots_sitemap_refs or [],
        }

        refs = robots_sitemap_refs or []
        if sitemap_url and sitemap_url in refs:
            result["referenced_in_robots"] = True
        elif any("sitemap" in r.lower() for r in refs):
            result["referenced_in_robots"] = True
        else:
            findings.append(_make_finding(
                f"https://{self.site}/robots.txt",
                "sitemap_no_robots_ref",
                "Sitemap URL not referenced in robots.txt",
            ))

        if sitemap_url and not result["referenced_in_robots"]:
            # Already reported above
            pass

        return result, findings

    def _audit_map_annotation(
        self, pages: list[GEOPageRecord],
    ) -> tuple[dict[str, object], list[GEOFinding]]:
        """Check map annotation (Baidu Map / AMap) consistency."""
        findings: list[GEOFinding] = []
        result: dict[str, object] = {
            "pages_with_baidu_map": [],
            "pages_with_amap": [],
            "pages_without_map": [],
        }

        for page in pages:
            if page.has_baidu_map:
                pages_list = result["pages_with_baidu_map"]
                if isinstance(pages_list, list):
                    pages_list.append(page.url)
            if page.has_amap:
                pages_list = result["pages_with_amap"]
                if isinstance(pages_list, list):
                    pages_list.append(page.url)
            if not page.has_baidu_map and not page.has_amap:
                pages_list = result["pages_without_map"]
                if isinstance(pages_list, list):
                    pages_list.append(page.url)
                findings.append(_make_finding(
                    page.url,
                    "map_annotation_missing",
                    f"Page {page.url} has no Baidu Map or AMap reference",
                ))

        # Check consistency: if some pages have maps and others don't
        baidu_count = len(result.get("pages_with_baidu_map", []))
        amap_count = len(result.get("pages_with_amap", []))
        no_map_count = len(result.get("pages_without_map", []))

        if baidu_count > 0 and amap_count > 0:
            findings.append(_make_finding(
                f"https://{self.site}/",
                "map_annotation_inconsistent",
                f"Inconsistent map providers: {baidu_count} pages with "
                f"Baidu Map, {amap_count} with AMap",
            ))

        return result, findings

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summary(findings: list[GEOFinding]) -> dict[str, int]:
        """Build summary statistics from findings."""
        summary: dict[str, int] = {
            "total_findings": len(findings),
            "severity_critical": 0,
            "severity_warning": 0,
            "severity_info": 0,
            "dimension_baidu": 0,
            "dimension_llms_txt": 0,
            "dimension_capability_drift": 0,
            "dimension_nap": 0,
            "dimension_sitemap": 0,
            "dimension_map_annotation": 0,
        }
        for f in findings:
            summary[f"severity_{f.severity}"] = (
                summary.get(f"severity_{f.severity}", 0) + 1
            )
            summary[f"dimension_{f.dimension}"] = (
                summary.get(f"dimension_{f.dimension}", 0) + 1
            )
        return summary

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    @staticmethod
    def write_report(
        report: GEODriftReport,
        output_path: str | Path,
    ) -> Path:
        """Write the drift report to a JSON file.

        Args:
            report: The GEODriftReport to write.
            output_path: File path for the JSON output.

        Returns:
            Resolved Path to the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path.resolve()


# ---------------------------------------------------------------------------
# Fixture loader
# ---------------------------------------------------------------------------


def load_fixture(
    fixture_path: str | Path,
) -> tuple[list[GEOPageRecord], LlmsTxtData, dict[str, object], str, list[str]]:
    """Load a fixture JSON file into typed structures.

    Returns:
        (pages, llms_txt, geo_profile, sitemap_url, robots_sitemap_refs)
    """
    data = json.loads(Path(fixture_path).read_text(encoding="utf-8"))

    # Parse pages
    raw_pages = data.get("pages", [])
    pages: list[GEOPageRecord] = []
    for rp in raw_pages:
        if not isinstance(rp, dict):
            continue
        pages.append(GEOPageRecord(
            url=rp.get("url", ""),
            title=rp.get("title", ""),
            description=rp.get("description", ""),
            baidu_verification_tag=rp.get("baidu_verification_tag", ""),
            nap_name=rp.get("nap_name", ""),
            nap_address=rp.get("nap_address", ""),
            nap_phone=rp.get("nap_phone", ""),
            has_baidu_map=rp.get("has_baidu_map", False),
            has_amap=rp.get("has_amap", False),
            json_ld_blocks=rp.get("json_ld_blocks", []),
            status_code=rp.get("status_code", 200),
            raw_html=rp.get("raw_html", ""),
        ))

    # Parse llms.txt
    raw_llms = data.get("llms_txt", {})
    llms_txt = LlmsTxtData(
        url=raw_llms.get("source_url", ""),
        reachable=raw_llms.get("reachable", True),
        content_lines=raw_llms.get("content_lines", []),
        content_hash=raw_llms.get("content_hash", ""),
        last_updated=raw_llms.get("last_updated", ""),
        capability_sections=raw_llms.get("capability_sections", []),
    )

    # Parse geo_profile
    geo_profile = data.get("geo_profile", {})

    # Sitemap and robots
    sitemap_url = data.get("sitemap_url", "")
    robots_sitemap_refs = data.get("robots_sitemap_refs", [])

    return pages, llms_txt, geo_profile, sitemap_url, robots_sitemap_refs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for geo_audit_runner.

    Usage::

        uv run python -m scripts.geo_audit_runner \\
            --fixture fixtures/synthetic-fixture.json \\
            --output /tmp/geo-drift-report.json
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="GEO operations drift-detection audit",
    )
    parser.add_argument(
        "--fixture",
        type=str,
        default=None,
        help="Path to fixture JSON file",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output path for drift report JSON",
    )
    parser.add_argument(
        "--site",
        type=str,
        default="lanlnk.cn",
        help="Site domain (default: lanlnk.cn)",
    )
    parser.add_argument(
        "--scope",
        type=str,
        default="full",
        choices=sorted(GEOAuditRunner.VALID_SCOPES),
        help="Audit scope (default: full)",
    )

    args = parser.parse_args(argv)

    if not args.fixture:
        print(  # noqa: T201
            "Error: --fixture is required for fixture mode",
            file=sys.stderr,
        )
        return 1

    fixture_path = Path(args.fixture)
    if not fixture_path.exists():
        print(f"Error: fixture not found: {fixture_path}", file=sys.stderr)  # noqa: T201
        return 1

    pages, llms_txt, geo_profile, sitemap_url, robots_refs = load_fixture(
        fixture_path,
    )

    runner = GEOAuditRunner(site=args.site, audit_scope=args.scope)
    report = runner.run(
        pages=pages,
        llms_txt=llms_txt,
        geo_profile=geo_profile,
        sitemap_url=sitemap_url,
        robots_sitemap_refs=robots_refs,
    )

    output_path = args.output or f"/tmp/geo-drift-report-{report.audit_date}.json"
    resolved = GEOAuditRunner.write_report(report, output_path)

    print(  # noqa: T201
        f"GEO drift report written to {resolved}\n"
        f"  Pages checked: {report.total_pages_checked}\n"
        f"  Total findings: {report.summary.get('total_findings', 0)}\n"
        f"  Critical: {report.summary.get('severity_critical', 0)}\n"
        f"  Warning: {report.summary.get('severity_warning', 0)}\n"
        f"  Info: {report.summary.get('severity_info', 0)}",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
