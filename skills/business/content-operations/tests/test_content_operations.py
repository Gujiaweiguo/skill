from __future__ import annotations

import json
import queue
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

import pytest

SKILL_ROOT: Final = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))
JsonScalar = str | bool

from scripts.cms_client import CmsConfig, CmsResponseError  # noqa: E402
from scripts.contracts import (  # noqa: E402
    CONTRACT_VERSION,
    PayloadValidationError,
    payload_sha256,
    validate_payload_file,
)
from scripts.import_artifacts import ImportPaths  # noqa: E402
from scripts.import_draft import import_draft  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping


class ReceivedRequest(NamedTuple):
    path: str
    authorization: str
    body: bytes


@contextmanager
def draft_server(
    response: dict[str, str | int],
) -> Generator[tuple[str, queue.Queue[ReceivedRequest]], None, None]:
    received: queue.Queue[ReceivedRequest] = queue.Queue()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            received.put(
                ReceivedRequest(
                    self.path,
                    self.headers.get("Authorization", ""),
                    self.rfile.read(length),
                )
            )
            encoded = json.dumps(response).encode()
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *_args: str) -> None:  # noqa: A002
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_name, server.server_port
        yield f"http://{host}:{port}/article-create", received
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


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


def test_importer_creates_draft_receipt_without_secret(tmp_path: Path) -> None:
    paths, _payload_path = prepare_import(tmp_path)
    token = "test-secret-token"

    with draft_server({"id": 42, "status": "draft"}) as (endpoint, received):
        receipt = import_draft(paths, CmsConfig(endpoint=endpoint, token=token))

    request = received.get_nowait()
    request_body = json.loads(request[2])
    assert request[0] == "/article-create"
    assert request[1] == f"Bearer {token}"
    assert request_body["slug"] == "what-is-ai-agent"
    assert "status" not in request_body
    assert receipt.cms_article_id == "42"
    assert receipt.status == "draft"
    assert receipt.slug == "what-is-ai-agent"
    assert receipt.category == "ai-trends"
    assert token not in paths.receipt.read_text(encoding="utf-8")


def test_importer_accepts_draft_response_with_article_fields(tmp_path: Path) -> None:
    paths, _payload_path = prepare_import(tmp_path)

    with draft_server(
        {
            "id": 42,
            "status": "draft",
            "slug": "what-is-ai-agent",
            "category": "ai-trends",
        }
    ) as (endpoint, _received):
        receipt = import_draft(paths, CmsConfig(endpoint=endpoint, token="secret"))

    assert receipt.cms_article_id == "42"
    assert receipt.status == "draft"


def test_importer_validates_before_any_cms_request(tmp_path: Path) -> None:
    paths, payload_path = prepare_import(tmp_path)
    invalid = valid_payload()
    invalid["status"] = "published"
    write_json(payload_path, invalid)

    with (
        draft_server({"id": 42, "status": "draft"}) as (endpoint, received),
        pytest.raises(PayloadValidationError),
    ):
        import_draft(paths, CmsConfig(endpoint=endpoint, token="secret"))

    assert received.empty()
    assert not paths.receipt.exists()


def test_importer_rejects_non_draft_response_without_receipt(tmp_path: Path) -> None:
    paths, _payload_path = prepare_import(tmp_path)

    with (
        draft_server({"id": 42, "status": "published"}) as (endpoint, _received),
        pytest.raises(CmsResponseError),
    ):
        import_draft(paths, CmsConfig(endpoint=endpoint, token="secret"))

    assert not paths.receipt.exists()
