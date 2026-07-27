"""Package-level import smoke tests.

Verifies that redirect-audit modules are importable as ``scripts.*``
package members.

Uses ``importlib.import_module`` to exercise the real import machinery.
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
        assert callable(mod.validate_redirect_payload)

    def test_mock_mcp_server_importable(self) -> None:
        """import tests.mock_mcp_server must succeed."""
        mod = importlib.import_module("tests.mock_mcp_server")
        server = mod.MockMCPServer()
        assert callable(server.redirect_list)
        assert callable(server.url_check)
        assert callable(server.get_call_tools)

    def test_validate_has_constants(self) -> None:
        """validate module must export key constants."""
        mod = importlib.import_module("scripts.validate")
        assert hasattr(mod, "SYNTHETIC_TEST_MODE")
        assert hasattr(mod, "FORBIDDEN_ACTION_KEYS")
        assert hasattr(mod, "FORBIDDEN_CJK_TERMS")
        assert hasattr(mod, "ALLOWED_MCP_TOOLS")
        assert hasattr(mod, "FORBIDDEN_MCP_TOOLS")

    def test_validate_result_class(self) -> None:
        """ValidationResult must be importable and instantiable."""
        mod = importlib.import_module("scripts.validate")
        result = mod.ValidationResult(valid=True)
        assert result.valid
        assert result.errors == []
        assert result.checks == {}
