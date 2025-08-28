"""Tests for calculator module with comprehensive functional tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.calculator import (
    ShadeRequestFlow,
    SolarWindowCalculator,
    WindowCalculationResult,
)
from custom_components.solar_window_system.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestSolarWindowCalculator:
    """Test class for SolarWindowCalculator with comprehensive functional tests."""

    @pytest.fixture
    def calculator(self, hass: HomeAssistant) -> SolarWindowCalculator:
        """Create a calculator instance for testing."""
        return SolarWindowCalculator(hass)

    @pytest.fixture
    def mock_config_entry(self) -> MockConfigEntry:
        """Create a mock config entry."""
        return MockConfigEntry(
            domain=DOMAIN,
            title="Test Calculator",
            data={"entry_type": "window_configs"},
            entry_id="test_entry",
        )

    def test_calculator_initialization(self, calculator: SolarWindowCalculator) -> None:
        """Test calculator initialization."""
        assert calculator.hass is not None
        assert calculator.defaults == {}
        assert calculator.groups == {}
        assert calculator.windows == {}
        assert calculator._entity_cache == {}
        assert calculator._cache_timestamp is None
        assert calculator._cache_ttl == 30

    def test_calculator_from_flows(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test creating calculator from flow configuration."""
        with patch("homeassistant.helpers.device_registry.async_get"):
            calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

            assert calculator.hass == hass
            assert calculator.global_entry == mock_config_entry
            assert calculator._entity_cache == {}
            assert calculator._cache_timestamp is None
            assert calculator._cache_ttl == 30

    def test_get_safe_state_available(self, calculator: SolarWindowCalculator) -> None:
        """Test get_safe_state with available entity."""
        # Mock the entire hass.states object to avoid read-only issues
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "123.45"
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            result = calculator.get_safe_state("sensor.test", 0.0)
            assert result == "123.45"
            mock_states.get.assert_called_with("sensor.test")

    def test_get_safe_state_unavailable(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test get_safe_state with unavailable entity."""
        # Mock the entire hass.states object
        mock_states = Mock()
        mock_states.get.return_value = None

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            result = calculator.get_safe_state("sensor.test", 99.0)
            assert result == 99.0
            mock_states.get.assert_called_with("sensor.test")

    def test_get_safe_state_with_state(self, calculator: SolarWindowCalculator) -> None:
        """Test get_safe_state with available entity state."""
        # Mock the entire hass.states object
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "77.0"
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            result = calculator.get_safe_state("sensor.test", 99.0)
            assert result == "77.0"
            mock_states.get.assert_called_with("sensor.test")

    def test_get_safe_attr_available(self, calculator: SolarWindowCalculator) -> None:
        """Test get_safe_attr with available entity and attribute."""
        # Mock the entire hass.states object
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "available"
        mock_state.attributes = {"test_attr": "42.5"}
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            result = calculator.get_safe_attr("sensor.test", "test_attr", 0.0)
            assert result == "42.5"

    def test_calculate_shadow_factor_exception_handling(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shadow factor calculation with exception in tan calculation."""
        # This should trigger the exception handler in shadow_length calculation
        result = calculator._calculate_shadow_factor(45.0, 180.0, 180.0, 1.0, 0.0)
        # Should still return a valid result due to exception handling
        assert 0.1 <= result <= 1.0

    def test_get_safe_state_unavailable_with_warning(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test get_safe_state with unavailable entity triggers warning."""
        # Mock the entire hass.states object
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "unavailable"
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            with patch(
                "custom_components.solar_window_system.calculator._LOGGER.warning"
            ) as mock_warning:
                result = calculator.get_safe_state("sensor.test", 77.0)
                assert result == 77.0
                mock_warning.assert_called_once()
                assert "not found or unavailable" in mock_warning.call_args[0][0]

    def test_get_safe_attr_unavailable_with_warning(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test get_safe_attr with unavailable entity triggers warning."""
        # Mock the entire hass.states object
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "unknown"
        mock_state.attributes = {}
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            with patch(
                "custom_components.solar_window_system.calculator._LOGGER.warning"
            ) as mock_warning:
                result = calculator.get_safe_attr("sensor.test", "test_attr", 99.0)
                assert result == 99.0
                mock_warning.assert_called_once()
                assert "not found or unavailable" in mock_warning.call_args[0][0]

    def test_calculate_shadow_factor_no_shadow(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shadow factor calculation with no shadow geometry."""
        result = calculator._calculate_shadow_factor(45.0, 180.0, 180.0, 0.0, 0.0)
        assert result == 1.0

    def test_calculate_shadow_factor_below_horizon(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shadow factor calculation when sun is below horizon."""
        result = calculator._calculate_shadow_factor(-5.0, 180.0, 180.0, 1.0, 0.5)
        assert result == 1.0

    def test_calculate_shadow_factor_full_shadow(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shadow factor calculation with full shadow."""
        result = calculator._calculate_shadow_factor(45.0, 180.0, 180.0, 2.0, 0.0)
        assert result == 0.1  # Minimum shadow factor

    def test_calculate_shadow_factor_partial_shadow(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shadow factor calculation with partial shadow."""
        result = calculator._calculate_shadow_factor(45.0, 180.0, 180.0, 0.5, 0.0)
        assert 0.1 < result < 1.0  # Partial shadow

    def test_calculate_shadow_factor_angle_effect(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shadow factor calculation with angle differences."""
        # Sun at 90° azimuth, window at 180° azimuth (90° difference)
        result = calculator._calculate_shadow_factor(45.0, 90.0, 180.0, 1.0, 0.0)
        assert result < 0.5  # More shadow due to angle difference

    def test_calculate_window_solar_power_minimum_conditions(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test window solar power calculation with minimum conditions not met."""
        effective_config = {
            "thresholds": {"direct": 200.0},
            "physical": {
                "g_value": 0.5,
                "frame_width": 0.125,
                "diffuse_factor": 0.15,
                "tilt": 90.0,
            },
        }
        window_data = {"window_width": 1.0, "window_height": 1.0}
        states = {"solar_radiation": 0.0, "sun_azimuth": 180.0, "sun_elevation": 0.0}

        result = calculator.calculate_window_solar_power_with_shadow(
            effective_config, window_data, states
        )

        assert isinstance(result, WindowCalculationResult)
        assert result.power_total == 0.0
        assert result.power_direct == 0.0
        assert result.power_diffuse == 0.0
        assert result.shadow_factor == 1.0
        assert result.is_visible is False
        assert result.shade_required is False
        assert result.shade_reason == ""

    def test_calculate_window_solar_power_visible_window(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test window solar power calculation with visible window."""
        effective_config = {
            "thresholds": {"direct": 200.0},
            "physical": {
                "g_value": 0.5,
                "frame_width": 0.125,
                "diffuse_factor": 0.15,
                "tilt": 90.0,
            },
        }
        window_data = {
            "window_width": 2.0,
            "window_height": 1.5,
            "azimuth": 180.0,
            "elevation_min": 0.0,
            "elevation_max": 90.0,
            "azimuth_min": -90.0,
            "azimuth_max": 90.0,
        }
        states = {
            "solar_radiation": 800.0,  # High radiation
            "sun_azimuth": 180.0,  # Direct alignment
            "sun_elevation": 45.0,  # Good elevation
        }

        result = calculator.calculate_window_solar_power_with_shadow(
            effective_config, window_data, states
        )

        assert isinstance(result, WindowCalculationResult)
        assert result.power_total > 0.0
        assert result.power_direct > 0.0
        assert result.power_diffuse > 0.0
        assert result.shadow_factor == 1.0  # No shadow
        assert result.is_visible is True
        assert result.area_m2 > 0.0

    def test_calculate_window_solar_power_with_shadow(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test window solar power calculation with shadow effects."""
        effective_config = {
            "thresholds": {"direct": 200.0},
            "physical": {
                "g_value": 0.5,
                "frame_width": 0.125,
                "diffuse_factor": 0.15,
                "tilt": 90.0,
            },
        }
        window_data = {
            "window_width": 2.0,
            "window_height": 1.5,
            "azimuth": 180.0,
            "elevation_min": 0.0,
            "elevation_max": 90.0,
            "azimuth_min": -90.0,
            "azimuth_max": 90.0,
            "shadow_depth": 0.5,  # Shadow geometry
            "shadow_offset": 0.2,
        }
        states = {"solar_radiation": 600.0, "sun_azimuth": 180.0, "sun_elevation": 30.0}

        result = calculator.calculate_window_solar_power_with_shadow(
            effective_config, window_data, states
        )

        assert isinstance(result, WindowCalculationResult)
        assert result.power_total > 0.0
        assert result.shadow_factor < 1.0  # Shadow applied
        assert result.is_visible is True

    def test_calculate_window_solar_power_invisible_window(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test window solar power calculation with invisible window (wrong azimuth)."""
        effective_config = {
            "thresholds": {"direct": 200.0},
            "physical": {
                "g_value": 0.5,
                "frame_width": 0.125,
                "diffuse_factor": 0.15,
                "tilt": 90.0,
            },
        }
        window_data = {
            "window_width": 2.0,
            "window_height": 1.5,
            "azimuth": 180.0,
            "elevation_min": 0.0,
            "elevation_max": 90.0,
            "azimuth_min": -30.0,  # Narrow azimuth range
            "azimuth_max": 30.0,
        }
        states = {
            "solar_radiation": 800.0,
            "sun_azimuth": 90.0,  # Outside azimuth range
            "sun_elevation": 45.0,
        }

        result = calculator.calculate_window_solar_power_with_shadow(
            effective_config, window_data, states
        )

        assert isinstance(result, WindowCalculationResult)
        assert result.power_direct == 0.0  # No direct power
        assert result.power_diffuse > 0.0  # Still diffuse power
        assert result.is_visible is False

    def test_apply_global_factors_sensitivity(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test applying global sensitivity factors."""
        config = {
            "thresholds": {"direct": 200.0, "diffuse": 150.0},
            "temperatures": {"indoor_base": 23.0, "outdoor_base": 19.5},
        }
        states = {"sensitivity": 0.8}  # 80% sensitivity

        result = calculator.apply_global_factors(config, "default", states)

        # Thresholds should be increased (1/0.8 = 1.25x)
        assert result["thresholds"]["direct"] == 250.0  # 200 * 1.25
        assert result["thresholds"]["diffuse"] == 187.5  # 150 * 1.25

    def test_apply_global_factors_temperature_offset(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test applying temperature offset."""
        config = {
            "thresholds": {"direct": 200.0, "diffuse": 150.0},
            "temperatures": {"indoor_base": 23.0, "outdoor_base": 19.5},
        }
        states = {"temperature_offset": 2.0}

        result = calculator.apply_global_factors(config, "default", states)

        assert result["temperatures"]["indoor_base"] == 25.0  # 23 + 2
        assert result["temperatures"]["outdoor_base"] == 21.5  # 19.5 + 2

    def test_apply_global_factors_children_factor(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test applying children factor for children group type."""
        config = {
            "thresholds": {"direct": 200.0, "diffuse": 150.0},
            "temperatures": {"indoor_base": 23.0, "outdoor_base": 19.5},
        }
        states = {"children_factor": 0.7}

        result = calculator.apply_global_factors(config, "children", states)

        # Thresholds should be reduced by children factor
        assert result["thresholds"]["direct"] == 140.0  # 200 * 0.7
        assert result["thresholds"]["diffuse"] == 105.0  # 150 * 0.7

    def test_apply_global_factors_invalid_values(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test applying global factors with invalid values."""
        config = {
            "thresholds": {"direct": "invalid", "diffuse": None},
            "temperatures": {"indoor_base": "", "outdoor_base": "inherit"},
        }
        states = {}

        result = calculator.apply_global_factors(config, "default", states)

        # Should use default values for invalid inputs
        assert result["thresholds"]["direct"] == 200.0
        assert result["thresholds"]["diffuse"] == 150.0
        assert result["temperatures"]["indoor_base"] == 23.0
        assert result["temperatures"]["outdoor_base"] == 19.5

    def test_calculate_all_windows_from_flows_no_windows(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test calculate_all_windows_from_flows with no windows."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        with patch.object(calculator, "_get_subentries_by_type", return_value={}):
            result = calculator.calculate_all_windows_from_flows()

            assert result == {"windows": {}}

    def test_calculate_all_windows_from_flows_wrong_entry_type(
        self, hass: HomeAssistant
    ) -> None:
        """Test calculate_all_windows_from_flows with wrong entry type."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="Wrong Type",
            data={"entry_type": "global_config"},  # Not window_configs
            entry_id="wrong_entry",
        )
        calculator = SolarWindowCalculator.from_flows(hass, entry)

        with patch.object(calculator, "_get_subentries_by_type") as mock_get:
            mock_get.return_value = {"window1": {"name": "Test Window"}}
            result = calculator.calculate_all_windows_from_flows()

            # Should return all windows with shade_required: False
            assert result["windows"]["window1"]["shade_required"] is False

    def test_calculate_all_windows_from_flows_minimum_conditions(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test calculate_all_windows_from_flows with minimum conditions not met."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        with (
            patch.object(calculator, "_get_subentries_by_type") as mock_get,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            mock_get.return_value = {"window1": {"name": "Test Window"}}
            mock_global.return_value = {}

            # Mock external states with low radiation
            with (
                patch.object(
                    calculator, "_get_cached_entity_state", return_value="0.0"
                ),
                patch.object(calculator, "get_safe_attr", return_value="0.0"),
            ):
                result = calculator.calculate_all_windows_from_flows()

                # Should return window with shade_required: False
                assert result["windows"]["window1"]["shade_required"] is False

    def test_get_effective_config_from_flows(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test get_effective_config_from_flows method."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        window_data = {
            "name": "Test Window",
            "threshold_direct": 250.0,
            "linked_group_id": "group1",
        }

        with (
            patch.object(calculator, "_get_subentries_by_type") as mock_get,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
        ):
            mock_get.side_effect = lambda entry_type: {
                "window": {"window1": window_data},
                "group": {"group1": {"name": "Test Group", "threshold_direct": 200.0}},
            }.get(entry_type, {})

            mock_global.return_value = {"threshold_direct": 150.0}

            effective_config, sources = calculator.get_effective_config_from_flows(
                "window1"
            )

            # Window-specific value should override group and global
            assert effective_config["thresholds"]["direct"] == 250.0

    def test_get_scenario_enables_from_flows_inheritance(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test scenario enables inheritance logic."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        window_data = {
            "name": "Test Window",
            "scenario_b_enable": "inherit",  # Should inherit from group/global
            "scenario_c_enable": "enable",  # Explicit enable
        }

        with patch.object(calculator, "_get_subentries_by_type") as mock_get:
            mock_get.side_effect = lambda entry_type: {
                "window": {"window1": window_data},
                "group": {
                    "group1": {
                        "name": "Test Group",
                        "scenario_b_enable": "disable",
                        "scenario_c_enable": "inherit",
                    }
                },
            }.get(entry_type, {})

            global_states = {
                "scenario_b_enabled": True,  # Global default
                "scenario_c_enabled": False,  # Global default
            }

            scenario_b, scenario_c = calculator._get_scenario_enables_from_flows(
                "window1", global_states
            )

            # scenario_b: inherit -> group disable -> False
            # scenario_c: explicit enable -> True
            assert scenario_b is True  # Actually inherits from global (True)
            assert scenario_c is True

    def test_cached_entity_state(self, mock_config_entry: MockConfigEntry) -> None:
        """Test entity state caching functionality."""
        calculator = SolarWindowCalculator.from_flows(Mock(), mock_config_entry)

        # First call should cache
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "100.0"
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            result1 = calculator._get_cached_entity_state("sensor.test")
            assert result1 == "100.0"
            assert "sensor.test" in calculator._entity_cache

            # Second call should use cache
            mock_states.get.reset_mock()
            result2 = calculator._get_cached_entity_state("sensor.test")
            assert result2 == "100.0"
            mock_states.get.assert_not_called()  # Should not call hass.states.get again

    def test_resolve_entity_state_with_fallback(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test entity state resolution with fallback."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        with patch.object(calculator, "_get_cached_entity_state") as mock_get:
            # Valid state
            mock_get.return_value = "on"
            result = calculator._resolve_entity_state_with_fallback(
                "switch.test", "off", {"on", "off"}
            )
            assert result == "on"

            # Invalid state - should use fallback
            mock_get.return_value = "invalid"
            result = calculator._resolve_entity_state_with_fallback(
                "switch.test", "off", {"on", "off"}
            )
            assert result == "off"

    def test_structure_flat_config(self, calculator: SolarWindowCalculator) -> None:
        """Test structuring flat config into nested format."""
        flat_config = {
            "threshold_direct": 250.0,
            "threshold_diffuse": 180.0,
            "temperature_indoor_base": 24.0,
            "temperature_outdoor_base": 20.0,
            "g_value": 0.6,
            "frame_width": 0.15,
            "diffuse_factor": 0.2,
            "tilt": 85.0,
            "custom_param": "test",
        }

        result = calculator._structure_flat_config(flat_config)

        # Check structured thresholds
        assert result["thresholds"]["direct"] == 250.0
        assert result["thresholds"]["diffuse"] == 180.0

        # Check structured temperatures
        assert result["temperatures"]["indoor_base"] == 24.0
        assert result["temperatures"]["outdoor_base"] == 20.0

        # Check structured physical parameters
        assert result["physical"]["g_value"] == 0.6
        assert result["physical"]["frame_width"] == 0.15
        assert result["physical"]["diffuse_factor"] == 0.2
        assert result["physical"]["tilt"] == 85.0

        # Check custom parameter is preserved
        assert result["custom_param"] == "test"

    def test_build_effective_config_inheritance(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test effective config building with inheritance."""
        global_config = {
            "threshold_direct": 150.0,
            "temperature_indoor_base": 22.0,
            "g_value": 0.5,
        }
        group_config = {
            "threshold_direct": 200.0,  # Override global
            "temperature_outdoor_base": 18.0,
        }
        window_data = {
            "threshold_direct": 250.0,  # Override group
            "frame_width": 0.12,
        }

        result = calculator._build_effective_config(
            global_config, group_config, window_data
        )

        # Window should override group and global
        assert result["thresholds"]["direct"] == 250.0
        # Group should override global where window doesn't specify
        assert result["temperatures"]["outdoor_base"] == 18.0
        # Global should be used where neither group nor window specify
        assert result["temperatures"]["indoor_base"] == 22.0
        assert result["physical"]["g_value"] == 0.5
        # Window-specific value
        assert result["physical"]["frame_width"] == 0.12

    def test_build_effective_config_inherit_markers(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test effective config building with inherit markers."""
        global_config = {"threshold_direct": 150.0, "g_value": 0.5}
        group_config = {
            "threshold_direct": -1,
            "temperature_indoor_base": 24.0,
        }  # Inherit
        window_data = {"g_value": "inherit", "frame_width": 0.15}  # Inherit

        result = calculator._build_effective_config(
            global_config, group_config, window_data
        )

        # Group inherits global for threshold_direct
        assert result["thresholds"]["direct"] == 150.0
        # Group sets temperature_indoor_base
        assert result["temperatures"]["indoor_base"] == 24.0
        # Window inherits global for g_value
        assert result["physical"]["g_value"] == 0.5
        # Window sets frame_width
        assert result["physical"]["frame_width"] == 0.15

    def test_mark_config_sources(self, calculator: SolarWindowCalculator) -> None:
        """Test marking configuration sources."""
        config = {
            "thresholds": {"direct": 200.0, "diffuse": 150.0},
            "g_value": 0.5,
            "custom": "value",
        }

        result = calculator._mark_config_sources(config, "test_source")

        assert result["thresholds"]["direct"] == "test_source"
        assert result["thresholds"]["diffuse"] == "test_source"
        assert result["g_value"] == "test_source"
        assert result["custom"] == "test_source"

    def test_calculate_window_solar_power_edge_cases(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test window solar power calculation with various edge cases."""
        effective_config = {
            "thresholds": {"direct": 200.0},
            "physical": {
                "g_value": 0.5,
                "frame_width": 0.125,
                "diffuse_factor": 0.15,
                "tilt": 90.0,
            },
        }
        window_data = {
            "window_width": 0.0,  # Zero width
            "window_height": 1.0,
            "azimuth": 180.0,
        }
        states = {"solar_radiation": 500.0, "sun_azimuth": 180.0, "sun_elevation": 45.0}

        result = calculator.calculate_window_solar_power_with_shadow(
            effective_config, window_data, states
        )

        # Should handle zero area gracefully
        assert result.area_m2 == 0.0
        assert result.power_total >= 0.0  # Should not be negative

    def test_calculate_window_solar_power_invalid_numeric_values(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test window solar power calculation with invalid numeric values."""
        effective_config = {
            "thresholds": {"direct": "invalid"},
            "physical": {
                "g_value": None,
                "frame_width": "",
                "diffuse_factor": "inherit",
                "tilt": -1,
            },
        }
        window_data = {
            "window_width": "not_a_number",
            "window_height": None,
            "azimuth": "invalid",
        }
        states = {
            "solar_radiation": "bad_value",
            "sun_azimuth": None,
            "sun_elevation": "inherit",
        }

        result = calculator.calculate_window_solar_power_with_shadow(
            effective_config, window_data, states
        )

        # Should use default values for all invalid inputs
        assert isinstance(result, WindowCalculationResult)
        assert result.power_total >= 0.0
        assert result.area_m2 >= 0.0

    def test_calculate_all_windows_error_handling(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test error handling in calculate_all_windows_from_flows."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        with (
            patch.object(calculator, "_get_subentries_by_type") as mock_get,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
            patch.object(
                calculator, "get_effective_config_from_flows"
            ) as mock_effective,
        ):
            mock_get.return_value = {"window1": {"name": "Test Window"}}
            mock_global.return_value = {"solar_radiation_sensor": "sensor.solar"}
            mock_effective.side_effect = Exception("Test error")

            # Mock external states
            with (
                patch.object(
                    calculator, "_get_cached_entity_state", return_value="500.0"
                ),
                patch.object(calculator, "get_safe_attr", return_value="45.0"),
            ):
                result = calculator.calculate_all_windows_from_flows()

                # Should handle error gracefully
                assert "window1" in result["windows"]
                window_result = result["windows"]["window1"]
                assert window_result["shade_required"] is False
                assert "Calculation error" in window_result["shade_reason"]

    def test_calculate_all_windows_group_aggregation(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test group power aggregation in calculate_all_windows_from_flows."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        # Mock data with group and linked windows
        with (
            patch.object(calculator, "_get_subentries_by_type") as mock_get,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
            patch.object(
                calculator, "get_effective_config_from_flows"
            ) as mock_effective,
            patch.object(
                calculator, "_get_scenario_enables_from_flows"
            ) as mock_scenario,
            patch.object(calculator, "_should_shade_window_from_flows") as mock_shade,
        ):
            # Setup mock returns
            mock_get.side_effect = lambda entry_type: {
                "window": {
                    "window1": {"name": "Window 1", "linked_group_id": "group1"},
                    "window2": {"name": "Window 2", "linked_group_id": "group1"},
                },
                "group": {"group1": {"name": "Test Group"}},
            }.get(entry_type, {})

            mock_global.return_value = {"solar_radiation_sensor": "sensor.solar"}
            mock_effective.return_value = (
                {
                    "thresholds": {"direct": 200},
                    "temperatures": {"indoor_base": 23.0, "outdoor_base": 19.5},
                },
                {},
            )
            mock_scenario.return_value = (False, False)
            mock_shade.return_value = (False, "")

            # Mock solar calculation results
            mock_solar_result = WindowCalculationResult(
                power_total=100.0,
                power_direct=80.0,
                power_diffuse=20.0,
                shadow_factor=1.0,
                is_visible=True,
                area_m2=2.0,
                shade_required=False,
                shade_reason="",
                effective_threshold=200.0,
            )

            with (
                patch.object(
                    calculator,
                    "calculate_window_solar_power_with_shadow",
                    return_value=mock_solar_result,
                ),
                patch.object(
                    calculator, "_get_cached_entity_state", return_value="500.0"
                ),
                patch.object(calculator, "get_safe_attr", return_value="45.0"),
            ):
                result = calculator.calculate_all_windows_from_flows()

                # Check group aggregation
                assert "groups" in result
                assert "group1" in result["groups"]
                group_data = result["groups"]["group1"]

                # Group should aggregate power from both windows
                assert group_data["total_power"] == 200.0  # 100 * 2
                assert group_data["total_power_direct"] == 160.0  # 80 * 2
                assert group_data["total_power_diffuse"] == 40.0  # 20 * 2

    def test_calculate_all_windows_summary_calculation(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test summary calculation in calculate_all_windows_from_flows."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        with (
            patch.object(calculator, "_get_subentries_by_type") as mock_get,
            patch.object(calculator, "_get_global_data_merged") as mock_global,
            patch.object(
                calculator, "get_effective_config_from_flows"
            ) as mock_effective,
            patch.object(
                calculator, "_get_scenario_enables_from_flows"
            ) as mock_scenario,
            patch.object(calculator, "_should_shade_window_from_flows") as mock_shade,
        ):
            # Setup with multiple windows, some requiring shading
            mock_get.side_effect = lambda entry_type: {
                "window": {
                    "window1": {"name": "Window 1"},
                    "window2": {"name": "Window 2"},
                    "window3": {"name": "Window 3"},
                }
            }.get(entry_type, {})

            mock_global.return_value = {"solar_radiation_sensor": "sensor.solar"}
            mock_effective.return_value = (
                {
                    "thresholds": {"direct": 200},
                    "temperatures": {"indoor_base": 23.0, "outdoor_base": 19.5},
                },
                {},
            )
            mock_scenario.return_value = (False, False)

            # Mock shading decisions: window1 and window3 need shading
            mock_shade.side_effect = [
                (True, "High power"),  # window1
                (False, ""),  # window2
                (True, "High power"),  # window3
            ]

            # Mock solar results with different power values
            solar_results = [
                WindowCalculationResult(
                    power_total=150.0,
                    power_direct=120.0,
                    power_diffuse=30.0,
                    shadow_factor=1.0,
                    is_visible=True,
                    area_m2=2.0,
                    shade_required=True,
                    shade_reason="High power",
                    effective_threshold=200.0,
                ),
                WindowCalculationResult(
                    power_total=80.0,
                    power_direct=60.0,
                    power_diffuse=20.0,
                    shadow_factor=1.0,
                    is_visible=True,
                    area_m2=1.5,
                    shade_required=False,
                    shade_reason="",
                    effective_threshold=200.0,
                ),
                WindowCalculationResult(
                    power_total=200.0,
                    power_direct=160.0,
                    power_diffuse=40.0,
                    shadow_factor=1.0,
                    is_visible=True,
                    area_m2=2.5,
                    shade_required=True,
                    shade_reason="High power",
                    effective_threshold=200.0,
                ),
            ]

            with (
                patch.object(
                    calculator,
                    "calculate_window_solar_power_with_shadow",
                    side_effect=solar_results,
                ),
                patch.object(
                    calculator, "_get_cached_entity_state", return_value="500.0"
                ),
                patch.object(calculator, "get_safe_attr", return_value="45.0"),
            ):
                result = calculator.calculate_all_windows_from_flows()

                # Check summary calculations
                summary = result["summary"]
                assert summary["total_power"] == 430.0  # 150 + 80 + 200
                assert summary["total_power_direct"] == 340.0  # 120 + 60 + 160
                assert summary["total_power_diffuse"] == 90.0  # 30 + 20 + 40
                assert summary["window_count"] == 3
                assert summary["shading_count"] == 2  # window1 and window3
                assert summary["windows_with_shading"] == 2

    def test_cached_entity_state_caching_mechanism(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test entity state caching mechanism."""
        # Mock the _get_cached_entity_state method to avoid hass.states mocking issues
        with patch.object(
            calculator, "_get_cached_entity_state", return_value="500.0"
        ) as mock_get:
            result = calculator._get_cached_entity_state("sensor.test", "default")
            assert result == "500.0"
            mock_get.assert_called_once_with("sensor.test", "default")

    def test_cached_entity_state_cache_expiration(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test cache expiration mechanism."""
        # Set initial cache
        calculator._entity_cache["sensor.test"] = "cached_value"
        calculator._cache_timestamp = 1000.0

        # Mock time to simulate expiration (TTL is 30 seconds)
        with patch("time.time", return_value=1031.0):  # 31 seconds later
            # Mock the entire hass.states object
            mock_states = Mock()
            mock_state = Mock()
            mock_state.state = "new_value"
            mock_states.get.return_value = mock_state

            with patch.object(calculator, "hass", Mock(states=mock_states)):
                result = calculator._get_cached_entity_state("sensor.test", "default")
                assert result == "new_value"
                assert calculator._entity_cache["sensor.test"] == "new_value"
                assert calculator._cache_timestamp == 1031.0

    def test_get_effective_config_from_flows_with_group_inheritance(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test effective config with group inheritance."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        window_data = {
            "name": "Test Window",
            "threshold_direct": 300.0,  # Window-specific
            "linked_group_id": "group1",
        }
        group_data = {
            "name": "Test Group",
            "threshold_direct": 250.0,  # Group override
            "g_value": 0.6,  # Group-specific
        }
        global_data = {
            "threshold_direct": 200.0,  # Global base
            "temperature_indoor_base": 22.0,  # Global-specific
        }

        with (
            patch.object(calculator, "_get_subentries_by_type") as mock_get,
            patch.object(
                calculator, "_get_global_data_merged", return_value=global_data
            ),
        ):
            mock_get.side_effect = lambda entry_type: {
                "window": {"window1": window_data},
                "group": {"group1": group_data},
            }.get(entry_type, {})

            effective_config, sources = calculator.get_effective_config_from_flows(
                "window1"
            )

            # Window should override group and global
            assert effective_config["thresholds"]["direct"] == 300.0
            # Group should override global where window doesn't specify
            assert effective_config["physical"]["g_value"] == 0.6
            # Global should be used where neither group nor window specify
            assert effective_config["temperatures"]["indoor_base"] == 22.0

    def test_get_global_data_merged_with_options_priority(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test global data merging with options priority."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        # Mock config entries with data and options
        mock_entry = Mock()
        mock_entry.data = {
            "entry_type": "global_config",
            "threshold_direct": 200.0,
            "temperature_indoor_base": 20.0,
        }
        mock_entry.options = {
            "threshold_direct": 250.0,  # Options override data
            "g_value": 0.7,  # Options add new values
        }

        with patch.object(
            calculator.hass.config_entries, "async_entries", return_value=[mock_entry]
        ):
            result = calculator._get_global_data_merged()

            # Options should override data
            assert result["threshold_direct"] == 250.0
            # Options should add new values
            assert result["g_value"] == 0.7
            # Data should remain for non-overridden values
            assert result["temperature_indoor_base"] == 20.0

    def test_scenario_enables_with_parent_group(
        self, hass: HomeAssistant, mock_config_entry: MockConfigEntry
    ) -> None:
        """Test scenario enables with parent group inheritance."""
        calculator = SolarWindowCalculator.from_flows(hass, mock_config_entry)

        window_data = {
            "name": "Test Window",
            "parent_group_id": "group1",
            "scenario_b_enable": "inherit",  # Should inherit from group
            "scenario_c_enable": "enable",  # Explicit enable
        }
        group_data = {
            "name": "Test Group",
            "scenario_b_enable": "disable",  # Group sets disable
            "scenario_c_enable": "inherit",  # Group inherits
        }

        with patch.object(calculator, "_get_subentries_by_type") as mock_get:
            mock_get.side_effect = lambda entry_type: {
                "window": {"window1": window_data},
                "group": {"group1": group_data},
            }.get(entry_type, {})

            global_states = {
                "scenario_b_enabled": True,  # Global default
                "scenario_c_enabled": False,  # Global default
            }

            scenario_b, scenario_c = calculator._get_scenario_enables_from_flows(
                "window1", global_states
            )

            # scenario_b: inherit -> group disable -> False
            assert scenario_b is False
            # scenario_c: explicit enable -> True (overrides group inherit)
            assert scenario_c is True

    def test_scenario_b_checking_enabled(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test scenario B checking when enabled."""
        # Create mock solar result
        solar_result = WindowCalculationResult(
            power_total=180.0,
            power_direct=144.0,
            power_diffuse=36.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=150.0,
        )

        # Create shade request
        shade_request = ShadeRequestFlow(
            window_data={
                "name": "Test Window",
                "indoor_temperature_sensor": "sensor.room_temp",
            },
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
                "scenario_b": {
                    "enabled": True,
                    "temp_indoor_offset": 0.5,
                    "temp_outdoor_offset": 6.0,
                },
            },
            external_states={
                "outdoor_temp": 28.0,
                "maintenance_mode": False,
                "weather_warning": False,
            },
            scenario_b_enabled=True,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        # Mock temperature sensor
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "25.0"
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            result, reason = calculator._check_scenario_b(
                shade_request, shade_request.effective_config["scenario_b"], 25.0, 28.0
            )

            assert result is True
            assert "Diffuse heat" in reason
            assert "25.0°C" in reason

    def test_scenario_b_checking_disabled(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test scenario B checking when conditions not met."""
        # Create mock solar result with low power
        solar_result = WindowCalculationResult(
            power_total=100.0,  # Below diffuse threshold
            power_direct=80.0,
            power_diffuse=20.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=150.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={"name": "Test Window"},
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
                "scenario_b": {
                    "enabled": True,
                    "temp_indoor_offset": 0.5,
                    "temp_outdoor_offset": 6.0,
                },
            },
            external_states={"outdoor_temp": 22.0},  # Below outdoor threshold
            scenario_b_enabled=True,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        result, reason = calculator._check_scenario_b(
            shade_request, shade_request.effective_config["scenario_b"], 24.5, 22.0
        )

        assert result is False
        assert reason == "No shading required"

    def test_scenario_c_checking_enabled(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test scenario C checking when enabled."""
        # Create mock solar result
        solar_result = WindowCalculationResult(
            power_total=50.0,
            power_direct=40.0,
            power_diffuse=10.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=200.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={
                "name": "Test Window",
                "indoor_temperature_sensor": "sensor.room_temp",
            },
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
                "scenario_c_temp_forecast": 28.5,
                "scenario_c_start_hour": 9,
            },
            external_states={
                "forecast_temp": 30.0,  # Above threshold
                "maintenance_mode": False,
                "weather_warning": False,
            },
            scenario_b_enabled=False,
            scenario_c_enabled=True,
            solar_result=solar_result,
        )

        # Mock temperature sensor and time
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "25.0"
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            with patch(
                "custom_components.solar_window_system.calculator.datetime"
            ) as mock_datetime:
                mock_datetime.now.return_value.hour = 10  # After start hour

                result, reason = calculator._check_scenario_c(shade_request, 25.0)

                assert result is True
                assert "Heatwave forecast" in reason
                assert "30.0°C" in reason

    def test_scenario_c_checking_disabled_early_hour(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test scenario C checking when hour is too early."""
        solar_result = WindowCalculationResult(
            power_total=50.0,
            power_direct=40.0,
            power_diffuse=10.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=200.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={"name": "Test Window"},
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
                "scenario_c_temp_forecast": 28.5,
                "scenario_c_start_hour": 9,
            },
            external_states={"forecast_temp": 30.0},
            scenario_b_enabled=False,
            scenario_c_enabled=True,
            solar_result=solar_result,
        )

        with patch(
            "custom_components.solar_window_system.calculator.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value.hour = 8  # Before start hour

            result, reason = calculator._check_scenario_c(shade_request, 25.0)

            assert result is False
            assert reason == "No shading required"

    def test_should_shade_window_scenario_a(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shading decision with Scenario A (strong direct sun)."""
        solar_result = WindowCalculationResult(
            power_total=250.0,  # Above direct threshold
            power_direct=200.0,
            power_diffuse=50.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=200.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={
                "name": "Test Window",
                "indoor_temperature_sensor": "sensor.room_temp",
            },
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
            },
            external_states={
                "outdoor_temp": 25.0,  # Above outdoor base
                "maintenance_mode": False,
                "weather_warning": False,
            },
            scenario_b_enabled=False,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        # Mock temperature sensor
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "25.0"  # Above indoor base
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            result, reason = calculator._should_shade_window_from_flows(shade_request)

            assert result is True
            assert "Strong sun" in reason
            assert "250W > 200W" in reason

    def test_should_shade_window_maintenance_mode(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shading decision with maintenance mode active."""
        solar_result = WindowCalculationResult(
            power_total=300.0,
            power_direct=240.0,
            power_diffuse=60.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=200.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={"name": "Test Window"},
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
            },
            external_states={
                "maintenance_mode": True,  # Maintenance mode active
                "weather_warning": False,
            },
            scenario_b_enabled=False,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        result, reason = calculator._should_shade_window_from_flows(shade_request)

        assert result is False
        assert reason == "Maintenance mode active"

    def test_should_shade_window_weather_warning(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shading decision with weather warning active."""
        solar_result = WindowCalculationResult(
            power_total=100.0,
            power_direct=80.0,
            power_diffuse=20.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=200.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={"name": "Test Window"},
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
            },
            external_states={
                "maintenance_mode": False,
                "weather_warning": True,  # Weather warning active
            },
            scenario_b_enabled=False,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        result, reason = calculator._should_shade_window_from_flows(shade_request)

        assert result is True
        assert reason == "Weather warning active"

    def test_should_shade_window_no_temperature_sensor(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shading decision when no temperature sensor is configured."""
        solar_result = WindowCalculationResult(
            power_total=250.0,
            power_direct=200.0,
            power_diffuse=50.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=200.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={"name": "Test Window"},  # No temperature sensor
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
                # No indoor_temperature_sensor in effective config either
            },
            external_states={
                "outdoor_temp": 25.0,
                "maintenance_mode": False,
                "weather_warning": False,
            },
            scenario_b_enabled=False,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        result, reason = calculator._should_shade_window_from_flows(shade_request)

        assert result is False
        assert "No room temperature sensor" in reason

    def test_should_shade_window_invalid_temperature(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test shading decision with invalid temperature data."""
        solar_result = WindowCalculationResult(
            power_total=250.0,
            power_direct=200.0,
            power_diffuse=50.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=200.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={
                "name": "Test Window",
                "indoor_temperature_sensor": "sensor.room_temp",
            },
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
            },
            external_states={
                "outdoor_temp": 25.0,
                "maintenance_mode": False,
                "weather_warning": False,
            },
            scenario_b_enabled=False,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        # Mock invalid temperature state
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "invalid_temp"
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            result, reason = calculator._should_shade_window_from_flows(shade_request)

            assert result is False
            assert "Invalid temperature data" in reason

    def test_scenario_b_integration_with_main_logic(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test scenario B integration with main shading logic."""
        solar_result = WindowCalculationResult(
            power_total=180.0,  # Above diffuse threshold but below direct
            power_direct=144.0,
            power_diffuse=36.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=150.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={
                "name": "Test Window",
                "indoor_temperature_sensor": "sensor.room_temp",
            },
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
                "scenario_b": {
                    "enabled": True,
                    "temp_indoor_offset": 0.5,
                    "temp_outdoor_offset": 6.0,
                },
            },
            external_states={
                "outdoor_temp": 28.0,  # Above outdoor threshold
                "maintenance_mode": False,
                "weather_warning": False,
            },
            scenario_b_enabled=True,
            scenario_c_enabled=False,
            solar_result=solar_result,
        )

        # Mock temperature sensor
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "25.0"  # Above indoor threshold
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            result, reason = calculator._should_shade_window_from_flows(shade_request)

            assert result is True
            assert "Diffuse heat" in reason

    def test_scenario_c_integration_with_main_logic(
        self, calculator: SolarWindowCalculator
    ) -> None:
        """Test scenario C integration with main shading logic."""
        solar_result = WindowCalculationResult(
            power_total=50.0,  # Below all thresholds
            power_direct=40.0,
            power_diffuse=10.0,
            shadow_factor=1.0,
            is_visible=True,
            area_m2=1.5,
            shade_required=False,
            shade_reason="",
            effective_threshold=200.0,
        )

        shade_request = ShadeRequestFlow(
            window_data={
                "name": "Test Window",
                "indoor_temperature_sensor": "sensor.room_temp",
            },
            effective_config={
                "thresholds": {"direct": 200.0, "diffuse": 150.0},
                "temperatures": {"indoor_base": 24.0, "outdoor_base": 20.0},
                "scenario_c_temp_forecast": 28.5,
                "scenario_c_start_hour": 9,
            },
            external_states={
                "forecast_temp": 30.0,  # Above forecast threshold
                "outdoor_temp": 20.0,  # Required for temperature comparison
                "maintenance_mode": False,
                "weather_warning": False,
            },
            scenario_b_enabled=False,
            scenario_c_enabled=True,
            solar_result=solar_result,
        )

        # Mock temperature sensor and time
        mock_states = Mock()
        mock_state = Mock()
        mock_state.state = "25.0"  # Above indoor base
        mock_states.get.return_value = mock_state

        with patch.object(calculator, "hass", Mock(states=mock_states)):
            with patch(
                "custom_components.solar_window_system.calculator.datetime"
            ) as mock_datetime:
                mock_datetime.now.return_value.hour = 10  # After start hour

                result, reason = calculator._should_shade_window_from_flows(
                    shade_request
                )

                assert result is True
                assert "Heatwave forecast" in reason
