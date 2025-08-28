"""Minimal integration-level tests for setup using standardized framework."""

from __future__ import annotations

from custom_components.solar_window_system.const import DOMAIN
from tests.helpers.test_framework import IntegrationTestCase


class TestIntegrationSetup(IntegrationTestCase):
    """Integration setup tests using standardized framework."""

    def test_integration_setup_importable(self) -> None:
        """Test that integration module can be imported and domain constant exists."""
        if DOMAIN != "solar_window_system":
            msg = f"DOMAIN should be 'solar_window_system', got {DOMAIN!r}"
            raise AssertionError(msg)
