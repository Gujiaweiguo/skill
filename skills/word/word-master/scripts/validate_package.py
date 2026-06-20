"""Word 内容包 Schema 校验器

在渲染前校验 .word-content.md 文件，提前拦截格式错误。
用法:
    cd skills/word/word-master
    uv run scripts/validate_package.py <文件或目录> [--json] [--verbose]

退出码: 0=全部通过, 1=有未通过项
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# ============================================================
# 常量
# ============================================================

VALID_TYPES = {"technical", "commercial", "proposal", "report", "intro"}

VALID_TEMPLATES = {
    "bidding-technical",
    "bidding-commercial",
    "bidding-standard",
    "bidding-compilation",
    "proposal",
    "report",
    "intro",
}

FRONTMATTER_DELIM = re.compile(r"^---\s*$", re.MULTILINE)
YAML_BLOCK = re.compile(r"^```yaml\s*\n(.*?)```", re.DOTALL | re.MULTILINE)
HEADING = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
IMAGE_REF = re.compile(r"!\[.*?\]\((.+?)\)")


# ============================================================
# 数据结构
# ============================================================

@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning"
    rule: str
    message: str
    line: int | None = None


@dataclass
class ValidationResult:
    path: str
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)


# ============================================================
# 校验器
# ============================================================

class PackageValidator:
    """Word 内容包校验器"""

    def __init__(self, lanlnk_base: str = ""):
        self.lanlnk_base = Path(lanlnk_base) if lanlnk_base else None

    def validate_file(self, path: Path) -> ValidationResult:
        result = ValidationResult(path=str(path), valid=True)

        if not path.exists():
            result.issues.append(ValidationIssue("error", "EXISTS", "文件不存在"))
            result.valid = False
            return result

        raw = path.read_text(encoding="utf-8")
        lines = raw.split("\n")

        # ── P0: Frontmatter ──────────────────────────────
        fm_text, body, fm_end_line = self._split_frontmatter(raw, lines)
        self._check_frontmatter(result, fm_text, body, fm_end_line)

        if fm_text:
            fm_data = self._safe_yaml(result, fm_text, "frontmatter")
            if fm_data:
                self._check_metadata(result, fm_data)
                self._check_cover(result, fm_data)
                self._check_header_footer(result, fm_data)
                self._check_toc(result, fm_data)
                self._check_sources(result, fm_data, path)
        else:
            result.issues.append(ValidationIssue(
                "error", "FM_MISSING", "缺少 YAML frontmatter（需要 --- 分隔）"
            ))

        # ── P1: Body ─────────────────────────────────────
        self._check_body_structure(result, body, path)
        self._check_yaml_blocks(result, body)
        self._check_tables(result, body)
        self._check_image_refs(result, body, path)

        # ── 汇总 ────────────────────────────────────────
        result.valid = not any(i.severity == "error" for i in result.issues)
        return result

    # ── Frontmatter 解析 ────────────────────────────────

    def _split_frontmatter(
        self, raw: str, lines: list[str]
    ) -> tuple[str | None, str, int]:
        matches = list(FRONTMATTER_DELIM.finditer(raw))
        if len(matches) >= 2:
            fm = raw[matches[0].end():matches[1].start()].strip()
            body = raw[matches[1].end():].strip()
            fm_end_line = matches[1].start()
            return fm, body, fm_end_line
        return None, raw, 0

    def _check_frontmatter(
        self, result: ValidationResult,
        fm_text: str | None, body: str, fm_end: int,
    ):
        if fm_text is None:
            return  # FM_MISSING 已在 validate_file 中记录

        try:
            yaml.safe_load(fm_text)
        except yaml.YAMLError as e:
            result.issues.append(ValidationIssue(
                "error", "FM_YAML",
                f"frontmatter YAML 解析失败: {e}"
            ))

    def _safe_yaml(
        self, result: ValidationResult, text: str, context: str,
    ) -> dict[str, Any] | None:
        try:
            data = yaml.safe_load(text)
            if data is None:
                return {}
            if not isinstance(data, dict):
                result.issues.append(ValidationIssue(
                    "error", f"{context.upper()}_TYPE",
                    f"{context} 必须是 YAML 字典"
                ))
                return None
            return data
        except yaml.YAMLError as e:
            return None

    # ── 字段校验 ────────────────────────────────────────

    def _check_metadata(self, result: ValidationResult, data: dict[str, Any]):
        title = data.get("title", "")
        if not title or not str(title).strip():
            result.issues.append(ValidationIssue(
                "error", "META_TITLE", "title 字段缺失或为空"
            ))

        doc_type = data.get("type", "")
        if doc_type and doc_type not in VALID_TYPES:
            result.issues.append(ValidationIssue(
                "error", "META_TYPE",
                f"type='{doc_type}' 无效，可选: {', '.join(sorted(VALID_TYPES))}"
            ))

        template = data.get("template", "")
        if template and template not in VALID_TEMPLATES:
            result.issues.append(ValidationIssue(
                "error", "META_TEMPLATE",
                f"template='{template}' 无效，可选: {', '.join(sorted(VALID_TEMPLATES))}"
            ))

        date_val = data.get("date", "")
        if date_val and isinstance(date_val, str):
            if not re.match(r"\d{4}[-/年]\d{1,2}[-/月]?", date_val):
                result.issues.append(ValidationIssue(
                    "warning", "META_DATE",
                    f"date='{date_val}' 格式建议为 YYYY-MM-DD 或 YYYY年MM月"
                ))

    def _check_cover(self, result: ValidationResult, data: dict[str, Any]):
        cover = data.get("cover")
        if cover is None:
            return
        if not isinstance(cover, dict):
            result.issues.append(ValidationIssue(
                "error", "COVER_TYPE", "cover 必须是字典"
            ))
            return
        if not cover.get("title", "").strip():
            result.issues.append(ValidationIssue(
                "warning", "COVER_TITLE",
                "cover.title 为空，渲染时会回退到顶层 title"
            ))

    def _check_header_footer(self, result: ValidationResult, data: dict[str, Any]):
        for key in ("header", "footer"):
            val = data.get(key)
            if val is None:
                continue
            if not isinstance(val, dict):
                result.issues.append(ValidationIssue(
                    "error", f"{key.upper()}_TYPE",
                    f"{key} 必须是字典"
                ))

    def _check_toc(self, result: ValidationResult, data: dict[str, Any]):
        toc = data.get("toc")
        if toc is None:
            return
        if not isinstance(toc, dict):
            result.issues.append(ValidationIssue(
                "error", "TOC_TYPE", "toc 必须是字典"
            ))
            return
        max_level = toc.get("max_level", 3)
        if not isinstance(max_level, int) or max_level < 1 or max_level > 4:
            result.issues.append(ValidationIssue(
                "warning", "TOC_LEVEL",
                f"toc.max_level={max_level} 建议为 1-4"
            ))

    def _check_sources(
        self, result: ValidationResult, data: dict[str, Any], pkg_path: Path,
    ):
        sources = data.get("sources")
        if sources is None:
            return
        if not isinstance(sources, list):
            result.issues.append(ValidationIssue(
                "error", "SOURCES_TYPE", "sources 必须是列表"
            ))
            return
        for i, src in enumerate(sources):
            if not isinstance(src, dict):
                result.issues.append(ValidationIssue(
                    "error", "SOURCE_ITEM",
                    f"sources[{i}] 必须是字典"
                ))
                continue
            path_str = src.get("path", "")
            if not path_str:
                result.issues.append(ValidationIssue(
                    "warning", "SOURCE_PATH",
                    f"sources[{i}].path 为空"
                ))
                continue
            resolved = self._resolve_path(path_str, pkg_path)
            if resolved and not resolved.exists():
                result.issues.append(ValidationIssue(
                    "warning", "SOURCE_EXISTS",
                    f"sources[{i}].path 文件不存在: {path_str}"
                ))

    # ── Body 校验 ───────────────────────────────────────

    def _check_body_structure(
        self, result: ValidationResult, body: str, pkg_path: Path,
    ):
        if not body.strip():
            result.issues.append(ValidationIssue(
                "error", "BODY_EMPTY", "正文为空"
            ))
            return

        headings = HEADING.findall(body)
        h1_count = sum(1 for hashes, _ in headings if len(hashes) == 2)

        if h1_count == 0:
            result.issues.append(ValidationIssue(
                "error", "BODY_NO_CHAPTER",
                "正文缺少 ## 章标题（至少需要一个 ## 开头章节）"
            ))

    def _check_yaml_blocks(self, result: ValidationResult, body: str):
        blocks = YAML_BLOCK.findall(body)
        for i, block_text in enumerate(blocks):
            try:
                data = yaml.safe_load(block_text)
                if data is not None and not isinstance(data, dict):
                    result.issues.append(ValidationIssue(
                        "warning", "YAML_BLOCK_TYPE",
                        f"第 {i+1} 个 yaml 代码块不是字典"
                    ))
            except yaml.YAMLError as e:
                result.issues.append(ValidationIssue(
                    "error", "YAML_BLOCK_PARSE",
                    f"第 {i+1} 个 yaml 代码块解析失败: {e}"
                ))

    def _check_tables(self, result: ValidationResult, body: str):
        blocks = YAML_BLOCK.findall(body)
        for i, block_text in enumerate(blocks):
            try:
                data = yaml.safe_load(block_text)
            except yaml.YAMLError:
                continue
            if not isinstance(data, dict):
                continue
            if "table" not in data:
                continue

            td = data.get("table_data")
            if not td or not isinstance(td, dict):
                result.issues.append(ValidationIssue(
                    "error", "TABLE_DATA_MISSING",
                    f"第 {i+1} 个 yaml 块声明了 table 但缺少 table_data"
                ))
                continue

            header = td.get("header")
            if not header or not isinstance(header, list):
                result.issues.append(ValidationIssue(
                    "error", "TABLE_HEADER",
                    f"第 {i+1} 个表格缺少 header 列定义"
                ))
                continue

            rows = td.get("rows")
            if rows is not None and not isinstance(rows, list):
                result.issues.append(ValidationIssue(
                    "error", "TABLE_ROWS",
                    f"第 {i+1} 个表格 rows 不是列表"
                ))

            # 列数一致性
            if isinstance(header, list) and isinstance(rows, list):
                h_len = len(header)
                for j, row in enumerate(rows):
                    if isinstance(row, list) and len(row) != h_len:
                        result.issues.append(ValidationIssue(
                            "warning", "TABLE_COL_COUNT",
                            f"第 {i+1} 个表格 row[{j}] 有 {len(row)} 列，"
                            f"header 有 {h_len} 列"
                        ))
                        break

    def _check_image_refs(
        self, result: ValidationResult, body: str, pkg_path: Path,
    ):
        refs = IMAGE_REF.findall(body)
        for ref in refs:
            if ref.startswith("http://") or ref.startswith("https://"):
                continue
            resolved = self._resolve_path(ref, pkg_path)
            if resolved and not resolved.exists():
                result.issues.append(ValidationIssue(
                    "warning", "IMAGE_EXISTS",
                    f"图片引用不存在: {ref}"
                ))

    # ── 工具方法 ────────────────────────────────────────

    def _resolve_path(self, path_str: str, pkg_path: Path) -> Path | None:
        """展开 $ 变量并解析路径"""
        # 展开 $LANLNK_BASE / $MATERIALS_DIR 等
        lanlnk = os.environ.get("LANLNK_BASE", "")
        materials = str(Path(lanlnk) / "materials") if lanlnk else ""

        resolved_str = (
            path_str
            .replace("$LANLNK_BASE", lanlnk)
            .replace("$MATERIALS_DIR", materials)
        )

        p = Path(resolved_str)
        if p.is_absolute():
            return p
        # 相对于内容包目录
        return pkg_path.parent / p


# ============================================================
# CLI
# ============================================================

def format_result(result: ValidationResult, verbose: bool = False) -> str:
    icon = "✅" if result.valid else "❌"
    lines = [f"  {icon} {result.path}"]

    if verbose or not result.valid:
        for issue in result.issues:
            sev_icon = "🔴" if issue.severity == "error" else "🟡"
            lines.append(
                f"    {sev_icon} [{issue.rule}] {issue.message}"
            )
    elif result.issues:
        err_count = sum(1 for i in result.issues if i.severity == "error")
        warn_count = sum(1 for i in result.issues if i.severity == "warning")
        parts = []
        if err_count:
            parts.append(f"{err_count} 错误")
        if warn_count:
            parts.append(f"{warn_count} 警告")
        if parts:
            lines.append(f"    ({', '.join(parts)})")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Word 内容包 Schema 校验器"
    )
    parser.add_argument(
        "path",
        help="要校验的 .word-content.md 文件或目录",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="输出 JSON 格式（供程序调用）",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="显示所有检查结果（包括通过的）",
    )

    args = parser.parse_args()
    target = Path(args.path)

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.rglob("*.word-content.md"))
    else:
        print(f"错误: 路径不存在: {target}", file=sys.stderr)
        sys.exit(1)

    if not files:
        if args.json:
            print(json.dumps({"total": 0, "passed": 0, "failed": 0, "results": []}))
        else:
            print("未找到 .word-content.md 文件")
        sys.exit(0)

    lanlnk_base = os.environ.get("LANLNK_BASE", "")
    validator = PackageValidator(lanlnk_base=lanlnk_base)

    results = [validator.validate_file(f) for f in files]
    passed = sum(1 for r in results if r.valid)
    failed = len(results) - passed

    if args.json:
        output = {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "results": [
                {
                    "path": r.path,
                    "valid": r.valid,
                    "issues": [
                        {
                            "severity": i.severity,
                            "rule": i.rule,
                            "message": i.message,
                        }
                        for i in r.issues
                    ],
                }
                for r in results
            ],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(format_result(r, args.verbose))
        print()
        print(f"  统计: ✅ {passed} 通过 | ❌ {failed} 未通过")
        print("=" * 60)

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
