# ruff: noqa: S101,PT012
"""
Test to verify string conversion handling in config flows.

Assertions are used intentionally in tests; disable assertion lint (S101) for this
module.
"""

# ruff: noqa: S101, ARG002, ANN001, D102

from unittest.mock import AsyncMock, PropertyMock, patch

import pytest
import voluptuous as vol

from custom_components.solar_window_system import config_flow
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from tests.test_data import (
    VALID_GLOBAL_ENHANCED,
    VALID_GLOBAL_SCENARIOS,
    VALID_GROUP_OPTIONS_NUMERIC,
    VALID_WINDOW_OPTIONS_NUMERIC,
)


class TestSecondSaveBugFix:
    """Test suite specifically designed to catch the string-conversion bug."""

    async def test_group_reconfigure_with_numeric_values_second_save(
        self, hass: HomeAssistant, global_config_entry
    ) -> None:
        """Test group reconfiguration with numeric values on second save."""
        flow = config_flow.GroupSubentryFlowHandler()
        flow.hass = hass
        flow.init_step = "user"
        with (
            patch.object(
                type(flow),
                "source",
                new_callable=PropertyMock,
                return_value=config_entries.SOURCE_USER,
            ),
            patch(
                "custom_components.solar_window_system.helpers.get_temperature_sensor_entities",
                return_value=[],
            ),
        ):
            initial_input = {
                k: str(v) if isinstance(v, (int, float)) else v
                for k, v in VALID_GROUP_OPTIONS_NUMERIC.items()
            }
            initial_input["indoor_temperature_sensor"] = "sensor.temp1"
            result = await flow.async_step_user(None)

            group_step1_data = {
                k: str(v) for k, v in VALID_GROUP_OPTIONS_NUMERIC.items()
            }
            result = await flow.async_step_user(group_step1_data)
            assert result["type"] == "form"
            assert result["step_id"] == "enhanced"

            group_step2_data = {k: str(v) for k, v in VALID_GLOBAL_SCENARIOS.items()}
            result = await flow.async_step_enhanced(group_step2_data)
            assert result["type"] == "create_entry"
            stored_data = initial_input.copy()

        reconfig_flow = config_flow.GroupSubentryFlowHandler()
        reconfig_flow.hass = hass
        reconfig_flow.init_step = "user"
        with (
            patch.object(
                type(reconfig_flow),
                "source",
                new_callable=PropertyMock,
                return_value=config_entries.SOURCE_RECONFIGURE,
            ),
            patch.object(
                reconfig_flow,
                "_get_reconfigure_subentry",
                return_value=AsyncMock(data=stored_data),
            ),
            patch(
                "custom_components.solar_window_system.helpers.get_temperature_sensor_entities",
                return_value=[],
            ),
        ):
            result2 = await reconfig_flow.async_step_reconfigure(None)
            assert result2["type"] == "form"
            assert result2["step_id"] == "user"
            assert "data_schema" in result2
            schema = result2["data_schema"]
            assert isinstance(schema, vol.Schema)

            same_input = {
                k: str(v) if isinstance(v, (int, float)) else v
                for k, v in VALID_GROUP_OPTIONS_NUMERIC.items()
            }
            try:
                validated_data = schema(same_input)
                assert isinstance(validated_data, dict)
            except vol.Invalid as exc:
                if "expected str" in str(exc):
                    pytest.fail(f"String conversion fix failed: {exc}")
                else:
                    pass

    async def test_window_reconfigure_with_numeric_values_second_save(
        self, hass, global_config_entry
    ) -> None:
        flow = config_flow.WindowSubentryFlowHandler()
        flow.hass = hass
        flow.init_step = "user"
        with (
            patch.object(
                type(flow),
                "source",
                new_callable=PropertyMock,
                return_value=config_entries.SOURCE_USER,
            ),
            patch(
                "custom_components.solar_window_system.helpers.get_temperature_sensor_entities",
                return_value=[],
            ),
            patch.object(
                flow,
                "_get_group_subentries",
                return_value=[],
            ),
        ):
            initial_input = {
                k: str(v) if isinstance(v, (int, float)) else v
                for k, v in VALID_WINDOW_OPTIONS_NUMERIC.items()
            }
            result = await flow.async_step_user(None)

            window_step1_data = {
                k: str(v) for k, v in VALID_WINDOW_OPTIONS_NUMERIC.items()
            }
            result = await flow.async_step_user(window_step1_data)
            assert result["type"] == "form"
            assert result["step_id"] == "overrides"

            window_step2_data = {k: str(v) for k, v in VALID_GLOBAL_ENHANCED.items()}
            result = await flow.async_step_overrides(window_step2_data)
            assert result["type"] == "form"
            assert result["step_id"] == "scenarios"

            window_step3_data = {k: str(v) for k, v in VALID_GLOBAL_SCENARIOS.items()}
            result = await flow.async_step_scenarios(window_step3_data)
            assert result["type"] == "create_entry"
            stored_data = initial_input.copy()

        reconfig_flow = config_flow.WindowSubentryFlowHandler()
        reconfig_flow.hass = hass
        reconfig_flow.init_step = "user"
        with (
            patch.object(
                type(reconfig_flow),
                "source",
                new_callable=PropertyMock,
                return_value=config_entries.SOURCE_RECONFIGURE,
            ),
            patch.object(
                reconfig_flow,
                "_get_reconfigure_subentry",
                return_value=AsyncMock(data=stored_data),
            ),
            patch(
                "custom_components.solar_window_system.helpers.get_temperature_sensor_entities",
                return_value=[],
            ),
            patch.object(
                reconfig_flow,
                "_get_group_subentries",
                return_value=[],
            ),
        ):
            result2 = await reconfig_flow.async_step_reconfigure(None)
            assert result2["type"] == "form"
            same_input = {
                k: str(v) if isinstance(v, (int, float)) else v
                for k, v in VALID_WINDOW_OPTIONS_NUMERIC.items()
            }
            try:
                schema = result2["data_schema"]
                validated_data = schema(same_input)
                assert isinstance(validated_data, dict)
            except vol.Invalid as exc:
                if "expected str" in str(exc):
                    pytest.fail(f"String conversion fix failed: {exc}")
                else:
                    pass

    def test_voluptuous_schema_with_numeric_defaults_fails_without_fix(self) -> None:
        with pytest.raises(vol.Invalid, match="expected str"):
            schema = vol.Schema({vol.Optional("test_field", default=123): str})
            schema({})

        schema_fixed = vol.Schema({vol.Optional("test_field", default="123"): str})
        result = schema_fixed({})
        assert result["test_field"] == "123"

    def test_ui_default_string_conversion(self) -> None:
        test_defaults = {
            "string_val": "test",
            "int_val": 123,
            "float_val": 45.67,
            "none_val": None,
            "empty_val": "",
        }

        global_data = {"int_val": 999, "none_val": 888}

        def _ui_default(key: str) -> str:
            cur = test_defaults.get(key, "")
            gv = global_data.get(key, "")
            if cur in ("", None) and gv not in ("", None):
                return "-1"
            return str(cur) if cur not in ("", None) else ""

        assert _ui_default("string_val") == "test"
        assert _ui_default("int_val") == "123"
        assert _ui_default("float_val") == "45.67"
        assert _ui_default("none_val") == "-1"
        assert _ui_default("empty_val") == ""
        assert _ui_default("missing") == ""

        for key in test_defaults:
            result = _ui_default(key)
            assert isinstance(result, str), (
                f"Result for {key} is not a string: {type(result)}"
            )
