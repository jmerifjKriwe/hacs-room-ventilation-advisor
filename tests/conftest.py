# ruff: noqa: PLC0415
"""
Pytest configuration and shared fixtures for the test suite.

This module configures pytest for Home Assistant custom component tests and
exposes commonly used fixtures used across the `tests/` directory.
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

# Ensure custom_components is in sys.path for Home Assistant test discovery
sys.path.insert(0, str((Path(__file__).parent.parent).resolve()))

from custom_components.solar_window_system.const import (
    DOMAIN,
    GLOBAL_CONFIG_ENTITIES,
)
from tests.test_data import VALID_WINDOW_DATA


# Ensure custom integrations are enabled for all tests
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """
    Enable custom integrations defined in the test dir.

    The parameter `enable_custom_integrations` is provided by the
    `pytest_homeassistant_custom_component` plugin; referencing it here
    ensures linters do not flag the argument as unused.
    """
    _ = enable_custom_integrations


# Fixtures for Home Assistant test environment
pytest_plugins = (
    "pytest_homeassistant_custom_component",
    "tests.helpers.fixtures_helpers",
)


@pytest.fixture
def mock_config_entry() -> Mock:
    """Return a mock config entry for global configuration."""
    return Mock(spec=ConfigEntry)


@pytest.fixture
def valid_global_input() -> dict[str, str]:
    """Return valid input for global configuration flow."""
    return {
        "entry_type": "global_config",
        "name": "Solar Window System",
    }


@pytest.fixture
def valid_window_input() -> dict[str, str | float | int]:
    """Return valid input for window configuration flow."""
    return VALID_WINDOW_DATA.copy()


@pytest.fixture
def valid_group_input() -> dict[str, str]:
    """Return valid input for group configuration flow."""
    return {
        "entry_type": "group",
        "group": "test_group",
        "group_name": "Test Group",
    }


# Note: canonical fixtures `global_config_entry` and `window_config_entry` are
# provided by `tests.helpers.fixtures_helpers`. Avoid redefining them here to
# prevent fixture override and accidental mutation of frozen attributes.


@pytest.fixture
def global_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a global config entry fixture for tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Solar Window System",
        data={"entry_type": "global_config"},
        entry_id="global_config_entry_id",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_device_registry() -> Mock:
    """
    Return a mock device registry.

    Tests may still depend on a mocked device registry for unit tests; keep a
    thin shim here while production fixtures are provided by helpers.
    """
    registry = Mock(spec=dr.DeviceRegistry)

    # Minimal global device placeholder to avoid test breakage
    global_device = Mock(spec=dr.DeviceEntry)
    global_device.id = "global_device_id"
    global_device.identifiers = {(DOMAIN, "global_config")}
    global_device.name = "Solar Window System Global Configuration"
    registry.devices = {"global_device_id": global_device}
    return registry


@pytest.fixture
def mock_entity_registry() -> Mock:
    """Return a mock entity registry."""
    registry = Mock(spec=er.EntityRegistry)
    registry.entities = {}
    return registry


@pytest.fixture
async def setup_global_config_device(
    hass: HomeAssistant, global_config_entry: Mock
) -> dr.DeviceEntry:
    """
    Set up a global configuration device in the device registry.

    Delegate to the helper `ensure_global_device` from
    `tests.helpers.fixtures_helpers` to maintain a single source of truth
    for how the device is created.
    """
    # Import here to avoid circular imports during pytest collection
    from tests.helpers.fixtures_helpers import (
        ensure_global_device,  # type: ignore[import]
    )

    return ensure_global_device(hass, global_config_entry)


@pytest.fixture
def expected_entity_ids() -> dict[str, str]:
    """Return expected entity IDs for global configuration entities."""
    expected = {}
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

        # Expected entity_id based on Home Assistant's automatic generation
        expected[entity_key] = f"{platform}.sws_global_{entity_key}"

    return expected


@pytest.fixture
def expected_entity_unique_ids() -> dict[str, str]:
    """Return expected unique IDs for global configuration entities."""
    expected = {}
    for entity_key in GLOBAL_CONFIG_ENTITIES:
        expected[entity_key] = f"sws_global_{entity_key}"

    return expected


@pytest.fixture
def entity_configs_by_platform() -> dict[str, list[tuple[str, dict[str, Any]]]]:
    """Return entity configurations grouped by platform."""
    platforms: dict[str, list[tuple[str, dict[str, Any]]]] = {
        "number": [],
        "text": [],
        "select": [],
        "switch": [],
        "sensor": [],
    }

    for entity_key, config in GLOBAL_CONFIG_ENTITIES.items():
        platform = config["platform"]
        if platform == "input_number":
            platforms["number"].append((entity_key, config))
        elif platform == "input_text":
            platforms["text"].append((entity_key, config))
        elif platform == "input_select":
            platforms["select"].append((entity_key, config))
        elif platform == "input_boolean":
            platforms["switch"].append((entity_key, config))
        elif platform == "sensor":
            platforms["sensor"].append((entity_key, config))

    return platforms


@pytest.fixture
def debug_entities() -> list[str]:
    """Return list of entity keys that should be diagnostic entities."""
    debug_entities = []
    for entity_key, config in GLOBAL_CONFIG_ENTITIES.items():
        if config.get("category") == "debug":
            debug_entities.append(entity_key)
    return debug_entities
