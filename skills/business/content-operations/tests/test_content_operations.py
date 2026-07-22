from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

SKILL_ROOT: Final = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))
JsonScalar = str | bool

from scripts.contracts import (  # noqa: E402
    CONTRACT_VERSION,
    PayloadValidationError,
    payload_sha256,
    validate_payload_file,
)
from scripts.import_artifacts import ImportPaths  # noqa: E402
from scripts.write_receipt import main as write_receipt_main  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Mapping


def valid_payload() -> dict[str, JsonScalar]:
    return {
        "title": "什么是 AI Agent",
        "body": "<p>AI Agent 是可执行任务的企业 AI 应用。</p>",
        "slug": "what-is-ai-agent",
        "category": "ai-trends",
        "summary": "企业 AI Agent 入门",
        "source_name": "蓝联创新",
        "commentary": "T-01 pilot",
        "status": "draft",
    }


def write_json(path: Path, value: Mapping[str, JsonScalar]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def prepare_import(tmp_path: Path) -> tuple[ImportPaths, Path]:
    base = tmp_path / "content"
    source_draft = base / "drafts" / "T-01.md"
    source_draft.parent.mkdir(parents=True)
    source_draft.write_text("# 什么是 AI Agent\n", encoding="utf-8")

    job_dir = base / "publish-jobs" / "what-is-ai-agent"
    payload_path = job_dir / "article.json"
    write_json(payload_path, valid_payload())
    validation_report = job_dir / "validation-report.json"
    validate_payload_file(payload_path, validation_report)

    review_record = base / "review" / "T-01.json"
    write_json(
        review_record,
        {
            "contract_version": CONTRACT_VERSION,
            "source_draft": str(source_draft.resolve()),
            "payload_sha256": payload_sha256(payload_path),
            "decision": "approved",
            "slug_available": True,
        },
    )
    return (
        ImportPaths(
            content_output_base=base,
            payload=payload_path,
            validation_report=validation_report,
            source_draft=source_draft,
            review_record=review_record,
            receipt=job_dir / "import-receipt.json",
        ),
        payload_path,
    )


def run_write_receipt(
    paths: ImportPaths,
    cms_status: str,
    monkeypatch: pytest.MonkeyPatch,
) -> int:
    monkeypatch.setenv("CONTENT_OUTPUT_BASE", str(paths.content_output_base))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "write_receipt.py",
            str(paths.payload),
            "--cms-article-id",
            "10",
            "--cms-status",
            cms_status,
            "--source-draft",
            str(paths.source_draft),
            "--review-record",
            str(paths.review_record),
            "--validation-report",
            str(paths.validation_report),
            "--receipt",
            str(paths.receipt),
        ],
    )
    return write_receipt_main()


@pytest.mark.parametrize(
    "category",
    ["ai-trends", "industry-insights", "case-studies", "community"],
)
def test_validator_accepts_supported_draft_categories(
    tmp_path: Path,
    category: str,
) -> None:
    payload_path = tmp_path / "article.json"
    data = valid_payload()
    data["category"] = category
    write_json(payload_path, data)

    payload = validate_payload_file(payload_path, tmp_path / "report.json")

    assert payload.status == "draft"
    assert payload.category == category


@pytest.mark.parametrize(
    ("change", "expected_code"),
    [
        ({"title": ""}, "string_too_short"),
        ({"body": "Markdown only"}, "html_body_required"),
        ({"slug": "Bad Slug"}, "string_pattern_mismatch"),
        ({"category": "unknown"}, "enum"),
        ({"status": "published"}, "literal_error"),
        ({"publish": True}, "publication_intent"),
    ],
)
def test_validator_rejects_unsupported_or_publication_payloads(
    tmp_path: Path,
    change: dict[str, JsonScalar],
    expected_code: str,
) -> None:
    data = valid_payload()
    data.update(change)
    payload_path = tmp_path / "article.json"
    write_json(payload_path, data)

    with pytest.raises(PayloadValidationError) as caught:
        validate_payload_file(payload_path, tmp_path / "report.json")

    assert expected_code in {issue.code for issue in caught.value.issues}


def test_validator_report_is_byte_deterministic(tmp_path: Path) -> None:
    payload_path = tmp_path / "article.json"
    write_json(payload_path, valid_payload())
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    validate_payload_file(payload_path, first)
    validate_payload_file(payload_path, second)

    assert first.read_bytes() == second.read_bytes()


def test_write_receipt_records_valid_mcp_draft_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths, _payload_path = prepare_import(tmp_path)

    exit_code = run_write_receipt(paths, "draft", monkeypatch)

    receipt = json.loads(paths.receipt.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert receipt == {
        "category": "ai-trends",
        "cms_article_id": "10",
        "contract_version": CONTRACT_VERSION,
        "payload_sha256": payload_sha256(paths.payload),
        "slug": "what-is-ai-agent",
        "source_draft": str(paths.source_draft.resolve()),
        "status": "draft",
    }


def test_write_receipt_rejects_non_draft_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths, _payload_path = prepare_import(tmp_path)

    exit_code = run_write_receipt(paths, "published", monkeypatch)

    assert exit_code == 1
    assert not paths.receipt.exists()


def test_write_receipt_rejects_missing_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths, _payload_path = prepare_import(tmp_path)
    paths.review_record.unlink()

    exit_code = run_write_receipt(paths, "draft", monkeypatch)

    assert exit_code == 1
    assert not paths.receipt.exists()


def test_write_receipt_rejects_invalid_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths, _payload_path = prepare_import(tmp_path)
    paths.review_record.write_text("{}", encoding="utf-8")

    exit_code = run_write_receipt(paths, "draft", monkeypatch)

    assert exit_code == 1
    assert not paths.receipt.exists()
