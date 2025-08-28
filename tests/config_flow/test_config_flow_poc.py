"""PoC tests for config flow refactor using framework."""

from __future__ import annotations

import importlib

from tests.helpers.test_framework import ConfigFlowTestCase


class TestConfigFlowPoc(ConfigFlowTestCase):
    """PoC tests for config flow refactor using framework."""

    def test_config_flow_imports_cleanly(self) -> None:
        """Ensure the config_flow module imports and exposes the expected class."""
        mod = importlib.import_module(
            "custom_components.solar_window_system.config_flow"
        )
        if not hasattr(mod, "SolarWindowSystemConfigFlow"):
            msg = "config_flow module should have SolarWindowSystemConfigFlow class"
            raise AssertionError(msg)
