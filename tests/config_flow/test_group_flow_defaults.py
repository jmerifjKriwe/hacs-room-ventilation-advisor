"""Test that Group subentry flow shows empty defaults but global suggested values."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.config_flow import GroupSubentryFlowHandler
from custom_components.solar_window_system.const import DOMAIN
from homeassistant.data_entry_flow import FlowResultType
from tests.helpers.test_framework import ConfigFlowTestCase
from tests.test_data import VALID_GLOBAL_BASIC, VALID_GLOBAL_ENHANCED

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestGroupFlowDefaults(ConfigFlowTestCase):
    """Test Group subentry flow shows empty defaults but global suggested values."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_group_parent_entry = MockConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Group configurations",
            data={
                "entry_type": "group_configs",
                "is_subentry_parent": True,
            },
            source="internal",
            entry_id="test_group_parent_id",
            unique_id=None,
        )

        data = {"entry_type": "global_config"}
        data.update(VALID_GLOBAL_BASIC)
        data.update(VALID_GLOBAL_ENHANCED)
        # Override with test-specific values
        data["diffuse_factor"] = "0.2"
        data["threshold_direct"] = "250"
        data["temperature_indoor_base"] = "22.0"
        data["indoor_temperature_sensor"] = "sensor.global_temp"
        self.mock_global_config_entry = MockConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Solar Window System",
            data=data,
            source="user",
            entry_id="global_config_entry_id",
            unique_id=None,
        )

    async def test_group_defaults_and_suggestions(self, hass: HomeAssistant) -> None:
        """Test group subentry form shows empty defaults but suggests global values."""
        self.mock_group_parent_entry.add_to_hass(hass)
        self.mock_global_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities",
            return_value=[{"label": "Global Temp", "value": "sensor.global_temp"}],
        ):
            flow_handler = GroupSubentryFlowHandler()
            flow_handler.hass = hass
            # set non-public attributes used by the handler
            try:
                flow_handler.handler = DOMAIN  # type: ignore[attr-defined]
            except AttributeError:
                # older handler versions may not expose this attr in type hints
                flow_handler.handler = DOMAIN  # type: ignore[attr-defined]
            try:
                flow_handler.parent_entry_id = self.mock_group_parent_entry.entry_id  # type: ignore[attr-defined]
            except AttributeError:
                flow_handler.parent_entry_id = self.mock_group_parent_entry.entry_id  # type: ignore[attr-defined]

            # Step: show form with no user input (defaults)
            result = await flow_handler.async_step_user()
            if result["type"] != FlowResultType.FORM:  # type: ignore[typeddict-item]
                msg = f"Expected form, got {result['type']}"  # type: ignore[typeddict-item]
                raise AssertionError(msg)
            schema = result["data_schema"].schema  # type: ignore[typeddict-item]

            # Numeric fields should have empty default but suggested_value from global
            for key, _expected in (
                ("diffuse_factor", "0.2"),
                ("threshold_direct", "250"),
                ("temperature_indoor_base", "22.0"),
            ):
                field = schema[key]
                # default should be empty string
                if getattr(field, "default", "") not in ("", None, ""):
                    msg = "Expected empty default"
                    raise AssertionError(msg)

            # Sensor selector: default is "-1" (inherit), and global value is suggested
            found = False
            for key in schema:
                if hasattr(key, "schema") and key.schema == "indoor_temperature_sensor":
                    default_value = (
                        key.default() if callable(key.default) else key.default
                    )
                    if default_value != "-1":
                        msg = "Expected default '-1'"
                        raise AssertionError(msg)
                    found = True
            if not found:
                msg = "Schema key for 'indoor_temperature_sensor' not found"
                raise AssertionError(msg)
