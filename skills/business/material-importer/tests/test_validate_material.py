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


if __name__ == "__main__":
    unittest.main()
