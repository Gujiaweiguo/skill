"""路径守卫回归测试。

背景（2026-09-01 事故）：某次会话在 skill 目录下以相对路径 ``lanlnk/raw/...``
作为输出根，转换产物污染了 skill 仓库
（skills/business/material-importer/lanlnk/raw/12-bi-platform/…）。
本文件锁定两条契约：
1. 公司基座解析：COMPANY_BASE ∥ LANLNK_BASE，必须绝对路径且根下有
   config/company.yaml，否则报错退出（无静默默认）。
2. extract_images 的 raw 输出目录永远不允许落在 skill 仓库内部。
"""

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import _company_base  # noqa: E402
import extract_images  # noqa: E402

SKILL_ROOT = Path(__file__).resolve().parents[1]


def _make_company_base(root: Path) -> Path:
    base = root / "lanlnk"
    (base / "config").mkdir(parents=True)
    (base / "config" / "company.yaml").write_text("brand: test\n", encoding="utf-8")
    return base


class ResolveCompanyBaseTest(unittest.TestCase):
    def test_returns_absolute_base_when_registered(self) -> None:
        # Given / When
        with TemporaryDirectory() as tmp:
            base = _make_company_base(Path(tmp))
            with patch.dict(os.environ, {"COMPANY_BASE": str(base)}, clear=False):
                resolved = _company_base.resolve_company_base()
        # Then
        self.assertEqual(resolved, base)

    def test_lanlnk_base_is_compatible_alias(self) -> None:
        with TemporaryDirectory() as tmp:
            base = _make_company_base(Path(tmp))
            env = {"LANLNK_BASE": str(base), "COMPANY_BASE": ""}
            with patch.dict(os.environ, env, clear=False):
                resolved = _company_base.resolve_company_base()
        self.assertEqual(resolved, base)

    def test_exits_when_env_missing(self) -> None:
        env = os.environ.copy()
        env.pop("COMPANY_BASE", None)
        env.pop("LANLNK_BASE", None)
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                _company_base.resolve_company_base()

    def test_exits_when_relative_path(self) -> None:
        # 复现事故形态：COMPANY_BASE=lanlnk（相对路径）
        with patch.dict(os.environ, {"COMPANY_BASE": "lanlnk"}, clear=False):
            with self.assertRaises(SystemExit):
                _company_base.resolve_company_base()

    def test_exits_when_company_yaml_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"COMPANY_BASE": tmp}, clear=False):
                with self.assertRaises(SystemExit):
                    _company_base.resolve_company_base()


class ResolveRawDirTest(unittest.TestCase):
    def test_default_resolves_to_company_raw(self) -> None:
        with TemporaryDirectory() as tmp:
            base = _make_company_base(Path(tmp))
            with patch.dict(os.environ, {"COMPANY_BASE": str(base)}, clear=False):
                raw_dir = extract_images.resolve_raw_dir(None)
        self.assertEqual(raw_dir, base / "raw")

    def test_default_exits_when_env_missing(self) -> None:
        env = os.environ.copy()
        env.pop("COMPANY_BASE", None)
        env.pop("LANLNK_BASE", None)
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                extract_images.resolve_raw_dir(None)

    def test_rejects_output_inside_skill_repo(self) -> None:
        # 复现事故形态：--raw-dir lanlnk/raw/12-bi-platform（相对路径，
        # 落在 skill 仓库内部）。显式路径不要求 env，但必须被污染守卫拦下。
        env = os.environ.copy()
        env.pop("COMPANY_BASE", None)
        env.pop("LANLNK_BASE", None)
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit):
                extract_images.resolve_raw_dir("lanlnk/raw/12-bi-platform")

    def test_rejects_absolute_output_inside_skill_repo(self) -> None:
        with self.assertRaises(SystemExit):
            extract_images.resolve_raw_dir(str(SKILL_ROOT / "lanlnk" / "raw"))

    def test_accepts_explicit_dir_outside_skill_repo(self) -> None:
        with TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env.pop("COMPANY_BASE", None)
            env.pop("LANLNK_BASE", None)
            target = Path(tmp) / "raw"
            with patch.dict(os.environ, env, clear=True):
                raw_dir = extract_images.resolve_raw_dir(str(target))
        self.assertEqual(raw_dir, target.resolve())

    def test_relative_explicit_dir_resolves_against_cwd(self) -> None:
        with TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                env = os.environ.copy()
                env.pop("COMPANY_BASE", None)
                env.pop("LANLNK_BASE", None)
                with patch.dict(os.environ, env, clear=True):
                    raw_dir = extract_images.resolve_raw_dir("rawout")
            finally:
                os.chdir(old_cwd)
        self.assertEqual(raw_dir, Path(tmp) / "rawout")


if __name__ == "__main__":
    unittest.main()
