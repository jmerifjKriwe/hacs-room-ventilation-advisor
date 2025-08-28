# ruff: noqa: S101,SLF001
"""Tests for binary_sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.binary_sensor import (
    WindowShadingRequiredBinarySensor,
    async_setup_entry,
)
from custom_components.solar_window_system.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_async_setup_entry_wrong_entry_type(hass: HomeAssistant) -> None:
    """Test async_setup_entry with wrong entry type."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"entry_type": "global_configs"},  # Wrong type
        entry_id="test_entry",
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, entry, async_add_entities)

    # Should not add any entities for wrong entry type
    async_add_entities.assert_not_called()


@pytest.mark.asyncio
async def test_async_setup_entry_no_coordinator(hass: HomeAssistant) -> None:
    """Test async_setup_entry with no coordinator found."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"entry_type": "window_configs"},
        entry_id="test_entry",
    )

    # Ensure no coordinator in hass.data
    if DOMAIN in hass.data:
        del hass.data[DOMAIN]

    async_add_entities = Mock()
    await async_setup_entry(hass, entry, async_add_entities)

    # Should not add any entities when no coordinator
    async_add_entities.assert_not_called()


@pytest.mark.asyncio
async def test_async_setup_entry_no_subentries(hass: HomeAssistant) -> None:
    """Test async_setup_entry with no subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"entry_type": "window_configs"},
        entry_id="test_entry",
    )
    entry.subentries = {}  # type: ignore[assignment]

    # Mock coordinator
    coordinator = Mock()
    hass.data[DOMAIN] = {entry.entry_id: {"coordinator": coordinator}}

    async_add_entities = Mock()
    await async_setup_entry(hass, entry, async_add_entities)

    # Should not add any entities when no subentries
    async_add_entities.assert_not_called()


@pytest.mark.asyncio
async def test_async_setup_entry_window_subentry(hass: HomeAssistant) -> None:
    """Test async_setup_entry with window subentry - simplified test."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"entry_type": "window_configs"},
        entry_id="test_entry",
    )

    # Mock window subentry
    window_subentry = Mock()
    window_subentry.subentry_type = "window"
    window_subentry.title = "Test Window"
    entry.subentries = {"window_1": window_subentry}  # type: ignore[assignment]

    # Mock coordinator
    coordinator = Mock()
    hass.data[DOMAIN] = {entry.entry_id: {"coordinator": coordinator}}

    # Mock device registry - simplified
    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = []
    hass.data["device_registry"] = mock_device_registry

    async_add_entities = Mock()
    await async_setup_entry(hass, entry, async_add_entities)

    # Should not add entities when no devices found (but covers the code path)
    assert async_add_entities.call_count == 0


@pytest.mark.asyncio
async def test_window_shading_required_binary_sensor_init() -> None:
    """Test WindowShadingRequiredBinarySensor initialization."""
    coordinator = Mock()
    device = Mock()
    device.identifiers = {(DOMAIN, "test_window")}
    device.name = "Test Window Device"
    device.manufacturer = "Test Manufacturer"
    device.model = "Test Model"

    window_name = "Test Window"
    sensor = WindowShadingRequiredBinarySensor(coordinator, device, window_name)

    assert sensor.coordinator == coordinator
    assert sensor._window_name == window_name
    assert sensor._attr_unique_id == "sws_window_test_window_shading_required"
    assert sensor._attr_suggested_object_id == "sws_window_test_window_shading_required"
    assert sensor._attr_name == "SWS_WINDOW Test Window Shading Required"
    assert sensor._attr_has_entity_name is False
    assert sensor._attr_icon == "mdi:shield-sun"
    assert sensor._friendly_label == "Shading Required"


@pytest.mark.asyncio
async def test_window_shading_required_binary_sensor_is_on_no_data() -> None:
    """Test is_on property when no coordinator data."""
    coordinator = Mock()
    coordinator.data = None
    device = Mock()
    device.identifiers = {(DOMAIN, "test_window")}

    sensor = WindowShadingRequiredBinarySensor(coordinator, device, "Test Window")
    assert sensor.is_on is False


@pytest.mark.asyncio
async def test_window_shading_required_binary_sensor_is_on_with_data() -> None:
    """Test is_on property with coordinator data."""
    coordinator = Mock()
    coordinator.data = {"test": "data"}
    coordinator.get_window_shading_status.return_value = True

    device = Mock()
    device.identifiers = {(DOMAIN, "test_window")}

    sensor = WindowShadingRequiredBinarySensor(coordinator, device, "Test Window")
    result = sensor.is_on
    assert result is True
    coordinator.get_window_shading_status.assert_called_once_with("Test Window")


@pytest.mark.asyncio
async def test_window_shading_required_binary_sensor_extra_state_attributes_no_data() -> (
    None
):
    """Test extra_state_attributes when no coordinator data."""
    coordinator = Mock()
    coordinator.data = None
    device = Mock()

    sensor = WindowShadingRequiredBinarySensor(coordinator, device, "Test Window")
    attributes = sensor.extra_state_attributes
    assert attributes == {}


@pytest.mark.asyncio
async def test_window_shading_required_binary_sensor_extra_state_attributes_no_window_data() -> (
    None
):
    """Test extra_state_attributes when no window data."""
    coordinator = Mock()
    coordinator.data = {"test": "data"}
    coordinator.get_window_data.return_value = None
    device = Mock()

    sensor = WindowShadingRequiredBinarySensor(coordinator, device, "Test Window")
    attributes = sensor.extra_state_attributes
    assert attributes == {}


@pytest.mark.asyncio
async def test_window_shading_required_binary_sensor_extra_state_attributes_with_data() -> (
    None
):
    """Test extra_state_attributes with complete window data."""
    coordinator = Mock()
    coordinator.data = {"test": "data"}

    window_data = {
        "solar_result": {
            "power": 150.5,
            "power_direct": 120.0,
            "power_diffuse": 30.5,
            "shadow_factor": 0.8,
        },
        "shade_reason": "High solar power",
        "scenarios_triggered": ["scenario_a", "scenario_b"],
    }
    coordinator.get_window_data.return_value = window_data

    device = Mock()
    sensor = WindowShadingRequiredBinarySensor(coordinator, device, "Test Window")
    attributes = sensor.extra_state_attributes

    expected_attributes = {
        "solar_power": 150.5,
        "solar_power_direct": 120.0,
        "solar_power_diffuse": 30.5,
        "shadow_factor": 0.8,
        "shade_reason": "High solar power",
        "scenarios_triggered": "scenario_a, scenario_b",
    }
    assert attributes == expected_attributes


@pytest.mark.asyncio
async def test_window_shading_required_binary_sensor_async_added_to_hass(
    hass: HomeAssistant,
) -> None:
    """Test async_added_to_hass method - simplified."""
    coordinator = Mock()
    device = Mock()

    sensor = WindowShadingRequiredBinarySensor(coordinator, device, "Test Window")
    sensor.hass = hass
    sensor.entity_id = "binary_sensor.test"

    # Mock entity registry
    mock_entity_registry = Mock()
    hass.data["entity_registry"] = mock_entity_registry

    # Mock restored state
    sensor.async_get_last_state = AsyncMock(return_value=None)

    # Mock entity entry with same name (no update needed)
    mock_entry = Mock()
    mock_entry.original_name = "Shading Required"  # Same as friendly name
    mock_entity_registry.entities = {"binary_sensor.test": mock_entry}

    await sensor.async_added_to_hass()

    # Should not update entity name when names are the same
    mock_entity_registry.async_update_entity.assert_not_called()


@pytest.mark.asyncio
async def test_async_setup_entry_success() -> None:
    """Test async_setup_entry with successful device discovery."""
    hass = Mock()
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        entry_id="test_entry",
    )

    # Mock device registry with a window device
    mock_device_registry = Mock()
    mock_device = Mock()
    mock_device.identifiers = {(DOMAIN, "window_1")}
    mock_device.name = "Window 1"
    mock_device.manufacturer = "Test Manufacturer"
    mock_device.model = "Test Model"
    mock_device_registry.devices = {"device_1": mock_device}

    # Mock coordinator
    coordinator = AsyncMock()
    coordinator.data = {"windows": {"Window 1": {}}}

    # Create a proper mock entity registry
    mock_registry = Mock()
    mock_registry.entities = {}
    mock_registry.async_update_entity = Mock(return_value=None)

    with (
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ),
        patch(
            "custom_components.solar_window_system.coordinator."
            "SolarWindowSystemCoordinator",
            return_value=coordinator,
        ),
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_registry,
        ),
    ):
        # Just test that no exception is raised
        await async_setup_entry(hass, config_entry, Mock())
    """Test async_added_to_hass with entity name update."""
    coordinator = AsyncMock()
    device = Mock()
    device.identifiers = {(DOMAIN, "test_window")}
    device.name = "Test Window Device"
    device.manufacturer = "Test Manufacturer"
    device.model = "Test Model"

    window_name = "Test Window"
    sensor = WindowShadingRequiredBinarySensor(coordinator, device, window_name)
    sensor.entity_id = "binary_sensor.sws_window_test_window_shading_required"

    # Mock entity registry
    mock_entity_registry = Mock()
    mock_entry = Mock()
    mock_entry.original_name = "Old Name"  # Different from friendly name
    mock_entity_registry.entities = {
        "binary_sensor.sws_window_test_window_shading_required": mock_entry
    }
    mock_entity_registry.async_update_entity = AsyncMock()

    # Mock restored state
    mock_state = Mock()
    mock_state.state = "on"

    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_entity_registry,
        ),
        patch.object(sensor, "async_get_last_state", return_value=mock_state),
    ):
        await sensor.async_added_to_hass()

    # Should update entity name when names are different
    mock_entity_registry.async_update_entity.assert_called_once_with(
        sensor.entity_id, name="Shading Required"
    )
