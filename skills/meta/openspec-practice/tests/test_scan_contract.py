"""Cross-file contract checks: scanner output, scan-output.schema.json, and docs.

Guards against drift between the three sources of truth:
- scripts/scan_openspec.py (emitted fields and enums)
- references/scan-output.schema.json (machine contract)
- SKILL.md + references/*.md (human contract)
"""

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_DIR / "scripts" / "scan_openspec.py"
SCHEMA_PATH = SKILL_DIR / "references" / "scan-output.schema.json"


def load_scanner_module() -> Any:
    spec = importlib.util.spec_from_file_location("scan_openspec_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScanContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scanner = load_scanner_module()
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.definitions = cls.schema["definitions"]

    def run_scanner(self, root: Path, *flags: str) -> dict[str, Any]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(root), *flags],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_schema_version_matches_scanner_constant(self) -> None:
        self.assertEqual(
            self.schema["properties"]["schema_version"]["const"],
            self.scanner.SCHEMA_VERSION,
        )

    def test_schema_enums_match_scanner_constants(self) -> None:
        scope = self.definitions["scope"]["properties"]
        self.assertEqual(
            set(scope["scan_status"]["enum"]),
            set(self.scanner.SCAN_STATUSES),
        )
        evidence = self.definitions["change_evidence"]["properties"]
        self.assertEqual(
            set(evidence["tasks_status"]["enum"]),
            set(self.scanner.TASKS_STATUSES),
        )
        self.assertEqual(
            set(evidence["verification_status"]["enum"]),
            set(self.scanner.VERIFICATION_STATUSES),
        )
        self.assertEqual(
            set(evidence["artifact_status"]["enum"]),
            set(self.scanner.ARTIFACT_STATUSES),
        )
        self.assertEqual(
            set(
                evidence["verification_reasons"]["items"]["enum"]
            ),
            set(self.scanner.VERIFICATION_REASON_VALUES),
        )

    def test_every_emitted_quality_reason_is_in_schema_enum(self) -> None:
        allowed = set(
            self.definitions["change_evidence"]["properties"]["verification_reasons"][
                "items"
            ]["enum"]
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            changes = Path(temporary_directory) / "openspec" / "changes"
            emitted: set[str] = set()

            broken = changes / "broken-link"
            broken.mkdir(parents=True)
            (broken / "verification-report.md").symlink_to("nowhere.md")

            def case(name: str, content: bytes | str) -> None:
                change = changes / name
                change.mkdir()
                report = change / "verification-report.md"
                if isinstance(content, str):
                    report.write_text(content, encoding="utf-8")
                else:
                    report.write_bytes(content)

            case("encoding", b"\xff\xfe")
            case("empty", "   \n")
            case("template", "TODO: 待填\n")
            case("thin", "# Notes\n\nchecked manually, looks fine\n")
            case("full", "# V\n\n- command: pytest\n- result: pass\n- revision: abc\n")

            as_dir = changes / "as-dir"
            as_dir.mkdir()
            (as_dir / "verification-report.md").mkdir()

            def assess(name: str) -> Any:
                return self.scanner.assess_verification_report(
                    changes / name / "verification-report.md"
                )

            for assessment in (
                assess("broken-link"),
                assess("encoding"),
                assess("empty"),
                assess("template"),
                assess("thin"),
                assess("full"),
                assess("as-dir"),
            ):
                emitted.update(assessment["quality_reasons"])

        self.assertEqual(
            emitted,
            {
                "broken-link",
                "unreadable-encoding",
                "unreadable-file",
                "empty",
                "template-markers",
                "missing-command",
                "missing-result",
                "missing-context",
            },
        )
        self.assertLessEqual(emitted, allowed)

    def test_scanner_output_keys_match_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            change = changes / "sample"
            change.mkdir(parents=True)
            (change / "verification-report.md").write_text(
                "# V\n\n- command: pytest\n- result: pass\n- revision: abc\n",
                encoding="utf-8",
            )
            baseline_path = root.parent / (root.name + "-contract-baseline.json")
            first = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), "--json"],
                check=True,
                capture_output=True,
                text=True,
            )
            baseline_path.write_text(first.stdout, encoding="utf-8")
            try:
                payload = self.run_scanner(root, "--json", "--baseline", str(baseline_path))
            finally:
                baseline_path.unlink()

        self.assertEqual(
            set(self.schema["required"]),
            {"schema_version", "root", "scope_count", "scopes", "discovery_errors"},
        )
        self.assertLessEqual(
            set(payload.keys()), set(self.schema["properties"].keys())
        )

        scope = payload["scopes"][0]
        self.assertEqual(
            set(scope.keys()),
            set(self.definitions["scope"]["properties"].keys()),
        )
        evidence = scope["active_evidence"]["sample"]
        self.assertEqual(
            set(evidence.keys()),
            set(self.definitions["change_evidence"]["properties"].keys()),
        )
        self.assertEqual(
            set(scope["verification"].keys()),
            set(self.definitions["verification"]["properties"].keys()),
        )
        self.assertEqual(
            set(payload["diff"].keys()),
            set(self.definitions["diff"]["properties"].keys()),
        )

    def test_retired_field_name_is_not_referenced_anywhere(self) -> None:
        pattern = "active_missing_verification"
        for path in [SCRIPT, SCHEMA_PATH, SKILL_DIR / "SKILL.md", *sorted((SKILL_DIR / "references").glob("*.md"))]:
            self.assertNotIn(
                pattern,
                path.read_text(encoding="utf-8"),
                f"retired field {pattern!r} still referenced in {path}",
            )

    def test_skill_md_reference_paths_exist(self) -> None:
        skill_md = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        referenced = set(re.findall(r"references/[A-Za-z0-9_.-]+\.md", skill_md))
        self.assertTrue(referenced)
        for relative in referenced:
            self.assertTrue(
                (SKILL_DIR / relative).is_file(),
                f"SKILL.md references missing file {relative}",
            )


    _TYPE_CHECKS: dict[str, Callable[[Any], bool]] = {
        "object": lambda value: isinstance(value, dict),
        "array": lambda value: isinstance(value, list),
        "string": lambda value: isinstance(value, str),
        "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
        "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": lambda value: isinstance(value, bool),
        "null": lambda value: value is None,
    }

    def assert_conforms(self, instance: Any, schema: Any, path: str = "$") -> None:
        """Validate against the draft-07 subset used by scan-output.schema.json."""
        if "$ref" in schema:
            ref = schema["$ref"]
            self.assertTrue(ref.startswith("#/definitions/"), f"{path}: unsupported $ref {ref}")
            self.assert_conforms(instance, self.schema["definitions"][ref.split("/")[-1]], path)
            return
        if "const" in schema:
            self.assertEqual(instance, schema["const"], f"{path}: const mismatch")
        if "enum" in schema:
            self.assertIn(instance, schema["enum"], f"{path}: {instance!r} not in enum")
        expected = schema.get("type")
        if expected is not None:
            allowed = [expected] if isinstance(expected, str) else expected
            self.assertTrue(
                any(self._TYPE_CHECKS[name](instance) for name in allowed),
                f"{path}: {type(instance).__name__} violates type {expected}",
            )
        if "minimum" in schema and isinstance(instance, (int, float)) and not isinstance(instance, bool):
            self.assertGreaterEqual(instance, schema["minimum"], f"{path}: below minimum")
        if isinstance(instance, dict):
            for key in schema.get("required", []):
                self.assertIn(key, instance, f"{path}: missing required {key!r}")
            properties = schema.get("properties", {})
            additional = schema.get("additionalProperties")
            for key, value in instance.items():
                if key in properties:
                    self.assert_conforms(value, properties[key], f"{path}.{key}")
                elif isinstance(additional, dict):
                    self.assert_conforms(value, additional, f"{path}.{key}")
        elif isinstance(instance, list) and "items" in schema:
            for index, item in enumerate(instance):
                self.assert_conforms(item, schema["items"], f"{path}[{index}]")

    def test_emitted_documents_conform_to_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            sample = changes / "sample"
            sample.mkdir(parents=True)
            (sample / "verification-report.md").write_text(
                "# V\n\n- command: pytest\n- result: pass\n- revision: abc\n",
                encoding="utf-8",
            )
            thin = changes / "thin"
            thin.mkdir()
            (thin / "verification-report.md").write_text(
                "# Notes\n\nchecked manually\n", encoding="utf-8"
            )
            (root / "Makefile").write_text(
                "check-openspec:\n\topenspec validate --strict\n", encoding="utf-8"
            )
            config_only = root / "packages" / "cfg-only"
            config_only.mkdir(parents=True)
            (config_only / ".openspec.yaml").write_text("extends: shared\n", encoding="utf-8")

            baseline_path = root.parent / (root.name + "-conformance-baseline.json")
            baseline_path.write_text(run_json(root), encoding="utf-8")
            try:
                with_diff = json.loads(
                    run_command_json(root, "--baseline", str(baseline_path))
                )
            finally:
                baseline_path.unlink()

        self.assert_conforms(with_diff, self.schema)
        self.assertEqual(len(with_diff["scopes"]), 2)
        by_path = {scope["scope"]: scope["scan_status"] for scope in with_diff["scopes"]}
        self.assertEqual(by_path[with_diff["root"]], "complete")
        config_only_path = next(path for path in by_path if path.endswith("cfg-only"))
        self.assertEqual(by_path[config_only_path], "partial")
        self.assertIn("diff", with_diff)

        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return  # permission-based fixture does not apply when running as root
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            changes = root / "openspec" / "changes"
            changes.mkdir(parents=True)
            os.chmod(changes, 0o000)
            try:
                inaccessible = json.loads(run_command_json(root))
            finally:
                os.chmod(changes, 0o755)
        self.assert_conforms(inaccessible, self.schema)
        self.assertEqual(inaccessible["scopes"][0]["scan_status"], "inaccessible")


def run_command_json(root: Path, *flags: str) -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(root), "--json", *flags],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def run_json(root: Path) -> str:
    return run_command_json(root)


if __name__ == "__main__":
    unittest.main()
