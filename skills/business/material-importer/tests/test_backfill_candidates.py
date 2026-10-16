"""Tests for backfill_candidates (phase-1 analysis, read-only vs base)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import backfill_candidates as bc  # noqa: E402


class IndexTest(unittest.TestCase):
    def test_index_excludes_raw_materials_out_and_includes_incoming(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = Path(tmp)
            for rel in ["incoming/海鼎/会员系统方案.pptx",
                        "10-strategy/战略规划.docx",
                        "raw/会员系统方案.pptx.md",
                        "materials/03-products/x.md",
                        "out/proposals/y.docx",
                        ".git/HEAD"]:
                p = base / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x", encoding="utf-8")
            idx = bc.build_index(base)
            stems = set(idx)
            self.assertIn("会员系统方案", stems)          # incoming/
            self.assertIn("战略规划", stems)              # 10-strategy/
            self.assertNotIn("会员系统方案.pptx", stems)  # raw/ excluded
            self.assertNotIn("x", stems)                 # materials/ excluded
            self.assertNotIn("y", stems)                 # out/ excluded

    def test_iter_index_skips_junk_dirs(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = Path(tmp)
            for rel in ["30-products/lnkcre/ontology/_media/a.pdf",
                        "30-products/lnkcre/ontology/INDEX.md",
                        "incoming/parsed/b.docx"]:
                p = base / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("x", encoding="utf-8")
            files = [p.name for p in bc.iter_index_files(base)]
            self.assertIn("INDEX.md", files)
            self.assertNotIn("a.pdf", files)
            self.assertNotIn("b.docx", files)


class CandidateTest(unittest.TestCase):
    IDX = {"海鼎会员系统解决方案v3": ["incoming/hd/海鼎会员系统解决方案v3.pptx"],
           "科传crm操作手册": ["03-competitors/科传crm操作手册.pdf"],
           "安胜旗数字化营销解决方案": ["incoming/asq/安胜旗数字化营销解决方案.pdf"]}

    def test_ratio_ranking_orders_top3(self):
        top3 = bc.top_candidates("海鼎会员系统解决方案v2", self.IDX)
        self.assertEqual(top3[0]["path"], "incoming/hd/海鼎会员系统解决方案v3.pptx")
        self.assertGreater(top3[0]["ratio"], 0.9)
        self.assertLessEqual(len(top3), 3)
        ratios = [c["ratio"] for c in top3]
        self.assertEqual(ratios, sorted(ratios, reverse=True))

    def test_no_candidates_below_floor_pruned(self):
        top3 = bc.top_candidates("完全无关的名字zzz", self.IDX)
        self.assertEqual(top3, [])


class RawStripTest(unittest.TestCase):
    def test_suffix_keys_longest_to_shortest(self):
        self.assertEqual(
            bc.raw_suffix_keys("03-competitors_会员系统_科传_科传crm3.0操作手册.pdf.md"),
            ["03-competitors_会员系统_科传_科传crm3.0操作手册.pdf",
             "会员系统_科传_科传crm3.0操作手册.pdf",
             "科传_科传crm3.0操作手册.pdf",
             "科传crm3.0操作手册.pdf"])
        self.assertEqual(
            bc.raw_suffix_keys("02租赁业务流程_业务应用规范.docx.md"),
            ["02租赁业务流程_业务应用规范.docx", "业务应用规范.docx"])

    def test_empty_when_no_orig_ext(self):
        self.assertEqual(bc.raw_suffix_keys("随便一个文件.md"), [])


class AuthoredTest(unittest.TestCase):
    def test_name_patterns_authored(self):
        self.assertTrue(bc.is_authored_guess("materials/01-company-overview/公司简介_V2_无商管有会员.md",
                                             "公司简介_v2_无商管有会员"))
        self.assertTrue(bc.is_authored_guess("materials/xx/组织架构.md", "组织架构"))

    def test_dir_hints_authored(self):
        self.assertTrue(bc.is_authored_guess("materials/01-company-overview/abc.md", "abc"))

    def test_ordinary_projection_not_authored(self):
        self.assertFalse(bc.is_authored_guess("materials/05-competitors/海鼎会员方案-v3.md",
                                              "海鼎会员方案-v3"))


class AnalyseTest(unittest.TestCase):
    def _make_base(self, tmp):
        base = Path(tmp)
        orig = base / "incoming" / "hd" / "海鼎会员系统解决方案v3.pptx"
        orig.parent.mkdir(parents=True)
        orig.write_text("x", encoding="utf-8")
        (base / "materials" / "05-competitors").mkdir(parents=True)
        (base / "materials" / "01-company-overview").mkdir(parents=True)
        rep = {"unmatched": [
            {"file": "materials/05-competitors/海鼎会员系统解决方案v2.md",
             "reason": "no-unique-hint"},
            {"file": "materials/01-company-overview/组织架构.md",
             "reason": "no-unique-hint"},
            {"file": "raw/03-competitors_会员系统_科传_科传crm3.0操作手册.pdf.md",
             "reason": "raw/no-suffix-match"},
        ]}
        rp = base / "raw" / "_backfill_report.json"
        rp.parent.mkdir(parents=True)
        rp.write_text(json.dumps(rep), encoding="utf-8")
        return base, rp

    def test_analyse_classifies_candidate_vs_authored(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, rp = self._make_base(tmp)
            results, idx = bc.analyse(base, rp, floor=0.6)
            by_file = {r["file"]: r for r in results}
            cand = by_file["materials/05-competitors/海鼎会员系统解决方案v2.md"]
            self.assertEqual(cand["class"], "candidate")
            self.assertGreater(cand["best"]["ratio"], 0.9)
            auth = by_file["materials/01-company-overview/组织架构.md"]
            self.assertEqual(auth["class"], "authored")
            self.assertFalse(auth.get("best") and auth["best"]["ratio"] >= 0.6)

    def test_analyse_raw_exact_suffix_hit(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, rp = self._make_base(tmp)
            # make the raw suffix-key match an indexed original exactly
            orig = base / "30-products" / "x"
            orig.mkdir(parents=True)
            (orig / "科传crm3.0操作手册.pdf").write_text("x", encoding="utf-8")
            results, _ = bc.analyse(base, rp, floor=0.6)
            raw_r = [r for r in results if r["file"].startswith("raw/")][0]
            self.assertEqual(raw_r["best"]["ratio"], 1.0)
            self.assertIn("科传crm3.0操作手册.pdf", raw_r["best"]["path"])

    def test_proposal_rows_buckets(self):
        results = [
            {"file": "a.md", "class": "candidate",
             "best": {"path": "incoming/a.pptx", "ratio": 0.91}},
            {"file": "a2.md", "class": "candidate",
             "best": {"path": "90-legacy/2026-x/in/a2.pptx", "ratio": 0.99, "legacy": True}},
            {"file": "b.md", "class": "candidate",
             "best": {"path": "incoming/b.pptx", "ratio": 0.65}},
            {"file": "c.md", "class": "authored",
             "best": {"path": "incoming/c.pptx", "ratio": 0.42}},
            {"file": "d.md", "class": "candidate",
             "best": {"path": "incoming/d.pptx", "ratio": 0.30}},
        ]
        rows = dict((f, (s, b)) for f, s, b in bc.proposal_rows(results))
        self.assertEqual(rows["a.md"], ("incoming/a.pptx", "accept"))
        self.assertEqual(rows["a2.md"], ("REVIEW", "review"))  # legacy-only copy
        self.assertEqual(rows["b.md"], ("REVIEW", "mid"))
        self.assertEqual(rows["c.md"], ("NONE", "authored"))
        self.assertEqual(rows["d.md"], ("REVIEW", "review"))


if __name__ == "__main__":
    unittest.main()
