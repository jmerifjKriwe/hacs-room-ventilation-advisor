"""
Test state restoration for Solar Window System entities after restart.

This module validates that RestoreEntity integration paths restore previous
state correctly for SWS sensors.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

from custom_components.solar_window_system.sensor import (
    SolarWindowSystemGroupDummySensor,
)
from homeassistant.helpers.restore_state import RestoreEntity
from tests.helpers.test_framework import BaseTestCase

# Test constants
EXPECTED_RESTORED_STATE = 99


class TestRestoreState(BaseTestCase):
    """Test state restoration for Solar Window System entities after restart."""

    test_type = "restore_state"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return []

    async def test_restore_state_on_restart(self) -> None:
        """Test that Solar Window System sensor restores its state after restart."""
        # Simulate a previous state
        old_state = Mock()
        old_state.state = EXPECTED_RESTORED_STATE
        old_state.attributes = {}

        # Patch RestoreEntity to return the old state
        with patch.object(
            RestoreEntity, "async_get_last_state", return_value=old_state
        ):
            entity = SolarWindowSystemGroupDummySensor("group1", "Test Group")
            await entity.async_added_to_hass()
            if entity.state != EXPECTED_RESTORED_STATE:
                msg = f"Expected state {EXPECTED_RESTORED_STATE}, got {entity.state}"
                raise AssertionError(msg)
