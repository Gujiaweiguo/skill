"""Regression tests for doc_map product filtering.

Bug fixed 2026-08-06: ``_iter_markdown_files`` used ``docs_root.rglob("*.md")``
without product filtering, so a multi-product docs root (e.g. lanlnk containing
both langchat and mi-cre trees) leaked other products' requirements into the
target product's doc map. This caused generator regressions: langchat PRD
inflated from 194/0 caps to 283/88 missing after mi-cre domain-model docs were
added to the shared lanlnk root.

These tests lock the fix: when ``project`` is passed, only files whose path
contains a ``<project>/`` segment are scanned.
"""

from __future__ import annotations

import pytest

from product_prd_generator.doc_map import _iter_markdown_files


@pytest.fixture()
def multi_product_tree(tmp_path):
    """Build a docs root with two product trees + non-product dirs.

    产品段出现在 30-products/ 之外的目录（此处用 90-legacy 历史快照目录模拟，
    2026-09 三层整理前的 20-architecture/<产品>/ 树同理）也必须被段过滤识别。
    """
    (tmp_path / "30-products" / "langchat" / "prd").mkdir(parents=True)
    (tmp_path / "30-products" / "langchat" / "prd" / "PRD-LC.md").write_text("# langchat PRD\n")
    (tmp_path / "90-legacy" / "langchat").mkdir(parents=True)
    (tmp_path / "90-legacy" / "langchat" / "current-state.md").write_text("# langchat state\n")

    (tmp_path / "30-products" / "mi-cre" / "prd").mkdir(parents=True)
    (tmp_path / "30-products" / "mi-cre" / "prd" / "PRD-MI.md").write_text("# mi-cre PRD\n")
    (tmp_path / "90-legacy" / "mi-cre").mkdir(parents=True)
    (tmp_path / "90-legacy" / "mi-cre" / "domain-model.md").write_text("# mi-cre domain\n")

    (tmp_path / "00-governance").mkdir()
    (tmp_path / "00-governance" / "README.md").write_text("# governance\n")
    (tmp_path / "incoming").mkdir()
    (tmp_path / "incoming" / "raw.md").write_text("# raw\n")
    return tmp_path


def test_no_filter_returns_all_files(multi_product_tree):
    """Without project filter, all md files are returned (backward compat)."""
    files = _iter_markdown_files(multi_product_tree)
    names = sorted(f.name for f in files)
    assert names == [
        "PRD-LC.md",
        "PRD-MI.md",
        "README.md",
        "current-state.md",
        "domain-model.md",
        "raw.md",
    ]


def test_project_filter_excludes_other_products(multi_product_tree):
    """langchat filter must exclude mi-cre files + non-product dirs."""
    files = _iter_markdown_files(multi_product_tree, project="langchat")
    names = sorted(f.name for f in files)
    assert names == ["PRD-LC.md", "current-state.md"]


def test_project_filter_excludes_langchat_when_scanning_mi(multi_product_tree):
    """mi-cre filter must exclude langchat files (symmetry check)."""
    files = _iter_markdown_files(multi_product_tree, project="mi-cre")
    names = sorted(f.name for f in files)
    assert names == ["PRD-MI.md", "domain-model.md"]


def test_project_filter_excludes_non_product_dirs(multi_product_tree):
    """Governance/incoming dirs have no product segment → excluded."""
    files = _iter_markdown_files(multi_product_tree, project="langchat")
    for f in files:
        assert "00-governance" not in str(f)
        assert "incoming" not in str(f)


def test_project_filter_nonexistent_dir(tmp_path):
    """Nonexistent docs_root returns empty tuple."""
    assert _iter_markdown_files(tmp_path / "nope", project="langchat") == ()


def test_project_filter_empty_dir(tmp_path):
    """Empty docs_root returns empty tuple."""
    (tmp_path / "30-products" / "langchat").mkdir(parents=True)
    assert _iter_markdown_files(tmp_path, project="langchat") == ()


# ─── LnkCRE 别名归一 / 迁移期 legacy 段识别（2026-09 lnkcre 目录统一）───


def test_lnkcre_alias_matches_canonical_and_legacy_segments(multi_product_tree):
    """LnkCRE / MI / MI-CRE 输入都识别 lnkcre + mi-cre 段（迁移期读取兼容）。"""
    (multi_product_tree / "30-products" / "lnkcre" / "prd").mkdir(parents=True)
    (multi_product_tree / "30-products" / "lnkcre" / "prd" / "PRD-LC-CRE.md").write_text("# lnkcre PRD\n")

    for raw in ("LnkCRE", "lnkcre", "MI", "MI-CRE"):
        files = _iter_markdown_files(multi_product_tree, project=raw)
        names = sorted(f.name for f in files)
        assert names == ["PRD-LC-CRE.md", "PRD-MI.md", "domain-model.md"], raw


def test_lnkre_filter_excludes_langchat_symmetry(multi_product_tree):
    """LnkCRE 过滤不得漏进 langchat 文件（跨产品隔离对称性）。"""
    files = _iter_markdown_files(multi_product_tree, project="lnkcre")
    for f in files:
        assert "langchat" not in str(f)


def test_case_insensitive_segment_match(multi_product_tree):
    """段匹配大小写不敏感：LnkCRE 输入能命中 lnkcre 目录段。"""
    files = _iter_markdown_files(multi_product_tree / "30-products", project="LnkCRE")
    assert sorted(f.name for f in files) == ["PRD-MI.md"]


def test_product_scoped_root_skips_segment_filter(tmp_path):
    """docs_root 自身即产品专属根（raw/prd-商管系统）：不做段过滤，全量纳入。"""
    root = tmp_path / "prd-商管系统"
    (root / "01-customer-requirements" / "万达").mkdir(parents=True)
    (root / "01-customer-requirements" / "万达" / "req.md").write_text("# 需求\n")
    (root / "02-competitors" / "海鼎").mkdir(parents=True)
    (root / "02-competitors" / "海鼎" / "manual.md").write_text("# 手册\n")
    files = _iter_markdown_files(root, project="商管系统")
    assert sorted(f.name for f in files) == ["manual.md", "req.md"]


def test_shared_root_still_filters(tmp_path):
    """共享根（名称不含产品别名）保持段过滤，防止跨产品泄漏回归。"""
    shared = tmp_path / "lanlnk"
    cre = shared / "30-products" / "lnkcre"
    chat = shared / "30-products" / "lnkchat"
    cre.mkdir(parents=True)
    chat.mkdir(parents=True)
    (cre / "a.md").write_text("# a\n")
    (chat / "b.md").write_text("# b\n")
    files = _iter_markdown_files(shared, project="LnkCRE")
    assert [f.name for f in files] == ["a.md"]


# ─── --exclude-dir 目录排除（2026-11-21 lnkretail 历史客户资料污染治理）───


@pytest.fixture()
def retail_tree(tmp_path):
    root = tmp_path / "prd-lnkretail"
    for rel in (
        "congou/SCM/需求.md",
        "congou/百丽滔博/需求.md",
        "congou/keep/需求.md",
        "myshop/BMS060616/需求.md",
        "myshop/current/需求.md",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# 需求\n")
    return root


def test_exclude_dir_prefix_skips_subtree(retail_tree):
    files = _iter_markdown_files(retail_tree, project="lnkretail", exclude_dirs=["congou/SCM", "myshop/BMS060616"])
    rels = sorted(str(f.relative_to(retail_tree)) for f in files)
    assert rels == ["congou/keep/需求.md", "congou/百丽滔博/需求.md", "myshop/current/需求.md"]


def test_exclude_dir_without_filter_still_excludes(retail_tree):
    files = _iter_markdown_files(retail_tree, exclude_dirs=["congou"])
    assert all(f.relative_to(retail_tree).parts[0] != "congou" for f in files)
    assert len(files) == 2  # myshop/current + myshop/BMS060616


def test_exclude_dir_no_specs_keeps_all(retail_tree):
    files = _iter_markdown_files(retail_tree, project="lnkretail")
    assert len(files) == 5


def test_exclude_dir_single_name_matches_any_level(retail_tree):
    files = _iter_markdown_files(retail_tree, project="lnkretail", exclude_dirs=["SCM"])
    assert all("SCM" not in f.relative_to(retail_tree).parts[:-1] for f in files)


def test_exclude_dir_no_substring_false_positive(tmp_path):
    """段精确比对：排除 SCM 不能误排 SCM-backup 或 SCM.md 文件。"""
    root = tmp_path / "prd-lnkretail"
    (root / "SCM-backup").mkdir(parents=True)
    (root / "SCM-backup" / "a.md").write_text("# a\n")
    (root / "SCM.md").write_text("# b\n")
    files = _iter_markdown_files(root, project="lnkretail", exclude_dirs=["SCM"])
    assert sorted(f.name for f in files) == ["SCM.md", "a.md"]


def test_cli_exclude_dir_repeatable(tmp_path, monkeypatch):
    """doc_map CLI 可重复 --exclude-dir 并透传到扫描。"""
    from product_prd_generator.doc_map import main as doc_map_main
    root = tmp_path / "prd-lnkretail"
    for rel in ("congou/SCM/a.md", "congou/keep/b.md"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# 需求\n## 功能 会员管理\n")
    out = tmp_path / "doc-map.json"
    monkeypatch.setattr(
        "sys.argv",
        ["doc_map", "--docs-root", str(root), "--project", "lnkretail",
         "--exclude-dir", "congou/SCM", "--exclude-dir", "myshop/BMS060616",
         "--output", str(out)],
    )
    assert doc_map_main() == 0
    import json
    payload = json.loads(out.read_text(encoding="utf-8"))
    sources = {f["source_file"] for f in payload["features"]}
    assert all("SCM" not in s for s in sources)
    assert any("keep" in s for s in sources)


def test_main_doc_map_args_passthrough():
    """main.generate 链路把 --exclude-dir 透传给 doc_map 子命令。"""
    import argparse
    from product_prd_generator.main import build_parser, _doc_map_args
    args = build_parser().parse_args([
        "--project", "lnkretail",
        "--exclude-dir", "congou/SCM",
        "--exclude-dir", "congou/百丽滔博",
    ])
    cmd = _doc_map_args(args, "/tmp/out.json")
    i = cmd.index("--exclude-dir")
    assert cmd[i + 1] == "congou/SCM" and cmd[i + 3] == "congou/百丽滔博"


# ─── --exclude-source 平铺文件排除（2026-11-21 lnkretail docs-root 平铺污染治理）───


@pytest.fixture()
def flat_tree(tmp_path):
    root = tmp_path / "prd-lnkretail"
    for rel in (
        "document-batch-01/百丽滔搏运动城业务管理系统解决方案V1.5.md",
        "document-batch-03/Mengniu-ChainOne-SA-01.md",
        "document-batch-03/Mengniu-ChainOne-SA-02.md",
        "document-batch-03/BMS-P74-Script-首府广场客户化说明.md",
        "document-batch-03/keep.md",
        "congou/Congou手册.md",
    ):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# 需求\n## 功能 会员管理-{rel}\n")
    return root


def test_exclude_source_exact_and_glob(flat_tree):
    files = _iter_markdown_files(
        flat_tree,
        project="lnkretail",
        exclude_sources=[
            "document-batch-01/百丽滔搏运动城业务管理系统解决方案V1.5.md",
            "document-batch-03/Mengniu-ChainOne-SA-*.md",
            "document-batch-03/BMS-P74-Script-首府广场客户化说明.md",
        ],
    )
    rels = sorted(str(f.relative_to(flat_tree)) for f in files)
    assert rels == ["congou/Congou手册.md", "document-batch-03/keep.md"]


def test_exclude_source_keeps_unmatched(flat_tree):
    files = _iter_markdown_files(flat_tree, project="lnkretail", exclude_sources=["document-batch-01/百丽*.md"])
    rels = {str(f.relative_to(flat_tree)) for f in files}
    assert "document-batch-03/keep.md" in rels
    assert len(files) == 5


def test_exclude_source_repeatable_via_cli(tmp_path, monkeypatch, flat_tree):
    from product_prd_generator.doc_map import main as doc_map_main
    out = tmp_path / "doc-map.json"
    monkeypatch.setattr(
        "sys.argv",
        ["doc_map", "--docs-root", str(flat_tree), "--project", "lnkretail",
         "--exclude-source", "document-batch-01/百丽滔搏运动城业务管理系统解决方案V1.5.md",
         "--exclude-source", "document-batch-03/Mengniu-ChainOne-SA-*.md",
         "--exclude-source", "document-batch-03/BMS-P74-Script-首府广场客户化说明.md",
         "--output", str(out)],
    )
    assert doc_map_main() == 0
    import json
    payload = json.loads(out.read_text(encoding="utf-8"))
    sources = {r["source_file"] for r in payload["requirements"]} | {f["source_file"] for f in payload["features"]}
    assert all("百丽" not in s and "Mengniu" not in s and "首府广场" not in s for s in sources)
    assert any("keep.md" in s for s in sources)


def test_exclude_source_main_passthrough():
    import argparse  # noqa: F401
    from product_prd_generator.main import build_parser, _doc_map_args
    args = build_parser().parse_args([
        "--project", "lnkretail",
        "--exclude-source", "document-batch-01/百丽*.md",
        "--exclude-source", "document-batch-03/Mengniu-*.md",
    ])
    cmd = _doc_map_args(args, "/tmp/out.json")
    i = cmd.index("--exclude-source")
    assert cmd[i + 1] == "document-batch-01/百丽*.md" and cmd[i + 3] == "document-batch-03/Mengniu-*.md"


def test_exclude_source_no_substring_false_positive(flat_tree):
    """全路径锚定匹配：排除 batch-01 的百丽文件不误排其他目录文件。"""
    files = _iter_markdown_files(flat_tree, project="lnkretail", exclude_sources=["*/百丽*.md"])
    rels = {str(f.relative_to(flat_tree)) for f in files}
    assert len(files) == 5
