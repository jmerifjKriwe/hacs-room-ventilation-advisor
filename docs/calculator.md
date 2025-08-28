# Solar Window System — Calculator (developer guide)

This document explains how the Calculator in the Solar Window System works
from a developer perspective. It covers the architecture, public functions,
data shapes, the solar + shadow math, shading decision logic, caching and
practical notes for testing and debugging.

Checklist (what this page provides)
- Contract: inputs, outputs, side-effects for the main APIs
- Data shapes used by the calculator
- Step-by-step explanation of the solar power calculation and the shadow
    factor
- Detailed scenario logic (A/B/C) and inheritance rules
- Performance & caching notes and recommended unit tests

Audience: this is written for developers who want to understand or extend
the calculation logic, add tests, or debug shading decisions.

## High-level architecture

- Coordinator: `SolarWindowSystemCoordinator`
    - Owns a `SolarWindowCalculator` instance and calls
        `calculate_all_windows_from_flows()` on a regular interval.
    - Exposes calculation results as coordinator data that sensor/binary
        platforms read to update Home Assistant entities.

- Calculator: `SolarWindowCalculator`
    - Flow-based entry point: `from_flows(hass, entry)` to create an instance
        when using the UI-based flow entries.
    - Main calculation API: `calculate_all_windows_from_flows()` returns a
        dict with `windows`, `groups` and `summary` ready for the coordinator.

## Contracts

1) SolarWindowCalculator.calculate_all_windows_from_flows() -> dict
     - Inputs: uses `hass.config_entries` to discover flow subentries and
         queries configured entity states (solar radiation, sun.sun attributes,
         temperature sensors) via short-lived cache helpers.
     - Output: dict with keys:
         - `windows`: mapping window_subentry_id -> window result dict
         - `groups`: mapping group_subentry_id -> group result dict
         - `summary`: aggregated values (total_power, counts, calculation_time)
     - Error modes: returns empty results for invalid conditions (e.g. no
         windows) and isolates exceptions per-window (exceptions are logged and
         the window receives a result with shade_required False and an error
         message).

2) SolarWindowCalculator.calculate_window_solar_power_with_shadow(effective_config, window_data, states) -> WindowCalculationResult
     - Inputs:
         - `effective_config`: nested dict (thresholds, temperatures, physical,
             plus extra keys)
         - `window_data`: raw window subentry data (may contain overrides)
         - `states`: dict with numeric `solar_radiation`, `sun_azimuth`,
             `sun_elevation`, `outdoor_temp`, `forecast_temp`, booleans etc.
     - Output: `WindowCalculationResult` dataclass with fields:
         - power_total, power_direct, power_diffuse, shadow_factor, is_visible,
             area_m2, shade_required (initial False), shade_reason (empty), effective_threshold
     - Error modes: returns zeros and is_visible False if minimums are not met.

Utility helpers
- `get_safe_state(entity_id, default)` and `get_safe_attr(entity_id, attr, default)`
    provide resilient state access and log missing/unavailable entities.
- `_get_cached_entity_state(entity_id, default, label)` caches entity state
    values for the duration of one calculation run to avoid repeated hass
    lookups.

## Data shapes

- `effective_config` (example minimal structure):
    {
        "thresholds": {"direct": 200.0, "diffuse": 150.0},
        "temperatures": {"indoor_base": 23.0, "outdoor_base": 19.5},
        "physical": {"g_value": 0.5, "frame_width": 0.125, "diffuse_factor": 0.15, "tilt": 90.0},
        ...additional window/group keys...
    }

- `WindowCalculationResult` fields (float/bool/str):
    - power_total, power_direct, power_diffuse, shadow_factor (0.1–1.0),
        is_visible, area_m2, shade_required, shade_reason, effective_threshold

## Effective config & inheritance

- `get_effective_config_from_flows(window_subentry_id)` discovers the
    corresponding window, optional linked group, and global config entries and
    merges them. The merging rules are:
    - Start with global as base
    - Overlay group values (skip explicit inheritance markers: -1, "inherit", "")
    - Overlay window-specific values (skip inheritance markers)
    - Finally normalize flat keys into nested `thresholds`, `temperatures`,
        `physical` using `_structure_flat_config()` so downstream code expects a
        stable shape.

This function also returns a `sources` structure that maps each final key to
its origin (global/group/window) which is useful for debugging and UI
tooling.

## Calculation steps (per-window)

1) Short-circuit checks
     - If `solar_radiation` < MIN_RADIATION (1e-3) or `sun_elevation` < MIN_ELEVATION
         (0.0), return zeros and is_visible False.

2) Physical parameters & area
     - Read `g_value`, `frame_width`, `diffuse_factor`, `tilt` from
         `effective_config` (safe float casting).
     - Compute glass area: `glass_width = max(0, window_width - 2*frame_width)` and
         `glass_height = max(0, window_height - 2*frame_width)`; `area = glass_width * glass_height`.

3) Diffuse power (always present)
     - power_diffuse = solar_radiation * diffuse_factor * area * g_value

4) Visibility & direct power
     - Determine visibility by checking elevation_min/max and an azimuth
         windowed sector. Azimuth difference `az_diff = ((sun_azimuth - window_azimuth + 180) % 360) - 180`.
     - If visible and cos_incidence > 0 compute (see numeric note below):
         power_direct = (solar_radiation * (1 - diffuse_factor) * cos_incidence / sin(sun_el_rad)) * area * g_value

Numeric note: cos_incidence is computed with standard spherical trig using
sun elevation/azimuth, window azimuth and panel tilt. Division by sin(sun_el)
is guarded by a small epsilon to avoid blow-ups near zero elevation.

5) Shadow factor
     - If shadow_depth>0 or shadow_offset>0 compute shadow factor via
         `_calculate_shadow_factor(sun_elevation, sun_azimuth, window_azimuth, shadow_depth, shadow_offset)`.
     - Implementation summary:
         - Convert sun elevation to radians; if <= 0 return 1.0 (sun below horizon).
         - Projected shadow length = shadow_depth / tan(sun_el_rad) (guard tan near 0).
         - Effective_shadow = max(0, shadow_length - shadow_offset)
         - Normalize by an assumed window height (the code used normalized 1.0m),
             then linearly interpolate factor between 1.0 (no shadow) and 0.1
             (full shadow). Angle dependency via azimuth difference reduces factor
             when sun aligns with window normal.

     - Final `power_direct` is multiplied by `shadow_factor`.

6) Aggregate metrics
     - power_total = power_direct + power_diffuse
     - power_m2 = power_total / max(area, 1) (guard against zero area)

7) Scenario decision
     - The code builds a `ShadeRequestFlow` with the window_data, effective_config,
         external_states and the solar_result and then calls
         `_should_shade_window_from_flows(shade_request)` which applies the
         scenario logic (A/B/C) described below.

## Shadow factor — design rationale and edge cases

- Rationale: treat shadow as geometric occlusion projected on the plane of
    the window. It scales the direct (beam) component only; diffuse remains
    unaffected.
- Edge cases and guards:
    - Near-zero sun elevation would otherwise blow up shadow_length; code
        guards using min tan and early return when sun_el_rad <= 0.
    - Negative or zero window area leads to zero power and is handled by
        max(area, 1) in per-area metrics and by returning is_visible False above.

## Scenario logic (detailed)

Precedence and overrides
- The function `_should_shade_window_from_flows()` first checks global
    overrides: `maintenance_mode` (disable shading) and `weather_warning`
    (force shading ON).

Scenario A — Strong direct sun (unconditional scenario)
- Trigger when:
    - solar_result.power_total > threshold_direct AND
    - indoor_temp >= temperatures.indoor_base AND
    - outdoor_temp >= temperatures.outdoor_base
- Returns True with reason string "Strong sun (...W > ...W)".

Scenario B — Diffuse heat (optional)
- Only evaluated if scenario B is enabled by inheritance logic.
- Trigger when:
    - solar_result.power_total > threshold_diffuse AND
    - indoor_temp > (indoor_base + scenario_b.temp_indoor_offset) AND
    - outdoor_temp > (outdoor_base + scenario_b.temp_outdoor_offset)

Scenario C — Heatwave forecast (optional)
- Only evaluated if scenario C is enabled by inheritance logic.
- Trigger when forecast_temp > temp_forecast_threshold AND
    indoor_temp >= indoor_base AND current_hour >= start_hour.

Inheritance for scenario enables
- `_get_scenario_enables_from_flows()` resolves scenario enables using
    window → group → global precedence. Window/group values can be
    `enable`/`disable`/`inherit`; global is boolean.

## Caching and performance

- Per-calculation-run entity-state caching: `_get_cached_entity_state()`
    caches states for ~30 seconds to avoid repeated hass.state lookups.
- Coordinator update interval (configurable) determines how often the
    heavy calculation runs. Default in code is 1 minute.
- When there are no windows (or insufficient radiation/elevation), the
    function returns early to save CPU.

## Logging & debugging

- The calculator logs a debug-level inheritance dump for each window
    (values coming from window/group/global and the final effective view).
- Important debug points:
    - External states read (solar_radiation, sun attributes)
    - Effective config produced per window (flat map vs sources)
    - Shadow factor and cos_incidence values when direct power is computed

## Edge cases and recommended test cases

Edge cases to cover in unit tests:
- sun below horizon or sun_elevation very small → no direct power, no
    shadow division by zero.
- shadow_depth=0 and shadow_offset>0 and vice versa.
- window dimensions too small (width/height smaller than 2*frame_width)
    → glass area clamps to zero.
- missing temperature sensor (window/group/global) → `_should_shade_window_from_flows`
    logs a warning and returns False with reason "No room temperature sensor".
- invalid numeric strings in flow data → helpers cast robustly and fall back.

Suggested unit tests (minimal set)
- calculate_window_solar_power_with_shadow: sunny, visible, no shadow
- calculate_window_solar_power_with_shadow: sun below horizon -> zeros
- _calculate_shadow_factor: series of sun elevations/azimuths vs expected factor
- _should_shade_window_from_flows: scenario A true/false, scenario B/C true/false,
    including inheritance permutations (window/group/global)

## How to trace a single shading decision (developer recipe)

1) Start from `SolarWindowSystemCoordinator._async_update_data()` — it calls the calculator method that returns the full results.
2) In the calculator: `calculate_all_windows_from_flows()` iterates windows and calls `get_effective_config_from_flows(window_id)` to build `effective_config` and `effective_sources`.
3) `apply_global_factors()` adjusts thresholds/temperatures with sensitivity/children_factor.
4) `calculate_window_solar_power_with_shadow(effective_config, window_data, external_states)` computes `WindowCalculationResult`.
5) `_get_scenario_enables_from_flows()` resolves scenario enables; `_should_shade_window_from_flows()` makes the final decision and sets `shade_required` and `shade_reason`.

Insert debug logs or run unit tests that assert intermediate values (effective_config, solar_result, shadow_factor) when verifying correctness.

## Recommendations for contributors

- Keep public helper behavior stable (safe state/attr getters and cache TTL).
- Write unit tests for pure calculation functions (`_calculate_shadow_factor`,
    `calculate_window_solar_power_with_shadow`, `_check_scenario_b/_c`).
- Use the `effective_sources` output to write tests that ensure inheritance
    works as expected.
- When changing numeric formulas, add tests for edge cases near singularities
    (sun elevation close to zero) and for typical mid-day values.

## Appendix — quick reference

- Default thresholds found in code: direct=200 W, diffuse=150 W
- Default physical values: g_value=0.5, frame_width=0.125 m, diffuse_factor=0.15, tilt=90°
- Cache TTL per calculation run: 30 seconds

If you want I can now:
- produce a small test module exercising the shadow factor and scenario
    decisions, or
- add a small tracing helper that writes the `effective_config`, `solar_result`
    and `shade_reason` to the log with a single call for easier debugging.
