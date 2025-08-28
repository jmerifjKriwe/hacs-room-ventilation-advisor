"""
Options flow for Solar Window System integration.

Note:
This options flow only handles the global configuration entry.
All logic for group and window subentries (including inheritance, defaults, and UI behavior)
is implemented in config_flow.py, not here.

"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

_LOGGER = logging.getLogger(__name__)


#
# Note: This file has been significantly simplified.
#
# The previous version contained redundant logic for handling group and window
# options, which is already correctly handled by the `reconfigure` flow
# in `config_flow.py`. It also contained duplicated helper functions.
#
# This options flow now ONLY handles the options for the GLOBAL config entry.
# The options for "Group Configurations" and "Window Configurations" entries
# are intentionally not handled here, as they are parent entries for sub-entries
# and do not have their own options.
#


# ----- Locale-aware parsing helpers -----
# These are kept here as they are used by the global options flow.
def _normalize_decimal_string(v: Any) -> str:
    """
    Normalize decimal separator for parsing.

    Accept strings with comma as decimal separator by converting to dot.
    Also handle numeric inputs by converting to string.
    """
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return v.strip().replace(",", ".")
    return str(v)


def _parse_float_locale(v: Any) -> float:
    """Parse a float accepting decimal comma or dot."""
    return float(_normalize_decimal_string(v))


def _parse_int_locale(v: Any) -> int:
    """Parse an int accepting decimal comma or dot (coerce via float)."""
    return int(float(_normalize_decimal_string(v)))


class SolarWindowSystemOptionsFlow(config_entries.OptionsFlow):
    """Options flow for the global configuration of Solar Window System."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""
        # Store the config entry privately to avoid relying on the public
        # attribute which is deprecated to be assigned by integrations.
        self._config_entry = config_entry
        # page storages
        self._p1: dict[str, Any] | None = None
        self._p2: dict[str, Any] | None = None

    async def async_step_init(
        self, _user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Start options flow, routing by entry type."""
        entry_type = (self._config_entry.data or {}).get("entry_type", "")

        # This options flow is only for the global configuration.
        if entry_type == "global_config":
            return await self.async_step_global_basic()

        # For other entry types like 'group_configs' or 'window_configs',
        # there are no options to configure at the parent level.
        # The user should configure the sub-entries (groups/windows) directly,
        # which triggers the reconfigure flow in config_flow.py.
        return self.async_abort(reason="not_supported")

    # ----- Page 1: Basic geometry + optional selectors -----
    async def async_step_global_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Options page 1: basic geometry and optional selectors."""
        opts = self._config_entry.options or {}
        data = self._config_entry.data or {}

        # build defaults from options with fallback to data
        def _g(key: str, fallback: Any = "") -> Any:
            return opts.get(key, data.get(key, fallback))

        def _sel_default(v: Any) -> Any:
            # For entity selector, None or "" renders as empty/cleared in UI
            return v if v else None

        def _sel_default_with_fallback(key: str) -> Any:
            # If key is explicitly present in options, prefer it
            # (including empty string)
            if key in opts:
                return _sel_default(opts.get(key))
            # Otherwise fall back to data
            return _sel_default(data.get(key, ""))

        defaults = {
            "update_interval": _g("update_interval", 1),
            "window_width": str(_g("window_width", "")),
            "window_height": str(_g("window_height", "")),
            "shadow_depth": str(_g("shadow_depth", "")),
            "shadow_offset": str(_g("shadow_offset", "")),
            "solar_radiation_sensor": _sel_default_with_fallback(
                "solar_radiation_sensor"
            ),
            "outdoor_temperature_sensor": _sel_default_with_fallback(
                "outdoor_temperature_sensor"
            ),
            "indoor_temperature_sensor": _sel_default_with_fallback(
                "indoor_temperature_sensor"
            ),
            # For selectors: use options if present, else fallback to data
            "forecast_temperature_sensor": _sel_default_with_fallback(
                "forecast_temperature_sensor"
            ),
            "weather_warning_sensor": _sel_default_with_fallback(
                "weather_warning_sensor"
            ),
        }

        # Prefer entity selectors over static lists for a true dropdown widget
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Optional(
                        "update_interval",
                        description={"suggested_value": defaults["update_interval"]},
                        default=defaults["update_interval"],
                    ): vol.Coerce(int),
                    vol.Required("window_width", default=defaults["window_width"]): str,
                    vol.Required(
                        "window_height", default=defaults["window_height"]
                    ): str,
                    vol.Required("shadow_depth", default=defaults["shadow_depth"]): str,
                    vol.Required(
                        "shadow_offset", default=defaults["shadow_offset"]
                    ): str,
                    vol.Required(
                        "solar_radiation_sensor",
                        description={
                            "suggested_value": defaults["solar_radiation_sensor"]
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["sensor"])
                    ),
                    vol.Required(
                        "outdoor_temperature_sensor",
                        description={
                            "suggested_value": defaults["outdoor_temperature_sensor"]
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"], device_class="temperature"
                        )
                    ),
                    vol.Optional(
                        "indoor_temperature_sensor",
                        description={
                            "suggested_value": defaults["indoor_temperature_sensor"]
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"], device_class="temperature"
                        )
                    ),
                    vol.Optional(
                        "forecast_temperature_sensor",
                        description={
                            "suggested_value": defaults["forecast_temperature_sensor"]
                        },
                    ): vol.Any(
                        None,
                        selector.EntitySelector(
                            selector.EntitySelectorConfig(
                                domain=["sensor"], device_class="temperature"
                            )
                        ),
                    ),
                    vol.Optional(
                        "weather_warning_sensor",
                        description={
                            "suggested_value": defaults["weather_warning_sensor"]
                        },
                    ): vol.Any(
                        None,
                        selector.EntitySelector(
                            selector.EntitySelectorConfig(
                                domain=["binary_sensor", "input_boolean"]
                            )
                        ),
                    ),
                }
            )
            return self.async_show_form(step_id="global_basic", data_schema=schema)

        errors: dict[str, str] = {}
        page1: dict[str, Any] = {}

        def _check_float_required(field: str, min_v: float, max_v: float) -> None:
            raw = user_input.get(field)
            if raw in (None, "", "-1"):
                errors[field] = "required"
                return
            try:
                fv = _parse_float_locale(raw)
            except (ValueError, TypeError):
                errors[field] = "invalid_number"
                return
            if fv < min_v or fv > max_v:
                errors[field] = "number_out_of_range"
                return
            page1[field] = str(raw)

        def _check_int_required(field: str, min_v: int, max_v: int) -> None:
            raw = user_input.get(field)
            if raw in (None, "", "-1"):
                errors[field] = "required"
                return
            try:
                iv = _parse_int_locale(raw)
            except (ValueError, TypeError):
                errors[field] = "invalid_number"
                return
            if iv < min_v or iv > max_v:
                errors[field] = "number_out_of_range"
                return
            page1[field] = iv

        _check_int_required("update_interval", 1, 1440)
        _check_float_required("window_width", 0.1, 10)
        _check_float_required("window_height", 0.1, 10)
        _check_float_required("shadow_depth", 0, 5)
        _check_float_required("shadow_offset", 0, 5)

        # Required selectors: indoor is also required
        for req_key in (
            "solar_radiation_sensor",
            "outdoor_temperature_sensor",
            "indoor_temperature_sensor",
        ):
            val = user_input.get(req_key)
            if val in (None, ""):
                errors[req_key] = "required"
            else:
                page1[req_key] = val

        # Optional selectors: allow clearing
        for key in ("forecast_temperature_sensor", "weather_warning_sensor"):
            val = user_input.get(key, "")
            page1[key] = "" if val in (None, "") else val

        if errors:
            schema = vol.Schema(
                {
                    vol.Optional(
                        "update_interval",
                        default=user_input.get("update_interval", 1),
                    ): vol.Coerce(int),
                    vol.Required(
                        "window_width",
                        default=str(user_input.get("window_width", "")),
                    ): str,
                    vol.Required(
                        "window_height",
                        default=str(user_input.get("window_height", "")),
                    ): str,
                    vol.Required(
                        "shadow_depth",
                        default=str(user_input.get("shadow_depth", "")),
                    ): str,
                    vol.Required(
                        "shadow_offset",
                        default=str(user_input.get("shadow_offset", "")),
                    ): str,
                    vol.Required(
                        "solar_radiation_sensor",
                        default=_sel_default(
                            user_input.get("solar_radiation_sensor", "")
                        ),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain=["sensor"])
                    ),
                    vol.Required(
                        "outdoor_temperature_sensor",
                        default=_sel_default(
                            user_input.get("outdoor_temperature_sensor", "")
                        ),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"], device_class="temperature"
                        )
                    ),
                    vol.Required(
                        "indoor_temperature_sensor",
                        default=_sel_default(
                            user_input.get("indoor_temperature_sensor", "")
                        ),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"], device_class="temperature"
                        )
                    ),
                    vol.Optional(
                        "forecast_temperature_sensor",
                        default=_sel_default(
                            user_input.get("forecast_temperature_sensor", "")
                        ),
                    ): vol.Any(
                        None,
                        selector.EntitySelector(
                            selector.EntitySelectorConfig(
                                domain=["sensor"], device_class="temperature"
                            )
                        ),
                    ),
                    vol.Optional(
                        "weather_warning_sensor",
                        default=_sel_default(
                            user_input.get("weather_warning_sensor", "")
                        ),
                    ): vol.Any(
                        None,
                        selector.EntitySelector(
                            selector.EntitySelectorConfig(
                                domain=["binary_sensor", "input_boolean"]
                            )
                        ),
                    ),
                }
            )
            return self.async_show_form(
                step_id="global_basic",
                data_schema=schema,
                errors=errors,
            )

        self._p1 = page1

        return await self.async_step_global_enhanced()

    # ----- Page 2: Required defaults -----
    async def async_step_global_enhanced(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Options page 2: required global defaults (validated)."""
        opts = self._config_entry.options or {}
        data = self._config_entry.data or {}

        def _g(key: str, fallback: Any = "") -> Any:
            return opts.get(key, data.get(key, fallback))

        defaults = {
            "g_value": str(_g("g_value", 0.5)),
            "frame_width": str(_g("frame_width", 0.125)),
            "tilt": str(_g("tilt", 90)),
            "diffuse_factor": str(_g("diffuse_factor", 0.15)),
            "threshold_direct": str(_g("threshold_direct", 200)),
            "threshold_diffuse": str(_g("threshold_diffuse", 150)),
            "temperature_indoor_base": str(_g("temperature_indoor_base", 23.0)),
            "temperature_outdoor_base": str(_g("temperature_outdoor_base", 19.5)),
        }

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required("g_value", default=defaults["g_value"]): str,
                    vol.Required("frame_width", default=defaults["frame_width"]): str,
                    vol.Required("tilt", default=defaults["tilt"]): str,
                    vol.Required(
                        "diffuse_factor", default=defaults["diffuse_factor"]
                    ): str,
                    vol.Required(
                        "threshold_direct", default=defaults["threshold_direct"]
                    ): str,
                    vol.Required(
                        "threshold_diffuse", default=defaults["threshold_diffuse"]
                    ): str,
                    vol.Required(
                        "temperature_indoor_base",
                        default=defaults["temperature_indoor_base"],
                    ): str,
                    vol.Required(
                        "temperature_outdoor_base",
                        default=defaults["temperature_outdoor_base"],
                    ): str,
                }
            )
            return self.async_show_form(step_id="global_enhanced", data_schema=schema)

        # per-field validation with locale-aware parsing
        errors2: dict[str, str] = {}
        page2: dict[str, Any] = {}

        def _check_float_required(field: str, min_v: float, max_v: float) -> None:
            raw = user_input.get(field)
            if raw in (None, "", "-1"):
                errors2[field] = "required"
                return
            try:
                fv = _parse_float_locale(raw)
            except (ValueError, TypeError):
                errors2[field] = "invalid_number"
                return
            if fv < min_v or fv > max_v:
                errors2[field] = "number_out_of_range"
                return
            page2[field] = str(raw)

        def _check_int_required(field: str, min_v: int, max_v: int) -> None:
            raw = user_input.get(field)
            if raw in (None, "", "-1"):
                errors2[field] = "required"
                return
            try:
                iv = _parse_int_locale(raw)
            except (ValueError, TypeError):
                errors2[field] = "invalid_number"
                return
            if iv < min_v or iv > max_v:
                errors2[field] = "number_out_of_range"
                return
            page2[field] = str(raw)

        _check_float_required("g_value", 0.1, 0.9)
        _check_float_required("frame_width", 0.05, 0.3)
        _check_int_required("tilt", 0, 90)
        _check_float_required("diffuse_factor", 0.05, 0.5)
        _check_int_required("threshold_direct", 0, 1000)
        _check_int_required("threshold_diffuse", 0, 1000)
        _check_float_required("temperature_indoor_base", 10, 30)
        _check_float_required("temperature_outdoor_base", 10, 30)

        if errors2:
            schema = vol.Schema(
                {
                    vol.Required(
                        "g_value", default=str(user_input.get("g_value", ""))
                    ): str,
                    vol.Required(
                        "frame_width", default=str(user_input.get("frame_width", ""))
                    ): str,
                    vol.Required("tilt", default=str(user_input.get("tilt", ""))): str,
                    vol.Required(
                        "diffuse_factor",
                        default=str(user_input.get("diffuse_factor", "")),
                    ): str,
                    vol.Required(
                        "threshold_direct",
                        default=str(user_input.get("threshold_direct", "")),
                    ): str,
                    vol.Required(
                        "threshold_diffuse",
                        default=str(user_input.get("threshold_diffuse", "")),
                    ): str,
                    vol.Required(
                        "temperature_indoor_base",
                        default=str(user_input.get("temperature_indoor_base", "")),
                    ): str,
                    vol.Required(
                        "temperature_outdoor_base",
                        default=str(user_input.get("temperature_outdoor_base", "")),
                    ): str,
                }
            )
            return self.async_show_form(
                step_id="global_enhanced",
                data_schema=schema,
                errors=errors2,
            )

        self._p2 = page2

        return await self.async_step_global_scenarios()

    # ----- Page 3: Scenario thresholds -----
    async def async_step_global_scenarios(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Options page 3: scenario thresholds (validated)."""
        opts = self._config_entry.options or {}
        data = self._config_entry.data or {}

        def _g(key: str, fallback: Any = "") -> Any:
            return opts.get(key, data.get(key, fallback))

        defaults = {
            "scenario_b_temp_indoor": str(_g("scenario_b_temp_indoor", 23.5)),
            "scenario_b_temp_outdoor": str(_g("scenario_b_temp_outdoor", 25.5)),
            "scenario_c_temp_indoor": str(_g("scenario_c_temp_indoor", 21.5)),
            "scenario_c_temp_outdoor": str(_g("scenario_c_temp_outdoor", 24.0)),
            "scenario_c_temp_forecast": str(_g("scenario_c_temp_forecast", 28.5)),
            "scenario_c_start_hour": str(_g("scenario_c_start_hour", 9)),
        }

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(
                        "scenario_b_temp_indoor",
                        default=defaults["scenario_b_temp_indoor"],
                    ): str,
                    vol.Required(
                        "scenario_b_temp_outdoor",
                        default=defaults["scenario_b_temp_outdoor"],
                    ): str,
                    vol.Required(
                        "scenario_c_temp_indoor",
                        default=defaults["scenario_c_temp_indoor"],
                    ): str,
                    vol.Required(
                        "scenario_c_temp_outdoor",
                        default=defaults["scenario_c_temp_outdoor"],
                    ): str,
                    vol.Required(
                        "scenario_c_temp_forecast",
                        default=defaults["scenario_c_temp_forecast"],
                    ): str,
                    vol.Required(
                        "scenario_c_start_hour",
                        default=defaults["scenario_c_start_hour"],
                    ): str,
                }
            )
            return self.async_show_form(step_id="global_scenarios", data_schema=schema)

        # validate page 3 with per-field errors and locale-aware parsing
        errors3: dict[str, str] = {}
        p3: dict[str, Any] = {}

        def _check_float_required(field: str, min_v: float, max_v: float) -> None:
            raw = user_input.get(field)
            if raw in (None, "", "-1"):
                errors3[field] = "required"
                return
            try:
                fv = _parse_float_locale(raw)
            except (ValueError, TypeError):
                errors3[field] = "invalid_number"
                return
            if fv < min_v or fv > max_v:
                errors3[field] = "number_out_of_range"
                return
            p3[field] = str(raw)

        def _check_int_required(field: str, min_v: int, max_v: int) -> None:
            raw = user_input.get(field)
            if raw in (None, "", "-1"):
                errors3[field] = "required"
                return
            try:
                iv = _parse_int_locale(raw)
            except (ValueError, TypeError):
                errors3[field] = "invalid_number"
                return
            if iv < min_v or iv > max_v:
                errors3[field] = "number_out_of_range"
                return
            p3[field] = str(raw)

        _check_float_required("scenario_b_temp_indoor", 10, 30)
        _check_float_required("scenario_b_temp_outdoor", 10, 30)
        _check_float_required("scenario_c_temp_indoor", 10, 30)
        _check_float_required("scenario_c_temp_outdoor", 10, 30)
        _check_float_required("scenario_c_temp_forecast", 15, 40)
        _check_int_required("scenario_c_start_hour", 0, 23)

        if errors3:
            schema = vol.Schema(
                {
                    vol.Required(
                        "scenario_b_temp_indoor",
                        default=str(user_input.get("scenario_b_temp_indoor", "")),
                    ): str,
                    vol.Required(
                        "scenario_b_temp_outdoor",
                        default=str(user_input.get("scenario_b_temp_outdoor", "")),
                    ): str,
                    vol.Required(
                        "scenario_c_temp_indoor",
                        default=str(user_input.get("scenario_c_temp_indoor", "")),
                    ): str,
                    vol.Required(
                        "scenario_c_temp_outdoor",
                        default=str(user_input.get("scenario_c_temp_outdoor", "")),
                    ): str,
                    vol.Required(
                        "scenario_c_temp_forecast",
                        default=str(user_input.get("scenario_c_temp_forecast", "")),
                    ): str,
                    vol.Required(
                        "scenario_c_start_hour",
                        default=str(user_input.get("scenario_c_start_hour", "")),
                    ): str,
                }
            )
            return self.async_show_form(
                step_id="global_scenarios",
                data_schema=schema,
                errors=errors3,
            )

        # Merge and save all pages
        data_out = {
            **(self._p1 or {}),
            **(self._p2 or {}),
            **p3,
        }
        return self.async_create_entry(title="", data=data_out)
