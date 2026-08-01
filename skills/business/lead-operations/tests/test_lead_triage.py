"""Comprehensive tests for the lead_triage module.

Covers:
- LeadRecord parsing and age calculation
- LeadScorer: keyword scoring, source multiplier, company bonus, classification
- SLAChecker: within/approaching/breached
- detect_risk_flags: empty/spam/invalid phone
- generate_follow_up_suggestion
- LeadTriageRunner.run with fixture leads
- LeadTriageRunner.write_report
- CLI entry point (fixture mode)
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.lead_triage import (
    DEFAULT_SLA_HOURS,
    KEYWORD_WEIGHTS,
    SLA_WARNING_HOURS,
    LeadRecord,
    LeadScorer,
    LeadTriageRunner,
    SLAChecker,
    TriageEntry,
    TriageReport,
    _cli,
    detect_risk_flags,
    generate_follow_up_suggestion,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


def _load_fixture() -> dict[str, object]:
    with FIXTURE_PATH.open() as f:
        return dict(json.load(f))


def _fixture_leads() -> list[LeadRecord]:
    raw = _load_fixture()
    return [
        LeadRecord.from_dict(r)
        for r in raw.get("leads", [])
        if isinstance(r, dict)
    ]


# =========================================================================
# LeadRecord tests
# =========================================================================


class TestLeadRecord:
    def test_from_dict_complete(self) -> None:
        raw = {
            "id": 3,
            "name": "张三",
            "company": "测试公司",
            "phone": "13800000003",
            "source": "website",
            "message": "咨询 AI 方案",
            "created_at": "2026-07-20T10:00:00Z",
            "status": "new",
        }
        lead = LeadRecord.from_dict(raw)
        assert lead.id == 3
        assert lead.name == "张三"
        assert lead.company == "测试公司"
        assert lead.source == "website"
        assert lead.message == "咨询 AI 方案"
        assert lead.status == "new"

    def test_from_dict_missing_fields(self) -> None:
        lead = LeadRecord.from_dict({"id": 5})
        assert lead.id == 5
        assert lead.name == ""
        assert lead.company == ""
        assert lead.phone == ""

    def test_from_dict_coerces_types(self) -> None:
        lead = LeadRecord.from_dict({"id": "7", "name": 123})
        assert lead.id == 7
        assert lead.name == "123"

    def test_age_hours_recent(self) -> None:
        recent = datetime.now(timezone.utc) - timedelta(hours=2)
        lead = LeadRecord(
            id=10,
            created_at=recent.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        assert 1.9 <= lead.age_hours <= 2.1

    def test_age_hours_empty_created_at(self) -> None:
        lead = LeadRecord(id=10)
        assert lead.age_hours == 0.0

    def test_age_hours_invalid_format(self) -> None:
        lead = LeadRecord(id=10, created_at="invalid-date")
        assert lead.age_hours == 0.0


# =========================================================================
# LeadScorer tests
# =========================================================================


class TestLeadScorer:
    def setup_method(self) -> None:
        self.scorer = LeadScorer()

    def test_ai_keywords_score_high(self) -> None:
        lead = LeadRecord(
            id=3,
            message="希望了解商业地产 AI 客服方案",
            source="website",
            company="某公司",
        )
        score = self.scorer.score(lead)
        assert score >= 60  # AI + 客服 + 商业地产 → high

    def test_no_keywords_low_score(self) -> None:
        lead = LeadRecord(
            id=10,
            message="你好",
            source="website",
            company="某公司",
        )
        score = self.scorer.score(lead)
        assert score < 30  # No keyword matches

    def test_referral_source_multiplier(self) -> None:
        """Referral source should boost score vs website."""
        msg = "咨询 AI 方案"
        website_lead = LeadRecord(id=1, message=msg, source="website", company="c")
        referral_lead = LeadRecord(id=2, message=msg, source="referral", company="c")
        ws = self.scorer.score(website_lead)
        rs = self.scorer.score(referral_lead)
        assert rs > ws  # referral multiplier > website

    def test_company_bonus(self) -> None:
        msg = "咨询 AI 方案"
        with_co = LeadRecord(id=1, message=msg, source="website", company="某公司")
        no_co = LeadRecord(id=2, message=msg, source="website", company="")
        assert self.scorer.score(with_co) > self.scorer.score(no_co)

    def test_message_length_bonus(self) -> None:
        short_msg = LeadRecord(id=1, message="AI", source="website", company="c")
        long_msg = LeadRecord(
            id=2,
            message="我们希望了解 AI 智能客服的整体方案和报价",
            source="website",
            company="c",
        )
        assert self.scorer.score(long_msg) > self.scorer.score(short_msg)

    def test_score_capped_at_100(self) -> None:
        lead = LeadRecord(
            id=1,
            message="AI 人工智能 智能客服 问数 数字化转型 商业地产 产业园 物业 方案 合作",
            source="referral",
            company="某大型集团",
        )
        score = self.scorer.score(lead)
        assert score <= 100

    def test_classify_ai_solution(self) -> None:
        lead = LeadRecord(id=1, message="咨询 AI 智能客服", source="website")
        assert self.scorer.classify(lead) == "high-priority-ai-solution"

    def test_classify_commercial_real_estate(self) -> None:
        lead = LeadRecord(id=1, message="商业地产产业园合作", source="website")
        assert self.scorer.classify(lead) == "high-priority-commercial-real-estate"

    def test_classify_property_management(self) -> None:
        lead = LeadRecord(id=1, message="物业管理系统", source="website")
        assert self.scorer.classify(lead) == "medium-priority-property-management"

    def test_classify_referral(self) -> None:
        lead = LeadRecord(id=1, message="了解一下", source="referral")
        assert self.scorer.classify(lead) == "medium-priority-referral"

    def test_classify_standard(self) -> None:
        lead = LeadRecord(id=1, message="你好", source="website")
        assert self.scorer.classify(lead) == "standard"

    def test_priority_high(self) -> None:
        assert self.scorer.priority(75) == "high"

    def test_priority_medium(self) -> None:
        assert self.scorer.priority(45) == "medium"

    def test_priority_low(self) -> None:
        assert self.scorer.priority(15) == "low"

    def test_priority_boundary_60(self) -> None:
        assert self.scorer.priority(60) == "high"

    def test_priority_boundary_30(self) -> None:
        assert self.scorer.priority(30) == "medium"

    def test_custom_keyword_weights(self) -> None:
        scorer = LeadScorer(keyword_weights={"定制关键词": 50})
        lead = LeadRecord(id=1, message="定制关键词", source="website", company="c")
        assert scorer.score(lead) >= 50

    def test_custom_source_multipliers(self) -> None:
        scorer = LeadScorer(source_multipliers={"custom_source": 2.0})
        lead = LeadRecord(id=1, message="AI 方案", source="custom_source", company="c")
        default = LeadScorer()
        default_lead = LeadRecord(id=2, message="AI 方案", source="website", company="c")
        assert scorer.score(lead) > default.score(default_lead)


# =========================================================================
# SLAChecker tests
# =========================================================================


class TestSLAChecker:
    def test_within_sla(self) -> None:
        recent = datetime.now(timezone.utc) - timedelta(hours=2)
        lead = LeadRecord(
            id=1,
            created_at=recent.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        checker = SLAChecker(sla_hours=24, warning_hours=18)
        assert checker.check(lead) == "within_sla"

    def test_approaching_sla(self) -> None:
        approaching = datetime.now(timezone.utc) - timedelta(hours=20)
        lead = LeadRecord(
            id=1,
            created_at=approaching.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        checker = SLAChecker(sla_hours=24, warning_hours=18)
        assert checker.check(lead) == "approaching"

    def test_breached_sla(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(hours=30)
        lead = LeadRecord(
            id=1,
            created_at=old.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        checker = SLAChecker(sla_hours=24, warning_hours=18)
        assert checker.check(lead) == "breached"

    def test_no_created_at(self) -> None:
        """Lead without created_at → age 0 → within_sla."""
        lead = LeadRecord(id=1)
        checker = SLAChecker(sla_hours=24, warning_hours=18)
        assert checker.check(lead) == "within_sla"

    def test_boundary_exactly_sla(self) -> None:
        exactly = datetime.now(timezone.utc) - timedelta(hours=24)
        lead = LeadRecord(
            id=1,
            created_at=exactly.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        checker = SLAChecker(sla_hours=24, warning_hours=18)
        assert checker.check(lead) == "breached"

    def test_boundary_exactly_warning(self) -> None:
        exactly = datetime.now(timezone.utc) - timedelta(hours=18)
        lead = LeadRecord(
            id=1,
            created_at=exactly.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        checker = SLAChecker(sla_hours=24, warning_hours=18)
        assert checker.check(lead) == "approaching"


# =========================================================================
# Risk flag detection tests
# =========================================================================


class TestDetectRiskFlags:
    def test_clean_lead_no_flags(self) -> None:
        lead = LeadRecord(
            id=3,
            name="张三",
            message="咨询 AI 方案",
            phone="13800001234",
        )
        assert detect_risk_flags(lead) == []

    def test_empty_message_flag(self) -> None:
        lead = LeadRecord(id=1, message="")
        flags = detect_risk_flags(lead)
        assert "empty_message" in flags

    def test_whitespace_message_flag(self) -> None:
        lead = LeadRecord(id=1, message="   ")
        flags = detect_risk_flags(lead)
        assert "empty_message" in flags

    def test_very_short_message_flag(self) -> None:
        lead = LeadRecord(id=1, message="hi")
        flags = detect_risk_flags(lead)
        assert "very_short_message" in flags

    def test_test_keyword_flag(self) -> None:
        lead = LeadRecord(id=1, message="这是一个测试消息")
        flags = detect_risk_flags(lead)
        assert "potential_spam_or_test" in flags

    def test_ad_keyword_flag(self) -> None:
        lead = LeadRecord(id=1, message="广告推广服务")
        flags = detect_risk_flags(lead)
        assert "potential_spam_or_test" in flags

    def test_invalid_phone_all_zeros(self) -> None:
        lead = LeadRecord(id=1, message="正常消息内容", phone="00000000000")
        flags = detect_risk_flags(lead)
        assert "invalid_phone_pattern" in flags

    def test_invalid_phone_all_ones(self) -> None:
        lead = LeadRecord(id=1, message="正常消息内容", phone="11111111111")
        flags = detect_risk_flags(lead)
        assert "invalid_phone_pattern" in flags

    def test_invalid_phone_alpha(self) -> None:
        lead = LeadRecord(id=1, message="正常消息内容", phone="abcdefghijk")
        flags = detect_risk_flags(lead)
        assert "invalid_phone_pattern" in flags

    def test_valid_phone_no_flag(self) -> None:
        lead = LeadRecord(id=1, message="正常消息内容", phone="13812345678")
        flags = detect_risk_flags(lead)
        assert "invalid_phone_pattern" not in flags

    def test_multiple_flags(self) -> None:
        lead = LeadRecord(id=1, message="test", phone="00000000000")
        flags = detect_risk_flags(lead)
        assert len(flags) >= 2  # short message + invalid phone + test keyword


# =========================================================================
# Follow-up suggestion tests
# =========================================================================


class TestGenerateFollowUpSuggestion:
    def test_high_priority_ai(self) -> None:
        lead = LeadRecord(id=1, message="AI 方案")
        suggestion = generate_follow_up_suggestion(
            lead, "high-priority-ai-solution", "high", "within_sla",
        )
        assert "【高优先级】" in suggestion
        assert "AI" in suggestion

    def test_breached_sla(self) -> None:
        lead = LeadRecord(id=1, message="咨询")
        suggestion = generate_follow_up_suggestion(
            lead, "standard", "low", "breached",
        )
        assert "SLA 已超时" in suggestion

    def test_approaching_sla(self) -> None:
        lead = LeadRecord(id=1, message="咨询")
        suggestion = generate_follow_up_suggestion(
            lead, "standard", "medium", "approaching",
        )
        assert "SLA 即将到期" in suggestion

    def test_referral_category(self) -> None:
        lead = LeadRecord(id=1, message="了解", source="referral")
        suggestion = generate_follow_up_suggestion(
            lead, "medium-priority-referral", "medium", "within_sla",
        )
        assert "转介绍" in suggestion

    def test_standard_category(self) -> None:
        lead = LeadRecord(id=1, message="你好")
        suggestion = generate_follow_up_suggestion(
            lead, "standard", "low", "within_sla",
        )
        assert "【常规】" in suggestion


# =========================================================================
# TriageEntry / TriageReport serialisation
# =========================================================================


class TestTriageEntrySerialise:
    def test_to_dict(self) -> None:
        entry = TriageEntry(
            lead_id=3,
            category_suggestion="high-priority-ai-solution",
            priority="high",
            score=75,
            follow_up_suggestion="建议联系",
            risk_flags=[],
            sla_status="within_sla",
        )
        d = entry.to_dict()
        assert d["lead_id"] == 3
        assert d["priority"] == "high"
        assert d["score"] == 75
        assert d["human_review_required"] is True
        assert d["auto_actions_taken"] == []


class TestTriageReportSerialise:
    def test_to_dict(self) -> None:
        report = TriageReport(
            triage_date="2026-08-01T00:00:00Z",
            skill_version="0.2.0",
            mode="synthetic-test",
            total_leads=1,
            triage_entries=[
                TriageEntry(
                    lead_id=3,
                    category_suggestion="standard",
                    priority="low",
                    score=10,
                    follow_up_suggestion="建议联系",
                ),
            ],
            summary={"total_leads": 1, "priority_low": 1},
        )
        d = report.to_dict()
        assert d["skill"] == "lead-operations"
        assert d["total_leads"] == 1
        assert len(d["triage_entries"]) == 1
        assert d["human_review_required"] is True
        assert d["auto_actions_taken"] == []


# =========================================================================
# LeadTriageRunner tests
# =========================================================================


class TestLeadTriageRunnerSingle:
    def test_triage_single_returns_entry(self) -> None:
        lead = LeadRecord(
            id=3,
            name="测试",
            message="咨询 AI 方案",
            source="website",
            company="某公司",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        runner = LeadTriageRunner()
        entry = runner.triage_single(lead)
        assert isinstance(entry, TriageEntry)
        assert entry.lead_id == 3
        assert entry.category_suggestion == "high-priority-ai-solution"
        assert entry.priority in ("high", "medium", "low")
        assert entry.auto_actions_taken == []
        assert entry.human_review_required is True

    def test_triage_single_no_auto_actions(self) -> None:
        lead = LeadRecord(id=3, message="测试", source="website")
        runner = LeadTriageRunner()
        entry = runner.triage_single(lead)
        assert entry.auto_actions_taken == []


class TestLeadTriageRunnerRun:
    def test_run_with_fixture_leads(self) -> None:
        leads = _fixture_leads()
        runner = LeadTriageRunner()
        report = runner.run(leads, mode="synthetic-test")
        assert report.total_leads == len(leads)
        assert len(report.triage_entries) == len(leads)
        assert report.mode == "synthetic-test"
        assert report.auto_actions_taken == []

    def test_run_summary_has_priority_counts(self) -> None:
        leads = _fixture_leads()
        runner = LeadTriageRunner()
        report = runner.run(leads)
        priority_keys = [k for k in report.summary if k.startswith("priority_")]
        assert len(priority_keys) > 0
        total_priority = sum(
            v for k, v in report.summary.items() if k.startswith("priority_")
        )
        assert total_priority == len(leads)

    def test_run_summary_has_sla_counts(self) -> None:
        leads = _fixture_leads()
        runner = LeadTriageRunner()
        report = runner.run(leads)
        sla_keys = [k for k in report.summary if k.startswith("sla_")]
        assert len(sla_keys) > 0

    def test_run_summary_total_leads(self) -> None:
        leads = _fixture_leads()
        runner = LeadTriageRunner()
        report = runner.run(leads)
        assert report.summary["total_leads"] == len(leads)

    def test_run_empty_leads(self) -> None:
        runner = LeadTriageRunner()
        report = runner.run([], mode="synthetic-test")
        assert report.total_leads == 0
        assert report.triage_entries == []

    def test_run_no_write_actions(self) -> None:
        """Ensure the runner never takes auto actions."""
        leads = _fixture_leads()
        runner = LeadTriageRunner()
        report = runner.run(leads)
        assert report.auto_actions_taken == []
        for entry in report.triage_entries:
            assert entry.auto_actions_taken == []

    def test_run_custom_sla(self) -> None:
        """Runner with very short SLA → all old fixture leads breached."""
        leads = _fixture_leads()
        runner = LeadTriageRunner(sla_hours=1)
        report = runner.run(leads)
        breached = report.summary.get("sla_breached", 0)
        # Fixture leads are from July 2026, so all should be breached with 1h SLA
        assert breached > 0

    def test_run_all_entries_have_required_fields(self) -> None:
        leads = _fixture_leads()
        runner = LeadTriageRunner()
        report = runner.run(leads)
        for entry in report.triage_entries:
            assert entry.lead_id > 0
            assert entry.category_suggestion
            assert entry.priority in ("high", "medium", "low")
            assert isinstance(entry.score, int)
            assert 0 <= entry.score <= 100
            assert entry.follow_up_suggestion
            assert entry.sla_status in ("within_sla", "approaching", "breached")
            assert entry.human_review_required is True


# =========================================================================
# Write report tests
# =========================================================================


class TestWriteReport:
    def test_writes_valid_json(self) -> None:
        report = TriageReport(
            triage_date="2026-08-01T00:00:00Z",
            skill_version="0.2.0",
            mode="synthetic-test",
            total_leads=1,
        )
        with tempfile.TemporaryDirectory(prefix="lead-ops-") as tmp:
            out = Path(tmp) / "report.json"
            LeadTriageRunner.write_report(report, out)
            assert out.exists()
            data = json.loads(out.read_text())
            assert data["skill"] == "lead-operations"
            assert data["total_leads"] == 1

    def test_creates_parent_dirs(self) -> None:
        report = TriageReport(
            triage_date="2026-08-01",
            skill_version="0.2.0",
            mode="synthetic-test",
        )
        with tempfile.TemporaryDirectory(prefix="lead-ops-") as tmp:
            out = Path(tmp) / "deeply" / "nested" / "report.json"
            LeadTriageRunner.write_report(report, out)
            assert out.exists()

    def test_writes_fixture_mode_artifact(self) -> None:
        leads = _fixture_leads()
        runner = LeadTriageRunner()
        report = runner.run(leads, mode="synthetic-test")
        with tempfile.TemporaryDirectory(prefix="lead-ops-") as tmp:
            out = Path(tmp) / "triage-report.json"
            LeadTriageRunner.write_report(report, out)
            data = json.loads(out.read_text())
            assert data["mode"] == "synthetic-test"
            assert data["human_review_required"] is True
            assert len(data["triage_entries"]) == len(leads)


# =========================================================================
# CLI tests
# =========================================================================


class TestCLI:
    def test_fixture_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lead-ops-") as tmp:
            output = Path(tmp) / "triage.json"
            with patch("sys.argv", [
                "lead_triage",
                "--fixture", str(FIXTURE_PATH),
                "--output", str(output),
            ]):
                _cli()
            assert output.exists()
            data = json.loads(output.read_text())
            assert data["skill"] == "lead-operations"
            assert data["total_leads"] > 0

    def test_no_args_errors(self) -> None:
        with patch("sys.argv", ["lead_triage"]), pytest.raises(SystemExit):
            _cli()

    def test_custom_sla_hours(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lead-ops-") as tmp:
            output = Path(tmp) / "triage.json"
            with patch("sys.argv", [
                "lead_triage",
                "--fixture", str(FIXTURE_PATH),
                "--output", str(output),
                "--sla-hours", "1",
            ]):
                _cli()
            data = json.loads(output.read_text())
            # With 1h SLA, old fixture leads should be breached
            breached_entries = [
                e for e in data["triage_entries"]
                if e["sla_status"] == "breached"
            ]
            assert len(breached_entries) > 0


# =========================================================================
# Constants tests
# =========================================================================


class TestConstants:
    def test_keyword_weights_populated(self) -> None:
        assert len(KEYWORD_WEIGHTS) > 5
        assert "ai" in KEYWORD_WEIGHTS
        assert "物业" in KEYWORD_WEIGHTS

    def test_default_sla_hours(self) -> None:
        assert DEFAULT_SLA_HOURS == 24

    def test_sla_warning_hours(self) -> None:
        assert SLA_WARNING_HOURS == 18

    def test_fixture_has_5_leads(self) -> None:
        """Promotion Rule requires at least 5 leads."""
        fixture = _load_fixture()
        leads = fixture.get("leads", [])
        assert isinstance(leads, list)
        assert len(leads) >= 5

    def test_fixture_lead_ids_skip_forbidden(self) -> None:
        """Fixture must not include forbidden lead IDs 1 or 2."""
        fixture = _load_fixture()
        leads = fixture.get("leads", [])
        for lead in leads:
            if isinstance(lead, dict):
                assert lead.get("id") not in (1, 2)
