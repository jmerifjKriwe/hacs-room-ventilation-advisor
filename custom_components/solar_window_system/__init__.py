"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

"""Solar Window System integration package."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .coordinator import SolarWindowSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Get update interval from global config
    update_interval_minutes = 1
    for config_entry in hass.config_entries.async_entries(DOMAIN):
        if config_entry.data.get("entry_type") == "global_config":
            update_interval_minutes = config_entry.options.get(
                "update_interval", config_entry.data.get("update_interval", 1)
            )
            break

    # Register recalculate service (only once)
    if not hass.services.has_service(DOMAIN, "recalculate"):

        async def handle_recalculate_service(call: ServiceCall) -> None:
            """Service to trigger recalculation for all or a specific window."""
            window_id = call.data.get("window_id")
            # Recalculate for all window_configs coordinators
            for config_entry in hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("entry_type") == "window_configs":
                    coordinator = hass.data[DOMAIN][config_entry.entry_id][
                        "coordinator"
                    ]
                    await coordinator.async_refresh()
                    # If a specific window_id is given, optionally filter or log
                    if window_id:
                        # Optionally, you could implement per-window recalculation logic here
                        _LOGGER.info(f"Recalculation triggered for window: {window_id}")
                    else:
                        _LOGGER.info("Recalculation triggered for all windows.")

        hass.services.async_register(DOMAIN, "recalculate", handle_recalculate_service)
    """Set up Solar Window System from a config entry."""
    _LOGGER.debug("Setting up entry: %s", entry.title)
    _LOGGER.debug("Entry data: %s", entry.data)
    _LOGGER.debug("Entry ID: %s", entry.entry_id)

    device_registry = dr.async_get(hass)

    # Create device for global config
    if entry.title == "Solar Window System":
        _LOGGER.debug("Creating device for global config")
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, "global_config")},
            name="Solar Window System",
            manufacturer="SolarWindowSystem",
            model="GlobalConfig",
        )

        # Set up all platforms for this entry
        await hass.config_entries.async_forward_entry_setups(
            entry, ["sensor", "number", "text", "select", "switch"]
        )

    # Handle group configurations entry (subentry parent)
    elif entry.data.get("entry_type") == "group_configs":
        # Create devices for existing subentries
        await _create_subentry_devices(hass, entry)

        # Initialize coordinator for group configurations as well
        coordinator = SolarWindowSystemCoordinator(hass, entry, update_interval_minutes)

        # Store coordinator per entry to support multiple entries
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

        # Start coordinator updates
        await coordinator.async_config_entry_first_refresh()

        # Set up platforms for group configurations
        await hass.config_entries.async_forward_entry_setups(
            entry, ["select", "sensor"]
        )

        # Add update listener to handle new subentries
        entry.add_update_listener(_handle_config_entry_update)

    # Handle window configurations entry (subentry parent)
    elif entry.data.get("entry_type") == "window_configs":
        # Create devices for existing subentries
        await _create_subentry_devices(hass, entry)

        # Initialize coordinator for calculation updates
        coordinator = SolarWindowSystemCoordinator(hass, entry, update_interval_minutes)

        # Store coordinator in hass.data for access by binary sensors
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator}

        # Start coordinator updates
        await coordinator.async_config_entry_first_refresh()

        # Set up platforms for window configurations
        await hass.config_entries.async_forward_entry_setups(
            entry, ["select", "sensor", "binary_sensor", "number", "text", "switch"]
        )

        # Add update listener to handle new subentries
        entry.add_update_listener(_handle_config_entry_update)

    # Register service for manual device creation (only once)
    if not hass.services.has_service(DOMAIN, "create_subentry_devices"):

        async def create_subentry_devices_service(
            _call: ServiceCall,
        ) -> None:
            """Service to manually create subentry devices."""
            for config_entry in hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("entry_type") in [
                    "group_configs",
                    "window_configs",
                ]:
                    await _create_subentry_devices(hass, config_entry)

        hass.services.async_register(
            DOMAIN, "create_subentry_devices", create_subentry_devices_service
        )

    _LOGGER.debug("Setup completed for: %s", entry.title)
    return True


@callback
async def _handle_config_entry_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry updates to create devices for new subentries."""
    _LOGGER.debug("Config entry update detected for: %s", entry.title)
    if entry.data.get("entry_type") in ["group_configs", "window_configs"]:
        await _create_subentry_devices(hass, entry)

        # Reconfigure coordinator if this entry manages flows
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
            await coordinator.async_reconfigure()

        # Reload select platform to pick up new entities for new subentries
        _LOGGER.debug("Reloading platforms for updated entry: %s", entry.title)
        if entry.data.get("entry_type") in ("group_configs", "window_configs"):
            # Reload platforms to pick up entities for new subentries
            platforms = ["select", "sensor"]
            if entry.data.get("entry_type") == "window_configs":
                platforms.append("binary_sensor")
            await hass.config_entries.async_unload_platforms(entry, platforms)
            await hass.config_entries.async_forward_entry_setups(entry, platforms)


async def _create_subentry_devices(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Create devices for all subentries using proper Device Registry API."""
    device_registry = dr.async_get(hass)

    # The correct way to access subentries is through entry.subentries
    # This is a dict where keys are subentry IDs and values are ConfigSubentry objects

    if getattr(entry, "subentries", None):
        for subentry_id, subentry in entry.subentries.items():
            if subentry.subentry_type == "group":
                group_name = subentry.title
                _LOGGER.debug("Creating device for group subentry: %s", group_name)

                # This is the key: use config_subentry_id parameter
                # to link device to subentry
                device = device_registry.async_get_or_create(
                    config_entry_id=entry.entry_id,
                    config_subentry_id=subentry_id,  # Links device to subentry!
                    identifiers={(DOMAIN, f"group_{subentry_id}")},
                    name=group_name,
                    manufacturer="SolarWindowSystem",
                    model="GroupConfig",
                )
                _LOGGER.debug(
                    "Device created for subentry: %s (%s)", device.name, device.id
                )
            elif subentry.subentry_type == "window":
                window_name = subentry.title
                _LOGGER.debug("Creating device for window subentry: %s", window_name)

                # Create device for window subentry
                device = device_registry.async_get_or_create(
                    config_entry_id=entry.entry_id,
                    config_subentry_id=subentry_id,  # Links device to subentry!
                    identifiers={(DOMAIN, f"window_{subentry_id}")},
                    name=window_name,
                    manufacturer="SolarWindowSystem",
                    model="WindowConfig",
                )
                _LOGGER.debug(
                    "Device created for subentry: %s (%s)", device.name, device.id
                )
                _LOGGER.debug(
                    "Device config_entries_subentries: %s",
                    device.config_entries_subentries,
                )
            else:
                _LOGGER.debug(
                    "Skipping subentry (unknown type): %s", subentry.subentry_type
                )
    else:
        _LOGGER.debug("No subentries found in entry")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading entry: %s", entry.title)

    # Unload platforms if this is the global config entry
    if entry.title == "Solar Window System":
        return await hass.config_entries.async_unload_platforms(
            entry, ["sensor", "number", "text", "select", "switch"]
        )

    # Handle window_configs entry unloading
    if entry.data.get("entry_type") == "window_configs":
        # Clean up coordinator
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            del hass.data[DOMAIN][entry.entry_id]

        return await hass.config_entries.async_unload_platforms(
            entry, ["select", "sensor", "binary_sensor"]
        )

    # Handle group_configs entry unloading
    if entry.data.get("entry_type") == "group_configs":
        # Clean up coordinator
        if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
            del hass.data[DOMAIN][entry.entry_id]
        return await hass.config_entries.async_unload_platforms(
            entry, ["select", "sensor"]
        )

    return True
