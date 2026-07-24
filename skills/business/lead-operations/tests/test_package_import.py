"""Package-level import smoke tests."""

from __future__ import annotations

import importlib


class TestPackageSmoke:
    def test_synthetic_runner_importable(self) -> None:
        mod = importlib.import_module("scripts.synthetic_runner")
        assert callable(mod.run_synthetic_fixture)

    def test_validate_importable(self) -> None:
        mod = importlib.import_module("scripts.validate")
        assert callable(mod.validate_lead_payload)
