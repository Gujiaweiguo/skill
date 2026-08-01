"""Tests for case_workflow CLI module.

Covers: validate, generate, import (mock), and screen subcommands.
Uses subprocess-free in-process testing via ``main()``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from scripts.case_workflow import main as workflow_main

if TYPE_CHECKING:
    import pytest

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "fixtures" / "synthetic-fixture.json"
)


class TestValidateCommand:
    def test_valid_fixture(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = workflow_main(["validate", str(FIXTURE_PATH)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "VALID" in captured.out

    def test_writes_report(self, tmp_path: Path) -> None:
        report_path = tmp_path / "report.json"
        rc = workflow_main([
            "validate", str(FIXTURE_PATH), "--report", str(report_path),
        ])
        assert rc == 0
        assert report_path.exists()
        data = json.loads(report_path.read_text())
        assert data["valid"] is True
        assert data["skill"] == "case-operations"

    def test_invalid_payload(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        bad_payload = tmp_path / "bad.json"
        bad_payload.write_text(json.dumps({
            "slug": "test",
            "client_name": "test",
            "industry": "office",
            "problem": "p",
            "solution": "s",
            "outcome": "o",
            "client_authorized": False,
            "fixture": True,
        }))
        rc = workflow_main(["validate", str(bad_payload)])
        assert rc == 1
        captured = capsys.readouterr()
        assert "INVALID" in captured.err


class TestGenerateCommand:
    def test_generates_artifacts(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        output_dir = tmp_path / "run"
        rc = workflow_main([
            "generate", str(FIXTURE_PATH), "--output-dir", str(output_dir),
        ])
        assert rc == 0
        assert (output_dir / "case-research-pack.md").exists()
        assert (output_dir / "case-payload.json").exists()
        assert (output_dir / "validation-report.json").exists()
        assert (output_dir / "import-receipt.json").exists()
        captured = capsys.readouterr()
        assert "Generated 4 artifacts" in captured.out

    def test_rejects_non_fixture(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        payload = tmp_path / "case.json"
        payload.write_text(json.dumps({
            "slug": "test",
            "client_name": "test",
            "industry": "office",
            "problem": "p",
            "solution": "s",
            "outcome": "o",
            "client_authorized": True,
        }))
        rc = workflow_main(["generate", str(payload)])
        assert rc == 1
        captured = capsys.readouterr()
        assert "fixture=true" in captured.err


class TestImportCommand:
    def test_mock_import(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        receipt_path = tmp_path / "receipt.json"
        rc = workflow_main([
            "import", str(FIXTURE_PATH),
            "--mock",
            "--receipt", str(receipt_path),
        ])
        assert rc == 0
        assert receipt_path.exists()
        receipt = json.loads(receipt_path.read_text())
        assert receipt["draft_status"] == "draft"
        assert receipt["mcp_tool"] == "case_create"
        captured = capsys.readouterr()
        assert "[MOCK]" in captured.out

    def test_production_import_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = workflow_main(["import", str(FIXTURE_PATH)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "MCP case_create" in captured.out

    def test_rejects_invalid_payload(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        bad_payload = tmp_path / "bad.json"
        bad_payload.write_text(json.dumps({
            "slug": "test",
            "client_name": "test",
            "industry": "office",
            "problem": "p",
            "solution": "s",
            "outcome": "o",
            "client_authorized": False,
            "fixture": True,
        }))
        rc = workflow_main(["import", str(bad_payload), "--mock"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "validation failed" in captured.err


class TestScreenCommand:
    def test_screen_with_stub(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Screen command should work when the API is reachable."""
        from scripts.case_screening import CaseScreener as RealCaseScreener  # noqa: PLC0415
        from scripts.case_screening import ScreeningReport  # noqa: PLC0415

        fake_report = ScreeningReport(
            api_url="https://lanlnk.cn/api/cases",
            fetched_at="2026-08-01T18:00:00",
            total_cases=3,
            published_cases=3,
            top_candidates=[
                {"slug": "yuehai-tianhe-cheng", "client_name": "粤海天河城", "combined_score": 1.0},
            ],
            all_scores=[
                {"slug": "yuehai-tianhe-cheng", "client_name": "粤海天河城", "combined_score": 1.0},
            ],
            summary={"published_count": 3},
        )

        with patch("scripts.case_workflow.CaseScreener") as mock_cls:
            instance = mock_cls.return_value
            instance.screen.return_value = fake_report
            # write_report needs to actually write — delegate to real impl
            instance.write_report.side_effect = RealCaseScreener.write_report
            rc = workflow_main([
                "screen", "--output", str(tmp_path / "report.json"),
            ])
        assert rc == 0
        assert (tmp_path / "report.json").exists()
        captured = capsys.readouterr()
        assert "Screening complete" in captured.out
