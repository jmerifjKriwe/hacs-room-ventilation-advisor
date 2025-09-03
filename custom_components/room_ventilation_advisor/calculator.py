"""
Ventilation calculation logic for Room Ventilation Advisor.

Provides calculation of ventilation scores and factors for rooms
based on sensor data and configuration.
"""

import logging
import math
from dataclasses import dataclass
from typing import Any

from custom_components.room_ventilation_advisor.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_CO2_THRESHOLDS,
    CONF_HUMIDITY_THRESHOLDS,
    CONF_ROOM_TIME_PATTERNS,
    CONF_SCORE_WEIGHTS,
    CONF_TEMPERATURE_THRESHOLDS,
    CONF_TIME_FACTORS,
    CONF_WIND_THRESHOLDS,
    DEFAULT_CO2_THRESHOLDS,
    DEFAULT_HUMIDITY_THRESHOLDS,
    DEFAULT_ROOM_TIME_PATTERNS,
    DEFAULT_SCORE_WEIGHTS,
    DEFAULT_TEMPERATURE_THRESHOLDS,
    DEFAULT_TIME_FACTORS,
    DEFAULT_WIND_THRESHOLDS,
    ROOM_TYPE_BATHROOM,
    ROOM_TYPE_BEDROOM,
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_LIVING_ROOM,
    ROOM_TYPE_OFFICE,
)


@dataclass
class RoomData:
    """Data class for room sensor readings."""

    temp_in: float
    humidity_in: float
    temp_out: float
    humidity_out: float
    wind_speed: float
    hour: int
    month: int
    room_type: str
    co2: float | None = None


_LOGGER = logging.getLogger(__name__)


class VentilationCalculator:
    """Core calculation logic for ventilation recommendations."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize calculator with configuration."""
        self.config: dict[str, Any] = config

        # Load advanced settings with defaults
        advanced: dict[str, Any] = config.get(CONF_ADVANCED_SETTINGS, {})

        # Temperature thresholds
        temp_thresholds: dict[str, Any] = advanced.get(CONF_TEMPERATURE_THRESHOLDS, {})
        self.temp_winter_good: float = temp_thresholds.get(
            "winter_good",
            DEFAULT_TEMPERATURE_THRESHOLDS["winter_good"],
        )
        self.temp_winter_moderate: float = temp_thresholds.get(
            "winter_moderate",
            DEFAULT_TEMPERATURE_THRESHOLDS["winter_moderate"],
        )
        self.temp_summer_good: float = temp_thresholds.get(
            "summer_good",
            DEFAULT_TEMPERATURE_THRESHOLDS["summer_good"],
        )
        self.temp_summer_moderate: float = temp_thresholds.get(
            "summer_moderate",
            DEFAULT_TEMPERATURE_THRESHOLDS["summer_moderate"],
        )
        self.temp_default_good: float = temp_thresholds.get(
            "default_good",
            DEFAULT_TEMPERATURE_THRESHOLDS["default_good"],
        )
        self.temp_default_moderate: float = temp_thresholds.get(
            "default_moderate",
            DEFAULT_TEMPERATURE_THRESHOLDS["default_moderate"],
        )

        # Humidity thresholds
        humidity_thresholds: dict[str, Any] = advanced.get(CONF_HUMIDITY_THRESHOLDS, {})
        self.humidity_good: float = humidity_thresholds.get(
            "good",
            DEFAULT_HUMIDITY_THRESHOLDS["good"],
        )
        self.humidity_moderate: float = humidity_thresholds.get(
            "moderate",
            DEFAULT_HUMIDITY_THRESHOLDS["moderate"],
        )

        # CO2 thresholds
        co2_thresholds: dict[str, Any] = advanced.get(CONF_CO2_THRESHOLDS, {})
        self.co2_very_poor: float = co2_thresholds.get(
            "very_poor",
            DEFAULT_CO2_THRESHOLDS["very_poor"],
        )
        self.co2_poor: float = co2_thresholds.get(
            "poor",
            DEFAULT_CO2_THRESHOLDS["poor"],
        )
        self.co2_moderate: float = co2_thresholds.get(
            "moderate",
            DEFAULT_CO2_THRESHOLDS["moderate"],
        )

        # Wind thresholds
        wind_thresholds: dict[str, Any] = advanced.get(CONF_WIND_THRESHOLDS, {})
        self.wind_no_effect: float = wind_thresholds.get(
            "no_effect",
            DEFAULT_WIND_THRESHOLDS["no_effect"],
        )
        self.wind_moderate_effect: float = wind_thresholds.get(
            "moderate_effect",
            DEFAULT_WIND_THRESHOLDS["moderate_effect"],
        )

        # Score weights
        score_weights: dict[str, Any] = advanced.get(CONF_SCORE_WEIGHTS, {})
        self.weight_temp: float = score_weights.get(
            "temperature",
            DEFAULT_SCORE_WEIGHTS["temperature"],
        )
        self.weight_humidity: float = score_weights.get(
            "humidity",
            DEFAULT_SCORE_WEIGHTS["humidity"],
        )
        self.weight_co2: float = score_weights.get("co2", DEFAULT_SCORE_WEIGHTS["co2"])
        self.weight_time: float = score_weights.get(
            "time",
            DEFAULT_SCORE_WEIGHTS["time"],
        )
        self.weight_temp_with_co2: float = score_weights.get(
            "temperature_with_co2",
            DEFAULT_SCORE_WEIGHTS["temperature_with_co2"],
        )
        self.weight_humidity_with_co2: float = score_weights.get(
            "humidity_with_co2",
            DEFAULT_SCORE_WEIGHTS["humidity_with_co2"],
        )
        self.weight_co2_with_sensor: float = score_weights.get(
            "co2_with_sensor",
            DEFAULT_SCORE_WEIGHTS["co2_with_sensor"],
        )
        self.weight_time_with_co2: float = score_weights.get(
            "time_with_co2",
            DEFAULT_SCORE_WEIGHTS["time_with_co2"],
        )

        # Time factors
        time_factors: dict[str, Any] = advanced.get(CONF_TIME_FACTORS, {})
        self.time_high: float = time_factors.get("high", DEFAULT_TIME_FACTORS["high"])
        self.time_moderate: float = time_factors.get(
            "moderate",
            DEFAULT_TIME_FACTORS["moderate"],
        )
        self.time_low: float = time_factors.get("low", DEFAULT_TIME_FACTORS["low"])

        # Room time patterns
        self.room_patterns: dict[str, Any] = advanced.get(
            CONF_ROOM_TIME_PATTERNS,
            DEFAULT_ROOM_TIME_PATTERNS,
        )

    def calculate_room_score(self, room_data: RoomData) -> float:
        """
        Calculate ventilation score for a room.

        Returns a score between -0.5 and 1.0 where:
        - > 0.5: Good ventilation conditions
        - 0.2 to 0.5: Moderate ventilation conditions
        - < 0.2: Poor ventilation conditions
        - < 0: Ventilation not recommended (high wind, etc.)
        """
        # Extract data from room_data
        temp_in = room_data.temp_in
        humidity_in = room_data.humidity_in
        temp_out = room_data.temp_out
        humidity_out = room_data.humidity_out
        wind_speed = room_data.wind_speed
        hour = room_data.hour
        month = room_data.month
        room_type = room_data.room_type
        co2 = room_data.co2

        # Calculate absolute humidity
        ah_in = self._calculate_absolute_humidity(humidity_in, temp_in)
        ah_out = self._calculate_absolute_humidity(humidity_out, temp_out)

        # Temperature factor
        temp_diff = temp_in - temp_out
        f_t = self._calculate_temperature_factor(temp_diff, month)

        # Humidity factor
        f_rh = self._calculate_humidity_factor(ah_in, ah_out)

        # CO2 factor
        f_co2 = self._calculate_co2_factor(room_type, hour, co2)

        # Time factor
        f_time = self._calculate_time_factor(hour)

        # Wind factor
        enable_wind = self.config.get("enable_wind_factor", True)
        f_w = self._calculate_wind_factor(wind_speed, enable_wind=enable_wind)

        # Final calculation
        if co2 is None:
            score = (
                self.weight_temp * f_t
                + self.weight_humidity * f_rh
                + self.weight_co2 * f_co2
                + self.weight_time * f_time
                + f_w
            )
        else:
            score = (
                self.weight_temp_with_co2 * f_t
                + self.weight_humidity_with_co2 * f_rh
                + self.weight_co2_with_sensor * f_co2
                + self.weight_time_with_co2 * f_time
                + f_w
            )

        return round(score, 2)

    def _calculate_absolute_humidity(
        self,
        humidity_percent: float,
        temp_celsius: float,
    ) -> float:
        """Calculate absolute humidity in g/m³."""
        saturation_vapor_pressure = 6.112 * math.exp(
            (17.67 * temp_celsius) / (temp_celsius + 243.5),
        )
        return (
            (humidity_percent / 100)
            * saturation_vapor_pressure
            * 2.1674
            / (273.15 + temp_celsius)
            * 100
        )

    def _calculate_temperature_factor(self, temp_diff: float, month: int) -> float:
        """Calculate temperature factor based on season."""
        winter_months = self.config.get("winter_months", [12, 1, 2])
        summer_months = self.config.get("summer_months", [6, 7, 8])

        if month in winter_months:
            return (
                0.8
                if temp_diff > self.temp_winter_good
                else (0.4 if temp_diff > self.temp_winter_moderate else 0)
            )
        if month in summer_months:
            return (
                0.8
                if temp_diff > self.temp_summer_good
                else (0.3 if temp_diff > self.temp_summer_moderate else 0)
            )
        return (
            0.6
            if temp_diff > self.temp_default_good
            else (0.3 if temp_diff > self.temp_default_moderate else 0)
        )

    def _calculate_humidity_factor(self, ah_in: float, ah_out: float) -> float:
        """Calculate humidity factor."""
        diff = ah_in - ah_out
        return (
            1.0
            if diff > self.humidity_good
            else (0.5 if diff > self.humidity_moderate else 0)
        )

    def _calculate_co2_factor(
        self,
        room_type: str,
        hour: int,
        co2: float | None = None,
    ) -> float:
        """Calculate CO2 factor."""
        if co2 is not None:
            if co2 > self.co2_very_poor:
                return 1.0
            if co2 > self.co2_poor:
                return 0.7
            if co2 > self.co2_moderate:
                return 0.3
            return 0

        # Use room type and time-based patterns when no CO2 sensor
        patterns = {
            ROOM_TYPE_BEDROOM: 0.8 if hour in [6, 7, 8, 9, 21, 22, 23] else 0.2,
            ROOM_TYPE_BATHROOM: (
                0.7 if hour in [6, 7, 8, 9, 18, 19, 20, 21, 22] else 0.3
            ),
            ROOM_TYPE_OFFICE: (
                0.8 if hour in [8, 9, 10, 11, 12, 13, 14, 15, 16, 17] else 0.2
            ),
            ROOM_TYPE_KITCHEN: (
                0.8
                if hour in [6, 7, 8]
                else (0.9 if hour in [11, 12, 13, 17, 18, 19, 20] else 0.3)
            ),
            ROOM_TYPE_LIVING_ROOM: (
                0.7
                if hour in [6, 7, 8, 9]
                else (
                    0.6
                    if hour in [17, 18, 19, 20, 21, 22]
                    else (0.3 if hour in [10, 11, 12, 13, 14, 15, 16] else 0.2)
                )
            ),
        }
        return patterns.get(room_type, 0.2)

    def _calculate_time_factor(self, hour: int) -> float:
        """Calculate time factor based on hour."""
        return (
            0.8
            if hour in [7, 8, 9, 18, 19, 20]
            else (0.5 if hour in [6, 10, 11, 16, 17, 21] else 0.2)
        )

    def _calculate_wind_factor(
        self,
        wind_speed: float,
        *,
        enable_wind: bool = True,
    ) -> float:
        """Calculate wind factor."""
        if not enable_wind:
            return 0
        return (
            0
            if wind_speed < self.wind_no_effect
            else (-0.2 if wind_speed < self.wind_moderate_effect else -0.5)
        )
