"""Phase-2 tests for backfill_source: all-suffix raw matching, unique prefix
containment rescue, mapping application (authored->none, missing-target skip),
and whole-base index construction."""

import hashlib
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


class BackfillPersistenceTest(unittest.TestCase):
    """Task 4.2: backfill writes persist provenance_class + at-backfill hash
    semantics into the products themselves (raw comment block / materials
    frontmatter), not only into the one-shot report; new writes never use
    the bare `source_sha256` field name. Chinese + space filenames."""

    def _base(self, tmp):
        base = Path(tmp) / "base"
        (base / "config").mkdir(parents=True)
        (base / "config" / "company.yaml").write_text(
            "company: test\n", encoding="utf-8")
        orig = base / "incoming" / "hd" / "海鼎 会员 方案.pptx"
        orig.parent.mkdir(parents=True)
        orig.write_text("原始字节", encoding="utf-8")
        raw_md = base / "raw" / "海鼎 会员 方案.pptx.md"
        raw_md.parent.mkdir()
        raw_md.write_text("# 内容", encoding="utf-8")
        mat = base / "materials" / "05-competitors" / "海鼎 会员 方案.md"
        mat.parent.mkdir(parents=True)
        mat.write_text("---\ntitle: t\n---\n正文", encoding="utf-8")
        return base, orig, raw_md, mat

    def _run(self, base, extra=()):
        rep = base.parent / "rep.json"
        proc = subprocess.run(
            ["uv", "run", "python", str(SCRIPTS_DIR / "backfill_source.py"),
             str(base), "--json-report", str(rep)] + list(extra),
            capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(rep.read_text(encoding="utf-8"))

    def test_backfill_persists_class_and_at_backfill_hash(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, orig, raw_md, mat = self._base(tmp)
            rep = self._run(base)
            sha = hashlib.sha256(orig.read_bytes()).hexdigest()

            raw_text = raw_md.read_text(encoding="utf-8")
            self.assertIn("<!-- source: incoming/hd/海鼎 会员 方案.pptx -->",
                          raw_text)
            self.assertIn(
                "<!-- provenance_class: candidate-association -->", raw_text)
            self.assertIn(f"<!-- source_sha256_at_backfill: {sha} -->",
                          raw_text)
            self.assertRegex(raw_text, r"<!-- backfilled_at: \d{4}-\d{2}-\d{2} -->")
            self.assertIn("backfilled", raw_text)  # extracted_by marker kept
            # new writes must NOT use the bare old field name
            self.assertNotIn("<!-- source_sha256: ", raw_text)

            mat_text = mat.read_text(encoding="utf-8")
            self.assertIn('source: "incoming/hd/海鼎 会员 方案.pptx"', mat_text)
            self.assertIn("provenance_class: candidate-association", mat_text)
            self.assertIn(f"source_sha256_at_backfill: {sha}", mat_text)
            self.assertRegex(mat_text, r"backfilled_at: \d{4}-\d{2}-\d{2}")
            self.assertNotIn("\nsource_sha256:", mat_text)

            for m in rep["matched"]:
                self.assertEqual(m["provenance_class"],
                                 "candidate-association")
                self.assertEqual(m["hash_semantics"], "at-backfill")

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, orig, raw_md, mat = self._base(tmp)
            before = {p: p.read_bytes()
                      for p in base.rglob("*") if p.is_file()}
            self._run(base, extra=["--dry-run"])
            after = {p: p.read_bytes()
                     for p in base.rglob("*") if p.is_file()}
            self.assertEqual(before, after)
            self.assertNotIn("provenance_class:",
                             raw_md.read_text(encoding="utf-8"))

    def test_authored_row_gets_no_provenance_class(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, _, _, _ = self._base(tmp)
            mat = base / "materials" / "01-company-overview" / "自撰.md"
            mat.parent.mkdir(parents=True)
            mat.write_text("---\ntitle: t\n---\n正文", encoding="utf-8")
            tsv = base.parent / "m.tsv"
            tsv.write_text("file\tproposed_source\tbucket\n"
                           "materials/01-company-overview/自撰.md\tNONE\tauthored\n",
                           encoding="utf-8")
            rep = base.parent / "rep.json"
            proc = subprocess.run(
                ["uv", "run", "python", str(SCRIPTS_DIR / "backfill_source.py"),
                 str(base), "--mapping", str(tsv),
                 "--json-report", str(rep)],
                capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            rep_json = json.loads(rep.read_text(encoding="utf-8"))
            text = mat.read_text(encoding="utf-8")
            self.assertIn('source: "none"', text)
            self.assertNotIn("provenance_class:", text)
            entry = [m for m in rep_json["matched"] if m["file"].endswith("自撰.md")]
            self.assertTrue(entry)
            self.assertNotIn("provenance_class", entry[0])


class ClassifyRecordTest(unittest.TestCase):
    """D7 compatibility reader: old backfilled records keep backfill nature
    regardless of hash field name; bare unmarked source_sha256 → unknown;
    recorded-at-conversion requires all three elements (converter signature
    + in-base source + valid 64-hex hash) and never upgrades by field name
    alone."""

    HEX = "a" * 64

    def _base(self, tmp):
        base = Path(tmp)
        orig = base / "incoming" / "hd" / "方案.pptx"
        orig.parent.mkdir(parents=True)
        orig.write_text("x", encoding="utf-8")
        return base, orig

    def test_old_backfilled_with_old_field_name_stays_backfill(self):
        header = ("<!-- source: incoming/hd/方案.pptx -->\n"
                  f"<!-- source_sha256: {self.HEX} -->\n"
                  "<!-- extracted_by: markitdown (pre-existing artifact, "
                  "backfilled 2026-01-01) -->\n")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, _ = self._base(tmp)
            got = bs.classify_record(header, base)
            self.assertEqual(got["provenance_class"],
                             "candidate-association")
            self.assertEqual(got["hash_semantics"], "at-backfill")

    def test_new_field_name_backfilled_stays_backfill(self):
        header = ("<!-- source: incoming/hd/方案.pptx -->\n"
                  "<!-- provenance_class: candidate-association -->\n"
                  f"<!-- source_sha256_at_backfill: {self.HEX} -->\n"
                  "<!-- backfilled_at: 2026-11-14 -->\n"
                  "<!-- extracted_by: markitdown (pre-existing artifact, "
                  "backfilled 2026-11-14) -->\n")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, _ = self._base(tmp)
            got = bs.classify_record(header, base)
            self.assertEqual(got["hash_semantics"], "at-backfill")

    def test_bare_source_sha256_without_markers_is_unknown(self):
        header = ("<!-- source: incoming/hd/方案.pptx -->\n"
                  f"<!-- source_sha256: {self.HEX} -->\n"
                  "<!-- extracted_by: markitdown -->\n")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, _ = self._base(tmp)
            got = bs.classify_record(header, base)
            self.assertIsNone(got["provenance_class"])
            self.assertEqual(got["hash_semantics"], "unknown")

    def test_converter_signature_in_base_with_valid_hash(self):
        header = ("<!-- source: incoming/hd/方案.pptx -->\n"
                  f"<!-- source_sha256: {self.HEX} -->\n"
                  "<!-- extracted_by: markitdown via convert_doc.py v3 -->\n")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, _ = self._base(tmp)
            got = bs.classify_record(header, base)
            self.assertEqual(got["provenance_class"], "recorded-at-conversion")
            self.assertEqual(got["hash_semantics"], "at-conversion")

    def test_converter_signature_source_outside_base_not_recorded(self):
        header = ("<!-- source: /etc/方案.pptx -->\n"
                  f"<!-- source_sha256: {self.HEX} -->\n"
                  "<!-- extracted_by: markitdown via convert_doc.py v3 -->\n")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, _ = self._base(tmp)
            got = bs.classify_record(header, base)
            self.assertIsNone(got["provenance_class"])
            self.assertEqual(got["hash_semantics"], "unknown")

    def test_converter_signature_invalid_hash_not_recorded(self):
        header = ("<!-- source: incoming/hd/方案.pptx -->\n"
                  "<!-- source_sha256: nothex -->\n"
                  "<!-- extracted_by: markitdown via convert_doc.py v3 -->\n")
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, _ = self._base(tmp)
            got = bs.classify_record(header, base)
            self.assertEqual(got["hash_semantics"], "unknown")

    def test_manifest_extractor_field_shape(self):
        header = {"source_path": "incoming/hd/方案.pptx",
                  "extractor": "markitdown via convert_excel.py v2",
                  "source_sha256": self.HEX}
        text = "\n".join(f"{k}: {v}" for k, v in header.items())
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, _ = self._base(tmp)
            got = bs.classify_record(text, base)
            self.assertEqual(got["provenance_class"], "recorded-at-conversion")


class WrongSourceSuspectsTest(unittest.TestCase):
    """Has-source files are never rewritten; unresolvable declared sources
    land in wrong_source_suspects with assessment + suggestion only."""

    def _base(self, tmp):
        base = Path(tmp) / "base"
        orig = base / "incoming" / "hd" / "方案.pptx"
        orig.parent.mkdir(parents=True)
        orig.write_text("x", encoding="utf-8")
        bad = base / "materials" / "05-competitors" / "bad.md"
        bad.parent.mkdir(parents=True)
        bad.write_text('---\ntitle: t\nsource: "incoming/gone.pptx"\n---\n正文',
                       encoding="utf-8")
        good = base / "materials" / "05-competitors" / "good.md"
        good.write_text(
            f'---\ntitle: t\nsource: "{orig.relative_to(base).as_posix()}"\n---\n正文',
            encoding="utf-8")
        raw_bad = base / "raw" / "旧 投影.docx.md"
        raw_bad.parent.mkdir()
        raw_bad.write_text(
            "<!-- source: incoming/消失.docx -->\n"
            "<!-- source_sha256: " + "b" * 64 + " -->\n"
            "<!-- extracted_by: markitdown (pre-existing artifact, "
            "backfilled 2026-01-01) -->\n正文", encoding="utf-8")
        return base, bad, good, raw_bad

    def test_unresolvable_sources_reported_files_untouched(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, bad, good, raw_bad = self._base(tmp)
            before = {p: p.read_bytes() for p in (bad, good, raw_bad)}
            rep = base.parent / "rep.json"
            proc = subprocess.run(
                ["uv", "run", "python", str(SCRIPTS_DIR / "backfill_source.py"),
                 str(base), "--json-report", str(rep)],
                capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            r = json.loads(rep.read_text(encoding="utf-8"))
            sus = {s["file"] for s in r["wrong_source_suspects"]}
            self.assertEqual(sus, {
                "materials/05-competitors/bad.md", "raw/旧 投影.docx.md"})
            for s in r["wrong_source_suspects"]:
                self.assertIn(s["assessment"], ("missing", "boundary-violation"))
                self.assertTrue(s["suggestion"])
            self.assertNotIn("materials/05-competitors/good.md", sus)
            after = {p: p.read_bytes() for p in (bad, good, raw_bad)}
            self.assertEqual(before, after)  # assessment only, no rewrite

    def test_boundary_violation_reported(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, bad, _, _ = self._base(tmp)
            bad.write_text('---\ntitle: t\nsource: "/etc/passwd"\n---\n正文',
                           encoding="utf-8")
            rep = base.parent / "rep.json"
            proc = subprocess.run(
                ["uv", "run", "python", str(SCRIPTS_DIR / "backfill_source.py"),
                 str(base), "--json-report", str(rep)],
                capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            r = json.loads(rep.read_text(encoding="utf-8"))
            entry = [s for s in r["wrong_source_suspects"]
                     if s["file"].endswith("bad.md")]
            self.assertEqual(entry[0]["assessment"], "boundary-violation")
            self.assertEqual(entry[0]["declared_source"], "/etc/passwd")


class MappingBoundaryTest(unittest.TestCase):
    """Review-fix 1: mapping targets (approved TSV) may be absolute, contain
    `..`, or be symlinks into another base — all must be refused BEFORE any
    read of the target content, reported separately, and never written."""

    MARKER = "TOPSECRET-OTHER-BASE-内容"

    def _bases(self, tmp):
        base = Path(tmp) / "base"
        other = Path(tmp) / "other-base"
        orig = base / "incoming" / "hd" / "方案.pptx"
        orig.parent.mkdir(parents=True)
        orig.write_text("x", encoding="utf-8")
        secret = other / "机密.pptx"
        secret.parent.mkdir(parents=True)
        secret.write_text(self.MARKER, encoding="utf-8")
        mat = base / "materials" / "05-competitors" / "accept.md"
        mat.parent.mkdir(parents=True)
        mat.write_text("---\ntitle: t\n---\n正文", encoding="utf-8")
        raw_md = base / "raw" / "旧 投影.docx.md"
        raw_md.parent.mkdir()
        raw_md.write_text("# 内容", encoding="utf-8")
        return base, other, secret, mat, raw_md

    def _run(self, base, tsv):
        rep = base.parent / "rep.json"
        proc = subprocess.run(
            ["uv", "run", "python", str(SCRIPTS_DIR / "backfill_source.py"),
             str(base), "--mapping", str(tsv), "--json-report", str(rep)],
            capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return rep.read_text(encoding="utf-8")

    def test_absolute_path_proposed_refused(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, other, secret, mat, raw_md = self._bases(tmp)
            tsv = base.parent / "m.tsv"
            tsv.write_text(
                "file\tproposed_source\tbucket\n"
                f"materials/05-competitors/accept.md\t{secret}\taccept\n",
                encoding="utf-8")
            rep_text = self._run(base, tsv)
            rep = json.loads(rep_text)
            self.assertEqual(rep["mapping_target_out_of_base"],
                             [{"file": "materials/05-competitors/accept.md",
                               "proposed": str(secret),
                               "status": "boundary-violation"}])
            self.assertNotIn("source:", mat.read_text(encoding="utf-8"))
            # zero read: target content never reaches any output
            self.assertNotIn(self.MARKER, rep_text)
            self.assertEqual(rep["written"], 0)

    def test_dotdot_relative_proposed_refused(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, other, secret, mat, raw_md = self._bases(tmp)
            tsv = base.parent / "m.tsv"
            tsv.write_text(
                "file\tproposed_source\tbucket\n"
                "materials/05-competitors/accept.md\t"
                "../other-base/机密.pptx\taccept\n",
                encoding="utf-8")
            rep_text = self._run(base, tsv)
            rep = json.loads(rep_text)
            self.assertEqual(len(rep["mapping_target_out_of_base"]), 1)
            self.assertNotIn("source:", mat.read_text(encoding="utf-8"))
            self.assertNotIn(self.MARKER, rep_text)
            self.assertEqual(rep["written"], 0)

    def test_symlink_into_other_base_refused_both_branches(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, other, secret, mat, raw_md = self._bases(tmp)
            link = base / "incoming" / "链接.pptx"
            link.symlink_to(secret)
            tsv = base.parent / "m.tsv"
            tsv.write_text(
                "file\tproposed_source\tbucket\n"
                "materials/05-competitors/accept.md\tincoming/链接.pptx\taccept\n"
                "raw/旧 投影.docx.md\tincoming/链接.pptx\taccept\n",
                encoding="utf-8")
            rep_text = self._run(base, tsv)
            rep = json.loads(rep_text)
            self.assertEqual(
                {e["file"] for e in rep["mapping_target_out_of_base"]},
                {"materials/05-competitors/accept.md", "raw/旧 投影.docx.md"})
            self.assertNotIn("source:", mat.read_text(encoding="utf-8"))
            self.assertNotIn("provenance_class:",
                             raw_md.read_text(encoding="utf-8"))
            self.assertNotIn(self.MARKER, rep_text)
            self.assertEqual(rep["written"], 0)

    def test_index_excludes_out_of_base_symlink_candidates(self):
        """Auto-match candidates cannot escape either: a file symlink into
        another base is excluded from the match index (recorded, not silent),
        so no candidate path ever reads outside the base."""
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, other, secret, _, _ = self._bases(tmp)
            link = base / "incoming" / "独苗方案.pptx"
            link.symlink_to(secret)
            mat = base / "materials" / "05-competitors" / "独苗方案.md"
            mat.write_text("---\ntitle: t\n---\n正文", encoding="utf-8")
            errors = []
            by_basename, _ = bs.build_base_index(base, errors)
            self.assertNotIn("独苗方案.pptx", by_basename)
            self.assertTrue(any("独苗方案.pptx" in e and "outside base" in e
                                for e in errors))
            empty_tsv = base.parent / "empty.tsv"
            empty_tsv.write_text("file\tproposed_source\tbucket\n",
                                 encoding="utf-8")
            rep_text = self._run(base, empty_tsv)
            self.assertNotIn(self.MARKER, rep_text)


class EncodingFailureTest(unittest.TestCase):
    """Review-fix 2: bad-encoding files fail per-item (bytes untouched),
    replace-decoded text is never written back, one failure never eats the
    report or previously processed results."""

    def _base(self, tmp):
        base = Path(tmp) / "base"
        orig = base / "incoming" / "hd" / "好 方案.pptx"
        orig.parent.mkdir(parents=True)
        orig.write_text("x", encoding="utf-8")
        good_mat = base / "materials" / "05-competitors" / "好 方案.md"
        good_mat.parent.mkdir(parents=True)
        good_mat.write_text("---\ntitle: t\n---\n正文", encoding="utf-8")
        good_raw = base / "raw" / "好 方案.pptx.md"
        good_raw.parent.mkdir()
        good_raw.write_text("# 内容", encoding="utf-8")
        bad_mat = base / "materials" / "05-competitors" / "坏字节.md"
        bad_mat.write_bytes(b"---\ntitle: t\n---\nbody \xff\xfe tail")
        bad_raw = base / "raw" / "坏 投影.docx.md"
        bad_raw.write_bytes(b"# \xc3\x28 \xff heading\n")
        return base, good_mat, good_raw, bad_mat, bad_raw, orig

    def _run(self, base):
        rep = base.parent / "rep.json"
        proc = subprocess.run(
            ["uv", "run", "python", str(SCRIPTS_DIR / "backfill_source.py"),
             str(base), "--json-report", str(rep)],
            capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(rep.read_text(encoding="utf-8"))

    def test_bad_encoding_files_fail_isolated_bytes_untouched(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, good_mat, good_raw, bad_mat, bad_raw, orig = self._base(tmp)
            bad_mat_before = bad_mat.read_bytes()
            bad_raw_before = bad_raw.read_bytes()
            rep = self._run(base)
            self.assertEqual(bad_mat.read_bytes(), bad_mat_before)
            self.assertEqual(bad_raw.read_bytes(), bad_raw_before)
            failed = {f["file"]: f for f in rep["failed"]}
            self.assertEqual(set(failed),
                             {"materials/05-competitors/坏字节.md",
                              "raw/坏 投影.docx.md"})
            for f in rep["failed"]:
                self.assertTrue(f["reason"].startswith("encoding-invalid:"))
                self.assertIn(f["stage"], ("read", "process"))
            # others processed normally, counts accurate
            self.assertEqual(rep["written"], 2)
            self.assertIn("provenance_class:",
                          good_mat.read_text(encoding="utf-8"))
            self.assertIn("provenance_class:",
                          good_raw.read_text(encoding="utf-8"))
            self.assertNotIn("坏字节.md", {m["file"] for m in rep["matched"]})

    @unittest.skipIf(os.geteuid() == 0, "chmod-based unreadable file does not block root")
    def test_permission_failure_isolated(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base, good_mat, good_raw, bad_mat, bad_raw, orig = self._base(tmp)
            locked = base / "materials" / "05-competitors" / "锁读.md"
            locked.write_text("---\ntitle: t\n---\n正文", encoding="utf-8")
            locked.chmod(0o000)
            try:
                rep = self._run(base)
            finally:
                locked.chmod(0o644)
            failed = {f["file"]: f for f in rep["failed"]}
            self.assertIn("materials/05-competitors/锁读.md", failed)
            self.assertIn("read-error", failed[
                "materials/05-competitors/锁读.md"]["reason"])
            # earlier/other results intact and accurately counted
            self.assertEqual(rep["written"], 2)
            self.assertTrue(any(m["file"].endswith("好 方案.md")
                                for m in rep["matched"]))


class FrontmatterEOFTest(unittest.TestCase):
    """Review-fix 3: closing `---` at EOF without trailing newline is valid
    frontmatter; fields append INSIDE the original block as a byte splice —
    no second frontmatter, no newline-style re-flow."""

    def test_eof_no_trailing_newline_appends_inside_block(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            md = Path(tmp) / "a.md"
            md.write_text("---\ntitle: t\n---", encoding="utf-8")  # EOF, no \n
            got = bs.insert_source(md, "none")
            self.assertEqual(got, "frontmatter-appended")
            self.assertEqual(md.read_text(encoding="utf-8"),
                             '---\ntitle: t\nsource: "none"\n---')

    def test_eof_frontmatter_with_body_and_lf_preserved(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            md = Path(tmp) / "b.md"
            original = "---\ntitle: t\ntags: x\n---\n\n正文\n"
            md.write_text(original, encoding="utf-8")
            bs.insert_source(md, "none")
            self.assertEqual(md.read_text(encoding="utf-8"),
                             "---\ntitle: t\ntags: x\n"
                             'source: "none"\n---\n\n正文\n')

    def test_crlf_style_preserved(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            md = Path(tmp) / "c.md"
            md.write_bytes(b"---\r\ntitle: t\r\n---\r\nbody")
            bs.insert_source(md, "none")
            self.assertEqual(
                md.read_bytes(),
                b'---\r\ntitle: t\r\nsource: "none"\r\n---\r\nbody')

    def test_provenance_fields_inserted_before_closing_fence_eof(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            md = Path(tmp) / "d.md"
            md.write_text("---\ntitle: t\n---", encoding="utf-8")
            bs.insert_source(md, "incoming/hd/方案.pptx",
                             sha256_at_backfill="a" * 64,
                             backfilled_at="2026-11-14")
            self.assertEqual(
                md.read_text(encoding="utf-8"),
                "---\ntitle: t\n"
                'source: "incoming/hd/方案.pptx"\n'
                "provenance_class: candidate-association\n"
                "source_sha256_at_backfill: " + "a" * 64 + "\n"
                "backfilled_at: 2026-11-14\n---")

    def test_cli_single_frontmatter_block_on_eof_file(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            base = Path(tmp) / "base"
            mat = base / "materials" / "01" / "eof.md"
            mat.parent.mkdir(parents=True)
            mat.write_text("---\ntitle: t\n---", encoding="utf-8")
            tsv = base.parent / "m.tsv"
            tsv.write_text(
                "file\tproposed_source\tbucket\n"
                "materials/01/eof.md\tNONE\tauthored\n", encoding="utf-8")
            rep = base.parent / "rep.json"
            proc = subprocess.run(
                ["uv", "run", "python", str(SCRIPTS_DIR / "backfill_source.py"),
                 str(base), "--mapping", str(tsv), "--json-report", str(rep)],
                capture_output=True, text=True, cwd=str(SCRIPTS_DIR.parent))
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = mat.read_text(encoding="utf-8")
            self.assertEqual(text.count("---"), 2)  # exactly one block
            self.assertEqual(text,
                             '---\ntitle: t\nsource: "none"\n---')


if __name__ == "__main__":
    unittest.main()
