"""Test reconfigure flow for the global configuration entry using framework."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import DOMAIN
from tests.helpers.test_framework import ConfigFlowTestCase
from tests.test_data import (
    VALID_GLOBAL_BASIC,
    VALID_GLOBAL_ENHANCED,
    VALID_GLOBAL_SCENARIOS,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestConfigFlowReconfigure(ConfigFlowTestCase):
    """Test reconfigure flow for the global configuration entry using framework."""

    async def test_global_config_reconfigure_flow(self, hass: HomeAssistant) -> None:
        """
        Reconfigure existing global entry with options flow.

        Reconfiguring an existing global entry should show the options flow
        and accept new values.

        The global configuration is exposed via the OptionsFlow (not a
        ConfigFlow reconfigure handler). Use the options API to exercise
        the three option pages.
        """
        # Create an existing global config entry
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"entry_type": "global_config"},
            title="Solar Window System",
            entry_id="global_config_entry_id",
        )
        entry.add_to_hass(hass)

        # Start Options Flow for the entry
        result = await hass.config_entries.options.async_init(entry.entry_id)
        if result["type"] != "form":
            msg = f"Expected form type, got {result['type']}"
            raise AssertionError(msg)
        if result["step_id"] != "global_basic":
            msg = f"Expected global_basic step, got {result['step_id']}"
            raise AssertionError(msg)

        # Submit basic values
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=VALID_GLOBAL_BASIC
        )
        if result["type"] != "form":
            msg = f"Expected form type, got {result['type']}"
            raise AssertionError(msg)
        if result["step_id"] != "global_enhanced":
            msg = f"Expected global_enhanced step, got {result['step_id']}"
            raise AssertionError(msg)

        # Submit enhanced values
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=VALID_GLOBAL_ENHANCED
        )
        if result["type"] != "form":
            msg = f"Expected form type, got {result['type']}"
            raise AssertionError(msg)
        if result["step_id"] != "global_scenarios":
            msg = f"Expected global_scenarios step, got {result['step_id']}"
            raise AssertionError(msg)

        # Submit scenarios to finish
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input=VALID_GLOBAL_SCENARIOS
        )
        if result["type"] != "create_entry":
            msg = f"Expected create_entry type, got {result['type']}"
            raise AssertionError(msg)
