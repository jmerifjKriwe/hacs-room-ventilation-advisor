"""Test invalid value handling in Solar Window System config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.solar_window_system.const import DOMAIN
from homeassistant import config_entries
from tests.helpers.test_framework import ConfigFlowTestCase
from tests.test_data import INVALID_GLOBAL_BASIC

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestConfigFlowInvalidValue(ConfigFlowTestCase):
    """Test invalid value handling in Solar Window System config flow."""

    async def test_config_flow_invalid_value(self, hass: HomeAssistant) -> None:
        """Test that invalid numeric values are rejected in the config flow."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        if result.get("type") != "form":
            msg = f"Expected form, got: {result}"
            raise AssertionError(msg)
        if result.get("step_id") != "global_basic":
            msg = f"Expected global_basic step, got: {result.get('step_id')}"
            raise AssertionError(msg)

        user_input = INVALID_GLOBAL_BASIC.copy()
        user_input["window_width"] = "0.05"  # Must be >= 0.1
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=user_input
        )
        if result2.get("type") != "form":
            msg = f"Expected form with errors, got: {result2}"
            raise AssertionError(msg)
        errors = result2.get("errors")
        if not errors or "window_width" not in errors:
            msg = f"Expected error for window_width, got: {errors}"
            raise AssertionError(msg)
