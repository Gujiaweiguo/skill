from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .word_export import build_content_package, render_docx
from ._paths import (
    MissingProductDataError,
    competitor_evidence_paths_for_project,
    default_output_paths,
    output_dir_for_project,
    resolve_code_root,
    validate_project,
)


def _run(module: str, extra_args: list[str]) -> int:
    cmd = [sys.executable, "-m", module, *extra_args]
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def _competitor_capability_dirs(project: str, output_dir: str) -> list[Path]:
    """竞品能力矩阵目录：canonical evidence/competitors 优先，legacy mi-cre
    competitor-analysis 迁移期只读兼容，最后兜底 <output_dir>/competitor-analysis。"""
    canonical_root, legacy_root = competitor_evidence_paths_for_project(project)
    roots = [canonical_root, legacy_root, Path(output_dir) / "competitor-analysis"]
    dirs: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root is None or not root.is_dir():
            continue
        for comp_dir in sorted(root.iterdir()):
            resolved = comp_dir.resolve()
            if resolved in seen or not comp_dir.is_dir():
                continue
            seen.add(resolved)
            if comp_dir.glob("*capability-map.md"):
                dirs.append(comp_dir)
    return dirs


def _doc_map_args(args: argparse.Namespace, output: str) -> list[str]:
    cmd = [
        "--docs-root", args.docs_root,
        "--skill-root", args.skill_root,
        "--project", args.project,
        "--output", output,
    ]
    if args.mode == "coverage-validate":
        if args.competitors_root:
            extra = Path(args.competitors_root)
        else:
            docs_root = Path(args.docs_root)
            extra = docs_root.parent.parent.parent / "materials" / "13-competitors"
        if extra.is_dir():
            cmd.extend(["--extra-docs-root", str(extra)])
    for spec in args.exclude_dir or []:
        cmd.extend(["--exclude-dir", spec])
    for pattern in getattr(args, "exclude_source", None) or []:
        cmd.extend(["--exclude-source", pattern])
    return cmd


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="product-prd-generator")
    parser.add_argument("--project", default="商管系统", type=validate_project)
    parser.add_argument("--code-root", default="")
    parser.add_argument("--docs-root", default="")
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--parsed-dir", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--canonical-target", action="store_true")
    parser.add_argument("--output-kind", choices=["baseline", "increments", "requirements", "decisions", "handoffs"], default="baseline")
    parser.add_argument("--word-master-root", default=str(Path(__file__).resolve().parents[3] / "word" / "word-master"))
    parser.add_argument("--docx-output", default="")
    parser.add_argument("--mode", choices=["generate", "coverage-validate"], default="generate")
    parser.add_argument("--baseline", default="")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--customers", default="")
    parser.add_argument("--competitors", default="")
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory prefix (relative to docs-root) or bare dir name excluded from generate doc scan. Repeatable.",
    )
    parser.add_argument(
        "--exclude-source",
        action="append",
        default=[],
        help="Glob pattern relative to docs-root excluding flat files (e.g. document-batch-01/百丽*.md) from doc scan. Repeatable.",
    )
    parser.add_argument(
        "--competitors-root",
        default="",
        help=(
            "Competitor materials root for coverage-validate extra-docs-root. "
            "Default empty: legacy three-hop path <docs-root>/../../../materials/13-competitors/ "
            "(商管系统 convention). Set explicitly for non-商管 projects."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        _, default_parsed, default_docs, default_review = default_output_paths(args.project)
        code_root = resolve_code_root(args.project, args.code_root)
    except MissingProductDataError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    requested_output_dir = args.output_dir
    args.output_dir = str(output_dir_for_project(args.project, requested_output_dir, args.canonical_target, args.output_kind))
    args.parsed_dir = args.parsed_dir or str(default_parsed)
    args.docs_root = args.docs_root or str(default_docs)
    args.code_root = str(code_root)
    parsed_dir = Path(args.parsed_dir)
    parsed_dir.mkdir(parents=True, exist_ok=True)

    code_map_path = parsed_dir / "current-code-map.json"
    doc_map_path = parsed_dir / "current-doc-map.json"
    reconcile_path = parsed_dir / "capability-reconciliation.json"

    if _run("product_prd_generator.code_map", ["--code-root", args.code_root, "--project", args.project, "--skill-root", args.skill_root, "--output", str(code_map_path)]) != 0:
        return 1
    if _run("product_prd_generator.doc_map", _doc_map_args(args, str(doc_map_path))) != 0:
        return 1
    if _run("product_prd_generator.reconcile", ["--code-map", str(code_map_path), "--doc-map", str(doc_map_path), "--output", str(reconcile_path)]) != 0:
        return 1

    review_dir = Path(args.output_dir).parent / "review"
    if not requested_output_dir and not args.canonical_target:
        review_dir = default_review

    if args.mode == "coverage-validate":
        coverage_args = [
            "--reconcile", str(reconcile_path),
            "--doc-map", str(doc_map_path),
            "--output-dir", args.output_dir,
            "--review-dir", str(review_dir),
            "--skill-root", args.skill_root,
            "--project", args.project,
        ]
        for comp_dir in _competitor_capability_dirs(args.project, args.output_dir):
            coverage_args.extend(["--capability-map-dir", str(comp_dir)])
        if args.baseline:
            coverage_args.extend(["--baseline", args.baseline])
        if args.update_baseline:
            coverage_args.append("--update-baseline")
        if args.customers:
            coverage_args.extend(["--customers", args.customers])
        if args.competitors:
            coverage_args.extend(["--competitors", args.competitors])
        if _run("product_prd_generator.coverage_validate", coverage_args) != 0:
            return 1
        return 0

    if _run(
        "product_prd_generator.render",
        [
            "--reconcile", str(reconcile_path),
            "--doc-map", str(doc_map_path),
            "--docs-root", args.docs_root,
            "--output-dir", args.output_dir,
            "--project", args.project,
            "--code-root", args.code_root,
        ],
    ) != 0:
        return 1

    content_package_path = build_content_package(reconcile_path, doc_map_path, args.output_dir, args.docs_root)
    try:
        import json
        reconcile_data = json.loads(reconcile_path.read_text(encoding="utf-8"))
        capabilities = reconcile_data.get("capabilities", [])
        code_map_data = json.loads(code_map_path.read_text(encoding="utf-8"))
        specs_scan = code_map_data.get("scan_coverage", {}).get("scanners", {}).get("specs", {})
        baseline_unavailable = (
            isinstance(specs_scan, dict)
            and int(specs_scan.get("artifact_count", 0) or 0) == 0
            and specs_scan.get("status") in {"inaccessible", "not-scanned"}
        )
        manifest_lines = [
            "# Generation Manifest",
            "",
            f"- project: `{args.project}`",
            f"- docs_root: `{Path(args.docs_root).resolve()}`",
            f"- code_root: `{Path(args.code_root).resolve()}`",
            f"- baseline_status: `{'baseline-unavailable' if baseline_unavailable else 'scanned'}`",
            f"- capability_count: {len(capabilities)}",
            f"- present_unconfirmed: {sum(1 for item in capabilities if isinstance(item, dict) and item.get('reconciled_status') == 'present-unconfirmed')}",
            f"- exclude_dir: {', '.join(f'`{item}`' for item in (args.exclude_dir or [])) or '(none)' }",
            f"- exclude_source: {', '.join(f'`{item}`' for item in (args.exclude_source or [])) or '(none)' }",
            "- source_policy: historical/reference inputs are not authorized product requirements unless explicitly classified as customer-requirements or owner-decisions",
            "",
        ]
        (Path(args.output_dir) / "generation-manifest.md").write_text("\n".join(manifest_lines), encoding="utf-8")
    except (OSError, ValueError, TypeError):
        print("warning: could not write generation-manifest.md", file=sys.stderr)
    if args.docx_output:
        render_docx(content_package_path, args.docx_output, args.word_master_root)

    review_dir.mkdir(parents=True, exist_ok=True)
    return _run("product_prd_generator.review", ["--reconcile", str(reconcile_path), "--output-dir", str(review_dir)])


if __name__ == "__main__":
    raise SystemExit(main())
