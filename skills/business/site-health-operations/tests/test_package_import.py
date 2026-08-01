"""Package-level import smoke tests.

Verifies that site-health-operations modules are importable as
``scripts.*`` package members, not just as flat modules via pytest
``pythonpath``.

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
        assert callable(mod.validate_health_payload)

    def test_init_importable(self) -> None:
        """import scripts must succeed with docstring."""
        mod = importlib.import_module("scripts")
        assert mod.__doc__ is not None

    def test_health_check_importable(self) -> None:
        """import scripts.health_check must succeed."""
        mod = importlib.import_module("scripts.health_check")
        assert callable(mod.HealthChecker)
        assert callable(mod.HealthChecker.run)
