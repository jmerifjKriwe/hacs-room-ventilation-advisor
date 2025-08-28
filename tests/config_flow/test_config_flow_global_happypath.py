"""Integration-style tests for the global config flow (happy path)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.solar_window_system.const import DOMAIN
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from tests.helpers.test_framework import ConfigFlowTestCase
from tests.test_data import (
    VALID_GLOBAL_BASIC,
    VALID_GLOBAL_ENHANCED,
    VALID_GLOBAL_SCENARIOS,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestGlobalConfigFlowHappyPath(ConfigFlowTestCase):
    """Integration-style tests for the global config flow (happy path)."""

    async def test_global_config_flow_create_entry(self, hass: HomeAssistant) -> None:
        """Walk the global config flow through both steps and expect create_entry."""
        # Step 1: start flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        if result.get("type") != "form":
            msg = f"Expected form, got {result.get('type')}"
            raise AssertionError(msg)
        if result.get("step_id") != "global_basic":
            msg = f"Expected global_basic, got {result.get('step_id')}"
            raise AssertionError(msg)

        # Provide basic global data
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=VALID_GLOBAL_BASIC
        )
        if result2.get("type") != "form":
            msg = f"Expected form, got {result2.get('type')}"
            raise AssertionError(msg)
        if result2.get("step_id") != "global_enhanced":
            msg = f"Expected global_enhanced, got {result2.get('step_id')}"
            raise AssertionError(msg)

        # Provide enhanced global data (step 2); next step is scenarios (step 3)
        result3 = await hass.config_entries.flow.async_configure(
            result2["flow_id"], user_input=VALID_GLOBAL_ENHANCED
        )
        if result3.get("type") != "form":
            msg = f"Expected form, got {result3.get('type')}"
            raise AssertionError(msg)
        if result3.get("step_id") != "global_scenarios":
            msg = f"Expected global_scenarios, got {result3.get('step_id')}"
            raise AssertionError(msg)

        # Provide scenarios and expect create_entry
        result4 = await hass.config_entries.flow.async_configure(
            result3["flow_id"], user_input=VALID_GLOBAL_SCENARIOS
        )
        if result4.get("type") != FlowResultType.CREATE_ENTRY:
            msg = f"Expected CREATE_ENTRY, got {result4.get('type')}"
            raise AssertionError(msg)
