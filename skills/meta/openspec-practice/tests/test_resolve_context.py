from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_context.py"


def _write_company(base: Path, company_id: str, products_yaml: str) -> None:
    config = base / "config" / "company.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        f"schema_version: 1\nid: {company_id}\nproducts:\n{products_yaml}",
        encoding="utf-8",
    )


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
    )


class ResolveContextCliTest(unittest.TestCase):
    def test_serializes_product_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _write_company(base, "acme", "  - id: demo\n    name: Demo\n    code_root: null\n")
            result = _run(["demo", "--company-base", str(base)])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
        self.assertEqual(payload["company"]["id"], "acme")
        self.assertEqual(payload["product"]["id"], "demo")
        self.assertIsNone(payload["layers"]["code_root"])
        self.assertIn("scope_count", payload["openspec"])
        self.assertIn("scopes", payload["openspec"])

    def test_unknown_product_is_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _write_company(base, "acme", "  - id: demo\n    name: Demo\n")
            result = _run(["unknown", "--company-base", str(base)])
        self.assertEqual(result.returncode, 2)
        self.assertIn("context resolution failed", result.stderr)

    def test_missing_product_id_and_all_is_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _write_company(base, "acme", "  - id: demo\n    name: Demo\n")
            no_args = _run(["--company-base", str(base)])
            both = _run(["demo", "--all", "--company-base", str(base)])
        self.assertEqual(no_args.returncode, 2)
        self.assertEqual(both.returncode, 2)

    def test_all_resolves_every_registered_product(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _write_company(
                base,
                "acme",
                "  - id: one\n    name: One\n    code_root: null\n"
                "  - id: two\n    name: Two\n    code_root: null\n",
            )
            result = _run(["--all", "--company-base", str(base)])
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
        self.assertEqual(payload["company"]["id"], "acme")
        self.assertEqual([entry["product_id"] for entry in payload["products"]], ["one", "two"])
        self.assertTrue(all(entry["status"] == "resolved" for entry in payload["products"]))
        self.assertEqual(payload["products"][0]["context"]["product"]["id"], "one")

    def test_all_reports_per_product_errors_without_silent_skip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _write_company(
                base,
                "acme",
                "  - id: demo\n    name: Demo\n    code_root: null\n"
                "  - id: demo\n    name: Duplicate\n    code_root: null\n",
            )
            result = _run(["--all", "--company-base", str(base)])
            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
        statuses = [entry["status"] for entry in payload["products"]]
        self.assertIn("unresolved", statuses)
        unresolved = [entry for entry in payload["products"] if entry["status"] == "unresolved"]
        self.assertTrue(all("error" in entry for entry in unresolved))

    def test_dynamic_product_needs_only_company_yaml_and_docs_skeleton(self) -> None:
        """新增产品只写 company.yaml 条目 + 30-products 骨架即可被 CLI 解析。"""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _write_company(base, "acme", "")
            product_root = base / "30-products" / "newproduct"
            (product_root / "ontology").mkdir(parents=True)
            (product_root / "prd").mkdir()
            (product_root / "INDEX.md").write_text("# New\n", encoding="utf-8")
            (product_root / "ontology" / "README.md").write_text(
                "| canonical ontology | `onto.md` |\n", encoding="utf-8"
            )
            (product_root / "ontology" / "onto.md").write_text("v1\n", encoding="utf-8")
            (product_root / "prd" / "README.md").write_text("| 主 PRD | `main.md` |\n", encoding="utf-8")
            (product_root / "prd" / "main.md").write_text("v1\n", encoding="utf-8")
            before = _run(["newproduct", "--company-base", str(base)])
            self.assertEqual(before.returncode, 2)
            config = base / "config" / "company.yaml"
            config.write_text(
                config.read_text(encoding="utf-8")
                + "  - id: newproduct\n    name: New Product\n    code_root: null\n",
                encoding="utf-8",
            )
            after = _run(["newproduct", "--company-base", str(base)])
            self.assertEqual(after.returncode, 0, after.stderr)
            payload = json.loads(after.stdout)
            self.assertEqual(payload["product"]["id"], "newproduct")
            self.assertEqual(payload["authority"]["ontology"]["status"], "complete")
            batch = _run(["--all", "--company-base", str(base)])
            self.assertEqual(batch.returncode, 0, batch.stderr)
            self.assertEqual(
                [entry["product_id"] for entry in json.loads(batch.stdout)["products"]],
                ["newproduct"],
            )


if __name__ == "__main__":
    unittest.main()
