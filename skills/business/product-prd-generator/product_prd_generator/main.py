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


def _doc_map_args(args: argparse.Namespace, output: str) -> list[str]:
    cmd = [
        "--docs-root", args.docs_root,
        "--skill-root", args.skill_root,
        "--project", args.project,
        "--output", output,
    ]
    if args.mode == "coverage-validate":
        docs_root = Path(args.docs_root)
        extra = docs_root.parent.parent.parent / "materials" / "13-competitors"
        if extra.is_dir():
            cmd.extend(["--extra-docs-root", str(extra)])
    return cmd


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
    parser.add_argument("--mode", choices=["generate", "coverage-validate"], default="generate")
    parser.add_argument("--baseline", default="")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--customers", default="")
    parser.add_argument("--competitors", default="")
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
    if _run("product_prd_generator.doc_map", _doc_map_args(args, str(doc_map_path))) != 0:
        return 1
    if _run("product_prd_generator.reconcile", ["--code-map", str(code_map_path), "--doc-map", str(doc_map_path), "--output", str(reconcile_path)]) != 0:
        return 1

    if args.mode == "coverage-validate":
        review_dir = Path("review")
        coverage_args = [
            "--reconcile", str(reconcile_path),
            "--doc-map", str(doc_map_path),
            "--output-dir", args.output_dir,
            "--review-dir", str(review_dir),
            "--skill-root", args.skill_root,
        ]
        analysis_root = Path(args.output_dir).parent / "competitor-analysis"
        for comp_dir in sorted(analysis_root.iterdir()) if analysis_root.is_dir() else []:
            if comp_dir.is_dir() and comp_dir.glob("*capability-map.md"):
                coverage_args.extend(["--capability-map-dir", str(comp_dir)])
        if args.baseline:
            coverage_args.extend(["--baseline", args.baseline])
        if args.update_baseline:
            coverage_args.append("--update-baseline")
        if args.customers:
            coverage_args.extend(["--customers", args.customers])
        if args.competitors:
            coverage_args.extend(["--competitors", args.competitors])
        return _run("product_prd_generator.coverage_validate", coverage_args)

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
