"""Number platform for Solar Window System."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.number import NumberEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, ENTITY_PREFIX_GLOBAL, GLOBAL_CONFIG_ENTITIES

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up number entities for Solar Window System."""
    # Only handle Global Configuration
    if entry.title != "Solar Window System":
        return

    device_registry = dr.async_get(hass)
    global_device = None

    # Find the global configuration device
    for device in device_registry.devices.values():
        if device.config_entries and entry.entry_id in device.config_entries:
            for identifier in device.identifiers:
                if identifier[0] == DOMAIN and identifier[1] == "global_config":
                    global_device = device
                    break
            if global_device:
                break

    if global_device:
        number_entities = []
        for entity_key, config in GLOBAL_CONFIG_ENTITIES.items():
            if config["platform"] == "input_number":
                number_entities.append(
                    GlobalConfigNumberEntity(entity_key, config, global_device)
                )

        if number_entities:
            async_add_entities(number_entities)
    else:
        _LOGGER.warning("Global Configuration device not found")


class GlobalConfigNumberEntity(NumberEntity, RestoreEntity):
    """Number entity for global configuration values."""

    def __init__(
        self,
        entity_key: str,
        config: dict,
        device: dr.DeviceEntry,
    ) -> None:
        """Initialize the number entity."""
        self._entity_key = entity_key
        self._config = config
        self._device = device
        # Unique ID stays stable
        self._attr_unique_id = f"{ENTITY_PREFIX_GLOBAL}_{entity_key}"
        # Suggest object id for desired entity_id: number.sws_global_<key>
        self._attr_suggested_object_id = f"{ENTITY_PREFIX_GLOBAL}_{entity_key}"
        # Use a readable name but don't combine with device name for entity_id
        self._attr_name = f"SWS_GLOBAL {config['name']}"
        self._attr_has_entity_name = False
        self._attr_device_info = {
            "identifiers": device.identifiers,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        self._attr_native_min_value = config["min"]
        self._attr_native_max_value = config["max"]
        self._attr_native_step = config["step"]
        self._attr_native_unit_of_measurement = config.get("unit")
        self._attr_icon = config.get("icon")
        self._attr_native_value = config["default"]

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass and restore previous state if available."""
        await super().async_added_to_hass()
        # Restore previous state if available
        restored_state = await self.async_get_last_state()
        if restored_state is not None:
            try:
                value = float(restored_state.state)
                if self._attr_native_min_value <= value <= self._attr_native_max_value:
                    self._attr_native_value = value
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

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value and persist state."""
        self._attr_native_value = value
        self.async_write_ha_state()
