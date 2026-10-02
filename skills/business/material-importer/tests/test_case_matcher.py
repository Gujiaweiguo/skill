"""case_matcher 回归测试：评分权重、过滤排序、坏文件跳过可见性。

背景：本脚本被 company-intro-generator / bid-doc-master 两个下游 skill 调用，
此前评分逻辑无任何回归保护；且坏 frontmatter 文件曾无声消失（「解析不了」
被当成「案例不存在」）。本文件锁定两条契约：
1. 各匹配维度的加权分值与 min_score 过滤、排序行为。
2. 跳过清单必须显式上报（stderr WARN + --json skipped_files）。
"""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import os
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import case_matcher  # noqa: E402


PLAZA_CASE = """---
id: "case-20260101-001"
type: "案例"
name: "天河城会员小程序"
client: "天河城"
project: "会员小程序"
industry: ["商业地产"]
domain: ["商管", "会员"]
scenario: ["会员营销", "积分"]
scale: "20万㎡"
contract_amount: "50万"
status: "complete"
---

正文提到 私域 与 积分商城。
"""

MALL_CASE = """---
id: "case-20260101-002"
type: "案例"
name: "万象城CRM"
industry: ["购物中心"]
scenario: ["会员营销"]
scale: "18万㎡"
status: ""
---

正文。
"""


def _write(dir_path: Path, name: str, content: str) -> None:
    (dir_path / name).write_text(content, encoding="utf-8")


def _load_two_cases() -> tuple[list[case_matcher.CaseInfo], list[dict[str, str]]]:
    with TemporaryDirectory() as tmp:
        cases_dir = Path(tmp) / "04-cases"
        cases_dir.mkdir()
        _write(cases_dir, "plaza.md", PLAZA_CASE)
        _write(cases_dir, "mall.md", MALL_CASE)
        cases, skipped = case_matcher.load_cases(cases_dir)
    return cases, skipped


class LoadCasesTest(unittest.TestCase):
    def test_gb18030_encoded_case_is_loaded_not_crashed(self) -> None:
        with TemporaryDirectory() as tmp:
            cases_dir = Path(tmp) / "04-cases"
            cases_dir.mkdir()
            (cases_dir / "plaza.md").write_text(PLAZA_CASE, encoding="utf-8")
            legacy = PLAZA_CASE.replace("天河城会员小程序", "环贸商城CRM")
            (cases_dir / "legacy.md").write_bytes(legacy.encode("gb18030"))

            cases, skipped = case_matcher.load_cases(cases_dir)

            results = case_matcher.match_cases(cases, keywords=["环贸商城"])

        self.assertEqual(skipped, [])
        self.assertEqual(
            [c.name for c in cases], ["环贸商城CRM", "天河城会员小程序"]
        )
        # 默认 min_score=20：环贸商城CRM 关键词 15 + complete 5 = 20 入选；
        # 天河城 无命中 仅 complete 5 被过滤
        self.assertEqual([r.case.name for r in results], ["环贸商城CRM"])

    def test_reports_skipped_files_instead_of_silent_drop(self) -> None:
        with TemporaryDirectory() as tmp:
            cases_dir = Path(tmp) / "04-cases"
            cases_dir.mkdir()
            _write(cases_dir, "good.md", PLAZA_CASE)
            _write(cases_dir, "no_frontmatter.md", "纯正文，没有 frontmatter。\n")
            _write(cases_dir, "bad_yaml.md", "---\nname: \"未闭合\n---\n正文\n")
            _write(cases_dir, "list_fm.md", "---\n- 1\n- 2\n---\n正文\n")

            cases, skipped = case_matcher.load_cases(cases_dir)

        self.assertEqual([c.name for c in cases], ["天河城会员小程序"])
        self.assertEqual(
            [Path(s["path"]).name for s in skipped],
            ["bad_yaml.md", "list_fm.md", "no_frontmatter.md"],
        )
        reasons = " ".join(s["reason"] for s in skipped)
        self.assertIn("YAML 解析失败", reasons)
        self.assertIn("不是键值映射", reasons)
        self.assertIn("缺少 frontmatter", reasons)


class MatchScoringTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cases, self.skipped = _load_two_cases()
        self.assertEqual(self.skipped, [])

    def test_industry_exact_match_is_30_plus_complete_5(self) -> None:
        results = case_matcher.match_cases(self.cases, industry="商业地产", min_score=0)

        by_name = {r.case.name: r.score for r in results}
        self.assertEqual(by_name["天河城会员小程序"], 35.0)

    def test_industry_related_match_is_20(self) -> None:
        results = case_matcher.match_cases(self.cases, industry="地产", min_score=0)

        by_name = {r.case.name: r.score for r in results}
        # 万象城 industry=购物中心 不含「地产」→ 不加分；天河城 complete +5
        self.assertEqual(by_name["天河城会员小程序"], 25.0)

    def test_scenario_score_is_proportional(self) -> None:
        # 万象城仅命中 会员营销（1/2）→ 12.5
        results = case_matcher.match_cases(
            self.cases, scenarios=["会员营销", "积分"], min_score=0
        )

        by_name = {r.case.name: r.score for r in results}
        self.assertEqual(by_name["万象城CRM"], 12.5)
        # 天河城命中 2/2 → 25 + complete 5
        self.assertEqual(by_name["天河城会员小程序"], 30.0)

    def test_keyword_score_is_proportional_to_hits(self) -> None:
        # 天河城正文含 私域+积分商城（2/4）→ 7.5 + complete 5
        results = case_matcher.match_cases(
            self.cases, keywords=["私域", "积分商城", "停车", "招商"], min_score=0
        )

        by_name = {r.case.name: r.score for r in results}
        self.assertEqual(by_name["天河城会员小程序"], 12.5)
        self.assertEqual(by_name["万象城CRM"], 0.0)

    def test_scale_proximity_adds_10_when_ratio_above_07(self) -> None:
        results = case_matcher.match_cases(self.cases, scale="18万㎡", min_score=0)

        by_name = {r.case.name: r.score for r in results}
        # 18 vs 20 → ratio 0.9 → +10
        self.assertEqual(by_name["天河城会员小程序"], 15.0)

    def test_incomplete_status_penalizes_2(self) -> None:
        plaza = next(c for c in self.cases if c.name == "天河城会员小程序")
        plaza.status = "incomplete"

        results = case_matcher.match_cases([plaza], industry="商业地产", min_score=0)

        self.assertEqual(results[0].score, 28.0)

    def test_min_score_filters_non_matching_cases(self) -> None:
        results = case_matcher.match_cases(
            self.cases, keywords=["完全不存在的关键词"], min_score=20
        )

        self.assertEqual(results, [])

    def test_results_sorted_by_score_desc_and_limited(self) -> None:
        results = case_matcher.match_cases(
            self.cases, scenarios=["会员营销"], min_score=0, limit=1
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].case.name, "天河城会员小程序")


class ListTagsTest(unittest.TestCase):
    def test_tags_come_only_from_parseable_cases(self) -> None:
        with TemporaryDirectory() as tmp:
            cases_dir = Path(tmp) / "04-cases"
            cases_dir.mkdir()
            _write(cases_dir, "good.md", PLAZA_CASE)
            _write(cases_dir, "bad_yaml.md", "---\nname: \"未闭合\n---\n正文\n")
            cases, _skipped = case_matcher.load_cases(cases_dir)

            tags = case_matcher.list_tags(cases)

        self.assertEqual(tags["industries"], ["商业地产"])
        self.assertEqual(tags["scenarios"], ["会员营销", "积分"])


class CliJsonTest(unittest.TestCase):
    def test_json_output_carries_skipped_files_and_warns_on_stderr(self) -> None:
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "config").mkdir()
            (base / "config" / "company.yaml").write_text("brand: t\n", encoding="utf-8")
            cases_dir = base / "materials" / "04-cases"
            cases_dir.mkdir(parents=True)
            _write(cases_dir, "good.md", PLAZA_CASE)
            _write(cases_dir, "bad_yaml.md", "---\nname: \"未闭合\n---\n正文\n")

            import json

            stdout, stderr = StringIO(), StringIO()
            argv = [
                "case_matcher.py", "--industry", "商业地产",
                "--json", "--min-score", "0",
            ]
            with patch.dict(os.environ, {"COMPANY_BASE": str(base)}, clear=False):
                with patch.object(sys, "argv", argv):
                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        with self.assertRaises(SystemExit) as ctx:
                            case_matcher.main()

            payload = json.loads(stdout.getvalue())

        self.assertEqual(ctx.exception.code, 0)
        self.assertEqual(payload["matched"], 1)
        self.assertEqual(len(payload["skipped_files"]), 1)
        self.assertIn("案例文件跳过", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
