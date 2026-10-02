"""add_frontmatter 回归测试：has_frontmatter 三态契约。

背景（发现≠判断）：has_frontmatter 此前读失败返回 False，把「读不了」
当成「没有 frontmatter」，不可读文件会被排进补写队列——失败观察变成了
修改决策。本文件锁定：True/False/None 三态，None 时 process_dir 跳过并 WARN。
"""

from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import os
import sys
from tempfile import TemporaryDirectory
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import add_frontmatter  # noqa: E402


def _skip_if_root(test: unittest.TestCase) -> None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        test.skipTest("permission checks do not apply when running as root")


class HasFrontmatterTest(unittest.TestCase):
    def test_true_for_frontmatter_file(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.md"
            p.write_text("---\nname: x\n---\n正文", encoding="utf-8")

            self.assertTrue(add_frontmatter.has_frontmatter(str(p)))

    def test_false_for_plain_markdown(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.md"
            p.write_text("# 标题\n正文", encoding="utf-8")

            self.assertFalse(add_frontmatter.has_frontmatter(str(p)))

    def test_none_and_warn_for_unreadable_file(self) -> None:
        _skip_if_root(self)
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "locked.md"
            p.write_text("x", encoding="utf-8")
            os.chmod(p, 0o000)
            stderr = StringIO()
            try:
                with redirect_stderr(stderr):
                    result = add_frontmatter.has_frontmatter(str(p))
            finally:
                os.chmod(p, 0o755)

        self.assertIsNone(result)
        self.assertIn("[WARN]", stderr.getvalue())
        self.assertIn(str(p), stderr.getvalue())


class ProcessDirTest(unittest.TestCase):
    def test_raw_exclusion_is_path_segment_not_substring(self) -> None:
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            raw_dir = materials / "raw" / "13-competitors" / "qimao"
            rawnotes_dir = materials / "raw-notes" / "13-competitors" / "qimao"
            raw_dir.mkdir(parents=True)
            rawnotes_dir.mkdir(parents=True)
            (raw_dir / "skipme.md").write_text("# 原始\n正文", encoding="utf-8")
            (rawnotes_dir / "processme.md").write_text("# 修补\n正文", encoding="utf-8")

            done, _skipped, counters = add_frontmatter.process_dir(
                str(materials), str(materials), "2026-01-01", dry_run=True
            )

        done_paths = [d[0] for d in done]
        self.assertEqual(done_paths, [str(rawnotes_dir / "processme.md")])
        self.assertEqual(counters, {"qimao": 1})

    def test_unreadable_file_is_not_enqueued_for_rewrite(self) -> None:
        _skip_if_root(self)
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            vendor_dir = materials / "13-competitors" / "qimao"
            vendor_dir.mkdir(parents=True)
            good = vendor_dir / "good.md"
            good.write_text("# 旗茂功能\n正文", encoding="utf-8")
            locked = vendor_dir / "locked.md"
            locked.write_text("# 不可读\n正文", encoding="utf-8")
            os.chmod(locked, 0o000)
            stderr = StringIO()
            try:
                with redirect_stderr(stderr):
                    done, _skipped, counters = add_frontmatter.process_dir(
                        str(materials), str(materials), "2026-01-01", dry_run=True
                    )
            finally:
                os.chmod(locked, 0o755)

        done_paths = [d[0] for d in done]
        self.assertEqual(done_paths, [str(good)])
        self.assertEqual(counters, {"qimao": 1})
        self.assertIn("[WARN]", stderr.getvalue())
        self.assertIn(str(locked), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
