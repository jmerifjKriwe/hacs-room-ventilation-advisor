"""Room Ventilation Advisor integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, PLATFORMS

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Room Ventilation Advisor from a config entry."""
    _LOGGER.info("Setting up Room Ventilation Advisor integration")

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register device for the integration
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.data.get("name", "Room Ventilation Advisor"),
        manufacturer="Room Ventilation Advisor",
        model="Ventilation Calculator",
        sw_version="1.0.0",
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Room Ventilation Advisor integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up device registry
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, entry.entry_id)},
        )
        if device:
            device_registry.async_remove_device(device.id)

    return unload_ok


async def async_migrate_entry(_hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        # Migration from version 1 to 2 would go here
        # For now, we just return True as we're on version 1
        return True

    # This shouldn't happen, but just in case
    _LOGGER.error("Unknown migration version %s", config_entry.version)
    return False
