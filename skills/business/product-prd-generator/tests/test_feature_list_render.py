from __future__ import annotations

import os
import subprocess
from pathlib import Path

import yaml

from product_prd_generator.render import _render_feature_list


def _front_matter(rendered: str) -> tuple[dict[str, object], str]:
    opening, metadata_text, body = rendered.split("---", maxsplit=2)
    assert opening == ""
    metadata = yaml.safe_load(metadata_text)
    assert isinstance(metadata, dict)
    return metadata, body


def test_feature_list_front_matter_reports_source_revision_and_counts(tmp_path: Path) -> None:
    # Given
    code_root = tmp_path / "product"
    code_root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=code_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=code_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=code_root, check=True)
    (code_root / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=code_root, check=True)
    commit_env = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-07-26T10:20:30+08:00",
        "GIT_COMMITTER_DATE": "2026-07-26T10:20:30+08:00",
    }
    subprocess.run(["git", "commit", "-q", "-m", "fixture"], cwd=code_root, env=commit_env, check=True)
    expected_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=code_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    capabilities = [
        {"name": "Existing", "reconciled_status": "existing", "confidence": "high", "evidence": []},
        {"name": "Partial", "reconciled_status": "partial", "confidence": "medium", "evidence": []},
        {"name": "Missing", "reconciled_status": "missing", "confidence": "low", "evidence": []},
        {
            "name": "Deferred",
            "reconciled_status": "explicitly-not-do",
            "confidence": "high",
            "evidence": [],
        },
        {"name": "Unclassified", "confidence": "high", "evidence": []},
    ]

    # When
    rendered = _render_feature_list(capabilities, project="测试项目", code_root=str(code_root))

    # Then
    metadata, body = _front_matter(rendered)
    assert metadata == {
        "generated_at": metadata["generated_at"],
        "generator": "product-prd-generator",
        "generator_version": "0.1.0",
        "project": "测试项目",
        "mi_code_root": str(code_root),
        "mi_commit": expected_commit,
        "mi_commit_date": "2026-07-26",
        "mi_commits_since_last_prd": None,
        "item_count": 5,
        "status_distribution": {
            "existing": 1,
            "partial": 1,
            "missing": 1,
            "explicitly_not_do": 1,
        },
        "high_confidence_count": 3,
    }
    assert body == (
        "\n\n# 功能清单\n\n"
        "| 功能名 | 状态 | 置信度 | 证据数 |\n"
        "|---|---|---|---|\n"
        "| Existing | existing | high | 0 |\n"
        "| Partial | partial | medium | 0 |\n"
        "| Missing | missing | low | 0 |\n"
        "| Deferred | explicitly-not-do | high | 0 |\n"
        "| Unclassified | missing | high | 0 |\n"
    )


def test_feature_list_front_matter_uses_null_revision_for_non_git_root(tmp_path: Path) -> None:
    # Given
    capabilities: list[dict[str, object]] = []

    # When
    rendered = _render_feature_list(capabilities, project="测试项目", code_root=str(tmp_path))

    # Then
    metadata, _ = _front_matter(rendered)
    assert metadata["mi_commit"] is None
    assert metadata["mi_commit_date"] is None
    assert metadata["status_distribution"] == {
        "existing": 0,
        "partial": 0,
        "missing": 0,
        "explicitly_not_do": 0,
    }
