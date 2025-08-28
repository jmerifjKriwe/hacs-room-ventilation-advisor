"""
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""

import logging
import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, NamedTuple

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)


class SolarCalculationError(HomeAssistantError):
    """Exception for solar calculation errors."""


@dataclass
class WindowCalculationResult:
    """Results from solar power calculation for a window."""

    power_total: float
    power_direct: float
    power_diffuse: float
    shadow_factor: float
    is_visible: bool
    area_m2: float
    shade_required: bool
    shade_reason: str
    effective_threshold: float


class ShadeRequestFlow(NamedTuple):
    """Parameters for flow-based shading decision."""

    window_data: dict[str, Any]
    effective_config: dict[str, Any]
    external_states: dict[str, Any]
    scenario_b_enabled: bool
    scenario_c_enabled: bool
    solar_result: "WindowCalculationResult"


class SolarWindowCalculator:
    def _calculate_shadow_factor(
        self,
        sun_elevation: float,
        sun_azimuth: float,
        window_azimuth: float,
        shadow_depth: float,
        shadow_offset: float,
    ) -> float:
        """
        Calculate the geometric shadow factor for a window.
        Returns a value between 0.1 (full shadow) and 1.0 (no shadow).
        """
        # If no shadow geometry, return 1.0 (no shadow)
        if shadow_depth <= 0 and shadow_offset <= 0:
            return 1.0

        # Projected shadow length on the window plane
        # sun_elevation in degrees, convert to radians
        sun_el_rad = math.radians(sun_elevation)
        if sun_el_rad <= 0:
            return 1.0  # sun below horizon, no shadow

        # Calculate the angle difference between sun and window azimuth
        az_diff = ((sun_azimuth - window_azimuth + 180) % 360) - 180
        az_factor = max(
            0.0, math.cos(math.radians(az_diff))
        )  # 1.0 = direct, 0.0 = perpendicular

        # Shadow length: shadow_depth / tan(sun_elevation)
        try:
            shadow_length = shadow_depth / max(math.tan(sun_el_rad), 1e-3)
        except Exception:
            shadow_length = 0.0

        # Effective shadow on window: shadow_length - shadow_offset
        effective_shadow = max(0.0, shadow_length - shadow_offset)

        # Heuristic: if effective_shadow is large, strong shadow; if small, weak shadow
        # For simplicity, assume window height = 1.0m (normalized)
        window_height = 1.0
        if effective_shadow <= 0:
            return 1.0  # no shadow
        if effective_shadow >= window_height:
            return 0.1  # full shadow (minimum factor)
        # Linear interpolation between 1.0 (no shadow) and 0.1 (full shadow)
        factor = 1.0 - 0.9 * (effective_shadow / window_height)
        # Angle dependency: more shadow if sun is direct, less if angled
        factor = factor * az_factor + (1.0 - az_factor)
        return max(0.1, min(1.0, factor))

    def __init__(
        self, hass, defaults_config=None, groups_config=None, windows_config=None
    ):
        self.hass = hass
        self.defaults = defaults_config or {}
        self.groups = groups_config or {}
        self.windows = windows_config or {}

        # Flow-based attributes - will be set by __init_flow_based__
        self.global_entry = None
        self._entity_cache: dict[str, Any] = {}
        self._cache_timestamp: float | None = None
        self._cache_ttl = 30  # 30 seconds cache for one calculation run

        _LOGGER.debug("Calculator initialized with %s windows.", len(self.windows))

    def get_safe_state(self, entity_id: str, default: str | float = 0):
        """
        Safely get the state of an entity, returning a default if it is
        unavailable, unknown, or not found.
        """
        if not entity_id:
            return default

        state = self.hass.states.get(entity_id)

        if state is None or state.state in ["unknown", "unavailable"]:
            _LOGGER.warning(
                "Entity %s not found or unavailable, returning default value.",
                entity_id,
            )
            return default

        return state.state

    def get_safe_attr(self, entity_id: str, attr: str, default: str | float = 0):
        """Safely get an attribute of an entity, returning a default if unavailable."""
        if not entity_id:
            return default

        state = self.hass.states.get(entity_id)

        if state is None or state.state in ["unknown", "unavailable"]:
            _LOGGER.warning(
                "Entity %s not found or unavailable, returning default value for attribute %s.",
                entity_id,
                attr,
            )
            return default

        return state.attributes.get(attr, default)

    def apply_global_factors(
        self, config: dict[str, Any], group_type: str, states: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply global sensitivity and offset factors to configuration, robust gegen ungültige Werte."""

        def safe_float(val, default=0.0):
            if val in ("", None, "inherit", "-1", -1):
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        # Schwellenwerte robust casten
        config["thresholds"]["direct"] = safe_float(
            config["thresholds"].get("direct", 200), 200
        )
        config["thresholds"]["diffuse"] = safe_float(
            config["thresholds"].get("diffuse", 150), 150
        )

        sensitivity = safe_float(states.get("sensitivity", 1.0), 1.0)
        config["thresholds"]["direct"] /= sensitivity
        config["thresholds"]["diffuse"] /= sensitivity

        if group_type == "children":
            factor = safe_float(states.get("children_factor", 1.0), 1.0)
            config["thresholds"]["direct"] *= factor
            config["thresholds"]["diffuse"] *= factor

        # Temperaturen robust casten
        config["temperatures"]["indoor_base"] = safe_float(
            config["temperatures"].get("indoor_base", 23.0), 23.0
        )
        config["temperatures"]["outdoor_base"] = safe_float(
            config["temperatures"].get("outdoor_base", 19.5), 19.5
        )

        temp_offset = safe_float(states.get("temperature_offset", 0.0), 0.0)
        config["temperatures"]["indoor_base"] += temp_offset
        config["temperatures"]["outdoor_base"] += temp_offset

        return config

    # ==== NEW FLOW-BASED METHODS ====

    @classmethod
    def from_flows(
        cls, hass: HomeAssistant, entry: ConfigEntry
    ) -> "SolarWindowCalculator":
        """Create calculator instance from flow-based configuration."""
        # Create instance with empty windows list first
        instance = cls(hass, [], {})

        # Set up flow-based configuration
        instance.global_entry = entry

        # Initialize caching
        instance._entity_cache = {}
        instance._cache_timestamp = None
        instance._cache_ttl = 30  # 30 seconds cache for one calculation run

        _LOGGER.debug("Calculator initialized with flow-based configuration.")
        return instance

    def _get_cached_entity_state(
        self, entity_id: str, default_value: Any = None, debug_label: str = None
    ) -> Any:
        """Get entity state with short-term caching for one calculation run, with debug logging."""
        current_time = time.time()

        # Check if cache is expired
        if (
            self._cache_timestamp is None
            or current_time - self._cache_timestamp > self._cache_ttl
        ):
            self._entity_cache.clear()
            self._cache_timestamp = current_time

        # Check cache first
        if entity_id in self._entity_cache:
            value = self._entity_cache[entity_id]
        else:
            # Get from HomeAssistant
            state = self.hass.states.get(entity_id)
            value = state.state if state else default_value
            # Cache the result
            self._entity_cache[entity_id] = value
        return value

    def _resolve_entity_state_with_fallback(
        self, entity_id: str, fallback: str, valid_states: set[str]
    ) -> str:
        """Resolve entity state with validation and fallback."""
        state = self._get_cached_entity_state(entity_id, fallback)
        if state in valid_states:
            return state
        _LOGGER.warning(
            "Invalid state '%s' for entity %s, using fallback '%s'",
            state,
            entity_id,
            fallback,
        )
        return fallback

    def _get_subentries_by_type(self, entry_type: str) -> dict[str, dict[str, Any]]:
        """Get all sub-entries of a specific type. Handles legacy, new type names, and subentries in parent configs."""
        subentries = {}

        # Map legacy and new type names for global config
        entry_type_map = {
            "global": ["global_config"],  # Standardized to global_config only
            "group": ["group"],
            "window": ["window"],
            "group_configs": ["group_configs"],
            "window_configs": ["window_configs"],
        }
        valid_types = entry_type_map.get(entry_type, [entry_type])

        # Get all config entries for this domain
        domain_entries = self.hass.config_entries.async_entries("solar_window_system")

        for entry in domain_entries:
            # Direct match (classic style)
            if entry.data.get("entry_type") in valid_types:
                subentries[entry.entry_id] = entry.data

            # For window/group: also check subentries in parent configs
            if entry_type in ("window", "group") and hasattr(entry, "subentries"):
                for sub in entry.subentries.values():
                    # Support ConfigSubentry objects (Home Assistant 2024+) and dicts (legacy)
                    if hasattr(sub, "data") and hasattr(sub, "subentry_type"):
                        sub_data = (
                            dict(sub.data) if hasattr(sub.data, "items") else sub.data
                        )
                        sub_type = getattr(sub, "subentry_type", None) or sub_data.get(
                            "entry_type"
                        )
                        sub_id = getattr(sub, "subentry_id", None) or getattr(
                            sub, "title", None
                        )
                    elif isinstance(sub, dict):
                        sub_data = sub.get("data", {})
                        sub_type = sub_data.get("entry_type") or sub.get(
                            "subentry_type"
                        )
                        sub_id = sub.get("subentry_id") or sub.get("title")
                    else:
                        continue  # skip unknown subentry type
                    if (
                        sub_type == entry_type
                        or sub_data.get("entry_type") == entry_type
                    ) and sub_id:
                        subentries[sub_id] = sub_data

        return subentries

    def get_effective_config_from_flows(
        self, window_subentry_id: str
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Get effective configuration using flow-based inheritance."""
        # Get all relevant subentries
        windows = self._get_subentries_by_type("window")
        groups = self._get_subentries_by_type("group")

        if window_subentry_id not in windows:
            msg = f"Window configuration not found: {window_subentry_id}"
            raise ValueError(msg)

        window_data = windows[window_subentry_id]

        # Start with global configuration (merged from data and options)
        global_config = self._get_global_data_merged()
        global_sources = {}
        if global_config:
            # Mark all values as coming from global
            global_sources = self._mark_config_sources(global_config, "global")

        # Apply group configuration if linked
        group_config = {}
        group_sources = {}
        linked_group_id = window_data.get("linked_group_id")
        if linked_group_id and linked_group_id in groups:
            group_config = groups[linked_group_id]
            group_sources = self._mark_config_sources(group_config, "group")

        # Build effective configuration
        effective_config = self._build_effective_config(
            global_config, group_config, window_data
        )

        # Build source tracking
        effective_sources = self._build_effective_sources(
            global_sources, group_sources, window_data
        )

        return effective_config, effective_sources

    def _mark_config_sources(
        self, config: dict[str, Any], source: str
    ) -> dict[str, Any]:
        """Mark all configuration values with their source."""
        sources = {}
        for key, value in config.items():
            if isinstance(value, dict):
                sources[key] = self._mark_config_sources(value, source)
            else:
                sources[key] = source
        return sources

    def _build_effective_config(
        self,
        global_config: dict[str, Any],
        group_config: dict[str, Any],
        window_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Build effective configuration with inheritance, respecting explicit inheritance markers."""

        def is_inherit_marker(val):
            return val in ("-1", -1, "", None, "inherit")

        # Start with global as base
        effective = {}

        # Copy all global config
        for key, value in global_config.items():
            if isinstance(value, dict):
                effective[key] = value.copy()
            else:
                effective[key] = value

        # Override with group config, but skip inherit markers
        for key, value in group_config.items():
            if is_inherit_marker(value):
                continue
            if (
                key in effective
                and isinstance(effective[key], dict)
                and isinstance(value, dict)
            ):
                # Nested dict: update only non-inherit values
                for subkey, subval in value.items():
                    if not is_inherit_marker(subval):
                        effective[key][subkey] = subval
            else:
                effective[key] = value

        # Override with window-specific data, but skip inherit markers
        for key, value in window_data.items():
            if is_inherit_marker(value):
                continue
            if (
                key in effective
                and isinstance(effective[key], dict)
                and isinstance(value, dict)
            ):
                for subkey, subval in value.items():
                    if not is_inherit_marker(subval):
                        effective[key][subkey] = subval
            else:
                effective[key] = value

        # Structure flat config into expected nested format for apply_global_factors
        return self._structure_flat_config(effective)

    def _structure_flat_config(self, flat_config: dict[str, Any]) -> dict[str, Any]:
        """Structure flat config into nested format expected by apply_global_factors."""
        structured = {
            "thresholds": {
                "direct": flat_config.get("threshold_direct", 200),
                "diffuse": flat_config.get("threshold_diffuse", 150),
            },
            "temperatures": {
                "indoor_base": flat_config.get("temperature_indoor_base", 23.0),
                "outdoor_base": flat_config.get("temperature_outdoor_base", 19.5),
            },
            "physical": {
                "g_value": flat_config.get("g_value", 0.5),
                "frame_width": flat_config.get("frame_width", 0.125),
                "diffuse_factor": flat_config.get("diffuse_factor", 0.15),
                "tilt": flat_config.get("tilt", 90.0),
            },
        }

        # Add remaining flat config items not in structured categories
        excluded_keys = {
            "threshold_direct",
            "threshold_diffuse",
            "temperature_indoor_base",
            "temperature_outdoor_base",
            "g_value",
            "frame_width",
            "diffuse_factor",
            "tilt",
        }
        structured.update(
            {
                key: value
                for key, value in flat_config.items()
                if key not in excluded_keys
            }
        )

        return structured

    def _build_effective_sources(
        self,
        global_sources: dict[str, Any],
        group_sources: dict[str, Any],
        window_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Build source tracking for effective configuration."""
        sources = global_sources.copy()

        # Update with group sources
        for key, value in group_sources.items():
            if (
                key in sources
                and isinstance(sources[key], dict)
                and isinstance(value, dict)
            ):
                sources[key].update(value)
            else:
                sources[key] = value

        # Mark window data as window source
        window_sources = self._mark_config_sources(window_data, "window")
        for key, value in window_sources.items():
            if (
                key in sources
                and isinstance(sources[key], dict)
                and isinstance(value, dict)
            ):
                sources[key].update(value)
            else:
                sources[key] = value

        return sources

    def _get_global_data_merged(self) -> dict[str, Any]:
        """Get merged global data from global config entry and entities."""
        # Get global config data (merge data and options with options priority)
        global_data = {}
        global_configs = self._get_subentries_by_type("global")

        if global_configs:
            global_entry_id = next(iter(global_configs))
            global_data = global_configs[global_entry_id].copy()

            # Find config entry and merge options over data (options have priority)
            for entry in self.hass.config_entries.async_entries("solar_window_system"):
                entry_type = entry.data.get("entry_type")

                # Check for global_config only (standardized)
                if entry_type in ["global_config"]:
                    # Start with data as base
                    merged_config = dict(entry.data)

                    # Options override data (priority system)
                    if entry.options:
                        merged_config.update(entry.options)

                    # Now replace the global_data with merged config
                    global_data = merged_config
                    break

        return global_data

    def calculate_window_solar_power_with_shadow(
        self,
        effective_config: dict[str, Any],
        window_data: dict[str, Any],
        states: dict[str, Any],
    ) -> WindowCalculationResult:
        """
        Calculate solar power for a window including shadow effects.

        Args:
            effective_config: Effective configuration after inheritance
            window_data: Window-specific data from subentry
            states: External state data (sun position, etc.)

        Returns:
            WindowCalculationResult with calculated values

        """

        def safe_float(val, default=0.0):
            if val in ("", None, "inherit", "-1", -1):
                return default
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        solar_radiation = safe_float(states.get("solar_radiation", 0.0), 0.0)
        sun_azimuth = safe_float(states.get("sun_azimuth", 0.0), 0.0)
        sun_elevation = safe_float(states.get("sun_elevation", 0.0), 0.0)

        # Thresholds for minimum radiation and elevation
        MIN_RADIATION = 1e-3
        MIN_ELEVATION = 0.0

        # Check if minimums are met; if not, skip calculation
        if solar_radiation < MIN_RADIATION or sun_elevation < MIN_ELEVATION:
            return WindowCalculationResult(
                power_total=0.0,
                power_direct=0.0,
                power_diffuse=0.0,
                shadow_factor=1.0,
                is_visible=False,
                area_m2=0.0,
                shade_required=False,
                shade_reason="",
                effective_threshold=effective_config["thresholds"]["direct"],
            )

        # Physical parameters (robust cast)
        g_value = safe_float(effective_config["physical"].get("g_value", 0.5), 0.5)
        frame_width = safe_float(
            effective_config["physical"].get("frame_width", 0.125), 0.125
        )
        diffuse_factor = safe_float(
            effective_config["physical"].get("diffuse_factor", 0.15), 0.15
        )
        tilt = safe_float(effective_config["physical"].get("tilt", 90.0), 90.0)

        # Window dimensions and area calculation
        window_width = safe_float(window_data.get("window_width", 1.0), 1.0)
        window_height = safe_float(window_data.get("window_height", 1.0), 1.0)
        glass_width = max(0, window_width - 2 * frame_width)
        glass_height = max(0, window_height - 2 * frame_width)
        area = glass_width * glass_height

        # Shadow parameters (robust cast)
        shadow_depth = safe_float(window_data.get("shadow_depth", 0), 0.0)
        shadow_offset = safe_float(window_data.get("shadow_offset", 0), 0.0)

        # Calculate diffuse power (not affected by shadows)
        power_diffuse = solar_radiation * diffuse_factor * area * g_value
        power_direct = 0
        is_visible = False
        shadow_factor = 1.0

        _LOGGER.debug(
            "Solar Power Calculation for %s: sun_el=%.1f°, sun_az=%.1f°, "
            "window_az=%.1f°, shadow_depth=%.2fm, shadow_offset=%.2fm",
            window_data.get("name", "Unknown"),
            sun_elevation,
            sun_azimuth,
            safe_float(window_data.get("azimuth", 180), 180.0),
            shadow_depth,
            shadow_offset,
        )

        # Check if sun is visible to window (robust cast)
        elevation_min = safe_float(window_data.get("elevation_min", 0), 0.0)
        elevation_max = safe_float(window_data.get("elevation_max", 90), 90.0)
        azimuth_min = safe_float(window_data.get("azimuth_min", -90), -90.0)
        azimuth_max = safe_float(window_data.get("azimuth_max", 90), 90.0)
        window_azimuth = safe_float(window_data.get("azimuth", 180), 180.0)

        if elevation_min <= sun_elevation <= elevation_max:
            az_diff = ((sun_azimuth - window_azimuth + 180) % 360) - 180
            if azimuth_min <= az_diff <= azimuth_max:
                is_visible = True
                _LOGGER.debug("Sun is VISIBLE to the window.")

                # Calculate basic direct solar power
                sun_el_rad = math.radians(sun_elevation)
                sun_az_rad = math.radians(sun_azimuth)
                win_az_rad = math.radians(window_azimuth)
                tilt_rad = math.radians(tilt)

                cos_incidence = math.sin(sun_el_rad) * math.cos(tilt_rad) + math.cos(
                    sun_el_rad
                ) * math.sin(tilt_rad) * math.cos(sun_az_rad - win_az_rad)

                if cos_incidence > 0 and sun_el_rad > 0:
                    power_direct = (
                        (
                            solar_radiation
                            * (1 - diffuse_factor)
                            * cos_incidence
                            / math.sin(sun_el_rad)
                        )
                        * area
                        * g_value
                    )

                    # Apply shadow calculation
                    if shadow_depth > 0 or shadow_offset > 0:
                        shadow_factor = self._calculate_shadow_factor(
                            sun_elevation,
                            sun_azimuth,
                            window_azimuth,
                            shadow_depth,
                            shadow_offset,
                        )
                        power_direct *= shadow_factor
                        _LOGGER.debug("Shadow factor applied: %.2f", shadow_factor)

        _LOGGER.debug(
            "Power calculation result: direct=%.2fW, diffuse=%.2fW, "
            "total=%.2fW, shadow_factor=%.2f",
            power_direct,
            power_diffuse,
            power_direct + power_diffuse,
            shadow_factor,
        )

        return WindowCalculationResult(
            power_total=power_direct + power_diffuse,
            power_direct=power_direct,
            power_diffuse=power_diffuse,
            shadow_factor=shadow_factor,
            is_visible=is_visible,
            area_m2=area,
            shade_required=False,  # Will be set by shading logic
            shade_reason="",  # Will be set by shading logic
            effective_threshold=effective_config["thresholds"]["direct"],
        )

    def calculate_all_windows_from_flows(self) -> dict[str, Any]:
        """
        Calculate all window shading requirements using flow-based configuration.

        Returns:
            Dictionary with calculation results for all windows

        """
        # Clear cache at start of calculation run
        self._entity_cache.clear()
        self._cache_timestamp = time.time()

        global_data = self._get_global_data_merged()
        # Determine whether this coordinator should calculate windows. Only
        # coordinators with entry_type == 'window_configs' do calculations.
        entry_type = getattr(self.global_entry, "data", {}).get("entry_type", "")
        should_calculate_windows = entry_type == "window_configs"

        # If this coordinator isn't responsible for windows, return all windows with shade_required: False
        if not should_calculate_windows:
            _LOGGER.debug(
                "Skipping calculations: entry_type '%s' does not calculate windows",
                entry_type,
            )
            windows = self._get_subentries_by_type("window")
            return {"windows": {k: {"shade_required": False} for k in windows}}

        # Get all window subentries; if none exist, return all windows with shade_required: False
        windows = self._get_subentries_by_type("window")
        if not windows:
            _LOGGER.debug("No window subentries found; skipping calculations.")
            return {"windows": {}}

        # Get external states (only when there are windows to calculate)
        # Debug: log which entity IDs are being used for external states
        _LOGGER.debug(
            "Using entity IDs: solar_radiation='%s', outdoor_temp='%s', "
            "forecast_temp='%s', weather_warning='%s'",
            global_data.get("solar_radiation_sensor", ""),
            global_data.get("outdoor_temperature_sensor", ""),
            global_data.get("weather_forecast_temperature_sensor", ""),
            global_data.get("weather_warning_sensor", ""),
        )

        external_states = {
            "sensitivity": global_data.get("global_sensitivity", 1.0),
            "children_factor": global_data.get("children_factor", 0.8),
            "temperature_offset": global_data.get("temperature_offset", 0.0),
            "scenario_b_enabled": global_data.get("scenario_b_enabled", False),
            "scenario_c_enabled": global_data.get("scenario_c_enabled", False),
            "debug_mode": global_data.get("debug_mode", False),
            "maintenance_mode": global_data.get("maintenance_mode", False),
            "solar_radiation": float(
                self._get_cached_entity_state(
                    global_data.get("solar_radiation_sensor", ""), 0, "solar_radiation"
                )
            ),
            "sun_azimuth": float(self.get_safe_attr("sun.sun", "azimuth", 0)),
            "sun_elevation": float(self.get_safe_attr("sun.sun", "elevation", 0)),
            "outdoor_temp": float(
                self._get_cached_entity_state(
                    global_data.get("outdoor_temperature_sensor", ""), 0, "outdoor_temp"
                )
            ),
            "forecast_temp": float(
                self._get_cached_entity_state(
                    global_data.get("weather_forecast_temperature_sensor", ""),
                    0,
                    "forecast_temp",
                )
            ),
            "weather_warning": self._get_cached_entity_state(
                global_data.get("weather_warning_sensor", ""), "off", "weather_warning"
            )
            == "on",
        }

        _LOGGER.debug("External states: %s", external_states)

        window_results = {}
        total_power = 0
        shading_count = 0

        # Check if calculation conditions are met (minimum radiation/elevation)
        min_radiation = external_states.get("solar_radiation", 0.0)
        min_elevation = external_states.get("sun_elevation", 0.0)
        if min_radiation < 1e-3 or min_elevation < 0.0:
            for window_subentry_id, window_data in windows.items():
                window_results[window_subentry_id] = {
                    "name": window_data.get("name", window_subentry_id),
                    "shade_required": False,
                }
            return {"windows": window_results}

        for window_subentry_id, window_data in windows.items():
            try:
                # Get effective configuration and sources
                effective_config, effective_sources = (
                    self.get_effective_config_from_flows(window_subentry_id)
                )

                # Apply global factors
                group_type = window_data.get("group_type", "default")
                effective_config = self.apply_global_factors(
                    effective_config, group_type, external_states
                )

                # Debug-Ausgabe: Vererbungs- und Wertestruktur
                def flatten_dict(d, parent_key="", sep="."):
                    items = []
                    for k, v in d.items():
                        new_key = f"{parent_key}{sep}{k}" if parent_key else k
                        if isinstance(v, dict):
                            items.extend(flatten_dict(v, new_key, sep=sep).items())
                        else:
                            items.append((new_key, v))
                    return dict(items)

                flat_window = flatten_dict(window_data)
                flat_group = (
                    flatten_dict(group_config) if "group_config" in locals() else {}
                )
                flat_global = flatten_dict(global_data)
                flat_effective = flatten_dict(effective_config)
                flat_sources = flatten_dict(effective_sources)

                # Welche Werte sind im Fenster gesetzt?
                window_set = {
                    k: v
                    for k, v in flat_window.items()
                    if v not in ("-1", -1, "", None, "inherit")
                }
                # Welche Werte werden aus Gruppe geerbt?
                group_inherited = {
                    k: flat_group.get(k)
                    for k, src in flat_sources.items()
                    if src == "group" and k not in window_set
                }
                # Welche Werte werden aus Global geerbt?
                global_inherited = {
                    k: flat_global.get(k)
                    for k, src in flat_sources.items()
                    if src == "global"
                    and k not in window_set
                    and k not in group_inherited
                }
                # Aggregierter View: finale Werte
                final_view = flat_effective

                _LOGGER.debug(
                    "[DEBUG-VERERBUNG] Fenster '%s':\n  Fenster-spezifisch: %s\n  Geerbt (Gruppe): %s\n  Geerbt (Global): %s\n  Final genutzt: %s",
                    window_data.get("name", window_subentry_id),
                    window_set,
                    group_inherited,
                    global_inherited,
                    final_view,
                )

                # Calculate solar power with shadows
                solar_result = self.calculate_window_solar_power_with_shadow(
                    effective_config, window_data, external_states
                )

                # Get scenario enables for this window with inheritance logic
                (
                    scenario_b_enabled,
                    scenario_c_enabled,
                ) = self._get_scenario_enables_from_flows(
                    window_subentry_id, external_states
                )

                # Check shading requirement with full scenario logic
                shade_request = ShadeRequestFlow(
                    window_data=window_data,
                    effective_config=effective_config,
                    external_states=external_states,
                    scenario_b_enabled=scenario_b_enabled,
                    scenario_c_enabled=scenario_c_enabled,
                    solar_result=solar_result,
                )
                shade_required, shade_reason = self._should_shade_window_from_flows(
                    shade_request
                )

                # Update result
                solar_result.shade_required = shade_required
                solar_result.shade_reason = shade_reason

                # Calculate additional metrics
                power_raw = (
                    solar_result.power_direct / solar_result.shadow_factor
                    + solar_result.power_diffuse
                    if solar_result.shadow_factor > 0
                    else solar_result.power_total
                )
                # Avoid division by zero
                area = solar_result.area_m2 if solar_result.area_m2 > 0 else 1

                # Store results in the correct structure for coordinator
                window_results[window_subentry_id] = {
                    "name": window_data.get("name", window_subentry_id),
                    "total_power": round(solar_result.power_total, 2),
                    "total_power_direct": round(solar_result.power_direct, 2),
                    "total_power_diffuse": round(solar_result.power_diffuse, 2),
                    "total_power_raw": round(power_raw, 2),
                    "power_m2_total": round(solar_result.power_total / area, 2),
                    "power_m2_direct": round(solar_result.power_direct / area, 2),
                    "power_m2_diffuse": round(solar_result.power_diffuse / area, 2),
                    "power_m2_raw": round(power_raw / area, 2),
                    "shadow_factor": solar_result.shadow_factor,
                    "area_m2": solar_result.area_m2,
                    "is_visible": solar_result.is_visible,
                    "shade_required": solar_result.shade_required,
                    "shade_reason": solar_result.shade_reason,
                    "effective_threshold": solar_result.effective_threshold,
                }

                total_power += solar_result.power_total
                if shade_required:
                    shading_count += 1

            except Exception as err:
                _LOGGER.exception("Error calculating window %s", window_subentry_id)
                window_results[window_subentry_id] = {
                    "name": window_data.get("name", window_subentry_id),
                    "total_power": 0,
                    "total_power_direct": 0,
                    "total_power_diffuse": 0,
                    "total_power_raw": 0,
                    "power_m2_total": 0,
                    "power_m2_direct": 0,
                    "power_m2_diffuse": 0,
                    "power_m2_raw": 0,
                    "shadow_factor": 0,
                    "area_m2": 0,
                    "is_visible": False,
                    "shade_required": False,
                    "shade_reason": f"Calculation error: {err}",
                    "effective_threshold": 0,
                }
        # (no-op) calculations completed for windows

        # Calculate group aggregations
        group_results = {}
        groups = self._get_subentries_by_type("group")

        for group_id, group_data in groups.items():
            group_name = group_data.get("name", group_id)
            group_total_power = 0
            group_total_direct = 0
            group_total_diffuse = 0

            # Sum up all windows linked to this group
            for window_id, window_result in window_results.items():
                # Check if window is linked to this group (via window config)
                window_config = windows.get(window_id, {})
                if window_config.get("linked_group_id") == group_id:
                    group_total_power += window_result["total_power"]
                    group_total_direct += window_result["total_power_direct"]
                    group_total_diffuse += window_result["total_power_diffuse"]

            group_results[group_id] = {
                "name": group_name,
                "total_power": round(group_total_power, 2),
                "total_power_direct": round(group_total_direct, 2),
                "total_power_diffuse": round(group_total_diffuse, 2),
            }

        # Calculate system-wide totals
        total_power_direct = sum(
            w["total_power_direct"] for w in window_results.values()
        )
        total_power_diffuse = sum(
            w["total_power_diffuse"] for w in window_results.values()
        )
        windows_with_shading = sum(
            1 for w in window_results.values() if w["shade_required"]
        )

        # Return results in the structure expected by coordinator
        results = {
            "windows": window_results,
            "groups": group_results,
            "summary": {
                "total_power": round(total_power, 2),
                "total_power_direct": round(total_power_direct, 2),
                "total_power_diffuse": round(total_power_diffuse, 2),
                "windows_with_shading": windows_with_shading,
                "window_count": len(windows),
                "shading_count": shading_count,
                "calculation_time": datetime.now(UTC).isoformat(),
            },
        }

        _LOGGER.debug("calculation cycle finished")
        return results

    def _get_scenario_enables_from_flows(
        self,
        window_subentry_id: str,
        global_states: dict[str, Any],
    ) -> tuple[bool, bool]:
        """
        Get scenario B and C enables with flow-based inheritance logic.

        Inheritance order: Window → Group → Global
        Values: "inherit" | "enable" | "disable"

        Returns:
            Tuple of (scenario_b_enabled, scenario_c_enabled)

        """
        # Get window data
        windows = self._get_subentries_by_type("window")
        window_data = windows.get(window_subentry_id, {})

        # Get parent group data if available
        parent_group_id = window_data.get("parent_group_id")
        group_data = {}
        if parent_group_id:
            groups = self._get_subentries_by_type("group")
            group_data = groups.get(parent_group_id, {})

        def resolve_scenario_enable(scenario_key: str, global_enabled: bool) -> bool:
            """Resolve inheritance for a single scenario."""
            # Check window level
            window_value = window_data.get(scenario_key, "inherit")
            if window_value in ["enable", "disable"]:
                return window_value == "enable"

            # Check group level
            if group_data:
                group_value = group_data.get(scenario_key, "inherit")
                if group_value in ["enable", "disable"]:
                    return group_value == "enable"

            # Fall back to global
            return global_enabled

        scenario_b_enabled = resolve_scenario_enable(
            "scenario_b_enable", global_states.get("scenario_b_enabled", False)
        )
        scenario_c_enabled = resolve_scenario_enable(
            "scenario_c_enable", global_states.get("scenario_c_enabled", False)
        )

        return scenario_b_enabled, scenario_c_enabled

    def _should_shade_window_from_flows(
        self,
        shade_request: ShadeRequestFlow,
    ) -> tuple[bool, str]:
        """
        Flow-based shading decision with full scenario logic.

        Implements the same logic as should_shade_window() but for flow-based
        calculation.
        """
        window_name = shade_request.window_data.get("name", "Unknown")

        _LOGGER.debug("[SHADE-FLOW] ---- Shading Logic for %s ----", window_name)

        # Check maintenance mode
        if shade_request.external_states["maintenance_mode"]:
            _LOGGER.debug("[SHADE-FLOW] Result: OFF (Maintenance mode active)")
            return False, "Maintenance mode active"

        # Check weather warning override
        if shade_request.external_states["weather_warning"]:
            _LOGGER.debug("[SHADE-FLOW] Result: ON (Weather warning active)")
            return True, "Weather warning active"

        # Get indoor temperature from window, group, or global config
        try:

            def is_inherit_marker(val: Any) -> bool:
                return val in ("-1", -1, "", None, "inherit")

            # 1. Window-specific - prefer new key, but accept legacy key
            indoor_temp_entity = shade_request.window_data.get(
                "indoor_temperature_sensor", ""
            ) or shade_request.window_data.get("room_temp_entity", "")
            # 2. If not found or is inheritance marker, use effective config
            if not indoor_temp_entity or is_inherit_marker(indoor_temp_entity):
                indoor_temp_entity = shade_request.effective_config.get(
                    "indoor_temperature_sensor", ""
                ) or shade_request.effective_config.get("room_temp_entity", "")

            if not indoor_temp_entity:
                _LOGGER.warning(
                    "No room temperature sensor for window %s "
                    "(neither window, group, nor global config)",
                    window_name,
                )
                return False, "No room temperature sensor"

            indoor_temp_str = self._get_cached_entity_state(indoor_temp_entity, "0")
            indoor_temp = float(indoor_temp_str)
            outdoor_temp = shade_request.external_states["outdoor_temp"]

            _LOGGER.debug(
                "[SHADE-FLOW] Temps - Indoor: %.1f°C, Outdoor: %.1f°C",
                indoor_temp,
                outdoor_temp,
            )
        except (ValueError, TypeError):
            _LOGGER.warning("Could not parse temperature for window %s", window_name)
            return False, "Invalid temperature data"

        # --- Scenario A: Strong direct sun (always active) ---
        threshold_direct = shade_request.effective_config["thresholds"]["direct"]
        _LOGGER.debug(
            "[SHADE-FLOW] Scenario A Check: Power (%.1fW) > Threshold (%.1fW)? "
            "AND Indoor (%.1f°C) >= Base (%.1f°C)? "
            "AND Outdoor (%.1f°C) >= Base (%.1f°C)?",
            shade_request.solar_result.power_total,
            threshold_direct,
            indoor_temp,
            shade_request.effective_config["temperatures"]["indoor_base"],
            outdoor_temp,
            shade_request.effective_config["temperatures"]["outdoor_base"],
        )

        if (
            shade_request.solar_result.power_total > threshold_direct
            and indoor_temp
            >= shade_request.effective_config["temperatures"]["indoor_base"]
            and outdoor_temp
            >= shade_request.effective_config["temperatures"]["outdoor_base"]
        ):
            _LOGGER.debug("[SHADE-FLOW] Result: ON (Scenario A triggered)")
            power_val = shade_request.solar_result.power_total
            return (
                True,
                f"Strong sun ({power_val:.0f}W > {threshold_direct:.0f}W)",
            )

        # --- Scenario B: Diffuse heat ---
        scenario_b_config = shade_request.effective_config.get("scenario_b", {})
        if shade_request.scenario_b_enabled and scenario_b_config.get("enabled", True):
            result_b, reason_b = self._check_scenario_b(
                shade_request, scenario_b_config, indoor_temp, outdoor_temp
            )
            if result_b:
                return result_b, reason_b

        # --- Scenario C: Heatwave forecast ---
        # Check if scenario C is enabled (default to True if not specified)
        scenario_c_enabled_in_config = shade_request.effective_config.get(
            "scenario_c_enable", "inherit"
        )
        if shade_request.scenario_c_enabled and scenario_c_enabled_in_config not in (
            "disable",
            False,
        ):
            result_c, reason_c = self._check_scenario_c(shade_request, indoor_temp)
            if result_c:
                return result_c, reason_c

        _LOGGER.debug("[SHADE-FLOW] Result: OFF (No scenario triggered)")
        return False, "No shading required"

    def _check_scenario_b(
        self,
        shade_request: ShadeRequestFlow,
        scenario_b_config: dict[str, Any],
        indoor_temp: float,
        outdoor_temp: float,
    ) -> tuple[bool, str]:
        """Check scenario B: Diffuse heat."""
        threshold_diffuse = shade_request.effective_config["thresholds"]["diffuse"]
        temp_indoor_b = shade_request.effective_config["temperatures"][
            "indoor_base"
        ] + scenario_b_config.get("temp_indoor_offset", 0.5)
        temp_outdoor_b = shade_request.effective_config["temperatures"][
            "outdoor_base"
        ] + scenario_b_config.get("temp_outdoor_offset", 6.0)

        _LOGGER.debug(
            "[SHADE-FLOW] Scenario B Check: Power (%.1fW) > Threshold (%.1fW)? "
            "AND Indoor (%.1f°C) > Offset (%.1f°C)? "
            "AND Outdoor (%.1f°C) > Offset (%.1f°C)?",
            shade_request.solar_result.power_total,
            threshold_diffuse,
            indoor_temp,
            temp_indoor_b,
            outdoor_temp,
            temp_outdoor_b,
        )

        if (
            shade_request.solar_result.power_total > threshold_diffuse
            and indoor_temp > temp_indoor_b
            and outdoor_temp > temp_outdoor_b
        ):
            _LOGGER.debug("[SHADE-FLOW] Result: ON (Scenario B triggered)")
            power_val = shade_request.solar_result.power_total
            return (
                True,
                f"Diffuse heat ({power_val:.0f}W, Indoor: {indoor_temp:.1f}°C)",
            )
        return False, "No shading required"

    def _check_scenario_c(
        self,
        shade_request: ShadeRequestFlow,
        indoor_temp: float,
    ) -> tuple[bool, str]:
        """Check scenario C: Heatwave forecast."""
        try:
            forecast_temp = shade_request.external_states["forecast_temp"]
            if forecast_temp > 0:
                current_hour = datetime.now(UTC).hour
                # Read threshold from effective config instead of nested
                # scenario_c_config
                temp_forecast_threshold = shade_request.effective_config.get(
                    "scenario_c_temp_forecast", 28.5
                )
                start_hour = shade_request.effective_config.get(
                    "scenario_c_start_hour", 9
                )

                _LOGGER.debug(
                    "[SHADE-FLOW] Scenario C Check: Forecast (%.1f°C) > "
                    "Threshold (%.1f°C)? AND Indoor (%.1f°C) >= Base (%.1f°C)? "
                    "AND Hour (%d) >= Start (%d)?",
                    forecast_temp,
                    temp_forecast_threshold,
                    indoor_temp,
                    shade_request.effective_config["temperatures"]["indoor_base"],
                    current_hour,
                    start_hour,
                )

                if (
                    forecast_temp > temp_forecast_threshold
                    and indoor_temp
                    >= shade_request.effective_config["temperatures"]["indoor_base"]
                    and current_hour >= start_hour
                ):
                    _LOGGER.debug("[SHADE-FLOW] Result: ON (Scenario C triggered)")
                    return (
                        True,
                        f"Heatwave forecast ({forecast_temp:.1f}°C expected)",
                    )
        except (ValueError, TypeError):
            _LOGGER.warning("Could not read forecast temperature for Scenario C")

        return False, "No shading required"
