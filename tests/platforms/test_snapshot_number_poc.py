"""
PoC snapshot test for a number entity.

Demonstrates serializing a mapping and a State-like object for a number.
"""

from __future__ import annotations

from unittest.mock import Mock

from tests.helpers import (
    normalize_entity_snapshot,
    normalize_timestamps,
    trim_name_prefix,
)
from tests.helpers.serializer import serialize_entity
from tests.helpers.snapshot import assert_matches_snapshot
from tests.helpers.test_framework import BaseTestCase


class TestNumberSnapshot(BaseTestCase):
    """PoC snapshot test for a number entity."""

    test_type = "snapshot"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return []

    async def test_number_snapshot_minimal(self) -> None:
        """Serialize a tiny number entity and compare to snapshot."""
        raw = {
            "entity_id": "number.sws_example_setpoint",
            "unique_id": "sws_global_example_setpoint",
            "state": "21.5",
            "attributes": {
                "unit_of_measurement": "°C",
                "friendly_name": "Example Setpoint",
            },
        }

        example = serialize_entity(raw, normalize_numbers=True)
        normalize_entity_snapshot(example)
        normalize_timestamps(example)
        trim_name_prefix(example)
        assert_matches_snapshot("number_snapshot_minimal", example)

        mock_state = Mock()
        mock_state.entity_id = "number.sws_example_setpoint"
        mock_state.state = "21.5"
        mock_state.attributes = {
            "unit_of_measurement": "°C",
            "friendly_name": "Example Setpoint",
        }
        mock_state.unique_id = "sws_global_example_setpoint"

        example2 = serialize_entity(mock_state, normalize_numbers=True)
        normalize_entity_snapshot(example2)
        normalize_timestamps(example2)
        trim_name_prefix(example2)
        if example2 != example:
            msg = "Serializer output for Mock state should match mapping-based output"
            raise AssertionError(msg)
