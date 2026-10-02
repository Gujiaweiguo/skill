import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scan_openspec.py"


def run_scanner(root: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root), *flags],
        check=True,
        capture_output=True,
        text=True,
    )


class ScanOpenSpecTest(unittest.TestCase):
    def test_hidden_change_directories_are_not_active_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            (changes / "real-change").mkdir(parents=True)
            (changes / ".evidence").mkdir()
            (changes / "archive").mkdir()

            payload = json.loads(run_scanner(root, "--json").stdout)

        scope = payload["scopes"][0]
        self.assertEqual(scope["active_changes"], ["real-change"])
        self.assertEqual(scope["scope_source"], "openspec-dir")
        self.assertEqual(scope["scan_status"], "complete")

    def test_undecodable_archive_tasks_are_reported_as_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tasks = root / "openspec" / "changes" / "archive" / "old-change" / "tasks.md"
            tasks.parent.mkdir(parents=True)
            tasks.write_bytes(b"\xff\xfe")

            payload = json.loads(run_scanner(root, "--json").stdout)

        scope = payload["scopes"][0]
        self.assertEqual(scope["archive_unreadable_task_files"], 1)
        self.assertEqual(scope["archive_unreadable_task_samples"][0]["change"], "old-change")

    def test_archive_unchecked_tasks_are_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            tasks = root / "openspec" / "changes" / "archive" / "shipped" / "tasks.md"
            tasks.parent.mkdir(parents=True)
            tasks.write_text(
                "- [ ] open item\n"
                "- [x] done item\n"
                "  - [ ] nested open item\n",
                encoding="utf-8",
            )

            payload = json.loads(run_scanner(root, "--json").stdout)

        scope = payload["scopes"][0]
        self.assertEqual(scope["archive_unchecked_task_files"], 1)
        self.assertEqual(scope["archive_unchecked_task_total"], 2)
        self.assertEqual(scope["archive_unchecked_samples"][0]["change"], "shipped")
        self.assertEqual(scope["archive_unchecked_samples"][0]["unchecked"], 2)

    def test_multiple_scopes_include_nested_project(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "openspec" / "changes" / "root-change").mkdir(parents=True)
            nested_specs = root / "packages" / "sub" / "openspec" / "specs" / "billing"
            nested_specs.mkdir(parents=True)
            (nested_specs / "spec.md").write_text("# billing\n", encoding="utf-8")

            payload = json.loads(run_scanner(root, "--json").stdout)

        self.assertEqual(payload["scope_count"], 2)
        scope_paths = [scope["scope"] for scope in payload["scopes"]]
        self.assertIn(str(root), scope_paths)
        nested = next(scope for scope in payload["scopes"] if scope["scope"] != str(root))
        self.assertEqual(nested["spec_count"], 1)
        self.assertEqual(nested["active_count"], 0)
        self.assertEqual(nested["active_changes"], [])

    def test_yaml_only_scope_is_partial_with_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / ".openspec.yaml").write_text("extends: shared\n", encoding="utf-8")

            payload = json.loads(run_scanner(root, "--json").stdout)
            markdown = run_scanner(root).stdout

        self.assertEqual(payload["schema_version"], 1)
        scope = payload["scopes"][0]
        self.assertEqual(scope["scope_source"], "openspec-yaml")
        self.assertEqual(scope["scan_status"], "partial")
        self.assertEqual(scope["spec_count"], 0)
        self.assertEqual(scope["active_count"], 0)
        self.assertIn("Partially scanned scope", markdown)

    def test_empty_root_reports_zero_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            payload = json.loads(run_scanner(root, "--json").stdout)
            markdown = run_scanner(root).stdout

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["scope_count"], 0)
        self.assertEqual(payload["scopes"], [])
        self.assertIn("scopes: 0", markdown)

    def test_verification_reports_are_classified_with_quality_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"

            present = changes / "present"
            present.mkdir(parents=True)
            (present / "verification-report.md").write_text(
                "# Verification Report\n\n- command: `uv run pytest`\n- result: all passed\n- revision: abc123\n",
                encoding="utf-8",
            )
            thin = changes / "thin"
            thin.mkdir()
            (thin / "verification-report.md").write_text(
                "# Notes\n\nchecked manually, looks fine\n", encoding="utf-8"
            )
            placeholder = changes / "placeholder"
            placeholder.mkdir()
            (placeholder / "verification-report.md").write_text(
                "# Verification\n\nTODO: 待填\n", encoding="utf-8"
            )
            empty = changes / "empty"
            empty.mkdir()
            (empty / "verification-report.md").write_text("   \n", encoding="utf-8")
            unreadable = changes / "unreadable"
            unreadable.mkdir()
            (unreadable / "verification-report.md").write_bytes(b"\xff\xfe")
            (changes / "missing").mkdir()
            mention = changes / "mention"
            mention.mkdir()
            (mention / "verification-report.md").write_text(
                "# Verification Report\n\n- command: `uv run pytest`\n- result: all passed\n- revision: abc123\n\nno TODOs remain\n",
                encoding="utf-8",
            )
            reviewed = changes / "reviewed"
            reviewed.mkdir()
            (reviewed / "verification-report.md").write_text(
                "# Review\n\nchange validated manually, nothing updated\n",
                encoding="utf-8",
            )
            as_dir = changes / "as-dir"
            as_dir.mkdir()
            (as_dir / "verification-report.md").mkdir()

            payload = json.loads(run_scanner(root, "--json").stdout)

        evidence = payload["scopes"][0]["active_evidence"]
        self.assertEqual(
            evidence["present"],
            {
                "tasks_status": "missing",
                "verification_status": "present",
                "verification_reasons": [],
                "artifact_status": "missing",
            },
        )
        self.assertEqual(evidence["mention"]["verification_status"], "present")
        self.assertEqual(evidence["mention"]["verification_reasons"], [])
        self.assertEqual(evidence["thin"]["verification_status"], "present")
        self.assertEqual(
            evidence["thin"]["verification_reasons"],
            ["missing-command", "missing-result", "missing-context"],
        )
        self.assertEqual(
            evidence["placeholder"]["verification_status"], "placeholder"
        )
        self.assertEqual(
            evidence["placeholder"]["verification_reasons"], ["template-markers"]
        )
        self.assertEqual(evidence["empty"]["verification_status"], "empty")
        self.assertEqual(evidence["unreadable"]["verification_status"], "unreadable")
        self.assertEqual(evidence["missing"]["verification_status"], "missing")
        self.assertEqual(evidence["as-dir"]["verification_status"], "unreadable")
        self.assertEqual(evidence["as-dir"]["verification_reasons"], ["unreadable-file"])
        self.assertEqual(
            evidence["reviewed"]["verification_reasons"],
            ["missing-command", "missing-result", "missing-context"],
        )

    def test_broken_symlink_report_and_tasks_are_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            change = changes / "ghost"
            change.mkdir(parents=True)
            os.symlink("nowhere-report.md", change / "verification-report.md")
            os.symlink("nowhere-tasks.md", change / "tasks.md")

            payload = json.loads(run_scanner(root, "--json").stdout)

        evidence = payload["scopes"][0]["active_evidence"]["ghost"]
        self.assertEqual(evidence["verification_status"], "unreadable")
        self.assertEqual(evidence["verification_reasons"], ["broken-link"])
        self.assertEqual(evidence["tasks_status"], "unreadable")

    def test_broken_symlink_archive_tasks_are_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            archived = root / "openspec" / "changes" / "archive" / "broken"
            archived.mkdir(parents=True)
            os.symlink("nowhere.md", archived / "tasks.md")

            payload = json.loads(run_scanner(root, "--json").stdout)

        scope = payload["scopes"][0]
        self.assertEqual(scope["archive_unreadable_task_files"], 1)
        self.assertEqual(scope["archive_unreadable_task_samples"][0]["change"], "broken")

    def test_unreadable_changes_dir_reports_inaccessible_scope(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("permission checks do not apply when running as root")
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            changes.mkdir(parents=True)
            os.chmod(changes, 0o000)
            try:
                payload = json.loads(run_scanner(root, "--json").stdout)
                markdown = run_scanner(root).stdout
            finally:
                os.chmod(changes, 0o755)

        scope = payload["scopes"][0]
        self.assertEqual(scope["scan_status"], "inaccessible")
        self.assertIsNotNone(scope["error"])
        self.assertIn("Inaccessible scope", markdown)

    def test_active_evidence_covers_tasks_and_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"

            full = changes / "full"
            full.mkdir(parents=True)
            (full / "proposal.md").write_text("# p\n", encoding="utf-8")
            (full / "tasks.md").write_text("- [x] one\n", encoding="utf-8")

            partial = changes / "partial"
            partial.mkdir()
            (partial / "tasks.md").write_text("- [x] a\n- [ ] b\n", encoding="utf-8")

            (changes / "bare").mkdir()

            payload = json.loads(run_scanner(root, "--json").stdout)

        evidence = payload["scopes"][0]["active_evidence"]
        self.assertEqual(evidence["full"]["tasks_status"], "complete")
        self.assertEqual(evidence["full"]["artifact_status"], "complete")
        self.assertEqual(evidence["partial"]["tasks_status"], "partial")
        self.assertEqual(evidence["partial"]["artifact_status"], "partial")
        self.assertEqual(evidence["bare"]["tasks_status"], "missing")
        self.assertEqual(evidence["bare"]["artifact_status"], "missing")

    def test_verification_commands_are_discovered_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "openspec" / "changes" / "dummy").mkdir(parents=True)
            (root / "Makefile").write_text(
                "check-openspec:\n\topenspec validate --strict\n\nbuild:\n\t@echo hi\n",
                encoding="utf-8",
            )
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "check_openspec.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (scripts / "deploy.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "scripts": {
                            "openspec:validate": "openspec validate --strict",
                            "build": "vite build",
                        }
                    }
                ),
                encoding="utf-8",
            )

            payload = json.loads(run_scanner(root, "--json").stdout)
            markdown = run_scanner(root).stdout

        verification = payload["scopes"][0]["verification"]
        self.assertEqual(verification["command_source"], "discovered")
        self.assertEqual(
            sorted(verification["commands"]),
            ["make check-openspec", "npm run openspec:validate", "scripts/check_openspec.sh"],
        )
        self.assertEqual(verification["execution"], "not-run")
        self.assertIsNone(verification["result_ref"])
        self.assertIn("Verification commands", markdown)
        self.assertIn("(execution: not-run)", markdown)

    def test_markdown_output_reports_gaps_and_archive_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            archive = changes / "archive"
            (archive / "legacy").mkdir(parents=True)
            (archive / "legacy" / "tasks.md").write_bytes(b"\xff\xfe")
            (archive / "stale").mkdir()
            (archive / "stale" / "tasks.md").write_text("- [ ] left\n", encoding="utf-8")
            live = changes / "live"
            live.mkdir()
            template = changes / "live2"
            template.mkdir()
            (template / "verification-report.md").write_text("TODO\n", encoding="utf-8")
            live3 = changes / "live3"
            live3.mkdir()
            (live3 / "verification-report.md").write_text(
                "# Notes\n\nchecked manually\n", encoding="utf-8"
            )

            markdown = run_scanner(root).stdout

        self.assertIn("Archive unreadable task files", markdown)
        self.assertIn("legacy", markdown)
        self.assertIn("Archive unchecked samples", markdown)
        self.assertIn("stale: 1 unchecked tasks", markdown)
        self.assertIn("Active verification gaps", markdown)
        self.assertIn("- live: missing", markdown)
        self.assertIn("- live2: placeholder (template-markers)", markdown)
        self.assertIn(
            "- live3: present (missing-command, missing-result, missing-context)", markdown
        )

    def test_baseline_diff_reports_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            (changes / "alpha").mkdir(parents=True)

            baseline_path = root.parent / (root.name + "-baseline.json")
            baseline_path.write_text(run_scanner(root, "--json").stdout, encoding="utf-8")

            (changes / "beta").mkdir()
            (archive := changes / "archive").mkdir()
            (archive / "done").mkdir()
            (archive / "done" / "tasks.md").write_text("- [ ] forgotten\n", encoding="utf-8")

            payload = json.loads(
                run_scanner(root, "--json", "--baseline", str(baseline_path)).stdout
            )
            markdown = run_scanner(root, "--baseline", str(baseline_path)).stdout

            baseline_path.unlink()

        self.assertIn("diff", payload)
        diff = payload["diff"]
        self.assertEqual(diff["scopes_added"], [])
        changed = diff["scopes_changed"][0]
        self.assertEqual(changed["active_added"], ["beta"])
        self.assertEqual(changed["verification_gaps_added"], ["beta"])
        self.assertEqual(changed["archive_unchecked_delta"], 1)
        self.assertIn("Diff vs baseline", markdown)
        self.assertIn("active +beta", markdown)

    def test_baseline_without_changes_reports_no_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "openspec" / "changes" / "solo").mkdir(parents=True)
            baseline_path = root.parent / (root.name + "-baseline2.json")
            baseline_path.write_text(run_scanner(root, "--json").stdout, encoding="utf-8")

            markdown = run_scanner(root, "--baseline", str(baseline_path)).stdout

            baseline_path.unlink()

        self.assertIn("Diff vs baseline", markdown)
        self.assertIn("- no changes", markdown)


    def test_command_discovery_ignores_makefile_variables_and_malformed_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "openspec" / "changes" / "dummy").mkdir(parents=True)
            (root / "Makefile").write_text(
                "OPENSPEC := ./bin/openspec\n"
                "OPENSPEC_BIN ?= openspec\n"
                ".PHONY: check-openspec\n"
                "check-openspec:\n\topenspec validate --strict\n",
                encoding="utf-8",
            )
            (root / "package.json").write_text(
                json.dumps({"scripts": ["openspec"]}), encoding="utf-8"
            )

            payload = json.loads(run_scanner(root, "--json").stdout)

        verification = payload["scopes"][0]["verification"]
        self.assertEqual(verification["commands"], ["make check-openspec"])
        self.assertEqual(verification["command_source"], "discovered")
        self.assertEqual(verification["execution"], "not-run")

    def test_baseline_inaccessible_scope_is_uncomparable_not_resolved(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("permission checks do not apply when running as root")
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            (changes / "alpha").mkdir(parents=True)
            baseline_path = root.parent / (root.name + "-baseline3.json")
            baseline_path.write_text(run_scanner(root, "--json").stdout, encoding="utf-8")
            os.chmod(changes, 0o000)
            try:
                payload = json.loads(
                    run_scanner(root, "--json", "--baseline", str(baseline_path)).stdout
                )
            finally:
                os.chmod(changes, 0o755)
                baseline_path.unlink()

        diff = payload["diff"]
        self.assertEqual(diff["scopes_changed"], [])
        self.assertFalse(diff["scopes_removed"])
        uncomparable = diff["uncomparable_scopes"]
        self.assertEqual(len(uncomparable), 1)
        self.assertEqual(uncomparable[0]["current_scan_status"], "inaccessible")
        self.assertEqual(uncomparable[0]["baseline_scan_status"], "complete")
        resolved = [item for item in diff["scopes_changed"] if item["verification_gaps_resolved"]]
        self.assertEqual(resolved, [])

    def test_invalid_baselines_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "openspec" / "changes" / "solo").mkdir(parents=True)
            cases = {
                "shape": {"scopes": "not-a-list"},
                "version": {"schema_version": 0, "root": str(root.resolve()), "scopes": []},
                "cross-root": {"schema_version": 1, "root": "/foreign", "scopes": []},
                "empty-scope-id": {
                    "schema_version": 1,
                    "root": str(root.resolve()),
                    "scopes": [{"scope": ""}],
                },
            }
            for name, document in cases.items():
                baseline_path = root.parent / f"{root.name}-{name}.json"
                baseline_path.write_text(json.dumps(document), encoding="utf-8")
                try:
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(root), "--json", "--baseline", str(baseline_path)],
                        capture_output=True,
                        text=True,
                    )
                finally:
                    baseline_path.unlink()
                self.assertEqual(result.returncode, 2, f"case {name} should exit 2")
                self.assertIn("baseline", result.stderr.lower(), f"case {name} should name the baseline")

    def test_baseline_placeholder_to_thin_present_stays_a_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            change = root / "openspec" / "changes" / "alpha"
            change.mkdir(parents=True)
            report = change / "verification-report.md"
            report.write_text("TODO\n", encoding="utf-8")
            baseline_path = root.parent / (root.name + "-baseline4.json")
            baseline_path.write_text(run_scanner(root, "--json").stdout, encoding="utf-8")
            report.write_text("# Notes\n\nchecked manually\n", encoding="utf-8")
            payload = json.loads(
                run_scanner(root, "--json", "--baseline", str(baseline_path)).stdout
            )
            baseline_path.unlink()

        changed = payload["diff"]["scopes_changed"]
        self.assertEqual(changed, [])
        self.assertEqual(payload["diff"]["uncomparable_scopes"], [])


    def test_baseline_scopes_missing_diff_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "openspec" / "changes" / "solo").mkdir(parents=True)
            resolved = str(root.resolve())
            cases = {
                "missing-evidence": {
                    "schema_version": 1,
                    "root": resolved,
                    "scopes": [
                        {"scope": resolved, "scan_status": "complete", "active_changes": []}
                    ],
                },
                "missing-status": {
                    "schema_version": 1,
                    "root": resolved,
                    "scopes": [{"scope": resolved}],
                },
                "malformed-evidence": {
                    "schema_version": 1,
                    "root": resolved,
                    "scopes": [
                        {
                            "scope": resolved,
                            "scan_status": "complete",
                            "active_changes": [],
                            "active_evidence": {"solo": {}},
                        }
                    ],
                },
                "bad-total": {
                    "schema_version": 1,
                    "root": resolved,
                    "scopes": [
                        {
                            "scope": resolved,
                            "scan_status": "complete",
                            "active_changes": [],
                            "active_evidence": {},
                            "archive_unchecked_task_total": "0",
                        }
                    ],
                },
                "evidence-missing-change": {
                    "schema_version": 1,
                    "root": resolved,
                    "scopes": [
                        {
                            "scope": resolved,
                            "scan_status": "complete",
                            "active_changes": ["solo"],
                            "active_evidence": {},
                        }
                    ],
                },
                "evidence-extra-change": {
                    "schema_version": 1,
                    "root": resolved,
                    "scopes": [
                        {
                            "scope": resolved,
                            "scan_status": "complete",
                            "active_changes": [],
                            "active_evidence": {
                                "ghost": {
                                    "verification_status": "missing",
                                    "verification_reasons": [],
                                }
                            },
                        }
                    ],
                },
                "unknown-reason": {
                    "schema_version": 1,
                    "root": resolved,
                    "scopes": [
                        {
                            "scope": resolved,
                            "scan_status": "complete",
                            "active_changes": ["solo"],
                            "active_evidence": {
                                "solo": {
                                    "verification_status": "present",
                                    "verification_reasons": ["bogus-reason"],
                                }
                            },
                        }
                    ],
                },
            }
            for name, document in cases.items():
                baseline_path = root.parent / f"{root.name}-{name}.json"
                baseline_path.write_text(json.dumps(document), encoding="utf-8")
                try:
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), str(root), "--json", "--baseline", str(baseline_path)],
                        capture_output=True,
                        text=True,
                    )
                finally:
                    baseline_path.unlink()
                self.assertEqual(result.returncode, 2, f"case {name} should exit 2")
                self.assertIn("baseline", result.stderr.lower(), f"case {name} should name the baseline")

    def test_baseline_unreadable_subtree_not_reported_removed(self) -> None:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("permission checks do not apply when running as root")
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "openspec" / "changes" / "root-change").mkdir(parents=True)
            locked = root / "locked"
            (locked / "openspec" / "changes" / "child").mkdir(parents=True)
            baseline_path = root.parent / (root.name + "-baseline5.json")
            baseline_path.write_text(run_scanner(root, "--json").stdout, encoding="utf-8")
            os.chmod(locked, 0o000)
            try:
                payload = json.loads(
                    run_scanner(root, "--json", "--baseline", str(baseline_path)).stdout
                )
                markdown = run_scanner(root, "--baseline", str(baseline_path)).stdout
            finally:
                os.chmod(locked, 0o755)
                baseline_path.unlink()

        self.assertEqual([scope["scope"] for scope in payload["scopes"]], [str(root)])
        self.assertEqual(len(payload["discovery_errors"]), 1)
        self.assertIn(str(locked), payload["discovery_errors"][0])
        diff = payload["diff"]
        self.assertEqual(diff["scopes_removed"], [])
        uncomparable = {item["scope"]: item for item in diff["uncomparable_scopes"]}
        self.assertIn(str(locked), uncomparable)
        blocked = uncomparable[str(locked)]
        self.assertIsNone(blocked["current_scan_status"])
        self.assertEqual(blocked["reason"], "discovery-error")
        self.assertEqual(blocked["baseline_scan_status"], "complete")
        self.assertIn("Discovery errors", markdown)
        self.assertIn("not-discovered", markdown)


if __name__ == "__main__":
    unittest.main()
