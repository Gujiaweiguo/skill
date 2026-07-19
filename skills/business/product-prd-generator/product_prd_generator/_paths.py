"""Project-scoped path resolution for product-prd-generator config files.

Provides fallback semantics: project-specific config takes precedence;
when absent, falls back to 商管系统 defaults. This preserves zero-regression
behavior for 商管系统 while allowing langchat / LnkChatBI / CRM etc. to
override ontology and term-aliases without forking the skill.

Resolution priority (per design Decision 1 in change prd-gen-config-externalization):

- ontology_path_for_project(project):
    1. $LANLNK_BASE/out/prd/<project>/output/ontology.yaml   (project-specific)
    2. $LANLNK_BASE/config/ontology/business-ontology.yaml    (商管 fallback)

- term_aliases_path_for_project(project, skill_root):
    1. $LANLNK_BASE/out/prd/<project>/output/term-aliases.yaml  (project-specific)
    2. <skill_root>/references/term-aliases.yaml                (商管 fallback)

Both helpers return a Path object unconditionally. They do NOT raise on
missing project-specific files — the fallback path is returned even if
it too does not exist; callers handle the empty-ontology case.
"""
from __future__ import annotations

import os
from pathlib import Path


def _lanlnk_base() -> Path:
    """Resolve $LANLNK_BASE at call time (not import time).

    Reading at call time allows tests / scripts to set LANLNK_BASE between
    calls. Reading at import time would freeze the value for the whole
    process, breaking test isolation.
    """
    return Path(os.environ.get("LANLNK_BASE", "/opt/code/docs/lanlnk"))


def ontology_path_for_project(project: str) -> Path:
    """Resolve ontology.yaml path for a project.

    Returns the project-specific path if it exists as a file;
    otherwise returns the 商管 fallback path
    ($LANLNK_BASE/config/ontology/business-ontology.yaml).

    The fallback path is returned even if it also does not exist —
    caller handles the empty-ontology case (callers in doc_map.py and
    render.py check `.is_file()` before loading).
    """
    project_specific = _lanlnk_base() / "out" / "prd" / project / "output" / "ontology.yaml"
    if project_specific.is_file():
        return project_specific
    return _lanlnk_base() / "config" / "ontology" / "business-ontology.yaml"


def term_aliases_path_for_project(project: str, skill_root: Path) -> Path:
    """Resolve term-aliases.yaml path for a project.

    Returns the project-specific path if it exists as a file;
    otherwise returns the 商管 fallback path
    (<skill_root>/references/term-aliases.yaml).

    The fallback path is returned even if it also does not exist —
    caller handles the missing-file case.
    """
    project_specific = _lanlnk_base() / "out" / "prd" / project / "output" / "term-aliases.yaml"
    if project_specific.is_file():
        return project_specific
    return skill_root / "references" / "term-aliases.yaml"
