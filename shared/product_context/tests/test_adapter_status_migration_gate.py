"""D2 retirement gate: adapter_status 字段已退役，全仓零消费 + 三条 authority 冻结线。

依据（owner decision O4 → D2，2026-10-04）：
- O4 五步迁移（``references/adapter-capability-owner-decision-2026-10-04.md`` §D-O4）
  步骤 ⑤：字段删除需 owner 独立批准 + 门禁测试同批更新；
- D2 批准记录：``references/adapter-capability-owner-decision-d2-adapter-status-retire-2026-10-04.md``
  （status=approved，decision=delete-field，OWNER SIGN-OFF: RECORDED (OPC)）。

本测试是 **退役后门禁**（gate），不是业务功能测试：
- 证明 ProductContext 已无 adapter_status 字段、as_dict 不再输出该键
  （含 company.yaml 显式携带该键时也不透传）；
- 证明 resolver 不读取任何 capability 文件，capability 状态不进入 authority；
- 钉死三条 authority 冻结线（lnkcrm / lnkgateway / lnkwebsite）——D2 明令原样保留；
- 机械扫描整个 skill 仓的 .py/.sh 源码：全仓零 adapter_status 消费
  （唯一豁免 = 禁令执行文件自身）。

恢复该字段或放宽本门禁任何断言 = 违反 D2 禁令，必须先取得 owner 独立批准。
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

O4_DECISION_RECORD = "references/adapter-capability-owner-decision-2026-10-04.md"
D2_DECISION_RECORD = (
    "references/adapter-capability-owner-decision-d2-adapter-status-retire-2026-10-04.md"
)
RETIRED_FIELD = "adapter_status"

# ── D2 退役后静态禁令：仓内 .py/.sh 源码零 adapter_status 消费 ──
# 唯一豁免 = 禁令执行文件自身（token 出现在断言/fixture/说明中是执行机制的一部分）。
# 任何其他 .py/.sh 文件出现 ``adapter_status`` 字面量（键访问/属性访问/序列化键/断言）
# 即违规；执行文件自身的命中数钉死基线（精确相等，防执行文件内夹带真实消费）。
_GATE_TEST_PATH = "shared/product_context/tests/test_adapter_status_migration_gate.py"
_KEY_BAN_TEST_PATH = "shared/product_context/tests/test_adapter_capabilities_schema.py"
_KEY_BAN_TEST_BASELINE = 7  # O4 键级禁令自检（capability 文件不得携带该字段）的既有基线
_ENFORCEMENT_FILES = frozenset({_GATE_TEST_PATH, _KEY_BAN_TEST_PATH})
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


class FieldRetiredTest(unittest.TestCase):
    """门禁 1（D2 改写）：adapter_status 字段已退役（O4 步骤 ⑤ 落地，owner decision D2）。"""

    def test_dataclass_field_removed(self) -> None:
        self.assertNotIn(
            RETIRED_FIELD,
            ProductContext.__dataclass_fields__,
            f"{RETIRED_FIELD} 已于 D2（2026-10-04）退役；恢复该字段需 owner 独立批准"
            f"（依据 {O4_DECISION_RECORD} 步骤 5 → {D2_DECISION_RECORD}）并同 commit 更新本门禁",
        )

    def test_as_dict_omits_key_even_when_company_yaml_sets_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            _fixture_company(
                base, "  - id: demo\n    name: Demo\n    adapter_status: partial\n"
            )
            _fixture_product(base, "demo")
            payload = resolve_product("demo", resolve_company(company_base=base)).as_dict()
            self.assertNotIn(
                RETIRED_FIELD,
                payload["product"],
                "company.yaml 残留的 adapter_status 键不得透传进 as_dict（D2 已退役）",
            )

    def test_all_live_products_as_dict_without_retired_field(self) -> None:
        company = _live_lanlnk()
        if company is None:
            self.skipTest("live lanlnk company base 不可发现（需 /opt/code/docs/lanlnk）")
        for item in company.products:
            pid = str(item.get("id", ""))
            if not pid:
                continue
            payload = resolve_product(pid, company).as_dict()
            self.assertNotIn(
                RETIRED_FIELD,
                payload["product"],
                f"{pid}: 退役字段不得出现在 resolver 输出中（D2，2026-10-04）",
            )


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


class ZeroConsumerScanTest(unittest.TestCase):
    """门禁 7（D2 改写）：仓内 .py/.sh 源码 adapter_status 零消费。

    字段已退役（D2，2026-10-04）——``adapter_status`` 字面量出现在任何源码行
    （键访问/属性访问/序列化键/断言）均为违规，唯一豁免 = 禁令执行文件自身
    （本门禁 + O4 键级禁令自检），其命中数钉死基线（精确相等，防夹带真实消费）。
    prose（.md/.yaml/.json）不在扫描范围——baseline 契约自有字段与 README 已退役
    登记文案属文档层，由各自 owner 决策管理。
    """

    def test_zero_programmatic_consumer_repo_wide(self) -> None:
        hits_by_file: dict[str, list[str]] = {}
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
                    if RETIRED_FIELD in line
                ]
                if hits:
                    hits_by_file[relpath] = hits
        self.assertEqual(
            len(hits_by_file.get(_KEY_BAN_TEST_PATH, [])),
            _KEY_BAN_TEST_BASELINE,
            f"{_KEY_BAN_TEST_PATH}: adapter_status 命中行数偏离基线 "
            f"{_KEY_BAN_TEST_BASELINE}——键级禁令自检内新增/删除引用需 owner 批准的变更说明",
        )
        offenders = {
            relpath: hits
            for relpath, hits in hits_by_file.items()
            if relpath not in _ENFORCEMENT_FILES
        }
        self.assertFalse(
            offenders,
            "adapter_status 已退役（D2，2026-10-04），全仓 .py/.sh 源码零消费；"
            "业务支持度一律读各 skill 私有 references/adapter-capabilities.yaml:\n"
            + "\n".join(
                f"{relpath}: {lines}" for relpath, lines in sorted(offenders.items())
            ),
        )


if __name__ == "__main__":
    unittest.main()
