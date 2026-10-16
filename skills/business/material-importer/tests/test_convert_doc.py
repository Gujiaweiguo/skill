"""tests for scripts/convert_doc.py — 溯源携带的 markitdown 包装器。

通过 subprocess 跑 `uv run scripts/convert_doc.py in out`（cwd=skill 目录），
与真实调用方式一致。
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document
from pptx import Presentation
from pptx.util import Inches

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "convert_doc.py"


def run_script(src: Path, out: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(src), str(out)],
        cwd=str(SKILL_DIR),
        capture_output=True,
        text=True,
        timeout=300,
    )


class ConvertDocDocxTest(unittest.TestCase):
    def test_docx_provenance_header_and_body(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "company.yaml").write_text("company: test\n", encoding="utf-8")
            docx_path = root / "测试文档.docx"
            doc = Document()
            doc.add_paragraph("溯源契约测试正文内容")
            doc.save(str(docx_path))

            out = root / "out" / "测试文档.docx.md"
            proc = run_script(docx_path, out)
            self.assertEqual(proc.returncode, 0, proc.stderr)

            text = out.read_text(encoding="utf-8")
            lines = text.splitlines()
            self.assertTrue(lines[0].startswith("<!-- source: "), lines[0])
            # base 相对路径（config/company.yaml 存在于同根）
            self.assertIn("source: 测试文档.docx -->", lines[0])
            self.assertEqual(
                lines[1],
                f"<!-- source_sha256: {hashlib.sha256(docx_path.read_bytes()).hexdigest()} -->",
            )
            self.assertTrue(lines[2].startswith("<!-- extracted_by: markitdown via convert_doc.py v"), lines[2])
            self.assertTrue(lines[3].startswith("<!-- fidelity: "), lines[3])
            # docx 无 pptx_suspects 行
            self.assertNotIn("pptx_suspects", text)
            self.assertIn("溯源契约测试正文内容", text)


class ConvertDocPptxTest(unittest.TestCase):
    def _make_pptx(self, path: Path, cols: int):
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        shape = slide.shapes.add_table(2, cols, Inches(0.5), Inches(0.5), Inches(9), Inches(1))
        table = shape.table
        for r in range(2):
            for c in range(cols):
                table.cell(r, c).text = f"R{r}C{c}"
        prs.save(str(path))

    def test_pptx_wide_table_flagged(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            pptx_path = root / "wide.pptx"
            self._make_pptx(pptx_path, cols=11)

            out = root / "wide.pptx.md"
            proc = run_script(pptx_path, out)
            self.assertEqual(proc.returncode, 0, proc.stderr)

            text = out.read_text(encoding="utf-8")
            self.assertIn("pptx_suspects:", text)
            self.assertIn("slide 1", text)
            self.assertIn("cols>10", text)

    def test_pptx_clean_table_none(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            pptx_path = root / "clean.pptx"
            self._make_pptx(pptx_path, cols=4)

            out = root / "clean.pptx.md"
            proc = run_script(pptx_path, out)
            self.assertEqual(proc.returncode, 0, proc.stderr)

            text = out.read_text(encoding="utf-8")
            self.assertIn("pptx_suspects: none", text)


class ConvertDocFailureTest(unittest.TestCase):
    def test_corrupt_input_exit1_no_output(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            bad = root / "corrupt.pptx"
            bad.write_bytes(b"not a real pptx file at all")
            out = root / "corrupt.pptx.md"

            proc = run_script(bad, out)
            self.assertEqual(proc.returncode, 1)
            self.assertFalse(out.exists(), "失败时不得写出部分产物")


if __name__ == "__main__":
    unittest.main()
