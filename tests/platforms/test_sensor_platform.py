"""Tests for sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import DOMAIN
from custom_components.solar_window_system.sensor import (
    GroupWindowPowerSensor,
    SolarWindowSystemGroupDummySensor,
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

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should add global config sensor entities
        assert async_add_entities.call_count == 1
        entities = async_add_entities.call_args[0][0]
        assert len(entities) >= 1  # At least one sensor entity


@pytest.mark.asyncio
async def test_async_setup_entry_group_config(hass: HomeAssistant) -> None:
    """Test async_setup_entry with group config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Group Config",
        data={"entry_type": "group_configs"},
        entry_id="group_entry",
    )

    # Mock subentries
    subentry = Mock()
    subentry.subentry_type = "group"
    subentry.title = "Test Group"
    entry.subentries = {"group_1": subentry}

    # Mock device registry
    device = Mock()
    device.identifiers = {(DOMAIN, "group_group_1")}
    device.name = "Test Group"
    device.manufacturer = "Test Manufacturer"
    device.model = "Group"
    device.config_entries = {entry.entry_id}
    device.config_entries_subentries = {entry.entry_id: ["group_1"]}

    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = [device]

    # Mock coordinator
    coordinator = Mock()
    coordinator.data = {
        "groups": {"group_1": {"name": "Test Group", "total_power": 100}}
    }

    with (
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ),
        patch.dict(
            hass.data,
            {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}},
        ),
    ):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should add group power sensor entities
        assert async_add_entities.call_count == 1
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 3  # 3 power sensors for groups


@pytest.mark.asyncio
async def test_async_setup_entry_window_config(hass: HomeAssistant) -> None:
    """Test async_setup_entry with window config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Window Config",
        data={"entry_type": "window_configs"},
        entry_id="window_entry",
    )

    # Mock subentries
    subentry = Mock()
    subentry.subentry_type = "window"
    subentry.title = "Test Window"
    entry.subentries = {"window_1": subentry}

    # Mock device registry
    device = Mock()
    device.identifiers = {(DOMAIN, "window_window_1")}
    device.name = "Test Window"
    device.manufacturer = "Test Manufacturer"
    device.model = "Window"
    device.config_entries = {entry.entry_id}
    device.config_entries_subentries = {entry.entry_id: ["window_1"]}

    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = [device]

    # Mock coordinator
    coordinator = Mock()
    coordinator.data = {
        "windows": {"window_1": {"name": "Test Window", "total_power": 50}}
    }

    with (
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ),
        patch.dict(
            hass.data,
            {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}},
        ),
    ):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should add window power sensor entities
        assert async_add_entities.call_count == 1
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 8  # 8 different power metrics for windows


@pytest.mark.asyncio
async def test_async_setup_entry_no_global_device(hass: HomeAssistant) -> None:
    """Test async_setup_entry when no global device is found."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Solar Window System",
        data={},
        entry_id="global_entry",
    )

    # Mock empty device registry
    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = []

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should not add any entities when no global device found
        assert async_add_entities.call_count == 0


@pytest.mark.asyncio
async def test_async_setup_entry_group_no_subentries(hass: HomeAssistant) -> None:
    """Test async_setup_entry with group config but no subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Group Config",
        data={"entry_type": "group_configs"},
        entry_id="group_entry",
    )

    entry.subentries = None

    with patch("homeassistant.helpers.device_registry.async_get"):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should not add any entities when no subentries
        assert async_add_entities.call_count == 0


@pytest.mark.asyncio
async def test_async_setup_entry_window_no_subentries(hass: HomeAssistant) -> None:
    """Test async_setup_entry with window config but no subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Window Config",
        data={"entry_type": "window_configs"},
        entry_id="window_entry",
    )

    entry.subentries = None

    with patch("homeassistant.helpers.device_registry.async_get"):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should not add any entities when no subentries
        assert async_add_entities.call_count == 0


@pytest.mark.asyncio
async def test_group_window_power_sensor_window_data(hass: HomeAssistant) -> None:
    """Test GroupWindowPowerSensor with window data."""
    device = Mock()
    device.identifiers = {(DOMAIN, "window_1")}
    device.name = "Test Window"
    device.manufacturer = "Test Manufacturer"
    device.model = "Window"

    coordinator = Mock()
    coordinator.data = {
        "windows": {
            "window_1": {
                "name": "Test Window",
                "total_power": 100,
                "total_power_direct": 80,
                "total_power_diffuse": 20,
            }
        }
    }

    sensor = GroupWindowPowerSensor(
        kind="window",
        object_name="Test Window",
        device=device,
        key="total_power",
        label="Total Power",
        coordinator=coordinator,
    )

    # Test state property
    assert sensor.state == 100


@pytest.mark.asyncio
async def test_group_window_power_sensor_group_data(hass: HomeAssistant) -> None:
    """Test GroupWindowPowerSensor with group data."""
    device = Mock()
    device.identifiers = {(DOMAIN, "group_1")}
    device.name = "Test Group"
    device.manufacturer = "Test Manufacturer"
    device.model = "Group"

    coordinator = Mock()
    coordinator.data = {
        "groups": {
            "group_1": {
                "name": "Test Group",
                "total_power": 200,
                "total_power_direct": 150,
                "total_power_diffuse": 50,
            }
        }
    }

    sensor = GroupWindowPowerSensor(
        kind="group",
        object_name="Test Group",
        device=device,
        key="total_power",
        label="Total Power",
        coordinator=coordinator,
    )

    # Test state property
    assert sensor.state == 200


@pytest.mark.asyncio
async def test_group_window_power_sensor_no_data(hass: HomeAssistant) -> None:
    """Test GroupWindowPowerSensor when no coordinator data is available."""
    device = Mock()
    device.identifiers = {(DOMAIN, "window_1")}
    device.name = "Test Window"
    device.manufacturer = "Test Manufacturer"
    device.model = "Window"

    coordinator = Mock()
    coordinator.data = None

    sensor = GroupWindowPowerSensor(
        kind="window",
        object_name="Test Window",
        device=device,
        key="total_power",
        label="Total Power",
        coordinator=coordinator,
    )

    # Test state property when no data
    assert sensor.state is None


@pytest.mark.asyncio
async def test_solar_window_system_group_dummy_sensor(hass: HomeAssistant) -> None:
    """Test SolarWindowSystemGroupDummySensor."""
    sensor = SolarWindowSystemGroupDummySensor("group_1", "Test Group")

    # Test basic properties
    assert sensor.name == "Dummy Group Sensor (Test Group)"
    assert sensor.unique_id == "solar_window_system_group_group_1_dummy"
    assert sensor.state == 42


@pytest.mark.asyncio
async def test_group_window_power_sensor_async_added_to_hass(
    hass: HomeAssistant,
) -> None:
    """Test GroupWindowPowerSensor async_added_to_hass method."""
    device = Mock()
    device.identifiers = {(DOMAIN, "window_1")}
    device.name = "Test Window"
    device.manufacturer = "Test Manufacturer"
    device.model = "Window"

    coordinator = Mock()
    coordinator.data = None

    sensor = GroupWindowPowerSensor(
        kind="window",
        object_name="Test Window",
        device=device,
        key="total_power",
        label="Total Power",
        coordinator=coordinator,
    )

    # Mock entity registry
    mock_entity_registry = Mock()
    mock_entity_registry.entities = {}
    mock_entity_registry.async_update_entity = Mock()

    # Mock restored state
    restored_state = Mock()
    restored_state.state = "123.45"

    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_entity_registry,
        ),
        patch.object(sensor, "async_get_last_state", return_value=restored_state),
    ):
        await sensor.async_added_to_hass()

        # Check that restored state was set
        assert sensor._restored_state == 123.45


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

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should add global config sensor entities
        assert async_add_entities.call_count == 1
        entities = async_add_entities.call_args[0][0]
        assert len(entities) >= 1  # At least one sensor entity


@pytest.mark.asyncio
async def test_async_setup_entry_group_config(hass: HomeAssistant) -> None:
    """Test async_setup_entry with group config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Group Config",
        data={"entry_type": "group_configs"},
        entry_id="group_entry",
    )

    # Mock subentries
    subentry = Mock()
    subentry.subentry_type = "group"
    subentry.title = "Test Group"
    entry.subentries = {"group_1": subentry}

    # Mock device registry
    device = Mock()
    device.identifiers = {(DOMAIN, "group_group_1")}
    device.name = "Test Group"
    device.manufacturer = "Test Manufacturer"
    device.model = "Group"
    device.config_entries = {entry.entry_id}
    device.config_entries_subentries = {entry.entry_id: ["group_1"]}

    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = [device]

    # Mock coordinator
    coordinator = Mock()
    coordinator.data = {
        "groups": {"group_1": {"name": "Test Group", "total_power": 100}}
    }

    with (
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ),
        patch.dict(
            hass.data,
            {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}},
        ),
    ):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should add group power sensor entities
        assert async_add_entities.call_count == 1
        entities = async_add_entities.call_args[0][0]
        assert (
            len(entities) == 3
        )  # total_power, total_power_direct, total_power_diffuse


@pytest.mark.asyncio
async def test_async_setup_entry_window_config(hass: HomeAssistant) -> None:
    """Test async_setup_entry with window config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Window Config",
        data={"entry_type": "window_configs"},
        entry_id="window_entry",
    )

    # Mock subentries
    subentry = Mock()
    subentry.subentry_type = "window"
    subentry.title = "Test Window"
    entry.subentries = {"window_1": subentry}

    # Mock device registry
    device = Mock()
    device.identifiers = {(DOMAIN, "window_window_1")}
    device.name = "Test Window"
    device.manufacturer = "Test Manufacturer"
    device.model = "Window"
    device.config_entries = {entry.entry_id}
    device.config_entries_subentries = {entry.entry_id: ["window_1"]}

    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = [device]

    # Mock coordinator
    coordinator = Mock()
    coordinator.data = {
        "windows": {"window_1": {"name": "Test Window", "total_power": 50}}
    }

    with (
        patch(
            "homeassistant.helpers.device_registry.async_get",
            return_value=mock_device_registry,
        ),
        patch.dict(
            hass.data,
            {DOMAIN: {entry.entry_id: {"coordinator": coordinator}}},
        ),
    ):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should add window power sensor entities
        assert async_add_entities.call_count == 1
        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 8  # 8 different power metrics for windows


@pytest.mark.asyncio
async def test_async_setup_entry_no_global_device(hass: HomeAssistant) -> None:
    """Test async_setup_entry when no global device is found."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Solar Window System",
        data={},
        entry_id="global_entry",
    )

    # Mock empty device registry
    mock_device_registry = Mock()
    mock_device_registry.devices.values.return_value = []

    with patch(
        "homeassistant.helpers.device_registry.async_get",
        return_value=mock_device_registry,
    ):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should not add any entities when no global device found
        assert async_add_entities.call_count == 0


@pytest.mark.asyncio
async def test_async_setup_entry_group_no_subentries(hass: HomeAssistant) -> None:
    """Test async_setup_entry with group config but no subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Group Config",
        data={"entry_type": "group_configs"},
        entry_id="group_entry",
    )

    entry.subentries = None

    with patch("homeassistant.helpers.device_registry.async_get"):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should not add any entities when no subentries
        assert async_add_entities.call_count == 0


@pytest.mark.asyncio
async def test_async_setup_entry_window_no_subentries(hass: HomeAssistant) -> None:
    """Test async_setup_entry with window config but no subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Window Config",
        data={"entry_type": "window_configs"},
        entry_id="window_entry",
    )

    entry.subentries = None

    with patch("homeassistant.helpers.device_registry.async_get"):
        async_add_entities = Mock()
        await async_setup_entry(hass, entry, async_add_entities)

        # Should not add any entities when no subentries
        assert async_add_entities.call_count == 0


@pytest.mark.asyncio
async def test_group_window_power_sensor_window_data(hass: HomeAssistant) -> None:
    """Test GroupWindowPowerSensor with window data."""
    device = Mock()
    device.identifiers = {(DOMAIN, "window_1")}
    device.name = "Test Window"
    device.manufacturer = "Test Manufacturer"
    device.model = "Window"

    coordinator = Mock()
    coordinator.data = {
        "windows": {
            "window_1": {
                "name": "Test Window",
                "total_power": 100,
                "total_power_direct": 80,
                "total_power_diffuse": 20,
            }
        }
    }

    sensor = GroupWindowPowerSensor(
        kind="window",
        object_name="Test Window",
        device=device,
        key="total_power",
        label="Total Power",
        coordinator=coordinator,
    )

    # Test state property
    assert sensor.state == 100


@pytest.mark.asyncio
async def test_group_window_power_sensor_group_data(hass: HomeAssistant) -> None:
    """Test GroupWindowPowerSensor with group data."""
    device = Mock()
    device.identifiers = {(DOMAIN, "group_1")}
    device.name = "Test Group"
    device.manufacturer = "Test Manufacturer"
    device.model = "Group"

    coordinator = Mock()
    coordinator.data = {
        "groups": {
            "group_1": {
                "name": "Test Group",
                "total_power": 200,
                "total_power_direct": 150,
                "total_power_diffuse": 50,
            }
        }
    }

    sensor = GroupWindowPowerSensor(
        kind="group",
        object_name="Test Group",
        device=device,
        key="total_power",
        label="Total Power",
        coordinator=coordinator,
    )

    # Test state property
    assert sensor.state == 200


@pytest.mark.asyncio
async def test_group_window_power_sensor_no_data(hass: HomeAssistant) -> None:
    """Test GroupWindowPowerSensor when no coordinator data is available."""
    device = Mock()
    device.identifiers = {(DOMAIN, "window_1")}
    device.name = "Test Window"
    device.manufacturer = "Test Manufacturer"
    device.model = "Window"

    coordinator = Mock()
    coordinator.data = None

    sensor = GroupWindowPowerSensor(
        kind="window",
        object_name="Test Window",
        device=device,
        key="total_power",
        label="Total Power",
        coordinator=coordinator,
    )

    # Test state property when no data
    assert sensor.state is None


@pytest.mark.asyncio
async def test_solar_window_system_group_dummy_sensor(hass: HomeAssistant) -> None:
    """Test SolarWindowSystemGroupDummySensor."""
    sensor = SolarWindowSystemGroupDummySensor("group_1", "Test Group")

    # Test basic properties
    assert sensor.name == "Dummy Group Sensor (Test Group)"
    assert sensor.unique_id == "solar_window_system_group_group_1_dummy"
    assert sensor.state == 42


@pytest.mark.asyncio
async def test_group_window_power_sensor_async_added_to_hass(
    hass: HomeAssistant,
) -> None:
    """Test GroupWindowPowerSensor async_added_to_hass method."""
    device = Mock()
    device.identifiers = {(DOMAIN, "window_1")}
    device.name = "Test Window"
    device.manufacturer = "Test Manufacturer"
    device.model = "Window"

    coordinator = Mock()
    coordinator.data = None

    sensor = GroupWindowPowerSensor(
        kind="window",
        object_name="Test Window",
        device=device,
        key="total_power",
        label="Total Power",
        coordinator=coordinator,
    )

    # Mock entity registry
    mock_entity_registry = Mock()
    mock_entity_registry.entities = {}
    mock_entity_registry.async_update_entity = Mock()

    # Mock restored state
    restored_state = Mock()
    restored_state.state = "123.45"

    with (
        patch(
            "homeassistant.helpers.entity_registry.async_get",
            return_value=mock_entity_registry,
        ),
        patch.object(sensor, "async_get_last_state", return_value=restored_state),
    ):
        await sensor.async_added_to_hass()

        # Check that restored state was set
        assert sensor._restored_state == 123.45
