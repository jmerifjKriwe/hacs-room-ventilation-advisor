"""Tests to verify string conversion in options flow handlers."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.config_flow import (
    GroupSubentryFlowHandler,
    WindowSubentryFlowHandler,
)
from custom_components.solar_window_system.const import DOMAIN
from homeassistant.core import HomeAssistant
from tests.helpers.test_framework import ConfigFlowTestCase
from tests.test_data import VALID_GROUP_OPTIONS_NUMERIC, VALID_WINDOW_OPTIONS_NUMERIC


class TestOptionsFlowStrConversion(ConfigFlowTestCase):
    """Tests to verify string conversion in options flow handlers."""

    async def test_group_options_numeric_conversion(self, hass: HomeAssistant) -> None:
        """Test that group options flow handles numeric values correctly."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test Group",
            data=VALID_GROUP_OPTIONS_NUMERIC,
            options={},
            unique_id="test_group_1",
        )
        config_entry.add_to_hass(hass)

        handler = GroupSubentryFlowHandler()
        handler.hass = hass
        handler.handler = (DOMAIN, "group")

        with patch(
            "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities"
        ) as mock_temp:
            mock_temp.return_value = [
                {"value": "sensor.temp1", "label": "Temperature 1"},
                {"value": "sensor.temp2", "label": "Temperature 2"},
            ]

        result = await handler.async_step_user(None)
        if result["type"] != "form":
            msg = f"Expected form, got {result['type']}"
            raise AssertionError(msg)
        if result["step_id"] != "user":
            msg = f"Expected user, got {result['step_id']}"
            raise AssertionError(msg)
        if "data_schema" not in result:
            msg = "Expected data_schema in result"
            raise AssertionError(msg)

    async def test_window_options_numeric_conversion(self, hass: HomeAssistant) -> None:
        """Test that window options flow handles numeric values correctly."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test Window",
            data=VALID_WINDOW_OPTIONS_NUMERIC,
            options={},
            unique_id="test_window_1",
        )
        config_entry.add_to_hass(hass)

        handler = WindowSubentryFlowHandler()
        handler.hass = hass
        handler.handler = (DOMAIN, "window")

        with patch(
            "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities"
        ) as mock_temp:
            mock_temp.return_value = [
                {"value": "sensor.temp1", "label": "Temperature 1"},
                {"value": "sensor.temp2", "label": "Temperature 2"},
            ]

        result = await handler.async_step_user(None)
        if result["type"] != "form":
            msg = f"Expected form, got {result['type']}"
            raise AssertionError(msg)
        if result["step_id"] != "user":
            msg = f"Expected user, got {result['step_id']}"
            raise AssertionError(msg)
        if "data_schema" not in result:
            msg = "Expected data_schema in result"
            raise AssertionError(msg)
