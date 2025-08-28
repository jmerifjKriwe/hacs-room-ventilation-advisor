![GitHub Release](https://img.shields.io/github/v/release/jmerifjKriwe/hass-solar-window-system)
![Static Badge](https://img.shields.io/badge/HomeAssistant-2025.07-blue)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)

[![HACS+Hassfest validation](https://github.com/jmerifjKriwe/hass-solar-window-system/actions/workflows/validate.yml/badge.svg)](https://github.com/jmerifjKriwe/hass-solar-window-system/actions/workflows/validate.yml)
[![Run Tests](https://github.com/jmerifjKriwe/hass-solar-window-system/actions/workflows/test.yml/badge.svg)](https://github.com/jmerifjKriwe/hass-solar-window-system/actions/workflows/test.yml)
[![Coverage Badge](coverage.svg)](https://github.com/jmerifjKriwe/hass-solar-window-system/actions/workflows/coverage.yml)



Short introduction
------------------

Solar Window System (SWS) is a Home Assistant integration that decides when
to deploy shading (shutters, blinds, awnings) per window or per group of
windows. Decisions are based on measured solar radiation, sun position,
indoor/outdoor temperature, weather warnings and configurable scenario
thresholds. SWS provides a flow-based UI configuration (global → groups →
windows) and supports inheritance (window → group → global).

This README explains installation (HACS and manual), the recommended UI
configuration order, which sensors/entities SWS creates, the three shading
scenarios and how they work, and best practices to reduce flutter.

Installation
------------

HACS (recommended)
- Add this repository to HACS (Community -> Custom repositories -> Integration).
- Install "Solar Window System" from HACS.
- Restart Home Assistant (Configuration → Server Controls → Restart).
- Add the integration via Settings → Devices & Services → Add Integration → "Solar Window System".

Manual installation
- Copy the folder `custom_components/solar_window_system` into your Home
    Assistant `custom_components` directory.
- Ensure the integration's `manifest.json` requirements are available in your
    Home Assistant environment (if any). Restart Home Assistant.
- Add the integration via Settings → Devices & Services → Add Integration.

Notes
- The integration uses Home Assistant config entries and subentries. When
    installed it will create three logical entry types: a global configuration
    entry and two parent entries to hold group and window subentries.

UI configuration — recommended order
-----------------------------------

Follow this order to configure SWS safely for an inexperienced user:

1) Global configuration (first step when adding the integration)
     - Global Basic page: choose sensors (solar radiation, outdoor temp,
         indoor temp) and provide default window geometry (width/height),
         shadow depth/offset and update interval.
     - Global Enhanced page: set physical defaults (glass g-value, frame
         width, tilt, diffuse_factor) and default thresholds (direct/diffuse)
         plus base indoor/outdoor temperatures.
     - Global Scenarios page: set defaults for scenario thresholds (Scenario B
         and C) such as forecast threshold and start hour.

2) Create Group configurations (optional, but recommended for many windows)
     - Create group subentries with a name and optional group-level overrides
         (temperatures, thresholds). Group scenario enablement is exposed as
         a three-state select (enable / disable / inherit).

3) Create Window configurations (one per physical window)
     - For each window enter: name, azimuth/elevation constraints, window
         geometry (or inherit), shadow_depth/offset (or inherit), linked group
         (optional), and per-window overrides for thresholds/temperatures.

Important: inheritance
----------------------

- Values flow: Window → Group → Global. Use the UI's inherit option (or
    the special marker `-1`) to explicitly inherit from the parent level.
- Many fields accept empty/`-1` as "inherit"; others are required in the
    Global flow (solar radiation, outdoor and indoor temp sensors).

Entities and sensors created by SWS
----------------------------------

The integration creates entities for global configuration helpers, per-group
and per-window sensors, and binary shading indicators. Main entities are:

- Per-window binary sensor: shading required
    - unique ids / entity ids like `binary_sensor.sws_window_<slug>_shading_required`
    - Indicates whether shading is currently required for the window.

- Per-window power sensors
    - `sensor.sws_window_<slug>_total_power` (W)
    - `sensor.sws_window_<slug>_total_power_direct` (W)
    - `sensor.sws_window_<slug>_total_power_diffuse` (W)
    - `sensor.sws_window_<slug>_power_m2_total` (W/m²) and related m² metrics

- Per-group aggregated power sensors
    - `sensor.sws_group_<slug>_total_power` and _direct/_diffuse

- Global configuration entities (stable ids `sws_global_<key>`)
    - input_number, input_boolean, input_select and template sensors created
        for convenience (sensitivity, scenario enables, debug, totals, ...).

Implementation notes (how values are computed)
---------------------------------------------

- Effective configuration is computed by merging global, group and window
    data with explicit inheritance handling in `calculator.py` (functions
    `_build_effective_config`, `_structure_flat_config`).
- Solar power calculation is implemented in
    `SolarWindowCalculator.calculate_window_solar_power_with_shadow()`:
    - Diffuse power = solar_radiation * diffuse_factor * area * g_value
    - Direct power uses an incidence cosine and is scaled by a shadow factor
        computed from sun elevation/azimuth, window azimuth, shadow_depth and
        shadow_offset. Shadow factor is between 0.1 and 1.0.
- Results per window include total_power, direct/diffuse split, power per m²,
    shadow_factor, area, is_visible, effective thresholds and shade reason.

Shading decision logic (three scenarios)
----------------------------------------

The implementation uses a clear decision order (see `calculator.py`):

Pre-checks and overrides
- If `maintenance_mode` global input is active → shading disabled.
- If configured `weather_warning` entity reports ON → shading forced ON.

Scenario A — Strong direct sun (always evaluated)
- Trigger when:
    - window `power_total` > `threshold_direct` AND
    - indoor_temp >= `temperatures.indoor_base` AND
    - outdoor_temp >= `temperatures.outdoor_base`.
- Default threshold_direct = 200 W (global default).

Scenario B — Diffuse heat (optional: can be enabled/disabled)
- Trigger when:
    - window `power_total` > `threshold_diffuse` AND
    - indoor_temp > (indoor_base + scenario offset) AND
    - outdoor_temp > (outdoor_base + scenario offset).
- Default threshold_diffuse = 150 W. Scenario B is enabled via global
    flag and can be overridden per-group/per-window (inherit possible).

Scenario C — Heatwave / forecast (optional)
- Trigger when forecast temperature (configured sensor) exceeds
    configured forecast threshold, indoor temperature >= indoor_base and
    current hour >= configured start_hour.
- Also enabled by global flag with per-group/per-window overrides.

Notes about scenarios
- Scenario A is the core/standard rule and is always evaluated. Scenarios
    B and C can be toggled (window -> group -> global) using three-state
    selects (enable / disable / inherit).
- Weather warnings are treated as an immediate override: if active, shading
    is requested regardless of scenario thresholds.

Best practices to avoid flutter (rapid on/off)
--------------------------------------------

- Smooth the solar radiation input: use Home Assistant's `filter` (moving
    average) or `statistics` to provide an averaged sensor to SWS. This is the
    single most effective measure to reduce flicker.
- Smooth or average noisy indoor temperature sensors.
- Increase the global `update_interval` if your sensors are noisy.
- Use `sensitivity` (global input_number) to scale thresholds if many small
    oscillations occur — increasing sensitivity reduces switching.
- Correct physical parameters: provide accurate window width/height and
    frame width so area and power/m² calculations are stable.
- If a specific window toggles often, consider grouping it with similar
    windows or adding a small automation delay before actuators move.


Quick Start — minimal working example
------------------------------------

Below is a very small, copy-pasteable example showing how to:

- create a filtered (smoothed) solar radiation sensor that SWS will use as
    its `solar_radiation_sensor`, and
- create two automations that react to a per-window shading binary sensor
    (`binary_sensor.sws_window_<slug>_shading_required`) with simple debounce
    logic to avoid actuator flutter.

Replace the example entity IDs with the ones from your system.

1) Filtered solar radiation sensor

This uses Home Assistant's `filter` integration to produce a short moving
average of a raw radiation sensor (replace
`sensor.raw_solar_radiation` with your real sensor).

Add to your `configuration.yaml` (or include via a package):

```yaml
sensor:
    - platform: filter
        name: "Solar Radiation (filtered)"
        entity_id: sensor.raw_solar_radiation
        filters:
            - sliding_window_moving_average:
                    window_size: 5    # average over last 5 samples
                    precision: 1
```

Notes:
- Use `window_size` and the integration's update interval so the moving
    average is meaningful (e.g. if SWS updates every minute, a window_size of
    3–10 samples works well).
- Alternatively you can use `time_simple_moving_average` with a time window
    (e.g. `60s`) if your raw sensor updates irregularly.

2) Automations reacting to shading_required

Example automations that control a cover (blinds) when a window requests
shading. These include simple `for` debounce to avoid acting on very short
spikes.

Close blinds when shading is required (state -> on for >= 5s):

```yaml
automation:
    - id: sws_close_blinds_on_shade_required
        alias: "SWS: Close blinds when shading required"
        trigger:
            - platform: state
                entity_id: binary_sensor.sws_window_living_room_shading_required
                to: 'on'
                for: '00:00:05'
        action:
            - service: cover.close_cover
                target:
                    entity_id: cover.living_room_blinds
        mode: single
```

Re-open blinds when shading is no longer required (state -> off for >= 10m):

```yaml
automation:
    - id: sws_open_blinds_when_not_required
        alias: "SWS: Open blinds when shading not required"
        trigger:
            - platform: state
                entity_id: binary_sensor.sws_window_living_room_shading_required
                to: 'off'
                for: '00:10:00'
        action:
            - service: cover.open_cover
                target:
                    entity_id: cover.living_room_blinds
        mode: single
```

Hints to avoid actuator flutter:
- Use `for` in the triggers (as shown) so the state must be stable for a
    short period before the cover moves.
- Optionally combine the SWS binary sensor with an additional check on the
    averaged radiation sensor in a condition if you want extra safety, e.g.:

```yaml
condition:
    - condition: numeric_state
        entity_id: sensor.solar_radiation_filtered
        above: 50
```

Licence
------------------------------------
This project is licensed under the Mozilla Public License 2.0. See the LICENSE file for details.