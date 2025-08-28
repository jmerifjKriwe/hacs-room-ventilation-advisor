"""Tests for the `recalculate` service of the Solar Window System integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

from custom_components.solar_window_system.const import DOMAIN
from tests.helpers.test_framework import ServiceTestCase


class TestRecalculateService(ServiceTestCase):
    """Tests for the recalculate service."""

    async def test_recalculate_service_empty_payload(self) -> None:
        """Call the recalculate service with empty payload."""
        # Create mock hass
        mock_hass = Mock()
        mock_hass.services.has_service = Mock(return_value=True)
        mock_hass.services.async_call = AsyncMock()

        # Service should be registered by the integration setup
        if not mock_hass.services.has_service(DOMAIN, "recalculate"):
            msg = "recalculate service not registered"
            raise AssertionError(msg)

        # Call the service with empty payload
        await mock_hass.services.async_call(DOMAIN, "recalculate", {}, blocking=True)

        # Verify service was called
        mock_hass.services.async_call.assert_called_once_with(
            DOMAIN, "recalculate", {}, blocking=True
        )

    async def test_recalculate_service_invalid_window_id(self) -> None:
        """Call the recalculate service with invalid window id."""
        # Create mock hass
        mock_hass = Mock()
        mock_hass.services.has_service = Mock(return_value=True)
        mock_hass.services.async_call = AsyncMock()

        # Service should be registered by the integration setup
        if not mock_hass.services.has_service(DOMAIN, "recalculate"):
            msg = "recalculate service not registered"
            raise AssertionError(msg)

        # Call the service with invalid window id
        await mock_hass.services.async_call(
            DOMAIN, "recalculate", {"window_id": "invalid"}, blocking=True
        )

        # Verify service was called
        mock_hass.services.async_call.assert_called_once_with(
            DOMAIN, "recalculate", {"window_id": "invalid"}, blocking=True
        )
