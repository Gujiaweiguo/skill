"""Package-level import smoke tests.

Verifies that case-operations modules are importable as ``scripts.*``
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
        assert callable(mod.validate_case_payload)

    def test_content_ops_loader_importable(self) -> None:
        """import scripts.content_ops_loader must succeed."""
        mod = importlib.import_module("scripts.content_ops_loader")
        assert callable(mod.parse_case_payload)
        assert callable(mod.get_shared_parser_source)

    def test_shared_parser_source_points_to_content_ops(self) -> None:
        """Parser must originate from the content-operations skill."""
        mod = importlib.import_module("scripts.content_ops_loader")
        source = mod.get_shared_parser_source()
        assert source is not None
        assert "content-operations" in source
