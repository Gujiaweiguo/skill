"""Runtime loader for content-operations case_payload.

Injects ``content-operations/`` into ``sys.path`` and imports the real
``scripts.case_payload`` module via ``importlib``.  Exposes
``parse_case_payload`` and ``PayloadValidationError`` as module-level
attributes whose types are declared in the companion ``.pyi`` stub.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

_CONTENT_OPS_ROOT = Path(__file__).resolve().parents[2] / "content-operations"
if str(_CONTENT_OPS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONTENT_OPS_ROOT))

_runtime_mod = importlib.import_module("scripts.case_payload")
parse_case_payload = _runtime_mod.parse_case_payload
PayloadValidationError = _runtime_mod.PayloadValidationError

__all__ = [
    "PayloadValidationError",
    "parse_case_payload",
]
