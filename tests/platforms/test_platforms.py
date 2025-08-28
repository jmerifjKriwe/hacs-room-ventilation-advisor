"""
Parametrized platform tests PoC for Solar Window System.

This file demonstrates how platform tests can be consolidated and
parametrized to reduce duplication.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from tests.helpers.fixtures_helpers import (
    collect_entities_for_setup,
    create_global_config_entry,
    ensure_global_device,
)
from tests.helpers.test_framework import PlatformTestCase

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[tuple[str, str]] = [
    ("number", "custom_components.solar_window_system.number"),
    ("text", "custom_components.solar_window_system.text"),
    ("select", "custom_components.solar_window_system.select"),
    ("switch", "custom_components.solar_window_system.switch"),
    ("sensor", "custom_components.solar_window_system.sensor"),
]


class TestPlatformSetup(PlatformTestCase):
    """Test platform setup using shared helpers."""

    test_type = "platform"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return ["hass", "global_config_entry", "entity_configs_by_platform"]

    async def test_platform_setup_minimal(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Minimal smoke test for platform setup using shared helpers."""
        for platform_name, module_path in PLATFORMS:
            entry_id = f"test_{platform_name}_entry"
            entry = create_global_config_entry(hass, entry_id=entry_id)
            ensure_global_device(hass, entry)

            module = importlib.import_module(module_path)
            added = await collect_entities_for_setup(hass, module, entry)

            # If the integration defines entities for this platform,
            # ensure they expose unique_id
            if added:
                for entity in added:
                    # Prefer public property `unique_id`.
                    # If not present, this is a failure
                    if not getattr(entity, "unique_id", None):
                        msg = "Entity must expose unique_id property"
                        raise AssertionError(msg)
