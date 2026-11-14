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
  - 表头错位自动扫描（默认开）：row1 稀疏(<0.4)时在前 ≤5 行找首个占比 >0.6 且
    提升 ≥0.2 的行作真实表头；之前行进「前言区」（CSV → .notes.md 顶部，MD →
    引用块），永不丢弃。`--header-row N` 显式指定，`--no-header-scan` 关闭
  - Excel 序列号日期 → ISO 字符串（列级判定：仅当该列 ≥2 个数值单元格且全部
    落在 30000<val<100000（约 1982–2173 年）时才整列转换；单个数值/年份/编码
    不再被误转。可用 --no-date-coerce 完全关闭数值转换）
  - 百分比格式（number_format 含 %）→ Excel 显示值（0.15 → 15%）
  - 批注 / list 类数据验证导出（CSV 路径 → 同名 .csv.notes.md 边车；MD 路径 → 追加文末）
  - 尾部全空列裁剪（不做前导空列裁剪）
  - 溯源：每次转换写 {output_dir}/_manifest.json（source 路径/sha256/时间/extractor
    版本/产物清单/fidelity + 指纹字段 options/outputs/backend/fingerprint_format）；
    MD 产物文首附 <!-- provenance --> 注释块（CSV 无内联头，由 manifest 覆盖）
  - MD 表格单元格转义：换行 → <br>，| → 转义竖线（CSV 路径由 csv 模块原生引号处理）
  - .xls / 误标 .xlsx（OLE2）自动用 libreoffice 转换

增量重跑与守卫（harden-material-import-provenance）：
  - 指纹七态状态机与模式×状态矩阵见 scripts/_fingerprint.py（唯一权威）。
  - `--check`：只读状态检查（含路由变化 orphan-outputs 盘点 + needs_recheck
    清单），零业务写入；.xls 且 soffice 不可得 → 该项 backend-unavailable。
  - `--skip-up-to-date`：up-to-date 跳过；unknown 且已有输出 → 保留并报告需
    显式重转；output-modified/conflict 任何模式不静默覆盖。
  - `--force-overwrite-modified`：覆盖已检出人工修改输出的唯一显式例外。
  - manifest 预写检查（D8）：任何输出写入前解析+结构校验目标 _manifest.json
    （不可解析 / 结构非法 / 同 source_path 冲突记录三分类失败）；失败 → 该目录
    全部失败、manifest 与已有输出字节原样保留、非零 rc；半成功（输出写而
    manifest 更新失败）显式报错并给修复指引。
  - 批量枚举跳过 basename `~$` 前缀的 Office 锁文件（列 skipped，不崩批量）。

退出码：0=完成；1=工具失败（manifest 损坏/冲突、写入失败等）；3=完成且有
发现（--check 检出非 up-to-date 状态；写模式存在被保护跳过/unknown 保留）。
"""

from __future__ import annotations

import csv
import functools
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import load_workbook

import _fingerprint

SIMPLE_MAX_COLS = 8
EXCEL_EPOCH = datetime(1899, 12, 30)
TEMP_CONVERT = Path("/tmp/opencode/excel-convert")
EXTRACTOR_VERSION = 3
MANIFEST_NAME = "_manifest.json"
# 指纹元数据格式版本（独立于 EXTRACTOR_VERSION，设计 D6）
FINGERPRINT_FORMAT = _fingerprint.FINGERPRINT_FORMAT
# 静态保真度说明（extractor 级预期，非逐文件分析）
FIDELITY = {
    "text": "high",
    "structure": (
        "high (grid preserved; comments/validations exported to "
        ".notes.md sidecars; percent rendered display-style)"
    ),
    "notes": (
        "date coercion is column-voted; --no-date-coerce to disable; "
        "header misalignment auto-scan (--header-row/--no-header-scan)"
    ),
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class ManifestError(Exception):
    """manifest 预写检查失败（D8 三分类 + 写入失败）。

    kind ∈ unparseable / unreadable / invalid-structure / manifest-conflict /
    write-failed
    """

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


class ConversionFailure(Exception):
    """多输出转换部分写入失败的结构化报告（修复 7）。

    不强求事务、不宣称回滚；半成品文件不删除。report 字段：
    {source, stage: write|hash|manifest, error, written_paths（已确认写完的）,
    possibly_affected（该源全部预期输出——首写即败也不能凭成功计数宣称零影响）,
    manifest_updated, recovery}
    """

    def __init__(self, report: dict):
        super().__init__(str(report.get("error", "")))
        self.report = report


@functools.lru_cache(maxsize=1)
def _soffice_version() -> str | None:
    """libreoffice 版本字符串；不可得时 None（不猜测）。"""
    try:
        proc = subprocess.run(
            ["soffice", "--version"], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    lines = (proc.stdout or proc.stderr or "").strip().splitlines()
    return lines[0].strip() if lines else None


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


def _row_ratio(r: list[object]) -> float:
    """非空单元格 / 行宽（用于表头启发式）。"""
    if not r:
        return 0.0
    return sum(1 for v in r if v is not None and v != "") / len(r)


def _trim_trailing(raw_rows: list[list[object]], fmt_rows: list[list[str]]) -> None:
    """尾部全空列裁剪：找最后一个有值的列，截断其后所有列（前导空列不动）。"""
    last_col = -1
    for r in raw_rows:
        for i in range(len(r) - 1, last_col, -1):
            if r[i] is not None and r[i] != "":
                last_col = i
                break
    if last_col < len(raw_rows[0]) - 1:
        for r, f in zip(raw_rows, fmt_rows, strict=True):
            del r[last_col + 1:]
            del f[last_col + 1:]


def _detect_preface(
    raw_rows: list[list[object]],
    header_row: int | None,
    header_scan: bool,
) -> int:
    """返回表头行索引（0-based）；无前言返回 0。

    显式 header_row（1-based）优先；否则启发式扫描前 ≤5 行：
    row1 占比 <0.4 时，找第一个占比 >0.6 且相对上一行提升 ≥0.2 的行。
    """
    if header_row is not None:
        if 1 <= header_row <= len(raw_rows):
            return header_row - 1
        return 0  # 越界 → 回退旧行为
    if not header_scan or len(raw_rows) < 2:
        return 0
    first_ratio = _row_ratio(raw_rows[0])
    if first_ratio >= 0.4:
        return 0
    prev = first_ratio
    for i in range(1, min(5, len(raw_rows))):
        r = _row_ratio(raw_rows[i])
        if r > 0.6 and r - prev >= 0.2:
            return i
        prev = r
    return 0


def read_sheet_data(
    ws,
    max_rows: int = 20000,
    date_coerce: bool = True,
    header_row: int | None = None,
    header_scan: bool = True,
):
    """读取 sheet，传播合并值，展平双行表头。返回 (headers, rows, preface)。

    date_coerce=False 时数值单元格永不转日期（datetime 分支不受影响）。
    合并单元格传播值 + 左上角 number_format；尾部全空列裁剪（前导空列保留）。
    header_row=None + header_scan=True 时自动检测前言区（标题/状态行），
    真实表头行之前的行作为 preface 返回（前言不参与列统计，永不丢弃）。
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
        return [], [], []

    max_len = max(len(r) for r in raw_rows)
    for r, f in zip(raw_rows, fmt_rows, strict=True):
        while len(r) < max_len:
            r.append(None)
            f.append("")

    # 尾部全空列裁剪（先做一次，让表头启发式的行宽有意义）
    _trim_trailing(raw_rows, fmt_rows)

    # 前言区检测（显式 --header-row 优先于自动扫描）
    hidx = _detect_preface(raw_rows, header_row, header_scan)
    preface_raw = raw_rows[:hidx]
    preface_fmt = fmt_rows[:hidx]
    raw_rows = raw_rows[hidx:]
    fmt_rows = fmt_rows[hidx:]
    if hidx:
        # 剥离后按剩余网格重裁（列统计只看正文区）
        _trim_trailing(raw_rows, fmt_rows)

    # 前言区不参与日期强转统计
    preface = [
        " ".join(
            t for t in (
                normalize_cell(v, fmt=f[ci], coerce=False)
                for ci, v in enumerate(r)
            ) if t
        )
        for r, f in zip(preface_raw, preface_fmt, strict=True)
    ]

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
            return headers, all_rows[2:], preface

    return all_rows[0], all_rows[1:], preface


def sheet_is_simple(headers: list[str], has_merge: bool) -> bool:
    non_empty = sum(1 for h in headers if h)
    return non_empty <= SIMPLE_MAX_COLS and not has_merge


def file_is_simple(
    xlsx_path: Path,
    header_row: int | None = None,
    header_scan: bool = True,
) -> bool:
    """文件级判定：所有 sheet 都简单 且 仅 1 个 visible sheet → True。"""
    wb = load_workbook(xlsx_path, data_only=True, read_only=False)
    visible_sheets = [
        ws for ws in wb.worksheets
        if getattr(ws, "state", "visible") == "visible"
    ]
    if len(visible_sheets) != 1:
        wb.close()
        return False

    headers, _, _ = read_sheet_data(
        visible_sheets[0], header_row=header_row, header_scan=header_scan
    )
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


def build_notes_lines(
    ws,
    multi_sheet: bool,
    preface: list[str] | None = None,
) -> list[str]:
    """前言区/批注/数据验证 → Markdown 行。无内容返回 []。

    前言区放最前（表头扫描剥离的标题/状态行，永不丢弃）。
    多 sheet 时加 sheet 前缀（批注 `{sheet}!{cell}`，验证 `{sheet} {sqref}`）。
    """
    comments, validations = collect_notes(ws)
    if not comments and not validations and not preface:
        return []
    c_prefix = f"{ws.title}!" if multi_sheet else ""
    v_prefix = f"{ws.title} " if multi_sheet else ""
    lines: list[str] = []
    if preface:
        lines.append("## 前言区\n")
        lines.extend(f"- {t}" for t in preface if t)
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
    """MD 表格单元格转义：换行 → <br>（去掉 \\\\r），| → \\\\|。"""
    return s.replace("\r\n", "\n").replace("\r", "").replace("\n", "<br>").replace("|", "\\|")


def write_md(
    path: Path,
    title: str,
    headers: list[str],
    rows: list[list[str]],
    notes: list[str] | None = None,
    provenance_lines: list[str] | None = None,
    preface: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if provenance_lines:
        lines.append("<!--")
        lines.extend(provenance_lines)
        lines.append("-->")
        lines.append("")
    lines.append(f"# {title}\n")
    if preface:
        lines.extend(f"> {t}" for t in preface if t)
        lines.append("")
    lines.append("| " + " | ".join(_md_escape_cell(h) for h in headers) + " |")
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        lines.append("| " + " | ".join(_md_escape_cell(c) for c in row) + " |")
    if notes:
        lines.append("")
        lines.extend(notes)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ─── manifest 预写检查（设计 D8）───────────────────────────────────


def _validate_manifest_records(records: object) -> list[dict]:
    """结构校验 + 同 source_path 重复去重/冲突检测。失败 raise ManifestError。"""
    if not isinstance(records, list):
        raise ManifestError(
            "invalid-structure", f"manifest 顶层不是记录数组: {type(records).__name__}"
        )
    seen: dict[str, dict] = {}
    out: list[dict] = []
    for r in records:
        if not isinstance(r, dict) or "source_path" not in r:
            raise ManifestError(
                "invalid-structure", f"记录缺必需键 source_path 或非对象: {r!r:.200}"
            )
        sp = r["source_path"]
        if sp in seen:
            if seen[sp] != r:
                raise ManifestError(
                    "manifest-conflict",
                    f"同 source_path 重复且内容冲突的既有记录: {sp}",
                )
            continue  # 完全相同的重复条目 → 静默去重
        seen[sp] = r
        out.append(r)
    return out


def _load_manifest(output_dir: Path) -> list[dict]:
    """解析+结构校验目标 _manifest.json（预写检查）。失败 raise ManifestError。

    不存在 → []（首转）。
    """
    manifest = output_dir / MANIFEST_NAME
    if not manifest.exists():
        return []
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ManifestError("unparseable", str(exc)) from exc
    except OSError as exc:
        raise ManifestError("unreadable", str(exc)) from exc
    return _validate_manifest_records(data)


def _upsert_manifest(output_dir: Path, record: dict) -> None:
    """按 source_path 覆盖旧记录后追加（重跑幂等）。

    写入前先做与预写检查相同的解析+结构校验；任何失败上抛 ManifestError，
    不再静默清空历史记录。
    """
    records = _load_manifest(output_dir)
    records = [r for r in records if r.get("source_path") != record["source_path"]]
    records.append(record)
    manifest = output_dir / MANIFEST_NAME
    try:
        manifest.write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    except OSError as exc:
        raise ManifestError(
            "write-failed",
            f"输出可能已写而 manifest 更新失败（半成功状态，不可接受）— "
            f"修复指引: 解决 {exc} 后重跑以重建 manifest，或人工核对 {manifest} "
            f"与目录内产物后修复该文件",
        ) from exc


def _find_record(records: list[dict], source_path: str) -> dict | None:
    for r in records:
        if r.get("source_path") == source_path:
            return r
    return None


def _safe_output_path(output_dir: Path, rel: object) -> Path | None:
    """manifest 记录中的相对输出路径 → 绝对路径；越界/非法 → None。"""
    if not isinstance(rel, str) or not rel:
        return None
    if rel.startswith("/") or rel.startswith("\\") or ".." in rel.replace("\\", "/").split("/"):
        return None
    return output_dir / rel


def _disk_stem_family(output_dir: Path, stem: str) -> set[str]:
    """磁盘上属本源 stem 家族的输出文件（相对 output_dir posix 路径）。

    家族：{stem}.md、csv/{stem}.csv、csv/{stem}_*.csv 及其 .notes.md 边车。
    精确字符串匹配（不用 glob，stem 可含 [] 等特殊字符）；只盘点存在文件。
    """
    family: set[str] = set()
    if (output_dir / f"{stem}.md").is_file():
        family.add(f"{stem}.md")
    csv_dir = output_dir / "csv"
    if csv_dir.is_dir():
        single = f"{stem}.csv"
        under = stem + "_"
        for name in os.listdir(csv_dir):
            is_family = (
                name == single
                or name == single + ".notes.md"
                or (
                    name.startswith(under)
                    and (name.endswith(".csv") or name.endswith(".csv.notes.md"))
                )
            )
            if is_family and (csv_dir / name).is_file():
                family.add(f"csv/{name}")
    return family


# ─── 指纹评估 ──────────────────────────────────────────────────────


def _options_snapshot(
    date_coerce: bool, header_row: int | None, header_scan: bool
) -> dict:
    return {
        "date_coerce": bool(date_coerce),
        "header_row": header_row,
        "header_scan": bool(header_scan),
    }


def _record_factors(record: dict) -> _fingerprint.RecordFactors:
    return _fingerprint.RecordFactors(
        source_sha256=record.get("source_sha256"),
        options=record.get("options"),
        converter_version=record.get("extractor_version"),
        outputs=record.get("outputs"),
        fingerprint_format=record.get("fingerprint_format"),
    )


def _observed_for(
    src: Path,
    output_dir: Path,
    record: dict,
    options: dict,
) -> tuple[_fingerprint.Observed, bool]:
    """当前观测 + 该源是否已有任何输出文件落盘（unknown 保留规则用）。

    has_existing_output = record outputs/artifacts 命中磁盘 ∪ 磁盘保守候选
    （stem 家族任一文件在磁盘，复用 _disk_stem_family）——修复 5：record 存在
    但 outputs/artifacts 缺失或为空（旧/不完整记录）时，若只按 record 推导，
    unknown 态会在 --skip-up-to-date 下走补齐语义覆盖磁盘上无指纹的旧产物。
    """
    existing: list[dict] = []
    has_output = False
    recorded = record.get("outputs") or []
    legacy = record.get("artifacts") or []
    checked: set[str] = set()
    for o in recorded + [{"path": a} for a in legacy]:
        rel = o.get("path")
        if not isinstance(rel, str) or rel in checked:
            continue
        checked.add(rel)
        p = _safe_output_path(output_dir, rel)
        if p is not None and p.is_file():
            has_output = True
            if isinstance(o.get("sha256"), str):
                existing.append({"path": rel, "sha256": file_sha256(p)})
    if not has_output and _disk_stem_family(output_dir, src.stem):
        has_output = True  # 磁盘保守候选命中：旧产物无指纹、修改不可检测
    return (
        _fingerprint.Observed(
            source_sha256=file_sha256(src),
            options=options,
            converter_version=EXTRACTOR_VERSION,
            existing_outputs=existing,
        ),
        has_output,
    )


# ─── 路由规划（纯读；供 process_file 写盘与 check_file 预期产物共用）──


def _collect_artifacts(
    xlsx: Path,
    src: Path,
    output_dir: Path,
    date_coerce: bool,
    header_row: int | None,
    header_scan: bool,
) -> tuple[str, list[dict], str]:
    """纯读：按当前路由计算产物数据。返回 (route, items, result_str)。

    items 每项 {kind: md|csv|notes, rel, ...payload}；不写任何文件。
    """
    stem = src.stem
    simple = file_is_simple(xlsx, header_row=header_row, header_scan=header_scan)

    wb = load_workbook(xlsx, data_only=True, read_only=False)
    visible = [
        ws for ws in wb.worksheets
        if getattr(ws, "state", "visible") == "visible"
    ]

    items: list[dict] = []
    if simple and len(visible) == 1:
        headers, rows, preface = read_sheet_data(
            visible[0], date_coerce=date_coerce,
            header_row=header_row, header_scan=header_scan,
        )
        if not headers:
            wb.close()
            return "md", items, ""
        notes = build_notes_lines(visible[0], multi_sheet=False)
        items.append({
            "kind": "md", "rel": f"{stem}.md", "title": stem,
            "headers": headers, "rows": rows, "notes": notes, "preface": preface,
        })
        wb.close()
        return (
            "md",
            items,
            f"Markdown({sum(1 for h in headers if h)}c/{len(rows)}r)",
        )

    # 复杂：每 sheet 一个 CSV（+ notes 边车）
    multi = len(visible) > 1
    for ws in visible:
        headers, rows, preface = read_sheet_data(
            ws, date_coerce=date_coerce,
            header_row=header_row, header_scan=header_scan,
        )
        if not headers:
            continue
        safe = ws.title.replace("/", "_").replace(" ", "_")
        name = f"{stem}_{safe}.csv" if multi else f"{stem}.csv"
        rel = f"csv/{name}"
        items.append({
            "kind": "csv", "rel": rel, "headers": headers, "rows": rows,
        })
        notes = build_notes_lines(ws, multi_sheet=multi, preface=preface)
        if notes:
            items.append({"kind": "notes", "rel": f"{rel}.notes.md", "notes": notes})
    wb.close()
    return "csv", items, f"CSV({len(visible)}s)"


# ─── 只读状态检查（--check）────────────────────────────────────────


def check_file(
    src: Path,
    output_dir: Path,
    date_coerce: bool = True,
    header_row: int | None = None,
    header_scan: bool = True,
) -> dict:
    """单文件只读状态检查（零业务写入）。

    返回 {file, state, missing_paths, modified_paths, orphans, needs_recheck,
    note}；orphan-outputs 只盘点永不删除；.xls 且 soffice 不可得 →
    backend-unavailable（不整体失败）。missing/modified 为叠加诊断（修复 6）：
    并存时主状态仍是 output-modified/conflict，两侧清单同时携带。
    """
    info: dict = {
        "file": src.name,
        "state": None,
        "missing_paths": [],
        "modified_paths": [],
        "orphans": [],
        "needs_recheck": False,
        "note": None,
    }
    try:
        records = _load_manifest(output_dir)
    except ManifestError as exc:
        info.update(state="manifest-invalid", note=str(exc), needs_recheck=True)
        return info

    record = _find_record(records, str(src.resolve()))
    if record is None:
        info.update(state="unknown", note="no manifest record", needs_recheck=True)
        return info

    options = _options_snapshot(date_coerce, header_row, header_scan)
    factors = _record_factors(record)
    detail = {"state": "unknown", "missing_paths": [], "modified_paths": []}
    if (
        factors.source_sha256 is None
        or factors.options is None
        or factors.outputs is None
        or factors.converter_version is None
    ):
        detail["state"] = "unknown"
        note = "旧记录缺指纹字段（options/outputs/version）"
    else:
        observed, _ = _observed_for(src, output_dir, record, options)
        detail = _fingerprint.evaluate_detail(factors, observed)
        note = detail["state"]
    state = detail["state"]

    # 路由预期（纯读）→ orphan-outputs 盘点
    expected: set[str] = set()
    needs_soffice = src.suffix == ".xls" or is_ole2(src)
    if needs_soffice and _soffice_version() is None:
        info.update(
            state="backend-unavailable",
            note="soffice 不可得，无法判定 .xls 路由（其余指纹检查照常）",
            needs_recheck=True,
        )
        return info
    try:
        xlsx = ensure_xlsx(src)
        if is_ole2(xlsx):
            info.update(
                state=state, note=f"{note}; route-check-failed: OLE2 转换失败",
                needs_recheck=True,
            )
            return info
        _route, items, _r = _collect_artifacts(
            xlsx, src, output_dir, date_coerce, header_row, header_scan
        )
        expected = {it["rel"] for it in items}
    except Exception as exc:  # 路由检查失败不掩盖已得状态
        info.update(
            state=state,
            note=f"{note}; route-check-failed: {type(exc).__name__}: {exc}",
            needs_recheck=True,
        )
        return info

    recorded_paths = {
        o.get("path") for o in (record.get("outputs") or []) if isinstance(o, dict)
    } or {a for a in (record.get("artifacts") or []) if isinstance(a, str)}
    orphans = [
        {"path": p, "origin": "manifest-recorded"}
        for p in sorted(recorded_paths - expected) if p
    ]
    # disk-untracked 口径：磁盘上属本源 stem 家族、既不在当前路由预期、也不在
    # 本目录 manifest 任何 record 的 outputs/artifacts 里的文件（"不在任何
    # record"是保守护栏——同 stem 异扩展名或他人产物不误报）。默认重转后
    # manifest 刷新不再列旧输出，此口径保证残留仍可盘点（tasks 2.6）。
    if expected:
        tracked: set[str] = set()
        for r in records:
            for o in (r.get("outputs") or []):
                if isinstance(o, dict) and isinstance(o.get("path"), str):
                    tracked.add(o["path"])
            for a in (r.get("artifacts") or []):
                if isinstance(a, str):
                    tracked.add(a)
        for rel in sorted(_disk_stem_family(output_dir, src.stem)):
            if rel not in expected and rel not in tracked:
                orphans.append({"path": rel, "origin": "disk-untracked"})
    info.update(
        state=state,
        note=note,
        orphans=orphans,
        missing_paths=detail.get("missing_paths", []),
        modified_paths=detail.get("modified_paths", []),
        needs_recheck=(state != "up-to-date") or bool(orphans),
    )
    return info


# ─── 转换入口 ──────────────────────────────────────────────────────


def process_file(
    src: Path,
    output_dir: Path,
    date_coerce: bool = True,
    header_row: int | None = None,
    header_scan: bool = True,
    mode: str = _fingerprint.MODE_DEFAULT,
    force_overwrite_modified: bool = False,
) -> str:
    """处理一个文件，返回产出的格式（'Markdown(...)' / 'CSV(...)' / 'skip(...)'）。

    同时写/更新 {output_dir}/_manifest.json（provenance + fidelity + 指纹字段，
    按 source_path 幂等）。header_row（1-based 显式表头行）/ header_scan
    （自动前言区检测）逐层透传。

    顺序（D8）：预检 manifest → 指纹状态评估 → （按矩阵）转换写输出 →
    upsert manifest（内部同样先校验）。任何输出写入之前 manifest 损坏 →
    ManifestError；输出写而 manifest 更新失败 → ManifestError（半成功显式报错）。
    """
    if src.suffix == ".docx":
        return "skip"

    # 预写检查：在本项目任何输出写入之前
    records = _load_manifest(output_dir)

    xlsx = ensure_xlsx(src)
    if is_ole2(xlsx):
        return "skip"

    source_path = str(src.resolve())
    record = _find_record(records, source_path)
    options = _options_snapshot(date_coerce, header_row, header_scan)

    if record is not None:
        factors = _record_factors(record)
        observed, has_output = _observed_for(src, output_dir, record, options)
        detail = _fingerprint.evaluate_detail(factors, observed)
        state = detail["state"]
        decision = _fingerprint.decide_action(
            state, mode,
            has_existing_output=has_output,
            force_overwrite_modified=force_overwrite_modified,
            missing_paths=detail["missing_paths"],
            modified_paths=detail["modified_paths"],
        )
        if decision.action == "skip":
            if decision.protected:
                print(
                    f"skip: {src.name} — {decision.note}", file=sys.stderr
                )
            return f"skip({decision.note})"
        if (
            force_overwrite_modified
            and state in (
                _fingerprint.STATE_OUTPUT_MODIFIED, _fingerprint.STATE_CONFLICT
            )
        ):
            covered = sorted(
                o.get("path", "")
                for o in (record.get("outputs") or [])
                if isinstance(o, dict)
            )
            print(
                "force-overwrite-modified: 覆盖已检出人工修改的输出: "
                + ", ".join(p for p in covered if p)
            )

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

    route, items, result = _collect_artifacts(
        xlsx, src, output_dir, date_coerce, header_row, header_scan
    )
    if route == "md" and not items:
        return "skip"  # 空 sheet → 旧语义：不写 manifest

    # 分阶段失败报告（修复 7）：不强求事务、不回滚；半成品如实列受影响面。
    expected_rels = [it["rel"] for it in items]

    def _fail(stage: str, exc: Exception, written: list[str]) -> ConversionFailure:
        recovery = {
            "write": (
                "重跑 convert_excel（默认模式）修复输出；manifest 未更新，"
                "指纹状态仍指向失败前"
            ),
            "hash": (
                "重跑 convert_excel（默认模式）重算输出指纹；manifest 未更新，"
                "指纹状态仍指向失败前"
            ),
            "manifest": (
                "输出已写而 manifest 未更新（半成功，不可接受状态）：解决 "
                "_manifest.json 写入问题后重跑以重建该源 record；期间不要手工"
                "编辑该源输出"
            ),
        }[stage]
        return ConversionFailure({
            "source": src.name,
            "stage": stage,
            "error": f"{type(exc).__name__}: {exc}",
            "written_paths": list(written),
            # 首写即败也不能凭"成功计数=0"宣称零影响——截断文件也可能存在
            "possibly_affected": list(expected_rels),
            "manifest_updated": False,
            "recovery": recovery,
        })

    artifacts: list[str] = []
    outputs_meta: list[dict] = []
    written: list[str] = []  # 已确认写完（write+hash 均成功）的输出
    for it in items:
        p = output_dir / it["rel"]
        try:
            if it["kind"] == "md":
                write_md(
                    p, it["title"], it["headers"], it["rows"], notes=it["notes"],
                    provenance_lines=provenance_lines, preface=it["preface"],
                )
            elif it["kind"] == "csv":
                write_csv(p, it["headers"], it["rows"])
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("\n".join(it["notes"]) + "\n", encoding="utf-8")
        except Exception as exc:
            raise _fail("write", exc, written) from exc
        try:
            sha = file_sha256(p)
            size = p.stat().st_size
        except Exception as exc:
            raise _fail("hash", exc, written) from exc
        written.append(it["rel"])
        artifacts.append(it["rel"])
        outputs_meta.append({"path": it["rel"], "sha256": sha, "bytes": size})

    try:
        _upsert_manifest(output_dir, {
            "source_path": source_path,
            "source_sha256": source_sha,
            "source_size": source_size,
            "extracted_at": extracted_at,
            "extractor": "convert_excel.py",
            "extractor_version": EXTRACTOR_VERSION,
            "artifacts": artifacts,
            "fidelity": dict(FIDELITY),
            "options": options,
            "outputs": outputs_meta,
            "backend": _soffice_version(),
            "fingerprint_format": FINGERPRINT_FORMAT,
        })
    except ManifestError as exc:
        print(
            f"ERROR: 半成功状态 — {src.name} 输出已写而 manifest 更新失败: {exc}",
            file=sys.stderr,
        )
        raise _fail("manifest", exc, written) from exc
    return result


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    positional: list[str] = []
    date_coerce = True
    header_scan = True
    header_row: int | None = None
    check_mode = False
    skip_mode = False
    force = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--no-date-coerce":
            date_coerce = False
        elif a == "--no-header-scan":
            header_scan = False
        elif a == "--header-row" and i + 1 < len(argv):
            i += 1
            header_row = int(argv[i])
        elif a.startswith("--header-row="):
            header_row = int(a.split("=", 1)[1])
        elif a == "--check":
            check_mode = True
        elif a == "--skip-up-to-date":
            skip_mode = True
        elif a == "--force-overwrite-modified":
            force = True
        else:
            positional.append(a)
        i += 1

    if len(positional) < 2:
        print(
            f"用法: {sys.argv[0]} <input_dir> <output_dir> "
            "[--no-date-coerce] [--header-row N] [--no-header-scan] "
            "[--check] [--skip-up-to-date] [--force-overwrite-modified]\n"
            "  旗标互斥: --check / --skip-up-to-date / --force-overwrite-modified "
            "不可组合使用"
        )
        return 1
    if skip_mode and force:
        print(
            "error: --skip-up-to-date 与 --force-overwrite-modified 不支持组合使用；"
            "请用默认转换模式 + --force-overwrite-modified",
            file=sys.stderr,
        )
        return 2
    if check_mode and (skip_mode or force):
        print(
            "error: --check 与 --skip-up-to-date/--force-overwrite-modified 互斥",
            file=sys.stderr,
        )
        return 2
    mode = (
        _fingerprint.MODE_CHECK if check_mode
        else (_fingerprint.MODE_SKIP_UP_TO_DATE if skip_mode
              else _fingerprint.MODE_DEFAULT)
    )

    input_dir = Path(positional[0])
    output_dir = Path(positional[1])

    files = sorted(
        f for f in os.listdir(input_dir)
        if f.endswith((".xlsx", ".xls"))
    )
    # Office 锁文件守卫（D5 输入侧）：在 openpyxl/libreoffice 调用之前列 skipped
    lock_files = [f for f in files if f.startswith("~$")]
    files = [f for f in files if not f.startswith("~$")]
    for f in lock_files:
        print(f"  ⊘ {f}: skipped (office lock file)")
    print(f"处理 {len(files)} 个 Excel 文件...\n")

    if mode == _fingerprint.MODE_CHECK:
        # --check：零业务写入（不 mkdir output_dir）
        needs_recheck: list[str] = []
        errors = 0
        for filename in files:
            try:
                info = check_file(
                    input_dir / filename, output_dir,
                    date_coerce=date_coerce, header_row=header_row,
                    header_scan=header_scan,
                )
            except Exception as exc:
                errors += 1
                print(f"  ✗ {filename}: check-error: {type(exc).__name__}: {exc}")
                continue
            symbol = "✓" if not info["needs_recheck"] else "⊘"
            line = f"  {symbol} {filename}: {info['state']}"
            if info.get("note") and info["note"] != info["state"]:
                line += f" ({info['note']})"
            if info["orphans"]:
                line += " | orphan-outputs: " + ", ".join(
                    f"{o['path']} ({o['origin']})" for o in info["orphans"]
                )
            if info.get("missing_paths"):
                line += " | missing: " + ", ".join(info["missing_paths"])
            if info.get("modified_paths"):
                line += " | modified: " + ", ".join(info["modified_paths"])
            print(line)
            if info["needs_recheck"]:
                needs_recheck.append(str((input_dir / filename).resolve()))
                needs_recheck.extend(
                    str((output_dir / o["path"]).resolve())
                    for o in info["orphans"]
                )
        if errors:
            print(f"\n{errors} 个文件检查失败（工具错误）")
            return 1
        if needs_recheck:
            print("\nneeds_recheck（仅路径引用；不自动删除/不改写人工 needs_review）:")
            for p in sorted(set(needs_recheck)):
                print(f"  - {p}")
            return 3
        print("\n全部 up-to-date")
        return 0

    # 写模式（default / skip-up-to-date）
    output_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    findings: list[str] = []
    for filename in files:
        try:
            result = process_file(
                input_dir / filename, output_dir,
                date_coerce=date_coerce, header_row=header_row,
                header_scan=header_scan, mode=mode,
                force_overwrite_modified=force,
            )
        except ManifestError as exc:
            failures.append(filename)
            print(f"  ✗ {filename}: manifest 预写检查失败 — {exc}", file=sys.stderr)
            print(f"  ✗ {filename}: manifest failure ({exc.kind})")
            continue
        except ConversionFailure as exc:
            failures.append(filename)
            rpt = exc.report
            print(
                f"  ✗ {filename}: stage={rpt['stage']} {rpt['error']} | "
                f"written={rpt['written_paths']} | "
                f"possibly_affected={rpt['possibly_affected']} | "
                f"manifest_updated={rpt['manifest_updated']}",
                file=sys.stderr,
            )
            print(
                f"  ✗ {filename}: 失败阶段={rpt['stage']}；"
                f"可能受影响={len(rpt['possibly_affected'])} 个输出；"
                f"修复: {rpt['recovery']}"
            )
            continue
        except Exception as exc:
            failures.append(filename)
            print(f"  ✗ {filename}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        symbol = "✓" if not result.startswith("skip") else "⊘"
        if result.startswith("skip") and result != "skip":
            # skip(<原因>) — up-to-date 跳过不算发现，其余算
            if "up-to-date" not in result:
                findings.append(filename)
        print(f"  {symbol} {filename}: {result}")

    if failures:
        print(f"\n失败汇总（{len(failures)} 个）: {', '.join(failures)}", file=sys.stderr)
        print(
            f"\n失败汇总: {len(failures)} 个（manifest 预写失败项：manifest 未被改动、"
            "已有输出字节不变；转换中断项：半成品不删除不回滚，受影响面见 possibly_affected）"
        )
        return 1
    if findings:
        print(f"\n发现需注意项（{len(findings)} 个）: {', '.join(findings)}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
