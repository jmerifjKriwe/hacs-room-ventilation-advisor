"""Tests for invalid value handling in the config flow using standardized framework."""

import pytest

from homeassistant.core import HomeAssistant
from tests.helpers.test_framework import ConfigFlowTestCase, TestPatterns
from tests.test_data import INVALID_GLOBAL_BASIC


class TestConfigFlowInvalidValue(ConfigFlowTestCase):
    """Test invalid value handling in config flow using standardized framework."""

    @pytest.mark.asyncio
    async def test_config_flow_invalid_value(self, hass: HomeAssistant) -> None:
        """Invalid numeric values should be reported as form errors."""
        result = await self.init_flow(hass, "user")
        TestPatterns.assert_config_flow_result(result, "form", "global_basic")

        user_input = INVALID_GLOBAL_BASIC.copy()
        user_input["window_width"] = "0.05"  # Must be >= 0.1 per validators
        flow_id = result["flow_id"]
        result2 = await self.submit_form(hass, flow_id, user_input)
        TestPatterns.assert_config_flow_result(result2, "form", "global_basic")

        # Check for specific error
        errors = result2.get("errors")
        if not errors or "window_width" not in errors:
            msg = f"Expected error for window_width, got: {errors}"
            raise AssertionError(msg)
