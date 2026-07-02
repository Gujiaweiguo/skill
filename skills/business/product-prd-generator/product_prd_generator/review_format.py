from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .data_model import TableMeta


@dataclass(frozen=True, slots=True)
class ReviewBriefInput:
    project: str
    status_stats: Counter[str]
    requirement_count: int
    tables_by_module: Mapping[str, Sequence[TableMeta]]
    unmatched_table_count: int


def render_review_brief(data: ReviewBriefInput) -> str:
    total_capabilities = sum(data.status_stats.values())
    mapped_tables = sum(len(tables) for tables in data.tables_by_module.values())
    lines = [
        "## 0. 人工 Review 指南",
        "",
        "### 0.1 结论先行",
        "",
        f"本 PRD 用于指导 OpenCode 开发 `{data.project}`，不是竞品资料汇编。Review 时只审查已消化后的业务规则、流程、字段和验收口径，不需要逐张阅读原始表结构。",
        "",
        "**资料主线策略**：以海鼎作为主干，其他资料作为证据叠层。原因：海鼎资料最完整，包含功能手册、操作手册、OCR 表结构和 CRE 4.1.0 数据字典；学伟等资料更适合补充流程、术语、验收口径和设计变体。",
        "",
        "### 0.2 资料分工",
        "",
        "| 来源 | 在 PRD 中的角色 | 使用方式 | 晋升为主干的条件 |",
        "| --- | --- | --- | --- |",
        "| 海鼎 | 主干 / 标准骨架 | 模块结构、标准术语、核心单据、数据字典、字段口径 | 默认主干 |",
        "| 学伟 | 流程补充 / 设计态参考 | 跨模块流程、KPI、开发路线、Prisma 关系模型、PRD 表达方式 | 与海鼎或客户需求一致，或能补足海鼎空白 |",
        "| 明源 / 悦商 / ifca | 竞品变体 | 补充边界场景、替代流程、界面/操作差异 | 多来源重复出现或客户明确要求 |",
        "| 客户需求 | 必审约束 | 明确范围、优先级、交付要求、非功能指标 | 必须进入决策或待确认 |",
        "| 当前代码 / `/opt/code/mi` | 现状基线 | 判断 existing / partial / missing，不定义目标态 | 仅用于差距分析 |",
        "",
        "### 0.3 Review 顺序",
        "",
        "1. 先看本节：确认海鼎主干 + 证据叠层策略是否接受。",
        "2. 再看 `3. 业务模块详细设计`：逐模块审查场景、字段、业务规则、流程、数据模型。",
        "3. 每个模块只做三类判断：必须做 / 变体待定 / 不做。不要在 Review 时回看原始竞品资料。",
        "4. 最后看 `风险与待确认项`、`高优先级需求review清单.md` 和 `pending-items.md`。",
        "",
        "### 0.4 模块 Review 清单",
        "",
        "| 检查项 | 通过标准 |",
        "| --- | --- |",
        "| 目标 | 模块目标能说明业务价值和边界 |",
        "| 场景 | 每个核心场景有触发条件、角色、流程、异常分支 |",
        "| 字段 | 字段来自客户/海鼎/竞品证据，不是主观补写 |",
        "| 规则 | 业务规则可转成开发验收条件 |",
        "| 数据 | 表结构已被提炼成业务含义，不要求 reviewer 看原始表 |",
        "| 来源 | 主干/补充/变体来源清晰可追溯 |",
        "| 决策 | 争议项进入待确认，不混入确定需求 |",
        "",
        "### 0.5 当前规模",
        "",
        "| 指标 | 数量 |",
        "| --- | --- |",
        f"| 能力项 | {total_capabilities} |",
        f"| 需求条目 | {data.requirement_count} |",
        f"| 已映射数据表 | {mapped_tables} |",
        f"| 未归类数据表 | {data.unmatched_table_count} |",
        f"| existing | {data.status_stats.get('existing', 0)} |",
        f"| partial | {data.status_stats.get('partial', 0)} |",
        f"| missing | {data.status_stats.get('missing', 0)} |",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)
