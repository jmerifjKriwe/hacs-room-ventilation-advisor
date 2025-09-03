"""Test the sensor platform for Room Ventilation Advisor integration."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.room_ventilation_advisor.const import (
    CONF_ROOMS,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.room_ventilation_advisor.sensor import (
    VentilationDataUpdateCoordinator,
    VentilationSensor,
    async_setup_entry,
)


class TestVentilationSensor:
    """Test the VentilationSensor class."""

    async def test_sensor_initialization(self, hass: HomeAssistant) -> None:
        """Test sensor initialization."""
        # Mock config entry
        config_entry = MagicMock()
        config_entry.entry_id = "test_entry_id"
        config_entry.data = {}
        config_entry.options = {}

        # Create coordinator
        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)

        # Create sensor
        room_config = {
            "temp_sensor": "sensor.temp",
            "room_type": "living_room",
        }
        sensor = VentilationSensor(coordinator, "Living Room", room_config)

        assert sensor.room_name == "Living Room"
        assert sensor.room_config == room_config
        assert sensor._attr_unique_id == "test_entry_id_Living Room"
        assert sensor._attr_name == "Living Room Ventilation Score"
        assert sensor._attr_has_entity_name is True

    async def test_sensor_device_info(self, hass: HomeAssistant) -> None:
        """Test sensor device info."""
        config_entry = MagicMock()
        config_entry.entry_id = "test_entry_id"
        config_entry.data = {}
        config_entry.options = {}

        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)
        sensor = VentilationSensor(coordinator, "Test Room", {})

        device_info = sensor._attr_device_info
        assert device_info is not None
        assert "identifiers" in device_info
        assert "name" in device_info
        assert device_info["identifiers"] == {(DOMAIN, "test_entry_id")}
        assert device_info["name"] == "Room Ventilation Advisor"


class TestVentilationDataUpdateCoordinator:
    """Test the VentilationDataUpdateCoordinator class."""

    async def test_coordinator_initialization(self, hass: HomeAssistant) -> None:
        """Test coordinator initialization."""
        config_entry = MagicMock()
        config_entry.data = {CONF_SCAN_INTERVAL: 600}
        config_entry.options = {}

        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)

        assert coordinator.entry == config_entry
        assert coordinator.update_interval is not None
        assert coordinator.update_interval.seconds == 600

    async def test_get_sensor_value_none(self, hass: HomeAssistant) -> None:
        """Test getting sensor value with None entity_id."""
        config_entry = MagicMock()
        config_entry.data = {}
        config_entry.options = {}
        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)

        assert coordinator._get_sensor_value(None) is None


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    async def test_async_setup_entry_no_rooms(self, hass: HomeAssistant) -> None:
        """Test async_setup_entry with no rooms configured."""
        config_entry = MagicMock()
        config_entry.data = {CONF_ROOMS: {}}
        config_entry.options = {}

        mock_async_add_entities = MagicMock()

        await async_setup_entry(hass, config_entry, mock_async_add_entities)

        # Verify no entities were added
        mock_async_add_entities.assert_called_once_with([])
