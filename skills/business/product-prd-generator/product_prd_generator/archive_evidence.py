"""Archive evidence ingestion.

Reads archived OpenSpec changes under <code_root>/openspec/changes/archive/
and exposes their declared capabilities as EvidenceRef payloads that
reconcile can attach to (or create) capabilities. Archive evidence is the
strongest available signal that a capability is implemented and verified,
since OpenSpec archive requires `/opsx-verify` to pass.

The loader is defensive: any single malformed archive is skipped, never
raised, so a noisy archive tree cannot block PRD generation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .models import (
    CapabilityStatus,
    Confidence,
    EvidenceKind,
    EvidenceRef,
    ReconciledCapability,
)

_CAPABILITY_LINE = re.compile(r"^-\s+`([a-z0-9][a-z0-9-]*)`\s*:?.*$", re.MULTILINE)
_CHECKED_TASK = re.compile(r"^-\s+\[x\]", re.MULTILINE | re.IGNORECASE)
_UNCHECKED_TASK = re.compile(r"^-\s+\[ \]", re.MULTILINE)
_DATE_CHANGE_ID = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-(?P<change_id>[A-Za-z0-9][A-Za-z0-9-]*)$")
_NEW_CAPABILITIES_HEADER = "### New Capabilities"
_MODIFIED_CAPABILITIES_HEADER = "### Modified Capabilities"
_NONE_MARKER = "(none)"


@dataclass(frozen=True, slots=True)
class ArchiveEvidence:
    change_id: str
    archive_date: str
    new_capabilities: tuple[str, ...]
    modified_capabilities: tuple[str, ...]
    tasks_completed: int
    tasks_total: int
    short_description: str
    archive_path: str


def load_archive_evidence(code_root: Path) -> tuple[ArchiveEvidence, ...]:
    """Scan <code_root>/openspec/changes/archive/ and return one entry per
    archived change that declares at least one capability.

    Malformed archives are skipped silently. Returns an empty tuple when the
    archive directory is missing or contains no capability-bearing changes.
    """
    archive_root = code_root / "openspec" / "changes" / "archive"
    if not archive_root.is_dir():
        return ()

    results: list[ArchiveEvidence] = []
    for entry in sorted(archive_root.iterdir()):
        if not entry.is_dir():
            continue
        parsed = _parse_archive_dir(entry)
        if parsed is not None:
            results.append(parsed)
    return tuple(results)


def _parse_archive_dir(entry: Path) -> ArchiveEvidence | None:
    match = _DATE_CHANGE_ID.match(entry.name)
    if match is None:
        return None
    change_id = match.group("change_id")
    archive_date = match.group("date")

    proposal_path = entry / "proposal.md"
    if not proposal_path.is_file():
        return None
    proposal_body = proposal_path.read_text(encoding="utf-8")
    new_caps, modified_caps = _extract_capabilities(proposal_body)
    if not new_caps and not modified_caps:
        return None

    tasks_completed, tasks_total = _count_tasks(entry / "tasks.md")
    short_description = _read_short_description(entry / "README.md", change_id)

    return ArchiveEvidence(
        change_id=change_id,
        archive_date=archive_date,
        new_capabilities=new_caps,
        modified_capabilities=modified_caps,
        tasks_completed=tasks_completed,
        tasks_total=tasks_total,
        short_description=short_description,
        archive_path=str(entry),
    )


def _extract_capabilities(proposal_body: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (new, modified) capability ID tuples from the proposal's
    Capabilities section. Empty tuples when the section or its subsections
    are absent, or when a subsection lists only `(none)`.
    """
    capabilities_section = _isolate_section(proposal_body, "## Capabilities")
    if capabilities_section is None:
        return ((), ())
    new_caps = _extract_subsection_ids(
        capabilities_section,
        _NEW_CAPABILITIES_HEADER,
    )
    modified_caps = _extract_sub_section_ids_with_none(
        capabilities_section,
        _MODIFIED_CAPABILITIES_HEADER,
    )
    return (new_caps, modified_caps)


def _isolate_section(body: str, heading: str) -> str | None:
    pattern = re.compile(
        r"^" + re.escape(heading) + r"\s*\n(?P<body>.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(body)
    if match is None:
        return None
    return match.group("body")


def _extract_sub_section_ids_with_none(section_body: str, header: str) -> tuple[str, ...]:
    """Extract IDs from a subsection; treat an explicit `(none)` body as empty."""
    sub_section = _isolate_subsection(section_body, header)
    if sub_section is None:
        return ()
    stripped = sub_section.strip()
    if stripped == _NONE_MARKER or _NONE_MARKER in stripped.splitlines()[0:1]:
        return ()
    return tuple(_CAPABILITY_LINE.findall(sub_section))


def _extract_subsection_ids(section_body: str, header: str) -> tuple[str, ...]:
    sub_section = _isolate_subsection(section_body, header)
    if sub_section is None:
        return ()
    return tuple(_CAPABILITY_LINE.findall(sub_section))


def _isolate_subsection(parent_body: str, header: str) -> str | None:
    pattern = re.compile(
        r"^" + re.escape(header) + r"\s*\n(?P<body>.*?)(?=^###[^#]|^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(parent_body)
    if match is None:
        return None
    return match.group("body")


def _count_tasks(tasks_path: Path) -> tuple[int, int]:
    if not tasks_path.is_file():
        return (0, 0)
    body = tasks_path.read_text(encoding="utf-8")
    completed = len(_CHECKED_TASK.findall(body))
    unchecked = len(_UNCHECKED_TASK.findall(body))
    return (completed, completed + unchecked)


def _read_short_description(readme_path: Path, fallback_change_id: str) -> str:
    if not readme_path.is_file():
        return fallback_change_id
    first_line = readme_path.read_text(encoding="utf-8").splitlines()[0:1]
    if not first_line:
        return fallback_change_id
    return first_line[0].lstrip("# ").strip() or fallback_change_id


def apply_archive_evidence(
    by_id: dict[str, ReconciledCapability],
    evidence: tuple[ArchiveEvidence, ...],
) -> None:
    """Promote capabilities listed in archived changes to existing/high and
    attach an `openspec-archive` EvidenceRef to each.

    Capabilities already present in `by_id` are updated in place; unknown IDs
    are inserted as freshly-created existing/high capabilities. Archive
    evidence overrides any prior reconciled_status, since OpenSpec archive
    requires `/opsx-verify` to pass — it is the strongest signal available.
    """
    for entry in evidence:
        for capability_id in (*entry.new_capabilities, *entry.modified_capabilities):
            archive_ref = EvidenceRef(
                kind=EvidenceKind.OPENSPEC_ARCHIVE,
                ref=f"{entry.change_id}@{entry.archive_date}",
                note=entry.short_description,
            )
            existing = by_id.get(capability_id)
            if existing is None:
                by_id[capability_id] = ReconciledCapability(
                    id=capability_id,
                    name=capability_id,
                    code_status=CapabilityStatus.EXISTING,
                    doc_status=CapabilityStatus.EXISTING,
                    reconciled_status=CapabilityStatus.EXISTING,
                    confidence=Confidence.HIGH,
                    gaps=(),
                    evidence=(archive_ref,),
                )
                continue
            merged_evidence = _merge_evidence(existing.evidence, archive_ref)
            by_id[capability_id] = ReconciledCapability(
                id=existing.id,
                name=existing.name,
                code_status=CapabilityStatus.EXISTING,
                doc_status=existing.doc_status,
                reconciled_status=CapabilityStatus.EXISTING,
                confidence=Confidence.HIGH,
                gaps=(),
                evidence=merged_evidence,
            )


def _merge_evidence(
    existing: tuple[EvidenceRef, ...],
    incoming: EvidenceRef,
) -> tuple[EvidenceRef, ...]:
    seen = {(ref.kind, ref.ref) for ref in existing}
    if (incoming.kind, incoming.ref) in seen:
        return existing
    return (*existing, incoming)
