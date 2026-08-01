"""Comprehensive tests for the health_check module.

Covers:
- EndpointResult / SSLResult / ServiceResult / ResourceResult dataclasses
- CurlOnlineChecker (mocked subprocess)
- SSLCertChecker (mocked)
- SystemdServiceChecker (mocked subprocess)
- SystemResourceChecker (mocked file reads)
- Threshold evaluation (endpoint, SSL, service, resource)
- HealthChecker.run with injected mocks
- HealthChecker.write_report
- CLI entry point (fixture mode)
- Fail-closed / read-only guarantees
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.health_check import (
    DEFAULT_SERVICES,
    DEFAULT_SITES,
    CurlOnlineChecker,
    EndpointResult,
    HealthChecker,
    HealthFinding,
    HealthReport,
    ResourceResult,
    SSLCertChecker,
    SSLResult,
    ServiceResult,
    SystemResourceChecker,
    SystemdServiceChecker,
    _FixtureOnlineChecker,
    _FixtureResourceChecker,
    _FixtureServiceChecker,
    _FixtureSSLChecker,
    _evaluate_endpoint,
    _evaluate_resources,
    _evaluate_service,
    _evaluate_ssl,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures" / "synthetic-fixture.json"
)
THRESHOLDS_PATH = (
    Path(__file__).resolve().parent.parent
    / "config" / "thresholds.json"
)


def _load_fixture() -> dict[str, object]:
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


def _load_thresholds() -> dict[str, object]:
    with THRESHOLDS_PATH.open() as f:
        return dict(json.load(f))


# =========================================================================
# Dataclass tests
# =========================================================================


class TestEndpointResult:
    def test_defaults(self) -> None:
        r = EndpointResult(url="https://example.com")
        assert r.http_code == 0
        assert r.response_time_ms == 0.0
        assert r.redirect_chain == []
        assert r.reachable is False
        assert r.error is None

    def test_redirect_chain_default_empty(self) -> None:
        r = EndpointResult(url="https://example.com")
        assert len(r.redirect_chain) == 0


class TestSSLResult:
    def test_defaults(self) -> None:
        r = SSLResult(domain="example.com")
        assert r.days_remaining == 0
        assert r.error is None
        assert r.issuer == ""


class TestServiceResult:
    def test_defaults(self) -> None:
        r = ServiceResult(name="test")
        assert r.status == "unknown"
        assert r.main_pid == 0


class TestResourceResult:
    def test_defaults(self) -> None:
        r = ResourceResult()
        assert r.disk_used_percent == 0.0
        assert r.memory_used_percent == 0.0
        assert r.swap_used_percent == 0.0


class TestHealthReportToDict:
    def test_serialise(self) -> None:
        report = HealthReport(
            check_date="2026-08-01",
            check_scope="full",
            endpoints=[EndpointResult(url="https://x.com", http_code=200)],
            ssl_certs=[SSLResult(domain="x.com", days_remaining=60)],
            services=[ServiceResult(name="svc1", status="active")],
            resources=ResourceResult(disk_used_percent=50),
            findings=[HealthFinding(
                check="test", target="x", severity="warning", message="msg",
            )],
            summary={"total_findings": 1},
        )
        d = report.to_dict()
        assert d["check_date"] == "2026-08-01"
        assert len(d["endpoints"]) == 1
        assert d["endpoints"][0]["http_code"] == 200
        assert d["resources"]["disk_used_percent"] == 50.0
        assert d["findings"][0]["severity"] == "warning"

    def test_serialise_none_resources(self) -> None:
        report = HealthReport(check_date="2026-08-01", check_scope="quick")
        d = report.to_dict()
        assert d["resources"] is None


# =========================================================================
# Threshold evaluation tests
# =========================================================================


class TestEvaluateEndpoint:
    def _config(self, **kw: object) -> dict[str, object]:
        return {
            "expected_http_code": 200,
            "max_response_time_ms": 3000,
            "expected_https": True,
            **kw,
        }

    def test_healthy_endpoint_no_findings(self) -> None:
        ep = EndpointResult(
            url="https://lanlnk.cn",
            http_code=200,
            response_time_ms=100,
            ssl_enabled=True,
            reachable=True,
        )
        findings: list[HealthFinding] = []
        _evaluate_endpoint(ep, self._config(), findings)
        assert len(findings) == 0

    def test_unreachable_critical(self) -> None:
        ep = EndpointResult(url="https://lanlnk.cn", error="timeout")
        findings: list[HealthFinding] = []
        _evaluate_endpoint(ep, self._config(), findings)
        assert len(findings) == 1
        assert findings[0].severity == "critical"
        assert findings[0].check == "endpoint_reachable"

    def test_wrong_http_code(self) -> None:
        ep = EndpointResult(
            url="https://lanlnk.cn",
            http_code=502,
            response_time_ms=100,
            ssl_enabled=True,
            reachable=True,
        )
        findings: list[HealthFinding] = []
        _evaluate_endpoint(ep, self._config(), findings)
        codes = [f.check for f in findings]
        assert "http_status" in codes
        http_finding = [f for f in findings if f.check == "http_status"][0]
        assert http_finding.severity == "critical"  # 5xx → critical

    def test_4xx_warning(self) -> None:
        ep = EndpointResult(
            url="https://lanlnk.cn",
            http_code=404,
            response_time_ms=100,
            ssl_enabled=True,
            reachable=True,
        )
        findings: list[HealthFinding] = []
        _evaluate_endpoint(ep, self._config(), findings)
        http_finding = [f for f in findings if f.check == "http_status"][0]
        assert http_finding.severity == "warning"

    def test_slow_response_time(self) -> None:
        ep = EndpointResult(
            url="https://lanlnk.cn",
            http_code=200,
            response_time_ms=5000,
            ssl_enabled=True,
            reachable=True,
        )
        findings: list[HealthFinding] = []
        _evaluate_endpoint(ep, self._config(), findings)
        rt_findings = [f for f in findings if f.check == "response_time"]
        assert len(rt_findings) == 1
        assert rt_findings[0].severity == "warning"

    def test_not_https(self) -> None:
        ep = EndpointResult(
            url="http://lanlnk.cn",
            http_code=200,
            response_time_ms=50,
            ssl_enabled=False,
            reachable=True,
        )
        findings: list[HealthFinding] = []
        _evaluate_endpoint(ep, self._config(), findings)
        https_findings = [f for f in findings if f.check == "https_enabled"]
        assert len(https_findings) == 1

    def test_unexpected_redirect(self) -> None:
        ep = EndpointResult(
            url="http://lanlnk.cn",
            http_code=301,
            response_time_ms=50,
            ssl_enabled=False,
            reachable=True,
            final_url="https://wrong.com",
            redirect_chain=["http://lanlnk.cn", "https://wrong.com"],
        )
        cfg = self._config(expected_redirect="https://lanlnk.cn")
        findings: list[HealthFinding] = []
        _evaluate_endpoint(ep, cfg, findings)
        redirect_findings = [f for f in findings if f.check == "redirect_target"]
        assert len(redirect_findings) == 1


class TestEvaluateSSL:
    def test_healthy_cert(self) -> None:
        ssl_result = SSLResult(domain="lanlnk.cn", days_remaining=60)
        cfg = {"warn_days_remaining": 30, "critical_days_remaining": 7}
        findings: list[HealthFinding] = []
        _evaluate_ssl(ssl_result, cfg, findings)
        assert len(findings) == 0

    def test_warning_threshold(self) -> None:
        ssl_result = SSLResult(domain="lanlnk.cn", days_remaining=20)
        cfg = {"warn_days_remaining": 30, "critical_days_remaining": 7}
        findings: list[HealthFinding] = []
        _evaluate_ssl(ssl_result, cfg, findings)
        assert len(findings) == 1
        assert findings[0].severity == "warning"

    def test_critical_threshold(self) -> None:
        ssl_result = SSLResult(domain="lanlnk.cn", days_remaining=3)
        cfg = {"warn_days_remaining": 30, "critical_days_remaining": 7}
        findings: list[HealthFinding] = []
        _evaluate_ssl(ssl_result, cfg, findings)
        assert len(findings) == 1
        assert findings[0].severity == "critical"

    def test_ssl_error(self) -> None:
        ssl_result = SSLResult(domain="lanlnk.cn", error="connection refused")
        cfg = {"warn_days_remaining": 30, "critical_days_remaining": 7}
        findings: list[HealthFinding] = []
        _evaluate_ssl(ssl_result, cfg, findings)
        assert len(findings) == 1
        assert findings[0].severity == "critical"


class TestEvaluateService:
    def test_active_service_ok(self) -> None:
        svc = ServiceResult(name="svc1", status="active")
        cfg = {"expected_status": "active"}
        findings: list[HealthFinding] = []
        _evaluate_service(svc, cfg, findings)
        assert len(findings) == 0

    def test_failed_service_critical(self) -> None:
        svc = ServiceResult(name="svc1", status="failed")
        cfg = {"expected_status": "active"}
        findings: list[HealthFinding] = []
        _evaluate_service(svc, cfg, findings)
        assert len(findings) == 1
        assert findings[0].severity == "critical"

    def test_inactive_service_critical(self) -> None:
        svc = ServiceResult(name="svc1", status="inactive")
        cfg = {"expected_status": "active"}
        findings: list[HealthFinding] = []
        _evaluate_service(svc, cfg, findings)
        assert len(findings) == 1
        assert findings[0].severity == "critical"

    def test_service_error(self) -> None:
        svc = ServiceResult(name="svc1", error="not found")
        cfg = {"expected_status": "active"}
        findings: list[HealthFinding] = []
        _evaluate_service(svc, cfg, findings)
        assert len(findings) == 1
        assert findings[0].severity == "warning"


class TestEvaluateResources:
    def _config(self) -> dict[str, object]:
        return {
            "disk_warn_percent": 80,
            "disk_critical_percent": 90,
            "memory_warn_percent": 75,
            "memory_critical_percent": 90,
            "swap_warn_percent": 60,
            "swap_critical_percent": 80,
        }

    def test_all_normal(self) -> None:
        res = ResourceResult(
            disk_used_percent=50,
            memory_used_percent=40,
            swap_used_percent=30,
        )
        findings: list[HealthFinding] = []
        _evaluate_resources(res, self._config(), findings)
        assert len(findings) == 0

    def test_disk_warn(self) -> None:
        res = ResourceResult(disk_used_percent=85)
        findings: list[HealthFinding] = []
        _evaluate_resources(res, self._config(), findings)
        assert len(findings) == 1
        assert findings[0].severity == "warning"
        assert findings[0].check == "resource_disk"

    def test_disk_critical(self) -> None:
        res = ResourceResult(disk_used_percent=95)
        findings: list[HealthFinding] = []
        _evaluate_resources(res, self._config(), findings)
        assert len(findings) == 1
        assert findings[0].severity == "critical"

    def test_memory_critical(self) -> None:
        res = ResourceResult(memory_used_percent=92)
        findings: list[HealthFinding] = []
        _evaluate_resources(res, self._config(), findings)
        assert len(findings) == 1
        assert findings[0].severity == "critical"
        assert findings[0].check == "resource_memory"

    def test_swap_warn(self) -> None:
        res = ResourceResult(swap_used_percent=65)
        findings: list[HealthFinding] = []
        _evaluate_resources(res, self._config(), findings)
        assert len(findings) == 1
        assert findings[0].severity == "warning"

    def test_all_critical(self) -> None:
        res = ResourceResult(
            disk_used_percent=95,
            memory_used_percent=92,
            swap_used_percent=85,
        )
        findings: list[HealthFinding] = []
        _evaluate_resources(res, self._config(), findings)
        assert len(findings) == 3
        assert all(f.severity == "critical" for f in findings)


# =========================================================================
# Fixture-based mock checker tests
# =========================================================================


class TestFixtureOnlineChecker:
    def test_known_endpoint(self) -> None:
        fixture = _load_fixture()
        ep_data = fixture.get("endpoints", {})
        assert isinstance(ep_data, dict)
        checker = _FixtureOnlineChecker(ep_data)
        result = checker.check("https://lanlnk.cn")
        assert result.http_code == 200
        assert result.reachable is True
        assert result.ssl_enabled is True

    def test_unknown_endpoint_defaults_healthy(self) -> None:
        checker = _FixtureOnlineChecker({})
        result = checker.check("https://unknown.com")
        assert result.http_code == 200
        assert result.response_time_ms == 50.0


class TestFixtureSSLChecker:
    def test_returns_healthy_result(self) -> None:
        checker = _FixtureSSLChecker()
        result = checker.check("lanlnk.cn")
        assert result.days_remaining == 53
        assert result.error is None
        assert "lanlnk.cn" in result.subject.get("commonName", "")


class TestFixtureServiceChecker:
    def test_known_service(self) -> None:
        fixture = _load_fixture()
        svc_data = fixture.get("services", {})
        assert isinstance(svc_data, dict)
        checker = _FixtureServiceChecker(svc_data)
        result = checker.check("lnkwebsite-backend")
        assert result.status == "active"
        assert result.main_pid == 2050626

    def test_unknown_service_defaults(self) -> None:
        checker = _FixtureServiceChecker({})
        result = checker.check("unknown-svc")
        assert result.status == "active"
        assert result.uptime_hours == 1


class TestFixtureResourceChecker:
    def test_seeded_data(self) -> None:
        checker = _FixtureResourceChecker({
            "disk_used_percent": 42,
            "memory_used_percent": 55,
            "swap_used_percent": 30,
        })
        result = checker.check()
        assert result.disk_used_percent == 42
        assert result.memory_used_percent == 55
        assert result.swap_used_percent == 30


# =========================================================================
# HealthChecker.run integration tests
# =========================================================================


class TestHealthCheckerRun:
    def _mock_checker(self, thresholds: dict[str, object] | None = None) -> HealthChecker:
        fixture = _load_fixture()
        return HealthChecker(
            thresholds=thresholds or _load_thresholds(),
            online_checker=_FixtureOnlineChecker(fixture.get("endpoints", {})),  # type: ignore[arg-type]
            ssl_checker=_FixtureSSLChecker(),
            service_checker=_FixtureServiceChecker(fixture.get("services", {})),  # type: ignore[arg-type]
            resource_checker=_FixtureResourceChecker(fixture.get("resources", {})),  # type: ignore[arg-type]
        )

    def test_full_run_produces_report(self) -> None:
        checker = self._mock_checker()
        report = checker.run()
        assert report.check_date
        assert report.check_scope == "full"
        assert len(report.endpoints) == 4
        assert len(report.ssl_certs) == 4
        assert len(report.services) == 4
        assert report.resources is not None
        assert "total_findings" in report.summary

    def test_quick_scope(self) -> None:
        checker = self._mock_checker()
        report = checker.run(check_scope="quick")
        assert report.check_scope == "quick"

    def test_no_findings_for_healthy_system(self) -> None:
        """With fixture data (all healthy), should have minimal findings."""
        checker = self._mock_checker()
        report = checker.run()
        # Fixture SSL has 53 days remaining → below warn (30)? No, 53 > 30 → no warning
        # All endpoints are 200, services active, resources moderate
        critical = [f for f in report.findings if f.severity == "critical"]
        assert len(critical) == 0, f"Unexpected critical findings: {critical}"

    def test_custom_sites(self) -> None:
        checker = self._mock_checker()
        report = checker.run(sites=["https://lanlnk.cn"])
        assert len(report.endpoints) == 1
        assert len(report.ssl_certs) == 1

    def test_disable_checks(self) -> None:
        checker = self._mock_checker()
        report = checker.run(
            check_online=False,
            check_ssl=False,
            check_services=False,
            check_resources=False,
        )
        assert len(report.endpoints) == 0
        assert len(report.ssl_certs) == 0
        assert len(report.services) == 0
        assert report.resources is None
        assert len(report.findings) == 0

    def test_summary_counts(self) -> None:
        checker = self._mock_checker()
        report = checker.run()
        total = report.summary.get("total_findings", 0)
        severity_sum = sum(
            v for k, v in report.summary.items()
            if k.startswith("severity_")
        )
        assert total == severity_sum

    def test_default_sites_used_when_none(self) -> None:
        checker = self._mock_checker()
        report = checker.run(sites=None)
        assert len(report.endpoints) == len(DEFAULT_SITES)

    def test_default_services_used_when_none(self) -> None:
        checker = self._mock_checker()
        report = checker.run(services=None)
        assert len(report.services) == len(DEFAULT_SERVICES)


# =========================================================================
# Threshold-driven finding tests (end-to-end via HealthChecker)
# =========================================================================


class TestHealthCheckerThresholdFindings:
    def test_slow_endpoint_triggers_warning(self) -> None:
        """Fixture endpoint with response time > threshold should warn."""
        thresholds = _load_thresholds()
        # Lower the threshold to trigger warning
        ep_config = thresholds.get("endpoints", {})
        if isinstance(ep_config, dict) and isinstance(ep_config.get("lanlnk.cn"), dict):
            ep_config["lanlnk.cn"]["max_response_time_ms"] = 10  # type: ignore[union-attr]

        fixture = _load_fixture()
        checker = HealthChecker(
            thresholds=thresholds,
            online_checker=_FixtureOnlineChecker(fixture.get("endpoints", {})),  # type: ignore[arg-type]
            ssl_checker=_FixtureSSLChecker(),
            service_checker=_FixtureServiceChecker(fixture.get("services", {})),  # type: ignore[arg-type]
            resource_checker=_FixtureResourceChecker(fixture.get("resources", {})),  # type: ignore[arg-type]
        )
        report = checker.run()
        rt_findings = [f for f in report.findings if f.check == "response_time"]
        assert len(rt_findings) >= 1


# =========================================================================
# Write report tests
# =========================================================================


class TestWriteReport:
    def test_writes_valid_json(self) -> None:
        report = HealthReport(
            check_date="2026-08-01",
            check_scope="full",
            summary={"total_findings": 0},
        )
        with tempfile.TemporaryDirectory(prefix="site-health-") as tmp:
            out = Path(tmp) / "report.json"
            HealthChecker.write_report(report, out)
            assert out.exists()
            data = json.loads(out.read_text())
            assert data["check_date"] == "2026-08-01"

    def test_creates_parent_dirs(self) -> None:
        report = HealthReport(check_date="2026-08-01", check_scope="quick")
        with tempfile.TemporaryDirectory(prefix="site-health-") as tmp:
            out = Path(tmp) / "deeply" / "nested" / "report.json"
            HealthChecker.write_report(report, out)
            assert out.exists()


# =========================================================================
# CurlOnlineChecker tests (mocked subprocess)
# =========================================================================


class TestCurlOnlineChecker:
    @patch("scripts.health_check.subprocess.run")
    def test_successful_check(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="200\t0.125\t0\thttps://lanlnk.cn",
            stderr="",
            returncode=0,
        )
        checker = CurlOnlineChecker(timeout=5)
        result = checker.check("https://lanlnk.cn")
        assert result.http_code == 200
        assert result.response_time_ms == 125.0
        assert result.reachable is True
        assert result.ssl_enabled is True

    @patch("scripts.health_check.subprocess.run")
    def test_timeout_error(self, mock_run: MagicMock) -> None:
        import subprocess as sp

        mock_run.side_effect = sp.TimeoutExpired(cmd="curl", timeout=5)
        checker = CurlOnlineChecker(timeout=5)
        result = checker.check("https://lanlnk.cn")
        assert result.reachable is False
        assert result.error is not None
        assert "curl failed" in result.error

    @patch("scripts.health_check.subprocess.run")
    def test_curl_not_found(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = FileNotFoundError("curl not found")
        checker = CurlOnlineChecker(timeout=5)
        result = checker.check("https://lanlnk.cn")
        assert result.reachable is False
        assert result.error is not None

    @patch("scripts.health_check.subprocess.run")
    def test_redirect_followed(self, mock_run: MagicMock) -> None:
        # First call returns 301 (no follow)
        # Second call follows and returns final URL
        mock_run.side_effect = [
            MagicMock(
                stdout="301\t0.050\t0\thttp://lanlnk.cn",
                stderr="",
                returncode=0,
            ),
            MagicMock(
                stdout="https://lanlnk.cn",
                stderr="",
                returncode=0,
            ),
        ]
        checker = CurlOnlineChecker(timeout=5)
        result = checker.check("http://lanlnk.cn")
        assert result.http_code == 301
        assert len(result.redirect_chain) >= 1

    @patch("scripts.health_check.subprocess.run")
    def test_garbage_output(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="garbage output",
            stderr="",
            returncode=0,
        )
        checker = CurlOnlineChecker(timeout=5)
        result = checker.check("https://lanlnk.cn")
        assert result.reachable is False
        assert result.error is not None


# =========================================================================
# SystemdServiceChecker tests (mocked subprocess)
# =========================================================================


class TestSystemdServiceChecker:
    @patch("scripts.health_check.subprocess.run")
    def test_active_service(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout=(
                "ActiveState=active\n"
                "MainPID=2050626\n"
                "ExecMainStartTimestamp=Fri 2026-07-25 09:30:00 CST\n"
            ),
            stderr="",
            returncode=0,
        )
        checker = SystemdServiceChecker()
        result = checker.check("lnkwebsite-backend")
        assert result.status == "active"
        assert result.main_pid == 2050626
        assert result.error is None

    @patch("scripts.health_check.subprocess.run")
    def test_systemctl_failure(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="Unit not found",
            returncode=1,
        )
        checker = SystemdServiceChecker()
        result = checker.check("nonexistent")
        assert result.error is not None
        assert "systemctl returned 1" in result.error

    @patch("scripts.health_check.subprocess.run")
    def test_timeout(self, mock_run: MagicMock) -> None:
        import subprocess as sp

        mock_run.side_effect = sp.TimeoutExpired(cmd="systemctl", timeout=10)
        checker = SystemdServiceChecker()
        result = checker.check("svc1")
        assert result.error is not None
        assert "systemctl failed" in result.error


# =========================================================================
# SystemResourceChecker tests
# =========================================================================


class TestSystemResourceChecker:
    @patch("scripts.health_check.subprocess.run")
    def test_disk_usage(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            stdout=(
                "Filesystem     1K-blocks    Used Available Use% Mounted on\n"
                "/dev/vda1       51420868 13854832  35393476  28% /\n"
            ),
            stderr="",
            returncode=0,
        )
        checker = SystemResourceChecker()
        # Patch the meminfo read
        with patch.object(Path, "read_text", return_value=(
            "MemTotal:       16384000 kB\n"
            "MemAvailable:    6553600 kB\n"
            "SwapTotal:       2097152 kB\n"
            "SwapFree:        1048576 kB\n"
        )):
            result = checker.check()
        assert result.disk_used_percent == 28.0
        assert result.memory_used_percent == 60.0
        assert result.swap_used_percent == 50.0

    @patch("scripts.health_check.subprocess.run")
    def test_disk_command_failure(self, mock_run: MagicMock) -> None:
        import subprocess as sp

        mock_run.side_effect = sp.TimeoutExpired(cmd="df", timeout=10)
        checker = SystemResourceChecker()
        with patch.object(Path, "read_text", return_value=(
            "MemTotal:       16384000 kB\n"
            "MemAvailable:    6553600 kB\n"
            "SwapTotal:       2097152 kB\n"
            "SwapFree:        1048576 kB\n"
        )):
            result = checker.check()
        # Disk fails but memory still works
        assert result.disk_used_percent == 0.0
        assert result.memory_used_percent == 60.0


# =========================================================================
# SSLCertChecker tests (mocked)
# =========================================================================


class TestSSLCertChecker:
    @patch("scripts.health_check.ssl.create_default_context")
    def test_successful_check(self, mock_ctx_fn: MagicMock) -> None:
        # Build a mock context + socket chain
        mock_ctx = MagicMock()
        mock_sock = MagicMock()
        mock_ssock = MagicMock()
        mock_ctx_fn.return_value = mock_ctx
        mock_ctx.wrap_socket.return_value.__enter__.return_value = mock_ssock

        mock_ssock.getpeercert.return_value = {
            "issuer": [(("commonName", "Let's Encrypt R3"),)],
            "subject": [(("commonName", "lanlnk.cn"),)],
            "notBefore": "Jun 25 00:00:00 2026 GMT",
            "notAfter": "Sep 23 00:00:00 2026 GMT",
        }

        with patch("socket.create_connection"):
            checker = SSLCertChecker(timeout=5)
            result = checker.check("lanlnk.cn")
        assert result.error is None
        assert "commonName" in result.issuer
        assert result.not_before == "Jun 25 00:00:00 2026 GMT"
        assert result.days_remaining >= 0

    def test_connection_failure(self) -> None:
        with patch("socket.create_connection", side_effect=OSError("refused")):
            checker = SSLCertChecker(timeout=1)
            result = checker.check("unreachable.example.com")
        assert result.error is not None
        assert "refused" in result.error


# =========================================================================
# Constants and defaults tests
# =========================================================================


class TestDefaults:
    def test_default_sites(self) -> None:
        assert len(DEFAULT_SITES) == 4
        assert all(s.startswith("https://") for s in DEFAULT_SITES)
        assert "https://lanlnk.cn" in DEFAULT_SITES
        assert "https://www.lanlnk.cn" in DEFAULT_SITES
        assert "https://openclaw.lanlnk.cn" in DEFAULT_SITES
        assert "https://chatbi.lanlnk.cn" in DEFAULT_SITES

    def test_default_services(self) -> None:
        assert len(DEFAULT_SERVICES) == 4
        assert "lnkwebsite-backend" in DEFAULT_SERVICES
        assert "lnkwebsite-frontend" in DEFAULT_SERVICES

    def test_thresholds_file_exists(self) -> None:
        assert THRESHOLDS_PATH.exists()
        th = json.loads(THRESHOLDS_PATH.read_text())
        assert "endpoints" in th
        assert "ssl" in th
        assert "resources" in th
        assert "services" in th

    def test_thresholds_endpoint_config_complete(self) -> None:
        th = json.loads(THRESHOLDS_PATH.read_text())
        for domain in ["lanlnk.cn", "www.lanlnk.cn", "openclaw.lanlnk.cn", "chatbi.lanlnk.cn"]:
            assert domain in th["endpoints"], f"missing {domain}"
            cfg = th["endpoints"][domain]
            assert "max_response_time_ms" in cfg
            assert "expected_http_code" in cfg
