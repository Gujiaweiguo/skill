"""Phase-2 tests for backfill_source: all-suffix raw matching, unique prefix
containment rescue, mapping application (authored->none, missing-target skip),
and whole-base index construction."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import backfill_source as bs  # noqa: E402


class BaseIndexTest(unittest.TestCase):
    def _base(self, tmp):
        base = Path(tmp)
        for rel in ["incoming/hd/会员系统方案.pptx",
                    "90-legacy/snap/input/会员系统方案.pptx",
                    "raw/会员系统方案.pptx.md",
                    "materials/x.md", "out/y.docx", ".git/HEAD"]:
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x", encoding="utf-8")
        return base

    def test_index_excludes_projections_prefers_non_legacy(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = self._base(tmp)
            by_basename, by_stem = bs.build_base_index(base)
            paths = by_basename["会员系统方案.pptx"]
            self.assertEqual(len(paths), 2)
            self.assertEqual(paths[0], base / "incoming/hd/会员系统方案.pptx")
            self.assertNotIn("x.md", by_stem)
            self.assertNotIn("y.docx", by_basename)

    def test_unique_rep_prefers_non_legacy_and_rejects_ambiguity(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = self._base(tmp)
            by_basename, _ = bs.build_base_index(base)
            hit = by_basename["会员系统方案.pptx"]
            self.assertEqual(bs.unique_rep(hit, base),
                             base / "incoming/hd/会员系统方案.pptx")
            # two distinct non-legacy copies -> ambiguous (different content)
            (base / "40-delivery").mkdir()
            (base / "40-delivery" / "会员系统方案.pptx").write_text("different", encoding="utf-8")
            by_basename, _ = bs.build_base_index(base)
            self.assertIsNone(bs.unique_rep(by_basename["会员系统方案.pptx"], base))
            # byte-identical duplicates collapse to one logical original
            # (representative is whichever sorts first — content is identical)
            (base / "40-delivery" / "会员系统方案.pptx").write_bytes(
                (base / "incoming/hd/会员系统方案.pptx").read_bytes())
            rep = bs.unique_rep(by_basename["会员系统方案.pptx"], base)
            self.assertIsNotNone(rep)
            self.assertEqual(rep.read_bytes(),
                             (base / "incoming/hd/会员系统方案.pptx").read_bytes())


class RawSuffixTest(unittest.TestCase):
    def test_all_suffix_keys_longest_first(self):
        keys = bs.raw_suffix_keys(
            "03-competitors_会员系统_科传_科传crm3.0操作手册.pdf")
        self.assertEqual(keys[-1], "科传crm3.0操作手册.pdf")
        self.assertEqual(keys[0],
                         "03-competitors_会员系统_科传_科传crm3.0操作手册.pdf")

    def test_shortest_suffix_rescues_decorated_raw_md(self):
        """The decorated raw name must hit the index via a SHORT suffix —
        the old longest-only logic returned no-suffix-match for exactly this
        shape (phase-1 finding: 22/29 raw unmatched)."""
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = Path(tmp)
            orig = base / "incoming" / "会员系统竞对" / "科传" / "科传crm3.0操作手册.pdf"
            orig.parent.mkdir(parents=True)
            orig.write_text("x", encoding="utf-8")
            raw_md = base / "raw" / "03-competitors_会员系统_科传_科传crm3.0操作手册.pdf.md"
            raw_md.parent.mkdir(parents=True)
            raw_md.write_text("# 内容", encoding="utf-8")
            by_basename, _ = bs.build_base_index(base)
            hit, reason, rule = bs.backfill_raw_md(raw_md, base, by_basename)
            self.assertEqual(hit, orig)
            self.assertEqual(rule, "raw-suffix-fixed")

    def test_ambiguous_suffix_not_matched(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = Path(tmp)
            for i, d in enumerate(("incoming/a", "incoming/b")):
                p = base / d / "方案.docx"
                p.parent.mkdir(parents=True)
                p.write_text(f"content-{i}", encoding="utf-8")
            raw_md = base / "raw" / "03-x_方案.docx.md"
            raw_md.parent.mkdir(parents=True)
            raw_md.write_text("# 内容", encoding="utf-8")
            by_basename, _ = bs.build_base_index(base)
            hit, reason, _ = bs.backfill_raw_md(raw_md, base, by_basename)
            self.assertIsNone(hit)
            self.assertEqual(reason, "no-suffix-match")


class PrefixRescueTest(unittest.TestCase):
    def _ctx(self, tmp):
        base = Path(tmp)
        orig = base / "incoming" / "业绩" / "近三年服务业绩表-蓝联科技.xlsx"
        orig.parent.mkdir(parents=True)
        orig.write_text("x", encoding="utf-8")
        md = base / "materials" / "14-achievements" / "近三年服务业绩.md"
        md.parent.mkdir(parents=True)
        md.write_text("---\ntitle: x\n---\n业绩内容", encoding="utf-8")
        return base, orig, md

    def test_unique_containment_rescues(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, orig, md = self._ctx(tmp)
            _, by_stem = bs.build_base_index(base)
            got, conf, rule = bs.match_material(
                md, {}, {}, {}, base_stem_index=by_stem, base=base)
            self.assertEqual(got, orig)
            self.assertEqual(rule, "prefix-rescue")

    def test_ambiguous_containment_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, orig, md = self._ctx(tmp)
            other = base / "incoming" / "其他" / "近三年服务业绩表-友商.xlsx"
            other.parent.mkdir(parents=True)
            other.write_text("x", encoding="utf-8")
            _, by_stem = bs.build_base_index(base)
            got, conf, rule = bs.match_material(
                md, {}, {}, {}, base_stem_index=by_stem, base=base)
            self.assertIsNone(got)

    def test_short_stem_not_rescued(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, orig, md = self._ctx(tmp)
            md = md.with_name("业绩.md")
            md.write_text("x", encoding="utf-8")
            _, by_stem = bs.build_base_index(base)
            got, _, _ = bs.match_material(
                md, {}, {}, {}, base_stem_index=by_stem, base=base)
            self.assertIsNone(got)


class MappingTest(unittest.TestCase):
    def _tree(self, tmp):
        base = Path(tmp)
        orig = base / "incoming" / "hd" / "海鼎会员方案.pptx"
        orig.parent.mkdir(parents=True)
        orig.write_text("x", encoding="utf-8")
        for rel in ["materials/05-competitors/accept.md",
                    "materials/01-company-overview/authored.md",
                    "materials/05-competitors/missing-target.md",
                    "materials/05-competitors/review-row.md"]:
            p = base / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("---\ntitle: t\n---\n正文", encoding="utf-8")
        tsv = base / "proposal.tsv"
        tsv.write_text(
            "file\tproposed_source\tbucket\n"
            f"materials/05-competitors/accept.md\t{orig.relative_to(base).as_posix()}\taccept\n"
            "materials/01-company-overview/authored.md\tNONE\tauthored\n"
            "materials/05-competitors/missing-target.md\tincoming/gone.pptx\taccept\n"
            "materials/05-competitors/review-row.md\tincoming/hd/x.docx\tmid\n",
            encoding="utf-8")
        return base, tsv, orig

    def test_load_mapping_filters_buckets(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, tsv, _ = self._tree(tmp)
            m = bs.load_mapping(tsv)
            self.assertEqual(set(m), {
                "materials/05-competitors/accept.md",
                "materials/01-company-overview/authored.md",
                "materials/05-competitors/missing-target.md"})

    def test_dry_run_then_apply(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, tsv, orig = self._tree(tmp)
            for extra in (["--dry-run"], []):
                proc = subprocess.run(
                    ["uv", "run", "python", str(SCRIPTS_DIR / "backfill_source.py"),
                     str(base), "--mapping", str(tsv),
                     "--json-report", str(base / "rep.json")] + extra,
                    capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent))
                self.assertEqual(proc.returncode, 0, proc.stderr)
            rep = json.loads((base / "rep.json").read_text(encoding="utf-8"))
            by_rule = {m["applied_rule"] for m in rep["matched"]}
            self.assertIn("mapping", by_rule)
            self.assertIn("mapping-authored", by_rule)
            self.assertEqual(rep["mapping_missing"],
                             [{"file": "materials/05-competitors/missing-target.md",
                               "missing_target": "incoming/gone.pptx"}])
            acc = (base / "materials/05-competitors/accept.md").read_text(encoding="utf-8")
            self.assertIn('source: "incoming/hd/海鼎会员方案.pptx"', acc)
            auth = (base / "materials/01-company-overview/authored.md").read_text(encoding="utf-8")
            self.assertIn('source: "none"', auth)
            rev = (base / "materials/05-competitors/review-row.md").read_text(encoding="utf-8")
            self.assertNotIn("source:", rev)
            miss = (base / "materials/05-competitors/missing-target.md").read_text(encoding="utf-8")
            self.assertNotIn("source:", miss)

    def test_has_source_files_never_rewritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, tsv, orig = self._tree(tmp)
            md = base / "materials/01-company-overview/authored.md"
            md.write_text('---\ntitle: t\nsource: "keep"\n---\n正文', encoding="utf-8")
            proc = subprocess.run(
                ["uv", "run", "python", str(SCRIPTS_DIR / "backfill_source.py"),
                 str(base), "--mapping", str(tsv),
                 "--json-report", str(base / "rep2.json")],
                capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('source: "keep"', md.read_text(encoding="utf-8"))


class LegacyFilterTest(unittest.TestCase):
    def test_filter_selects_only_high_ratio_legacy_materials(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = Path(tmp)
            cj = base / "cand.json"
            cj.write_text(json.dumps({"results": [
                {"file": "materials/a.md", "best": {"path": "90-legacy/x/a.md", "ratio": 1.0, "legacy": True}},
                {"file": "materials/b.md", "best": {"path": "incoming/b.docx", "ratio": 0.99, "legacy": False}},
                {"file": "materials/c.md", "best": {"path": "90-legacy/x/c.md", "ratio": 0.6, "legacy": True}},
                {"file": "raw/d.md", "best": {"path": "90-legacy/x/d.md", "ratio": 1.0, "legacy": True}},
                {"file": "materials/e.md", "best": None},
            ]}), encoding="utf-8")
            tsv = base / "p3.tsv"
            rows = bs.filter_legacy_accepts(cj, tsv)
            self.assertEqual(rows, [("materials/a.md", "90-legacy/x/a.md")])
            self.assertEqual(
                tsv.read_text(encoding="utf-8"),
                "file\tproposed_source\tbucket\n"
                "materials/a.md\t90-legacy/x/a.md\taccept\n")


class WalkErrorReportingTest(unittest.TestCase):
    """os.walk + explicit onerror discipline (AGENTS.md「os.walk 静默跳过陷阱」,
    2026-10-02): unreadable directories must be recorded and surfaced in the
    report, never silently skipped; "not discovered" must not be conflated
    with "does not exist"."""

    def _base(self, tmp):
        base = Path(tmp)
        orig = base / "incoming" / "hd" / "方案.pptx"
        orig.parent.mkdir(parents=True)
        orig.write_text("x", encoding="utf-8")
        return base

    def test_deep_subdirectory_recursion(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = self._base(tmp)
            deep = base / "30-products" / "lnkcre" / "ontology" / "refs" / "深层数据字典.xlsx"
            deep.parent.mkdir(parents=True)
            deep.write_text("x", encoding="utf-8")
            by_basename, _ = bs.build_base_index(base)
            self.assertIn(deep, by_basename.get(deep.name.lower(), []))

    @unittest.skipIf(os.geteuid() == 0, "chmod-based unreadable dir does not block root")
    def test_unreadable_dir_recorded_not_silent(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = self._base(tmp)
            secret = base / "30-products" / "secret"
            secret.mkdir(parents=True)
            (secret / "机密.docx").write_text("x", encoding="utf-8")
            secret.chmod(0o000)
            try:
                errors = []
                by_basename, _ = bs.build_base_index(base, errors)
                # traversal continues past the unreadable dir
                self.assertIn("方案.pptx", by_basename)
                self.assertEqual(len(errors), 1)
                self.assertIn("secret", errors[0])
            finally:
                secret.chmod(0o755)

    def test_walk_onerror_invoked_and_traversal_continues(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = self._base(tmp)
            real_walk = os.walk

            def fake_walk(top, onerror=None, **kwargs):
                if onerror is None:
                    raise AssertionError("os.walk must be given an explicit onerror")
                onerror(OSError(13, "Permission denied", str(base / "secret")))
                return real_walk(top, onerror=onerror, **kwargs)

            with mock.patch("os.walk", side_effect=fake_walk):
                errors = []
                by_basename, _ = bs.build_base_index(base, errors)
            self.assertIn("方案.pptx", by_basename)
            self.assertEqual(len(errors), 1)
            self.assertIn("secret", errors[0])

    def test_main_report_json_contains_discovery_errors(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = self._base(tmp)
            for d in ("raw", "materials"):
                (base / d).mkdir()
            real_walk = os.walk

            def fake_walk(top, onerror=None, **kwargs):
                if onerror is None:
                    raise AssertionError("os.walk must be given an explicit onerror")
                onerror(OSError(13, "Permission denied", str(base / "secret")))
                return real_walk(top, onerror=onerror, **kwargs)

            rep_path = base / "rep.json"
            with mock.patch("os.walk", side_effect=fake_walk), \
                 mock.patch.object(sys, "argv", [
                     "backfill_source.py", str(base), "--dry-run",
                     "--json-report", str(rep_path)]):
                bs.main()
            rep = json.loads(rep_path.read_text(encoding="utf-8"))
            self.assertEqual(len(rep["discovery_errors"]), 1)
            self.assertIn("secret", rep["discovery_errors"][0])


if __name__ == "__main__":
    unittest.main()
