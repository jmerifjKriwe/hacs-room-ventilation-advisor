"""PoC snapshot test using framework."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.helpers.serializer import serialize_entity
from tests.helpers.snapshot import assert_matches_snapshot
from tests.helpers.test_framework import IntegrationTestCase

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestSnapshotHassStatePoc(IntegrationTestCase):
    """PoC snapshot test using framework."""

    async def test_hass_state_serialization(self, hass: HomeAssistant) -> None:
        """Set a state in hass and verify the serialized snapshot matches."""
        entity_id = "sensor.sws_integration_example"
        unique_id = "sws_int_example"

        # Use hass' public API to set a state (integration-style example).
        hass.states.async_set(
            entity_id,
            "12.3",
            {
                "unit_of_measurement": "W",
                "friendly_name": "Int Example",
                "unique_id": unique_id,
            },
        )
        await hass.async_block_till_done()

        st = hass.states.get(entity_id)
        example = serialize_entity(st, normalize_numbers=True)

        assert_matches_snapshot("hass_state_snapshot_minimal", example)
