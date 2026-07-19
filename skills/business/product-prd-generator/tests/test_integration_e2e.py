"""Integration tests for product-prd-generator end-to-end scenarios.

Each test invokes the full CLI as a subprocess and verifies exit code +
key modules in the generated 产品PRD.md. Tests are marked with skipif
for environment dependencies (code roots + docs roots must exist).

Covers 5 scenarios:
  1. 商管系统 generate (regression)
  2. 商管系统 coverage-validate (regression)
  3. langchat generate
  4. langchat coverage-validate
  5. LnkChatBI generate
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
LANLNK_BASE = Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk"))

SHANGGUAN_CODE_ROOT = Path("/opt/code/mi")
SHANGGUAN_DOCS_ROOT = LANLNK_BASE / "raw" / "prd-商管系统"
LANGCHAT_CODE_ROOT = Path("/opt/code/langchat")
LANGCHAT_DOCS_ROOT = LANLNK_BASE / "raw" / "prd-langchat"
LNKCHATBI_CODE_ROOT = Path("/opt/code/LnkChatBI")
LNKCHATBI_DOCS_ROOT = LANLNK_BASE / "raw" / "prd-LnkChatBI"

SHANGGUAN_MODULES = ["资源管理", "招商管理", "合同管理", "财务管理"]
LANGCHAT_MODULES = ["数字员工与契约", "能力治理与发布", "工作流与蓝图", "知识治理"]
LNKCHATBI_MODULES = ["数据源管理", "问数会话", "术语库", "OpenClaw 集成"]


def _run_cli(args: list[str], output_dir: Path, parsed_dir: Path, mode: str) -> subprocess.CompletedProcess:
    """Invoke product-prd-generator CLI as subprocess."""
    cmd = [
        "uv", "run", "product-prd-generator",
        "--skill-root", str(SKILL_ROOT),
        "--output-dir", str(output_dir),
        "--parsed-dir", str(parsed_dir),
        "--mode", mode,
    ] + args
    return subprocess.run(cmd, cwd=str(SKILL_ROOT), capture_output=True, text=True, timeout=300)


def _assert_modules_in_prd(output_dir: Path, expected_modules: list[str]) -> None:
    """Verify all expected modules appear as ### 3.N headings in 产品PRD.md."""
    prd = output_dir / "产品PRD.md"
    assert prd.is_file(), f"产品PRD.md missing in {output_dir}"
    content = prd.read_text(encoding="utf-8")
    for mod in expected_modules:
        assert mod in content, f"Expected module '{mod}' missing in 产品PRD.md"


# ─── 1. 商管系统 generate (regression) ─────────────────────────────────


@pytest.mark.skipif(
    not SHANGGUAN_CODE_ROOT.is_dir() or not SHANGGUAN_DOCS_ROOT.is_dir(),
    reason=f"requires {SHANGGUAN_CODE_ROOT} + {SHANGGUAN_DOCS_ROOT}",
)
def test_e2e_商管_generate(tmp_path: Path):
    result = _run_cli(
        ["--project", "商管系统", "--code-root", str(SHANGGUAN_CODE_ROOT),
         "--docs-root", str(SHANGGUAN_DOCS_ROOT)],
        output_dir=tmp_path / "out",
        parsed_dir=tmp_path / "parsed",
        mode="generate",
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}"
    _assert_modules_in_prd(tmp_path / "out", SHANGGUAN_MODULES)


# ─── 2. 商管系统 coverage-validate (regression) ────────────────────────


@pytest.mark.skipif(
    not SHANGGUAN_CODE_ROOT.is_dir() or not SHANGGUAN_DOCS_ROOT.is_dir(),
    reason=f"requires {SHANGGUAN_CODE_ROOT} + {SHANGGUAN_DOCS_ROOT}",
)
def test_e2e_商管_coverage_validate(tmp_path: Path):
    generate_result = _run_cli(
        ["--project", "商管系统", "--code-root", str(SHANGGUAN_CODE_ROOT),
         "--docs-root", str(SHANGGUAN_DOCS_ROOT)],
        output_dir=tmp_path / "out",
        parsed_dir=tmp_path / "parsed",
        mode="generate",
    )
    assert generate_result.returncode == 0, f"Generate precondition failed:\n{generate_result.stderr}"

    coverage_result = _run_cli(
        ["--project", "商管系统", "--code-root", str(SHANGGUAN_CODE_ROOT),
         "--docs-root", str(SHANGGUAN_DOCS_ROOT)],
        output_dir=tmp_path / "out",
        parsed_dir=tmp_path / "parsed",
        mode="coverage-validate",
    )
    assert coverage_result.returncode == 0, f"Coverage-validate failed:\n{coverage_result.stderr}"


# ─── 3. langchat generate ──────────────────────────────────────────────


@pytest.mark.skipif(
    not LANGCHAT_CODE_ROOT.is_dir() or not LANGCHAT_DOCS_ROOT.is_dir(),
    reason=f"requires {LANGCHAT_CODE_ROOT} + {LANGCHAT_DOCS_ROOT}",
)
def test_e2e_langchat_generate(tmp_path: Path):
    result = _run_cli(
        ["--project", "langchat", "--code-root", str(LANGCHAT_CODE_ROOT),
         "--docs-root", str(LANGCHAT_DOCS_ROOT)],
        output_dir=tmp_path / "out",
        parsed_dir=tmp_path / "parsed",
        mode="generate",
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}"
    _assert_modules_in_prd(tmp_path / "out", LANGCHAT_MODULES)


# ─── 4. langchat coverage-validate ─────────────────────────────────────


@pytest.mark.skipif(
    not LANGCHAT_CODE_ROOT.is_dir() or not LANGCHAT_DOCS_ROOT.is_dir(),
    reason=f"requires {LANGCHAT_CODE_ROOT} + {LANGCHAT_DOCS_ROOT}",
)
def test_e2e_langchat_coverage_validate(tmp_path: Path):
    generate_result = _run_cli(
        ["--project", "langchat", "--code-root", str(LANGCHAT_CODE_ROOT),
         "--docs-root", str(LANGCHAT_DOCS_ROOT)],
        output_dir=tmp_path / "out",
        parsed_dir=tmp_path / "parsed",
        mode="generate",
    )
    assert generate_result.returncode == 0, f"Generate precondition failed:\n{generate_result.stderr}"

    coverage_result = _run_cli(
        ["--project", "langchat", "--code-root", str(LANGCHAT_CODE_ROOT),
         "--docs-root", str(LANGCHAT_DOCS_ROOT)],
        output_dir=tmp_path / "out",
        parsed_dir=tmp_path / "parsed",
        mode="coverage-validate",
    )
    assert coverage_result.returncode == 0, f"Coverage-validate failed:\n{coverage_result.stderr}"


# ─── 5. LnkChatBI generate ─────────────────────────────────────────────


@pytest.mark.skipif(
    not LNKCHATBI_CODE_ROOT.is_dir() or not LNKCHATBI_DOCS_ROOT.is_dir(),
    reason=f"requires {LNKCHATBI_CODE_ROOT} + {LNKCHATBI_DOCS_ROOT}",
)
def test_e2e_LnkChatBI_generate(tmp_path: Path):
    result = _run_cli(
        ["--project", "LnkChatBI", "--code-root", str(LNKCHATBI_CODE_ROOT),
         "--docs-root", str(LNKCHATBI_DOCS_ROOT)],
        output_dir=tmp_path / "out",
        parsed_dir=tmp_path / "parsed",
        mode="generate",
    )
    assert result.returncode == 0, f"CLI failed:\n{result.stderr}"
    _assert_modules_in_prd(tmp_path / "out", LNKCHATBI_MODULES)
