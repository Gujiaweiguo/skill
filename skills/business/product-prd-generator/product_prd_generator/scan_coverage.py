from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from .models import ScanCoverage, ScanStatus, ScannerCoverage


class ScannerCoverageJSON(TypedDict):
    status: str
    scope: list[str]
    limitations: list[str]
    artifact_count: int


class ScannersJSON(TypedDict):
    specs: ScannerCoverageJSON
    matrix: ScannerCoverageJSON
    direct_code: ScannerCoverageJSON
    direct_tests: ScannerCoverageJSON


class ScanCoverageJSON(TypedDict):
    status: str
    scope: list[str]
    limitations: list[str]
    scanners: ScannersJSON


def build_scan_coverage(
    code_root: Path,
    specs_root: Path,
    matrix_path: Path | None,
    spec_count: int,
    matrix_count: int,
    direct_code: ScannerCoverage | None = None,
    direct_tests: ScannerCoverage | None = None,
) -> ScanCoverage:
    specs_exists = specs_root.is_dir()
    specs = ScannerCoverage(
        status=ScanStatus.COMPLETE if specs_exists else ScanStatus.INACCESSIBLE,
        scope=(str(specs_root.relative_to(code_root)), "*/spec.md"),
        limitations=() if specs_exists else ("Configured OpenSpec specs root does not exist.",),
        artifact_count=spec_count,
    )

    if matrix_path is None:
        matrix = ScannerCoverage(
            status=ScanStatus.NOT_SCANNED,
            scope=("matrix disabled by code-map rules",),
            limitations=("No matrix scanner ran because matrix.enabled is false.",),
        )
    elif matrix_path.is_file():
        matrix = ScannerCoverage(
            status=ScanStatus.COMPLETE,
            scope=(str(matrix_path.relative_to(code_root)),),
            artifact_count=matrix_count,
        )
    else:
        matrix = ScannerCoverage(
            status=ScanStatus.NOT_SCANNED,
            scope=(str(matrix_path.relative_to(code_root)),),
            limitations=("Configured matrix file does not exist; no matrix rows were scanned.",),
            artifact_count=matrix_count,
        )

    direct_code = direct_code or ScannerCoverage(
        status=ScanStatus.NOT_SCANNED,
        scope=("runtime source code",),
        limitations=("No direct runtime code scanner is enabled.",),
    )
    direct_tests = direct_tests or ScannerCoverage(
        status=ScanStatus.NOT_SCANNED,
        scope=("test files and test execution",),
        limitations=("No direct test scanner or test execution is enabled.",),
    )
    return ScanCoverage(
        status=(
            ScanStatus.PARTIAL
            if direct_code.status is not ScanStatus.COMPLETE
            or direct_tests.status is not ScanStatus.COMPLETE
            else ScanStatus.INACCESSIBLE
            if not specs_exists
            else ScanStatus.COMPLETE
        ),
        scope=("configured OpenSpec specs", "configured alignment matrix", "direct runtime code", "direct tests"),
        limitations=("Direct runtime code and test evidence are not scanned.",),
        specs=specs,
        matrix=matrix,
        direct_code=direct_code,
        direct_tests=direct_tests,
    )


def scan_coverage_to_json(coverage: ScanCoverage) -> ScanCoverageJSON:
    def serialize_scanner(scanner: ScannerCoverage) -> ScannerCoverageJSON:
        return {
            "status": scanner.status.value,
            "scope": list(scanner.scope),
            "limitations": list(scanner.limitations),
            "artifact_count": scanner.artifact_count,
        }

    return {
        "status": coverage.status.value,
        "scope": list(coverage.scope),
        "limitations": list(coverage.limitations),
        "scanners": {
            "specs": serialize_scanner(coverage.specs),
            "matrix": serialize_scanner(coverage.matrix),
            "direct_code": serialize_scanner(coverage.direct_code),
            "direct_tests": serialize_scanner(coverage.direct_tests),
        },
    }
