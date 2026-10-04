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


def company_file(base: Path, company_id: str, products: str) -> None:
    config = base / "config" / "company.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        f"schema_version: 1\nid: {company_id}\nproducts:\n{products}", encoding="utf-8"
    )


class CompanyResolutionTest(unittest.TestCase):
    def test_explicit_base_and_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: demo\n    name: Demo\n    code_root: null\n")
            context = resolve_company(company_id="acme", company_base=base)
            self.assertEqual(context.id, "acme")

    def test_cwd_infers_company(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: demo\n    name: Demo\n")
            with patch.dict("os.environ", {"COMPANY_BASE": "", "LANLNK_BASE": ""}):
                with patch("shared.product_context.resolver._DOCS_ROOT", Path(directory)):
                    context = resolve_company(cwd=base / "30-products")
            self.assertEqual(context.base, base)

    def test_no_default_company(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {"COMPANY_BASE": "", "LANLNK_BASE": ""}):
                with patch("shared.product_context.resolver._DOCS_ROOT", Path(directory)):
                    with self.assertRaises(ResolutionError):
                        resolve_company(cwd=directory, require_explicit=True)

    def test_ambiguous_company_discovery_never_picks_default(self) -> None:
        """多家公司且无显式上下文时必须报错，不得静默取排序第一（如 lanlnk）。"""
        with tempfile.TemporaryDirectory() as directory:
            for slug in ("aaa-co", "zzz-co"):
                company_file(Path(directory) / slug, slug, "")
            with patch.dict("os.environ", {"COMPANY_BASE": "", "LANLNK_BASE": ""}):
                with patch("shared.product_context.resolver._DOCS_ROOT", Path(directory)):
                    with self.assertRaises(ResolutionError):
                        resolve_company(cwd=directory)

    def test_single_discovered_company_is_unique_inference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            company_file(Path(directory) / "solo", "solo", "")
            with patch.dict("os.environ", {"COMPANY_BASE": "", "LANLNK_BASE": ""}):
                with patch("shared.product_context.resolver._DOCS_ROOT", Path(directory)):
                    context = resolve_company()
            self.assertEqual(context.id, "solo")

    def test_id_must_match_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "other", "  - id: demo\n    name: Demo\n")
            with self.assertRaises(ResolutionError):
                resolve_company(company_base=base)


class ProductResolutionTest(unittest.TestCase):
    def test_product_and_alias_use_current_company_registry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(
                base,
                "acme",
                "  - id: demo\n    name: Demo\n    code_root: null\n    aliases: [DemoAlias]\n",
            )
            product_root = base / "30-products" / "demo"
            (product_root / "ontology").mkdir(parents=True)
            (product_root / "prd").mkdir()
            (product_root / "INDEX.md").write_text("# Demo\n", encoding="utf-8")
            (product_root / "ontology" / "README.md").write_text(
                "| canonical ontology | `domain.md` |\n", encoding="utf-8"
            )
            (product_root / "ontology" / "domain.md").write_text("v1\n", encoding="utf-8")
            (product_root / "prd" / "README.md").write_text("| PRD 家族 | `prd.md` |\n", encoding="utf-8")
            (product_root / "prd" / "prd.md").write_text("v1\n", encoding="utf-8")
            product = resolve_product("DemoAlias", resolve_company(company_base=base))
            self.assertEqual(product.id, "demo")
            self.assertEqual(product.authority["ontology"].status, "complete")
            self.assertEqual(product.authority["prd"].status, "complete")
            self.assertEqual(product.authority["code"].status, "unresolved")

    def test_null_code_root_is_not_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: demo\n    name: Demo\n    code_root: null\n    prd_ready: false\n")
            product = resolve_product("demo", resolve_company(company_base=base))
            self.assertIsNone(product.code_root)
            self.assertEqual(product.authority["code"].status, "planned")

    def test_existing_external_checkout_is_present_unconfirmed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: demo\n    name: Demo\n    code_root: null\n")
            external = Path("/opt/code/demo")
            with patch("shared.product_context.resolver._observed_code_candidate", return_value=external):
                product = resolve_product("demo", resolve_company(company_base=base))
            self.assertIsNone(product.code_root)
            self.assertEqual(product.authority["code"].status, "present-unconfirmed")
            self.assertEqual(product.authority["code"].path, external)
            self.assertIsNone(product.layers["code_root"])

    def test_unknown_product_does_not_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: demo\n    name: Demo\n")
            with self.assertRaises(ResolutionError):
                resolve_product("lnkcre", resolve_company(company_base=base))

    def test_prd_only_product_has_non_applicable_ontology(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: site\n    name: Site\n    prd_ready: true\n")
            product_root = base / "30-products" / "site"
            (product_root / "prd").mkdir(parents=True)
            (product_root / "INDEX.md").write_text("# prd-only\n", encoding="utf-8")
            (product_root / "prd" / "README.md").write_text("| PRD 家族 | `prd.md` |\n", encoding="utf-8")
            product = resolve_product("site", resolve_company(company_base=base))
            self.assertEqual(product.product_status, "prd-only")
            self.assertEqual(product.authority["ontology"].status, "not-applicable")

    def test_configured_code_root_has_revision_and_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            code = base / "code"
            (code / ".git").mkdir(parents=True)
            (code / "openspec" / "specs" / "demo").mkdir(parents=True)
            company_file(base, "acme", f"  - id: demo\n    name: Demo\n    code_root: {code}\n")
            with patch("shared.product_context.resolver._git_revision", return_value="abc1234"):
                product = resolve_product("demo", resolve_company(company_base=base))
            self.assertEqual(product.authority["code"].status, "complete")
            self.assertEqual(product.repo_revision, "abc1234")
            self.assertEqual(product.openspec_scopes, ("demo",))

    def test_registered_unresolved_ontology_does_not_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: demo\n    name: Demo\n")
            product = resolve_product("demo", resolve_company(company_base=base))
            self.assertEqual(product.authority["ontology"].status, "not-found")
            self.assertIsNone(product.layers["ontology_entry"])


class DeclaredPointerSemanticsTest(unittest.TestCase):
    """治理 README 指针单元格的三种显式声明语义。"""

    @staticmethod
    def _resolve_readme(base: Path, product_id: str, ontology_cell: str, prd_cell: str):
        product_root = base / "30-products" / product_id
        (product_root / "prd").mkdir(parents=True)
        (product_root / "INDEX.md").write_text("# index\n", encoding="utf-8")
        (product_root / "ontology" / "README.md").parent.mkdir(parents=True)
        (product_root / "ontology" / "README.md").write_text(
            f"| 项 | 值 |\n|---|---|\n| canonical ontology | {ontology_cell} |\n",
            encoding="utf-8",
        )
        (product_root / "prd" / "README.md").write_text(
            f"| 项 | 值 |\n|---|---|\n| canonical PRD | {prd_cell} |\n",
            encoding="utf-8",
        )
        return resolve_product(product_id, resolve_company(company_base=base))

    def test_absent_cell_keeps_unresolved_even_with_layer_dir(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: gw\n    name: GW\n    code_root: null\n")
            product = self._resolve_readme(base, "gw", "无（unresolved）", "无（unresolved）")
            self.assertEqual(product.authority["ontology"].status, "unresolved")
            self.assertIsNone(product.layers["ontology_entry"])
            self.assertEqual(product.authority["prd"].status, "unresolved")

    def test_directory_family_cell_points_to_layer_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: site\n    name: Site\n")
            product = self._resolve_readme(base, "site", "未建立", "**已建立（2026-09-27 晋升）**：`baseline/{产品PRD.md, 功能清单.md}`")
            self.assertEqual(product.authority["ontology"].status, "unresolved")
            self.assertEqual(product.authority["prd"].status, "complete")
            self.assertEqual(product.layers["prd_entry"], base / "30-products" / "site" / "prd")

    def test_markdown_link_table_declares_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: crm\n    name: CRM\n")
            product_root = base / "30-products" / "crm"
            (product_root / "prd").mkdir(parents=True)
            (product_root / "prd" / "产品PRD.md").write_text("# prd\n", encoding="utf-8")
            (product_root / "INDEX.md").write_text("# index\n", encoding="utf-8")
            (product_root / "ontology" / "README.md").parent.mkdir(parents=True)
            (product_root / "ontology" / "README.md").write_text(
                "| 项 | 值 |\n|---|---|\n| 业务本体 | `ontology/ontology.yaml` |\n", encoding="utf-8"
            )
            (product_root / "ontology" / "ontology.yaml").write_text("v1\n", encoding="utf-8")
            (product_root / "prd" / "README.md").write_text(
                "| 文件 | 用途 |\n|---|---|\n| [产品PRD.md](./产品PRD.md) | 主文档：首发能力下限 |\n",
                encoding="utf-8",
            )
            product = resolve_product("crm", resolve_company(company_base=base))
            self.assertEqual(product.authority["prd"].status, "complete")
            self.assertEqual(product.layers["prd_entry"], product_root / "prd" / "产品PRD.md")

    def test_30_products_prefixed_pointer_resolves_via_company_base(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "  - id: chat\n    name: Chat\n")
            product_root = base / "30-products" / "chat"
            (product_root / "prd").mkdir(parents=True)
            (product_root / "prd" / "README.md").write_text("| PRD 家族 | 本目录实际内容 |\n", encoding="utf-8")
            (product_root / "INDEX.md").write_text("# index\n", encoding="utf-8")
            (product_root / "ontology" / "README.md").parent.mkdir(parents=True)
            (product_root / "ontology" / "README.md").write_text(
                "| 项 | 值 |\n|---|---|\n| canonical ontology | `30-products/chat/ontology.yaml`（根级） |\n",
                encoding="utf-8",
            )
            (product_root / "ontology.yaml").write_text("v1\n", encoding="utf-8")
            product = resolve_product("chat", resolve_company(company_base=base))
            self.assertEqual(product.authority["ontology"].status, "complete")
            self.assertEqual(product.layers["ontology_entry"], product_root / "ontology.yaml")


class DynamicProductFixtureTest(unittest.TestCase):
    """新增产品只改 company.yaml + 30-products 骨架即可解析，零 resolver 改动。"""

    def test_registry_entry_is_the_only_switch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(base, "acme", "")
            product_root = base / "30-products" / "newproduct"
            (product_root / "ontology").mkdir(parents=True)
            (product_root / "prd").mkdir()
            (product_root / "INDEX.md").write_text("# NewProduct\n", encoding="utf-8")
            (product_root / "ontology" / "README.md").write_text(
                "| canonical ontology | `onto.md` |\n", encoding="utf-8"
            )
            (product_root / "ontology" / "onto.md").write_text("v1\n", encoding="utf-8")
            (product_root / "prd" / "README.md").write_text(
                "| 主 PRD | `main.md` |\n", encoding="utf-8"
            )
            (product_root / "prd" / "main.md").write_text("v1\n", encoding="utf-8")
            company = resolve_company(company_base=base)
            with self.assertRaises(ResolutionError):
                resolve_product("newproduct", company)
            config = base / "config" / "company.yaml"
            config.write_text(
                config.read_text(encoding="utf-8")
                + "  - id: newproduct\n    name: New Product\n    code_root: null\n",
                encoding="utf-8",
            )
            company = resolve_company(company_base=base)
            product = resolve_product("newproduct", company)
            self.assertEqual(product.id, "newproduct")
            self.assertEqual(product.authority["ontology"].status, "complete")
            self.assertEqual(product.authority["prd"].status, "complete")
            self.assertEqual(product.authority["code"].status, "unresolved")
            self.assertEqual(product.layers["docs_root"], product_root)

    def test_every_registered_product_resolves_or_raises_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "acme"
            company_file(
                base,
                "acme",
                "  - id: one\n    name: One\n    code_root: null\n"
                "  - id: two\n    name: Two\n    code_root: null\n",
            )
            company = resolve_company(company_base=base)
            outcomes = []
            for item in company.products:
                pid = str(item["id"])
                try:
                    outcomes.append((pid, resolve_product(pid, company).id))
                except ResolutionError as error:
                    outcomes.append((pid, f"explicit-error: {error}"))
            self.assertEqual([pid for pid, _ in outcomes], ["one", "two"])
            self.assertTrue(all(result in {"one", "two"} for _, result in outcomes))


EXPECTED_PRODUCTS = {
    "lnkchat",
    "lnkchatbi",
    "lnkcre",
    "lnkcrm",
    "lnkgateway",
    "lnkreport",
    "lnkvision",
    "lnkwebsite",
}

_LANLNK_BASE = Path("/opt/code/docs/lanlnk")


@unittest.skipUnless(
    (_LANLNK_BASE / "config" / "company.yaml").is_file(),
    "真实 lanlnk docs 基座不在本机时跳过（CI 环境无 /opt/code/docs）",
)
class LanlnkEightProductIntegrationTest(unittest.TestCase):
    """八产品回归：集合完整性、逐产品 authority、产品隔离。数据源是真实 docs 仓。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.company = resolve_company(company_base=_LANLNK_BASE)

    def test_company_registry_covers_all_eight_products(self) -> None:
        registered = {str(item["id"]) for item in self.company.products}
        self.assertTrue(
            EXPECTED_PRODUCTS.issubset(registered),
            f"company.yaml 缺产品: {sorted(EXPECTED_PRODUCTS - registered)}",
        )

    def test_docs_tree_matches_registry(self) -> None:
        docs_tree = {p.name for p in (self.company.base / "30-products").iterdir() if p.is_dir()}
        registered = {str(item["id"]) for item in self.company.products}
        self.assertEqual(docs_tree, registered)

    def test_every_registered_product_resolves_without_silent_skip(self) -> None:
        for item in self.company.products:
            pid = str(item["id"])
            product = resolve_product(pid, self.company)
            self.assertEqual(product.id, pid)
            for layer in ("ontology", "prd", "code"):
                self.assertIn(
                    product.authority[layer].status,
                    {"complete", "partial", "unresolved", "not-found", "planned",
                     "present-unconfirmed", "inaccessible", "not-applicable"},
                )

    def _resolve(self, product_id: str):
        return resolve_product(product_id, self.company)

    def test_lnkchat_identity_and_nested_scopes(self) -> None:
        product = self._resolve("lnkchat")
        self.assertEqual(product.layers["docs_root"], _LANLNK_BASE / "30-products" / "lnkchat")
        self.assertEqual(product.layers["code_root"], Path("/opt/code/lnkchat"))
        self.assertEqual(product.authority["code"].status, "complete")
        self.assertEqual(
            product.layers["ontology_entry"], _LANLNK_BASE / "30-products" / "lnkchat" / "ontology.yaml"
        )
        self.assertEqual(product.authority["ontology"].status, "complete")
        entry = product.layers["ontology_entry"]
        assert entry is not None
        self.assertTrue(entry.is_file())
        self.assertNotIn("langchat", str(product.layers["code_root"]))
        backend = [s for s in product.openspec_scopes if s.startswith("apps/backend/")]
        root_scopes = [s for s in product.openspec_scopes if "/" not in s]
        self.assertGreater(len(root_scopes), 200)
        self.assertGreaterEqual(len(backend), 20)
        self.assertEqual(product.as_dict()["openspec"]["scope_count"], len(product.openspec_scopes))

    def test_lnkchatbi_uses_own_authority(self) -> None:
        product = self._resolve("lnkchatbi")
        self.assertEqual(product.layers["code_root"], Path("/opt/code/lnkchatbi"))
        entry = product.layers["ontology_entry"]
        self.assertEqual(entry, _LANLNK_BASE / "30-products" / "lnkchatbi" / "ontology" / "ontology.yaml")
        self.assertEqual(product.authority["ontology"].status, "complete")
        self.assertNotIn("lnkcre", str(entry))
        self.assertNotIn("lnkchat/", str(entry).replace("lnkchatbi", ""))
        self.assertEqual(product.authority["prd"].status, "complete")

    def test_lnkcre_keeps_business_ontology_authority(self) -> None:
        product = self._resolve("lnkcre")
        self.assertEqual(product.layers["code_root"], Path("/opt/code/lnkcre"))
        entry = product.layers["ontology_entry"]
        self.assertEqual(entry, _LANLNK_BASE / "config" / "ontology" / "business-ontology.yaml")
        self.assertEqual(product.authority["ontology"].status, "complete")
        self.assertEqual(product.authority["prd"].status, "complete")

    def test_lnkcrm_code_root_configured_complete(self) -> None:
        """lnkcrm code 冻结线（2026-10-04 对账，ratify docs c41a978，路线 A）。

        company.yaml code_root=/opt/code/lnkcrm → layers.code_root 为配置值、
        authority=complete（revision 证据随配置根解析）。旧基线
        present-unconfirmed（code_root=null + observed checkout 仅证据）已被
        docs 提交 c41a978 取代。
        """
        product = self._resolve("lnkcrm")
        self.assertEqual(product.authority["ontology"].status, "complete")
        self.assertEqual(product.authority["prd"].status, "complete")
        self.assertEqual(product.layers["code_root"], Path("/opt/code/lnkcrm"))
        code = product.authority["code"]
        self.assertEqual(code.status, "complete")
        self.assertEqual(code.path, Path("/opt/code/lnkcrm"))
        self.assertTrue(code.revision)

    def test_lnkgateway_unresolved_does_not_fallback(self) -> None:
        product = self._resolve("lnkgateway")
        self.assertEqual(product.authority["ontology"].status, "unresolved")
        self.assertIsNone(product.layers["ontology_entry"])
        self.assertEqual(product.authority["prd"].status, "unresolved")
        self.assertEqual(product.layers["code_root"], Path("/opt/code/lnkgateway"))

    def test_lnkreport_own_canonical_paths(self) -> None:
        product = self._resolve("lnkreport")
        self.assertEqual(product.layers["docs_root"], _LANLNK_BASE / "30-products" / "lnkreport")
        self.assertEqual(product.layers["code_root"], Path("/opt/code/lnkreport"))
        self.assertEqual(
            product.layers["ontology_entry"],
            _LANLNK_BASE / "30-products" / "lnkreport" / "ontology" / "ontology.yaml",
        )
        self.assertEqual(product.authority["prd"].status, "complete")

    def test_lnkvision_markdown_ontology_authority(self) -> None:
        product = self._resolve("lnkvision")
        entry = product.layers["ontology_entry"]
        assert entry is not None
        self.assertEqual(entry, _LANLNK_BASE / "30-products" / "lnkvision" / "ontology" / "域知识.md")
        self.assertEqual(entry.suffix, ".md")
        self.assertEqual(product.authority["ontology"].status, "complete")
        self.assertEqual(product.layers["code_root"], Path("/opt/code/lnkvision"))

    def test_lnkwebsite_prd_only_without_ontology(self) -> None:
        product = self._resolve("lnkwebsite")
        self.assertEqual(product.product_status, "prd-only")
        self.assertEqual(product.authority["ontology"].status, "not-applicable")
        self.assertIsNone(product.layers["ontology_entry"])
        self.assertEqual(product.authority["prd"].status, "complete")
        self.assertEqual(product.layers["code_root"], Path("/opt/code/lnkwebsite"))

    def test_unknown_product_does_not_fallback_to_lnkcre(self) -> None:
        with self.assertRaises(ResolutionError):
            self._resolve("nonexistent-product-x")


if __name__ == "__main__":
    unittest.main()
