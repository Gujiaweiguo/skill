"""多公司基座隔离测试（Lane A，task 1.6：双合成公司基座，Python 级 + CLI 级）。

四场景（spec material-import-provenance「溯源工具 SHALL 维持多公司基座隔离」）：
1. 同名原件不跨公司匹配（A 无候选 + B 有同名 → A 保持 unresolved，B 不被读）
2. 相同相对路径产物/指纹不复用（A/B 各报各的哈希，互不污染）
3. unset/无效 COMPANY_BASE → resolver 报错非零，无 lanlnk 回退
4. symlink 跨基座声明 → boundary-violation 单列、hash_check=not-applicable、
   目标内容不出现在报告（证明未读取目标）
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import provenance_inventory as pi  # noqa: E402

SCRIPT = SCRIPTS_DIR / "provenance_inventory.py"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_base(root: Path, name: str) -> Path:
    base = root / name
    (base / "config").mkdir(parents=True)
    (base / "config" / "company.yaml").write_text(
        f"name: {name}\n", encoding="utf-8")
    (base / "incoming").mkdir()
    (base / "raw").mkdir()
    (base / "materials").mkdir()
    return base


def run_cli(base: Path, *extra, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base", str(base), *extra],
        capture_output=True, text=True, env=env, timeout=120)


class CompanyIsolationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base_a = make_base(self.root, "companya")
        self.base_b = make_base(self.root, "companyb")

    def tearDown(self):
        self._tmp.cleanup()

    # 1. 同名原件不跨公司匹配
    def test_same_basename_not_matched_across_companies(self):
        # A：投影无候选；B：存在同名原件
        (self.base_a / "raw" / "共享.docx.md").write_text("正文\n",
                                                          encoding="utf-8")
        (self.base_b / "incoming" / "共享.docx").write_bytes(b"B-ORIGINAL")
        report = pi.run_inventory(self.base_a, repair_candidates=True)
        rep = [r for r in report["repair_candidates"]
               if r["path"] == "raw/共享.docx.md"]
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep[0]["resolution"], "unresolved")
        # 报告不含 B 基座路径任何片段
        text = json.dumps(report, ensure_ascii=False)
        self.assertNotIn(str(self.base_b), text)
        self.assertNotIn("companyb", text)
        # CLI 级同样验证
        r = run_cli(self.base_a, "--repair-candidates")
        self.assertNotIn(str(self.base_b), r.stdout)
        self.assertNotIn("companyb", r.stdout)

    # 2. 相同相对路径产物/指纹不复用
    def test_same_relpath_projections_not_reused(self):
        # 两基座同 relpath raw md（各声明各的 incoming 原件，内容不同）
        a_orig = self.base_a / "incoming" / "proj.docx"
        b_orig = self.base_b / "incoming" / "proj.docx"
        a_orig.write_bytes(b"A-CONTENT")
        b_orig.write_bytes(b"B-CONTENT-DIFFERENT")
        for base, orig in ((self.base_a, a_orig), (self.base_b, b_orig)):
            (base / "raw" / "proj.docx.md").write_text(
                f"<!-- source: incoming/proj.docx -->\n"
                f"<!-- source_sha256: {sha(orig.read_bytes())} -->\n\n正文\n",
                encoding="utf-8")
        # 同 relpath 的 manifest 记录也不同
        for base, srcname in ((self.base_a, "a.xlsx"), (self.base_b, "b.xlsx")):
            sub = base / "raw" / "sub"
            sub.mkdir()
            (sub / "_manifest.json").write_text(
                json.dumps([{"source_path": str(srcname)}]), encoding="utf-8")
        rep_a = pi.run_inventory(self.base_a)
        rep_b = pi.run_inventory(self.base_b)
        self.assertEqual(rep_a["items"]["raw/proj.docx.md"]["source_sha256_actual"],
                         sha(b"A-CONTENT"))
        self.assertEqual(rep_b["items"]["raw/proj.docx.md"]["source_sha256_actual"],
                         sha(b"B-CONTENT-DIFFERENT"))
        self.assertNotEqual(rep_a["items"]["raw/proj.docx.md"]["source_sha256_actual"],
                            rep_b["items"]["raw/proj.docx.md"]["source_sha256_actual"])
        # manifest 各报各的 source_path，互不污染
        self.assertEqual(
            json.dumps(rep_a["items"]["raw/sub/_manifest.json"],
                       ensure_ascii=False).find("b.xlsx"), -1)
        self.assertIn("a.xlsx",
                      json.dumps(rep_a["items"]["raw/sub/_manifest.json"],
                                 ensure_ascii=False))

    # 3. unset / 无效 COMPANY_BASE → 非零 + resolver 报错 + 无 lanlnk 回退
    def test_unset_or_invalid_company_base_fails(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("COMPANY_BASE", "LANLNK_BASE")}
        # unset（无 --base）
        r = subprocess.run([sys.executable, str(SCRIPT)],
                           capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 1)
        self.assertIn("COMPANY_BASE", r.stderr)
        self.assertEqual(r.stdout, "")  # 无报告输出
        self.assertNotIn("/opt/code/docs/lanlnk", r.stdout + r.stderr)
        # 指向无 config/company.yaml 的路径
        notcompany = self.root / "notacompany"
        notcompany.mkdir()
        env2 = dict(env, COMPANY_BASE=str(notcompany))
        r2 = subprocess.run([sys.executable, str(SCRIPT)],
                            capture_output=True, text=True, env=env2, timeout=60)
        self.assertEqual(r2.returncode, 1)
        self.assertIn("不是已注册公司", r2.stderr)
        self.assertNotIn("/opt/code/docs/lanlnk", r2.stdout + r2.stderr)

    # 4. symlink 跨基座 → boundary-violation、not-applicable、目标不被读取
    def test_symlink_cross_base_boundary_violation(self):
        secret = self.base_b / "incoming" / "secret.docx"
        secret_bytes = b"B-SECRET-CONTENT-CONFIDENTIAL"
        secret.write_bytes(secret_bytes)
        link = self.base_a / "incoming" / "link.docx"
        link.symlink_to(secret)
        # 声明一个故意错误的哈希：若工具读了目标必 mismatch；not-applicable 证明未读
        (self.base_a / "raw" / "linked.md").write_text(
            "<!-- source: incoming/link.docx -->\n"
            "<!-- source_sha256: " + "0" * 64 + " -->\n\n正文\n",
            encoding="utf-8")
        report = pi.run_inventory(self.base_a)
        bv = [b for b in report["boundary_violations"]
              if b["path"] == "raw/linked.md"]
        self.assertEqual(len(bv), 1)
        item = report["items"]["raw/linked.md"]
        self.assertEqual(item["hash_check"], "not-applicable")
        self.assertNotEqual(item["hash_check"], "mismatch")
        text = json.dumps(report, ensure_ascii=False)
        self.assertNotIn(secret_bytes.decode(), text)
        self.assertNotIn(sha(secret_bytes), text)  # 未读目标字节
        # resolved_to 允许携带越界解析结果（boundary 证据本身），但目标内容/哈希绝不出现
        # CLI 级
        r = run_cli(self.base_a)
        self.assertEqual(r.returncode, 3)
        self.assertNotIn(secret_bytes.decode(), r.stdout)


if __name__ == "__main__":
    unittest.main()
