"""Tests for archive evidence ingestion.

Each test builds a synthetic openspec archive tree under tmp_path and asserts
the loader extracts the expected fields and applies them to by_id correctly.
Run with `uv run pytest tests/test_archive_evidence.py -v`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from product_prd_generator.archive_evidence import (
    ArchiveEvidence,
    apply_archive_evidence,
    load_archive_evidence,
)
from product_prd_generator.models import (
    CapabilityStatus,
    Confidence,
    EvidenceKind,
    EvidenceRef,
    ReconciledCapability,
)


def _write_archive(
    root: Path,
    change_id: str,
    archive_date: str,
    proposal_body: str,
    tasks_body: str,
    readme_body: str = "",
) -> Path:
    archive_dir = root / "openspec" / "changes" / "archive" / f"{archive_date}-{change_id}"
    archive_dir.mkdir(parents=True)
    (archive_dir / "proposal.md").write_text(proposal_body, encoding="utf-8")
    (archive_dir / "tasks.md").write_text(tasks_body, encoding="utf-8")
    (archive_dir / "README.md").write_text(readme_body or f"# {change_id}", encoding="utf-8")
    (archive_dir / "design.md").write_text("placeholder", encoding="utf-8")
    specs_dir = archive_dir / "specs" / change_id
    specs_dir.mkdir(parents=True)
    (specs_dir / "spec.md").write_text("placeholder", encoding="utf-8")
    return archive_dir


def test_load_extracts_new_and_modified_capabilities(tmp_path: Path) -> None:
    _write_archive(
        tmp_path,
        change_id="w01-005-workbench-g2-view",
        archive_date="2026-08-06",
        proposal_body="""## Upstream

- **PRD**: PRD-LC-002

## Why

Operator visibility.

## What Changes

- Four new tabs.

## Capabilities

### New Capabilities

- `workbench-g2-view`: Frontend Workbench tabs for the Definition / Revision chain.

### Modified Capabilities

- `workbench`: extends the master-detail layout with new tabs.

## Impact

- Frontend code only.
""",
        tasks_body="""## 1. Sub-components

- [x] 1.1 DefinitionTab
- [x] 1.2 RevisionTab
- [x] 1.3 InvocationTab
- [ ] 1.4 EvidenceTab
""",
    )

    evidence = load_archive_evidence(tmp_path)

    assert len(evidence) == 1
    only = evidence[0]
    assert only.change_id == "w01-005-workbench-g2-view"
    assert only.archive_date == "2026-08-06"
    assert only.new_capabilities == ("workbench-g2-view",)
    assert only.modified_capabilities == ("workbench",)
    assert only.tasks_completed == 3
    assert only.tasks_total == 4
    assert "workbench-g2-view" in only.short_description


def test_load_returns_empty_when_archive_dir_missing(tmp_path: Path) -> None:
    evidence = load_archive_evidence(tmp_path)

    assert evidence == ()


def test_load_skips_archives_without_capabilities_section(tmp_path: Path) -> None:
    _write_archive(
        tmp_path,
        change_id="legacy-cleanup",
        archive_date="2025-05-27",
        proposal_body="## Why\n\nBranding cleanup only.\n",
        tasks_body="- [x] 1.1 strip headers\n",
    )

    evidence = load_archive_evidence(tmp_path)

    assert evidence == ()


def test_load_treats_none_modified_as_empty(tmp_path: Path) -> None:
    _write_archive(
        tmp_path,
        change_id="w01-002-de-revision-binding",
        archive_date="2026-08-06",
        proposal_body="""## Capabilities

### New Capabilities

- `de-revision-binding`: API + column for active revision.

### Modified Capabilities

- (none)

## Impact

- Backend only.
""",
        tasks_body="- [x] 1.1 migration\n- [x] 1.2 routes\n",
    )

    evidence = load_archive_evidence(tmp_path)

    assert len(evidence) == 1
    only = evidence[0]
    assert only.new_capabilities == ("de-revision-binding",)
    assert only.modified_capabilities == ()


def test_apply_promotes_existing_capability_to_existing_high(tmp_path: Path) -> None:
    archive_evidence = (
        ArchiveEvidence(
            change_id="w01-005-workbench-g2-view",
            archive_date="2026-08-06",
            new_capabilities=("workbench-g2-view",),
            modified_capabilities=(),
            tasks_completed=4,
            tasks_total=4,
            short_description="Workbench G2 view",
            archive_path="/opt/code/langchat/openspec/changes/archive/2026-08-06-w01-005-workbench-g2-view",
        ),
    )
    by_id: dict[str, ReconciledCapability] = {
        "workbench-g2-view": ReconciledCapability(
            id="workbench-g2-view",
            name="workbench-g2-view",
            code_status=CapabilityStatus.MISSING,
            doc_status=CapabilityStatus.EXISTING,
            reconciled_status=CapabilityStatus.MISSING,
            confidence=Confidence.LOW,
            gaps=("spec has no doc evidence yet",),
        ),
    }

    apply_archive_evidence(by_id, archive_evidence)

    promoted = by_id["workbench-g2-view"]
    assert promoted.reconciled_status == CapabilityStatus.EXISTING
    assert promoted.confidence == Confidence.HIGH
    assert promoted.gaps == ()
    archive_refs = [e for e in promoted.evidence if e.kind == EvidenceKind.OPENSPEC_ARCHIVE]
    assert len(archive_refs) == 1
    assert archive_refs[0].ref == "w01-005-workbench-g2-view@2026-08-06"


def test_apply_creates_new_capability_when_id_not_in_by_id(tmp_path: Path) -> None:
    archive_evidence = (
        ArchiveEvidence(
            change_id="w01-003-evidence-manifest",
            archive_date="2026-08-06",
            new_capabilities=("evidence-manifest-projection",),
            modified_capabilities=(),
            tasks_completed=2,
            tasks_total=2,
            short_description="Evidence manifest",
            archive_path="/opt/code/langchat/openspec/changes/archive/2026-08-06-w01-003-evidence-manifest",
        ),
    )
    by_id: dict[str, ReconciledCapability] = {}

    apply_archive_evidence(by_id, archive_evidence)

    created = by_id["evidence-manifest-projection"]
    assert created.reconciled_status == CapabilityStatus.EXISTING
    assert created.confidence == Confidence.HIGH
    assert created.code_status == CapabilityStatus.EXISTING
    assert created.doc_status == CapabilityStatus.EXISTING
    archive_refs = [e for e in created.evidence if e.kind == EvidenceKind.OPENSPEC_ARCHIVE]
    assert len(archive_refs) == 1


def test_apply_handles_empty_evidence_gracefully(tmp_path: Path) -> None:
    by_id: dict[str, ReconciledCapability] = {
        "x": ReconciledCapability(
            id="x",
            name="x",
            code_status=CapabilityStatus.EXISTING,
            doc_status=CapabilityStatus.EXISTING,
            reconciled_status=CapabilityStatus.EXISTING,
            confidence=Confidence.MEDIUM,
        ),
    }

    apply_archive_evidence(by_id, ())

    assert by_id["x"].confidence == Confidence.MEDIUM
