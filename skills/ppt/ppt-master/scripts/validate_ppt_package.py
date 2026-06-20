#!/usr/bin/env python3
"""PPT 内容包 Schema 校验器

在 compile.py 渲染前校验 PPT YAML 配置，提前拦截格式错误。
用法:
    cd skills/ppt/ppt-master/templates/proposal-pptx
    uv run ../../scripts/validate_ppt_package.py <YAML配置> [--json] [--verbose]

退出码: 0=全部通过, 1=有未通过项
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ── 常量 ──────────────────────────────────────────────

VALID_MODES = {"proposal", "intro", "tender"}

VALID_SLIDE_TYPES = {
    "agenda",
    "requirement-understanding",
    "coverage-analysis",
    "core-scenario",
    "pricing-comparison",
    "implementation-plan",
    "text-bullets",
    "feature-cards",
}

MAX_TOC_TITLES = 4

SLIDE_REQUIRED_FIELDS: dict[str, list[str]] = {
    "text-bullets": [],
    "feature-cards": ["items"],
    "requirement-understanding": ["categories"],
    "coverage-analysis": [],
    "core-scenario": [],
    "pricing-comparison": [],
    "implementation-plan": [],
    "agenda": [],
}

COVER_KEYS = {"title", "subtitle", "date", "version", "confidential"}
THEME_KEYS = {
    "primary", "secondary", "accent", "accent_light", "bg", "bg_light",
    "bg_card", "text_light", "text_dark", "text_gray", "success",
    "warning", "meituan", "douyin", "font",
}


# ── 数据结构 ──────────────────────────────────────────

@dataclass
class ValidationIssue:
    severity: str
    rule: str
    message: str


@dataclass
class ValidationResult:
    path: str
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)


# ── 校验器 ────────────────────────────────────────────

class PPTPackageValidator:

    def validate_file(self, path: Path) -> ValidationResult:
        result = ValidationResult(path=str(path), valid=True)

        if not path.exists():
            result.issues.append(ValidationIssue("error", "EXISTS", "文件不存在"))
            result.valid = False
            return result

        try:
            raw = path.read_text(encoding="utf-8")
        except Exception as e:
            result.issues.append(ValidationIssue("error", "READ", f"读取失败: {e}"))
            result.valid = False
            return result

        data = self._safe_yaml(result, raw)
        if data is None:
            result.valid = False
            return result

        mode = self._check_mode(result, data)
        self._check_base_ppt(result, data)
        self._check_cover(result, data)
        self._check_theme(result, data)
        self._check_toc(result, data, mode)
        self._check_slides(result, data, mode)
        self._check_output(result, data, path)

        result.valid = not any(i.severity == "error" for i in result.issues)
        return result

    def _safe_yaml(self, result: ValidationResult, raw: str) -> dict[str, Any] | None:
        try:
            data = yaml.safe_load(raw)
            if data is None:
                result.issues.append(ValidationIssue("error", "YAML_EMPTY", "YAML 为空"))
                return None
            if not isinstance(data, dict):
                result.issues.append(ValidationIssue(
                    "error", "YAML_TYPE", "顶层必须是 YAML 字典"
                ))
                return None
            return data
        except yaml.YAMLError as e:
            result.issues.append(ValidationIssue("error", "YAML_PARSE", f"YAML 解析失败: {e}"))
            return None

    def _check_mode(self, result: ValidationResult, data: dict[str, Any]) -> str:
        mode = data.get("mode", "")
        if not mode:
            has_sections_list = isinstance(data.get("sections"), list)
            has_slides = "slides" in data
            if has_sections_list:
                mode = "intro"
            elif has_slides and not has_sections_list:
                mode = "proposal"
            result.issues.append(ValidationIssue(
                "warning", "MODE_INFERRED",
                f"mode 未指定，推断为 '{mode}'"
            ))
            return mode

        if mode not in VALID_MODES:
            result.issues.append(ValidationIssue(
                "error", "MODE_INVALID",
                f"mode='{mode}' 无效，可选: {', '.join(sorted(VALID_MODES))}"
            ))
            return "proposal"

        return mode

    def _check_base_ppt(self, result: ValidationResult, data: dict[str, Any]):
        base = data.get("base_ppt", "")
        if not base:
            result.issues.append(ValidationIssue(
                "error", "BASE_MISSING", "base_ppt 缺失（参考 PPT 路径必填）"
            ))
            return

        base_path = self._expand_path(base)
        if not Path(base_path).exists():
            result.issues.append(ValidationIssue(
                "error", "BASE_EXISTS",
                f"base_ppt 文件不存在: {base}"
            ))

    def _check_cover(self, result: ValidationResult, data: dict[str, Any]):
        cover = data.get("cover")
        if cover is None:
            return
        if not isinstance(cover, dict):
            result.issues.append(ValidationIssue("error", "COVER_TYPE", "cover 必须是字典"))
            return

        unknown = set(cover.keys()) - COVER_KEYS
        if unknown:
            result.issues.append(ValidationIssue(
                "warning", "COVER_KEYS",
                f"cover 含未知字段: {', '.join(sorted(unknown))}"
            ))

    def _check_theme(self, result: ValidationResult, data: dict[str, Any]):
        theme = data.get("theme")
        if theme is None:
            return
        if not isinstance(theme, dict):
            result.issues.append(ValidationIssue("error", "THEME_TYPE", "theme 必须是字典"))
            return

        for key in ("primary", "secondary", "accent"):
            val = theme.get(key, "")
            if val and not self._is_valid_hex(val):
                result.issues.append(ValidationIssue(
                    "warning", "THEME_COLOR",
                    f"theme.{key}='{val}' 不是有效十六进制颜色（#RRGGBB）"
                ))

        unknown = set(theme.keys()) - THEME_KEYS
        if unknown:
            result.issues.append(ValidationIssue(
                "warning", "THEME_KEYS",
                f"theme 含未知字段: {', '.join(sorted(unknown))}"
            ))

    def _check_toc(self, result: ValidationResult, data: dict[str, Any], mode: str):
        toc = data.get("toc")
        if toc is None:
            sections = data.get("sections")
            if isinstance(sections, dict):
                toc = sections
            else:
                return

        if not isinstance(toc, dict):
            result.issues.append(ValidationIssue("error", "TOC_TYPE", "toc 必须是字典"))
            return

        titles = toc.get("titles", [])
        if titles:
            if not isinstance(titles, list):
                result.issues.append(ValidationIssue("error", "TOC_TITLES_TYPE", "toc.titles 必须是列表"))
                return
            if len(titles) > MAX_TOC_TITLES:
                result.issues.append(ValidationIssue(
                    "warning", "TOC_TITLES_COUNT",
                    f"toc.titles 有 {len(titles)} 项，参考 PPT 最多支持 {MAX_TOC_TITLES} 个目录标题"
                ))
            empty_titles = [i for i, t in enumerate(titles) if not str(t).strip()]
            if empty_titles:
                result.issues.append(ValidationIssue(
                    "warning", "TOC_TITLES_EMPTY",
                    f"toc.titles[{empty_titles[0]}] 为空"
                ))

    def _check_slides(self, result: ValidationResult, data: dict[str, Any], mode: str):
        sections = data.get("sections")
        top_slides = data.get("slides")

        if isinstance(sections, list):
            for i, sec in enumerate(sections):
                if not isinstance(sec, dict):
                    result.issues.append(ValidationIssue(
                        "error", "SECTION_TYPE",
                        f"sections[{i}] 必须是字典"
                    ))
                    continue
                sec_slides = sec.get("slides", [])
                for j, slide_cfg in enumerate(sec_slides):
                    self._check_slide_cfg(result, slide_cfg, f"sections[{i}].slides[{j}]")
        elif mode in ("intro", "tender") and sections is None:
            result.issues.append(ValidationIssue(
                "warning", "SECTIONS_MISSING",
                f"mode='{mode}' 建议定义 sections（自定义幻灯片）"
            ))

        if isinstance(top_slides, list):
            for i, slide_cfg in enumerate(top_slides):
                self._check_slide_cfg(result, slide_cfg, f"slides[{i}]")

    def _check_slide_cfg(self, result: ValidationResult, cfg: Any, context: str):
        if not isinstance(cfg, dict):
            result.issues.append(ValidationIssue(
                "error", "SLIDE_CFG_TYPE",
                f"{context} 必须是字典"
            ))
            return

        slide_type = cfg.get("type", "")
        if not slide_type:
            result.issues.append(ValidationIssue(
                "error", "SLIDE_TYPE_MISSING",
                f"{context} 缺少 type 字段"
            ))
            return

        if slide_type not in VALID_SLIDE_TYPES:
            result.issues.append(ValidationIssue(
                "error", "SLIDE_TYPE_INVALID",
                f"{context} type='{slide_type}' 无效，可选: {', '.join(sorted(VALID_SLIDE_TYPES))}"
            ))
            return

        required = SLIDE_REQUIRED_FIELDS.get(slide_type, [])
        for field_name in required:
            val = cfg.get(field_name)
            if val is None or (isinstance(val, (list, str)) and not val):
                result.issues.append(ValidationIssue(
                    "warning", "SLIDE_FIELD_MISSING",
                    f"{context} type='{slide_type}' 建议包含 {field_name}"
                ))

        if slide_type == "feature-cards":
            items = cfg.get("items", [])
            if isinstance(items, list):
                for k, item in enumerate(items):
                    if isinstance(item, dict):
                        if not item.get("title"):
                            result.issues.append(ValidationIssue(
                                "warning", "CARD_TITLE",
                                f"{context}.items[{k}] 缺少 title"
                            ))

    def _check_output(self, result: ValidationResult, data: dict[str, Any], yaml_path: Path):
        output = data.get("output", "")
        if not output:
            return
        output_path = Path(self._expand_path(output))
        if output_path.parent and not output_path.parent.exists():
            result.issues.append(ValidationIssue(
                "warning", "OUTPUT_DIR",
                f"output 目录不存在: {output_path.parent}"
            ))

    def _expand_path(self, path_str: str) -> str:
        lanlnk = os.environ.get("LANLNK_BASE", "")
        return path_str.replace("$LANLNK_BASE", lanlnk)

    def _is_valid_hex(self, val: str) -> bool:
        h = val.lstrip("#")
        return len(h) == 6 and all(c in "0123456789abcdefABCDEF" for c in h)


# ── CLI ───────────────────────────────────────────────

def format_result(result: ValidationResult, verbose: bool = False) -> str:
    icon = "✅" if result.valid else "❌"
    lines = [f"  {icon} {result.path}"]

    if verbose or not result.valid:
        for issue in result.issues:
            sev_icon = "🔴" if issue.severity == "error" else "🟡"
            lines.append(f"    {sev_icon} [{issue.rule}] {issue.message}")
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
    parser = argparse.ArgumentParser(description="PPT 内容包 Schema 校验器")
    parser.add_argument("path", help="要校验的 YAML 文件或目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示所有检查结果")

    args = parser.parse_args()
    target = Path(args.path)

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(
            p for p in target.rglob("*.yaml")
            if "ppt" in p.name.lower() or "_pptx" in p.name.lower() or "tender" in p.name.lower()
        )
        if not files:
            files = sorted(target.rglob("*.yaml"))
    else:
        print(f"错误: 路径不存在: {target}", file=sys.stderr)
        sys.exit(1)

    if not files:
        if args.json:
            print(json.dumps({"total": 0, "passed": 0, "failed": 0, "results": []}))
        else:
            print("未找到 YAML 配置文件")
        sys.exit(0)

    validator = PPTPackageValidator()
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
                        {"severity": i.severity, "rule": i.rule, "message": i.message}
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
