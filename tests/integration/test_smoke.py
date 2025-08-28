"""Lightweight smoke tests for Solar Window System integration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.solar_window_system as integration
from custom_components.solar_window_system.const import DOMAIN
from homeassistant.helpers import device_registry as dr
from tests.helpers.test_framework import IntegrationTestCase, TestPatterns

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestIntegrationSmoke(IntegrationTestCase):
    """Smoke tests for integration setup using standardized framework."""

    async def test_global_setup_smoke(self, hass: HomeAssistant) -> None:
        """Smoke test: set up the global entry and ensure core wiring works."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Solar Window System",
            data={"entry_type": "global"},
            entry_id="smoke_global",
        )
        entry.add_to_hass(hass)

        # Avoid integration discovery in this smoke test
        original_forward = hass.config_entries.async_forward_entry_setups
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=None)

        ok = await integration.async_setup_entry(hass, entry)
        if ok is not True:
            msg = "Setup should return True"
            raise AssertionError(msg)

        # Device for global configuration should exist with canonical identifier
        device_registry = dr.async_get(hass)
        found = any(
            (DOMAIN, "global_config") in dev.identifiers
            for dev in device_registry.devices.values()
            if entry.entry_id in (dev.config_entries or set())
        )
        if not found:
            msg = "Global config device should be found"
            raise AssertionError(msg)

        # Service for creating subentry devices should be registered
        TestPatterns.assert_service_registered(hass, "create_subentry_devices")

        # Restore original method
        hass.config_entries.async_forward_entry_setups = original_forward

    async def test_unload_smoke(self, hass: HomeAssistant) -> None:
        """Smoke test: unload returns True for the global entry."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Solar Window System",
            data={"entry_type": "global"},
            entry_id="smoke_unload",
        )
        entry.add_to_hass(hass)

        # Avoid integration discovery in this smoke test
        original_forward = hass.config_entries.async_forward_entry_setups
        original_unload = hass.config_entries.async_unload_platforms
        hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=None)
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        await integration.async_setup_entry(hass, entry)
        ok = await integration.async_unload_entry(hass, entry)
        if ok is not True:
            msg = "Unload should return True"
            raise AssertionError(msg)

        # Restore original methods
        hass.config_entries.async_forward_entry_setups = original_forward
        hass.config_entries.async_unload_platforms = original_unload
