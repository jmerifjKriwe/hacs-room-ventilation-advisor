"""
Config flow for Solar Window System integration.

Note:
All logic for creating and reconfiguring group and window subentries,
including default value handling and inheritance (-1 marker), is implemented here.
The options_flow.py is only responsible for the global configuration entry.

"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import DOMAIN
from .helpers import get_temperature_sensor_entities
from .options_flow import SolarWindowSystemOptionsFlow

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

# Constants for entry types
ENTRY_TYPE_GLOBAL = "global_config"
ENTRY_TYPE_GROUPS = "group_configs"
ENTRY_TYPE_WINDOWS = "window_configs"

# Common UI labels
NONE_LABEL = "(none)"

# Constants for UI default handling
INHERITANCE_INDICATOR = "-1"
EMPTY_STRING_VALUES = ("", None)


def _get_global_data_merged(hass: Any) -> dict[str, Any]:
    """
    Return Global Configuration data merged with options.

    Options take precedence over data.
    """
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get("entry_type") == ENTRY_TYPE_GLOBAL:
            merged: dict[str, Any] = dict(entry.data)
            # Options reflect the latest saved values; prefer them where present
            if getattr(entry, "options", None):
                # Defensive: options may be a mapping proxy; ignore if not mutable
                with contextlib.suppress(Exception):
                    merged.update(entry.options or {})
            return merged
    return {}


def _convert_inherit_value(v: Any) -> Any:
    """
    Convert UI inherit marker '-1' to storage empty string.

    Accepts int or str '-1' and returns "" for persistence. Otherwise returns v.
    """
    if v in (-1, "-1"):
        return ""
    return v


# ----- Shared validators that allow clearing values (empty string) -----
def _normalize_decimal_string(v: Any) -> str:
    """
    Normalize decimal separator for parsing.

    Accepts strings with comma as decimal separator by converting to dot.
    Also handle numeric inputs by converting to string.
    """
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        return v.strip().replace(",", ".")
    # Let downstream converters raise the appropriate errors
    return str(v)


def _parse_float_locale(v: Any) -> float:
    """Parse a float accepting decimal comma or dot."""
    return float(_normalize_decimal_string(v))


def _parse_int_locale(v: Any) -> int:
    """Parse an int accepting decimal comma or dot (coerce via float)."""
    return int(float(_normalize_decimal_string(v)))


def allow_empty_float(min_v: float | None = None, max_v: float | None = None) -> Any:
    """
    Return a validator that coerces to float and allows empty strings.

    When the provided value is "" or None, the validator returns "".
    Otherwise, it coerces to float and enforces optional min/max bounds.
    """

    def _validator(v: Any) -> Any:
        if v in ("", None, "-1", -1):
            return ""
        fv = _parse_float_locale(v)
        if min_v is not None and fv < min_v:
            msg = "value below minimum"
            raise vol.Invalid(msg)
        if max_v is not None and fv > max_v:
            msg = "value above maximum"
            raise vol.Invalid(msg)
        return fv

    return _validator


def allow_empty_int(min_v: int | None = None, max_v: int | None = None) -> Any:
    """
    Return a validator that coerces to int and allows empty strings.

    When the provided value is "" or None, the validator returns "".
    Otherwise, it coerces to int and enforces optional min/max bounds.
    """

    def _validator(v: Any) -> Any:
        if v in ("", None, "-1", -1):
            return ""
        iv = _parse_int_locale(v)
        if min_v is not None and iv < min_v:
            msg = "value below minimum"
            raise vol.Invalid(msg)
        if max_v is not None and iv > max_v:
            msg = "value above maximum"
            raise vol.Invalid(msg)
        return iv

    return _validator


def allow_inherit_or_float(
    min_v: float | None = None, max_v: float | None = None
) -> Any:
    """
    Return a validator that allows '-1' (as string or int) for inheritance,
    or coerces to float and checks range.
    """

    def validator(v: Any) -> Any:
        if v in (-1, "-1"):
            return v
        if v in ("", None):
            return v
        f = float(_normalize_decimal_string(v))
        if min_v is not None and f < min_v:
            raise vol.Invalid(f"Value {f} below minimum {min_v}")
        if max_v is not None and f > max_v:
            raise vol.Invalid(f"Value {f} above maximum {max_v}")
        return f

    return validator


def allow_inherit_or_int(min_v: int | None = None, max_v: int | None = None) -> Any:
    """
    Return a validator that allows '-1' (as string or int) for inheritance,
    or coerces to int and checks range.
    """

    def validator(v: Any) -> Any:
        if v in (-1, "-1"):
            return v
        if v in ("", None):
            return v
        i = int(float(_normalize_decimal_string(v)))
        if min_v is not None and i < min_v:
            raise vol.Invalid(f"Value {i} below minimum {min_v}")
        if max_v is not None and i > max_v:
            raise vol.Invalid(f"Value {i} above maximum {max_v}")
        return i

    return validator


class GroupSubentryFlowHandler(config_entries.ConfigSubentryFlow):
    """
    Handle subentry flow for adding and modifying a group.

    IMPORTANT: This is a SubentryFlow, NOT a regular ConfigFlow!
    - Groups are created via this SubentryFlow Handler
    - NOT via the main SolarWindowSystemConfigFlow
    - The main ConfigFlow only creates parent entries and global config
    - SubentryFlows are used for individual group/window configurations

    Two-step wizard:
    - user (basic): name + core thresholds
    - enhanced: scenario enable + scenario thresholds
    """

    def __init__(self) -> None:
        """Initialize the group subentry flow handler."""
        self._basic: dict[str, Any] = {}
        self._reconfigure_mode: bool = False

    # ----- Creation flow (step 1: basic) -----
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Render basic group configuration (page 1)."""
        # Prepare temperature sensor options
        temp_sensor_options = await get_temperature_sensor_entities(self.hass)

        # Defaults for basic page
        defaults: dict[str, Any] = {
            "name": getattr(getattr(self, "subentry", None), "title", ""),
            "indoor_temperature_sensor": "-1",  # Default to inherit
            "diffuse_factor": "",
            "threshold_direct": "",
            "threshold_diffuse": "",
            "temperature_indoor_base": "",
            "temperature_outdoor_base": "",
        }

        # Inherit suggestions from Global Configuration for numeric fields
        global_data = _get_global_data_merged(self.hass)

        # If reconfiguring, prefill from current subentry title and data
        if self.source == config_entries.SOURCE_RECONFIGURE:
            sub = self._get_reconfigure_subentry()
            if getattr(sub, "title", None):
                defaults["name"] = sub.title
            for key in list(defaults.keys()):
                if key == "name":
                    continue
                if key in sub.data:
                    raw_val = sub.data[key]
                    # support migration from old key name if present
                    if (
                        key == "indoor_temperature_sensor"
                        and "room_temp_entity" in sub.data
                    ):
                        # support migration from old key name
                        defaults[key] = sub.data.get(
                            "room_temp_entity", sub.data.get(key)
                        )
                    else:
                        defaults[key] = raw_val

        # Determine UI default for sensor: if no local default but Global has a value,
        # show '-1' in the selector to indicate 'inherit'. The suggested_value shows
        # the actual Global value as a hint to the user.
        sensor_default = defaults.get("indoor_temperature_sensor", "")
        sensor_suggested = global_data.get("indoor_temperature_sensor", "")
        # Always preselect 'Inherit' (-1) if the value is empty or None
        if sensor_default in ("", None):
            sensor_ui_default = "-1"
        else:
            sensor_ui_default = sensor_default

        def _ui_default(key: str) -> str:
            cur = defaults.get(key, "")
            gv = global_data.get(key, "")
            if cur in EMPTY_STRING_VALUES and gv not in EMPTY_STRING_VALUES:
                return INHERITANCE_INDICATOR  # Inheritance indicator
            return str(cur) if cur not in EMPTY_STRING_VALUES else ""

        schema_dict: dict[Any, Any] = {
            vol.Required("name", default=defaults["name"]): str,
            # ACHTUNG: Obwohl 'indoor_temperature_sensor' hier als optional deklariert ist,
            # ist es für eine gültige Konfiguration faktisch verpflichtend!
            # Die Validierung erfolgt erst später im Flow/bei der Nutzung.
            # Für Tests und echte Flows IMMER einen Wert angeben!
            vol.Optional(
                "indoor_temperature_sensor",
                default=_ui_default("indoor_temperature_sensor"),
                description={
                    "suggested_value": _ui_default("indoor_temperature_sensor")
                },
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=cast("Any", temp_sensor_options),
                    custom_value=True,
                )
            ),
        }

        # Helper function to ensure string defaults for Voluptuous schema compatibility
        def _ui_default(key: str) -> str:
            cur = defaults.get(key, "")
            gv = global_data.get(key, "")
            if cur in EMPTY_STRING_VALUES and gv not in EMPTY_STRING_VALUES:
                return INHERITANCE_INDICATOR  # Inheritance indicator
            # CRITICAL: Always convert to string for Voluptuous schema compatibility
            return str(cur) if cur not in EMPTY_STRING_VALUES else ""

        # Build schema with safe string defaults
        for key in (
            "diffuse_factor",
            "threshold_direct",
            "threshold_diffuse",
            "temperature_indoor_base",
            "temperature_outdoor_base",
        ):
            schema_dict[vol.Optional(key, default=_ui_default(key))] = str

        schema = vol.Schema(schema_dict)

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=schema)

        errors = {}
        validated_input = dict(user_input)

        # --- Duplicate name check ---
        # Only check on creation, not reconfigure
        if self.source != config_entries.SOURCE_RECONFIGURE and user_input is not None:
            new_name = (user_input.get("name") or "").strip().lower()
            # Find the parent entry for groups
            parent_entry = None
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data.get("entry_type") == ENTRY_TYPE_GROUPS:
                    parent_entry = entry
                    break
            if parent_entry and hasattr(parent_entry, "subentries"):
                for sub in parent_entry.subentries.values():
                    if (
                        getattr(sub, "subentry_type", None) == "group"
                        and (sub.title or "").strip().lower() == new_name
                    ):
                        errors["name"] = "duplicate_name"
                        break

        def strict_float(field: str, min_v: float, max_v: float) -> float | str | None:
            val = user_input.get(field)
            if val in (INHERITANCE_INDICATOR, -1):
                return INHERITANCE_INDICATOR
            try:
                fv = _parse_float_locale(val)
            except (ValueError, TypeError):
                errors[field] = "invalid_number"
                return None
            if fv < min_v or fv > max_v:
                errors[field] = "number_out_of_range"
                return None
            return fv

        def strict_int(field: str, min_v: int, max_v: int) -> int | str | None:
            val = user_input.get(field)
            if val in (INHERITANCE_INDICATOR, -1):
                return INHERITANCE_INDICATOR
            try:
                iv = _parse_int_locale(val)
            except (ValueError, TypeError):
                errors[field] = "invalid_number"
                return None
            if iv < min_v or iv > max_v:
                errors[field] = "number_out_of_range"
                return None
            return iv

        for k, (func, min_v, max_v) in {
            "diffuse_factor": (strict_float, 0.05, 0.5),
            "threshold_direct": (strict_int, 0, 1000),
            "threshold_diffuse": (strict_int, 0, 1000),
            "temperature_indoor_base": (strict_float, 10, 30),
            "temperature_outdoor_base": (strict_float, 10, 30),
        }.items():
            if k in user_input:
                validated = func(k, min_v, max_v)
                validated_input[k] = validated

        if errors:
            # Zeige das Formular erneut mit Fehlern und den bisherigen Eingaben
            return self.async_show_form(
                step_id="user",
                data_schema=schema,
                errors=errors,
                description_placeholders=None,
                last_step=None,
            )

        self._basic = validated_input
        return await self.async_step_enhanced()

    # ----- Creation flow (step 2: enhanced) -----
    async def async_step_enhanced(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Render enhanced group configuration (page 2)."""
        global_data = _get_global_data_merged(self.hass)

        enhanced_defaults: dict[str, Any] = {
            # All fields on this page can be empty
            # Note: scenario enable moved to entities; temps remain here
            "scenario_b_temp_indoor": "",
            "scenario_b_temp_outdoor": "",
            "scenario_c_temp_indoor": "",
            "scenario_c_temp_outdoor": "",
            "scenario_c_temp_forecast": "",
            "scenario_c_start_hour": "",
        }

        # On reconfigure, prefill from existing subentry data
        if self.source == config_entries.SOURCE_RECONFIGURE:
            sub = self._get_reconfigure_subentry()
            for key in list(enhanced_defaults.keys()):
                if key in sub.data:
                    enhanced_defaults[key] = sub.data[key]

        # Build schema with suggestions from Global if current default is empty
        def _sv(key: str) -> str:
            v = global_data.get(key, "")
            return str(v) if v not in ("", None) else ""

        # Determine UI default: if local default empty but Global provides a value,
        # show '-1' to indicate inheritance (consistent with page 1 behavior).
        def _ui_default(key: str) -> str:
            cur = enhanced_defaults.get(key, "")
            gv = global_data.get(key, "")
            if cur in ("", None) and gv not in ("", None):
                return "-1"
            # Always convert to string for Voluptuous schema compatibility
            return str(cur) if cur not in ("", None) else ""

        schema = vol.Schema(
            {
                vol.Optional(
                    "scenario_b_temp_indoor",
                    default=_ui_default("scenario_b_temp_indoor"),
                ): str,
                vol.Optional(
                    "scenario_b_temp_outdoor",
                    default=_ui_default("scenario_b_temp_outdoor"),
                ): str,
                vol.Optional(
                    "scenario_c_temp_indoor",
                    default=_ui_default("scenario_c_temp_indoor"),
                ): str,
                vol.Optional(
                    "scenario_c_temp_outdoor",
                    default=_ui_default("scenario_c_temp_outdoor"),
                ): str,
                vol.Optional(
                    "scenario_c_temp_forecast",
                    default=_ui_default("scenario_c_temp_forecast"),
                ): str,
                vol.Optional(
                    "scenario_c_start_hour",
                    default=_ui_default("scenario_c_start_hour"),
                ): str,
            }
        )

        if user_input is None:
            return self.async_show_form(step_id="enhanced", data_schema=schema)

        # Coerce numeric strings while allowing "" to clear
        if user_input is not None:
            coerce_map = {
                "scenario_b_temp_indoor": allow_empty_float(10, 30),
                "scenario_b_temp_outdoor": allow_empty_float(10, 30),
                "scenario_c_temp_indoor": allow_empty_float(10, 30),
                "scenario_c_temp_outdoor": allow_empty_float(10, 30),
                "scenario_c_temp_forecast": allow_empty_float(15, 40),
                "scenario_c_start_hour": allow_empty_int(0, 23),
            }
            for k, conv in coerce_map.items():
                if k in user_input:
                    user_input[k] = conv(user_input[k])

        # Merge pages and create/update entry (keep name in data to preserve behavior)
        data = {**self._basic, **user_input, "entry_type": "group"}
        name = data["name"]

        # Creation and reconfigure both end with creating/updating subentry data
        if self.source == config_entries.SOURCE_RECONFIGURE:
            entry = self._get_entry()
            subentry = self._get_reconfigure_subentry()
            return self.async_update_and_abort(
                entry,
                subentry,
                title=name,
                data=data,
            )
        return self.async_create_entry(title=name, data=data)

    # ----- Reconfigure entry point (delegates to the same 2-step flow) -----
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Start reconfigure and reuse user/enhanced steps with defaults."""
        self._reconfigure_mode = True
        return await self.async_step_user(user_input)


class WindowSubentryFlowHandler(config_entries.ConfigSubentryFlow):
    """
    Handle subentry flow for adding and modifying a window.

    IMPORTANT: This is a SubentryFlow, NOT a regular ConfigFlow!
    - Windows are created via this SubentryFlow Handler
    - NOT via the main SolarWindowSystemConfigFlow
    - The main ConfigFlow only creates parent entries and global config
    - SubentryFlows are used for individual group/window configurations
    """

    def __init__(self) -> None:
        """Initialize window subentry flow state."""
        self._page1 = {}
        self._page2 = {}

    # ----- Helpers for Page 1 (basic) -----
    def _page1_defaults(
        self, group_options_map: list[tuple[str, str]]
    ) -> dict[str, Any]:
        """Build defaults for page 1, prefilling and resolving group name."""
        # For new windows, default optional fields to "-1" (inherit)
        # and mandatory fields to ""
        defaults: dict[str, Any] = {
            "name": getattr(getattr(self, "subentry", None), "title", ""),
            # Mandatory fields
            "azimuth": "",
            "azimuth_min": "-90",
            "azimuth_max": "90",
            "elevation_min": "0",
            "elevation_max": "90",
            # Optional/Inheritable fields
            "window_width": "-1",
            "window_height": "-1",
            "shadow_depth": "-1",
            "shadow_offset": "-1",
            "indoor_temperature_sensor": "-1",
            "linked_group": NONE_LABEL,
        }

        is_reconfigure = self.source == config_entries.SOURCE_RECONFIGURE
        if is_reconfigure:
            sub = self._get_reconfigure_subentry()
            if getattr(sub, "title", None):
                defaults["name"] = sub.title

            # Overwrite defaults with any saved values
            for k in list(defaults.keys()):
                if k == "name" or k == "linked_group":  # linked_group is special
                    continue

                val = sub.data.get(k)
                if k == "indoor_temperature_sensor":
                    val = sub.data.get(
                        "room_temp_entity", val
                    )  # migration from old key

                is_optional = k in [
                    "window_width",
                    "window_height",
                    "shadow_depth",
                    "shadow_offset",
                    "indoor_temperature_sensor",
                ]

                if is_optional:
                    defaults[k] = val if val not in ("", None) else "-1"
                elif val is not None:
                    defaults[k] = val

            # Resolve previously stored linked_group_id to display name
            if (
                not defaults.get("linked_group")
                or defaults.get("linked_group") == NONE_LABEL
            ):
                gid = sub.data.get("linked_group_id")
                if gid:
                    for group_id, group_name in group_options_map:
                        if group_id == gid:
                            defaults["linked_group"] = group_name
                            break

        return defaults

    def _page1_schema(
        self,
        defaults: dict[str, Any],
        temp_sensor_options: list[str],
        group_display_options: list[str],
    ) -> vol.Schema:
        """Build the serializable schema for page 1."""

        # Helper function to ensure string defaults for Voluptuous schema compatibility
        def _ui_default(key: str) -> str:
            value = defaults.get(key, "")
            return str(value) if value not in ("", None) else ""

        schema_dict: dict[Any, Any] = {}
        schema_dict[vol.Required("name", default=_ui_default("name"))] = str

        # Mandatory numeric fields
        for key in (
            "azimuth",
            "azimuth_min",
            "azimuth_max",
            "elevation_min",
            "elevation_max",
        ):
            schema_dict[vol.Required(key, default=_ui_default(key))] = str

        # Optional numeric fields
        for key in (
            "window_width",
            "window_height",
            "shadow_depth",
            "shadow_offset",
        ):
            schema_dict[vol.Optional(key, default=_ui_default(key))] = str

        # Note: temp_sensor_options now contain option dicts ({value,label}), but
        # vol.In expects values; accept an empty string or any of the values.
        schema_dict[
            vol.Optional(
                "indoor_temperature_sensor",
                default=_ui_default("indoor_temperature_sensor"),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=cast("Any", temp_sensor_options),
                custom_value=True,
            )
        )

        # Use a clearable dropdown for group assignment
        schema_dict[
            vol.Optional(
                "linked_group",
                description={
                    "suggested_value": _ui_default("linked_group") or NONE_LABEL
                },
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=group_display_options,
                custom_value=True,
            )
        )

        return vol.Schema(schema_dict)

    def _page1_process_submit(
        self, user_input: dict[str, Any], group_options_map: list[tuple[str, str]]
    ) -> dict[str, Any]:
        """Coerce numeric fields and map linked group name to id, allowing clearing."""
        coerce_map = {
            "azimuth": allow_empty_float(0, 360),
            "azimuth_min": allow_empty_float(-90, 0),
            "azimuth_max": allow_empty_float(0, 90),
            "elevation_min": allow_empty_float(0, 90),
            "elevation_max": allow_empty_float(0, 90),
            "window_width": allow_empty_float(0.1, 10),
            "window_height": allow_empty_float(0.1, 10),
            "shadow_depth": allow_empty_float(0, 5),
            "shadow_offset": allow_empty_float(0, 5),
        }
        for k, conv in coerce_map.items():
            if k in user_input:
                user_input[k] = conv(user_input[k])

        selected_group_name = user_input.get("linked_group", NONE_LABEL)
        if selected_group_name and selected_group_name != NONE_LABEL:
            for gid, gname in group_options_map:
                if gname == selected_group_name:
                    user_input["linked_group_id"] = gid
                    break
        else:
            # Explicitly clear any previously stored link
            user_input["linked_group"] = ""
            user_input["linked_group_id"] = ""
        return user_input

    # ----- Page 1: Basic window configuration -----
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        """Render basic window configuration (page 1)."""
        # Prepare temperature sensor options
        temp_sensor_options = await get_temperature_sensor_entities(self.hass)

        # Prepare group options (from Group configurations entry)
        group_options_map = await self._get_group_subentries()
        group_display_options = [name for _, name in group_options_map]
        defaults = self._page1_defaults(group_options_map)

        # Helper function to ensure string defaults for Voluptuous schema compatibility
        def _ui_default(key: str) -> str:
            value = defaults.get(key, "")
            return str(value) if value not in ("", None) else ""

        # Build schema, only include group if groups exist
        schema_dict = {}
        schema_dict[vol.Required("name", default=_ui_default("name"))] = str

        # Mandatory numeric fields
        for key in (
            "azimuth",
            "azimuth_min",
            "azimuth_max",
            "elevation_min",
            "elevation_max",
        ):
            schema_dict[vol.Required(key, default=_ui_default(key))] = str

        # Optional numeric fields
        for key in (
            "window_width",
            "window_height",
            "shadow_depth",
            "shadow_offset",
        ):
            schema_dict[vol.Optional(key, default=_ui_default(key))] = str

        # Use a clearable dropdown for indoor_temperature_sensor
        schema_dict[
            vol.Optional(
                "indoor_temperature_sensor",
                description={
                    "suggested_value": _ui_default("indoor_temperature_sensor")
                },
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=cast("Any", temp_sensor_options),
                custom_value=True,
            )
        )

        # Only show group field if groups exist
        if group_display_options:
            schema_dict[
                vol.Optional(
                    "linked_group",
                    description={"suggested_value": _ui_default("linked_group")},
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=group_display_options,
                    custom_value=True,
                )
            )

        schema = vol.Schema(schema_dict)

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=schema)

        # Coerce numerics and map linked_group display name to internal id
        if user_input is None:
            self._page1 = {}
        else:
            # Accept old key name for compatibility
            if (
                "room_temp_entity" in user_input
                and "indoor_temperature_sensor" not in user_input
            ):
                user_input["indoor_temperature_sensor"] = user_input.get(
                    "room_temp_entity", ""
                )
            # Convert UI inherit marker to storage empty
            if "indoor_temperature_sensor" in user_input:
                user_input["indoor_temperature_sensor"] = _convert_inherit_value(
                    user_input.get("indoor_temperature_sensor")
                )
            self._page1 = self._page1_process_submit(user_input, group_options_map)
        return await self.async_step_overrides()

    # ----- Page 2: Window overrides -----
    async def async_step_overrides(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Render window overrides (page 2)."""
        defaults: dict[str, Any] = {
            # For new windows, default all inheritable fields to "-1"
            "g_value": "-1",
            "frame_width": "-1",
            "tilt": "-1",
            "diffuse_factor": "-1",
            "threshold_direct": "-1",
            "threshold_diffuse": "-1",
            "temperature_indoor_base": "-1",
            "temperature_outdoor_base": "-1",
        }

        # Prefill from current subentry on reconfigure
        if self.source == config_entries.SOURCE_RECONFIGURE:
            sub = self._get_reconfigure_subentry()
            for k in defaults:
                val = sub.data.get(k)
                defaults[k] = val if val not in ("", None) else "-1"

        # Coerce all defaults to strings for Voluptuous schema compatibility
        def _ui_default(key: str) -> str:
            value = defaults.get(key, "")
            return str(value) if value not in ("", None) else ""

        schema_overrides: dict[Any, Any] = {}
        for key in (
            "g_value",
            "frame_width",
            "tilt",
            "diffuse_factor",
            "threshold_direct",
            "threshold_diffuse",
            "temperature_indoor_base",
            "temperature_outdoor_base",
        ):
            schema_overrides[
                vol.Optional(
                    key,
                    default=_ui_default(key),
                )
            ] = str

        schema = vol.Schema(schema_overrides)

        if user_input is None:
            return self.async_show_form(step_id="overrides", data_schema=schema)

        # Coerce numeric strings while allowing "" to clear
        # Coerce numeric strings while allowing "" and '-1' for inheritance
        if user_input is not None:
            coerce_map = {
                "g_value": allow_inherit_or_float(),
                "frame_width": allow_inherit_or_float(),
                "tilt": allow_inherit_or_float(),
                "diffuse_factor": allow_inherit_or_float(0.05, 0.5),
                "threshold_direct": allow_inherit_or_int(0, 1000),
                "threshold_diffuse": allow_inherit_or_int(0, 1000),
                "temperature_indoor_base": allow_inherit_or_float(10, 30),
                "temperature_outdoor_base": allow_inherit_or_float(10, 30),
            }
            for k, conv in coerce_map.items():
                if k in user_input:
                    user_input[k] = conv(user_input[k])

        self._page2 = user_input
        return await self.async_step_scenarios()

    # ----- Page 3: Scenario configuration -----
    async def async_step_scenarios(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Render window scenario configuration (page 3)."""
        defaults: dict[str, Any] = {
            # Für neue Fenster: alle Felder auf "-1"
            "scenario_b_temp_indoor": "-1",
            "scenario_b_temp_outdoor": "-1",
            "scenario_c_temp_indoor": "-1",
            "scenario_c_temp_outdoor": "-1",
            "scenario_c_temp_forecast": "-1",
            "scenario_c_start_hour": "-1",
        }

        # Prefill from current subentry on reconfigure
        if self.source == config_entries.SOURCE_RECONFIGURE:
            sub = self._get_reconfigure_subentry()
            for k in defaults:
                val = sub.data.get(k)
                defaults[k] = val if val not in ("", None) else "-1"

        # Coerce all defaults to strings for Voluptuous schema compatibility
        def _ui_default(key: str) -> str:
            value = defaults.get(key, "")
            return str(value) if value not in ("", None) else ""

        schema = vol.Schema(
            {
                vol.Optional(
                    "scenario_b_temp_indoor",
                    default=_ui_default("scenario_b_temp_indoor"),
                ): str,
                vol.Optional(
                    "scenario_b_temp_outdoor",
                    default=_ui_default("scenario_b_temp_outdoor"),
                ): str,
                vol.Optional(
                    "scenario_c_temp_indoor",
                    default=_ui_default("scenario_c_temp_indoor"),
                ): str,
                vol.Optional(
                    "scenario_c_temp_outdoor",
                    default=_ui_default("scenario_c_temp_outdoor"),
                ): str,
                vol.Optional(
                    "scenario_c_temp_forecast",
                    default=_ui_default("scenario_c_temp_forecast"),
                ): str,
                vol.Optional(
                    "scenario_c_start_hour",
                    default=_ui_default("scenario_c_start_hour"),
                ): str,
            }
        )

        if user_input is None:
            return self.async_show_form(step_id="scenarios", data_schema=schema)

        # Coerce numeric strings while allowing "" to clear
        # Coerce numeric strings while allowing "" and '-1' for inheritance
        coerce_map = {
            "scenario_b_temp_indoor": allow_inherit_or_float(10, 30),
            "scenario_b_temp_outdoor": allow_inherit_or_float(10, 30),
            "scenario_c_temp_indoor": allow_inherit_or_float(10, 30),
            "scenario_c_temp_outdoor": allow_inherit_or_float(10, 30),
            "scenario_c_temp_forecast": allow_inherit_or_float(15, 40),
            "scenario_c_start_hour": allow_inherit_or_int(0, 23),
        }
        for k, conv in coerce_map.items():
            if k in user_input:
                user_input[k] = conv(user_input[k])
        # No scenario enable here; those are entities

        # Merge all page data
        data = {
            **self._page1,
            **self._page2,
            **user_input,
            "entry_type": "window",
        }
        name = self._page1.get("name") or getattr(
            getattr(self, "subentry", None), "title", "Window"
        )

        if self.source == config_entries.SOURCE_RECONFIGURE:
            entry = self._get_entry()
            subentry = self._get_reconfigure_subentry()
            return self.async_update_and_abort(
                entry,
                subentry,
                title=name,
                data=data,
            )
        return self.async_create_entry(title=name, data=data)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Start reconfigure and reuse the same steps with defaults."""
        return await self.async_step_user(user_input)

    # (removed, now using shared get_temperature_sensor_entities)

    async def _get_group_subentries(self) -> list[tuple[str, str]]:
        """Return list of (subentry_id, title) for existing group subentries."""
        result: list[tuple[str, str]] = []
        # Iterate current entries to find the Group configurations parent
        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("entry_type") == ENTRY_TYPE_GROUPS:
                if entry.subentries:
                    for sub_id, sub in entry.subentries.items():
                        if sub.subentry_type == "group":
                            result.append((sub_id, sub.title or f"Group {sub_id}"))
                break
        return result


class SolarWindowSystemConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar Window System."""

    VERSION = 1
    _created = False
    # Storage for global flow pages
    _global_p1: dict[str, Any] | None = None
    _global_p2: dict[str, Any] | None = None

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[config_entries.ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        # Return only the subentry type relevant for this specific config entry
        if config_entry.data.get("entry_type") == ENTRY_TYPE_GROUPS:
            return {"group": GroupSubentryFlowHandler}
        if config_entry.data.get("entry_type") == ENTRY_TYPE_WINDOWS:
            return {"window": WindowSubentryFlowHandler}
        # No subentries for the global/root entry
        return {}

    async def async_step_user(self, _user_input: dict[str, Any] | None = None) -> Any:
        """Handle Add entry button and bootstrap missing parents as needed."""
        # Inspect current entries for this domain
        existing = list(self._async_current_entries())
        has_main = any(e.title == "Solar Window System" for e in existing)
        has_group_parent = any(
            e.data.get("entry_type") == ENTRY_TYPE_GROUPS for e in existing
        )
        has_window_parent = any(
            e.data.get("entry_type") == ENTRY_TYPE_WINDOWS for e in existing
        )

        # First-time setup from Integrations → Add: collect Global config first
        if not has_main and not has_group_parent and not has_window_parent:
            # Start multi-page global configuration flow
            self._global_p1 = {}
            self._global_p2 = {}
            return await self.async_step_global_basic()

        # If both parents exist already, inform user it's configured
        if has_group_parent and has_window_parent:
            return self.async_abort(reason="already_configured")

        # Create any missing parent entries, then inform user
        if not has_group_parent:
            await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "internal"},
                data={"entry_type": ENTRY_TYPE_GROUPS},
            )
        if not has_window_parent:
            await self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "internal"},
                data={"entry_type": ENTRY_TYPE_WINDOWS},
            )
        return self.async_abort(reason="created_missing_entries")

    async def async_step_internal(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Handle internal flow for creating sub-entries."""
        if user_input is None:
            return self.async_abort(reason="missing_data")

        entry_type = user_input.get("entry_type")
        if entry_type == ENTRY_TYPE_GROUPS:
            # Mark this entry as a subentry parent in the data
            return self.async_create_entry(
                title="Group configurations",
                data={"entry_type": ENTRY_TYPE_GROUPS, "is_subentry_parent": True},
            )
        if entry_type == ENTRY_TYPE_WINDOWS:
            # Mark this entry as a subentry parent in the data
            return self.async_create_entry(
                title="Window configurations",
                data={"entry_type": ENTRY_TYPE_WINDOWS, "is_subentry_parent": True},
            )

        return self.async_abort(reason="unknown_entry_type")

    # ----- Global configuration multi-page flow -----
    async def async_step_global_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Global configuration - Page 1 (basic)."""
        # Build selectors for sensors via HA entity selectors

        defaults = {
            "window_width": "",
            "window_height": "",
            "shadow_depth": "",
            "shadow_offset": "",
            "solar_radiation_sensor": "",
            "outdoor_temperature_sensor": "",
            "indoor_temperature_sensor": "",
            "forecast_temperature_sensor": "",
            "weather_warning_sensor": "",
            "update_interval": 1,
        }

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Optional(
                        "update_interval",
                        description={"suggested_value": defaults["update_interval"]},
                        default=defaults["update_interval"],
                    ): vol.Coerce(int),
                    vol.Required("window_width"): str,
                    vol.Required("window_height"): str,
                    vol.Required("shadow_depth"): str,
                    vol.Required("shadow_offset"): str,
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
                    vol.Required(
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
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"], device_class="temperature"
                        )
                    ),
                    vol.Optional(
                        "weather_warning_sensor",
                        description={
                            "suggested_value": defaults["weather_warning_sensor"]
                        },
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["binary_sensor", "input_boolean"]
                        )
                    ),
                }
            )
            return self.async_show_form(step_id="global_basic", data_schema=schema)

        # Validate/coerce required numbers with per-field errors (accept comma)
        errors: dict[str, str] = {}
        coerced: dict[str, Any] = {}

        def _check_float(field: str, min_v: float, max_v: float) -> None:
            raw = user_input.get(field)
            try:
                fv = _parse_float_locale(raw)
            except (ValueError, TypeError):
                errors[field] = "invalid_number"
                return
            if fv < min_v or fv > max_v:
                errors[field] = "number_out_of_range"
                return
            coerced[field] = fv

        def _check_int(field: str, min_v: int, max_v: int) -> None:
            raw = user_input.get(field)
            try:
                iv = _parse_int_locale(raw)
            except (ValueError, TypeError):
                errors[field] = "invalid_number"
                return
            if iv < min_v or iv > max_v:
                errors[field] = "number_out_of_range"
                return
            coerced[field] = iv

        _check_float("window_width", 0.1, 10)
        _check_float("window_height", 0.1, 10)
        _check_float("shadow_depth", 0, 5)
        _check_float("shadow_offset", 0, 5)
        _check_int("update_interval", 1, 1440)

        # Handle entity selectors properly: None means user cleared the field
        # Store None as "" for consistency with config entry data model
        # Required selectors must be present and non-empty
        for req_key in (
            "solar_radiation_sensor",
            "outdoor_temperature_sensor",
            "indoor_temperature_sensor",
        ):
            val = user_input.get(req_key)
            if val in (None, ""):
                errors[req_key] = "required"
            else:
                coerced[req_key] = val

        forecast_sensor = user_input.get("forecast_temperature_sensor")
        coerced["forecast_temperature_sensor"] = (
            "" if forecast_sensor is None else (forecast_sensor or "")
        )

        warning_sensor = user_input.get("weather_warning_sensor")
        coerced["weather_warning_sensor"] = (
            "" if warning_sensor is None else (warning_sensor or "")
        )

        if errors:
            schema = vol.Schema(
                {
                    vol.Optional(
                        "update_interval", default=user_input.get("update_interval", 1)
                    ): vol.Coerce(int),
                    vol.Required(
                        "window_width", default=user_input.get("window_width", "")
                    ): str,
                    vol.Required(
                        "window_height", default=user_input.get("window_height", "")
                    ): str,
                    vol.Required(
                        "shadow_depth", default=user_input.get("shadow_depth", "")
                    ): str,
                    vol.Required(
                        "shadow_offset", default=user_input.get("shadow_offset", "")
                    ): str,
                    vol.Required(
                        "solar_radiation_sensor",
                        default=user_input.get("solar_radiation_sensor", ""),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                        )
                    ),
                    vol.Required(
                        "outdoor_temperature_sensor",
                        default=user_input.get("outdoor_temperature_sensor", ""),
                    ): selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain=["sensor"],
                            device_class="temperature",
                        )
                    ),
                    vol.Optional(
                        "forecast_temperature_sensor",
                        default=user_input.get("forecast_temperature_sensor", ""),
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
                        default=user_input.get("weather_warning_sensor", ""),
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

        self._global_p1 = coerced
        return await self.async_step_global_enhanced()

    async def async_step_global_enhanced(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Global configuration - Page 2 (defaults with required values)."""
        defaults = {
            "g_value": 0.5,
            "frame_width": 0.125,
            "tilt": 90,
            "diffuse_factor": 0.15,
            "threshold_direct": 200,
            "threshold_diffuse": 150,
            "temperature_indoor_base": 23.0,
            "temperature_outdoor_base": 19.5,
        }
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required("g_value", default=str(defaults["g_value"])): str,
                    vol.Required(
                        "frame_width", default=str(defaults["frame_width"])
                    ): str,
                    vol.Required("tilt", default=str(defaults["tilt"])): str,
                    vol.Required(
                        "diffuse_factor", default=str(defaults["diffuse_factor"])
                    ): str,
                    vol.Required(
                        "threshold_direct", default=str(defaults["threshold_direct"])
                    ): str,
                    vol.Required(
                        "threshold_diffuse", default=str(defaults["threshold_diffuse"])
                    ): str,
                    vol.Required(
                        "temperature_indoor_base",
                        default=str(defaults["temperature_indoor_base"]),
                    ): str,
                    vol.Required(
                        "temperature_outdoor_base",
                        default=str(defaults["temperature_outdoor_base"]),
                    ): str,
                }
            )
            return self.async_show_form(step_id="global_enhanced", data_schema=schema)

        # Validate with per-field errors and locale-aware parsing
        errors2: dict[str, str] = {}
        coerced2: dict[str, Any] = {}

        def _check_float(field: str, min_v: float, max_v: float) -> None:
            raw = user_input.get(field)
            try:
                fv = _parse_float_locale(raw)
            except (ValueError, TypeError):
                errors2[field] = "invalid_number"
                return
            if fv < min_v or fv > max_v:
                errors2[field] = "number_out_of_range"
                return
            coerced2[field] = fv

        def _check_int(field: str, min_v: int, max_v: int) -> None:
            raw = user_input.get(field)
            try:
                iv = _parse_int_locale(raw)
            except (ValueError, TypeError):
                errors2[field] = "invalid_number"
                return
            if iv < min_v or iv > max_v:
                errors2[field] = "number_out_of_range"
                return
            coerced2[field] = iv

        _check_float("g_value", 0.1, 0.9)
        _check_float("frame_width", 0.05, 0.3)
        _check_int("tilt", 0, 90)
        _check_float("diffuse_factor", 0.05, 0.5)
        _check_int("threshold_direct", 0, 1000)
        _check_int("threshold_diffuse", 0, 1000)
        _check_float("temperature_indoor_base", 10, 30)
        _check_float("temperature_outdoor_base", 10, 30)

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

        self._global_p2 = coerced2
        return await self.async_step_global_scenarios()

    async def async_step_global_scenarios(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        """Global configuration - Page 3 (scenario thresholds)."""
        defaults = {
            "scenario_b_temp_indoor": 23.5,
            "scenario_b_temp_outdoor": 25.5,
            "scenario_c_temp_indoor": 21.5,
            "scenario_c_temp_outdoor": 24.0,
            "scenario_c_temp_forecast": 28.5,
            "scenario_c_start_hour": 9,
        }
        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(
                        "scenario_b_temp_indoor",
                        default=str(defaults["scenario_b_temp_indoor"]),
                    ): str,
                    vol.Required(
                        "scenario_b_temp_outdoor",
                        default=str(defaults["scenario_b_temp_outdoor"]),
                    ): str,
                    vol.Required(
                        "scenario_c_temp_indoor",
                        default=str(defaults["scenario_c_temp_indoor"]),
                    ): str,
                    vol.Required(
                        "scenario_c_temp_outdoor",
                        default=str(defaults["scenario_c_temp_outdoor"]),
                    ): str,
                    vol.Required(
                        "scenario_c_temp_forecast",
                        default=str(defaults["scenario_c_temp_forecast"]),
                    ): str,
                    vol.Required(
                        "scenario_c_start_hour",
                        default=str(defaults["scenario_c_start_hour"]),
                    ): str,
                }
            )
            return self.async_show_form(step_id="global_scenarios", data_schema=schema)

        # Validate with per-field errors and locale-aware parsing
        errors3: dict[str, str] = {}
        coerced3: dict[str, Any] = {}

        def _check_float(field: str, min_v: float, max_v: float) -> None:
            raw = user_input.get(field)
            try:
                fv = _parse_float_locale(raw)
            except (ValueError, TypeError):
                errors3[field] = "invalid_number"
                return
            if fv < min_v or fv > max_v:
                errors3[field] = "number_out_of_range"
                return
            coerced3[field] = fv

        def _check_int(field: str, min_v: int, max_v: int) -> None:
            raw = user_input.get(field)
            try:
                iv = _parse_int_locale(raw)
            except (ValueError, TypeError):
                errors3[field] = "invalid_number"
                return
            if iv < min_v or iv > max_v:
                errors3[field] = "number_out_of_range"
                return
            coerced3[field] = iv

        _check_float("scenario_b_temp_indoor", 10, 30)
        _check_float("scenario_b_temp_outdoor", 10, 30)
        _check_float("scenario_c_temp_indoor", 10, 30)
        _check_float("scenario_c_temp_outdoor", 10, 30)
        _check_float("scenario_c_temp_forecast", 15, 40)
        _check_int("scenario_c_start_hour", 0, 23)

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

        # Combine and create entries
        data = {
            **(self._global_p1 or {}),
            **(self._global_p2 or {}),
            **coerced3,
            "entry_type": ENTRY_TYPE_GLOBAL,
        }
        # Create the subentry parent entries
        await self._create_entries()
        self._created = True
        return self.async_create_entry(title="Solar Window System", data=data)

    def _already_configured(self) -> bool:
        """Check if the integration is already configured."""
        return any(entry.domain == DOMAIN for entry in self._async_current_entries())

    async def _create_entries(self) -> None:
        """Create the three required entries."""
        # Create Group configurations entry
        await self.hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "internal"},
            data={"entry_type": ENTRY_TYPE_GROUPS},
        )

        # Create Window configurations entry
        await self.hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "internal"},
            data={"entry_type": ENTRY_TYPE_WINDOWS},
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return options flow handler; route steps by entry type inside the flow."""
        # Hand off to the dedicated OptionsFlow which will route by entry type
        return SolarWindowSystemOptionsFlow(config_entry)


class _NoOpOptionsFlow(config_entries.OptionsFlow):
    """Options flow that immediately aborts for unsupported entries."""

    async def async_step_init(
        self, _user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        return self.async_abort(reason="not_supported")
