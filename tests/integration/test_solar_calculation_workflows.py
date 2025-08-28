"""End-to-end integration tests for solar window calculation workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.calculator import (
    ShadeRequestFlow,
    SolarWindowCalculator,
    WindowCalculationResult,
)
from custom_components.solar_window_system.const import DOMAIN
from tests.helpers.test_framework import IntegrationTestCase

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# Constants for test thresholds
DEFAULT_DIRECT_THRESHOLD = 200.0
DEFAULT_DIFFUSE_THRESHOLD = 150.0
DEFAULT_INDOOR_BASE_TEMP = 24.0
DEFAULT_OUTDOOR_BASE_TEMP = 20.0
MIN_SHADOW_FACTOR = 0.1


class TestSolarCalculationWorkflows(IntegrationTestCase):
    """Comprehensive integration tests for end-to-end solar calculation workflows."""

    def test_complete_solar_calculation_workflow_scenario_a(
        self, hass: HomeAssistant
    ) -> None:
        """Test complete workflow from configuration to Scenario A shading decision."""
        # Setup global configuration
        global_config = {
            "entry_type": "global_config",
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
            "global_sensitivity": 1.0,
            "scenario_b_enabled": False,
            "scenario_c_enabled": False,
        }

        # Setup window configuration
        window_config = {
            "entry_type": "window",
            "name": "Living Room Window",
            "window_width": 2.0,
            "window_height": 1.5,
            "azimuth": 180.0,
            "elevation_min": 10.0,
            "elevation_max": 80.0,
            "azimuth_min": -45.0,
            "azimuth_max": 45.0,
            "indoor_temperature_sensor": "sensor.room_temp",
            "threshold_direct": DEFAULT_DIRECT_THRESHOLD,
            "temperature_indoor_base": DEFAULT_INDOOR_BASE_TEMP,
            "temperature_outdoor_base": DEFAULT_OUTDOOR_BASE_TEMP,
        }

        # Create calculator instance
        calculator = SolarWindowCalculator.from_flows(
            hass,
            MockConfigEntry(domain=DOMAIN, data=global_config, entry_id="test_global"),
        )

        # Mock external states
        mock_states = Mock()
        mock_states.get.side_effect = lambda entity_id: {
            "sensor.solar_radiation": Mock(state="250.0"),
            "sensor.outdoor_temp": Mock(state="25.0"),
            "sensor.room_temp": Mock(state="25.0"),
            "sun.sun": Mock(attributes={"elevation": 45.0, "azimuth": 180.0}),
        }.get(entity_id, Mock(state="0"))

        with (
            patch.object(calculator, "hass", Mock(states=mock_states)),
            patch.object(calculator, "_get_subentries_by_type") as mock_get_subentries,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            # Mock subentries to return our window config
            mock_get_subentries.side_effect = lambda entry_type: {
                "window": {"test_window": window_config},
                "group": {},
            }.get(entry_type, {})

            # Mock global data
            mock_global.return_value = global_config

            # Step 1: Get effective configuration
            effective_config, sources = calculator.get_effective_config_from_flows(
                "test_window"
            )

            # Step 2: Calculate solar power
            solar_result = calculator.calculate_window_solar_power_with_shadow(
                effective_config,
                window_config,
                {
                    "solar_radiation": 250.0,
                    "sun_azimuth": 180.0,
                    "sun_elevation": 45.0,
                    "outdoor_temp": 25.0,
                },
            )

            # Step 3: Check shading decision
            shade_request = ShadeRequestFlow(
                window_data=window_config,
                effective_config=effective_config,
                external_states={
                    "outdoor_temp": 25.0,
                    "maintenance_mode": False,
                    "weather_warning": False,
                },
                scenario_b_enabled=False,
                scenario_c_enabled=False,
                solar_result=solar_result,
            )

            result, reason = calculator._should_shade_window_from_flows(shade_request)  # type: ignore[attr-defined]

            # Assertions
            assert result is True  # type: ignore[assert]
            assert "Strong sun" in reason  # type: ignore[assert]
            assert solar_result.power_total > DEFAULT_DIRECT_THRESHOLD  # type: ignore[assert]
            assert solar_result.is_visible is True  # type: ignore[assert]

    def test_complete_workflow_scenario_b_diffuse_heat(
        self, hass: HomeAssistant
    ) -> None:
        """Test complete workflow with Scenario B diffuse heat detection."""
        global_config = {
            "entry_type": "global_config",
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
            "scenario_b_enabled": True,
        }

        window_config = {
            "entry_type": "window",
            "name": "Kitchen Window",
            "window_width": 1.5,
            "window_height": 1.2,
            "azimuth": 90.0,
            "indoor_temperature_sensor": "sensor.kitchen_temp",
            "threshold_direct": DEFAULT_DIRECT_THRESHOLD,
            "threshold_diffuse": DEFAULT_DIFFUSE_THRESHOLD,
            "temperature_indoor_base": DEFAULT_INDOOR_BASE_TEMP,
            "temperature_outdoor_base": DEFAULT_OUTDOOR_BASE_TEMP,
            "scenario_b_enable": "enable",
        }

        calculator = SolarWindowCalculator.from_flows(
            hass,
            MockConfigEntry(domain=DOMAIN, data=global_config, entry_id="test_global"),
        )

        # Mock states for Scenario B conditions
        mock_states = Mock()
        mock_states.get.side_effect = lambda entity_id: {
            "sensor.solar_radiation": Mock(state="170.0"),  # Above diffuse threshold
            "sensor.outdoor_temp": Mock(state="28.0"),  # Above outdoor offset
            "sensor.kitchen_temp": Mock(state="25.5"),  # Above indoor offset
            "sun.sun": Mock(attributes={"elevation": 30.0, "azimuth": 90.0}),
        }.get(entity_id, Mock(state="0"))

        with (
            patch.object(calculator, "hass", Mock(states=mock_states)),
            patch.object(calculator, "_get_subentries_by_type") as mock_get_subentries,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            # Mock subentries to return our window config
            mock_get_subentries.side_effect = lambda entry_type: {
                "window": {"test_window": window_config},
                "group": {},
            }.get(entry_type, {})

            # Mock global data
            mock_global.return_value = global_config

            # Get effective config
            effective_config, sources = calculator.get_effective_config_from_flows(
                "test_window"
            )

            # Calculate solar power
            solar_result = calculator.calculate_window_solar_power_with_shadow(
                effective_config,
                window_config,
                {
                    "solar_radiation": 170.0,
                    "sun_azimuth": 90.0,
                    "sun_elevation": 30.0,
                    "outdoor_temp": 28.0,
                },
            )

            # Check shading with Scenario B
            shade_request = ShadeRequestFlow(
                window_data=window_config,
                effective_config=effective_config,
                external_states={
                    "outdoor_temp": 28.0,
                    "maintenance_mode": False,
                    "weather_warning": False,
                },
                scenario_b_enabled=True,
                scenario_c_enabled=False,
                solar_result=solar_result,
            )

            result, reason = calculator._should_shade_window_from_flows(shade_request)  # type: ignore[attr-defined]

            assert result is True  # type: ignore[assert]
            assert "Diffuse heat" in reason  # type: ignore[assert]
            assert "25.5°C" in reason  # type: ignore[assert]

    def test_complete_workflow_scenario_c_heatwave_forecast(
        self, hass: HomeAssistant
    ) -> None:
        """Test complete workflow with Scenario C heatwave forecast."""
        global_config = {
            "entry_type": "global_config",
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
            "weather_forecast_temperature_sensor": "sensor.weather_forecast",
            "scenario_c_enabled": True,
        }

        window_config = {
            "entry_type": "window",
            "name": "Bedroom Window",
            "window_width": 1.8,
            "window_height": 1.4,
            "azimuth": 270.0,
            "indoor_temperature_sensor": "sensor.bedroom_temp",
            "temperature_indoor_base": DEFAULT_INDOOR_BASE_TEMP,
            "scenario_c_temp_forecast": 28.5,
            "scenario_c_start_hour": 9,
        }

        calculator = SolarWindowCalculator.from_flows(
            hass,
            MockConfigEntry(domain=DOMAIN, data=global_config, entry_id="test_global"),
        )

        # Mock states for Scenario C conditions
        mock_states = Mock()
        mock_states.get.side_effect = lambda entity_id: {
            "sensor.solar_radiation": Mock(state="80.0"),  # Below thresholds
            "sensor.outdoor_temp": Mock(state="22.0"),
            "sensor.weather_forecast": Mock(state="30.0"),  # Above forecast threshold
            "sensor.bedroom_temp": Mock(state="25.0"),  # Above indoor base
            "sun.sun": Mock(attributes={"elevation": 20.0, "azimuth": 270.0}),
        }.get(entity_id, Mock(state="0"))

        with (
            patch.object(calculator, "hass", Mock(states=mock_states)),
            patch.object(calculator, "_get_subentries_by_type") as mock_get_subentries,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
            patch(
                "custom_components.solar_window_system.calculator.datetime"
            ) as mock_datetime,
        ):
            mock_datetime.now.return_value.hour = 10  # After start hour

            # Mock subentries to return our window config
            mock_get_subentries.side_effect = lambda entry_type: {
                "window": {"test_window": window_config},
                "group": {},
            }.get(entry_type, {})

            # Mock global data
            mock_global.return_value = global_config

            # Get effective config
            effective_config, sources = calculator.get_effective_config_from_flows(
                "test_window"
            )

            # Calculate solar power
            solar_result = calculator.calculate_window_solar_power_with_shadow(
                effective_config,
                window_config,
                {
                    "solar_radiation": 80.0,
                    "sun_azimuth": 270.0,
                    "sun_elevation": 20.0,
                    "outdoor_temp": 22.0,
                    "forecast_temp": 30.0,
                },
            )

            # Check shading with Scenario C
            shade_request = ShadeRequestFlow(
                window_data=window_config,
                effective_config=effective_config,
                external_states={
                    "outdoor_temp": 22.0,
                    "forecast_temp": 30.0,
                    "maintenance_mode": False,
                    "weather_warning": False,
                },
                scenario_b_enabled=False,
                scenario_c_enabled=True,
                solar_result=solar_result,
            )

            result, reason = calculator._should_shade_window_from_flows(shade_request)  # type: ignore[attr-defined]

            assert result is True  # type: ignore[assert]
            assert "Heatwave forecast" in reason  # type: ignore[assert]
            assert "30.0°C" in reason  # type: ignore[assert]

    def test_workflow_with_weather_warning_override(self, hass: HomeAssistant) -> None:
        """Test workflow with weather warning override."""
        global_config = {
            "entry_type": "global_config",
            "weather_warning_sensor": "binary_sensor.weather_warning",
        }

        window_config = {
            "entry_type": "window",
            "name": "Office Window",
            "indoor_temperature_sensor": "sensor.office_temp",
        }

        calculator = SolarWindowCalculator.from_flows(
            hass,
            MockConfigEntry(domain=DOMAIN, data=global_config, entry_id="test_global"),
        )

        # Mock weather warning active
        mock_states = Mock()
        mock_states.get.side_effect = lambda entity_id: {
            "binary_sensor.weather_warning": Mock(state="on"),
            "sensor.office_temp": Mock(state="20.0"),
        }.get(entity_id, Mock(state="0"))

        with (
            patch.object(calculator, "hass", Mock(states=mock_states)),
            patch.object(calculator, "_get_subentries_by_type") as mock_get_subentries,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            # Mock subentries to return our window config
            mock_get_subentries.side_effect = lambda entry_type: {
                "window": {"test_window": window_config},
                "group": {},
            }.get(entry_type, {})

            # Mock global data
            mock_global.return_value = global_config

            effective_config, sources = calculator.get_effective_config_from_flows(
                "test_window"
            )

            solar_result = WindowCalculationResult(
                power_total=50.0,
                power_direct=40.0,
                power_diffuse=10.0,
                shadow_factor=1.0,
                is_visible=True,
                area_m2=2.0,
                shade_required=False,
                shade_reason="",
                effective_threshold=DEFAULT_DIRECT_THRESHOLD,
            )

            shade_request = ShadeRequestFlow(
                window_data=window_config,
                effective_config=effective_config,
                external_states={
                    "weather_warning": True,
                    "maintenance_mode": False,
                },
                scenario_b_enabled=False,
                scenario_c_enabled=False,
                solar_result=solar_result,
            )

            result, reason = calculator._should_shade_window_from_flows(shade_request)  # type: ignore[attr-defined]

            assert result is True  # type: ignore[assert]
            assert reason == "Weather warning active"  # type: ignore[assert]

    def test_workflow_with_maintenance_mode(self, hass: HomeAssistant) -> None:
        """Test workflow with maintenance mode active."""
        global_config = {
            "entry_type": "window_configs",  # Must be window_configs to calculate
            "maintenance_mode": True,
            "solar_radiation_sensor": "sensor.solar_radiation",  # Add sensor entity ID
        }

        window_config = {
            "entry_type": "window",
            "name": "Bathroom Window",
        }

        calculator = SolarWindowCalculator.from_flows(
            hass,
            MockConfigEntry(domain=DOMAIN, data=global_config, entry_id="test_global"),
        )

        # Mock states with sufficient solar radiation to trigger calculation
        mock_states = Mock()
        mock_states.get.side_effect = lambda entity_id: {
            "sun.sun": Mock(attributes={"elevation": 30.0, "azimuth": 180.0}),
            "sensor.solar_radiation": Mock(state="100.0"),  # Add solar radiation sensor
        }.get(entity_id, Mock(state="0"))

        with (
            patch.object(calculator, "hass", Mock(states=mock_states)),
            patch.object(calculator, "_get_subentries_by_type") as mock_get_subentries,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            # Mock subentries to return our window config
            mock_get_subentries.side_effect = lambda entry_type: {
                "window": {"test_window": window_config},
                "group": {},
            }.get(entry_type, {})

            # Mock global data with maintenance mode
            mock_global.return_value = global_config

            result = calculator.calculate_all_windows_from_flows()

            # Should return no shading due to maintenance mode
            window_result = result["windows"]["test_window"]
            assert window_result["shade_required"] is False  # type: ignore[assert]
            assert window_result["shade_reason"] == "Maintenance mode active"  # type: ignore[assert]

        solar_result = WindowCalculationResult(
            power_total=300.0,
            power_direct=240.0,
            power_diffuse=60.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=DEFAULT_DIRECT_THRESHOLD,
        )

        effective_config = {
            "thresholds": {
                "direct": DEFAULT_DIRECT_THRESHOLD,
                "diffuse": DEFAULT_DIFFUSE_THRESHOLD,
            },
            "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
        }

        shade_request = ShadeRequestFlow(
            window_data=window_config,
            effective_config=effective_config,
            external_states={
                "maintenance_mode": True,  # Maintenance mode active
                "weather_warning": False,
            },
            scenario_b_enabled=False,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        result, reason = calculator._should_shade_window_from_flows(shade_request)  # type: ignore[attr-defined]

        assert result is False  # type: ignore[assert]
        assert reason == "Maintenance mode active"  # type: ignore[assert]

    def test_workflow_no_shading_required(self, hass: HomeAssistant) -> None:
        """Test workflow when no shading conditions are met."""
        global_config = {
            "entry_type": "global_config",
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
        }

        window_config = {
            "entry_type": "window",
            "name": "Hallway Window",
            "indoor_temperature_sensor": "sensor.hallway_temp",
        }

        calculator = SolarWindowCalculator.from_flows(
            hass,
            MockConfigEntry(domain=DOMAIN, data=global_config, entry_id="test_global"),
        )

        # Mock low conditions
        mock_states = Mock()
        mock_states.get.side_effect = lambda entity_id: {
            "sensor.solar_radiation": Mock(state="50.0"),  # Low radiation
            "sensor.outdoor_temp": Mock(state="18.0"),  # Low temperature
            "sensor.hallway_temp": Mock(state="20.0"),
            "sun.sun": Mock(attributes={"elevation": 15.0, "azimuth": 180.0}),
        }.get(entity_id, Mock(state="0"))

        with (
            patch.object(calculator, "hass", Mock(states=mock_states)),
            patch.object(calculator, "_get_subentries_by_type") as mock_get_subentries,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            # Mock subentries to return our window config
            mock_get_subentries.side_effect = lambda entry_type: {
                "window": {"test_window": window_config},
                "group": {},
            }.get(entry_type, {})

            # Mock global data
            mock_global.return_value = global_config

            effective_config, sources = calculator.get_effective_config_from_flows(
                "test_window"
            )

            solar_result = calculator.calculate_window_solar_power_with_shadow(
                effective_config,
                window_config,
                {
                    "solar_radiation": 50.0,
                    "sun_azimuth": 180.0,
                    "sun_elevation": 15.0,
                    "outdoor_temp": 18.0,
                },
            )

            shade_request = ShadeRequestFlow(
                window_data=window_config,
                effective_config=effective_config,
                external_states={
                    "outdoor_temp": 18.0,
                    "maintenance_mode": False,
                    "weather_warning": False,
                },
                scenario_b_enabled=False,
                scenario_c_enabled=False,
                solar_result=solar_result,
            )

            result, reason = calculator._should_shade_window_from_flows(shade_request)  # type: ignore[attr-defined]

            assert result is False  # type: ignore[assert]
            assert reason == "No shading required"  # type: ignore[assert]

    def test_workflow_with_shadow_calculations(self, hass: HomeAssistant) -> None:
        """Test workflow including shadow factor calculations."""
        global_config = {
            "entry_type": "window_configs",
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
        }

        window_config = {
            "entry_type": "window",
            "name": "Shadow Test Window",
            "window_width": 2.0,
            "window_height": 1.5,
            "azimuth": 180.0,
            "shadow_depth": 0.8,
            "shadow_offset": 0.2,
            "indoor_temperature_sensor": "sensor.shadow_test_temp",
            "threshold_direct": 150.0,
        }

        calculator = SolarWindowCalculator.from_flows(
            hass,
            MockConfigEntry(domain=DOMAIN, data=global_config, entry_id="test_global"),
        )

        # Mock states with sufficient solar radiation
        mock_states = Mock()
        mock_states.get.side_effect = lambda entity_id: {
            "sensor.solar_radiation": Mock(state="300.0"),
            "sensor.outdoor_temp": Mock(state="25.0"),
            "sensor.shadow_test_temp": Mock(state="25.0"),
            "sun.sun": Mock(attributes={"elevation": 45.0, "azimuth": 180.0}),
        }.get(entity_id, Mock(state="0"))

        with (
            patch.object(calculator, "hass", Mock(states=mock_states)),
            patch.object(calculator, "_get_subentries_by_type") as mock_get_subentries,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            # Mock subentries to return our window config
            mock_get_subentries.side_effect = lambda entry_type: {
                "window": {"test_window": window_config},
                "group": {},
            }.get(entry_type, {})

            # Mock global data
            mock_global.return_value = global_config

            result = calculator.calculate_all_windows_from_flows()

            # Should return shading required due to strong sun
            window_result = result["windows"]["test_window"]
            assert window_result["shade_required"] is True  # type: ignore[assert]
            assert "Strong sun" in window_result["shade_reason"]  # type: ignore[assert]

    def test_workflow_error_handling_invalid_temperature(
        self, hass: HomeAssistant
    ) -> None:
        """Test workflow error handling with invalid temperature data."""
        global_config = {
            "entry_type": "global_config",
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
        }

        window_config = {
            "entry_type": "window",
            "name": "Error Test Window",
            "indoor_temperature_sensor": "sensor.error_temp",
        }

        calculator = SolarWindowCalculator.from_flows(
            hass,
            MockConfigEntry(domain=DOMAIN, data=global_config, entry_id="test_global"),
        )

        # Mock invalid temperature
        mock_states = Mock()
        mock_states.get.side_effect = lambda entity_id: {
            "sensor.solar_radiation": Mock(state="250.0"),
            "sensor.outdoor_temp": Mock(state="25.0"),
            "sensor.error_temp": Mock(state="invalid_temp"),
            "sun.sun": Mock(attributes={"elevation": 45.0, "azimuth": 180.0}),
        }.get(entity_id, Mock(state="0"))

        with (
            patch.object(calculator, "hass", Mock(states=mock_states)),
            patch.object(calculator, "_get_subentries_by_type") as mock_get_subentries,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            # Mock subentries to return our window config
            mock_get_subentries.side_effect = lambda entry_type: {
                "window": {"test_window": window_config},
                "group": {},
            }.get(entry_type, {})

            # Mock global data
            mock_global.return_value = global_config

            effective_config, sources = calculator.get_effective_config_from_flows(
                "test_window"
            )

            solar_result = WindowCalculationResult(
                power_total=250.0,
                power_direct=200.0,
                power_diffuse=50.0,
                shadow_factor=1.0,
                is_visible=True,
                area_m2=2.0,
                shade_required=False,
                shade_reason="",
                effective_threshold=DEFAULT_DIRECT_THRESHOLD,
            )

            shade_request = ShadeRequestFlow(
                window_data=window_config,
                effective_config=effective_config,
                external_states={
                    "outdoor_temp": 25.0,
                    "maintenance_mode": False,
                    "weather_warning": False,
                },
                scenario_b_enabled=False,
                scenario_c_enabled=False,
                solar_result=solar_result,
            )

            result, reason = calculator._should_shade_window_from_flows(shade_request)  # type: ignore[attr-defined]

            assert result is False  # type: ignore[assert]
            assert "Invalid temperature data" in reason  # type: ignore[assert]

    def test_workflow_error_handling_missing_sensor(self, hass: HomeAssistant) -> None:
        """Test workflow error handling with missing temperature sensor."""
        global_config = {
            "entry_type": "window_configs",
            "solar_radiation_sensor": "sensor.solar_radiation",
            "outdoor_temperature_sensor": "sensor.outdoor_temp",
        }

        window_config = {
            "entry_type": "window",
            "name": "Missing Sensor Window",
            # No indoor_temperature_sensor configured
        }

        calculator = SolarWindowCalculator.from_flows(
            hass,
            MockConfigEntry(domain=DOMAIN, data=global_config, entry_id="test_global"),
        )

        # Mock states for missing sensor scenario
        mock_states = Mock()
        mock_states.get.side_effect = lambda entity_id: {
            "sensor.solar_radiation": Mock(state="150.0"),
            "sensor.outdoor_temp": Mock(state="25.0"),
            "sun.sun": Mock(attributes={"elevation": 30.0, "azimuth": 180.0}),
            # No indoor temperature sensor available
        }.get(entity_id, Mock(state="0"))

        with (
            patch.object(calculator, "hass", Mock(states=mock_states)),
            patch.object(calculator, "_get_subentries_by_type") as mock_get_subentries,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            # Mock subentries to return our window config
            mock_get_subentries.side_effect = lambda entry_type: {
                "window": {"test_window": window_config},
                "group": {},
            }.get(entry_type, {})

            # Mock global data
            mock_global.return_value = global_config

            result = calculator.calculate_all_windows_from_flows()

            # Should return no shading due to missing sensor
            window_result = result["windows"]["test_window"]
            assert window_result["shade_required"] is False  # type: ignore[assert]
            assert "No room temperature sensor" in window_result["shade_reason"]  # type: ignore[assert]

        solar_result = WindowCalculationResult(
            power_total=250.0,
            power_direct=200.0,
            power_diffuse=50.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=2.0,
            shade_required=False,
            shade_reason="",
            effective_threshold=DEFAULT_DIRECT_THRESHOLD,
        )

        effective_config = {
            "thresholds": {
                "direct": DEFAULT_DIRECT_THRESHOLD,
                "diffuse": DEFAULT_DIFFUSE_THRESHOLD,
            },
            "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
        }

        shade_request = ShadeRequestFlow(
            window_data=window_config,
            effective_config=effective_config,
            external_states={
                "outdoor_temp": 25.0,
                "maintenance_mode": False,
                "weather_warning": False,
            },
            scenario_b_enabled=False,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        result, reason = calculator._should_shade_window_from_flows(shade_request)  # type: ignore[attr-defined]

        assert result is False  # type: ignore[assert]
        assert "No room temperature sensor" in reason  # type: ignore[assert]
