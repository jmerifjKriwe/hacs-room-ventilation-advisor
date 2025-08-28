# ruff: noqa: TRY004
"""Integration/unit tests for SolarWindowSystemCoordinator using framework."""

from __future__ import annotations

import types
from unittest.mock import MagicMock, Mock, patch

from custom_components.solar_window_system.calculator import SolarWindowCalculator
from custom_components.solar_window_system.coordinator import (
    SolarWindowSystemCoordinator,
)
from homeassistant.helpers.update_coordinator import UpdateFailed
from tests.helpers.test_framework import IntegrationTestCase


class TestCoordinator(IntegrationTestCase):
    """Coordinator tests using standardized framework."""

    async def test_coordinator_initialization(self) -> None:
        """Test coordinator initialization."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, window_entry, 1)

        if coordinator.hass != fake_hass_magicmock:
            msg = "Coordinator hass should match fake_hass_magicmock"
            raise AssertionError(msg)
        if coordinator.entry != window_entry:
            msg = "Coordinator entry should match window_entry"
            raise AssertionError(msg)
        if coordinator.calculator is None:
            msg = "Coordinator calculator should not be None"
            raise AssertionError(msg)
        if not isinstance(coordinator.calculator, SolarWindowCalculator):
            msg = "Coordinator calculator should be SolarWindowCalculator instance"
            raise AssertionError(msg)

    async def test_coordinator_update_data(self) -> None:
        """Test coordinator update data."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}
        # Use SimpleNamespace to match attribute access and provide
        # all required window fields
        window_entry.subentries = {
            "window_1": types.SimpleNamespace(
                title="Living Room Window",
                subentry_type="window",
                data={
                    "entry_type": "window",
                    "azimuth": 180,
                    "azimuth_min": -90,
                    "azimuth_max": 90,
                    "elevation_min": 0,
                    "elevation_max": 90,
                    "window_width": 1.2,
                    "window_height": 1.5,
                    "shadow_depth": 0.2,
                    "shadow_offset": 0.1,
                    "room_temperature_sensor": "sensor.room_temp_living",
                },
            ),
            "window_2": types.SimpleNamespace(
                title="Bedroom Window",
                subentry_type="window",
                data={
                    "entry_type": "window",
                    "azimuth": 90,
                    "azimuth_min": -90,
                    "azimuth_max": 90,
                    "elevation_min": 0,
                    "elevation_max": 90,
                    "window_width": 1.0,
                    "window_height": 1.2,
                    "shadow_depth": 0.1,
                    "shadow_offset": 0.05,
                    "room_temperature_sensor": "sensor.room_temp_bedroom",
                },
            ),
        }
        # Patch hass.config_entries.async_entries to return [mock_entry]
        fake_hass_magicmock.config_entries.async_entries.return_value = [window_entry]

        # Mock the calculator methods that are called during update
        with patch.object(
            SolarWindowCalculator,
            "calculate_all_windows_from_flows",
            return_value={
                "summary": {
                    "total_power": 1000,
                    "window_count": 2,
                    "shading_count": 1,
                    "calculation_time": 0.1,
                },
                "windows": {
                    "Living Room Window": {"requires_shading": True},
                    "Bedroom Window": {"requires_shading": False},
                },
            },
        ):
            coordinator = SolarWindowSystemCoordinator(
                fake_hass_magicmock, window_entry, 1
            )

            # Perform first update
            await coordinator.async_refresh()

            if coordinator.data is None:
                msg = "Coordinator data should not be None after refresh"
                raise AssertionError(msg)
        # Accept either legacy or new structure
        if "summary" in coordinator.data:
            summary = coordinator.data["summary"]
            if "total_power" not in summary:
                msg = "Summary should contain total_power"
                raise AssertionError(msg)
            if "window_count" not in summary:
                msg = "Summary should contain window_count"
                raise AssertionError(msg)
            if "shading_count" not in summary:
                msg = "Summary should contain shading_count"
                raise AssertionError(msg)
            if "calculation_time" not in summary:
                msg = "Summary should contain calculation_time"
                raise AssertionError(msg)
            if "windows" not in coordinator.data:
                msg = "Coordinator data should contain windows"
                raise AssertionError(msg)
        else:
            # New structure: windows dict must be present and non-empty
            if "windows" not in coordinator.data:
                msg = "Coordinator data should contain windows"
                raise AssertionError(msg)
            if not isinstance(coordinator.data["windows"], dict):
                msg = "Coordinator data windows should be dict"
                raise AssertionError(msg)
            if len(coordinator.data["windows"]) == 0:
                msg = "Coordinator data windows should not be empty"
                raise AssertionError(msg)

    async def test_coordinator_window_data_access(self) -> None:
        """Test coordinator window data access methods."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, window_entry, 1)

        # Perform first update
        with patch.object(
            SolarWindowCalculator,
            "calculate_all_windows_from_flows",
            return_value={
                "summary": {
                    "total_power": 1000,
                    "window_count": 2,
                    "shading_count": 1,
                    "calculation_time": 0.1,
                },
                "windows": {
                    "Living Room Window": {"requires_shading": True},
                    "Bedroom Window": {"requires_shading": False},
                },
            },
        ):
            await coordinator.async_refresh()

        # Test window data access methods
        living_room_shading = coordinator.get_window_shading_status(
            "Living Room Window"
        )
        bedroom_shading = coordinator.get_window_shading_status("Bedroom Window")

        # These should be boolean values
        if not isinstance(living_room_shading, bool):
            msg = "Living room shading should be boolean"
            raise TypeError(msg)
        if not isinstance(bedroom_shading, bool):
            msg = "Bedroom shading should be boolean"
            raise TypeError(msg)

        # Test get_window_data method
        living_room_data = coordinator.get_window_data("Living Room Window")
        bedroom_data = coordinator.get_window_data("Bedroom Window")

        if not isinstance(living_room_data, dict):
            msg = "Living room data should be dict"
            raise TypeError(msg)
        if not isinstance(bedroom_data, dict):
            msg = "Bedroom data should be dict"
            raise TypeError(msg)

    async def test_coordinator_reconfigure(self) -> None:
        """Test coordinator reconfigure."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, window_entry, 1)

        # Perform first update
        with patch.object(
            SolarWindowCalculator,
            "calculate_all_windows_from_flows",
            return_value={
                "summary": {
                    "total_power": 1000,
                    "window_count": 2,
                    "shading_count": 1,
                    "calculation_time": 0.1,
                },
                "windows": {
                    "Living Room Window": {"requires_shading": True},
                    "Bedroom Window": {"requires_shading": False},
                },
            },
        ):
            await coordinator.async_refresh()

        # Reconfigure
        await coordinator.async_reconfigure()

        # Data should be refreshed
        with patch.object(
            SolarWindowCalculator,
            "calculate_all_windows_from_flows",
            return_value={
                "summary": {
                    "total_power": 1000,
                    "window_count": 2,
                    "shading_count": 1,
                    "calculation_time": 0.1,
                },
                "windows": {
                    "Living Room Window": {"requires_shading": True},
                    "Bedroom Window": {"requires_shading": False},
                },
            },
        ):
            await coordinator.async_refresh()
        if coordinator.data is None:
            msg = "Coordinator data should not be None after reconfigure"
            raise AssertionError(msg)

        # Calculator should still be available
        if coordinator.calculator is None:
            msg = "Coordinator calculator should not be None after reconfigure"
            raise AssertionError(msg)

    def test_coordinator_with_missing_calculator(self) -> None:
        """Test coordinator with missing calculator."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}
        entry = window_entry
        entry.subentries = None

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, entry, 1)

        # Calculator should be None if initialization fails
        # But coordinator should still be created
        if coordinator.hass != fake_hass_magicmock:
            msg = "Coordinator hass should match fake_hass_magicmock"
            raise AssertionError(msg)
        if coordinator.entry != entry:
            msg = "Coordinator entry should match window_entry"
            raise AssertionError(msg)

    async def test_flow_based_calculation_called(self) -> None:
        """Test flow based calculation called."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, window_entry, 1)

        # Mock the calculate_all_windows_from_flows method to verify it's called
        if coordinator.calculator is not None:
            coordinator.calculator.calculate_all_windows_from_flows = MagicMock(
                return_value={
                    "summary": {
                        "total_power": 1000,
                        "window_count": 2,
                        "shading_count": 1,
                    },
                    "windows": {
                        "Living Room Window": {"requires_shading": True},
                        "Bedroom Window": {"requires_shading": False},
                    },
                }
            )

            # Perform update
            await coordinator.async_refresh()

            # Verify the flow-based method was called
            coordinator.calculator.calculate_all_windows_from_flows.assert_called_once()

            # Verify data is correct
            if coordinator.data["summary"]["window_count"] != 2:  # noqa: PLR2004
                msg = "Window count should be 2"
                raise AssertionError(msg)
            if coordinator.get_window_shading_status("Living Room Window") is not True:
                msg = "Living room should require shading"
                raise AssertionError(msg)
            if coordinator.get_window_shading_status("Bedroom Window") is not False:
                msg = "Bedroom should not require shading"
                raise AssertionError(msg)

    async def test_coordinator_setup_calculator_exception(self) -> None:
        """Test coordinator setup calculator exception handling."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        # Mock SolarWindowCalculator.from_flows to raise an exception
        with patch.object(
            SolarWindowCalculator,
            "from_flows",
            side_effect=ValueError("Test exception"),
        ):
            coordinator = SolarWindowSystemCoordinator(
                fake_hass_magicmock, window_entry, 1
            )

            # Calculator should be None after exception
            if coordinator.calculator is not None:
                msg = "Coordinator calculator should be None after exception"
                raise AssertionError(msg)

    async def test_async_update_data_no_calculator(self) -> None:
        """Test _async_update_data when calculator is None."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, window_entry, 1)
        # Force calculator to be None
        coordinator.calculator = None

        # Call _async_update_data
        result = await coordinator._async_update_data()  # noqa: SLF001

        # Should return empty dict
        if result != {}:
            msg = "Should return empty dict when calculator is None"
            raise AssertionError(msg)

    async def test_async_update_data_calculation_exception(self) -> None:
        """Test _async_update_data when calculation raises exception."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, window_entry, 1)

        # Mock calculate_all_windows_from_flows to raise an exception
        with patch.object(
            SolarWindowCalculator,
            "calculate_all_windows_from_flows",
            side_effect=ValueError("Calculation error"),
        ):
            # Should raise UpdateFailed
            try:
                await coordinator._async_update_data()  # noqa: SLF001
                msg = "Should have raised UpdateFailed"
                raise AssertionError(msg)
            except UpdateFailed:
                pass  # Expected

    async def test_async_update_data_missing_keys(self) -> None:
        """Test _async_update_data when result is missing windows/groups keys."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, window_entry, 1)

        # Mock calculate_all_windows_from_flows to return incomplete result
        with patch.object(
            SolarWindowCalculator,
            "calculate_all_windows_from_flows",
            return_value={"summary": {"total_power": 1000}},
        ):
            result = await coordinator._async_update_data()  # noqa: SLF001

            # Should have windows and groups keys added
            if "windows" not in result:
                msg = "Should have windows key added"
                raise AssertionError(msg)
            if "groups" not in result:
                msg = "Should have groups key added"
                raise AssertionError(msg)
            if result["windows"] != {}:
                msg = "Windows should be empty dict"
                raise AssertionError(msg)
            if result["groups"] != {}:
                msg = "Groups should be empty dict"
                raise AssertionError(msg)

    async def test_get_window_shading_status_no_data(self) -> None:
        """Test get_window_shading_status when coordinator has no data."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, window_entry, 1)

        # Data is None initially
        result = coordinator.get_window_shading_status("test_window")

        # Should return False
        if result is not False:
            msg = "Should return False when no data"
            raise AssertionError(msg)

    async def test_get_window_data_no_data(self) -> None:
        """Test get_window_data when coordinator has no data."""
        fake_hass_magicmock = Mock()
        window_entry = Mock()
        window_entry.data = {"entry_type": "window_configs"}

        # Mock config_entries.async_entries to return empty list
        fake_hass_magicmock.config_entries.async_entries.return_value = []

        coordinator = SolarWindowSystemCoordinator(fake_hass_magicmock, window_entry, 1)

        # Data is None initially
        result = coordinator.get_window_data("test_window")

        # Should return empty dict
        if result != {}:
            msg = "Should return empty dict when no data"
            raise AssertionError(msg)
