# ruff: noqa: SLF001
"""Tests for global_config.py module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from custom_components.solar_window_system.const import (
    DOMAIN,
    ENTITY_PREFIX_GLOBAL,
    GLOBAL_CONFIG_ENTITIES,
)
from custom_components.solar_window_system.global_config import (
    GlobalConfigSensor,
    _associate_entity_with_device,
    _create_input_boolean_via_service,
    _create_input_number_via_service,
    _create_input_select_via_service,
    _create_input_text_via_service,
    _get_binary_sensor_entities,
    _get_input_boolean_entities,
    _get_temperature_sensor_entities,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr


class TestGlobalConfig:
    """Test global configuration functionality."""

    @pytest.fixture
    def mock_device(self) -> dr.DeviceEntry:
        """Create a mock device entry."""
        device = Mock(spec=dr.DeviceEntry)
        device.id = "test_device_id"
        device.identifiers = {(DOMAIN, "global_config")}
        device.name = "Test Global Config Device"
        device.manufacturer = "Test Manufacturer"
        device.model = "Test Model"
        return device

    @pytest.fixture
    def mock_hass(self) -> HomeAssistant:
        """Create a mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        hass.services = Mock()
        hass.services.async_call = AsyncMock()
        hass.data = {}
        hass.states = Mock()
        return hass

    @pytest.mark.asyncio
    async def test_create_input_number_via_service(
        self, mock_hass: HomeAssistant, mock_device: dr.DeviceEntry
    ) -> None:
        """Test creating input_number entity via service."""
        entity_key = "min_solar_radiation"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        with patch(
            "custom_components.solar_window_system.global_config._associate_entity_with_device"
        ) as mock_associate:
            mock_associate.return_value = None

            await _create_input_number_via_service(
                mock_hass, entity_key, config, mock_device
            )

            # Verify service call
            mock_hass.services.async_call.assert_called_once_with(
                "input_number",
                "create",
                {
                    "name": f"{ENTITY_PREFIX_GLOBAL}_{entity_key}",
                    "min": config["min"],
                    "max": config["max"],
                    "step": config["step"],
                    "initial": config["default"],
                    "icon": config.get("icon"),
                    "unit_of_measurement": config["unit"],
                },
            )

            # Verify entity association
            mock_associate.assert_called_once_with(
                mock_hass,
                f"input_number.{ENTITY_PREFIX_GLOBAL}_{entity_key}",
                mock_device,
            )

    @pytest.mark.asyncio
    async def test_create_input_text_via_service(
        self, mock_hass: HomeAssistant, mock_device: dr.DeviceEntry
    ) -> None:
        """Test creating input_text entity via service."""
        entity_key = "debug"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        with patch(
            "custom_components.solar_window_system.global_config._associate_entity_with_device"
        ) as mock_associate:
            mock_associate.return_value = None

            await _create_input_text_via_service(
                mock_hass, entity_key, config, mock_device
            )

            # Verify service call
            mock_hass.services.async_call.assert_called_once_with(
                "input_text",
                "create",
                {
                    "name": f"{ENTITY_PREFIX_GLOBAL}_{entity_key}",
                    "initial": config["default"],
                    "max": config["max"],
                    "icon": config.get("icon"),
                },
            )

            # Verify entity association
            mock_associate.assert_called_once_with(
                mock_hass,
                f"input_text.{ENTITY_PREFIX_GLOBAL}_{entity_key}",
                mock_device,
            )

    @pytest.mark.asyncio
    async def test_create_input_boolean_via_service(
        self, mock_hass: HomeAssistant, mock_device: dr.DeviceEntry
    ) -> None:
        """Test creating input_boolean entity via service."""
        entity_key = "scenario_b_enable"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        with patch(
            "custom_components.solar_window_system.global_config._associate_entity_with_device"
        ) as mock_associate:
            mock_associate.return_value = None

            await _create_input_boolean_via_service(
                mock_hass, entity_key, config, mock_device
            )

            # Verify service call
            mock_hass.services.async_call.assert_called_once_with(
                "input_boolean",
                "create",
                {
                    "name": f"{ENTITY_PREFIX_GLOBAL}_{entity_key}",
                    "initial": config["default"],
                    "icon": config.get("icon"),
                },
            )

            # Verify entity association
            mock_associate.assert_called_once_with(
                mock_hass,
                f"input_boolean.{ENTITY_PREFIX_GLOBAL}_{entity_key}",
                mock_device,
            )

    @pytest.mark.asyncio
    async def test_create_input_select_via_service(
        self, mock_hass: HomeAssistant, mock_device: dr.DeviceEntry
    ) -> None:
        """Test creating input_select entity via service."""
        entity_key = "weather_warning_sensor"
        config = {
            "platform": "input_select",
            "name": "Weather Warning Sensor",
            "options": ["", "binary_sensor.weather_warning"],
            "default": "",
            "icon": "mdi:weather-lightning",
        }

        with patch(
            "custom_components.solar_window_system.global_config._associate_entity_with_device"
        ) as mock_associate:
            mock_associate.return_value = None

            await _create_input_select_via_service(
                mock_hass, entity_key, config, mock_device
            )

            # Verify service call without initial value since default is empty string
            mock_hass.services.async_call.assert_called_once_with(
                "input_select",
                "create",
                {
                    "name": f"{ENTITY_PREFIX_GLOBAL}_{entity_key}",
                    "options": config["options"],
                    "icon": config.get("icon"),
                    # No initial value since default is empty string
                },
            )

            # Verify entity association
            mock_associate.assert_called_once_with(
                mock_hass,
                f"input_select.{ENTITY_PREFIX_GLOBAL}_{entity_key}",
                mock_device,
            )

    @pytest.mark.asyncio
    async def test_create_input_select_via_service_no_default(
        self, mock_hass: HomeAssistant, mock_device: dr.DeviceEntry
    ) -> None:
        """Test creating input_select entity without default value."""
        entity_key = "weather_warning_sensor"
        config = {
            "platform": "input_select",
            "name": "Weather Warning Sensor",
            "options": ["", "binary_sensor.weather_warning"],
            "default": "invalid_default",  # Not in options
            "icon": "mdi:weather-lightning",
        }

        with patch(
            "custom_components.solar_window_system.global_config._associate_entity_with_device"
        ) as mock_associate:
            mock_associate.return_value = None

            await _create_input_select_via_service(
                mock_hass, entity_key, config, mock_device
            )

            # Verify service call without initial value
            mock_hass.services.async_call.assert_called_once_with(
                "input_select",
                "create",
                {
                    "name": f"{ENTITY_PREFIX_GLOBAL}_{entity_key}",
                    "options": config["options"],
                    "icon": config.get("icon"),
                    # No initial value since default is not in options
                },
            )

    @pytest.mark.asyncio
    async def test_associate_entity_with_device(
        self, mock_hass: HomeAssistant, mock_device: dr.DeviceEntry
    ) -> None:
        """Test associating entity with device."""
        entity_id = "input_number.test_entity"

        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_entry = Mock()
        mock_entity_registry.async_get.return_value = mock_entity_entry
        mock_entity_registry.async_update_entity = Mock()

        with patch(
            "custom_components.solar_window_system.global_config.er.async_get",
            return_value=mock_entity_registry,
        ):
            with patch.object(
                mock_hass, "async_block_till_done", new_callable=AsyncMock
            ):
                await _associate_entity_with_device(mock_hass, entity_id, mock_device)

                # Verify entity update
                mock_entity_registry.async_update_entity.assert_called_once_with(
                    entity_id, device_id=mock_device.id
                )

    @pytest.mark.asyncio
    async def test_associate_entity_with_device_not_found(
        self, mock_hass: HomeAssistant, mock_device: dr.DeviceEntry
    ) -> None:
        """Test associating entity with device when entity not found."""
        entity_id = "input_number.test_entity"

        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.async_get.return_value = None
        mock_entity_registry.async_update_entity = Mock()

        with patch(
            "custom_components.solar_window_system.global_config.er.async_get",
            return_value=mock_entity_registry,
        ):
            with patch.object(
                mock_hass, "async_block_till_done", new_callable=AsyncMock
            ):
                await _associate_entity_with_device(mock_hass, entity_id, mock_device)

                # Verify no entity update attempted
                mock_entity_registry.async_update_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_binary_sensor_entities(self, mock_hass: HomeAssistant) -> None:
        """Test getting binary sensor entities."""
        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "binary_sensor.test1": Mock(
                entity_id="binary_sensor.test1", disabled_by=None, hidden_by=None
            ),
            "binary_sensor.test2": Mock(
                entity_id="binary_sensor.test2", disabled_by=None, hidden_by=None
            ),
            "sensor.test3": Mock(
                entity_id="sensor.test3", disabled_by=None, hidden_by=None
            ),
        }

        with patch(
            "custom_components.solar_window_system.global_config.er.async_get",
            return_value=mock_entity_registry,
        ):
            result = await _get_binary_sensor_entities(mock_hass)

            expected = ["binary_sensor.test1", "binary_sensor.test2"]
            assert result == expected

    @pytest.mark.asyncio
    async def test_get_input_boolean_entities(self, mock_hass: HomeAssistant) -> None:
        """Test getting input boolean entities."""
        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "input_boolean.test1": Mock(
                entity_id="input_boolean.test1", disabled_by=None, hidden_by=None
            ),
            "input_boolean.test2": Mock(
                entity_id="input_boolean.test2", disabled_by=None, hidden_by=None
            ),
            "binary_sensor.test3": Mock(
                entity_id="binary_sensor.test3", disabled_by=None, hidden_by=None
            ),
        }

        with patch(
            "custom_components.solar_window_system.global_config.er.async_get",
            return_value=mock_entity_registry,
        ):
            result = await _get_input_boolean_entities(mock_hass)

            expected = ["input_boolean.test1", "input_boolean.test2"]
            assert result == expected

    @pytest.mark.asyncio
    async def test_get_temperature_sensor_entities(
        self, mock_hass: HomeAssistant
    ) -> None:
        """Test getting temperature sensor entities."""
        # Mock entity registry and states
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "sensor.temp1": Mock(
                entity_id="sensor.temp1", disabled_by=None, hidden_by=None
            ),
            "sensor.temp2": Mock(
                entity_id="sensor.temp2", disabled_by=None, hidden_by=None
            ),
            "sensor.humidity": Mock(
                entity_id="sensor.humidity", disabled_by=None, hidden_by=None
            ),
        }

        # Mock states
        mock_state_temp1 = Mock()
        mock_state_temp1.attributes = {"unit_of_measurement": "°C"}
        mock_state_temp2 = Mock()
        mock_state_temp2.attributes = {"unit_of_measurement": "°F"}
        mock_state_humidity = Mock()
        mock_state_humidity.attributes = {"unit_of_measurement": "%"}

        mock_hass.states.get.side_effect = lambda entity_id: {
            "sensor.temp1": mock_state_temp1,
            "sensor.temp2": mock_state_temp2,
            "sensor.humidity": mock_state_humidity,
        }.get(entity_id)

        with patch(
            "custom_components.solar_window_system.global_config.er.async_get",
            return_value=mock_entity_registry,
        ):
            result = await _get_temperature_sensor_entities(mock_hass)

            expected = ["sensor.temp1", "sensor.temp2"]
            assert result == expected


class TestGlobalConfigSensor:
    """Test GlobalConfigSensor class."""

    @pytest.fixture
    def mock_device(self) -> dr.DeviceEntry:
        """Create a mock device entry."""
        device = Mock(spec=dr.DeviceEntry)
        device.id = "test_device_id"
        device.identifiers = {(DOMAIN, "global_config")}
        device.name = "Test Global Config Device"
        device.manufacturer = "Test Manufacturer"
        device.model = "Test Model"
        return device

    @pytest.fixture
    def mock_hass(self) -> HomeAssistant:
        """Create a mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        hass.data = {}
        return hass

    def test_global_config_sensor_init(self, mock_device: dr.DeviceEntry) -> None:
        """Test GlobalConfigSensor initialization."""
        entity_key = "total_power"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        sensor = GlobalConfigSensor(entity_key, config, mock_device)

        assert sensor._entity_key == entity_key
        assert sensor._config == config
        assert sensor._device == mock_device
        assert sensor._attr_unique_id == f"{ENTITY_PREFIX_GLOBAL}_{entity_key}"
        assert (
            sensor._attr_suggested_object_id == f"{ENTITY_PREFIX_GLOBAL}_{entity_key}"
        )
        assert sensor._attr_name == f"SWS_GLOBAL {config['name']}"
        assert sensor._attr_has_entity_name is False
        assert sensor._attr_unit_of_measurement == config.get("unit")
        assert sensor._attr_icon == config.get("icon")
        assert sensor._state == config["default"]
        assert sensor._attr_device_info == {
            "identifiers": mock_device.identifiers,
            "name": mock_device.name,
            "manufacturer": mock_device.manufacturer,
            "model": mock_device.model,
        }

    def test_global_config_sensor_state_property(
        self, mock_device: dr.DeviceEntry, mock_hass: HomeAssistant
    ) -> None:
        """Test GlobalConfigSensor state property."""
        entity_key = "total_power"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        sensor = GlobalConfigSensor(entity_key, config, mock_device)
        sensor.hass = mock_hass  # Set hass for testing

        # Test non-aggregated sensor
        assert sensor.state == config["default"]

        # Test aggregated sensors
        for key in [
            "total_power",
            "total_power_direct",
            "total_power_diffuse",
            "window_with_shading",
        ]:
            sensor._entity_key = key
            sensor._state = 0  # Reset state
            # Should return _get_aggregated_value result, which is 0 for empty data
            assert sensor.state == 0

    def test_global_config_sensor_get_aggregated_value(
        self, mock_device: dr.DeviceEntry, mock_hass: HomeAssistant
    ) -> None:
        """Test GlobalConfigSensor _get_aggregated_value method."""
        entity_key = "total_power"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        sensor = GlobalConfigSensor(entity_key, config, mock_device)
        sensor.hass = mock_hass

        # Mock empty domain data
        mock_hass.data = {DOMAIN: {}}

        # Test all aggregated sensor types
        test_cases = [
            ("total_power", 0.0),
            ("total_power_direct", 0.0),
            ("total_power_diffuse", 0.0),
            ("window_with_shading", 0),
        ]

        for key, expected in test_cases:
            sensor._entity_key = key
            result = sensor._get_aggregated_value()
            assert result == expected

    def test_global_config_sensor_get_aggregated_value_with_data(
        self, mock_device: dr.DeviceEntry, mock_hass: HomeAssistant
    ) -> None:
        """Test GlobalConfigSensor _get_aggregated_value with actual data."""
        entity_key = "total_power"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        sensor = GlobalConfigSensor(entity_key, config, mock_device)
        sensor.hass = mock_hass

        # Mock coordinator with data
        mock_coordinator = Mock()
        mock_coordinator.data = {
            "summary": {
                "total_power": 100.5,
                "total_power_direct": 80.2,
                "total_power_diffuse": 20.3,
                "shading_count": 3,
            }
        }

        mock_hass.data = {
            DOMAIN: {
                "entry1": {"coordinator": mock_coordinator},
                "entry2": {"coordinator": mock_coordinator},
            }
        }

        # Test aggregated values
        sensor._entity_key = "total_power"
        assert sensor._get_aggregated_value() == 201.0  # 100.5 * 2

        sensor._entity_key = "total_power_direct"
        assert sensor._get_aggregated_value() == 160.4  # 80.2 * 2

        sensor._entity_key = "total_power_diffuse"
        assert sensor._get_aggregated_value() == 40.6  # 20.3 * 2

        sensor._entity_key = "window_with_shading"
        assert sensor._get_aggregated_value() == 6  # 3 * 2

    def test_global_config_sensor_async_update_state(
        self, mock_device: dr.DeviceEntry
    ) -> None:
        """Test GlobalConfigSensor async_update_state method."""
        entity_key = "total_power"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        sensor = GlobalConfigSensor(entity_key, config, mock_device)

        # Mock async_write_ha_state
        sensor.async_write_ha_state = Mock()

        # Test state update
        sensor.async_update_state(123.45)

        assert sensor._state == 123.45
        sensor.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_global_config_sensor_async_added_to_hass(
        self, mock_device: dr.DeviceEntry, mock_hass: HomeAssistant
    ) -> None:
        """Test GlobalConfigSensor async_added_to_hass method."""
        entity_key = "total_power"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        sensor = GlobalConfigSensor(entity_key, config, mock_device)
        sensor.hass = mock_hass

        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_entry = Mock()
        mock_entity_entry.original_name = "Old Name"
        mock_entity_registry.entities = {sensor.entity_id: mock_entity_entry}
        mock_entity_registry.async_update_entity = Mock()

        # Mock restore state
        mock_restored_state = Mock()
        mock_restored_state.state = "123.45"
        sensor.async_get_last_state = AsyncMock(return_value=mock_restored_state)

        with patch(
            "custom_components.solar_window_system.global_config.er.async_get",
            return_value=mock_entity_registry,
        ):
            await sensor.async_added_to_hass()

            # Verify state restoration
            assert sensor._state == 123.45

            # Verify friendly name update
            mock_entity_registry.async_update_entity.assert_called_once_with(
                sensor.entity_id, name=config.get("name")
            )

    @pytest.mark.asyncio
    async def test_global_config_sensor_async_added_to_hass_no_restore(
        self, mock_device: dr.DeviceEntry, mock_hass: HomeAssistant
    ) -> None:
        """Test GlobalConfigSensor async_added_to_hass with no restore state."""
        entity_key = "total_power"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        sensor = GlobalConfigSensor(entity_key, config, mock_device)
        sensor.hass = mock_hass

        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_entry = Mock()
        mock_entity_entry.original_name = "Old Name"
        mock_entity_registry.entities = {sensor.entity_id: mock_entity_entry}
        mock_entity_registry.async_update_entity = Mock()

        # Mock no restore state
        sensor.async_get_last_state = AsyncMock(return_value=None)

        with patch(
            "custom_components.solar_window_system.global_config.er.async_get",
            return_value=mock_entity_registry,
        ):
            await sensor.async_added_to_hass()

            # Verify state remains default
            assert sensor._state == config["default"]

    def test_global_config_sensor_setup_coordinator_listeners(
        self, mock_device: dr.DeviceEntry, mock_hass: HomeAssistant
    ) -> None:
        """Test GlobalConfigSensor _setup_coordinator_listeners method."""
        entity_key = "total_power"
        config = GLOBAL_CONFIG_ENTITIES[entity_key]

        sensor = GlobalConfigSensor(entity_key, config, mock_device)
        sensor.hass = mock_hass

        # Mock coordinators
        mock_coordinator1 = Mock()
        mock_coordinator2 = Mock()

        mock_hass.data = {
            DOMAIN: {
                "entry1": {"coordinator": mock_coordinator1},
                "entry2": {"coordinator": mock_coordinator2},
            }
        }

        # Mock async_write_ha_state
        sensor.async_write_ha_state = Mock()

        # Call setup method
        sensor._setup_coordinator_listeners()

        # Verify listeners were added to both coordinators
        mock_coordinator1.async_add_listener.assert_called_once()
        mock_coordinator2.async_add_listener.assert_called_once()

        # Test callback function
        callback_func = mock_coordinator1.async_add_listener.call_args[0][0]
        callback_func()

        # Verify async_write_ha_state was called
        sensor.async_write_ha_state.assert_called_once()
