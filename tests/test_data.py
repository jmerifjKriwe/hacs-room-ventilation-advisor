# Shared group and window options with numeric values for str conversion tests
VALID_GROUP_OPTIONS_NUMERIC = {
    "entry_type": "group",
    "name": "Test Group",
    "diffuse_factor": 0.15,
    "threshold_direct": 200,
    "threshold_diffuse": 150,
    "temperature_indoor_base": 23.0,
    "temperature_outdoor_base": 19.5,
    "indoor_temperature_sensor": "sensor.temp1",
}

VALID_WINDOW_OPTIONS_NUMERIC = {
    "entry_type": "window",
    "name": "Test Window",
    "g_value": 0.5,
    "frame_width": 0.125,
    "tilt": 90,
    "diffuse_factor": 0.15,
    "threshold_direct": 200,
    "threshold_diffuse": 150,
    "temperature_indoor_base": 23.0,
    "temperature_outdoor_base": 19.5,
    "indoor_temperature_sensor": "sensor.temp1",
}
# Shared group and window subentry mocks for entity tests
MOCK_GROUP_SUBENTRIES = {
    "group_id_1": {
        "subentry_type": "group",
        "title": "Living Room Group",
        "entry_id": "group_id_1",
    },
    "group_id_2": {
        "subentry_type": "group",
        "title": "Bedroom Group",
        "entry_id": "group_id_2",
    },
}

MOCK_WINDOW_SUBENTRIES = {
    "window_id_1": {
        "subentry_type": "window",
        "title": "Kitchen Window",
        "entry_id": "window_id_1",
    },
    "window_id_2": {
        "subentry_type": "window",
        "title": "Office Window",
        "entry_id": "window_id_2",
    },
}
# New: Shared window and group test data for calculator and flow tests
VALID_WINDOW_DATA = {
    "name": "South Window",
    "window_width": 2.0,
    "window_height": 1.5,
    "azimuth": 180,
    "elevation_min": 0,
    "elevation_max": 90,
    "azimuth_min": -90,
    "azimuth_max": 90,
    "shadow_depth": 0.5,
    "shadow_offset": 0.2,
    "indoor_temperature_sensor": "sensor.room_0_temp",
}

VALID_WINDOW_DATA_ALT = {
    "name": "North Window",
    "window_width": 1.0,
    "window_height": 1.0,
    "azimuth": 0,
    "elevation_min": 0,
    "elevation_max": 90,
    "azimuth_min": -45,
    "azimuth_max": 45,
    "shadow_depth": 0,
    "shadow_offset": 0,
    "indoor_temperature_sensor": "sensor.room_1_temp",
}

VALID_PHYSICAL = {
    "g_value": 0.7,
    "frame_width": 0.05,
    "diffuse_factor": 0.3,
    "tilt": 0,
}

VALID_THRESHOLDS = {"direct": 400, "diffuse": 200}
VALID_TEMPERATURES = {"indoor_base": 24, "outdoor_base": 25}
"""Central test data for Solar Window System tests."""

VALID_GLOBAL_BASIC = {
    "window_width": "1.5",
    "window_height": "2.0",
    "shadow_depth": "0.5",
    "shadow_offset": "0.2",
    "solar_radiation_sensor": "sensor.dummy_solar",
    "outdoor_temperature_sensor": "sensor.dummy_outdoor",
    "indoor_temperature_sensor": "sensor.dummy_indoor",
    "forecast_temperature_sensor": "sensor.dummy",
    "weather_warning_sensor": "binary_sensor.dummy",
}

VALID_GLOBAL_ENHANCED = {
    "g_value": "0.6",
    "frame_width": "0.1",
    "tilt": "90",
    "diffuse_factor": "0.2",
    "threshold_direct": "250",
    "threshold_diffuse": "120",
    "temperature_indoor_base": "22.0",
    "temperature_outdoor_base": "20.0",
}

VALID_GLOBAL_SCENARIOS = {
    "scenario_b_temp_indoor": "24",
    "scenario_b_temp_outdoor": "26",
    "scenario_c_temp_indoor": "22",
    "scenario_c_temp_outdoor": "25",
    "scenario_c_temp_forecast": "28",
    "scenario_c_start_hour": "8",
}

INVALID_GLOBAL_BASIC = {
    "window_width": "abc",
    "window_height": "2.0",
    "shadow_depth": "0.5",
    "shadow_offset": "0.2",
    "solar_radiation_sensor": "sensor.dummy_solar",
    "outdoor_temperature_sensor": "sensor.dummy_outdoor",
    "indoor_temperature_sensor": "sensor.dummy_indoor",
}
