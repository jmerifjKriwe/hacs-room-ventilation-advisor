"""Sensor platform for Room Ventilation Advisor integration."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from functools import cached_property
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .calculator import RoomData, VentilationCalculator
from .const import (
    ATTR_ADVICE,
    ATTR_CO2_LEVEL,
    ATTR_HUMIDITY_INDOOR,
    ATTR_HUMIDITY_OUTDOOR,
    ATTR_ROOM_TYPE,
    ATTR_SCORE,
    ATTR_TEMPERATURE_INDOOR,
    ATTR_TEMPERATURE_OUTDOOR,
    ATTR_WIND_SPEED,
    CONF_CO2_SENSOR,
    CONF_ENABLED,
    CONF_HUMIDITY_SENSOR,
    CONF_OUTDOOR_HUMIDITY_SENSOR,
    CONF_OUTDOOR_TEMP_SENSOR,
    CONF_ROOM_TYPE,
    CONF_ROOMS,
    CONF_SCAN_INTERVAL,
    CONF_TEMP_SENSOR,
    CONF_WIND_SENSOR,
    DOMAIN,
    ICON_VENTILATION,
    ICON_VENTILATION_GOOD,
    ICON_VENTILATION_MODERATE,
    ICON_VENTILATION_POOR,
)

_LOGGER = logging.getLogger(__name__)

# Score thresholds
SCORE_GOOD = 0.5
SCORE_MODERATE = 0.0
SCORE_POOR = -0.3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = VentilationDataUpdateCoordinator(hass, entry)
    # Initial refresh for coordinator data
    await coordinator.async_refresh()

    entities: list[VentilationSensor] = []
    rooms_data = entry.data.get(CONF_ROOMS, {})

    for room_name, room_config in rooms_data.items():
        if room_config.get(CONF_ENABLED, True):
            entities.append(VentilationSensor(coordinator, room_name, room_config))

    async_add_entities(entities)


class VentilationDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Data update coordinator for ventilation sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL) or entry.data.get(
            CONF_SCAN_INTERVAL, 300
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.entry = entry
        self.calculator = VentilationCalculator({})

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from sensors."""
        data = {}

        # Get outdoor sensors - check options first, then config
        outdoor_temp_entity = self.entry.options.get(
            CONF_OUTDOOR_TEMP_SENSOR
        ) or self.entry.data.get(CONF_OUTDOOR_TEMP_SENSOR)
        outdoor_humidity_entity = self.entry.options.get(
            CONF_OUTDOOR_HUMIDITY_SENSOR
        ) or self.entry.data.get(CONF_OUTDOOR_HUMIDITY_SENSOR)
        wind_entity = self.entry.options.get(CONF_WIND_SENSOR) or self.entry.data.get(
            CONF_WIND_SENSOR
        )

        try:
            outdoor_temp = self._get_sensor_value(outdoor_temp_entity)
            outdoor_humidity = self._get_sensor_value(outdoor_humidity_entity)
            wind_speed = self._get_sensor_value(wind_entity)

            data["outdoor_temp"] = outdoor_temp
            data["outdoor_humidity"] = outdoor_humidity
            data["wind_speed"] = wind_speed

        except (ValueError, TypeError):
            _LOGGER.exception("Error reading outdoor sensors")
            raise

        # Get room data
        rooms_data = self.entry.data.get(CONF_ROOMS, {})
        room_options = self.entry.options.get("room_settings", {})
        room_data = {}

        for room_name, room_config in rooms_data.items():
            # Check if room is enabled (from options or config)
            room_settings = room_options.get(room_name, {})
            default_enabled = room_config.get(CONF_ENABLED, True)
            room_enabled = room_settings.get("enabled", default_enabled)
            if not room_enabled:
                continue

            try:
                # Get room sensors - check options first, then config
                temp_sensor = room_settings.get(CONF_TEMP_SENSOR) or room_config.get(
                    CONF_TEMP_SENSOR
                )
                humidity_sensor = room_settings.get(
                    CONF_HUMIDITY_SENSOR
                ) or room_config.get(CONF_HUMIDITY_SENSOR)
                co2_sensor = room_settings.get(CONF_CO2_SENSOR) or room_config.get(
                    CONF_CO2_SENSOR
                )
                room_type = room_settings.get(CONF_ROOM_TYPE) or room_config.get(
                    CONF_ROOM_TYPE
                )

                indoor_temp = self._get_sensor_value(temp_sensor)
                indoor_humidity = self._get_sensor_value(humidity_sensor)
                co2_level = None

                if co2_sensor:
                    co2_level = self._get_sensor_value(co2_sensor)

                room_data[room_name] = {
                    "indoor_temp": indoor_temp,
                    "indoor_humidity": indoor_humidity,
                    "co2_level": co2_level,
                    "room_type": room_type,
                }

            except (ValueError, TypeError):
                _LOGGER.exception("Error reading sensors for room %s", room_name)
                continue

        data["rooms"] = room_data
        return data

    def _get_sensor_value(self, entity_id: str | None) -> float | None:
        """Get sensor value from entity."""
        if not entity_id:
            return None

        state = self.hass.states.get(entity_id)
        if state and state.state not in ["unknown", "unavailable"]:
            try:
                return float(state.state)
            except ValueError:
                return None
        return None


class VentilationSensor(
    CoordinatorEntity[VentilationDataUpdateCoordinator],
    SensorEntity,  # type: ignore[override]
):
    """Ventilation sensor for a room."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VentilationDataUpdateCoordinator,
        room_name: str,
        room_config: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.room_name = room_name
        self.room_config = room_config
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{room_name}"
        self._attr_name = f"{room_name} Ventilation Score"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self.coordinator.entry.entry_id)},
            "name": "Room Ventilation Advisor",
            "manufacturer": "GitHub Community",
            "model": "Ventilation Calculator",
            "sw_version": "1.0.0",
        }
        object_id = re.sub(r"[^a-zA-Z0-9_]", "_", self.room_name.lower())
        self._attr_entity_id = f"sensor.{object_id}_ventilation_score"
        self._attr_icon = ICON_VENTILATION
        self._attr_extra_state_attributes = {}

    @cached_property
    def native_value(self) -> float | None:
        """Return the ventilation score."""
        if not self.coordinator.data:
            return None

        room_data = self.coordinator.data.get("rooms", {}).get(self.room_name)
        if not room_data:
            return None

        # Check if all required values are available
        temp_out = self.coordinator.data.get("outdoor_temp")
        humidity_out = self.coordinator.data.get("outdoor_humidity")
        wind_speed = self.coordinator.data.get("wind_speed")

        if temp_out is None or humidity_out is None or wind_speed is None:
            return None

        try:
            room_data_obj = RoomData(
                temp_in=room_data["indoor_temp"],
                humidity_in=room_data["indoor_humidity"],
                temp_out=temp_out,
                humidity_out=humidity_out,
                wind_speed=wind_speed,
                hour=datetime.now(UTC).hour,
                month=datetime.now(UTC).month,
                room_type=room_data["room_type"],
                co2=room_data.get("co2_level"),
            )
            score = self.coordinator.calculator.calculate_room_score(room_data_obj)
            return round(score, 2)
        except (ValueError, TypeError):
            _LOGGER.exception(
                "Error calculating ventilation score for %s", self.room_name
            )
            return None

    def _get_ventilation_advice(self) -> str:
        """Get ventilation advice based on score."""
        if self.native_value is None:
            return "Unable to calculate ventilation advice"

        score = self.native_value
        if score >= SCORE_GOOD:
            return "Good ventilation - no action needed"
        if score >= SCORE_MODERATE:
            return "Moderate ventilation - consider opening windows briefly"
        if score >= SCORE_POOR:
            return "Poor ventilation - open windows for 10-15 minutes"
        return "Very poor ventilation - ventilate immediately for 20+ minutes"

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_icon()
        self._update_extra_state_attributes()
        self.async_write_ha_state()

    def _update_icon(self) -> None:
        """Update the icon based on current ventilation score."""
        if self.native_value is None:
            self._attr_icon = ICON_VENTILATION
        else:
            score = self.native_value
            if score >= SCORE_GOOD:
                self._attr_icon = ICON_VENTILATION_GOOD
            elif score >= SCORE_MODERATE:
                self._attr_icon = ICON_VENTILATION_MODERATE
            else:
                self._attr_icon = ICON_VENTILATION_POOR

    def _update_extra_state_attributes(self) -> None:
        """Update extra state attributes."""
        if not self.coordinator.data:
            self._attr_extra_state_attributes = {}
            return

        room_data = self.coordinator.data.get("rooms", {}).get(self.room_name)
        if not room_data:
            self._attr_extra_state_attributes = {}
            return

        attributes = {
            ATTR_ROOM_TYPE: self.room_config.get(CONF_ROOM_TYPE),
            ATTR_SCORE: self.native_value,
            ATTR_ADVICE: self._get_ventilation_advice(),
        }

        # Add sensor values if available
        if room_data.get("indoor_temp") is not None:
            attributes[ATTR_TEMPERATURE_INDOOR] = room_data["indoor_temp"]
        if room_data.get("indoor_humidity") is not None:
            attributes[ATTR_HUMIDITY_INDOOR] = room_data["indoor_humidity"]
        if room_data.get("co2_level") is not None:
            attributes[ATTR_CO2_LEVEL] = room_data["co2_level"]

        if self.coordinator.data.get("outdoor_temp") is not None:
            attributes[ATTR_TEMPERATURE_OUTDOOR] = self.coordinator.data["outdoor_temp"]
        if self.coordinator.data.get("outdoor_humidity") is not None:
            attributes[ATTR_HUMIDITY_OUTDOOR] = self.coordinator.data[
                "outdoor_humidity"
            ]
        if self.coordinator.data.get("wind_speed") is not None:
            attributes[ATTR_WIND_SPEED] = self.coordinator.data["wind_speed"]

        self._attr_extra_state_attributes = attributes
