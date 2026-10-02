from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import fix_frontmatter  # noqa: E402


class FixFrontmatterTest(unittest.TestCase):
    def test_raw_exclusion_is_path_segment_not_substring(self) -> None:
        # Given：raw/ 必须排除，rawdata/（前缀撞车）必须处理，二者都在配置目录前缀下
        with TemporaryDirectory() as tmp_dir:
            materials = Path(tmp_dir) / "materials"
            raw_target = materials / "16-customers" / "raw"
            rawdata_target = materials / "16-customers" / "rawdata"
            raw_target.mkdir(parents=True)
            rawdata_target.mkdir(parents=True)
            (raw_target / "skipme.md").write_text("# 原始\n正文\n", encoding="utf-8")
            (rawdata_target / "processme.md").write_text("# 修补\n正文\n", encoding="utf-8")

            # When
            log, _ = fix_frontmatter.process(
                str(materials), str(materials), dry_run=True
            )

        # Then
        self.assertEqual(
            [r for _, r, _ in log], ["16-customers/rawdata/processme.md"]
        )

    def test_process_preserves_body_when_frontmatter_is_missing(self) -> None:
        # Given
        original = "# Example\n\n客户需求正文。\n"
        with TemporaryDirectory() as tmp_dir:
            materials = Path(tmp_dir) / "materials"
            target = materials / "16-customers"
            target.mkdir(parents=True)
            document = target / "example.md"
            document.write_text(original, encoding="utf-8")

            # When
            log, _ = fix_frontmatter.process(
                str(target), str(materials), dry_run=False
            )

            # Then
            output = document.read_text(encoding="utf-8")
            self.assertEqual(len(log), 1)
            self.assertTrue(output.endswith(original))
            self.assertIn('type: "客户资料"', output)


if __name__ == "__main__":
    unittest.main()
