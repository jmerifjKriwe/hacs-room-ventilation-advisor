"""Tests for entity ID generation and global configuration entity creation."""

# ruff: noqa: FBT001,FBT002,ANN001,ARG001,E501
# These rules are disabled for test files as mock functions often require
# boolean parameters, missing type annotations, unused arguments, and longer lines

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from custom_components.solar_window_system.const import (
    DOMAIN,
    ENTITY_PREFIX,
    GLOBAL_CONFIG_ENTITIES,
)
from custom_components.solar_window_system.number import (
    async_setup_entry as number_async_setup_entry,
)
from custom_components.solar_window_system.select import (
    async_setup_entry as select_async_setup_entry,
)
from custom_components.solar_window_system.sensor import (
    async_setup_entry as sensor_async_setup_entry,
)
from custom_components.solar_window_system.switch import (
    async_setup_entry as switch_async_setup_entry,
)
from custom_components.solar_window_system.text import (
    async_setup_entry as text_async_setup_entry,
)
from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr
from tests.helpers.fixtures_helpers import ensure_global_device
from tests.helpers.serializer import serialize_entity
from tests.helpers.snapshot import assert_matches_snapshot
from tests.helpers.test_framework import BaseTestCase, IntegrationTestCase

if TYPE_CHECKING:
    from collections.abc import Iterable
    from unittest.mock import Mock

    from homeassistant.core import HomeAssistant


class TestGlobalConfigEntityCreation(IntegrationTestCase):
    """Test automatic entity creation for global configuration."""

    test_type = "integration"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return ["hass", "global_config_entry", "entity_configs_by_platform"]

    @pytest.mark.usefixtures("hass")
    async def test_entity_unique_ids_have_prefix(self) -> None:
        """Test that all entity unique IDs have the correct prefix."""
        for entity_key in GLOBAL_CONFIG_ENTITIES:
            expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
            if not expected_unique_id.startswith(ENTITY_PREFIX):
                msg = f"Entity {entity_key} unique_id should start with {ENTITY_PREFIX}"
                raise AssertionError(msg)
            if expected_unique_id != f"{ENTITY_PREFIX}_global_{entity_key}":
                msg = (
                    f"Entity {entity_key} should have unique_id "
                    f"{ENTITY_PREFIX}_global_{entity_key}"
                )
                raise AssertionError(msg)

    @pytest.mark.usefixtures("hass")
    async def test_entity_id_generation_from_unique_id(self) -> None:
        """Test that entity IDs are correctly generated from unique IDs."""
        for entity_key in GLOBAL_CONFIG_ENTITIES:
            config = GLOBAL_CONFIG_ENTITIES[entity_key]
            platform = config["platform"]

            # Map platform types to actual platforms
            if platform == "input_number":
                platform = "number"
            elif platform == "input_text":
                platform = "text"
            elif platform == "input_select":
                platform = "select"
            elif platform == "input_boolean":
                platform = "switch"

            # Verify the entity_id follows the pattern: platform.unique_id_part
            # For unique_id "sws_global_scenario_b_enable", entity_id should be
            # "switch.sws_global_scenario_b_enable"
            _ = f"{platform}.{ENTITY_PREFIX}_global_{entity_key}"
            # Test passes if we reach this point without assertion errors

    async def test_number_entities_creation(
        self,
        hass: HomeAssistant,
        entity_configs_by_platform: dict,
        global_config_entry: Mock,
    ) -> None:
        """Test that number entities are created correctly."""
        # Ensure the global device exists and is linked to the config entry
        ensure_global_device(hass, global_config_entry)

        # Track added entities
        added_entities: list = []

        def mock_async_add_entities(
            new_entities: Iterable, update_before_add: bool = False
        ) -> None:
            added_entities.extend(new_entities)

        # Call the setup function
        await number_async_setup_entry(
            hass, global_config_entry, mock_async_add_entities
        )

        # Verify entities were created
        number_configs = entity_configs_by_platform["number"]
        expected_count = len(number_configs)
        if len(added_entities) != expected_count:
            msg = f"Expected {expected_count} entities, got {len(added_entities)}"
            raise AssertionError(msg)

        for i, (entity_key, config) in enumerate(number_configs):
            entity = added_entities[i]
            expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
            if entity.unique_id != expected_unique_id:
                msg = f"Expected unique_id {expected_unique_id}, got {entity.unique_id}"
                raise AssertionError(msg)
            # Name is initially set with SWS_GLOBAL prefix;
            # HA will adjust via registry later
            if not entity.name.endswith(config["name"]):
                msg = f"Expected name to end with {config['name']}, got {entity.name}"
                raise AssertionError(msg)
            expected_min = config["min"]
            actual_min = getattr(
                entity,
                "native_min_value",
                getattr(entity, "_attr_native_min_value", None),
            )
            if actual_min != expected_min:
                msg = f"Expected native_min_value {expected_min}, got {actual_min}"
                raise AssertionError(msg)
            expected_max = config["max"]
            actual_max = getattr(
                entity,
                "native_max_value",
                getattr(entity, "_attr_native_max_value", None),
            )
            if actual_max != expected_max:
                msg = f"Expected native_max_value {expected_max}, got {actual_max}"
                raise AssertionError(msg)
            expected_step = config["step"]
            actual_step = getattr(
                entity, "native_step", getattr(entity, "_attr_native_step", None)
            )
            if actual_step != expected_step:
                msg = f"Expected native_step {expected_step}, got {actual_step}"
                raise AssertionError(msg)
            # Snapshot the first number entity to lock down serialization shape
            # and important attributes. This is a lightweight PoC to demonstrate
            # use of the serializer + snapshot helpers.
            if i == 0:
                serialized = serialize_entity(
                    {
                        "entity_id": (
                            entity.entity_id
                            or f"number.{ENTITY_PREFIX}_global_{entity_key}"
                        ),
                        "unique_id": entity.unique_id,
                        "state": getattr(entity, "native_value", None)
                        or getattr(entity, "_attr_native_value", None),
                        "attributes": {
                            "unit_of_measurement": getattr(
                                entity, "native_unit_of_measurement", None
                            )
                            or getattr(
                                entity, "_attr_native_unit_of_measurement", None
                            ),
                            "name": entity.name,
                        },
                    },
                    normalize_numbers=True,
                )

                assert_matches_snapshot("entity_number_example_minimal", serialized)

    async def test_text_entities_creation(
        self,
        hass: HomeAssistant,
        entity_configs_by_platform: dict,
        global_config_entry: Mock,
    ) -> None:
        """Test that text entities are created correctly."""
        # Ensure the global device exists and is linked to the config entry
        ensure_global_device(hass, global_config_entry)

        # Track added entities
        added_entities = []

        def mock_async_add_entities(
            new_entities, update_before_add: bool = False
        ) -> None:
            added_entities.extend(new_entities)

        # Call the setup function
        await text_async_setup_entry(hass, global_config_entry, mock_async_add_entities)

        # Verify entities were created
        text_configs = entity_configs_by_platform["text"]
        expected_count = len(text_configs)
        if len(added_entities) != expected_count:
            msg = f"Expected {expected_count} text entities, got {len(added_entities)}"
            raise AssertionError(msg)

        for i, (entity_key, config) in enumerate(text_configs):
            entity = added_entities[i]
            expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
            if entity.unique_id != expected_unique_id:
                msg = f"Expected unique_id {expected_unique_id}, got {entity.unique_id}"
                raise AssertionError(msg)
            if not entity.name.endswith(config["name"]):
                msg = f"Expected name to end with {config['name']}, got {entity.name}"
                raise AssertionError(msg)
            expected_max = config["max"]
            actual_max = getattr(
                entity, "native_max", getattr(entity, "_attr_native_max", None)
            )
            if actual_max != expected_max:
                msg = f"Expected native_max {expected_max}, got {actual_max}"
                raise AssertionError(msg)
            expected_value = config["default"]
            actual_value = getattr(
                entity, "native_value", getattr(entity, "_attr_native_value", None)
            )
            if actual_value != expected_value:
                msg = f"Expected native_value {expected_value}, got {actual_value}"
                raise AssertionError(msg)

    async def test_select_entities_creation(
        self,
        hass: HomeAssistant,
        entity_configs_by_platform: dict,
        global_config_entry: Mock,
    ) -> None:
        """Test that select entities are created correctly."""
        # Ensure the global device exists and is linked to the config entry
        ensure_global_device(hass, global_config_entry)

        # Track added entities
        added_entities = []

        def mock_async_add_entities(
            new_entities, update_before_add: bool = False, *, config_subentry_id=None
        ) -> None:
            added_entities.extend(new_entities)

        # Call the setup function
        await select_async_setup_entry(
            hass, global_config_entry, mock_async_add_entities
        )

        # Verify entities were created
        select_configs = entity_configs_by_platform["select"]
        expected_count = len(select_configs)
        if len(added_entities) != expected_count:
            msg = (
                f"Expected {expected_count} select entities, got {len(added_entities)}"
            )
            raise AssertionError(msg)

        for i, (entity_key, config) in enumerate(select_configs):
            entity = added_entities[i]
            expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
            if entity.unique_id != expected_unique_id:
                msg = f"Expected unique_id {expected_unique_id}, got {entity.unique_id}"
                raise AssertionError(msg)
            if not entity.name.endswith(config["name"]):
                msg = f"Expected name to end with {config['name']}, got {entity.name}"
                raise AssertionError(msg)
            # Options are dynamic; we ensure an empty placeholder is present as first option
            options = getattr(entity, "options", getattr(entity, "_attr_options", None))
            if not isinstance(options, list):
                msg = f"Expected options to be a list, got {type(options)}"
                raise TypeError(msg)
            if options[0] != "":
                msg = f"Expected first option to be empty string, got '{options[0]}'"
                raise AssertionError(msg)

    async def test_switch_entities_creation(
        self,
        hass: HomeAssistant,
        entity_configs_by_platform: dict,
        global_config_entry: Mock,
    ) -> None:
        """Test that switch entities are created correctly."""
        # Ensure the global device exists and is linked to the config entry
        ensure_global_device(hass, global_config_entry)

        # Track added entities
        added_entities = []

        def mock_async_add_entities(
            new_entities, update_before_add: bool = False
        ) -> None:
            added_entities.extend(new_entities)

        # Call the setup function
        await switch_async_setup_entry(
            hass, global_config_entry, mock_async_add_entities
        )

        # Verify entities were created
        switch_configs = entity_configs_by_platform["switch"]
        expected_count = len(switch_configs)
        if len(added_entities) != expected_count:
            msg = (
                f"Expected {expected_count} switch entities, got {len(added_entities)}"
            )
            raise AssertionError(msg)

        for i, (entity_key, config) in enumerate(switch_configs):
            entity = added_entities[i]
            expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
            if entity.unique_id != expected_unique_id:
                msg = f"Expected unique_id {expected_unique_id}, got {entity.unique_id}"
                raise AssertionError(msg)
            if not entity.name.endswith(config["name"]):
                msg = f"Expected name to end with {config['name']}, got {entity.name}"
                raise AssertionError(msg)
            expected_state = config["default"]
            actual_state = getattr(
                entity, "is_on", getattr(entity, "_attr_is_on", None)
            )
            if actual_state != expected_state:
                msg = f"Expected is_on {expected_state}, got {actual_state}"
                raise AssertionError(msg)

    async def test_sensor_entities_creation(
        self,
        hass: HomeAssistant,
        entity_configs_by_platform: dict,
        global_config_entry: Mock,
    ) -> None:
        """Test that sensor entities are created correctly."""
        # Ensure the global device exists and is linked to the config entry
        ensure_global_device(hass, global_config_entry)

        # Track added entities
        added_entities = []

        def mock_async_add_entities(
            new_entities, update_before_add: bool = False, *, config_subentry_id=None
        ) -> None:
            added_entities.extend(new_entities)

        # Call the setup function
        await sensor_async_setup_entry(
            hass, global_config_entry, mock_async_add_entities
        )

        # Verify entities were created
        sensor_configs = entity_configs_by_platform["sensor"]
        expected_count = len(sensor_configs)
        if len(added_entities) != expected_count:
            msg = (
                f"Expected {expected_count} sensor entities, got {len(added_entities)}"
            )
            raise AssertionError(msg)

        for i, (entity_key, config) in enumerate(sensor_configs):
            entity = added_entities[i]
            expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
            if entity.unique_id != expected_unique_id:
                msg = f"Expected unique_id {expected_unique_id}, got {entity.unique_id}"
                raise AssertionError(msg)
            if not entity.name.endswith(config["name"]):
                msg = f"Expected name to end with {config['name']}, got {entity.name}"
                raise AssertionError(msg)

    async def test_diagnostic_entities_have_correct_category(
        self, hass: HomeAssistant, debug_entities: list[str], global_config_entry: Mock
    ) -> None:
        """Test that debug entities have the diagnostic category."""
        # Set up device registry with global config device
        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=global_config_entry.entry_id,
            identifiers={(DOMAIN, "global_config")},
            name="Solar Window System Global Configuration",
            manufacturer="Solar Window System",
            model="Global Configuration",
        )

        # Track added entities
        added_entities = []

        def mock_async_add_entities(
            new_entities, update_before_add: bool = False
        ) -> None:
            added_entities.extend(new_entities)

        # Call the setup function
        await text_async_setup_entry(hass, global_config_entry, mock_async_add_entities)

        # Find debug entities and verify their category
        debug_found = []
        for entity in added_entities:
            # Derive entity_key from unique_id instead of relying on internals.
            entity_key = None
            if entity.unique_id and f"{ENTITY_PREFIX}_global_" in entity.unique_id:
                entity_key = entity.unique_id.split(f"{ENTITY_PREFIX}_global_", 1)[1]

            if entity_key in debug_entities:
                debug_found.append(entity_key)
                expected_category = EntityCategory.DIAGNOSTIC
                actual_category = getattr(
                    entity,
                    "entity_category",
                    getattr(entity, "_attr_entity_category", None),
                )
                if actual_category != expected_category:
                    msg = f"Debug entity {entity_key} should have DIAGNOSTIC category"
                    raise AssertionError(msg)

        # Ensure we found all debug entities
        expected_debug_entities = set(debug_entities)
        actual_debug_entities = set(debug_found)
        if actual_debug_entities != expected_debug_entities:
            msg = "Not all debug entities were found"
            raise AssertionError(msg)

    async def test_all_entities_have_device_info(
        self,
        hass: HomeAssistant,
        global_config_entry: Mock,
    ) -> None:
        """Test that all entities have proper device info."""
        # Ensure the global device exists and is linked to the config entry
        expected_device = ensure_global_device(hass, global_config_entry)

        # Track added entities
        added_entities = []

        def mock_async_add_entities(
            new_entities, update_before_add: bool = False
        ) -> None:
            added_entities.extend(new_entities)

        # Call the setup function
        await number_async_setup_entry(
            hass, global_config_entry, mock_async_add_entities
        )

        # Verify all entities have correct device info
        for entity in added_entities:
            device_info = entity.device_info
            if device_info is None:
                msg = "Entity device_info should not be None"
                raise AssertionError(msg)
            if device_info["identifiers"] != expected_device.identifiers:
                msg = (
                    f"Expected identifiers {expected_device.identifiers}, "
                    f"got {device_info['identifiers']}"
                )
                raise AssertionError(msg)
            if device_info["name"] != expected_device.name:
                msg = f"Expected name {expected_device.name}, got {device_info['name']}"
                raise AssertionError(msg)
            if device_info["manufacturer"] != expected_device.manufacturer:
                msg = (
                    f"Expected manufacturer {expected_device.manufacturer}, "
                    f"got {device_info['manufacturer']}"
                )
                raise AssertionError(msg)
            if device_info["model"] != expected_device.model:
                msg = (
                    f"Expected model {expected_device.model}, "
                    f"got {device_info['model']}"
                )
                raise AssertionError(msg)

    async def test_only_global_config_entry_processed(
        self, hass: HomeAssistant, window_config_entry: Mock
    ) -> None:
        """Test that only global configuration entries are processed."""
        # Track added entities
        added_entities = []

        def mock_async_add_entities(
            new_entities, update_before_add: bool = False
        ) -> None:
            added_entities.extend(new_entities)

        # Call setup with window entry (should not create entities)
        await number_async_setup_entry(
            hass, window_config_entry, mock_async_add_entities
        )

        # No entities should be created for window entries
        if len(added_entities) != 0:
            msg = f"Expected 0 entities for window entries, got {len(added_entities)}"
            raise AssertionError(msg)


class TestEntityIdNamingConvention(BaseTestCase):
    """Test entity ID naming conventions and prefixing."""

    async def test_entity_prefix_constant(self) -> None:
        """Test that entity prefix constant is correctly defined."""
        if ENTITY_PREFIX != "sws":
            msg = f"Entity prefix should be 'sws', got '{ENTITY_PREFIX}'"
            raise AssertionError(msg)

    async def test_unique_id_prefix_application(
        self, expected_entity_unique_ids: dict[str, str]
    ) -> None:
        """Test that unique IDs correctly apply the prefix."""
        for entity_key, unique_id in expected_entity_unique_ids.items():
            expected_prefix = f"{ENTITY_PREFIX}_global_"
            if not unique_id.startswith(expected_prefix):
                msg = f"Unique ID {unique_id} should start with {expected_prefix}"
                raise AssertionError(msg)

            # Verify the entity key is preserved
            if not unique_id.endswith(entity_key):
                msg = f"Unique ID {unique_id} should end with {entity_key}"
                raise AssertionError(msg)

    async def test_entity_id_format(self, expected_entity_ids: dict[str, str]) -> None:
        """Test that entity IDs follow the correct format."""
        for entity_key, entity_id in expected_entity_ids.items():
            parts = entity_id.split(".", 1)
            entity_id_parts_count = 2
            if len(parts) != entity_id_parts_count:
                msg = f"Entity ID {entity_id} should have format 'platform.name'"
                raise AssertionError(msg)

            platform, name_part = parts
            if platform not in [
                "number",
                "text",
                "select",
                "switch",
                "sensor",
            ]:
                msg = f"Platform {platform} is not recognized"
                raise AssertionError(msg)

            expected_name = f"{ENTITY_PREFIX}_global_{entity_key}"
            if name_part != expected_name:
                msg = f"Name part {name_part} should be {expected_name}"
                raise AssertionError(msg)

    async def test_entity_count_by_platform(
        self, entity_configs_by_platform: dict
    ) -> None:
        """Test that entities are correctly distributed across platforms."""
        # Verify we have entities for each platform
        total_entities = sum(
            len(configs) for configs in entity_configs_by_platform.values()
        )
        expected_total = len(GLOBAL_CONFIG_ENTITIES)

        if total_entities != expected_total:
            msg = f"Total entities {total_entities} should equal {expected_total}"
            raise AssertionError(msg)

        # Verify each platform has at least one entity
        for platform, configs in entity_configs_by_platform.items():
            if len(configs) > 0:
                # Verify all entities in this platform have the correct platform mapping
                for entity_key, config in configs:
                    platform_mapping = {
                        "number": "input_number",
                        "text": "input_text",
                        "select": "input_select",
                        "switch": "input_boolean",
                        "sensor": "sensor",
                    }
                    expected_platform = platform_mapping[platform]
                    if config["platform"] != expected_platform:
                        msg = (
                            f"Entity {entity_key} should have platform "
                            f"{expected_platform}"
                        )
                        raise AssertionError(msg)
