# ruff: noqa: SLF001
"""Integration tests for SolarWindowCalculator using framework."""

from __future__ import annotations

from unittest.mock import Mock, patch

from custom_components.solar_window_system.calculator import SolarWindowCalculator
from homeassistant.config_entries import ConfigEntry
from tests.helpers.test_framework import IntegrationTestCase
from tests.test_data import (
    VALID_PHYSICAL,
    VALID_TEMPERATURES,
    VALID_THRESHOLDS,
    VALID_WINDOW_DATA,
)

# Test constants to avoid magic numbers in assertions
EXPECTED_NO_SHADOW = 1.0
EXPECTED_COMPLETE_SHADOW = 0.1
EXPECTED_TRIGGER_COUNT = 2


class TestCalculatorFlowBased(IntegrationTestCase):
    """Integration tests for SolarWindowCalculator using framework."""

    def test_shadow_factor_no_shadow(self) -> None:
        """Test shadow factor with no shadow."""
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.data = {"entry_type": "window_configs"}
        calculator = SolarWindowCalculator(mock_hass, mock_entry)
        result = calculator._calculate_shadow_factor(45, 180, 180, 0, 0)  # type: ignore[attr-defined]
        if result != EXPECTED_NO_SHADOW:
            msg = f"Expected {EXPECTED_NO_SHADOW}, got {result}"
            raise AssertionError(msg)

    def test_shadow_factor_complete_shadow(self) -> None:
        """Test shadow factor with complete shadow."""
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.data = {"entry_type": "window_configs"}
        calculator = SolarWindowCalculator(mock_hass, mock_entry)
        result = calculator._calculate_shadow_factor(10, 180, 180, 2.0, 0.0)  # type: ignore[attr-defined]
        if result != EXPECTED_COMPLETE_SHADOW:
            msg = f"Expected {EXPECTED_COMPLETE_SHADOW}, got {result}"
            raise AssertionError(msg)

    def test_entity_cache_hit(self) -> None:
        """Test entity cache hit."""
        mock_hass = Mock()
        mock_entry = Mock()
        mock_entry.data = {"entry_type": "window_configs"}
        calculator = SolarWindowCalculator(mock_hass, mock_entry)
        mock_state = Mock()
        mock_state.state = "42.5"
        with patch.object(mock_hass.states, "get", return_value=mock_state) as mock_get:
            r1 = calculator._get_cached_entity_state("sensor.test", 0)  # type: ignore[attr-defined]
            r2 = calculator._get_cached_entity_state("sensor.test", 0)  # type: ignore[attr-defined]
            if r1 != "42.5":
                msg = f"Expected '42.5', got {r1!r}"
                raise AssertionError(msg)
            if r2 != "42.5":
                msg = f"Expected '42.5', got {r2!r}"
                raise AssertionError(msg)
            if mock_get.call_count != 1:
                msg = f"Expected 1 call, got {mock_get.call_count}"
                raise AssertionError(msg)

    def test_scenario_b_c_inheritance(self) -> None:
        """Test scenario B/C enable inheritance and override logic."""
        mock_entry = Mock(spec=ConfigEntry)
        mock_entry.data = {"entry_type": "window_configs"}
        mock_hass = Mock()
        calc = SolarWindowCalculator(mock_hass, mock_entry)

        windows = {
            "w_global": {"name": "GlobalWin", "parent_group_id": "g1"},
            "w_group": {"name": "GroupWin", "parent_group_id": "g2"},
            "w_window": {
                "name": "WindowWin",
                "parent_group_id": "g3",
                "scenario_b_enable": "enable",
                "scenario_c_enable": "disable",
            },
        }
        groups = {
            "g1": {"name": "Group1"},
            "g2": {
                "name": "Group2",
                "scenario_b_enable": "disable",
                "scenario_c_enable": "enable",
            },
            "g3": {
                "name": "Group3",
                "scenario_b_enable": "disable",
                "scenario_c_enable": "enable",
            },
        }

        def _subentries_scenario(entry_type: str) -> dict:
            if entry_type == "window":
                return windows
            if entry_type == "group":
                return groups
            return {}

        calc._get_subentries_by_type = _subentries_scenario  # type: ignore[attr-defined,assignment]

        global_states = {"scenario_b_enabled": True, "scenario_c_enabled": True}

        b, c = calc._get_scenario_enables_from_flows("w_global", global_states)  # type: ignore[attr-defined]
        if b is not True:
            msg = "Expected b to be True for w_global"
            raise AssertionError(msg)
        if c is not True:
            msg = "Expected c to be True for w_global"
            raise AssertionError(msg)

        b, c = calc._get_scenario_enables_from_flows("w_group", global_states)  # type: ignore[attr-defined]
        if b is not False:
            msg = "Expected b to be False for w_group"
            raise AssertionError(msg)
        if c is not True:
            msg = "Expected c to be True for w_group"
            raise AssertionError(msg)

        b, c = calc._get_scenario_enables_from_flows("w_window", global_states)  # type: ignore[attr-defined]
        if b is not True:
            msg = "Expected b to be True for w_window"
            raise AssertionError(msg)
        if c is not False:
            msg = "Expected c to be False for w_window"
            raise AssertionError(msg)

    def test_recalculation_triggered_on_weather_warning(self) -> None:
        """Ensure calculator recalculates when weather warning state changes."""
        mock_entry = Mock(spec=ConfigEntry)
        mock_entry.data = {"entry_type": "window_configs"}
        calc = SolarWindowCalculator(Mock(), mock_entry)

        def _subentries_recalc(entry_type: str) -> dict:
            if entry_type == "window":
                return {"w1": VALID_WINDOW_DATA.copy()}
            if entry_type == "group":
                return {}
            if entry_type == "global":
                return {"global_config": {}}
            return {}

        calc._get_subentries_by_type = _subentries_recalc  # type: ignore[attr-defined,assignment]

        calc._get_global_data_merged = lambda: {  # type: ignore[attr-defined,assignment]
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
            "weather_forecast_temperature_sensor": "sensor.forecast_temp",
            "weather_warning_sensor": "sensor.weather_warning",
        }

        calc._get_cached_entity_state = lambda *_args, **_kwargs: 0  # type: ignore[attr-defined,assignment]
        calc.get_safe_attr = lambda *_args, **_kwargs: 0  # type: ignore[assignment]

        def _get_effective_config_from_flows(_w: str) -> tuple:
            return (
                {
                    "physical": VALID_PHYSICAL,
                    "thresholds": VALID_THRESHOLDS,
                    "temperatures": VALID_TEMPERATURES,
                },
                {},
            )

        calc.get_effective_config_from_flows = _get_effective_config_from_flows  # type: ignore[attr-defined,assignment]
        calc.apply_global_factors = lambda c, *_args, **_kwargs: c  # type: ignore[attr-defined,assignment]
        calc._should_shade_window_from_flows = lambda *_args, **_kwargs: (  # type: ignore[attr-defined,assignment]
            True,
            "Should shade",
        )
        calc._get_scenario_enables_from_flows = lambda *_args, **_kwargs: (  # type: ignore[attr-defined,assignment]
            False,
            False,
        )

        call_count = {"count": 0}
        orig_calc = calc.calculate_all_windows_from_flows

        def counting_calc() -> dict:
            call_count["count"] += 1
            return orig_calc()

        calc.calculate_all_windows_from_flows = counting_calc  # type: ignore[attr-defined,assignment]

        calc._get_cached_entity_state = lambda *_args, **_kwargs: "off"  # type: ignore[attr-defined,assignment]
        calc.calculate_all_windows_from_flows()
        calc._get_cached_entity_state = lambda *_args, **_kwargs: "on"  # type: ignore[attr-defined,assignment]
        calc.calculate_all_windows_from_flows()

        if call_count["count"] != EXPECTED_TRIGGER_COUNT:
            msg = f"Expected {EXPECTED_TRIGGER_COUNT} calls, got {call_count['count']}"
            raise AssertionError(msg)
