"""端到端合成基座验证（harden-material-import-provenance tasks 5.1/5.2/5.3）。

与既有测试的分工：
- tests/test_company_isolation.py（1.6）：四场景 Python 级 + 单脚本 CLI 级。
- tests/test_conversion_fingerprint.py（2.7/2.8）：状态机与模式×状态矩阵逐格。
- tests/test_golden_fixtures.py：外部金样例回归由 orchestrator 在最终回归跑，
  本文件**不重复**金样例断言（5.3.4 分工）。
- 本文件：跨工具 CLI 端到端 —— 临时目录手工构造微型公司基座
  （config/company.yaml + incoming/ + raw/），走 incoming → convert →
  edit → recheck 完整生命周期，全部 subprocess CLI 级（不 import 被测工具）。

中文/空格/方括号文件名贯穿全部用例。soffice/.xls 分支不在本文件范围
（无 .xls 输入；若引入按 shutil.which("soffice") skipif 并注明）。
每个用例自清理（TemporaryDirectory），不依赖执行顺序。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook
from pptx import Presentation

TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
EXCEL_SCRIPT = SCRIPTS_DIR / "convert_excel.py"
DOC_SCRIPT = SCRIPTS_DIR / "convert_doc.py"
INV_SCRIPT = SCRIPTS_DIR / "provenance_inventory.py"

# convert_doc 端到端依赖 markitdown（skill venv，脚本内部 `uv run markitdown`
# cwd=SKILL_DIR）；本测试文件必须经 `uv run pytest` 在 skill 目录运行。
MARKITDOWN = shutil.which("markitdown") is not None or Path(SKILL_DIR / ".venv").exists()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_base(root: Path, name: str) -> Path:
    base = root / name
    (base / "config").mkdir(parents=True)
    (base / "config" / "company.yaml").write_text(
        f"name: {name}\n", encoding="utf-8")
    (base / "incoming").mkdir()
    (base / "raw").mkdir()
    (base / "materials").mkdir()
    return base


def snapshot(base: Path) -> dict[str, str]:
    """{relpath: sha256} 全基座字节快照（--check 零写入断言用）。"""
    out: dict[str, str] = {}
    for cur, _dirs, files in os.walk(base):
        for f in files:
            p = Path(cur) / f
            out[p.relative_to(base).as_posix()] = sha(p.read_bytes())
    return out


def clean_env(base: Path | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if k not in ("COMPANY_BASE", "LANLNK_BASE")}
    if base is not None:
        env["COMPANY_BASE"] = str(base)
    return env


def run_cli(script: Path, *args: str, base: Path | None = None,
            timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, env=clean_env(base),
        timeout=timeout,
    )


def make_simple_xlsx(path: Path) -> None:
    """单 sheet 简单表（MD 路由）。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "数据"
    ws.append(["指标", "数值"])
    ws.append(["销售额", 100])
    ws.append(["利润", 30])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def make_multi_xlsx(path: Path, sheets: list[str]) -> None:
    """多 sheet 工作簿（CSV 路由：每 sheet 一个 csv）。"""
    wb = Workbook()
    wb.remove(wb.active)
    for name in sheets:
        ws = wb.create_sheet(title=name)
        ws.append([f"{name}指标", "数值"])
        ws.append(["甲", 1])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def make_pptx(path: Path, text: str = "端到端标题") -> None:
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = text
    path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(path)


# ══════════════════════════════════════════════════════════════════
# 5.1 微型基座端到端（incoming → convert → edit → recheck 生命周期）
# ══════════════════════════════════════════════════════════════════


class MicroBaseE2ETest(unittest.TestCase):
    """tasks 5.1：单一微型合成基座走完整溯源生命周期（步骤 1-4 为单一链路）。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = make_base(Path(self._tmp.name), "microco")
        self.incoming = self.base / "incoming"
        self.raw = self.base / "raw"

    def tearDown(self):
        self._tmp.cleanup()

    def xlsx(self, name: str) -> Path:
        return self.incoming / name

    # ── 步骤 1-4：单文件生命周期（转换 → up-to-date → 源变 → 人工编辑保护）──
    def test_excel_lifecycle_convert_check_source_change_edit(self):
        src = self.xlsx("数据 表[2024].xlsx")
        make_simple_xlsx(src)
        out_dir = self.raw / "测试"

        # 1. 首转：断言产物 + manifest 新字段
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir), base=self.base)
        self.assertEqual(r.returncode, 0, r.stderr)
        md = out_dir / "数据 表[2024].md"
        self.assertTrue(md.is_file(), r.stdout)
        manifest = json.loads((out_dir / "_manifest.json").read_text("utf-8"))
        rec = manifest[0]
        for field in ("options", "outputs", "backend", "fingerprint_format"):
            self.assertIn(field, rec, f"manifest 缺新字段 {field}")
        self.assertEqual(rec["fingerprint_format"], 1)
        self.assertIn("sha256", rec["outputs"][0])
        self.assertIn("bytes", rec["outputs"][0])

        # 2. --check → up-to-date + 全基座字节不变
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir),
                    "--check", base=self.base)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("up-to-date", r.stdout)
        snap_before = snapshot(self.base)
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir),
                    "--check", base=self.base)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(snapshot(self.base), snap_before, "--check 发生了写入")

        # 3. 改源单元格 → --check → source-changed、零写入
        from openpyxl import load_workbook
        wb = load_workbook(src)
        wb["数据"]["B2"] = 999
        wb.save(src)
        snap_before = snapshot(self.base)  # 源编辑后取快照，check 不应再动任何字节
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir),
                    "--check", base=self.base)
        self.assertEqual(r.returncode, 3)
        self.assertIn("source-changed", r.stdout)
        self.assertNotIn("up-to-date\n", r.stdout)
        self.assertEqual(snapshot(self.base), snap_before, "check 改写业务文件")

        # 4. 手工编辑输出正文 → --check → output-modified/conflict 不虚报；
        #    默认模式重跑 → 人工修改被保留
        with open(md, "a", encoding="utf-8") as f:
            f.write("| 人工修改 | MARKER-EDIT |\n")
        snap_before = snapshot(self.base)  # 人工编辑后取快照
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir),
                    "--check", base=self.base)
        self.assertEqual(r.returncode, 3)
        # 源已变 + 输出被改 → conflict（若源已恢复则 output-modified）；
        # 两种都不得虚报 up-to-date
        self.assertTrue(
            "output-modified" in r.stdout or "conflict" in r.stdout,
            f"未报告 output-modified/conflict: {r.stdout}")
        self.assertNotIn("全部 up-to-date", r.stdout)
        self.assertEqual(snapshot(self.base), snap_before,
                         "check 阶段不应有任何字节变化（含人工编辑后）")
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir), base=self.base)
        self.assertEqual(r.returncode, 3, "默认模式检出受保护跳过应为发现 rc=3")
        self.assertIn("MARKER-EDIT", md.read_text("utf-8"),
                      "默认重跑静默覆盖了人工修改")

    # ── 步骤 5：多 sheet 转换 → 删 sheet → --check 报 orphan-outputs 不删除 ──
    def test_multi_sheet_orphan_outputs(self):
        src = self.xlsx("multi 表.xlsx")
        make_multi_xlsx(src, ["一", "二", "三"])
        out_dir = self.raw / "multi"
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir), base=self.base)
        self.assertEqual(r.returncode, 0, r.stderr)
        orphan_csv = out_dir / "csv" / "multi 表_二.csv"
        self.assertTrue(orphan_csv.is_file())

        # 删一个 sheet → --check → orphan-outputs 盘点（记录 vs 当前路由预期）
        from openpyxl import load_workbook
        wb = load_workbook(src)
        wb.remove(wb["二"])
        wb.save(src)
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir),
                    "--check", base=self.base)
        self.assertEqual(r.returncode, 3)
        self.assertIn("orphan-outputs", r.stdout)
        self.assertIn("multi 表_二.csv", r.stdout)
        # 被删 sheet 的 csv 仍在磁盘、未被删除
        self.assertTrue(orphan_csv.is_file(), "orphan 输出被自动删除")
        # needs_recheck 仅路径引用（含 orphan 路径）
        self.assertIn(str(orphan_csv), r.stdout)

        # 默认重转后：orphan 文件仍不删除（永不自动删除任何文件）
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir), base=self.base)
        self.assertIn(r.returncode, (0, 3))
        self.assertTrue(orphan_csv.is_file(), "重转后删除了 orphan 文件")
        # 重转后 manifest 已刷新（不再列被删 sheet 的旧 csv），--check 仍须以
        # disk-untracked 口径盘点出磁盘残留（tasks 2.6：不依赖 check 跑在重转前）
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir),
                    "--check", base=self.base)
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("orphan-outputs", r.stdout)
        self.assertIn("multi 表_二.csv", r.stdout)
        self.assertIn("disk-untracked", r.stdout)
        self.assertTrue(orphan_csv.is_file())

    # ── 步骤 6：锁文件批量守卫（skipped、其余产出、rc=0 不崩溃）──
    def test_lock_file_batch_guard(self):
        self.incoming.joinpath("~$锁 文件.xlsx").write_bytes(
            b"\x00\x01\x02 not-a-pk-zip \xff\xfe")
        make_simple_xlsx(self.xlsx("正常 文件.xlsx"))
        out_dir = self.raw / "锁测试"
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir), base=self.base)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("~$锁 文件.xlsx", r.stdout)
        self.assertIn("skipped", r.stdout)
        self.assertTrue((out_dir / "正常 文件.md").is_file())
        manifest = json.loads((out_dir / "_manifest.json").read_text("utf-8"))
        self.assertEqual(len(manifest), 1)
        self.assertIn("正常 文件", manifest[0]["source_path"])


class ConvertDocE2ETest(unittest.TestCase):
    """tasks 5.1 步骤 7：convert_doc 端到端（真实 markitdown，skill venv）。"""

    setUp_base = None

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = make_base(Path(self._tmp.name), "docco")
        self.incoming = self.base / "incoming"
        self.raw = self.base / "raw"

    def tearDown(self):
        self._tmp.cleanup()

    @unittest.skipUnless(MARKITDOWN, "markitdown 依赖 skill venv（uv run pytest）")
    def test_pptx_fingerprint_lifecycle(self):
        src = self.incoming / "产品 介绍.pptx"
        make_pptx(src, text="端到端幻灯片标题")
        out = self.raw / "产品 介绍.pptx.md"

        # 转换：头含 output_body_sha256 + output_digest_scope
        r = run_cli(DOC_SCRIPT, str(src), str(out), base=self.base)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = out.read_text("utf-8")
        self.assertIn("output_body_sha256: ", text)
        self.assertIn("output_digest_scope: post-provenance-header", text)
        self.assertIn("source: incoming/产品 介绍.pptx", text)
        before = sha(out.read_bytes())

        # --check → up-to-date、零写入
        r = run_cli(DOC_SCRIPT, str(src), str(out), "--check", base=self.base)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("up-to-date", r.stdout)
        self.assertEqual(sha(out.read_bytes()), before, "--check 写入了输出")

        # 编辑正文 → output-modified、零写入
        with open(out, "a", encoding="utf-8") as f:
            f.write("人工修改 DOC-MARKER\n")
        modified_bytes = out.read_bytes()
        r = run_cli(DOC_SCRIPT, str(src), str(out), "--check", base=self.base)
        self.assertEqual(r.returncode, 3)
        self.assertIn("output-modified", r.stdout)
        self.assertEqual(out.read_bytes(), modified_bytes, "check 覆盖了人工修改")

    def test_lock_file_single_guard(self):
        lock = self.incoming / "~$产品 介绍.pptx"
        lock.write_bytes(b"\x00\x01notpk")
        r = run_cli(DOC_SCRIPT, str(lock),
                    str(self.raw / "lock.md"), base=self.base)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("skipped", r.stdout + r.stderr)
        self.assertIn("lock", (r.stdout + r.stderr).lower())
        self.assertFalse((self.raw / "lock.md").exists(), "锁文件被转换产出")


class InventoryOnSyntheticBaseTest(unittest.TestCase):
    """tasks 5.1 步骤 8/9：体检默认口径 + 退出码三分可区分 + repair 零写入。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _gap_base(self) -> Path:
        """制造过缺口的基座：raw md 无任何 provenance → missing_source。"""
        base = make_base(self.root, "gapco")
        (base / "raw" / "无溯源 文档.md").write_text("正文\n", encoding="utf-8")
        return base

    def _clean_base(self) -> Path:
        """干净合成基座：只有原件、无 raw 投影 → 无缺口。"""
        base = make_base(self.root, "cleanco")
        make_simple_xlsx(base / "incoming" / "原件 表[2024].xlsx")
        return base

    def test_gap_base_rc3_clean_base_rc0_repair_zero_write(self):
        gap = self._gap_base()
        clean = self._clean_base()

        r = run_cli(INV_SCRIPT, "--base", str(gap))
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        report = json.loads(r.stdout)
        self.assertTrue(any(report["gaps"]["missing_source"]))

        r = run_cli(INV_SCRIPT, "--base", str(clean))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

        # --repair-candidates 前后快照字节不变（仍零写入）
        snap = snapshot(gap)
        r = run_cli(INV_SCRIPT, "--base", str(gap), "--repair-candidates")
        self.assertEqual(r.returncode, 3)
        self.assertEqual(snapshot(gap), snap, "--repair-candidates 发生写入")
        report = json.loads(r.stdout)
        self.assertIn("repair_candidates", report)

    def test_exit_codes_distinguish_findings_vs_failure(self):
        # 干净基座 rc=0（无发现）
        self.assertEqual(
            run_cli(INV_SCRIPT, "--base", str(self._clean_base())).returncode, 0)
        # 有缺口 rc=3（完成且有发现）
        self.assertEqual(
            run_cli(INV_SCRIPT, "--base", str(self._gap_base())).returncode, 3)
        # --base 指向无 config/company.yaml 的目录 rc=1（工具失败，非发现）
        notcompany = self.root / "notacompany"
        notcompany.mkdir()
        r = run_cli(INV_SCRIPT, "--base", str(notcompany))
        self.assertEqual(r.returncode, 1)
        self.assertIn("不是已注册公司", r.stderr)


# ══════════════════════════════════════════════════════════════════
# 5.2 双合成公司基座 CLI 级隔离（1.6 四场景的跨工具 subprocess 复验）
# ══════════════════════════════════════════════════════════════════


class DualCompanyIsolationE2ETest(unittest.TestCase):
    """tasks 5.2：两个独立合成公司基座，四场景全部 subprocess CLI 级。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base_a = make_base(self.root, "companya")
        self.base_b = make_base(self.root, "companyb")

    def tearDown(self):
        self._tmp.cleanup()

    # 1. 同名原件不跨公司匹配
    def test_same_basename_not_matched_across_companies(self):
        (self.base_a / "raw" / "共享 文档.md").write_text("正文\n", encoding="utf-8")
        (self.base_b / "incoming" / "共享 文档.docx").write_bytes(b"B-ORIGINAL")
        r = run_cli(INV_SCRIPT, "--base", str(self.base_a),
                    "--repair-candidates")
        self.assertEqual(r.returncode, 3)
        report = json.loads(r.stdout)
        rep = [x for x in report["repair_candidates"]
               if x["path"] == "raw/共享 文档.md"]
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep[0]["resolution"], "unresolved")
        # 报告 JSON 全文不含 B 基座路径子串
        self.assertNotIn(str(self.base_b), r.stdout)
        self.assertNotIn("companyb", r.stdout)

    # 2. 相同相对路径产物/指纹不复用：A/B 各自转换各自 check，互不污染
    def test_same_relpath_fingerprint_not_reused(self):
        for base, val in ((self.base_a, 100), (self.base_b, 777)):
            make_simple_xlsx(base / "incoming" / "报价 表.xlsx")
            from openpyxl import load_workbook
            wb = load_workbook(base / "incoming" / "报价 表.xlsx")
            wb["数据"]["B2"] = val
            wb.save(base / "incoming" / "报价 表.xlsx")
            r = run_cli(EXCEL_SCRIPT, str(base / "incoming"),
                        str(base / "raw" / "x"), base=base)
            self.assertEqual(r.returncode, 0, r.stderr)
        # A 源变化后：A 报 source-changed（rc 3），B 仍 up-to-date（rc 0）
        src_a = self.base_a / "incoming" / "报价 表.xlsx"
        from openpyxl import load_workbook
        wb = load_workbook(src_a)
        wb["数据"]["B3"] = 12345
        wb.save(src_a)
        r_a = run_cli(EXCEL_SCRIPT, str(self.base_a / "incoming"),
                      str(self.base_a / "raw" / "x"), "--check",
                      base=self.base_a)
        r_b = run_cli(EXCEL_SCRIPT, str(self.base_b / "incoming"),
                      str(self.base_b / "raw" / "x"), "--check",
                      base=self.base_b)
        self.assertEqual(r_a.returncode, 3)
        self.assertIn("source-changed", r_a.stdout)
        self.assertEqual(r_b.returncode, 0, r_b.stdout + r_b.stderr)
        self.assertIn("up-to-date", r_b.stdout)
        # 各自 manifest 的指纹互不相同、A 报告不含 B 路径
        man_a = json.loads((self.base_a / "raw" / "x" / "_manifest.json")
                           .read_text("utf-8"))
        man_b = json.loads((self.base_b / "raw" / "x" / "_manifest.json")
                           .read_text("utf-8"))
        self.assertNotEqual(man_a[0]["source_sha256"], man_b[0]["source_sha256"])
        self.assertNotIn(str(self.base_b), r_a.stdout)

    # 3. unset / 无效 COMPANY_BASE → resolver 报错非零、无 lanlnk 默认路径回退
    def test_unset_or_invalid_company_base(self):
        env = clean_env()  # COMPANY_BASE / LANLNK_BASE 已剔除
        r = subprocess.run([sys.executable, str(INV_SCRIPT)],
                           capture_output=True, text=True, env=env, timeout=120)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(r.returncode, 1)
        self.assertIn("COMPANY_BASE", r.stderr)
        # 无回退到 lanlnk 默认路径（resolver 提示文本中的示例字样不算回退）
        self.assertNotIn("/opt/code/docs/lanlnk", r.stdout + r.stderr)
        # 指向无 config/company.yaml 的绝对路径
        r2 = subprocess.run(
            [sys.executable, str(INV_SCRIPT)],
            capture_output=True, text=True,
            env=dict(env, COMPANY_BASE="/nonexistent"),
            timeout=120)
        self.assertEqual(r2.returncode, 1)
        self.assertIn("不是已注册公司", r2.stderr)
        self.assertNotIn("/opt/code/docs/lanlnk", r2.stdout + r2.stderr)

    # 4. symlink 跨基座声明 → boundary-violation 单列 + hash_check=
    #    not-applicable + B 文件字节未进报告
    def test_symlink_cross_base_boundary_violation(self):
        secret_bytes = b"B-SECRET-CONTENT-CONFIDENTIAL"
        secret = self.base_b / "incoming" / "secret 文档.docx"
        secret.write_bytes(secret_bytes)
        link = self.base_a / "incoming" / "link 文档.docx"
        link.symlink_to(secret)
        (self.base_a / "raw" / "linked.md").write_text(
            "<!-- source: incoming/link 文档.docx -->\n"
            "<!-- source_sha256: " + "0" * 64 + " -->\n\n正文\n",
            encoding="utf-8")
        r = run_cli(INV_SCRIPT, "--base", str(self.base_a))
        self.assertEqual(r.returncode, 3)
        report = json.loads(r.stdout)
        bv = [b for b in report["boundary_violations"]
              if b["path"] == "raw/linked.md"]
        self.assertEqual(len(bv), 1)
        item = report["items"]["raw/linked.md"]
        self.assertEqual(item["hash_check"], "not-applicable")
        # B 文件内容与其哈希均未出现在报告（证明目标未被读取）
        self.assertNotIn(secret_bytes.decode(), r.stdout)
        self.assertNotIn(sha(secret_bytes), r.stdout)


# ══════════════════════════════════════════════════════════════════
# 5.3 向后兼容（旧 manifest / 旧 raw md 头 / 旧 _index.json）
# ══════════════════════════════════════════════════════════════════


class BackwardCompatE2ETest(unittest.TestCase):
    """tasks 5.3：旧代际元数据可读、unknown 不虚报、零写入、不崩溃。

    金样例（fixtures_registry 外部样例）断言由 tests/test_golden_fixtures.py
    承担，orchestrator 最终回归统一执行，本文件不重复（5.3.4 分工）。
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = make_base(Path(self._tmp.name), "legacyco")
        self.incoming = self.base / "incoming"
        self.raw = self.base / "raw"

    def tearDown(self):
        self._tmp.cleanup()

    def test_legacy_manifest_reports_unknown_zero_write(self):
        make_simple_xlsx(self.incoming / "旧 表.xlsx")
        out_dir = self.raw / "旧"
        out_dir.mkdir(parents=True)
        (out_dir / "旧 表.md").write_text(
            "<!--\nsource_path: " + str(self.incoming / "旧 表.xlsx")
            + "\nsource_sha256: " + "a" * 64 + "\nextracted_at: 2024-01-01\n"
            "extractor: convert_excel.py\nextractor_version: 2\n"
            "artifacts: [\"旧 表.md\"]\nfidelity: {text: high}\n-->\n\n# 旧 表\n",
            encoding="utf-8")
        # 旧 manifest：手写无新字段（无 options/outputs/backend/fingerprint_format）
        (out_dir / "_manifest.json").write_text(
            json.dumps([{
                "source_path": str((self.incoming / "旧 表.xlsx").resolve()),
                "source_sha256": "a" * 64,
                "source_size": 1,
                "extracted_at": "2024-01-01T00:00:00",
                "extractor": "convert_excel.py",
                "extractor_version": 2,
                "artifacts": ["旧 表.md"],
                "fidelity": {"text": "high"},
            }], ensure_ascii=False),
            encoding="utf-8")
        snap = snapshot(self.base)
        r = run_cli(EXCEL_SCRIPT, str(self.incoming), str(out_dir),
                    "--check", base=self.base)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("unknown", r.stdout)
        self.assertNotIn("全部 up-to-date", r.stdout)
        self.assertNotIn("ERROR", r.stderr)
        self.assertEqual(snapshot(self.base), snap, "--check 对旧产物发生写入")

    def test_legacy_raw_md_header_reports_unknown_zero_write(self):
        make_pptx(self.incoming / "旧 产品.pptx", text="旧代际标题")
        out = self.raw / "旧 产品.pptx.md"
        # convert_doc v2 格式：无 output_body_sha256 / output_digest_scope 行
        out.write_text(
            "<!-- source: incoming/旧 产品.pptx -->\n"
            "<!-- source_sha256: " + "b" * 64 + " -->\n"
            "<!-- extracted_by: markitdown via convert_doc.py v2 (2024-01-01) -->\n"
            "<!-- fidelity: text=high -->\n\n# 旧 产品\n\n正文\n",
            encoding="utf-8")
        before = out.read_bytes()
        r = run_cli(DOC_SCRIPT, str(self.incoming / "旧 产品.pptx"),
                    str(out), "--check", base=self.base)
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("state=unknown", r.stdout)
        self.assertNotIn("up-to-date", r.stdout)
        self.assertEqual(out.read_bytes(), before, "--check 写入了旧产物")

    def test_legacy_index_json_inferred_link(self):
        # 旧 _index.json：最小合法结构（含 imported_from）
        (self.raw / "_index.json").write_text(
            json.dumps({"旧 文档.md": {"imported_from": "incoming/旧 文档.docx"}},
                       ensure_ascii=False),
            encoding="utf-8")
        (self.raw / "旧 文档.md").write_text("正文\n", encoding="utf-8")
        r = run_cli(INV_SCRIPT, "--base", str(self.base))
        # 不崩溃；inferred 条目正常读取（inferred 本身不算缺口）
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        report = json.loads(r.stdout)
        item = report["items"]["raw/旧 文档.md"]
        self.assertEqual(item["link_state"], "inferred")
        self.assertIn("incoming/旧 文档.docx", item["inferred_candidates"])
        self.assertEqual(item["hash_check"], "no-declared-hash")


if __name__ == "__main__":
    unittest.main()
