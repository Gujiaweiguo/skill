#!/usr/bin/env python3
"""provenance_inventory — 只读溯源体检（harden-material-import-provenance Lane A）。

设计依据：openspec/changes/harden-material-import-provenance/design.md
D1（独立纯读脚本）/ D5（投影侧候选线索与抽样口径）/ D7（回填 provenance 兼容读取与
recorded-at-conversion 三要件）/ D10（三维分维表达）/ D11（多公司基座隔离）。

事实纪律（design「事实纪律」节）：
- 观察.observed / 声明.declared / 推断.inferred / 不可得.unknown-unavailable 四类
  信息不得互相冒充；路径/文件名推断永不升级为已验证身份（即便候选唯一）。
- NUL 计数口径显式：默认抽样前 64 KiB，报 sampled_bytes / sample_nul_count /
  nul_scope（"sample"|"full"，full 仅当实际读满全文件），绝不冒充全文件计数。
- 文件名中部 `~$` 只是无效投影候选线索（garbage-candidate），不拦截不定罪不删除。
- 扫描不完整（不可访问目录）显式上报，绝不静默跳过（os.walk onerror 模式，
  参考 scan_raw_index.ScanFailure）。

来源观察异常三分类矩阵（三者互斥；OSError 绝不冒充 boundary-violation 或 missing）：
- boundary      = resolve **成功**且解析结果落在基座外（绝对路径越界/符号链接
                  跨公司）→ boundary_violations 节，停止验证，不读目标；
- unresolvable /
  permission-denied /
  inaccessible  = 观察动作自身失败（resolve/stat/read 抛 OSError，reason 带
                  errno 号+errno 名）：EACCES/EPERM → permission-denied，
                  其余（ENAMETOOLONG/ELOOP/…）→ inaccessible → 单列
                  unverifiable_sources 节，计入发现；
- missing       = 观察成功且目标不存在 → gaps.missing_original。
「无法观察」≠「不存在」≠「越界」，任何一项都不得冒充另一项。

零业务写入：本工具不写任何 docs 基座文件；报告写 stdout 或显式 --report 路径。

用法:
  python provenance_inventory.py [--base ABS_PATH] [--report PATH]
                                 [--full-hash] [--repair-candidates]
                                 [--sample-bytes N]

退出码: 0=完成无缺口 / 1=工具失败 / 2=用法错误 / 3=完成且有发现。
纯 stdlib；不要求 OCR/libreoffice（后端不可用只影响依赖项，本工具无依赖项）。
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _company_base import resolve_company_base  # noqa: E402

TOOL = "provenance_inventory"
DEFAULT_SAMPLE_BYTES = 65536

# 原件树枚举排除（语义对齐 backfill_source.EXCLUDED_ROOT_DIRS / SKIP_DIR_NAMES）
EXCLUDED_ROOT_DIRS = {"raw", "materials", "out", ".git"}
SKIP_DIR_NAMES = {"_media", "__pycache__", ".venv", "node_modules",
                  ".playwright-mcp", "parsed", "images", "_extracted"}

# raw md 文首 provenance 字段——两种形态：
# ① 行内形态（convert_doc / backfill_source）：每行独立 <!-- source: ... --> 注释
# ② 块形态（convert_excel）：单个多行 <!--\nsource_path: ...\nextractor: ...\n--> 注释块
INLINE_SOURCE_RE = re.compile(r"<!--\s*source:\s*(.*?)\s*-->")
INLINE_SOURCE_PATH_RE = re.compile(r"<!--\s*source_path:\s*(.*?)\s*-->")
INLINE_SHA_RE = re.compile(r"<!--\s*(?:source_sha256|source_sha256_at_backfill)"
                           r":\s*([0-9a-fA-F]+)\s*-->")
INLINE_SIGNATURE_RE = re.compile(
    r"<!--\s*(?:extracted_by|extractor):\s*(.*?)\s*-->")
COMMENT_BLOCK_RE = re.compile(r"<!--\s*\n?(.*?)-->", re.S)
BLOCK_SOURCE_RE = re.compile(r"(?m)^[ \t]*(?:source|source_path)[ \t]*:"
                             r"[ \t]*(.*?)[ \t]*$")
BLOCK_SHA_RE = re.compile(r"(?m)^[ \t]*(?:source_sha256|source_sha256_at_backfill)"
                          r"[ \t]*:[ \t]*([0-9a-fA-F]+)[ \t]*$")
BLOCK_SIGNATURE_RE = re.compile(r"(?m)^[ \t]*(?:extracted_by|extractor)"
                                r"[ \t]*:[ \t]*(.*?)[ \t]*$")
CONVERTER_SIGNATURE_RE = re.compile(r"convert_(?:doc|excel)\.py v\d")
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# materials frontmatter
FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.S)
FM_SOURCE_RE = re.compile(r"(?m)^\s*source\s*:\s*(.*?)\s*$")

MID_TILDE_DOLLAR_RE = re.compile(r"^.+~\$.+")  # basename 中部含 ~$（非前缀）


class ScanFailure:
    """一次扫描中无法访问的位置（目录不可进入 / 文件不可读）。"""

    def __init__(self, location: str, message: str):
        self.location = location
        self.message = message

    def __str__(self) -> str:
        return f"{self.location}: {self.message}"


# ---------------------------------------------------------------------------
# 基座解析
# ---------------------------------------------------------------------------

def resolve_base(arg_base: str | None) -> Path:
    """--base 显式路径走与 resolver 相同校验；否则复用 resolver（无静默默认）。"""
    if arg_base is None:
        return resolve_company_base()
    path = Path(arg_base)
    if not path.is_absolute():
        sys.exit(f"错误: --base 必须是绝对路径（当前: {arg_base}）。")
    if not (path / "config" / "company.yaml").is_file():
        sys.exit(
            f"错误: {path} 不是已注册公司（缺 config/company.yaml）。\n"
            "  新公司请在 docs 仓库运行 scripts/onboard.sh company <slug> 创建。"
        )
    return path


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_sample(path: Path, sample_bytes: int) -> tuple[bytes, str]:
    """读前 sample_bytes 字节；文件更小则整读。返回 (data, nul_scope)。"""
    with open(path, "rb") as fh:
        data = fh.read(sample_bytes)
    scope = "full" if len(data) < sample_bytes else "sample"
    return data, scope


def detect_encoding_invalid(data: bytes, sample_bytes: int,
                            file_size: int) -> dict | None:
    """UTF-8 严格解码探测。抽样截断多字节字符（错误位于样本末尾且文件更大）时
    视为不可判定，不误报。"""
    try:
        data.decode("utf-8")
        return None
    except UnicodeDecodeError as e:
        if (file_size > sample_bytes and len(data) - e.start <= 4):
            return None  # 截断边界，不可判定
        return {"encoding_invalid": True, "error_offset": e.start,
                "reason": e.reason}


def parse_raw_md_provenance(text_head: str) -> dict:
    """解析 raw md 文首 provenance（行内 `<!-- source: ... -->` 与 convert_excel 的
    块形态 `<!--\\nsource_path: ...\\nextractor: ...\\n-->` 均接受）。

    - 声明来源：`source:` 与 `source_path:` 都认，两者都在时取**先出现**的；
      `declared_via` 保留命中字段名便于审计。
    - 签名载体：`extracted_by:` 与 `extractor:` 进同一分类通道。
    - 哈希：`source_sha256` / `source_sha256_at_backfill`（旧/新名均可）。
    """
    out: dict = {"source": None, "declared_via": None,
                 "source_sha256": None, "extracted_by": None,
                 "signature_via": None}
    source_hits: list[tuple[int, str, str]] = []  # (位置, 值, 字段名)

    for regex, via in ((INLINE_SOURCE_RE, "source"),
                       (INLINE_SOURCE_PATH_RE, "source_path")):
        m = regex.search(text_head)
        if m:
            source_hits.append((m.start(), m.group(1).strip(), via))
    m = INLINE_SHA_RE.search(text_head)
    if m:
        out["source_sha256"] = m.group(1).lower()
    m = INLINE_SIGNATURE_RE.search(text_head)
    if m:
        out["extracted_by"] = m.group(1).strip()
        out["signature_via"] = m.lastgroup or "inline"

    # 块形态（convert_excel 单注释块，字段逐行）
    bm = COMMENT_BLOCK_RE.search(text_head[:2000])
    if bm:
        content = bm.group(1)
        for fm in BLOCK_SOURCE_RE.finditer(content):
            via = "source_path" if fm.group(0).lstrip().startswith(
                "source_path") else "source"
            source_hits.append((bm.start() + fm.start(),
                                fm.group(1).strip(), via))
        fm = BLOCK_SHA_RE.search(content)
        if fm and out["source_sha256"] is None:
            out["source_sha256"] = fm.group(1).lower()
        fm = BLOCK_SIGNATURE_RE.search(content)
        if fm and out["extracted_by"] is None:
            out["extracted_by"] = fm.group(1).strip()
            out["signature_via"] = "block"

    if source_hits:
        # 去重（行内与块可能双命中同一值）后取先出现者
        seen: set[tuple[str, str]] = set()
        unique = [h for h in sorted(source_hits)
                  if (h[1], h[2]) not in seen and not seen.add((h[1], h[2]))]
        _pos, value, via = unique[0]
        out["source"] = value
        out["declared_via"] = via
    return out


def classify_provenance(prov: dict) -> dict:
    """D7 兼容读取分类。

    - extracted_by 含 backfilled → 回填性质（candidate-association，
      hash_semantics=at-backfill，无论字段旧名 source_sha256 还是新名）。
    - extracted_by 是转换器签名 且 来源可解析在基座内 且 哈希 64hex
      → recorded-at-conversion（仅证明存在转换时点来源声明，附语义限定说明；
      不要求当前原件哈希等于记录哈希——freshness 分维度）。
    - 裸 source_sha256 无签名无标记 → hash_semantics=unknown。
    任何情况下不因字段名相同而升级为转换时已验证。
    """
    extracted_by = prov.get("extracted_by") or ""
    has_hash = prov.get("source_sha256") is not None
    hash_format_ok = bool(HEX64_RE.match(prov.get("source_sha256") or ""))
    result = {"provenance_class": None, "hash_semantics": None}

    if "backfilled" in extracted_by.lower():
        result["provenance_class"] = "candidate-association"
        result["hash_semantics"] = "at-backfill"
        result["class_basis"] = "extracted_by 含 backfilled 标记（回填性质，保持不升级）"
        return result

    if (CONVERTER_SIGNATURE_RE.search(extracted_by) and prov.get("source")
            and has_hash and hash_format_ok):
        # 三要件中第②件（同基座内可解析来源）由调用方核验后回填 in_base；
        # 此处先给候选分类，越界时调用方撤销。
        result["_candidate_recorded_at_conversion"] = True

    if has_hash and not extracted_by:
        result["hash_semantics"] = "unknown"
        result["hash_semantics_basis"] = (
            "裸 source_sha256：既无转换器签名也无 backfilled 标记，哈希语义未知")
    return result


def resolve_declared_source(declared: str, base: Path) -> tuple[Path | None, str]:
    """声明来源按基座解析（跟随 symlink）。返回 (resolved, status)。

    分类矩阵（三者互斥，OSError 绝不冒充 boundary/missing）：
    - status="in-base"     ：resolve 成功且落在当前基座内，可继续验证；
    - status="boundary"    ：resolve **成功**且解析结果落在基座外（绝对路径越界
                             或符号链接跨公司）——调用方必须停止该来源验证，
                             绝不读取目标内容；
    - status="unresolvable"：resolve 自身抛 OSError（如 Errno 36 名字过长，
                             docs 基座已知故障家族，见 troubleshooting #15）
                             ——观察动作自身失败，非越界非缺失。
    """
    p = Path(declared)
    raw = p if p.is_absolute() else base / p
    try:
        resolved = raw.resolve()
    except OSError:
        return None, "unresolvable"
    try:
        resolved.relative_to(base)
        return resolved, "in-base"
    except ValueError:
        return resolved, "boundary"


def stat_error_detail(e: OSError) -> str:
    """观察失败的可审计描述：strerror + errno 号 + errno 名。"""
    name = errno.errorcode.get(e.errno, "UNKNOWN")
    return f"{e.strerror or e} (errno {e.errno} {name})"


def accessibility_for_error(e: OSError) -> str:
    """按 errno 给有依据的可访问性分类（不笼统 permission-denied）。

    EACCES/EPERM → permission-denied；其余（ENAMETOOLONG/ELOOP/…）→ inaccessible。
    """
    if e.errno in (errno.EACCES, errno.EPERM):
        return "permission-denied"
    return "inaccessible"


def safe_exists(p: Path) -> tuple[bool, OSError | None]:
    """exists() 的 OSError 防护。返回 (是否存在, 观察异常)。

    os.stat 在异常输入（超长文件名 Errno 36、ELOOP 等）上直接抛 OSError；
    观察失败不得 crash、不得冒充「不存在」（spec「不可访问范围如实上报」），
    由调用方按 accessibility_for_error 分类并进 unverifiable_sources。
    """
    try:
        return p.exists(), None
    except OSError as e:
        return False, e


def walk_with_errors(root: Path, root_filter=None, dir_filter=None):
    """os.walk + 显式 onerror（绝不静默跳过不可读目录）。

    root_filter(dirs, is_root) / dir_filter(dirs) 就地修改目录列表。
    返回 ([(dirpath, filenames)], failures)。
    """
    failures: list[ScanFailure] = []

    def _on_error(err: OSError) -> None:
        failures.append(ScanFailure(
            location=getattr(err, "filename", None) or str(root),
            message=err.strerror or str(err)))

    visited = []
    for cur, dirs, files in os.walk(root, onerror=_on_error):
        if root_filter and Path(cur) == root:
            root_filter(dirs)
        elif dir_filter:
            dir_filter(dirs)
        visited.append((cur, list(files)))
    return visited, failures


# ---------------------------------------------------------------------------
# 主体检逻辑（纯函数，可被测试直接调用）
# ---------------------------------------------------------------------------

def run_inventory(base: Path, *, full_hash: bool = False,
                  repair_candidates: bool = False,
                  sample_bytes: int = DEFAULT_SAMPLE_BYTES) -> dict:
    base = base.resolve()
    report: dict = {
        "tool": TOOL,
        "base": str(base),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan": {
            "scope": ["originals(whole-base excl. raw/materials/out/.git)",
                      "raw/**/*.md|*.csv|*.notes.md（仅文本投影）",
                      "raw/**/_manifest.json",
                      "materials/**/*.md"],
            "inaccessible": [],
            "not_scanned": [],
            "discovery_errors": [],
            "complete": True,
        },
        "items": {},
        "boundary_violations": [],
        "gaps": {
            "missing_source": [], "missing_hash": [], "missing_original": [],
            "ambiguous": [], "manifest_corrupt": [], "manifest_invalid": [],
            "manifest_conflict": [], "outputs_missing": [],
            "no_manifest_coverage": [],
        },
        "garbage_candidates": [],
        "invalid_projections": [],
        "hash_mismatches": [],
        "unverifiable_sources": [],
        "provenance_class_summary": {},
    }

    sha_cache: dict[Path, tuple[str | None, OSError | None]] = {}

    def sha_of(p: Path) -> tuple[str | None, OSError | None]:
        """读字节算 sha256；OSError 不吞——返回 (sha|None, 异常|None) 供调用方
        按 errno 分类表达为观察失败（绝不冒充 mismatch/missing）。"""
        if p not in sha_cache:
            try:
                sha_cache[p] = (sha256_bytes(p.read_bytes()), None)
            except OSError as e:
                sha_cache[p] = (None, e)
        return sha_cache[p]

    def note_gap(kind: str, rel: str, detail: dict | None = None):
        entry = {"path": rel}
        if detail:
            entry.update(detail)
        report["gaps"][kind].append(entry)

    def _note_unverifiable(rep: dict, rel: str, declared: str, reason: str,
                           field: str = "accessibility",
                           value: str = "inaccessible"):
        """观察不可得（resolve/stat/read 抛 OSError）→ 单列清单，计入发现（rc=3）。

        不冒充 missing（无法观察 ≠ 不存在），也不冒充 boundary（非越界）。
        field/value 指明写回条目的哪个可访问性字段（item 自身 or 来源侧）。
        """
        rep["items"].setdefault(rel, {})
        rep["items"][rel][field] = value
        rep["items"][rel]["note"] = reason
        rep["unverifiable_sources"].append({
            "path": rel, "declared_source": declared, "reason": reason})

    # ------------------------------------------------------------------
    # 1) 原件树（整基座枚举，排除投影/状态树）
    # ------------------------------------------------------------------
    originals_by_basename: dict[str, list[str]] = {}
    originals_by_stem: dict[str, list[str]] = {}
    original_items: list[dict] = []

    def _root_filter(dirs):
        dirs[:] = [d for d in dirs
                   if d not in EXCLUDED_ROOT_DIRS and not d.startswith(".")
                   and d not in SKIP_DIR_NAMES]

    def _dir_filter(dirs):
        dirs[:] = [d for d in dirs
                   if d not in SKIP_DIR_NAMES and not d.startswith(".")]

    visited, failures = walk_with_errors(base, _root_filter, _dir_filter)
    for f in failures:
        report["scan"]["inaccessible"].append(
            {"location": f.location, "message": f.message})
        report["scan"]["not_scanned"].append(
            {"location": f.location, "reason": "permission-denied/unavailable"})
        report["scan"]["discovery_errors"].append(str(f))
    for cur, files in visited:
        for fname in files:
            if fname.startswith(".") or fname.startswith("_"):
                continue
            p = Path(cur) / fname
            rel = p.relative_to(base).as_posix()
            item = {"path": rel, "kind": "original", "link_state": "observed",
                    "source_nature": None, "accessibility": "accessible",
                    "hash_check": "not-applicable"}
            if full_hash:
                h, h_err = sha_of(p)
                if h:
                    item["sha256"] = h
                elif h_err is not None:
                    item["accessibility"] = accessibility_for_error(h_err)
                    _note_unverifiable(report, rel, rel,
                                       f"full-hash 读取失败: "
                                       f"{stat_error_detail(h_err)}",
                                       value=accessibility_for_error(h_err))
            original_items.append(item)
            report["items"][rel] = item
            originals_by_basename.setdefault(fname.lower(), []).append(rel)
            originals_by_stem.setdefault(p.stem.lower(), []).append(rel)

    # ------------------------------------------------------------------
    # 2) raw/_index.json（inferred 来源线索；缺失/损坏 → not-scanned，非工具失败）
    # ------------------------------------------------------------------
    raw_dir = base / "raw"
    imported_from: dict[str, str] = {}
    index_rel = "raw/_index.json"
    if raw_dir.is_dir():
        index_path = raw_dir / "_index.json"
        if index_path.is_file():
            try:
                data = json.loads(index_path.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if isinstance(v, dict) and v.get("imported_from"):
                        imported_from[k] = str(v["imported_from"])
                report["items"][index_rel] = {
                    "path": index_rel, "kind": "index",
                    "link_state": "observed", "accessibility": "accessible",
                }
            except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
                report["items"][index_rel] = {
                    "path": index_rel, "kind": "index",
                    "accessibility": "not-scanned",
                    "note": f"_index.json 损坏，imported_from 推断线索不可用: {e}",
                }
                report["scan"]["not_scanned"].append(
                    {"location": index_rel, "reason": "index-corrupt"})
        else:
            report["scan"]["not_scanned"].append(
                {"location": index_rel, "reason": "index-missing"})

    # ------------------------------------------------------------------
    # 3) raw 树（md / csv / notes 边车 / manifest）
    # ------------------------------------------------------------------
    def _raw_dir_filter(dirs):
        dirs[:] = [d for d in dirs
                   if d not in SKIP_DIR_NAMES and not d.startswith(".")]

    raw_visited, raw_failures = walk_with_errors(raw_dir, _raw_dir_filter,
                                                 _raw_dir_filter)
    for f in raw_failures:
        report["scan"]["inaccessible"].append(
            {"location": f.location, "message": f.message})
        report["scan"]["not_scanned"].append(
            {"location": f.location, "reason": "permission-denied/unavailable"})
        report["scan"]["discovery_errors"].append(str(f))
    # _media 整树范围外标注（语义=范围外，≠无问题；不计入发现）
    report["scan"]["not_scanned"].append({
        "location": "raw/**/_media",
        "reason": "out-of-scope: 二进制媒体目录，非文本投影，未纳入体检"
                  "（范围外不等于无问题）"})

    # tasks 1.1：raw 侧只收 .md / .csv / .notes.md 三类文本投影；
    # 其他文件（jpeg/png/bin 等二进制，UTF-8 探测必然假阳性）不入收集，
    # _media 目录整树范围外（下方 scan.not_scanned 如实标注）。
    raw_files: list[tuple[Path, str]] = []      # (path, kind)
    manifest_paths: list[Path] = []
    for cur, files in raw_visited:
        for fname in files:
            if fname == "_index.json":
                continue
            p = Path(cur) / fname
            if fname == "_manifest.json":
                manifest_paths.append(p)
            elif fname.endswith(".notes.md"):
                raw_files.append((p, "raw-notes"))
            elif fname.endswith(".md"):
                raw_files.append((p, "raw-md"))
            elif fname.endswith(".csv"):
                raw_files.append((p, "raw-csv"))

    # manifest 预读（覆盖情况 + 三类发现）
    manifest_cover: dict[Path, dict] = {}   # dir -> parsed records
    for mp in manifest_paths:
        rel = mp.relative_to(base).as_posix()
        item = {"path": rel, "kind": "manifest", "accessibility": "accessible"}
        report["items"][rel] = item
        try:
            records = json.loads(mp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            item["status"] = "manifest-corrupt"
            item["detail"] = str(e)
            note_gap("manifest_corrupt", rel, {"reason": str(e)})
            continue
        if (not isinstance(records, list)
                or any(not isinstance(r, dict) or "source_path" not in r
                       for r in records)):
            item["status"] = "manifest-invalid"
            note_gap("manifest_invalid", rel, {
                "reason": "非记录数组/记录缺 source_path 键"})
            continue
        item["status"] = "ok"
        item["source_paths"] = [str(r.get("source_path")) for r in records]
        manifest_cover[mp.parent] = {"records": records, "rel_dir":
                                     mp.parent.relative_to(base).as_posix()}
        # 同 source_path 多条且内容冲突
        by_src: dict[str, list[dict]] = {}
        for r in records:
            by_src.setdefault(str(r.get("source_path")), []).append(r)
        for src, rs in by_src.items():
            if len(rs) > 1 and len({json.dumps(r, sort_keys=True,
                                                ensure_ascii=False)
                                    for r in rs}) > 1:
                item["status"] = "manifest-conflict"
                note_gap("manifest_conflict", rel, {"source_path": src})
        # outputs/artifacts 中列出的文件不存在 → outputs-missing
        listed: list[str] = []
        for r in records:
            for key in ("artifacts", "outputs"):
                vals = r.get(key) or []
                if isinstance(vals, list):
                    listed.extend(str(v) for v in vals)
                elif isinstance(vals, dict):
                    listed.extend(str(v) for v in vals.keys())
        for listed_rel in sorted(set(listed)):
            target = mp.parent / listed_rel
            ok, err = safe_exists(target)
            if err is not None:
                _note_unverifiable(
                    report,
                    (mp.parent / listed_rel).relative_to(base).as_posix(),
                    listed_rel,
                    f"manifest 列出文件 stat 失败: {stat_error_detail(err)}",
                    value=accessibility_for_error(err))
            elif not ok:
                note_gap("outputs_missing",
                         (mp.parent / listed_rel).relative_to(base).as_posix(),
                         {"listed_in": rel})

    covered_files: dict[Path, list[str]] = {}   # file -> [manifest rel]
    for mp_parent, info in manifest_cover.items():
        for r in info["records"]:
            vals: list[str] = []
            for key in ("artifacts", "outputs"):
                v = r.get(key) or []
                if isinstance(v, list):
                    vals.extend(str(x) for x in v)
                elif isinstance(v, dict):
                    vals.extend(str(x) for x in v.keys())
            for v in vals:
                target = mp_parent / v
                covered_files.setdefault(target, []).append(
                    info["rel_dir"] + "/_manifest.json")

    # raw 文件逐条检查
    need_repair: list[dict] = []   # --repair-candidates 输入
    wrong_source_suspects: list[dict] = []

    def projection_diagnostics(p: Path, item: dict):
        """无效投影诊断（D5）：抽样 NUL / UTF-8 严格探测 / 文件名中部 ~$。"""
        try:
            size = p.stat().st_size
            data, scope = read_sample(p, sample_bytes)
        except OSError as e:
            item["accessibility"] = accessibility_for_error(e)
            item["sampling_error"] = stat_error_detail(e)
            return
        item["sampling"] = {
            "sampled_bytes": len(data),
            "sample_nul_count": data.count(b"\x00"),
            "nul_scope": scope,
            "sample_limit_bytes": sample_bytes,
        }
        enc = detect_encoding_invalid(data, sample_bytes, size)
        if enc:
            entry = {"path": item["path"], "issue": "encoding-invalid",
                     "error_offset": enc["error_offset"],
                     "reason": enc["reason"],
                     "sampled_bytes": len(data)}
            report["invalid_projections"].append(entry)
        if MID_TILDE_DOLLAR_RE.match(p.name) and not p.name.startswith("~$"):
            report["garbage_candidates"].append({
                "path": item["path"],
                "reason": "文件名中部含 ~$（疑似锁文件投影，仅候选线索，"
                          "不拦截不定罪不删除）",
            })

    for p, kind in raw_files:
        rel = p.relative_to(base).as_posix()
        item: dict = {"path": rel, "kind": kind, "accessibility": "accessible"}
        report["items"][rel] = item
        projection_diagnostics(p, item)
        if item.get("accessibility") != "accessible":
            continue  # 抽样已观察失败（permission-denied/inaccessible），后续检查无依据

        if kind in ("raw-md",):
            try:
                head = p.read_text(encoding="utf-8",
                                   errors="replace")[:4000]
            except OSError as e:
                item["accessibility"] = accessibility_for_error(e)
                item["note"] = stat_error_detail(e)
                continue
            prov = parse_raw_md_provenance(head)
            cls = classify_provenance(prov)
            item["extracted_by"] = prov.get("extracted_by")
            if prov.get("declared_via"):
                item["declared_via"] = prov["declared_via"]
            if prov.get("signature_via"):
                item["signature_via"] = prov["signature_via"]

            if prov.get("source"):
                item["source_nature"] = "declared"
                item["link_state"] = "declared"
                item["declared_source"] = prov["source"]
                resolved, status = resolve_declared_source(prov["source"], base)
                if status == "unresolvable":
                    item["hash_check"] = "not-applicable"
                    _note_unverifiable(report, rel, prov["source"],
                                       "resolve 失败（观察动作自身失败，"
                                       "非越界非缺失）",
                                       value="inaccessible")
                elif status == "boundary":
                    item["hash_check"] = "not-applicable"
                    item["boundary_violation"] = True
                    report["boundary_violations"].append({
                        "path": rel, "declared_source": prov["source"],
                        "resolved_to": str(resolved),
                        "reason": "声明来源解析后落在当前公司基座之外"
                                  "（绝对路径越界或符号链接跨公司）；"
                                  "已停止该来源验证，未读取目标内容",
                    })
                else:
                    item["source"] = resolved.relative_to(base).as_posix()
                    exists_ok, stat_err = safe_exists(resolved)
                    if stat_err is not None:
                        # stat 抛 OSError（ENAMETOOLONG/ELOOP/EACCES…）：观察动作
                        # 自身失败，不 crash、不冒充 missing/boundary（spec
                        # 「不可访问范围如实上报」）；按 errno 分类
                        acc = accessibility_for_error(stat_err)
                        item["accessibility"] = acc
                        item["hash_check"] = "not-applicable"
                        _note_unverifiable(report, rel, prov["source"],
                                           f"stat 失败: "
                                           f"{stat_error_detail(stat_err)}",
                                           value=acc)
                    elif not exists_ok:
                        item["accessibility"] = "missing"
                        item["hash_check"] = "not-applicable"
                        note_gap("missing_original", rel,
                                 {"declared_source": prov["source"]})
                    else:
                        item["source_accessibility"] = "accessible"
                        if prov.get("source_sha256"):
                            declared_hash = prov["source_sha256"]
                            actual, read_err = sha_of(resolved)
                            if read_err is not None:
                                # 读失败 = 观察失败：not-applicable + errno 依据，
                                # 绝不冒充 mismatch/missing
                                acc = accessibility_for_error(read_err)
                                item["hash_check"] = "not-applicable"
                                item["source_accessibility"] = acc
                                _note_unverifiable(
                                    report, rel, prov["source"],
                                    f"来源字节读取失败: "
                                    f"{stat_error_detail(read_err)}",
                                    field="source_accessibility", value=acc)
                            elif actual == declared_hash:
                                item["hash_check"] = "match"
                                item["source_sha256_actual"] = actual
                            else:
                                item["hash_check"] = "mismatch"
                                item["source_sha256_declared"] = declared_hash
                                item["source_sha256_actual"] = actual
                                item["note"] = (
                                    "声明哈希与当前原件不一致：不判定哪一侧权威，"
                                    "不触发任何重写")
                                report["hash_mismatches"].append({
                                    "path": rel,
                                    "declared_sha256": declared_hash,
                                    "actual_sha256": actual,
                                })
                            # recorded-at-conversion 三要件回填（②已核验在基座内）
                            if cls.get("_candidate_recorded_at_conversion"):
                                cls["provenance_class"] = \
                                    "recorded-at-conversion"
                                cls["hash_semantics"] = "at-conversion"
                                cls["class_basis"] = (
                                    "D7 三要件齐备：转换器签名 + 同基座可解析来源"
                                    " + 格式合法转换时哈希；仅证明存在转换时点的"
                                    "来源声明，不独立证明历史真实性，不要求当前"
                                    "原件哈希等于记录哈希")
                                if item["hash_check"] == "mismatch":
                                    item["freshness"] = \
                                        "source-changed-since-record"
                                    item["hash_check"] = "mismatch"
                        else:
                            item["hash_check"] = "no-declared-hash"
                            note_gap("missing_hash", rel,
                                     {"declared_source": prov["source"]})
                        if full_hash and resolved not in sha_cache:
                            h, h_err = sha_of(resolved)  # full-hash：全量哈希原件
                            if h:
                                item.setdefault("source_sha256_actual", h)
                            elif h_err is not None:
                                item.setdefault(
                                    "source_accessibility",
                                    accessibility_for_error(h_err))
                # 回填分类不因字段名升级（classify 已按 extracted_by 分流）
                if "backfilled" in (prov.get("extracted_by") or "").lower():
                    pass  # classify_provenance 已给 candidate-association/at-backfill
                elif cls.get("_candidate_recorded_at_conversion") and \
                        status != "in-base":
                    # 来源越界/不可解析 → recorded-at-conversion 第②要件不成立
                    cls = {"provenance_class": None, "hash_semantics": "unknown"}
            else:
                # 无声明来源
                if imported_from.get(p.relative_to(raw_dir).as_posix()):
                    cand = imported_from[p.relative_to(raw_dir).as_posix()]
                    item["source_nature"] = "inferred"
                    item["link_state"] = "inferred"
                    item["inferred_candidates"] = [cand]
                    item["inference_basis"] = (
                        "raw/_index.json imported_from（路径结构推断）；"
                        "推断永不升级为已验证身份，即便候选唯一")
                    item["hash_check"] = "no-declared-hash"
                else:
                    item["source_nature"] = "none"
                    item["link_state"] = "unknown-unavailable"
                    item["hash_check"] = "no-declared-hash"
                    note_gap("missing_source", rel)
                need_repair.append({"path": rel, "kind": kind, "item": item})

            for key in ("provenance_class", "hash_semantics", "class_basis",
                        "hash_semantics_basis"):
                if cls.get(key):
                    item[key] = cls[key]
            if item.get("provenance_class"):
                report["provenance_class_summary"][
                    item["provenance_class"]] = \
                    report["provenance_class_summary"].get(
                        item["provenance_class"], 0) + 1
            if full_hash:
                h, _e = sha_of(p)
                if h:
                    item["self_sha256"] = h
        else:
            # csv / notes 边车：manifest 覆盖检查
            item["source_nature"] = None
            item["link_state"] = "unknown-unavailable"
            item["hash_check"] = "no-declared-hash"
            covers = covered_files.get(p) or covered_files.get(
                p.parent / p.name)
            if covers:
                item["manifest_coverage"] = sorted(set(covers))
            else:
                note_gap("no_manifest_coverage", rel, {
                    "reason": "所在目录无 _manifest.json 或未被任何 record 的 "
                              "artifacts/outputs 列出"})
                need_repair.append({"path": rel, "kind": kind, "item": item})
            if full_hash:
                h, _e = sha_of(p)
                if h:
                    item["self_sha256"] = h

    # ------------------------------------------------------------------
    # 4) materials/**/*.md frontmatter source
    # ------------------------------------------------------------------
    materials_dir = base / "materials"
    mat_visited, mat_failures = walk_with_errors(materials_dir)
    for f in mat_failures:
        report["scan"]["inaccessible"].append(
            {"location": f.location, "message": f.message})
        report["scan"]["not_scanned"].append(
            {"location": f.location, "reason": "permission-denied/unavailable"})
        report["scan"]["discovery_errors"].append(str(f))

    for cur, files in mat_visited:
        for fname in files:
            if not fname.endswith(".md"):
                continue
            p = Path(cur) / fname
            rel = p.relative_to(base).as_posix()
            item = {"path": rel, "kind": "material-md",
                    "accessibility": "accessible"}
            report["items"][rel] = item
            projection_diagnostics(p, item)
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:8000]
            except OSError as e:
                item["accessibility"] = accessibility_for_error(e)
                item["note"] = stat_error_detail(e)
                continue
            m = FM_RE.match(text)
            source_val = None
            if m:
                sm = FM_SOURCE_RE.search(m.group(1))
                if sm:
                    source_val = sm.group(1).strip().strip('"').strip("'")
            if source_val is None:
                item["source_nature"] = "none"
                item["link_state"] = "unknown-unavailable"
                item["hash_check"] = "no-declared-hash"
                note_gap("missing_source", rel)
                need_repair.append({"path": rel, "kind": "material-md",
                                    "item": item})
            elif source_val == "none":
                item["source_nature"] = "none"
                item["link_state"] = "unknown-unavailable"
                item["hash_check"] = "no-declared-hash"
                item["note"] = 'source: "none" 为 authored 标记，非缺口'
            else:
                item["source_nature"] = "declared"
                item["link_state"] = "declared"
                item["declared_source"] = source_val
                resolved, status = resolve_declared_source(source_val, base)
                if status == "unresolvable":
                    item["hash_check"] = "not-applicable"
                    _note_unverifiable(report, rel, source_val,
                                       "resolve 失败（观察动作自身失败，"
                                       "非越界非缺失）",
                                       value="inaccessible")
                elif status == "boundary":
                    item["hash_check"] = "not-applicable"
                    item["boundary_violation"] = True
                    report["boundary_violations"].append({
                        "path": rel, "declared_source": source_val,
                        "resolved_to": str(resolved),
                        "reason": "声明来源越界；已停止验证，未读取目标内容",
                    })
                else:
                    exists_ok, stat_err = safe_exists(resolved)
                    if stat_err is not None:
                        acc = accessibility_for_error(stat_err)
                        item["accessibility"] = acc
                        item["hash_check"] = "not-applicable"
                        _note_unverifiable(report, rel, source_val,
                                           f"stat 失败: "
                                           f"{stat_error_detail(stat_err)}",
                                           value=acc)
                    elif not exists_ok:
                        item["accessibility"] = "missing"
                        item["hash_check"] = "not-applicable"
                        note_gap("missing_original", rel,
                                 {"declared_source": source_val})
                    else:
                        item["source"] = resolved.relative_to(base).as_posix()
                        item["hash_check"] = "not-applicable"
                        item["source_accessibility"] = "accessible"
                wrong_source_suspects.append({"path": rel, "item": item})
            if full_hash:
                h, _e = sha_of(p)
                if h:
                    item["self_sha256"] = h

    # ------------------------------------------------------------------
    # 5) --repair-candidates（仍零写入，只加报告节）
    # ------------------------------------------------------------------
    if repair_candidates:
        def _cand_fields(orig_rel: str) -> dict:
            """候选原件当前哈希；读取失败如实带 errno 依据（不冒充无哈希）。"""
            h, e = sha_of(base / orig_rel)
            out = {"candidate_sha256": h}
            if e is not None:
                out["candidate_sha256_error"] = stat_error_detail(e)
            return out

        repairs: list[dict] = []
        for entry in need_repair:
            rel, kind = entry["path"], entry["kind"]
            fname = Path(rel).name
            cands = originals_by_basename.get(fname.lower(), [])
            result: dict = {"path": rel, "kind": kind}
            if kind in ("raw-csv", "raw-notes"):
                stem = fname
                for suffix in (".csv.notes.md", ".csv"):
                    if stem.endswith(suffix):
                        stem = stem[: -len(suffix)]
                        break
                stem_cands = originals_by_stem.get(stem.lower(), [])
                if len(stem_cands) == 1:
                    orig_rel = stem_cands[0]
                    result.update({
                        "resolution": "candidate",
                        "provenance_class": "candidate-association",
                        "candidate": orig_rel,
                        "basis": "unique-workbook-stem（workbook 级 stem 唯一匹配；"
                                 "sheet 级映射无 manifest 依据，保持 unresolved）",
                        "sheet_mapping": "unresolved",
                    })
                    result.update(_cand_fields(orig_rel))
                elif len(stem_cands) > 1:
                    result.update({"resolution": "unresolved",
                                   "candidates": sorted(stem_cands),
                                   "reason": "多个同 stem 原件，歧义不选择"})
                    note_gap("ambiguous", rel, {"candidates":
                                                sorted(stem_cands)})
                elif len(cands) == 1:
                    orig_rel = cands[0]
                    result.update({
                        "resolution": "candidate",
                        "provenance_class": "candidate-association",
                        "candidate": orig_rel,
                        "basis": "unique-basename",
                    })
                    result.update(_cand_fields(orig_rel))
                elif len(cands) > 1:
                    result.update({"resolution": "unresolved",
                                   "candidates": sorted(cands),
                                   "reason": "多个同 basename 原件，歧义不选择"})
                    note_gap("ambiguous", rel, {"candidates": sorted(cands)})
                else:
                    result.update({"resolution": "unresolved",
                                   "reason": "当前基座内无候选"
                                             "（匹配索引只在当前公司基座内构建）"})
                repairs.append(result)
            else:
                # raw md / material md：先按原 basename 匹配，再按去掉 .md 后缀
                # （raw md 命名约定 <original>.md）匹配
                fname_nomd = fname[:-3] if fname.endswith(".md") else fname
                cands = (originals_by_basename.get(fname.lower())
                         or originals_by_basename.get(fname_nomd.lower())
                         or [])
                if len(cands) == 1:
                    orig_rel = cands[0]
                    result.update({
                        "resolution": "candidate",
                        "provenance_class": "candidate-association",
                        "candidate": orig_rel,
                        "basis": "unique-basename",
                        "note": "唯一文件名候选只产生 candidate-association 级候选，"
                                "不触发 recorded-at-conversion；本工具零写入，"
                                "写入需 Owner 基于 dry-run 报告另行授权",
                    })
                    result.update(_cand_fields(orig_rel))
                elif len(cands) > 1:
                    result.update({"resolution": "unresolved",
                                   "candidates": sorted(cands),
                                   "reason": "多个同 basename 原件，歧义不选择"})
                    note_gap("ambiguous", rel, {"candidates": sorted(cands)})
                else:
                    result.update({"resolution": "unresolved",
                                   "reason": "当前基座内无候选"})
                repairs.append(result)
        report["repair_candidates"] = sorted(repairs, key=lambda r: r["path"])

        suspects: list[dict] = []
        # materials 分支已收集 wrong_source_suspects；raw-md declared 同样只评估不改写
        for it in report["items"].values():
            if it.get("kind") == "raw-md" and it.get("source_nature") == "declared":
                wrong_source_suspects.append({"path": it["path"], "item": it})
        for s in wrong_source_suspects:
            item = s["item"]
            if item.get("source_nature") != "declared":
                continue
            ev = {"path": s["path"], "declared_source":
                  item.get("declared_source")}
            if item.get("boundary_violation"):
                ev["verifiability"] = "boundary-violation"
                ev["suggestion"] = "声明来源越界，人工核查来源指向"
            elif item.get("accessibility") == "missing" or \
                    item.get("source_accessibility") == "missing":
                ev["verifiability"] = "source-missing"
                ev["suggestion"] = "声明来源在基座内不存在，人工核查"
            else:
                ev["verifiability"] = "resolvable-in-base"
                if item.get("hash_check") == "mismatch":
                    ev["hash_check"] = "mismatch"
                    ev["suggested_action"] = (
                        "reconvert（建议动作=重转换；reconverted 级 provenance "
                        "由实际重转换产生，本工具不产生它）")
                else:
                    ev["suggestion"] = "来源可解析，无需修复"
            suspects.append(ev)
        report["wrong_source_suspects"] = sorted(suspects,
                                                 key=lambda s: s["path"])

    # ------------------------------------------------------------------
    # 6) 排序 / 完成度 / 汇总
    # ------------------------------------------------------------------
    report["items"] = {k: report["items"][k] for k in sorted(report["items"])}
    for key in ("boundary_violations", "garbage_candidates",
                "invalid_projections", "hash_mismatches",
                "unverifiable_sources"):
        report[key] = sorted(report[key], key=lambda e: e["path"])
    for key in report["gaps"]:
        report["gaps"][key] = sorted(report["gaps"][key],
                                     key=lambda e: e["path"])
    report["scan"]["complete"] = not (
        report["scan"]["inaccessible"] or report["scan"]["discovery_errors"])
    return report


def has_findings(report: dict) -> bool:
    return bool(
        any(report["gaps"].values())
        or report["boundary_violations"]
        or report["garbage_candidates"]
        or report["invalid_projections"]
        or report["hash_mismatches"]
        or report["unverifiable_sources"]
        or report["scan"]["inaccessible"]
        or report["scan"]["discovery_errors"]
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=TOOL,
        description="只读溯源体检（零业务写入；报告 stdout 或显式 --report）")
    parser.add_argument("--base", default=None,
                        help="公司基座绝对路径（缺省用 COMPANY_BASE∥LANLNK_BASE "
                             "resolver，无静默默认公司）")
    parser.add_argument("--report", default=None,
                        help="报告写入路径（缺省 stdout；默认绝不写入 docs 基座）")
    parser.add_argument("--full-hash", action="store_true",
                        help="全量哈希（默认仅哈希有声明哈希需比对的对象）")
    parser.add_argument("--repair-candidates", action="store_true",
                        help="附加修复候选报告节（仍零写入）")
    parser.add_argument("--sample-bytes", type=int,
                        default=DEFAULT_SAMPLE_BYTES,
                        help=f"无效投影抽样字节数（默认 {DEFAULT_SAMPLE_BYTES}）")
    args = parser.parse_args(argv)

    base = resolve_base(args.base)

    try:
        report = run_inventory(
            base, full_hash=args.full_hash,
            repair_candidates=args.repair_candidates,
            sample_bytes=args.sample_bytes)
    except Exception:  # 工具失败（扫描器自身异常）
        print(f"[ERROR] {TOOL} 工具失败:", file=sys.stderr)
        traceback.print_exc()
        return 1

    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False)
    if args.report:
        # --report 是用户显式指定的路径（可在基座外；默认 stdout 绝不写基座）
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
        print(f"[OK] 报告已写入: {out}", file=sys.stderr)
    else:
        print(payload)

    if has_findings(report):
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
