"""provenance_inventory 只读溯源体检测试（Lane A，tasks 1.5 / 3.2 / 3.3 覆盖）。

全部使用临时目录合成公司基座（config/company.yaml + incoming/ raw/ materials/），
不触碰任何真实 docs 基座。双层：纯函数 run_inventory + CLI subprocess。
核心纪律断言：零业务写入（前后 {relpath: sha256} 快照完全相等）。
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import provenance_inventory as pi  # noqa: E402

SCRIPT = SCRIPTS_DIR / "provenance_inventory.py"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_base(root: Path, name: str = "co") -> Path:
    base = root / name
    (base / "config").mkdir(parents=True)
    (base / "config" / "company.yaml").write_text(
        f"name: {name}\n", encoding="utf-8")
    (base / "incoming").mkdir()
    (base / "raw").mkdir()
    (base / "materials").mkdir()
    return base


def snapshot(base: Path) -> dict:
    out = {}
    for cur, _dirs, files in os.walk(base):
        for f in files:
            p = Path(cur) / f
            out[p.relative_to(base).as_posix()] = sha(p.read_bytes())
    return out


def run_cli(base: Path, *extra, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base", str(base), *extra],
        capture_output=True, text=True, env=env, timeout=120)


def write_raw_md(base: Path, rel: str, source: str | None, source_sha: str | None,
                 extracted_by: str | None = None, body: str = "正文\n") -> Path:
    p = base / "raw" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if source is not None:
        lines.append(f"<!-- source: {source} -->")
    if source_sha is not None:
        lines.append(f"<!-- source_sha256: {source_sha} -->")
    if extracted_by is not None:
        lines.append(f"<!-- extracted_by: {extracted_by} -->")
    p.write_text("\n".join(lines) + "\n\n" + body, encoding="utf-8")
    return p


class ProvenanceInventoryTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    # 1. 声明来源可解析且哈希匹配
    def test_declared_source_hash_match(self):
        orig = self.base / "incoming" / "原始 文件.pptx"
        orig.write_bytes(b"ORIGINAL-BYTES")
        write_raw_md(self.base, "doc.md", "incoming/原始 文件.pptx",
                     sha(b"ORIGINAL-BYTES"),
                     "markitdown via convert_doc.py v2 (2026-01-01)")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/doc.md"]
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["link_state"], "declared")
        self.assertEqual(item["hash_check"], "match")
        self.assertEqual(item["source"], "incoming/原始 文件.pptx")
        # 保留 observed 的原件路径事实
        orig_item = report["items"]["incoming/原始 文件.pptx"]
        self.assertEqual(orig_item["link_state"], "observed")
        self.assertEqual(orig_item["kind"], "original")

    # 2. 声明哈希不匹配 → mismatch，零重写
    def test_declared_hash_mismatch_no_rewrite(self):
        orig = self.base / "incoming" / "x.docx"
        orig.write_bytes(b"AAA")
        write_raw_md(self.base, "x.md", "incoming/x.docx", "0" * 64)
        before = snapshot(self.base)
        r = run_cli(self.base)
        self.assertEqual(r.returncode, 3)
        report = json.loads(r.stdout)
        item = report["items"]["raw/x.md"]
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["hash_check"], "mismatch")
        self.assertTrue(report["hash_mismatches"])
        self.assertEqual(snapshot(self.base), before)  # 无任何重写

    # 3. _index.json imported_from 推断 → inferred，候选唯一也不升级
    def test_inferred_from_index_never_upgraded(self):
        (self.base / "incoming" / "foo.pptx").write_bytes(b"FOO")
        md = self.base / "raw" / "sub" / "foo.pptx.md"
        md.parent.mkdir(parents=True)
        md.write_text("正文\n", encoding="utf-8")
        (self.base / "raw" / "_index.json").write_text(
            json.dumps({"sub/foo.pptx.md": {"imported_from": "incoming/foo.pptx"}},
                       ensure_ascii=False), encoding="utf-8")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/sub/foo.pptx.md"]
        self.assertEqual(item["source_nature"], "inferred")
        self.assertEqual(item["link_state"], "inferred")
        self.assertEqual(item["inferred_candidates"], ["incoming/foo.pptx"])
        self.assertNotEqual(item.get("source_nature"), "declared")
        self.assertNotIn("source", item)  # 未升级为已验证身份

    # 4. 无权限子目录 → not-scanned/unavailable 而非「不存在」
    @unittest.skipIf(os.geteuid() == 0, "root 无视权限位，chmod 000 不生效")
    def test_unreadable_subdir_reported_not_scanned(self):
        locked = self.base / "raw" / "locked"
        locked.mkdir()
        (locked / "secret.md").write_text("x", encoding="utf-8")
        os.chmod(locked, 0o000)
        try:
            report = pi.run_inventory(self.base)
        finally:
            os.chmod(locked, 0o755)  # 先于 TemporaryDirectory 清理恢复权限
        self.assertTrue(report["scan"]["not_scanned"])
        self.assertTrue(report["scan"]["inaccessible"])
        self.assertFalse(report["scan"]["complete"])
        # 该子树文件既非 missing 也非 accessible —— 不冒充「不存在」
        for item in report["items"].values():
            self.assertFalse(item["path"].startswith("raw/locked/"))

    # 5. 损坏 _manifest.json → manifest-corrupt 缺口 + 扫描继续 + rc=3
    def test_corrupt_manifest_gap_scan_continues(self):
        sub = self.base / "raw" / "sub"
        sub.mkdir()
        (sub / "_manifest.json").write_text("{bad json", encoding="utf-8")
        (self.base / "incoming" / "y.docx").write_bytes(b"Y")
        write_raw_md(self.base, "y.md", "incoming/y.docx", sha(b"Y"))
        r = run_cli(self.base)
        self.assertEqual(r.returncode, 3)
        report = json.loads(r.stdout)
        self.assertTrue(report["gaps"]["manifest_corrupt"])
        self.assertEqual(report["gaps"]["manifest_corrupt"][0]["path"],
                         "raw/sub/_manifest.json")
        # 扫描继续：其他条目仍在报告里
        self.assertIn("raw/y.md", report["items"])
        self.assertEqual(report["items"]["raw/y.md"]["hash_check"], "match")

    # 6. 歧义候选（两个同 basename 原件）→ unresolved
    def test_ambiguous_candidates_unresolved(self):
        (self.base / "incoming" / "a").mkdir()
        (self.base / "incoming" / "b").mkdir()
        (self.base / "incoming" / "a" / "x.docx").write_bytes(b"A")
        (self.base / "incoming" / "b" / "x.docx").write_bytes(b"B")
        csvf = self.base / "raw" / "x.csv"
        csvf.write_text("h\n", encoding="utf-8")
        report = pi.run_inventory(self.base, repair_candidates=True)
        rep = [r for r in report["repair_candidates"] if r["path"] == "raw/x.csv"]
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep[0]["resolution"], "unresolved")
        self.assertEqual(sorted(rep[0]["candidates"]),
                         ["incoming/a/x.docx", "incoming/b/x.docx"])
        self.assertTrue(report["gaps"]["ambiguous"])

    # 7. 文件名中部 ~$ 投影（含 NUL）→ garbage-candidate + 抽样口径字段
    def test_mid_tilde_dollar_projection_with_nul(self):
        p = self.base / "raw" / "报告_~$1 培训.md"
        p.write_bytes(b"ab\x00cd")
        report = pi.run_inventory(self.base)
        self.assertIn("raw/报告_~$1 培训.md",
                      [g["path"] for g in report["garbage_candidates"]])
        item = report["items"]["raw/报告_~$1 培训.md"]
        self.assertEqual(item["sampling"]["sampled_bytes"], 5)
        self.assertEqual(item["sampling"]["sample_nul_count"], 1)
        self.assertEqual(item["sampling"]["nul_scope"], "full")  # 读满全文件才写 full

    def test_sample_scope_not_full_when_truncated(self):
        p = self.base / "raw" / "big.md"
        p.write_bytes(b"\x00" * 300)
        report = pi.run_inventory(self.base, sample_bytes=128)
        item = report["items"]["raw/big.md"]
        self.assertEqual(item["sampling"]["sampled_bytes"], 128)
        self.assertEqual(item["sampling"]["nul_scope"], "sample")  # 不冒充全文件

    # 8. 中文/空格/方括号文件名全链路
    def test_unicode_space_bracket_filenames(self):
        name = "方括号 [v2] 报 告.docx"
        orig = self.base / "incoming" / name
        orig.write_bytes(b"BRACKET")
        write_raw_md(self.base, name + ".md", f"incoming/{name}",
                     sha(b"BRACKET"))
        r = run_cli(self.base)
        report = json.loads(r.stdout)
        item = report["items"][f"raw/{name}.md"]
        self.assertEqual(item["hash_check"], "match")
        self.assertEqual(item["source"], f"incoming/{name}")

    # 9. encoding-invalid 探测
    def test_encoding_invalid_detected(self):
        (self.base / "raw" / "bad.md").write_bytes(b"ok\xff\xfemore")
        report = pi.run_inventory(self.base)
        entry = [e for e in report["invalid_projections"]
                 if e["path"] == "raw/bad.md"]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["issue"], "encoding-invalid")
        self.assertEqual(entry[0]["error_offset"], 2)

    # 10. 零写入断言（含 --repair-candidates 模式）
    def test_zero_write_with_repair_candidates(self):
        (self.base / "incoming" / "solo.docx").write_bytes(b"S")
        write_raw_md(self.base, "solo.docx.md", None, None)  # 缺 provenance
        (self.base / "raw" / "orphan.csv").write_text("h\n", encoding="utf-8")
        mat = self.base / "materials" / "m.md"
        mat.write_text("# 无来源\n", encoding="utf-8")
        before = snapshot(self.base)
        r = run_cli(self.base, "--repair-candidates")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(snapshot(self.base), before)
        report = json.loads(r.stdout)
        rep = {x["path"]: x for x in report["repair_candidates"]}
        self.assertEqual(rep["raw/solo.docx.md"]["resolution"], "candidate")
        self.assertEqual(rep["raw/solo.docx.md"]["provenance_class"],
                         "candidate-association")
        self.assertEqual(rep["raw/solo.docx.md"]["basis"], "unique-basename")
        self.assertEqual(rep["raw/solo.docx.md"]["candidate_sha256"], sha(b"S"))
        self.assertTrue(report["gaps"]["no_manifest_coverage"])

    # 11. 退出码矩阵
    def test_exit_codes(self):
        # 干净基座 rc=0：声明+匹配 raw md，materials authored source:none
        (self.base / "incoming" / "c.pptx").write_bytes(b"C")
        write_raw_md(self.base, "c.md", "incoming/c.pptx", sha(b"C"))
        (self.base / "materials" / "authored.md").write_text(
            '---\nsource: "none"\n---\n正文\n', encoding="utf-8")
        r = run_cli(self.base)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # 有缺口 rc=3
        (self.base / "materials" / "nosrc.md").write_text("无来源\n",
                                                          encoding="utf-8")
        r = run_cli(self.base)
        self.assertEqual(r.returncode, 3)
        # --base 缺 config/company.yaml → rc=1
        empty = self.root / "notacompany"
        empty.mkdir()
        r = run_cli(empty)
        self.assertEqual(r.returncode, 1)
        self.assertIn("不是已注册公司", r.stderr)

    # 12. 默认哈希策略 vs --full-hash
    def test_full_hash_vs_default_policy(self):
        (self.base / "incoming" / "used.pptx").write_bytes(b"U")
        (self.base / "incoming" / "unused.docx").write_bytes(b"N")
        write_raw_md(self.base, "used.md", "incoming/used.pptx", sha(b"U"))
        default = pi.run_inventory(self.base)
        # 默认不哈希无声明哈希需比对的对象：unused.docx 条目不该出现在哈希相关输出
        self.assertNotIn("sha256", default["items"]["incoming/unused.docx"])
        full = pi.run_inventory(self.base, full_hash=True)
        self.assertEqual(full["items"]["incoming/unused.docx"].get("sha256"),
                         sha(b"N"))
        self.assertEqual(full["items"]["incoming/used.pptx"].get("sha256"),
                         sha(b"U"))

    # 13. 旧 backfilled 记录不升级；裸 source_sha256 → hash_semantics unknown
    def test_backfilled_and_bare_hash_semantics(self):
        (self.base / "incoming" / "bf.docx").write_bytes(b"BF")
        write_raw_md(self.base, "bf.md", "incoming/bf.docx", sha(b"BF"),
                     "markitdown (pre-existing artifact, backfilled 2026-01-01)")
        (self.base / "incoming" / "bare.docx").write_bytes(b"BARE")
        write_raw_md(self.base, "bare.md", "incoming/bare.docx", sha(b"BARE"))
        # converter 签名 + 同基座来源 + 合法哈希 → recorded-at-conversion（仅声明存在）
        (self.base / "incoming" / "conv.docx").write_bytes(b"CV")
        write_raw_md(self.base, "conv.md", "incoming/conv.docx", sha(b"CV"),
                     "markitdown via convert_doc.py v2 (2026-01-01)")
        report = pi.run_inventory(self.base)
        bf = report["items"]["raw/bf.md"]
        self.assertEqual(bf["provenance_class"], "candidate-association")
        self.assertEqual(bf["hash_semantics"], "at-backfill")
        self.assertEqual(bf["hash_check"], "match")
        self.assertNotIn("recorded", str(bf.get("provenance_class")))
        bare = report["items"]["raw/bare.md"]
        self.assertEqual(bare["hash_semantics"], "unknown")
        self.assertIsNone(bare.get("provenance_class"))
        conv = report["items"]["raw/conv.md"]
        self.assertEqual(conv["provenance_class"], "recorded-at-conversion")

    # 补：唯一文件名候选不触发 recorded-at-conversion（repair 模式）
    def test_unique_basename_candidate_not_recorded_at_conversion(self):
        (self.base / "incoming" / "uniq.docx").write_bytes(b"Q")
        write_raw_md(self.base, "uniq.docx.md", None, None)
        report = pi.run_inventory(self.base, repair_candidates=True)
        rep = report["repair_candidates"][0]
        self.assertEqual(rep["provenance_class"], "candidate-association")
        self.assertNotEqual(rep["provenance_class"], "recorded-at-conversion")

    # --- convert_excel 块形态（source_path/extractor 字段名）兼容 ---

    def write_excel_md(self, rel: str, source_path: str, source_sha: str) -> Path:
        """convert_excel.py provenance_lines 的真实块形态（绝对路径 source_path）。"""
        p = self.base / "raw" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            "<!--\n"
            f"source_path: {source_path}\n"
            f"source_sha256: {source_sha}\n"
            "extracted_at: 2026-01-01T00:00:00\n"
            "extractor: convert_excel.py v3\n"
            "fidelity: text=high; structure=high; notes: none\n"
            "-->\n\n# 标题\n\n正文\n",
            encoding="utf-8")
        return p

    def test_excel_block_declared_in_base_no_false_gap(self):
        orig = self.base / "incoming" / "表.xlsx"
        orig.write_bytes(b"XLSX")
        self.write_excel_md("表.md", str(orig.resolve()), sha(b"XLSX"))
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/表.md"]
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["link_state"], "declared")
        self.assertEqual(item["hash_check"], "match")
        self.assertEqual(item["source"], "incoming/表.xlsx")
        self.assertEqual(item["declared_via"], "source_path")
        # 不产生假阳性缺口
        self.assertEqual(report["gaps"]["missing_source"], [])
        self.assertEqual(report["gaps"]["missing_hash"], [])
        # 三要件齐备 → recorded-at-conversion（仅声明存在，不越权表述）
        self.assertEqual(item["provenance_class"], "recorded-at-conversion")

    def test_excel_block_absolute_path_outside_base_boundary(self):
        orig = self.base / "incoming" / "表.xlsx"
        orig.write_bytes(b"XLSX")
        outside = self.root / "elsewhere" / "别的基座.xlsx"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_bytes(b"OTHER")
        self.write_excel_md("表.md", str(outside), "0" * 64)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/表.md"]
        self.assertEqual(item["hash_check"], "not-applicable")
        self.assertNotEqual(item["hash_check"], "mismatch")  # 未读取目标
        bv = [b for b in report["boundary_violations"]
              if b["path"] == "raw/表.md"]
        self.assertEqual(len(bv), 1)
        self.assertIn("基座之外", bv[0]["reason"])

    def test_excel_block_hash_mismatch_not_convicted(self):
        orig = self.base / "incoming" / "表.xlsx"
        orig.write_bytes(b"XLSX")
        self.write_excel_md("表.md", str(orig.resolve()), "1" * 64)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/表.md"]
        self.assertEqual(item["hash_check"], "mismatch")
        self.assertIn("不判定哪一侧权威", item["note"])
        self.assertTrue(report["hash_mismatches"])
        self.assertEqual(report["boundary_violations"], [])

    # --- 声明 source 为超长描述文字（真实基座 Errno 36 家族，troubleshooting #15）---

    # --- raw 收集范围：_media/非文本文件不入体检（真实基座 21193 假阳性回归）---

    def test_media_and_binary_files_excluded_from_raw_scan(self):
        media = self.base / "raw" / "sub" / "_media"
        media.mkdir(parents=True)
        (media / "image1.jpeg").write_bytes(b"\xff\xd8\xff\xe0binary")  # 非法 UTF-8
        (self.base / "raw" / "stray.jpeg").write_bytes(b"\xff\xd8\xff")  # raw 顶层散落二进制
        (self.base / "raw" / "t.md").write_text("正文\n", encoding="utf-8")
        (self.base / "raw" / "t.csv").write_text("h\n", encoding="utf-8")
        (self.base / "raw" / "t.notes.md").write_text("notes\n", encoding="utf-8")
        report = pi.run_inventory(self.base)
        # 媒体/二进制不出现在 items / invalid_projections / no_manifest_coverage
        for path in ("raw/sub/_media/image1.jpeg", "raw/stray.jpeg"):
            self.assertNotIn(path, report["items"])
            self.assertNotIn(path, [e.get("path") for e
                                    in report["invalid_projections"]])
            self.assertNotIn(path, [g["path"] for g
                                    in report["gaps"]["no_manifest_coverage"]])
        # 三类文本投影照常收集
        for path in ("raw/t.md", "raw/t.csv", "raw/t.notes.md"):
            self.assertIn(path, report["items"])
        self.assertIn("raw/t.csv",
                      [g["path"] for g in report["gaps"]["no_manifest_coverage"]])
        # _media 范围外如实标注（范围外 ≠ 无问题）
        oos = [n for n in report["scan"]["not_scanned"]
               if n["location"] == "raw/**/_media"]
        self.assertEqual(len(oos), 1)
        self.assertIn("out-of-scope", oos[0]["reason"])
        # 范围外标注不冒充不可访问失败
        self.assertEqual(report["scan"]["inaccessible"], [])

    def test_declared_source_name_too_long_no_crash(self):
        long_name = "借鉴明源客户成功体系客户旅程地图实施转服务巡检评级年度服务规划" * 10 \
                    + ".docx"  # basename 600+ 字节 > 255
        write_raw_md(self.base, "desc.md", f"incoming/{long_name}", "0" * 64)
        r = run_cli(self.base)  # 不得 crash 成 rc=1
        self.assertEqual(r.returncode, 3)
        report = json.loads(r.stdout)
        item = report["items"]["raw/desc.md"]
        # 观察失败 → inaccessible（带 errno 依据），绝不冒充 missing 或 boundary
        self.assertEqual(item["accessibility"], "inaccessible")
        self.assertEqual(item["hash_check"], "not-applicable")
        self.assertTrue(report["unverifiable_sources"])
        self.assertIn("errno", report["unverifiable_sources"][0]["reason"])
        self.assertIn("ENAMETOOLONG", report["unverifiable_sources"][0]["reason"])
        self.assertEqual(report["gaps"]["missing_original"], [])
        self.assertEqual(report["boundary_violations"], [])

    # --- EACCES 观察失败按 errno 分类（非 boundary 非 missing）---

    @unittest.skipIf(os.geteuid() == 0, "root 无视权限位，chmod 000 不生效")
    def test_declared_source_unreadable_file_permission_denied(self):
        orig = self.base / "incoming" / "secret.docx"
        orig.write_bytes(b"SECRET")
        os.chmod(orig, 0o000)
        try:
            write_raw_md(self.base, "s.md", "incoming/secret.docx",
                         sha(b"SECRET"))
            report = pi.run_inventory(self.base)
        finally:
            os.chmod(orig, 0o644)
        item = report["items"]["raw/s.md"]
        # stat 成功、read EACCES → source 侧 permission-denied + errno 依据
        self.assertEqual(item["source_accessibility"], "permission-denied")
        self.assertEqual(item["hash_check"], "not-applicable")
        self.assertNotEqual(item["hash_check"], "mismatch")  # 读失败 ≠ 不匹配
        unver = [u for u in report["unverifiable_sources"]
                 if u["path"] == "raw/s.md"]
        self.assertEqual(len(unver), 1)
        self.assertIn("EACCES", unver[0]["reason"])
        self.assertEqual(report["gaps"]["missing_original"], [])
        self.assertEqual(report["boundary_violations"], [])

    @unittest.skipIf(os.geteuid() == 0, "root 无视权限位，chmod 000 不生效")
    def test_declared_source_in_locked_dir_permission_denied(self):
        locked = self.base / "incoming" / "locked"
        locked.mkdir()
        (locked / "inner.docx").write_bytes(b"INNER")
        write_raw_md(self.base, "inner.md", "incoming/locked/inner.docx",
                     sha(b"INNER"))
        os.chmod(locked, 0o000)
        try:
            report = pi.run_inventory(self.base)
        finally:
            os.chmod(locked, 0o755)
        item = report["items"]["raw/inner.md"]
        # stat EACCES → permission-denied + errno 依据，非 boundary 非 missing
        self.assertEqual(item["accessibility"], "permission-denied")
        self.assertEqual(item["hash_check"], "not-applicable")
        unver = [u for u in report["unverifiable_sources"]
                 if u["path"] == "raw/inner.md"]
        self.assertEqual(len(unver), 1)
        self.assertIn("EACCES", unver[0]["reason"])
        self.assertEqual(report["gaps"]["missing_original"], [])
        self.assertEqual(report["boundary_violations"], [])

    def test_classification_matrix_mutually_exclusive(self):
        # 同一报告里：真越界（绝对路径指向基座外存在的文件）+ 超长名观察失败
        outside = self.root / "outside.docx"
        outside.write_bytes(b"OUT")
        write_raw_md(self.base, "b.md", str(outside), "0" * 64)
        long_name = "长" * 200 + ".docx"
        write_raw_md(self.base, "desc.md", f"incoming/{long_name}", "0" * 64)
        report = pi.run_inventory(self.base)
        self.assertEqual(len(report["boundary_violations"]), 1)
        self.assertTrue(report["unverifiable_sources"])
        # boundary 条目 = resolve 成功落基座外，reason 不含 OSError 证据字样
        for b in report["boundary_violations"]:
            self.assertNotIn("errno", b["reason"])
            self.assertIn("基座之外", b["reason"])
        # unverifiable 条目 = 观察动作自身失败，不含越界语义
        for u in report["unverifiable_sources"]:
            self.assertNotIn("基座之外", u["reason"])
            self.assertIn("errno", u["reason"])


if __name__ == "__main__":
    unittest.main()
