"""Config flow tests for global config flow using standardized framework."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.solar_window_system.const import DOMAIN
from homeassistant import config_entries
from tests.helpers.test_framework import ConfigFlowTestCase

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestGlobalConfigFlow(ConfigFlowTestCase):
    """Test global config flow using standardized framework."""

    async def test_init_shows_basic_step(self, hass: HomeAssistant) -> None:
        """
        Starting the config flow should show the global_basic step.

        This ensures the initial step_id is `global_basic` for the global entry.
        """
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        # ConfigFlowResult behaves like a mapping for our checks
        if result.get("type") != "form":
            msg = f"Expected form, got {result.get('type')}"
            raise AssertionError(msg)
        if result.get("step_id") != "global_basic":
            msg = f"Expected global_basic, got {result.get('step_id')}"
            raise AssertionError(msg)
