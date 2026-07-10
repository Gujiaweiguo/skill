#!/usr/bin/env python3
"""Scan OpenSpec scopes in a repository.

The script is intentionally small and stdlib-only. It does not decide whether a
change is correct; it gives the agent a reliable inventory to reason from.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "vendor",
    "__pycache__",
}


def discover_scopes(root: Path) -> list[Path]:
    scopes: set[Path] = set()

    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        path = Path(current)

        if ".openspec.yaml" in filenames:
            scopes.add(path)

        if "openspec" in dirnames:
            openspec_dir = path / "openspec"
            if (openspec_dir / "specs").exists() or (openspec_dir / "changes").exists():
                scopes.add(path)
                dirnames.remove("openspec")

    return sorted(scopes, key=lambda p: (len(p.relative_to(root).parts), str(p)))


def count_unchecked_tasks(tasks_file: Path) -> int:
    try:
        return sum(1 for line in tasks_file.read_text(encoding="utf-8").splitlines() if line.lstrip().startswith("- [ ]"))
    except UnicodeDecodeError:
        return 0


def scan_scope(scope: Path) -> dict[str, Any]:
    openspec = scope / "openspec"
    specs_dir = openspec / "specs"
    changes_dir = openspec / "changes"
    archive_dir = changes_dir / "archive"

    specs = sorted(p for p in specs_dir.glob("*/spec.md") if p.is_file()) if specs_dir.exists() else []
    active_changes = (
        sorted(p for p in changes_dir.iterdir() if p.is_dir() and p.name != "archive")
        if changes_dir.exists()
        else []
    )
    archived_changes = (
        sorted(p for p in archive_dir.iterdir() if p.is_dir())
        if archive_dir.exists()
        else []
    )

    stale_files: list[dict[str, Any]] = []
    stale_total = 0
    for tasks_file in archive_dir.glob("*/tasks.md") if archive_dir.exists() else []:
        count = count_unchecked_tasks(tasks_file)
        if count:
            stale_total += count
            stale_files.append(
                {
                    "change": tasks_file.parent.name,
                    "path": str(tasks_file),
                    "unchecked": count,
                }
            )

    return {
        "scope": str(scope),
        "has_openspec_yaml": (scope / ".openspec.yaml").exists(),
        "spec_count": len(specs),
        "active_count": len(active_changes),
        "active_changes": [p.name for p in active_changes],
        "archive_count": len(archived_changes),
        "archive_unchecked_task_files": len(stale_files),
        "archive_unchecked_task_total": stale_total,
        "archive_unchecked_samples": stale_files[:20],
    }


def render_markdown(root: Path, scopes: list[dict[str, Any]]) -> str:
    lines = [
        f"# OpenSpec scan: {root}",
        "",
        f"- scopes: {len(scopes)}",
        f"- specs: {sum(s['spec_count'] for s in scopes)}",
        f"- active changes: {sum(s['active_count'] for s in scopes)}",
        f"- archived changes: {sum(s['archive_count'] for s in scopes)}",
        f"- archived task files with unchecked items: {sum(s['archive_unchecked_task_files'] for s in scopes)}",
        "",
        "| Scope | Specs | Active | Archive | Stale task files |",
        "|---|---:|---:|---:|---:|",
    ]

    for scope in scopes:
        lines.append(
            "| {scope} | {spec_count} | {active_count} | {archive_count} | {archive_unchecked_task_files} |".format(
                **scope
            )
        )

    for scope in scopes:
        if scope["active_changes"]:
            lines.extend(["", f"## Active: {scope['scope']}"])
            lines.extend(f"- {name}" for name in scope["active_changes"])

        if scope["archive_unchecked_samples"]:
            lines.extend(["", f"## Archive unchecked samples: {scope['scope']}"])
            for item in scope["archive_unchecked_samples"]:
                lines.append(f"- {item['change']}: {item['unchecked']} unchecked tasks")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan OpenSpec scopes in a repository.")
    parser.add_argument("root", nargs="?", default=".", help="Repository or project root")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        parser.error(f"path does not exist: {root}")

    scopes = [scan_scope(scope) for scope in discover_scopes(root)]
    result = {"root": str(root), "scope_count": len(scopes), "scopes": scopes}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(root, scopes), end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
