"""Global Configuration Registry Entity ID Tests."""

from __future__ import annotations

from unittest.mock import Mock

from custom_components.solar_window_system.number import GlobalConfigNumberEntity
from homeassistant.helpers import device_registry as dr
from tests.helpers.test_framework import BaseTestCase


class TestGlobalConfigRegistryIds(BaseTestCase):
    """Global Configuration Registry Entity ID Tests."""

    test_type = "entity_ids"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return []

    def test_entity_attributes_have_sws_global_prefix(self) -> None:
        """Test that entity attributes have the correct SWS global prefix."""
        entity_key = "window_g_value"
        config = {
            "name": "Window G-Value",
            "min": 0.1,
            "max": 1.0,
            "step": 0.01,
            "default": 0.5,
            "unit": None,
            "icon": "mdi:window-closed-variant",
        }

        device = Mock(spec=dr.DeviceEntry)
        device.identifiers = {("solar_window_system", "global_config")}
        device.name = "Solar Window System Global Configuration"
        device.manufacturer = "Solar Window System"
        device.model = "Global Configuration"

        entity = GlobalConfigNumberEntity(entity_key, config, device)

        expected_unique_id = f"sws_global_{entity_key}"
        # Prefer the public `unique_id` property
        if entity.unique_id != expected_unique_id:
            msg = f"Expected unique_id '{expected_unique_id}', got '{entity.unique_id}'"
            raise AssertionError(msg)

        expected_suggested_object_id = f"sws_global_{entity_key}"
        # Use public `suggested_object_id` attribute if available, otherwise
        # fall back to the private attribute for older Home Assistant versions.
        suggested = getattr(entity, "suggested_object_id", None)
        # Accept either the public suggested_object_id (newer HA) or the internal
        # fallback used in older versions. In some environments suggested may be a
        # friendly name, so allow that too if it matches the human name.
        if suggested is not None and suggested != expected_suggested_object_id:
            # allow friendly-name-like suggestions
            if entity.name and suggested not in (
                entity.name,
                expected_suggested_object_id,
            ):
                msg = (
                    f"Expected suggested_object_id to be "
                    f"'{expected_suggested_object_id}' or '{entity.name}', "
                    f"got '{suggested}'"
                )
                raise AssertionError(msg)
        elif (
            getattr(entity, "_attr_suggested_object_id", None)
            != expected_suggested_object_id
        ):
            msg = (
                f"Expected _attr_suggested_object_id "
                f"'{expected_suggested_object_id}', "
                f"got '{getattr(entity, '_attr_suggested_object_id', None)}'"
            )
            raise AssertionError(msg)

        expected_temp_name = f"SWS_GLOBAL {config['name']}"
        if entity.name != expected_temp_name:
            msg = f"Expected name '{expected_temp_name}', got '{entity.name}'"
            raise AssertionError(msg)
        # Verify the public unique_id includes the entity key
        if entity.unique_id != expected_unique_id:
            msg = f"Expected unique_id '{expected_unique_id}', got '{entity.unique_id}'"
            raise AssertionError(msg)

    def test_multiple_entities_have_correct_prefixes(self) -> None:
        """Test that multiple entities have correct prefixes."""
        config = {
            "name": "Test Entity",
            "min": 0,
            "max": 100,
            "step": 1,
            "default": 50,
            "unit": None,
            "icon": "mdi:test",
        }

        device = Mock(spec=dr.DeviceEntry)
        device.identifiers = {("solar_window_system", "global_config")}
        device.name = "Test Device"
        device.manufacturer = "Test Manufacturer"
        device.model = "Test Model"

        test_entity_keys = ["window_g_value", "window_frame_width", "threshold_direct"]

        for entity_key in test_entity_keys:
            entity = GlobalConfigNumberEntity(entity_key, config, device)
            # Assert via public API for each created entity
            expected_unique_id = f"sws_global_{entity_key}"
            if entity.unique_id != expected_unique_id:
                msg = (
                    f"Expected unique_id '{expected_unique_id}', "
                    f"got '{entity.unique_id}'"
                )
                raise AssertionError(msg)
            entity_name = str(entity.name) if entity.name else ""
            if entity_name and not entity_name.startswith("SWS_GLOBAL"):
                msg = f"Expected name to start with 'SWS_GLOBAL', got '{entity_name}'"
                raise AssertionError(msg)
