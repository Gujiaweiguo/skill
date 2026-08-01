"""Production redirect-audit workflow.

Cross-checks redirect data from multiple sources to identify drift.
Read-only: never creates, modifies, or deletes redirects.

Sources compared:
    1. DB (via MCP ``redirect_list`` or injected list)
    2. Docs (``redirect-map.md`` or injected list)
    3. Online (``curl`` or injected HTTP check results)

Usage (programmatic)::

    runner = AuditRunner(audit_scope="cross-check")
    report = runner.run(records, online_results)
    runner.write_report(report, output_path)

Usage (CLI, synthetic mode)::

    uv run python -m scripts.audit_runner \\
        --fixture fixtures/synthetic-fixture.json \\
        --output /tmp/redirect-drift-report.json
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
class RedirectRecord:
    """A single redirect's state across all tracked sources."""

    source_url: str
    db_status: str = "missing"
    doc_status: str = "missing"
    nginx_status: str = "unknown"
    online_status_code: int = 0
    online_target: str | None = None
    expected_target: str | None = None
    notes: str = ""


@dataclass
class DriftFinding:
    """A single detected drift between sources."""

    source_url: str
    drift_type: str
    severity: str  # "info" | "warning" | "critical"
    description: str
    db_status: str
    doc_status: str
    nginx_status: str
    online_status_code: int


@dataclass
class AuditReport:
    """Complete audit result."""

    audit_date: str
    audit_scope: str
    total_checked: int
    drifts: list[DriftFinding] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "audit_date": self.audit_date,
            "audit_scope": self.audit_scope,
            "total_checked": self.total_checked,
            "total_drifts": len(self.drifts),
            "drifts": [
                {
                    "source_url": d.source_url,
                    "drift_type": d.drift_type,
                    "severity": d.severity,
                    "description": d.description,
                    "db_status": d.db_status,
                    "doc_status": d.doc_status,
                    "nginx_status": d.nginx_status,
                    "online_status_code": d.online_status_code,
                }
                for d in self.drifts
            ],
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Online check protocol (for dependency injection)
# ---------------------------------------------------------------------------


class OnlineCheckerProtocol(Protocol):
    """Check a URL's HTTP redirect chain. Read-only."""

    def check(self, url: str) -> dict[str, object]:
        """Return ``{"status_code": int, "target": str | None, "reachable": bool}``."""
        ...


# ---------------------------------------------------------------------------
# Built-in curl-based online checker
# ---------------------------------------------------------------------------


class CurlOnlineChecker:
    """Check URLs via the system ``curl`` binary. Read-only."""

    def __init__(self, *, timeout: int = 10, follow: bool = False) -> None:
        self._timeout = timeout
        self._follow = follow

    def check(self, url: str) -> dict[str, object]:
        """Check a single URL via curl.

        Returns ``{"status_code": int, "target": str | None, "reachable": bool}``.
        """
        cmd = [
            "curl",
            "-s",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}\\t%{redirect_url}",
            "--max-time",
            str(self._timeout),
        ]
        if not self._follow:
            cmd.append("--no-location")
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
                "target": None,
                "reachable": False,
            }

        output = result.stdout.strip()
        parts = output.split("\t", 1)
        status_code = int(parts[0]) if parts[0].isdigit() else 0
        target = parts[1] if len(parts) > 1 and parts[1] else None

        return {
            "status_code": status_code,
            "target": target,
            "reachable": status_code > 0,
        }


# ---------------------------------------------------------------------------
# Doc parser (reads redirect-map.md style files)
# ---------------------------------------------------------------------------


def parse_redirect_doc(doc_path: Path) -> dict[str, str]:
    """Parse a redirect-map markdown file into ``{source_url: status}``.

    Recognises table rows and list items with redirect annotations.
    """
    if not doc_path.exists():
        return {}

    text = doc_path.read_text(encoding="utf-8")
    entries: dict[str, str] = {}

    # Table rows: | source | target | status |
    table_pattern = re.compile(
        r"^\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|",
        re.MULTILINE,
    )
    for match in table_pattern.finditer(text):
        source = match.group(1).strip()
        if source in ("Source", "源域名", "---", "源"):
            continue
        status = match.group(3).strip().lower()
        if source and not source.startswith("#"):
            entries[source] = status or "active"

    return entries


# ---------------------------------------------------------------------------
# Core audit logic
# ---------------------------------------------------------------------------

# Drift severity mapping
_SEVERITY_MAP: dict[str, str] = {
    "none": "info",
    "ownership-confirmation-pending": "critical",
    "doc-db-inconsistency": "warning",
    "stale-doc-entry": "warning",
    "unexpected-target": "critical",
    "db-missing-but-online": "critical",
    "doc-missing-but-online": "warning",
    "disabled-but-online": "critical",
    "offline-but-active": "critical",
}


def _classify_drift(record: RedirectRecord) -> str:
    """Classify the drift type for a single record."""
    s = record

    # No drift
    if (
        s.db_status in ("active",)
        and s.doc_status in ("active",)
        and s.online_status_code in (301, 302)
        and (
            s.expected_target is None
            or s.online_target is None
            or s.expected_target == s.online_target
        )
    ):
        return "none"

    # Ownership pending
    if "pending" in s.doc_status or "pending" in s.notes.lower():
        return "ownership-confirmation-pending"

    # Doc says removed but DB says active
    if s.db_status == "active" and s.doc_status in ("removed", "missing"):
        return "doc-db-inconsistency"

    # Doc says active but DB says disabled
    if s.db_status == "disabled" and s.doc_status == "active":
        return "stale-doc-entry"

    # DB missing but online responds
    if s.db_status == "missing" and s.online_status_code > 0:
        return "db-missing-but-online"

    # Doc missing but online responds
    if s.doc_status == "missing" and s.online_status_code > 0:
        return "doc-missing-but-online"

    # DB disabled but still online
    if s.db_status == "disabled" and s.online_status_code in (301, 302):
        return "disabled-but-online"

    # Active in DB but offline
    if s.db_status == "active" and s.online_status_code in (0, 404, 502, 503):
        return "offline-but-active"

    # Unexpected redirect target
    if (
        s.expected_target
        and s.online_target
        and s.expected_target != s.online_target
        and s.online_status_code in (301, 302)
    ):
        return "unexpected-target"

    return "none"


def cross_check(record: RedirectRecord) -> DriftFinding | None:
    """Analyse a single record and return a drift finding if drift detected.

    Returns ``None`` when no drift.
    """
    drift_type = _classify_drift(record)
    if drift_type == "none":
        return None

    descriptions: dict[str, str] = {
        "ownership-confirmation-pending": (
            f"Redirect for {record.source_url} has pending ownership confirmation. "
            f"Nginx: {record.nginx_status}, online: {record.online_status_code}"
        ),
        "doc-db-inconsistency": (
            f"{record.source_url}: DB status='{record.db_status}' but "
            f"doc status='{record.doc_status}'"
        ),
        "stale-doc-entry": (
            f"{record.source_url}: disabled in DB but doc still lists as active"
        ),
        "db-missing-but-online": (
            f"{record.source_url}: not in DB but returns HTTP {record.online_status_code} online"
        ),
        "doc-missing-but-online": (
            f"{record.source_url}: not in docs but returns HTTP {record.online_status_code} online"
        ),
        "disabled-but-online": (
            f"{record.source_url}: disabled in DB but still redirecting online "
            f"(HTTP {record.online_status_code})"
        ),
        "offline-but-active": (
            f"{record.source_url}: active in DB but online returns HTTP "
            f"{record.online_status_code}"
        ),
        "unexpected-target": (
            f"{record.source_url}: expected target {record.expected_target} "
            f"but online redirects to {record.online_target}"
        ),
    }

    return DriftFinding(
        source_url=record.source_url,
        drift_type=drift_type,
        severity=_SEVERITY_MAP.get(drift_type, "warning"),
        description=descriptions.get(drift_type, f"Unclassified drift for {record.source_url}"),
        db_status=record.db_status,
        doc_status=record.doc_status,
        nginx_status=record.nginx_status,
        online_status_code=record.online_status_code,
    )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

VALID_AUDIT_SCOPES = frozenset({
    "db-only",
    "nginx-only",
    "online-only",
    "cross-check",
})


class AuditRunner:
    """Orchestrates the redirect audit workflow.

    Read-only. Never modifies any redirect, nginx config, or documentation.
    """

    def __init__(
        self,
        audit_scope: str = "cross-check",
        online_checker: OnlineCheckerProtocol | None = None,
    ) -> None:
        if audit_scope not in VALID_AUDIT_SCOPES:
            msg = f"invalid audit_scope: {audit_scope}"
            raise ValueError(msg)
        self.audit_scope = audit_scope
        self._online_checker = online_checker

    # ------------------------------------------------------------------
    # Single-record checks
    # ------------------------------------------------------------------

    def check_online(self, url: str) -> dict[str, object]:
        """Check a URL's HTTP status. Uses injected checker or curl."""
        if self._online_checker is not None:
            return self._online_checker.check(url)
        return CurlOnlineChecker().check(url)

    def audit_record(self, record: RedirectRecord) -> DriftFinding | None:
        """Audit a single record. Returns finding or None."""
        if self.audit_scope == "db-only" and record.db_status == "missing":
            return DriftFinding(
                source_url=record.source_url,
                drift_type="db-missing",
                severity="warning",
                description=f"{record.source_url}: not found in DB",
                db_status=record.db_status,
                doc_status=record.doc_status,
                nginx_status=record.nginx_status,
                online_status_code=record.online_status_code,
            )
        if self.audit_scope == "nginx-only" and record.nginx_status == "unknown":
            return DriftFinding(
                source_url=record.source_url,
                drift_type="nginx-unknown",
                severity="warning",
                description=f"{record.source_url}: nginx status unknown",
                db_status=record.db_status,
                doc_status=record.doc_status,
                nginx_status=record.nginx_status,
                online_status_code=record.online_status_code,
            )
        if self.audit_scope == "online-only":
            result = self.check_online(record.source_url)
            code = int(result.get("status_code", 0))
            if code != record.online_status_code:
                return DriftFinding(
                    source_url=record.source_url,
                    drift_type="online-mismatch",
                    severity="warning",
                    description=(
                        f"{record.source_url}: expected {record.online_status_code} "
                        f"but got {code}"
                    ),
                    db_status=record.db_status,
                    doc_status=record.doc_status,
                    nginx_status=record.nginx_status,
                    online_status_code=code,
                )
            return None

        # cross-check (default)
        return cross_check(record)

    # ------------------------------------------------------------------
    # Full audit
    # ------------------------------------------------------------------

    def run(
        self,
        records: list[RedirectRecord],
        *,
        check_online: bool = False,
    ) -> AuditReport:
        """Run the full audit across all records.

        Args:
            records: List of redirect records to audit.
            check_online: If True, perform live URL checks for each record.
                If False, use the ``online_status_code`` already on the record.

        Returns:
            AuditReport with all findings.
        """
        findings: list[DriftFinding] = []
        audit_date = time.strftime("%Y-%m-%d")

        for record in records:
            if check_online:
                result = self.check_online(record.source_url)
                record.online_status_code = int(result.get("status_code", 0))
                record.online_target = result.get("target")  # type: ignore[assignment]

            finding = self.audit_record(record)
            if finding is not None:
                findings.append(finding)

        # Build summary
        severity_counts: dict[str, int] = {}
        drift_type_counts: dict[str, int] = {}
        for f in findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
            drift_type_counts[f.drift_type] = drift_type_counts.get(f.drift_type, 0) + 1

        summary: dict[str, int] = {
            "total_records": len(records),
            "total_drifts": len(findings),
            **{f"severity_{k}": v for k, v in severity_counts.items()},
            **{f"type_{k}": v for k, v in drift_type_counts.items()},
        }

        return AuditReport(
            audit_date=audit_date,
            audit_scope=self.audit_scope,
            total_checked=len(records),
            drifts=findings,
            summary=summary,
        )

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    @staticmethod
    def write_report(report: AuditReport, output_path: Path) -> None:
        """Write the drift report to ``output_path`` as JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# CLI entry (synthetic mode only — production uses MCP injection)
# ---------------------------------------------------------------------------


def _cli() -> None:
    """CLI entry point for fixture-based audit runs."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Redirect audit runner (read-only)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Path to a fixture JSON file with redirect records",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/redirect-drift-report.json"),
        help="Output path for the drift report (default: /tmp/redirect-drift-report.json)",
    )
    parser.add_argument(
        "--scope",
        choices=sorted(VALID_AUDIT_SCOPES),
        default="cross-check",
        help="Audit scope (default: cross-check)",
    )
    args = parser.parse_args()

    if not args.fixture:
        parser.error("--fixture is required")

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    raw_redirects = fixture.get("redirects", [])

    records: list[RedirectRecord] = []
    for item in raw_redirects:
        records.append(RedirectRecord(
            source_url=item.get("source_url", ""),
            db_status=item.get("db_status", "missing"),
            doc_status=item.get("doc_status", "missing"),
            nginx_status=item.get("nginx_status", "unknown"),
            online_status_code=int(item.get("online_status_code", 0)),
            notes=item.get("notes", ""),
        ))

    runner = AuditRunner(audit_scope=args.scope)
    report = runner.run(records, check_online=False)
    runner.write_report(report, args.output)

    # Also print summary to stdout
    report_dict = report.to_dict()
    print(f"Audit complete: {report_dict['total_drifts']} drift(s) found")  # noqa: T201
    print(f"Report written to: {args.output}")  # noqa: T201

    if report_dict["total_drifts"] > 0:
        print("\nDrift summary:")  # noqa: T201
        for drift in report_dict["drifts"]:
            print(  # noqa: T201
                f"  [{drift['severity']}] {drift['source_url']}: {drift['drift_type']}"
            )


if __name__ == "__main__":
    _cli()
