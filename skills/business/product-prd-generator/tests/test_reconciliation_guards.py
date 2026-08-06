from __future__ import annotations

from pathlib import Path

import pytest

from product_prd_generator._paths import (
    InvalidProjectError,
    codebase_features_path_for_project,
    validate_project,
)
from product_prd_generator.coverage_validate import (
    CapabilityRow,
    _build_suggested_changes,
    _write_suggested_changes_yaml,
)
from product_prd_generator.doc_map import SourceType, _classify_source_type
from product_prd_generator.reconcile import _add_spec_referenced_capabilities


def test_target_architecture_source_is_not_customer_requirements() -> None:
    source = _classify_source_type(Path("04-target-architecture/langchat-v2/charter.md"))

    assert source == SourceType.ARCHITECTURE.value
    assert source != SourceType.CUSTOMER.value


def test_non_ontology_lowercase_heading_is_not_added_as_missing() -> None:
    doc_map = {
        "requirements": [
            {
                "source_type": SourceType.CUSTOMER.value,
                "normalized_term": "bindingmanifestdigest",
                "source_customer": "langchat-v2",
            }
        ]
    }

    capabilities: dict[str, object] = {}
    _add_spec_referenced_capabilities(capabilities, doc_map, ontology_ids={"skill-release"})

    assert capabilities == {}


def test_low_confidence_missing_is_not_suggested_change() -> None:
    rows = [
        CapabilityRow(
            capability_id="noise",
            capability_name="noise",
            module="architecture",
            prd_status="missing",
            confidence="low",
        ),
        CapabilityRow(
            capability_id="real-gap",
            capability_name="real gap",
            module="runtime",
            prd_status="missing",
            confidence="high",
        ),
    ]

    changes = _build_suggested_changes(rows)

    assert [change["change_id"] for change in changes] == ["real-gap"]


def test_codebase_features_path_is_project_scoped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LANLNK_BASE", str(tmp_path))

    expected = tmp_path / "raw" / "prd-langchat" / "parsed" / "codebase-features.json"

    assert codebase_features_path_for_project("langchat") == expected


def test_coverage_suggested_changes_yaml_does_not_collide_with_handoff(tmp_path: Path) -> None:
    rows = [
        CapabilityRow(
            capability_id="spa-data",
            capability_name="SPA data completeness",
            module="runtime",
            prd_status="missing",
            confidence="high",
            customer_cells={"wandai": type("C", (), {"strength": "strong", "matched_count": 1})()},
        ),
    ]

    written = _write_suggested_changes_yaml(tmp_path, rows)

    assert written.name == "coverage-suggested-openspec-changes.yaml"
    assert not (tmp_path / "suggested-openspec-changes.yaml").exists()
    assert (tmp_path / "coverage-suggested-openspec-changes.yaml").exists()


@pytest.mark.parametrize(
    "raw",
    [
        "../etc",
        "foo/bar",
        "foo\\bar",
        "",
        "  ",
        "langchat\0x",
        "a\tb",
    ],
)
def test_validate_project_rejects_unsafe_input(raw: str) -> None:
    with pytest.raises(InvalidProjectError):
        validate_project(raw)


@pytest.mark.parametrize("raw", ["商管系统", "langchat", "LnkChatBI", "mi-cre"])
def test_validate_project_accepts_known_projects(raw: str) -> None:
    assert validate_project(raw) == raw
