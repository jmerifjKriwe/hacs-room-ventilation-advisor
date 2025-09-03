"""Test the sensor platform for Room Ventilation Advisor integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.room_ventilation_advisor.const import (
    CONF_ENABLED,
    CONF_ROOMS,
    CONF_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.room_ventilation_advisor.sensor import (
    ICON_VENTILATION_GOOD,
    ICON_VENTILATION_MODERATE,
    ICON_VENTILATION_POOR,
    VentilationDataUpdateCoordinator,
    VentilationSensor,
    async_setup_entry,
)


class TestVentilationSensor:
    """Test the VentilationSensor class."""

    async def test_sensor_initialization(self, hass: HomeAssistant) -> None:
        """Test sensor initialization."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_id",
            data={},
        )

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
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_id",
            data={},
        )
        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)
        sensor = VentilationSensor(coordinator, "Test Room", {})

        device_info = sensor._attr_device_info
        assert device_info is not None
        assert "identifiers" in device_info
        assert "name" in device_info
        assert device_info["identifiers"] == {(DOMAIN, "test_entry_id")}
        assert device_info["name"] == "Room Ventilation Advisor"

    async def test_sensor_state_and_attributes(self, hass: HomeAssistant) -> None:
        """Test sensor state and attributes after coordinator update."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            entry_id="test_entry_id",
            data={CONF_ROOMS: {"Living Room": {"room_type": "living_room"}}},
        )
        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)
        sensor = VentilationSensor(
            coordinator,
            "Living Room",
            {"room_type": "living_room"},
        )
        sensor.hass = hass
        sensor.async_write_ha_state = MagicMock()

        # Mock coordinator data
        coordinator.data = {
            "outdoor_temp": 10,
            "outdoor_humidity": 70,
            "wind_speed": 5,
            "rooms": {
                "Living Room": {
                    "indoor_temp": 20,
                    "indoor_humidity": 60,
                    "co2_level": 800,
                    "room_type": "living_room",
                },
            },
        }

        # Manually trigger update
        sensor._handle_coordinator_update()

        # Assertions
        assert sensor.native_value is not None
        assert isinstance(sensor.native_value, float)
        attrs = sensor.extra_state_attributes
        assert attrs is not None
        assert attrs["temperature_indoor"] == 20
        assert attrs["humidity_indoor"] == 60
        assert attrs["co2_level"] == 800
        assert attrs["temperature_outdoor"] == 10
        assert attrs["humidity_outdoor"] == 70
        assert attrs["wind_speed"] == 5

        # For these inputs the computed score is just below the 'good' threshold
        # so we expect a 'Moderate ventilation' recommendation.
        assert "Moderate ventilation" in attrs["ventilation_advice"]

    @pytest.mark.parametrize(
        ("score", "expected_icon"),
        [
            (0.8, ICON_VENTILATION_GOOD),
            (0.3, ICON_VENTILATION_MODERATE),
            (-0.1, ICON_VENTILATION_POOR),
            (None, "mdi:fan"),
        ],
    )
    async def test_icon_update(
        self,
        hass: HomeAssistant,
        score: float | None,
        expected_icon: str,
    ) -> None:
        """Test that the icon updates based on the score."""
        config_entry = MockConfigEntry(domain=DOMAIN, data={})
        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)
        sensor = VentilationSensor(coordinator, "Test Room", {})

        with patch.object(
            VentilationSensor,
            "native_value",
            new_callable=MagicMock,
        ) as mock_native_value:
            mock_native_value.__get__ = MagicMock(return_value=score)
            sensor._update_icon()
            assert sensor.icon == expected_icon

    async def test_native_value_missing_data(self, hass: HomeAssistant) -> None:
        """Test native_value returns None when data is missing."""
        config_entry = MockConfigEntry(domain=DOMAIN, data={})
        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)
        sensor = VentilationSensor(coordinator, "Test Room", {})

        # No data in coordinator
        coordinator.data = {}
        assert sensor.native_value is None


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

    @pytest.mark.parametrize(
        ("state", "expected_value"),
        [
            ("21.5", 21.5),
            ("unknown", None),
            ("unavailable", None),
            ("not_a_number", None),
            (None, None),
        ],
    )
    async def test_get_sensor_value(
        self,
        hass: HomeAssistant,
        state: str | None,
        expected_value: float | None,
    ) -> None:
        """Test getting sensor value for various states."""
        config_entry = MockConfigEntry(domain=DOMAIN, data={})
        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)
        entity_id = "sensor.test"

        if state is not None:
            hass.states.async_set(entity_id, state)

        assert coordinator._get_sensor_value(entity_id) == expected_value

    async def test_async_update_data_success(self, hass: HomeAssistant) -> None:
        """Test successful data update."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind",
                CONF_ROOMS: {
                    "Living Room": {
                        "temp_sensor": "sensor.living_temp",
                        "humidity_sensor": "sensor.living_humidity",
                        "co2_sensor": "sensor.living_co2",
                        "room_type": "living_room",
                        "enabled": True,
                    },
                    "Office": {
                        "temp_sensor": "sensor.office_temp",
                        "humidity_sensor": "sensor.office_humidity",
                        "room_type": "office",
                        "enabled": False,  # Should be skipped
                    },
                },
            },
        )
        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)

        # Set sensor states
        hass.states.async_set("sensor.outdoor_temp", "10.0")
        hass.states.async_set("sensor.outdoor_humidity", "75.0")
        hass.states.async_set("sensor.wind", "5.0")
        hass.states.async_set("sensor.living_temp", "21.0")
        hass.states.async_set("sensor.living_humidity", "55.0")
        hass.states.async_set("sensor.living_co2", "850")
        hass.states.async_set("sensor.office_temp", "22.0")

        data = await coordinator._async_update_data()

        assert data["outdoor_temp"] == 10.0
        assert data["outdoor_humidity"] == 75.0
        assert data["wind_speed"] == 5.0
        assert "Living Room" in data["rooms"]
        assert "Office" not in data["rooms"]  # Check that disabled room is skipped
        assert data["rooms"]["Living Room"]["indoor_temp"] == 21.0
        assert data["rooms"]["Living Room"]["co2_level"] == 850

    async def test_async_update_data_missing_sensor(self, hass: HomeAssistant) -> None:
        """Test data update with a missing sensor."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={"outdoor_temp_sensor": "sensor.non_existent"},
        )
        coordinator = VentilationDataUpdateCoordinator(hass, config_entry)

        # Missing outdoor temp sensor should result in None
        data = await coordinator._async_update_data()
        assert data["outdoor_temp"] is None


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    async def test_async_setup_entry_no_rooms(self, hass: HomeAssistant) -> None:
        """Test async_setup_entry with no rooms configured."""
        config_entry = MockConfigEntry(domain=DOMAIN, data={CONF_ROOMS: {}})
        mock_async_add_entities = AsyncMock()

        await async_setup_entry(hass, config_entry, mock_async_add_entities)

        # Verify no entities were added; ensure update_before_add keyword was used
        mock_async_add_entities.assert_called_once()
        called_args, called_kwargs = mock_async_add_entities.call_args
        assert called_args[0] == []
        assert called_kwargs.get("update_before_add", False) is True

    async def test_async_setup_entry_with_rooms(self, hass: HomeAssistant) -> None:
        """Test async_setup_entry with enabled and disabled rooms."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ROOMS: {
                    "Living Room": {CONF_ENABLED: True, "temp_sensor": "sensor.temp1"},
                    "Bedroom": {CONF_ENABLED: True, "temp_sensor": "sensor.temp2"},
                    "Office": {CONF_ENABLED: False, "temp_sensor": "sensor.temp3"},
                },
            },
        )
        mock_async_add_entities = AsyncMock()

        with patch(
            "custom_components.room_ventilation_advisor.sensor.VentilationDataUpdateCoordinator.async_refresh",
            new_callable=AsyncMock,
        ):
            await async_setup_entry(hass, config_entry, mock_async_add_entities)

        # Verify that two entities were added (Living Room and Bedroom)
        assert mock_async_add_entities.call_count == 1
        assert len(mock_async_add_entities.call_args[0][0]) == 2
