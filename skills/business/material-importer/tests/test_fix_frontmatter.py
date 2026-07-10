from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import fix_frontmatter  # noqa: E402


class FixFrontmatterTest(unittest.TestCase):
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
