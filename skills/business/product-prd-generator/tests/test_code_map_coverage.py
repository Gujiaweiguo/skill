from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, cast

from product_prd_generator.code_map import extract, to_json


SKILL_ROOT = Path(__file__).resolve().parents[1]


def _write_spec(code_root: Path) -> None:
    spec_dir = code_root / "openspec" / "specs" / "example"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(
        "## Purpose\n\nExample capability.\n\n### Requirement: Example behavior\n",
        encoding="utf-8",
    )


def test_extract_reports_complete_specs_and_disabled_matrix(tmp_path: Path) -> None:
    _write_spec(tmp_path)
    code_map = extract(tmp_path, "langchat", skill_root=SKILL_ROOT)

    coverage = to_json(code_map)["scan_coverage"]
    assert isinstance(coverage, dict)
    assert coverage["status"] == "partial"
    assert coverage["scanners"]["specs"]["status"] == "complete"
    assert coverage["scanners"]["specs"]["artifact_count"] == 1
    assert coverage["scanners"]["matrix"]["status"] == "not-scanned"
    assert coverage["scanners"]["matrix"]["artifact_count"] == 0
    assert set(to_json(code_map)) >= {
        "project",
        "source_path",
        "commit_sha",
        "spec_capabilities",
        "matrix_rows",
        "scan_coverage",
    }


def test_extract_reports_complete_configured_matrix(tmp_path: Path) -> None:
    _write_spec(tmp_path)
    matrix_path = tmp_path / "artifacts" / "alignment" / "product-definition-matrix.md"
    matrix_path.parent.mkdir(parents=True)
    matrix_path.write_text(
        "| ID | Manual Function Point | Manual Ref | OpenSpec Mapping | MI Status | MI landing point | Classification | Disposition | Priority |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| example | Example | §1 | example | existing | app | core | keep | P1 |\n",
        encoding="utf-8",
    )
    code_map = extract(tmp_path, "商管系统", skill_root=SKILL_ROOT)

    coverage = to_json(code_map)["scan_coverage"]
    assert isinstance(coverage, dict)
    assert coverage["scanners"]["matrix"]["status"] == "complete"
    assert coverage["scanners"]["matrix"]["artifact_count"] == 1


def test_extract_reports_missing_specs_root_inaccessible(tmp_path: Path) -> None:
    code_map = extract(tmp_path, "langchat", skill_root=SKILL_ROOT)

    coverage = to_json(code_map)["scan_coverage"]
    assert isinstance(coverage, dict)
    assert coverage["scanners"]["specs"]["status"] == "inaccessible"
    assert coverage["scanners"]["specs"]["artifact_count"] == 0


def test_json_marks_direct_runtime_and_tests_not_scanned(tmp_path: Path) -> None:
    _write_spec(tmp_path)
    payload = to_json(extract(tmp_path, "langchat", skill_root=SKILL_ROOT))

    serialized = json.loads(json.dumps(payload))
    scanners = serialized["scan_coverage"]["scanners"]
    assert scanners["direct_code"]["status"] == "not-scanned"
    assert scanners["direct_tests"]["status"] == "not-scanned"
    assert scanners["direct_code"]["artifact_count"] == 0
    assert scanners["direct_tests"]["artifact_count"] == 0
    assert all(
        item["kind"] not in {"code", "test"}
        for cap in serialized["spec_capabilities"]
        for item in cap["evidence"]
    )


def test_enabled_direct_scanners_propagate_static_evidence(tmp_path: Path) -> None:
    spec_dir = tmp_path / "openspec" / "specs" / "capability-a"
    spec_dir.mkdir(parents=True)
    (spec_dir / "spec.md").write_text(
        "## Purpose\n\nCapability A.\n\n### Requirement: A\n",
        encoding="utf-8",
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "service.py").write_text("Capability A\n", encoding="utf-8")
    (tmp_path / "tests" / "test_service.py").write_text("Capability A\n", encoding="utf-8")
    rules_dir = tmp_path / "skill" / "references"
    rules_dir.mkdir(parents=True)
    (rules_dir / "code-map-rules-langchat.yaml").write_text(
        "\n".join(
            [
                "project: langchat",
                "specs:",
                "  path: openspec/specs",
                "matrix:",
                "  enabled: false",
                "direct_code:",
                "  enabled: true",
                "  include_paths: [src/**/*.py]",
                "  extensions: [.py]",
                "  capabilities:",
                "    capability-a: [Capability A]",
                "  spec_anchors:",
                "    capability-a: capability-a-spec",
                "direct_tests:",
                "  enabled: true",
                "  include_paths: [tests/**/*.py]",
                "  extensions: [.py]",
                "  capabilities:",
                "    capability-a: [Capability A]",
                "  spec_anchors:",
                "    capability-a: capability-a-spec",
                "exclude_paths: []",
            ]
        ),
        encoding="utf-8",
    )

    payload = to_json(extract(tmp_path, "langchat", skill_root=tmp_path / "skill"))

    capability = cast(list[Mapping[str, object]], payload["spec_capabilities"])[0]
    evidence = cast(list[Mapping[str, object]], capability["evidence"])
    assert {item["kind"] for item in evidence} == {"spec", "code", "test"}
    scan_coverage = cast(Mapping[str, object], payload["scan_coverage"])
    scanners = cast(Mapping[str, Mapping[str, object]], scan_coverage["scanners"])
    assert scanners["direct_code"]["status"] == "complete"
    assert scanners["direct_tests"]["status"] == "complete"
    direct_evidence = cast(Mapping[str, object], payload["direct_evidence"])
    matches = cast(list[Mapping[str, object]], direct_evidence["matches"])
    assert matches[0]["evidence_id"]
    assert matches[0]["spec_capability_id"] == "capability-a-spec"
    assert matches[0]["role"] in {"declaration", "mapping", "other"}
