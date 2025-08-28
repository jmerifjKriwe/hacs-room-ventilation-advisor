"""
PoC snapshot test for a switch entity.

Demonstrates serializing a mapping and a State-like object for a switch.
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


class TestSwitchSnapshot(BaseTestCase):
    """PoC snapshot test for a switch entity."""

    test_type = "snapshot"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return []

    async def test_switch_snapshot_minimal(self) -> None:
        """Serialize a tiny switch and compare to snapshot."""
        raw = {
            "entity_id": "switch.sws_example_outlet",
            "unique_id": "sws_global_example_outlet",
            "state": "on",
            "attributes": {"friendly_name": "Example Outlet"},
        }

        example = serialize_entity(raw, normalize_numbers=True)
        normalize_entity_snapshot(example)
        normalize_timestamps(example)
        trim_name_prefix(example)
        assert_matches_snapshot("switch_snapshot_minimal", example)

        mock_state = Mock()
        mock_state.entity_id = "switch.sws_example_outlet"
        mock_state.state = "on"
        mock_state.attributes = {"friendly_name": "Example Outlet"}
        mock_state.unique_id = "sws_global_example_outlet"

        example2 = serialize_entity(mock_state, normalize_numbers=True)
        normalize_entity_snapshot(example2)
        normalize_timestamps(example2)
        trim_name_prefix(example2)
        if example2 != example:
            msg = "Serializer output for Mock state should match mapping-based output"
            raise AssertionError(msg)
