from __future__ import annotations

import fnmatch
import hashlib
import ast
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

from .models import EvidenceKind, EvidenceRef, ScanStatus, ScannerCoverage


class EvidenceRole(str, Enum):
    IMPORT = "import"
    DECLARATION = "declaration"
    FIXTURE = "fixture"
    ASSERTION = "assertion"
    MAPPING = "mapping"
    OTHER = "other"


@dataclass(frozen=True, slots=True)
class DirectEvidenceMatch:
    capability_id: str
    spec_capability_id: str
    kind: str
    ref: str
    term: str
    evidence_id: str
    role: EvidenceRole

    def to_evidence_ref(self) -> EvidenceRef:
        if self.kind == EvidenceKind.CODE.value:
            note = "static source match; runtime not verified"
        else:
            note = "test-file match; test execution not verified"
        return EvidenceRef(
            kind=self.kind,
            ref=self.ref,
            note=(
                f"{note}; role={self.role.value}; capability_id={self.capability_id}; "
                f"evidence_id={self.evidence_id}"
            ),
        )


@dataclass(frozen=True, slots=True)
class DirectEvidenceScan:
    code: ScannerCoverage
    tests: ScannerCoverage
    matches: tuple[DirectEvidenceMatch, ...] = ()

    def evidence_for(self, capability_id: str) -> tuple[EvidenceRef, ...]:
        return tuple(
            match.to_evidence_ref()
            for match in self.matches
            if match.capability_id == capability_id
        )

    def to_json(self) -> dict[str, object]:
        return {
            "matches": [
                {
                    "capability_id": match.capability_id,
                    "spec_capability_id": match.spec_capability_id,
                    "kind": match.kind,
                    "ref": match.ref,
                    "term": match.term,
                    "evidence_id": match.evidence_id,
                    "role": match.role.value,
                }
                for match in self.matches
            ],
            "code": {
                "status": self.code.status.value,
                "scope": list(self.code.scope),
                "limitations": list(self.code.limitations),
                "artifact_count": self.code.artifact_count,
            },
            "tests": {
                "status": self.tests.status.value,
                "scope": list(self.tests.scope),
                "limitations": list(self.tests.limitations),
                "artifact_count": self.tests.artifact_count,
            },
        }


def _as_strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str) and item)


def _matches_pattern(relative_path: str, pattern: str) -> bool:
    if fnmatch.fnmatchcase(relative_path, pattern) or Path(relative_path).match(pattern):
        return True
    if "**/" in pattern:
        return fnmatch.fnmatchcase(relative_path, pattern.replace("**/", "")) or fnmatch.fnmatchcase(
            relative_path, pattern.replace("**/", "*/")
        )
    return False


def _excluded(relative_path: str, patterns: tuple[str, ...]) -> bool:
    return any(_matches_pattern(relative_path, pattern) for pattern in patterns)


def _configured_roots(code_root: Path, patterns: tuple[str, ...]) -> tuple[Path, ...]:
    roots: set[Path] = set()
    for pattern in patterns:
        literal = pattern.split("*", 1)[0].rstrip("/")
        if literal:
            roots.add(code_root / literal)
    return tuple(sorted(roots))


def _files_for_patterns(
    code_root: Path,
    include_patterns: tuple[str, ...],
    extensions: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
) -> tuple[Path, ...]:
    roots = _configured_roots(code_root, include_patterns)
    files: set[Path] = set()
    for root in roots:
        if root.is_file():
            candidates = (root,)
        elif root.is_dir():
            candidates = root.rglob("*")
        else:
            continue
        for path in candidates:
            if not path.is_file() or path.suffix not in extensions:
                continue
            relative = path.relative_to(code_root).as_posix()
            if any(_matches_pattern(relative, pattern) for pattern in include_patterns) and not _excluded(relative, exclude_patterns):
                files.add(path)
    return tuple(sorted(files, key=lambda path: path.relative_to(code_root).as_posix()))


def _line_roles(source: str, kind: EvidenceKind) -> dict[int, EvidenceRole]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    roles: dict[int, EvidenceRole] = {}

    def mark(node: ast.AST, role: EvidenceRole) -> None:
        start = getattr(node, "lineno", None)
        end = getattr(node, "end_lineno", start)
        if not isinstance(start, int) or not isinstance(end, int):
            return
        for line_number in range(start, end + 1):
            roles.setdefault(line_number, role)

    def visit(node: ast.AST, context: tuple[str, ...] = ()) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name.casefold()
            nested_context = (*context, name)
            definition_line = getattr(node, "lineno", None)
            if name.startswith(("dummy", "fake", "mock")) or "fixture" in name:
                if isinstance(definition_line, int):
                    roles.setdefault(definition_line, EvidenceRole.FIXTURE)
            else:
                if isinstance(definition_line, int):
                    roles.setdefault(definition_line, EvidenceRole.DECLARATION)
            for child in ast.iter_child_nodes(node):
                visit(child, nested_context)
            return
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mark(node, EvidenceRole.IMPORT)
        elif kind is EvidenceKind.TEST and isinstance(node, ast.Assert):
            mark(node, EvidenceRole.ASSERTION)
        elif isinstance(node, ast.Return) and "get_provider_capabilities" in context:
            mark(node, EvidenceRole.MAPPING)
        elif isinstance(node, (ast.AnnAssign, ast.Assign, ast.NamedExpr)):
            targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
            target_names = tuple(
                target.id.casefold()
                for target in targets
                if isinstance(target, ast.Name)
            )
            if any(
                part.startswith(("dummy", "fake", "mock")) or "fixture" in part
                for part in (*context, *target_names)
            ):
                mark(node, EvidenceRole.FIXTURE)
            elif kind is EvidenceKind.TEST and any(part.startswith("test_") for part in context):
                mark(node, EvidenceRole.ASSERTION)
            elif "get_provider_capabilities" in context:
                mark(node, EvidenceRole.MAPPING)
            else:
                mark(node, EvidenceRole.DECLARATION)
        elif isinstance(node, ast.Call) and "get_provider_capabilities" in context:
            mark(node, EvidenceRole.MAPPING)
        for child in ast.iter_child_nodes(node):
            visit(child, context)

    visit(tree)
    return roles


def _scan_surface(
    code_root: Path,
    config: object,
    global_excludes: tuple[str, ...],
    kind: EvidenceKind,
) -> tuple[ScannerCoverage, tuple[DirectEvidenceMatch, ...]]:
    if not isinstance(config, Mapping) or not config.get("enabled", False):
        return (
            ScannerCoverage(
                status=ScanStatus.NOT_SCANNED,
                scope=(f"direct {kind.value} evidence",),
                limitations=(f"No direct {kind.value} scanner is enabled.",),
            ),
            (),
        )

    include_patterns = _as_strings(config.get("include_paths"))
    extensions = _as_strings(config.get("extensions"))
    local_excludes = _as_strings(config.get("exclude_paths"))
    excludes = global_excludes + local_excludes
    capabilities = config.get("capabilities", {})
    if not isinstance(capabilities, Mapping):
        capabilities = {}
    spec_anchors = config.get("spec_anchors", {})
    if not isinstance(spec_anchors, Mapping):
        spec_anchors = {}

    roots = _configured_roots(code_root, include_patterns)
    if not include_patterns or not any(root.exists() for root in roots):
        return (
            ScannerCoverage(
                status=ScanStatus.INACCESSIBLE,
                scope=include_patterns or (f"direct {kind.value} evidence",),
                limitations=("Configured direct evidence root does not exist.",),
            ),
            (),
        )

    matches: list[DirectEvidenceMatch] = []
    errors: list[str] = []
    files = _files_for_patterns(code_root, include_patterns, extensions, excludes)
    for path in files:
        relative = path.relative_to(code_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
            lines = source.splitlines()
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative}: {type(exc).__name__}")
            continue
        line_roles = _line_roles(source, kind)
        for line_number, line in enumerate(lines, 1):
            lowered = line.casefold()
            for raw_capability_id, raw_terms in capabilities.items():
                capability_id = str(raw_capability_id)
                terms = _as_strings(raw_terms)
                for term in terms:
                    if term.casefold() not in lowered:
                        continue
                    ref = f"{relative}:{line_number}"
                    identity = f"{kind.value}|{capability_id}|{ref}|{term.casefold()}"
                    evidence_id = hashlib.sha256(identity.encode()).hexdigest()[:16]
                    matches.append(
                        DirectEvidenceMatch(
                            capability_id=capability_id,
                            spec_capability_id=str(spec_anchors.get(capability_id, "")),
                            kind=kind.value,
                            ref=ref,
                            term=term,
                            evidence_id=evidence_id,
                            role=line_roles.get(line_number, EvidenceRole.OTHER),
                        )
                    )

    matches.sort(key=lambda item: (item.capability_id, item.ref, item.term.casefold(), item.evidence_id))
    coverage = ScannerCoverage(
        status=ScanStatus.PARTIAL if errors else ScanStatus.COMPLETE,
        scope=include_patterns,
        limitations=tuple(f"Unable to read {error}." for error in errors),
        artifact_count=len(files),
    )
    return coverage, tuple(matches)


def scan_direct_evidence(code_root: Path, rules: Mapping[str, object]) -> DirectEvidenceScan:
    global_excludes = _as_strings(rules.get("exclude_paths"))
    code_coverage, code_matches = _scan_surface(
        code_root, rules.get("direct_code"), global_excludes, EvidenceKind.CODE
    )
    test_coverage, test_matches = _scan_surface(
        code_root, rules.get("direct_tests"), global_excludes, EvidenceKind.TEST
    )
    return DirectEvidenceScan(
        code=code_coverage,
        tests=test_coverage,
        matches=tuple(sorted(code_matches + test_matches, key=lambda item: (item.kind, item.capability_id, item.ref, item.evidence_id))),
    )
