"""Constants for Solar Window System integration."""

DOMAIN = "solar_window_system"

# Entity ID prefix for better organization and future extensions
ENTITY_PREFIX = "sws"
ENTITY_PREFIX_GLOBAL = "sws_global"

# Global Configuration Entity IDs
GLOBAL_CONFIG_ENTITIES = {
    # Configuration entities retained as entities
    "min_solar_radiation": {
        "platform": "input_number",
        "name": "Minimum Solar Radiation",
        "min": 0,
        "max": 1000,
        "step": 1,
        "default": 50,
        "unit": "W/m²",
        "icon": "mdi:white-balance-sunny",
        "category": "configuration",
    },
    "min_sun_elevation": {
        "platform": "input_number",
        "name": "Minimum Sun Elevation",
        "min": -20,
        "max": 90,
        "step": 1,
        "default": 10,
        "unit": "°",
        "icon": "mdi:weather-sunset-up",
        "category": "configuration",
    },
    "scenario_b_enable": {
        "platform": "input_boolean",
        "name": "Scenario B Enable",
        "default": False,
        "icon": "mdi:toggle-switch-off",
        "category": "configuration",
    },
    "scenario_c_enable": {
        "platform": "input_boolean",
        "name": "Scenario C Enable",
        "default": False,
        "icon": "mdi:toggle-switch-off",
        "category": "configuration",
    },
    # Operational controls
    "maintenance_mode": {
        "platform": "input_boolean",
        "name": "Maintenance Mode",
        "default": False,
        "icon": "mdi:tools",
        "category": "configuration",
    },
    "sensitivity": {
        "platform": "input_number",
        "name": "Sensitivity",
        "min": 0.5,
        "max": 2.0,
        "step": 0.1,
        "default": 1.0,
        "unit": "",
        "icon": "mdi:tune-variant",
        "category": "configuration",
    },
    # Debug entities
    "debug": {
        "platform": "input_text",
        "name": "Debug",
        "max": 255,
        "default": "",
        "icon": "mdi:bug-outline",
        "category": "debug",
    },
    # Sensor entities
    "window_with_shading": {
        "platform": "sensor",
        "name": "Window with Shading",
        "default": 0,
        "unit": "",
        "icon": "mdi:window-shutter",
        "category": "sensor",
    },
    "total_power": {
        "platform": "sensor",
        "name": "Total Power",
        "default": 0,
        "unit": "W",
        "icon": "mdi:lightning-bolt",
        "category": "sensor",
    },
    "total_power_direct": {
        "platform": "sensor",
        "name": "Total Power Direct",
        "default": 0,
        "unit": "W",
        "icon": "mdi:weather-sunny",
        "category": "sensor",
    },
    "total_power_diffuse": {
        "platform": "sensor",
        "name": "Total Power Diffuse",
        "default": 0,
        "unit": "W",
        "icon": "mdi:weather-partly-cloudy",
        "category": "sensor",
    },
    # Weather-related select entities
    "weather_warning_sensor": {
        "platform": "input_select",
        "name": "Weather Warning Sensor",
        "options": [],
        "default": "",
        "icon": "mdi:weather-cloudy-alert",
        "category": "configuration",
    },
    "weather_forecast_temperature_sensor": {
        "platform": "input_select",
        "name": "Weather Forecast Temperature Sensor",
        "options": [],
        "default": "",
        "icon": "mdi:thermometer",
        "category": "configuration",
    },
}
