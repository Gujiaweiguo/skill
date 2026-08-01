r"""Case screening - fetch and score published cases from the website API.

Read-only: fetches ``https://lanlnk.cn/api/cases`` and produces a
structured screening report.  Does not modify any case.

Usage (programmatic)::

    screener = CaseScreener()
    report = screener.screen()
    screener.write_report(report, output_path)

Usage (CLI)::

    uv run python -m scripts.case_screening \\
        --output /tmp/case-screening-report.json
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen

_HTTP_OK = 200

CASES_API_URL = "https://lanlnk.cn/api/cases"

#: Industries that map to high-value commercial real estate scenarios.
_PRIORITY_INDUSTRIES = frozenset({
    "shopping-center",
    "commercial-real-estate",
    "complex",
    "office",
})

#: Fields that must be non-empty for a complete case.
_REQUIRED_FIELDS = ("slug", "client_name", "industry", "problem", "solution", "outcome")


class HttpResponseError(Exception):
    """Raised when the API returns a non-200 status."""


class FetcherProtocol(Protocol):
    """HTTP fetcher protocol for dependency injection."""

    def fetch(self, url: str) -> str:
        """Return raw response body as text."""
        ...


class UrllibFetcher:
    """Default urllib-based HTTP fetcher."""

    def fetch(self, url: str) -> str:
        """Fetch a URL and return the response body."""
        req = Request(  # noqa: S310
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "case-ops-screening/0.1",
            },
        )
        try:
            with urlopen(req, timeout=15) as resp:  # noqa: S310
                body = resp.read().decode("utf-8")
                if resp.status != _HTTP_OK:
                    msg = f"API returned HTTP {resp.status}"
                    raise HttpResponseError(msg)
                return body
        except URLError as exc:
            msg = f"Failed to fetch {url}: {exc}"
            raise HttpResponseError(msg) from exc


@dataclass
class CaseCandidate:
    """A single published case from the API."""

    id: int
    slug: str
    client_name: str
    industry: str
    problem: str
    solution: str
    outcome: str
    testimonial: str | None
    status: str
    product: str | None
    completeness_score: float = 0.0
    priority_score: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class ScreeningReport:
    """Structured case screening report."""

    api_url: str
    fetched_at: str
    total_cases: int
    published_cases: int
    top_candidates: list[dict[str, object]]
    all_scores: list[dict[str, object]]
    summary: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to plain dict for JSON output."""
        return {
            "api_url": self.api_url,
            "fetched_at": self.fetched_at,
            "total_cases": self.total_cases,
            "published_cases": self.published_cases,
            "top_candidates": self.top_candidates,
            "all_scores": self.all_scores,
            "summary": self.summary,
        }


class CaseScreener:
    """Screen published cases and score them for pilot candidacy.

    Read-only: never creates, updates, or deletes any case.
    """

    def __init__(self, fetcher: FetcherProtocol | None = None) -> None:
        """Initialize with optional fetcher injection."""
        self._fetcher = fetcher or UrllibFetcher()

    def _parse_cases(self, raw_json: str) -> list[dict[str, object]]:
        """Parse the API response into a list of case dicts."""
        data = json.loads(raw_json)
        if isinstance(data, list):
            return data  # type: ignore[return-value]
        if isinstance(data, dict) and "results" in data:
            return data["results"]  # type: ignore[return-value]
        if isinstance(data, dict) and "data" in data:
            return data["data"]  # type: ignore[return-value]
        msg = "Unexpected API response format"
        raise ValueError(msg)

    def _score_completeness(self, case: dict[str, object]) -> tuple[float, list[str]]:
        """Score field completeness (0.0-1.0) and collect notes."""
        filled = 0
        total = len(_REQUIRED_FIELDS)
        notes: list[str] = []

        for field_name in _REQUIRED_FIELDS:
            val = case.get(field_name)
            if isinstance(val, str) and val.strip():
                filled += 1
            else:
                notes.append(f"empty: {field_name}")

        # Bonus fields
        bonus_fields = ("testimonial", "seo_title", "seo_description", "image")
        bonus_max = len(bonus_fields)
        bonus = 0
        for bf in bonus_fields:
            val = case.get(bf)
            if isinstance(val, str) and val.strip():
                bonus += 1

        score = (filled / total) * 0.8 + (bonus / bonus_max) * 0.2
        return score, notes

    def _score_priority(self, case: dict[str, object]) -> float:
        """Score industry priority (0.0-1.0)."""
        industry = str(case.get("industry", ""))
        if industry in _PRIORITY_INDUSTRIES:
            return 1.0
        return 0.5

    def screen(self, api_url: str = CASES_API_URL) -> ScreeningReport:
        """Fetch and screen all cases from the API.

        Returns a ScreeningReport with scored candidates.
        """
        raw = self._fetcher.fetch(api_url)
        cases = self._parse_cases(raw)

        published = [c for c in cases if c.get("status") == "published"]

        all_scores: list[dict[str, object]] = []
        for case in published:
            completeness, notes = self._score_completeness(case)
            priority = self._score_priority(case)
            combined = completeness * 0.6 + priority * 0.4

            candidate = CaseCandidate(
                id=int(case.get("id", 0)),
                slug=str(case.get("slug", "")),
                client_name=str(case.get("client_name", "")),
                industry=str(case.get("industry", "")),
                problem=str(case.get("problem", "")),
                solution=str(case.get("solution", "")),
                outcome=str(case.get("outcome", "")),
                testimonial=(
                    case.get("testimonial")
                    if isinstance(case.get("testimonial"), str)
                    else None
                ),
                status=str(case.get("status", "")),
                product=(
                    case.get("product")
                    if isinstance(case.get("product"), str)
                    else None
                ),
                completeness_score=completeness,
                priority_score=priority,
                notes=notes,
            )

            all_scores.append({
                "id": candidate.id,
                "slug": candidate.slug,
                "client_name": candidate.client_name,
                "industry": candidate.industry,
                "completeness_score": round(completeness, 3),
                "priority_score": round(priority, 3),
                "combined_score": round(combined, 3),
                "notes": notes,
            })

        # Sort by combined score descending
        all_scores.sort(key=lambda x: x["combined_score"], reverse=True)

        # Top 3 candidates
        top_candidates = all_scores[:3]

        # Industry distribution
        industry_dist: dict[str, int] = {}
        for c in all_scores:
            ind = c["industry"]  # type: ignore[assignment]
            industry_dist[ind] = industry_dist.get(ind, 0) + 1  # type: ignore[index]

        avg_completeness = (
            sum(c["completeness_score"] for c in all_scores) / len(all_scores)
            if all_scores else 0.0
        )

        summary = {
            "published_count": len(published),
            "avg_completeness": round(avg_completeness, 3),
            "industry_distribution": industry_dist,
            "top_slug": top_candidates[0]["slug"] if top_candidates else None,
        }

        return ScreeningReport(
            api_url=api_url,
            fetched_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            total_cases=len(cases),
            published_cases=len(published),
            top_candidates=top_candidates,
            all_scores=all_scores,
            summary=summary,
        )

    @staticmethod
    def write_report(report: ScreeningReport, output_path: Path) -> None:
        """Write the screening report to ``output_path`` as JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli() -> None:
    """CLI entry point for case screening."""
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(
        description="Screen published cases from the website API (read-only)",
    )
    parser.add_argument(
        "--api-url",
        default=CASES_API_URL,
        help=f"Cases API URL (default: {CASES_API_URL})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/case-screening-report.json"),  # noqa: S108
        help="Output path for the screening report",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=3,
        help="Number of top candidates to highlight (default: 3)",
    )
    args = parser.parse_args()

    screener = CaseScreener()
    try:
        report = screener.screen(api_url=args.api_url)
    except HttpResponseError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    # Adjust top candidates to requested count
    report.top_candidates = report.all_scores[:args.top]
    screener.write_report(report, args.output)

    print(f"Screening complete: {report.published_cases} published cases")
    print(f"Report written to: {args.output}")

    if report.top_candidates:
        print(f"\nTop {len(report.top_candidates)} candidates:")
        for i, c in enumerate(report.top_candidates, 1):
            print(
                f"  {i}. {c['client_name']} ({c['slug']}) "
                f"— score: {c['combined_score']}"
            )


if __name__ == "__main__":
    _cli()
