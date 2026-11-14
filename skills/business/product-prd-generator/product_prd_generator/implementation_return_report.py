"""implementation-return 严格校验三段报告（source / normalization / normalized）。

背景（change align-governance-handoff-contracts A4，2026-11-13）：lnkcard IC1 实践
中源件 2 errors、docs 规范化后通过，需要机械化的三段可区分输出，避免「规范化
通过」被冒称为「源件严格通过」。本模块是相邻报告模块：

- 复用 ``implementation_return_compat.normalize_implementation_return``（stdlib-only，
  API 不变，不迁移不写回）；
- 本模块自身依赖 jsonschema（pyproject dev 依赖，不进 runtime dependencies）；
  缺依赖时抛 ``ReportDependencyError``（明确的依赖错误，不是校验通过/失败）；
- schema 解析走本地 referencing Registry（注册 references/product-governance/
  全部 *.schema.json），无网络请求；
- 三段各自独立：source 与 normalized 都允许失败，报告全部剩余错误；规范化
  不补造 review_owner / verification_refs / change 标识等任何事实。

CLI（退出码语义：source 是唯一裁决输入）::

    uv run python -m product_prd_generator.implementation_return_report <return.json>

    0 = source 严格校验通过（即使 normalized 另有结果）
    1 = source 严格校验失败（即使 normalized 通过，也不冒称源件通过）
    2 = 依赖缺失 / 输入文件不可读或非 object 等操作性错误
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from product_prd_generator.implementation_return_compat import (
    normalize_implementation_return,
)

CONTRACTS_DIR: Path = Path(__file__).resolve().parents[1] / "references" / "product-governance"
SCHEMA_NAME = "implementation-return.schema.json"

# 归一化动作说明中用于区分「键缺失」与「值为 None」的哨兵（仅出现在报告中，
# 不进 normalized view，不写回任何文件）。
_MISSING = "<missing>"


class ReportDependencyError(RuntimeError):
    """报告模块依赖（jsonschema/referencing）不可用——操作性错误，非校验结论。"""


def _load_validator() -> Any:
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        from referencing.jsonschema import DRAFT202012
    except ImportError as exc:  # pragma: no cover - 环境相关
        raise ReportDependencyError(
            "implementation_return_report 依赖 jsonschema（pyproject "
            "[project.optional-dependencies] dev extra）。安装/运行："
            "uv sync --extra dev 或 uv run --extra dev python -m …。"
            "该错误是操作性依赖错误，不代表任何校验通过或失败。"
        ) from exc

    registry: Any = Registry()
    for schema_path in sorted(CONTRACTS_DIR.glob("*.schema.json")):
        resource = Resource.from_contents(
            json.loads(schema_path.read_text(encoding="utf-8")),
            default_specification=DRAFT202012,
        )
        schema_id = resource.id()
        if schema_id is not None:
            registry = registry.with_resource(schema_id, resource)
    schema = json.loads((CONTRACTS_DIR / SCHEMA_NAME).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=registry)


def _path_of(error: Any) -> str:
    parts = list(error.absolute_path)
    if not parts:
        return "$"
    out = "$"
    for part in parts:
        out += f"[{part}]" if isinstance(part, int) else f".{part}"
    return out


def _validate_section(validator: Any, value: Any) -> dict[str, Any]:
    errors = [
        {"path": _path_of(e), "message": e.message}
        for e in sorted(validator.iter_errors(value), key=lambda e: (list(e.absolute_path), e.message))
    ]
    return {"ok": not errors, "error_count": len(errors), "errors": errors}


def _source_value(raw: dict[str, Any], key: str) -> Any:
    if key not in raw:
        return _MISSING
    return raw[key]


# 已知字段的语义化动作标签（可选，增强可读性；没有标签的字段用通用分类）。
_SPECIAL_LABELS: dict[str, str] = {
    "schema_version": "folded-to-'1.0'",
    "review_status": "wild-or-missing-value-not-mapped",
    "trace_ids": "shape-normalized",
    "changes": "identifier/commit-keys-normalized",
    "proposed_updates": "shapes-normalized",
}


def _summarize_actions(raw: dict[str, Any], view: dict[str, Any]) -> list[dict[str, Any]]:
    """source→view 的确定性逐键通用 diff（仅事实对照，不补造字段）。

    覆盖两侧行（键）的全集：任何被投影丢弃的键（如 review_owner / findings /
    phase_record 所在的 changes 结构差异）都会出现为 ``projected-out``，不静默
    消失。每条动作携带：

    - ``source_present`` / ``view_present``：布尔存在性——用于区分「键缺失」与
      「字面量 '<missing>' 字符串值」（哨兵 ``source_value``/``view_value`` 在
      缺失时也写 '<missing>'，存在性布尔才是权威判据）；
    - ``source_value`` / ``view_value``：原始值 / 视图值（缺失时为哨兵）。

    动作分类：``projected-out``（源有视图无）/ ``added-by-normalization``
    （视图有源无）/ ``changed``（两侧都在且值不同，已知字段用语义化标签）。
    两侧都在且值相等的键不产生动作。
    """
    actions: list[dict[str, Any]] = []
    for key in sorted(set(raw) | set(view)):
        source_present = key in raw
        view_present = key in view
        source_value = raw[key] if source_present else _MISSING
        view_value = view[key] if view_present else _MISSING
        if source_present and not view_present:
            action = "projected-out"
        elif not source_present and view_present:
            action = "added-by-normalization"
        elif source_value != view_value:
            action = "changed"
        else:
            continue  # 未变化，无动作
        entry: dict[str, Any] = {
            "field": key,
            "action": action,
            "source_present": source_present,
            "view_present": view_present,
            "source_value": source_value,
            "view_value": view_value,
        }
        if key in _SPECIAL_LABELS:
            entry["label"] = _SPECIAL_LABELS[key]
        actions.append(entry)
    return actions


def strict_validation_report(raw: dict[str, Any]) -> dict[str, Any]:
    """对一件 implementation-return 原始 JSON 产出三段报告。

    返回结构::

        {
          "schema": "implementation-return.schema.json",
          "source":  {"ok", "error_count", "errors": [{"path", "message"}, …]},
          "normalization": {"warnings": […], "actions": [{"field", "action",
                                                          "source_value", "view_value"}, …]},
          "normalized": {"ok", "error_count", "errors": […]}
        }

    source 校验独立的深拷贝原件；normalized 校验 compat helper 的归一化视图，
    允许仍失败（剩余错误如实列出）。warnings/actions 保留原始值，不猜测映射、
    不补造事实。本函数只读输入，不写回文件。
    """
    if not isinstance(raw, dict):
        raise TypeError(f"implementation-return 必须是 JSON object，收到 {type(raw).__name__}")

    validator = _load_validator()
    source_value = deepcopy(raw)
    view, warnings = normalize_implementation_return(source_value)
    return {
        "schema": SCHEMA_NAME,
        "source": _validate_section(validator, source_value),
        "normalization": {
            "warnings": list(warnings),
            "actions": _summarize_actions(source_value, view),
        },
        "normalized": _validate_section(validator, view),
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print(json.dumps({
            "operational_error": "用法: python -m product_prd_generator.implementation_return_report <return.json>",
        }, ensure_ascii=False))
        return 2

    path = Path(args[0])
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"operational_error": f"输入文件读取/解析失败: {exc}"}, ensure_ascii=False))
        return 2
    if not isinstance(raw, dict):
        print(json.dumps({
            "operational_error": f"implementation-return 必须是 JSON object，收到 {type(raw).__name__}",
        }, ensure_ascii=False))
        return 2

    try:
        report = strict_validation_report(raw)
    except ReportDependencyError as exc:
        print(json.dumps({"operational_error": str(exc)}, ensure_ascii=False))
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        # schema 文件读取/解析失败是操作性错误（exit 2），不是校验结论，也不 traceback
        print(json.dumps({
            "operational_error": f"schema 契约文件读取/解析失败: {exc}",
        }, ensure_ascii=False))
        return 2

    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    # 退出码只看 source：normalized 通过不能追溯为源件通过（A4 红线）。
    return 0 if report["source"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
