"""Production SEO-audit workflow.

Audits SEO health across four dimensions:
    1. Sitemap completeness (sitemap.xml existence, URL count, broken URLs)
    2. Canonical consistency (canonical tags vs page URLs)
    3. Structured data validation (JSON-LD presence and validity)
    4. Meta uniqueness (duplicate titles and descriptions)

Also checks: robots.txt existence, Open Graph tags, H1 uniqueness.

Read-only: never modifies any file, configuration, or online resource.

Usage (programmatic)::

    runner = SEOAuditRunner(audit_scope="full")
    report = runner.run(page_records)
    runner.write_report(report, output_path)

Usage (CLI, fixture mode)::

    uv run python -m scripts.seo_audit_runner \\
        --fixture fixtures/synthetic-fixture.json \\
        --output /tmp/seo-drift-report.json
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
from urllib.parse import urljoin, urlparse

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class PageRecord:
    """A single page's SEO data extracted from HTML or API."""

    url: str
    title: str = ""
    description: str = ""
    canonical: str = ""
    h1_tags: list[str] = field(default_factory=list)
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    json_ld_blocks: list[str] = field(default_factory=list)
    meta_robots: str = ""
    status_code: int = 200
    raw_html: str = ""


@dataclass
class SitemapData:
    """Parsed sitemap.xml data."""

    url: str = ""
    total_urls: int = 0
    entries: list[dict[str, str]] = field(default_factory=list)
    reachable: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class RobotsData:
    """Parsed robots.txt data."""

    url: str = ""
    reachable: bool = False
    sitemap_refs: list[str] = field(default_factory=list)
    disallowed_paths: list[str] = field(default_factory=list)
    raw_content: str = ""


@dataclass
class SEOFinding:
    """A single SEO issue detected during audit."""

    page_url: str
    issue_type: str
    severity: str  # "info" | "warning" | "critical"
    description: str
    dimension: str  # "sitemap" | "canonical" | "structured_data" | "meta" | "robots" | "og"


@dataclass
class SEOAuditReport:
    """Complete SEO audit result."""

    audit_date: str
    audit_scope: str
    site: str
    total_pages_checked: int
    sitemap: dict[str, object] = field(default_factory=dict)
    canonical: dict[str, object] = field(default_factory=dict)
    structured_data: dict[str, object] = field(default_factory=dict)
    meta: dict[str, object] = field(default_factory=dict)
    robots: dict[str, object] = field(default_factory=dict)
    findings: list[SEOFinding] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "audit_date": self.audit_date,
            "audit_scope": self.audit_scope,
            "site": self.site,
            "total_pages_checked": self.total_pages_checked,
            "sitemap": self.sitemap,
            "canonical": self.canonical,
            "structured_data": self.structured_data,
            "meta": self.meta,
            "robots": self.robots,
            "total_findings": len(self.findings),
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
# Fetch protocol (for dependency injection)
# ---------------------------------------------------------------------------


class FetcherProtocol(Protocol):
    """Fetch a URL and return its content. Read-only."""

    def fetch(self, url: str) -> dict[str, object]:
        """Return ``{"status_code": int, "content": str, "reachable": bool}``."""
        ...


# ---------------------------------------------------------------------------
# Built-in curl-based fetcher
# ---------------------------------------------------------------------------


class CurlFetcher:
    """Fetch URLs via the system ``curl`` binary. Read-only."""

    def __init__(self, *, timeout: int = 15, follow: bool = True) -> None:
        self._timeout = timeout
        self._follow = follow

    def fetch(self, url: str) -> dict[str, object]:
        """Fetch a single URL via curl.

        Returns ``{"status_code": int, "content": str, "reachable": bool}``.
        """
        cmd = [
            "curl",
            "-s",
            "-w",
            "\n%{http_code}",
            "--max-time",
            str(self._timeout),
        ]
        if self._follow:
            cmd.append("--location")
        cmd.append(url)

        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout + 5,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {
                "status_code": 0,
                "content": "",
                "reachable": False,
            }

        output = result.stdout
        # Last line is the HTTP status code
        lines = output.rsplit("\n", 1)
        if len(lines) == 2 and lines[1].isdigit():
            content = lines[0]
            status_code = int(lines[1])
        else:
            content = output
            status_code = 0

        return {
            "status_code": status_code,
            "content": content,
            "reachable": status_code > 0,
        }


# ---------------------------------------------------------------------------
# HTML parsers
# ---------------------------------------------------------------------------

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_META_DESC_RE_ALT = re.compile(
    r'<meta\s+[^>]*content=["\'](.*?)["\'][^>]*name=["\']description["\']',
    re.IGNORECASE | re.DOTALL,
)
_CANONICAL_RE = re.compile(
    r'<link\s+[^>]*rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_CANONICAL_RE_ALT = re.compile(
    r'<link\s+[^>]*href=["\'](.*?)["\'][^>]*rel=["\']canonical["\']',
    re.IGNORECASE | re.DOTALL,
)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_OG_TITLE_RE = re.compile(
    r'<meta\s+[^>]*property=["\']og:title["\'][^>]*content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_OG_DESC_RE = re.compile(
    r'<meta\s+[^>]*property=["\']og:description["\'][^>]*content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_OG_IMAGE_RE = re.compile(
    r'<meta\s+[^>]*property=["\']og:image["\'][^>]*content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_META_ROBOTS_RE = re.compile(
    r'<meta\s+[^>]*name=["\']robots["\'][^>]*content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_JSON_LD_RE = re.compile(
    r'<script\s+[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def _strip_tags(text: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_html(html: str, url: str = "") -> PageRecord:
    """Parse raw HTML into a PageRecord.

    Extracts: title, meta description, canonical, H1 tags,
    Open Graph tags, JSON-LD blocks, meta robots.
    """
    def _first(patterns: tuple[re.Pattern[str], ...]) -> str:
        for pat in patterns:
            match = pat.search(html)
            if match:
                return _strip_tags(match.group(1))
        return ""

    title = _first((_TITLE_RE,))
    description = _first((_META_DESC_RE, _META_DESC_RE_ALT))
    canonical = _first((_CANONICAL_RE, _CANONICAL_RE_ALT))
    og_title = _first((_OG_TITLE_RE,))
    og_description = _first((_OG_DESC_RE,))
    og_image = _first((_OG_IMAGE_RE,))
    meta_robots = _first((_META_ROBOTS_RE,))

    h1_tags = [_strip_tags(m.group(1)) for m in _H1_RE.finditer(html)]

    json_ld_matches = _JSON_LD_RE.findall(html)
    json_ld_blocks: list[str] = []
    for block in json_ld_matches:
        block = block.strip()
        if block:
            json_ld_blocks.append(block)

    return PageRecord(
        url=url,
        title=title,
        description=description,
        canonical=canonical,
        h1_tags=h1_tags,
        og_title=og_title,
        og_description=og_description,
        og_image=og_image,
        json_ld_blocks=json_ld_blocks,
        meta_robots=meta_robots,
        raw_html=html,
    )


# ---------------------------------------------------------------------------
# Sitemap parser
# ---------------------------------------------------------------------------

_URL_LOC_RE = re.compile(r"<loc>(.*?)</loc>", re.IGNORECASE)


def parse_sitemap(content: str, sitemap_url: str = "") -> SitemapData:
    """Parse sitemap.xml content into SitemapData."""
    entries: list[dict[str, str]] = []
    locs = _URL_LOC_RE.findall(content)

    for loc in locs:
        loc = loc.strip()
        # Strip namespace if present (e.g. xmlns smuggling)
        loc = loc.replace(" ", "")
        if loc.startswith("http"):
            entries.append({"loc": loc})

    return SitemapData(
        url=sitemap_url,
        total_urls=len(entries),
        entries=entries,
        reachable=bool(content.strip()),
        errors=[],
    )


# ---------------------------------------------------------------------------
# Robots.txt parser
# ---------------------------------------------------------------------------


def parse_robots(content: str, robots_url: str = "") -> RobotsData:
    """Parse robots.txt content into RobotsData."""
    sitemap_refs: list[str] = []
    disallowed_paths: list[str] = []

    for line in content.splitlines():
        line = line.strip()
        if line.lower().startswith("sitemap:"):
            sitemap_refs.append(line.split(":", 1)[1].strip())
        elif line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path:
                disallowed_paths.append(path)

    return RobotsData(
        url=robots_url,
        reachable=bool(content.strip()),
        sitemap_refs=sitemap_refs,
        disallowed_paths=disallowed_paths,
        raw_content=content,
    )


# ---------------------------------------------------------------------------
# JSON-LD validation
# ---------------------------------------------------------------------------


def validate_json_ld(block: str) -> list[str]:
    """Validate a single JSON-LD block.

    Returns a list of error messages (empty if valid).
    """
    errors: list[str] = []
    try:
        data = json.loads(block)
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON: {exc}")
        return errors

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            items = data["@graph"]
        else:
            items = [data]
    else:
        errors.append("JSON-LD must be an object or array of objects")
        return errors

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"Item {i}: not a JSON object")
            continue
        if "@type" not in item:
            errors.append(f"Item {i}: missing @type")

    return errors


# ---------------------------------------------------------------------------
# Core audit logic
# ---------------------------------------------------------------------------

VALID_AUDIT_SCOPES = frozenset({
    "full",
    "sitemap-only",
    "canonical-only",
    "schema-only",
})

_SEVERITY_MAP: dict[str, str] = {
    "missing_title": "critical",
    "empty_title": "critical",
    "title_too_long": "warning",
    "title_too_short": "warning",
    "duplicate_title": "warning",
    "missing_description": "critical",
    "empty_description": "critical",
    "description_too_long": "warning",
    "description_too_short": "warning",
    "duplicate_description": "warning",
    "missing_canonical": "warning",
    "canonical_mismatch": "critical",
    "canonical_empty": "warning",
    "multiple_h1": "warning",
    "missing_h1": "warning",
    "missing_json_ld": "warning",
    "invalid_json_ld": "critical",
    "missing_og_title": "warning",
    "missing_og_description": "warning",
    "missing_og_image": "warning",
    "sitemap_unreachable": "critical",
    "sitemap_empty": "critical",
    "sitemap_missing_url": "warning",
    "robots_unreachable": "warning",
    "robots_no_sitemap_ref": "info",
    "blocked_by_robots": "critical",
}


class SEOAuditRunner:
    """Orchestrates the SEO audit workflow.

    Read-only. Never modifies any file, URL, or configuration.
    """

    def __init__(
        self,
        audit_scope: str = "full",
        site: str = "",
        fetcher: FetcherProtocol | None = None,
    ) -> None:
        if audit_scope not in VALID_AUDIT_SCOPES:
            msg = f"invalid audit_scope: {audit_scope}"
            raise ValueError(msg)
        self.audit_scope = audit_scope
        self.site = site
        self._fetcher = fetcher

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def fetch(self, url: str) -> dict[str, object]:
        """Fetch a URL. Uses injected fetcher or curl."""
        if self._fetcher is not None:
            return self._fetcher.fetch(url)
        return CurlFetcher().fetch(url)

    def fetch_page(self, url: str) -> PageRecord:
        """Fetch a page and parse it into a PageRecord."""
        result = self.fetch(url)
        content = str(result.get("content", ""))
        status_code = int(result.get("status_code", 0))

        record = parse_html(content, url=url)
        record.status_code = status_code
        return record

    def fetch_sitemap(self, sitemap_url: str) -> SitemapData:
        """Fetch and parse sitemap.xml."""
        result = self.fetch(sitemap_url)
        content = str(result.get("content", ""))
        reachable = bool(result.get("reachable", False))

        if not reachable or not content.strip():
            return SitemapData(
                url=sitemap_url,
                total_urls=0,
                entries=[],
                reachable=False,
                errors=[f"Sitemap not reachable at {sitemap_url}"],
            )

        return parse_sitemap(content, sitemap_url)

    def fetch_robots(self, robots_url: str) -> RobotsData:
        """Fetch and parse robots.txt."""
        result = self.fetch(robots_url)
        content = str(result.get("content", ""))
        reachable = bool(result.get("reachable", False))

        if not reachable or not content.strip():
            return RobotsData(
                url=robots_url,
                reachable=False,
            )

        return parse_robots(content, robots_url)

    # ------------------------------------------------------------------
    # Dimension: Sitemap
    # ------------------------------------------------------------------

    def audit_sitemap(
        self,
        sitemap_url: str,
        known_urls: list[str] | None = None,
    ) -> tuple[SitemapData, list[SEOFinding]]:
        """Audit sitemap completeness."""
        findings: list[SEOFinding] = []
        sitemap = self.fetch_sitemap(sitemap_url)

        if not sitemap.reachable:
            findings.append(SEOFinding(
                page_url=sitemap_url,
                issue_type="sitemap_unreachable",
                severity=_SEVERITY_MAP["sitemap_unreachable"],
                description=f"Sitemap at {sitemap_url} is not reachable",
                dimension="sitemap",
            ))
            return sitemap, findings

        if sitemap.total_urls == 0:
            findings.append(SEOFinding(
                page_url=sitemap_url,
                issue_type="sitemap_empty",
                severity=_SEVERITY_MAP["sitemap_empty"],
                description=f"Sitemap at {sitemap_url} contains no URLs",
                dimension="sitemap",
            ))
            return sitemap, findings

        # Check for missing URLs if known_urls provided
        if known_urls:
            sitemap_locs = {e["loc"] for e in sitemap.entries}
            for url in known_urls:
                if url not in sitemap_locs:
                    findings.append(SEOFinding(
                        page_url=url,
                        issue_type="sitemap_missing_url",
                        severity=_SEVERITY_MAP["sitemap_missing_url"],
                        description=f"URL {url} is missing from sitemap",
                        dimension="sitemap",
                    ))

        return sitemap, findings

    # ------------------------------------------------------------------
    # Dimension: Canonical
    # ------------------------------------------------------------------

    def audit_canonical(self, records: list[PageRecord]) -> list[SEOFinding]:
        """Audit canonical tag consistency."""
        findings: list[SEOFinding] = []

        for record in records:
            if not record.canonical:
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="missing_canonical",
                    severity=_SEVERITY_MAP["missing_canonical"],
                    description=f"Page {record.url} has no canonical tag",
                    dimension="canonical",
                ))
            elif record.canonical.strip() == "":
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="canonical_empty",
                    severity=_SEVERITY_MAP["canonical_empty"],
                    description=f"Page {record.url} has an empty canonical tag",
                    dimension="canonical",
                ))
            else:
                # Check canonical matches page URL (or is a self-referencing canonical)
                canonical_clean = record.canonical.strip().rstrip("/")
                url_clean = record.url.strip().rstrip("/")
                if canonical_clean and url_clean and canonical_clean != url_clean:
                    # Not necessarily an error — canonical may point to a preferred version
                    # Only flag if canonical points to a different domain
                    canonical_domain = urlparse(record.canonical).netloc
                    page_domain = urlparse(record.url).netloc
                    if canonical_domain and page_domain and canonical_domain != page_domain:
                        findings.append(SEOFinding(
                            page_url=record.url,
                            issue_type="canonical_mismatch",
                            severity=_SEVERITY_MAP["canonical_mismatch"],
                            description=(
                                f"Page {record.url} canonical points to different domain: "
                                f"{record.canonical}"
                            ),
                            dimension="canonical",
                        ))

        return findings

    # ------------------------------------------------------------------
    # Dimension: Structured Data
    # ------------------------------------------------------------------

    def audit_structured_data(self, records: list[PageRecord]) -> list[SEOFinding]:
        """Audit JSON-LD structured data validity."""
        findings: list[SEOFinding] = []

        for record in records:
            if not record.json_ld_blocks:
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="missing_json_ld",
                    severity=_SEVERITY_MAP["missing_json_ld"],
                    description=f"Page {record.url} has no JSON-LD structured data",
                    dimension="structured_data",
                ))
                continue

            for i, block in enumerate(record.json_ld_blocks):
                errors = validate_json_ld(block)
                for err in errors:
                    findings.append(SEOFinding(
                        page_url=record.url,
                        issue_type="invalid_json_ld",
                        severity=_SEVERITY_MAP["invalid_json_ld"],
                        description=f"Page {record.url} JSON-LD block {i}: {err}",
                        dimension="structured_data",
                    ))

        return findings

    # ------------------------------------------------------------------
    # Dimension: Meta tags
    # ------------------------------------------------------------------

    def audit_meta(self, records: list[PageRecord]) -> tuple[list[SEOFinding], dict[str, list[str]]]:
        """Audit meta tags: titles, descriptions, H1 uniqueness."""
        findings: list[SEOFinding] = []

        # Title checks
        title_map: dict[str, list[str]] = {}
        for record in records:
            if not record.title:
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="missing_title",
                    severity=_SEVERITY_MAP["missing_title"],
                    description=f"Page {record.url} has no <title> tag",
                    dimension="meta",
                ))
            elif record.title.strip() == "":
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="empty_title",
                    severity=_SEVERITY_MAP["empty_title"],
                    description=f"Page {record.url} has an empty title",
                    dimension="meta",
                ))
            else:
                if len(record.title) > 60:
                    findings.append(SEOFinding(
                        page_url=record.url,
                        issue_type="title_too_long",
                        severity=_SEVERITY_MAP["title_too_long"],
                        description=(
                            f"Page {record.url} title is {len(record.title)} chars "
                            f"(recommended max 60): \"{record.title[:50]}...\""
                        ),
                        dimension="meta",
                    ))
                if len(record.title) < 10:
                    findings.append(SEOFinding(
                        page_url=record.url,
                        issue_type="title_too_short",
                        severity=_SEVERITY_MAP["title_too_short"],
                        description=(
                            f"Page {record.url} title is only {len(record.title)} chars "
                            f"(recommended min 10)"
                        ),
                        dimension="meta",
                    ))
                title_map.setdefault(record.title, []).append(record.url)

        # Description checks
        desc_map: dict[str, list[str]] = {}
        for record in records:
            if not record.description:
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="missing_description",
                    severity=_SEVERITY_MAP["missing_description"],
                    description=f"Page {record.url} has no meta description",
                    dimension="meta",
                ))
            elif record.description.strip() == "":
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="empty_description",
                    severity=_SEVERITY_MAP["empty_description"],
                    description=f"Page {record.url} has an empty meta description",
                    dimension="meta",
                ))
            else:
                if len(record.description) > 160:
                    findings.append(SEOFinding(
                        page_url=record.url,
                        issue_type="description_too_long",
                        severity=_SEVERITY_MAP["description_too_long"],
                        description=(
                            f"Page {record.url} description is {len(record.description)} chars "
                            f"(recommended max 160)"
                        ),
                        dimension="meta",
                    ))
                if len(record.description) < 50:
                    findings.append(SEOFinding(
                        page_url=record.url,
                        issue_type="description_too_short",
                        severity=_SEVERITY_MAP["description_too_short"],
                        description=(
                            f"Page {record.url} description is only {len(record.description)} chars "
                            f"(recommended min 50)"
                        ),
                        dimension="meta",
                    ))
                desc_map.setdefault(record.description, []).append(record.url)

        # Duplicate titles
        duplicates: dict[str, list[str]] = {}
        for title, urls in title_map.items():
            if len(urls) > 1:
                duplicates[title] = urls
                findings.append(SEOFinding(
                    page_url=urls[0],
                    issue_type="duplicate_title",
                    severity=_SEVERITY_MAP["duplicate_title"],
                    description=(
                        f"Duplicate title \"{title[:40]}...\" used on {len(urls)} pages: "
                        f"{', '.join(urls[:5])}"
                    ),
                    dimension="meta",
                ))

        # Duplicate descriptions
        dup_descs: dict[str, list[str]] = {}
        for desc, urls in desc_map.items():
            if len(urls) > 1:
                dup_descs[desc] = urls
                findings.append(SEOFinding(
                    page_url=urls[0],
                    issue_type="duplicate_description",
                    severity=_SEVERITY_MAP["duplicate_description"],
                    description=(
                        f"Duplicate description used on {len(urls)} pages: "
                        f"{', '.join(urls[:5])}"
                    ),
                    dimension="meta",
                ))

        # H1 checks
        for record in records:
            if len(record.h1_tags) == 0:
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="missing_h1",
                    severity=_SEVERITY_MAP["missing_h1"],
                    description=f"Page {record.url} has no H1 tag",
                    dimension="meta",
                ))
            elif len(record.h1_tags) > 1:
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="multiple_h1",
                    severity=_SEVERITY_MAP["multiple_h1"],
                    description=(
                        f"Page {record.url} has {len(record.h1_tags)} H1 tags "
                        f"(should have exactly 1)"
                    ),
                    dimension="meta",
                ))

        # Open Graph checks
        for record in records:
            if not record.og_title:
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="missing_og_title",
                    severity=_SEVERITY_MAP["missing_og_title"],
                    description=f"Page {record.url} is missing og:title",
                    dimension="og",
                ))
            if not record.og_description:
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="missing_og_description",
                    severity=_SEVERITY_MAP["missing_og_description"],
                    description=f"Page {record.url} is missing og:description",
                    dimension="og",
                ))
            if not record.og_image:
                findings.append(SEOFinding(
                    page_url=record.url,
                    issue_type="missing_og_image",
                    severity=_SEVERITY_MAP["missing_og_image"],
                    description=f"Page {record.url} is missing og:image",
                    dimension="og",
                ))

        return findings, {"duplicate_titles": list(duplicates.keys()),
                          "duplicate_descriptions": list(dup_descs.keys())}

    # ------------------------------------------------------------------
    # Dimension: Robots.txt
    # ------------------------------------------------------------------

    def audit_robots(
        self,
        robots_url: str,
        site_urls: list[str] | None = None,
    ) -> tuple[RobotsData, list[SEOFinding]]:
        """Audit robots.txt existence and configuration."""
        findings: list[SEOFinding] = []
        robots = self.fetch_robots(robots_url)

        if not robots.reachable:
            findings.append(SEOFinding(
                page_url=robots_url,
                issue_type="robots_unreachable",
                severity=_SEVERITY_MAP["robots_unreachable"],
                description=f"robots.txt at {robots_url} is not reachable",
                dimension="robots",
            ))
            return robots, findings

        if not robots.sitemap_refs:
            findings.append(SEOFinding(
                page_url=robots_url,
                issue_type="robots_no_sitemap_ref",
                severity=_SEVERITY_MAP["robots_no_sitemap_ref"],
                description="robots.txt does not reference any sitemap",
                dimension="robots",
            ))

        # Check if important pages are blocked
        if site_urls:
            for url in site_urls:
                path = urlparse(url).path
                for disallowed in robots.disallowed_paths:
                    disallowed_clean = disallowed.rstrip("/")
                    if disallowed_clean and path.startswith(disallowed_clean):
                        findings.append(SEOFinding(
                            page_url=url,
                            issue_type="blocked_by_robots",
                            severity=_SEVERITY_MAP["blocked_by_robots"],
                            description=(
                                f"Page {url} may be blocked by robots.txt disallow: {disallowed}"
                            ),
                            dimension="robots",
                        ))

        return robots, findings

    # ------------------------------------------------------------------
    # Full audit
    # ------------------------------------------------------------------

    def run(
        self,
        records: list[PageRecord],
        *,
        sitemap_url: str = "",
        robots_url: str = "",
        known_urls: list[str] | None = None,
    ) -> SEOAuditReport:
        """Run the full SEO audit across all dimensions.

        Args:
            records: List of parsed page records.
            sitemap_url: Sitemap URL to check (empty = skip sitemap fetch).
            robots_url: Robots.txt URL to check (empty = skip robots fetch).
            known_urls: URLs that should be in the sitemap (for missing URL check).

        Returns:
            SEOAuditReport with all findings.
        """
        all_findings: list[SEOFinding] = []
        audit_date = time.strftime("%Y-%m-%d")

        sitemap_data: SitemapData | None = None
        robots_data: RobotsData | None = None

        if self.audit_scope in ("full", "sitemap-only"):
            if sitemap_url:
                sitemap_data, s_findings = self.audit_sitemap(sitemap_url, known_urls)
                all_findings.extend(s_findings)

        if self.audit_scope in ("full", "canonical-only"):
            c_findings = self.audit_canonical(records)
            all_findings.extend(c_findings)

        if self.audit_scope in ("full", "schema-only"):
            sd_findings = self.audit_structured_data(records)
            all_findings.extend(sd_findings)

        if self.audit_scope == "full":
            meta_findings, duplicates = self.audit_meta(records)
            all_findings.extend(meta_findings)

            if robots_url:
                site_urls = [r.url for r in records]
                robots_data, r_findings = self.audit_robots(robots_url, site_urls)
                all_findings.extend(r_findings)
        else:
            duplicates = {"duplicate_titles": [], "duplicate_descriptions": []}

        # Build dimension summaries
        sitemap_dict: dict[str, object] = {}
        if sitemap_data:
            sitemap_dict = {
                "url": sitemap_data.url,
                "total_urls": sitemap_data.total_urls,
                "reachable": sitemap_data.reachable,
                "errors": sitemap_data.errors,
            }

        canonical_findings = [f for f in all_findings if f.dimension == "canonical"]
        canonical_dict: dict[str, object] = {
            "inconsistencies": [
                {"page_url": f.page_url, "issue_type": f.issue_type, "description": f.description}
                for f in canonical_findings
            ],
        }

        schema_findings = [f for f in all_findings if f.dimension == "structured_data"]
        schema_dict: dict[str, object] = {
            "validated_pages": [r.url for r in records],
            "errors": [
                {"page_url": f.page_url, "description": f.description}
                for f in schema_findings
            ],
        }

        meta_dict: dict[str, object] = {
            "duplicate_titles": duplicates.get("duplicate_titles", []),
            "duplicate_descriptions": duplicates.get("duplicate_descriptions", []),
        }

        robots_dict: dict[str, object] = {}
        if robots_data:
            robots_dict = {
                "url": robots_data.url,
                "reachable": robots_data.reachable,
                "sitemap_refs": robots_data.sitemap_refs,
                "disallowed_paths": robots_data.disallowed_paths,
            }

        # Build summary
        severity_counts: dict[str, int] = {}
        dimension_counts: dict[str, int] = {}
        for f in all_findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
            dimension_counts[f.dimension] = dimension_counts.get(f.dimension, 0) + 1

        summary: dict[str, int] = {
            "total_pages": len(records),
            "total_findings": len(all_findings),
            **{f"severity_{k}": v for k, v in severity_counts.items()},
            **{f"dimension_{k}": v for k, v in dimension_counts.items()},
        }

        return SEOAuditReport(
            audit_date=audit_date,
            audit_scope=self.audit_scope,
            site=self.site,
            total_pages_checked=len(records),
            sitemap=sitemap_dict,
            canonical=canonical_dict,
            structured_data=schema_dict,
            meta=meta_dict,
            robots=robots_dict,
            findings=all_findings,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    @staticmethod
    def write_report(report: SEOAuditReport, output_path: Path) -> None:
        """Write the drift report to ``output_path`` as JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# CLI entry (fixture mode — production uses fetcher injection)
# ---------------------------------------------------------------------------


def _cli() -> None:
    """CLI entry point for fixture-based audit runs."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SEO audit runner (read-only)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Path to a fixture JSON file with page records",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/seo-drift-report.json"),
        help="Output path for the drift report (default: /tmp/seo-drift-report.json)",
    )
    parser.add_argument(
        "--scope",
        choices=sorted(VALID_AUDIT_SCOPES),
        default="full",
        help="Audit scope (default: full)",
    )
    parser.add_argument(
        "--site",
        default="",
        help="Site URL being audited (e.g. https://lanlnk.cn)",
    )
    args = parser.parse_args()

    if not args.fixture:
        parser.error("--fixture is required")

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))

    # Parse page records from fixture
    records: list[PageRecord] = []
    pages = fixture.get("pages", [])

    for item in pages:
        html = item.get("html", "")
        url = item.get("url", "")
        if html:
            record = parse_html(html, url=url)
        else:
            record = PageRecord(
                url=url,
                title=item.get("title", ""),
                description=item.get("description", ""),
                canonical=item.get("canonical", ""),
                h1_tags=item.get("h1_tags", []),
                og_title=item.get("og_title", ""),
                og_description=item.get("og_description", ""),
                og_image=item.get("og_image", ""),
                json_ld_blocks=item.get("json_ld_blocks", []),
                meta_robots=item.get("meta_robots", ""),
            )
        record.status_code = int(item.get("status_code", 200))
        records.append(record)

    sitemap_url = fixture.get("sitemap_url", "")
    robots_url = fixture.get("robots_url", "")
    known_urls = fixture.get("known_urls")

    runner = SEOAuditRunner(audit_scope=args.scope, site=args.site)
    report = runner.run(
        records,
        sitemap_url=sitemap_url,
        robots_url=robots_url,
        known_urls=known_urls,
    )
    runner.write_report(report, args.output)

    report_dict = report.to_dict()
    print(f"SEO Audit complete: {report_dict['total_findings']} finding(s)")  # noqa: T201
    print(f"Pages checked: {report_dict['total_pages_checked']}")  # noqa: T201
    print(f"Report written to: {args.output}")  # noqa: T201

    if report_dict["total_findings"] > 0:
        print("\nFindings by dimension:")  # noqa: T201
        dim_counts: dict[str, int] = {}
        for f in report_dict["findings"]:
            dim = f["dimension"]
            dim_counts[dim] = dim_counts.get(dim, 0) + 1
        for dim, count in sorted(dim_counts.items()):
            print(f"  {dim}: {count}")  # noqa: T201


if __name__ == "__main__":
    _cli()
