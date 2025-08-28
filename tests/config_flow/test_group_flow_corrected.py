"""
Test group subentry configuration flow.

This module tests the GroupSubentryFlowHandler which handles creation
and modification of group configurations as subentries.

Key Points:
- Groups are created via GroupSubentryFlowHandler (ConfigSubentryFlow)
- NOT via the main Config Flow (SolarWindowSystemConfigFlow)
- The main Config Flow only creates parent entries and global config
- Subentry flows are tested differently than main flows
"""

import logging
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.config_flow import GroupSubentryFlowHandler
from custom_components.solar_window_system.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from tests.test_data import (
    VALID_GLOBAL_BASIC,
    VALID_GLOBAL_ENHANCED,
    VALID_GLOBAL_SCENARIOS,
)

_LOGGER = logging.getLogger(__name__)


# Test constants
EXPECTED_DIFFUSE_FACTOR = 0.15
EXPECTED_THRESHOLD_DIRECT = 200
EXPECTED_THRESHOLD_DIFFUSE = 150
EXPECTED_TEMP_INDOOR_BASE = 23.0
EXPECTED_TEMP_OUTDOOR_BASE = 19.5


@pytest.fixture
def mock_group_parent_entry() -> MockConfigEntry:
    """Create a mock group parent config entry."""
    return MockConfigEntry(
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


@pytest.fixture
def mock_global_config_entry() -> MockConfigEntry:
    """Create a mock global config entry with all required fields."""
    data = {"entry_type": "global_config"}
    data.update(VALID_GLOBAL_BASIC)
    data.update(VALID_GLOBAL_ENHANCED)
    data.update(VALID_GLOBAL_SCENARIOS)
    # Add any additional required fields for this test
    data["window_width"] = 1.0
    data["window_height"] = 1.0
    data["shadow_depth"] = 0.0
    data["shadow_offset"] = 0.0
    data["solar_radiation_sensor"] = "sensor.solar_radiation"
    data["outdoor_temperature_sensor"] = "sensor.outdoor_temp"
    data["indoor_temperature_sensor"] = "sensor.indoor_temp"
    data["g_value"] = 0.5
    data["frame_width"] = 0.125
    data["tilt"] = 90
    data["diffuse_factor"] = 0.15
    data["threshold_direct"] = 200
    data["threshold_diffuse"] = 150
    data["temperature_indoor_base"] = 23.0
    data["temperature_outdoor_base"] = 19.5
    data["scenario_b_temp_indoor"] = 23.5
    data["scenario_b_temp_outdoor"] = 25.5
    data["scenario_c_temp_indoor"] = 21.5
    data["scenario_c_temp_outdoor"] = 24.0
    data["scenario_c_temp_forecast"] = 28.5
    data["scenario_c_start_hour"] = 9
    return MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Solar Window System",
        data=data,
        source="user",
        entry_id="test_global_config_id",
        unique_id=None,
    )


@pytest.mark.asyncio
async def test_group_subentry_flow_basic_step(
    hass: HomeAssistant,
    mock_group_parent_entry: MockConfigEntry,
    mock_global_config_entry: MockConfigEntry,
) -> None:
    """Test the basic step of group subentry flow."""
    # Add the required entries to hass
    mock_group_parent_entry.add_to_hass(hass)
    mock_global_config_entry.add_to_hass(hass)

    # Mock the temperature sensor helper function
    with patch(
        "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities",
        return_value=[
            {"label": "Indoor Temp", "value": "sensor.indoor_temp"},
            {"label": "Outdoor Temp", "value": "sensor.outdoor_temp"},
            {"label": "Inherit from Global", "value": "-1"},
        ],
    ):
        # Create the subentry flow handler directly
        flow_handler = GroupSubentryFlowHandler()

        # Set the required attributes that would normally be set by Home Assistant
        flow_handler.hass = hass
        flow_handler.handler = DOMAIN
        flow_handler.parent_entry_id = mock_group_parent_entry.entry_id

        # Test the user step (basic configuration)
        result = await flow_handler.async_step_user()

        # Should show a form for basic group configuration
        if result["type"] != FlowResultType.FORM:
            msg = f"Expected form, got {result['type']}"
            raise AssertionError(msg)

        if result["step_id"] != "user":
            msg = "Expected step_id 'user'"
            raise AssertionError(msg)
        if "data_schema" not in result:
            msg = "Expected data_schema in result"
            raise AssertionError(msg)

        # Test form submission with valid data
        user_input = {
            "name": "Test Group",
            "indoor_temperature_sensor": VALID_GLOBAL_BASIC[
                "indoor_temperature_sensor"
            ],
            "diffuse_factor": VALID_GLOBAL_ENHANCED["diffuse_factor"],
            "threshold_direct": VALID_GLOBAL_ENHANCED["threshold_direct"],
            "threshold_diffuse": VALID_GLOBAL_ENHANCED["threshold_diffuse"],
            "temperature_indoor_base": VALID_GLOBAL_ENHANCED["temperature_indoor_base"],
            "temperature_outdoor_base": VALID_GLOBAL_ENHANCED[
                "temperature_outdoor_base"
            ],
        }

        result2 = await flow_handler.async_step_user(user_input)

        # Should proceed to enhanced step
        if result2["type"] != FlowResultType.FORM:
            msg = f"Expected form for enhanced step, got {result2['type']}"
            raise AssertionError(msg)

        if result2["step_id"] != "enhanced":
            msg = "Expected step_id 'enhanced'"
            raise AssertionError(msg)
