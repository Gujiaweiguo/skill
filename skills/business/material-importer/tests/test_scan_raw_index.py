from hashlib import sha256
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import json
import os
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import scan_raw_index  # noqa: E402


def _skip_if_root(test: unittest.TestCase) -> None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        test.skipTest("permission checks do not apply when running as root")


class BuildEntryTest(unittest.TestCase):
    def test_identity_is_deterministic_and_company_root_independent(self) -> None:
        # Given
        with TemporaryDirectory() as first_tmp, TemporaryDirectory() as second_tmp:
            first_raw = Path(first_tmp) / "raw" / "source" / "report.md"
            second_raw = Path(second_tmp) / "raw" / "source" / "report.md"
            first_raw.parent.mkdir(parents=True)
            second_raw.parent.mkdir(parents=True)
            first_raw.write_bytes(b"same bytes")
            second_raw.write_bytes(b"same bytes")

            # When
            first = scan_raw_index.build_entry(first_raw, first_raw.parents[1], {})
            second = scan_raw_index.build_entry(second_raw, second_raw.parents[1], {})

        # Then
        self.assertEqual(first["source_id"], "raw:source/report.md")
        self.assertEqual(first["source_id"], second["source_id"])
        self.assertEqual(first["content_sha256"], second["content_sha256"])
        self.assertNotIn(first_tmp, first["source_id"])

    def test_fingerprint_changes_when_raw_bytes_change(self) -> None:
        # Given
        with TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            raw_dir.mkdir()
            raw_file = raw_dir / "report.md"
            raw_file.write_bytes(b"version one")

            # When
            original = scan_raw_index.build_entry(raw_file, raw_dir, {})
            raw_file.write_bytes(b"version two")
            changed = scan_raw_index.build_entry(raw_file, raw_dir, {})

        # Then
        self.assertNotEqual(original["content_sha256"], changed["content_sha256"])

    def test_root_raw_file_has_no_inferred_original_source(self) -> None:
        # Given
        with TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            raw_dir.mkdir()
            raw_file = raw_dir / "report.md"
            raw_file.write_bytes(b"raw content")

            # When
            entry = scan_raw_index.build_entry(raw_file, raw_dir, {})

        # Then
        self.assertEqual(entry["imported_from"], "")
        self.assertEqual(entry["source_id"], "raw:report.md")

    def test_legacy_entry_without_identity_fields_remains_readable(self) -> None:
        # Given
        legacy = {
            "imported_at": "2026-06-18",
            "imported_from": "",
            "consumed_by": ["materials/03-products/example.md"],
            "unconsumed_sections": [],
            "needs_review": False,
        }

        # When
        loaded = legacy

        # Then
        self.assertEqual(loaded["imported_at"], "2026-06-18")
        self.assertEqual(loaded["imported_from"], "")
        self.assertEqual(loaded["consumed_by"], ["materials/03-products/example.md"])
        self.assertNotIn("source_id", loaded)
        self.assertNotIn("content_sha256", loaded)


class FindRawFilesTest(unittest.TestCase):
    def test_collects_md_and_csv_excluding_media_and_hidden(self) -> None:
        with TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            for rel in [
                "topic/a.docx.md",
                "topic/csv/清单.csv",
                "topic/_media/ignored.csv",
                ".hidden/x.csv",
                "_index.json",
            ]:
                p = raw_dir / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x", encoding="utf-8")

            found, failures = scan_raw_index.find_raw_files(raw_dir)

        self.assertEqual(
            [str(p.relative_to(raw_dir)) for p in found],
            ["topic/a.docx.md", "topic/csv/清单.csv"],
        )
        self.assertEqual(failures, [])

    def test_walk_failure_is_reported_not_swallowed(self) -> None:
        _skip_if_root(self)
        with TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            (raw_dir / "topic").mkdir(parents=True)
            (raw_dir / "topic" / "a.md").write_text("x", encoding="utf-8")
            locked = raw_dir / "locked"
            locked.mkdir()
            (locked / "b.md").write_text("x", encoding="utf-8")
            os.chmod(locked, 0o000)
            try:
                found, failures = scan_raw_index.find_raw_files(raw_dir)
            finally:
                os.chmod(locked, 0o755)

        self.assertEqual([p.name for p in found], ["a.md"])
        self.assertEqual(len(failures), 1)
        self.assertIn(str(locked), failures[0].location)
        self.assertTrue(failures[0].message)


class LoadMaterialsContentTest(unittest.TestCase):
    def test_unreadable_material_file_is_reported_not_swallowed(self) -> None:
        _skip_if_root(self)
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            materials_dir = base / "materials"
            materials_dir.mkdir()
            good = materials_dir / "good.md"
            good.write_text("内容", encoding="utf-8")
            locked = materials_dir / "locked.md"
            locked.write_text("内容", encoding="utf-8")
            os.chmod(locked, 0o000)
            try:
                contents, failures = scan_raw_index.load_materials_content(materials_dir)
            finally:
                os.chmod(locked, 0o755)

        self.assertEqual(list(contents.keys()), ["materials/good.md"])
        self.assertEqual(len(failures), 1)
        self.assertIn(str(locked), failures[0].location)


class ScanMainIncompleteTest(unittest.TestCase):
    """main() 的失败可见性行为：不可读输入必须落 WARN 与 scan_incomplete 标记。"""

    @staticmethod
    def _make_base(tmp: str) -> Path:
        base = Path(tmp)
        (base / "config").mkdir(parents=True, exist_ok=True)
        (base / "config" / "company.yaml").write_text("brand: test\n", encoding="utf-8")
        return base

    def _run_main(self, raw_dir: Path, materials_dir: Path) -> tuple[int, str]:
        stderr = StringIO()
        argv = [
            "scan_raw_index.py",
            "--raw-dir", str(raw_dir),
            "--materials-dir", str(materials_dir),
        ]
        with patch.dict(os.environ, {"COMPANY_BASE": str(raw_dir.parents[0])}, clear=False):
            with patch.object(sys, "argv", argv):
                with redirect_stderr(stderr):
                    rc = scan_raw_index.main()
        return rc, stderr.getvalue()

    def test_unreadable_material_flags_entries_and_warns(self) -> None:
        _skip_if_root(self)
        with TemporaryDirectory() as tmp:
            base = self._make_base(tmp)
            raw_dir = base / "raw"
            raw_dir.mkdir()
            (raw_dir / "报告.docx.md").write_text("内容", encoding="utf-8")
            materials_dir = base / "materials"
            materials_dir.mkdir()
            consumer = materials_dir / "案例.md"
            consumer.write_text(
                '---\nsource: "raw/报告.docx.md"\n---\n正文', encoding="utf-8"
            )
            os.chmod(consumer, 0o000)
            try:
                rc, stderr = self._run_main(raw_dir, materials_dir)
            finally:
                os.chmod(consumer, 0o755)

            index = json.loads((raw_dir / "_index.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertIn("[WARN]", stderr)
        self.assertIn("consumed_by 检测未覆盖", stderr)
        entry = index["报告.docx.md"]
        self.assertEqual(entry["consumed_by"], [])
        self.assertTrue(entry["needs_review"])
        self.assertTrue(entry["scan_incomplete"])

    def test_clean_scan_has_no_scan_incomplete_flag(self) -> None:
        with TemporaryDirectory() as tmp:
            base = self._make_base(tmp)
            raw_dir = base / "raw"
            raw_dir.mkdir()
            (raw_dir / "报告.docx.md").write_text("内容", encoding="utf-8")
            materials_dir = base / "materials"
            materials_dir.mkdir()

            rc, stderr = self._run_main(raw_dir, materials_dir)

            index = json.loads((raw_dir / "_index.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertNotIn("scan_incomplete", index["报告.docx.md"])
        self.assertNotIn("[WARN]", stderr)

    def test_merge_preserves_entries_under_inaccessible_subtree(self) -> None:
        _skip_if_root(self)
        with TemporaryDirectory() as tmp:
            base = self._make_base(tmp)
            raw_dir = base / "raw"
            (raw_dir / "topic").mkdir(parents=True)
            (raw_dir / "topic" / "a.md").write_text("内容", encoding="utf-8")
            locked = raw_dir / "locked"
            locked.mkdir()
            (locked / "b.md").write_text("内容", encoding="utf-8")
            materials_dir = base / "materials"
            materials_dir.mkdir()

            rc1, _ = self._run_main(raw_dir, materials_dir)
            self.assertEqual(rc1, 0)
            first = json.loads((raw_dir / "_index.json").read_text(encoding="utf-8"))
            self.assertIn("locked/b.md", first)

            os.chmod(locked, 0o000)
            try:
                rc2, stderr = self._run_main(raw_dir, materials_dir)
            finally:
                os.chmod(locked, 0o755)

            second = json.loads((raw_dir / "_index.json").read_text(encoding="utf-8"))

        self.assertEqual(rc2, 0)
        self.assertIn("locked/b.md", second)
        self.assertTrue(second["locked/b.md"]["scan_incomplete"])
        self.assertNotIn("scan_incomplete", second["topic/a.md"])
        self.assertIn("保留并标记 scan_incomplete", stderr)


class FindConsumersTest(unittest.TestCase):
    def test_matches_exact_raw_filename_in_source_frontmatter(self) -> None:
        materials = {
            "materials/case.md": '---\nsource: "raw/report.docx.md"\n---\ncontent',
        }

        consumers = scan_raw_index.find_consumers("report.docx.md", materials)

        self.assertEqual(consumers, ["materials/case.md"])

    def test_matches_raw_filename_in_source_file_frontmatter(self) -> None:
        materials = {
            "materials/case.md": '---\nsource_file: "raw/report.docx.md"\n---',
        }

        consumers = scan_raw_index.find_consumers("report.docx.md", materials)

        self.assertEqual(consumers, ["materials/case.md"])

    def test_matches_second_source_in_semicolon_separated_frontmatter(self) -> None:
        materials = {
            "materials/case.md": '---\nsource: "raw/other.xlsx.md; raw/report.docx.md"\n---',
        }

        consumers = scan_raw_index.find_consumers("report.docx.md", materials)

        self.assertEqual(consumers, ["materials/case.md"])

    def test_matches_original_filename_in_source_frontmatter(self) -> None:
        materials = {
            "materials/case.md": '---\nsource: "raw/report.docx.md; report.docx"\n---',
        }

        consumers = scan_raw_index.find_consumers("report.docx.md", materials)

        self.assertEqual(consumers, ["materials/case.md"])

    def test_matches_raw_media_path(self) -> None:
        materials = {
            "materials/case.md": "![image](../../raw/report_media/image.png)",
        }

        consumers = scan_raw_index.find_consumers("report.docx.md", materials)

        self.assertEqual(consumers, ["materials/case.md"])

    def test_ignores_extensionless_phrase_in_prose(self) -> None:
        materials = {
            "materials/guide.md": "商户约谈记录应归档。",
        }

        consumers = scan_raw_index.find_consumers("商户约谈记录.md", materials)

        self.assertEqual(consumers, [])

    def test_ignores_filename_prefix_inside_a_longer_filename(self) -> None:
        materials = {
            "materials/guide.md": '---\nsource: "raw/report.docx.mdx"\n---',
        }

        consumers = scan_raw_index.find_consumers("report.docx.md", materials)

        self.assertEqual(consumers, [])

    def test_does_not_match_media_path_for_another_document(self) -> None:
        materials = {
            "materials/case.md": "![image](raw/reporting_media/image.png)",
        }

        consumers = scan_raw_index.find_consumers("report.docx.md", materials)

        self.assertEqual(consumers, [])

    def test_does_not_match_media_directory_outside_raw(self) -> None:
        materials = {
            "materials/case.md": "![image](assets/report_media/image.png)",
        }

        consumers = scan_raw_index.find_consumers("report.docx.md", materials)

        self.assertEqual(consumers, [])

    def test_matches_csv_filename_in_source_file_frontmatter(self) -> None:
        materials = {
            "materials/bi.md": '---\nsource_file: "raw/12-bi-platform/csv/标准报表.csv"\n---',
        }

        consumers = scan_raw_index.find_consumers("标准报表.csv", materials)

        self.assertEqual(consumers, ["materials/bi.md"])

    def test_matches_csv_path_inside_parenthesized_source(self) -> None:
        materials = {
            "materials/sop.md": (
                '---\nsource: "借鉴明源体系（raw/x/csv/实施转服务CheckList_v2.csv）+ 蓝联适配。"\n---'
            ),
        }

        consumers = scan_raw_index.find_consumers("实施转服务CheckList_v2.csv", materials)

        self.assertEqual(consumers, ["materials/sop.md"])

    def test_ignores_bare_csv_stem_in_prose(self) -> None:
        materials = {
            "materials/guide.md": "标准报表 应定期归档。",
        }

        consumers = scan_raw_index.find_consumers("标准报表.csv", materials)

        self.assertEqual(consumers, [])

    def test_ignores_underscore_prefixed_sibling_csv(self) -> None:
        materials = {
            "materials/sop.md": '---\nsource: "raw/x/csv/_合同录入及时率.csv"\n---',
        }

        consumers = scan_raw_index.find_consumers("合同录入及时率.csv", materials)

        self.assertEqual(consumers, [])

    def test_matches_glob_reference_in_source(self) -> None:
        materials = {
            "materials/deep.md": (
                '---\nsource: "raw/prd-lnkcrm/01/深中润/csv/会籍产品包_*.csv"\n---'
            ),
        }

        consumers = scan_raw_index.find_consumers("会籍产品包_云旗航空.csv", materials)

        self.assertEqual(consumers, ["materials/deep.md"])

    def test_glob_does_not_match_different_prefix(self) -> None:
        materials = {
            "materials/deep.md": (
                '---\nsource: "raw/prd-lnkcrm/01/深中润/csv/会籍产品包_*.csv"\n---'
            ),
        }

        consumers = scan_raw_index.find_consumers("权益产品包_云旗航空.csv", materials)

        self.assertEqual(consumers, [])


class CsvEntryTest(unittest.TestCase):
    def test_csv_imported_from_is_extensionless(self) -> None:
        with TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            csv_file = raw_dir / "12-bi-platform" / "csv" / "标准报表.csv"
            csv_file.parent.mkdir(parents=True)
            csv_file.write_text("模块,报表\n", encoding="utf-8")

            entry = scan_raw_index.build_entry(csv_file, raw_dir, {})

        self.assertEqual(entry["imported_from"], "incoming/12-bi-platform/标准报表")
        self.assertEqual(entry["source_id"], "raw:12-bi-platform/csv/标准报表.csv")

    def test_csv_consumer_and_sha_roundtrip(self) -> None:
        with TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            csv_file = raw_dir / "12-bi-platform" / "csv" / "标准报表.csv"
            csv_file.parent.mkdir(parents=True)
            csv_file.write_bytes(b"a,b\n1,2\n")
            materials = {
                "materials/12-bi-platform/标准报表.md": (
                    '---\nsource_file: "raw/12-bi-platform/csv/标准报表.csv"\n---'
                ),
            }

            entry = scan_raw_index.build_entry(csv_file, raw_dir, materials)

        self.assertEqual(entry["consumed_by"], ["materials/12-bi-platform/标准报表.md"])
        self.assertFalse(entry["needs_review"])
        self.assertEqual(
            entry["content_sha256"],
            sha256(b"a,b\n1,2\n").hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
