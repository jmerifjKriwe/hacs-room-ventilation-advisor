"""Test for clean import and presence of main config flow class."""

from __future__ import annotations

import importlib

from tests.helpers.test_framework import ConfigFlowTestCase


class TestConfigFlowImport(ConfigFlowTestCase):
    """Test for clean import and presence of main config flow class."""

    def test_config_flow_imports_cleanly(self) -> None:
        """
        Ensure the config_flow module imports and contains SolarWindowSystemConfigFlow.

        This test verifies that the config_flow module can be imported without errors
        and contains the expected main flow class.
        """
        importlib.invalidate_caches()
        mod = importlib.import_module(
            "custom_components.solar_window_system.config_flow"
        )
        if not hasattr(mod, "SolarWindowSystemConfigFlow"):
            msg = "Missing SolarWindowSystemConfigFlow"
            raise AssertionError(msg)
