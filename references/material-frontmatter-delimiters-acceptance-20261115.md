# Verification — fix-material-frontmatter-delimiters

日期：2026-11-15。验收人：独立 verify 子代理（openspec-verify-change 工作流）。实施会话：Fixer subagent。
本件为独立复验记录（非 apply 会话自查），全部证据当日新鲜取证；原始 /tmp 证据 volatile，关键输出逐字转录于下。

## 1. 基线与哈希（observed）

- 基线副本（改动前）：`/tmp/opencode/fmfdd-baseline/validate_material.py`
  sha256 `99d299348894d10eb9c3d83a9c39bfa4c91810e8b2151ed554f9ad3bfecb67a7`（与 evidence.md 声明一致，复算核实）
- 当前实现：`skills/business/material-importer/scripts/validate_material.py`
  sha256 `39a266b86a76dfe7075069158c36f74489563016c9201dc59c356ec897c48fd3`

## 2. 命令与退出码（本会话实跑）

| 命令（cwd） | exit | 结果 |
|---|---|---|
| `uv run pytest tests/test_validate_material.py -q`（material-importer） | 0 | **15 passed** |
| `uv run pytest tests/ -q`（material-importer，独立全量重跑） | 0 | **392 passed in 20.67s** |
| `python3 /tmp/opencode/fmfdd-baseline/compare_frontmatter.py`（独立重跑全量只读对比） | 0 | **TOTAL_MD=1429 DIFFS=0**（输出逐字转录于下） |
| `openspec list --json` | 0 | fix-material-frontmatter-delimiters：7/7 tasks，status complete |
| `openspec status --change fix-material-frontmatter-delimiters --json` | 0 | 全部 artifact done（proposal/specs/design/tasks），planningHome.root=/opt/code/skill |

## 3. 关键输出逐字转录（防 /tmp 丢失）

红跑（实施前，`/tmp/opencode/fmfdd-baseline/red_run.log` 尾部，原始保留未删）：

```
FAILED tests/test_validate_material.py::FrontmatterDelimiterTest::test_four_dashes_opening_is_missing_frontmatter
FAILED tests/test_validate_material.py::FrontmatterDelimiterTest::test_quoted_scalar_with_dashes_preserved
FAILED tests/test_validate_material.py::FrontmatterDelimiterTest::test_unquoted_scalar_with_dashes_preserved
3 failed, 12 passed in 0.08s
```

全量绿跑（`full_suite.log`）：`392 passed in 19.89s`。
真实素材对比（`compare_result.log`，本会话独立重跑结果一致）：

```
TOTAL_MD=1429 DIFFS=0
```

对比辅助脚本（`compare_frontmatter.py`，importlib 双载基线/新版逐文件比较 `(data, error)`）：

```python
#!/usr/bin/env python3
"""只读对比基线/新版 parse_frontmatter 在 lanlnk materials 全量上的逐文件结果。"""
import importlib.util
import sys
from pathlib import Path

MATERIALS = Path("/opt/code/docs/lanlnk/materials")

def load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

old = load("/tmp/opencode/fmfdd-baseline/validate_material.py", "vm_old")
new = load("/opt/code/skill/skills/business/material-importer/scripts/validate_material.py", "vm_new")

diffs = []
files = sorted(MATERIALS.rglob("*.md"))
for f in files:
    d_old, e_old = old.parse_frontmatter(str(f))
    d_new, e_new = new.parse_frontmatter(str(f))
    if d_old == d_new and e_old == e_new:
        continue
    diffs.append((f, d_old, e_old, d_new, e_new))

print(f"TOTAL_MD={len(files)} DIFFS={len(diffs)}")
for f, d_old, e_old, d_new, e_new in diffs:
    print(f"FILE={f}")
    print(f"  OLD error={e_old!r} data={d_old!r}")
    print(f"  NEW error={e_new!r} data={d_new!r}")
```

CLI 全量（实施会话，`uv run <script> /opt/code/docs/lanlnk/materials --json` 双版本）：exit 0，
summary 均 `{total:1395, valid:1395, invalid:0}`；record 级 19 条差异经核查全部为 warnings 数组
迭代序翻转（DATE_FIELDS/REQUIRED_FIELDS 为 set，PYTHONHASHSEED 跨进程不定，两版本共有），
排序归一后 old-vs-new 差异 0——与本次改动无关。

## 4. 实现 ↔ 需求/场景映射

实现：`scripts/validate_material.py:49`（`_DELIMITER_LINE_RE = re.compile(r"^---[ \t]*\r?$")`）、
`:52-54`（`_is_delimiter_line`）、`:65-79`（逐行开/闭 delimiter 识别 + yaml_block 拼接）、
`:81-87`（YAML 解析错误 / 非 mapping 文案原文不动）。

回归组 `tests/test_validate_material.py:158-260`（`FrontmatterDelimiterTest`，10 用例）：

| Spec 场景（delta spec） | 回归用例（行号） |
|---|---|
| 未加引号标量值内含三连字符 | `test_unquoted_scalar_with_dashes_preserved` :170 |
| 加引号标量值内含三连字符 | `test_quoted_scalar_with_dashes_preserved` :185 |
| 闭 delimiter 行尾空白 | `test_closing_delimiter_trailing_whitespace` :218 |
| CRLF 文件 | `test_crlf_frontmatter` :208 |
| 缺少开分隔符（含 `----` 例外 2） | `test_missing_open_delimiter` :226 + `test_four_dashes_opening_is_missing_frontmatter` :252 |
| frontmatter 块未闭合 | `test_unclosed_block` :232 |
| 非法 YAML / 非 mapping | `test_invalid_yaml` :238 + `test_non_mapping` :246 |
| （正常 LF 基线） | `test_normal_lf_frontmatter` :200 |

设计遵循：Decision 1–4 全部落实（独立成行匹配、首行收紧含 `----` 归类、错误文案不动、
单函数改动）；`fix_frontmatter.py` 未触碰（Non-Goal）；`git status` 改动仅
validate_material.py + test_validate_material.py（M）+ openspec/changes/（untracked）。

## 5. 核查结论

- CRITICAL：0；WARNING：0；SUGGESTION：0；Not verified：0（全部检查有证据）。
- Completeness 7/7 tasks；Correctness 2 ADDED 需求全映射；Coherence 设计全遵循、模式一致（模块级正则 + docstring 中文风格与仓内一致）。
- 结论：**All checks passed. Ready for archive.**
