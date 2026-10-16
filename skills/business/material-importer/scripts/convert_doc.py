#!/usr/bin/env python3
"""溯源携带的 markitdown 包装器（pptx/docx/pdf → Markdown）。

背景：P0「原件为源契约」要求每个派生产物携带 provenance；裸
`uv run markitdown file > raw/x.md` 产出无溯源的裸 md。本脚本补上：
  1. 从输入文件向上找 config/company.yaml → 源记录为 base 相对 posix 路径；
     找不到则记绝对路径。
  2. sha256 源文件。
  3. 跑 markitdown（skill venv），失败打印 stderr 并 exit 1，不写部分产物。
  4. pptx 额外跑 pptx_table_guard.py detect，命中写 pptx_suspects 行
     （无命中写 pptx_suspects: none）；docx/pdf 无此行。
  5. 输出 = provenance 注释块 + 转换内容；覆盖已有输出允许（重提取幂等）。

用法：uv run scripts/convert_doc.py <input.(pptx|docx|pdf)> <output.md>
（非 PEP 723 独立脚本 —— markitdown 在 skill venv pyproject 里。）
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

EXTRACTOR_VERSION = 1
FIDELITY = "text=high; structure=variable (pptx 合并表格不可靠 — 见 pptx_table_guard)"
SKILL_DIR = Path(__file__).resolve().parent.parent


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_source_relpath(path: Path) -> str:
    """向上找 config/company.yaml；命中 → base 相对 posix 路径，否则绝对路径。"""
    for parent in path.resolve().parents:
        if (parent / "config" / "company.yaml").is_file():
            try:
                return path.resolve().relative_to(parent).as_posix()
            except ValueError:
                break
    return str(path.resolve())


def run_markitdown(src: Path) -> str:
    proc = subprocess.run(
        ["uv", "run", "markitdown", str(src)],
        cwd=str(SKILL_DIR),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"markitdown failed (rc={proc.returncode}):\n{proc.stderr}", file=sys.stderr)
        raise SystemExit(1)
    return proc.stdout


def detect_pptx_suspects(src: Path) -> list[dict]:
    """返回 findings 列表（suspects）。guard 恒 exit 0；异常按无命中处理。"""
    proc = subprocess.run(
        ["uv", "run", "scripts/pptx_table_guard.py", "detect", str(src), "--json"],
        cwd=str(SKILL_DIR),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"warning: pptx_table_guard detect failed — treating as no suspects", file=sys.stderr)
        return []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    suspects: list[dict] = []
    for res in data.get("suspects", []):
        for f in res.get("findings", []):
            suspects.append(f)
    return suspects


def render_suspects_line(suspects: list[dict]) -> str:
    if not suspects:
        return "pptx_suspects: none"
    parts = [
        f"slide {f['slide']} ({', '.join(f['reasons'])})"
        for f in suspects
    ]
    return "pptx_suspects: " + ", ".join(parts)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"用法: {argv[0]} <input.(pptx|docx|pdf)> <output.md>", file=sys.stderr)
        return 2
    src = Path(argv[0]).resolve()
    out = Path(argv[1])
    if not src.is_file():
        print(f"error: not found: {src}", file=sys.stderr)
        return 2
    suffix = src.suffix.lower()
    if suffix not in (".pptx", ".docx", ".pdf"):
        print(f"error: unsupported suffix {suffix!r} (expect .pptx/.docx/.pdf)", file=sys.stderr)
        return 2

    # markitdown 对垃圾字节可能按纯文本 rc=0 输出（实测），先做魔数校验拦截
    magic = src.open("rb").read(5)
    if suffix in (".pptx", ".docx") and not magic.startswith(b"PK"):
        print(f"error: {src} is not a valid OOXML (zip) file — refusing to convert", file=sys.stderr)
        return 1
    if suffix == ".pdf" and magic != b"%PDF-":
        print(f"error: {src} is not a valid PDF file — refusing to convert", file=sys.stderr)
        return 1

    source_rel = resolve_source_relpath(src)
    sha = file_sha256(src)

    content = run_markitdown(src)  # 失败即 exit 1，不写部分产物

    suspects: list[dict] = []
    if suffix == ".pptx":
        suspects = detect_pptx_suspects(src)

    header_lines = [
        f"<!-- source: {source_rel} -->",
        f"<!-- source_sha256: {sha} -->",
        f"<!-- extracted_by: markitdown via convert_doc.py v{EXTRACTOR_VERSION} ({date.today().isoformat()}) -->",
        f"<!-- fidelity: {FIDELITY} -->",
    ]
    if suffix == ".pptx":
        header_lines.append(f"<!-- {render_suspects_line(suspects)} -->")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(header_lines) + "\n" + content, encoding="utf-8")

    n = len(suspects)
    print(
        f"ok: source={source_rel} sha256={sha[:8]} "
        f"out={out} ({out.stat().st_size} bytes)"
        + (f" suspects={n}" if suffix == ".pptx" else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
