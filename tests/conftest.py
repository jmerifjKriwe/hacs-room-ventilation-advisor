"""Test constants and fixtures for Room Ventilation Advisor."""

import logging
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.room_ventilation_advisor import DOMAIN
from custom_components.room_ventilation_advisor.const import (
    CONF_CO2_SENSOR,
    CONF_ENABLED,
    CONF_HUMIDITY_SENSOR,
    CONF_NAME,
    CONF_OUTDOOR_HUMIDITY_SENSOR,
    CONF_OUTDOOR_TEMP_SENSOR,
    CONF_ROOM_NAME,
    CONF_ROOM_TYPE,
    CONF_ROOMS,
    CONF_SCAN_INTERVAL,
    CONF_TEMP_SENSOR,
    CONF_WIND_SENSOR,
    DEFAULT_SCAN_INTERVAL,
    ROOM_TYPE_LIVING_ROOM,
)


@pytest.fixture
def mock_config_entry() -> dict[str, Any]:
    """Create a mock config entry."""
    return {
        CONF_NAME: "Test Ventilation Advisor",
        CONF_OUTDOOR_TEMP_SENSOR: "sensor.outdoor_temperature",
        CONF_OUTDOOR_HUMIDITY_SENSOR: "sensor.outdoor_humidity",
        CONF_WIND_SENSOR: "sensor.wind_speed",
        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        CONF_ROOMS: {
            "living_room": {
                CONF_ROOM_NAME: "Living Room",
                CONF_TEMP_SENSOR: "sensor.living_room_temperature",
                CONF_HUMIDITY_SENSOR: "sensor.living_room_humidity",
                CONF_ROOM_TYPE: ROOM_TYPE_LIVING_ROOM,
                CONF_CO2_SENSOR: "sensor.living_room_co2",
                CONF_ENABLED: True,
            },
        },
    }


@pytest.fixture
async def mock_hass() -> AsyncGenerator[HomeAssistant, Any]:
    """Create a mock Home Assistant instance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        hass = HomeAssistant(str(Path(temp_dir)))
        # Mock sensor states
        hass.states.async_set("sensor.outdoor_temperature", "15.0")
        hass.states.async_set("sensor.outdoor_humidity", "60.0")
        hass.states.async_set("sensor.wind_speed", "5.0")
        hass.states.async_set("sensor.living_room_temperature", "20.0")
        hass.states.async_set("sensor.living_room_humidity", "50.0")
        hass.states.async_set("sensor.living_room_co2", "800")
        yield hass


@pytest.fixture(name="config_entry")
def config_entry_fixture() -> MockConfigEntry:
    """Create a mock config entry for testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test Ventilation Advisor",
            CONF_OUTDOOR_TEMP_SENSOR: "sensor.outdoor_temperature",
            CONF_OUTDOOR_HUMIDITY_SENSOR: "sensor.outdoor_humidity",
            CONF_WIND_SENSOR: "sensor.wind_speed",
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_ROOMS: {},
        },
        options={},
    )


@pytest.fixture(autouse=True)
def suppress_expected_test_errors() -> Generator[None]:
    """Automatically suppress expected test environment errors for all tests."""
    # Store original handlers
    original_handlers = {}
    null_handler = logging.NullHandler()

    loggers_to_suppress = [
        "homeassistant.setup",
        "homeassistant.config_entries",
        "homeassistant.loader",
        "custom_components.room_ventilation_advisor",
    ]

    for logger_name in loggers_to_suppress:
        logger = logging.getLogger(logger_name)
        original_handlers[logger_name] = logger.handlers[:]
        logger.handlers.clear()
        logger.addHandler(null_handler)
        logger.setLevel(logging.CRITICAL)

    yield  # Test runs here

    # Restore original handlers
    for logger_name, handlers in original_handlers.items():
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.handlers.extend(handlers)
