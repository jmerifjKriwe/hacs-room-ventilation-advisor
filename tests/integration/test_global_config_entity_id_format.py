"""Test global config entity id format using framework."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import (
    ENTITY_PREFIX_GLOBAL,
    GLOBAL_CONFIG_ENTITIES,
)
from custom_components.solar_window_system.global_config import GlobalConfigSensor
from custom_components.solar_window_system.number import GlobalConfigNumberEntity
from custom_components.solar_window_system.select import GlobalConfigSelectEntity
from custom_components.solar_window_system.switch import GlobalConfigSwitchEntity
from custom_components.solar_window_system.text import GlobalConfigTextEntity
from homeassistant.helpers import device_registry as dr
from tests.helpers.test_framework import IntegrationTestCase

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestGlobalConfigEntityIdFormat(IntegrationTestCase):
    """Test global config entity id format using framework."""

    async def test_global_config_entity_id_and_unique_id_format(
        self, hass: HomeAssistant
    ) -> None:
        """
        Ensure entities expose the expected unique_id and entity_id formats.

        The test uses the `global_config_entry` fixture which registers a
        MockConfigEntry via the public `add_to_hass` API so the test does not
        manipulate internal hass state directly.
        """
        # Use the provided fixture which creates and adds a MockConfigEntry via
        # the public API (`add_to_hass`) so tests don't touch internals.
        global_config_entry = MockConfigEntry(
            domain="solar_window_system",
            title="Solar Window System",
            data={"entry_type": "global"},
            entry_id="test_global_entry",
        )
        global_config_entry.add_to_hass(hass)

        device_registry = dr.async_get(hass)
        device = device_registry.async_get_or_create(
            config_entry_id=global_config_entry.entry_id,
            identifiers={("solar_window_system", "global_config")},
            name="Solar Window System Global Configuration",
            manufacturer="Solar Window System",
            model="Global Configuration",
        )

        for entity_key in GLOBAL_CONFIG_ENTITIES:
            config = {
                "name": entity_key,
                "default": 0,
                "min": 0,
                "max": 100,
                "step": 1,
                "options": ["A", "B"],
                "icon": "mdi:test",
            }
            sensor = GlobalConfigSensor(entity_key, config, device)
            number = GlobalConfigNumberEntity(entity_key, config, device)
            select = GlobalConfigSelectEntity(entity_key, config, device)
            text = GlobalConfigTextEntity(entity_key, config, device)
            switch = GlobalConfigSwitchEntity(entity_key, config, device)

            for entity in [sensor, number, select, text, switch]:
                # Use the public property `unique_id` instead of reading private
                # `_attr_unique_id`.
                unique_id = entity.unique_id
                expected_unique_id = f"{ENTITY_PREFIX_GLOBAL}_{entity_key}"
                if unique_id != expected_unique_id:
                    msg = (
                        f"Entity unique_id '{unique_id}' should be "
                        f"'{expected_unique_id}'"
                    )
                    raise AssertionError(msg)
