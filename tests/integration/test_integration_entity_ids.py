"""Tests for Solar Window System entity ID integration using framework."""

# ruff: noqa: ANN001,FBT001,ARG001,FBT002

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import (
    DOMAIN,
    ENTITY_PREFIX,
    GLOBAL_CONFIG_ENTITIES,
)
from custom_components.solar_window_system.sensor import (
    async_setup_entry as sensor_setup,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from tests.helpers.test_framework import IntegrationTestCase

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestEntityIDIntegration(IntegrationTestCase):
    """Test actual entity ID generation in integration."""

    async def test_sensor_entity_unique_id_format(self, hass: HomeAssistant) -> None:
        """Test that sensor entities get correct unique_id format."""
        # Create a proper mock config entry for global configuration
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Solar Window System",
            data={"entry_type": "global"},
            entry_id="test_global_entry",
        )
        config_entry.add_to_hass(hass)

        # Create device registry and add global device
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, "global_config")},
            name="Solar Window System Global Configuration",
            manufacturer="Solar Window System",
            model="Global Configuration",
        )

        # Mock entity addition to capture entities
        added_entities = []

        def mock_add_entities(
            new_entities,  # type: ignore[no-untyped-def]
            update_before_add: bool = False,
            *,
            config_subentry_id=None,
        ) -> None:
            added_entities.extend(list(new_entities))

        # Set up sensors for global entities
        await sensor_setup(hass, config_entry, mock_add_entities)

        # Verify entities were created
        if len(added_entities) == 0:
            msg = "No sensor entities were created"
            raise AssertionError(msg)

        # Check entity unique_id format
        expected_sensor_entities = [
            key
            for key, config in GLOBAL_CONFIG_ENTITIES.items()
            if config["platform"] == "sensor"
        ]

        if len(added_entities) != len(expected_sensor_entities):
            msg = (
                f"Expected {len(expected_sensor_entities)} sensor entities, "
                f"got {len(added_entities)}"
            )
            raise AssertionError(msg)

        # Verify each entity has correct unique_id format
        for entity in added_entities:
            unique_id = entity.unique_id
            if unique_id is None:
                msg = "Entity unique_id should not be None"
                raise AssertionError(msg)
            if not unique_id.startswith(ENTITY_PREFIX):
                msg = (
                    f"Entity unique_id '{unique_id}' should start with "
                    f"'{ENTITY_PREFIX}'"
                )
                raise AssertionError(msg)
            if "_global_" not in unique_id:
                msg = f"Entity unique_id '{unique_id}' should contain '_global_'"
                raise AssertionError(msg)

        # Verify specific entity unique_ids by deriving keys from unique_id
        entity_unique_ids = {
            (
                entity.unique_id.split(f"{ENTITY_PREFIX}_global_", 1)[1]
                if entity.unique_id and f"{ENTITY_PREFIX}_global_" in entity.unique_id
                else None
            ): entity.unique_id
            for entity in added_entities
        }

        for entity_key in expected_sensor_entities:
            expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
            if entity_unique_ids.get(entity_key) != expected_unique_id:
                msg = (
                    f"Entity {entity_key} has unique_id "
                    f"'{entity_unique_ids.get(entity_key)}', "
                    f"expected '{expected_unique_id}'"
                )
                raise AssertionError(msg)

    async def test_entity_registry_integration(self, hass: HomeAssistant) -> None:
        """Test that entities registered with entity registry get correct entity_id."""
        # Create config entry
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Solar Window System",
            data={"entry_type": "global"},
            entry_id="test_global_entry",
        )
        config_entry.add_to_hass(hass)

        # Create device
        device_registry = dr.async_get(hass)
        global_device = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, "global_config")},
            name="Solar Window System Global Configuration",
            manufacturer="Solar Window System",
            model="Global Configuration",
        )

        # Create and register entities manually to test entity_id generation
        entity_registry = er.async_get(hass)

        # Test one specific entity
        test_entity_key = "total_power"  # Existing sensor entity key
        test_config = GLOBAL_CONFIG_ENTITIES[test_entity_key]

        unique_id = f"{ENTITY_PREFIX}_global_{test_entity_key}"
        # Home Assistant prefixes object_id with the integration platform
        # when creating via registry
        entity_id = f"sensor.{DOMAIN}_{unique_id}"

        # Register entity
        entity_entry = entity_registry.async_get_or_create(
            domain="sensor",
            platform=DOMAIN,
            unique_id=unique_id,
            config_entry=config_entry,
            device_id=global_device.id,
            original_name=test_config["name"],
        )

        # Verify entity_id follows expected pattern
        if entity_entry.entity_id != entity_id:
            msg = f"Entity ID '{entity_entry.entity_id}' should be '{entity_id}'"
            raise AssertionError(msg)

        # Also verify it contains the unique part
        if not entity_entry.entity_id.endswith(unique_id):
            msg = "Entity ID should end with unique_id"
            raise AssertionError(msg)
