from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .word_export import build_content_package, render_docx


def _run(module: str, extra_args: list[str]) -> int:
    cmd = [sys.executable, "-m", module, *extra_args]
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="product-prd-generator")
    parser.add_argument("--project", default="商管系统")
    parser.add_argument("--code-root", default="/opt/code/mi")
    parser.add_argument("--docs-root", default=str(Path.cwd()))
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--parsed-dir", default="parsed")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--word-master-root", default=str(Path(__file__).resolve().parents[3] / "word" / "word-master"))
    parser.add_argument("--docx-output", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    parsed_dir = Path(args.parsed_dir)
    parsed_dir.mkdir(parents=True, exist_ok=True)

    code_map_path = parsed_dir / "current-code-map.json"
    doc_map_path = parsed_dir / "current-doc-map.json"
    reconcile_path = parsed_dir / "capability-reconciliation.json"

    if _run("product_prd_generator.code_map", ["--code-root", args.code_root, "--project", args.project, "--output", str(code_map_path)]) != 0:
        return 1
    if _run("product_prd_generator.doc_map", ["--docs-root", args.docs_root, "--skill-root", args.skill_root, "--project", args.project, "--output", str(doc_map_path)]) != 0:
        return 1
    if _run("product_prd_generator.reconcile", ["--code-map", str(code_map_path), "--doc-map", str(doc_map_path), "--output", str(reconcile_path)]) != 0:
        return 1
    if _run("product_prd_generator.render", ["--reconcile", str(reconcile_path), "--doc-map", str(doc_map_path), "--docs-root", args.docs_root, "--output-dir", args.output_dir]) != 0:
        return 1

    content_package_path = build_content_package(reconcile_path, doc_map_path, args.output_dir, args.docs_root)
    if args.docx_output:
        render_docx(content_package_path, args.docx_output, args.word_master_root)

    review_dir = Path("review")
    review_dir.mkdir(parents=True, exist_ok=True)
    return _run("product_prd_generator.review", ["--reconcile", str(reconcile_path), "--output-dir", str(review_dir)])


if __name__ == "__main__":
    raise SystemExit(main())
