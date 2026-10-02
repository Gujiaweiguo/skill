"""ocr_extract 回归测试：无法打开的图片必须进入 skipped_unreadable。

背景：此前尺寸探测失败静默 continue，叠加增量 checkpoint 契约
（slides.jsonl 只记已处理）时，坏图片会从 OCR 产出中无声消失——
「打不开」被当成「不存在」。
"""

from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import ocr_extract  # noqa: E402


class ScanImagesTest(unittest.TestCase):
    def test_unreadable_images_are_reported_not_swallowed(self) -> None:
        from PIL import Image

        with TemporaryDirectory() as tmp:
            media_dir = Path(tmp) / "source_media"
            media_dir.mkdir()
            good = media_dir / "slide1.png"
            image = Image.new("RGB", (100, 100), color=(30, 30, 30))
            image.save(good)
            corrupt = media_dir / "slide2.png"
            corrupt.write_bytes(b"this is not an image")

            stderr = StringIO()
            with redirect_stderr(stderr):
                refs, skipped = ocr_extract.scan_images([media_dir])

        self.assertEqual([r.path.name for r in refs], ["slide1.png"])
        self.assertEqual(skipped, [str(corrupt)])
        self.assertIn("图片无法打开", stderr.getvalue())
        self.assertIn("共 1 张", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
