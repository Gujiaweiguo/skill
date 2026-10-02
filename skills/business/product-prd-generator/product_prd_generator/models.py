from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import NewType


@unique
class CapabilityStatus(str, Enum):
    EXISTING = "existing"
    PARTIAL = "partial"
    MISSING = "missing"
    EXPLICITLY_NOT_DO = "explicitly-not-do"


@unique
class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@unique
class ScanStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    NOT_SCANNED = "not-scanned"
    INACCESSIBLE = "inaccessible"


@unique
class EvidenceKind(str, Enum):
    SPEC = "spec"
    CODE = "code"
    TEST = "test"
    DOC = "doc"
    IMAGE = "image"
    MATRIX = "matrix"
    OPENSPEC_ARCHIVE = "openspec-archive"


@unique
class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


CapabilityId = NewType("CapabilityId", str)


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    kind: EvidenceKind | str
    ref: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class CodeCapability:
    id: CapabilityId
    name: str
    status: CapabilityStatus
    spec_path: str
    purpose: str
    requirement_count: int
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class MatrixRow:
    id: CapabilityId
    function_point: str
    manual_ref: str
    spec_mapping: str
    mi_status: CapabilityStatus
    landing_point: str
    classification: str
    disposition: str
    priority: Priority


@dataclass(frozen=True, slots=True)
class ScannerCoverage:
    status: ScanStatus
    scope: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    artifact_count: int = 0


@dataclass(frozen=True, slots=True)
class ScanCoverage:
    status: ScanStatus
    scope: tuple[str, ...]
    limitations: tuple[str, ...]
    specs: ScannerCoverage
    matrix: ScannerCoverage
    direct_code: ScannerCoverage
    direct_tests: ScannerCoverage


@dataclass(frozen=True, slots=True)
class CodeMap:
    project: str
    source_path: str
    commit_sha: str
    spec_capabilities: tuple[CodeCapability, ...]
    matrix_rows: tuple[MatrixRow, ...]
    scan_coverage: ScanCoverage
    direct_evidence: tuple[object, ...] = ()


@dataclass(frozen=True, slots=True)
class DocFeature:
    source_file: str
    source_type: str
    heading: str
    depth: int
    normalized_term: str
    evidence: tuple[EvidenceRef, ...]


@dataclass(frozen=True, slots=True)
class Requirement:
    """Structured requirement from customer/product docs.

    Only leaf headings (no sub-headings beneath) become Requirements.
    Container headings provide scenario context. Six-dimension framework:
    scenario/sub_scenario/function come from heading hierarchy,
    nearby_text captures pain-point description, source_customer tracks origin.
    """
    source_file: str
    source_type: str
    source_customer: str
    scenario: str
    sub_scenario: str
    function: str
    depth: int
    nearby_text: str
    normalized_term: str
    evidence: tuple[EvidenceRef, ...]
    kind: str = "feature"
    clause_parent: str = ""
    clause_path: str = ""


@dataclass(frozen=True, slots=True)
class DocMap:
    project: str
    source_path: str
    features: tuple[DocFeature, ...]
    requirements: tuple[Requirement, ...] = ()


@dataclass(frozen=True, slots=True)
class ReconciledCapability:
    id: str
    name: str
    code_status: CapabilityStatus | str
    doc_status: CapabilityStatus | str
    reconciled_status: CapabilityStatus | str
    confidence: Confidence | str
    gaps: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()

    @property
    def evidence_provenance(self) -> str:
        kinds = {item.kind.value if isinstance(item.kind, EvidenceKind) else item.kind for item in self.evidence}
        has_archive = EvidenceKind.OPENSPEC_ARCHIVE.value in kinds
        has_code = EvidenceKind.CODE.value in kinds
        has_test = EvidenceKind.TEST.value in kinds
        if has_code and has_test:
            direct = "direct-code-and-test"
        elif has_code:
            direct = "direct-code"
        elif has_test:
            direct = "direct-test"
        elif EvidenceKind.SPEC.value in kinds:
            direct = "spec-only"
        else:
            direct = "no-direct-evidence"
        if has_archive and direct.startswith("direct-"):
            return f"archive-and-{direct.removeprefix('direct-')}"
        if has_archive and direct == "spec-only":
            return "archive-and-spec-only"
        if has_archive:
            return "archive-only"
        return direct


@dataclass(frozen=True, slots=True)
class RequirementRecord:
    """A requirement matched against code capabilities, with priority."""
    source_file: str
    source_type: str
    source_customer: str
    kind: str
    scenario: str
    sub_scenario: str
    function: str
    nearby_text: str
    normalized_term: str
    matched_capability: str
    code_status: str
    priority: str
    clause_parent: str = ""
    clause_path: str = ""
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    project: str
    capabilities: tuple[ReconciledCapability, ...]
    requirements: tuple[RequirementRecord, ...] = ()
    source_path: str = ""
    source_revision: str = ""
    scan_coverage: dict[str, object] = field(default_factory=dict)
