"""Production site-health-operations workflow.

Performs read-only health checks across four dimensions:
    1. HTTP endpoint checks (status code, response time, redirect chain)
    2. SSL certificate expiry
    3. Systemd service status
    4. System resource usage (disk, memory, swap)

**Never** performs any write action.  See ``ForbiddenActions`` in SKILL.md.

Usage (programmatic)::

    checker = HealthChecker(thresholds=ths)
    report = checker.run(
        sites=SITES,
        check_online=True,
        check_ssl=True,
    )
    checker.write_report(report, output_path)

Usage (CLI, synthetic mode)::

    uv run python -m scripts.health_check \\
        --fixture fixtures/synthetic-fixture.json \\
        --thresholds config/thresholds.json \\
        --output /tmp/site-health/health-baseline-report.json

Usage (CLI, live mode)::

    uv run python -m scripts.health_check \\
        --thresholds config/thresholds.json \\
        --live \\
        --output /tmp/site-health/health-baseline-report.json
"""

from __future__ import annotations

import json
import ssl
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
class EndpointResult:
    """Result of checking a single HTTP endpoint."""

    url: str
    http_code: int = 0
    response_time_ms: float = 0.0
    final_url: str = ""
    redirect_chain: list[str] = field(default_factory=list)
    ssl_enabled: bool = False
    reachable: bool = False
    error: str | None = None


@dataclass
class SSLResult:
    """Result of checking a single domain's SSL certificate."""

    domain: str
    issuer: str = ""
    subject: str = ""
    not_before: str = ""
    not_after: str = ""
    days_remaining: int = 0
    error: str | None = None


@dataclass
class ServiceResult:
    """Result of checking a single systemd service."""

    name: str
    status: str = "unknown"
    main_pid: int = 0
    uptime_hours: float = 0.0
    error: str | None = None


@dataclass
class ResourceResult:
    """System resource snapshot."""

    disk_used_percent: float = 0.0
    memory_used_percent: float = 0.0
    swap_used_percent: float = 0.0


@dataclass
class HealthFinding:
    """A single health alert/warning."""

    check: str
    target: str
    severity: str  # "info" | "warning" | "critical"
    message: str
    current_value: str = ""
    threshold: str = ""


@dataclass
class HealthReport:
    """Complete health check result."""

    check_date: str
    check_scope: str  # "quick" | "full"
    endpoints: list[EndpointResult] = field(default_factory=list)
    ssl_certs: list[SSLResult] = field(default_factory=list)
    services: list[ServiceResult] = field(default_factory=list)
    resources: ResourceResult | None = None
    findings: list[HealthFinding] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "check_date": self.check_date,
            "check_scope": self.check_scope,
            "endpoints": [
                {
                    "url": e.url,
                    "http_code": e.http_code,
                    "response_time_ms": round(e.response_time_ms, 1),
                    "final_url": e.final_url,
                    "redirect_chain": e.redirect_chain,
                    "ssl_enabled": e.ssl_enabled,
                    "reachable": e.reachable,
                    **({"error": e.error} if e.error else {}),
                }
                for e in self.endpoints
            ],
            "ssl_certs": [
                {
                    "domain": s.domain,
                    "issuer": s.issuer,
                    "subject": s.subject,
                    "not_before": s.not_before,
                    "not_after": s.not_after,
                    "days_remaining": s.days_remaining,
                    **({"error": s.error} if s.error else {}),
                }
                for s in self.ssl_certs
            ],
            "services": [
                {
                    "name": s.name,
                    "status": s.status,
                    "main_pid": s.main_pid,
                    "uptime_hours": round(s.uptime_hours, 1),
                    **({"error": s.error} if s.error else {}),
                }
                for s in self.services
            ],
            "resources": (
                {
                    "disk_used_percent": round(self.resources.disk_used_percent, 1),
                    "memory_used_percent": round(self.resources.memory_used_percent, 1),
                    "swap_used_percent": round(self.resources.swap_used_percent, 1),
                }
                if self.resources
                else None
            ),
            "findings": [
                {
                    "check": f.check,
                    "target": f.target,
                    "severity": f.severity,
                    "message": f.message,
                    "current_value": f.current_value,
                    "threshold": f.threshold,
                }
                for f in self.findings
            ],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Protocols for dependency injection
# ---------------------------------------------------------------------------


class OnlineCheckerProtocol(Protocol):
    """Check a URL's HTTP status and redirect chain. Read-only."""

    def check(self, url: str) -> EndpointResult:
        """Return EndpointResult for the URL."""
        ...


class SSLCheckerProtocol(Protocol):
    """Check a domain's SSL certificate. Read-only."""

    def check(self, domain: str, port: int = 443) -> SSLResult:
        """Return SSLResult for the domain."""
        ...


class ServiceCheckerProtocol(Protocol):
    """Check a systemd service status. Read-only."""

    def check(self, service_name: str) -> ServiceResult:
        """Return ServiceResult for the service."""
        ...


class ResourceCheckerProtocol(Protocol):
    """Check system resource usage. Read-only."""

    def check(self) -> ResourceResult:
        """Return ResourceResult snapshot."""
        ...


# ---------------------------------------------------------------------------
# Built-in curl-based online checker
# ---------------------------------------------------------------------------


class CurlOnlineChecker:
    """Check URLs via the system ``curl`` binary. Read-only."""

    def __init__(self, *, timeout: int = 10) -> None:
        self._timeout = timeout

    def check(self, url: str) -> EndpointResult:
        """Check a single URL via curl.

        Uses ``curl -L`` to follow redirects and captures:
        - Final HTTP status code
        - Total time (approximated as response_time_ms)
        - Redirect chain (parsed from verbose output)
        """
        result = EndpointResult(url=url)

        # First, get status code + timing without following redirects
        cmd_no_follow = [
            "curl",
            "-s",
            "-o", "/dev/null",
            "-w", "%{http_code}\t%{time_total}\t%{ssl_verify_result}\t%{url_effective}",
            "--max-time", str(self._timeout),
            "--no-location",
            url,
        ]

        try:
            proc = subprocess.run(  # noqa: S603
                cmd_no_follow,
                capture_output=True,
                text=True,
                timeout=self._timeout + 5,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            result.error = f"curl failed: {exc}"
            return result

        output = proc.stdout.strip()
        parts = output.split("\t")
        if not parts or not parts[0].isdigit():
            result.error = f"unexpected curl output: {output}"
            return result

        result.http_code = int(parts[0])
        result.response_time_ms = float(parts[1]) * 1000 if len(parts) > 1 else 0.0
        result.ssl_enabled = url.startswith("https://")
        result.reachable = result.http_code > 0

        # If there's a redirect (3xx), follow it to build the chain
        if 300 <= result.http_code < 400:
            result.redirect_chain.append(url)
            self._follow_chain(url, result)
        elif result.http_code >= 200:
            result.final_url = url

        return result

    def _follow_chain(self, start_url: str, result: EndpointResult) -> None:
        """Follow a redirect chain using verbose curl output."""
        cmd = [
            "curl",
            "-s",
            "-L",
            "-o", "/dev/null",
            "-w", "%{url_effective}",
            "--max-time", str(self._timeout),
            start_url,
        ]

        try:
            proc = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout + 5,
                check=False,
            )
            result.final_url = proc.stdout.strip()
            if result.final_url and result.final_url != start_url:
                result.redirect_chain.append(result.final_url)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Leave chain as-is


# ---------------------------------------------------------------------------
# Built-in SSL checker
# ---------------------------------------------------------------------------


class SSLCertChecker:
    """Check SSL certificate expiry via Python ``ssl`` module. Read-only."""

    def __init__(self, *, timeout: int = 10) -> None:
        self._timeout = timeout

    def check(self, domain: str, port: int = 443) -> SSLResult:
        """Check SSL certificate for a domain."""
        result = SSLResult(domain=domain)

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            import socket
            with socket.create_connection((domain, port), timeout=self._timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()

            if cert:
                result.issuer = dict(x[0] for x in cert.get("issuer", []))
                result.subject = dict(x[0] for x in cert.get("subject", []))
                result.not_before = cert.get("notBefore", "")
                result.not_after = cert.get("notAfter", "")

                if result.not_after:
                    expiry_date = ssl.cert_time_to_seconds(result.not_after)
                    now = time.time()
                    result.days_remaining = int((expiry_date - now) / 86400)
            else:
                result.error = "no certificate returned"

        except Exception as exc:  # noqa: BLE001
            result.error = str(exc)

        return result


# ---------------------------------------------------------------------------
# Built-in systemd service checker
# ---------------------------------------------------------------------------


class SystemdServiceChecker:
    """Check systemd service status via ``systemctl``. Read-only."""

    def check(self, service_name: str) -> ServiceResult:
        """Check a single systemd service."""
        result = ServiceResult(name=service_name)

        cmd = [
            "systemctl",
            "show",
            service_name,
            "--property=ActiveState,MainPID,ExecMainStartTimestamp",
        ]

        try:
            proc = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            result.error = f"systemctl failed: {exc}"
            return result

        if proc.returncode != 0:
            result.error = f"systemctl returned {proc.returncode}: {proc.stderr.strip()}"
            return result

        for line in proc.stdout.strip().splitlines():
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            if key == "ActiveState":
                result.status = val.strip()
            elif key == "MainPID":
                try:
                    result.main_pid = int(val)
                except ValueError:
                    pass
            elif key == "ExecMainStartTimestamp":
                # Parse timestamp like "Fri 2026-07-25 09:30:00 CST"
                result.uptime_hours = self._calc_uptime_hours(val.strip())

        return result

    @staticmethod
    def _calc_uptime_hours(timestamp_str: str) -> float:
        """Calculate uptime hours from a systemctl timestamp string."""
        if not timestamp_str:
            return 0.0
        try:
            # Parse "Fri 2026-07-25 09:30:00 CST" format
            parts = timestamp_str.split()
            if len(parts) >= 3:
                date_str = f"{parts[1]} {parts[2]}"
                start = time.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                start_epoch = time.mktime(start)
                now = time.time()
                return max(0.0, (now - start_epoch) / 3600)
        except (ValueError, OverflowError):
            pass
        return 0.0


# ---------------------------------------------------------------------------
# Built-in resource checker
# ---------------------------------------------------------------------------


class SystemResourceChecker:
    """Check disk, memory, swap usage. Read-only."""

    def check(self) -> ResourceResult:
        """Return system resource snapshot."""
        result = ResourceResult()

        # Disk usage (root partition)
        try:
            proc = subprocess.run(  # noqa: S603
                ["df", "/"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            lines = proc.stdout.strip().splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    pct_str = parts[4].rstrip("%")
                    result.disk_used_percent = float(pct_str)
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass

        # Memory + swap via /proc/meminfo (no external dependency)
        try:
            meminfo = Path("/proc/meminfo").read_text()
            mem_total = 0
            mem_available = 0
            swap_total = 0
            swap_free = 0
            for line in meminfo.splitlines():
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem_available = int(line.split()[1])
                elif line.startswith("SwapTotal:"):
                    swap_total = int(line.split()[1])
                elif line.startswith("SwapFree:"):
                    swap_free = int(line.split()[1])

            if mem_total > 0:
                result.memory_used_percent = round(
                    (1 - mem_available / mem_total) * 100, 1
                )
            if swap_total > 0:
                result.swap_used_percent = round(
                    (1 - swap_free / swap_total) * 100, 1
                )
        except (FileNotFoundError, ValueError, IndexError):
            pass

        return result


# ---------------------------------------------------------------------------
# Default site list
# ---------------------------------------------------------------------------

DEFAULT_SITES: list[str] = [
    "https://lanlnk.cn",
    "https://www.lanlnk.cn",
    "https://openclaw.lanlnk.cn",
    "https://chatbi.lanlnk.cn",
]

DEFAULT_SERVICES: list[str] = [
    "lnkwebsite-backend",
    "lnkwebsite-frontend",
    "lnkwebsite-admin",
    "lnkwebsite-h5",
]


# ---------------------------------------------------------------------------
# Threshold evaluation
# ---------------------------------------------------------------------------

def _evaluate_endpoint(
    ep: EndpointResult,
    config: dict[str, object],
    findings: list[HealthFinding],
) -> None:
    """Evaluate an endpoint result against threshold config."""
    target = ep.url

    # Unreachable
    if not ep.reachable:
        findings.append(HealthFinding(
            check="endpoint_reachable",
            target=target,
            severity="critical",
            message=f"{target} is unreachable",
            current_value=ep.error or f"HTTP {ep.http_code}",
        ))
        return

    # HTTP status code
    expected_code = config.get("expected_http_code")
    if expected_code and ep.http_code != expected_code:
        findings.append(HealthFinding(
            check="http_status",
            target=target,
            severity="critical" if ep.http_code >= 500 else "warning",
            message=f"{target} returned HTTP {ep.http_code}, expected {expected_code}",
            current_value=str(ep.http_code),
            threshold=str(expected_code),
        ))

    # Response time
    max_rt = config.get("max_response_time_ms")
    if max_rt and ep.response_time_ms > float(max_rt):
        findings.append(HealthFinding(
            check="response_time",
            target=target,
            severity="warning",
            message=(
                f"{target} response time {ep.response_time_ms:.0f}ms "
                f"exceeds threshold {max_rt}ms"
            ),
            current_value=f"{ep.response_time_ms:.0f}ms",
            threshold=f"{max_rt}ms",
        ))

    # Expected redirect
    expected_redirect = config.get("expected_redirect")
    if expected_redirect and ep.redirect_chain:
        if ep.final_url and expected_redirect not in ep.final_url:
            findings.append(HealthFinding(
                check="redirect_target",
                target=target,
                severity="warning",
                message=(
                    f"{target} redirected to {ep.final_url}, "
                    f"expected {expected_redirect}"
                ),
                current_value=ep.final_url,
                threshold=str(expected_redirect),
            ))

    # HTTPS check
    expected_https = config.get("expected_https")
    if expected_https and not ep.ssl_enabled:
        findings.append(HealthFinding(
            check="https_enabled",
            target=target,
            severity="warning",
            message=f"{target} is not using HTTPS",
            current_value="http",
            threshold="https",
        ))


def _evaluate_ssl(
    ssl_result: SSLResult,
    ssl_config: dict[str, object],
    findings: list[HealthFinding],
) -> None:
    """Evaluate an SSL certificate result against thresholds."""
    if ssl_result.error:
        findings.append(HealthFinding(
            check="ssl_certificate",
            target=ssl_result.domain,
            severity="critical",
            message=f"SSL check failed for {ssl_result.domain}: {ssl_result.error}",
        ))
        return

    critical_days = int(ssl_config.get("critical_days_remaining", 7))
    warn_days = int(ssl_config.get("warn_days_remaining", 30))

    if ssl_result.days_remaining <= critical_days:
        findings.append(HealthFinding(
            check="ssl_expiry",
            target=ssl_result.domain,
            severity="critical",
            message=(
                f"SSL certificate for {ssl_result.domain} expires in "
                f"{ssl_result.days_remaining} days ({ssl_result.not_after})"
            ),
            current_value=f"{ssl_result.days_remaining} days",
            threshold=f"≤{critical_days} days",
        ))
    elif ssl_result.days_remaining <= warn_days:
        findings.append(HealthFinding(
            check="ssl_expiry",
            target=ssl_result.domain,
            severity="warning",
            message=(
                f"SSL certificate for {ssl_result.domain} expires in "
                f"{ssl_result.days_remaining} days ({ssl_result.not_after})"
            ),
            current_value=f"{ssl_result.days_remaining} days",
            threshold=f"≤{warn_days} days",
        ))


def _evaluate_service(
    svc: ServiceResult,
    svc_config: dict[str, object],
    findings: list[HealthFinding],
) -> None:
    """Evaluate a service result against expected status."""
    expected = svc_config.get("expected_status", "active")

    if svc.error:
        findings.append(HealthFinding(
            check="service_status",
            target=svc.name,
            severity="warning",
            message=f"Could not check service {svc.name}: {svc.error}",
        ))
        return

    if svc.status != expected:
        findings.append(HealthFinding(
            check="service_status",
            target=svc.name,
            severity="critical" if svc.status in ("failed", "inactive") else "warning",
            message=(
                f"Service {svc.name} status is '{svc.status}', "
                f"expected '{expected}'"
            ),
            current_value=svc.status,
            threshold=expected,
        ))


def _evaluate_resources(
    res: ResourceResult,
    res_config: dict[str, object],
    findings: list[HealthFinding],
) -> None:
    """Evaluate resource usage against thresholds."""
    pairs: list[tuple[str, float, str, str]] = [
        ("disk", res.disk_used_percent, "disk_warn_percent", "disk_critical_percent"),
        ("memory", res.memory_used_percent, "memory_warn_percent", "memory_critical_percent"),
        ("swap", res.swap_used_percent, "swap_warn_percent", "swap_critical_percent"),
    ]

    for label, value, warn_key, crit_key in pairs:
        warn = float(res_config.get(warn_key, 999))
        crit = float(res_config.get(crit_key, 999))

        if value >= crit:
            findings.append(HealthFinding(
                check=f"resource_{label}",
                target="system",
                severity="critical",
                message=f"{label.capitalize()} usage {value:.1f}% exceeds critical threshold {crit}%",
                current_value=f"{value:.1f}%",
                threshold=f"{crit}%",
            ))
        elif value >= warn:
            findings.append(HealthFinding(
                check=f"resource_{label}",
                target="system",
                severity="warning",
                message=f"{label.capitalize()} usage {value:.1f}% exceeds warn threshold {warn}%",
                current_value=f"{value:.1f}%",
                threshold=f"{warn}%",
            ))


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


class HealthChecker:
    """Orchestrates the site health check workflow.

    Read-only. Never modifies any service, configuration, or file.
    """

    def __init__(
        self,
        thresholds: dict[str, object] | None = None,
        online_checker: OnlineCheckerProtocol | None = None,
        ssl_checker: SSLCheckerProtocol | None = None,
        service_checker: ServiceCheckerProtocol | None = None,
        resource_checker: ResourceCheckerProtocol | None = None,
    ) -> None:
        self._thresholds = thresholds or {}
        self._online_checker = online_checker
        self._ssl_checker = ssl_checker
        self._service_checker = service_checker
        self._resource_checker = resource_checker

    # ------------------------------------------------------------------
    # Individual check helpers
    # ------------------------------------------------------------------

    def _check_endpoint(self, url: str) -> EndpointResult:
        """Check a single endpoint, using injected checker or curl."""
        if self._online_checker is not None:
            return self._online_checker.check(url)
        return CurlOnlineChecker().check(url)

    def _check_ssl(self, domain: str, port: int = 443) -> SSLResult:
        """Check SSL cert for a domain."""
        if self._ssl_checker is not None:
            return self._ssl_checker.check(domain, port)
        return SSLCertChecker().check(domain, port)

    def _check_service(self, name: str) -> ServiceResult:
        """Check a single systemd service."""
        if self._service_checker is not None:
            return self._service_checker.check(name)
        return SystemdServiceChecker().check(name)

    def _check_resources(self) -> ResourceResult:
        """Get system resource snapshot."""
        if self._resource_checker is not None:
            return self._resource_checker.check()
        return SystemResourceChecker().check()

    # ------------------------------------------------------------------
    # Full health check
    # ------------------------------------------------------------------

    def run(
        self,
        *,
        sites: list[str] | None = None,
        services: list[str] | None = None,
        check_online: bool = True,
        check_ssl: bool = True,
        check_services: bool = True,
        check_resources: bool = True,
        check_scope: str = "full",
    ) -> HealthReport:
        """Run the full health check suite.

        Args:
            sites: List of URLs to check. Defaults to ``DEFAULT_SITES``.
            services: List of systemd service names. Defaults to ``DEFAULT_SERVICES``.
            check_online: Whether to perform HTTP endpoint checks.
            check_ssl: Whether to perform SSL certificate checks.
            check_services: Whether to perform systemd service checks.
            check_resources: Whether to perform resource usage checks.
            check_scope: ``quick`` or ``full``.

        Returns:
            HealthReport with all results and findings.
        """
        sites = sites if sites is not None else list(DEFAULT_SITES)
        services = services if services is not None else list(DEFAULT_SERVICES)
        findings: list[HealthFinding] = []
        report = HealthReport(
            check_date=time.strftime("%Y-%m-%d"),
            check_scope=check_scope,
        )

        # 1. Endpoint checks
        if check_online:
            ep_config = self._thresholds.get("endpoints", {})
            if not isinstance(ep_config, dict):
                ep_config = {}
            for url in sites:
                result = self._check_endpoint(url)
                report.endpoints.append(result)
                # Find matching config by domain
                domain = url.replace("https://", "").replace("http://", "").rstrip("/")
                cfg = ep_config.get(domain, {})
                if isinstance(cfg, dict):
                    _evaluate_endpoint(result, cfg, findings)

        # 2. SSL checks
        if check_ssl:
            ssl_config = self._thresholds.get("ssl", {})
            if not isinstance(ssl_config, dict):
                ssl_config = {}
            for url in sites:
                domain = url.replace("https://", "").replace("http://", "").rstrip("/")
                ssl_result = self._check_ssl(domain)
                report.ssl_certs.append(ssl_result)
                _evaluate_ssl(ssl_result, ssl_config, findings)

        # 3. Service checks
        if check_services:
            svc_config = self._thresholds.get("services", {})
            if not isinstance(svc_config, dict):
                svc_config = {}
            for name in services:
                svc_result = self._check_service(name)
                report.services.append(svc_result)
                cfg = svc_config.get(name, {})
                if isinstance(cfg, dict):
                    _evaluate_service(svc_result, cfg, findings)

        # 4. Resource checks
        if check_resources:
            res_config = self._thresholds.get("resources", {})
            if not isinstance(res_config, dict):
                res_config = {}
            res_result = self._check_resources()
            report.resources = res_result
            _evaluate_resources(res_result, res_config, findings)

        # Build summary
        severity_counts: dict[str, int] = {}
        check_counts: dict[str, int] = {}
        for f in findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
            check_counts[f.check] = check_counts.get(f.check, 0) + 1

        report.findings = findings
        report.summary = {
            "total_endpoints": len(report.endpoints),
            "total_ssl_certs": len(report.ssl_certs),
            "total_services": len(report.services),
            "total_findings": len(findings),
            **{f"severity_{k}": v for k, v in severity_counts.items()},
            **{f"check_{k}": v for k, v in check_counts.items()},
        }

        return report

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    @staticmethod
    def write_report(report: HealthReport, output_path: Path) -> None:
        """Write the health report to ``output_path`` as JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _cli() -> None:
    """CLI entry point for health check runs."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Site health operations runner (read-only)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Path to a fixture JSON file (synthetic mode)",
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "config" / "thresholds.json",
        help="Path to thresholds JSON (default: config/thresholds.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/site-health/health-baseline-report.json"),
        help="Output path for the health report",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live checks against real endpoints (default: fixture mode)",
    )
    parser.add_argument(
        "--scope",
        choices=["quick", "full"],
        default="full",
        help="Check scope (default: full)",
    )
    args = parser.parse_args()

    # Load thresholds
    thresholds: dict[str, object] = {}
    if args.thresholds.exists():
        thresholds = json.loads(args.thresholds.read_text(encoding="utf-8"))

    if args.live:
        # Live mode: check real endpoints
        checker = HealthChecker(thresholds=thresholds)
        report = checker.run(check_scope=args.scope)
    elif args.fixture:
        # Synthetic mode: use fixture data
        fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
        checker = _build_synthetic_checker(fixture, thresholds)
        report = checker.run(check_scope=args.scope)
    else:
        parser.error("either --fixture or --live is required")

    HealthChecker.write_report(report, args.output)

    # Print summary
    report_dict = report.to_dict()
    print(f"Health check complete: {report_dict['summary']['total_findings']} finding(s)")  # noqa: T201
    print(f"Report written to: {args.output}")  # noqa: T201

    if report_dict["findings"]:
        print("\nFindings summary:")  # noqa: T201
        for f in report_dict["findings"]:
            print(  # noqa: T201
                f"  [{f['severity']}] {f['check']}: {f['message']}"
            )


def _build_synthetic_checker(
    fixture: dict[str, object],
    thresholds: dict[str, object],
) -> HealthChecker:
    """Build a HealthChecker with mock checkers seeded from fixture data."""
    ep_data = fixture.get("endpoints", {})
    svc_data = fixture.get("services", {})
    res_data = fixture.get("resources", {})

    return HealthChecker(
        thresholds=thresholds,
        online_checker=_FixtureOnlineChecker(ep_data if isinstance(ep_data, dict) else {}),
        ssl_checker=_FixtureSSLChecker(),
        service_checker=_FixtureServiceChecker(svc_data if isinstance(svc_data, dict) else {}),
        resource_checker=_FixtureResourceChecker(
            res_data if isinstance(res_data, dict) else {}
        ),
    )


# ---------------------------------------------------------------------------
# Fixture-based mock checkers (for synthetic mode)
# ---------------------------------------------------------------------------


class _FixtureOnlineChecker:
    """Returns pre-seeded endpoint results from fixture data."""

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def check(self, url: str) -> EndpointResult:
        # Match by endpoint name in fixture, or build a default
        for _name, ep_raw in self._data.items():
            if not isinstance(ep_raw, dict):
                continue
            ep_url = str(ep_raw.get("url", ""))
            if ep_url == url or url.endswith(ep_url) or ep_url.endswith(url):
                return EndpointResult(
                    url=url,
                    http_code=int(ep_raw.get("http_code", 200)),
                    response_time_ms=float(ep_raw.get("response_time_ms", 50)),
                    final_url=ep_url or url,
                    redirect_chain=ep_raw.get("redirect_chain", []),
                    ssl_enabled=url.startswith("https://"),
                    reachable=True,
                )
        # Default healthy response for unknown URLs
        return EndpointResult(
            url=url,
            http_code=200,
            response_time_ms=50.0,
            final_url=url,
            ssl_enabled=url.startswith("https://"),
            reachable=True,
        )


class _FixtureSSLChecker:
    """Returns healthy SSL results for fixture mode."""

    def check(self, domain: str, port: int = 443) -> SSLResult:
        return SSLResult(
            domain=domain,
            issuer={"commonName": "Let's Encrypt R3"},
            subject={"commonName": domain},
            not_before="Jun 25 00:00:00 2026 GMT",
            not_after="Sep 23 00:00:00 2026 GMT",
            days_remaining=53,
        )


class _FixtureServiceChecker:
    """Returns pre-seeded service results from fixture data."""

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def check(self, service_name: str) -> ServiceResult:
        raw = self._data.get(service_name, {})
        if not isinstance(raw, dict):
            raw = {}
        return ServiceResult(
            name=service_name,
            status=str(raw.get("status", "active")),
            main_pid=int(raw.get("main_pid", 0)),
            uptime_hours=float(raw.get("uptime_hours", 1)),
        )


class _FixtureResourceChecker:
    """Returns pre-seeded resource data from fixture."""

    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def check(self) -> ResourceResult:
        return ResourceResult(
            disk_used_percent=float(self._data.get("disk_used_percent", 0)),
            memory_used_percent=float(self._data.get("memory_used_percent", 0)),
            swap_used_percent=float(self._data.get("swap_used_percent", 0)),
        )


if __name__ == "__main__":
    _cli()
