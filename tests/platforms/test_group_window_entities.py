"""Tests for group and window related entities."""

# ruff: noqa: ANN001,ARG002,FBT001,ARG001,FBT002,TRY004

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import DOMAIN
from custom_components.solar_window_system.sensor import (
    GroupWindowPowerSensor,
    async_setup_entry,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from tests.helpers.test_framework import IntegrationTestCase
from tests.test_data import MOCK_GROUP_SUBENTRIES, MOCK_WINDOW_SUBENTRIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestGroupWindowEntities(IntegrationTestCase):
    """Tests for group and window related entities."""

    test_type = "integration"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return ["hass", "global_config_entry"]

    def _create_mock_coordinator(self) -> AsyncMock:
        """Create a mock DataUpdateCoordinator."""
        coordinator = AsyncMock(spec=DataUpdateCoordinator)
        coordinator.data = {}  # Initialize with empty data
        return coordinator

    def _create_mock_group_config_entry(
        self, coordinator: AsyncMock
    ) -> MockConfigEntry:
        """Create a mock ConfigEntry for group configurations."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test Group Config",
            data={"entry_type": "group_configs"},
            entry_id="test_group_entry",
        )
        # Use shared subentry mocks
        entry.subentries = {k: Mock(**v) for k, v in MOCK_GROUP_SUBENTRIES.items()}  # type: ignore[assignment]
        return entry

    def _create_mock_window_config_entry(
        self, coordinator: AsyncMock
    ) -> MockConfigEntry:
        """Create a mock ConfigEntry for window configurations."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Test Window Config",
            data={"entry_type": "window_configs"},
            entry_id="test_window_entry",
        )
        # Use shared subentry mocks
        entry.subentries = {k: Mock(**v) for k, v in MOCK_WINDOW_SUBENTRIES.items()}  # type: ignore[assignment]
        return entry

    @pytest.mark.asyncio
    async def test_setup_group_power_sensors_creation(
        self, hass: HomeAssistant
    ) -> None:
        """Test that group power sensors are created correctly."""
        mock_coordinator = self._create_mock_coordinator()
        mock_group_config_entry = self._create_mock_group_config_entry(mock_coordinator)

        # Add the config entry to hass (public API).
        mock_group_config_entry.add_to_hass(hass)

        # Populate hass.data using the public hass API so the setup can access
        # the provided mock coordinator during the test.
        hass.data.setdefault(DOMAIN, {})[mock_group_config_entry.entry_id] = {
            "coordinator": mock_coordinator
        }

        # Create mock devices in device registry for the subentries
        dev_reg = dr.async_get(hass)
        for subentry_id, subentry in mock_group_config_entry.subentries.items():
            dev_reg.async_get_or_create(
                config_entry_id=mock_group_config_entry.entry_id,
                config_subentry_id=subentry_id,
                identifiers={(DOMAIN, f"group_{subentry_id}")},
                name=subentry.title,
                manufacturer="Solar Window System",
                model="Group",
            )

        # Track added entities
        added_entities = []

        def mock_add_entities(
            new_entities, update_before_add: bool = False, config_subentry_id=None
        ) -> None:
            added_entities.extend(list(new_entities))

        await async_setup_entry(hass, mock_group_config_entry, mock_add_entities)

        # Expect 2 groups * 3 sensors/group = 6 sensors
        expected_count = 6
        if len(added_entities) != expected_count:
            msg = f"Expected {expected_count} entities, got {len(added_entities)}"
            raise AssertionError(msg)

        # Verify unique IDs and device info for created sensors
        expected_unique_ids = {
            "sws_group_living_room_group_total_power",
            "sws_group_living_room_group_total_power_direct",
            "sws_group_living_room_group_total_power_diffuse",
            "sws_group_bedroom_group_total_power",
            "sws_group_bedroom_group_total_power_direct",
            "sws_group_bedroom_group_total_power_diffuse",
        }

        actual_unique_ids = {entity.unique_id for entity in added_entities}
        if actual_unique_ids != expected_unique_ids:
            msg = f"Expected unique_ids {expected_unique_ids}, got {actual_unique_ids}"
            raise AssertionError(msg)

        # Use identifiers in device_info to derive subentry IDs and assert they exist
        for entity in added_entities:
            if not isinstance(entity, GroupWindowPowerSensor):
                msg = f"Expected GroupWindowPowerSensor, got {type(entity)}"
                raise AssertionError(msg)
            if entity.device_info is None:
                msg = "Entity device_info should not be None"
                raise AssertionError(msg)
            identifiers = entity.device_info.get("identifiers", set())
            # Find the domain-specific identifier for the group
            domain_ids = [
                i for i in identifiers if i[0] == DOMAIN and i[1].startswith("group_")
            ]
            if not domain_ids:
                msg = "Expected a domain/group identifier in device_info"
                raise AssertionError(msg)
            # Extract and validate the subentry id
            _, full_id = domain_ids[0]
            # Accept any configured subentry key embedded in the identifier string
            if not any(k in full_id for k in mock_group_config_entry.subentries):
                msg = f"No valid subentry key found in {full_id}"
                raise AssertionError(msg)

    async def test_setup_window_power_sensors_creation(
        self, hass: HomeAssistant
    ) -> None:
        """Test that window power sensors are created correctly."""
        mock_coordinator = self._create_mock_coordinator()
        mock_window_config_entry = self._create_mock_window_config_entry(
            mock_coordinator
        )

        mock_window_config_entry.add_to_hass(hass)

        # Populate hass.data so setup can find the injected mock coordinator.
        hass.data.setdefault(DOMAIN, {})[mock_window_config_entry.entry_id] = {
            "coordinator": mock_coordinator
        }

        dev_reg = dr.async_get(hass)
        for subentry_id, subentry in mock_window_config_entry.subentries.items():
            dev_reg.async_get_or_create(
                config_entry_id=mock_window_config_entry.entry_id,
                config_subentry_id=subentry_id,
                identifiers={(DOMAIN, f"window_{subentry_id}")},
                name=subentry.title,
                manufacturer="Solar Window System",
                model="Window",
            )

        added_entities = []

        def mock_add_entities(
            new_entities, update_before_add: bool = False, config_subentry_id=None
        ) -> None:
            added_entities.extend(list(new_entities))

        await async_setup_entry(hass, mock_window_config_entry, mock_add_entities)

        # Expect 2 windows * 8 sensors/window = 16 sensors
        expected_count = 16
        if len(added_entities) != expected_count:
            msg = f"Expected {expected_count} entities, got {len(added_entities)}"
            raise AssertionError(msg)

        expected_unique_ids = {
            "sws_window_kitchen_window_total_power",
            "sws_window_kitchen_window_total_power_direct",
            "sws_window_kitchen_window_total_power_diffuse",
            "sws_window_kitchen_window_power_m2_total",
            "sws_window_kitchen_window_power_m2_diffuse",
            "sws_window_kitchen_window_power_m2_direct",
            "sws_window_kitchen_window_power_m2_raw",
            "sws_window_kitchen_window_total_power_raw",
            "sws_window_office_window_total_power",
            "sws_window_office_window_total_power_direct",
            "sws_window_office_window_total_power_diffuse",
            "sws_window_office_window_power_m2_total",
            "sws_window_office_window_power_m2_diffuse",
            "sws_window_office_window_power_m2_direct",
            "sws_window_office_window_power_m2_raw",
            "sws_window_office_window_total_power_raw",
        }

        actual_unique_ids = {entity.unique_id for entity in added_entities}
        if actual_unique_ids != expected_unique_ids:
            msg = f"Expected unique_ids {expected_unique_ids}, got {actual_unique_ids}"
            raise AssertionError(msg)

        # Use identifiers in device_info to derive subentry IDs and assert they exist
        for entity in added_entities:
            if not isinstance(entity, GroupWindowPowerSensor):
                msg = f"Expected GroupWindowPowerSensor, got {type(entity)}"
                raise AssertionError(msg)
            if entity.device_info is None:
                msg = "Entity device_info should not be None"
                raise AssertionError(msg)
            identifiers = entity.device_info.get("identifiers", set())
            domain_ids = [
                i for i in identifiers if i[0] == DOMAIN and i[1].startswith("window_")
            ]
            if not domain_ids:
                msg = "Expected a domain/window identifier in device_info"
                raise AssertionError(msg)
            _, full_id = domain_ids[0]
            if not any(k in full_id for k in mock_window_config_entry.subentries):
                msg = f"No valid subentry key found in {full_id}"
                raise AssertionError(msg)
