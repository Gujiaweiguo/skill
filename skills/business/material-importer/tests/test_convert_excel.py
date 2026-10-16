"""convert_excel 日期转换回归测试：列级判定取代逐单元格强转。

背景：旧实现把任意 1<val<100000 的数值逐格转成 1900 年日期，
真实凭证表里 T1 代码/科目编码/年份被批量污染（108 个假日期）。
新规则：列内 ≥2 个数值且全部 30000<val<100000 才整列转换，一个反例否决整列。
"""

from datetime import datetime
from pathlib import Path
import sys
import unittest

from openpyxl import Workbook, load_workbook

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import convert_excel  # noqa: E402


def make_sheet(cols: list[list[object]]) -> object:
    """按列构建 sheet：第 1 行表头（文本），第 2 行起数据。"""
    ws = Workbook().active
    n_rows = max(len(c) for c in cols)
    for ci, col in enumerate(cols, start=1):
        ws.cell(row=1, column=ci, value=f"H{ci}")
        for ri, v in enumerate(col, start=2):
            ws.cell(row=ri, column=ci, value=v)
    return ws


class ColumnAwareCoerceTest(unittest.TestCase):
    def test_small_int_column_stays_raw(self) -> None:
        ws = make_sheet([[2, 5, 8, 100], ["a", "b", "c", "d"]])
        _, rows, _p = convert_excel.read_sheet_data(ws)
        self.assertEqual([r[0] for r in rows], ["2", "5", "8", "100"])

    def test_year_column_stays_numeric(self) -> None:
        ws = make_sheet([[2024, 2025], ["a", "b"]])
        _, rows, _p = convert_excel.read_sheet_data(ws)
        self.assertEqual([r[0] for r in rows], ["2024", "2025"])

    def test_serial_date_column_converts(self) -> None:
        # 1899-12-30 + 45000 天 = 2023-03-15（45000 = 2023 年第 74 天）
        ws = make_sheet([[45000, 45015, 45030], ["a", "b", "c"]])
        _, rows, _p = convert_excel.read_sheet_data(ws)
        self.assertEqual(
            [r[0] for r in rows], ["2023-03-15", "2023-03-30", "2023-04-14"]
        )

    def test_mixed_column_counterexample_vetoes(self) -> None:
        ws = make_sheet([[2, 45000, 45015], ["a", "b", "c"]])
        _, rows, _p = convert_excel.read_sheet_data(ws)
        self.assertEqual([r[0] for r in rows], ["2", "45000", "45015"])

    def test_single_numeric_cell_not_coerced(self) -> None:
        ws = make_sheet([[45000], ["a"]])
        _, rows, _p = convert_excel.read_sheet_data(ws)
        self.assertEqual(rows[0][0], "45000")

    def test_datetime_cell_still_converts(self) -> None:
        # 同列 datetime + 小整数：datetime 分支照常，数值不转
        ws = make_sheet([[datetime(2024, 6, 1, 12, 30), 2]])
        _, rows, _p = convert_excel.read_sheet_data(ws)
        self.assertEqual(rows[0][0], "2024-06-01")
        self.assertEqual(rows[1][0], "2")

    def test_no_date_coerce_flag(self) -> None:
        ws = make_sheet([[45000, 45015], ["a", "b"]])
        _, rows, _p = convert_excel.read_sheet_data(ws, date_coerce=False)
        self.assertEqual([r[0] for r in rows], ["45000", "45015"])

    def test_process_file_via_cli_flag(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src_dir = tmp_path / "in"
            out_dir = tmp_path / "out"
            src_dir.mkdir()
            wb2 = Workbook()
            ws1 = wb2.active
            ws1.append(["H1", "H2"])
            ws1.append([45000, 2])
            ws1.append([45015, 5])
            wb2.create_sheet("S2").append(["X"])  # 多 sheet → CSV 路由
            src = src_dir / "t.xlsx"
            wb2.save(src)

            self.assertIn(
                "CSV", convert_excel.process_file(src, out_dir, date_coerce=False)
            )
            csv_file = out_dir / "csv" / "t_Sheet.csv"  # 多 sheet → 按 sheet 命名
            self.assertTrue(csv_file.exists())
            text = csv_file.read_text(encoding="utf-8-sig")
            self.assertIn("45000", text)
            self.assertNotIn("2023-", text)


def build_notes_workbook(multi: bool = True) -> Path:
    """含批注 + list/非 list 数据验证的工作簿，写到临时目录并返回路径。"""
    import tempfile

    from openpyxl.comments import Comment
    from openpyxl.worksheet.datavalidation import DataValidation

    tmp = tempfile.mkdtemp()
    wb = Workbook()
    ws = wb.active
    ws.title = "凭证"
    ws.append(["H1", "H2"])
    ws.append(["a", 1])
    ws["B2"].comment = Comment("这里是批注\n第二行", "auditor")
    dv_list = DataValidation(type="list", formula1='"是,否"', allow_blank=True)
    dv_list.add("A2:A10")
    ws.add_data_validation(dv_list)
    dv_whole = DataValidation(type="whole", operator="between", formula1="1", formula2="99")
    dv_whole.add("B2:B10")
    ws.add_data_validation(dv_whole)
    if multi:
        wb.create_sheet("S2").append(["X"])
    src = Path(tmp) / "t.xlsx"
    wb.save(src)
    return src


class NotesAndDisplayTest(unittest.TestCase):
    def test_comment_sidecar_with_sheet_prefix(self) -> None:
        src = build_notes_workbook(multi=True)
        out = src.parent / "out"
        self.assertIn("CSV", convert_excel.process_file(src, out))
        sidecar = out / "csv" / "t_凭证.csv.notes.md"
        self.assertTrue(sidecar.exists())
        text = sidecar.read_text(encoding="utf-8")
        self.assertIn("## 批注", text)
        self.assertIn("凭证!B2", text)  # 多 sheet → 带 sheet 前缀
        self.assertIn("这里是批注 / 第二行", text)  # 换行 → " / "

    def test_list_validation_exported_non_list_skipped(self) -> None:
        src = build_notes_workbook(multi=True)
        out = src.parent / "out"
        convert_excel.process_file(src, out)
        text = (out / "csv" / "t_凭证.csv.notes.md").read_text(encoding="utf-8")
        self.assertIn("## 数据验证", text)
        self.assertIn("是,否", text)
        self.assertIn("A2:A10", text)
        self.assertNotIn("B2:B10", text)  # whole 类不导出

    def test_percent_format_rendered_excel_style(self) -> None:
        ws = make_sheet([[0.15, 0.1234, 42]])  # 单列三行数值
        ws.cell(row=2, column=1).number_format = "0.00%"
        ws.cell(row=3, column=1).number_format = "0.0%"
        # 第 4 行普通数值格式，不变
        _, rows, _p = convert_excel.read_sheet_data(ws)
        self.assertEqual([r[0] for r in rows], ["15%", "12.34%", "42"])

    def test_trailing_empty_columns_trimmed_leading_kept(self) -> None:
        wb = Workbook()
        ws = wb.active
        ws.append(["H1", "H2", "", ""])
        ws.append(["a", "b", None, None])
        headers, rows, _p = convert_excel.read_sheet_data(ws)
        self.assertEqual(len(headers), 2)
        self.assertTrue(all(len(r) == 2 for r in rows))
        # 前导空列保留
        wb2 = Workbook()
        ws2 = wb2.active
        ws2["B1"] = "H2"
        ws2["B2"] = "x"
        headers2, rows2, _p2 = convert_excel.read_sheet_data(ws2)
        self.assertEqual(headers2[0], "")
        self.assertEqual(headers2[1], "H2")

    def test_md_escape_newline_and_pipe(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            wb = Workbook()
            ws = wb.active
            ws.append(["H1", "H2"])
            ws.append(["a\nb", "x|y"])
            ws.append(["c", "d"])
            src = tmp_path / "in" / "t.xlsx"
            src.parent.mkdir(parents=True)
            wb.save(src)
            out = tmp_path / "out"
            self.assertIn("Markdown", convert_excel.process_file(src, out))
            text = (out / "t.md").read_text(encoding="utf-8")
            self.assertIn("a<br>b", text)
            self.assertIn("x\\|y", text)
            # 表格行数完整：表头 + 分隔行 + 2 数据行
            table_rows = [l for l in text.splitlines() if l.startswith("|")]
            self.assertEqual(len(table_rows), 4)

    def test_no_notes_no_sidecar(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            wb = Workbook()
            ws = wb.active
            ws.append(["H1", "H2"])
            ws.append(["a", 1])
            wb.create_sheet("S2").append(["X"])  # 多 sheet → CSV 路由
            src = tmp_path / "t.xlsx"
            wb.save(src)
            out = tmp_path / "out"
            convert_excel.process_file(src, out)
            csv_dir = out / "csv"
            self.assertFalse(any(csv_dir.glob("*.notes.md")))

    def test_md_path_notes_appended_to_file(self) -> None:
        import tempfile

        from openpyxl.comments import Comment

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            wb = Workbook()
            ws = wb.active
            ws.append(["H1"])
            ws.append(["a"])
            ws["A2"].comment = Comment("单sheet批注", "auditor")
            src = tmp_path / "t.xlsx"
            wb.save(src)
            out = tmp_path / "out"
            self.assertIn("Markdown", convert_excel.process_file(src, out))
            text = (out / "t.md").read_text(encoding="utf-8")
            self.assertIn("## 批注", text)
            self.assertIn("- A2: 单sheet批注", text)  # 单 sheet → 无 sheet 前缀


class ProvenanceManifestTest(unittest.TestCase):
    def _convert(self) -> tuple[Path, Path, Path]:
        import hashlib
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            pass  # keep imports local; real body below
        return None  # placeholder replaced by callers

    def test_manifest_sha_and_fields(self) -> None:
        import hashlib
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            wb = Workbook()
            wb.active.append(["H1", "H2"])
            wb.active.append(["a", 1])
            wb.create_sheet("S2").append(["X"])  # 多 sheet → CSV 路径
            src = tmp_path / "t.xlsx"
            wb.save(src)
            out = tmp_path / "out"
            self.assertIn("CSV", convert_excel.process_file(src, out))

            manifest = out / "_manifest.json"
            self.assertTrue(manifest.exists())
            records = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual(len(records), 1)
            rec = records[0]
            self.assertEqual(rec["source_path"], str(src.resolve()))
            self.assertEqual(
                rec["source_sha256"],
                hashlib.sha256(src.read_bytes()).hexdigest(),
            )
            self.assertEqual(rec["extractor"], "convert_excel.py")
            self.assertEqual(rec["extractor_version"], 3)
            self.assertEqual(rec["source_size"], src.stat().st_size)
            self.assertIn("fidelity", rec)
            self.assertEqual(rec["fidelity"]["text"], "high")
            self.assertTrue(rec["artifacts"])
            for a in rec["artifacts"]:
                self.assertTrue((out / a).exists(), a)

    def test_manifest_rerun_idempotent_by_source_path(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            wb = Workbook()
            wb.active.append(["H1"])
            wb.active.append(["a"])
            wb.create_sheet("S2").append(["X"])
            src = tmp_path / "t.xlsx"
            wb.save(src)
            out = tmp_path / "out"
            convert_excel.process_file(src, out)
            # 第二个不同源文件 → 2 条记录
            src2 = tmp_path / "u.xlsx"
            wb2 = Workbook()
            wb2.active.append(["X"])
            wb2.create_sheet("Y").append(["Z"])
            wb2.save(src2)
            convert_excel.process_file(src2, out)
            records = json.loads((out / "_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(records), 2)
            # 重跑同一源 → 仍 2 条（按 source_path 覆盖，不重复）
            convert_excel.process_file(src, out)
            records = json.loads((out / "_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(records), 2)
            self.assertEqual(
                {r["source_path"] for r in records},
                {str(src.resolve()), str(src2.resolve())},
            )

    def test_md_provenance_header(self) -> None:
        import hashlib
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            wb = Workbook()
            wb.active.append(["H1"])
            wb.active.append(["a"])
            src = tmp_path / "t.xlsx"
            wb.save(src)
            out = tmp_path / "out"
            self.assertIn("Markdown", convert_excel.process_file(src, out))
            text = (out / "t.md").read_text(encoding="utf-8")
            # 头部在最前，标题仍是第一个 heading
            self.assertTrue(text.startswith("<!--\n"))
            self.assertIn(f"source_path: {src.resolve()}", text)
            self.assertIn(
                f"source_sha256: {hashlib.sha256(src.read_bytes()).hexdigest()}",
                text,
            )
            self.assertIn("extractor: convert_excel.py v3", text)
            self.assertIn("-->", text)
            title_idx = text.index("# t")
            header_end = text.index("-->")
            self.assertLess(header_end, title_idx)


def make_qa_sheet(ws) -> None:
    """黄金样式：row1 合并式标题(稀疏) + row2/3 状态行 + row4 真实表头。"""
    ws["B1"] = "■QA管理表"
    ws["C2"] = "确认中"
    ws["C3"] = "确认完成"
    for ci, h in enumerate(["编号", "状态", "类型", "QA内容", "提出日期"], start=2):
        ws.cell(row=4, column=ci, value=h)
    ws.cell(row=5, column=2, value="1")
    ws.cell(row=5, column=3, value="确认中")
    ws.cell(row=5, column=4, value="凭证定义")


class HeaderScanTest(unittest.TestCase):
    def test_scan_finds_real_header_and_keeps_preface(self) -> None:
        wb = Workbook()
        ws = wb.active
        make_qa_sheet(ws)
        headers, rows, preface = convert_excel.read_sheet_data(ws)
        self.assertEqual(headers[:3], ["", "编号", "状态"])
        self.assertEqual(len(rows), 1)  # 数据行完整
        self.assertEqual(rows[0][3], "凭证定义")  # D 列（0-based idx 3）
        self.assertIn("■QA管理表", preface[0])
        self.assertTrue(any("确认中" in p for p in preface))

    def test_preface_to_csv_notes_and_md_blockquote(self) -> None:
        import tempfile

        for multi in (True, False):
            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                wb = Workbook()
                make_qa_sheet(wb.active)
                if multi:
                    wb.create_sheet("S2").append(["X"])
                src = tmp_path / "t.xlsx"
                wb.save(src)
                out = tmp_path / "out"
                result = convert_excel.process_file(src, out)
                if multi:
                    self.assertIn("CSV", result)
                    sidecar = out / "csv" / "t_Sheet.csv.notes.md"
                    self.assertTrue(sidecar.exists())
                    text = sidecar.read_text(encoding="utf-8")
                    self.assertTrue(text.startswith("## 前言区"))
                    self.assertIn("■QA管理表", text)
                    self.assertIn("确认完成", text)
                    csv_text = (out / "csv" / "t_Sheet.csv").read_text(
                        encoding="utf-8-sig")
                    self.assertTrue(csv_text.startswith(",编号,状态"))
                else:
                    self.assertIn("Markdown", result)
                    md = (out / "t.md").read_text(encoding="utf-8")
                    self.assertIn("> ■QA管理表", md)
                    self.assertIn("确认完成", md)
                    # 前言在表格之前
                    self.assertLess(md.index("> ■QA管理表"), md.index("|  | 编号"))

    def test_no_preface_regression_unchanged(self) -> None:
        ws = make_sheet([[2, 5, 8, 100], ["a", "b", "c", "d"]])
        headers, rows, preface = convert_excel.read_sheet_data(ws)
        self.assertEqual(preface, [])
        self.assertEqual([r[0] for r in rows], ["2", "5", "8", "100"])

    def test_sparse_data_rows_do_not_misfire(self) -> None:
        # row1 稀疏 + 后续都是稀疏数据行（无 >0.6+margin 的行）→ 不扫描，旧行为
        wb = Workbook()
        ws = wb.active
        ws["B1"] = "标签"
        ws["C2"] = "v1"
        ws["C3"] = "v2"
        headers, rows, preface = convert_excel.read_sheet_data(ws)
        self.assertEqual(preface, [])
        self.assertEqual(headers[1], "标签")  # row1 仍是表头（旧行为）

    def test_explicit_header_row(self) -> None:
        wb = Workbook()
        ws = wb.active
        make_qa_sheet(ws)
        headers, rows, preface = convert_excel.read_sheet_data(ws, header_row=4)
        self.assertEqual(headers[:3], ["", "编号", "状态"])
        self.assertEqual(len(preface), 3)
        self.assertIn("确认完成", preface[2])

    def test_no_header_scan_restores_old_behavior(self) -> None:
        wb = Workbook()
        ws = wb.active
        make_qa_sheet(ws)
        headers, rows, preface = convert_excel.read_sheet_data(
            ws, header_scan=False
        )
        self.assertEqual(preface, [])
        # 旧行为：row1（稀疏标题行）当表头
        self.assertEqual(headers[1], "■QA管理表")
        self.assertEqual(rows[0][2], "确认中")

    def test_title_row_simple_sheet_routes_to_md(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            wb = Workbook()
            ws = wb.active
            ws["A1"] = "标题行"
            for ci, h in enumerate(["H1", "H2"], start=1):
                ws.cell(row=2, column=ci, value=h)
            ws.cell(row=3, column=1, value="a")
            ws.cell(row=3, column=2, value="b")
            src = tmp_path / "t.xlsx"
            wb.save(src)
            self.assertTrue(convert_excel.file_is_simple(src))
            out = tmp_path / "out"
            self.assertIn("Markdown", convert_excel.process_file(src, out))

    def test_preface_excluded_from_date_coercion_stats(self) -> None:
        # 前言行里的小整数 2 不参与列投票 → 正文列(45000,45015)仍被强转
        wb = Workbook()
        ws = wb.active
        ws["A1"] = "标题"          # row1 稀疏标题
        ws["B2"] = 2              # row2 前言状态行（含小整数）
        for ci, h in enumerate(["H1", "H2", "H3"], start=2):  # row3 真实表头
            ws.cell(row=3, column=ci, value=h)
        ws.cell(row=4, column=2, value=45000)
        ws.cell(row=5, column=2, value=45015)
        headers, rows, preface = convert_excel.read_sheet_data(ws)
        self.assertEqual(headers[:2], ["", "H1"])
        self.assertEqual([r[1] for r in rows], ["2023-03-15", "2023-03-30"])


if __name__ == "__main__":
    unittest.main()
