"""implementation-return 存量 JSON 的兼容读取（过渡态，stdlib only）。

背景：`references/product-governance/implementation-return.schema.json` 是目标契约，
但 27 件真实回执（lnkcre/lnkcrm/lnkreport）存在形态漂移——changes[] 标识键
（change_id/change/id）混用、feature_commit(s) 标量/列表混用、trace_ids
数组/字符串/对象/缺失、proposed_updates 字符串/结构体/缺失、review_status
缺失或野值。本 helper 只做「兼容读取 + 归一化视图 + drift 警告」，不迁移、
不写回任何文件。

trace_ids 对象形态的确定性表示：对每个顶层键展开为 ``'.'.join(path)`` 风格的
稳定字符串（如 ``{"waves": ["W1-a"]}`` → ``["waves.W1-a"]``）。选择 dotted path
是因为它与 OpenSpec/治理文档里既有的 trace 写法（``changes.<id>``）一致，且对
标量与列表叶子统一、无歧义（JSON 对象保序，输出顺序即键序，确定性有保障）。

proposed_updates 两种结构体键集的归一映射：{target, update[, status]}（lnkcre/
lnkcrm 风格）原键对应填入；{destination_layer, summary, status}（lnkreport/
lnkchat 风格）按 destination_layer→target、summary→update、status→disposition
对应填入；status 缺省补 "proposed"。changes[].status 中 archived 与 done 同义，
统一折叠为 done。findings 变体（无 changes、以 findings/reconciliation_ids 承载）
不套 changes 模型、不伪造 changes，只记 warning。

用法：
    view, warnings = normalize_implementation_return(raw_dict)
"""

from __future__ import annotations

from typing import Any

# 契约词表（与 schema enum 保持一致；rejected 表达否决，incomplete 已移除，
# 缺失信息由 warning 表达）。
REVIEW_STATUS_VOCAB: frozenset[str] = frozenset(
    {"pending", "reviewed", "absorbed", "rejected"}
)

# change 标识键的识别优先级（契约名在前，历史别名在后）。
_CHANGE_ID_KEYS: tuple[str, ...] = ("change_id", "change", "id")

_SCALAR = (str, int, float, bool)


def _flatten_trace_dict(value: dict[str, Any], prefix: tuple[str, ...] = ()) -> list[str]:
    out: list[str] = []
    for key, item in value.items():
        path = (*prefix, str(key))
        if isinstance(item, dict):
            out.extend(_flatten_trace_dict(item, path))
        elif isinstance(item, (list, tuple)):
            for leaf in item:
                if isinstance(leaf, _SCALAR):
                    out.append(".".join((*path, str(leaf))))
                else:
                    out.append(".".join(path))
        elif isinstance(item, _SCALAR):
            out.append(".".join((*path, str(item))))
        else:
            out.append(".".join(path))
    return out


def _as_commit_list(raw: Any, warnings: list[str], label: str) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, _SCALAR):
        return [str(raw)]
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw if isinstance(x, _SCALAR)]
    warnings.append(f"{label}: 无法识别的提交形态 {type(raw).__name__}，已忽略")
    return []


def _normalize_changes(raw: Any, warnings: list[str]) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        warnings.append(f"changes: 非 list 形态 {type(raw).__name__}，已忽略")
        return []
    normalized: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            warnings.append(f"changes[{i}]: 非 object 形态，已忽略")
            continue
        change_id: str | None = None
        for key in _CHANGE_ID_KEYS:
            if isinstance(item.get(key), str) and item[key]:
                change_id = item[key]
                break
        if change_id is None:
            preview = str(item)[:60]
            warnings.append(f"changes[{i}]: 未识别到 change_id/change/id 标识键（{preview}…）")
        feature_commits: list[str] = []
        if "feature_commits" in item:
            feature_commits = _as_commit_list(item["feature_commits"], warnings, f"changes[{i}].feature_commits")
        elif "feature_commit" in item:
            feature_commits = _as_commit_list(item["feature_commit"], warnings, f"changes[{i}].feature_commit")
        entry: dict[str, Any] = {"change_id": change_id, "feature_commits": feature_commits}
        if "supporting_commits" in item:
            entry["supporting_commits"] = _as_commit_list(
                item["supporting_commits"], warnings, f"changes[{i}].supporting_commits"
            )
        # done ≡ archived 同义（2026-10-21 第二波盘点口径），统一折叠为 done。
        raw_status = item.get("status")
        if raw_status is not None:
            entry["status"] = "done" if raw_status == "archived" else raw_status
        normalized.append(entry)
    return normalized


def _normalize_proposed_update_object(item: dict[str, Any]) -> dict[str, Any]:
    """两种结构体键集统一映射为 {target, update, disposition}（status 缺省 proposed）。"""
    target = item.get("target", item.get("destination_layer"))
    update = item.get("update", item.get("summary"))
    disposition = item.get("status", item.get("disposition"))
    return {
        "target": target,
        "update": update,
        "disposition": "proposed" if disposition is None else disposition,
    }


def _normalize_proposed_updates(raw: Any, warnings: list[str]) -> list[Any]:
    if raw is None:
        warnings.append("proposed_updates: 缺失")
        return []
    if isinstance(raw, str):
        return [{"target": None, "update": raw, "disposition": None}]
    if not isinstance(raw, list):
        warnings.append(f"proposed_updates: 非 list/str 形态 {type(raw).__name__}，已忽略")
        return []
    normalized: list[Any] = []
    for i, item in enumerate(raw):
        if isinstance(item, str):
            normalized.append({"target": None, "update": item, "disposition": None})
        elif isinstance(item, dict):
            normalized.append(_normalize_proposed_update_object(item))
        else:
            warnings.append(f"proposed_updates[{i}]: 非 str/object 形态，已忽略")
    return normalized


def normalize_implementation_return(ret: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """归一化一件 implementation-return 存量 JSON。

    返回 (normalized_view, warnings)。view 只含归一化后的可校验字段；
    warnings 记录全部 drift（标识键别名、trace_ids 形态、缺失、review_status
    野值/缺失、schema_version 非目标值等）。本函数只读输入，不写回文件。
    """
    warnings: list[str] = []
    view: dict[str, Any] = {}

    for key in ("return_id", "product_id", "target_repo", "origin_flow", "source_revision"):
        if ret.get(key) is not None:
            view[key] = ret[key]
    # schema_version 统一折叠为 "1.0"（第二波盘点口径：'1.0'/'1'/数字 1/'implementation-return/1.x'/缺失）。
    if "schema_version" not in ret or ret["schema_version"] is None:
        warnings.append("schema_version: 缺失，已折叠为 '1.0'")
    elif ret["schema_version"] != "1.0":
        warnings.append(f"schema_version: 非目标值 {ret['schema_version']!r}，已折叠为 '1.0'")
    view["schema_version"] = "1.0"

    # review_status：词表内原样通过；野值/缺失只记 warning，不进 view
    # （不猜测野值到词表的映射，保留原文于 warning 供 owner 裁决）。
    review_status = ret.get("review_status")
    if review_status is None:
        warnings.append("review_status: 缺失")
    elif review_status in REVIEW_STATUS_VOCAB:
        view["review_status"] = review_status
    else:
        warnings.append(f"review_status: 野值 {review_status!r}（不在词表 {sorted(REVIEW_STATUS_VOCAB)}），未猜测映射")

    # trace_ids：数组保留，字符串包一层，对象展开为 dotted-path 字符串。
    trace_raw = ret.get("trace_ids")
    if trace_raw is None:
        warnings.append("trace_ids: 缺失")
        view["trace_ids"] = []
    elif isinstance(trace_raw, str):
        warnings.append("trace_ids: 字符串形态已包为单元素列表")
        view["trace_ids"] = [trace_raw]
    elif isinstance(trace_raw, dict):
        warnings.append("trace_ids: 对象形态已展开为 dotted-path 字符串列表")
        view["trace_ids"] = _flatten_trace_dict(trace_raw)
    elif isinstance(trace_raw, list):
        view["trace_ids"] = [str(x) if isinstance(x, _SCALAR) else str(x) for x in trace_raw]
    else:
        warnings.append(f"trace_ids: 无法识别的形态 {type(trace_raw).__name__}")
        view["trace_ids"] = []

    view["changes"] = _normalize_changes(ret.get("changes"), warnings)
    # findings 变体（无 changes、以 findings/reconciliation_ids/verification_refs 承载）：
    # 不套 changes 模型、不伪造 changes，只记 warning。
    if not view["changes"] and isinstance(ret.get("findings"), list) and ret["findings"]:
        warnings.append("findings-variant: 无 changes 而以 findings 承载，不套 changes 模型")
    view["proposed_updates"] = _normalize_proposed_updates(ret.get("proposed_updates"), warnings)

    # 原样透传的常见存量字段（view 允许 additionalProperties，透传不产生警告）。
    for key in ("verification_refs", "open_spec_change_id", "scan_coverage"):
        if ret.get(key) is not None:
            view[key] = ret[key]

    return view, warnings
