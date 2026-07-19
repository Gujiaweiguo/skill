from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from enum import Enum, unique
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .models import CapabilityId, CapabilityStatus, CodeCapability, CodeMap, EvidenceKind, EvidenceRef, MatrixRow, Priority


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
_PRIORITY_BY_LABEL = {"P0": Priority.P0, "P1": Priority.P1, "P2": Priority.P2, "P3": Priority.P3}

_LEGACY_RULES: dict[str, Any] = {
    "project": "商管系统",
    "description": "Legacy hardcoded rules (pre-Phase-B). Used when project-specific yaml missing.",
    "specs": {"path": "openspec/specs"},
    "matrix": {
        "enabled": True,
        "path": "artifacts/alignment/product-definition-matrix.md",
    },
    "future_scanners": {},
    "exclude_paths": [],
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


def _parse_spec(spec_path: Path, project_root: Path) -> CodeCapability:
    text = spec_path.read_text(encoding="utf-8")
    purpose = _parse_purpose(text)
    requirement_count = len(_SPEC_HEADING.findall(text))
    status = _parse_status(purpose)
    rel_path = str(spec_path.relative_to(project_root))
    return CodeCapability(
        id=CapabilityId(spec_path.parent.name),
        name=spec_path.parent.name.replace("-", " "),
        status=status,
        spec_path=rel_path,
        purpose=purpose,
        requirement_count=requirement_count,
        evidence=(EvidenceRef(kind=EvidenceKind.SPEC, ref=rel_path),),
    )


def _iter_spec_capabilities(specs_root: Path, project_root: Path) -> tuple[CodeCapability, ...]:
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
        id=CapabilityId(raw_id),
        function_point=function_point,
        manual_ref=manual_ref,
        spec_mapping=spec_mapping,
        mi_status=status,
        landing_point=landing,
        classification=classification,
        disposition=disposition,
        priority=prio,
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


def _load_code_map_rules(project: str, skill_root: Path | None) -> dict[str, Any]:
    """Load project-specific code-map scanning rules.

    Returns dict with keys: project, description, specs, matrix, future_scanners, exclude_paths.
    Falls back to ``_LEGACY_RULES`` (商管 hardcoded defaults) when:
      - skill_root is None, OR
      - ``<skill_root>/references/code-map-rules-<project>.yaml`` does not exist, OR
      - yaml parsing fails

    Legacy fallback preserves byte-identical behavior to pre-Phase-B code_map.
    """
    if skill_root is None:
        return dict(_LEGACY_RULES)
    yaml_path = skill_root / "references" / f"code-map-rules-{project}.yaml"
    if not yaml_path.is_file():
        return dict(_LEGACY_RULES)
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return dict(_LEGACY_RULES)
    if not isinstance(data, dict):
        return dict(_LEGACY_RULES)
    data.setdefault("project", project)
    data.setdefault("description", "")
    data.setdefault("specs", {"path": "openspec/specs"})
    data.setdefault("matrix", {"enabled": True, "path": "artifacts/alignment/product-definition-matrix.md"})
    data.setdefault("future_scanners", {})
    data.setdefault("exclude_paths", [])
    return data


def extract(
    code_root: Path,
    project: str = "商管系统",
    skill_root: Path | None = None,
) -> CodeMap:
    rules = _load_code_map_rules(project, skill_root)
    specs_root = code_root / rules["specs"]["path"]
    matrix_cfg = rules.get("matrix", {})
    matrix_rows: tuple[MatrixRow, ...] = ()
    if matrix_cfg.get("enabled", True):
        matrix_path = code_root / matrix_cfg.get(
            "path", "artifacts/alignment/product-definition-matrix.md"
        )
        matrix_rows = _iter_matrix_rows(matrix_path)
    return CodeMap(
        project=project,
        source_path=str(code_root),
        commit_sha=_git_head_sha(str(code_root)),
        spec_capabilities=_iter_spec_capabilities(specs_root, code_root),
        matrix_rows=matrix_rows,
    )


def to_json(code_map: CodeMap) -> dict[str, object]:
    return {
        "project": code_map.project,
        "source_path": code_map.source_path,
        "commit_sha": code_map.commit_sha,
        "spec_capabilities": [
            {
                "id": cap.id,
                "name": cap.name,
                "status": cap.status.value,
                "spec_path": cap.spec_path,
                "purpose": cap.purpose,
                "requirement_count": cap.requirement_count,
                "evidence": [{"kind": e.kind.value, "ref": e.ref, "note": e.note} for e in cap.evidence],
            }
            for cap in code_map.spec_capabilities
        ],
        "matrix_rows": [
            {
                "id": row.id,
                "function_point": row.function_point,
                "manual_ref": row.manual_ref,
                "spec_mapping": row.spec_mapping,
                "mi_status": row.mi_status.value,
                "landing_point": row.landing_point,
                "classification": row.classification,
                "disposition": row.disposition,
                "priority": row.priority.value,
            }
            for row in code_map.matrix_rows
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract code-side capability map from OpenSpec specs + alignment matrix.")
    parser.add_argument("--code-root", default="/opt/code/mi")
    parser.add_argument("--project", default="商管系统")
    parser.add_argument("--skill-root", default="")
    parser.add_argument("--output", default="-")
    args = parser.parse_args()

    skill_root = Path(args.skill_root) if args.skill_root else None
    code_map = extract(Path(args.code_root), args.project, skill_root=skill_root)
    payload = json.dumps(to_json(code_map), ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
