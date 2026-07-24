"""Runtime loader for content-operations case_payload.

Loads the real content-operations ``scripts.case_payload`` module
using a temporary ``sys.modules`` swap to avoid namespace collision
between case-operations' and content-operations' ``scripts`` packages.

Exposes ``parse_case_payload`` and ``PayloadValidationError`` whose
types are declared in the companion ``.pyi`` stub.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

_CONTENT_OPS_ROOT = Path(__file__).resolve().parents[2] / "content-operations"


def _load_real_case_payload() -> ModuleType:
    """Import content-operations' case_payload without scripts conflict.

    Temporarily removes case-operations' ``scripts`` package entries
    from ``sys.modules``, inserts the content-operations root onto
    ``sys.path``, imports ``scripts.case_payload`` (which internally
    imports ``scripts.article_payload``), then restores the original
    case-operations modules and cleans up the temporary path entry.
    """
    co_root = str(_CONTENT_OPS_ROOT)

    # Snapshot and remove case-ops scripts modules
    snapshot: dict[str, ModuleType] = {}
    for key in list(sys.modules):
        if key == "scripts" or key.startswith("scripts."):
            snapshot[key] = sys.modules.pop(key)

    sys.path.insert(0, co_root)
    try:
        mod = importlib.import_module("scripts.case_payload")
    finally:
        sys.path.remove(co_root)
        # Remove content-ops scripts modules
        for key in list(sys.modules):
            if key == "scripts" or key.startswith("scripts."):
                sys.modules.pop(key, None)
        # Restore case-ops scripts modules
        sys.modules.update(snapshot)

    return mod


_runtime_mod = _load_real_case_payload()
parse_case_payload = _runtime_mod.parse_case_payload
PayloadValidationError = _runtime_mod.PayloadValidationError


def get_shared_parser_source() -> str | None:
    """Return the file path of the real content-ops parser module."""
    return getattr(_runtime_mod, "__file__", None)


__all__ = [
    "PayloadValidationError",
    "get_shared_parser_source",
    "parse_case_payload",
]
