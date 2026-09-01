"""material-importer CLI 脚本共享的公司基座解析。

契约（/opt/code/docs/COMPANIES.md §3）：COMPANY_BASE ∥ LANLNK_BASE，
必须是绝对路径且根下存在 config/company.yaml，无静默默认。
转换产物一律写入 docs 仓库（$COMPANY_BASE 下），绝不落入 skill 仓库。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ENV_HINT = "  export COMPANY_BASE=/opt/code/docs/<company>   # 如 lianyou / lanlnk"


def resolve_company_base() -> Path:
    """解析并校验当前公司基座；不合法时向 stderr 报错并以 rc=1 退出。"""
    base = os.environ.get("COMPANY_BASE") or os.environ.get("LANLNK_BASE")
    if not base:
        sys.exit("错误: 未设置 COMPANY_BASE（或兼容变量 LANLNK_BASE）。\n" + _ENV_HINT)
    path = Path(base)
    if not path.is_absolute():
        sys.exit(f"错误: COMPANY_BASE 必须是绝对路径（当前: {base}）。\n" + _ENV_HINT)
    if not (path / "config" / "company.yaml").is_file():
        sys.exit(
            f"错误: {path} 不是已注册公司（缺 config/company.yaml）。\n"
            "  新公司请在 docs 仓库运行 scripts/onboard.sh company <slug> 创建。"
        )
    return path
