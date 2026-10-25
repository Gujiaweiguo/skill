"""Maintenance handler tests (R-CMS-03): red-first, mock MCP injected."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

SKILL_ROOT: Final = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))

from scripts.contracts import (  # noqa: E402
    CONTRACT_VERSION,
    PayloadValidationError,
    payload_sha256,
    validate_payload_file,
)
from scripts.maintenance_payload import (  # noqa: E402
    SERVER_CONTROLLED_FIELDS,
    build_proposed_fields,
    parse_maintenance_payload,
    render_diff_document,
)
from scripts.maintenance_payload import main as build_main  # noqa: E402
from scripts.maintenance_post_apply import main as post_apply_main  # noqa: E402
from scripts.maintenance_receipt import main as receipt_main  # noqa: E402
from scripts.validate_maintenance import main as validate_main  # noqa: E402
from tests.mock_mcp_maintenance import MockMCPError, MockMCPServer  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Mapping

MaintenanceJson = dict[str, object]


def _current_snapshot() -> dict[str, object]:
    return {
        "id": 24,
        "status": "published",
        "title": "什么是 AI Agent",
        "summary": "企业 AI Agent 入门",
        "published_at": "2026-08-01T00:00:00Z",
        "created_at": "2026-07-31T00:00:00Z",
        "updated_at": "2026-08-01T00:00:00Z",
    }


def _desired_snapshot() -> dict[str, object]:
    return {
        "id": 24,
        "status": "published",
        "title": "什么是 AI Agent（2026 修订）",
        "summary": "企业 AI Agent 入门",
        "published_at": "2026-08-01T00:00:00Z",
        "created_at": "2026-07-31T00:00:00Z",
        "updated_at": "2026-08-01T00:00:00Z",
    }


def write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


# ── build proposed_fields ─────────────────────────────


def test_build_proposed_fields_only_includes_changed_fields() -> None:
    proposed, filtered = build_proposed_fields(
        _current_snapshot(), _desired_snapshot(),
    )
    assert proposed == {"title": "什么是 AI Agent（2026 修订）"}
    assert filtered == []


def test_build_proposed_fields_adds_new_field() -> None:
    desired = _desired_snapshot() | {"commentary": "修订说明"}
    proposed, _filtered = build_proposed_fields(_current_snapshot(), desired)
    assert proposed == {
        "title": "什么是 AI Agent（2026 修订）",
        "commentary": "修订说明",
    }


def test_build_proposed_fields_filters_server_controlled() -> None:
    desired = _desired_snapshot() | {"status": "draft", "published_at": "2099-01-01"}
    proposed, filtered = build_proposed_fields(_current_snapshot(), desired)
    assert "status" not in proposed
    assert "published_at" not in proposed
    assert filtered == ["published_at", "status"]


def test_server_controlled_fields_contract() -> None:
    assert frozenset(
        {"id", "status", "published_at", "created_at", "updated_at"},
    ) == SERVER_CONTROLLED_FIELDS


# ── parse & validate ──────────────────────────────────


def _valid_maintenance_payload() -> MaintenanceJson:
    return {
        "entity_type": "article",
        "entity_id": "24",
        "rationale": "修正过时表述，与 2026-10 官方口径对齐",
        "base_digest": "a" * 64,
        "proposed_fields": {"title": "什么是 AI Agent（2026 修订）"},
        "status": "pending-review",
    }


def test_parse_valid_maintenance_payload() -> None:
    payload = parse_maintenance_payload(
        json.dumps(_valid_maintenance_payload()).encode(),
    )
    assert payload.entity_type.value == "article"
    assert payload.entity_id == "24"
    assert payload.status == "pending-review"


@pytest.mark.parametrize(
    ("change", "expected_code"),
    [
        ({"entity_type": "bogus"}, "enum"),
        ({"entity_id": ""}, "string_too_short"),
        ({"rationale": " "}, "string_too_short"),
        ({"base_digest": "not-a-digest"}, "string_pattern_mismatch"),
        ({"proposed_fields": {}}, "dict_min_length"),
        (
            {"proposed_fields": {"status": "draft"}},
            "server_controlled_field",
        ),
        (
            {"proposed_fields": {"published_at": "2099-01-01"}},
            "server_controlled_field",
        ),
        ({"status": "applied"}, "literal_error"),
        ({"extra_field": True}, "extra_forbidden"),
    ],
)
def test_parse_rejects_invalid_maintenance_payloads(
    change: dict[str, object],
    expected_code: str,
) -> None:
    data = _valid_maintenance_payload() | change
    with pytest.raises(PayloadValidationError) as exc_info:
        parse_maintenance_payload(json.dumps(data).encode())
    assert expected_code in {issue.code for issue in exc_info.value.issues}


def test_parse_rejects_missing_required_field() -> None:
    data = _valid_maintenance_payload()
    del data["rationale"]
    with pytest.raises(PayloadValidationError) as exc_info:
        parse_maintenance_payload(json.dumps(data).encode())
    assert any(i.code == "missing" for i in exc_info.value.issues)


def test_validator_report_via_contracts(tmp_path: Path) -> None:
    payload_path = tmp_path / "proposed.json"
    write_json(payload_path, _valid_maintenance_payload())

    payload = validate_payload_file(
        payload_path,
        tmp_path / "validation-report.json",
        parse_fn=parse_maintenance_payload,
    )

    assert payload.entity_id == "24"
    report = json.loads(
        (tmp_path / "validation-report.json").read_text(encoding="utf-8"),
    )
    assert report["valid"] is True
    assert report["payload_sha256"] == payload_sha256(payload_path)
    assert report["contract_version"] == CONTRACT_VERSION


# ── diff review document ──────────────────────────────


def test_render_diff_document_lists_changes() -> None:
    document = render_diff_document(
        entity_type="article",
        entity_id="24",
        current=_current_snapshot(),
        proposed={"title": "什么是 AI Agent（2026 修订）"},
        rationale="修正过时表述",
    )
    assert "article" in document
    assert "24" in document
    assert "title" in document
    assert "什么是 AI Agent（2026 修订）" in document
    assert "修正过时表述" in document
    assert '-"什么是 AI Agent"' in document
    assert '+"什么是 AI Agent（2026 修订）"' in document


# ── CLI: validate_maintenance ─────────────────────────


def _run_cli(
    main,  # noqa: ANN001
    argv: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> int:
    monkeypatch.setattr(sys, "argv", argv)
    return main()


def test_cli_validate_accepts_valid_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path = tmp_path / "proposed.json"
    write_json(payload_path, _valid_maintenance_payload())

    exit_code = _run_cli(
        validate_main,
        [
            "validate_maintenance.py",
            str(payload_path),
            "--report",
            str(tmp_path / "validation-report.json"),
        ],
        monkeypatch,
    )

    report = json.loads(
        (tmp_path / "validation-report.json").read_text(encoding="utf-8"),
    )
    assert exit_code == 0
    assert report["valid"] is True


def test_cli_validate_rejects_forbidden_field(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = _valid_maintenance_payload() | {
        "proposed_fields": {"status": "draft"},
    }
    payload_path = tmp_path / "proposed.json"
    write_json(payload_path, data)

    exit_code = _run_cli(
        validate_main,
        [
            "validate_maintenance.py",
            str(payload_path),
            "--report",
            str(tmp_path / "validation-report.json"),
        ],
        monkeypatch,
    )

    report = json.loads(
        (tmp_path / "validation-report.json").read_text(encoding="utf-8"),
    )
    assert exit_code == 1
    assert report["valid"] is False
    assert any(
        i["code"] == "server_controlled_field" for i in report["issues"]
    )


# ── CLI: maintenance_receipt ──────────────────────────


def _run_receipt_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cms_status: str,
    base_digest: str,
) -> tuple[int, Path]:
    payload_path = tmp_path / "proposed.json"
    data = _valid_maintenance_payload() | {"base_digest": base_digest}
    write_json(payload_path, data)
    receipt_path = tmp_path / "create-receipt.json"
    exit_code = _run_cli(
        receipt_main,
        [
            "maintenance_receipt.py",
            str(payload_path),
            "--revision-id",
            "mrev-001",
            "--cms-status",
            cms_status,
            "--base-digest",
            base_digest,
            "--receipt",
            str(receipt_path),
        ],
        monkeypatch,
    )
    return exit_code, receipt_path


def test_cli_receipt_accepts_pending_review_with_matching_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_code, receipt_path = _run_receipt_cli(
        tmp_path, monkeypatch, "pending-review", "b" * 64,
    )

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert receipt["status"] == "pending-review"
    assert receipt["revision_id"] == "mrev-001"
    assert receipt["entity_type"] == "article"
    assert receipt["entity_id"] == "24"
    assert receipt["base_digest"] == "b" * 64
    assert receipt["payload_sha256"] == payload_sha256(
        tmp_path / "proposed.json",
    )
    assert receipt["contract_version"] == CONTRACT_VERSION


def test_cli_receipt_rejects_non_pending_review_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_code, receipt_path = _run_receipt_cli(
        tmp_path, monkeypatch, "applied", "b" * 64,
    )
    assert exit_code == 1
    assert not receipt_path.exists()


def test_cli_receipt_rejects_digest_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path = tmp_path / "proposed.json"
    write_json(payload_path, _valid_maintenance_payload() | {"base_digest": "b" * 64})
    receipt_path = tmp_path / "create-receipt.json"
    exit_code = _run_cli(
        receipt_main,
        [
            "maintenance_receipt.py",
            str(payload_path),
            "--revision-id",
            "mrev-001",
            "--cms-status",
            "pending-review",
            "--base-digest",
            "c" * 64,
            "--receipt",
            str(receipt_path),
        ],
        monkeypatch,
    )
    assert exit_code == 1
    assert not receipt_path.exists()


def test_cli_receipt_records_filtered_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload_path = tmp_path / "proposed.json"
    write_json(payload_path, _valid_maintenance_payload() | {"base_digest": "b" * 64})
    receipt_path = tmp_path / "create-receipt.json"
    exit_code = _run_cli(
        receipt_main,
        [
            "maintenance_receipt.py",
            str(payload_path),
            "--revision-id",
            "mrev-001",
            "--cms-status",
            "pending-review",
            "--base-digest",
            "b" * 64,
            "--filtered-fields",
            '["status"]',
            "--receipt",
            str(receipt_path),
        ],
        monkeypatch,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert receipt["filtered_fields"] == ["status"]


# ── CLI: maintenance_post_apply ───────────────────────


def _applied_revision() -> MaintenanceJson:
    return {
        "id": "mrev-001",
        "entity_type": "article",
        "entity_id": "24",
        "rationale": "修正过时表述",
        "proposed_fields": {"title": "什么是 AI Agent（2026 修订）"},
        "filtered_fields": [],
        "base_digest": "a" * 64,
        "status": "applied",
        "reviewer": "opc",
        "review_digest": "a" * 64,
        "pre_snapshot_id": "snap-pre-001",
        "post_snapshot_id": "snap-post-001",
    }


def _run_post_apply_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    revision: MaintenanceJson,
) -> tuple[int, Path]:
    revision_path = tmp_path / "revision-get.json"
    write_json(revision_path, revision)
    receipt_path = tmp_path / "create-receipt.json"
    write_json(
        receipt_path,
        {
            "contract_version": CONTRACT_VERSION,
            "entity_type": "article",
            "entity_id": "24",
            "revision_id": "mrev-001",
            "payload_sha256": "0" * 64,
            "base_digest": "a" * 64,
            "filtered_fields": [],
            "status": "pending-review",
        },
    )
    output_path = tmp_path / "post-apply-verification.json"
    exit_code = _run_cli(
        post_apply_main,
        [
            "maintenance_post_apply.py",
            "--revision",
            str(revision_path),
            "--receipt",
            str(receipt_path),
            "--output",
            str(output_path),
        ],
        monkeypatch,
    )
    return exit_code, output_path


def test_cli_post_apply_accepts_applied_revision_with_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exit_code, output_path = _run_post_apply_cli(
        tmp_path, monkeypatch, _applied_revision(),
    )

    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert artifact["verified"] is True
    assert artifact["revision_id"] == "mrev-001"
    assert artifact["status"] == "applied"
    assert artifact["post_snapshot_id"] == "snap-post-001"
    assert artifact["contract_version"] == CONTRACT_VERSION


def test_cli_post_apply_rejects_not_applied_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = _applied_revision() | {"status": "pending-review"}
    exit_code, output_path = _run_post_apply_cli(
        tmp_path, monkeypatch, revision,
    )
    assert exit_code == 1
    assert not output_path.exists()


def test_cli_post_apply_rejects_missing_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = _applied_revision() | {"post_snapshot_id": None}
    exit_code, output_path = _run_post_apply_cli(
        tmp_path, monkeypatch, revision,
    )
    assert exit_code == 1
    assert not output_path.exists()


def test_cli_post_apply_rejects_receipt_for_other_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    revision = _applied_revision() | {"id": "mrev-999"}
    exit_code, output_path = _run_post_apply_cli(
        tmp_path, monkeypatch, revision,
    )
    assert exit_code == 1
    assert not output_path.exists()


# ── full synthetic chain with mock MCP ────────────────


def test_full_chain_creates_all_four_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_mcp = MockMCPServer()
    work = tmp_path / "maintenance" / "article" / "24" / "proposed"
    work.mkdir(parents=True)

    # 1) build proposed payload + diff review document
    current_path = work / "current.json"
    desired_path = work / "desired.json"
    write_json(current_path, _current_snapshot())
    write_json(desired_path, _desired_snapshot())
    payload_path = work / "proposed.json"
    diff_path = work / "diff-review.md"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "maintenance_payload.py",
            "--entity-type",
            "article",
            "--entity-id",
            "24",
            "--current",
            str(current_path),
            "--desired",
            str(desired_path),
            "--rationale",
            "修正过时表述，与 2026-10 官方口径对齐",
            "--output-dir",
            str(work),
        ],
    )
    exit_build = build_main()
    assert exit_build == 0
    assert payload_path.exists()
    assert diff_path.exists()
    built = json.loads(payload_path.read_text(encoding="utf-8"))
    assert built["base_digest"] == payload_sha256(current_path)
    assert built["proposed_fields"] == {"title": "什么是 AI Agent（2026 修订）"}

    # 2) deterministic validation
    report_path = work / "validation-report.json"
    exit_validate = _run_cli(
        validate_main,
        [
            "validate_maintenance.py",
            str(payload_path),
            "--report",
            str(report_path),
        ],
        monkeypatch,
    )
    assert exit_validate == 0

    # 3) agent calls MCP create (mock) -> receipt with assertions
    create_result = mock_mcp.maintenance_revision_create(
        entity_type=built["entity_type"],
        entity_id=built["entity_id"],
        rationale=built["rationale"],
        proposed_fields=built["proposed_fields"],
        base_digest=built["base_digest"],
    )
    receipt_path = work / "create-receipt.json"
    exit_receipt = _run_cli(
        receipt_main,
        [
            "maintenance_receipt.py",
            str(payload_path),
            "--revision-id",
            str(create_result["id"]),
            "--cms-status",
            str(create_result["status"]),
            "--base-digest",
            str(create_result["base_digest"]),
            "--filtered-fields",
            json.dumps(create_result["filtered_fields"]),
            "--receipt",
            str(receipt_path),
        ],
        monkeypatch,
    )
    assert exit_receipt == 0

    # 4) human approve+apply happens OUTSIDE the Skill (admin UI)
    mock_mcp.simulate_human_review_apply(str(create_result["id"]))

    revision = mock_mcp.maintenance_revision_get(str(create_result["id"]))
    assert revision is not None
    revision_path = work / "revision-get.json"
    write_json(revision_path, revision)
    verification_path = work / "post-apply-verification.json"
    exit_verify = _run_cli(
        post_apply_main,
        [
            "maintenance_post_apply.py",
            "--revision",
            str(revision_path),
            "--receipt",
            str(receipt_path),
            "--output",
            str(verification_path),
        ],
        monkeypatch,
    )
    assert exit_verify == 0

    # four artifacts all present
    for artifact in (
        report_path,
        diff_path,
        receipt_path,
        verification_path,
    ):
        assert artifact.exists()

    # no forbidden tool was ever called
    mock_mcp.assert_no_forbidden_calls()
    assert set(mock_mcp.get_call_tools()) == {
        "maintenance_revision_create",
        "maintenance_revision_get",
    }


def test_mock_rejects_forbidden_tools() -> None:
    mock_mcp = MockMCPServer()
    with pytest.raises(MockMCPError):
        mock_mcp.call("maintenance_revision_apply", id="mrev-001")
    with pytest.raises(MockMCPError):
        mock_mcp.call("maintenance_revision_approve", id="mrev-001")
    with pytest.raises(MockMCPError):
        mock_mcp.call("maintenance_revision_reject", id="mrev-001")
