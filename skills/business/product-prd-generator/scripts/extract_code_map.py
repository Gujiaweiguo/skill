# ─── How to run ───
#   cd skills/business/product-prd-generator
#   uv run scripts/extract_code_map.py --code-root /opt/code/mi --output parsed/current-code-map.json

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from enum import Enum, unique
from functools import lru_cache
from pathlib import Path


@unique
class CapabilityStatus(str, Enum):
    EXISTING = "existing"
    PARTIAL = "partial"
    MISSING = "missing"
    EXPLICITLY_NOT_DO = "explicitly-not-do"


@unique
class EvidenceKind(str, Enum):
    SPEC = "spec"
    MATRIX = "matrix"


@unique
class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    kind: str
    ref: str


@dataclass(frozen=True, slots=True)
class SpecCapability:
    id: str
    name: str
    status: str
    spec_path: str
    purpose: str
    requirement_count: int
    evidence: tuple[EvidenceRef, ...]


@dataclass(frozen=True, slots=True)
class MatrixRow:
    id: str
    function_point: str
    manual_ref: str
    spec_mapping: str
    mi_status: str
    landing_point: str
    classification: str
    disposition: str
    priority: str


@dataclass(frozen=True, slots=True)
class CodeMap:
    project: str
    source_path: str
    commit_sha: str
    spec_capabilities: tuple[SpecCapability, ...]
    matrix_rows: tuple[MatrixRow, ...]


_SPEC_HEADING = re.compile(r"^### Requirement:\s*(.+)$", re.MULTILINE)
_MATRIX_HEADER = re.compile(
    r"\|\s*ID\s*\|\s*Manual Function Point\s*\|\s*Manual Ref\s*\|"
    r"\s*OpenSpec Mapping\s*\|\s*MI Status\s*\|\s*MI landing point\s*\|"
    r"\s*Classification\s*\|\s*Disposition\s*\|\s*Priority\s*\|"
)
_STATUS_BY_LABEL = {
    "existing": CapabilityStatus.EXISTING,
    "partial": CapabilityStatus.PARTIAL,
    "missing": CapabilityStatus.MISSING,
    "explicitly-not-do": CapabilityStatus.EXPLICITLY_NOT_DO,
}
_PRIORITY_BY_LABEL = {
    "P0": Priority.P0,
    "P1": Priority.P1,
    "P2": Priority.P2,
    "P3": Priority.P3,
}


@lru_cache(maxsize=1)
def _git_head_sha(repo_root: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", repo_root, "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return completed.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown"


def _parse_purpose(spec_text: str) -> str:
    match = re.search(r"^## Purpose\s*\n+(.+?)(?=\n## |\Z)", spec_text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _parse_status(purpose_text: str) -> CapabilityStatus:
    lowered = purpose_text.lower()
    if "explicitly-not-do" in lowered or "explicitly not do" in lowered:
        return CapabilityStatus.EXPLICITLY_NOT_DO
    if "partial" in lowered:
        return CapabilityStatus.PARTIAL
    if "missing" in lowered:
        return CapabilityStatus.MISSING
    return CapabilityStatus.EXISTING


def _parse_spec(spec_path: Path, project_root: Path) -> SpecCapability:
    text = spec_path.read_text(encoding="utf-8")
    purpose = _parse_purpose(text)
    requirement_count = len(_SPEC_HEADING.findall(text))
    status = _parse_status(purpose)
    rel_path = str(spec_path.relative_to(project_root))
    return SpecCapability(
        id=spec_path.parent.name,
        name=spec_path.parent.name.replace("-", " "),
        status=status.value,
        spec_path=rel_path,
        purpose=purpose,
        requirement_count=requirement_count,
        evidence=(EvidenceRef(kind=EvidenceKind.SPEC.value, ref=rel_path),),
    )


def _iter_spec_capabilities(specs_root: Path, project_root: Path) -> tuple[SpecCapability, ...]:
    return tuple(
        _parse_spec(spec_path, project_root)
        for spec_path in sorted(specs_root.glob("*/spec.md"))
        if spec_path.is_file()
    )


def _parse_matrix_row(line: str) -> MatrixRow | None:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) < 9:
        return None
    raw_id, function_point, manual_ref, spec_mapping, mi_status, landing, classification, disposition, priority = cells[:9]
    status = _STATUS_BY_LABEL.get(mi_status.strip().lower())
    if status is None:
        return None
    prio = _PRIORITY_BY_LABEL.get(priority.strip().upper(), Priority.P3)
    return MatrixRow(
        id=raw_id,
        function_point=function_point,
        manual_ref=manual_ref,
        spec_mapping=spec_mapping,
        mi_status=status.value,
        landing_point=landing,
        classification=classification,
        disposition=disposition,
        priority=prio.value,
    )


def _iter_matrix_rows(matrix_path: Path) -> tuple[MatrixRow, ...]:
    if not matrix_path.is_file():
        return ()
    text = matrix_path.read_text(encoding="utf-8")
    rows: list[MatrixRow] = []
    in_matrix = False
    for line in text.splitlines():
        if _MATRIX_HEADER.search(line):
            in_matrix = True
            continue
        if in_matrix and line.startswith("|"):
            if set(line.strip().strip("|").strip()) <= {"-"}:
                continue
            parsed = _parse_matrix_row(line)
            if parsed is not None:
                rows.append(parsed)
        elif in_matrix and line.strip().startswith("#"):
            break
    return tuple(rows)


def extract(code_root: Path, project: str = "商管系统") -> CodeMap:
    specs_root = code_root / "openspec" / "specs"
    matrix_path = code_root / "artifacts" / "alignment" / "product-definition-matrix.md"
    return CodeMap(
        project=project,
        source_path=str(code_root),
        commit_sha=_git_head_sha(str(code_root)),
        spec_capabilities=_iter_spec_capabilities(specs_root, code_root),
        matrix_rows=_iter_matrix_rows(matrix_path),
    )


def _to_dict(code_map: CodeMap) -> dict[str, object]:
    return {
        "project": code_map.project,
        "source_path": code_map.source_path,
        "commit_sha": code_map.commit_sha,
        "spec_capabilities": [
            {
                "id": cap.id,
                "name": cap.name,
                "status": cap.status,
                "spec_path": cap.spec_path,
                "purpose": cap.purpose,
                "requirement_count": cap.requirement_count,
                "evidence": [{"kind": e.kind, "ref": e.ref} for e in cap.evidence],
            }
            for cap in code_map.spec_capabilities
        ],
        "matrix_rows": [asdict(row) for row in code_map.matrix_rows],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract code-side capability map from OpenSpec specs + alignment matrix.")
    parser.add_argument("--code-root", default="/opt/code/mi")
    parser.add_argument("--project", default="商管系统")
    parser.add_argument("--output", default="-", help="output JSON path; '-' for stdout")
    args = parser.parse_args()

    code_map = extract(Path(args.code_root), args.project)
    payload = json.dumps(_to_dict(code_map), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
