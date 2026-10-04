"""O4 migration gate: adapter_status compatibility field, no-consumer convergence.

依据（owner decision O4，2026-10-04）：
``references/adapter-capability-owner-decision-2026-10-04.md`` §D-O4 五步迁移——
② 迁移实际读取方（盘点结论：程序化调用方 0）→ ③ 兼容告警/迁移提示 → ④ 禁止新增
adapter_status 依赖 → ⑤ owner 确认无消费方后另行批准删除字段。

本测试是 **O4 迁移门禁**（gate），不是业务功能测试：
- 证明 resolver 仍输出 adapter_status 兼容字段（未被删除/重命名/语义变更）；
- 证明 resolver 不读取任何 capability 文件，capability 状态不进入 authority；
- 钉死三条 authority 冻结线（lnkcrm / lnkgateway / lnkwebsite）；
- 机械扫描整个 skill 仓的 .py/.sh 源码，禁止出现新的程序化 adapter_status 消费方。

放宽或移除本测试中的任何断言 = 违反 O4 禁令，必须先取得 owner 独立批准。
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

from shared.product_context import ResolutionError, resolve_company, resolve_product
from shared.product_context.models import ProductContext

DECISION_RECORD = "references/adapter-capability-owner-decision-2026-10-04.md"
CAPABILITY_FILENAME = "adapter-capabilities.yaml"
COMPAT_DEFAULT = "unsupported"

# ── O4 步骤 4 静态禁令：仓内 .py/.sh 源码允许出现 adapter_status 字面量的位置白名单 ──
# 白名单 = 2026-10-04 O4 盘点基线（类别 1/2/3/4/6：定义、赋值、序列化透传、测试自检、
# registry 自有字段断言）。值 = 允许的命中行数上限（精确相等，防白名单文件内夹带新增消费）。
# 新文件/新行数出现在白名单外 → 测试失败；扩充白名单或调整计数需 owner 批准的变更说明。
ALLOWED_ADAPTER_STATUS_SOURCES: dict[str, int] = {
    "shared/product_context/models.py": 2,  # 字段定义 + as_dict 序列化透传
    "shared/product_context/resolver.py": 2,  # 赋值（company.yaml 原样透传+缺省回落）+ 构造传参
    "shared/product_context/tests/test_adapter_capabilities_schema.py": 7,  # O4 键级禁令自检
    "skills/business/product-prd-generator/tests/test_product_governance_contracts.py": 0,  # B1 迁移（2026-10-04）清零：adapter 支持度断言改读 skill 私有 capability 文件（references/adapter-capabilities.yaml，owner 批准执行 B1）；保留 0 基线防止 token 回流
}
# 自指豁免：本门禁测试自身是禁令执行者，token 出现在断言/fixture/说明中是执行机制的一部分；
# 豁免不免除计数以外的义务——本文件内不得出现对业务代码 adapter_status 的真实读取。
_GATE_TEST_PATH = "shared/product_context/tests/test_adapter_status_migration_gate.py"
_SCAN_ROOTS = ("shared", "skills", "references/scripts")
_SCAN_SUFFIXES = (".py", ".sh")
_SKIP_DIR_SEGMENTS = {
    ".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
    ".ruff_cache", ".mypy_cache", "dist", "build", "output", "parsed",
}

# ── O4 步骤 5 前置：三条 authority 冻结线（capability/迁移动作不得触碰） ──
# lnkcrm code 线 2026-10-04 对账更新（O5-lnkcrm-code 路线 A，ratify docs 提交 c41a978）：
# company.yaml 已配置 code_root=/opt/code/lnkcrm（revision 4323b8c…）→ authority=complete。
FREEZE_LINES = {
    "lnkcrm": {"code": "complete"},  # company.yaml code_root=/opt/code/lnkcrm（docs c41a978，2026-10-04 ratified）
    "lnkgateway": {"ontology": "unresolved"},    # ontology_entry=null，无跨产品 fallback
    "lnkwebsite": {"ontology": "not-applicable"},  # product_status=prd-only
}


def _fixture_company(base: Path, products_yaml: str) -> None:
    config = base / "config" / "company.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        f"schema_version: 1\nid: acme\nproducts:\n{products_yaml}", encoding="utf-8"
    )


def _fixture_product(base: Path, product_id: str, *, prd_only: bool = False) -> None:
    root = base / "30-products" / product_id
    (root / "prd").mkdir(parents=True, exist_ok=True)
    (root / "INDEX.md").write_text(
        "# index\n" + ("prd-only\n" if prd_only else ""), encoding="utf-8"
    )
    ontology_readme = root / "ontology" / "README.md"
    ontology_readme.parent.mkdir(parents=True, exist_ok=True)
    ontology_readme.write_text(
        "| 项 | 值 |\n|---|---|\n| canonical ontology | "
        + ("无（unresolved）\n" if not prd_only else "无（prd-only）\n"),
        encoding="utf-8",
    )
    (root / "prd" / "README.md").write_text(
        "| 项 | 值 |\n|---|---|\n| 主 PRD | `main.md` |\n", encoding="utf-8"
    )
    (root / "prd" / "main.md").write_text("v1\n", encoding="utf-8")


def _live_lanlnk():
    """Live lanlnk company base; None when /opt/code/docs 不在本机（环境守卫，非断言放宽）。"""
    try:
        return resolve_company(company_id="lanlnk")
    except ResolutionError:
        return None


class CompatFieldRetainedTest(unittest.TestCase):
    """门禁 1：resolver 仍可输出 adapter_status 兼容字段（O4 保留兼容期）。"""

    def test_dataclass_field_not_removed_or_renamed(self) -> None:
        self.assertIn(
            "adapter_status",
            ProductContext.__dataclass_fields__,
            "删除/重命名 adapter_status 字段需 owner 独立批准（O4 步骤 5）并同 commit 更新本门禁",
        )

    def test_compat_default_fallback_when_company_yaml_omits_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _fixture_company(base, "  - id: demo\n    name: Demo\n    code_root: null\n")
            _fixture_product(base, "demo")
            payload = resolve_product("demo", resolve_company(company_base=base)).as_dict()
            self.assertIn("adapter_status", payload["product"])
            self.assertEqual(payload["product"]["adapter_status"], COMPAT_DEFAULT)

    def test_company_yaml_value_passes_through_verbatim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _fixture_company(
                base, "  - id: demo\n    name: Demo\n    adapter_status: partial\n"
            )
            _fixture_product(base, "demo")
            payload = resolve_product("demo", resolve_company(company_base=base)).as_dict()
            self.assertEqual(payload["product"]["adapter_status"], "partial")

    def test_all_live_products_output_compat_field(self) -> None:
        company = _live_lanlnk()
        if company is None:
            self.skipTest("live lanlnk company base 不可发现（需 /opt/code/docs/lanlnk）")
        for item in company.products:
            pid = str(item.get("id", ""))
            if not pid:
                continue
            payload = resolve_product(pid, company).as_dict()
            self.assertIn(
                "adapter_status",
                payload["product"],
                f"{pid}: 兼容字段必须仍在 resolver 输出中（O4 保留兼容期）",
            )
            self.assertIsInstance(payload["product"]["adapter_status"], str, pid)


class CapabilityLayeringTest(unittest.TestCase):
    """门禁 2/3：capability 文件不被 resolver 读取；capability 状态不改变 authority。"""

    def test_resolver_and_models_source_never_reference_capability_files(self) -> None:
        for relpath in ("shared/product_context/resolver.py", "shared/product_context/models.py"):
            text = (_REPOSITORY_ROOT / relpath).read_text(encoding="utf-8")
            self.assertNotIn("adapter-capabilities", text, relpath)
            self.assertNotIn("adapter_capabilities", text, relpath)

    @staticmethod
    def _recorded_read_text(company, product_ids: list[str]) -> list[Path]:
        real = Path.read_text
        seen: list[Path] = []

        def recording(self: Path, *args, **kwargs):
            seen.append(self)
            return real(self, *args, **kwargs)

        with patch.object(Path, "read_text", recording):
            for pid in product_ids:
                resolve_product(pid, company)
        return seen

    def test_fixture_resolution_reads_no_capability_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _fixture_company(base, "  - id: one\n    name: One\n    code_root: null\n")
            _fixture_product(base, "one")
            seen = self._recorded_read_text(resolve_company(company_base=base), ["one"])
        for path in seen:
            self.assertNotIn(
                "adapter-capabilities",
                path.name,
                f"resolver 不得读取 capability 文件（方案 B 红线）: {path}",
            )

    def test_live_resolution_reads_no_capability_file(self) -> None:
        company = _live_lanlnk()
        if company is None:
            self.skipTest("live lanlnk company base 不可发现（需 /opt/code/docs/lanlnk）")
        product_ids = [str(item.get("id", "")) for item in company.products]
        product_ids = [pid for pid in product_ids if pid]
        seen = self._recorded_read_text(company, product_ids)
        for path in seen:
            self.assertNotIn(
                "adapter-capabilities",
                path.name,
                f"resolver 不得读取 capability 文件（方案 B 红线）: {path}",
            )

    def test_capability_only_status_never_leaks_into_authority(self) -> None:
        """capability 专有状态 blocked 不在 resolver 词汇表内——8 产品 authority 不得出现。"""
        company = _live_lanlnk()
        if company is None:
            self.skipTest("live lanlnk company base 不可发现（需 /opt/code/docs/lanlnk）")
        for item in company.products:
            pid = str(item.get("id", ""))
            if not pid:
                continue
            product = resolve_product(pid, company)
            statuses = {value.status for value in product.authority.values()}
            statuses |= set(product.resolution_status.values())
            self.assertNotIn(
                "blocked",
                statuses,
                f"{pid}: capability 专有状态 blocked 泄入 resolver authority（capability 不得覆盖 authority）",
            )


class AuthorityFreezeLineTest(unittest.TestCase):
    """门禁 4/5/6：三条 authority 冻结线（live 权威态，非 capability 态）。"""

    def _live_product(self, pid: str):
        company = _live_lanlnk()
        if company is None:
            self.skipTest("live lanlnk company base 不可发现（需 /opt/code/docs/lanlnk）")
        return resolve_product(pid, company)

    def test_lnkcrm_code_authority_complete_under_configured_root(self) -> None:
        """lnkcrm code 冻结线（2026-10-04 对账，O5-lnkcrm-code 路线 A，ratify docs c41a978）。

        company.yaml code_root=/opt/code/lnkcrm → layers.code_root 为该配置值、
        authority=complete。回退本基线（layers 归 null / authority 降级为
        present-unconfirmed）需 owner 独立批准并同 commit 更新本门禁。
        """
        product = self._live_product("lnkcrm")
        self.assertEqual(
            product.layers.get("code_root"),
            Path("/opt/code/lnkcrm"),
            "lnkcrm 冻结线：company.yaml code_root=/opt/code/lnkcrm（docs c41a978），"
            "layers.code_root 必须为该配置值",
        )
        self.assertEqual(
            product.authority["code"].status,
            FREEZE_LINES["lnkcrm"]["code"],
            "lnkcrm 冻结线：code_root 经 company.yaml 配置（revision 4323b8c…），"
            "authority=complete（对账基线 2026-10-04）",
        )
        self.assertTrue(
            product.authority["code"].revision,
            "lnkcrm 冻结线：configured code root 必须携带 git revision 证据",
        )

    def test_lnkgateway_ontology_stays_unresolved_without_fallback(self) -> None:
        product = self._live_product("lnkgateway")
        self.assertEqual(
            product.authority["ontology"].status,
            FREEZE_LINES["lnkgateway"]["ontology"],
            "lnkgateway 冻结线：ontology 必须保持 unresolved（O11 pending）",
        )
        self.assertIsNone(
            product.layers.get("ontology_entry"),
            "lnkgateway 冻结线：ontology_entry=null，不得跨产品 fallback 到其他产品本体",
        )

    def test_lnkwebsite_stays_prd_only_not_applicable(self) -> None:
        product = self._live_product("lnkwebsite")
        self.assertEqual(product.product_status, "prd-only")
        self.assertEqual(
            product.authority["ontology"].status,
            FREEZE_LINES["lnkwebsite"]["ontology"],
            "lnkwebsite 冻结线：prd-only 裁定下 ontology=not-applicable",
        )


class NoNewConsumerScanTest(unittest.TestCase):
    """门禁 7：仓内 .py/.sh 源码不得出现白名单之外的 adapter_status 程序化消费。

    覆盖所有访问形态（``adapter_status`` 字面量出现在源码行 = 键访问/属性访问/
    序列化键/断言）。prose（.md/.yaml/.json）不在扫描范围——文档级迁移是 Batch 3
    文档候选，且多处存在其他会话未提交修改。
    """

    def test_no_programmatic_consumer_outside_allowlist(self) -> None:
        offenders: dict[str, list[str]] = {}
        counts: dict[str, int] = {}
        for scan_root in _SCAN_ROOTS:
            root = _REPOSITORY_ROOT / scan_root
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.suffix not in _SCAN_SUFFIXES:
                    continue
                if _SKIP_DIR_SEGMENTS & set(path.relative_to(_REPOSITORY_ROOT).parts):
                    continue
                relpath = path.relative_to(_REPOSITORY_ROOT).as_posix()
                hits = [
                    f"{index}: {line.strip()}"
                    for index, line in enumerate(
                        path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
                    )
                    if "adapter_status" in line
                ]
                if not hits or relpath == _GATE_TEST_PATH:
                    continue
                counts[relpath] = len(hits)
                if relpath not in ALLOWED_ADAPTER_STATUS_SOURCES:
                    offenders[relpath] = hits
        for relpath, expected in ALLOWED_ADAPTER_STATUS_SOURCES.items():
            actual = counts.get(relpath, 0)
            self.assertEqual(
                actual,
                expected,
                f"{relpath}: adapter_status 命中行数 {actual} ≠ 基线 {expected}——"
                "白名单文件内新增/删除消费需 owner 批准并更新本基线（O4 步骤 4 禁令）",
            )
        self.assertFalse(
            offenders,
            "发现白名单外的 adapter_status 程序化消费（O4 步骤 4 禁止新增依赖；"
            "业务支持度一律读各 skill 私有 references/adapter-capabilities.yaml）:\n"
            + "\n".join(
                f"{relpath}: {lines}" for relpath, lines in sorted(offenders.items())
            ),
        )


if __name__ == "__main__":
    unittest.main()
