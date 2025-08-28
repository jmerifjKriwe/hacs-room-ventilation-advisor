"""
Test helper fixtures for the Solar Window System tests.

Place reusable fixtures and helpers here so platform tests can be concise.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import DOMAIN, ENTITY_PREFIX
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from tests.constants import (
    GLOBAL_DEVICE_MANUFACTURER,
    GLOBAL_DEVICE_MODEL,
    GLOBAL_DEVICE_NAME,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


def create_global_config_entry(
    hass: HomeAssistant, entry_id: str = "test_entry"
) -> MockConfigEntry:
    """Create and add a MockConfigEntry for global config and return it."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Solar Window System",
        data={"entry_type": "global_config"},
        entry_id=entry_id,
    )

    # Idempotently register the created MockConfigEntry in hass. Some tests
    # expect the config entry to exist so devices can be linked to it; other
    # tests call this helper multiple times with the same entry id. Checking
    # for an existing entry avoids duplicate-registration warnings.
    existing = hass.config_entries.async_get_entry(entry_id)
    if existing is None:
        entry.add_to_hass(hass)

    return entry


def ensure_global_device(hass: HomeAssistant, entry: MockConfigEntry) -> Any:
    """Ensure the global device is present in the device registry and return it."""
    device_registry = dr.async_get(hass)
    # Ensure the config entry is added to hass so the device registry can
    # link devices to it. Some tests call `create_global_config_entry()` but
    # don't register the entry; register it here if missing.
    existing = hass.config_entries.async_get_entry(entry.entry_id)

    if existing is None:
        # Safe to call add_to_hass; MockConfigEntry handles idempotency in tests.
        entry.add_to_hass(hass)

    return device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "global_config")},
        name=GLOBAL_DEVICE_NAME,
        manufacturer=GLOBAL_DEVICE_MANUFACTURER,
        model=GLOBAL_DEVICE_MODEL,
    )


async def collect_entities_for_setup(
    hass: HomeAssistant, module: Any, entry: MockConfigEntry
) -> list[Any]:
    """

    Call module.async_setup_entry and return a list of added entities.

    The module is expected to expose
    ``async_setup_entry(hass, entry, async_add_entities)``.

    """
    added_entities: list[Any] = []

    def _mock_async_add_entities(new_entities: Iterable, *_args: Any) -> None:
        # materialize iterator
        added_entities.extend(list(new_entities))

    await module.async_setup_entry(hass, entry, _mock_async_add_entities)
    return added_entities


async def collect_entities_for_setup_with_assert(
    hass: HomeAssistant, module: Any, entry: MockConfigEntry
) -> tuple[list[Any], Callable[..., None]]:
    """

    Collect entities via module.async_setup_entry and return them.

    Return entities plus a small assert helper.

    Returns (added_entities, assert_non_empty) where ``assert_non_empty()`` will
    raise a clear AssertionError when no entities were added — useful to
    reduce boilerplate in platform tests.

    """
    added_entities = await collect_entities_for_setup(hass, module, entry)

    def assert_non_empty(message: str | None = None) -> None:
        if not added_entities:
            raise AssertionError(
                message or "No entities were registered by the platform"
            )

    return added_entities, assert_non_empty


@pytest.fixture
def global_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Pytest fixture that creates and returns a global MockConfigEntry."""
    return create_global_config_entry(hass)


# Canonical fixture name used across the test-suite
@pytest.fixture
def global_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """
    Canonical fixture alias for historical `global_entry`.

    Many tests reference `global_config_entry`; expose it from the helper
    to provide a single, consistent source of truth.
    """
    return create_global_config_entry(hass, entry_id="global_config_entry_id")


@pytest.fixture
def fake_hass_magicmock() -> MagicMock:
    """

    Return a MagicMock mimicking HomeAssistant for pure unit tests.

    Use this fixture for tests that should not rely on the real ``hass`` event
    loop or its helpers (unit tests for coordinator, calculator, etc.).
    """
    hass = MagicMock(spec=HomeAssistant)

    states_mock = MagicMock()
    hass.states = states_mock

    def _mock_get_state(_entity_id: str) -> None:
        # Minimal default mapping; tests can override hass.states.get.side_effect.
        return None

    states_mock.get.side_effect = _mock_get_state
    return hass


def create_window_config_entry(entry_id: str = "test_window_entry") -> MagicMock:
    """
    Create a MagicMock that mimics a ConfigEntry with window subentries.

    This is intended for unit tests that don't require a real MockConfigEntry
    (e.g., coordinator unit tests using MagicMock for hass).
    """
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = entry_id
    entry.title = "Test Window Configs"
    entry.data = {"entry_type": "window_configs"}

    entry.subentries = {
        "window_1": MagicMock(
            title="Living Room Window",
            subentry_type="window",
            data={"room_temperature_sensor": "sensor.room_temp_living"},
        ),
        "window_2": MagicMock(
            title="Bedroom Window",
            subentry_type="window",
            data={"room_temperature_sensor": "sensor.room_temp_bedroom"},
        ),
    }

    return entry


@pytest.fixture
def window_entry() -> MagicMock:
    """Fixture returning a MagicMock window config entry for unit tests."""
    return create_window_config_entry()


# Canonical fixture name used by platform and integration tests
@pytest.fixture
def window_config_entry() -> MagicMock:
    """
    Canonical fixture alias for historical `window_entry`.

    Returns a MagicMock mimicking a ConfigEntry for window subentries.
    """
    return create_window_config_entry(entry_id="window_config_entry_id")


async def validate_entities_for_platform(
    hass: HomeAssistant,
    module: Any,
    entry: MockConfigEntry,
    platform_configs: list[tuple[str, dict[str, Any]]],
    platform_name: str,
) -> list[Any]:
    """
    Validate entities created by a platform module.

    This function handles the common pattern of setting up entities for a platform
    and validating their basic properties.
    """
    # Ensure the global device exists
    ensure_global_device(hass, entry)

    # Collect entities
    added_entities = await collect_entities_for_setup(hass, module, entry)

    # Basic validation
    if len(added_entities) != len(platform_configs):
        msg = (
            f"Expected {len(platform_configs)} entities for {platform_name}, "
            f"got {len(added_entities)}"
        )
        raise AssertionError(msg)

    for i, (entity_key, config) in enumerate(platform_configs):
        entity = added_entities[i]
        expected_unique_id = f"{ENTITY_PREFIX}_global_{entity_key}"
        if entity.unique_id != expected_unique_id:
            msg = (
                f"Entity {i} unique_id should be {expected_unique_id}, "
                f"got {entity.unique_id}"
            )
            raise AssertionError(msg)
        if not entity.name.endswith(config["name"]):
            msg = f"Entity {i} name should end with {config['name']}, got {entity.name}"
            raise AssertionError(msg)

    return added_entities
