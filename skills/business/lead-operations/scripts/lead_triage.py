r"""Production lead-operations triage workflow.

Read-only lead triage: classifies leads, scores them, checks SLA,
and generates auditable triage reports. **Never** performs any write
action (no status changes, no external messages).

Usage (programmatic)::

    runner = LeadTriageRunner(config=config)
    report = runner.run(leads=leads)
    runner.write_report(report, output_path)

Usage (CLI, fixture mode)::

    uv run python -m scripts.lead_triage \\
        --fixture fixtures/synthetic-fixture.json \\
        --output /tmp/lead-ops/triage-report.json

Usage (CLI, live mode — reads from MCP)::

    uv run python -m scripts.lead_triage \\
        --live \\
        --output /tmp/lead-ops/triage-report.json
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass
class LeadRecord:
    """Normalised representation of a single lead from the CRM/MCP."""

    id: int
    name: str = ""
    company: str = ""
    phone: str = ""
    source: str = ""
    message: str = ""
    created_at: str = ""
    status: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> LeadRecord:
        """Build from a raw MCP dict, tolerating missing keys."""
        return cls(
            id=int(raw.get("id", 0)),
            name=str(raw.get("name", "")),
            company=str(raw.get("company", "")),
            phone=str(raw.get("phone", "")),
            source=str(raw.get("source", "")),
            message=str(raw.get("message", "")),
            created_at=str(raw.get("created_at", "")),
            status=str(raw.get("status", "")),
        )

    @property
    def age_hours(self) -> float:
        """Hours since ``created_at`` (0 if unparseable)."""
        if not self.created_at:
            return 0.0
        try:
            dt = datetime.fromisoformat(
                self.created_at.replace("Z", "+00:00"),
            )
            delta = datetime.now(timezone.utc) - dt
            return max(0.0, delta.total_seconds() / 3600)
        except (ValueError, TypeError):
            return 0.0


@dataclass
class TriageEntry:
    """A single lead's triage suggestion."""

    lead_id: int
    category_suggestion: str
    priority: str  # "high" | "medium" | "low"
    score: int
    follow_up_suggestion: str
    risk_flags: list[str] = field(default_factory=list)
    sla_status: str = "within_sla"  # "within_sla" | "approaching" | "breached"
    auto_actions_taken: list[str] = field(default_factory=list)
    human_review_required: bool = True

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict."""
        return {
            "lead_id": self.lead_id,
            "category_suggestion": self.category_suggestion,
            "priority": self.priority,
            "score": self.score,
            "follow_up_suggestion": self.follow_up_suggestion,
            "risk_flags": self.risk_flags,
            "sla_status": self.sla_status,
            "auto_actions_taken": self.auto_actions_taken,
            "human_review_required": self.human_review_required,
        }


@dataclass
class TriageReport:
    """Complete triage result for all leads processed."""

    triage_date: str
    skill_version: str
    mode: str
    total_leads: int = 0
    triage_entries: list[TriageEntry] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    auto_actions_taken: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialise to a plain dict suitable for JSON output."""
        return {
            "skill": "lead-operations",
            "skill_version": self.skill_version,
            "mode": self.mode,
            "triage_date": self.triage_date,
            "total_leads": self.total_leads,
            "triage_entries": [e.to_dict() for e in self.triage_entries],
            "summary": self.summary,
            "auto_actions_taken": self.auto_actions_taken,
            "human_review_required": True,
        }


# ---------------------------------------------------------------------------
# Scoring & Classification Configuration
# ---------------------------------------------------------------------------

# Keyword → score weight mapping. Higher score = higher priority.
KEYWORD_WEIGHTS: dict[str, int] = {
    # AI / tech signals (high intent)
    "ai": 25,
    "人工智能": 25,
    "智能": 20,
    "客服": 15,
    "问数": 20,
    "数字化": 15,
    "转型": 15,
    # Property / real estate
    "商业地产": 20,
    "物业": 15,
    "产业园": 15,
    "写字楼": 10,
    # General business
    "方案": 10,
    "合作": 10,
    "咨询": 5,
    "了解": 5,
    "感兴趣": 10,
}

# Source priority multipliers
SOURCE_MULTIPLIERS: dict[str, float] = {
    "referral": 1.3,
    "website": 1.0,
    "ad": 0.9,
    "cold": 0.7,
}

DEFAULT_SLA_HOURS = 24
SLA_WARNING_HOURS = 18  # 75% of SLA → approaching


# ---------------------------------------------------------------------------
# Lead scoring engine
# ---------------------------------------------------------------------------


class LeadScorer:
    """Score leads based on message content, source, and company signals.

    Score range: 0-100. Higher = more promising.
    """

    def __init__(self, keyword_weights: dict[str, int] | None = None, source_multipliers: dict[str, float] | None = None) -> None:  # noqa: D107
        self._keyword_weights = keyword_weights or dict(KEYWORD_WEIGHTS)
        self._source_multipliers = source_multipliers or dict(SOURCE_MULTIPLIERS)

    def score(self, lead: LeadRecord) -> int:
        """Calculate a 0-100 priority score for a lead.

        Scoring factors:
        - Keyword matches in message (weighted sum, capped at 60)
        - Source multiplier (0.7x–1.3x on keyword score)
        - Company name bonus (+5 if company is non-empty)
        - Message length bonus (+5 if message > 20 chars, indicates detail)
        """
        message = lead.message.lower()
        keyword_score = 0
        for kw, weight in self._keyword_weights.items():
            if kw.lower() in message:
                keyword_score += weight

        # Cap keyword contribution at 60
        keyword_score = min(keyword_score, 60)

        # Apply source multiplier
        multiplier = self._source_multipliers.get(lead.source, 1.0)
        score = int(keyword_score * multiplier)

        # Company bonus
        if lead.company.strip():
            score += 5

        # Message detail bonus
        if len(lead.message.strip()) > 20:
            score += 5

        return min(score, 100)

    def classify(self, lead: LeadRecord) -> str:
        """Generate a category suggestion for a lead.

        Categories:
        - high-priority-ai-solution: AI / smart / intelligent keywords
        - high-priority-commercial-real-estate: Commercial property keywords
        - medium-priority-property-management: Property management keywords
        - medium-priority-referral: Referred leads
        - standard: Default
        """
        message = lead.message.lower()

        if any(kw in message for kw in ("ai", "人工智能", "智能", "问数")):
            return "high-priority-ai-solution"
        if any(kw in message for kw in ("商业地产", "产业园", "写字楼")):
            return "high-priority-commercial-real-estate"
        if "物业" in message:
            return "medium-priority-property-management"
        if lead.source == "referral":
            return "medium-priority-referral"
        return "standard"

    def priority(self, score: int) -> str:
        """Map score to priority label.

        - ≥60: high
        - 30-59: medium
        - <30: low
        """
        if score >= 60:
            return "high"
        if score >= 30:
            return "medium"
        return "low"


# ---------------------------------------------------------------------------
# SLA checker
# ---------------------------------------------------------------------------


class SLAChecker:
    """Check whether a lead is within the response SLA.

    Uses ``created_at`` to compute age. Does NOT access any external
    clock beyond ``datetime.now()``.
    """

    def __init__(self, sla_hours: int = DEFAULT_SLA_HOURS, warning_hours: int = SLA_WARNING_HOURS) -> None:  # noqa: D107
        self._sla_hours = sla_hours
        self._warning_hours = warning_hours

    def check(self, lead: LeadRecord) -> str:
        """Return SLA status: ``within_sla``, ``approaching``, or ``breached``.

        Args:
            lead: Lead record with ``created_at`` timestamp.

        Returns:
            SLA status string.

        """
        age = lead.age_hours

        if age >= self._sla_hours:
            return "breached"
        if age >= self._warning_hours:
            return "approaching"
        return "within_sla"


# ---------------------------------------------------------------------------
# Risk flag detection
# ---------------------------------------------------------------------------

# Patterns that indicate potentially risky / low-quality leads
RISK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"广告|推广|marketing", re.IGNORECASE),
    re.compile(r"测试|test", re.IGNORECASE),
    re.compile(r"^\s*$"),  # empty message
]

# Phone patterns that look invalid
INVALID_PHONE_PATTERN = re.compile(r"^0+$|^[a-zA-Z]+$|^1{11,}$")


def detect_risk_flags(lead: LeadRecord) -> list[str]:
    """Detect risk flags for a lead.

    Checks for:
    - Empty or very short messages
    - Test / spam keywords
    - Invalid phone patterns
    """
    flags: list[str] = []

    # Empty message
    if not lead.message.strip():
        flags.append("empty_message")
    elif len(lead.message.strip()) < 5:
        flags.append("very_short_message")

    # Test / spam keywords
    msg_lower = lead.message.lower()
    for pattern in RISK_PATTERNS:
        if pattern.search(msg_lower):
            flags.append("potential_spam_or_test")
            break

    # Invalid phone
    if lead.phone and INVALID_PHONE_PATTERN.match(lead.phone):
        flags.append("invalid_phone_pattern")

    return flags


# ---------------------------------------------------------------------------
# Triage suggestion generator
# ---------------------------------------------------------------------------


def generate_follow_up_suggestion(
    lead: LeadRecord,
    category: str,
    priority: str,
    sla_status: str,
) -> str:
    """Generate a human-readable follow-up suggestion.

    These are advisory only — the sales owner makes all final decisions.
    """
    base = ""

    if category == "high-priority-ai-solution":
        base = "建议准备 AI 解决方案介绍材料"
    elif category == "high-priority-commercial-real-estate":
        base = "建议准备商业地产案例集"
    elif category == "medium-priority-property-management":
        base = "建议准备物业管理平台介绍"
    elif category == "medium-priority-referral":
        base = "转介绍线索，建议优先建立信任关系"
    else:
        base = "建议了解客户基本需求后跟进"

    # SLA urgency
    if sla_status == "breached":
        urgency = "，SLA 已超时，建议立即联系"
    elif sla_status == "approaching":
        urgency = "，SLA 即将到期，建议尽快联系"
    else:
        urgency = "，建议 24h 内联系"

    # Priority prefix
    if priority == "high":
        prefix = "【高优先级】"
    elif priority == "medium":
        prefix = "【中优先级】"
    else:
        prefix = "【常规】"

    return f"{prefix}{base}{urgency}"


# ---------------------------------------------------------------------------
# MCP reader protocol (for live mode)
# ---------------------------------------------------------------------------


class MCPReaderProtocol(Protocol):
    """Protocol for reading leads from MCP server."""

    def lead_list(self) -> list[dict[str, object]]:
        """List all leads."""
        ...

    def lead_get(self, lead_id: int) -> dict[str, object] | None:
        """Get a single lead by ID."""
        ...


# ---------------------------------------------------------------------------
# Main triage runner
# ---------------------------------------------------------------------------


class LeadTriageRunner:
    """Orchestrates the lead triage workflow.

    Read-only. Never modifies lead status, sends messages, or
    performs any write action.
    """

    SKILL_VERSION = "0.2.0"

    def __init__(  # noqa: D107
        self,
        sla_hours: int = DEFAULT_SLA_HOURS,
        sla_warning_hours: int = SLA_WARNING_HOURS,
        scorer: LeadScorer | None = None,
        sla_checker: SLAChecker | None = None,
    ) -> None:
        self._scorer = scorer or LeadScorer()
        self._sla_checker = sla_checker or SLAChecker(
            sla_hours=sla_hours,
            warning_hours=sla_warning_hours,
        )

    def triage_single(self, lead: LeadRecord) -> TriageEntry:
        """Generate a triage entry for a single lead.

        Args:
            lead: Normalised lead record.

        Returns:
            TriageEntry with suggestions (never actions).

        """
        score = self._scorer.score(lead)
        category = self._scorer.classify(lead)
        priority = self._scorer.priority(score)
        sla_status = self._sla_checker.check(lead)
        risk_flags = detect_risk_flags(lead)
        follow_up = generate_follow_up_suggestion(
            lead, category, priority, sla_status,
        )

        return TriageEntry(
            lead_id=lead.id,
            category_suggestion=category,
            priority=priority,
            score=score,
            follow_up_suggestion=follow_up,
            risk_flags=risk_flags,
            sla_status=sla_status,
            auto_actions_taken=[],
            human_review_required=True,
        )

    def run(
        self,
        leads: list[LeadRecord],
        *,
        mode: str = "synthetic-test",
    ) -> TriageReport:
        """Run triage across multiple leads.

        Args:
            leads: List of normalised lead records.
            mode: Execution mode label for the report.

        Returns:
            TriageReport with entries and summary.

        """
        entries = [self.triage_single(lead) for lead in leads]

        # Build summary
        priority_counts: dict[str, int] = {}
        sla_counts: dict[str, int] = {}
        risk_count = 0
        for e in entries:
            priority_counts[e.priority] = priority_counts.get(e.priority, 0) + 1
            sla_counts[e.sla_status] = sla_counts.get(e.sla_status, 0) + 1
            if e.risk_flags:
                risk_count += 1

        summary = {
            "total_leads": len(entries),
            **{f"priority_{k}": v for k, v in priority_counts.items()},
            **{f"sla_{k}": v for k, v in sla_counts.items()},
            "leads_with_risk_flags": risk_count,
        }

        return TriageReport(
            triage_date=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            skill_version=self.SKILL_VERSION,
            mode=mode,
            total_leads=len(entries),
            triage_entries=entries,
            summary=summary,
            auto_actions_taken=[],
        )

    @staticmethod
    def write_report(report: TriageReport, output_path: Path) -> None:
        """Write the triage report to ``output_path`` as JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _cli() -> None:
    """CLI entry point for lead triage runs."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Lead operations triage runner (read-only)",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        help="Path to a fixture JSON file (synthetic mode)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/lead-ops/triage-report.json"),
        help="Output path for the triage report",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Read from live MCP server at 127.0.0.1:5580 (default: fixture mode)",
    )
    parser.add_argument(
        "--sla-hours",
        type=int,
        default=DEFAULT_SLA_HOURS,
        help=f"SLA threshold in hours (default: {DEFAULT_SLA_HOURS})",
    )
    args = parser.parse_args()

    runner = LeadTriageRunner(sla_hours=args.sla_hours)

    if args.live:
        # Live mode: would connect to MCP server
        print("Live mode requires MCP server connection (not yet implemented).", file=sys.stderr)
        sys.exit(1)
    elif args.fixture:
        # Synthetic mode: use fixture data
        fixture_raw = json.loads(args.fixture.read_text(encoding="utf-8"))
        raw_leads = fixture_raw.get("leads", [])
        if not isinstance(raw_leads, list):
            print("Fixture missing 'leads' list", file=sys.stderr)
            sys.exit(1)
        leads = [LeadRecord.from_dict(r) for r in raw_leads if isinstance(r, dict)]
        report = runner.run(leads, mode="synthetic-test")
    else:
        parser.error("either --fixture or --live is required")

    LeadTriageRunner.write_report(report, args.output)

    # Print summary
    report_dict = report.to_dict()
    print(f"Triage complete: {report_dict['total_leads']} lead(s) processed")
    print(f"Report written to: {args.output}")
    print(f"Summary: {json.dumps(report_dict['summary'], ensure_ascii=False)}")


if __name__ == "__main__":
    _cli()
