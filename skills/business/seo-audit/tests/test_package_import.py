"""Package-level import smoke tests.

Verifies that seo-audit modules are importable as ``scripts.*``
package members, not just as flat modules via pytest ``pythonpath``.

Uses ``importlib.import_module`` (not bare ``import``) to avoid
PLC0415 while still exercising the real import machinery at call time.
"""

from __future__ import annotations

import importlib


class TestPackageSmoke:
    """Verify package-level imports work end-to-end."""

    def test_synthetic_runner_importable(self) -> None:
        """import scripts.synthetic_runner must succeed."""
        mod = importlib.import_module("scripts.synthetic_runner")
        assert callable(mod.run_synthetic_fixture)

    def test_validate_importable(self) -> None:
        """import scripts.validate must succeed."""
        mod = importlib.import_module("scripts.validate")
        assert callable(mod.validate_audit_payload)

    def test_mock_mcp_importable(self) -> None:
        """import tests.mock_mcp_server must succeed."""
        mod = importlib.import_module("tests.mock_mcp_server")
        assert hasattr(mod, "MockMCPServer")
