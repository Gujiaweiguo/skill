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


# 顶层 limitations 如实反映 direct 扫描器是否真的扫过（2026-11-27）。此前恒为
# “Direct runtime code and test evidence are not scanned.”——direct_code / direct_tests
# 显式启用并扫完后（lnkcard 2026-11-01 起）这句话不成立。两个扫描器都没扫过时
# 沿用既有文案（存量产物与测试 fixture 不变）；只要有一个扫过，就不再声称
# not scanned，并保留真实限制：静态源码/测试文件证据不等于运行时验证或测试执行。
_LEGACY_NOT_SCANNED = "Direct runtime code and test evidence are not scanned."
_CODE_NOT_SCANNED = "Direct runtime code evidence is not scanned."
_TESTS_NOT_SCANNED = "Direct test evidence is not scanned."
_STATIC_EVIDENCE_CAVEAT = (
    "Direct evidence is static source/test-file scanning only; "
    "it is not runtime verification or test execution."
)


def _actually_scanned(scanner: ScannerCoverage) -> bool:
    return scanner.status in (ScanStatus.COMPLETE, ScanStatus.PARTIAL)


def _top_level_limitations(
    direct_code: ScannerCoverage, direct_tests: ScannerCoverage
) -> tuple[str, ...]:
    code_scanned = _actually_scanned(direct_code)
    tests_scanned = _actually_scanned(direct_tests)
    if not code_scanned and not tests_scanned:
        return (_LEGACY_NOT_SCANNED,)
    limitations: list[str] = []
    if not code_scanned:
        limitations.append(_CODE_NOT_SCANNED)
    if not tests_scanned:
        limitations.append(_TESTS_NOT_SCANNED)
    limitations.append(_STATIC_EVIDENCE_CAVEAT)
    return tuple(limitations)


def build_scan_coverage(
    code_root: Path,
    specs_root: Path,
    matrix_path: Path | None,
    spec_count: int,
    matrix_count: int,
    direct_code: ScannerCoverage | None = None,
    direct_tests: ScannerCoverage | None = None,
    excluded_spec_count: int = 0,
) -> ScanCoverage:
    specs_exists = specs_root.is_dir()
    # 空基线显式化（2026-10-26 lnkcard 实证）：specs 目录存在但零 spec scope 时，
    # 扫描已执行（status=complete）但必须携带 empty-baseline limitation + artifact_count=0，
    # 不得让下游把空集读成"已验证的完整实现基线"。
    specs_limitations: tuple[str, ...] = ()
    if not specs_exists:
        specs_limitations = ("Configured OpenSpec specs root does not exist.",)
    elif spec_count == 0 and excluded_spec_count:
        # 技术骨架基线（2026-11-23 lnkretail）：specs 目录里只有被规则文件排除的技术骨架 scope，
        # 业务基线为空。仍属 empty-baseline 语义（下游按 present-unconfirmed 播种本体能力，不得记为
        # missing），但原因必须如实说明，并带 technical-only 标记供措辞区分。
        specs_limitations = (
            f"OpenSpec specs root contains only {excluded_spec_count} spec scope(s) excluded by code-map "
            "rules as technical-only (non-business); the business baseline is empty "
            "(empty baseline; no business code capability claims).",
        )
    elif spec_count == 0:
        specs_limitations = (
            "OpenSpec specs root exists but contains no spec scopes (empty baseline; no code capability claims).",
        )
    elif excluded_spec_count:
        specs_limitations = (
            f"{excluded_spec_count} technical-only spec scope(s) excluded by code-map rules from the business baseline.",
        )
    specs = ScannerCoverage(
        status=ScanStatus.COMPLETE if specs_exists else ScanStatus.INACCESSIBLE,
        scope=(str(specs_root.relative_to(code_root)), "*/spec.md"),
        limitations=specs_limitations,
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
        limitations=_top_level_limitations(direct_code, direct_tests),
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
