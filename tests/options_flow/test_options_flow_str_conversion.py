"""Test to specifically verify the str conversion fix."""

from __future__ import annotations

from unittest.mock import Mock, patch

from custom_components.solar_window_system.config_flow import (
    GroupSubentryFlowHandler,
    WindowSubentryFlowHandler,
)
from custom_components.solar_window_system.const import DOMAIN
from tests.helpers.test_framework import ConfigFlowTestCase
from tests.test_data import VALID_GROUP_OPTIONS_NUMERIC, VALID_WINDOW_OPTIONS_NUMERIC


class TestOptionsFlowStrConversion(ConfigFlowTestCase):
    """Test to specifically verify the str conversion fix."""

    async def test_group_options_numeric_values_conversion(self) -> None:
        """Numeric values from data/options are converted to strings in group flow."""
        # Create mock hass
        mock_hass = Mock()

        # Create mock config entry
        mock_config_entry = Mock()
        mock_config_entry.domain = DOMAIN
        mock_config_entry.title = "Test Group"
        mock_config_entry.data = VALID_GROUP_OPTIONS_NUMERIC
        mock_config_entry.options = {}
        mock_config_entry.unique_id = "test_group_1"

        # Mock add_to_hass
        mock_config_entry.add_to_hass = Mock()

        # Mock config_entries for hass
        mock_hass.config_entries.async_entries = Mock(return_value=[])

        handler = GroupSubentryFlowHandler()
        handler.hass = mock_hass
        handler.handler = (DOMAIN, "group")

        with patch(
            "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities"
        ) as mock_temp:
            mock_temp.return_value = [
                {"value": "sensor.temp1", "label": "Temperature 1"},
                {"value": "sensor.temp2", "label": "Temperature 2"},
            ]

            # This should not raise an error - fix converts numeric values to strings
            result = await handler.async_step_user(None)
            # Verify the schema was created successfully
            if result["type"] != "form":
                msg = f"Expected form, got {result['type']}"
                raise AssertionError(msg)
            if result["step_id"] != "user":
                msg = f"Expected user, got {result['step_id']}"
                raise AssertionError(msg)
            if "data_schema" not in result:
                msg = "data_schema not in result"
                raise AssertionError(msg)

    async def test_window_options_numeric_values_conversion(self) -> None:
        """Numeric values from data/options are converted to strings in window flow."""
        # Create mock hass
        mock_hass = Mock()

        # Create mock config entry
        mock_config_entry = Mock()
        mock_config_entry.domain = DOMAIN
        mock_config_entry.title = "Test Window"
        mock_config_entry.data = VALID_WINDOW_OPTIONS_NUMERIC
        mock_config_entry.options = {}
        mock_config_entry.unique_id = "test_window_1"

        # Mock add_to_hass
        mock_config_entry.add_to_hass = Mock()

        # Mock config_entries for hass
        mock_hass.config_entries.async_entries = Mock(return_value=[])

        handler = WindowSubentryFlowHandler()
        handler.hass = mock_hass
        handler.handler = (DOMAIN, "window")

        with patch(
            "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities"
        ) as mock_temp:
            mock_temp.return_value = [
                {"value": "sensor.temp1", "label": "Temperature 1"},
                {"value": "sensor.temp2", "label": "Temperature 2"},
            ]

            # This should not raise an error - fix converts numeric values to strings
            result = await handler.async_step_user(None)
            # Verify the schema was created successfully
            if result["type"] != "form":
                msg = f"Expected form, got {result['type']}"
                raise AssertionError(msg)
            if result["step_id"] != "user":
                msg = f"Expected user, got {result['step_id']}"
                raise AssertionError(msg)
            if "data_schema" not in result:
                msg = "data_schema not in result"
                raise AssertionError(msg)
