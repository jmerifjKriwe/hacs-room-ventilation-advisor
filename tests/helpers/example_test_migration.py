"""
Example test file demonstrating the new standardized test framework.

This file shows how to use the new BaseTestCase classes and TestPatterns
for consistent test structure across the Solar Window System test suite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.helpers.test_framework import ConfigFlowTestCase, TestPatterns

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestGlobalConfigFlow(ConfigFlowTestCase):
    """Test global config flow using standardized framework."""

    async def test_init_shows_basic_step(self, hass: HomeAssistant) -> None:
        """Test that config flow initialization shows the basic step."""
        result = await self.init_flow(hass, "user")
        TestPatterns.assert_config_flow_result(result, "form", "global_basic")

    async def test_basic_step_with_valid_data(self, hass: HomeAssistant) -> None:
        """Test basic step with valid configuration data."""
        # First initialize the flow
        result = await self.init_flow(hass, "user")
        TestPatterns.assert_config_flow_result(result, "form", "global_basic")

        # Submit valid form data
        form_data = {
            "name": "Test System",
            "latitude": 52.52,
            "longitude": 13.405,
            "timezone": "Europe/Berlin",
        }
        result = await self.submit_form(hass, "global_basic", form_data)
        TestPatterns.assert_config_flow_result(result, "form", "global_enhanced")

    async def test_basic_step_with_invalid_data(self, hass: HomeAssistant) -> None:
        """Test basic step with invalid configuration data."""
        result = await self.init_flow(hass, "user")
        TestPatterns.assert_config_flow_result(result, "form", "global_basic")

        # Submit invalid form data (empty name)
        form_data = {
            "name": "",
            "latitude": 52.52,
            "longitude": 13.405,
            "timezone": "Europe/Berlin",
        }
        result = await self.submit_form(hass, "global_basic", form_data)
        TestPatterns.assert_config_flow_result(result, "form", "global_basic")


class TestWindowConfigFlow(ConfigFlowTestCase):
    """Test window config flow using standardized framework."""

    async def test_window_creation_flow(self, hass: HomeAssistant) -> None:
        """Test complete window creation flow."""
        # Initialize window creation flow
        result = await self.init_flow(hass, "user", {"entry_type": "window"})
        TestPatterns.assert_config_flow_result(result, "form", "window_basic")

        # Submit window basic configuration
        window_data = {
            "name": "Living Room Window",
            "width": 1.5,
            "height": 2.0,
            "orientation": "south",
        }
        result = await self.submit_form(hass, "window_basic", window_data)
        TestPatterns.assert_config_flow_result(result, "form", "window_enhanced")


class TestGroupConfigFlow(ConfigFlowTestCase):
    """Test group config flow using standardized framework."""

    async def test_group_creation_flow(self, hass: HomeAssistant) -> None:
        """Test complete group creation flow."""
        # Initialize group creation flow
        result = await self.init_flow(hass, "user", {"entry_type": "group"})
        TestPatterns.assert_config_flow_result(result, "form", "group_basic")

        # Submit group basic configuration
        group_data = {
            "name": "Living Room Windows",
            "description": "All windows in living room",
        }
        result = await self.submit_form(hass, "group_basic", group_data)
        TestPatterns.assert_config_flow_result(result, "form", "group_enhanced")
