"""word-master 的公司基座解析（COMPANIES.md §3）。

契约：COMPANY_BASE ∥ LANLNK_BASE，必须是绝对路径且根下存在 config/company.yaml，
无静默默认——两者皆未设置时报错退出，绝不回落 /opt/code/docs/lanlnk。
防止其他公司会话（如 lianyou）静默读到 lanlnk 素材。
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
