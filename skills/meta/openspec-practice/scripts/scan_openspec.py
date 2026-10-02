#!/usr/bin/env python3
"""Scan OpenSpec scopes in a repository.

The script is intentionally small and stdlib-only. It does not decide whether a
change is correct; it gives the agent a reliable inventory to reason from.

Output contract: references/scan-output.schema.json. Additive field changes
keep schema_version; removing a field or changing its semantics bumps it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1

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

SCAN_STATUSES = ("complete", "partial", "inaccessible")
VERIFICATION_STATUSES = ("present", "missing", "unreadable", "empty", "placeholder")
TASKS_STATUSES = ("missing", "empty", "partial", "complete", "unreadable")
ARTIFACT_STATUSES = ("missing", "partial", "complete")
VERIFICATION_REASON_VALUES = (
    "broken-link",
    "unreadable-encoding",
    "unreadable-file",
    "empty",
    "template-markers",
    "missing-command",
    "missing-result",
    "missing-context",
)

ASCII_PLACEHOLDER_MARKERS = ("TODO", "PLACEHOLDER")
CJK_PLACEHOLDER_MARKERS = ("待填", "待补", "待完成", "占位")
COMMAND_EVIDENCE_MARKERS = ("command", "命令", "cmd")
RESULT_EVIDENCE_MARKERS = ("result", "结果", "结论", "pass", "fail", "通过", "未通过")
CONTEXT_EVIDENCE_MARKERS = ("revision", "commit", "date", "日期", "范围", "scope")

_PLACEHOLDER_LINE_PREFIX = re.compile(r"^(?:[-*+>#]|\[[ xX]\]|\d+[.)])\s*")


def _marker_present(text_lower: str, marker: str) -> bool:
    """ASCII markers match whole words (with common suffixes); CJK markers match as substrings.

    Word boundaries stop false hits like ``date`` inside ``validated`` or ``pass``
    inside ``compass``, while still matching ``date:``, ``results``, ``passed``.
    """
    if marker.isascii():
        return re.search(
            rf"(?<![a-z0-9]){re.escape(marker)}(?:es|s|ed|ing)?(?![a-z0-9])",
            text_lower,
        ) is not None
    return marker in text_lower


def _line_anchor(line: str) -> str:
    stripped = line.lstrip()
    while True:
        match = _PLACEHOLDER_LINE_PREFIX.match(stripped)
        if not match:
            return stripped
        stripped = stripped[match.end():]


def _contains_unfilled_placeholder(text: str) -> bool:
    """Count as placeholder only a line that itself is an unfilled marker.

    Inline mentions such as ``no TODOs remain`` are evidence discussion, not
    template content, and must not downgrade a real report.
    """
    for line in text.splitlines():
        anchor = _line_anchor(line)
        upper = anchor.upper()
        for marker in ASCII_PLACEHOLDER_MARKERS:
            if re.match(rf"{marker}\b", upper):
                return True
        if any(anchor.startswith(marker) for marker in CJK_PLACEHOLDER_MARKERS):
            return True
    return False


def discover_scopes(root: Path) -> tuple[list[Path], list[str]]:
    """Discover scopes; unreadable subtrees are recorded instead of silently skipped."""
    scopes: set[Path] = set()
    errors: list[str] = []

    def on_error(error: OSError) -> None:
        errors.append(f"{type(error).__name__}: {error.filename or error}")

    for current, dirnames, filenames in os.walk(root, onerror=on_error):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        path = Path(current)

        if ".openspec.yaml" in filenames:
            scopes.add(path)

        if "openspec" in dirnames:
            openspec_dir = path / "openspec"
            if (openspec_dir / "specs").exists() or (openspec_dir / "changes").exists():
                scopes.add(path)
                dirnames.remove("openspec")

    return (
        sorted(scopes, key=lambda p: (len(p.relative_to(root).parts), str(p))),
        errors,
    )


def count_unchecked_tasks(tasks_file: Path) -> int | None:
    try:
        return sum(
            1
            for line in tasks_file.read_text(encoding="utf-8").splitlines()
            if line.lstrip().startswith("- [ ]")
        )
    except (UnicodeDecodeError, OSError):
        return None


def assess_verification_report(report: Path) -> dict[str, Any]:
    """Classify a change's verification-report.md with granular quality reasons.

    Discovery only: a `present` report is real content, not proof that
    verification passed; `quality_reasons` names structural gaps.
    """
    if not report.exists():
        if os.path.lexists(report):
            return {"status": "unreadable", "quality_reasons": ["broken-link"]}
        return {"status": "missing", "quality_reasons": []}
    try:
        text = report.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"status": "unreadable", "quality_reasons": ["unreadable-encoding"]}
    except OSError:
        return {"status": "unreadable", "quality_reasons": ["unreadable-file"]}

    stripped = text.strip()
    if not stripped:
        return {"status": "empty", "quality_reasons": ["empty"]}

    if _contains_unfilled_placeholder(stripped):
        return {"status": "placeholder", "quality_reasons": ["template-markers"]}

    lower = stripped.lower()
    reasons: list[str] = []
    if not any(_marker_present(lower, marker) for marker in COMMAND_EVIDENCE_MARKERS):
        reasons.append("missing-command")
    if not any(_marker_present(lower, marker) for marker in RESULT_EVIDENCE_MARKERS):
        reasons.append("missing-result")
    if not any(_marker_present(lower, marker) for marker in CONTEXT_EVIDENCE_MARKERS):
        reasons.append("missing-context")
    return {"status": "present", "quality_reasons": reasons}


def assess_tasks(tasks_file: Path) -> str:
    if not tasks_file.exists():
        return "unreadable" if os.path.lexists(tasks_file) else "missing"
    try:
        lines = tasks_file.read_text(encoding="utf-8").splitlines()
    except (UnicodeDecodeError, OSError):
        return "unreadable"

    unchecked = sum(1 for line in lines if line.lstrip().startswith("- [ ]"))
    checked = sum(1 for line in lines if line.lstrip().startswith(("- [x]", "- [X]")))
    total = unchecked + checked
    if total == 0:
        return "empty"
    if unchecked:
        return "partial"
    return "complete"


def assess_artifacts(change_dir: Path) -> str:
    has_proposal = (change_dir / "proposal.md").exists()
    has_tasks = (change_dir / "tasks.md").exists()
    if has_proposal and has_tasks:
        return "complete"
    if has_proposal or has_tasks:
        return "partial"
    return "missing"


def discover_verification_commands(scope: Path) -> dict[str, Any]:
    """Find candidate verification entrypoints. Discovery only, never execution."""
    commands: list[str] = []

    makefile = scope / "Makefile"
    if makefile.exists():
        try:
            for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith(("\t", " ", "#")) or not line.strip():
                    continue
                head, separator, tail = line.partition(":")
                target = head.strip()
                if (
                    not separator
                    or not target
                    or target.startswith(".")
                    or "=" in head
                    or tail.startswith(("=", "?", "+"))
                ):
                    continue
                if "openspec" in target.lower():
                    commands.append(f"make {target}")
        except OSError:
            pass

    scripts_dir = scope / "scripts"
    if scripts_dir.is_dir():
        try:
            for entry in sorted(scripts_dir.iterdir()):
                if entry.is_file() and "openspec" in entry.name.lower():
                    commands.append(f"scripts/{entry.name}")
        except OSError:
            pass

    package_json = scope / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                scripts = data.get("scripts")
                if isinstance(scripts, dict):
                    for key in sorted(scripts):
                        if isinstance(key, str) and "openspec" in key.lower():
                            commands.append(f"npm run {key}")
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "command_source": "discovered" if commands else "none",
        "commands": commands,
        "execution": "not-run",
        "result_ref": None,
    }


def scan_scope(scope: Path) -> dict[str, Any]:
    openspec = scope / "openspec"
    specs_dir = openspec / "specs"
    changes_dir = openspec / "changes"
    archive_dir = changes_dir / "archive"

    has_openspec_yaml = (scope / ".openspec.yaml").exists()

    try:
        specs = (
            sorted(p for p in specs_dir.glob("*/spec.md") if p.is_file())
            if specs_dir.exists()
            else []
        )
        active_changes = (
            sorted(
                p
                for p in changes_dir.iterdir()
                if p.is_dir() and p.name != "archive" and not p.name.startswith(".")
            )
            if changes_dir.exists()
            else []
        )
        active_evidence = {}
        for change in active_changes:
            verification = assess_verification_report(change / "verification-report.md")
            active_evidence[change.name] = {
                "tasks_status": assess_tasks(change / "tasks.md"),
                "verification_status": verification["status"],
                "verification_reasons": verification["quality_reasons"],
                "artifact_status": assess_artifacts(change),
            }
        archived_changes = (
            sorted(p for p in archive_dir.iterdir() if p.is_dir())
            if archive_dir.exists()
            else []
        )

        stale_files: list[dict[str, Any]] = []
        unreadable_files: list[dict[str, str]] = []
        stale_total = 0
        for tasks_file in archive_dir.glob("*/tasks.md") if archive_dir.exists() else []:
            count = count_unchecked_tasks(tasks_file)
            if count is None:
                unreadable_files.append(
                    {
                        "change": tasks_file.parent.name,
                        "path": str(tasks_file),
                    }
                )
                continue
            if count:
                stale_total += count
                stale_files.append(
                    {
                        "change": tasks_file.parent.name,
                        "path": str(tasks_file),
                        "unchecked": count,
                    }
                )

        verification = discover_verification_commands(scope)
    except OSError as error:
        return {
            "scope": str(scope),
            "scope_source": "openspec-dir"
            if (specs_dir.exists() or changes_dir.exists())
            else "openspec-yaml",
            "scan_status": "inaccessible",
            "has_openspec_yaml": has_openspec_yaml,
            "error": f"{type(error).__name__}: {error}",
            "spec_count": 0,
            "active_count": 0,
            "active_changes": [],
            "active_evidence": {},
            "verification": {
                "command_source": "none",
                "commands": [],
                "execution": "not-run",
                "result_ref": None,
            },
            "archive_count": 0,
            "archive_unchecked_task_files": 0,
            "archive_unchecked_task_total": 0,
            "archive_unchecked_samples": [],
            "archive_unreadable_task_files": 0,
            "archive_unreadable_task_samples": [],
        }

    if specs_dir.exists() or changes_dir.exists():
        scope_source = "openspec-dir"
        scan_status = "complete"
    else:
        scope_source = "openspec-yaml"
        scan_status = "partial"

    return {
        "scope": str(scope),
        "scope_source": scope_source,
        "scan_status": scan_status,
        "has_openspec_yaml": has_openspec_yaml,
        "error": None,
        "spec_count": len(specs),
        "active_count": len(active_changes),
        "active_changes": [p.name for p in active_changes],
        "active_evidence": active_evidence,
        "verification": verification,
        "archive_count": len(archived_changes),
        "archive_unchecked_task_files": len(stale_files),
        "archive_unchecked_task_total": stale_total,
        "archive_unchecked_samples": stale_files[:20],
        "archive_unreadable_task_files": len(unreadable_files),
        "archive_unreadable_task_samples": unreadable_files[:20],
    }


def verification_gaps(scope: dict[str, Any]) -> set[str]:
    """A gap is any non-present report OR a present report with structural quality reasons."""
    return {
        name
        for name, evidence in scope["active_evidence"].items()
        if evidence["verification_status"] != "present" or evidence["verification_reasons"]
    }


def _validate_baseline_scope(item: dict[str, Any], name: str) -> str | None:
    """Validate the fields diff_against_baseline reads, so bad baselines fail loudly."""
    status = item.get("scan_status")
    if not isinstance(status, str) or status not in SCAN_STATUSES:
        return f"scope {name!r} needs a valid 'scan_status'"
    if status != "complete":
        return None

    changes = item.get("active_changes")
    if not isinstance(changes, list) or not all(isinstance(entry, str) for entry in changes):
        return f"complete scope {name!r} needs a list of strings 'active_changes'"

    evidence = item.get("active_evidence")
    if not isinstance(evidence, dict):
        return f"complete scope {name!r} needs an object 'active_evidence'"
    for change_name, change_evidence in evidence.items():
        if not isinstance(change_name, str) or not isinstance(change_evidence, dict):
            return f"complete scope {name!r} has malformed 'active_evidence'"
        verification_status = change_evidence.get("verification_status")
        if (
            not isinstance(verification_status, str)
            or verification_status not in VERIFICATION_STATUSES
        ):
            return (
                f"complete scope {name!r} change {change_name!r} "
                "needs a valid 'verification_status'"
            )
        reasons = change_evidence.get("verification_reasons")
        if not isinstance(reasons, list) or not all(
            isinstance(reason, str) and reason in VERIFICATION_REASON_VALUES
            for reason in reasons
        ):
            return (
                f"complete scope {name!r} change {change_name!r} "
                "needs 'verification_reasons' values from the schema enum"
            )

    if set(evidence) != set(changes):
        return (
            f"complete scope {name!r} has 'active_evidence' keys "
            "that do not match 'active_changes'"
        )

    total = item.get("archive_unchecked_task_total")
    if not isinstance(total, int) or isinstance(total, bool):
        return f"complete scope {name!r} needs an integer 'archive_unchecked_task_total'"
    return None


def _validate_baseline(baseline: Any, current_root: str) -> str | None:
    """Return a human-readable problem, or None when the baseline is comparable."""
    if not isinstance(baseline, dict):
        return "top-level JSON must be an object"
    version = baseline.get("schema_version")
    if version != SCHEMA_VERSION:
        return f"unsupported schema_version {version!r}; expected {SCHEMA_VERSION}"
    if baseline.get("root") != current_root:
        return (
            f"baseline root {baseline.get('root')!r} does not match current root {current_root!r}"
        )
    scopes = baseline.get("scopes")
    if not isinstance(scopes, list):
        return "'scopes' must be a list"
    seen: set[str] = set()
    for item in scopes:
        if not isinstance(item, dict):
            return "each baseline scope must be an object"
        name = item.get("scope")
        if not isinstance(name, str) or not name:
            return "each baseline scope needs a non-empty string 'scope'"
        if name in seen:
            return f"duplicate baseline scope {name!r}"
        seen.add(name)
        field_problem = _validate_baseline_scope(item, name)
        if field_problem:
            return field_problem
    return None


def _error_paths(discovery_errors: list[str]) -> list[str]:
    paths = []
    for error in discovery_errors:
        _, separator, path_part = error.partition(": ")
        if separator:
            paths.append(path_part.rstrip("/"))
    return [path for path in paths if path]


def _hidden_by_discovery_error(scope_path: str, error_paths: list[str]) -> bool:
    return any(scope_path == path or scope_path.startswith(path + "/") for path in error_paths)


def diff_against_baseline(current: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    current_scopes = {s["scope"]: s for s in current["scopes"]}
    baseline_scopes = {s["scope"]: s for s in baseline.get("scopes", [])}
    error_paths = _error_paths(current.get("discovery_errors") or [])

    uncomparable: list[dict[str, Any]] = []
    changed = []
    for path in sorted(set(current_scopes) & set(baseline_scopes)):
        cur, base = current_scopes[path], baseline_scopes[path]
        if cur.get("scan_status") != "complete" or base.get("scan_status") != "complete":
            uncomparable.append(
                {
                    "scope": path,
                    "current_scan_status": cur.get("scan_status"),
                    "baseline_scan_status": base.get("scan_status"),
                }
            )
            continue
        active_added = sorted(set(cur["active_changes"]) - set(base["active_changes"]))
        active_removed = sorted(set(base["active_changes"]) - set(cur["active_changes"]))
        gaps_added = sorted(verification_gaps(cur) - verification_gaps(base))
        gaps_resolved = sorted(verification_gaps(base) - verification_gaps(cur))
        stale_delta = cur["archive_unchecked_task_total"] - base["archive_unchecked_task_total"]
        if active_added or active_removed or gaps_added or gaps_resolved or stale_delta:
            changed.append(
                {
                    "scope": path,
                    "active_added": active_added,
                    "active_removed": active_removed,
                    "verification_gaps_added": gaps_added,
                    "verification_gaps_resolved": gaps_resolved,
                    "archive_unchecked_delta": stale_delta,
                }
            )

    removed = sorted(set(baseline_scopes) - set(current_scopes))
    blocked = {path for path in removed if _hidden_by_discovery_error(path, error_paths)}
    for path in sorted(blocked):
        uncomparable.append(
            {
                "scope": path,
                "current_scan_status": None,
                "baseline_scan_status": baseline_scopes[path].get("scan_status"),
                "reason": "discovery-error",
            }
        )

    return {
        "scopes_added": sorted(set(current_scopes) - set(baseline_scopes)),
        "scopes_removed": [path for path in removed if path not in blocked],
        "scopes_changed": changed,
        "uncomparable_scopes": uncomparable,
    }


def render_diff(diff: dict[str, Any]) -> list[str]:
    lines = ["", "## Diff vs baseline"]
    if diff["scopes_added"]:
        lines.append(f"- scopes added: {', '.join(diff['scopes_added'])}")
    if diff["scopes_removed"]:
        lines.append(f"- scopes removed: {', '.join(diff['scopes_removed'])}")
    for item in diff["uncomparable_scopes"]:
        current_status = item["current_scan_status"] or "not-discovered"
        lines.append(
            f"- uncomparable: {item['scope']} "
            f"(current: {current_status}, baseline: {item['baseline_scan_status']})"
        )
    for change in diff["scopes_changed"]:
        parts = [f"{change['scope']}:"]
        if change["active_added"]:
            parts.append(f"active +{', '.join(change['active_added'])}")
        if change["active_removed"]:
            parts.append(f"active -{', '.join(change['active_removed'])}")
        if change["verification_gaps_added"]:
            parts.append(f"verification gaps +{', '.join(change['verification_gaps_added'])}")
        if change["verification_gaps_resolved"]:
            parts.append(
                f"verification gaps resolved: {', '.join(change['verification_gaps_resolved'])}"
            )
        if change["archive_unchecked_delta"]:
            parts.append(f"archive unchecked {change['archive_unchecked_delta']:+d}")
        lines.append("- " + " ".join(parts))
    if len(lines) == 2:
        lines.append("- no changes")
    return lines


def render_markdown(
    root: Path,
    scopes: list[dict[str, Any]],
    diff: dict[str, Any] | None = None,
    discovery_errors: list[str] | None = None,
) -> str:
    lines = [
        f"# OpenSpec scan: {root}",
        "",
        f"- scopes: {len(scopes)}",
        f"- specs: {sum(s['spec_count'] for s in scopes)}",
        f"- active changes: {sum(s['active_count'] for s in scopes)}",
        f"- archived changes: {sum(s['archive_count'] for s in scopes)}",
        f"- archived task files with unchecked items: {sum(s['archive_unchecked_task_files'] for s in scopes)}",
        f"- archived task files unreadable: {sum(s['archive_unreadable_task_files'] for s in scopes)}",
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

    if diff is not None:
        lines.extend(render_diff(diff))

    if discovery_errors:
        lines.extend(["", "## Discovery errors"])
        lines.extend(f"- {error}" for error in discovery_errors)

    for scope in scopes:
        if scope["active_changes"]:
            lines.extend(["", f"## Active: {scope['scope']}"])
            lines.extend(f"- {name}" for name in scope["active_changes"])

        gaps = {
            name: evidence
            for name, evidence in scope["active_evidence"].items()
            if evidence["verification_status"] != "present" or evidence["verification_reasons"]
        }
        if gaps:
            lines.extend(["", f"## Active verification gaps: {scope['scope']}"])
            for name, evidence in sorted(gaps.items()):
                reasons = evidence["verification_reasons"]
                suffix = f" ({', '.join(reasons)})" if reasons else ""
                lines.append(f"- {name}: {evidence['verification_status']}{suffix}")

        if scope["verification"]["commands"]:
            lines.extend(["", f"## Verification commands: {scope['scope']}"])
            lines.extend(
                f"- {command} (execution: {scope['verification']['execution']})"
                for command in scope["verification"]["commands"]
            )

        if scope["scan_status"] == "partial":
            lines.extend(
                [
                    "",
                    f"## Partially scanned scope: {scope['scope']}",
                    "- config-only scope: .openspec.yaml layout is not parsed; zero counts are not evidence of absence",
                ]
            )

        if scope["scan_status"] == "inaccessible":
            lines.extend(["", f"## Inaccessible scope: {scope['scope']}"])
            lines.append(f"- {scope['error']}")

        if scope["archive_unchecked_samples"]:
            lines.extend(["", f"## Archive unchecked samples: {scope['scope']}"])
            for item in scope["archive_unchecked_samples"]:
                lines.append(f"- {item['change']}: {item['unchecked']} unchecked tasks")

        if scope["archive_unreadable_task_samples"]:
            lines.extend(["", f"## Archive unreadable task files: {scope['scope']}"])
            lines.extend(
                f"- {item['change']}: unreadable tasks file ({item['path']})"
                for item in scope["archive_unreadable_task_samples"]
            )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan OpenSpec scopes in a repository.")
    parser.add_argument("root", nargs="?", default=".", help="Repository or project root")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")
    parser.add_argument(
        "--baseline", help="Previous scan JSON file to diff against (report-only)"
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists():
        parser.error(f"path does not exist: {root}")

    discovered, discovery_errors = discover_scopes(root)
    scopes = [scan_scope(scope) for scope in discovered]
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "root": str(root),
        "scope_count": len(scopes),
        "scopes": scopes,
        "discovery_errors": discovery_errors,
    }

    diff: dict[str, Any] | None = None
    if args.baseline:
        baseline_path = Path(args.baseline).expanduser().resolve()
        if not baseline_path.is_file():
            parser.error(f"baseline file does not exist: {baseline_path}")
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            parser.error(f"baseline file is not readable JSON: {error}")
        problem = _validate_baseline(baseline, str(root))
        if problem:
            parser.error(f"invalid baseline file {baseline_path}: {problem}")
        diff = diff_against_baseline(result, baseline)
        result["diff"] = diff

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(root, scopes, diff, discovery_errors), end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
