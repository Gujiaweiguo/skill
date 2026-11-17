"""Golden fixture tests: pin real-world files that drove the 2026-10/11 fixes.

- 福州香格里拉 xlsx → column-aware date coerce + header-scan width basis
  (257-column sheet, preface region, percent rendering, notes sidecars)
- 明源 产品拆分 pptx → pptx_table_guard merged-cells detection
- lanlnk v7 manifest → provenance_inventory outputs 对象数组零假阳性

Fixtures live in the external docs repo and are referenced by absolute path +
sha256 (tests/fixtures_registry.json); binaries are never copied into this repo.
File missing → SKIP (external dependency). sha mismatch → FAIL ("source drifted,
update expectations") because the golden assumption no longer holds.
"""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"

import sys

sys.path.insert(0, str(SCRIPTS_DIR))

import convert_excel  # noqa: E402
import pptx_table_guard  # noqa: E402
import provenance_inventory as pi  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_registry() -> dict:
    return json.loads(
        (TESTS_DIR / "fixtures_registry.json").read_text(encoding="utf-8")
    )


class GoldenFixtureTestBase(unittest.TestCase):
    registry = _load_registry()

    def get_fixture(self, name: str) -> dict:
        for fx in self.registry["fixtures"]:
            if fx["name"] == name:
                return fx
        self.fail(f"fixture {name!r} not in registry")

    def resolve(self, fx: dict) -> Path | None:
        """None → SKIP (missing); raises self.failureException on sha drift."""
        path = Path(fx["path"])
        if not path.exists():
            return None
        actual = _sha256(path)
        if actual != fx["sha256"]:
            self.fail(
                f"{path} sha256 drifted ({actual} != {fx['sha256']}): "
                "source drifted, update expectations"
            )
        return path


class GoldenXlsxShangriLaTest(GoldenFixtureTestBase):
    """福州香格里拉输出凭证表：CSV 路由 + 前言区 + 批注边车 + 百分比 + manifest。"""

    def setUp(self) -> None:
        fx = self.get_fixture("福州香格里拉中心_输出凭证_20231121")
        path = self.resolve(fx)
        if path is None:
            self.skipTest("golden fixture not present on this box")
        self.fx = fx
        self.src = path
        self.tmp = tempfile.TemporaryDirectory(prefix="golden_xlsx_")
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name)
        result = convert_excel.process_file(self.src, self.out)
        self.assertEqual(result.startswith("CSV"), True, result)
        self.exp = fx["expectations"]

    def test_qa_csv_header(self) -> None:
        csv_path = self.out / "csv" / f"{self.src.stem}_QA管理表.csv"
        self.assertTrue(csv_path.exists(), f"missing {csv_path.name}")
        header = csv_path.read_text(encoding="utf-8-sig").splitlines()[0]
        self.assertTrue(
            header.startswith(self.exp["qa_csv_header_starts_with"]),
            f"header was: {header!r}",
        )

    def test_qa_notes_sidecar(self) -> None:
        notes = (
            self.out / "csv" / f"{self.src.stem}_QA管理表.csv.notes.md"
        ).read_text(encoding="utf-8")
        for token in self.exp["qa_notes_contains"]:
            self.assertIn(token, notes)

    def test_voucher_notes_sidecar(self) -> None:
        notes = (
            self.out / "csv" / f"{self.src.stem}_凭证式样.csv.notes.md"
        ).read_text(encoding="utf-8")
        for token in self.exp["voucher_notes_contains"]:
            self.assertIn(token, notes)

    def test_voucher_percent_strings(self) -> None:
        csv_text = (
            self.out / "csv" / f"{self.src.stem}_凭证式样.csv"
        ).read_text(encoding="utf-8")
        for token in self.exp["voucher_csv_percent_strings"]:
            self.assertIn(token, csv_text)

    def test_manifest_provenance(self) -> None:
        records = json.loads(
            (self.out / "_manifest.json").read_text(encoding="utf-8")
        )
        rec = next(r for r in records if r["source_sha256"] == self.fx["sha256"])
        self.assertEqual(rec["extractor_version"], self.exp["manifest_extractor_version"])
        self.assertEqual(rec["source_path"], str(self.src.resolve()))


class GoldenPptxMingyuanTest(GoldenFixtureTestBase):
    """明源产品拆分 pptx：slide 1/2 命中 merged-cells 可疑表格。"""

    def test_detect_merged_cells(self) -> None:
        fx = self.get_fixture("产品拆分20210629")
        path = self.resolve(fx)
        if path is None:
            self.skipTest("golden fixture not present on this box")
        result = pptx_table_guard.detect_file(path)
        self.assertIsNone(result["error"])
        slides = {f["slide"] for f in result["findings"]}
        for expected_slide in fx["expectations"]["suspect_slides"]:
            self.assertIn(expected_slide, slides)
        for f in result["findings"]:
            if f["slide"] in fx["expectations"]["suspect_slides"]:
                self.assertIn(fx["expectations"]["reasons_include"], f["reasons"])


class GoldenManifestV7OutputsTest(GoldenFixtureTestBase):
    """lanlnk v7 manifest（outputs 对象数组）：provenance_inventory 零假阳性回归。

    真实 manifest（sha 钉线，只读）物化到临时合成基座：列出的 artifacts/
    outputs 文件以占位内容创建 → run_inventory 不得对 outputs 列出的文件
    报 outputs_missing，且全部计入 manifest 覆盖（不复制外部仓任何字节进本仓，
    也不写外部仓任何文件）。
    """

    def test_outputs_object_array_paths_resolvable(self) -> None:
        fx = self.get_fixture("lanlnk-v7-outputs-manifest")
        path = self.resolve(fx)
        if path is None:
            self.skipTest("golden fixture not present on this box")
        records = json.loads(path.read_text(encoding="utf-8"))
        exp = fx["expectations"]
        # 真实形态锁：fingerprint_format 1 + outputs 全部为含 path 的对象
        for r in records:
            self.assertEqual(r["fingerprint_format"],
                             exp["fingerprint_format"])
            for o in r["outputs"]:
                self.assertIsInstance(o, dict)
                self.assertIn("path", o)
        listed: set[str] = set()
        for r in records:
            listed.update(r.get("artifacts") or [])
            listed.update(o["path"] for o in r["outputs"])
        with tempfile.TemporaryDirectory(prefix="golden_manifest_") as td:
            base = Path(td) / "co"
            (base / "config").mkdir(parents=True)
            (base / "config" / "company.yaml").write_text(
                "name: co\n", encoding="utf-8")
            sub = base / "raw" / "golden"
            sub.mkdir(parents=True)
            # manifest 原字节入临时基座（合成内容占位，不读外部仓投影正文）
            (sub / "_manifest.json").write_bytes(path.read_bytes())
            for rel in sorted(listed):
                target = sub / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("golden-placeholder\n", encoding="utf-8")
            report = pi.run_inventory(base)
            self.assertEqual(report["gaps"]["outputs_missing"], [])
            for rel in sorted(listed):
                # 该 manifest 列出的均为 csv / notes 边车 → manifest 覆盖必须命中
                self.assertEqual(
                    report["items"][f"raw/golden/{rel}"].get("manifest_coverage"),
                    ["raw/golden/_manifest.json"],
                    f"outputs/artifacts 列出文件未被覆盖: {rel}")


if __name__ == "__main__":
    unittest.main()
