"""Tests for the configuration inheritance logic of Solar Window System."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from tests.helpers.test_framework import ConfigFlowTestCase
from tests.test_data import (
    INVALID_GLOBAL_BASIC,
    VALID_GLOBAL_BASIC,
    VALID_GLOBAL_ENHANCED,
    VALID_GLOBAL_SCENARIOS,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestConfigInheritance(ConfigFlowTestCase):
    """Tests for the configuration inheritance logic of Solar Window System."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.group_configs_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Group configurations",
            data={"entry_type": "group_configs", "is_subentry_parent": True},
            entry_id="group_configs_entry_id",
        )

        self.window_configs_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Window configurations",
            data={"entry_type": "window_configs", "is_subentry_parent": True},
            entry_id="window_configs_entry_id",
        )

    async def test_full_global_config_flow_happy_path(
        self, hass: HomeAssistant
    ) -> None:
        """Test the complete global config flow happy path."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        if result["type"] != FlowResultType.FORM:  # type: ignore[typeddict-item]
            msg = f"Expected FORM, got {result['type']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)
        if result["step_id"] != "global_basic":  # type: ignore[typeddict-item]
            msg = f"Expected global_basic, got {result['step_id']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_GLOBAL_BASIC
        )
        if result["type"] != FlowResultType.FORM:  # type: ignore[typeddict-item]
            msg = f"Expected FORM, got {result['type']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)
        if result["step_id"] != "global_enhanced":  # type: ignore[typeddict-item]
            msg = f"Expected global_enhanced, got {result['step_id']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], VALID_GLOBAL_ENHANCED
        )
        if result["type"] != FlowResultType.FORM:  # type: ignore[typeddict-item]
            msg = f"Expected FORM, got {result['type']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)
        if result["step_id"] != "global_scenarios":  # type: ignore[typeddict-item]
            msg = f"Expected global_scenarios, got {result['step_id']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)

        with patch(
            "custom_components.solar_window_system.config_flow.SolarWindowSystemConfigFlow._create_entries"
        ) as mock_create_entries:
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], VALID_GLOBAL_SCENARIOS
            )
            await hass.async_block_till_done()

            if result["type"] != FlowResultType.CREATE_ENTRY:  # type: ignore[typeddict-item]
                msg = f"Expected CREATE_ENTRY, got {result['type']}"  # type: ignore[typeddict-item]
                raise AssertionError(msg)
            if result["title"] != "Solar Window System":  # type: ignore[typeddict-item]
                msg = f"Expected 'Solar Window System', got {result['title']}"  # type: ignore[typeddict-item]
                raise AssertionError(msg)

            data = result["data"]  # type: ignore[typeddict-item]
            if data["window_width"] != 1.5:  # noqa: PLR2004
                msg = f"Expected window_width 1.5, got {data['window_width']}"
                raise AssertionError(msg)
            if data["g_value"] != 0.6:  # noqa: PLR2004
                msg = f"Expected g_value 0.6, got {data['g_value']}"
                raise AssertionError(msg)
            if data["scenario_b_temp_indoor"] != 24.0:  # noqa: PLR2004
                msg = (
                    f"Expected scenario_b_temp_indoor 24.0, got "
                    f"{data['scenario_b_temp_indoor']}"
                )
                raise AssertionError(msg)
            if data["entry_type"] != "global_config":
                msg = f"Expected 'global_config', got {data['entry_type']}"
                raise AssertionError(msg)

            mock_create_entries.assert_called_once()

    async def test_global_config_flow_validation(self, hass: HomeAssistant) -> None:
        """Test global config flow validation with invalid data."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        if result["type"] != FlowResultType.FORM:  # type: ignore[typeddict-item]
            msg = f"Expected FORM, got {result['type']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)
        if result["step_id"] != "global_basic":  # type: ignore[typeddict-item]
            msg = f"Expected global_basic, got {result['step_id']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], INVALID_GLOBAL_BASIC
        )

        if result["type"] != FlowResultType.FORM:  # type: ignore[typeddict-item]
            msg = f"Expected FORM, got {result['type']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)
        if result["step_id"] != "global_basic":  # type: ignore[typeddict-item]
            msg = f"Expected global_basic, got {result['step_id']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)
        if result["errors"] is None:  # type: ignore[typeddict-item]
            msg = "Expected errors, got None"
            raise AssertionError(msg)
        if "window_width" not in result["errors"]:  # type: ignore[typeddict-item]
            msg = f"Expected window_width in errors, got {result['errors']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)
        if result["errors"]["window_width"] != "invalid_number":  # type: ignore[typeddict-item]
            msg = f"Expected 'invalid_number', got {result['errors']['window_width']}"  # type: ignore[typeddict-item]
            raise AssertionError(msg)
