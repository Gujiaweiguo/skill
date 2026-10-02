"""link_images 回归测试：media 排除按路径段而非子串 + 读失败 WARN。

背景：此前 `"/media" in root` 会把 mediadata/ 等目录一并排除，
其中的断引用永远得不到修复。
"""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import os
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import link_images  # noqa: E402


def _skip_if_root(test: unittest.TestCase) -> None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        test.skipTest("permission checks do not apply when running as root")


BROKEN_REF_MD = "# 标题\n\n![截图](shot1.jpg)\n"


class MainTest(unittest.TestCase):
    def test_media_exclusion_is_path_segment_not_substring(self) -> None:
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            media_dir = materials / "media"
            mediadata_dir = materials / "mediadata"
            media_dir.mkdir(parents=True)
            mediadata_dir.mkdir(parents=True)
            (media_dir / "skipme.md").write_text(BROKEN_REF_MD, encoding="utf-8")
            (mediadata_dir / "fixme.md").write_text(BROKEN_REF_MD, encoding="utf-8")
            (materials / "top.md").write_text(BROKEN_REF_MD, encoding="utf-8")

            stdout = StringIO()
            argv = ["link_images.py", str(materials), "--dry-run"]
            with patch.object(sys, "argv", argv):
                with redirect_stdout(stdout):
                    link_images.main()

        # media/ 排除；mediadata/（前缀撞车）与顶层文件都处理
        self.assertIn("修复 2 个文件", stdout.getvalue())

    def test_unreadable_material_file_warns_and_is_skipped(self) -> None:
        _skip_if_root(self)
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            materials.mkdir()
            locked = materials / "locked.md"
            locked.write_text(BROKEN_REF_MD, encoding="utf-8")
            os.chmod(locked, 0o000)
            stderr = StringIO()
            argv = ["link_images.py", str(materials), "--dry-run"]
            try:
                with patch.object(sys, "argv", argv):
                    with redirect_stdout(StringIO()), redirect_stderr(stderr):
                        link_images.main()
            finally:
                os.chmod(locked, 0o755)

        self.assertIn("[WARN]", stderr.getvalue())
        self.assertIn(str(locked), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
