"""validate_material 回归测试：raw 排除按路径段而非子串。

背景：此前 `"/raw" in root` 会把 raw-notes/、rawdata/ 等目录一并排除，
校验报告对其中素材「无声缺失」。
"""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import validate_material  # noqa: E402


VALID_MD = """---
id: "customer-20260101-001"
type: "客户资料"
name: "示例客户"
domain: ["通用"]
status: "complete"
created: "2026-01-01"
---

正文。
"""


class ValidTypesTest(unittest.TestCase):
    def test_init_template_type_is_valid_and_clean(self) -> None:
        """初始化模板 是合法 type（2026-10-16 竞品导入 24 件使用），且不产生 warning。"""
        self.assertIn("初始化模板", validate_material.VALID_TYPES)
        md = VALID_MD.replace('type: "客户资料"', 'type: "初始化模板"')
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            materials.mkdir()
            (materials / "tpl.md").write_text(md, encoding="utf-8")

            stdout = StringIO()
            argv = ["validate_material.py", str(materials), "--json"]
            with patch.object(sys, "argv", argv):
                with redirect_stdout(stdout):
                    validate_material.main()

            report = json.loads(stdout.getvalue())

        self.assertEqual(report["summary"]["invalid"], 0)
        self.assertEqual(report["files"][0]["warnings"], [])


class MainTest(unittest.TestCase):
    def test_raw_exclusion_is_path_segment_not_substring(self) -> None:
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            raw_dir = materials / "raw"
            rawnotes_dir = materials / "raw-notes"
            raw_dir.mkdir(parents=True)
            rawnotes_dir.mkdir(parents=True)
            (raw_dir / "skipme.md").write_text(VALID_MD, encoding="utf-8")
            (rawnotes_dir / "checkme.md").write_text(VALID_MD, encoding="utf-8")

            stdout = StringIO()
            argv = ["validate_material.py", str(materials), "--json"]
            with patch.object(sys, "argv", argv):
                with redirect_stdout(stdout):
                    validate_material.main()

            report = json.loads(stdout.getvalue())

        # file 字段是相对 CWD 的展示路径（既有行为），按后缀断言
        files = sorted(r["file"].replace("\\", "/") for r in report["files"])
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].endswith("materials/raw-notes/checkme.md"))
        self.assertNotIn("raw/skipme.md", files[0])


class IdUniquenessTest(unittest.TestCase):
    def test_duplicate_id_marks_both_holders_invalid(self) -> None:
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            materials.mkdir(parents=True)
            (materials / "a.md").write_text(VALID_MD, encoding="utf-8")
            (materials / "b.md").write_text(
                VALID_MD.replace("示例客户", "示例客户B"), encoding="utf-8"
            )

            stdout = StringIO()
            argv = ["validate_material.py", str(materials), "--json"]
            with patch.object(sys, "argv", argv):
                with redirect_stdout(stdout):
                    with self.assertRaises(SystemExit) as cm:
                        validate_material.main()

            report = json.loads(stdout.getvalue())

        self.assertEqual(cm.exception.code, 1)
        self.assertEqual(report["summary"]["invalid"], 2)
        by_file = {r["file"]: r for r in report["files"]}
        for fname, r in by_file.items():
            self.assertFalse(r["valid"], fname)
            self.assertTrue(any("id 重复" in e for e in r["errors"]), fname)
            # 错误信息必须指认另一个持有者
            other = "b.md" if fname.endswith("a.md") else "a.md"
            self.assertTrue(any(other in e for e in r["errors"]), fname)

    def test_extracted_dir_is_skipped_for_id_check(self) -> None:
        """_extracted/ 是机器 OCR 聚合产物（非人工策展记录），不参与 id 唯一性检查。"""
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            extracted = materials / "_extracted"
            extracted.mkdir(parents=True)
            (materials / "curated.md").write_text(VALID_MD, encoding="utf-8")
            (extracted / "aggregate.md").write_text(VALID_MD, encoding="utf-8")

            stdout = StringIO()
            argv = ["validate_material.py", str(materials), "--json"]
            with patch.object(sys, "argv", argv):
                with redirect_stdout(stdout):
                    validate_material.main()

            report = json.loads(stdout.getvalue())

        self.assertEqual(report["summary"]["total"], 1)
        self.assertEqual(report["summary"]["invalid"], 0)
        self.assertTrue(report["files"][0]["file"].endswith("curated.md"))

    def test_unique_ids_all_pass(self) -> None:
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            materials.mkdir(parents=True)
            (materials / "a.md").write_text(VALID_MD, encoding="utf-8")
            (materials / "b.md").write_text(
                VALID_MD.replace("customer-20260101-001", "customer-20260101-002"),
                encoding="utf-8",
            )

            stdout = StringIO()
            argv = ["validate_material.py", str(materials), "--json"]
            with patch.object(sys, "argv", argv):
                with redirect_stdout(stdout):
                    validate_material.main()

            report = json.loads(stdout.getvalue())

        self.assertEqual(report["summary"]["total"], 2)
        self.assertEqual(report["summary"]["invalid"], 0)
        for r in report["files"]:
            self.assertEqual(r["errors"], [])


class FrontmatterDelimiterTest(unittest.TestCase):
    """delimiter 回归组（fix-material-frontmatter-delimiters）。

    契约：`---` 仅在独立成行时作为 frontmatter 边界；值内 `---` 不影响解析；
    错误类别四类保持。断言值见 change design.md 实测表。
    """

    def _parse(self, tmp: Path, name: str, content: str) -> tuple:
        p = tmp / name
        p.write_text(content, encoding="utf-8", newline="")
        return validate_material.parse_frontmatter(str(p))

    def test_unquoted_scalar_with_dashes_preserved(self) -> None:
        """未加引号标量值内含 ---：解析成功且值保全原文（现状静默截断为 成本）。"""
        with TemporaryDirectory() as tmp:
            data, err = self._parse(
                Path(tmp),
                "unquoted.md",
                "---\n"
                'id: "customer-20260101-001"\n'
                "source: 成本---成本管理典型问题库.xlsx\n"
                "---\n"
                "\n正文。\n",
            )
        self.assertIsNone(err)
        self.assertEqual(data["source"], "成本---成本管理典型问题库.xlsx")

    def test_quoted_scalar_with_dashes_preserved(self) -> None:
        """加引号标量值内含 ---：解析成功且值保全原文（现状 YAML 解析错误）。"""
        with TemporaryDirectory() as tmp:
            data, err = self._parse(
                Path(tmp),
                "quoted.md",
                "---\n"
                'id: "customer-20260101-001"\n'
                'source: "成本---成本管理典型问题库.xlsx"\n'
                "---\n"
                "\n正文。\n",
            )
        self.assertIsNone(err)
        self.assertEqual(data["source"], "成本---成本管理典型问题库.xlsx")

    def test_normal_lf_frontmatter(self) -> None:
        with TemporaryDirectory() as tmp:
            data, err = self._parse(
                Path(tmp), "lf.md", "---\nid: x\ncreated: 2026-01-01\n---\n正文\n"
            )
        self.assertIsNone(err)
        self.assertEqual(data["id"], "x")

    def test_crlf_frontmatter(self) -> None:
        with TemporaryDirectory() as tmp:
            data, err = self._parse(
                Path(tmp),
                "crlf.md",
                "---\r\nid: x\r\ncreated: 2026-01-01\r\n---\r\n\r\n正文\r\n",
            )
        self.assertIsNone(err)
        self.assertEqual(data["id"], "x")

    def test_closing_delimiter_trailing_whitespace(self) -> None:
        with TemporaryDirectory() as tmp:
            data, err = self._parse(
                Path(tmp), "trail.md", "---\nid: x\n--- \n正文\n"
            )
        self.assertIsNone(err)
        self.assertEqual(data["id"], "x")

    def test_missing_open_delimiter(self) -> None:
        with TemporaryDirectory() as tmp:
            data, err = self._parse(Path(tmp), "noopen.md", "id: x\n---\n正文\n")
        self.assertIsNone(data)
        self.assertEqual(err, "缺少 YAML frontmatter（不以 --- 开头）")

    def test_unclosed_block(self) -> None:
        with TemporaryDirectory() as tmp:
            data, err = self._parse(Path(tmp), "unclosed.md", "---\nid: x\n正文\n")
        self.assertIsNone(data)
        self.assertEqual(err, "YAML frontmatter 未闭合")

    def test_invalid_yaml(self) -> None:
        with TemporaryDirectory() as tmp:
            data, err = self._parse(
                Path(tmp), "badyaml.md", "---\nid: [unclosed\n---\n正文\n"
            )
        self.assertIsNone(data)
        self.assertTrue(err.startswith("YAML 解析错误"), err)

    def test_non_mapping(self) -> None:
        with TemporaryDirectory() as tmp:
            data, err = self._parse(Path(tmp), "list.md", "---\n- a\n- b\n---\n正文\n")
        self.assertIsNone(data)
        self.assertEqual(err, "frontmatter 不是合法的键值对")

    def test_four_dashes_opening_is_missing_frontmatter(self) -> None:
        """---- 开头：归类为缺少 YAML frontmatter（现状为 YAML 解析错误，既定例外 2）。"""
        with TemporaryDirectory() as tmp:
            data, err = self._parse(
                Path(tmp), "four.md", "----\nid: x\n----\n正文\n"
            )
        self.assertIsNone(data)
        self.assertEqual(err, "缺少 YAML frontmatter（不以 --- 开头）")


if __name__ == "__main__":
    unittest.main()
