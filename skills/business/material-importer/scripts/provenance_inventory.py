#!/usr/bin/env python3
"""provenance_inventory — 只读溯源体检（harden-material-import-provenance Lane A）。

设计依据：openspec/changes/harden-material-import-provenance/design.md
D1（独立纯读脚本）/ D5（投影侧候选线索与抽样口径）/ D7（回填 provenance 兼容读取与
recorded-at-conversion 三要件）/ D10（三维分维表达）/ D11（多公司基座隔离）。
inspect-material-source-fragments：materials frontmatter 来源完整字面路径优先，
仅明确不存在且符合受限 .jsonl 片段语法时拆分容器与 fragment（锚点一律
not-performed，独立 rc3 计数，不改共享 resolver）。

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
import stat
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

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

# --- recognize-web-capture-provenance（D1：受控网页声明采集） ---
# 声明字段名 → kind。键为「去首尾空白、去内部空白、ASCII 小写」归一后的字段名；
# 中文键（来源 URL / 抓取时间）与 ASCII 键（source_url / local_archive 系）都认，
# 半角/全角冒号均接受。
DECL_KIND_BY_FIELD = {
    "来源url": "source-url",
    "source_url": "source-url",
    "抓取时间": "captured-at",
    "local_archive": "local-archive",
    "local_archive_sha256_observed": "archive-hash-observed",
    "local_archive_observed_at": "archive-observed-at",
}
DECL_LINE_RE = re.compile(r"(?m)^[ \t]*([^:：\r\n]+?)[ \t]*[:：][ \t]*(.*?)[ \t]*$")
URL_SCHEME_SHAPED_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


def _norm_decl_field(name: str) -> str:
    return re.sub(r"[ \t]", "", name).lower()


def iter_head_comment_blocks(text: str):
    """产出文首空白后**连续 HTML 注释区**内每个已闭合注释的
    (content, content 在全文中的起始偏移)。

    - 只认文首：跳过文首空白（含 BOM）后必须立刻是 `<!--`；
    - 注释之间只允许空白；正文、代码块、后置注释一律不在产出内；
    - 未闭合（含被 4000 字符头截断）的注释不给有效来源。
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    pos = 0
    while pos < len(text) and text[pos].isspace():
        pos += 1
    while pos < len(text):
        if not text.startswith("<!--", pos):
            break
        end = text.find("-->", pos + 4)
        if end == -1:
            break  # 未闭合/截断：不给有效来源
        yield text[pos + 4:end], pos + 4
        pos = end + 3
        while pos < len(text) and text[pos].isspace():
            pos += 1


def head_comment_region_end(text: str) -> int:
    """文首连续注释区的结束偏移（原文本坐标系；含 BOM 时不位移命中位置）。

    与 iter_head_comment_blocks 同一口径：跳过文首空白（含 BOM）后必须立刻
    是 `<!--`，注释之间只允许空白。返回最后一个已闭合文首注释的 `-->`
    结束偏移；无文首注释（或首个注释未闭合/截断）时返回 0。

    旧 source/source_path 的 URL 形态命中只有落在此区内才是有效网页声明
    位置（spec 场景3「URL只在声明位置识别」）；本地路径命中不受此区限制
    （既有全头检索兼容行为不变，不收紧）。
    """
    pos = 1 if text.startswith("\ufeff") else 0
    while pos < len(text) and text[pos].isspace():
        pos += 1
    last_end = 0
    while pos < len(text):
        if not text.startswith("<!--", pos):
            break
        end = text.find("-->", pos + 4)
        if end == -1:
            break  # 未闭合/截断：文首区在此终止
        last_end = end + 3
        pos = last_end
        while pos < len(text) and text[pos].isspace():
            pos += 1
    return last_end


def collect_source_declarations(text_head: str) -> list[dict]:
    """D1 有界首部声明采集：仅文首连续注释区内的受控字段。

    每条：field（原文键名）/ kind / value（原值，仅去行尾空白）/
    value_normalized（去首尾空白，用于比较归组）/ line（头部内 1-based 行位置）。
    日期类声明只保留原文 + declared 语义，不推断时区、不校验历史真实性。
    """
    decls: list[dict] = []
    for content, abs_start in iter_head_comment_blocks(text_head):
        for m in DECL_LINE_RE.finditer(content):
            kind = DECL_KIND_BY_FIELD.get(_norm_decl_field(m.group(1)))
            if kind is None:
                continue
            value = m.group(2)
            decls.append({
                "field": m.group(1),
                "kind": kind,
                "value": value,
                "value_normalized": value.strip(),
                "line": text_head.count("\n", 0, abs_start + m.start()) + 1,
            })
    return decls


def diagnose_web_url(value: str) -> tuple[str, str]:
    """受控 URL 诊断（纯 urlsplit 解析，绝不联网）。

    返回 (status, detail)：
    - "valid"             合法 HTTP(S) 单个完整 URL；
    - "unsupported-scheme" 有 scheme 形态但非 http/https（file/ftp…），
                           不当相对路径、不做 basename 推断；
    - "malformed"         scheme 形态存在但结构非法（内部空白附注/控制符/
                           无 hostname/用户凭据/urlsplit 失败）；
    - "not-url"           无 scheme 形态（对 source_url 类字段按声明错误列诊断；
                          对旧 source/source_path 保持本地路径逻辑）。
    """
    v = value.strip()
    if not v:
        return "not-url", "空值"
    if URL_SCHEME_SHAPED_RE.match(v) is None:
        return "not-url", "无 scheme 形态（http(s)://…）"
    if any(ch.isspace() for ch in v):
        return "malformed", "URL 内含空白分隔附注，非单个完整 URL"
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in v):
        return "malformed", "含控制符"
    try:
        parts = urlsplit(v)
    except ValueError as e:
        return "malformed", f"urlsplit 解析失败: {e}"
    scheme = (parts.scheme or "").lower()
    if scheme not in ("http", "https"):
        return "unsupported-scheme", f"scheme={scheme}（仅支持 http/https）"
    if not parts.hostname:
        return "malformed", "无 hostname"
    if "@" in (parts.netloc or ""):
        return "malformed", "netloc 含用户凭据（user:pass@）"
    return "valid", ""


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
                 "source_pos": None,
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
        out["source_pos"] = _pos  # 头部内偏移（用于声明行位置；加法键）
        # 第三批（复核遗漏补充）：全部命中按位置加法保留，供调用方做
        # URL/本地多声明分流；source/declared_via 语义（先出现者）不变
        out["source_hits"] = [{"pos": p, "value": v, "via": vv}
                              for p, v, vv in unique]
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


def stat_or_none(p: Path) -> "os.stat_result | None | OSError":
    """stat 级存在观察（materials 字面路径优先用，D1）。

    返回三态：stat_result（存在）/ None（明确 FileNotFoundError=ENOENT，
    唯一允许片段回退的情形）/ OSError 实例（ENOTDIR/EACCES/ELOOP/
    ENAMETOOLONG 等观察失败——不冒充不存在，不触发回退）。
    """
    try:
        return os.stat(p)
    except FileNotFoundError:
        return None
    except OSError as e:
        return e


def resolve_declared_source_guarded(declared: str, base: Path):
    """resolve_declared_source 的 RuntimeError 承接包装（materials 局部）。

    pathlib.Path.resolve 将 ELOOP（自环 symlink）包成 RuntimeError（非
    OSError，Python 3.12 实证）；共享 resolver 语义不动，调用侧局部承接为
    观察失败。返回 (resolved, status, err_detail|None)；err_detail 附
    stat 探针取得的原始 errno 证据（pathlib 吞掉了 errno）。
    """
    try:
        resolved, status = resolve_declared_source(declared, base)
        return resolved, status, None
    except RuntimeError as e:
        detail = str(e)
        p_decl = Path(declared)
        raw_decl = p_decl if p_decl.is_absolute() else base / p_decl
        st_probe = stat_or_none(raw_decl)
        if isinstance(st_probe, OSError):
            detail += f"; {stat_error_detail(st_probe)}"
        return None, "unresolvable", detail


# --- inspect-material-source-fragments（D1：materials 受限 .jsonl 片段语法）---

def split_material_fragment_source(declared: str) -> tuple[str, str] | None:
    """materials 来源受限 .jsonl 片段语法判定（保守：宁可不拆，也不猜）。

    只在完整字面路径**明确不存在**（ENOENT）后由调用方调用；返回
    (容器, fragment) 或 None（不符合受限语法 → 调用方保留完整路径诊断）：
    - 按首个 # 分割（partition），左右两侧均非空；
    - 左侧（容器）：以 .jsonl 结尾；非 scheme:// 形态；不含换行/控制字符、
      中文分号；不剥括号、不推断「同名.md」、不做 URL 解码；
    - 右侧（fragment）：不含空白、控制字符、中文分号、ASCII/全角括号
      （括注叙述不是锚点）；额外 # 与 %xx 原样保留，不把 fragment 当路径。
    """
    if "#" not in declared:
        return None
    left, _, right = declared.partition("#")
    if not left or not right:
        return None
    if not left.endswith(".jsonl"):
        return None
    if URL_SCHEME_SHAPED_RE.match(left):
        return None
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in left):
        return None
    if "；" in left:
        return None
    if any(ch.isspace() or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in right):
        return None
    if "；" in right:
        return None
    if any(ch in right for ch in "()（）"):
        return None
    return left, right


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
        # --- recognize-web-capture-provenance（D2：新增节始终存在，向后兼容扩展）---
        "external_sources_unverified": [],
        "source_declaration_conflicts": [],
        "source_declaration_errors": [],
        "local_archive_findings": [],
        # --- inspect-material-source-fragments（D2：materials 片段发现，始终存在）---
        "material_source_fragment_findings": [],
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
            # declared_via/declared_source 统一在下方分流处按有效命中回填
            # （第三批：非文首区 URL 命中不是有效来源，不再从 prov 顶层带入）
            if prov.get("signature_via"):
                item["signature_via"] = prov["signature_via"]

            # --- D1/D2：受控网页声明采集（加法输出，不改本地字段优先规则）---
            # 第三批（复核遗漏补充）修复：
            # (a) 旧 source/source_path 多条命中不再只取先出现的一条——
            #     文首区 URL 命中全部进声明表（外部未核验清单），本地命中
            #     取先出现者照常解析，双方并存不互相掩盖（spec 场景4）；
            # (b) URL 形态命中只有落在文首连续注释区内才是有效网页来源；
            #     正文/代码块/后置注释中的 URL 命中不算（spec 场景3）。
            #     本地路径命中的既有全头检索兼容行为不变（不收紧）。
            decls = collect_source_declarations(head)
            region_end = head_comment_region_end(head)
            head_url_hits: list[dict] = []
            local_hits: list[dict] = []
            for h in prov.get("source_hits") or []:
                if URL_SCHEME_SHAPED_RE.match(h["value"]):
                    if h["pos"] < region_end:
                        head_url_hits.append(h)
                    # 非文首区 URL 形态命中：不是有效网页来源——不进外部
                    # 清单、不进本地解析、也不当缺失文件（spec 场景3）
                else:
                    local_hits.append(h)
            for h in head_url_hits:
                decls.append({
                    "field": h["via"],
                    "kind": "source-url",
                    "value": h["value"],
                    "value_normalized": h["value"].strip(),
                    "line": head.count("\n", 0, h["pos"]) + 1,
                })
            decls.sort(key=lambda d: d["line"])
            item["source_declarations"] = decls

            url_decls = [d for d in decls if d["kind"] == "source-url"]
            url_groups: dict[str, list[dict]] = {}
            for d in url_decls:
                status, detail = diagnose_web_url(d["value_normalized"])
                d["status"] = status
                if detail:
                    d["status_detail"] = detail
                if status == "valid":
                    # 相同 URL 按去首尾空白后的精确值归组，保留全部位置；
                    # 不做重定向/大小写/参数排序合并
                    url_groups.setdefault(d["value_normalized"], []).append(d)
                else:
                    report["source_declaration_errors"].append({
                        "path": rel, "field": d["field"], "line": d["line"],
                        "value": d["value"], "issue": status, "detail": detail,
                    })
            valid_urls = sorted(url_groups)
            external_present = bool(valid_urls)
            url_attempted = bool(url_decls)

            captured_at_decls = [d for d in decls
                                 if d["kind"] == "captured-at"]
            # C3：多条不同抓取时间 → 声明冲突（不选首条为权威），
            #     外部条目不带单一权威时间；单条时保留原文 declared 语义
            distinct_captured_at: list[str] = []
            for d in captured_at_decls:
                if d["value_normalized"] not in distinct_captured_at:
                    distinct_captured_at.append(d["value_normalized"])
            captured_at_conflict = len(distinct_captured_at) > 1
            if external_present:
                for url in valid_urls:
                    entry = {
                        "path": rel, "url": url,
                        "declarations": [{"field": d["field"],
                                          "line": d["line"]}
                                         for d in url_groups[url]],
                        "verification": "not-performed",
                        "note": "声明的外部网页来源；未联网核验，无网络取证",
                    }
                    if captured_at_decls and not captured_at_conflict:
                        # 日期保留原文且仅为声明（declared），
                        # 不推断时区、不校验历史抓取真实发生
                        entry["captured_at"] = captured_at_decls[0]["value"]
                        entry["captured_at_semantics"] = "declared"
                    report["external_sources_unverified"].append(entry)
                if len(valid_urls) > 1:
                    report["source_declaration_conflicts"].append({
                        "path": rel, "urls": valid_urls,
                        "reason": "多个不同URL声明并存：逐条保留并分别标记"
                                  "未核验，不推断权威版本，不合并",
                    })
                if captured_at_conflict:
                    report["source_declaration_conflicts"].append({
                        "path": rel, "kind": "captured-at",
                        "values": [d["value"] for d in captured_at_decls],
                        "lines": [d["line"] for d in captured_at_decls],
                        "reason": "多个不同抓取时间声明并存：逐条保留，"
                                  "不选首条为权威；外部条目不带单一权威"
                                  "时间（日期只是声明）",
                    })
                item["external_urls"] = valid_urls

            def _external_summary():
                """URL-only 顶层摘要：来源侧未扫描；MD 自身读取状态单列。"""
                item["source_kind"] = "external-url"
                item["source_nature"] = "declared"
                item["link_state"] = "declared"
                item["accessibility"] = "not-scanned"
                item["projection_accessibility"] = "accessible"
                item["hash_check"] = "unknown-scope"
                if prov.get("source_sha256"):
                    item["source_sha256_declared"] = prov["source_sha256"]
                    item["external_hash_note"] = (
                        "source_sha256 声明针对外部URL；URL 字节未获得，"
                        "不适用于网页核验（unknown-scope）")

            if local_hits:
                # 本地来源 = 旧 source/source_path 命中中先出现的非 URL 值
                # （既有「先出现者优先」语义不变；URL 命中一律走外部通道，
                #  绝不进入 resolve_declared_source）
                local_src = local_hits[0]["value"]
                item["source_kind"] = "mixed" if external_present else "local"
                item["source_nature"] = "declared"
                item["link_state"] = "declared"
                item["declared_source"] = local_src
                item["declared_via"] = local_hits[0]["via"]
                resolved, status = resolve_declared_source(local_src, base)
                if status == "unresolvable":
                    item["hash_check"] = "not-applicable"
                    _note_unverifiable(report, rel, local_src,
                                       "resolve 失败（观察动作自身失败，"
                                       "非越界非缺失）",
                                       value="inaccessible")
                elif status == "boundary":
                    item["hash_check"] = "not-applicable"
                    item["boundary_violation"] = True
                    report["boundary_violations"].append({
                        "path": rel, "declared_source": local_src,
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
                        _note_unverifiable(report, rel, local_src,
                                           f"stat 失败: "
                                           f"{stat_error_detail(stat_err)}",
                                           value=acc)
                    elif not exists_ok:
                        item["accessibility"] = "missing"
                        item["hash_check"] = "not-applicable"
                        note_gap("missing_original", rel,
                                 {"declared_source": local_src})
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
                                    report, rel, local_src,
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
                                     {"declared_source": local_src})
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
            elif external_present:
                # 仅外部URL声明（或旧 source/source_path 文首命中完整值为 URL）：
                # 来源为有效声明，不进本地路径解析，
                # 不算 missing_source/missing_original/missing_hash
                _external_summary()
                if head_url_hits:
                    # 旧字段载体声明（原值 + 原字段名保留；非文首区 URL 命中
                    # 不在此列——它们不是有效网页来源）
                    item["declared_source"] = head_url_hits[0]["value"]
                    item["declared_via"] = head_url_hits[0]["via"]
                if cls.get("_candidate_recorded_at_conversion"):
                    # recorded-at-conversion 第②要件（同基座内可解析来源）不成立
                    cls = {"provenance_class": None,
                           "hash_semantics": "unknown",
                           "hash_semantics_basis": (
                               "来源为外部URL，recorded-at-conversion 第②要件"
                               "（同基座内可解析来源）不成立，不升级")}
                # 有效外部声明 = 已有来源：不进 need_repair，不生成本地回填候选
            else:
                # 无可用声明来源
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
                if url_attempted:
                    # 仅畸形/不支持协议的URL声明：错误节已列诊断；
                    # 不得当作「无来源、可自动补本地source」
                    item["note"] = ("仅存在畸形或不支持协议的URL声明"
                                    "（见 source_declaration_errors）；"
                                    "不自动生成本地来源回填候选")
                else:
                    need_repair.append({"path": rel, "kind": kind, "item": item})

            # --- D3：独立本地存档观察（仅明确 local_archive 声明，
            #     不按同名 HTML 推断；当前观察 ≠ 历史输入，不升级真实性）---
            # 独立复核修复（第二批）：声明采集与发现判定覆盖零路径/多值/
            # 非法值形态，全部只做加法发现，不放宽既有规则
            archive_decls = [d for d in decls if d["kind"] == "local-archive"]
            hash_decls = [d for d in decls
                          if d["kind"] == "archive-hash-observed"]
            observed_at_decls = [d for d in decls
                                 if d["kind"] == "archive-observed-at"]
            if archive_decls or hash_decls or observed_at_decls:
                # C4：local_archive 值形态诊断（空值 / URL 形态）——
                #     非法形态不 resolve、不 stat、不读字节（不猜文件路径）
                valid_archive_decls: list[dict] = []
                for d in archive_decls:
                    v = d["value_normalized"]
                    if not v:
                        issue = "empty-value"
                    elif URL_SCHEME_SHAPED_RE.match(v):
                        issue = "url-shaped"
                    else:
                        issue = None
                    if issue is not None:
                        report["local_archive_findings"].append({
                            "path": rel,
                            "kind": "invalid-archive-declaration",
                            "declared_path": d["value"],
                            "line": d["line"],
                            "issue": issue,
                            "detail": ("local_archive 声明值"
                                       + ("为空，不是路径" if issue ==
                                          "empty-value"
                                          else "为 URL 形态，不是基座内路径")
                                       + "；不做文件系统解析、不猜路径、"
                                         "不联网，原值保留"),
                        })
                    else:
                        valid_archive_decls.append(d)

                # C2：哈希多值冲突——逐值分列，不选首条为权威比对基准
                distinct_hashes: list[str] = []
                for d in hash_decls:
                    v = d["value_normalized"].lower()
                    if v not in distinct_hashes:
                        distinct_hashes.append(v)
                hash_conflict = len(distinct_hashes) > 1
                invalid_hash_values = [v for v in distinct_hashes
                                       if not HEX64_RE.match(v)]
                declared_sha = (distinct_hashes[0]
                                if (distinct_hashes and not hash_conflict
                                    and not invalid_hash_values)
                                else None)

                # C3：观察时间多值冲突——同样不选首条
                distinct_observed_at: list[str] = []
                for d in observed_at_decls:
                    if d["value_normalized"] not in distinct_observed_at:
                        distinct_observed_at.append(d["value_normalized"])
                observed_at_conflict = len(distinct_observed_at) > 1
                declared_observed_at_value = (
                    observed_at_decls[0]["value"]
                    if (observed_at_decls and not observed_at_conflict)
                    else None)

                distinct_paths: list[str] = []
                for d in valid_archive_decls:
                    if d["value_normalized"] not in distinct_paths:
                        distinct_paths.append(d["value_normalized"])
                # 游离/冲突哈希只在可唯一绑定（合法格式 + 唯一路径）时挂接；
                # 零路径、多路径或多值冲突时绑定保持 unresolved，不静默套用
                hash_bindable = (declared_sha is not None
                                 and len(distinct_paths) == 1)

                observations: list[dict] = []
                for d in valid_archive_decls:
                    declared_path = d["value_normalized"]
                    obs = {
                        "declared_path": declared_path,
                        "declared_line": d["line"],
                        "accessibility": None,
                        "sha256_observed": None,
                        "observed_at": None,
                        "declared_sha256_observed": (declared_sha
                                                     if hash_bindable
                                                     else None),
                        "declared_observed_at": (
                            declared_observed_at_value
                            if hash_bindable else None),
                        "hash_check": None,
                    }
                    a_resolved, a_status = resolve_declared_source(
                        declared_path, base)
                    if a_status == "unresolvable":
                        obs["accessibility"] = "inaccessible"
                        report["local_archive_findings"].append({
                            "path": rel, "kind": "read-error",
                            "declared_path": declared_path,
                            "detail": "存档路径 resolve 失败（观察动作自身"
                                      "失败，非越界非缺失）"})
                    elif a_status == "boundary":
                        obs["accessibility"] = "boundary-violation"
                        report["local_archive_findings"].append({
                            "path": rel, "kind": "boundary",
                            "declared_path": declared_path,
                            "resolved_to": str(a_resolved),
                            "detail": "存档路径解析后落在当前公司基座之外"
                                      "（跨公司/基座外绝对路径/越界符号链接）；"
                                      "已停止观察，未读取目标内容，不复用其他"
                                      "公司同名存档或哈希"})
                    else:
                        obs["resolved_path"] = a_resolved.relative_to(
                            base).as_posix()
                        a_exists, a_err = safe_exists(a_resolved)
                        if a_err is not None:
                            acc = accessibility_for_error(a_err)
                            obs["accessibility"] = acc
                            report["local_archive_findings"].append({
                                "path": rel, "kind": "read-error",
                                "declared_path": declared_path,
                                "detail": f"存档 stat 失败: "
                                          f"{stat_error_detail(a_err)}"})
                        elif not a_exists:
                            obs["accessibility"] = "missing"
                            report["local_archive_findings"].append({
                                "path": rel, "kind": "missing",
                                "declared_path": declared_path,
                                "detail": "声明的存档在当前基座内不存在"
                                          "（≠ 网页原件不存在，两者分列）"})
                        else:
                            # SHA 对当前可读存档实际计算（仅明确关联对象，
                            # 开销有界；同基座内读取走缓存）
                            a_sha, a_read_err = sha_of(a_resolved)
                            if a_read_err is not None:
                                acc = accessibility_for_error(a_read_err)
                                obs["accessibility"] = acc
                                report["local_archive_findings"].append({
                                    "path": rel, "kind": "read-error",
                                    "declared_path": declared_path,
                                    "detail": f"存档字节读取失败: "
                                              f"{stat_error_detail(a_read_err)}"})
                            else:
                                obs["accessibility"] = "accessible"
                                obs["sha256_observed"] = a_sha
                                obs["observed_at"] = datetime.now(
                                    timezone.utc).isoformat()
                                if hash_bindable:
                                    obs["hash_check"] = (
                                        "match-observed"
                                        if a_sha == declared_sha
                                        else "mismatch-observed")
                                    if a_sha != declared_sha:
                                        report["local_archive_findings"].append({
                                            "path": rel,
                                            "kind": "hash-mismatch-observed",
                                            "declared_path": declared_path,
                                            "declared_sha256_observed":
                                                declared_sha,
                                            "sha256_observed": a_sha,
                                            "detail": "两时点哈希分列：声明"
                                                      "观察时点与本次观察"
                                                      "不一致；不判定哪一侧"
                                                      "权威，不升级真实性"})
                                elif hash_decls:
                                    # 有哈希声明但未绑定（多值冲突/多路径）：
                                    # 标注 unresolved，不冒充无声明
                                    obs["hash_check"] = "unresolved-declared-hash"
                                else:
                                    obs["hash_check"] = "no-declared-hash"
                    if obs["hash_check"] is None:
                        obs["hash_check"] = "not-applicable"  # 未能观察字节
                    observations.append(obs)

                if len(distinct_paths) > 1:
                    report["local_archive_findings"].append({
                        "path": rel, "kind": "archive-conflict",
                        "declared_paths": sorted(distinct_paths),
                        "detail": "多个不同 local_archive 声明并存：逐项保留"
                                  "观察，不选首条为权威"})
                if hash_conflict:
                    report["local_archive_findings"].append({
                        "path": rel, "kind": "declared-hash-conflict",
                        "declared_sha256_values": sorted(distinct_hashes),
                        "detail": "多条不同 local_archive_sha256_observed "
                                  "并存：逐值保留分列，不选首条为权威比对"
                                  "基准，不静默绑定",
                    })
                if invalid_hash_values:
                    invalid_orig = [d["value"] for d in hash_decls
                                    if d["value_normalized"].lower()
                                    in invalid_hash_values]
                    report["local_archive_findings"].append({
                        "path": rel, "kind": "invalid-hash",
                        "value": invalid_orig[0] if invalid_orig else None,
                        "values": invalid_orig,
                        "detail": "local_archive_sha256_observed 非 64 位"
                                  "十六进制，不作为比对基准",
                    })
                elif declared_sha is not None and len(distinct_paths) != 1:
                    # 零路径或多路径：合法单一哈希无法唯一绑定
                    report["local_archive_findings"].append({
                        "path": rel, "kind": "unresolved-hash-binding",
                        "declared_sha256_observed": declared_sha,
                        "declared_paths": sorted(distinct_paths),
                        "detail": ("零路径" if not distinct_paths else "多路径")
                                  + "无法唯一绑定观察哈希：绑定保持"
                                  " unresolved，不静默应用到任何一条",
                    })
                if observed_at_conflict:
                    report["local_archive_findings"].append({
                        "path": rel, "kind": "observed-at-conflict",
                        "declared_observed_at_values": [
                            d["value"] for d in observed_at_decls],
                        "detail": "多条不同 local_archive_observed_at 并存："
                                  "逐条保留，不选首条为权威观察时点",
                    })
                item["local_archive_observations"] = observations

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

    def _observe_material_fragment(item: dict, rel: str, source_val: str,
                                   container: str, fragment: str,
                                   full_hash: bool) -> None:
        """D2：materials 片段来源的容器独立观察。

        只 stat 容器（默认不读正文、不核验锚点、不做文本解码）；观察失败/
        越界/缺失按既有清单口径分列，同时始终保留 fragment 未核验发现。
        """
        item["source_expression_kind"] = "local-file-fragment"
        item["source_container"] = container
        item["source_fragment"] = fragment
        item["anchor_verification"] = "not-performed"
        item["projection_accessibility"] = "accessible"  # 材料自身读取状态单列
        finding: dict = {"path": rel, "declared_source": source_val,
                         "source_container": container,
                         "source_fragment": fragment}
        resolve_err: str | None = None
        c_resolved, c_status, resolve_err = resolve_declared_source_guarded(
            container, base)
        if c_status == "unresolvable":
            detail = f"（{resolve_err}）" if resolve_err else ""
            item["container_accessibility"] = "inaccessible"
            item["hash_check"] = "not-applicable"
            _note_unverifiable(report, rel, source_val,
                               f"片段容器 resolve 失败{detail}"
                               "（观察动作自身失败，非越界非缺失）",
                               value="inaccessible")
            finding["kind"] = "container-check-failed"
            finding["reason"] = (f"容器 resolve 失败{detail}"
                                 "（观察动作自身失败）；锚点亦未核验")
        elif c_status == "boundary":
            item["container_accessibility"] = "boundary-violation"
            item["hash_check"] = "not-applicable"
            item["boundary_violation"] = True
            report["boundary_violations"].append({
                "path": rel, "declared_source": source_val,
                "resolved_to": str(c_resolved),
                "reason": "片段容器解析后落在当前公司基座之外（绝对路径越界"
                          "或符号链接跨公司）；已停止该来源验证，未读取目标内容",
            })
            finding["kind"] = "container-boundary-violation"
            finding["reason"] = ("容器越界（不读取目标内容，不跨公司复用同名"
                                 "容器）；锚点亦未核验")
        else:
            cst = stat_or_none(c_resolved)
            if isinstance(cst, OSError):
                acc = accessibility_for_error(cst)
                item["container_accessibility"] = acc
                item["accessibility"] = acc
                item["hash_check"] = "not-applicable"
                _note_unverifiable(report, rel, source_val,
                                   f"片段容器 stat 失败: "
                                   f"{stat_error_detail(cst)}", value=acc)
                finding["kind"] = "container-check-failed"
                finding["reason"] = (f"容器 stat 失败: {stat_error_detail(cst)}；"
                                     "锚点亦未核验")
            elif cst is None:
                # 明确 ENOENT：missing_original 记容器（非原整串），原声明保留
                item["container_accessibility"] = "missing"
                item["accessibility"] = "missing"
                item["hash_check"] = "not-applicable"
                note_gap("missing_original", rel, {
                    "declared_source": source_val,
                    "source_container": container,
                    "source_fragment": fragment,
                    "container_path": c_resolved.relative_to(base).as_posix(),
                })
                finding["kind"] = "container-missing"
                finding["reason"] = ("容器在当前基座内不存在（missing_original "
                                     "记容器而非原整串，原声明与 fragment 保留）；"
                                     "锚点亦未核验")
            elif not stat.S_ISREG(cst.st_mode):
                item["container_accessibility"] = "not-regular-file"
                item["hash_check"] = "not-applicable"
                finding["kind"] = "container-check-failed"
                finding["reason"] = ("容器存在但不是普通文件（目录/特殊文件），"
                                     "不当作可用容器，也不判锚点无效")
            else:
                item["container_accessibility"] = "accessible"
                item["source_accessibility"] = "accessible"
                item["source"] = c_resolved.relative_to(base).as_posix()
                item["hash_check"] = "unknown-scope"  # 未验证锚点或历史哈希
                finding["kind"] = "anchor-not-verified"
                finding["reason"] = ("容器存在且可访问；锚点未核验（默认不读"
                                     "容器正文、不在内容中匹配 fragment；"
                                     "scan.complete 不代表锚点已核验）")
                if full_hash:
                    h, h_err = sha_of(c_resolved)
                    if h is not None:
                        # 当前观察哈希/时点，不冒充转换时哈希（不写 source_sha256*）
                        item["container_sha256_observed"] = h
                        item["container_observed_at"] = datetime.now(
                            timezone.utc).isoformat()
                    else:
                        # 实际读取失败（任意 OSError：EACCES/EIO/…）与 stat
                        # 存在分开表达，但状态/诊断/repair 一致为
                        # container-check-failed：不假装观察成功、不产生容器
                        # 哈希、hash_check 明确未完成、anchor_verification
                        # 保持 not-performed
                        item["container_hash_error"] = \
                            stat_error_detail(h_err)
                        item["container_hash_check"] = "not-completed"
                        item["hash_check"] = "not-applicable"
                        _note_unverifiable(
                            report, rel, source_val,
                            f"--full-hash 容器字节读取失败: "
                            f"{stat_error_detail(h_err)}",
                            field="container_accessibility",
                            value="accessible")
                        finding["kind"] = "container-check-failed"
                        finding["reason"] = (
                            f"容器 stat 存在但字节读取失败: "
                            f"{stat_error_detail(h_err)}（stat 存在与读取失败"
                            "分开表达）；锚点亦未核验")
        report["material_source_fragment_findings"].append(finding)

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
                # pathlib Path.resolve 将 ELOOP（自环 symlink）包成 RuntimeError
                # （非 OSError）：共享 resolver 不动，materials 局部承接为
                # 观察失败（附 errno 证据），不回退、不崩溃
                resolved, status, resolve_err = \
                    resolve_declared_source_guarded(source_val, base)
                if status == "unresolvable":
                    detail = f"（{resolve_err}）" if resolve_err else ""
                    item["hash_check"] = "not-applicable"
                    _note_unverifiable(report, rel, source_val,
                                       f"resolve 失败{detail}"
                                       "（观察动作自身失败，"
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
                    # D1：完整字面路径优先 —— stat 级区分「明确不存在」与观察
                    # 失败（ENOTDIR/EACCES/ELOOP 等绝不冒充不存在，不触发回退）
                    st = stat_or_none(resolved)
                    if isinstance(st, OSError):
                        acc = accessibility_for_error(st)
                        item["accessibility"] = acc
                        item["hash_check"] = "not-applicable"
                        _note_unverifiable(report, rel, source_val,
                                           f"stat 失败: "
                                           f"{stat_error_detail(st)}",
                                           value=acc)
                    elif st is not None and not stat.S_ISREG(st.st_mode):
                        # 存在但非普通文件：观察失败口径，不当作有效文件或缺失
                        item["accessibility"] = "not-regular-file"
                        item["hash_check"] = "not-applicable"
                        _note_unverifiable(
                            report, rel, source_val,
                            "声明来源存在但不是普通文件（目录/特殊文件）；"
                            "不当作有效文件或缺失，不做片段回退",
                            value="not-regular-file")
                    elif st is not None:
                        # 完整字面文件存在（含 #、括号、空格、分号）：直接沿用
                        item["source"] = resolved.relative_to(base).as_posix()
                        item["hash_check"] = "not-applicable"
                        item["source_accessibility"] = "accessible"
                    else:
                        # 明确 ENOENT：唯一允许考虑受限片段语法的情形
                        split = split_material_fragment_source(source_val)
                        if split is None:
                            item["accessibility"] = "missing"
                            item["hash_check"] = "not-applicable"
                            note_gap("missing_original", rel,
                                     {"declared_source": source_val})
                        else:
                            _observe_material_fragment(
                                item, rel, source_val, split[0], split[1],
                                full_hash=full_hash)
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
            if item.get("source_expression_kind") == "local-file-fragment":
                # D3：片段来源独立分支——已有声明，永不进回填候选；
                # 容器状态分别保留原因，不落 resolvable-in-base/无需修复，
                # 不建议自动重转
                ev["source_expression_kind"] = "local-file-fragment"
                ca = item.get("container_accessibility")
                if item.get("container_hash_error"):
                    # 容器 stat 存在但 --full-hash 字节读取失败：读取失败与
                    # stat 存在分开表达，诊断口径与状态一致（不落
                    # fragment-not-verified，不假装容器观察完成）
                    ev["verifiability"] = "container-check-failed"
                    ev["suggestion"] = ("容器 stat 存在但字节读取失败"
                                        "（container_hash_error 保留 errno）；"
                                        "人工核查，本工具不读容器正文、"
                                        "不自动回填来源")
                elif ca == "accessible":
                    ev["verifiability"] = "fragment-not-verified"
                    ev["suggestion"] = ("容器存在但锚点未核验；人工在容器中"
                                        "核对 fragment，本工具不读容器正文、"
                                        "不自动回填来源")
                elif ca == "missing":
                    ev["verifiability"] = "container-missing"
                    ev["suggestion"] = ("片段容器在基座内不存在；人工核查，"
                                        "不建议自动重转")
                elif ca == "boundary-violation":
                    ev["verifiability"] = "boundary-violation"
                    ev["suggestion"] = ("片段容器越界；人工核查来源指向"
                                        "（未读取目标内容）")
                else:  # not-regular-file / permission-denied / inaccessible
                    ev["verifiability"] = "container-check-failed"
                    ev["suggestion"] = ("片段容器观察失败或不可用（详见对应"
                                        "清单）；人工核查")
            elif item.get("source_kind") == "external-url":
                # 外部URL声明：未联网核验，绝不落 resolvable-in-base
                ev["source_kind"] = "external-url"
                ev["verifiability"] = "external-not-verified"
                ev["suggestion"] = ("外部网页来源未联网核验；人工核验，"
                                    "或补充明确 local_archive 声明后再观察，"
                                    "不自动回填本地 source")
            elif item.get("boundary_violation"):
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
    report["external_sources_unverified"] = sorted(
        report["external_sources_unverified"],
        key=lambda e: (e["path"], e["url"]))
    report["source_declaration_errors"] = sorted(
        report["source_declaration_errors"],
        key=lambda e: (e["path"], e["field"], e["line"]))
    report["source_declaration_conflicts"] = sorted(
        report["source_declaration_conflicts"], key=lambda e: e["path"])
    report["local_archive_findings"] = sorted(
        report["local_archive_findings"],
        key=lambda e: (e["path"], e.get("kind", ""),
                       e.get("declared_path", "")))
    report["material_source_fragment_findings"] = sorted(
        report["material_source_fragment_findings"],
        key=lambda e: (e["path"], e.get("kind", ""),
                       e.get("source_container", ""),
                       e.get("source_fragment", "")))
    for key in report["gaps"]:
        report["gaps"][key] = sorted(report["gaps"][key],
                                     key=lambda e: e["path"])
    report["scan"]["complete"] = not (
        report["scan"]["inaccessible"] or report["scan"]["discovery_errors"])
    # scan.complete 只覆盖声明的本地扫描范围；外部URL声明一律未核验
    report["external_verification"] = {
        "status": ("not-performed"
                   if report["external_sources_unverified"]
                   else "no-external-declarations"),
        "note": "本工具绝不联网；外部URL声明未核验（unverified），"
                "scan.complete 不包含外部来源可达性",
    }
    return report


def has_findings(report: dict) -> bool:
    return bool(
        any(report["gaps"].values())
        or report["boundary_violations"]
        or report["garbage_candidates"]
        or report["invalid_projections"]
        or report["hash_mismatches"]
        or report["unverifiable_sources"]
        or report["external_sources_unverified"]
        or report["source_declaration_conflicts"]
        or report["source_declaration_errors"]
        or report["local_archive_findings"]
        or report["material_source_fragment_findings"]
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
