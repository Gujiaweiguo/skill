#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["openpyxl>=3.1.0"]
# ///
# ─── How to run ───
# 1. Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run: uv run convert_excel.py <input_dir> <output_dir>
# 3. Example: uv run convert_excel.py incoming/海鼎模板 raw/海鼎模板
# ──────────────────
"""Excel 工作簿 → 按复杂度分流为 Markdown(简单) 或 CSV(复杂)。

核心原则：一个源文件只产出一种格式，不混 .md 和 .csv。

路由规则（文件级）：
  - 该文件所有 sheet 都 ≤8 列 且 无合并 且 仅 1 个 sheet → Markdown table
  - 其余（任一 sheet 超阈值 / 有合并 / 多 sheet）→ CSV（每 sheet 一个）

技术处理：
  - 合并单元格值传播（openpyxl 只有左上角有值，number_format 一并传播）
  - 双行表头展平（R1 分组合并 + R2 字段名 → 单行）
  - Excel 序列号日期 → ISO 字符串（列级判定：仅当该列 ≥2 个数值单元格且全部
    落在 30000<val<100000（约 1982–2173 年）时才整列转换；单个数值/年份/编码
    不再被误转。可用 --no-date-coerce 完全关闭数值转换）
  - 百分比格式（number_format 含 %）→ Excel 显示值（0.15 → 15%）
  - 批注 / list 类数据验证导出（CSV 路径 → 同名 .csv.notes.md 边车；MD 路径 → 追加文末）
  - 尾部全空列裁剪（不做前导空列裁剪）
  - 溯源：每次转换写 {output_dir}/_manifest.json（source 路径/sha256/时间/extractor
    版本/产物清单/fidelity）；MD 产物文首附 <!-- provenance --> 注释块（CSV 无内联头，
    由 manifest 覆盖）
  - MD 表格单元格转义：换行 → <br>，| → 转义竖线（CSV 路径由 csv 模块原生引号处理）
  - .xls / 误标 .xlsx（OLE2）自动用 libreoffice 转换
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import load_workbook

SIMPLE_MAX_COLS = 8
EXCEL_EPOCH = datetime(1899, 12, 30)
TEMP_CONVERT = Path("/tmp/opencode/excel-convert")
EXTRACTOR_VERSION = 2
MANIFEST_NAME = "_manifest.json"
# 静态保真度说明（extractor 级预期，非逐文件分析）
FIDELITY = {
    "text": "high",
    "structure": (
        "high (grid preserved; comments/validations exported to "
        ".notes.md sidecars; percent rendered display-style)"
    ),
    "notes": "date coercion is column-voted; --no-date-coerce to disable",
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_ole2(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(8) == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def ensure_xlsx(path: Path) -> Path:
    """.xls 或误标 .xlsx(OLE2) → 用 libreoffice 转为真 .xlsx 到临时目录。"""
    if path.suffix == ".xlsx" and not is_ole2(path):
        return path

    TEMP_CONVERT.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    target = TEMP_CONVERT / f"{stem}.xlsx"
    if not target.exists():
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "xlsx",
             "--outdir", str(TEMP_CONVERT), str(path)],
            capture_output=True, timeout=60,
        )
    return target if target.exists() else path


def excel_serial_to_date(val: object) -> str:
    """数值 → Excel 序列日期。仅应由列级判定通过的单元格调用。"""
    if isinstance(val, int | float) and not isinstance(val, bool):
        try:
            return (EXCEL_EPOCH + timedelta(days=val)).strftime("%Y-%m-%d")
        except (OverflowError, ValueError):
            pass
    return str(val)


def normalize_cell(val: object, fmt: str = "", coerce: bool = False) -> str:
    if val is None:
        return ""
    # 百分比格式：按 Excel 显示语义渲染（0.15 → 15%）
    if (
        isinstance(val, int | float)
        and not isinstance(val, bool)
        and fmt
        and "%" in fmt
    ):
        return f"{val * 100:g}%"
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    s = excel_serial_to_date(val) if coerce else str(val)
    return s.strip() if isinstance(s, str) else str(s)


def _coerced_columns(all_rows: list[list[object]]) -> set[int]:
    """列级判定：≥2 个数值单元格且全部满足 30000 < val < 100000 才转换。

    一个反例（年份、小整数编码等）即否决整列。datetime 不参与统计。
    """
    numeric: dict[int, list[float]] = {}
    for r in all_rows:
        for c, v in enumerate(r):
            if isinstance(v, int | float) and not isinstance(v, bool):
                numeric.setdefault(c, []).append(v)
    return {
        c for c, vals in numeric.items()
        if len(vals) >= 2 and all(30000 < v < 100000 for v in vals)
    }


def read_sheet_data(ws, max_rows: int = 20000, date_coerce: bool = True):
    """读取 sheet，传播合并值，展平双行表头。返回 (headers, rows)。

    date_coerce=False 时数值单元格永不转日期（datetime 分支不受影响）。
    合并单元格传播值 + 左上角 number_format；尾部全空列裁剪（前导空列保留）。
    """
    merged_ranges = list(ws.merged_cells.ranges)

    merge_values: dict[tuple[int, int], object] = {}
    merge_formats: dict[tuple[int, int], str] = {}
    for mr in merged_ranges:
        tl = ws.cell(mr.min_row, mr.min_col)
        for r in range(mr.min_row, mr.max_row + 1):
            for c in range(mr.min_col, mr.max_col + 1):
                merge_values[(r, c)] = tl.value
                merge_formats[(r, c)] = tl.number_format or ""

    raw_rows: list[list[object]] = []
    fmt_rows: list[list[str]] = []
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, max_rows), values_only=False):
        values = []
        formats = []
        for cell in row:
            pos = (cell.row, cell.column)
            values.append(merge_values.get(pos, cell.value))
            formats.append(merge_formats.get(pos, cell.number_format or ""))
        if any(v is not None and v != "" for v in values):
            raw_rows.append(values)
            fmt_rows.append(formats)

    if not raw_rows:
        return [], []

    max_len = max(len(r) for r in raw_rows)
    for r, f in zip(raw_rows, fmt_rows, strict=True):
        while len(r) < max_len:
            r.append(None)
            f.append("")

    # 尾部全空列裁剪：找最后一个有值的列，截断其后所有列（前导空列不动）
    last_col = -1
    for r in raw_rows:
        for i in range(len(r) - 1, last_col, -1):
            if r[i] is not None and r[i] != "":
                last_col = i
                break
    if last_col < max_len - 1:
        for r, f in zip(raw_rows, fmt_rows, strict=True):
            del r[last_col + 1:]
            del f[last_col + 1:]

    coerce_cols = _coerced_columns(raw_rows) if date_coerce else set()
    all_rows: list[list[str]] = [
        [
            normalize_cell(v, fmt=f[ci], coerce=(ci in coerce_cols))
            for ci, v in enumerate(r)
        ]
        for r, f in zip(raw_rows, fmt_rows, strict=True)
    ]

    # 双行表头展平
    if len(all_rows) >= 2 and len(merged_ranges) > 0:
        row1_has_col_merge = any(
            mr.min_row == 1 and mr.max_row == 1 and mr.max_col > mr.min_col
            for mr in merged_ranges
        )
        if row1_has_col_merge:
            headers: list[str] = []
            for h1, h2 in zip(all_rows[0], all_rows[1], strict=False):
                headers.append(h2 if h2 else (h1 if h1 else ""))
            return headers, all_rows[2:]

    return all_rows[0], all_rows[1:]


def sheet_is_simple(headers: list[str], has_merge: bool) -> bool:
    non_empty = sum(1 for h in headers if h)
    return non_empty <= SIMPLE_MAX_COLS and not has_merge


def file_is_simple(xlsx_path: Path) -> bool:
    """文件级判定：所有 sheet 都简单 且 仅 1 个 visible sheet → True。"""
    wb = load_workbook(xlsx_path, data_only=True, read_only=False)
    visible_sheets = [
        ws for ws in wb.worksheets
        if getattr(ws, "state", "visible") == "visible"
    ]
    if len(visible_sheets) != 1:
        wb.close()
        return False

    headers, _ = read_sheet_data(visible_sheets[0])
    has_merge = len(list(visible_sheets[0].merged_cells.ranges)) > 0
    wb.close()
    return sheet_is_simple(headers, has_merge)


def collect_notes(ws) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """收集 sheet 的批注与 list 类数据验证。返回 (批注, 验证)。

    批注: [(cell_ref, text)]；验证: [(sqref, values_text)]。
    只导出 type=="list" 的验证；formula1 为显式引号列表时拆分逗号，否则记原始公式。
    """
    comments: list[tuple[str, str]] = []
    for row in ws.iter_rows():
        for cell in row:
            c = cell.comment
            if c is not None and c.text:
                text = c.text.strip().replace("\r\n", "\n").replace("\r", "\n")
                comments.append((cell.coordinate, text.replace("\n", " / ")))

    validations: list[tuple[str, str]] = []
    for dv in ws.data_validations.dataValidation:
        if dv.type != "list":
            continue
        f1 = (dv.formula1 or "").strip()
        if len(f1) >= 2 and f1[0] == '"' and f1[-1] == '"':
            values = ",".join(
                x.strip() for x in f1[1:-1].split(",") if x.strip()
            )
        else:
            values = f1
        if values:
            validations.append((str(dv.sqref), values))
    return comments, validations


def build_notes_lines(ws, multi_sheet: bool) -> list[str]:
    """批注/数据验证 → Markdown 行（两个 section）。无内容返回 []。

    多 sheet 时加 sheet 前缀（批注 `{sheet}!{cell}`，验证 `{sheet} {sqref}`）。
    """
    comments, validations = collect_notes(ws)
    if not comments and not validations:
        return []
    c_prefix = f"{ws.title}!" if multi_sheet else ""
    v_prefix = f"{ws.title} " if multi_sheet else ""
    lines: list[str] = []
    if comments:
        lines.append("## 批注\n")
        lines.extend(f"- {c_prefix}{cell}: {text}" for cell, text in comments)
    if validations:
        lines.append("## 数据验证\n")
        lines.extend(
            f"- {v_prefix}{sqref}: {values}" for sqref, values in validations
        )
    return lines


def write_csv(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


def _md_escape_cell(s: str) -> str:
    """MD 表格单元格转义：换行 → <br>（去掉 \\r），| → \\|。"""
    return s.replace("\r\n", "\n").replace("\r", "").replace("\n", "<br>").replace("|", "\\|")


def write_md(
    path: Path,
    title: str,
    headers: list[str],
    rows: list[list[str]],
    notes: list[str] | None = None,
    provenance_lines: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if provenance_lines:
        lines.append("<!--")
        lines.extend(provenance_lines)
        lines.append("-->")
        lines.append("")
    lines.append(f"# {title}\n")
    lines.append("| " + " | ".join(_md_escape_cell(h) for h in headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(_md_escape_cell(c) for c in row) + " |")
    if notes:
        lines.append("")
        lines.extend(notes)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _upsert_manifest(output_dir: Path, record: dict) -> None:
    """按 source_path 覆盖旧记录后追加（重跑幂等）。"""
    manifest = output_dir / MANIFEST_NAME
    records: list[dict] = []
    if manifest.exists():
        try:
            records = json.loads(manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            records = []
    records = [r for r in records if r.get("source_path") != record["source_path"]]
    records.append(record)
    manifest.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def process_file(src: Path, output_dir: Path, date_coerce: bool = True) -> str:
    """处理一个文件，返回产出的格式（'Markdown' / 'CSV' / 'skip'）。

    同时写/更新 {output_dir}/_manifest.json（provenance + fidelity，按 source_path 幂等）。
    """
    if src.suffix == ".docx":
        return "skip"

    xlsx = ensure_xlsx(src)
    if is_ole2(xlsx):
        return "skip"

    source_path = str(src.resolve())
    source_sha = file_sha256(src)
    source_size = src.stat().st_size
    extracted_at = datetime.now().isoformat(timespec="seconds")
    provenance_lines = [
        f"source_path: {source_path}",
        f"source_sha256: {source_sha}",
        f"extracted_at: {extracted_at}",
        f"extractor: convert_excel.py v{EXTRACTOR_VERSION}",
        "fidelity: "
        f"text={FIDELITY['text']}; structure={FIDELITY['structure']}; "
        f"notes: {FIDELITY['notes']}",
    ]
    artifacts: list[str] = []

    stem = src.stem
    simple = file_is_simple(xlsx)

    wb = load_workbook(xlsx, data_only=True, read_only=False)
    visible = [
        ws for ws in wb.worksheets
        if getattr(ws, "state", "visible") == "visible"
    ]

    if simple and len(visible) == 1:
        headers, rows = read_sheet_data(visible[0], date_coerce=date_coerce)
        if not headers:
            wb.close()
            return "skip"
        notes = build_notes_lines(visible[0], multi_sheet=False)
        md_path = output_dir / f"{stem}.md"
        write_md(
            md_path, stem, headers, rows, notes=notes,
            provenance_lines=provenance_lines,
        )
        artifacts.append(md_path.relative_to(output_dir).as_posix())
        wb.close()
        result = f"Markdown({sum(1 for h in headers if h)}c/{len(rows)}r)"
    else:
        # 复杂：每 sheet 一个 CSV
        csv_dir = output_dir / "csv"
        multi = len(visible) > 1
        for ws in visible:
            headers, rows = read_sheet_data(ws, date_coerce=date_coerce)
            if not headers:
                continue
            safe = ws.title.replace("/", "_").replace(" ", "_")
            name = f"{stem}_{safe}.csv" if multi else f"{stem}.csv"
            write_csv(csv_dir / name, headers, rows)
            artifacts.append(f"csv/{name}")
            notes = build_notes_lines(ws, multi_sheet=multi)
            if notes:
                sidecar = csv_dir / f"{name}.notes.md"
                sidecar.write_text("\n".join(notes) + "\n", encoding="utf-8")
                artifacts.append(f"csv/{name}.notes.md")
        wb.close()
        result = f"CSV({len(visible)}s)"

    _upsert_manifest(output_dir, {
        "source_path": source_path,
        "source_sha256": source_sha,
        "source_size": source_size,
        "extracted_at": extracted_at,
        "extractor": "convert_excel.py",
        "extractor_version": EXTRACTOR_VERSION,
        "artifacts": artifacts,
        "fidelity": dict(FIDELITY),
    })
    return result


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--no-date-coerce"]
    date_coerce = len(args) == len(sys.argv) - 1
    if len(args) < 2:
        print(f"用法: {sys.argv[0]} <input_dir> <output_dir> [--no-date-coerce]")
        return 1

    input_dir = Path(args[0])
    output_dir = Path(args[1])
    output_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(
        f for f in os.listdir(input_dir)
        if f.endswith((".xlsx", ".xls"))
    )
    print(f"处理 {len(files)} 个 Excel 文件...\n")

    for filename in files:
        result = process_file(input_dir / filename, output_dir, date_coerce=date_coerce)
        symbol = "✓" if result != "skip" else "⊘"
        print(f"  {symbol} {filename}: {result}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
