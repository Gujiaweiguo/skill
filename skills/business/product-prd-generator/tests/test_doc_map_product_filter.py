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
    """Build a docs root with two product trees + non-product dirs."""
    (tmp_path / "30-products" / "langchat" / "prd").mkdir(parents=True)
    (tmp_path / "30-products" / "langchat" / "prd" / "PRD-LC.md").write_text("# langchat PRD\n")
    (tmp_path / "20-architecture" / "langchat").mkdir(parents=True)
    (tmp_path / "20-architecture" / "langchat" / "current-state.md").write_text("# langchat state\n")

    (tmp_path / "30-products" / "mi-cre" / "prd").mkdir(parents=True)
    (tmp_path / "30-products" / "mi-cre" / "prd" / "PRD-MI.md").write_text("# mi-cre PRD\n")
    (tmp_path / "20-architecture" / "mi-cre").mkdir(parents=True)
    (tmp_path / "20-architecture" / "mi-cre" / "domain-model.md").write_text("# mi-cre domain\n")

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
