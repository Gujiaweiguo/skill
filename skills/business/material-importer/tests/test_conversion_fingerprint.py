"""转换指纹状态机与模式×状态矩阵测试（harden-material-import-provenance 2.7/2.8）。

覆盖：
- _fingerprint.evaluate：七态不互相折叠（source/options/converter 分别可识别、
  缺指纹要素=unknown、输出缺失/被编辑不虚报 up-to-date）。
- _fingerprint.decide_action：D2 矩阵六态×三模式逐格（18 格）+
  --force-overwrite-modified 例外 + unknown 无输出的首转补齐语义。
- convert_excel 脚本级：--skip-up-to-date 跳过、--check 零写入（字节快照）、
  三态变化可识别（改 manifest 模拟 converter 变化）、output-modified/conflict
  全模式不静默覆盖、force 覆盖打印清单、orphan-outputs 盘点不删除。
- convert_doc 脚本级：MD 内联指纹（body 编辑检出、头部行不参与 body 摘要、
  头部后追加内容属于 body）、锁/矩阵行为；markitdown 全程 monkeypatch 绕过，
  端到端 1 条真实小 pptx 转换。
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import _fingerprint  # noqa: E402
import convert_excel  # noqa: E402

from openpyxl import Workbook  # noqa: E402

DOC_SCRIPT = SCRIPTS_DIR / "convert_doc.py"

_module_seq = 0


def load_convert_doc():
    """进程内加载 convert_doc.py（独立模块名避免装载冲突）。"""
    global _module_seq
    _module_seq += 1
    spec = importlib.util.spec_from_file_location(
        f"convert_doc_fp_{_module_seq}", DOC_SCRIPT
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─── 合成样例 helpers ──────────────────────────────────────────────


def make_simple_xlsx(path: Path) -> Path:
    """单 sheet 简单表 → Markdown 路由。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet"
    ws.append(["H1", "H2"])
    ws.append(["a", 1])
    wb.save(path)
    return path


def make_multi_xlsx(path: Path, sheets: tuple[str, ...] = ("S1", "S2")) -> Path:
    """多 sheet → CSV 路由。"""
    wb = Workbook()
    wb.remove(wb.active)
    for name in sheets:
        ws = wb.create_sheet(name)
        ws.append(["H1", "H2"])
        ws.append(["a", 1])
    wb.save(path)
    return path


def snapshot(root: Path) -> dict[str, str]:
    """目录树字节快照 {相对路径: sha256}（用于零写入钉死）。"""
    snap: dict[str, str] = {}
    if not root.exists():
        return snap
    for p in sorted(root.rglob("*")):
        if p.is_file():
            snap[p.relative_to(root).as_posix()] = hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
    return snap


def strip_fingerprint_fields(manifest: Path) -> None:
    """把 manifest 中的新指纹字段剥掉，模拟旧代际记录。"""
    records = json.loads(manifest.read_text(encoding="utf-8"))
    for r in records:
        for k in ("options", "outputs", "backend", "fingerprint_format"):
            r.pop(k, None)
    manifest.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def first_record(output_dir: Path) -> dict:
    return json.loads(
        (output_dir / "_manifest.json").read_text(encoding="utf-8")
    )[0]


# ─── _fingerprint.evaluate：七态语义 ───────────────────────────────


class EvaluateStateTest(unittest.TestCase):
    SHA_A = "a" * 64
    SHA_B = "b" * 64
    BODY_1 = "1" * 64
    BODY_2 = "2" * 64

    def _record(self, **kw) -> _fingerprint.RecordFactors:
        base = dict(
            source_sha256=self.SHA_A,
            options={"date_coerce": True},
            converter_version=3,
            outputs=[{"path": "t.md", "sha256": self.BODY_1}],
        )
        base.update(kw)
        return _fingerprint.RecordFactors(**base)

    def _observed(self, **kw) -> _fingerprint.Observed:
        base = dict(
            source_sha256=self.SHA_A,
            options={"date_coerce": True},
            converter_version=3,
            existing_outputs=[{"path": "t.md", "sha256": self.BODY_1}],
        )
        base.update(kw)
        return _fingerprint.Observed(**base)

    def test_up_to_date(self):
        self.assertEqual(
            _fingerprint.evaluate(self._record(), self._observed()), "up-to-date"
        )

    def test_source_changed(self):
        state = _fingerprint.evaluate(
            self._record(), self._observed(source_sha256=self.SHA_B)
        )
        self.assertEqual(state, "source-changed")

    def test_options_changed(self):
        state = _fingerprint.evaluate(
            self._record(), self._observed(options={"date_coerce": False})
        )
        self.assertEqual(state, "options-changed")

    def test_converter_changed(self):
        state = _fingerprint.evaluate(
            self._record(), self._observed(converter_version=2)
        )
        self.assertEqual(state, "converter-changed")

    def test_three_changes_do_not_collapse(self):
        """三态分别可识别，不互相折叠（spec 验收场景）。"""
        states = {
            _fingerprint.evaluate(
                self._record(), self._observed(source_sha256=self.SHA_B)
            ),
            _fingerprint.evaluate(
                self._record(), self._observed(options={"date_coerce": False})
            ),
            _fingerprint.evaluate(
                self._record(), self._observed(converter_version=99)
            ),
        }
        self.assertEqual(
            states, {"source-changed", "options-changed", "converter-changed"}
        )

    def test_missing_any_factor_is_unknown(self):
        cases = [
            self._record(source_sha256=None),
            self._record(options=None),
            self._record(converter_version=None),
            self._record(outputs=None),
            self._record(outputs=[]),          # 空输出清单不合法
            self._record(source_sha256="zz"),  # 非法哈希格式
            None,                              # 无记录
        ]
        for record in cases:
            self.assertEqual(
                _fingerprint.evaluate(record, self._observed()), "unknown", repr(record)
            )

    def test_future_fingerprint_format_is_unknown(self):
        state = _fingerprint.evaluate(
            self._record(fingerprint_format=99), self._observed()
        )
        self.assertEqual(state, "unknown")

    def test_output_missing_not_up_to_date(self):
        state = _fingerprint.evaluate(
            self._record(), self._observed(existing_outputs=[])
        )
        self.assertEqual(state, "output-missing")

    def test_output_modified_not_up_to_date(self):
        state = _fingerprint.evaluate(
            self._record(),
            self._observed(
                existing_outputs=[{"path": "t.md", "sha256": self.BODY_2}]
            ),
        )
        self.assertEqual(state, "output-modified")

    def test_conflict_is_modified_and_changed(self):
        state = _fingerprint.evaluate(
            self._record(),
            self._observed(
                source_sha256=self.SHA_B,
                existing_outputs=[{"path": "t.md", "sha256": self.BODY_2}],
            ),
        )
        self.assertEqual(state, "conflict")

    def test_doc_style_no_options_never_options_changed(self):
        """convert_doc 无选项域（两侧 {}）：options-changed 不凭空出现。"""
        record = self._record(options={})
        state = _fingerprint.evaluate(record, self._observed(options={}))
        self.assertEqual(state, "up-to-date")


# ─── _fingerprint.decide_action：D2 矩阵 18 格逐格 ────────────────
# 六态 = unknown / up-to-date / changed（source-changed 代表，options/converter
# 行为相同性另有断言）/ output-missing / output-modified / conflict；
# 三模式 = default / check / skip-up-to-date。


class MatrixDefaultModeTest(unittest.TestCase):
    """旧默认命令列（3 格 + force 例外）。"""

    def _decide(self, state, **kw):
        return _fingerprint.decide_action(
            state, _fingerprint.MODE_DEFAULT, has_existing_output=True, **kw
        )

    def test_cell_default_unknown(self):
        d = self._decide("unknown")
        self.assertEqual(d.action, "convert")  # =现状重转覆盖（无从检测修改）
        self.assertFalse(d.protected)

    def test_cell_default_up_to_date(self):
        d = self._decide("up-to-date")
        self.assertEqual(d.action, "convert")  # 现状幂等重写
        self.assertFalse(d.protected)

    def test_cell_default_changed(self):
        for state in ("source-changed", "options-changed", "converter-changed"):
            d = self._decide(state)
            self.assertEqual(d.action, "convert", state)
            self.assertFalse(d.protected, state)

    def test_cell_default_output_missing(self):
        d = self._decide("output-missing")
        self.assertEqual(d.action, "convert")
        self.assertFalse(d.protected)

    def test_cell_default_output_modified(self):
        d = self._decide("output-modified")
        self.assertEqual(d.action, "skip")  # 不覆盖
        self.assertTrue(d.protected)

    def test_cell_default_conflict(self):
        d = self._decide("conflict")
        self.assertEqual(d.action, "skip")
        self.assertTrue(d.protected)

    def test_default_force_overwrite_modified_exception(self):
        for state in ("output-modified", "conflict"):
            d = self._decide(state, force_overwrite_modified=True)
            self.assertEqual(d.action, "convert", state)
            self.assertFalse(d.protected, state)
            self.assertIn("force", d.note)


class MatrixCheckModeTest(unittest.TestCase):
    """--check 列（6 格）：一律 report、零写入。"""

    def _decide(self, state):
        return _fingerprint.decide_action(
            state, _fingerprint.MODE_CHECK, has_existing_output=True
        )

    def test_cell_check_unknown(self):
        self.assertEqual(self._decide("unknown").action, "report")

    def test_cell_check_up_to_date(self):
        self.assertEqual(self._decide("up-to-date").action, "report")

    def test_cell_check_changed(self):
        for state in ("source-changed", "options-changed", "converter-changed"):
            self.assertEqual(self._decide(state).action, "report", state)
            self.assertEqual(self._decide(state).state, state)

    def test_cell_check_output_missing(self):
        self.assertEqual(self._decide("output-missing").action, "report")

    def test_cell_check_output_modified(self):
        self.assertEqual(self._decide("output-modified").action, "report")

    def test_cell_check_conflict(self):
        self.assertEqual(self._decide("conflict").action, "report")


class MatrixSkipUpToDateModeTest(unittest.TestCase):
    """--skip-up-to-date 列（6 格 + unknown 首转细分）。"""

    def _decide(self, state, has_output=True):
        return _fingerprint.decide_action(
            state, _fingerprint.MODE_SKIP_UP_TO_DATE, has_existing_output=has_output
        )

    def test_cell_skip_unknown_with_output_kept(self):
        d = self._decide("unknown", has_output=True)
        self.assertEqual(d.action, "skip")
        self.assertFalse(d.protected)
        self.assertIn("显式重转", d.note)

    def test_cell_skip_unknown_no_output_first_conversion(self):
        """unknown 无输出（首转/output-missing 补齐）不被 unknown 规则拦截。"""
        d = self._decide("unknown", has_output=False)
        self.assertEqual(d.action, "convert")

    def test_cell_skip_up_to_date(self):
        d = self._decide("up-to-date")
        self.assertEqual(d.action, "skip")
        self.assertFalse(d.protected)

    def test_cell_skip_changed(self):
        for state in ("source-changed", "options-changed", "converter-changed"):
            d = self._decide(state)
            self.assertEqual(d.action, "convert", state)
            self.assertFalse(d.protected, state)

    def test_cell_skip_output_missing(self):
        d = self._decide("output-missing")
        self.assertEqual(d.action, "convert")
        self.assertFalse(d.protected)

    def test_cell_skip_output_modified(self):
        d = self._decide("output-modified")
        self.assertEqual(d.action, "skip")
        self.assertTrue(d.protected)

    def test_cell_skip_conflict(self):
        d = self._decide("conflict")
        self.assertEqual(d.action, "skip")
        self.assertTrue(d.protected)


# ─── convert_excel 脚本级（指纹 + 矩阵 + 预写检查 + orphan）────────


class ExcelFingerprintTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(dir="/tmp/opencode")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.in_dir = self.root / "in"
        self.out_dir = self.root / "out"
        self.in_dir.mkdir()


class ExcelFingerprintTest(ExcelFingerprintTestBase):
    def test_same_input_same_config_skip_up_to_date(self):
        """同输入同配置 → up-to-date；--skip-up-to-date 跳过且 manifest/输出不变。"""
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        self.assertIn("Markdown", convert_excel.process_file(src, self.out_dir))
        before_out = snapshot(self.out_dir)
        result = convert_excel.process_file(
            src, self.out_dir, mode=_fingerprint.MODE_SKIP_UP_TO_DATE
        )
        self.assertTrue(result.startswith("skip("), result)
        self.assertIn("up-to-date", result)
        self.assertEqual(snapshot(self.out_dir), before_out)

    def test_check_reports_up_to_date_rc0(self):
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        rc = convert_excel.main([str(self.in_dir), str(self.out_dir), "--check"])
        self.assertEqual(rc, 0)

    def test_unknown_old_manifest_check_zero_writes(self):
        """旧产物缺指纹 → unknown；--check 前后全部目标文件字节逐字节相同。"""
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        strip_fingerprint_fields(self.out_dir / "_manifest.json")
        before = snapshot(self.out_dir)
        rc = convert_excel.main([str(self.in_dir), str(self.out_dir), "--check"])
        self.assertEqual(rc, 3)
        info = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info["state"], "unknown")
        self.assertTrue(info["needs_recheck"])
        self.assertEqual(snapshot(self.out_dir), before)

    def test_skip_up_to_date_keeps_unknown_old_output(self):
        """unknown+已有输出：--skip-up-to-date 保留旧输出、报告需显式重转。"""
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        strip_fingerprint_fields(self.out_dir / "_manifest.json")
        md = self.out_dir / "t.md"
        md_before = md.read_bytes()
        result = convert_excel.process_file(
            src, self.out_dir, mode=_fingerprint.MODE_SKIP_UP_TO_DATE
        )
        self.assertTrue(result.startswith("skip("), result)
        self.assertIn("unknown", result)
        self.assertIn("显式重转", result)
        self.assertEqual(md.read_bytes(), md_before)

    def test_skip_up_to_date_first_conversion_not_blocked(self):
        """首转（无 manifest/无输出）在 --skip-up-to-date 下不被 unknown 拦截。"""
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        result = convert_excel.process_file(
            src, self.out_dir, mode=_fingerprint.MODE_SKIP_UP_TO_DATE
        )
        self.assertIn("Markdown", result)
        self.assertTrue((self.out_dir / "t.md").exists())

    def test_source_changed_identified_and_reconverted(self):
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        # 修改源（追加行 → 字节变化）
        from openpyxl import load_workbook

        wb = load_workbook(src)
        wb.active.append(["new", 9])
        wb.save(src)
        info = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info["state"], "source-changed")
        # skip 模式重转 + manifest sha 更新
        result = convert_excel.process_file(
            src, self.out_dir, mode=_fingerprint.MODE_SKIP_UP_TO_DATE
        )
        self.assertIn("Markdown", result)
        rec = first_record(self.out_dir)
        self.assertEqual(
            rec["source_sha256"],
            hashlib.sha256(src.read_bytes()).hexdigest(),
        )

    def test_options_changed_identified(self):
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        info = convert_excel.check_file(src, self.out_dir, date_coerce=False)
        self.assertEqual(info["state"], "options-changed")
        rc = convert_excel.main(
            [str(self.in_dir), str(self.out_dir), "--check", "--no-date-coerce"]
        )
        self.assertEqual(rc, 3)

    def test_converter_changed_identified(self):
        """直接改 manifest record 的 extractor_version 模拟转换器代际变化。"""
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        manifest = self.out_dir / "_manifest.json"
        records = json.loads(manifest.read_text(encoding="utf-8"))
        records[0]["extractor_version"] = 2
        manifest.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        info = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info["state"], "converter-changed")

    def test_output_missing_not_faked_as_up_to_date(self):
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        (self.out_dir / "t.md").unlink()
        info = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info["state"], "output-missing")
        # skip 模式补齐
        result = convert_excel.process_file(
            src, self.out_dir, mode=_fingerprint.MODE_SKIP_UP_TO_DATE
        )
        self.assertIn("Markdown", result)
        self.assertTrue((self.out_dir / "t.md").exists())

    def _make_modified(self) -> Path:
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        md = self.out_dir / "t.md"
        md.write_text(md.read_text(encoding="utf-8") + "\n人工补充注释\n", encoding="utf-8")
        return md

    def test_output_modified_default_keeps_human_edit(self):
        md = self._make_modified()
        edited = md.read_bytes()
        result = convert_excel.process_file(src := self.in_dir / "t.xlsx", self.out_dir)
        self.assertTrue(result.startswith("skip("), result)
        self.assertIn("output-modified", result)
        self.assertEqual(md.read_bytes(), edited)  # 人工编辑保留
        # manifest 也不被改动
        info = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info["state"], "output-modified")

    def test_output_modified_check_reports_with_rc3(self):
        self._make_modified()
        rc = convert_excel.main([str(self.in_dir), str(self.out_dir), "--check"])
        self.assertEqual(rc, 3)

    def test_output_modified_skip_mode_keeps(self):
        md = self._make_modified()
        edited = md.read_bytes()
        result = convert_excel.process_file(
            self.in_dir / "t.xlsx", self.out_dir,
            mode=_fingerprint.MODE_SKIP_UP_TO_DATE,
        )
        self.assertTrue(result.startswith("skip("), result)
        self.assertEqual(md.read_bytes(), edited)

    def test_force_overwrite_modified_prints_covered_list(self):
        md = self._make_modified()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = convert_excel.process_file(
                self.in_dir / "t.xlsx", self.out_dir,
                force_overwrite_modified=True,
            )
        self.assertIn("Markdown", result)
        out = buf.getvalue()
        self.assertIn("force-overwrite-modified", out)
        self.assertIn("t.md", out)  # 打印被覆盖清单
        self.assertNotIn("人工补充注释", md.read_text(encoding="utf-8"))

    def test_conflict_default_keeps_and_check_reports(self):
        md = self._make_modified()
        edited = md.read_bytes()
        src = self.in_dir / "t.xlsx"
        from openpyxl import load_workbook

        wb = load_workbook(src)
        wb.active.append(["new", 9])
        wb.save(src)
        result = convert_excel.process_file(src, self.out_dir)
        self.assertTrue(result.startswith("skip("), result)
        self.assertIn("conflict", result)
        self.assertEqual(md.read_bytes(), edited)
        info = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info["state"], "conflict")
        rc = convert_excel.main([str(self.in_dir), str(self.out_dir), "--check"])
        self.assertEqual(rc, 3)

    def test_orphan_outputs_md_to_csv_route_change(self):
        """MD↔CSV 路由切换 → --check 报 orphan-outputs + needs_recheck，不删文件。"""
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        self.assertTrue((self.out_dir / "t.md").exists())
        # 改成多 sheet → CSV 路由；t.md 不再属于新预期
        make_multi_xlsx(src)
        info = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info["state"], "source-changed")
        orphan = {o["path"]: o["origin"] for o in info["orphans"]}
        self.assertEqual(orphan.get("t.md"), "manifest-recorded")
        self.assertTrue(info["needs_recheck"])
        self.assertTrue((self.out_dir / "t.md").exists())  # 永不自动删除
        rc = convert_excel.main([str(self.in_dir), str(self.out_dir), "--check"])
        self.assertEqual(rc, 3)
        # 默认重转后：manifest 刷新不再列 t.md，但磁盘残留仍可盘点（disk-untracked）
        result = convert_excel.process_file(src, self.out_dir)
        self.assertIn("CSV", result)
        self.assertTrue((self.out_dir / "t.md").exists())  # 重转不删旧输出
        info2 = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info2["state"], "up-to-date")
        orphan2 = {o["path"]: o["origin"] for o in info2["orphans"]}
        self.assertEqual(orphan2.get("t.md"), "disk-untracked")
        self.assertTrue(info2["needs_recheck"])  # up-to-date 但有 orphan 仍需复核
        rc2 = convert_excel.main([str(self.in_dir), str(self.out_dir), "--check"])
        self.assertEqual(rc2, 3)
        self.assertTrue((self.out_dir / "t.md").exists())

    def test_orphan_outputs_sheet_deleted(self):
        """多 sheet 删 sheet → 旧 CSV 残留被盘点，不删除；重转后仍可盘点。"""
        src = make_multi_xlsx(self.in_dir / "t.xlsx", sheets=("S1", "S2"))
        convert_excel.process_file(src, self.out_dir)
        csv1 = self.out_dir / "csv" / "t_S1.csv"
        csv2 = self.out_dir / "csv" / "t_S2.csv"
        self.assertTrue(csv1.exists() and csv2.exists())
        make_simple_xlsx(src)  # 单 sheet 简单表 → MD 路由
        info = convert_excel.check_file(src, self.out_dir)
        orphan = {o["path"]: o["origin"] for o in info["orphans"]}
        self.assertEqual(
            set(orphan), {"csv/t_S1.csv", "csv/t_S2.csv"}
        )
        self.assertEqual(set(orphan.values()), {"manifest-recorded"})
        self.assertTrue(csv1.exists() and csv2.exists())
        # 默认重转后：manifest 刷新（只列 t.md），旧 csv 仍以 disk-untracked 盘出
        result = convert_excel.process_file(src, self.out_dir)
        self.assertIn("Markdown", result)
        self.assertTrue(csv1.exists() and csv2.exists())
        info2 = convert_excel.check_file(src, self.out_dir)
        orphan2 = {o["path"]: o["origin"] for o in info2["orphans"]}
        self.assertEqual(
            orphan2,
            {"csv/t_S1.csv": "disk-untracked", "csv/t_S2.csv": "disk-untracked"},
        )
        self.assertTrue(info2["needs_recheck"])


# ─── convert_doc 脚本级（MD 内联指纹）──────────────────────────────


class DocFingerprintTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(dir="/tmp/opencode")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.mod = load_convert_doc()
        self.md_calls: list[Path] = []
        self.mod.run_markitdown = self._fake_markitdown

    def _fake_markitdown(self, src: Path) -> str:
        self.md_calls.append(src)
        return "markitdown 转换正文\n"

    def make_src(self, name: str = "s.docx", content: bytes = b"PK\x03\x04zip-body") -> Path:
        src = self.root / name
        src.write_bytes(content)
        return src

    def write_out_with_fingerprint(
        self,
        out: Path,
        src: Path,
        body: str = "markitdown 转换正文\n",
        version: int = 2,
        with_body_sha: bool = True,
        with_source_sha: bool = True,
    ) -> None:
        src_sha = hashlib.sha256(src.read_bytes()).hexdigest()
        lines = []
        if with_source_sha:
            lines.append(f"<!-- source: {src.name} -->")
            lines.append(f"<!-- source_sha256: {src_sha} -->")
        lines.append(
            f"<!-- extracted_by: markitdown via convert_doc.py v{version} (2026-01-01) -->"
        )
        lines.append("<!-- fidelity: text=high -->")
        if with_body_sha:
            lines.append(
                f"<!-- output_body_sha256: "
                f"{hashlib.sha256(body.encode('utf-8')).hexdigest()} -->"
            )
            lines.append(
                "<!-- output_digest_scope: post-provenance-header -->"
            )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n" + body, encoding="utf-8")

    def run_main(self, *argv: str) -> tuple[int, str, str]:
        out_buf, err_buf = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
            rc = self.mod.main(list(argv))
        return rc, out_buf.getvalue(), err_buf.getvalue()


class DocFingerprintTest(DocFingerprintTestBase):
    def test_check_up_to_date_zero_markitdown_calls(self):
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src)
        before = out.read_bytes()
        rc, stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 0)
        self.assertIn("up-to-date", stdout)
        self.assertEqual(out.read_bytes(), before)
        self.assertEqual(self.md_calls, [])  # --check 不调 markitdown

    def test_old_output_without_fingerprint_is_unknown_check_zero_writes(self):
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src, with_body_sha=False)
        before = out.read_bytes()
        rc, stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 3)
        self.assertIn("unknown", stdout)
        self.assertEqual(out.read_bytes(), before)
        self.assertEqual(self.md_calls, [])

    def test_body_edit_detected_as_output_modified(self):
        """改正文一个字 → output-modified；默认模式不覆盖、字节保留。"""
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src)
        text = out.read_text(encoding="utf-8").replace("正文", "内文")
        out.write_text(text, encoding="utf-8")
        edited = out.read_bytes()
        rc, stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 3)
        self.assertIn("output-modified", stdout)
        rc2, _o, _e = self.run_main(str(src), str(out))  # 默认模式
        self.assertEqual(rc2, 3)
        self.assertEqual(out.read_bytes(), edited)  # 人工编辑保留
        self.assertEqual(self.md_calls, [])

    def test_header_line_not_in_body_digest(self):
        """头块内的行不参与 body 摘要：改头块内容 → 仍 up-to-date（R2 明示）。"""
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src)
        text = out.read_text(encoding="utf-8").replace(
            "fidelity: text=high", "fidelity: hand-edited"
        )
        out.write_text(text, encoding="utf-8")
        rc, stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 0)  # 头块不在内联保护内 → 状态不因头块编辑改变
        self.assertIn("up-to-date", stdout)

    def test_append_after_header_is_body(self):
        """头部块之后追加的任何内容（含注释行）都属于 body → 被检出。"""
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src)
        with out.open("a", encoding="utf-8") as f:
            f.write("<!-- 追加注释 -->\n")
        rc, stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 3)
        self.assertIn("output-modified", stdout)

    def test_source_changed_and_default_reconverts(self):
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src)
        rc, stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 0)
        src.write_bytes(b"PK\x03\x04zip-body-v2")  # 源变化
        rc, stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 3)
        self.assertIn("source-changed", stdout)
        # 默认模式重转覆盖（现状语义）
        rc2, _o, _e = self.run_main(str(src), str(out))
        self.assertEqual(rc2, 0)
        self.assertEqual(len(self.md_calls), 1)
        self.assertIn(
            "output_body_sha256: ", out.read_text(encoding="utf-8")
        )

    def test_converter_changed(self):
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src, version=1)
        rc, stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 3)
        self.assertIn("converter-changed", stdout)

    def test_extracted_by_date_not_part_of_state(self):
        """extracted_by 行内的日期不参与状态判定：只改日期 → up-to-date。"""
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src)
        text = out.read_text(encoding="utf-8").replace(
            "(2026-01-01)", "(2025-12-31)"
        )
        out.write_text(text, encoding="utf-8")
        rc, _stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 0)

    def test_skip_up_to_date_keeps_unknown_output(self):
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src, with_body_sha=False)
        before = out.read_bytes()
        rc, stdout, stderr = self.run_main(str(src), str(out), "--skip-up-to-date")
        self.assertEqual(rc, 3)
        self.assertIn("unknown", stdout)
        self.assertIn("显式重转", stdout + stderr)
        self.assertEqual(out.read_bytes(), before)
        self.assertEqual(self.md_calls, [])

    def test_skip_up_to_date_first_conversion(self):
        """首转在 --skip-up-to-date 下不被拦截。"""
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        rc, _o, _e = self.run_main(str(src), str(out), "--skip-up-to-date")
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.md_calls), 1)
        self.assertTrue(out.exists())

    def test_skip_up_to_date_skips_when_up_to_date(self):
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src)
        before = out.read_bytes()
        rc, stdout, _ = self.run_main(str(src), str(out), "--skip-up-to-date")
        self.assertEqual(rc, 0)
        self.assertIn("skip", stdout)
        self.assertEqual(out.read_bytes(), before)
        self.assertEqual(self.md_calls, [])

    def test_force_overwrite_modified_reconverts(self):
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        self.write_out_with_fingerprint(out, src)
        text = out.read_text(encoding="utf-8").replace("正文", "内文")
        out.write_text(text, encoding="utf-8")
        rc, stdout, _ = self.run_main(
            str(src), str(out), "--force-overwrite-modified"
        )
        self.assertEqual(rc, 0)
        self.assertIn("force-overwrite-modified", stdout)
        self.assertIn("覆盖", stdout)
        self.assertIn(out.name, stdout)
        self.assertEqual(len(self.md_calls), 1)
        self.assertIn("markitdown 转换正文", out.read_text(encoding="utf-8"))

    def test_check_first_conversion_no_output(self):
        src = self.make_src()
        out = self.root / "out" / "s.docx.md"
        rc, stdout, _ = self.run_main(str(src), str(out), "--check")
        self.assertEqual(rc, 3)
        self.assertIn("unknown", stdout)
        self.assertFalse(out.exists())


class DocEndToEndMarkitdownTest(unittest.TestCase):
    """端到端 1 条真实转换（python-pptx 造 1 页小 pptx + 真实 markitdown）。"""

    def test_real_pptx_fingerprint_roundtrip(self):
        import subprocess

        from pptx import Presentation as PptxPresentation
        from pptx.util import Inches

        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            pptx_path = root / "mini.pptx"
            prs = PptxPresentation()
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            tb = slide.shapes.add_textbox(
                Inches(1), Inches(1), Inches(6), Inches(1)
            )
            tb.text_frame.text = "端到端指纹测试正文"
            prs.save(str(pptx_path))

            out = root / "mini.pptx.md"
            proc = subprocess.run(
                [sys.executable, str(DOC_SCRIPT), str(pptx_path), str(out)],
                cwd=str(TESTS_DIR.parent),
                capture_output=True, text=True, timeout=300,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = out.read_text(encoding="utf-8")
            self.assertIn("output_digest_scope: post-provenance-header", text)
            self.assertIn("output_body_sha256: ", text)
            self.assertIn("端到端指纹测试正文", text)

            # 重算 body 哈希自洽 + --check up-to-date
            mod = load_convert_doc()
            fields, body_offset = mod.parse_provenance_header(out)
            self.assertEqual(
                fields["output_body_sha256"],
                hashlib.sha256(out.read_bytes()[body_offset:]).hexdigest(),
            )
            check = subprocess.run(
                [sys.executable, str(DOC_SCRIPT), str(pptx_path), str(out), "--check"],
                cwd=str(TESTS_DIR.parent),
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("up-to-date", check.stdout)

            # 正文编辑 → output-modified
            out.write_text(
                out.read_text(encoding="utf-8").replace("端到端", "端对端"),
                encoding="utf-8",
            )
            check2 = subprocess.run(
                [sys.executable, str(DOC_SCRIPT), str(pptx_path), str(out), "--check"],
                cwd=str(TESTS_DIR.parent),
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(check2.returncode, 3)
            self.assertIn("output-modified", check2.stdout)


class DecisionDiagnosticsTest(unittest.TestCase):
    """修复 6：evaluate_detail 叠加诊断 + Decision 携带两侧清单；修复 8：组合防御。"""

    SHA_A = "a" * 64
    BODY_1 = "1" * 64
    BODY_2 = "2" * 64

    def _record_outputs2(self) -> _fingerprint.RecordFactors:
        return _fingerprint.RecordFactors(
            source_sha256=self.SHA_A,
            options={"date_coerce": True},
            converter_version=3,
            outputs=[
                {"path": "csv/a_S1.csv", "sha256": self.BODY_1},
                {"path": "csv/a_S2.csv", "sha256": self.BODY_2},
            ],
        )

    def test_modified_plus_missing_both_reported(self):
        """1 个被改 + 1 个缺失并存：主状态 output-modified，两侧清单同报。"""
        record = self._record_outputs2()
        observed = _fingerprint.Observed(
            source_sha256=self.SHA_A,
            options={"date_coerce": True},
            converter_version=3,
            existing_outputs=[
                {"path": "csv/a_S1.csv", "sha256": "9" * 64},  # 被人工编辑
                # a_S2 缺失
            ],
        )
        detail = _fingerprint.evaluate_detail(record, observed)
        self.assertEqual(detail["state"], "output-modified")
        self.assertEqual(detail["modified_paths"], ["csv/a_S1.csv"])
        self.assertEqual(detail["missing_paths"], ["csv/a_S2.csv"])
        # evaluate 兼容签名与 detail 主状态一致
        self.assertEqual(_fingerprint.evaluate(record, observed), "output-modified")

    def test_conflict_plus_missing_both_reported(self):
        record = self._record_outputs2()
        observed = _fingerprint.Observed(
            source_sha256="b" * 64,  # 源也变 → conflict
            options={"date_coerce": True},
            converter_version=3,
            existing_outputs=[{"path": "csv/a_S1.csv", "sha256": "9" * 64}],
        )
        detail = _fingerprint.evaluate_detail(record, observed)
        self.assertEqual(detail["state"], "conflict")
        self.assertEqual(detail["modified_paths"], ["csv/a_S1.csv"])
        self.assertEqual(detail["missing_paths"], ["csv/a_S2.csv"])

    def test_decision_carries_paths_and_no_fill_hint(self):
        d = _fingerprint.decide_action(
            "conflict", _fingerprint.MODE_DEFAULT,
            has_existing_output=True,
            missing_paths=["csv/a_S2.csv"],
            modified_paths=["csv/a_S1.csv"],
        )
        self.assertEqual(d.action, "skip")
        self.assertTrue(d.protected)
        self.assertEqual(d.modified_paths, ["csv/a_S1.csv"])
        self.assertEqual(d.missing_paths, ["csv/a_S2.csv"])
        self.assertIn("csv/a_S2.csv", d.note)
        self.assertIn("需显式重转（默认模式）才能补齐缺失", d.note)

    def test_decide_action_skip_mode_plus_force_raises(self):
        """修复 8 防御层：skip-up-to-date + force → ValueError。"""
        with self.assertRaises(ValueError) as ctx:
            _fingerprint.decide_action(
                "output-modified", _fingerprint.MODE_SKIP_UP_TO_DATE,
                has_existing_output=True,
                force_overwrite_modified=True,
            )
        self.assertIn("不支持组合使用", str(ctx.exception))
        self.assertIn("默认转换模式 + --force-overwrite-modified", str(ctx.exception))

    def test_decide_action_check_mode_never_raises_for_force(self):
        """--check + force 由 CLI 层拒绝（互斥），决策函数 check 分支不触组合防御。"""
        d = _fingerprint.decide_action(
            "output-modified", _fingerprint.MODE_CHECK,
            has_existing_output=True, force_overwrite_modified=True,
        )
        self.assertEqual(d.action, "report")


class UnknownExistingOutputGuardTest(ExcelFingerprintTestBase):
    """修复 5：record 存在但 outputs/artifacts 均缺失/为空、磁盘有旧产物 →
    --skip-up-to-date 保留（unknown+已有输出），不因"record 无输出登记"误判首转。"""

    def _setup_incomplete_record(self) -> Path:
        """转换后把 record 的 outputs/artifacts 清空，磁盘保留 t.md（旧产物）。"""
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        convert_excel.process_file(src, self.out_dir)
        manifest = self.out_dir / "_manifest.json"
        records = json.loads(manifest.read_text(encoding="utf-8"))
        records[0]["outputs"] = []
        records[0].pop("artifacts", None)
        manifest.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.assertTrue((self.out_dir / "t.md").is_file())
        return src

    def test_skip_mode_keeps_disk_output_with_incomplete_record(self):
        src = self._setup_incomplete_record()
        md = self.out_dir / "t.md"
        before = md.read_bytes()
        result = convert_excel.process_file(
            src, self.out_dir, mode=_fingerprint.MODE_SKIP_UP_TO_DATE
        )
        self.assertTrue(result.startswith("skip("), result)
        self.assertIn("unknown", result)
        self.assertIn("显式重转", result)
        self.assertEqual(md.read_bytes(), before, "无指纹旧产物被补齐语义覆盖")

    def test_check_same_scenario_zero_writes_report_only(self):
        src = self._setup_incomplete_record()
        before = snapshot(self.out_dir)
        info = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info["state"], "unknown")
        rc = convert_excel.main([str(self.in_dir), str(self.out_dir), "--check"])
        self.assertEqual(rc, 3)
        self.assertEqual(snapshot(self.out_dir), before, "--check 零写入")

    def test_default_mode_still_overwrites(self):
        """默认模式 unknown → 现状覆盖语义不变（record 刷新带 outputs）。"""
        src = self._setup_incomplete_record()
        result = convert_excel.process_file(src, self.out_dir)
        self.assertIn("Markdown", result)
        rec = first_record(self.out_dir)
        self.assertTrue(rec["outputs"], "重转后 record 应回填 outputs 指纹")

    def test_no_disk_family_files_first_conversion(self):
        """磁盘完全无 stem 家族文件 → 按首转补齐转换（不被 unknown 保留拦截）。"""
        src = make_simple_xlsx(self.in_dir / "t.xlsx")
        # 手工放置一条"无输出登记"的 record（如上游中断残留），磁盘无 t.md
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "_manifest.json").write_text(
            json.dumps(
                [{"source_path": str(src.resolve()), "source_sha256": "0" * 64}],
                ensure_ascii=False, indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        result = convert_excel.process_file(
            src, self.out_dir, mode=_fingerprint.MODE_SKIP_UP_TO_DATE
        )
        self.assertIn("Markdown", result)
        self.assertTrue((self.out_dir / "t.md").exists())


class ModifiedPlusMissingProtectionTest(ExcelFingerprintTestBase):
    """修复 6 脚本级：多 sheet 下 1 输出被改 + 1 输出被删 → 双侧报告、
    任何模式不转换补缺失。"""

    def _setup(self) -> tuple[Path, Path, Path]:
        src = make_multi_xlsx(self.in_dir / "t.xlsx", sheets=("S1", "S2"))
        convert_excel.process_file(src, self.out_dir)
        csv1 = self.out_dir / "csv" / "t_S1.csv"
        csv2 = self.out_dir / "csv" / "t_S2.csv"
        self.assertTrue(csv1.exists() and csv2.exists())
        # 人工编辑 csv1 + 删除 csv2
        csv1.write_text(
            csv1.read_text(encoding="utf-8-sig") + "MARKER-EDIT\n",
            encoding="utf-8-sig",
        )
        csv2.unlink()
        return src, csv1, csv2

    def test_check_reports_both_sides(self):
        src, csv1, csv2 = self._setup()
        before = snapshot(self.out_dir)
        info = convert_excel.check_file(src, self.out_dir)
        self.assertEqual(info["state"], "output-modified")
        self.assertEqual(info["modified_paths"], ["csv/t_S1.csv"])
        self.assertEqual(info["missing_paths"], ["csv/t_S2.csv"])
        rc = convert_excel.main([str(self.in_dir), str(self.out_dir), "--check"])
        self.assertEqual(rc, 3)
        self.assertEqual(snapshot(self.out_dir), before, "--check 零写入")

    def test_default_mode_neither_overwrites_nor_fills(self):
        src, csv1, csv2 = self._setup()
        edited = csv1.read_bytes()
        result = convert_excel.process_file(src, self.out_dir)
        self.assertTrue(result.startswith("skip("), result)
        self.assertIn("csv/t_S1.csv", result)   # 修改侧在报告里
        self.assertIn("csv/t_S2.csv", result)   # 缺失侧在报告里
        self.assertIn("才能补齐缺失", result)
        self.assertEqual(csv1.read_bytes(), edited, "被改文件被覆盖")
        self.assertFalse(csv2.exists(), "缺失被静默补齐")

    def test_skip_mode_same_protection(self):
        src, csv1, csv2 = self._setup()
        edited = csv1.read_bytes()
        result = convert_excel.process_file(
            src, self.out_dir, mode=_fingerprint.MODE_SKIP_UP_TO_DATE
        )
        self.assertTrue(result.startswith("skip("), result)
        self.assertEqual(csv1.read_bytes(), edited)
        self.assertFalse(csv2.exists())


class FlagCombinationTest(unittest.TestCase):
    """修复 8：--skip-up-to-date + --force-overwrite-modified → 用法错误 rc=2（CLI 级）。"""

    EXCEL_SCRIPT = SCRIPTS_DIR / "convert_excel.py"
    DOC_SCRIPT = DOC_SCRIPT

    def _run(self, script: Path, *args: str):
        import subprocess

        return subprocess.run(
            [sys.executable, str(script), *args],
            cwd=str(TESTS_DIR.parent),
            capture_output=True, text=True, timeout=120,
        )

    def test_excel_combo_usage_error_rc2(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            (root / "in").mkdir()
            proc = self._run(
                self.EXCEL_SCRIPT, str(root / "in"), str(root / "out"),
                "--skip-up-to-date", "--force-overwrite-modified",
            )
            self.assertEqual(proc.returncode, 2)
            msg = proc.stdout + proc.stderr
            self.assertIn("不支持组合使用", msg)
            self.assertIn("默认转换模式 + --force-overwrite-modified", msg)

    def test_excel_check_plus_flag_usage_error_rc2(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            (root / "in").mkdir()
            proc = self._run(
                self.EXCEL_SCRIPT, str(root / "in"), str(root / "out"),
                "--check", "--skip-up-to-date",
            )
            self.assertEqual(proc.returncode, 2)

    def test_doc_combo_usage_error_rc2(self):
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            src = root / "s.docx"
            src.write_bytes(b"PK\x03\x04body")
            out = root / "s.docx.md"
            proc = self._run(
                self.DOC_SCRIPT, str(src), str(out),
                "--skip-up-to-date", "--force-overwrite-modified",
            )
            self.assertEqual(proc.returncode, 2)
            msg = proc.stdout + proc.stderr
            self.assertIn("不支持组合使用", msg)
            self.assertIn("默认转换模式 + --force-overwrite-modified", msg)

    def test_single_flags_still_accepted(self):
        """回归：单旗标组合不受影响（--check 正常执行并零写入）。"""
        with tempfile.TemporaryDirectory(dir="/tmp/opencode") as tmp:
            root = Path(tmp)
            src = root / "s.docx"
            src.write_bytes(b"PK\x03\x04body")
            out = root / "s.docx.md"
            proc = self._run(self.DOC_SCRIPT, str(src), str(out), "--check")
            self.assertEqual(proc.returncode, 3)  # 首转无输出 → unknown 报告
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
