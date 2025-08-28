"""Switch platform for Solar Window System."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    ENTITY_PREFIX_GLOBAL,
    GLOBAL_CONFIG_ENTITIES,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up switch entities for Solar Window System."""
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
        switch_entities = []
        for entity_key, config in GLOBAL_CONFIG_ENTITIES.items():
            if config["platform"] == "input_boolean":
                switch_entities.append(
                    GlobalConfigSwitchEntity(entity_key, config, global_device)
                )

        if switch_entities:
            async_add_entities(switch_entities)
    else:
        _LOGGER.warning("Global Configuration device not found")


class GlobalConfigSwitchEntity(SwitchEntity, RestoreEntity):
    """Switch entity for global configuration boolean values."""

    def __init__(
        self,
        entity_key: str,
        config: dict,
        device: dr.DeviceEntry,
    ) -> None:
        """Initialize the switch entity."""
        self._entity_key = entity_key
        self._config = config
        self._device = device
        # Stable unique id and desired object id for switch.sws_global_*
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
        self._attr_icon = config.get("icon")
        self._attr_is_on = config["default"]

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass and restore previous state if available."""
        await super().async_added_to_hass()
        # Restore previous state if available
        restored_state = await self.async_get_last_state()
        if restored_state is not None:
            if restored_state.state.lower() in ("on", "true", "1"):
                self._attr_is_on = True
            elif restored_state.state.lower() in ("off", "false", "0"):
                self._attr_is_on = False
        # Set friendly name to config['name']
        entity_registry = er.async_get(self.hass)
        if self.entity_id in entity_registry.entities:
            ent_reg_entry = entity_registry.entities[self.entity_id]
            new_friendly_name = self._config.get("name")
            if ent_reg_entry.original_name != new_friendly_name:
                entity_registry.async_update_entity(
                    self.entity_id, name=new_friendly_name
                )

    async def async_turn_on(self) -> None:
        """Turn the entity on and persist state."""
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn the entity off and persist state."""
        self._attr_is_on = False
        self.async_write_ha_state()
