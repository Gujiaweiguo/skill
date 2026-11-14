"""extract_images 锁文件守卫测试（harden-material-import-provenance 3.1/3.5）。

- 单文件模式：basename `~$` 前缀 → skipped + rc=3，不进入提取逻辑；
- 批量模式：既有 `~$` 跳过行为保持，其余文件正常处理；
- 用合成非 PK 字节样例（触发 BadZipFile 的真实锁文件形态）。
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import extract_images  # noqa: E402


def _make_pptx(path: Path) -> Path:
    from pptx import Presentation

    prs = Presentation()
    prs.save(str(path))
    return path


class ExtractImagesLockFileTest(unittest.TestCase):
    def test_single_file_lock_exit3_no_extraction(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            lock = root / "~$xxx.pptx"
            lock.write_bytes(b"\x00\x01office-lock-garbage-not-zip")
            raw_dir = root / "raw"
            rc = extract_images.main([str(lock), "--json", "--raw-dir", str(raw_dir)])
            self.assertEqual(rc, 3)
            self.assertFalse(raw_dir.exists(), "锁文件不得进入提取逻辑/创建输出")

    def test_single_file_lock_docx_exit3(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            lock = root / "~$y.docx"
            lock.write_bytes(b"lock-bytes")
            rc = extract_images.main(
                [str(lock), "--raw-dir", str(root / "raw")]
            )
            self.assertEqual(rc, 3)

    def test_batch_lock_skipped_others_processed(self) -> None:
        """批量遇锁文件其余正常：锁文件不产出，正常 pptx 照常处理，rc=0。"""
        import contextlib
        import io

        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            src_dir = root / "in"
            src_dir.mkdir()
            (src_dir / "~$bad.pptx").write_bytes(b"\x00\x01lock-garbage")
            ok = _make_pptx(src_dir / "ok.pptx")
            raw_dir = root / "raw"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = extract_images.main(
                    [str(src_dir), "--json", "--raw-dir", str(raw_dir)]
                )
            self.assertEqual(rc, 0, "批量遇锁文件不得崩溃/非零")
            payload = json.loads(buf.getvalue()[buf.getvalue().index("{"):])
            files = [f["file"] for f in payload["files"]]
            self.assertIn("ok.pptx", files)
            self.assertNotIn("~$bad.pptx", files)
            self.assertTrue((raw_dir / "ok_media").exists())
            self.assertFalse((raw_dir / "~$bad_media").exists())


if __name__ == "__main__":
    unittest.main()
