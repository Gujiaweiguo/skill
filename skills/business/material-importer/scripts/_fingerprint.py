"""转换指纹共享状态机（convert_excel / convert_doc 共用，纯 stdlib）。

七态状态机 + 模式×状态行为矩阵（设计 D2/D4）的唯一权威实现；两个转换脚本
按本模块返回的 Decision 行事，禁止各自复制矩阵逻辑。

指纹要素（RecordFactors，来自 manifest record 或 MD 头解析）：
  source_sha256 / options（有效选项快照）/ converter_version / outputs（预期
  输出清单 + 各输出 sha256）/ fingerprint_format（元数据格式版本）。
缺任何指纹要素 → unknown（旧产物不判 up-to-date，也不强制重转）。

版本号分离（设计 D6）：FINGERPRINT_FORMAT 是指纹元数据格式版本，独立于
各脚本的 EXTRACTOR_VERSION（转换内容逻辑代际），互不倒推。
"""

from __future__ import annotations

from dataclasses import dataclass, field

FINGERPRINT_FORMAT = 1

# 状态常量（七态；conflict = output-modified ∧ 任一 changed）
STATE_UNKNOWN = "unknown"
STATE_UP_TO_DATE = "up-to-date"
STATE_SOURCE_CHANGED = "source-changed"
STATE_OPTIONS_CHANGED = "options-changed"
STATE_CONVERTER_CHANGED = "converter-changed"
STATE_OUTPUT_MISSING = "output-missing"
STATE_OUTPUT_MODIFIED = "output-modified"
STATE_CONFLICT = "conflict"

# 模式常量
MODE_DEFAULT = "default"              # 旧默认命令（无旗标）
MODE_CHECK = "check"                  # --check（零业务写入）
MODE_SKIP_UP_TO_DATE = "skip-up-to-date"  # --skip-up-to-date（opt-in）

_CHANGED_PRIORITY = (
    STATE_SOURCE_CHANGED,
    STATE_OPTIONS_CHANGED,
    STATE_CONVERTER_CHANGED,
)

_HEX = set("0123456789abcdef")


def valid_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in _HEX for c in value)
    )


@dataclass
class RecordFactors:
    """上次转换记录的指纹要素；任一为 None = 指纹不完整 → unknown。"""

    source_sha256: str | None = None
    options: dict | None = None
    converter_version: int | str | None = None
    outputs: list[dict] | None = None  # [{path, sha256}]
    fingerprint_format: int | None = None


@dataclass
class Observed:
    """当前观测：当前源哈希、当前有效选项、当前转换器版本、实际存在的输出及哈希。"""

    source_sha256: str | None = None
    options: dict | None = None
    converter_version: int | str | None = None
    existing_outputs: list[dict] | None = None  # [{path, sha256}]（磁盘上存在且已哈希）


@dataclass
class Decision:
    """矩阵裁决：action ∈ convert / skip / report；protected=人工修改检出被保留。

    missing_paths / modified_paths：主保护状态之外的叠加诊断（修复 6）——
    modified 非空（含 conflict）时任何模式不转换补缺失，两侧清单随报告输出。
    """

    action: str
    protected: bool = False
    note: str = ""
    state: str = ""
    missing_paths: list = field(default_factory=list)
    modified_paths: list = field(default_factory=list)


def _valid_outputs(outputs: object) -> bool:
    if not isinstance(outputs, list) or not outputs:
        return False
    for o in outputs:
        if not isinstance(o, dict):
            return False
        if not isinstance(o.get("path"), str) or not o.get("path"):
            return False
        if not valid_sha256(o.get("sha256")):
            return False
    return True


def evaluate_detail(record: RecordFactors | None, observed: Observed) -> dict:
    """结构化状态评估（修复 6）：{state, missing_paths, modified_paths}。

    主状态语义与 evaluate() 完全一致（evaluate = evaluate_detail(...)["state"]
    的兼容签名）；missing/modified 是叠加诊断，不改变主状态优先级——
    modified + missing 并存时 state 仍为 output-modified/conflict，但两侧
    清单同时携带，行为层"任何模式不转换补缺失"由矩阵保证（modified 非空
    即落入保护态）。
    """
    state = STATE_UNKNOWN
    missing_paths: list = []
    modified_paths: list = []

    valid = (
        record is not None
        and record.fingerprint_format in (None, FINGERPRINT_FORMAT)
        and valid_sha256(getattr(record, "source_sha256", None))
        and getattr(record, "options", None) is not None
        and getattr(record, "converter_version", None) is not None
        and _valid_outputs(getattr(record, "outputs", None))
    )
    if valid:
        assert record is not None
        changed: list[str] = []
        if observed.source_sha256 != record.source_sha256:
            changed.append(STATE_SOURCE_CHANGED)
        if (record.options or {}) != (observed.options or {}):
            changed.append(STATE_OPTIONS_CHANGED)
        if str(record.converter_version) != str(observed.converter_version):
            changed.append(STATE_CONVERTER_CHANGED)

        present = {
            o.get("path"): o.get("sha256")
            for o in (observed.existing_outputs or [])
            if isinstance(o, dict)
        }
        modified = False
        missing = False
        for o in record.outputs:  # type: ignore[union-attr]
            path = o["path"]
            if path not in present:
                missing = True
                missing_paths.append(path)
            elif present[path] != o["sha256"]:
                modified = True
                modified_paths.append(path)

        if modified and changed:
            state = STATE_CONFLICT
        elif modified:
            state = STATE_OUTPUT_MODIFIED
        elif missing:
            state = STATE_OUTPUT_MISSING
        else:
            for changed_state in _CHANGED_PRIORITY:
                if changed_state in changed:
                    state = changed_state
                    break
            else:
                state = STATE_UP_TO_DATE
    return {
        "state": state,
        "missing_paths": missing_paths,
        "modified_paths": modified_paths,
    }


def evaluate(record: RecordFactors | None, observed: Observed) -> str:
    """状态评估纯函数（D4，兼容签名）。主状态语义见 evaluate_detail。"""
    return evaluate_detail(record, observed)["state"]


_PROTECTED_NOTE = (
    "人工修改检出，任何模式不静默覆盖（--force-overwrite-modified 为唯一显式例外）"
)


def _protected_note(
    state: str,
    modified_paths: list | None,
    missing_paths: list | None,
) -> str:
    note = f"{state}: {_PROTECTED_NOTE}"
    if modified_paths:
        note += f"；被修改输出: {', '.join(modified_paths)}"
    if missing_paths:
        note += (
            f"；同时存在缺失输出: {', '.join(missing_paths)}"
            "（不自动补齐；需显式重转（默认模式）才能补齐缺失）"
        )
    return note


def decide_action(
    state: str,
    mode: str,
    *,
    has_existing_output: bool,
    force_overwrite_modified: bool = False,
    missing_paths: list | None = None,
    modified_paths: list | None = None,
) -> Decision:
    """D2 模式×状态行为矩阵逐格权威实现。

    修复 6：modified_paths 非空（含 conflict 叠加）时任何模式不转换补缺失
    （人工编辑保护优先），缺失/修改两侧清单随 Decision 携带。
    修复 8：mode==skip-up-to-date 且 force=True 为不支持的参数组合 →
    ValueError（防御层，调用方应转为用法错误 rc=2）。
    """
    if mode not in (MODE_DEFAULT, MODE_CHECK, MODE_SKIP_UP_TO_DATE):
        raise ValueError(f"unknown mode: {mode!r}")
    if mode == MODE_SKIP_UP_TO_DATE and force_overwrite_modified:
        raise ValueError(
            "--skip-up-to-date 与 --force-overwrite-modified 不支持组合使用；"
            "请用默认转换模式 + --force-overwrite-modified"
        )
    missing = list(missing_paths or [])
    modified = list(modified_paths or [])

    if mode == MODE_CHECK:
        # --check 一律零业务写入，只报告
        return Decision(
            "report", note=state, state=state,
            missing_paths=missing, modified_paths=modified,
        )

    if mode == MODE_DEFAULT:
        if state in (STATE_OUTPUT_MODIFIED, STATE_CONFLICT):
            if force_overwrite_modified:
                return Decision(
                    "convert", note="force-overwrite-modified", state=state,
                    missing_paths=missing, modified_paths=modified,
                )
            return Decision(
                "skip", protected=True,
                note=_protected_note(state, modified, missing), state=state,
                missing_paths=missing, modified_paths=modified,
            )
        # unknown / up-to-date / changed / output-missing → 现状语义（重转覆盖）
        return Decision("convert", note=state, state=state)

    # mode == MODE_SKIP_UP_TO_DATE
    if state == STATE_UP_TO_DATE:
        return Decision("skip", note="up-to-date", state=state)
    if state == STATE_UNKNOWN:
        if has_existing_output:
            return Decision(
                "skip",
                note=(
                    "unknown: 已有输出保留、不自动转换；无指纹无法检测修改，"
                    "需显式重转（去掉 --skip-up-to-date）"
                ),
                state=state,
            )
        # 首转 / output-missing 补齐语义不受 unknown 保留规则拦截
        return Decision(
            "convert", note="unknown: 无已有输出，按首转/补齐处理", state=state
        )
    if state in (STATE_OUTPUT_MODIFIED, STATE_CONFLICT):
        return Decision(
            "skip", protected=True,
            note=_protected_note(state, modified, missing), state=state,
            missing_paths=missing, modified_paths=modified,
        )
    # changed ×3 / output-missing → 重转
    return Decision("convert", note=state, state=state)
