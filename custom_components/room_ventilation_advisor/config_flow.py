"""Config flow for Room Ventilation Advisor integration."""

import contextlib
import os
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from custom_components.room_ventilation_advisor.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_CO2_SENSOR,
    CONF_CO2_THRESHOLDS,
    CONF_ENABLED,
    CONF_HUMIDITY_SENSOR,
    CONF_HUMIDITY_THRESHOLDS,
    CONF_NAME,
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
    DEFAULT_CO2_THRESHOLDS,
    DEFAULT_HUMIDITY_THRESHOLDS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SCORE_WEIGHTS,
    DEFAULT_TEMPERATURE_THRESHOLDS,
    DEFAULT_WIND_THRESHOLDS,
    DOMAIN,
    ROOM_TYPES,
)

MAX_ROOMS = 20


class RoomVentilationAdvisorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for Room Ventilation Advisor."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._base_config: dict[str, Any] = {}
        self._rooms: dict[str, dict[str, Any]] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle initial step - base configuration."""
        # Check if already configured
        existing_entries = self.hass.config_entries.async_entries(DOMAIN)
        if existing_entries:
            return self.async_abort(reason="already_configured")
        """Handle initial step - base configuration."""
        errors = {}

        if user_input is not None:
            self._base_config = user_input
            return await self.async_step_room_setup()

        # Get available sensors for selection
        sensor_entities = []
        for entity_id in self.hass.states.async_entity_ids("sensor"):
            state = self.hass.states.get(entity_id)
            if state and state.attributes.get("device_class") in [
                "temperature",
                "humidity",
            ]:
                sensor_entities.append(entity_id)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default="Room Ventilation Advisor"): str,
                vol.Required(CONF_OUTDOOR_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="temperature"
                    )
                ),
                vol.Required(CONF_OUTDOOR_HUMIDITY_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="humidity"
                    )
                ),
                vol.Required(CONF_WIND_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60, max=3600, unit_of_measurement="seconds"
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_room_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle room setup."""
        if user_input is not None:
            room_name = user_input[CONF_ROOM_NAME]
            self._rooms[room_name] = {
                CONF_ROOM_NAME: room_name,
                CONF_TEMP_SENSOR: user_input[CONF_TEMP_SENSOR],
                CONF_HUMIDITY_SENSOR: user_input[CONF_HUMIDITY_SENSOR],
                CONF_ROOM_TYPE: user_input[CONF_ROOM_TYPE],
                CONF_CO2_SENSOR: user_input.get(CONF_CO2_SENSOR),
                CONF_ENABLED: user_input.get(CONF_ENABLED, True),
            }

            if user_input.get("add_another_room", False):
                return await self.async_step_room_setup()

            return await self._async_create_entry()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ROOM_NAME): str,
                vol.Required(CONF_TEMP_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="temperature"
                    )
                ),
                vol.Required(CONF_HUMIDITY_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="humidity"
                    )
                ),
                vol.Required(CONF_ROOM_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=ROOM_TYPES)
                ),
                vol.Optional(CONF_CO2_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(CONF_ENABLED, default=True): bool,
                vol.Optional(
                    "add_another_room", default=len(self._rooms) < MAX_ROOMS
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="room_setup",
            data_schema=data_schema,
            description_placeholders={"rooms_configured": str(len(self._rooms))},
        )

    async def _async_create_entry(self) -> config_entries.ConfigFlowResult:
        """Create the config entry."""
        config_data = {
            **self._base_config,
            CONF_ROOMS: self._rooms,
        }

        return self.async_create_entry(
            title=self._base_config[CONF_NAME], data=config_data
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow."""
        return RoomVentilationAdvisorOptionsFlow(config_entry)


class RoomVentilationAdvisorOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Room Ventilation Advisor."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry
        # Track currently selected room for edit/remove steps
        self._room_to_edit: str | None = None
        self._room_to_remove: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            if user_input.get("configure_basic"):
                return await self.async_step_basic()
            if user_input.get("configure_rooms"):
                return await self.async_step_rooms()
            if user_input.get("configure_advanced"):
                return await self.async_step_advanced()
            return self.async_create_entry(title="", data=user_input)

        # Show menu with basic, rooms, and advanced options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional("configure_basic", default=False): bool,
                    vol.Optional("configure_rooms", default=False): bool,
                    vol.Optional("configure_advanced", default=False): bool,
                }
            ),
            description_placeholders={
                "basic_desc": "Configure scan interval, wind factor, and room settings",
                "rooms_desc": "Add, remove, or modify room configurations",
                "advanced_desc": "Configure advanced ventilation "
                "calculation parameters",
            },
        )

    async def async_step_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle basic options - only global settings."""
        if user_input is not None:
            # Process basic settings only
            options_data = {}

            # Update basic sensor configuration
            if CONF_OUTDOOR_TEMP_SENSOR in user_input:
                options_data[CONF_OUTDOOR_TEMP_SENSOR] = user_input[
                    CONF_OUTDOOR_TEMP_SENSOR
                ]
            if CONF_OUTDOOR_HUMIDITY_SENSOR in user_input:
                options_data[CONF_OUTDOOR_HUMIDITY_SENSOR] = user_input[
                    CONF_OUTDOOR_HUMIDITY_SENSOR
                ]
            if CONF_WIND_SENSOR in user_input:
                options_data[CONF_WIND_SENSOR] = user_input[CONF_WIND_SENSOR]
            if CONF_SCAN_INTERVAL in user_input:
                options_data[CONF_SCAN_INTERVAL] = user_input[CONF_SCAN_INTERVAL]
            if "enable_wind_factor" in user_input:
                options_data["enable_wind_factor"] = user_input["enable_wind_factor"]

            return self.async_create_entry(title="", data=options_data)

        # Build the schema for basic settings (only global sensors and settings)
        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_OUTDOOR_TEMP_SENSOR,
                    default=self._config_entry.data.get(CONF_OUTDOOR_TEMP_SENSOR),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="temperature"
                    )
                ),
                vol.Optional(
                    CONF_OUTDOOR_HUMIDITY_SENSOR,
                    default=self._config_entry.data.get(CONF_OUTDOOR_HUMIDITY_SENSOR),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="humidity"
                    )
                ),
                vol.Optional(
                    CONF_WIND_SENSOR,
                    default=self._config_entry.data.get(CONF_WIND_SENSOR),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self._config_entry.data.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=60, max=3600, unit_of_measurement="seconds"
                    )
                ),
                vol.Optional("enable_wind_factor", default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="basic",
            data_schema=options_schema,
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle advanced ventilation settings."""
        if user_input is not None:
            # Merge advanced settings with existing options
            current_options = dict(self._config_entry.options)

            # Accept either nested submission under CONF_ADVANCED_SETTINGS
            # or a flat set of advanced keys produced by the form.
            if CONF_ADVANCED_SETTINGS in user_input and isinstance(
                user_input[CONF_ADVANCED_SETTINGS], dict
            ):
                advanced_settings = user_input[CONF_ADVANCED_SETTINGS]
            else:
                # Build nested advanced_settings from flat keys
                advanced_settings = {}

                # Temperature thresholds
                temp = {}
                if "temperature_winter_good" in user_input:
                    temp["winter_good"] = user_input["temperature_winter_good"]
                if "temperature_winter_moderate" in user_input:
                    temp["winter_moderate"] = user_input["temperature_winter_moderate"]
                if "temperature_summer_good" in user_input:
                    temp["summer_good"] = user_input["temperature_summer_good"]
                if "temperature_summer_moderate" in user_input:
                    temp["summer_moderate"] = user_input["temperature_summer_moderate"]
                if "temperature_default_good" in user_input:
                    temp["default_good"] = user_input["temperature_default_good"]
                if "temperature_default_moderate" in user_input:
                    temp["default_moderate"] = user_input[
                        "temperature_default_moderate"
                    ]
                if temp:
                    advanced_settings[CONF_TEMPERATURE_THRESHOLDS] = temp

                # Humidity
                hum = {}
                if "humidity_good" in user_input:
                    hum["good"] = user_input["humidity_good"]
                if "humidity_moderate" in user_input:
                    hum["moderate"] = user_input["humidity_moderate"]
                if hum:
                    advanced_settings[CONF_HUMIDITY_THRESHOLDS] = hum

                # CO2
                co2 = {}
                if "co2_very_poor" in user_input:
                    co2["very_poor"] = user_input["co2_very_poor"]
                if "co2_poor" in user_input:
                    co2["poor"] = user_input["co2_poor"]
                if "co2_moderate" in user_input:
                    co2["moderate"] = user_input["co2_moderate"]
                if co2:
                    advanced_settings[CONF_CO2_THRESHOLDS] = co2

                # Wind
                wind = {}
                if "wind_no_effect" in user_input:
                    wind["no_effect"] = user_input["wind_no_effect"]
                if "wind_moderate_effect" in user_input:
                    wind["moderate_effect"] = user_input["wind_moderate_effect"]
                if wind:
                    advanced_settings[CONF_WIND_THRESHOLDS] = wind

                # Score weights
                weights = {}
                if "weight_temperature" in user_input:
                    weights["temperature"] = user_input["weight_temperature"]
                if "weight_humidity" in user_input:
                    weights["humidity"] = user_input["weight_humidity"]
                if "weight_co2" in user_input:
                    weights["co2"] = user_input["weight_co2"]
                if "weight_time" in user_input:
                    weights["time"] = user_input["weight_time"]
                if weights:
                    advanced_settings[CONF_SCORE_WEIGHTS] = weights

            # Update advanced settings
            if CONF_ADVANCED_SETTINGS not in current_options:
                current_options[CONF_ADVANCED_SETTINGS] = {}

            current_options[CONF_ADVANCED_SETTINGS].update(advanced_settings)

            return self.async_create_entry(title="", data=current_options)

        # Get current advanced settings and defaults
        current_advanced = self._config_entry.options.get(CONF_ADVANCED_SETTINGS, {})

        advanced_schema = vol.Schema(
            {
                # Temperature thresholds
                vol.Optional(
                    "temperature_winter_good",
                    default=current_advanced.get(CONF_TEMPERATURE_THRESHOLDS, {}).get(
                        "winter_good", DEFAULT_TEMPERATURE_THRESHOLDS["winter_good"]
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "temperature_winter_moderate",
                    default=current_advanced.get(CONF_TEMPERATURE_THRESHOLDS, {}).get(
                        "winter_moderate",
                        DEFAULT_TEMPERATURE_THRESHOLDS["winter_moderate"],
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "temperature_summer_good",
                    default=current_advanced.get(CONF_TEMPERATURE_THRESHOLDS, {}).get(
                        "summer_good", DEFAULT_TEMPERATURE_THRESHOLDS["summer_good"]
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "temperature_summer_moderate",
                    default=current_advanced.get(CONF_TEMPERATURE_THRESHOLDS, {}).get(
                        "summer_moderate",
                        DEFAULT_TEMPERATURE_THRESHOLDS["summer_moderate"],
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "temperature_default_good",
                    default=current_advanced.get(CONF_TEMPERATURE_THRESHOLDS, {}).get(
                        "default_good", DEFAULT_TEMPERATURE_THRESHOLDS["default_good"]
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "temperature_default_moderate",
                    default=current_advanced.get(CONF_TEMPERATURE_THRESHOLDS, {}).get(
                        "default_moderate",
                        DEFAULT_TEMPERATURE_THRESHOLDS["default_moderate"],
                    ),
                ): vol.Coerce(float),
                # Humidity
                vol.Optional(
                    "humidity_good",
                    default=current_advanced.get(CONF_HUMIDITY_THRESHOLDS, {}).get(
                        "good", DEFAULT_HUMIDITY_THRESHOLDS["good"]
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "humidity_moderate",
                    default=current_advanced.get(CONF_HUMIDITY_THRESHOLDS, {}).get(
                        "moderate", DEFAULT_HUMIDITY_THRESHOLDS["moderate"]
                    ),
                ): vol.Coerce(float),
                # CO2
                vol.Optional(
                    "co2_very_poor",
                    default=current_advanced.get(CONF_CO2_THRESHOLDS, {}).get(
                        "very_poor", DEFAULT_CO2_THRESHOLDS["very_poor"]
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    "co2_poor",
                    default=current_advanced.get(CONF_CO2_THRESHOLDS, {}).get(
                        "poor", DEFAULT_CO2_THRESHOLDS["poor"]
                    ),
                ): vol.Coerce(int),
                vol.Optional(
                    "co2_moderate",
                    default=current_advanced.get(CONF_CO2_THRESHOLDS, {}).get(
                        "moderate", DEFAULT_CO2_THRESHOLDS["moderate"]
                    ),
                ): vol.Coerce(int),
                # Wind
                vol.Optional(
                    "wind_no_effect",
                    default=current_advanced.get(CONF_WIND_THRESHOLDS, {}).get(
                        "no_effect", DEFAULT_WIND_THRESHOLDS["no_effect"]
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "wind_moderate_effect",
                    default=current_advanced.get(CONF_WIND_THRESHOLDS, {}).get(
                        "moderate_effect", DEFAULT_WIND_THRESHOLDS["moderate_effect"]
                    ),
                ): vol.Coerce(float),
                # Score weights
                vol.Optional(
                    "weight_temperature",
                    default=current_advanced.get(CONF_SCORE_WEIGHTS, {}).get(
                        "temperature", DEFAULT_SCORE_WEIGHTS["temperature"]
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "weight_humidity",
                    default=current_advanced.get(CONF_SCORE_WEIGHTS, {}).get(
                        "humidity", DEFAULT_SCORE_WEIGHTS["humidity"]
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "weight_co2",
                    default=current_advanced.get(CONF_SCORE_WEIGHTS, {}).get(
                        "co2", DEFAULT_SCORE_WEIGHTS["co2"]
                    ),
                ): vol.Coerce(float),
                vol.Optional(
                    "weight_time",
                    default=current_advanced.get(CONF_SCORE_WEIGHTS, {}).get(
                        "time", DEFAULT_SCORE_WEIGHTS["time"]
                    ),
                ): vol.Coerce(float),
            }
        )

        return self.async_show_form(
            step_id="advanced",
            data_schema=advanced_schema,
        )

    async def async_step_rooms(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle room configuration options."""
        if user_input is not None:
            if user_input.get("add_room"):
                return await self.async_step_add_room()
            if user_input.get("edit_room"):
                room_to_edit = user_input.get("room_to_edit")
                if room_to_edit:
                    # store selection on the flow instance and show edit form
                    self._room_to_edit = room_to_edit
                    return await self.async_step_edit_room()
            if user_input.get("remove_room"):
                room_to_remove = user_input.get("room_to_remove")
                if room_to_remove:
                    # store selection and show remove confirmation
                    self._room_to_remove = room_to_remove
                    return await self.async_step_remove_room()
            return self.async_create_entry(title="", data=user_input)

        rooms_data = self._config_entry.data.get(CONF_ROOMS, {})
        room_names = list(rooms_data.keys())

        schema_dict = {}

        if room_names:
            schema_dict.update(
                {
                    vol.Optional("edit_room", default=False): bool,
                    vol.Optional("room_to_edit"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=room_names)
                    )
                    if room_names
                    else None,
                    vol.Optional("remove_room", default=False): bool,
                    vol.Optional("room_to_remove"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=room_names)
                    )
                    if room_names
                    else None,
                }
            )

        schema_dict[vol.Optional("add_room", default=False)] = bool

        return self.async_show_form(
            step_id="rooms",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "current_rooms": ", ".join(room_names)
                if room_names
                else "No rooms configured",
                "max_rooms": str(MAX_ROOMS),
            },
        )

    async def async_step_add_room(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add a new room."""
        if user_input is not None:
            room_name = user_input[CONF_ROOM_NAME]
            current_rooms = self._config_entry.data.get(CONF_ROOMS, {})

            if room_name in current_rooms:
                return self.async_show_form(
                    step_id="add_room",
                    data_schema=self._get_room_schema(),
                    errors={"room_name": "Room name already exists"},
                )

            if len(current_rooms) >= MAX_ROOMS:
                return self.async_show_form(
                    step_id="add_room",
                    data_schema=self._get_room_schema(),
                    errors={"room_name": f"Maximum {MAX_ROOMS} rooms allowed"},
                )

            # Add new room to config
            co2_sensor_value = user_input.get(CONF_CO2_SENSOR)
            # Convert empty strings to None for CO2 sensor
            if (
                co2_sensor_value
                and isinstance(co2_sensor_value, str)
                and not co2_sensor_value.strip()
            ):
                co2_sensor_value = None

            new_room_config = {
                CONF_ROOM_NAME: room_name,
                CONF_TEMP_SENSOR: user_input[CONF_TEMP_SENSOR],
                CONF_HUMIDITY_SENSOR: user_input[CONF_HUMIDITY_SENSOR],
                CONF_ROOM_TYPE: user_input[CONF_ROOM_TYPE],
                CONF_CO2_SENSOR: co2_sensor_value,
                CONF_ENABLED: user_input.get(CONF_ENABLED, True),
            }

            updated_config = dict(self._config_entry.data)
            updated_rooms = dict(current_rooms)
            updated_rooms[room_name] = new_room_config
            updated_config[CONF_ROOMS] = updated_rooms

            self.hass.config_entries.async_update_entry(
                self._config_entry, data=updated_config
            )

            # Reload the entry to update sensors (skip in testing)
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                with contextlib.suppress(Exception):
                    await self.hass.config_entries.async_reload(
                        self._config_entry.entry_id
                    )

            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="add_room",
            data_schema=self._get_room_schema(),
        )

    async def async_step_edit_room(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """
        Edit an existing room.

        The selected room name is stored on the flow instance in
        `self._room_to_edit` when the user navigates from the rooms menu.
        Home Assistant will call this step with only `user_input` when the
        form is submitted, so we must not rely on a positional room_name
        parameter.
        """
        room_name = self._room_to_edit

        # If no room is selected, return to room management menu
        if room_name is None:
            return await self.async_step_init()

        if user_input is not None:
            current_rooms = self._config_entry.data.get(CONF_ROOMS, {})
            current_room_config = current_rooms.get(room_name, {})

            # Update room configuration
            co2_sensor_value = user_input.get(CONF_CO2_SENSOR)
            # Convert empty strings to None for CO2 sensor
            if (
                co2_sensor_value
                and isinstance(co2_sensor_value, str)
                and not co2_sensor_value.strip()
            ):
                co2_sensor_value = None

            updated_room_config = dict(current_room_config)
            updated_room_config.update(
                {
                    CONF_TEMP_SENSOR: user_input[CONF_TEMP_SENSOR],
                    CONF_HUMIDITY_SENSOR: user_input[CONF_HUMIDITY_SENSOR],
                    CONF_ROOM_TYPE: user_input[CONF_ROOM_TYPE],
                    CONF_CO2_SENSOR: co2_sensor_value,
                    CONF_ENABLED: user_input.get(CONF_ENABLED, True),
                }
            )

            updated_config = dict(self._config_entry.data)
            updated_rooms = dict(current_rooms)
            updated_rooms[room_name] = updated_room_config
            updated_config[CONF_ROOMS] = updated_rooms

            self.hass.config_entries.async_update_entry(
                self._config_entry, data=updated_config
            )

            # clear stored selection
            self._room_to_edit = None

            return self.async_create_entry(title="", data={})

        # Pre-fill form with current room data
        current_rooms = self._config_entry.data.get(CONF_ROOMS, {})
        current_room_config = current_rooms.get(room_name, {})

        schema = self._get_room_schema(current_room_config)

        return self.async_show_form(
            step_id="edit_room",
            data_schema=schema,
            description_placeholders={"room_name": room_name},
        )

    async def async_step_remove_room(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """
        Remove a room.

        The selected room to remove is stored on the flow instance in
        `self._room_to_remove` when navigating from the rooms menu. This
        step will be called by Home Assistant with only `user_input` on
        submit, so use the stored value.
        """
        room_name = self._room_to_remove

        # If no room is selected, return to room management menu
        if room_name is None:
            return await self.async_step_init()

        if user_input is not None:
            if user_input.get("confirm_remove", False):
                current_rooms = self._config_entry.data.get(CONF_ROOMS, {})

                if room_name in current_rooms:
                    updated_config = dict(self._config_entry.data)
                    updated_rooms = dict(current_rooms)
                    del updated_rooms[room_name]
                    updated_config[CONF_ROOMS] = updated_rooms

                    self.hass.config_entries.async_update_entry(
                        self._config_entry, data=updated_config
                    )

                    # Reload the entry to update sensors (skip in testing)
                    if not os.environ.get("PYTEST_CURRENT_TEST"):
                        with contextlib.suppress(Exception):
                            await self.hass.config_entries.async_reload(
                                self._config_entry.entry_id
                            )

                    # clear stored selection
                    self._room_to_remove = None

                    # Return success after room removal
                    return self.async_create_entry(title="", data=updated_config)

                # Room not found, return to room management menu
                self._room_to_remove = None
                return await self.async_step_init()

            # If not confirmed, return to room management menu
            self._room_to_remove = None
            return await self.async_step_init()

        return self.async_show_form(
            step_id="remove_room",
            data_schema=vol.Schema(
                {
                    vol.Required("confirm_remove", default=False): bool,
                }
            ),
            description_placeholders={"room_name": room_name},
        )

    def _get_room_schema(
        self, current_config: dict[str, Any] | None = None
    ) -> vol.Schema:
        """Get the room configuration schema."""
        if current_config is None:
            current_config = {}

        return vol.Schema(
            {
                vol.Required(
                    CONF_ROOM_NAME, default=current_config.get(CONF_ROOM_NAME, "")
                ): str,
                vol.Required(
                    CONF_TEMP_SENSOR, default=current_config.get(CONF_TEMP_SENSOR)
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="temperature"
                    )
                ),
                vol.Required(
                    CONF_HUMIDITY_SENSOR,
                    default=current_config.get(CONF_HUMIDITY_SENSOR),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="sensor", device_class="humidity"
                    )
                ),
                vol.Required(
                    CONF_ROOM_TYPE, default=current_config.get(CONF_ROOM_TYPE)
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=ROOM_TYPES)
                ),
                vol.Optional(
                    CONF_CO2_SENSOR, default=current_config.get(CONF_CO2_SENSOR)
                ): vol.Any(
                    None,
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="sensor")
                    ),
                ),
                vol.Optional(
                    CONF_ENABLED, default=current_config.get(CONF_ENABLED, True)
                ): bool,
            }
        )
