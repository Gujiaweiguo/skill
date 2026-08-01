"""Tests for the production audit runner.

Covers: cross-check drift detection, single-scope audits, CLI entry,
report generation, online checker injection, and doc parser.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts.audit_runner import (
    AuditReport,
    AuditRunner,
    CurlOnlineChecker,
    DriftFinding,
    RedirectRecord,
    VALID_AUDIT_SCOPES,
    cross_check,
    parse_redirect_doc,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fixture_record(**overrides: object) -> RedirectRecord:
    """Create a clean (no-drift) record with optional overrides."""
    defaults: dict[str, object] = {
        "source_url": "example.lanlnk.cn",
        "db_status": "active",
        "doc_status": "active",
        "nginx_status": "301-to-www.lanlnk.cn",
        "online_status_code": 301,
        "online_target": "https://www.lanlnk.cn",
        "expected_target": "https://www.lanlnk.cn",
    }
    defaults.update(overrides)
    return RedirectRecord(**defaults)  # type: ignore[arg-type]


class FakeOnlineChecker:
    """Deterministic online checker for tests."""

    def __init__(self, responses: dict[str, dict[str, object]]) -> None:
        self._responses = responses
        self.calls: list[str] = []

    def check(self, url: str) -> dict[str, object]:
        self.calls.append(url)
        return self._responses.get(
            url,
            {"status_code": 0, "target": None, "reachable": False},
        )


# ---------------------------------------------------------------------------
# cross_check function tests
# ---------------------------------------------------------------------------


class TestCrossCheckNoDrift:
    """Records with consistent state should return None."""

    def test_clean_record(self) -> None:
        record = _fixture_record()
        assert cross_check(record) is None

    def test_clean_302(self) -> None:
        record = _fixture_record(online_status_code=302)
        assert cross_check(record) is None


class TestCrossCheckDriftTypes:
    """Each drift classification must be detected correctly."""

    def test_ownership_pending(self) -> None:
        record = _fixture_record(
            doc_status="pending-ownership-confirmation",
            notes="pending ownership confirmation",
        )
        finding = cross_check(record)
        assert finding is not None
        assert finding.drift_type == "ownership-confirmation-pending"
        assert finding.severity == "critical"

    def test_doc_db_inconsistency(self) -> None:
        record = _fixture_record(doc_status="removed")
        finding = cross_check(record)
        assert finding is not None
        assert finding.drift_type == "doc-db-inconsistency"
        assert finding.severity == "warning"

    def test_stale_doc_entry(self) -> None:
        record = _fixture_record(db_status="disabled", doc_status="active")
        finding = cross_check(record)
        assert finding is not None
        assert finding.drift_type == "stale-doc-entry"
        assert finding.severity == "warning"

    def test_db_missing_but_online(self) -> None:
        record = _fixture_record(db_status="missing", online_status_code=302)
        finding = cross_check(record)
        assert finding is not None
        assert finding.drift_type == "db-missing-but-online"
        assert finding.severity == "critical"

    def test_disabled_but_online(self) -> None:
        record = _fixture_record(
            db_status="disabled",
            doc_status="active",
            online_status_code=301,
        )
        finding = cross_check(record)
        assert finding is not None
        # Could be stale-doc-entry or disabled-but-online depending on order
        assert finding.drift_type in ("stale-doc-entry", "disabled-but-online")

    def test_offline_but_active(self) -> None:
        record = _fixture_record(online_status_code=404)
        finding = cross_check(record)
        assert finding is not None
        assert finding.drift_type == "offline-but-active"
        assert finding.severity == "critical"

    def test_unexpected_target(self) -> None:
        record = _fixture_record(
            expected_target="https://lanlnk.cn",
            online_target="https://www.lanlnk.com",
            online_status_code=302,
        )
        finding = cross_check(record)
        assert finding is not None
        assert finding.drift_type == "unexpected-target"
        assert finding.severity == "critical"


class TestCrossCheckSeverityMapping:
    """Severity levels must be consistent."""

    @pytest.mark.parametrize("drift_type,expected_severity", [
        ("ownership-confirmation-pending", "critical"),
        ("doc-db-inconsistency", "warning"),
        ("stale-doc-entry", "warning"),
        ("db-missing-but-online", "critical"),
        ("doc-missing-but-online", "warning"),
        ("disabled-but-online", "critical"),
        ("offline-but-active", "critical"),
        ("unexpected-target", "critical"),
    ])
    def test_severity(self, drift_type: str, expected_severity: str) -> None:
        from scripts.audit_runner import _SEVERITY_MAP
        assert _SEVERITY_MAP[drift_type] == expected_severity


# ---------------------------------------------------------------------------
# AuditRunner tests
# ---------------------------------------------------------------------------


class TestAuditRunnerInit:
    """Constructor validation."""

    @pytest.mark.parametrize("scope", sorted(VALID_AUDIT_SCOPES))
    def test_valid_scope(self, scope: str) -> None:
        runner = AuditRunner(audit_scope=scope)
        assert runner.audit_scope == scope

    def test_invalid_scope(self) -> None:
        with pytest.raises(ValueError, match="invalid audit_scope"):
            AuditRunner(audit_scope="production-write")


class TestAuditRunnerCrossCheck:
    """Cross-check mode (default) audit tests."""

    def test_no_drifts(self) -> None:
        runner = AuditRunner()
        records = [_fixture_record(), _fixture_record(source_url="b.lanlnk.cn")]
        report = runner.run(records)
        assert len(report.drifts) == 0
        assert report.total_checked == 2
        assert report.summary["total_records"] == 2
        assert report.summary["total_drifts"] == 0

    def test_with_drifts(self) -> None:
        runner = AuditRunner()
        records = [
            _fixture_record(),
            _fixture_record(
                source_url="gzshopex.com",
                db_status="missing",
                doc_status="pending-ownership-confirmation",
                nginx_status="302-to-www.lanlnk.com",
                notes="pending ownership confirmation",
            ),
            _fixture_record(
                source_url="old.lanlnk.cn",
                doc_status="removed",
            ),
        ]
        report = runner.run(records)
        assert len(report.drifts) == 2
        assert report.drifts[0].source_url == "gzshopex.com"
        assert report.drifts[1].source_url == "old.lanlnk.cn"

    def test_report_date(self) -> None:
        runner = AuditRunner()
        report = runner.run([_fixture_record()])
        # audit_date should be YYYY-MM-DD
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}", report.audit_date)

    def test_summary_counts(self) -> None:
        runner = AuditRunner()
        records = [
            _fixture_record(),  # no drift
            _fixture_record(source_url="a.com", db_status="missing"),  # drift
            _fixture_record(source_url="b.com", doc_status="removed"),  # drift
        ]
        report = runner.run(records)
        assert report.summary["total_records"] == 3
        assert report.summary["total_drifts"] == 2


class TestAuditRunnerOnlineCheck:
    """Online checking via injected checker."""

    def test_injected_checker_used(self) -> None:
        fake = FakeOnlineChecker({
            "test.lanlnk.cn": {"status_code": 301, "target": "https://www.lanlnk.cn", "reachable": True},
        })
        runner = AuditRunner(online_checker=fake)
        result = runner.check_online("test.lanlnk.cn")
        assert result["status_code"] == 301
        assert "test.lanlnk.cn" in fake.calls

    def test_online_only_no_drift(self) -> None:
        fake = FakeOnlineChecker({
            "ok.lanlnk.cn": {"status_code": 301, "target": None, "reachable": True},
        })
        runner = AuditRunner(audit_scope="online-only", online_checker=fake)
        record = _fixture_record(
            source_url="ok.lanlnk.cn",
            online_status_code=301,
        )
        finding = runner.audit_record(record)
        assert finding is None

    def test_online_only_mismatch(self) -> None:
        fake = FakeOnlineChecker({
            "bad.lanlnk.cn": {"status_code": 404, "target": None, "reachable": False},
        })
        runner = AuditRunner(audit_scope="online-only", online_checker=fake)
        record = _fixture_record(
            source_url="bad.lanlnk.cn",
            online_status_code=301,
        )
        finding = runner.audit_record(record)
        assert finding is not None
        assert finding.drift_type == "online-mismatch"

    def test_run_with_live_check(self) -> None:
        fake = FakeOnlineChecker({
            "live.lanlnk.cn": {"status_code": 302, "target": "https://lanlnk.cn", "reachable": True},
        })
        runner = AuditRunner(online_checker=fake)
        record = _fixture_record(
            source_url="live.lanlnk.cn",
            online_status_code=0,  # will be overwritten
        )
        report = runner.run([record], check_online=True)
        assert record.online_status_code == 302


class TestAuditRunnerScopes:
    """Single-scope audit modes."""

    def test_db_only_missing(self) -> None:
        runner = AuditRunner(audit_scope="db-only")
        record = _fixture_record(db_status="missing")
        finding = runner.audit_record(record)
        assert finding is not None
        assert finding.drift_type == "db-missing"

    def test_db_only_active_no_drift(self) -> None:
        runner = AuditRunner(audit_scope="db-only")
        record = _fixture_record(db_status="active")
        finding = runner.audit_record(record)
        assert finding is None

    def test_nginx_only_unknown(self) -> None:
        runner = AuditRunner(audit_scope="nginx-only")
        record = _fixture_record(nginx_status="unknown")
        finding = runner.audit_record(record)
        assert finding is not None
        assert finding.drift_type == "nginx-unknown"


# ---------------------------------------------------------------------------
# Report output tests
# ---------------------------------------------------------------------------


class TestReportSerialization:
    """Report to_dict and write_report."""

    def test_to_dict_structure(self) -> None:
        runner = AuditRunner()
        report = runner.run([_fixture_record(source_url="x.com", db_status="missing")])
        d = report.to_dict()
        assert "audit_date" in d
        assert "audit_scope" in d
        assert "total_checked" in d
        assert "total_drifts" in d
        assert "drifts" in d
        assert "summary" in d
        assert isinstance(d["drifts"], list)

    def test_write_report(self, tmp_path: Path) -> None:
        runner = AuditRunner()
        report = runner.run([_fixture_record()])
        output = tmp_path / "report.json"
        runner.write_report(report, output)
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["total_checked"] == 1

    def test_write_report_creates_parent(self, tmp_path: Path) -> None:
        runner = AuditRunner()
        report = runner.run([_fixture_record()])
        output = tmp_path / "nested" / "dir" / "report.json"
        runner.write_report(report, output)
        assert output.exists()


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestCLI:
    """CLI entry point tests."""

    def test_cli_fixture_run(self, tmp_path: Path) -> None:
        import scripts.audit_runner as mod
        output = tmp_path / "drift-report.json"

        # Build a minimal fixture
        fixture = {
            "redirects": [
                {
                    "source_url": "clean.lanlnk.cn",
                    "db_status": "active",
                    "doc_status": "active",
                    "nginx_status": "301-to-www.lanlnk.cn",
                    "online_status_code": 301,
                },
                {
                    "source_url": "bad.lanlnk.cn",
                    "db_status": "missing",
                    "doc_status": "active",
                    "nginx_status": "302-to-wrong.example.com",
                    "online_status_code": 302,
                },
            ],
        }
        fixture_path = tmp_path / "fixture.json"
        fixture_path.write_text(json.dumps(fixture))

        # Simulate CLI invocation
        orig_argv = sys.argv
        try:
            sys.argv = [
                "audit_runner",
                "--fixture", str(fixture_path),
                "--output", str(output),
                "--scope", "cross-check",
            ]
            mod._cli()
        finally:
            sys.argv = orig_argv

        assert output.exists()
        report = json.loads(output.read_text())
        assert report["total_checked"] == 2
        assert report["total_drifts"] >= 1

    def test_cli_missing_fixture_arg(self) -> None:
        import scripts.audit_runner as mod

        orig_argv = sys.argv
        try:
            sys.argv = ["audit_runner", "--output", "/tmp/x.json"]
            with pytest.raises(SystemExit):
                mod._cli()
        finally:
            sys.argv = orig_argv


# ---------------------------------------------------------------------------
# Doc parser tests
# ---------------------------------------------------------------------------


class TestParseRedirectDoc:
    """Redirect-map.md parser."""

    def test_parse_table(self, tmp_path: Path) -> None:
        doc = tmp_path / "redirect-map.md"
        doc.write_text("""# Redirect Map

| Source | Target | Status |
|---|---|---|
| old.lanlnk.cn | www.lanlnk.cn | active |
| m.lanlnk.cn | www.lanlnk.cn | removed |
| gzshopex.com | lanlnk.cn | pending |
""")
        result = parse_redirect_doc(doc)
        assert result["old.lanlnk.cn"] == "active"
        assert result["m.lanlnk.cn"] == "removed"
        assert "gzshopex.com" in result

    def test_parse_nonexistent(self) -> None:
        result = parse_redirect_doc(Path("/nonexistent/file.md"))
        assert result == {}

    def test_skips_header_row(self, tmp_path: Path) -> None:
        doc = tmp_path / "test.md"
        doc.write_text("""| Source | Target | Status |
|---|---|---|
| real.lanlnk.cn | www.lanlnk.cn | active |
""")
        result = parse_redirect_doc(doc)
        assert "Source" not in result
        assert "real.lanlnk.cn" in result


# ---------------------------------------------------------------------------
# DriftFinding description tests
# ---------------------------------------------------------------------------


class TestDriftFindingDescriptions:
    """Drift findings must have meaningful descriptions."""

    def test_description_not_empty(self) -> None:
        runner = AuditRunner()
        records = [
            _fixture_record(source_url="a.com", db_status="missing"),
            _fixture_record(source_url="b.com", doc_status="removed"),
            _fixture_record(source_url="c.com", online_status_code=404),
        ]
        report = runner.run(records)
        for drift in report.drifts:
            assert drift.description
            assert len(drift.description) > 10
            assert drift.source_url in drift.description


# ---------------------------------------------------------------------------
# Fixture integration test
# ---------------------------------------------------------------------------


class TestFixtureIntegration:
    """The synthetic fixture should produce expected drifts."""

    def test_fixture_audit(self) -> None:
        with FIXTURE_PATH.open() as f:
            fixture = json.load(f)

        # Expected targets for records where the target is known
        expected_targets: dict[str, str] = {
            "shop.lanlnk.cn": "https://www.lanlnk.cn/shop",
        }
        online_targets: dict[str, str] = {
            "shop.lanlnk.cn": "https://m.lanlnk.cn",
        }

        records: list[RedirectRecord] = []
        for item in fixture["redirects"]:
            src = item["source_url"]
            records.append(RedirectRecord(
                source_url=src,
                db_status=item.get("db_status", "missing"),
                doc_status=item.get("doc_status", "missing"),
                nginx_status=item.get("nginx_status", "unknown"),
                online_status_code=int(item.get("online_status_code", 0)),
                online_target=online_targets.get(src),
                expected_target=expected_targets.get(src),
                notes=item.get("notes", ""),
            ))

        runner = AuditRunner()
        report = runner.run(records)

        # The fixture has 5 records with various drifts
        assert report.total_checked == 5
        # At least the known drifts should be found
        drift_urls = {d.source_url for d in report.drifts}
        assert "gzshopex.com" in drift_urls
        assert "blog.lanlnk.com" in drift_urls
        assert "m.lanlnk.cn" in drift_urls
        assert "shop.lanlnk.cn" in drift_urls
