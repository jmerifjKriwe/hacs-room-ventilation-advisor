"""Select platform for Solar Window System."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, ENTITY_PREFIX_GLOBAL, GLOBAL_CONFIG_ENTITIES

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up select entities for Solar Window System."""
    # Handle Global Configuration
    if entry.title == "Solar Window System":
        await _setup_global_config_selects(hass, entry, async_add_entities)
    # Handle Group Configuration subentries
    elif entry.data.get("entry_type") == "group_configs":
        await _setup_group_config_selects(hass, entry, async_add_entities)
    # Handle Window Configuration subentries
    elif entry.data.get("entry_type") == "window_configs":
        await _setup_window_config_selects(hass, entry, async_add_entities)


async def _setup_global_config_selects(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Global Configuration select entities."""
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
        # Get available entities for selectors
        binary_sensors = await _get_binary_sensor_entities(hass)
        input_booleans = await _get_input_boolean_entities(hass)
        temperature_sensors = await _get_temperature_sensor_entities(hass)

        select_entities = []
        for entity_key, config in GLOBAL_CONFIG_ENTITIES.items():
            if config["platform"] == "input_select":
                # Update options for specific selectors
                updated_config = config.copy()
                if entity_key == "weather_warning_sensor":
                    updated_config["options"] = ["", *binary_sensors, *input_booleans]
                elif entity_key == "weather_forecast_temperature_sensor":
                    updated_config["options"] = ["", *temperature_sensors]

                select_entities.append(
                    GlobalConfigSelectEntity(entity_key, updated_config, global_device)
                )

        if select_entities:
            async_add_entities(select_entities)
    else:
        _LOGGER.warning("Global Configuration device not found")


async def _setup_group_config_selects(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Group Configuration select entities."""
    device_registry = dr.async_get(hass)

    if not entry.subentries:
        _LOGGER.warning("No group subentries found")
        return

    # Process each group subentry
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == "group":
            group_name = subentry.title

            # Find the device for this group
            group_device = None
            for device in device_registry.devices.values():
                # Check if device belongs to this entry and subentry
                device_has_entry = (
                    device.config_entries and entry.entry_id in device.config_entries
                )
                subentries = device.config_entries_subentries
                device_has_subentry = (
                    subentries
                    and entry.entry_id in subentries
                    and subentry_id in subentries[entry.entry_id]
                )

                if device_has_entry and device_has_subentry:
                    for identifier in device.identifiers:
                        if (
                            identifier[0] == DOMAIN
                            and identifier[1] == f"group_{subentry_id}"
                        ):
                            group_device = device
                            break
                    if group_device:
                        break

            if group_device:
                # Create scenario enable select entities for this group
                subentry_select_entities = [
                    GroupConfigSelectEntity(
                        "scenario_b_enable",
                        {
                            "name": "Enable Scenario B",
                            "options": ["disable", "enable", "inherit"],
                            "default": "inherit",
                            "icon": "mdi:toggle-switch",
                        },
                        group_device,
                        group_name,
                        subentry_id,
                    ),
                    GroupConfigSelectEntity(
                        "scenario_c_enable",
                        {
                            "name": "Enable Scenario C",
                            "options": ["disable", "enable", "inherit"],
                            "default": "inherit",
                            "icon": "mdi:toggle-switch",
                        },
                        group_device,
                        group_name,
                        subentry_id,
                    ),
                ]

                # IMPORTANT: Add entities for this group with the correct subentry id
                async_add_entities(
                    subentry_select_entities, config_subentry_id=subentry_id
                )
            else:
                _LOGGER.warning("Group device not found for: %s", group_name)


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


class GlobalConfigSelectEntity(SelectEntity, RestoreEntity):
    """Select entity for global configuration values."""

    def __init__(
        self,
        entity_key: str,
        config: dict,
        device: dr.DeviceEntry,
    ) -> None:
        """Initialize the select entity."""
        self._entity_key = entity_key
        self._config = config
        self._device = device
        # Stable ID and desired entity_id pattern: select.sws_global_*
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
        self._attr_options = config["options"]
        self._attr_icon = config.get("icon")
        # Set current option to default if it's in the options list
        if config["default"] and config["default"] in config["options"]:
            self._attr_current_option = config["default"]
        else:
            self._attr_current_option = (
                config["options"][0] if config["options"] else None
            )

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass and restore previous state if available."""
        await super().async_added_to_hass()
        # Restore previous state if available
        if (restored_state := await self.async_get_last_state()) is not None:
            if restored_state.state in self._attr_options:
                self._attr_current_option = restored_state.state
        # Set friendly name to config['name'] (e.g. 'Weather Warning Sensor')
        entity_registry = er.async_get(self.hass)
        if self.entity_id in entity_registry.entities:
            ent_reg_entry = entity_registry.entities[self.entity_id]
            new_friendly_name = self._config.get("name")
            if ent_reg_entry.original_name != new_friendly_name:
                entity_registry.async_update_entity(
                    self.entity_id, name=new_friendly_name
                )

    async def async_select_option(self, option: str) -> None:
        """Update the current selection and persist state."""
        self._attr_current_option = option
        self.async_write_ha_state()


class GroupConfigSelectEntity(SelectEntity, RestoreEntity):
    """Select entity for group configuration scenario enables."""

    def __init__(
        self,
        entity_key: str,
        config: dict,
        device: dr.DeviceEntry,
        group_name: str,
        subentry_id: str,
    ) -> None:
        """Initialize the group select entity."""
        self._entity_key = entity_key
        self._config = config
        self._device = device
        self._group_name = group_name
        self._subentry_id = subentry_id
        # Predictable IDs: select.sws_group_<group>_<key>
        group_slug = group_name.lower().replace(" ", "_").replace("-", "_")
        self._attr_unique_id = f"sws_group_{group_slug}_{entity_key}"
        self._attr_suggested_object_id = f"sws_group_{group_slug}_{entity_key}"
        self._attr_name = f"SWS_GROUP {group_name} {config['name']}"
        self._attr_has_entity_name = False

        self._attr_device_info = {
            "identifiers": device.identifiers,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        self._attr_options = config["options"]
        self._attr_icon = config.get("icon")
        # Set current option to default if it's in the options list
        if config["default"] and config["default"] in config["options"]:
            self._attr_current_option = config["default"]
        else:
            self._attr_current_option = (
                config["options"][0] if config["options"] else None
            )

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass and restore previous state if available."""
        await super().async_added_to_hass()
        # Restore previous state if available
        if (restored_state := await self.async_get_last_state()) is not None:
            if restored_state.state in self._attr_options:
                self._attr_current_option = restored_state.state
        # Set friendly name to config['name'] (e.g. 'Enable Scenario B')
        entity_registry = er.async_get(self.hass)
        if self.entity_id in entity_registry.entities:
            ent_reg_entry = entity_registry.entities[self.entity_id]
            new_friendly_name = self._config.get("name")
            if ent_reg_entry.original_name != new_friendly_name:
                entity_registry.async_update_entity(
                    self.entity_id, name=new_friendly_name
                )

    async def async_select_option(self, option: str) -> None:
        """Update the current selection and persist state."""
        self._attr_current_option = option
        self.async_write_ha_state()


async def _setup_window_config_selects(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Window Configuration select entities."""
    device_registry = dr.async_get(hass)
    if not entry.subentries:
        _LOGGER.warning("No window subentries found")
        return
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != "window":
            continue
        window_name = subentry.title
        window_device = None

        # Find device for this window subentry
        for device in device_registry.devices.values():
            device_has_entry = (
                device.config_entries and entry.entry_id in device.config_entries
            )
            subentries = device.config_entries_subentries
            device_has_subentry = (
                subentries
                and entry.entry_id in subentries
                and subentry_id in subentries[entry.entry_id]
            )
            if device_has_entry and device_has_subentry:
                for identifier in device.identifiers:
                    if (
                        identifier[0] == DOMAIN
                        and identifier[1] == f"window_{subentry_id}"
                    ):
                        window_device = device
                        break
                if window_device:
                    break

        if not window_device:
            _LOGGER.warning("Window device not found for: %s", window_name)
            continue

        # Create 2 example window selects mirroring group ones
        subentry_select_entities = [
            WindowConfigSelectEntity(
                "scenario_b_enable",
                {
                    "name": "Enable Scenario B",
                    "options": ["disable", "enable", "inherit"],
                    "default": "inherit",
                    "icon": "mdi:toggle-switch",
                },
                window_device,
                window_name,
                subentry_id,
            ),
            WindowConfigSelectEntity(
                "scenario_c_enable",
                {
                    "name": "Enable Scenario C",
                    "options": ["disable", "enable", "inherit"],
                    "default": "inherit",
                    "icon": "mdi:toggle-switch",
                },
                window_device,
                window_name,
                subentry_id,
            ),
        ]

        async_add_entities(subentry_select_entities, config_subentry_id=subentry_id)


class WindowConfigSelectEntity(SelectEntity, RestoreEntity):
    """Select entity for window configuration scenario enables."""

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass and restore previous state if available."""
        await super().async_added_to_hass()
        # Restore previous state if available
        restored_state = await self.async_get_last_state()
        if restored_state is not None and restored_state.state in self._attr_options:
            self._attr_current_option = restored_state.state
        # Set friendly name to config['name'] (e.g. 'Enable Scenario B')
        entity_registry = er.async_get(self.hass)
        if self.entity_id in entity_registry.entities:
            ent_reg_entry = entity_registry.entities[self.entity_id]
            new_friendly_name = self._config.get("name")
            if ent_reg_entry.original_name != new_friendly_name:
                entity_registry.async_update_entity(
                    self.entity_id, name=new_friendly_name
                )

    """Select entity for window configuration scenario enables."""

    def __init__(
        self,
        entity_key: str,
        config: dict,
        device: dr.DeviceEntry,
        window_name: str,
        subentry_id: str,
    ) -> None:
        """Initialize the window select entity."""
        self._entity_key = entity_key
        self._config = config
        self._device = device
        self._window_name = window_name
        self._subentry_id = subentry_id

        # Predictable IDs: select.sws_window_<window>_<key>
        window_slug = window_name.lower().replace(" ", "_").replace("-", "_")
        self._attr_unique_id = f"sws_window_{window_slug}_{entity_key}"
        self._attr_suggested_object_id = f"sws_window_{window_slug}_{entity_key}"
        self._attr_name = f"SWS_WINDOW {window_name} {config['name']}"
        self._attr_has_entity_name = False

        self._attr_device_info = {
            "identifiers": device.identifiers,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        self._attr_options = config["options"]
        self._attr_icon = config.get("icon")
        # Set current option to default if it's in the options list
        if config["default"] and config["default"] in config["options"]:
            self._attr_current_option = config["default"]
        else:
            self._attr_current_option = (
                config["options"][0] if config["options"] else None
            )

    async def async_select_option(self, option: str) -> None:
        """Update the current selection and persist state."""
        self._attr_current_option = option
        self.async_write_ha_state()
