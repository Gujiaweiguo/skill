#!/usr/bin/env python3
"""案例匹配器 — 根据客户行业/场景/关键词自动匹配案例库

用法:
    cd skills/business/material-importer
    export LANLNK_BASE=/opt/code/docs/lanlnk

    # 按行业 + 场景匹配
    uv run scripts/case_matcher.py --industry 商业地产 --scenarios 会员营销,积分

    # 按关键词（搜索标题+正文）
    uv run scripts/case_matcher.py --keywords 会员营销,积分商城,小程序

    # 组合查询 + 限制数量
    uv run scripts/case_matcher.py --industry 商业地产 --scenarios 会员营销 --scale 20万㎡ --limit 5

    # JSON 输出
    uv run scripts/case_matcher.py --industry 商业地产 --json

    # 列出所有可选行业和场景
    uv run scripts/case_matcher.py --list-tags

退出码: 0=找到匹配, 1=无匹配
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── 数据结构 ──────────────────────────────────────────

@dataclass
class CaseInfo:
    path: str
    name: str
    client: str
    project: str
    industry: list[str] = field(default_factory=list)
    domain: list[str] = field(default_factory=list)
    scenario: list[str] = field(default_factory=list)
    scale: str = ""
    contract_amount: str = ""
    status: str = ""
    body_text: str = ""
    body_keywords: set[str] = field(default_factory=set)


@dataclass
class MatchResult:
    case: CaseInfo
    score: float
    reasons: list[str] = field(default_factory=list)


# ── 案例库加载 ────────────────────────────────────────

SCALE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*万?㎡")
COMMON_KEYWORDS = {
    "会员", "积分", "营销", "商城", "小程序", "CRM", "SCRM", "私域",
    "停车", "支付", "优惠券", "优惠券", "商圈", "招商", "ERP",
    "数据分析", "BI", "智能", "数字化", "智慧", "社区", "园区",
    "文旅", "商业地产", "购物中心", "商业街", "综合体",
    "企微", "抖音", "美团", "阿里", "腾讯",
    "会员卡", "会员等级", "积分兑换", "积分抵扣", "会员权益",
    "联合运营", "代运营", "品牌", "导购", "导流",
    "物业", "楼宇", "资产", "国资", "国企",
}


def load_cases(cases_dir: Path) -> list[CaseInfo]:
    cases = []
    for md_path in sorted(cases_dir.glob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        fm_match = re.match(r"^---\n(.*?)\n---", raw, re.DOTALL)
        if not fm_match:
            continue

        try:
            fm = yaml.safe_load(fm_match.group(1))
        except yaml.YAMLError:
            continue

        if not fm or not isinstance(fm, dict):
            continue

        body = raw[fm_match.end():].strip()

        case = CaseInfo(
            path=str(md_path),
            name=fm.get("name", md_path.stem),
            client=fm.get("client", ""),
            project=fm.get("project", ""),
            industry=_as_list(fm.get("industry", [])),
            domain=_as_list(fm.get("domain", [])),
            scenario=_as_list(fm.get("scenario", [])),
            scale=fm.get("scale", ""),
            contract_amount=fm.get("contract_amount", ""),
            status=fm.get("status", ""),
            body_text=body,
            body_keywords=_extract_keywords(body),
        )
        cases.append(case)

    return cases


def _as_list(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(v) for v in val]
    if isinstance(val, str):
        return [val]
    return []


def _extract_keywords(text: str) -> set[str]:
    found = set()
    for kw in COMMON_KEYWORDS:
        if kw.lower() in text.lower():
            found.add(kw)
    return found


# ── 匹配引擎 ──────────────────────────────────────────

def match_cases(
    cases: list[CaseInfo],
    industry: str = "",
    scenarios: list[str] | None = None,
    keywords: list[str] | None = None,
    scale: str = "",
    limit: int = 10,
    min_score: float = 20.0,
) -> list[MatchResult]:

    results = []
    query_scale = _parse_scale(scale) if scale else None
    query_keywords = set(k.lower() for k in (keywords or []))

    for case in cases:
        score = 0.0
        reasons = []

        # ── Industry match (×3.0) ──
        if industry:
            if industry in case.industry:
                score += 30.0
                reasons.append(f"行业匹配: {industry}")
            elif any(industry in ind or ind in industry for ind in case.industry):
                score += 20.0
                reasons.append(f"行业相关: {', '.join(case.industry)}")

        # ── Scenario match (×2.5) ──
        if scenarios:
            case_scenarios = set(s.lower() for s in case.scenario)
            matched_scenarios = []
            for s in scenarios:
                s_lower = s.lower()
                for cs in case_scenarios:
                    if s_lower in cs or cs in s_lower:
                        matched_scenarios.append(s)
                        break
            if matched_scenarios:
                pts = len(matched_scenarios) / len(scenarios) * 25.0
                score += pts
                reasons.append(f"场景匹配: {', '.join(matched_scenarios)}")

        # ── Keyword match (×1.5) ──
        if keywords:
            case_fields = " ".join([
                case.body_text, case.name, case.client, case.project,
                " ".join(case.scenario), " ".join(case.industry),
            ]).lower()
            matched_kw = [k for k in keywords if k.lower() in case_fields]
            if matched_kw:
                pts = min(len(matched_kw) / max(len(keywords), 1) * 15.0, 15.0)
                score += pts
                reasons.append(f"关键词命中: {', '.join(matched_kw[:3])}")

        # ── Scale proximity (×1.0) ──
        if query_scale:
            case_scale = _parse_scale(case.scale)
            if case_scale:
                if query_scale > 0 and case_scale > 0:
                    ratio = min(query_scale, case_scale) / max(query_scale, case_scale)
                    if ratio > 0.7:
                        score += 10.0
                        reasons.append(f"规模相近: {case.scale}")
                    elif ratio > 0.3:
                        score += 5.0

        # ── Completeness bonus (×0.5) ──
        if case.status == "complete":
            score += 5.0
        elif case.status == "incomplete":
            score -= 2.0

        if score >= min_score:
            results.append(MatchResult(case=case, score=round(score, 1), reasons=reasons))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit]


def _parse_scale(scale_str: str) -> float | None:
    m = SCALE_PATTERN.search(scale_str)
    if m:
        return float(m.group(1))
    return None


# ── 统计 ──────────────────────────────────────────────

def list_tags(cases: list[CaseInfo]) -> dict[str, list[str]]:
    industries = sorted(set(ind for c in cases for ind in c.industry))
    scenarios = sorted(set(s for c in cases for s in c.scenario))
    return {"industries": industries, "scenarios": scenarios}


# ── CLI ───────────────────────────────────────────────

def format_results(results: list[MatchResult], verbose: bool = False) -> str:
    if not results:
        return "  未找到匹配案例"

    lines = [f"  🎯 匹配案例 ({len(results)} 个):\n"]
    for i, r in enumerate(results, 1):
        c = r.case
        lines.append(f"  {i}. [{r.score:.0f}分] {c.name}")
        detail_parts = []
        if c.industry:
            detail_parts.append(f"行业: {','.join(c.industry)}")
        if c.scenario:
            detail_parts.append(f"场景: {','.join(c.scenario[:3])}")
        if c.scale:
            detail_parts.append(f"规模: {c.scale}")
        if c.contract_amount and "待" not in c.contract_amount:
            detail_parts.append(f"金额: {c.contract_amount}")
        if detail_parts:
            lines.append(f"     {' | '.join(detail_parts)}")
        if r.reasons:
            lines.append(f"     匹配原因: {'; '.join(r.reasons)}")
        if verbose:
            lines.append(f"     客户: {c.client}")
            lines.append(f"     文件: {c.path}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="案例匹配器 — 根据客户行业/场景/关键词匹配案例库"
    )
    parser.add_argument("--industry", "-i", default="", help="客户行业（如：商业地产、产业园区）")
    parser.add_argument("--scenarios", "-s", default="", help="场景标签，逗号分隔（如：会员营销,积分）")
    parser.add_argument("--keywords", "-k", default="", help="关键词，逗号分隔（搜索标题+正文）")
    parser.add_argument("--scale", default="", help="项目规模（如：20万㎡）")
    parser.add_argument("--limit", "-n", type=int, default=10, help="返回数量（默认10）")
    parser.add_argument("--min-score", type=float, default=20.0, help="最低匹配分（默认20）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示客户名和文件路径")
    parser.add_argument("--list-tags", action="store_true", help="列出所有可选行业和场景")

    args = parser.parse_args()

    lanlnk_base = os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk")
    cases_dir = Path(lanlnk_base) / "materials" / "04-cases"

    if not cases_dir.exists():
        print(f"错误: 案例目录不存在: {cases_dir}", file=sys.stderr)
        sys.exit(1)

    cases = load_cases(cases_dir)

    if args.list_tags:
        tags = list_tags(cases)
        print(f"  可选行业 ({len(tags['industries'])}):")
        for ind in tags["industries"]:
            count = sum(1 for c in cases if ind in c.industry)
            print(f"    {ind} ({count}个案例)")
        print(f"\n  可选场景 ({len(tags['scenarios'])}):")
        for sc in tags["scenarios"]:
            count = sum(1 for c in cases if sc in c.scenario)
            print(f"    {sc} ({count}个案例)")
        return

    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    if not any([args.industry, scenarios, keywords]):
        parser.print_help()
        print("\n错误: 至少指定 --industry / --scenarios / --keywords 之一", file=sys.stderr)
        sys.exit(1)

    results = match_cases(
        cases,
        industry=args.industry,
        scenarios=scenarios or None,
        keywords=keywords or None,
        scale=args.scale,
        limit=args.limit,
        min_score=args.min_score,
    )

    if args.json:
        output = {
            "total_cases": len(cases),
            "matched": len(results),
            "results": [
                {
                    "score": r.score,
                    "name": r.case.name,
                    "client": r.case.client,
                    "industry": r.case.industry,
                    "scenario": r.case.scenario,
                    "scale": r.case.scale,
                    "contract_amount": r.case.contract_amount,
                    "status": r.case.status,
                    "path": r.case.path,
                    "reasons": r.reasons,
                }
                for r in results
            ],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(format_results(results, args.verbose))

    sys.exit(0 if results else 1)


if __name__ == "__main__":
    main()
