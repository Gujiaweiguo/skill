from __future__ import annotations

from dataclasses import dataclass
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
class EvidenceKind(str, Enum):
    SPEC = "spec"
    CODE = "code"
    DOC = "doc"
    IMAGE = "image"
    MATRIX = "matrix"


@unique
class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


CapabilityId = NewType("CapabilityId", str)


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    kind: EvidenceKind
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
class CodeMap:
    project: str
    source_path: str
    commit_sha: str
    spec_capabilities: tuple[CodeCapability, ...]
    matrix_rows: tuple[MatrixRow, ...]


@dataclass(frozen=True, slots=True)
class DocFeature:
    source_file: str
    source_type: str
    heading: str
    depth: int
    normalized_term: str
    evidence: tuple[EvidenceRef, ...]


@dataclass(frozen=True, slots=True)
class DocMap:
    project: str
    source_path: str
    features: tuple[DocFeature, ...]


@dataclass(frozen=True, slots=True)
class ReconciledCapability:
    id: CapabilityId
    name: str
    code_status: CapabilityStatus
    doc_status: CapabilityStatus
    reconciled_status: CapabilityStatus
    confidence: Confidence
    gaps: tuple[str, ...] = ()
    evidence: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    project: str
    capabilities: tuple[ReconciledCapability, ...]
