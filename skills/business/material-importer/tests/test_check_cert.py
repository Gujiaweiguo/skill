"""check_cert 回归测试：raw 排除按路径段而非子串。

背景：此前 `"raw" in root` 会把 rawdata/ 等目录一并排除——
「目录名撞前缀」不该让证照从有效期报告里消失。
"""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import check_cert  # noqa: E402


CERT_MD = """---
id: "qual-20260101-001"
type: "资质荣誉"
name: "ISO27001认证"
expires: "2030-01-01"
issued: "2026-01-01"
issuer: "认证机构"
---

证书正文。
"""


class ScanMaterialsTest(unittest.TestCase):
    def test_raw_exclusion_is_path_segment_not_substring(self) -> None:
        with TemporaryDirectory() as tmp:
            materials = Path(tmp) / "materials"
            raw_dir = materials / "raw"
            rawdata_dir = materials / "rawdata"
            raw_dir.mkdir(parents=True)
            rawdata_dir.mkdir(parents=True)
            (raw_dir / "skipme.md").write_text(CERT_MD, encoding="utf-8")
            (rawdata_dir / "processme.md").write_text(CERT_MD, encoding="utf-8")

            results = check_cert.scan_materials(str(materials))

        files = sorted(r["file"] for r in results)
        self.assertEqual(files, ["rawdata/processme.md"])
        self.assertEqual(results[0]["status"], "valid")


if __name__ == "__main__":
    unittest.main()
