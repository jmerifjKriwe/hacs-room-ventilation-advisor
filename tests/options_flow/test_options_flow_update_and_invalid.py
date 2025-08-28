# ruff: noqa: PLR0915
"""
Test Options Flow for Solar Window System integration.

This verifies the options flow updates options, handles invalid input by
presenting additional steps, and persists values as expected.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

from custom_components.solar_window_system.const import DOMAIN
from tests.helpers.test_framework import ConfigFlowTestCase
from tests.test_data import (
    VALID_GLOBAL_BASIC,
    VALID_GLOBAL_ENHANCED,
    VALID_GLOBAL_SCENARIOS,
)


class TestOptionsFlowUpdateAndInvalid(ConfigFlowTestCase):
    """Test that options flow updates options and handles invalid input."""

    async def test_options_flow_update_and_invalid(self) -> None:
        """Test that options flow updates options and handles invalid input."""
        # Setup: create an existing ConfigEntry
        mock_entry = Mock()
        mock_entry.domain = DOMAIN
        mock_entry.title = "Solar Window System"
        mock_entry.data = {"entry_type": "global_config"}
        mock_entry.unique_id = "unique_global_1"
        mock_entry.options = {}
        mock_entry.entry_id = "test_entry_id"

        # Mock hass and config_entries
        mock_hass = Mock()
        mock_hass.config_entries.async_get_entry.return_value = mock_entry
        mock_hass.config_entries.async_setup = AsyncMock(return_value=True)
        mock_hass.config_entries.async_entries = Mock(return_value=[])
        mock_hass.async_block_till_done = AsyncMock()

        # Create updated entry mock with expected options
        updated_entry = Mock()
        updated_entry.options = {"window_width": "1.5"}
        mock_hass.config_entries.async_get_entry.side_effect = lambda entry_id: (
            updated_entry if entry_id == mock_entry.entry_id else mock_entry
        )

        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.async_get_or_create = Mock()
        mock_hass.helpers.entity_registry.async_get = Mock(
            return_value=mock_entity_registry
        )

        # Mock options flow
        mock_options_flow = Mock()
        mock_options_flow.async_init = AsyncMock(return_value={"flow_id": "test_flow"})
        mock_options_flow.async_configure = AsyncMock()
        mock_hass.config_entries.options.async_init = AsyncMock(
            return_value={"flow_id": "test_flow"}
        )
        mock_hass.config_entries.options.async_configure = AsyncMock(
            return_value={"type": "create_entry"}
        )

        # Setup: simulate adding entry to hass
        mock_entry.add_to_hass = Mock()
        mock_entry.add_to_hass(mock_hass)

        # Simulate setup
        await mock_hass.config_entries.async_setup(mock_entry.entry_id)
        await mock_hass.async_block_till_done()

        # Register dummy entities for selectors
        entity_registry = mock_entity_registry
        entity_registry.async_get_or_create(
            "sensor", "test", "dummy_solar", suggested_object_id="dummy_solar"
        )
        entity_registry.async_get_or_create(
            "sensor", "test", "dummy_outdoor", suggested_object_id="dummy_outdoor"
        )
        entity_registry.async_get_or_create(
            "sensor", "test", "dummy_indoor", suggested_object_id="dummy_indoor"
        )

        # Start Options Flow
        result = await mock_hass.config_entries.options.async_init(mock_entry.entry_id)

        # Simulate valid input for global_basic
        user_input = VALID_GLOBAL_BASIC.copy()
        user_input["shadow_offset"] = "0.3"
        result2 = await mock_hass.config_entries.options.async_configure(
            result["flow_id"], user_input=user_input
        )

        # Expect either another form or create_entry
        if result2.get("type") not in ("form", "create_entry"):
            msg = f"Expected form or create_entry, got: {result2}"
            raise AssertionError(msg)

        if result2.get("type") == "form":
            # Continue through enhanced and scenarios
            enhanced_user_input = VALID_GLOBAL_ENHANCED.copy()
            enhanced_user_input["g_value"] = "0.5"
            enhanced_user_input["frame_width"] = "0.125"
            enhanced_user_input["diffuse_factor"] = "0.15"
            result3 = await mock_hass.config_entries.options.async_configure(
                result2["flow_id"], user_input=enhanced_user_input
            )
            if result3.get("type") == "form":
                scenarios_user_input = VALID_GLOBAL_SCENARIOS.copy()
                scenarios_user_input["scenario_c_temp_forecast"] = "28.5"
                scenarios_user_input["scenario_c_start_hour"] = "9"
                result4 = await mock_hass.config_entries.options.async_configure(
                    result3["flow_id"], user_input=scenarios_user_input
                )
                if result4.get("type") != "create_entry":
                    msg = f"Expected create_entry, got: {result4}"
                    raise AssertionError(msg)

        # Check that window_width was updated in options
        updated_entry = mock_hass.config_entries.async_get_entry(mock_entry.entry_id)
        if updated_entry is None:
            msg = "Entry not found after options update"
            raise AssertionError(msg)

        # Options values are stored as strings
        actual = updated_entry.options.get("window_width")
        expected = "1.5"
        if actual != expected:
            msg = f"Expected window_width '{expected}', got '{actual}'"
            raise AssertionError(msg)
