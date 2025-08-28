"""PoC tests for subentry flows: group and window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.config_flow import (
    GroupSubentryFlowHandler,
    WindowSubentryFlowHandler,
)
from custom_components.solar_window_system.const import DOMAIN
from tests.helpers.test_framework import ConfigFlowTestCase

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestConfigFlowSubentries(ConfigFlowTestCase):
    """PoC tests for subentry flows: group and window."""

    async def test_group_subentry_handler_user_flow(self, hass: HomeAssistant) -> None:
        """
        Instantiate GroupSubentryFlowHandler and ensure user step form is shown.

        The test attaches a MockConfigEntry as the parent and invokes the
        subentry handler's `async_step_user` to assert the form is returned.
        """
        parent = MockConfigEntry(
            domain=DOMAIN,
            data={"entry_type": "group_configs", "is_subentry_parent": True},
            title="Group configurations",
        )
        parent.add_to_hass(hass)

        handler = GroupSubentryFlowHandler()
        handler.hass = hass
        # Tests in this repo assign directly to parent_entry on the handler
        handler.parent_entry = parent  # type: ignore[attr-defined]

        result = await handler.async_step_user(None)
        if result["type"] != "form":
            msg = f"Expected form type, got {result['type']}"
            raise AssertionError(msg)

    async def test_window_subentry_handler_user_flow(self, hass: HomeAssistant) -> None:
        """Instantiate WindowSubentryFlowHandler and ensure user step form is shown."""
        parent = MockConfigEntry(
            domain=DOMAIN,
            data={"entry_type": "window_configs", "is_subentry_parent": True},
            title="Window configurations",
        )
        parent.add_to_hass(hass)

        handler = WindowSubentryFlowHandler()
        handler.hass = hass
        handler.parent_entry = parent  # type: ignore[attr-defined]

        result = await handler.async_step_user(None)
        if result["type"] != "form":
            msg = f"Expected form type, got {result['type']}"
            raise AssertionError(msg)
