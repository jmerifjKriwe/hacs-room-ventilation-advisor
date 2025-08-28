"""Binary sensor platform for Solar Window System (window subentries)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import SolarWindowSystemCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up binary sensors for window subentries."""
    if entry.data.get("entry_type") != "window_configs":
        return

    # Get coordinator
    coordinator = None
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    if not coordinator:
        _LOGGER.warning("No coordinator found for window_configs entry")
        return

    device_registry = dr.async_get(hass)

    if not entry.subentries:
        _LOGGER.warning("No window subentries found")
        return

    entities = []
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

        entity = WindowShadingRequiredBinarySensor(
            coordinator, window_device, window_name
        )
        entities.append((entity, subentry_id))

    # Add entities with their subentry_ids
    for entity, subentry_id in entities:
        async_add_entities([entity], config_subentry_id=subentry_id)


class WindowShadingRequiredBinarySensor(
    CoordinatorEntity, BinarySensorEntity, RestoreEntity
):
    """Binary sensor indicating if shading is required for a window."""

    coordinator: SolarWindowSystemCoordinator

    def __init__(
        self,
        coordinator: SolarWindowSystemCoordinator,
        device: dr.DeviceEntry,
        window_name: str,
    ) -> None:
        """Initialize the shading_required binary sensor for a window."""
        super().__init__(coordinator)
        self._window_name = window_name
        window_slug = window_name.lower().replace(" ", "_").replace("-", "_")
        self._attr_unique_id = f"sws_window_{window_slug}_shading_required"
        self._attr_suggested_object_id = f"sws_window_{window_slug}_shading_required"
        # Original name with prefix for traceability; friendly name will be overridden
        self._attr_name = f"SWS_WINDOW {window_name} Shading Required"
        self._attr_has_entity_name = False
        self._attr_device_info = {
            "identifiers": device.identifiers,
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
        }
        self._attr_icon = "mdi:shield-sun"
        self._friendly_label = "Shading Required"

    @property
    def is_on(self) -> bool:
        """Return True if shading is currently required."""
        if not self.coordinator.data:
            return False
        return self.coordinator.get_window_shading_status(self._window_name)

    @property
    def extra_state_attributes(self) -> dict[str, str | float | int | None]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        window_data = self.coordinator.get_window_data(self._window_name)
        if not window_data:
            return {}

        attributes = {}

        # Add calculation results as attributes
        if "solar_result" in window_data:
            solar_result = window_data["solar_result"]
            attributes.update(
                {
                    "solar_power": solar_result.get("power", 0),
                    "solar_power_direct": solar_result.get("power_direct", 0),
                    "solar_power_diffuse": solar_result.get("power_diffuse", 0),
                    "shadow_factor": solar_result.get("shadow_factor", 1.0),
                }
            )

        # Add shading decision details
        if "shade_reason" in window_data:
            attributes["shade_reason"] = window_data["shade_reason"]

        if "scenarios_triggered" in window_data:
            attributes["scenarios_triggered"] = ", ".join(
                window_data["scenarios_triggered"]
            )

        return attributes

    async def async_added_to_hass(self) -> None:
        """Restore previous state if available and set a clean friendly name."""
        await super().async_added_to_hass()
        # Restore previous state if available (for UI consistency, not logic)
        restored_state = await self.async_get_last_state()
        if restored_state is not None:
            self._restored_state = restored_state.state
        entity_registry = er.async_get(self.hass)
        if self.entity_id in entity_registry.entities:
            ent_reg_entry = entity_registry.entities[self.entity_id]
            new_friendly_name = self._friendly_label
            if ent_reg_entry.original_name != new_friendly_name:
                entity_registry.async_update_entity(
                    self.entity_id, name=new_friendly_name
                )
