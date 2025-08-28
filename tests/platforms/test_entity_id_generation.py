"""Tests for entity ID generation and prefix application."""

from __future__ import annotations

from custom_components.solar_window_system.const import (
    ENTITY_PREFIX,
    GLOBAL_CONFIG_ENTITIES,
)
from tests.helpers.test_framework import BaseTestCase

# Constants for expected values
EXPECTED_TOTAL_ENTITIES = 13
EXPECTED_NUMBER_ENTITIES = 3
EXPECTED_TEXT_ENTITIES = 1
EXPECTED_SELECT_ENTITIES = 2
EXPECTED_BOOLEAN_ENTITIES = 3
EXPECTED_SENSOR_ENTITIES = 4
EXPECTED_DEBUG_ENTITIES = 1


class TestEntityIdGeneration(BaseTestCase):
    """Test entity ID generation and naming conventions."""

    test_type = "entity_ids"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return []

    def test_entity_prefix_constant(self) -> None:
        """Verify the entity prefix constant matches the expected value."""
        expected_prefix = "sws"
        if expected_prefix != ENTITY_PREFIX:
            msg = f"Entity prefix should be '{expected_prefix}', got '{ENTITY_PREFIX}'"
            raise AssertionError(msg)

    def test_unique_id_format(self) -> None:
        """Validate the unique ID format for all global config entities."""
        for entity_key in GLOBAL_CONFIG_ENTITIES:
            expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
            if not expected_unique_id.startswith(ENTITY_PREFIX):
                msg = (
                    f"Unique ID {expected_unique_id} should start with {ENTITY_PREFIX}"
                )
                raise AssertionError(msg)
            if "_global_" not in expected_unique_id:
                msg = f"Unique ID {expected_unique_id} should contain '_global_'"
                raise AssertionError(msg)
            if not expected_unique_id.endswith(entity_key):
                msg = f"Unique ID {expected_unique_id} should end with {entity_key}"
                raise AssertionError(msg)

    def test_expected_entity_ids(self) -> None:
        """Verify expected entity IDs are constructed for each entity key."""
        expected_entity_ids = {}
        for entity_key, config in GLOBAL_CONFIG_ENTITIES.items():
            platform = config["platform"]
            if platform == "input_number":
                platform = "number"
            elif platform == "input_text":
                platform = "text"
            elif platform == "input_select":
                platform = "select"
            elif platform == "input_boolean":
                platform = "switch"
            expected_entity_ids[entity_key] = (
                f"{platform}.{ENTITY_PREFIX}_global_{entity_key}"
            )

        for entity_key, expected_entity_id in expected_entity_ids.items():
            if "." not in expected_entity_id:
                msg = f"Entity ID {expected_entity_id} should contain '.'"
                raise AssertionError(msg)
            platform, name_part = expected_entity_id.split(".", 1)
            valid_platforms = ["number", "text", "select", "switch", "sensor"]
            if platform not in valid_platforms:
                msg = f"Platform {platform} should be one of {valid_platforms}"
                raise AssertionError(msg)
            expected_name = f"{ENTITY_PREFIX}_global_{entity_key}"
            if name_part != expected_name:
                msg = f"Name part {name_part} should be {expected_name}"
                raise AssertionError(msg)

    def test_global_config_entities_structure(self) -> None:
        """Check the overall structure and counts of GLOBAL_CONFIG_ENTITIES."""
        actual_count = len(GLOBAL_CONFIG_ENTITIES)
        if actual_count != EXPECTED_TOTAL_ENTITIES:
            msg = f"Expected {EXPECTED_TOTAL_ENTITIES} entities, got {actual_count}"
            raise AssertionError(msg)

        platform_counts = {
            "input_number": 0,
            "input_text": 0,
            "input_select": 0,
            "input_boolean": 0,
            "sensor": 0,
        }
        debug_entities = 0

        for entity_key, config in GLOBAL_CONFIG_ENTITIES.items():
            required_fields = ["platform", "name", "default"]
            for field in required_fields:
                if field not in config:
                    msg = f"Entity {entity_key} missing required field: {field}"
                    raise AssertionError(msg)
            platform = config["platform"]
            if platform not in platform_counts:
                msg = f"Unknown platform: {platform}"
                raise AssertionError(msg)
            platform_counts[platform] += 1
            if config.get("category") == "debug":
                debug_entities += 1

        expected_counts = {
            "input_number": EXPECTED_NUMBER_ENTITIES,
            "input_text": EXPECTED_TEXT_ENTITIES,
            "input_select": EXPECTED_SELECT_ENTITIES,
            "input_boolean": EXPECTED_BOOLEAN_ENTITIES,
            "sensor": EXPECTED_SENSOR_ENTITIES,
        }

        for platform, expected_count in expected_counts.items():
            actual_count = platform_counts[platform]
            if actual_count != expected_count:
                msg = (
                    f"Expected {expected_count} {platform} entities, got {actual_count}"
                )
                raise AssertionError(msg)

        if debug_entities != EXPECTED_DEBUG_ENTITIES:
            msg = (
                f"Expected {EXPECTED_DEBUG_ENTITIES} debug entities, "
                f"got {debug_entities}"
            )
            raise AssertionError(msg)

        total_entities = sum(platform_counts.values())
        if total_entities != EXPECTED_TOTAL_ENTITIES:
            msg = (
                f"Total entities {total_entities} should equal "
                f"{EXPECTED_TOTAL_ENTITIES}"
            )
            raise AssertionError(msg)

    def test_entity_unique_id_uniqueness(self) -> None:
        """Ensure unique IDs are unique across all defined entities."""
        unique_ids = [
            f"{ENTITY_PREFIX}_global_{entity_key}"
            for entity_key in GLOBAL_CONFIG_ENTITIES
        ]
        if len(unique_ids) != len(set(unique_ids)):
            msg = "Found duplicate unique IDs"
            raise AssertionError(msg)

    def test_debug_entity_identification(self) -> None:
        """Detect debug-category entities and ensure they're marked correctly."""
        debug_entities = [
            entity_key
            for entity_key, config in GLOBAL_CONFIG_ENTITIES.items()
            if config.get("category") == "debug"
        ]
        if len(debug_entities) != EXPECTED_DEBUG_ENTITIES:
            msg = (
                f"Expected {EXPECTED_DEBUG_ENTITIES} debug entity, "
                f"got {len(debug_entities)}"
            )
            raise AssertionError(msg)
        if "debug" not in debug_entities:
            msg = "Expected 'debug' entity to be marked as debug"
            raise AssertionError(msg)
