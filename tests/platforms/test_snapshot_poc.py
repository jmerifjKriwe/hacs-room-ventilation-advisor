"""
PoC snapshot test for Solar Window System entities.

This test demonstrates using the snapshot helper to capture a small,
serialisable representation of a single entity's defining attributes.
"""

from __future__ import annotations

from unittest.mock import Mock

from tests.helpers import normalize_entity_snapshot
from tests.helpers.serializer import serialize_entity
from tests.helpers.snapshot import assert_matches_snapshot
from tests.helpers.test_framework import BaseTestCase


class TestEntitySnapshot(BaseTestCase):
    """PoC snapshot test for Solar Window System entities."""

    test_type = "snapshot"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return []

    async def test_entity_snapshot_minimal(self) -> None:
        """Create a tiny fake entity dict and compare against snapshot."""
        # Minimal representation; in real tests we'd collect entity.state,
        # attributes, unique_id etc from the entity object returned by the
        # integration. Here we demonstrate the serializer accepting a mapping.
        raw = {
            "entity_id": "sensor.sws_example_power",
            "unique_id": "sws_global_example_power",
            "state": "123.4",
            "attributes": {"unit_of_measurement": "W", "friendly_name": "Example"},
        }

        example = serialize_entity(raw, normalize_numbers=True)

        # Normalize transient fields before snapshot assertion.
        normalize_entity_snapshot(example)

        # Compare against the stored snapshot (created previously).
        assert_matches_snapshot("entity_snapshot_minimal", example)

        # Also demonstrate serializing a State-like object (Home Assistant uses
        # objects with `state` and `attributes` attributes).
        mock_state = Mock()
        mock_state.entity_id = "sensor.sws_example_power"
        mock_state.state = "123.4"
        mock_state.attributes = {"unit_of_measurement": "W", "friendly_name": "Example"}
        mock_state.unique_id = "sws_global_example_power"

        example2 = serialize_entity(mock_state, normalize_numbers=True)
        normalize_entity_snapshot(example2)
        if example2 != example:
            msg = "Serializer output for Mock state should match mapping-based output"
            raise AssertionError(msg)
