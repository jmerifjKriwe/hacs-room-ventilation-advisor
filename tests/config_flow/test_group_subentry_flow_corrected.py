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
    return MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Solar Window System",
        data={
            "entry_type": "global_config",
            "window_width": 1.0,
            "window_height": 1.0,
            "shadow_depth": 0.0,
            "shadow_offset": 0.0,
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
            "indoor_temperature_sensor": "sensor.indoor_temp",
            "g_value": 0.5,
            "frame_width": 0.125,
            "tilt": 90,
            "diffuse_factor": EXPECTED_DIFFUSE_FACTOR,
            "threshold_direct": EXPECTED_THRESHOLD_DIRECT,
            "threshold_diffuse": EXPECTED_THRESHOLD_DIFFUSE,
            "temperature_indoor_base": EXPECTED_TEMP_INDOOR_BASE,
            "temperature_outdoor_base": EXPECTED_TEMP_OUTDOOR_BASE,
            "scenario_b_temp_indoor": 23.5,
            "scenario_b_temp_outdoor": 25.5,
            "scenario_c_temp_indoor": 21.5,
            "scenario_c_temp_outdoor": 24.0,
            "scenario_c_temp_forecast": 28.5,
            "scenario_c_start_hour": 9,
        },
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
            msg = f"Expected step_id 'user', got {result['step_id']}"
            raise AssertionError(msg)
        if "data_schema" not in result:
            msg = "Expected 'data_schema' in result"
            raise AssertionError(msg)

        # Test form submission with valid data
        user_input = {
            "name": "Test Group",
            "indoor_temperature_sensor": "sensor.indoor_temp",
            "diffuse_factor": "0.15",
            "threshold_direct": "200",
            "threshold_diffuse": "150",
            "temperature_indoor_base": "23.0",
            "temperature_outdoor_base": "19.5",
        }

        result2 = await flow_handler.async_step_user(user_input)

        # Should proceed to enhanced step
        if result2["type"] != FlowResultType.FORM:
            msg = f"Expected form for enhanced step, got {result2['type']}"
            raise AssertionError(msg)

        if result2["step_id"] != "enhanced":
            msg = f"Expected step_id 'enhanced', got {result2['step_id']}"
            raise AssertionError(msg)


@pytest.mark.asyncio
async def test_group_subentry_flow_complete(
    hass: HomeAssistant,
    mock_group_parent_entry: MockConfigEntry,
    mock_global_config_entry: MockConfigEntry,
) -> None:
    """Test complete group subentry flow from start to finish."""
    # Add the required entries to hass
    mock_group_parent_entry.add_to_hass(hass)
    mock_global_config_entry.add_to_hass(hass)

    # Mock the temperature sensor helper function
    with (
        patch(
            "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities",
            return_value=[
                {"label": "Indoor Temp", "value": "sensor.indoor_temp"},
                {"label": "Outdoor Temp", "value": "sensor.outdoor_temp"},
                {"label": "Inherit from Global", "value": "-1"},
            ],
        ),
        patch(
            "custom_components.solar_window_system.config_flow.GroupSubentryFlowHandler.async_create_entry"
        ) as mock_create_entry,
    ):
        # Set up the mock to return a successful creation
        mock_create_entry.return_value = {
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Group",
            "data": {
                "name": "Test Group",
                "indoor_temperature_sensor": "sensor.indoor_temp",
                "diffuse_factor": EXPECTED_DIFFUSE_FACTOR,
                "threshold_direct": EXPECTED_THRESHOLD_DIRECT,
                "threshold_diffuse": EXPECTED_THRESHOLD_DIFFUSE,
                "temperature_indoor_base": EXPECTED_TEMP_INDOOR_BASE,
                "temperature_outdoor_base": EXPECTED_TEMP_OUTDOOR_BASE,
            },
        }

        # Create the subentry flow handler directly
        flow_handler = GroupSubentryFlowHandler()

        # Set the required attributes that would normally be set by Home Assistant
        flow_handler.hass = hass
        flow_handler.handler = DOMAIN
        flow_handler.parent_entry_id = mock_group_parent_entry.entry_id

        # Step 1: Basic configuration
        user_input_basic = {
            "name": "Test Group",
            "indoor_temperature_sensor": "sensor.indoor_temp",
            "diffuse_factor": "0.15",
            "threshold_direct": "200",
            "threshold_diffuse": "150",
            "temperature_indoor_base": "23.0",
            "temperature_outdoor_base": "19.5",
        }

        result = await flow_handler.async_step_user(user_input_basic)
        if result["step_id"] != "enhanced":
            msg = f"Expected step_id 'enhanced', got {result['step_id']}"
            raise AssertionError(msg)

        # Step 2: Enhanced configuration (scenarios)
        user_input_enhanced = {
            "scenario_b_enable": False,
            "scenario_c_enable": False,
        }

        result2 = await flow_handler.async_step_enhanced(user_input_enhanced)

        # Should create the entry
        if result2["type"] != FlowResultType.CREATE_ENTRY:
            msg = f"Expected create_entry, got {result2['type']}"
            raise AssertionError(msg)

        if result2["title"] != "Test Group":
            msg = f"Expected title 'Test Group', got {result2['title']}"
            raise AssertionError(msg)

        # Verify that async_create_entry was called
        mock_create_entry.assert_called_once()


@pytest.mark.asyncio
async def test_group_subentry_flow_inheritance(
    hass: HomeAssistant,
    mock_group_parent_entry: MockConfigEntry,
    mock_global_config_entry: MockConfigEntry,
) -> None:
    """Test that group subentry flow correctly inherits values from global config."""
    # Add the required entries to hass
    mock_group_parent_entry.add_to_hass(hass)
    mock_global_config_entry.add_to_hass(hass)

    # Mock the temperature sensor helper function
    with patch(
        "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities",
        return_value=[
            {"label": "Indoor Temp", "value": "sensor.indoor_temp"},
            {"label": "Inherit from Global", "value": "-1"},
        ],
    ):
        # Create the subentry flow handler directly
        flow_handler = GroupSubentryFlowHandler()

        # Set the required attributes that would normally be set by Home Assistant
        flow_handler.hass = hass
        flow_handler.handler = DOMAIN
        flow_handler.parent_entry_id = mock_group_parent_entry.entry_id

        # Test inheritance by using "-1" values (inherit from global)
        user_input = {
            "name": "Test Group with Inheritance",
            "indoor_temperature_sensor": "-1",  # Inherit from global
            "diffuse_factor": "-1",  # Inherit from global
            "threshold_direct": "-1",  # Inherit from global
            "threshold_diffuse": "-1",  # Inherit from global
            "temperature_indoor_base": "-1",  # Inherit from global
            "temperature_outdoor_base": "-1",  # Inherit from global
        }

        result = await flow_handler.async_step_user(user_input)

        # Should proceed to enhanced step even with inheritance values
        if result["type"] != FlowResultType.FORM:
            msg = f"Expected form for enhanced step, got {result['type']}"
            raise AssertionError(msg)

        if result["step_id"] != "enhanced":
            msg = f"Expected step_id 'enhanced', got {result['step_id']}"
            raise AssertionError(msg)
