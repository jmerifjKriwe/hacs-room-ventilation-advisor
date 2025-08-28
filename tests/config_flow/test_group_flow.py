"""Test group config flow."""

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


class TestGroupFlow(ConfigFlowTestCase):
    """Test group config flow."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_group_parent_entry = MockConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Group configurations",
            data={"entry_type": "group_configs", "is_subentry_parent": True},
            source="internal",
            entry_id="test_group_parent_id",
            unique_id=None,
        )

        data = {"entry_type": "global_config"}
        data.update(VALID_GLOBAL_BASIC)
        data.update(VALID_GLOBAL_ENHANCED)
        self.mock_global_config_entry = MockConfigEntry(
            version=1,
            minor_version=1,
            domain=DOMAIN,
            title="Solar Window System",
            data=data,
            source="user",
            entry_id="test_global_config_id",
            unique_id=None,
        )

    async def test_group_subentry_flow_add_and_invalid(
        self, hass: HomeAssistant
    ) -> None:
        """Verify group subentry flow with valid and invalid values."""
        self.mock_group_parent_entry.add_to_hass(hass)
        self.mock_global_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.solar_window_system.config_flow.get_temperature_sensor_entities",
            return_value=[{"label": "Indoor Temp", "value": "sensor.indoor_temp"}],
        ):
            flow_handler = GroupSubentryFlowHandler()
            flow_handler.hass = hass
            # Removed incorrect attribute assignments

            user_input = {
                "name": "Test Group",
                "indoor_temperature_sensor": "sensor.indoor_temp",
                "diffuse_factor": "0.15",
                "threshold_direct": "200",
                "threshold_diffuse": "150",
                "temperature_indoor_base": "23.0",
                "temperature_outdoor_base": "19.5",
            }
            result = await flow_handler.async_step_user(user_input)
            if result["type"] != FlowResultType.FORM:  # type: ignore[typeddict-item]
                msg = f"Expected FORM, got {result['type']}"  # type: ignore[typeddict-item]
                raise AssertionError(msg)
            if result["step_id"] != "enhanced":  # type: ignore[typeddict-item]
                msg = f"Expected enhanced, got {result['step_id']}"  # type: ignore[typeddict-item]
                raise AssertionError(msg)

            bad_input = {
                "name": "Test Group",
                "indoor_temperature_sensor": "sensor.indoor_temp",
                "diffuse_factor": "0.01",
                "threshold_direct": "200",
                "threshold_diffuse": "150",
                "temperature_indoor_base": "23.0",
                "temperature_outdoor_base": "19.5",
            }
            result2 = await flow_handler.async_step_user(bad_input)
            if result2["type"] != FlowResultType.FORM:  # type: ignore[typeddict-item]
                msg = f"Expected FORM, got {result2['type']}"  # type: ignore[typeddict-item]
                raise AssertionError(msg)
            errors = result2.get("errors")  # type: ignore[typeddict-item]
            if not errors:
                msg = "Expected errors, got None"
                raise AssertionError(msg)
            if "diffuse_factor" not in errors:
                msg = f"Expected diffuse_factor in errors, got {errors}"
                raise AssertionError(msg)
