"""Test the config flow for Room Ventilation Advisor."""

# pyright: reportTypedDictNotRequiredAccess=false,reportOptionalSubscript=false,reportOperatorIssue=false,reportArgumentType=false,reportAttributeAccessIssue=false

import os
from unittest.mock import AsyncMock

import voluptuous_serialize as vserialize
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.room_ventilation_advisor import DOMAIN
from custom_components.room_ventilation_advisor.config_flow import (
    RoomVentilationAdvisorConfigFlow,
    RoomVentilationAdvisorOptionsFlow,
)
from custom_components.room_ventilation_advisor.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_CO2_SENSOR,
    CONF_CO2_THRESHOLDS,
    CONF_ENABLED,
    CONF_HUMIDITY_SENSOR,
    CONF_HUMIDITY_THRESHOLDS,
    CONF_OUTDOOR_HUMIDITY_SENSOR,
    CONF_OUTDOOR_TEMP_SENSOR,
    CONF_ROOM_NAME,
    CONF_ROOM_TYPE,
    CONF_ROOMS,
    CONF_SCAN_INTERVAL,
    CONF_SCORE_WEIGHTS,
    CONF_TEMP_SENSOR,
    CONF_TEMPERATURE_THRESHOLDS,
    CONF_WIND_SENSOR,
    CONF_WIND_THRESHOLDS,
)


class TestRoomVentilationAdvisorConfigFlow:
    """Test the config flow."""

    async def test_config_flow_user_step(self, hass: HomeAssistant) -> None:
        """Test the user step of the config flow."""
        # Create a config flow instance
        flow = RoomVentilationAdvisorConfigFlow()
        flow.hass = hass

        result = await flow.async_step_user()

        assert result is not None
        assert "type" in result
        assert "step_id" in result
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    async def test_config_flow_user_step_valid_data(self, hass: HomeAssistant) -> None:
        """Test the user step with valid data."""
        flow = RoomVentilationAdvisorConfigFlow()
        flow.hass = hass

        user_input = {
            "name": "Test Advisor",
            "outdoor_temp_sensor": "sensor.outdoor_temperature",
            "outdoor_humidity_sensor": "sensor.outdoor_humidity",
            "wind_sensor": "sensor.wind_speed",
            "scan_interval": 300,
        }

        result = await flow.async_step_user(user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "room_setup"

    async def test_config_flow_room_setup_step(self, hass: HomeAssistant) -> None:
        """Test the room setup step."""
        flow = RoomVentilationAdvisorConfigFlow()
        flow.hass = hass

        # First complete the user step
        user_input = {
            "name": "Test Advisor",
            "outdoor_temp_sensor": "sensor.outdoor_temperature",
            "outdoor_humidity_sensor": "sensor.outdoor_humidity",
            "wind_sensor": "sensor.wind_speed",
            "scan_interval": 300,
        }

        await flow.async_step_user(user_input)

        # Now test the room setup step
        result = await flow.async_step_room_setup()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "room_setup"

        # Test with a single room
        room_input = {
            "room_name": "Living Room",
            "temp_sensor": "sensor.living_room_temperature",
            "humidity_sensor": "sensor.living_room_humidity",
            "room_type": "living_room",
            "co2_sensor": "sensor.living_room_co2",
            "enabled": True,
            "add_another_room": False,
        }

        result = await flow.async_step_room_setup(room_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["name"] == "Test Advisor"

    async def test_config_flow_with_rooms(self, hass: HomeAssistant) -> None:
        """Test the config flow with room configuration."""
        flow = RoomVentilationAdvisorConfigFlow()
        flow.hass = hass

        # Complete user step
        user_input = {
            "name": "Test Advisor",
            "outdoor_temp_sensor": "sensor.outdoor_temperature",
            "outdoor_humidity_sensor": "sensor.outdoor_humidity",
            "wind_sensor": "sensor.wind_speed",
            "scan_interval": 300,
        }

        await flow.async_step_user(user_input)

        # Configure a room
        room_input = {
            "room_name": "Living Room",
            "temp_sensor": "sensor.living_room_temperature",
            "humidity_sensor": "sensor.living_room_humidity",
            "room_type": "living_room",
            "co2_sensor": "sensor.living_room_co2",
            "enabled": True,
            "add_another_room": False,
        }

        result = await flow.async_step_room_setup(room_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert len(result["data"][CONF_ROOMS]) == 1
        assert result["data"][CONF_ROOMS]["Living Room"]["room_name"] == "Living Room"


class TestRoomVentilationAdvisorOptionsFlow:
    """Test the options flow."""

    async def test_options_flow_init(self, hass: HomeAssistant) -> None:
        """Test options flow initialization."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        result = await flow.async_step_init()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_flow_basic_settings(self, hass: HomeAssistant) -> None:
        """Test basic settings configuration."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to basic settings
        result = await flow.async_step_init({"configure_basic": True})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "basic"

        # Configure basic settings
        basic_input = {
            CONF_SCAN_INTERVAL: 600,
            "enable_wind_factor": False,
        }

        result = await flow.async_step_basic(basic_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_SCAN_INTERVAL] == 600

    async def test_options_flow_basic_sensor_configuration(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test basic sensor configuration in options flow."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {
                    "Living Room": {
                        "temp_sensor": "sensor.living_temp",
                        "humidity_sensor": "sensor.living_humidity",
                        "co2_sensor": "sensor.living_co2",
                        "room_type": "living_room",
                        "enabled": True,
                    },
                },
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to basic settings
        result = await flow.async_step_init({"configure_basic": True})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "basic"

        # Configure all basic settings (only global sensors)
        basic_input = {
            CONF_OUTDOOR_TEMP_SENSOR: "sensor.new_outdoor_temp",
            CONF_OUTDOOR_HUMIDITY_SENSOR: "sensor.new_outdoor_humidity",
            CONF_WIND_SENSOR: "sensor.new_wind_speed",
            CONF_SCAN_INTERVAL: 600,
            "enable_wind_factor": False,
        }

        result = await flow.async_step_basic(basic_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        # Check outdoor sensors
        assert result["data"][CONF_OUTDOOR_TEMP_SENSOR] == "sensor.new_outdoor_temp"
        assert (
            result["data"][CONF_OUTDOOR_HUMIDITY_SENSOR]
            == "sensor.new_outdoor_humidity"
        )
        assert result["data"][CONF_WIND_SENSOR] == "sensor.new_wind_speed"
        assert result["data"][CONF_SCAN_INTERVAL] == 600
        assert result["data"]["enable_wind_factor"] is False
        # Room settings should not be in basic options
        assert "room_settings" not in result["data"]

    async def test_options_flow_advanced_settings(self, hass: HomeAssistant) -> None:
        """Test advanced settings configuration."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to advanced settings
        result = await flow.async_step_init({"configure_advanced": True})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "advanced"

    async def test_options_flow_advanced_schema_serializable(
        self,
        hass: HomeAssistant,
    ) -> None:
        """
        Ensure advanced options schema can be serialized to JSON.

        The UI serializes the voluptuous schema using voluptuous_serialize.convert
        when serving the form. A nested vol.Schema used as a mapping value can
        produce structures that break conversion; this test ensures conversion
        succeeds.
        """
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to advanced settings and get the schema
        result = await flow.async_step_init({"configure_advanced": True})
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "advanced"

        # Try to serialize the schema the same way the UI does
        schema = result["data_schema"]
        # should not raise
        vserialize.convert(schema)

    async def test_options_flow_temperature_thresholds(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test updating temperature thresholds."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to advanced settings
        await flow.async_step_init({"configure_advanced": True})

        # Update temperature thresholds
        advanced_input = {
            CONF_ADVANCED_SETTINGS: {
                CONF_TEMPERATURE_THRESHOLDS: {
                    "winter_good": 4.0,
                    "winter_moderate": 2.0,
                    "summer_good": 5.0,
                    "summer_moderate": 3.0,
                    "default_good": 4.5,
                    "default_moderate": 2.5,
                },
            },
        }

        result = await flow.async_step_advanced(advanced_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        temp_thresholds = result["data"][CONF_ADVANCED_SETTINGS][
            CONF_TEMPERATURE_THRESHOLDS
        ]
        assert temp_thresholds["winter_good"] == 4.0
        assert temp_thresholds["winter_moderate"] == 2.0

    async def test_options_flow_humidity_thresholds(self, hass: HomeAssistant) -> None:
        """Test updating humidity thresholds."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to advanced settings
        await flow.async_step_init({"configure_advanced": True})

        # Update humidity thresholds
        advanced_input = {
            CONF_ADVANCED_SETTINGS: {
                CONF_HUMIDITY_THRESHOLDS: {
                    "good": 3.0,
                    "moderate": 1.5,
                },
            },
        }

        result = await flow.async_step_advanced(advanced_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        humidity_thresholds = result["data"][CONF_ADVANCED_SETTINGS][
            CONF_HUMIDITY_THRESHOLDS
        ]
        assert humidity_thresholds["good"] == 3.0
        assert humidity_thresholds["moderate"] == 1.5

    async def test_options_flow_co2_thresholds(self, hass: HomeAssistant) -> None:
        """Test updating CO2 thresholds."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to advanced settings
        await flow.async_step_init({"configure_advanced": True})

        # Update CO2 thresholds
        advanced_input = {
            CONF_ADVANCED_SETTINGS: {
                CONF_CO2_THRESHOLDS: {
                    "very_poor": 1600,
                    "poor": 1400,
                    "moderate": 900,
                },
            },
        }

        result = await flow.async_step_advanced(advanced_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        co2_thresholds = result["data"][CONF_ADVANCED_SETTINGS][CONF_CO2_THRESHOLDS]
        assert co2_thresholds["very_poor"] == 1600
        assert co2_thresholds["poor"] == 1400
        assert co2_thresholds["moderate"] == 900

    async def test_options_flow_wind_thresholds(self, hass: HomeAssistant) -> None:
        """Test updating wind thresholds."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to advanced settings
        await flow.async_step_init({"configure_advanced": True})

        # Update wind thresholds
        advanced_input = {
            CONF_ADVANCED_SETTINGS: {
                CONF_WIND_THRESHOLDS: {
                    "no_effect": 15.0,
                    "moderate_effect": 25.0,
                },
            },
        }

        result = await flow.async_step_advanced(advanced_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        wind_thresholds = result["data"][CONF_ADVANCED_SETTINGS][CONF_WIND_THRESHOLDS]
        assert wind_thresholds["no_effect"] == 15.0
        assert wind_thresholds["moderate_effect"] == 25.0

    async def test_options_flow_score_weights(self, hass: HomeAssistant) -> None:
        """Test updating score weights."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to advanced settings
        await flow.async_step_init({"configure_advanced": True})

        # Update score weights
        advanced_input = {
            CONF_ADVANCED_SETTINGS: {
                CONF_SCORE_WEIGHTS: {
                    "temperature": 0.4,
                    "humidity": 0.3,
                    "co2": 0.2,
                    "time": 0.1,
                },
            },
        }

        result = await flow.async_step_advanced(advanced_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        score_weights = result["data"][CONF_ADVANCED_SETTINGS][CONF_SCORE_WEIGHTS]
        assert score_weights["temperature"] == 0.4
        assert score_weights["humidity"] == 0.3
        assert score_weights["co2"] == 0.2
        assert score_weights["time"] == 0.1

    async def test_options_flow_with_existing_settings(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test options flow with existing advanced settings."""
        existing_advanced = {
            CONF_TEMPERATURE_THRESHOLDS: {
                "winter_good": 3.5,
                "winter_moderate": 1.5,
            },
        }

        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={CONF_ADVANCED_SETTINGS: existing_advanced},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        result = await flow.async_step_init()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_flow_partial_update(self, hass: HomeAssistant) -> None:
        """Test partial update of advanced settings."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={
                CONF_ADVANCED_SETTINGS: {
                    CONF_TEMPERATURE_THRESHOLDS: {
                        "winter_good": 2.0,
                    },
                },
            },
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to advanced settings
        await flow.async_step_init({"configure_advanced": True})

        # Update only humidity thresholds, keep temperature
        advanced_input = {
            CONF_ADVANCED_SETTINGS: {
                CONF_HUMIDITY_THRESHOLDS: {
                    "good": 2.0,
                    "moderate": 0.5,
                },
            },
        }

        result = await flow.async_step_advanced(advanced_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        # Check that temperature threshold is preserved
        assert (
            result["data"][CONF_ADVANCED_SETTINGS][CONF_TEMPERATURE_THRESHOLDS][
                "winter_good"
            ]
            == 2.0
        )
        # Check that humidity thresholds are updated
        assert (
            result["data"][CONF_ADVANCED_SETTINGS][CONF_HUMIDITY_THRESHOLDS]["good"]
            == 2.0
        )

    async def test_options_flow_room_management_menu(self, hass: HomeAssistant) -> None:
        """Test room management menu navigation."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {
                    "Living Room": {
                        CONF_ROOM_NAME: "Living Room",
                        CONF_TEMP_SENSOR: "sensor.living_temp",
                        CONF_HUMIDITY_SENSOR: "sensor.living_humidity",
                        CONF_ROOM_TYPE: "living_room",
                        CONF_CO2_SENSOR: "sensor.living_co2",
                        CONF_ENABLED: True,
                    },
                },
            },
            options={},
        )

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to room management
        result = await flow.async_step_init({"configure_rooms": True})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "rooms"

    async def test_options_flow_add_room(self, hass: HomeAssistant) -> None:
        """Test adding a new room through options flow."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {},
            },
            options={},
        )
        config_entry.add_to_hass(hass)

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Mock the async_reload method to verify it's called
        mock_reload = AsyncMock()
        flow.hass.config_entries.async_reload = mock_reload

        # Mock the environment to simulate production (not testing)

        original_env = os.environ.get("PYTEST_CURRENT_TEST")
        os.environ.pop("PYTEST_CURRENT_TEST", None)

        # Navigate to rooms step
        await flow.async_step_init({"configure_rooms": True})
        result = await flow.async_step_rooms({"add_room": True})

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "add_room"

        # Add a room
        room_data = {
            CONF_ROOM_NAME: "Kitchen",
            CONF_TEMP_SENSOR: "sensor.kitchen_temp",
            CONF_HUMIDITY_SENSOR: "sensor.kitchen_humidity",
            CONF_ROOM_TYPE: "kitchen",
            CONF_CO2_SENSOR: "sensor.kitchen_co2",
            CONF_ENABLED: True,
        }

        result = await flow.async_step_add_room(room_data)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {}

        # Verify room was added to config entry
        updated_data = config_entry.data
        assert CONF_ROOMS in updated_data
        assert "Kitchen" in updated_data[CONF_ROOMS]

        # Verify that async_reload was called to update sensors
        mock_reload.assert_called_once_with(config_entry.entry_id)

        # Restore the environment variable
        if original_env is not None:
            os.environ["PYTEST_CURRENT_TEST"] = original_env
        assert updated_data[CONF_ROOMS]["Kitchen"][CONF_ROOM_NAME] == "Kitchen"
        assert (
            updated_data[CONF_ROOMS]["Kitchen"][CONF_TEMP_SENSOR]
            == "sensor.kitchen_temp"
        )

    async def test_options_flow_add_room_duplicate_name(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test adding a room with duplicate name."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {
                    "Living Room": {
                        CONF_ROOM_NAME: "Living Room",
                        CONF_TEMP_SENSOR: "sensor.living_temp",
                        CONF_HUMIDITY_SENSOR: "sensor.living_humidity",
                        CONF_ROOM_TYPE: "living_room",
                    },
                },
            },
            options={},
        )
        config_entry.add_to_hass(hass)

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to add room
        await flow.async_step_init({"configure_rooms": True})
        await flow.async_step_rooms({"add_room": True})

        # Try to add room with duplicate name
        room_data = {
            CONF_ROOM_NAME: "Living Room",  # Duplicate name
            CONF_TEMP_SENSOR: "sensor.kitchen_temp",
            CONF_HUMIDITY_SENSOR: "sensor.kitchen_humidity",
            CONF_ROOM_TYPE: "kitchen",
        }

        result = await flow.async_step_add_room(room_data)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "add_room"
        assert "errors" in result
        assert "room_name" in result["errors"]

    async def test_options_flow_edit_room(self, hass: HomeAssistant) -> None:
        """Test editing an existing room through options flow."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {
                    "Living Room": {
                        CONF_ROOM_NAME: "Living Room",
                        CONF_TEMP_SENSOR: "sensor.living_temp",
                        CONF_HUMIDITY_SENSOR: "sensor.living_humidity",
                        CONF_ROOM_TYPE: "living_room",
                        CONF_CO2_SENSOR: "sensor.living_co2",
                        CONF_ENABLED: True,
                    },
                },
            },
            options={},
        )
        config_entry.add_to_hass(hass)

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to edit room
        await flow.async_step_init({"configure_rooms": True})
        result = await flow.async_step_rooms(
            {"edit_room": True, "room_to_edit": "Living Room"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "edit_room"

        # Edit the room
        updated_room_data = {
            CONF_ROOM_NAME: "Living Room",
            CONF_TEMP_SENSOR: "sensor.living_temp_new",
            CONF_HUMIDITY_SENSOR: "sensor.living_humidity",
            CONF_ROOM_TYPE: "living_room",
            CONF_CO2_SENSOR: "sensor.living_co2_new",
            CONF_ENABLED: False,
        }

        result = await flow.async_step_edit_room(updated_room_data)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"] == {}

        # Verify room was updated
        updated_data = config_entry.data
        assert (
            updated_data[CONF_ROOMS]["Living Room"][CONF_TEMP_SENSOR]
            == "sensor.living_temp_new"
        )
        assert (
            updated_data[CONF_ROOMS]["Living Room"][CONF_CO2_SENSOR]
            == "sensor.living_co2_new"
        )
        assert updated_data[CONF_ROOMS]["Living Room"][CONF_ENABLED] is False

    async def test_options_flow_remove_room(self, hass: HomeAssistant) -> None:
        """Test removing a room through options flow."""
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Advisor",
                "outdoor_temp_sensor": "sensor.outdoor_temp",
                "outdoor_humidity_sensor": "sensor.outdoor_humidity",
                "wind_sensor": "sensor.wind_speed",
                "scan_interval": 300,
                CONF_ROOMS: {
                    "Living Room": {
                        CONF_ROOM_NAME: "Living Room",
                        CONF_TEMP_SENSOR: "sensor.living_temp",
                        CONF_HUMIDITY_SENSOR: "sensor.living_humidity",
                        CONF_ROOM_TYPE: "living_room",
                    },
                    "Kitchen": {
                        CONF_ROOM_NAME: "Kitchen",
                        CONF_TEMP_SENSOR: "sensor.kitchen_temp",
                        CONF_HUMIDITY_SENSOR: "sensor.kitchen_humidity",
                        CONF_ROOM_TYPE: "kitchen",
                    },
                },
            },
            options={},
        )
        config_entry.add_to_hass(hass)

        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to remove room
        await flow.async_step_init({"configure_rooms": True})
        result = await flow.async_step_rooms(
            {"remove_room": True, "room_to_remove": "Living Room"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "remove_room"

        # Confirm removal
        result = await flow.async_step_remove_room({"confirm_remove": True})

        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify room was removed
        updated_data = config_entry.data
        assert "Living Room" not in updated_data[CONF_ROOMS]
        assert "Kitchen" in updated_data[CONF_ROOMS]  # Other room should remain

    async def test_options_flow_co2_sensor_schema_validation(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test that CO2 sensor field handles empty strings correctly."""
        # Create a mock config entry
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ROOMS: {
                    "Test Room": {
                        CONF_ROOM_TYPE: "living_room",
                        CONF_HUMIDITY_SENSOR: "sensor.humidity",
                        CONF_TEMP_SENSOR: "sensor.temperature",
                        CONF_CO2_SENSOR: None,  # Initially None
                        CONF_ENABLED: True,
                    },
                },
            },
        )

        # Create options flow
        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to room configuration
        await flow.async_step_init({"configure_rooms": True})
        await flow.async_step_rooms({"configure_room": "Test Room"})

        # Test schema validation with empty CO2 sensor string
        current_config = config_entry.data[CONF_ROOMS]["Test Room"]
        schema = flow._get_room_schema(current_config)

        # This should not raise an exception with None (empty selection)
        test_data = {
            CONF_ROOM_NAME: "Test Room",
            CONF_ROOM_TYPE: "living_room",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            CONF_TEMP_SENSOR: "sensor.temperature",
            CONF_CO2_SENSOR: None,  # None - should be handled gracefully
            CONF_ENABLED: True,
        }

        # Validate the data against the schema
        validated_data = schema(test_data)

        # None should remain None
        assert validated_data[CONF_CO2_SENSOR] is None

    async def test_options_flow_remove_room_placeholder_and_functionality(
        self,
        hass: HomeAssistant,
    ) -> None:
        """Test remove room placeholder replacement and functionality work correctly."""
        # Create a mock config entry with a room
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ROOMS: {
                    "Test Room": {
                        CONF_ROOM_TYPE: "living_room",
                        CONF_HUMIDITY_SENSOR: "sensor.humidity",
                        CONF_TEMP_SENSOR: "sensor.temperature",
                        CONF_ENABLED: True,
                    },
                },
            },
        )

        # Add the config entry to hass
        config_entry.add_to_hass(hass)

        # Create options flow
        flow = RoomVentilationAdvisorOptionsFlow(config_entry)
        flow.hass = hass

        # Navigate to remove room
        await flow.async_step_init({"configure_rooms": True})
        result = await flow.async_step_rooms(
            {"remove_room": True, "room_to_remove": "Test Room"},
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "remove_room"

        # Check that placeholder is properly replaced
        assert "description_placeholders" in result
        assert result["description_placeholders"]["room_name"] == "Test Room"

        # Confirm removal - this should actually remove the room
        result = await flow.async_step_remove_room({"confirm_remove": True})

        # Should save configuration after successful removal
        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify room was actually removed from config
        updated_data = config_entry.data
        assert "Test Room" not in updated_data[CONF_ROOMS]
