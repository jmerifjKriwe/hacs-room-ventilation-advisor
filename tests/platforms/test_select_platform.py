# ruff: noqa: S101,SLF001
"""Tests for select platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import DOMAIN
from custom_components.solar_window_system.select import (
    GlobalConfigSelectEntity,
    GroupConfigSelectEntity,
    WindowConfigSelectEntity,
    _setup_global_config_selects,
    async_setup_entry,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_async_setup_entry_global_config(hass: HomeAssistant) -> None:
    """Test async_setup_entry with global config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Solar Window System",
        data={},
        entry_id="global_entry",
    )

    # Mock device registry
    device = Mock()
    device.identifiers = {(DOMAIN, "global_config")}
    device.name = "Solar Window System"
    device.manufacturer = "Test Manufacturer"
    device.model = "Test Model"
    device.config_entries = {entry.entry_id}

    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = [device]
    hass.data["device_registry"] = mock_device_registry

    # Mock entity registry for sensor discovery
    mock_entity_registry = Mock()
    mock_entity_registry.entities.values.return_value = []
    hass.data["entity_registry"] = mock_entity_registry

    # Mock states for sensor discovery
    with patch("homeassistant.core.StateMachine.get", return_value=None):
        # Mock device registry
        device = Mock()
        device.identifiers = {(DOMAIN, "global_config")}
        device.name = "Solar Window System"
        device.manufacturer = "Test Manufacturer"
        device.model = "Test Model"
        device.config_entries = {entry.entry_id}

        mock_device_registry = Mock()
        mock_device_registry.devices.values.return_value = [device]

        with patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ):
            async_add_entities = Mock()
            await async_setup_entry(hass, entry, async_add_entities)

            # Should add global config entities:
            # weather_warning_sensor and weather_forecast_temperature_sensor
            assert async_add_entities.call_count == 1
            entities = async_add_entities.call_args[0][0]
            assert len(entities) == 2  # Two select entities added
            entity_keys = [entity._entity_key for entity in entities]
            assert "weather_warning_sensor" in entity_keys
            assert "weather_forecast_temperature_sensor" in entity_keys


@pytest.mark.asyncio
async def test_async_setup_entry_group_config(hass: HomeAssistant) -> None:
    """Test async_setup_entry with group config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"entry_type": "group_configs"},
        entry_id="group_entry",
    )

    # Mock group subentry
    group_subentry = Mock()
    group_subentry.subentry_type = "group"
    group_subentry.title = "Test Group"

    with patch.object(entry, "subentries", {"group_1": group_subentry}):
        # Mock device registry
        device = Mock()
        device.identifiers = {(DOMAIN, "group_group_1")}
        device.name = "Test Group Device"
        device.manufacturer = "Test Manufacturer"
        device.model = "Test Model"
        device.config_entries = {entry.entry_id}
        device.config_entries_subentries = {entry.entry_id: ["group_1"]}

        mock_device_registry = Mock()
        mock_device_registry.devices.values.return_value = [device]

        with patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ):
            async_add_entities = Mock()
            await async_setup_entry(hass, entry, async_add_entities)

            # Should add group config entities
            assert async_add_entities.call_count == 1


@pytest.mark.asyncio
async def test_async_setup_entry_window_config(hass: HomeAssistant) -> None:
    """Test async_setup_entry with window config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"entry_type": "window_configs"},
        entry_id="window_entry",
    )

    # Mock window subentry
    window_subentry = Mock()
    window_subentry.subentry_type = "window"
    window_subentry.title = "Test Window"

    with patch.object(entry, "subentries", {"window_1": window_subentry}):
        # Mock device registry
        device = Mock()
        device.identifiers = {(DOMAIN, "window_window_1")}
        device.name = "Test Window Device"
        device.manufacturer = "Test Manufacturer"
        device.model = "Test Model"
        device.config_entries = {entry.entry_id}
        device.config_entries_subentries = {entry.entry_id: ["window_1"]}

        mock_device_registry = Mock()
        mock_device_registry.devices.values.return_value = [device]

        with patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ):
            async_add_entities = Mock()
            await async_setup_entry(hass, entry, async_add_entities)

            # Should add window config entities
            assert async_add_entities.call_count == 1


@pytest.mark.asyncio
async def test_global_config_select_entity_init() -> None:
    """Test GlobalConfigSelectEntity initialization."""
    device = Mock()
    device.identifiers = {(DOMAIN, "global_config")}
    device.name = "Global Device"
    device.manufacturer = "Test Manufacturer"
    device.model = "Test Model"

    config = {
        "name": "Test Select",
        "options": ["option1", "option2"],
        "default": "option1",
        "icon": "mdi:test",
    }

    entity = GlobalConfigSelectEntity("test_key", config, device)

    assert entity._entity_key == "test_key"
    assert entity._attr_unique_id == "sws_global_test_key"
    assert entity._attr_name == "SWS_GLOBAL Test Select"
    assert entity._attr_options == ["option1", "option2"]
    assert entity._attr_current_option == "option1"
    assert entity._attr_icon == "mdi:test"


@pytest.mark.asyncio
async def test_global_config_select_entity_added_to_hass(
    hass: HomeAssistant,
) -> None:
    """Test GlobalConfigSelectEntity async_added_to_hass."""
    device = Mock()
    device.identifiers = {(DOMAIN, "global_config")}

    config = {
        "name": "Test Select",
        "options": ["option1", "option2"],
        "default": "option1",
    }

    entity = GlobalConfigSelectEntity("test_key", config, device)
    entity.hass = hass
    entity.entity_id = "select.test"

    # Mock entity registry
    mock_entity_registry = Mock()
    mock_entry = Mock()
    mock_entry.original_name = "Old Name"
    mock_entity_registry.entities = {"select.test": mock_entry}

    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=mock_entity_registry,
    ):
        await entity.async_added_to_hass()

        # Should update entity name
        mock_entity_registry.async_update_entity.assert_called_once_with(
            "select.test",
            name="Test Select",
        )


@pytest.mark.asyncio
async def test_setup_global_config_selects_weather_warning_sensor(
    hass: HomeAssistant,
) -> None:
    """Test _setup_global_config_selects with weather_warning_sensor entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Solar Window System",
        data={},
        entry_id="global_entry",
    )

    # Mock device registry
    device = Mock()
    device.identifiers = {(DOMAIN, "global_config")}
    device.name = "Solar Window System"
    device.manufacturer = "Test Manufacturer"
    device.model = "Test Model"
    device.config_entries = {entry.entry_id}

    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = [device]

    # Mock binary sensor and input boolean entities
    binary_sensors = ["binary_sensor.weather_warning", "binary_sensor.another_sensor"]
    input_booleans = ["input_boolean.test_boolean"]

    with (
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ),
        patch(
            "custom_components.solar_window_system.select._get_binary_sensor_entities",
            return_value=binary_sensors,
        ),
        patch(
            "custom_components.solar_window_system.select._get_input_boolean_entities",
            return_value=input_booleans,
        ),
        patch(
            "custom_components.solar_window_system.select._get_temperature_sensor_entities",
            return_value=[],
        ),
        patch(
            "custom_components.solar_window_system.select.GLOBAL_CONFIG_ENTITIES",
            {
                "weather_warning_sensor": {
                    "platform": "input_select",
                    "name": "Weather Warning Sensor",
                    "options": [],
                    "default": "",
                    "icon": "mdi:weather-cloudy-alert",
                    "category": "configuration",
                }
            },
        ),
    ):
        async_add_entities = Mock()
        await _setup_global_config_selects(hass, entry, async_add_entities)

        # Verify that the weather_warning_sensor entity was created with correct options
        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1
        entity = entities[0]
        assert entity._entity_key == "weather_warning_sensor"
        assert "" in entity._attr_options
        assert "binary_sensor.weather_warning" in entity._attr_options


@pytest.mark.asyncio
async def test_setup_global_config_selects_temperature_sensor(
    hass: HomeAssistant,
) -> None:
    """Test _setup_global_config_selects with temperature_sensor entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Solar Window System",
        data={},
        entry_id="global_entry",
    )

    # Mock device registry
    device = Mock()
    device.identifiers = {(DOMAIN, "global_config")}
    device.name = "Solar Window System"
    device.manufacturer = "Test Manufacturer"
    device.model = "Test Model"
    device.config_entries = {entry.entry_id}

    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = [device]

    # Mock temperature sensors
    temperature_sensors = ["sensor.temperature_outdoor", "sensor.temperature_indoor"]

    with (
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ),
        patch(
            "custom_components.solar_window_system.select._get_binary_sensor_entities",
            return_value=[],
        ),
        patch(
            "custom_components.solar_window_system.select._get_input_boolean_entities",
            return_value=[],
        ),
        patch(
            "custom_components.solar_window_system.select._get_temperature_sensor_entities",
            return_value=temperature_sensors,
        ),
        patch(
            "custom_components.solar_window_system.select.GLOBAL_CONFIG_ENTITIES",
            {
                "weather_forecast_temperature_sensor": {
                    "platform": "input_select",
                    "name": "Weather Forecast Temperature Sensor",
                    "options": [],
                    "default": "",
                    "icon": "mdi:thermometer",
                    "category": "configuration",
                }
            },
        ),
    ):
        async_add_entities = Mock()
        await _setup_global_config_selects(hass, entry, async_add_entities)

        # Verify that the weather_forecast_temperature_sensor entity
        # was created with correct options
        async_add_entities.assert_called_once()
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1
        entity = entities[0]
        assert entity._entity_key == "weather_forecast_temperature_sensor"
        assert "" in entity._attr_options
        assert "sensor.temperature_outdoor" in entity._attr_options

        # This should test the lines 69-75 in select.py for temperature sensor case
        # The function should be called and the coverage should be improved
    """Test GlobalConfigSelectEntity async_select_option."""
    device = Mock()
    config = {
        "name": "Test Select",
        "options": ["option1", "option2"],
        "default": "option1",
    }

    entity = GlobalConfigSelectEntity("test_key", config, device)

    # Mock async_write_ha_state to avoid coroutine warning
    entity.async_write_ha_state = Mock()

    await entity.async_select_option("option2")

    assert entity._attr_current_option == "option2"
    entity.async_write_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_group_config_select_entity_init() -> None:
    """Test GroupConfigSelectEntity initialization."""
    device = Mock()
    device.identifiers = {(DOMAIN, "group_test")}
    device.name = "Group Device"
    device.manufacturer = "Test Manufacturer"
    device.model = "Test Model"

    config = {
        "name": "Enable Scenario B",
        "options": ["disable", "enable", "inherit"],
        "default": "inherit",
        "icon": "mdi:toggle-switch",
    }

    entity = GroupConfigSelectEntity(
        "scenario_b_enable",
        config,
        device,
        "Test Group",
        "group_1",
    )

    assert entity._entity_key == "scenario_b_enable"
    assert entity._group_name == "Test Group"
    assert entity._subentry_id == "group_1"
    assert entity._attr_unique_id == "sws_group_test_group_scenario_b_enable"
    assert entity._attr_name == "SWS_GROUP Test Group Enable Scenario B"
    assert entity._attr_options == ["disable", "enable", "inherit"]
    assert entity._attr_current_option == "inherit"


@pytest.mark.asyncio
async def test_window_config_select_entity_init() -> None:
    """Test WindowConfigSelectEntity initialization."""
    device = Mock()
    device.identifiers = {(DOMAIN, "window_test")}
    device.name = "Window Device"
    device.manufacturer = "Test Manufacturer"
    device.model = "Test Model"

    config = {
        "name": "Enable Scenario B",
        "options": ["disable", "enable", "inherit"],
        "default": "inherit",
        "icon": "mdi:toggle-switch",
    }

    entity = WindowConfigSelectEntity(
        "scenario_b_enable",
        config,
        device,
        "Test Window",
        "window_1",
    )

    assert entity._entity_key == "scenario_b_enable"
    assert entity._window_name == "Test Window"
    assert entity._subentry_id == "window_1"
    assert entity._attr_unique_id == "sws_window_test_window_scenario_b_enable"
    assert entity._attr_name == "SWS_WINDOW Test Window Enable Scenario B"
    assert entity._attr_options == ["disable", "enable", "inherit"]
    assert entity._attr_current_option == "inherit"
