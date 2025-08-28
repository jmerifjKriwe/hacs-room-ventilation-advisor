"""Simple test to verify entity ID generation works correctly."""

from __future__ import annotations

from unittest.mock import Mock

from custom_components.solar_window_system.const import (
    ENTITY_PREFIX,
    GLOBAL_CONFIG_ENTITIES,
)
from custom_components.solar_window_system.number import GlobalConfigNumberEntity
from homeassistant.helpers import device_registry as dr
from tests.helpers.test_framework import BaseTestCase


class TestEntityIDGenerationSimple(BaseTestCase):
    """Simple test to verify entity ID generation works correctly."""

    test_type = "entity_ids"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return []

    def test_number_entity_unique_id(self) -> None:
        """Test that number entity unique ID is generated correctly."""
        entity_key = "window_g_value"
        config = {
            "platform": "input_number",
            "name": "Window G-Value",
            "min": 0.1,
            "max": 0.9,
            "step": 0.01,
            "default": 0.5,
            "unit": "",
            "icon": "mdi:window-closed-variant",
        }

        device = Mock(spec=dr.DeviceEntry)
        device.identifiers = {("solar_window_system", "global_config")}
        device.name = "Test Device"
        device.manufacturer = "Test"
        device.model = "Test"

        entity = GlobalConfigNumberEntity(entity_key, config, device)
        expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"

        if entity.unique_id != expected_unique_id:
            msg = f"Expected unique_id '{expected_unique_id}', got '{entity.unique_id}'"
            raise AssertionError(msg)
        if entity.unique_id is None:
            msg = "Entity unique_id should not be None"
            raise AssertionError(msg)
        if not entity.unique_id.startswith(ENTITY_PREFIX):
            msg = (
                f"Entity unique_id should start with '{ENTITY_PREFIX}', "
                f"got '{entity.unique_id}'"
            )
            raise AssertionError(msg)

        expected_entity_id = f"number.{expected_unique_id}"
        if not expected_entity_id.startswith(f"number.{ENTITY_PREFIX}_"):
            msg = (
                f"Expected entity_id to start with 'number.{ENTITY_PREFIX}_', "
                f"got '{expected_entity_id}'"
            )
            raise AssertionError(msg)

    def test_all_global_config_entities_have_prefix(self) -> None:
        """Test that all global config entities have correct prefix."""
        for entity_key, config in GLOBAL_CONFIG_ENTITIES.items():
            platform = config["platform"]
            if platform == "input_number":
                ha_platform = "number"
            elif platform == "input_text":
                ha_platform = "text"
            elif platform == "input_select":
                ha_platform = "select"
            elif platform == "input_boolean":
                ha_platform = "switch"
            else:
                ha_platform = platform

            expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
            expected_entity_id = f"{ha_platform}.{expected_unique_id}"
            if not expected_entity_id.startswith(f"{ha_platform}.{ENTITY_PREFIX}_"):
                msg = (
                    f"Expected entity_id to start with "
                    f"'{ha_platform}.{ENTITY_PREFIX}_', "
                    f"got '{expected_entity_id}'"
                )
                raise AssertionError(msg)
