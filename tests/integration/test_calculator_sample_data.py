# ruff: noqa: SLF001,ARG001
"""Run SolarWindowCalculator with sample data using framework."""

from __future__ import annotations

from datetime import UTC
from unittest.mock import Mock, patch

from custom_components.solar_window_system.calculator import SolarWindowCalculator
from homeassistant.config_entries import ConfigEntry
from tests.helpers.test_framework import IntegrationTestCase


class TestCalculatorSampleData(IntegrationTestCase):
    """Run SolarWindowCalculator with sample data using framework."""

    def test_calculator_with_user_sample(self) -> None:
        """Use the user's sample window/group/global data and mocked entities."""
        mock_entry = Mock(spec=ConfigEntry)
        mock_entry.data = {"entry_type": "window_configs"}

        calc = SolarWindowCalculator(Mock(), mock_entry)
        # Mark this calculator as flow-backed so it will perform window calculations
        calc.global_entry = mock_entry  # type: ignore[assignment]

        # Sample data adapted from the user's snippet (fixed key names)
        windows = {
            "og_kind2_ost": {
                "name": "OG Kind 2 - Ost",
                "azimuth": 118,
                "elevation_min": 20,
                "elevation_max": 90,
                "azimuth_min": -90,
                "azimuth_max": 90,
                "window_width": 1.17,
                "window_height": 1.25,
                "shadow_depth": -1,
                "shadow_offset": -1,
                "indoor_temperature_sensor": "-1",
                "linked_group_id": "group_kind2",
            }
        }

        groups = {
            "group_kind2": {
                "name": "Kind 2 Gruppe",
                "indoor_temperature_sensor": "sensor.temperatur_kind2",
                "scenario_c_enable": "enable",
                "diffuse_factor": -1,
                "threshold_direct": 100,
                "threshold_diffuse": 100,
                "temperature_indoor_base": 21.0,
                "temperature_outdoor_base": 19.5,
                "scenario_b_temp_indoor": 23.0,
                "scenario_b_temp_outdoor": 25.5,
                "scenario_c_temp_indoor": 28.5,
                "scenario_c_temp_outdoor": 21.5,
                "scenario_c_temp_forecast": 25.0,
                "scenario_c_start_hour": -1,
            }
        }

        global_data = {
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
            "weather_forecast_temperature_sensor": "sensor.forecast_temp",
            "weather_warning_sensor": "binary_sensor.weather_warning",
            "scenario_b_enabled": True,
            "scenario_c_enabled": True,
            "maintenance_mode": False,
        }

        # Patch subentry lookup and global data merge
        calc._get_subentries_by_type = lambda entry_type: (
            windows
            if entry_type == "window"
            else (groups if entry_type == "group" else {"global_config": global_data})
        )
        calc._get_global_data_merged = lambda: global_data

        # Mock entity states accessed via _get_cached_entity_state
        def cached(
            entity_id: str,
            default_value: str | None = None,
            debug_label: str | None = None,
        ) -> str | None:
            mapping = {
                "sensor.temperatur_kind2": "25.29",
                "sensor.temperatur_kind1": "20.00",
                "sensor.solar_radiation": "800",
                "sensor.outdoor_temp": "22.5",
                "sensor.forecast_temp": "30.0",  # Increased to trigger scenario C
                "sensor.weather_warning": "off",
                "sensor.room_temp_living": "21.5",
                "sensor.room_temp_bedroom": "22.0",
            }
            return mapping.get(entity_id, default_value)

        calc._get_cached_entity_state = cached

        # Mock sun attributes
        def _get_safe_attr(
            entity_id: str,
            attr: str,  # type: ignore[ARG001]
            default: str | float = 0,
        ) -> str | float:
            return default

        calc.get_safe_attr = _get_safe_attr

        # Mock current hour to be after start_hour (9)
        with patch(
            "custom_components.solar_window_system.calculator.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value.hour = 10  # After 9 AM
            mock_datetime.UTC = UTC

            # Inspect effective config used for this window
            effective_cfg, sources = calc.get_effective_config_from_flows(
                "og_kind2_ost"
            )
            # debug: effective_cfg logged during development

            # Execute calculation
            results = calc.calculate_all_windows_from_flows()
            # TEMP DEBUG: results available during development

        if "og_kind2_ost" not in results["windows"]:
            msg = "Window 'og_kind2_ost' not found in results"
            raise AssertionError(msg)
        win = results["windows"]["og_kind2_ost"]
        # Basic sanity checks
        if "total_power" not in win:
            msg = "Window data missing 'total_power' key"
            raise TypeError(msg)
        if not isinstance(win["total_power"], (int, float)):
            msg = "total_power should be int or float"
            raise TypeError(msg)

        # EXPECTATION: scenario C should trigger for these inputs and require shading
        if "shade_required" not in win:
            msg = "Window data missing 'shade_required' key"
            raise AssertionError(msg)
        if win["shade_required"] is not True:
            msg = "Window should require shading"
            raise AssertionError(msg)
        # Reason should reference heatwave / forecast scenario
        shade_reason = win.get("shade_reason") or ""
        if "forecast" not in shade_reason.lower():
            msg = f"Shade reason should contain 'forecast', got: {shade_reason}"
            raise AssertionError(msg)
