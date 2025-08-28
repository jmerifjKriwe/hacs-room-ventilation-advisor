"""Test to reproduce and guard against the 'expected str' second-save bug."""

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.config_flow import GroupSubentryFlowHandler
from custom_components.solar_window_system.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from tests.test_data import VALID_GLOBAL_BASIC, VALID_GLOBAL_ENHANCED


@pytest.mark.asyncio
async def test_group_options_second_save_expected_str_error(
    hass: HomeAssistant,
) -> None:
    """
    Test the 'expected str' bug scenario using the correct subentry reconfigure flow.

    1. Create group parent and global config entries
    2. Create a group subentry with numeric values (as strings)
    3. Reconfigure the group subentry (simulate second save)
    4. Ensure no 'expected str' error occurs.
    """
    # Setup parent and global config entries
    parent_entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Group configurations",
        data={
            "entry_type": "group_configs",
            "is_subentry_parent": True,
        },
        source="internal",
        entry_id="test_group_parent_id",
        unique_id=None,
    )
    data = {"entry_type": "global_config"}
    data.update(VALID_GLOBAL_BASIC)
    data.update(VALID_GLOBAL_ENHANCED)
    # Override with test-specific values
    data["diffuse_factor"] = 0.15
    data["threshold_direct"] = 200
    data["threshold_diffuse"] = 150
    data["temperature_indoor_base"] = 23.0
    data["temperature_outdoor_base"] = 19.5
    global_entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Solar Window System",
        data=data,
        source="user",
        entry_id="test_global_config_id",
        unique_id=None,
    )
    parent_entry.add_to_hass(hass)
    global_entry.add_to_hass(hass)

    with patch(
        "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities",
        return_value=[{"label": "Kitchen", "value": "sensor.temp_kitchen"}],
    ):
        # Step 1: Create group subentry (first save)
        flow_handler = GroupSubentryFlowHandler()
        flow_handler.hass = hass

        user_input = {
            "name": "testgruppe21",
            "indoor_temperature_sensor": VALID_GLOBAL_BASIC[
                "indoor_temperature_sensor"
            ],
            "diffuse_factor": "-1",
            "threshold_direct": "-1",
            "threshold_diffuse": "500",
            "temperature_indoor_base": "-1",
            "temperature_outdoor_base": "-1",
        }
        # First save (creation)
        result = await flow_handler.async_step_user(user_input)
        if result["type"] != FlowResultType.FORM:
            msg = f"Expected form type, got {result['type']}"
            raise AssertionError(msg)
        if result["step_id"] != "enhanced":
            msg = f"Expected step_id 'enhanced', got {result['step_id']}"
            raise AssertionError(msg)

        # Second save (reconfigure)
        result2 = await flow_handler.async_step_reconfigure(user_input)
        if result2["type"] != FlowResultType.FORM:
            msg = f"Expected form type, got {result2['type']}"
            raise AssertionError(msg)
        if result2["step_id"] != "enhanced":
            msg = f"Expected step_id 'enhanced', got {result2['step_id']}"
            raise AssertionError(msg)
    # If we get here, the bug is fixed (no 'expected str' error)
