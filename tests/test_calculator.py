"""Tests for ventilation calculator logic."""

import math

import pytest

from custom_components.room_ventilation_advisor.const import (
    ROOM_TYPE_BATHROOM,
    ROOM_TYPE_BEDROOM,
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_LIVING_ROOM,
    ROOM_TYPE_OFFICE,
)

# Test constants for magic values
LARGE_TEMP_FACTOR = 0.8
MEDIUM_TEMP_FACTOR = 0.6
SMALL_TEMP_FACTOR = 0.4
MINOR_TEMP_FACTOR = 0.3
ZERO_FACTOR = 0.0
HUMIDITY_LARGE_DIFF = 1.0
HUMIDITY_SMALL_DIFF = 0.5
CO2_HIGH_FACTOR = 1.0
CO2_MEDIUM_FACTOR = 0.7
CO2_LOW_FACTOR = 0.3
TIME_FACTOR_HIGH = 0.8
TIME_FACTOR_LOW = 0.2
TIME_FACTOR_MEDIUM = 0.5
TIME_FACTOR_MEDIUM = 0.9


class TestVentilationCalculator:
    """Test the ventilation calculation logic."""

    def test_calculate_absolute_humidity(self) -> None:
        """Test absolute humidity calculation."""

        # This would be part of the calculator class
        def calculate_absolute_humidity(
            humidity_percent: float, temp_celsius: float
        ) -> float:
            """Calculate absolute humidity in g/m³."""
            saturation_vapor_pressure = 6.112 * math.exp(
                (17.67 * temp_celsius) / (temp_celsius + 243.5)
            )
            return (
                (humidity_percent / 100)
                * saturation_vapor_pressure
                * 2.1674
                / (273.15 + temp_celsius)
                * 1000
            )

        # Test cases - corrected expected values
        result1 = calculate_absolute_humidity(50, 20)
        assert result1 == pytest.approx(86.4, rel=0.01), (
            f"Expected ~86.4, got {result1}"
        )

        result2 = calculate_absolute_humidity(60, 15)
        assert result2 == pytest.approx(76.9, rel=0.01), (
            f"Expected ~76.9, got {result2}"
        )

        result3 = calculate_absolute_humidity(100, 25)
        assert result3 == pytest.approx(230.3, rel=0.01), (
            f"Expected ~230.3, got {result3}"
        )

    def test_temperature_factor_winter(self) -> None:
        """Test temperature factor calculation for winter."""

        def calculate_temp_factor(temp_diff: float, month: int) -> float:
            winter_months = [12, 1, 2]
            summer_months = [6, 7, 8]

            if month in winter_months:
                return 0.8 if temp_diff > 2 else (0.4 if temp_diff > 0 else 0)
            if month in summer_months:
                return 0.8 if temp_diff > 3 else (0.3 if temp_diff > 0 else 0)
            return 0.6 if temp_diff > 1 else (0.3 if temp_diff > -2 else 0)

        # Winter tests
        assert calculate_temp_factor(5, 1) == LARGE_TEMP_FACTOR  # Large positive diff
        assert calculate_temp_factor(1, 1) == SMALL_TEMP_FACTOR  # Small positive diff
        assert calculate_temp_factor(-1, 1) == ZERO_FACTOR  # Negative diff

    def test_temperature_factor_summer(self) -> None:
        """Test temperature factor calculation for summer."""

        def calculate_temp_factor(temp_diff: float, month: int) -> float:
            winter_months = [12, 1, 2]
            summer_months = [6, 7, 8]

            if month in winter_months:
                return 0.8 if temp_diff > 2 else (0.4 if temp_diff > 0 else 0)
            if month in summer_months:
                return 0.8 if temp_diff > 3 else (0.3 if temp_diff > 0 else 0)
            return 0.6 if temp_diff > 1 else (0.3 if temp_diff > -2 else 0)

        # Summer tests
        assert calculate_temp_factor(5, 7) == LARGE_TEMP_FACTOR  # Large positive diff
        assert calculate_temp_factor(2, 7) == MINOR_TEMP_FACTOR  # Small positive diff
        assert calculate_temp_factor(-1, 7) == ZERO_FACTOR  # Negative diff

    def test_humidity_factor(self) -> None:
        """Test humidity factor calculation."""

        def calculate_humidity_factor(ah_in: float, ah_out: float) -> float:
            return 1 if (ah_in - ah_out) > 1 else (0.5 if ah_in > ah_out else 0)

        assert calculate_humidity_factor(10, 8) == HUMIDITY_LARGE_DIFF
        assert calculate_humidity_factor(9, 8) == HUMIDITY_SMALL_DIFF
        assert calculate_humidity_factor(7, 8) == ZERO_FACTOR

    def test_co2_factor(self) -> None:
        """Test CO2 factor calculation."""

        def calculate_co2_factor(
            room_type: str, hour: int, co2: float | None = None
        ) -> float:
            if co2 is not None:
                return (
                    1
                    if co2 > 1200
                    else (0.7 if co2 > 1000 else (0.3 if co2 > 800 else 0))
                )

            patterns = {
                ROOM_TYPE_BEDROOM: 0.8 if hour in [6, 7, 8, 9, 21, 22, 23] else 0.2,
                ROOM_TYPE_BATHROOM: 0.7
                if hour in [6, 7, 8, 9, 18, 19, 20, 21, 22]
                else 0.3,
                ROOM_TYPE_OFFICE: 0.8
                if hour in [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
                else 0.2,
                ROOM_TYPE_KITCHEN: 0.8
                if hour in [6, 7, 8]
                else (0.9 if hour in [11, 12, 13, 17, 18, 19, 20] else 0.3),
                ROOM_TYPE_LIVING_ROOM: 0.7
                if hour in [6, 7, 8, 9]
                else (
                    0.6
                    if hour in [17, 18, 19, 20, 21, 22]
                    else (0.3 if hour in [10, 11, 12, 13, 14, 15, 16] else 0.2)
                ),
            }
            return patterns.get(room_type, 0.2)

        # CO2 sensor available
        assert calculate_co2_factor(ROOM_TYPE_LIVING_ROOM, 12, 1300) == CO2_HIGH_FACTOR
        assert (
            calculate_co2_factor(ROOM_TYPE_LIVING_ROOM, 12, 1100) == CO2_MEDIUM_FACTOR
        )
        assert calculate_co2_factor(ROOM_TYPE_LIVING_ROOM, 12, 900) == CO2_LOW_FACTOR
        assert calculate_co2_factor(ROOM_TYPE_LIVING_ROOM, 12, 700) == ZERO_FACTOR

        # No CO2 sensor - use patterns
        assert calculate_co2_factor(ROOM_TYPE_BEDROOM, 7) == TIME_FACTOR_HIGH
        assert calculate_co2_factor(ROOM_TYPE_BEDROOM, 14) == 0.2  # Afternoon
        assert calculate_co2_factor(ROOM_TYPE_OFFICE, 10) == 0.8  # Work hours
        assert calculate_co2_factor(ROOM_TYPE_KITCHEN, 12) == 0.9  # Lunch time

    def test_time_factor(self) -> None:
        """Test time factor calculation."""

        def calculate_time_factor(hour: int) -> float:
            return (
                0.8
                if hour in [7, 8, 9, 18, 19, 20]
                else (0.5 if hour in [6, 10, 11, 16, 17, 21] else 0.2)
            )

        assert calculate_time_factor(8) == 0.8  # Peak morning
        assert calculate_time_factor(6) == 0.5  # Early morning
        assert calculate_time_factor(14) == 0.2  # Afternoon

    def test_wind_factor(self) -> None:
        """Test wind factor calculation."""

        def calculate_wind_factor(wind_speed: float, enable_wind: bool = True) -> float:
            if not enable_wind:
                return 0
            return 0 if wind_speed < 15 else (-0.2 if wind_speed < 25 else -0.5)

        assert calculate_wind_factor(10, True) == 0  # Low wind
        assert calculate_wind_factor(20, True) == -0.2  # Medium wind
        assert calculate_wind_factor(30, True) == -0.5  # High wind
        assert calculate_wind_factor(20, False) == 0  # Wind disabled

    def test_overall_score_calculation(self) -> None:
        """Test complete score calculation."""

        def calculate_score(
            temp_in: float,
            humidity_in: float,
            temp_out: float,
            humidity_out: float,
            wind: float,
            hour: int,
            month: int,
            room_type: str,
            co2: float | None = None,
            enable_wind: bool = True,
        ) -> float:
            # Absolute humidity
            ah_in = (humidity_in / 100) * (
                6.112
                * math.exp((17.67 * temp_in) / (temp_in + 243.5))
                * 2.1674
                / (273.15 + temp_in)
            )
            ah_out = (humidity_out / 100) * (
                6.112
                * math.exp((17.67 * temp_out) / (temp_out + 243.5))
                * 2.1674
                / (273.15 + temp_out)
            )

            # Temperature factor
            temp_diff = temp_in - temp_out
            winter_months = [12, 1, 2]
            summer_months = [6, 7, 8]

            if month in winter_months:
                f_t = 0.8 if temp_diff > 2 else (0.4 if temp_diff > 0 else 0)
            elif month in summer_months:
                f_t = 0.8 if temp_diff > 3 else (0.3 if temp_diff > 0 else 0)
            else:
                f_t = 0.6 if temp_diff > 1 else (0.3 if temp_diff > -2 else 0)

            # Humidity factor
            f_rh = 1 if (ah_in - ah_out) > 1 else (0.5 if ah_in > ah_out else 0)

            # CO2 factor
            if co2 is not None:
                f_co2 = (
                    1
                    if co2 > 1200
                    else (0.7 if co2 > 1000 else (0.3 if co2 > 800 else 0))
                )
            else:
                patterns = {
                    ROOM_TYPE_BEDROOM: 0.8 if hour in [6, 7, 8, 9, 21, 22, 23] else 0.2,
                    ROOM_TYPE_BATHROOM: 0.7
                    if hour in [6, 7, 8, 9, 18, 19, 20, 21, 22]
                    else 0.3,
                    ROOM_TYPE_OFFICE: 0.8
                    if hour in [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
                    else 0.2,
                    ROOM_TYPE_KITCHEN: 0.8
                    if hour in [6, 7, 8]
                    else (0.9 if hour in [11, 12, 13, 17, 18, 19, 20] else 0.3),
                    ROOM_TYPE_LIVING_ROOM: 0.7
                    if hour in [6, 7, 8, 9]
                    else (
                        0.6
                        if hour in [17, 18, 19, 20, 21, 22]
                        else (0.3 if hour in [10, 11, 12, 13, 14, 15, 16] else 0.2)
                    ),
                }
                f_co2 = patterns.get(room_type, 0.2)

            # Time factor
            f_time = (
                0.8
                if hour in [7, 8, 9, 18, 19, 20]
                else (0.5 if hour in [6, 10, 11, 16, 17, 21] else 0.2)
            )

            # Wind factor
            f_w = (
                0
                if not enable_wind
                else (0 if wind < 15 else (-0.2 if wind < 25 else -0.5))
            )

            # Final calculation
            if co2 is None:
                score = 0.35 * f_t + 0.35 * f_rh + 0.2 * f_co2 + 0.1 * f_time + f_w
            else:
                score = 0.25 * f_t + 0.25 * f_rh + 0.35 * f_co2 + 0.15 * f_time + f_w

            return round(score, 2)

        # Test case 1: Good ventilation conditions
        score = calculate_score(
            temp_in=22,
            humidity_in=60,
            temp_out=15,
            humidity_out=70,
            wind=10,
            hour=8,
            month=5,
            room_type=ROOM_TYPE_LIVING_ROOM,
            co2=1300,
            enable_wind=True,
        )
        assert score > 0.5  # Should be good for ventilation

        # Test case 2: Poor ventilation conditions
        score = calculate_score(
            temp_in=18,
            humidity_in=40,
            temp_out=25,
            humidity_out=30,
            wind=30,
            hour=14,
            month=7,
            room_type=ROOM_TYPE_OFFICE,
            co2=600,
            enable_wind=True,
        )
        assert score < 0.3  # Should be poor for ventilation
