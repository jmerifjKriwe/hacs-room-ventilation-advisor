"""Global Configuration entities for Solar Window System."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, ENTITY_PREFIX_GLOBAL, GLOBAL_CONFIG_ENTITIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import device_registry as dr

_LOGGER = logging.getLogger(__name__)


async def async_create_global_config_entities(
    hass: HomeAssistant, device: dr.DeviceEntry
) -> None:
    """Create all global configuration entities for the global config device."""
    # Get available entities for selectors
    binary_sensors = await _get_binary_sensor_entities(hass)
    input_booleans = await _get_input_boolean_entities(hass)
    temperature_sensors = await _get_temperature_sensor_entities(hass)

    # Update selector options
    weather_warning_options = ["", *binary_sensors, *input_booleans]
    temperature_sensor_options = ["", *temperature_sensors]

    for entity_key, entity_config in GLOBAL_CONFIG_ENTITIES.items():
        try:
            # Update options for select entities
            if entity_key == "weather_warning_sensor":
                updated_config = {**entity_config, "options": weather_warning_options}
            elif entity_key == "weather_forecast_temperature_sensor":
                updated_config = {
                    **entity_config,
                    "options": temperature_sensor_options,
                }
            else:
                updated_config = entity_config

            # Create the entity based on platform using service calls
            if updated_config["platform"] == "input_number":
                await _create_input_number_via_service(
                    hass, entity_key, updated_config, device
                )
            elif updated_config["platform"] == "input_text":
                await _create_input_text_via_service(
                    hass, entity_key, updated_config, device
                )
            elif updated_config["platform"] == "input_boolean":
                await _create_input_boolean_via_service(
                    hass, entity_key, updated_config, device
                )
            elif updated_config["platform"] == "input_select":
                await _create_input_select_via_service(
                    hass, entity_key, updated_config, device
                )
            elif updated_config["platform"] == "sensor":
                # For sensors, we'll create template sensors
                await _create_template_sensor_via_service(entity_key)

        except (ValueError, OSError):
            _LOGGER.exception("Failed to create entity %s", entity_key)


async def _create_input_number_via_service(
    hass: HomeAssistant,
    entity_key: str,
    config: dict[str, Any],
    device: dr.DeviceEntry,
) -> None:
    """Create an input_number entity via service call."""
    service_data = {
        "name": f"{ENTITY_PREFIX_GLOBAL}_{entity_key}",
        "min": config["min"],
        "max": config["max"],
        "step": config["step"],
        "initial": config["default"],
        "icon": config.get("icon"),
    }

    if config.get("unit"):
        service_data["unit_of_measurement"] = config["unit"]

    await hass.services.async_call("input_number", "create", service_data)

    # Associate with device
    await _associate_entity_with_device(
        hass, f"input_number.{ENTITY_PREFIX_GLOBAL}_{entity_key}", device
    )


async def _create_input_text_via_service(
    hass: HomeAssistant,
    entity_key: str,
    config: dict[str, Any],
    device: dr.DeviceEntry,
) -> None:
    """Create an input_text entity via service call."""
    service_data = {
        "name": f"{ENTITY_PREFIX_GLOBAL}_{entity_key}",
        "initial": config["default"],
        "max": config["max"],
        "icon": config.get("icon"),
    }

    await hass.services.async_call("input_text", "create", service_data)

    # Associate with device
    await _associate_entity_with_device(
        hass, f"input_text.{ENTITY_PREFIX_GLOBAL}_{entity_key}", device
    )


async def _create_input_boolean_via_service(
    hass: HomeAssistant,
    entity_key: str,
    config: dict[str, Any],
    device: dr.DeviceEntry,
) -> None:
    """Create an input_boolean entity via service call."""
    service_data = {
        "name": f"{ENTITY_PREFIX_GLOBAL}_{entity_key}",
        "initial": config["default"],
        "icon": config.get("icon"),
    }

    await hass.services.async_call("input_boolean", "create", service_data)

    # Associate with device
    await _associate_entity_with_device(
        hass, f"input_boolean.{ENTITY_PREFIX_GLOBAL}_{entity_key}", device
    )


async def _create_input_select_via_service(
    hass: HomeAssistant,
    entity_key: str,
    config: dict[str, Any],
    device: dr.DeviceEntry,
) -> None:
    """Create an input_select entity via service call."""
    service_data = {
        "name": f"{ENTITY_PREFIX_GLOBAL}_{entity_key}",
        "options": config["options"],
        "icon": config.get("icon"),
    }

    if config["default"] and config["default"] in config["options"]:
        service_data["initial"] = config["default"]

    await hass.services.async_call("input_select", "create", service_data)

    # Associate with device
    await _associate_entity_with_device(
        hass, f"input_select.{ENTITY_PREFIX_GLOBAL}_{entity_key}", device
    )


async def _create_template_sensor_via_service(
    entity_key: str,
) -> None:
    """Create a template sensor entity."""
    # This is a placeholder - sensors will be created through platform setup


async def _associate_entity_with_device(
    hass: HomeAssistant, entity_id: str, device: dr.DeviceEntry
) -> None:
    """Associate an entity with a device."""
    entity_registry = er.async_get(hass)

    # Wait a bit for entity to be registered
    await hass.async_block_till_done()

    # Get the entity
    entity_entry = entity_registry.async_get(entity_id)
    if entity_entry:
        # Update entity to associate with device
        entity_registry.async_update_entity(entity_id, device_id=device.id)
    else:
        _LOGGER.warning("Entity %s not found in registry", entity_id)


async def _get_binary_sensor_entities(hass: HomeAssistant) -> list[str]:
    """Get all binary_sensor entities."""
    entity_registry = er.async_get(hass)
    return [
        entry.entity_id
        for entry in entity_registry.entities.values()
        if entry.entity_id.startswith("binary_sensor.")
        and not entry.disabled_by
        and not entry.hidden_by
    ]


async def _get_input_boolean_entities(hass: HomeAssistant) -> list[str]:
    """Get all input_boolean entities."""
    entity_registry = er.async_get(hass)
    return [
        entry.entity_id
        for entry in entity_registry.entities.values()
        if entry.entity_id.startswith("input_boolean.")
        and not entry.disabled_by
        and not entry.hidden_by
    ]


async def _get_temperature_sensor_entities(hass: HomeAssistant) -> list[str]:
    """Get all temperature sensor entities."""
    entity_registry = er.async_get(hass)
    temperature_entities = []

    for entry in entity_registry.entities.values():
        if (
            entry.entity_id.startswith("sensor.")
            and not entry.disabled_by
            and not entry.hidden_by
        ):
            # Check if it's a temperature sensor by looking at state
            state = hass.states.get(entry.entity_id)
            if state and state.attributes.get("unit_of_measurement") in [
                "°C",
                "°F",
                "K",
            ]:
                temperature_entities.append(entry.entity_id)

    return temperature_entities


class GlobalConfigSensor(RestoreEntity, SensorEntity):
    """Sensor entity for global configuration values."""

    def __init__(
        self,
        entity_key: str,
        config: dict[str, Any],
        device: dr.DeviceEntry,
    ) -> None:
        """Initialize the sensor."""
        self._entity_key = entity_key
        self._config = config
        self._device = device
        # Stable IDs to yield sensor.sws_global_* entity_ids
        self._attr_unique_id = f"{ENTITY_PREFIX_GLOBAL}_{entity_key}"
        self._attr_suggested_object_id = f"{ENTITY_PREFIX_GLOBAL}_{entity_key}"
        self._attr_name = f"SWS_GLOBAL {config['name']}"
        self._attr_has_entity_name = False

        self._attr_device_info = {
            "identifiers": device.identifiers,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        self._attr_unit_of_measurement = config.get("unit")
        self._attr_icon = config.get("icon")
        self._state = config["default"]

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass and restore previous state if available."""
        await super().async_added_to_hass()
        # Restore previous state if available
        restored_state = await self.async_get_last_state()
        if restored_state is not None:
            try:
                value = float(restored_state.state)
                self._state = value
            except (ValueError, TypeError):
                pass
        # Set friendly name to config['name']
        entity_registry = er.async_get(self.hass)
        if self.entity_id in entity_registry.entities:
            ent_reg_entry = entity_registry.entities[self.entity_id]
            new_friendly_name = self._config.get("name")
            if ent_reg_entry.original_name != new_friendly_name:
                entity_registry.async_update_entity(
                    self.entity_id, name=new_friendly_name
                )
        # For aggregated sensors, listen to coordinator updates
        sensor_keys = [
            "total_power",
            "total_power_direct",
            "total_power_diffuse",
            "window_with_shading",
        ]
        if self._entity_key in sensor_keys:
            self._setup_coordinator_listeners()

    def _setup_coordinator_listeners(self) -> None:
        """Set up listeners for coordinator updates."""

        # Listen to coordinator data updates to refresh state
        @callback
        def _coordinator_updated() -> None:
            """Handle coordinator update."""
            self.async_write_ha_state()

        # Register listeners for all coordinators
        domain_data = self.hass.data.get(DOMAIN, {})
        for entry_data in domain_data.values():
            coordinator = entry_data.get("coordinator")
            if coordinator:
                coordinator.async_add_listener(_coordinator_updated)

    @property
    def state(self) -> Any:
        """Return the state of the sensor."""
        # For system-level sensors, aggregate data from all coordinators
        sensor_keys = [
            "total_power",
            "total_power_direct",
            "total_power_diffuse",
            "window_with_shading",
        ]
        if self._entity_key in sensor_keys:
            return self._get_aggregated_value()
        return self._state

    def _get_aggregated_value(self) -> float | int:
        """Get aggregated value from all coordinators for system totals."""
        total_power = 0.0
        total_power_direct = 0.0
        total_power_diffuse = 0.0
        windows_with_shading = 0

        # Get all coordinators from hass.data
        domain_data = self.hass.data.get(DOMAIN, {})

        for entry_data in domain_data.values():
            coordinator = entry_data.get("coordinator")
            if coordinator and coordinator.data:
                # Aggregate from summary data
                summary = coordinator.data.get("summary", {})
                total_power += summary.get("total_power", 0)
                total_power_direct += summary.get("total_power_direct", 0)
                total_power_diffuse += summary.get("total_power_diffuse", 0)
                windows_with_shading += summary.get("shading_count", 0)

        # Return the appropriate value based on entity key
        if self._entity_key == "total_power":
            return round(total_power, 2)
        if self._entity_key == "total_power_direct":
            return round(total_power_direct, 2)
        if self._entity_key == "total_power_diffuse":
            return round(total_power_diffuse, 2)
        if self._entity_key == "window_with_shading":
            return windows_with_shading

        return 0

    @callback
    def async_update_state(self, value: Any) -> None:
        """Update the state of the sensor."""
        self._state = value
        self.async_write_ha_state()
