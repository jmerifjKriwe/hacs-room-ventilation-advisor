"""Constants for Room Ventilation Advisor integration."""

from typing import Final

DOMAIN: Final = "room_ventilation_advisor"

# Configuration keys
CONF_NAME: Final = "name"
CONF_OUTDOOR_TEMP_SENSOR: Final = "outdoor_temp_sensor"
CONF_OUTDOOR_HUMIDITY_SENSOR: Final = "outdoor_humidity_sensor"
CONF_WIND_SENSOR: Final = "wind_sensor"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_ROOMS: Final = "rooms"
CONF_ROOM_NAME: Final = "room_name"
CONF_TEMP_SENSOR: Final = "temp_sensor"
CONF_HUMIDITY_SENSOR: Final = "humidity_sensor"
CONF_ROOM_TYPE: Final = "room_type"
CONF_CO2_SENSOR: Final = "co2_sensor"
CONF_ENABLED: Final = "enabled"
CONF_ENABLE_WIND_FACTOR: Final = "enable_wind_factor"
CONF_WINTER_MONTHS: Final = "winter_months"
CONF_SUMMER_MONTHS: Final = "summer_months"

# Room types
ROOM_TYPE_LIVING_ROOM: Final = "living_room"
ROOM_TYPE_BEDROOM: Final = "bedroom"
ROOM_TYPE_BATHROOM: Final = "bathroom"
ROOM_TYPE_KITCHEN: Final = "kitchen"
ROOM_TYPE_OFFICE: Final = "office"

ROOM_TYPES: Final = [
    ROOM_TYPE_LIVING_ROOM,
    ROOM_TYPE_BEDROOM,
    ROOM_TYPE_BATHROOM,
    ROOM_TYPE_KITCHEN,
    ROOM_TYPE_OFFICE,
]

# Default values
DEFAULT_SCAN_INTERVAL: Final = 300
DEFAULT_ENABLE_WIND_FACTOR: Final = True
DEFAULT_WINTER_MONTHS: Final = [12, 1, 2]
DEFAULT_SUMMER_MONTHS: Final = [6, 7, 8]

# Ventilation calculation defaults
DEFAULT_TEMPERATURE_THRESHOLDS: Final = {
    "winter_good": 2.0,  # °C temperature difference for good ventilation
    "winter_moderate": 0.0,  # °C temperature difference for moderate ventilation
    "summer_good": 3.0,  # °C temperature difference for good ventilation
    "summer_moderate": 0.0,  # °C temperature difference for moderate ventilation
    "default_good": 1.0,  # °C temperature difference for good ventilation
    "default_moderate": -2.0,  # °C temperature difference for moderate ventilation
}

DEFAULT_HUMIDITY_THRESHOLDS: Final = {
    "good": 1.0,  # g/m³ absolute humidity difference for good ventilation
    "moderate": 0.0,  # g/m³ absolute humidity difference for moderate ventilation
}

DEFAULT_CO2_THRESHOLDS: Final = {
    "very_poor": 1200,  # ppm CO2 level for very poor air quality
    "poor": 1000,  # ppm CO2 level for poor air quality
    "moderate": 800,  # ppm CO2 level for moderate air quality
}

DEFAULT_WIND_THRESHOLDS: Final = {
    "no_effect": 15.0,  # m/s wind speed with no ventilation effect
    "moderate_effect": 25.0,  # m/s wind speed with moderate negative effect
}

DEFAULT_SCORE_WEIGHTS: Final = {
    "temperature": 0.35,  # Weight for temperature factor (without CO2)
    "humidity": 0.35,  # Weight for humidity factor (without CO2)
    "co2": 0.2,  # Weight for CO2 factor (without CO2)
    "time": 0.1,  # Weight for time factor (without CO2)
    "temperature_with_co2": 0.25,  # Weight for temperature factor (with CO2)
    "humidity_with_co2": 0.25,  # Weight for humidity factor (with CO2)
    "co2_with_sensor": 0.35,  # Weight for CO2 factor (with CO2)
    "time_with_co2": 0.15,  # Weight for time factor (with CO2)
}

DEFAULT_TIME_FACTORS: Final = {
    "high": [7, 8, 9, 18, 19, 20],  # Hours with high ventilation factor
    "moderate": [6, 10, 11, 16, 17, 21],  # Hours with moderate ventilation factor
    "low": [
        0,
        1,
        2,
        3,
        4,
        5,
        12,
        13,
        14,
        15,
        22,
        23,
    ],  # Hours with low ventilation factor
}

DEFAULT_ROOM_TIME_PATTERNS: Final = {
    ROOM_TYPE_BEDROOM: {
        "high": [6, 7, 8, 9, 21, 22, 23],
        "moderate": [5, 10, 20],
        "low": [0, 1, 2, 3, 4, 11, 12, 13, 14, 15, 16, 17, 18, 19],
    },
    ROOM_TYPE_BATHROOM: {
        "high": [6, 7, 8, 9, 18, 19, 20, 21, 22],
        "moderate": [5, 10, 17, 23],
        "low": [0, 1, 2, 3, 4, 11, 12, 13, 14, 15, 16],
    },
    ROOM_TYPE_OFFICE: {
        "high": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
        "moderate": [7, 18, 19],
        "low": [0, 1, 2, 3, 4, 5, 6, 20, 21, 22, 23],
    },
    ROOM_TYPE_KITCHEN: {
        "high": [6, 7, 8, 11, 12, 13, 17, 18, 19, 20],
        "moderate": [9, 10, 16, 21],
        "low": [0, 1, 2, 3, 4, 5, 14, 15, 22, 23],
    },
    ROOM_TYPE_LIVING_ROOM: {
        "high": [6, 7, 8, 9, 17, 18, 19, 20, 21, 22],
        "moderate": [10, 11, 12, 13, 14, 15, 16],
        "low": [0, 1, 2, 3, 4, 5, 23],
    },
}

# Configuration keys for advanced settings
CONF_ADVANCED_SETTINGS: Final = "advanced_settings"
CONF_TEMPERATURE_THRESHOLDS: Final = "temperature_thresholds"
CONF_HUMIDITY_THRESHOLDS: Final = "humidity_thresholds"
CONF_CO2_THRESHOLDS: Final = "co2_thresholds"
CONF_WIND_THRESHOLDS: Final = "wind_thresholds"
CONF_SCORE_WEIGHTS: Final = "score_weights"
CONF_TIME_FACTORS: Final = "time_factors"
CONF_ROOM_TIME_PATTERNS: Final = "room_time_patterns"

# Sensor attributes
ATTR_TEMP_IN: Final = "temp_in"
ATTR_TEMP_OUT: Final = "temp_out"
ATTR_HUMIDITY_IN: Final = "humidity_in"
ATTR_HUMIDITY_OUT: Final = "humidity_out"
ATTR_CO2: Final = "co2"
ATTR_WIND: Final = "wind"
ATTR_ROOM_TYPE: Final = "room_type"
ATTR_SCORE: Final = "ventilation_score"
ATTR_ADVICE: Final = "ventilation_advice"
ATTR_TEMPERATURE_INDOOR: Final = "temperature_indoor"
ATTR_TEMPERATURE_OUTDOOR: Final = "temperature_outdoor"
ATTR_HUMIDITY_INDOOR: Final = "humidity_indoor"
ATTR_HUMIDITY_OUTDOOR: Final = "humidity_outdoor"
ATTR_CO2_LEVEL: Final = "co2_level"
ATTR_WIND_SPEED: Final = "wind_speed"

# Icons
ICON_VENTILATION: Final = "mdi:fan"
ICON_VENTILATION_GOOD: Final = "mdi:fan-plus"
ICON_VENTILATION_MODERATE: Final = "mdi:fan-clock"
ICON_VENTILATION_POOR: Final = "mdi:fan-alert"

# Platforms
PLATFORMS: Final = ["sensor"]
