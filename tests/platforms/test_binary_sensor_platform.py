# ruff: noqa: S101,SLF001
"""Tests for binary_sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.solar_window_system.binary_sensor import (
    WindowShadingRequiredBinarySensor,
)
from custom_components.solar_window_system.const import DOMAIN


@pytest.mark.asyncio
async def test_window_shading_required_binary_sensor_init() -> None:
    """Test WindowShadingRequiredBinarySensor initialization."""
    coordinator = AsyncMock()
    device = Mock()
    device.identifiers = {(DOMAIN, "test_window")}
    device.name = "Test Window Device"
    device.manufacturer = "Test Manufacturer"
    device.model = "Test Model"

    window_name = "Test Window"
    sensor = WindowShadingRequiredBinarySensor(coordinator, device, window_name)

    assert sensor.coordinator == coordinator
    assert sensor._window_name == window_name
    assert sensor._attr_unique_id == "sws_window_test_window_shading_required"
    assert sensor._attr_suggested_object_id == "sws_window_test_window_shading_required"
    assert sensor._attr_name == "SWS_WINDOW Test Window Shading Required"
    assert sensor._attr_has_entity_name is False
    assert sensor._attr_icon == "mdi:shield-sun"
    assert sensor._friendly_label == "Shading Required"
