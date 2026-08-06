"""Project-scoped path resolution for product-prd-generator config files.

Resolution priority (post document-control-plane migration):

- ontology_path_for_project(project):
    1. $LANLNK_BASE/30-products/<canonical-dir>/ontology.yaml  (migrated)
    2. $LANLNK_BASE/out/prd/<project>/output/ontology.yaml      (legacy)
    3. $LANLNK_BASE/config/ontology/business-ontology.yaml      (fallback)

- term_aliases_path_for_project(project, skill_root):
    1. $LANLNK_BASE/30-products/<canonical-dir>/term-aliases.yaml  (migrated)
    2. $LANLNK_BASE/out/prd/<project>/output/term-aliases.yaml      (legacy)
    3. <skill_root>/references/term-aliases.yaml                    (fallback)

Both helpers return a Path object unconditionally. They do NOT raise on
missing files — the fallback path is returned even if it too does not
exist; callers handle the empty-ontology case.
"""
from __future__ import annotations

import os
from pathlib import Path

_PRODUCT_CANONICAL_DIR: dict[str, str] = {
    "商管系统": "mi-cre",
    "mi-cre": "mi-cre",
    "langchat": "langchat",
}


def _lanlnk_base() -> Path:
    return Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk"))


def ontology_path_for_project(project: str) -> Path:
    base = _lanlnk_base()

    canonical_subdir = _PRODUCT_CANONICAL_DIR.get(project)
    if canonical_subdir:
        p = base / "30-products" / canonical_subdir / "ontology.yaml"
        if p.is_file():
            return p

    legacy = base / "out" / "prd" / project / "output" / "ontology.yaml"
    if legacy.is_file():
        return legacy

    return base / "config" / "ontology" / "business-ontology.yaml"


def term_aliases_path_for_project(project: str, skill_root: Path) -> Path:
    base = _lanlnk_base()

    canonical_subdir = _PRODUCT_CANONICAL_DIR.get(project)
    if canonical_subdir:
        p = base / "30-products" / canonical_subdir / "term-aliases.yaml"
        if p.is_file():
            return p

    legacy = base / "out" / "prd" / project / "output" / "term-aliases.yaml"
    if legacy.is_file():
        return legacy

    return skill_root / "references" / "term-aliases.yaml"


def codebase_features_path_for_project(project: str) -> Path:
    """Return the optional curated code-feature map for a project."""
    base = _lanlnk_base()
    return base / "raw" / f"prd-{project}" / "parsed" / "codebase-features.json"


class InvalidProjectError(ValueError):
    """Raised when --project contains path-traversal or otherwise unsafe characters."""


def validate_project(raw: str) -> str:
    """CLI boundary parser for --project: reject path-unsafe inputs.

    Project names are interpolated into filesystem paths (raw/prd-<project>/...,
    out/prd/<project>/...). Reject separators, traversal, and empty strings so
    a hostile or mistyped value cannot redirect file reads outside $LANLNK_BASE.
    """
    if not raw or not raw.strip():
        raise InvalidProjectError("--project must not be empty")
    cleaned = raw.strip()
    for fragment in ("/", "\\", ".."):
        if fragment in cleaned:
            raise InvalidProjectError(
                f"--project contains forbidden fragment {fragment!r}: {raw!r}",
            )
    for char in cleaned:
        if char < " " or char == "\x7f":
            raise InvalidProjectError(
                f"--project contains control character: {raw!r}",
            )
    return cleaned
