"""Diagnostics support for Solar Window System integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.config_entries import ConfigEntry  # pragma: no cover
    from homeassistant.core import HomeAssistant  # pragma: no cover


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    # You can expand this to include more relevant diagnostics data
    return {
        "entry_data": entry.data,
        "data": {},
    }
