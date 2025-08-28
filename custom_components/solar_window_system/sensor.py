"""
Sensor platform for Solar Window System.

Creates:
- Global configuration sensors from GLOBAL_CONFIG_ENTITIES
- Group/window per-subentry sensors: total_power, total_power_direct,
  total_power_diffuse
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN, GLOBAL_CONFIG_ENTITIES
from .global_config import GlobalConfigSensor

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
    """Set up sensors for Solar Window System."""
    if entry.data.get("entry_type") == "group_configs":
        await _setup_group_power_sensors(hass, entry, async_add_entities)
        return
    if entry.data.get("entry_type") == "window_configs":
        await _setup_window_power_sensors(hass, entry, async_add_entities)
        return

    # Handle Global Configuration sensors
    if entry.title == "Solar Window System":
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
            sensors = [
                GlobalConfigSensor(entity_key, config, global_device)
                for entity_key, config in GLOBAL_CONFIG_ENTITIES.items()
                if config["platform"] == "sensor"
            ]
            if sensors:
                async_add_entities(sensors)  # type: ignore[arg-type]
        else:
            _LOGGER.warning("Global Configuration device not found")


class SolarWindowSystemGroupDummySensor(RestoreEntity, SensorEntity):
    """Dummy sensor for group configurations."""

    def __init__(self, group_id: str, group_name: str) -> None:
        """Initialize the dummy group sensor."""
        self._attr_name = f"Dummy Group Sensor ({group_name})"
        self._attr_unique_id = f"{DOMAIN}_group_{group_id}_dummy"
        # device_info must match the device created in __init__.py
        self._attr_device_info = {
            "identifiers": {(DOMAIN, group_id)},
            "name": group_name,
            "manufacturer": "Solar Window System",
            "model": "Group",
        }

    @property
    def state(self) -> int:
        """Return the state of the sensor."""
        return getattr(self, "_restored_state", 42)

    async def async_added_to_hass(self) -> None:
        """Restore previous state if available."""
        await super().async_added_to_hass()
        restored_state = await self.async_get_last_state()
        if restored_state is not None:
            try:
                self._restored_state = int(restored_state.state)
            except (ValueError, TypeError):
                self._restored_state = 42


async def _setup_group_power_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Attach total power sensors to each group subentry device."""
    device_registry = dr.async_get(hass)
    if not entry.subentries:
        _LOGGER.warning("No group subentries found")
        return
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != "group":
            continue
        group_name = subentry.title
        group_device = None
        for device in device_registry.devices.values():
            if device.config_entries and entry.entry_id in device.config_entries:
                subentries = device.config_entries_subentries
                if (
                    subentries
                    and entry.entry_id in subentries
                    and subentry_id in subentries[entry.entry_id]
                ):
                    for identifier in device.identifiers:
                        if (
                            identifier[0] == DOMAIN
                            and identifier[1] == f"group_{subentry_id}"
                        ):
                            group_device = device
                            break
                    if group_device:
                        break
        if not group_device:
            _LOGGER.warning("Group device not found for: %s", group_name)
            continue

        entities = []
        # Get coordinator from hass.data
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        for key, label in (
            ("total_power", "Total Power"),
            ("total_power_direct", "Total Power Direct"),
            ("total_power_diffuse", "Total Power Diffuse"),
        ):
            entities.append(
                GroupWindowPowerSensor(
                    kind="group",
                    object_name=group_name,
                    device=group_device,
                    key=key,
                    label=label,
                    coordinator=coordinator,
                )
            )
        if entities:
            async_add_entities(entities, config_subentry_id=subentry_id)


async def _setup_window_power_sensors(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Attach total power sensors to each window subentry device."""
    device_registry = dr.async_get(hass)
    if not entry.subentries:
        _LOGGER.warning("No window subentries found")
        return
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != "window":
            continue
        window_name = subentry.title
        window_device = None
        for device in device_registry.devices.values():
            if device.config_entries and entry.entry_id in device.config_entries:
                subentries = device.config_entries_subentries
                if (
                    subentries
                    and entry.entry_id in subentries
                    and subentry_id in subentries[entry.entry_id]
                ):
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

        entities = []
        # Get coordinator from hass.data
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        for key, label in (
            ("total_power", "Total Power"),
            ("total_power_direct", "Total Power Direct"),
            ("total_power_diffuse", "Total Power Diffuse"),
            ("power_m2_total", "Power/m² Total"),
            ("power_m2_diffuse", "Power/m² Diffuse"),
            ("power_m2_direct", "Power/m² Direct"),
            ("power_m2_raw", "Power/m² Raw"),
            ("total_power_raw", "Total Power Raw"),
        ):
            entities.append(
                GroupWindowPowerSensor(
                    kind="window",
                    object_name=window_name,
                    device=window_device,
                    key=key,
                    label=label,
                    coordinator=coordinator,
                )
            )
        if entities:
            async_add_entities(entities, config_subentry_id=subentry_id)


class GroupWindowPowerSensor(CoordinatorEntity, RestoreEntity):
    """Sensor for group/window total power metrics with predictable IDs."""

    def __init__(
        self,
        *,
        kind: str,  # "group" | "window"
        object_name: str,
        device: dr.DeviceEntry,
        key: str,  # total_power | total_power_direct | total_power_diffuse
        label: str,
        coordinator: DataUpdateCoordinator[Any],
    ) -> None:
        """Initialize power sensor bound to a group/window device."""
        super().__init__(coordinator)
        self._kind = kind
        self._key = key
        self._label = label
        self._object_name = object_name
        slug = object_name.lower().replace(" ", "_").replace("-", "_")
        self._attr_unique_id = f"sws_{kind}_{slug}_{key}"
        self._attr_suggested_object_id = f"sws_{kind}_{slug}_{key}"
        prefix = "SWS_GROUP" if kind == "group" else "SWS_WINDOW"
        self._attr_name = f"{prefix} {object_name} {label}"
        self._attr_has_entity_name = False
        self._attr_device_info = {
            "identifiers": device.identifiers,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        self._attr_unit_of_measurement = "W"
        if key == "total_power":
            self._attr_icon = "mdi:lightning-bolt"
        elif key == "total_power_direct":
            self._attr_icon = "mdi:weather-sunny"
        else:
            self._attr_icon = "mdi:weather-partly-cloudy"

    @property
    def state(self) -> Any:
        """
        Return current power value from latest coordinator data or restore if
        unavailable.

        If no data is available, returns the restored state if available.
        """
        if self.coordinator and self.coordinator.data:
            if self._kind == "window":
                windows = self.coordinator.data.get("windows", {})
                for win_data in windows.values():
                    if win_data.get("name") == self._object_name:
                        return win_data.get(self._key)
            elif self._kind == "group":
                groups = self.coordinator.data.get("groups", {})
                for group_data in groups.values():
                    if group_data.get("name") == self._object_name:
                        return group_data.get(self._key)
        # If no data, return restored state if available
        return getattr(self, "_restored_state", None)

    # Removed duplicate state property

    async def async_added_to_hass(self) -> None:
        """Restore previous state if available and set a clean friendly name."""
        await super().async_added_to_hass()
        # Restore state if available
        restored_state = await self.async_get_last_state()
        if restored_state is not None:
            try:
                self._restored_state = float(restored_state.state)
            except (ValueError, TypeError):
                self._restored_state = None
        # Set clean friendly name
        entity_registry = er.async_get(self.hass)
        if self.entity_id in entity_registry.entities:
            ent_reg_entry = entity_registry.entities[self.entity_id]
            new_friendly_name = self._label
            if ent_reg_entry.original_name != new_friendly_name:
                entity_registry.async_update_entity(
                    self.entity_id, name=new_friendly_name
                )
