"""Tests for case_screening module.

Covers: API parsing, scoring logic, report structure,
and fetcher injection (no real HTTP calls in tests).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from scripts.case_screening import (
    CASES_API_URL,
    CaseScreener,
    HttpResponseError,
)

if TYPE_CHECKING:
    from pathlib import Path


class StubFetcher:
    """In-process stub for HTTP fetching."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.fetched_urls: list[str] = []

    def fetch(self, url: str) -> str:
        self.fetched_urls.append(url)
        return self._response


class ErrorStubFetcher:
    """Always raises an error."""

    def fetch(self, url: str) -> str:
        msg = "Connection refused"
        raise HttpResponseError(msg)


def _make_case(  # noqa: PLR0913
    *,
    case_id: int = 1,
    slug: str = "test-case",
    client_name: str = "测试客户",
    industry: str = "shopping-center",
    status: str = "published",
    problem: str = "问题描述",
    solution: str = "方案描述",
    outcome: str = "结果描述",
    testimonial: str | None = "客户评价",
    seo_title: str | None = "SEO标题",
    seo_description: str | None = "SEO描述",
    image: str | None = "/cases/test.webp",
    product: str | None = "shopping-center",
) -> dict[str, object]:
    """Build a minimal case dict for testing."""
    case: dict[str, object] = {
        "id": case_id,
        "slug": slug,
        "client_name": client_name,
        "industry": industry,
        "problem": problem,
        "solution": solution,
        "outcome": outcome,
        "status": status,
        "product": product,
    }
    if testimonial is not None:
        case["testimonial"] = testimonial
    if seo_title is not None:
        case["seo_title"] = seo_title
    if seo_description is not None:
        case["seo_description"] = seo_description
    if image is not None:
        case["image"] = image
    return case


class TestFetcherInjection:
    def test_stub_fetcher_called(self) -> None:
        raw = json.dumps([_make_case()])
        stub = StubFetcher(raw)
        screener = CaseScreener(fetcher=stub)
        screener.screen()
        assert len(stub.fetched_urls) == 1
        assert stub.fetched_urls[0] == CASES_API_URL

    def test_custom_api_url(self) -> None:
        raw = json.dumps([_make_case()])
        stub = StubFetcher(raw)
        screener = CaseScreener(fetcher=stub)
        screener.screen(api_url="https://custom.example.com/api/cases")
        assert stub.fetched_urls[0] == "https://custom.example.com/api/cases"

    def test_error_propagates(self) -> None:
        screener = CaseScreener(fetcher=ErrorStubFetcher())  # type: ignore[arg-type]
        with pytest.raises(HttpResponseError, match="Connection refused"):
            screener.screen()


class TestResponseParsing:
    def test_list_response(self) -> None:
        raw = json.dumps([_make_case(case_id=1), _make_case(case_id=2)])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert report.total_cases == 2

    def test_results_wrapper(self) -> None:
        raw = json.dumps({"results": [_make_case()]})
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert report.total_cases == 1

    def test_data_wrapper(self) -> None:
        raw = json.dumps({"data": [_make_case()]})
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert report.total_cases == 1

    def test_invalid_format(self) -> None:
        raw = json.dumps({"unexpected": True})
        screener = CaseScreener(fetcher=StubFetcher(raw))
        with pytest.raises(ValueError, match="Unexpected API"):
            screener.screen()


class TestScoring:
    def test_complete_case_scores_high(self) -> None:
        raw = json.dumps([_make_case()])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        score = report.all_scores[0]["completeness_score"]
        assert score == 1.0  # type: ignore[comparison-overlap]

    def test_missing_optional_fields_lowers_score(self) -> None:
        case = _make_case(testimonial=None, seo_title=None, seo_description=None, image=None)
        raw = json.dumps([case])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        score = report.all_scores[0]["completeness_score"]
        assert score < 1.0  # type: ignore[comparison-overlap]
        assert score == 0.8  # type: ignore[comparison-overlap]

    def test_priority_industry_scores_high(self) -> None:
        case = _make_case(industry="shopping-center")
        raw = json.dumps([case])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert report.all_scores[0]["priority_score"] == 1.0

    def test_non_priority_industry(self) -> None:
        case = _make_case(industry="property")
        raw = json.dumps([case])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert report.all_scores[0]["priority_score"] == 0.5

    def test_combined_score_formula(self) -> None:
        case = _make_case()
        raw = json.dumps([case])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        # completeness=1.0, priority=1.0 → combined = 1.0*0.6 + 1.0*0.4 = 1.0
        assert report.all_scores[0]["combined_score"] == 1.0

    def test_empty_required_field_noted(self) -> None:
        case = _make_case(problem="")
        raw = json.dumps([case])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert "empty: problem" in report.all_scores[0]["notes"]


class TestReportStructure:
    def test_published_only(self) -> None:
        cases = [_make_case(case_id=1, status="published"), _make_case(case_id=2, status="draft")]
        raw = json.dumps(cases)
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert report.total_cases == 2
        assert report.published_cases == 1
        assert len(report.all_scores) == 1

    def test_sorted_by_score(self) -> None:
        case_low = _make_case(
            case_id=1, slug="low",
            testimonial=None, seo_title=None,
            seo_description=None, image=None,
            industry="property",
        )
        case_high = _make_case(case_id=2, slug="high")
        raw = json.dumps([case_low, case_high])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert report.all_scores[0]["slug"] == "high"

    def test_top_candidates(self) -> None:
        cases = [_make_case(case_id=i, slug=f"case-{i}") for i in range(5)]
        raw = json.dumps(cases)
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert len(report.top_candidates) == 3

    def test_summary_fields(self) -> None:
        cases = [
            _make_case(case_id=1, industry="shopping-center"),
            _make_case(case_id=2, industry="office"),
        ]
        raw = json.dumps(cases)
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert report.summary["published_count"] == 2
        assert "shopping-center" in report.summary["industry_distribution"]
        assert "office" in report.summary["industry_distribution"]

    def test_fetched_at_present(self) -> None:
        raw = json.dumps([_make_case()])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert len(report.fetched_at) > 0

    def test_empty_api(self) -> None:
        raw = json.dumps([])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        assert report.total_cases == 0
        assert report.published_cases == 0
        assert report.top_candidates == []
        assert report.summary["avg_completeness"] == 0.0


class TestWriteReport:
    def test_writes_json(self, tmp_path: Path) -> None:
        raw = json.dumps([_make_case()])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        out = tmp_path / "screening.json"
        screener.write_report(report, out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["total_cases"] == 1
        assert data["published_cases"] == 1

    def test_creates_parent_dir(self, tmp_path: Path) -> None:
        raw = json.dumps([_make_case()])
        screener = CaseScreener(fetcher=StubFetcher(raw))
        report = screener.screen()
        out = tmp_path / "nested" / "deeper" / "report.json"
        screener.write_report(report, out)
        assert out.exists()
