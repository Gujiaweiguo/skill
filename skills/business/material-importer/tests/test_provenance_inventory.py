"""provenance_inventory 只读溯源体检测试（Lane A，tasks 1.5 / 3.2 / 3.3 覆盖）。

全部使用临时目录合成公司基座（config/company.yaml + incoming/ raw/ materials/），
不触碰任何真实 docs 基座。双层：纯函数 run_inventory + CLI subprocess。
核心纪律断言：零业务写入（前后 {relpath: sha256} 快照完全相等）。
"""

import errno
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


# --- recognize-web-capture-provenance：受控网页声明解析（任务 1.1）---
# 全部合成基座；URL 一律 *.invalid（RFC 2606 保留域），不依赖真实 docs 基座、
# 不复制任何真实文章正文。真实锚点只读登记于 tests/fixtures_registry.json。

WEB_URL = "https://mp.example.invalid/s/abc123"
WEB_URL2 = "https://mp.example.invalid/s/def456"


def write_raw_md_head(base: Path, rel: str, head: str,
                      body: str = "正文段落\n") -> Path:
    p = base / "raw" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(head + "\n\n" + body, encoding="utf-8")
    return p


class WebCaptureDeclarationTest(unittest.TestCase):
    """中文/ASCII 网页抓取声明只在文首有界注释区识别；本地解析兼容接口不变。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _gaps_for(self, report: dict, rel: str) -> dict:
        return {k: [g for g in v if g["path"] == rel]
                for k, v in report["gaps"].items()}

    # 真实锚点格式：块注释 + 中文键 + 半角冒号（01-书记-杨军艇.md 同构）
    def test_chinese_head_url_and_capture_time(self):
        head = ("<!--\n"
                f"来源 URL: {WEB_URL}\n"
                "抓取时间: 2026-11-07\n"
                "账号名: 某协会\n"
                "文章标题: 某文章\n"
                "发布时间: 2026-09-29 16:57\n"
                "-->\n")
        write_raw_md_head(self.base, "article.md", head)
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/article.md"]
        self.assertEqual(item["source_kind"], "external-url")
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["link_state"], "declared")
        self.assertEqual(item["accessibility"], "not-scanned")
        self.assertEqual(item["projection_accessibility"], "accessible")
        self.assertEqual(item["hash_check"], "unknown-scope")
        decls = item["source_declarations"]
        url_decl = [d for d in decls if d["kind"] == "source-url"]
        self.assertEqual(len(url_decl), 1)
        self.assertEqual(url_decl[0]["value"], WEB_URL)      # 保留原值
        self.assertEqual(url_decl[0]["field"], "来源 URL")
        self.assertEqual(url_decl[0]["line"], 2)             # 1-based 行位置
        cap = [d for d in decls if d["kind"] == "captured-at"]
        self.assertEqual(cap[0]["value"], "2026-11-07")
        self.assertEqual(cap[0]["line"], 3)
        g = self._gaps_for(report, "raw/article.md")
        self.assertEqual(g["missing_source"], [])
        self.assertEqual(g["missing_original"], [])
        self.assertEqual(g["missing_hash"], [])
        ext = report["external_sources_unverified"]
        self.assertEqual([(e["path"], e["url"]) for e in ext],
                         [("raw/article.md", WEB_URL)])
        self.assertEqual(ext[0]["captured_at"], "2026-11-07")
        self.assertEqual(ext[0]["captured_at_semantics"], "declared")
        self.assertEqual(ext[0]["verification"], "not-performed")
        self.assertTrue(pi.has_findings(report))  # 未核验 → 有发现
        self.assertEqual(snapshot(self.base), before)  # 零写入

    def test_full_width_colon_and_compact_variants(self):
        head = ("<!--\n"
                f"来源URL：{WEB_URL}\n"
                "抓取时间：2026-11-07\n"
                "-->\n")
        write_raw_md_head(self.base, "fw.md", head)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/fw.md"]
        self.assertEqual(item["source_kind"], "external-url")
        self.assertEqual(report["external_sources_unverified"][0]["url"],
                         WEB_URL)

    def test_explicit_ascii_source_url_field(self):
        head = (f"<!-- source_url: {WEB_URL} -->\n"
                "<!-- 抓取时间: 2026-11-07 -->\n")
        write_raw_md_head(self.base, "ascii.md", head)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/ascii.md"]
        self.assertEqual(item["source_kind"], "external-url")
        self.assertEqual(item["source_declarations"][0]["field"],
                         "source_url")
        self.assertEqual(item["source_declarations"][0]["line"], 1)

    def test_old_source_field_http_url_external_branch(self):
        # <!-- source: https://... --> 完整值为合法 HTTP(S) URL → 外部分支
        write_raw_md(self.base, "web.md", WEB_URL, None)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/web.md"]
        self.assertEqual(item["source_kind"], "external-url")
        self.assertEqual(item["declared_source"], WEB_URL)
        self.assertEqual(item["declared_via"], "source")
        self.assertEqual(item["hash_check"], "unknown-scope")
        g = self._gaps_for(report, "raw/web.md")
        self.assertEqual(g["missing_original"], [])
        self.assertEqual(g["missing_source"], [])
        self.assertEqual(report["external_sources_unverified"][0]["url"],
                         WEB_URL)

    def test_old_block_source_path_with_url(self):
        # convert_excel 块形态 source_path: URL → 同样外部分支
        head = ("<!--\n"
                f"source_path: {WEB_URL}\n"
                "extractor: convert_excel.py v3\n"
                "-->\n")
        write_raw_md_head(self.base, "blk.md", head)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/blk.md"]
        self.assertEqual(item["source_kind"], "external-url")
        g = self._gaps_for(report, "raw/blk.md")
        self.assertEqual(g["missing_original"], [])

    def test_url_never_resolved_never_network(self):
        # URL 不进 resolve_declared_source；本地路径仍走（兼容接口不变）；
        # 网络哨兵：socket 被封死时扫描照常完成。
        (self.base / "incoming" / "local.docx").write_bytes(b"L")
        write_raw_md(self.base, "local.md", "incoming/local.docx",
                     sha(b"L"))
        head = f"<!--\n来源 URL: {WEB_URL}\n抓取时间: 2026-11-07\n-->\n"
        write_raw_md_head(self.base, "web.md", head)
        orig = pi.resolve_declared_source
        seen: list[str] = []

        def guard(declared, base):
            seen.append(declared)
            if declared.strip().lower().startswith(
                    ("http://", "https://", "ftp://", "file://")):
                raise AssertionError(f"URL 进入本地路径解析: {declared}")
            return orig(declared, base)

        with mock.patch.object(pi, "resolve_declared_source",
                               side_effect=guard):
            report = pi.run_inventory(self.base)
        self.assertIn("incoming/local.docx", seen)   # 本地路径照常解析
        self.assertNotIn(WEB_URL, seen)
        web_item = report["items"]["raw/web.md"]
        self.assertNotIn("source", web_item)          # 无本地解析结果
        self.assertNotIn("source_sha256_actual", web_item)
        with mock.patch("socket.socket",
                        side_effect=AssertionError("network attempted")), \
             mock.patch("socket.create_connection",
                        side_effect=AssertionError("network attempted")):
            report2 = pi.run_inventory(self.base)
        self.assertEqual(report2["external_sources_unverified"][0]["url"],
                         WEB_URL)

    def test_duplicate_urls_grouped_all_positions_kept(self):
        head = ("<!--\n"
                f"来源 URL: {WEB_URL}\n"
                f"来源 URL:  {WEB_URL}  \n"   # 首尾空白差异，去首尾空白后同值
                f"source_url: {WEB_URL}\n"
                "-->\n")
        write_raw_md_head(self.base, "dup.md", head)
        report = pi.run_inventory(self.base)
        ext = report["external_sources_unverified"]
        self.assertEqual(len(ext), 1)
        self.assertEqual(ext[0]["url"], WEB_URL)
        self.assertEqual([d["line"] for d in ext[0]["declarations"]],
                         [2, 3, 4])
        self.assertEqual(report["source_declaration_conflicts"], [])

    def test_conflicting_urls_reported_no_authority(self):
        head = ("<!--\n"
                f"来源 URL: {WEB_URL2}\n"
                f"source_url: {WEB_URL}\n"
                "-->\n")
        write_raw_md_head(self.base, "conf.md", head)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/conf.md"]
        self.assertEqual(item["source_kind"], "external-url")
        self.assertEqual(item["external_urls"], sorted([WEB_URL, WEB_URL2]))
        conf = report["source_declaration_conflicts"]
        self.assertEqual(len(conf), 1)
        self.assertEqual(conf[0]["path"], "raw/conf.md")
        self.assertEqual(conf[0]["urls"], sorted([WEB_URL, WEB_URL2]))
        ext_urls = sorted(e["url"] for e
                          in report["external_sources_unverified"])
        self.assertEqual(ext_urls, sorted([WEB_URL, WEB_URL2]))

    def test_malformed_url_declarations_diagnosed(self):
        cases = [
            ("m1.md", "https://exa mple.invalid/a", "malformed"),   # 内部空白附注
            ("m2.md", "https://", "malformed"),                     # 无 hostname
            ("m3.md", "https://u:p@mp.example.invalid/s", "malformed"),  # 用户凭据
            ("m4.md", "notaurl", "not-url"),                        # 无 scheme
        ]
        for rel, val, _issue in cases:
            write_raw_md_head(
                self.base, rel,
                f"<!-- source_url: {val} -->\n")
        report = pi.run_inventory(self.base)
        errs = report["source_declaration_errors"]
        self.assertEqual(len(errs), 4)
        for rel, val, issue in cases:
            e = [x for x in errs if x["path"] == f"raw/{rel}"]
            self.assertEqual(len(e), 1)
            self.assertEqual(e[0]["issue"], issue)
            self.assertEqual(e[0]["value"], val)          # 原值保留
            self.assertEqual(e[0]["field"], "source_url")
        self.assertEqual(report["external_sources_unverified"], [])
        for rel, _val, _issue in cases:
            g = self._gaps_for(report, f"raw/{rel}")
            self.assertEqual(g["missing_original"], [])   # 不当本地路径
        # 无可用来源 → missing_source 如实；但不做 basename 回填（见 2.x）

    def test_unsupported_scheme_reported_not_relative_path(self):
        for rel, val in (("f1.md", "file:///opt/x/doc.docx"),
                         ("f2.md", "ftp://example.invalid/f")):
            write_raw_md_head(self.base, rel,
                              f"<!--\nsource_url: {val}\n-->\n")
        report = pi.run_inventory(self.base)
        errs = report["source_declaration_errors"]
        self.assertEqual([e["issue"] for e in errs],
                         ["unsupported-scheme", "unsupported-scheme"])
        self.assertEqual(report["boundary_violations"], [])
        for rel in ("raw/f1.md", "raw/f2.md"):
            g = self._gaps_for(report, rel)
            self.assertEqual(g["missing_original"], [])   # 不当相对路径

    def test_body_code_block_and_post_comment_urls_ignored(self):
        # 正文段内 URL
        write_raw_md_head(self.base, "b1.md", "",
                          body=f"参考 {WEB_URL} 详情\n")
        # 围栏代码块内
        write_raw_md_head(self.base, "b2.md", "",
                          body=f"```\n来源 URL: {WEB_URL}\n```\n")
        # 正文之后的注释（非文首区）
        write_raw_md_head(self.base, "b3.md", "",
                          body=f"正文\n\n<!-- 来源 URL: {WEB_URL} -->\n")
        report = pi.run_inventory(self.base)
        self.assertEqual(report["external_sources_unverified"], [])
        for rel in ("raw/b1.md", "raw/b2.md", "raw/b3.md"):
            item = report["items"][rel]
            self.assertEqual(item.get("source_declarations"), [])
            g = self._gaps_for(report, rel)
            self.assertEqual(len(g["missing_source"]), 1)

    def test_truncated_or_unclosed_comment_yields_no_source(self):
        # 未闭合注释
        write_raw_md_head(self.base, "t1.md",
                          f"<!--\n来源 URL: {WEB_URL}\n抓取时间: 2026-11-07\n")
        # --> 落在 4000 字符头之外（截断）
        write_raw_md_head(
            self.base, "t2.md",
            f"<!--\n来源 URL: {WEB_URL}\n" + "填充" * 2200 + "\n-->\n")
        report = pi.run_inventory(self.base)
        self.assertEqual(report["external_sources_unverified"], [])
        self.assertEqual(report["source_declaration_errors"], [])
        for rel in ("raw/t1.md", "raw/t2.md"):
            g = self._gaps_for(report, rel)
            self.assertEqual(len(g["missing_source"]), 1)


# --- recognize-web-capture-provenance：分维报告与修复候选隔离（任务 2.1）---

class ExternalSourceReportingTest(unittest.TestCase):
    """URL-only / mixed / 坏本地source+URL / _index 推断并存 / 回填候选隔离。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _gaps_for(self, report: dict, rel: str) -> dict:
        return {k: [g for g in v if g["path"] == rel]
                for k, v in report["gaps"].items()}

    def test_url_only_rc3_scan_complete_external_not_performed(self):
        head = f"<!--\n来源 URL: {WEB_URL}\n抓取时间: 2026-11-07\n-->\n"
        write_raw_md_head(self.base, "web.md", head)
        before = snapshot(self.base)
        r = run_cli(self.base)
        self.assertEqual(r.returncode, 3)               # 未核验 → 有发现
        self.assertEqual(snapshot(self.base), before)   # 零写入
        report = json.loads(r.stdout)
        # 本地枚举完整性不受未联网影响
        self.assertTrue(report["scan"]["complete"])
        self.assertEqual(report["external_verification"]["status"],
                         "not-performed")
        # 不再 missing_source / missing_original / missing_hash
        g = self._gaps_for(report, "raw/web.md")
        self.assertEqual(g["missing_source"], [])
        self.assertEqual(g["missing_original"], [])
        self.assertEqual(g["missing_hash"], [])

    def test_mixed_local_and_url_keeps_local_diagnostics(self):
        (self.base / "incoming" / "orig.docx").write_bytes(b"O")
        head = (f"<!-- source: incoming/orig.docx -->\n"
                f"<!-- source_sha256: {sha(b'O')} -->\n"
                f"<!-- source_url: {WEB_URL} -->\n"
                "<!-- 抓取时间: 2026-11-07 -->\n")
        write_raw_md_head(self.base, "mixed.md", head)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/mixed.md"]
        self.assertEqual(item["source_kind"], "mixed")
        # 顶层保留本地语义：来源解析、哈希匹配照常
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["source"], "incoming/orig.docx")
        self.assertEqual(item["hash_check"], "match")
        # URL 走独立表达，不掩盖也不被掩盖
        self.assertEqual(item["external_urls"], [WEB_URL])
        self.assertEqual([(e["path"], e["url"])
                          for e in report["external_sources_unverified"]],
                         [("raw/mixed.md", WEB_URL)])
        self.assertEqual(report["source_declaration_conflicts"], [])
        g = self._gaps_for(report, "raw/mixed.md")
        self.assertEqual(g["missing_source"], [])
        self.assertEqual(g["missing_hash"], [])

    def test_bad_local_source_with_valid_url_not_masked(self):
        head = (f"<!-- source: incoming/不存在.docx -->\n"
                f"<!-- source_url: {WEB_URL} -->\n")
        write_raw_md_head(self.base, "bad.md", head)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/bad.md"]
        self.assertEqual(item["source_kind"], "mixed")
        self.assertEqual(item["accessibility"], "missing")
        # 本地缺口照常呈现，URL 不掩盖
        g = self._gaps_for(report, "raw/bad.md")
        self.assertEqual(len(g["missing_original"]), 1)
        # URL 仍未核验
        self.assertEqual([(e["path"], e["url"])
                          for e in report["external_sources_unverified"]],
                         [("raw/bad.md", WEB_URL)])

    def test_index_inference_coexistence(self):
        # 一个 URL md（声明优先于推断）+ 一个无声明 md（照常 _index 推断）
        head = f"<!--\n来源 URL: {WEB_URL}\n-->\n"
        write_raw_md_head(self.base, "web.md", head)
        (self.base / "incoming" / "foo.pptx").write_bytes(b"FOO")
        md = self.base / "raw" / "sub" / "foo.pptx.md"
        md.parent.mkdir(parents=True)
        md.write_text("正文\n", encoding="utf-8")
        (self.base / "raw" / "_index.json").write_text(
            json.dumps({"sub/foo.pptx.md":
                        {"imported_from": "incoming/foo.pptx"}}),
            encoding="utf-8")
        report = pi.run_inventory(self.base)
        web = report["items"]["raw/web.md"]
        self.assertEqual(web["source_kind"], "external-url")
        self.assertEqual(web["source_nature"], "declared")
        self.assertNotIn("inferred_candidates", web)   # 声明优先于推断
        inf = report["items"]["raw/sub/foo.pptx.md"]
        self.assertEqual(inf["source_nature"], "inferred")
        self.assertEqual(inf["inferred_candidates"], ["incoming/foo.pptx"])

    def test_external_declaration_not_backfill_candidate(self):
        # URL-only md + 同 basename 原件存在：不得按 basename 自动补 source
        (self.base / "incoming" / "web.docx").write_bytes(b"W")
        head = f"<!--\n来源 URL: {WEB_URL}\n-->\n"
        write_raw_md_head(self.base, "web.docx.md", head)
        report = pi.run_inventory(self.base, repair_candidates=True)
        paths = [r["path"] for r in report["repair_candidates"]]
        self.assertNotIn("raw/web.docx.md", paths)
        # 畸形URL声明同样不进回填候选
        write_raw_md_head(self.base, "bad.docx.md",
                          "<!-- source_url: notaurl -->\n")
        (self.base / "incoming" / "bad.docx").write_bytes(b"B")
        report2 = pi.run_inventory(self.base, repair_candidates=True)
        paths2 = [r["path"] for r in report2["repair_candidates"]]
        self.assertNotIn("raw/bad.docx.md", paths2)

    def test_wrong_source_suspects_external_branch(self):
        (self.base / "incoming" / "orig.docx").write_bytes(b"O")
        (self.base / "incoming" / "web.docx").write_bytes(b"W")
        head = f"<!--\n来源 URL: {WEB_URL}\n-->\n"
        write_raw_md_head(self.base, "web.docx.md", head)
        mixed = (f"<!-- source: incoming/orig.docx -->\n"
                 f"<!-- source_url: {WEB_URL} -->\n")
        write_raw_md_head(self.base, "mixed.md", mixed)
        report = pi.run_inventory(self.base, repair_candidates=True)
        suspects = {s["path"]: s for s in report["wrong_source_suspects"]}
        ext = suspects["raw/web.docx.md"]
        self.assertEqual(ext["source_kind"], "external-url")
        self.assertEqual(ext["verifiability"], "external-not-verified")
        self.assertNotEqual(ext["verifiability"], "resolvable-in-base")
        # mixed 条目沿用本地判断：来源可解析 → resolvable-in-base
        mix = suspects["raw/mixed.md"]
        self.assertEqual(mix["verifiability"], "resolvable-in-base")

    def test_cli_report_outside_base_and_sorted(self):
        for i in range(3):
            head = (f"<!--\n来源 URL: https://mp{i}.example.invalid/s/x\n"
                    "抓取时间: 2026-11-07\n-->\n")
            write_raw_md_head(self.base, f"z{i}.md", head)
        write_raw_md_head(self.base, "a.md",
                          f"<!-- source_url: {WEB_URL} -->\n")
        before = snapshot(self.base)
        out = self.root / "reports" / "inv.json"   # 基座外
        r = run_cli(self.base, "--report", str(out), "--repair-candidates")
        self.assertEqual(r.returncode, 3)
        self.assertTrue(out.is_file())
        self.assertEqual(snapshot(self.base), before)  # 基座零写入
        report = json.loads(out.read_text(encoding="utf-8"))
        ext = report["external_sources_unverified"]
        self.assertEqual(
            [(e["path"], e["url"]) for e in ext],
            sorted((e["path"], e["url"]) for e in ext))  # 稳定排序
        self.assertEqual(len(ext), 4)
        self.assertTrue(report["wrong_source_suspects"])
        ws = report["wrong_source_suspects"]
        self.assertEqual([s["path"] for s in ws],
                         sorted(s["path"] for s in ws))

    def test_external_url_with_signature_hash_not_upgraded(self):
        # URL-only + 转换器签名 + 哈希：recorded-at-conversion 第②要件
        # （同基座可解析来源）不成立，绝不升级；哈希对外部URL不可核验
        head = (f"<!--\n来源 URL: {WEB_URL}\n-->\n"
                f"<!-- source_sha256: {'a' * 64} -->\n"
                "<!-- extracted_by: markitdown via convert_doc.py v2"
                " (2026-01-01) -->\n")
        write_raw_md_head(self.base, "conv.md", head)
        # 旧 source 字段完整值为 URL + 签名 + 哈希：同样撤销升级
        write_raw_md(self.base, "conv2.md", WEB_URL, "b" * 64,
                     "markitdown via convert_doc.py v2 (2026-01-01)")
        report = pi.run_inventory(self.base)
        for rel in ("raw/conv.md", "raw/conv2.md"):
            item = report["items"][rel]
            self.assertEqual(item["source_kind"], "external-url")
            self.assertIsNone(item.get("provenance_class"))  # 不升级
            self.assertEqual(item["hash_check"], "unknown-scope")
            self.assertIn("source_sha256_declared", item)
        self.assertIn("第②要件",
                      report["items"]["raw/conv2.md"]
                      .get("hash_semantics_basis", ""))

    def test_new_sections_always_present_on_clean_base(self):
        report = pi.run_inventory(self.base)
        self.assertEqual(report["external_sources_unverified"], [])
        self.assertEqual(report["source_declaration_conflicts"], [])
        self.assertEqual(report["source_declaration_errors"], [])
        self.assertEqual(report["local_archive_findings"], [])
        self.assertEqual(report["external_verification"]["status"],
                         "no-external-declarations")
        self.assertFalse(pi.has_findings(report))


# --- recognize-web-capture-provenance：独立本地存档观察（任务 3.1）---

ARCHIVE_BYTES = b"<html>ARCHIVE-ORIGINAL</html>"


def write_web_md_with_archive(base: Path, rel: str, url: str,
                              archive: str | None,
                              archive_sha: str | None = None,
                              archive_at: str | None = None) -> Path:
    lines = ["<!--", f"来源 URL: {url}", "抓取时间: 2026-11-07"]
    if archive is not None:
        lines.append(f"local_archive: {archive}")
    if archive_sha is not None:
        lines.append(f"local_archive_sha256_observed: {archive_sha}")
    if archive_at is not None:
        lines.append(f"local_archive_observed_at: {archive_at}")
    lines.append("-->")
    return write_raw_md_head(base, rel, "\n".join(lines) + "\n")


class LocalArchiveObservationTest(unittest.TestCase):
    """local_archive 只作独立关系观察：两时点哈希分列，不升级真实性。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _findings_for(self, report: dict, rel: str) -> list[dict]:
        return [f for f in report["local_archive_findings"]
                if f["path"] == rel]

    def _obs(self, report: dict, rel: str) -> list[dict]:
        return report["items"][rel]["local_archive_observations"]

    def test_archive_present_two_timepoint_hashes(self):
        (self.base / "incoming" / "web.html").write_bytes(ARCHIVE_BYTES)
        declared_sha = sha(ARCHIVE_BYTES)
        write_web_md_with_archive(
            self.base, "a.md", WEB_URL, "incoming/web.html",
            archive_sha=declared_sha, archive_at="2026-11-07T10:00:00+08:00")
        report = pi.run_inventory(self.base)
        obs = self._obs(report, "raw/a.md")
        self.assertEqual(len(obs), 1)
        self.assertEqual(obs[0]["accessibility"], "accessible")
        self.assertEqual(obs[0]["resolved_path"], "incoming/web.html")
        self.assertEqual(obs[0]["sha256_observed"], sha(ARCHIVE_BYTES))
        self.assertTrue(obs[0]["observed_at"])               # 本次观察时点
        # 两时点分列：声明观察时点 ≠ 本次观察时点
        self.assertEqual(obs[0]["declared_sha256_observed"], declared_sha)
        self.assertEqual(obs[0]["declared_observed_at"],
                         "2026-11-07T10:00:00+08:00")
        self.assertNotEqual(obs[0]["declared_observed_at"],
                            obs[0]["observed_at"])
        self.assertEqual(obs[0]["hash_check"], "match-observed")
        # 存档不代替网页来源：external-url 摘要与未核验清单照旧
        item = report["items"]["raw/a.md"]
        self.assertEqual(item["source_kind"], "external-url")
        self.assertEqual(report["external_sources_unverified"][0]["url"],
                         WEB_URL)
        # 当前字节一致也只证明当前一致：不升级分级
        self.assertIsNone(item.get("provenance_class"))
        self.assertEqual(self._findings_for(report, "raw/a.md"), [])

    def test_archive_hash_mismatch_observed_two_timepoints(self):
        (self.base / "incoming" / "web.html").write_bytes(ARCHIVE_BYTES)
        write_web_md_with_archive(
            self.base, "a.md", WEB_URL, "incoming/web.html",
            archive_sha="0" * 64, archive_at="2026-11-07T10:00:00+08:00")
        report = pi.run_inventory(self.base)
        obs = self._obs(report, "raw/a.md")
        self.assertEqual(obs[0]["hash_check"], "mismatch-observed")
        self.assertEqual(obs[0]["declared_sha256_observed"], "0" * 64)
        self.assertEqual(obs[0]["sha256_observed"], sha(ARCHIVE_BYTES))
        f = self._findings_for(report, "raw/a.md")
        self.assertEqual([x["kind"] for x in f], ["hash-mismatch-observed"])

    def test_archive_invalid_declared_hash(self):
        (self.base / "incoming" / "web.html").write_bytes(ARCHIVE_BYTES)
        write_web_md_with_archive(self.base, "a.md", WEB_URL,
                                  "incoming/web.html", archive_sha="zzz")
        report = pi.run_inventory(self.base)
        obs = self._obs(report, "raw/a.md")
        self.assertIsNone(obs[0]["declared_sha256_observed"])
        self.assertEqual([x["kind"] for x in
                          self._findings_for(report, "raw/a.md")],
                         ["invalid-hash"])

    def test_archive_missing_keeps_external_unverified(self):
        write_web_md_with_archive(self.base, "a.md", WEB_URL,
                                  "incoming/不存在.html")
        report = pi.run_inventory(self.base)
        obs = self._obs(report, "raw/a.md")
        self.assertEqual(obs[0]["accessibility"], "missing")
        self.assertIsNone(obs[0]["sha256_observed"])
        kinds = [x["kind"] for x in self._findings_for(report, "raw/a.md")]
        self.assertEqual(kinds, ["missing"])
        # 存档缺失 ≠ 网页原件不存在：外部未核验照旧
        self.assertEqual(report["external_sources_unverified"][0]["url"],
                         WEB_URL)

    @unittest.skipIf(os.geteuid() == 0, "root 无视权限位，chmod 000 不生效")
    def test_archive_read_failure_reported(self):
        arch = self.base / "incoming" / "web.html"
        arch.write_bytes(ARCHIVE_BYTES)
        os.chmod(arch, 0o000)
        try:
            write_web_md_with_archive(self.base, "a.md", WEB_URL,
                                      "incoming/web.html")
            report = pi.run_inventory(self.base)
        finally:
            os.chmod(arch, 0o644)
        obs = self._obs(report, "raw/a.md")
        self.assertEqual(obs[0]["accessibility"], "permission-denied")
        self.assertIsNone(obs[0]["sha256_observed"])
        kinds = [x["kind"] for x in self._findings_for(report, "raw/a.md")]
        self.assertEqual(kinds, ["read-error"])
        self.assertEqual(report["external_sources_unverified"][0]["url"],
                         WEB_URL)

    def test_archive_boundary_not_read(self):
        # 基座外绝对路径
        outside = self.root / "elsewhere" / "web.html"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_bytes(b"OTHER-COMPANY-SECRET")
        write_web_md_with_archive(self.base, "a1.md", WEB_URL,
                                  str(outside))
        # 相对路径越界（..）
        write_web_md_with_archive(self.base, "a2.md", WEB_URL,
                                  "../elsewhere/web.html")
        # 基座内符号链接指向基座外
        link = self.base / "incoming" / "link.html"
        link.symlink_to(outside)
        write_web_md_with_archive(self.base, "a3.md", WEB_URL,
                                  "incoming/link.html")
        report = pi.run_inventory(self.base)
        for rel in ("raw/a1.md", "raw/a2.md", "raw/a3.md"):
            obs = self._obs(report, rel)
            self.assertEqual(obs[0]["accessibility"], "boundary-violation")
            # 越界不读取：无字节哈希，不泄露内容
            self.assertIsNone(obs[0]["sha256_observed"])
            self.assertNotIn("resolved_path", obs[0])
            kinds = [x["kind"] for x in self._findings_for(report, rel)]
            self.assertEqual(kinds, ["boundary"])

    def test_archive_multi_declaration_conflict_unbound_hash(self):
        (self.base / "incoming" / "a.html").write_bytes(b"AAA")
        (self.base / "incoming" / "b.html").write_bytes(b"BBB")
        head = ("<!--\n"
                f"来源 URL: {WEB_URL}\n"
                "local_archive: incoming/a.html\n"
                "local_archive: incoming/b.html\n"
                f"local_archive_sha256_observed: {sha(b'AAA')}\n"
                "local_archive_observed_at: 2026-11-07T10:00:00+08:00\n"
                "-->\n")
        write_raw_md_head(self.base, "a.md", head)
        report = pi.run_inventory(self.base)
        obs = self._obs(report, "raw/a.md")
        self.assertEqual(len(obs), 2)      # 逐项保留观察，不选首条权威
        for o in obs:
            # 游离哈希无法唯一绑定：不静默套用到任何一条
            self.assertIsNone(o["declared_sha256_observed"])
        kinds = sorted(x["kind"] for x
                       in self._findings_for(report, "raw/a.md"))
        self.assertEqual(kinds, ["archive-conflict", "unresolved-hash-binding"])

    def test_no_same_name_html_inference(self):
        # URL 已声明，raw 旁存在同名 HTML 但无 local_archive 声明
        (self.base / "incoming" / "web.html").write_bytes(ARCHIVE_BYTES)
        head = f"<!--\n来源 URL: {WEB_URL}\n-->\n"
        write_raw_md_head(self.base, "web.md", head)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/web.md"]
        self.assertNotIn("local_archive_observations", item)
        self.assertEqual(report["local_archive_findings"], [])
        # 同名 HTML 未被自动列为已确认存档
        html_item = report["items"]["incoming/web.html"]
        self.assertEqual(html_item["kind"], "original")

    def test_archive_alone_does_not_replace_missing_source(self):
        (self.base / "incoming" / "web.html").write_bytes(ARCHIVE_BYTES)
        head = "<!--\nlocal_archive: incoming/web.html\n-->\n"
        write_raw_md_head(self.base, "solo.md", head)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/solo.md"]
        # 存档声明不消除真正 missing_source
        g = [gg for gg in report["gaps"]["missing_source"]
             if gg["path"] == "raw/solo.md"]
        self.assertEqual(len(g), 1)
        # 但观察照做
        self.assertEqual(self._obs(report, "raw/solo.md")[0]
                         ["sha256_observed"], sha(ARCHIVE_BYTES))

    def test_cross_company_same_archive_path_not_reused(self):
        # 两家公司基座同名相对路径、字节不同：各观察各的，不复用
        co_a = self.base
        co_b = make_base(self.root, "co2")
        (co_a / "incoming" / "shared.html").write_bytes(b"COMPANY-A")
        (co_b / "incoming" / "shared.html").write_bytes(b"COMPANY-B")
        head = "<!--\nlocal_archive: incoming/shared.html\n-->\n"
        write_raw_md_head(co_a, "a.md", head)
        write_raw_md_head(co_b, "a.md", head)
        ra = pi.run_inventory(co_a)
        rb = pi.run_inventory(co_b)
        self.assertEqual(ra["items"]["raw/a.md"]["local_archive_observations"]
                         [0]["sha256_observed"], sha(b"COMPANY-A"))
        self.assertEqual(rb["items"]["raw/a.md"]["local_archive_observations"]
                         [0]["sha256_observed"], sha(b"COMPANY-B"))


# --- recognize-web-capture-provenance：独立复核修复回归（第二批，2026-11-14）---
# 五类问题（依据独立复核探针 /tmp/opencode/probe_rv + 复核扩展探针重建）：
#   C1 游离存档哈希（零 local_archive 路径）完全静默：
#      合法格式无 unresolved-hash-binding、非法格式无 invalid-hash、
#      local_archive_observations 键缺失（spec 场景11「游离哈希…报告未解决绑定」）。
#   C2 同头部多条不同 local_archive_sha256_observed：首条静默绑定，
#      hash_check 按首条判定（match 可掩盖冲突产生零发现）（spec 场景4/11）。
#   C3 多值观察时间/抓取时间冲突首条静默采用：local_archive_observed_at
#      与 抓取时间 均不报冲突（spec 场景4「多项声明并存不被隐藏」）。
#   C4 local_archive 值非法形态（URL 形态/空值）被当路径解析：
#      URL 形态 → in-base 假 missing；空值 → 解析成基座目录 EISDIR 假 read-error
#      （spec 场景3 原则「不猜测文件路径」）。
#   C5 SKILL.md 文档漂移（无 pytest 用例，由文档更新 + check 对齐，
#      见 SKILL.md §网页抓取声明识别 / §本地网页存档观察）。


class IndependentReviewFixRegressionTest(unittest.TestCase):
    """独立复核发现修复回归：只做加法发现，不放宽任何既有规则。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _findings_for(self, report: dict, rel: str) -> list[dict]:
        return [f for f in report["local_archive_findings"]
                if f["path"] == rel]

    def _kinds(self, report: dict, rel: str) -> list[str]:
        return sorted(x["kind"] for x in self._findings_for(report, rel))

    # --- C1：游离哈希（零路径） ---

    def test_orphan_valid_hash_zero_path_unresolved_binding(self):
        # probe_rv/03.md 同构：URL + 游离合法哈希，无任何 local_archive 路径
        head = ("<!--\n"
                f"来源 URL: {WEB_URL}\n"
                f"local_archive_sha256_observed: {sha(b'ORPHAN')}\n"
                "-->\n")
        write_raw_md_head(self.base, "a.md", head)
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        # 零路径 = 无法唯一绑定 → unresolved-hash-binding 必须出现
        self.assertEqual(self._kinds(report, "raw/a.md"),
                         ["unresolved-hash-binding"])
        f = self._findings_for(report, "raw/a.md")[0]
        self.assertEqual(f["declared_paths"], [])
        self.assertEqual(f["declared_sha256_observed"], sha(b"ORPHAN"))
        # observations 键一致存在（空列表），外部未核验照旧，不算 missing_source
        item = report["items"]["raw/a.md"]
        self.assertEqual(item["local_archive_observations"], [])
        self.assertEqual(item["source_kind"], "external-url")
        g = report["gaps"]
        self.assertEqual([x for x in g["missing_source"]
                          if x["path"] == "raw/a.md"], [])
        self.assertTrue(pi.has_findings(report))
        self.assertEqual(snapshot(self.base), before)  # 零写入

    def test_orphan_invalid_hash_zero_path_invalid_hash_reported(self):
        # probe_rv2/h6 同构：非法格式游离哈希 → invalid-hash 也要报告
        head = ("<!--\n"
                f"来源 URL: {WEB_URL}\n"
                "local_archive_sha256_observed: zz-not-hex\n"
                "-->\n")
        write_raw_md_head(self.base, "a.md", head)
        report = pi.run_inventory(self.base)
        self.assertEqual(self._kinds(report, "raw/a.md"), ["invalid-hash"])
        self.assertEqual(
            report["items"]["raw/a.md"]["local_archive_observations"], [])

    # --- C2：多值哈希冲突 ---

    def test_conflicting_hashes_first_match_not_authoritative(self):
        # probe_rv/04.md 升级版：存档存在且首条哈希恰好等于当前字节
        # （修复前：match-observed + 零冲突发现 = 虚假干净）
        (self.base / "incoming" / "web.html").write_bytes(ARCHIVE_BYTES)
        head = ("<!--\n"
                f"来源 URL: {WEB_URL}\n"
                "local_archive: incoming/web.html\n"
                f"local_archive_sha256_observed: {sha(ARCHIVE_BYTES)}\n"
                f"local_archive_sha256_observed: {sha(b'OTHER')}\n"
                "-->\n")
        write_raw_md_head(self.base, "a.md", head)
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        self.assertEqual(self._kinds(report, "raw/a.md"),
                         ["declared-hash-conflict"])
        f = self._findings_for(report, "raw/a.md")[0]
        self.assertEqual(f["declared_sha256_values"],
                         sorted([sha(ARCHIVE_BYTES), sha(b'OTHER')]))
        obs = report["items"]["raw/a.md"]["local_archive_observations"]
        self.assertEqual(len(obs), 1)
        # 冲突 → 不绑定任何一条，不按首条判 match/mismatch
        self.assertIsNone(obs[0]["declared_sha256_observed"])
        self.assertEqual(obs[0]["hash_check"], "unresolved-declared-hash")
        # 当前字节照常观察（两时点分列原则不因冲突取消）
        self.assertEqual(obs[0]["sha256_observed"], sha(ARCHIVE_BYTES))
        self.assertEqual(snapshot(self.base), before)

    def test_conflicting_hashes_no_mismatch_against_first(self):
        # 修复前：按首条判 mismatch-observed（首条被当作权威基准）
        (self.base / "incoming" / "web.html").write_bytes(ARCHIVE_BYTES)
        head = ("<!--\n"
                "local_archive: incoming/web.html\n"
                f"local_archive_sha256_observed: {sha(b'X1')}\n"
                f"local_archive_sha256_observed: {sha(b'X2')}\n"
                "-->\n")
        write_raw_md_head(self.base, "a.md", head)
        report = pi.run_inventory(self.base)
        self.assertEqual(self._kinds(report, "raw/a.md"),
                         ["declared-hash-conflict"])
        obs = report["items"]["raw/a.md"]["local_archive_observations"]
        self.assertEqual(obs[0]["hash_check"], "unresolved-declared-hash")

    # --- C3：多值观察时间 / 抓取时间冲突 ---

    def test_conflicting_observed_at_not_first_bound(self):
        (self.base / "incoming" / "web.html").write_bytes(ARCHIVE_BYTES)
        head = ("<!--\n"
                "local_archive: incoming/web.html\n"
                f"local_archive_sha256_observed: {sha(ARCHIVE_BYTES)}\n"
                "local_archive_observed_at: 2026-11-07T10:00:00+08:00\n"
                "local_archive_observed_at: 2026-11-08T10:00:00+08:00\n"
                "-->\n")
        write_raw_md_head(self.base, "a.md", head)
        report = pi.run_inventory(self.base)
        self.assertIn("observed-at-conflict", self._kinds(report, "raw/a.md"))
        f = [x for x in self._findings_for(report, "raw/a.md")
             if x["kind"] == "observed-at-conflict"][0]
        self.assertEqual(f["declared_observed_at_values"],
                         ["2026-11-07T10:00:00+08:00",
                          "2026-11-08T10:00:00+08:00"])
        obs = report["items"]["raw/a.md"]["local_archive_observations"]
        # 冲突 → 声明观察时间不绑定首条
        self.assertIsNone(obs[0]["declared_observed_at"])

    def test_conflicting_captured_at_conflict_reported(self):
        head = ("<!--\n"
                f"来源 URL: {WEB_URL}\n"
                "抓取时间: 2026-11-07\n"
                "抓取时间: 2026-11-08\n"
                "-->\n")
        write_raw_md_head(self.base, "a.md", head)
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        conf = report["source_declaration_conflicts"]
        self.assertEqual(len(conf), 1)
        self.assertEqual(conf[0]["path"], "raw/a.md")
        self.assertEqual(conf[0]["kind"], "captured-at")
        self.assertEqual(conf[0]["values"], ["2026-11-07", "2026-11-08"])
        # 外部条目不带单一权威时间（不选首条）
        ext = report["external_sources_unverified"]
        self.assertNotIn("captured_at", ext[0])
        self.assertEqual(snapshot(self.base), before)

    # --- C4：local_archive 值非法形态 ---

    def test_archive_url_shaped_value_never_resolved(self):
        # 诱饵：基座内真的存在以 URL 字面量拼出的"路径"，
        # 修复前会 resolve+读字节（accessible）；修复后不 resolve 不读。
        decoy = self.base / "https:" / "example.invalid" / "page.html"
        decoy.parent.mkdir(parents=True, exist_ok=True)
        decoy.write_bytes(b"DECOY-CONTENT")
        head = ("<!--\n"
                f"来源 URL: {WEB_URL}\n"
                "local_archive: https://example.invalid/page.html\n"
                "-->\n")
        write_raw_md_head(self.base, "a.md", head)
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        self.assertEqual(self._kinds(report, "raw/a.md"),
                         ["invalid-archive-declaration"])
        f = self._findings_for(report, "raw/a.md")[0]
        self.assertEqual(f["issue"], "url-shaped")
        self.assertEqual(f["declared_path"], "https://example.invalid/page.html")
        # 不产生 accessible/missing/boundary 假观察，不读诱饵字节
        obs = report["items"]["raw/a.md"]["local_archive_observations"]
        self.assertEqual(obs, [])
        self.assertEqual(snapshot(self.base), before)

    def test_archive_empty_value_not_dir_read(self):
        # 修复前：空值 resolve 成基座目录本身 → EISDIR 假 read-error
        head = "<!--\nlocal_archive:\n-->\n"
        write_raw_md_head(self.base, "a.md", head)
        report = pi.run_inventory(self.base)
        self.assertEqual(self._kinds(report, "raw/a.md"),
                         ["invalid-archive-declaration"])
        f = self._findings_for(report, "raw/a.md")[0]
        self.assertEqual(f["issue"], "empty-value")
        self.assertEqual(
            report["items"]["raw/a.md"]["local_archive_observations"], [])

    # --- 混合场景：C1+C4 并存，全部声明保留 ---

    def test_invalid_path_plus_orphan_hash_all_findings_kept(self):
        head = ("<!--\n"
                f"来源 URL: {WEB_URL}\n"
                "local_archive: https://example.invalid/x.html\n"
                f"local_archive_sha256_observed: {sha(b'K')}\n"
                "-->\n")
        write_raw_md_head(self.base, "a.md", head)
        report = pi.run_inventory(self.base)
        # 非法路径声明 + 合法哈希零有效路径：两类发现并存，不互相掩盖
        self.assertEqual(self._kinds(report, "raw/a.md"),
                         ["invalid-archive-declaration",
                          "unresolved-hash-binding"])
        # 全部声明原样保留在 source_declarations
        decls = report["items"]["raw/a.md"]["source_declarations"]
        self.assertEqual([d["field"] for d in decls],
                         ["来源 URL", "local_archive",
                          "local_archive_sha256_observed"])


# --- recognize-web-capture-provenance：复核遗漏补充回归（第三批，2026-11-14）---
# 原独立复核（第二批）遗漏的两类输入形态（探针 /tmp/opencode/probe_rv3/probe.py 复现）：
#   G1 文首两条旧 source/source_path 一条 URL 一条本地路径（两种顺序）：
#      修复前 parse_raw_md_provenance 只取先出现的一条，另一条整条静默丢弃——
#      URL 在前 → 本地路径不解析、缺失零报告（source_kind=external-url）；
#      本地在前 → URL 不进外部未核验清单（source_kind=local）
#      （spec 场景4「多项声明并存不被隐藏…不以有效URL掩盖本地来源缺失」）。
#   G2 正文、围栏代码块、后置注释中的旧 source/source_path URL 成为有效网页来源：
#      修复前 INLINE/BLOCK 正则对 4000 字符头全文检索，正文命中被当外部声明
#      （spec 场景3「URL只在声明位置识别」）。
#      修复约束：不得收紧本地路径既有兼容行为（正文中的本地 source 命中照旧有效）。


class ReviewGapFixRegressionTest(unittest.TestCase):
    """第三批复核遗漏修复回归：双声明并存不隐藏；URL 只认文首声明位置。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _gaps_for(self, report: dict, rel: str) -> dict:
        return {k: [g for g in v if g["path"] == rel]
                for k, v in report["gaps"].items()}

    # --- G1：文首 URL+本地双声明，两种顺序，双方都保留 ---

    def test_head_url_then_local_both_kept_missing_reported(self):
        # 顺序一：URL 在前、本地路径在后（修复前：本地整条丢弃，缺失零报告）
        head = (f"<!-- source: {WEB_URL} -->\n"
                "<!-- source_path: incoming/missing.docx -->\n")
        write_raw_md_head(self.base, "m1.md", head)
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/m1.md"]
        self.assertEqual(item["source_kind"], "mixed")
        # 双方声明都保留：URL 进声明表（原字段/原值/行位置）
        url_decls = [d for d in item["source_declarations"]
                     if d["kind"] == "source-url"]
        self.assertEqual([(d["field"], d["value"], d["line"])
                          for d in url_decls],
                         [("source", WEB_URL, 1)])
        # URL 进外部未核验清单
        self.assertEqual([(e["path"], e["url"])
                          for e in report["external_sources_unverified"]],
                         [("raw/m1.md", WEB_URL)])
        # 本地声明保留并照常校验：declared_source=本地路径，缺失如实报告
        self.assertEqual(item["declared_source"], "incoming/missing.docx")
        self.assertEqual(item["declared_via"], "source_path")
        self.assertEqual(item["accessibility"], "missing")
        self.assertEqual(
            len(self._gaps_for(report, "raw/m1.md")["missing_original"]), 1)
        # 不因 URL 掩盖而漏报，也不误报 missing_source
        self.assertEqual(
            self._gaps_for(report, "raw/m1.md")["missing_source"], [])
        self.assertTrue(pi.has_findings(report))
        self.assertEqual(snapshot(self.base), before)  # 零写入

    def test_head_local_then_url_both_kept_missing_reported(self):
        # 顺序二：本地路径在前、URL 在后（块形态 URL + 行内本地，覆盖两种载体；
        # 修复前：URL 整条丢弃，不进外部未核验清单）
        head = ("<!--\n"
                f"source_path: {WEB_URL}\n"
                "-->\n"
                "<!-- source: incoming/missing.docx -->\n")
        write_raw_md_head(self.base, "m2.md", head)
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/m2.md"]
        self.assertEqual(item["source_kind"], "mixed")
        url_decls = [d for d in item["source_declarations"]
                     if d["kind"] == "source-url"]
        self.assertEqual([(d["field"], d["value"]) for d in url_decls],
                         [("source_path", WEB_URL)])
        self.assertEqual([(e["path"], e["url"])
                          for e in report["external_sources_unverified"]],
                         [("raw/m2.md", WEB_URL)])
        self.assertEqual(item["declared_source"], "incoming/missing.docx")
        self.assertEqual(item["declared_via"], "source")
        self.assertEqual(
            len(self._gaps_for(report, "raw/m2.md")["missing_original"]), 1)
        self.assertEqual(
            self._gaps_for(report, "raw/m2.md")["missing_source"], [])
        self.assertTrue(pi.has_findings(report))
        self.assertEqual(snapshot(self.base), before)  # 零写入

    def test_head_url_and_existing_local_hash_match_mixed(self):
        # 本地原件存在且哈希匹配：URL 声明不打断本地核验通道（mixed 完整）
        (self.base / "incoming" / "orig.docx").write_bytes(b"O")
        head = (f"<!-- source_path: {WEB_URL} -->\n"
                f"<!-- source: incoming/orig.docx -->\n"
                f"<!-- source_sha256: {sha(b'O')} -->\n")
        write_raw_md_head(self.base, "m3.md", head)
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/m3.md"]
        self.assertEqual(item["source_kind"], "mixed")
        self.assertEqual(item["source"], "incoming/orig.docx")
        self.assertEqual(item["hash_check"], "match")
        self.assertEqual(item["declared_source"], "incoming/orig.docx")
        self.assertEqual(item["declared_via"], "source")
        self.assertEqual([e["url"]
                          for e in report["external_sources_unverified"]],
                         [WEB_URL])
        g = self._gaps_for(report, "raw/m3.md")
        self.assertEqual(g["missing_source"], [])
        self.assertEqual(g["missing_hash"], [])
        self.assertEqual(snapshot(self.base), before)  # 零写入

    # --- G2：正文/代码块/后置注释中的旧 source URL 不是有效网页来源 ---

    def test_body_old_source_url_not_web_source(self):
        # 修复前：正文注释中的旧 source URL 被当外部声明（external-url 分支）
        write_raw_md_head(self.base, "b1.md", "",
                          body=f"正文开头\n\n<!-- source: {WEB_URL} -->\n\n"
                               "结尾\n")
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/b1.md"]
        self.assertEqual(item.get("source_declarations"), [])
        self.assertEqual([e for e in report["external_sources_unverified"]
                          if e["path"] == "raw/b1.md"], [])
        self.assertNotEqual(item.get("source_kind"), "external-url")
        # 无可用声明来源 → missing_source 如实；URL 绝不当本地路径
        g = self._gaps_for(report, "raw/b1.md")
        self.assertEqual(len(g["missing_source"]), 1)
        self.assertEqual(g["missing_original"], [])
        self.assertEqual(report["boundary_violations"], [])
        self.assertEqual(snapshot(self.base), before)  # 零写入

    def test_code_block_old_source_url_not_web_source(self):
        # 围栏代码块内的旧 source 注释是文档内容，不是声明位置
        write_raw_md_head(self.base, "b2.md", "",
                          body=f"说明\n\n```\n<!-- source: {WEB_URL} -->\n```\n")
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/b2.md"]
        self.assertEqual(item.get("source_declarations"), [])
        self.assertEqual([e for e in report["external_sources_unverified"]
                          if e["path"] == "raw/b2.md"], [])
        self.assertNotEqual(item.get("source_kind"), "external-url")
        g = self._gaps_for(report, "raw/b2.md")
        self.assertEqual(len(g["missing_source"]), 1)
        self.assertEqual(g["missing_original"], [])
        self.assertEqual(snapshot(self.base), before)  # 零写入

    def test_post_comment_old_source_path_url_not_web_source(self):
        # 后置注释（正文之后）中的旧 source_path URL 同样不是声明位置
        write_raw_md_head(self.base, "b3.md", "正文段落\n",
                          body=f"\n<!-- source_path: {WEB_URL} -->\n")
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/b3.md"]
        self.assertEqual(item.get("source_declarations"), [])
        self.assertEqual([e for e in report["external_sources_unverified"]
                          if e["path"] == "raw/b3.md"], [])
        self.assertNotEqual(item.get("source_kind"), "external-url")
        g = self._gaps_for(report, "raw/b3.md")
        self.assertEqual(len(g["missing_source"]), 1)
        self.assertEqual(g["missing_original"], [])
        self.assertEqual(snapshot(self.base), before)  # 零写入

    def test_body_url_does_not_mask_head_local(self):
        # 文首本地 source + 正文 URL 注释：URL 整体忽略，本地照常（local 非 mixed）
        (self.base / "incoming" / "orig.docx").write_bytes(b"O")
        head = (f"<!-- source: incoming/orig.docx -->\n"
                f"<!-- source_sha256: {sha(b'O')} -->\n")
        write_raw_md_head(self.base, "b4.md", head,
                          body=f"正文\n\n<!-- source: {WEB_URL} -->\n")
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/b4.md"]
        self.assertEqual(item["source_kind"], "local")
        self.assertEqual(item["hash_check"], "match")
        self.assertEqual([e for e in report["external_sources_unverified"]
                          if e["path"] == "raw/b4.md"], [])
        self.assertEqual(snapshot(self.base), before)  # 零写入

    # --- G2 修复约束：本地路径既有兼容行为不得收紧 ---

    def test_body_only_local_source_compat_unchanged(self):
        # 正文中的本地路径 source 命中：修复前就有效，修复后必须仍然有效
        (self.base / "incoming" / "orig.docx").write_bytes(b"O")
        write_raw_md_head(self.base, "b5.md", "",
                          body=f"正文\n\n<!-- source: incoming/orig.docx -->\n")
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/b5.md"]
        self.assertEqual(item["source_kind"], "local")
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["source"], "incoming/orig.docx")
        g = self._gaps_for(report, "raw/b5.md")
        self.assertEqual(g["missing_source"], [])
        self.assertEqual(snapshot(self.base), before)  # 零写入

    def test_head_url_and_body_local_both_kept_compat(self):
        # 文首 URL + 正文本地 source 并存：双方都保留（URL 外部未核验 +
        # 本地照常解析），且本地兼容不因 URL 出现而收紧
        (self.base / "incoming" / "orig.docx").write_bytes(b"O")
        write_raw_md_head(self.base, "b6.md", f"<!-- source: {WEB_URL} -->\n",
                          body="正文\n\n<!-- source_path: incoming/orig.docx"
                               " -->\n")
        before = snapshot(self.base)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/b6.md"]
        self.assertEqual(item["source_kind"], "mixed")
        self.assertEqual(item["declared_source"], "incoming/orig.docx")
        self.assertEqual(item["declared_via"], "source_path")
        self.assertEqual(item["source"], "incoming/orig.docx")
        self.assertEqual([(e["path"], e["url"])
                          for e in report["external_sources_unverified"]],
                         [("raw/b6.md", WEB_URL)])
        self.assertEqual(snapshot(self.base), before)  # 零写入


# --- inspect-material-source-fragments：materials 片段来源回归（任务 1.1 / 2.1）---
# 真实锚点（只读登记于 tests/fixtures_registry.json，正文不复制）：
#   lianyou materials frontmatter source = raw/_extracted/slides.jsonl#溯源系统证书-1.png
#   —— 完整字面文件不存在、容器存在。旧实现把整串当文件路径误报 missing_original。
# 核心测试全部合成基座；语法守卫以联友其余四条描述性/复合来源为同构校准，
# 保证它们保持 missing_original 诊断不变（不借猜测拆分消除真实缺口）。


def write_material_md(base: Path, rel: str, source: str | None) -> Path:
    p = base / "materials" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if source is None:
        p.write_text("无 frontmatter 正文\n", encoding="utf-8")
    else:
        p.write_text(f"---\nsource: {source}\n---\n\n正文\n", encoding="utf-8")
    return p


def snapshot_all(root: Path) -> dict:
    """零写入断言用全树快照（覆盖基座外哨兵/双公司文件）。

    普通文件按字节哈希；symlink 按链接目标记录（自环/越界链接的目标字节
    既不可读也不该读——链接身份即其内容）。
    """
    out = {}
    for cur, dirs, files in os.walk(root):
        for name in dirs + files:
            p = Path(cur) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink():
                out[rel] = "symlink:" + os.readlink(p)
            elif p.is_file():
                out[rel] = sha(p.read_bytes())
    return out


FRAG_CERT = "raw/_extracted/slides.jsonl#溯源系统证书-1.png"


class MaterialFragmentSourceSyntaxTest(unittest.TestCase):
    """任务 1.1：字面路径优先 + 受限 .jsonl 片段语法 + 兼容守卫（先红后绿）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _frag_findings(self, report: dict) -> list[dict]:
        return report.get("material_source_fragment_findings", [])

    def _gaps_for(self, report: dict, rel: str) -> dict:
        return {k: [g for g in v if g["path"] == rel]
                for k, v in report["gaps"].items()}

    # 完整#文件与截断容器同时存在 → 字面完整路径优先，不拆
    def test_literal_hash_path_wins_over_truncated_container(self):
        (self.base / "raw" / "deck.jsonl").write_bytes(b"CONTAINER")
        literal = self.base / "raw" / "deck.jsonl#slide 1.png"
        literal.write_bytes(b"LITERAL-FILE")
        write_material_md(self.base, "幻灯.md", "raw/deck.jsonl#slide 1.png")
        before = snapshot_all(self.root)
        report = pi.run_inventory(self.base)
        item = report["items"]["materials/幻灯.md"]
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["source"], "raw/deck.jsonl#slide 1.png")
        self.assertEqual(item["source_accessibility"], "accessible")
        self.assertNotIn("source_expression_kind", item)   # 不拆 fragment
        self.assertNotIn("source_container", item)
        self.assertNotIn("source_fragment", item)
        self.assertEqual(self._gaps_for(report, "materials/幻灯.md")
                         ["missing_original"], [])
        self.assertEqual(
            [f for f in self._frag_findings(report)
             if f["path"] == "materials/幻灯.md"], [])
        self.assertEqual(snapshot_all(self.root), before)      # 零写入

    # .jsonl 合法片段：容器可访问 → 锚点未核验单列，rc3，不再误报 missing_original
    def test_jsonl_fragment_container_accessible_anchor_not_verified(self):
        container = self.base / "raw" / "_extracted" / "slides.jsonl"
        container.parent.mkdir(parents=True)
        container.write_bytes(b'{"image": "\xff\x00\xfebinary"}')  # 坏编码容器
        write_material_md(self.base, "证书.md", FRAG_CERT)
        before = snapshot_all(self.root)
        report = pi.run_inventory(self.base)
        item = report["items"]["materials/证书.md"]
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["link_state"], "declared")
        self.assertEqual(item["declared_source"], FRAG_CERT)   # 原整串保留
        self.assertEqual(item["source_expression_kind"],
                         "local-file-fragment")
        self.assertEqual(item["source_container"],
                         "raw/_extracted/slides.jsonl")
        self.assertEqual(item["source_fragment"], "溯源系统证书-1.png")
        self.assertEqual(item["anchor_verification"], "not-performed")
        self.assertEqual(item["container_accessibility"], "accessible")
        self.assertEqual(item["projection_accessibility"], "accessible")
        self.assertEqual(item["source"], "raw/_extracted/slides.jsonl")
        self.assertEqual(item["hash_check"], "unknown-scope")
        # 默认不读容器正文：无哈希观察字段；坏编码不是锚点失败
        self.assertNotIn("container_sha256_observed", item)
        findings = [f for f in self._frag_findings(report)
                    if f["path"] == "materials/证书.md"]
        self.assertEqual(len(findings), 1)
        f = findings[0]
        self.assertEqual(f["kind"], "anchor-not-verified")
        self.assertEqual(f["declared_source"], FRAG_CERT)
        self.assertEqual(f["source_container"], "raw/_extracted/slides.jsonl")
        self.assertEqual(f["source_fragment"], "溯源系统证书-1.png")
        self.assertTrue(f["reason"])
        # 不再误报 missing_original；未核验独立计数 → 有发现
        self.assertEqual(self._gaps_for(report, "materials/证书.md")
                         ["missing_original"], [])
        self.assertTrue(pi.has_findings(report))
        r = run_cli(self.base)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(snapshot_all(self.root), before)      # 零写入

    # 多个 # 与 %2F 原样保留：按首个 # 拆分，不做 URL 解码
    def test_fragment_multiple_hash_and_percent_untouched(self):
        (self.base / "raw" / "s.jsonl").write_bytes(b"S")
        write_material_md(self.base, "多号.md", "raw/s.jsonl#a#b%2Fc.png")
        report = pi.run_inventory(self.base)
        item = report["items"]["materials/多号.md"]
        self.assertEqual(item["source_container"], "raw/s.jsonl")
        self.assertEqual(item["source_fragment"], "a#b%2Fc.png")  # 原样
        self.assertEqual(item["source"], "raw/s.jsonl")           # 不解码

    # 兼容守卫：空值/空片段/URL/非 .jsonl/说明文本 → 保留完整路径诊断，不拆
    def test_restricted_syntax_guards_keep_full_path_diagnosis(self):
        cases = [
            ("空片段.md", "raw/x.jsonl#"),
            ("非jsonl.md", "raw/notes.csv#frag"),
            ("url.md", "https://mp.example.invalid/a.jsonl#f"),
            ("scheme.md", "file:///opt/x/slides.jsonl#f"),
            ("片段空白.md", "raw/x.jsonl#证 书.png"),
            ("片段括注.md", "raw/x.jsonl#证书（见附注）.png"),
            ("片段分号.md", "raw/x.jsonl#证书；见附注"),
            ("左侧分号.md", "raw/a.jsonl；见附注#证书"),
            ("左侧括注.md", "raw/考证/slides.jsonl（OCR版）#证书"),
            ("控制字符.md", "raw/x.jsonl#证书\t.png"),
        ]
        for rel, src in cases:
            write_material_md(self.base, rel, src)
        before = snapshot_all(self.root)
        report = pi.run_inventory(self.base)
        for rel, src in cases:
            mrel = f"materials/{rel}"
            item = report["items"][mrel]
            self.assertEqual(item["declared_source"], src, mrel)
            self.assertNotIn("source_expression_kind", item, mrel)
            self.assertNotIn("source_container", item, mrel)
            self.assertEqual(
                len(self._gaps_for(report, mrel)["missing_original"]), 1, mrel)
            self.assertEqual(
                [f for f in self._frag_findings(report) if f["path"] == mrel],
                [], mrel)
        self.assertEqual(snapshot_all(self.root), before)      # 零写入

    # 兼容守卫：联友其余四条描述性/复合来源同构 → 诊断保持不变
    def test_four_descriptive_shapes_unchanged(self):
        shapes = [
            "incoming/战略分析素材/微信图片×2；出处已确认（2026-08-28）＝竞品方案"
            "文件《某建议》§三（materials/13-competitors/某建议.md）——截图为局部",
            "国家/省两级政策文件（incoming PDF OCR）+ 政府官网核验（gov.cn）",
            "联网检索（厂商官网/行业报道，厂商自述未实测）+ 用户补充画像"
            "（2026-08-27 会话，待第二来源核验）",
            "incoming/战略分析素材/某方案.pdf（竞品方案文件，2026-08-20，7 页；"
            "出自哪家竞品待确认 #12）；转换件 raw/战略分析素材/同名.md（pypdf 文本层）",
        ]
        for i, src in enumerate(shapes):
            write_material_md(self.base, f"描述{i}.md", src)
        report = pi.run_inventory(self.base)
        for i, src in enumerate(shapes):
            mrel = f"materials/描述{i}.md"
            item = report["items"][mrel]
            self.assertEqual(item["declared_source"], src, mrel)
            self.assertNotIn("source_expression_kind", item, mrel)
            self.assertEqual(
                len(self._gaps_for(report, mrel)["missing_original"]), 1, mrel)
        self.assertEqual(self._frag_findings(report), [])

    # 兼容守卫：source:none / 缺来源行为不变，不进片段逻辑
    def test_none_and_missing_source_unchanged(self):
        (self.base / "raw" / "c.jsonl").write_bytes(b"C")
        write_material_md(self.base, "authored.md", "none")
        write_material_md(self.base, "nosrc.md", None)
        write_material_md(self.base, "frag.md", "raw/c.jsonl#锚.png")
        report = pi.run_inventory(self.base)
        authored = report["items"]["materials/authored.md"]
        self.assertEqual(authored["source_nature"], "none")
        nosrc = report["items"]["materials/nosrc.md"]
        self.assertEqual(nosrc["source_nature"], "none")
        self.assertEqual(
            len(self._gaps_for(report, "materials/nosrc.md")["missing_source"]),
            1)
        frag = report["items"]["materials/frag.md"]
        self.assertEqual(frag["source_nature"], "declared")
        self.assertEqual(
            len(self._gaps_for(report, "materials/frag.md")["missing_source"]),
            0)


class MaterialFragmentContainerStateTest(unittest.TestCase):
    """任务 2.1：容器状态矩阵 / 回退阻断 / 越界不读 / full-hash / rc3 / repair。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _frag_findings(self, report: dict) -> list[dict]:
        return report.get("material_source_fragment_findings", [])

    def _gaps_for(self, report: dict, rel: str) -> dict:
        return {k: [g for g in v if g["path"] == rel]
                for k, v in report["gaps"].items()}

    def _finding(self, report: dict, mrel: str) -> dict:
        f = [x for x in self._frag_findings(report) if x["path"] == mrel]
        self.assertEqual(len(f), 1, mrel)
        return f[0]

    # 容器缺失：missing_original 记容器而非原整串，原声明与 fragment 保留
    def test_container_missing_records_container_not_whole_string(self):
        write_material_md(self.base, "缺容器.md", FRAG_CERT)
        before = snapshot_all(self.root)
        report = pi.run_inventory(self.base)
        item = report["items"]["materials/缺容器.md"]
        self.assertEqual(item["container_accessibility"], "missing")
        self.assertEqual(item["accessibility"], "missing")
        self.assertEqual(item["declared_source"], FRAG_CERT)
        self.assertEqual(item["source_container"], "raw/_extracted/slides.jsonl")
        self.assertEqual(item["source_fragment"], "溯源系统证书-1.png")
        self.assertEqual(item["anchor_verification"], "not-performed")
        gaps = self._gaps_for(report, "materials/缺容器.md")["missing_original"]
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["declared_source"], FRAG_CERT)
        self.assertEqual(gaps[0]["source_container"],
                         "raw/_extracted/slides.jsonl")
        self.assertEqual(gaps[0]["source_fragment"], "溯源系统证书-1.png")
        f = self._finding(report, "materials/缺容器.md")
        self.assertEqual(f["kind"], "container-missing")
        self.assertTrue(pi.has_findings(report))
        self.assertEqual(snapshot_all(self.root), before)      # 零写入

    # 容器是目录：不把目录当可用容器，不判锚点无效，不记 missing
    def test_container_directory_not_usable(self):
        (self.base / "raw" / "dir.jsonl").mkdir(parents=True)
        write_material_md(self.base, "目录容器.md", "raw/dir.jsonl#锚.png")
        report = pi.run_inventory(self.base)
        item = report["items"]["materials/目录容器.md"]
        self.assertEqual(item["container_accessibility"], "not-regular-file")
        f = self._finding(report, "materials/目录容器.md")
        self.assertEqual(f["kind"], "container-check-failed")
        self.assertEqual(
            self._gaps_for(report, "materials/目录容器.md")["missing_original"],
            [])
        self.assertTrue(pi.has_findings(report))

    # 容器 stat 观察失败（ELOOP 自环 symlink，root 也生效）：按失败报告，不判缺失
    def test_container_stat_error_eloop_reported(self):
        loop = self.base / "incoming" / "loop.jsonl"
        loop.symlink_to("loop.jsonl")   # 自环
        write_material_md(self.base, "环容器.md", "incoming/loop.jsonl#锚.png")
        report = pi.run_inventory(self.base)
        item = report["items"]["materials/环容器.md"]
        self.assertEqual(item["container_accessibility"], "inaccessible")
        self.assertEqual(
            self._gaps_for(report, "materials/环容器.md")["missing_original"],
            [])
        unver = [u for u in report["unverifiable_sources"]
                 if u["path"] == "materials/环容器.md"]
        self.assertEqual(len(unver), 1)
        self.assertIn("ELOOP", unver[0]["reason"])
        f = self._finding(report, "materials/环容器.md")
        self.assertEqual(f["kind"], "container-check-failed")

    # 完整字面路径 stat 失败（EACCES）不得触发截断回退
    @unittest.skipIf(os.geteuid() == 0, "root 无视权限位，chmod 000 不生效")
    def test_full_literal_stat_error_no_truncation_fallback(self):
        locked = self.base / "incoming" / "locked"
        locked.mkdir()
        (locked / "slides.jsonl").write_bytes(b"CONTAINER-INSIDE")
        write_material_md(self.base, "锁定.md", "incoming/locked/slides.jsonl#锚.png")
        os.chmod(locked, 0o000)
        try:
            report = pi.run_inventory(self.base)
        finally:
            os.chmod(locked, 0o755)
        item = report["items"]["materials/锁定.md"]
        self.assertEqual(item["accessibility"], "permission-denied")
        self.assertNotIn("source_expression_kind", item)   # 不回退拆分
        self.assertNotIn("source_container", item)
        self.assertEqual(self._frag_findings(report), [])   # 不产生片段发现
        unver = [u for u in report["unverifiable_sources"]
                 if u["path"] == "materials/锁定.md"]
        self.assertEqual(len(unver), 1)
        self.assertIn("EACCES", unver[0]["reason"])
        self.assertEqual(
            self._gaps_for(report, "materials/锁定.md")["missing_original"], [])

    # 完整字面路径越界不得触发截断回退（哨兵文件字节不变）
    def test_full_literal_boundary_no_truncation_fallback(self):
        outside = self.root / "elsewhere" / "slides.jsonl"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_bytes(b"SENTINEL-BYTES")
        write_material_md(self.base, "越界整串.md", "../elsewhere/slides.jsonl#锚.png")
        before = snapshot_all(self.root)
        report = pi.run_inventory(self.base)
        item = report["items"]["materials/越界整串.md"]
        self.assertNotIn("source_expression_kind", item)
        bv = [b for b in report["boundary_violations"]
              if b["path"] == "materials/越界整串.md"]
        self.assertEqual(len(bv), 1)
        self.assertEqual(bv[0]["declared_source"],
                         "../elsewhere/slides.jsonl#锚.png")  # 整串入报
        self.assertEqual(self._frag_findings(report), [])
        self.assertEqual(snapshot_all(self.root), before)      # 零写入

    # 容器为跨公司符号链接 → 越界不读（--full-hash 也不产生容器哈希）
    def test_container_symlink_cross_company_boundary_not_read(self):
        co_b = make_base(self.root, "co2")
        target = co_b / "raw" / "same.jsonl"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"COMPANY-B-SECRET")
        link = self.base / "incoming" / "link.jsonl"
        link.symlink_to(target)
        write_material_md(self.base, "跨链.md", "incoming/link.jsonl#锚.png")
        before = snapshot_all(self.root)
        report = pi.run_inventory(self.base, full_hash=True)
        item = report["items"]["materials/跨链.md"]
        self.assertEqual(item["container_accessibility"],
                         "boundary-violation")
        self.assertNotIn("container_sha256_observed", item)  # 不读目标
        self.assertNotIn("source", item)                     # 不给解析路径
        bv = [b for b in report["boundary_violations"]
              if b["path"] == "materials/跨链.md"]
        self.assertEqual(len(bv), 1)
        f = self._finding(report, "materials/跨链.md")
        self.assertEqual(f["kind"], "container-boundary-violation")
        self.assertEqual(snapshot_all(self.root), before)      # 零写入（含 co-b）

    # 双公司同名容器：各观察各的，不跨公司复用
    def test_dual_company_same_container_each_own(self):
        co_b = make_base(self.root, "co2")
        for b, data in ((self.base, b"COMPANY-A"), (co_b, b"COMPANY-B")):
            (b / "raw").mkdir(exist_ok=True)
            (b / "raw" / "same.jsonl").write_bytes(data)
            write_material_md(b, "同名.md", "raw/same.jsonl#锚.png")
        ra = pi.run_inventory(self.base, full_hash=True)
        rb = pi.run_inventory(co_b, full_hash=True)
        for rep, data in ((ra, b"COMPANY-A"), (rb, b"COMPANY-B")):
            item = rep["items"]["materials/同名.md"]
            self.assertEqual(item["container_accessibility"], "accessible")
            self.assertEqual(item["container_sha256_observed"], sha(data))
            self.assertEqual(self._finding(rep, "materials/同名.md")["kind"],
                             "anchor-not-verified")

    # --full-hash：容器观察命名不冒充转换哈希；默认不读容器正文
    def test_full_hash_container_observation_fields(self):
        container = self.base / "raw" / "_extracted" / "slides.jsonl"
        container.parent.mkdir(parents=True)
        container.write_bytes(b"JSONL-BYTES")
        write_material_md(self.base, "哈希.md", FRAG_CERT)
        default = pi.run_inventory(self.base)
        self.assertNotIn("container_sha256_observed",
                         default["items"]["materials/哈希.md"])
        full = pi.run_inventory(self.base, full_hash=True)
        item = full["items"]["materials/哈希.md"]
        self.assertEqual(item["container_sha256_observed"], sha(b"JSONL-BYTES"))
        self.assertTrue(item["container_observed_at"])
        self.assertEqual(item["hash_check"], "unknown-scope")
        for key in item:                                  # 不写 source_sha256*
            self.assertFalse(key.startswith("source_sha256"), key)

    # --full-hash 容器读取失败：明确列错误，不冒充观察成功
    @unittest.skipIf(os.geteuid() == 0, "root 无视权限位，chmod 000 不生效")
    def test_full_hash_container_read_failure_listed(self):
        container = self.base / "raw" / "slides.jsonl"
        container.write_bytes(b"SECRET-CONTAINER")
        write_material_md(self.base, "读失败.md", "raw/slides.jsonl#锚.png")
        os.chmod(container, 0o000)
        try:
            report = pi.run_inventory(self.base, full_hash=True)
            rep = pi.run_inventory(self.base, full_hash=True,
                                   repair_candidates=True)
        finally:
            os.chmod(container, 0o644)
        item = report["items"]["materials/读失败.md"]
        # stat 成功 + read EACCES：stat 存在与读取失败分开表达，
        # 状态/诊断/repair 一致为 container-check-failed，不假装观察成功
        self.assertEqual(item["container_accessibility"], "accessible")
        self.assertEqual(item["hash_check"], "not-applicable")
        self.assertEqual(item.get("container_hash_check"), "not-completed")
        self.assertIn("EACCES", item.get("container_hash_error", ""))
        self.assertNotIn("container_sha256_observed", item)
        self.assertNotIn("container_observed_at", item)
        self.assertEqual(item["anchor_verification"], "not-performed")
        unver = [u for u in report["unverifiable_sources"]
                 if u["path"] == "materials/读失败.md"]
        self.assertEqual(len(unver), 1)
        self.assertIn("EACCES", unver[0]["reason"])
        self.assertEqual(self._finding(report, "materials/读失败.md")["kind"],
                         "container-check-failed")
        suspects = {s["path"]: s for s in rep["wrong_source_suspects"]}
        self.assertEqual(suspects["materials/读失败.md"]["verifiability"],
                         "container-check-failed")

    # 仅锚点未核验发现 → rc3；scan.complete 不得解读为锚点已核验
    def test_anchor_only_finding_drives_rc3(self):
        container = self.base / "raw" / "_extracted" / "slides.jsonl"
        container.parent.mkdir(parents=True)
        container.write_bytes(b"C")
        write_material_md(self.base, "唯一.md", FRAG_CERT)
        before = snapshot_all(self.root)
        r = run_cli(self.base)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertEqual(snapshot_all(self.root), before)      # 零写入
        report = json.loads(r.stdout)
        for kind, entries in report["gaps"].items():
            self.assertEqual(entries, [], kind)            # 无任何缺口
        self.assertEqual(report["boundary_violations"], [])
        self.assertEqual(report["unverifiable_sources"], [])
        self.assertEqual(len(self._frag_findings(report)), 1)
        self.assertTrue(report["scan"]["complete"])        # 本地枚举完整
        self.assertEqual(self._frag_findings(report)[0]["kind"],
                         "anchor-not-verified")

    # 报告稳定排序：按材料 path、kind、容器、fragment
    def test_findings_sorted_stably(self):
        names = ["m2", "m0", "m1"]
        for n in names:
            (self.base / "raw" / f"{n}.jsonl").write_bytes(b"X")
            write_material_md(self.base, f"{n}.md", f"raw/{n}.jsonl#锚{n}.png")
        report = pi.run_inventory(self.base)
        findings = self._frag_findings(report)
        self.assertEqual([f["path"] for f in findings],
                         ["materials/m0.md", "materials/m1.md",
                          "materials/m2.md"])
        keys = [(f["path"], f.get("kind", ""), f.get("source_container", ""),
                 f.get("source_fragment", "")) for f in findings]
        self.assertEqual(keys, sorted(keys))

    # repair 模式：fragment-not-verified / 容器错误分支，不落回填候选与无需修复
    def test_repair_mode_fragment_diagnostics(self):
        # 可访问 / 缺失 / 越界(symlink) / stat失败(自环)
        (self.base / "raw" / "ok.jsonl").write_bytes(b"OK")
        link = self.base / "incoming" / "link.jsonl"
        outside = self.root / "elsewhere" / "x.jsonl"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_bytes(b"OUT")
        link.symlink_to(outside)
        loop = self.base / "incoming" / "loop.jsonl"
        loop.symlink_to("loop.jsonl")
        write_material_md(self.base, "a可访问.md", "raw/ok.jsonl#锚.png")
        write_material_md(self.base, "b缺失.md", "raw/none.jsonl#锚.png")
        write_material_md(self.base, "c越界.md", "incoming/link.jsonl#锚.png")
        write_material_md(self.base, "d失败.md", "incoming/loop.jsonl#锚.png")
        before = snapshot_all(self.root)
        report = pi.run_inventory(self.base, repair_candidates=True)
        suspects = {s["path"]: s for s in report["wrong_source_suspects"]}
        s = suspects["materials/a可访问.md"]
        self.assertEqual(s["verifiability"], "fragment-not-verified")
        self.assertNotEqual(s["verifiability"], "resolvable-in-base")
        self.assertIn("人工", s["suggestion"])
        self.assertEqual(suspects["materials/b缺失.md"]["verifiability"],
                         "container-missing")
        self.assertEqual(suspects["materials/c越界.md"]["verifiability"],
                         "boundary-violation")
        self.assertEqual(suspects["materials/d失败.md"]["verifiability"],
                         "container-check-failed")
        for s in suspects.values():
            self.assertNotIn("无需修复", json.dumps(s, ensure_ascii=False))
            self.assertNotIn("reconvert", json.dumps(s, ensure_ascii=False))
        rep_paths = [x["path"] for x in report["repair_candidates"]]
        for mrel in ("materials/a可访问.md", "materials/b缺失.md",
                     "materials/c越界.md", "materials/d失败.md"):
            self.assertNotIn(mrel, rep_paths)             # 不进回填候选
        self.assertEqual(snapshot_all(self.root), before)      # 零写入

    # 旧行为与零业务写入保留：普通本地/none/缺来源/raw网页/materials片段同跑
    def test_mixed_legacy_and_fragment_in_one_run(self):
        (self.base / "incoming" / "orig.docx").write_bytes(b"O")
        write_raw_md(self.base, "doc.md", "incoming/orig.docx", sha(b"O"))
        head = f"<!--\n来源 URL: {WEB_URL}\n抓取时间: 2026-11-07\n-->\n"
        write_raw_md_head(self.base, "web.md", head)
        write_material_md(self.base, "authored.md", "none")
        write_material_md(self.base, "nosrc.md", None)
        (self.base / "raw" / "slides.jsonl").write_bytes(b"J")
        write_material_md(self.base, "frag.md", "raw/slides.jsonl#锚.png")
        before = snapshot_all(self.root)
        r = run_cli(self.base, "--repair-candidates")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(snapshot_all(self.root), before)      # 零写入
        report = json.loads(r.stdout)
        self.assertEqual(report["items"]["raw/doc.md"]["hash_check"], "match")
        self.assertEqual(report["items"]["raw/web.md"]["source_kind"],
                         "external-url")
        self.assertEqual(report["items"]["materials/authored.md"]
                         ["source_nature"], "none")
        self.assertEqual(report["items"]["materials/nosrc.md"]
                         ["source_nature"], "none")
        frag = report["items"]["materials/frag.md"]
        self.assertEqual(frag["source_nature"], "declared")
        self.assertEqual(frag["source_expression_kind"],
                         "local-file-fragment")
        self.assertEqual(len(self._frag_findings(report)), 1)


class MaterialFragmentGuardedResolveFixTest(unittest.TestCase):
    """有界修复回归（2026-11-14 第二批）：
    1) materials 完整字面 source 在 resolve 抛 RuntimeError（pathlib 将 ELOOP
       自环包成 RuntimeError，非 OSError）时不得崩溃：按观察失败上报
       （附 ELOOP errno 证据），不回退拆分、不冒充缺失，其余条目继续；
    2) --full-hash+repair 下容器字节读取失败（任意 OSError，不限于 EACCES）：
       实际读取失败与 stat 存在分开表达，状态/诊断/repair 一致为
       container-check-failed，hash_check 明确未完成，不产生容器哈希，
       不抹去 anchor_verification=not-performed。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _gaps_for(self, report: dict, rel: str) -> dict:
        return {k: [g for g in v if g["path"] == rel]
                for k, v in report["gaps"].items()}

    def _finding(self, report: dict, mrel: str) -> dict:
        f = [x for x in report["material_source_fragment_findings"]
             if x["path"] == mrel]
        self.assertEqual(len(f), 1, mrel)
        return f[0]

    # 修复1：片段形态与普通完整路径的自环 symlink → run_inventory 不崩溃，
    # 观察失败（ELOOP 证据），不回退，不误报缺失；正常材料继续处理
    def test_full_literal_eloop_selfloop_no_crash(self):
        (self.base / "raw" / "a.jsonl").write_bytes(b"A-CONTAINER")
        loop_frag = self.base / "raw" / "a.jsonl#image.png"
        loop_frag.symlink_to("a.jsonl#image.png")          # 自环
        loop_plain = self.base / "raw" / "loopplain.bin"
        loop_plain.symlink_to("loopplain.bin")             # 普通完整路径自环
        write_material_md(self.base, "片段环.md", "raw/a.jsonl#image.png")
        write_material_md(self.base, "普通环.md", "raw/loopplain.bin")
        write_material_md(self.base, "正常.md", "raw/a.jsonl")
        before = snapshot_all(self.root)
        report = pi.run_inventory(self.base)               # 不得抛 RuntimeError
        for mrel in ("materials/片段环.md", "materials/普通环.md"):
            item = report["items"][mrel]
            self.assertEqual(item["source_nature"], "declared", mrel)
            self.assertEqual(item["hash_check"], "not-applicable", mrel)
            self.assertNotIn("source_expression_kind", item, mrel)   # 不回退
            self.assertNotIn("source_container", item, mrel)
            unver = [u for u in report["unverifiable_sources"]
                     if u["path"] == mrel]
            self.assertEqual(len(unver), 1, mrel)
            self.assertIn("ELOOP", unver[0]["reason"], mrel)         # errno 证据
            self.assertEqual(
                self._gaps_for(report, mrel)["missing_original"], [],
                mrel)                                                # 不冒充缺失
            self.assertEqual(
                [f for f in report["material_source_fragment_findings"]
                 if f["path"] == mrel], [], mrel)
        ok = report["items"]["materials/正常.md"]          # 其余条目继续
        self.assertEqual(ok["source"], "raw/a.jsonl")
        self.assertEqual(ok["source_accessibility"], "accessible")
        self.assertEqual(snapshot_all(self.root), before)  # 零写入

    # 修复2：patch Path.read_bytes 注入 EACCES 与 EIO（任意 OSError）——
    # stat 存在与读取失败分开表达，三处（状态/诊断/repair）一致
    def test_full_hash_container_read_oserror_check_failed(self):
        for name in ("a.jsonl", "b.jsonl"):
            (self.base / "raw" / name).write_bytes(f"{name}-BYTES".encode())
        write_material_md(self.base, "甲.md", "raw/a.jsonl#锚.png")
        write_material_md(self.base, "乙.md", "raw/b.jsonl#锚.png")
        before = snapshot_all(self.root)
        orig_read_bytes = Path.read_bytes

        def fake_read_bytes(self):
            if self.name == "a.jsonl":
                raise PermissionError(errno.EACCES, "Permission denied")
            if self.name == "b.jsonl":
                raise OSError(errno.EIO, "Input/output error")
            return orig_read_bytes(self)

        Path.read_bytes = fake_read_bytes
        try:
            report = pi.run_inventory(self.base, full_hash=True,
                                      repair_candidates=True)
        finally:
            Path.read_bytes = orig_read_bytes
        for mrel, ename in (("materials/甲.md", "EACCES"),
                            ("materials/乙.md", "EIO")):
            item = report["items"][mrel]
            # stat 成功（存在）与读取失败分开表达；不假装观察成功
            self.assertEqual(item["container_accessibility"], "accessible",
                             mrel)
            self.assertEqual(item["hash_check"], "not-applicable", mrel)
            self.assertEqual(item.get("container_hash_check"), "not-completed",
                             mrel)
            self.assertIn(ename, item.get("container_hash_error", ""), mrel)
            self.assertNotIn("container_sha256_observed", item, mrel)
            self.assertNotIn("container_observed_at", item, mrel)
            self.assertEqual(item["anchor_verification"], "not-performed",
                             mrel)
            unver = [u for u in report["unverifiable_sources"]
                     if u["path"] == mrel]
            self.assertEqual(len(unver), 1, mrel)
            self.assertIn(ename, unver[0]["reason"], mrel)
            self.assertEqual(self._finding(report, mrel)["kind"],
                             "container-check-failed", mrel)
            suspects = {s["path"]: s for s in report["wrong_source_suspects"]}
            self.assertEqual(suspects[mrel]["verifiability"],
                             "container-check-failed", mrel)
        self.assertEqual(snapshot_all(self.root), before)  # 零写入


class AuthoredDeclarationTest(unittest.TestCase):
    """materials source: authored: 前缀声明（原创内容，not-applicable 语义）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_material(self, rel: str, source_line: str,
                        body: str = "正文\n") -> Path:
        p = self.base / "materials" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\nsource: {source_line}\n---\n{body}",
                     encoding="utf-8")
        return p

    # 1. authored 前缀：分维映射 + 退出 gaps
    def test_authored_prefix_not_in_gaps(self):
        self._write_material("a.md", "authored: 手写原创内容")
        report = pi.run_inventory(self.base)
        item = report["items"]["materials/a.md"]
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["link_state"], "not-applicable")
        self.assertEqual(item["accessibility"], "not-applicable")
        self.assertEqual(item["hash_check"], "not-applicable")
        for gap in report["gaps"].values():
            self.assertEqual([g for g in gap if g["path"] == "materials/a.md"],
                             [])
        self.assertEqual(report["authored_declarations"], [{
            "path": "materials/a.md",
            "source_verbatim": "authored: 手写原创内容",
            "line": 2,
        }])

    # 2. authored 声明目标不存在也不计 missing（无本地原件概念）
    def test_authored_not_counted_missing(self):
        self._write_material("b.md", "authored:whatever")
        report = pi.run_inventory(self.base)
        self.assertEqual(report["gaps"]["missing_original"], [])
        self.assertEqual(report["gaps"]["missing_source"], [])

    # 3. 清单纳入 rc=3：仅 authored 声明即「有发现」
    def test_authored_rc3_and_listing(self):
        self._write_material("c.md", "authored: 原创")
        r = run_cli(self.base)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(len(payload["authored_declarations"]), 1)
        self.assertTrue(pi.has_findings(payload))

    # 4. 无前缀相似文本不误判
    def test_similar_text_not_authored(self):
        # 4a. 大写/非精确前缀（Authoring:）→ 按普通声明处理（missing_original）
        self._write_material("d1.md", '"Authoring: not authored"')
        # 4b. 正文出现 authored: 文本、frontmatter source 正常 → 不认
        self._write_material("d2.md", "authored-in-body-check",
                             body="source: authored: 正文里出现的\n")
        report = pi.run_inventory(self.base)
        self.assertEqual(report["authored_declarations"], [])
        self.assertEqual(
            [g["path"] for g in report["gaps"]["missing_original"]],
            ["materials/d1.md", "materials/d2.md"])
        self.assertEqual(
            report["items"]["materials/d1.md"]["source_nature"], "declared")
        self.assertEqual(
            report["items"]["materials/d2.md"]["source_nature"], "declared")

    # 5. authored 与 source:none 并存（none 行为不变，均不进 gaps）
    def test_authored_coexists_with_source_none(self):
        self._write_material("e1.md", "authored: x")
        (self.base / "materials" / "e2.md").write_text(
            '---\nsource: "none"\n---\n正文\n', encoding="utf-8")
        report = pi.run_inventory(self.base)
        none_item = report["items"]["materials/e2.md"]
        self.assertEqual(none_item["source_nature"], "none")
        self.assertEqual(none_item["hash_check"], "no-declared-hash")
        self.assertEqual(len(report["authored_declarations"]), 1)
        for gap in report["gaps"].values():
            self.assertEqual(gap, [])

    # 6. --repair-candidates：authored 不产生候选/嫌疑
    def test_authored_no_repair_candidates(self):
        self._write_material("f.md", "authored: x")
        report = pi.run_inventory(self.base, repair_candidates=True)
        self.assertEqual(report.get("repair_candidates"), [])
        self.assertEqual(report.get("wrong_source_suspects"), [])
        self.assertEqual(report["authored_declarations"][0]["path"],
                         "materials/f.md")


if __name__ == "__main__":
    unittest.main()


class RawDeclaredNoneTest(unittest.TestCase):
    """raw 分支 declared source:"none" 与 materials 分支同语义：非缺口。

    对齐修复：raw-md 注释形态 `<!-- source: none -->` 声明 none 时，
    退出 missing_original/missing_source gaps 与 repair 候选；
    accessibility/hash_check 维持 raw 分支现状映射（missing/not-applicable）。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _gaps_for(self, report: dict, rel: str) -> dict:
        return {k: [g for g in v if g["path"] == rel]
                for k, v in report["gaps"].items()}

    # 1. raw-md 注释形态 none（含 frontmatter 同值，与实证
    #    raw/prd-lnkcard/00-owner-decisions.md 同构）退出 missing_original
    def test_raw_inline_none_exits_missing_original(self):
        head = ('---\nsource: none\n---\n'
                '<!-- source: none -->\n')
        write_raw_md_head(self.base, "owner.md", head)
        before = snapshot(self.base)
        report = pi.run_inventory(self.base, repair_candidates=True)
        item = report["items"]["raw/owner.md"]
        self.assertEqual(item["source_nature"], "none")
        self.assertEqual(item["link_state"], "unknown-unavailable")
        self.assertEqual(item["declared_source"], "none")
        self.assertEqual(item["note"], 'source: "none" 为 authored 标记，非缺口')
        # accessibility/hash_check 维持 raw 分支现状映射
        self.assertEqual(item["accessibility"], "missing")
        self.assertEqual(item["hash_check"], "not-applicable")
        g = self._gaps_for(report, "raw/owner.md")
        self.assertEqual(g["missing_original"], [])
        self.assertEqual(g["missing_source"], [])
        # 退出 repair 候选
        self.assertNotIn("raw/owner.md",
                         [r["path"] for r in report["repair_candidates"]])
        self.assertEqual(snapshot(self.base), before)  # 零写入

    # 2. raw-md frontmatter-only 形态：raw 解析口径只认注释载体，不读
    #    frontmatter——现状如实断言（不新增解析），none 声明仍计 missing_source
    def test_raw_frontmatter_only_none_parsed_via_fallback(self):
        # B3 工具闭环后：注释载体无命中时回退解析 frontmatter source，
        # none 沿用既有 none 语义（不再是 missing_source）
        write_raw_md_head(self.base, "fm.md", '---\nsource: none\n---\n')
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/fm.md"]
        self.assertEqual(item["declared_source"], "none")
        self.assertEqual(item["declared_via"], "frontmatter")
        self.assertEqual(item["source_nature"], "none")
        g = self._gaps_for(report, "raw/fm.md")
        self.assertEqual(g["missing_source"], [])
        self.assertEqual(g["missing_original"], [])

    # 3. materials 分支 none 行为回归不变（同语义对照）
    def test_materials_none_regression_unchanged(self):
        (self.base / "materials" / "m.md").write_text(
            '---\nsource: "none"\n---\n正文\n', encoding="utf-8")
        report = pi.run_inventory(self.base, repair_candidates=True)
        item = report["items"]["materials/m.md"]
        self.assertEqual(item["source_nature"], "none")
        self.assertEqual(item["hash_check"], "no-declared-hash")
        self.assertEqual(item["note"], 'source: "none" 为 authored 标记，非缺口')
        g = self._gaps_for(report, "materials/m.md")
        self.assertEqual(g["missing_source"], [])
        self.assertEqual(g["missing_original"], [])
        self.assertNotIn("materials/m.md",
                         [r["path"] for r in report["repair_candidates"]])

    # 4. rc 影响：raw 注释形态 none 单独存在时不再触发 rc=3（修复前计
    #    missing_original → rc=3；修复后干净基座 rc=0）
    def test_raw_none_rc_zero(self):
        write_raw_md_head(self.base, "solo.md", "<!-- source: none -->\n")
        before = snapshot(self.base)
        r = run_cli(self.base)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(snapshot(self.base), before)  # 零写入


class RawFrontmatterFallbackTest(unittest.TestCase):
    """raw 投影声明解析 frontmatter 回退（missing_source 轮 B3 工具闭环）。

    语义：注释载体（行内/块 source/source_path）命中优先、零变化；
    仅当注释载体无任何命中时回退读 frontmatter source 字段，
    值进入与注释值完全相同的处理链（declared_via='frontmatter'）。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_raw(self, rel: str, frontmatter_source: str | None,
                   head_comments: str = "", body: str = "正文\n") -> Path:
        p = self.base / "raw" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        fm = f"---\nsource: {frontmatter_source}\n---\n" \
            if frontmatter_source is not None else ""
        p.write_text(fm + head_comments + "\n" + body, encoding="utf-8")
        return p

    # ① raw 无注释、有 frontmatter source → declared_source 正确、
    #    declared_via=frontmatter、退出 missing_source
    def test_frontmatter_source_exits_missing_source(self):
        orig = self.base / "incoming" / "原始 文件.docx"
        orig.write_bytes(b"ORIGINAL-BYTES")
        self._write_raw("fm.md", "incoming/原始 文件.docx")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/fm.md"]
        self.assertEqual(item["declared_source"], "incoming/原始 文件.docx")
        self.assertEqual(item["declared_via"], "frontmatter")
        self.assertEqual(item["source_nature"], "declared")
        self.assertEqual(item["source"], "incoming/原始 文件.docx")
        self.assertEqual(item["hash_check"], "no-declared-hash")
        self.assertEqual(
            [g for g in report["gaps"]["missing_source"]
             if g["path"] == "raw/fm.md"], [])
        # 哈希链同样适用：frontmatter + 注释 sha 命中 → match
        orig2 = self.base / "incoming" / "y.docx"
        orig2.write_bytes(b"Y")
        p = self.base / "raw" / "fm2.md"
        p.write_text(f"---\nsource: incoming/y.docx\n---\n"
                     f"<!-- source_sha256: {sha(b'Y')} -->\n正文\n",
                     encoding="utf-8")
        report2 = pi.run_inventory(self.base)
        self.assertEqual(report2["items"]["raw/fm2.md"]["hash_check"],
                         "match")

    # ② 注释 + frontmatter 并存 → 注释优先，现状零变化
    def test_comment_takes_priority_over_frontmatter(self):
        orig = self.base / "incoming" / "c.docx"
        orig.write_bytes(b"C")
        self._write_raw(
            "both.md", "incoming/不存在的.docx",
            head_comments="<!-- source: incoming/c.docx -->\n")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/both.md"]
        self.assertEqual(item["declared_source"], "incoming/c.docx")
        self.assertEqual(item["declared_via"], "source")
        self.assertEqual(item["source"], "incoming/c.docx")
        # frontmatter 值不被解析（否则会 missing_original）
        self.assertEqual(
            [g for g in report["gaps"]["missing_original"]
             if g["path"] == "raw/both.md"], [])

    # ③ frontmatter source: none → 沿用既有 none 语义退出
    def test_frontmatter_none_uses_existing_none_semantics(self):
        self._write_raw("none.md", "none")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/none.md"]
        self.assertEqual(item["source_nature"], "none")
        self.assertEqual(item["declared_source"], "none")
        self.assertEqual(item["declared_via"], "frontmatter")
        self.assertEqual(item["note"], 'source: "none" 为 authored 标记，非缺口')
        self.assertEqual(
            [g for g in report["gaps"]["missing_source"]
             if g["path"] == "raw/none.md"], [])
        self.assertEqual(
            [g for g in report["gaps"]["missing_original"]
             if g["path"] == "raw/none.md"], [])

    # ④ frontmatter authored: 前缀 → raw 分支无 authored 专用语义，
    #    如实断言现状：按本地声明值走解析链（解析失败/不存在 →
    #    missing_original），authored_declarations 不计数（仅 materials
    #    分支计入）。不强行改，与 materials 差异在此标注。
    def test_frontmatter_authored_prefix_raw_current_behavior(self):
        self._write_raw("authored.md", "authored: 手写原创内容")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/authored.md"]
        self.assertEqual(item["declared_via"], "frontmatter")
        self.assertEqual(item["source_nature"], "declared")
        # 现状：值被当本地路径解析，目标不存在 → missing_original
        self.assertEqual(
            [g for g in report["gaps"]["missing_original"]
             if g["path"] == "raw/authored.md"],
            [{"path": "raw/authored.md",
              "declared_source": "authored: 手写原创内容"}])
        self.assertEqual(
            [a for a in report["authored_declarations"]
             if a["path"] == "raw/authored.md"], [])

    # ⑤ 注释声明回归零变化：仅注释（无 frontmatter）行为与历史一致
    def test_comment_only_regression_unchanged(self):
        orig = self.base / "incoming" / "r.docx"
        orig.write_bytes(b"R")
        write_raw_md(self.base, "reg.md", "incoming/r.docx", None)
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/reg.md"]
        self.assertEqual(item["declared_via"], "source")
        self.assertEqual(item["declared_source"], "incoming/r.docx")
        self.assertEqual(
            [g for g in report["gaps"]["missing_source"]
             if g["path"] == "raw/reg.md"], [])

    # ⑥（补充）frontmatter source 为 URL → 走外部声明通道，
    #    不进本地解析、不算 missing_source
    def test_frontmatter_url_goes_external_channel(self):
        self._write_raw("url.md", "https://example.com/page")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/url.md"]
        self.assertEqual(item["source_kind"], "external-url")
        self.assertEqual(item["declared_via"], "frontmatter")
        self.assertEqual(item["external_urls"], ["https://example.com/page"])
        self.assertEqual(
            [g for g in report["gaps"]["missing_source"]
             if g["path"] == "raw/url.md"], [])


class RawFrontmatterHashFallbackTest(unittest.TestCase):
    """raw 投影声明哈希 frontmatter 回退（missing_hash 轮 B3 工具闭环）。

    语义：注释载体（行内/块 sha）命中优先、零变化；仅当注释载体无任何
    source_sha256/source_sha256_at_backfill 命中时，回退读 frontmatter 的
    source_sha256_at_backfill → 作为 declared hash 进入既有哈希比对链
    （hash_via='frontmatter'，引号剥离同 source 回退）。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_raw(self, rel: str, frontmatter: str, head_comments: str = "",
                   body: str = "正文\n") -> Path:
        p = self.base / "raw" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\n{frontmatter}---\n" + head_comments + "\n" + body,
                     encoding="utf-8")
        return p

    # ① frontmatter-only 哈希被采用，hash_check 与当前文件比对
    def test_frontmatter_only_hash_adopted_and_compared(self):
        orig = self.base / "incoming" / "h.docx"
        orig.write_bytes(b"H")
        self._write_raw(
            "fh.md",
            f"source: incoming/h.docx\n"
            f"source_sha256_at_backfill: {sha(b'H')}\n")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/fh.md"]
        self.assertEqual(item["hash_via"], "frontmatter")
        self.assertEqual(item["hash_check"], "match")
        self.assertEqual(item["source_sha256_actual"], sha(b"H"))
        self.assertEqual(
            [g for g in report["gaps"]["missing_hash"]
             if g["path"] == "raw/fh.md"], [])
        # 引号剥离口径（YAML 引号值）同样命中
        self._write_raw(
            "fhq.md",
            f"source: incoming/h.docx\n"
            f"source_sha256_at_backfill: \"{sha(b'H')}\"\n")
        report2 = pi.run_inventory(self.base)
        self.assertEqual(report2["items"]["raw/fhq.md"]["hash_check"], "match")
        # 哈希不匹配 → 既有 mismatch 链路
        self._write_raw(
            "fhm.md",
            "source: incoming/h.docx\nsource_sha256_at_backfill: "
            + "0" * 64 + "\n")
        report3 = pi.run_inventory(self.base)
        self.assertEqual(report3["items"]["raw/fhm.md"]["hash_check"],
                         "mismatch")

    # ② 注释哈希 + frontmatter 哈希并存 → 注释优先，现状零变化
    def test_comment_hash_takes_priority_over_frontmatter(self):
        orig = self.base / "incoming" / "c2.docx"
        orig.write_bytes(b"C2")
        self._write_raw(
            "both-h.md", f"source: incoming/c2.docx\n"
                         f"source_sha256_at_backfill: {'0' * 64}\n",
            head_comments=f"<!-- source_sha256: {sha(b'C2')} -->\n")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/both-h.md"]
        self.assertNotIn("hash_via", item)  # frontmatter 哈希未被采用
        self.assertEqual(item["hash_check"], "match")  # 注释哈希胜出
        self.assertEqual(
            [g for g in report["gaps"]["missing_hash"]
             if g["path"] == "raw/both-h.md"], [])

    # ③ frontmatter source + frontmatter 哈希 → 同时退出 missing_source
    #    与 missing_hash（B3 raw 投影双回填形态）
    def test_frontmatter_source_and_hash_exit_both_gaps(self):
        orig = self.base / "incoming" / "b3.docx"
        orig.write_bytes(b"B3")
        self._write_raw(
            "b3.md",
            f"source: incoming/b3.docx\n"
            f"source_sha256_at_backfill: {sha(b'B3')}\n")
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/b3.md"]
        self.assertEqual(item["declared_via"], "frontmatter")
        self.assertEqual(item["hash_via"], "frontmatter")
        self.assertEqual(item["hash_check"], "match")
        self.assertEqual(
            [g for g in report["gaps"]["missing_source"]
             if g["path"] == "raw/b3.md"], [])
        self.assertEqual(
            [g for g in report["gaps"]["missing_hash"]
             if g["path"] == "raw/b3.md"], [])

    # ④ 注释哈希形态回归零变化：仅注释哈希（无 frontmatter）行为一致，
    #    frontmatter 哈希缺位时不制造新语义
    def test_comment_hash_only_regression_unchanged(self):
        orig = self.base / "incoming" / "r2.docx"
        orig.write_bytes(b"R2")
        write_raw_md(self.base, "reg2.md", "incoming/r2.docx", sha(b"R2"))
        report = pi.run_inventory(self.base)
        item = report["items"]["raw/reg2.md"]
        self.assertNotIn("hash_via", item)
        self.assertEqual(item["hash_check"], "match")
        # 无任何哈希载体 → 既有 no-declared-hash / missing_hash 不变
        write_raw_md(self.base, "nohash.md", "incoming/r2.docx", None)
        report2 = pi.run_inventory(self.base)
        item2 = report2["items"]["raw/nohash.md"]
        self.assertNotIn("hash_via", item2)
        self.assertEqual(item2["hash_check"], "no-declared-hash")
        self.assertEqual(
            [g for g in report2["gaps"]["missing_hash"]
             if g["path"] == "raw/nohash.md"],
            [{"path": "raw/nohash.md",
              "declared_source": "incoming/r2.docx"}])


# --- convert_excel v7 manifest：outputs 对象数组（docs 2026-11-17 入库批次实证）---
# v7（fingerprint_format: 1）manifest 的 outputs 为对象数组
# [{path, sha256, bytes, ...}]，artifacts 保持纯字符串数组。旧实现两处对
# artifacts/outputs 的 list 元素直接 str(v)：str(dict) 把整个对象当文件名 →
# stat 必失败 → outputs_missing 假阳性（真实基座 62 条 / 5 个 manifest），
# 且 covered_files 侧对象条目全部丢失。真实锚点只读登记于
# tests/fixtures_registry.json（lanlnk-v7-outputs-manifest），manifest 正文
# 不复制进本仓；核心测试全部合成基座。


def write_v7_manifest(base: Path, records: list[dict],
                      rel_dir: str = "sub") -> Path:
    sub = base / "raw" / rel_dir
    sub.mkdir(parents=True, exist_ok=True)
    mp = sub / "_manifest.json"
    mp.write_text(json.dumps(records, ensure_ascii=False, indent=2),
                  encoding="utf-8")
    return mp


class ManifestOutputsObjectArrayTest(unittest.TestCase):
    """v7 outputs 对象数组：取 v["path"]、缺 path 记 manifest_invalid、dict 形态兼容。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = make_base(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def _v7_record(self, **over) -> dict:
        rec = {
            "source_path": "incoming/表.xlsx",
            "source_sha256": sha(b"XLSX"),
            "source_size": 4,
            "extractor": "convert_excel.py v7",
            "extractor_version": 7,
            "fingerprint_format": 1,
            "artifacts": ["csv/a.csv"],
            "outputs": [
                {"path": "csv/b.csv", "sha256": sha(b"B"), "bytes": 1},
                {"path": "csv/c.csv.notes.md", "sha256": sha(b"C"), "bytes": 1},
            ],
        }
        rec.update(over)
        return rec

    def _materialize(self, rel_paths: list[str]) -> None:
        """把 manifest 列出的文件以占位内容物化到 raw/sub/ 下。"""
        for rel in rel_paths:
            p = self.base / "raw" / "sub" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("placeholder\n", encoding="utf-8")

    # 1. outputs 对象数组 → 取 v["path"]，不再把 str(dict) 整体当文件名
    def test_v7_outputs_object_array_no_false_missing(self):
        (self.base / "incoming" / "表.xlsx").write_bytes(b"XLSX")
        write_v7_manifest(self.base, [self._v7_record()])
        self._materialize(["csv/a.csv", "csv/b.csv", "csv/c.csv.notes.md"])
        report = pi.run_inventory(self.base)
        # 全部列出的文件真实存在 → outputs_missing 必须为空（旧实现假阳性）
        self.assertEqual(report["gaps"]["outputs_missing"], [])
        # artifacts（字符串）与 outputs（对象）列出的文件都计入 manifest 覆盖
        for rel in ("csv/a.csv", "csv/b.csv", "csv/c.csv.notes.md"):
            item = report["items"][f"raw/sub/{rel}"]
            self.assertEqual(item.get("manifest_coverage"),
                             ["raw/sub/_manifest.json"])
            self.assertNotIn(f"raw/sub/{rel}", [g["path"] for g in
                           report["gaps"]["no_manifest_coverage"]])

    # 2. outputs 对象缺 path 键 → 记入 manifest_invalid（不静默丢弃），
    #    同 record 其余合法条目不受牵连
    def test_v7_outputs_dict_missing_path_key_noted_not_dropped(self):
        rec = self._v7_record(outputs=[
            {"sha256": sha(b"X"), "bytes": 9},           # 缺 path 键
            {"path": "csv/b.csv", "sha256": sha(b"B"), "bytes": 1},
        ])
        write_v7_manifest(self.base, [rec])
        self._materialize(["csv/a.csv", "csv/b.csv"])
        report = pi.run_inventory(self.base)
        inv = report["gaps"]["manifest_invalid"]
        self.assertEqual(len(inv), 1)
        self.assertEqual(inv[0]["path"], "raw/sub/_manifest.json")
        self.assertEqual(inv[0]["key"], "outputs")
        self.assertIn("path", inv[0]["reason"])
        # 坏条目本身无路径可查（不当文件名 stat），合法条目照常覆盖
        self.assertEqual(report["gaps"]["outputs_missing"], [])
        self.assertEqual(
            report["items"]["raw/sub/csv/b.csv"].get("manifest_coverage"),
            ["raw/sub/_manifest.json"])

    # 3. 旧 dict 形态 outputs（键=路径）取键，行为不变
    def test_manifest_outputs_dict_shape_keys_still_covered(self):
        rec = self._v7_record(
            artifacts=[],
            outputs={"csv/legacy.csv": {"bytes": 1}})
        write_v7_manifest(self.base, [rec])
        self._materialize(["csv/legacy.csv"])
        report = pi.run_inventory(self.base)
        self.assertEqual(report["gaps"]["outputs_missing"], [])
        self.assertEqual(
            report["items"]["raw/sub/csv/legacy.csv"].get("manifest_coverage"),
            ["raw/sub/_manifest.json"])
