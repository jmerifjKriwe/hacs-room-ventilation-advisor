# ruff: noqa: SLF001
"""Tests for duplicate-name handling in Group SubentryFlowHandler."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import PropertyMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import DOMAIN
from homeassistant.data_entry_flow import FlowResultType
from tests.helpers.test_framework import ConfigFlowTestCase
from tests.test_data import VALID_GROUP_OPTIONS_NUMERIC

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class TestGroupSubentryDuplicate(ConfigFlowTestCase):
    """Tests for duplicate-name handling in Group SubentryFlowHandler."""

    async def test_create_group_duplicate_name(self, hass: HomeAssistant) -> None:
        """Creating a group with a duplicate name should produce an error."""
        # Create parent entry representing the groups container
        group_parent_entry = MockConfigEntry(
            domain=DOMAIN,
            data={"entry_type": "group_configs", "is_subentry_parent": True},
            title="Group configurations",
        )
        group_parent_entry.add_to_hass(hass)

        # Simulate existing subentry to provoke duplicate-name error
        class DummySub:
            def __init__(self, title: str) -> None:
                self.title = title
                self.subentry_type = "group"
                self.data = {"name": title}

        fake_subentries = {"1": DummySub("My Test Group")}
        # Attach a constant subentries mapping to simulate existing child entries
        group_parent_entry.subentries = fake_subentries  # type: ignore[attr-defined]

        # First creation should succeed
        handler1 = __import__(
            "custom_components.solar_window_system.config_flow",
            fromlist=["GroupSubentryFlowHandler"],
        ).GroupSubentryFlowHandler()
        handler1.hass = hass
        handler1.parent_entry = group_parent_entry  # type: ignore[attr-defined]
        with patch.object(
            type(handler1), "source", new_callable=PropertyMock, return_value="user"
        ):
            group_config = {
                k: str(v) if isinstance(v, (int, float)) else v
                for k, v in VALID_GROUP_OPTIONS_NUMERIC.items()
                if k != "name"
            }
            result1 = await handler1.async_step_user(
                {"name": "My Test Group", **group_config}
            )
            # Check if we got a form (need to provide enhanced input) or CREATE_ENTRY
            if result1["type"] == FlowResultType.FORM:
                # Need to provide enhanced input - ensure _basic is set first
                handler1._basic = {"name": "My Test Group", **group_config}  # type: ignore[attr-defined]
                result1 = await handler1.async_step_enhanced({})
            if result1["type"] != FlowResultType.CREATE_ENTRY:
                msg = f"Expected CREATE_ENTRY, got {result1['type']}"
                raise AssertionError(msg)

        # Second creation with same name should return a form with errors
        handler2 = __import__(
            "custom_components.solar_window_system.config_flow",
            fromlist=["GroupSubentryFlowHandler"],
        ).GroupSubentryFlowHandler()
        handler2.hass = hass
        handler2.parent_entry = group_parent_entry  # type: ignore[attr-defined]
        with patch.object(
            type(handler2), "source", new_callable=PropertyMock, return_value="subentry"
        ):
            group_config = {
                k: str(v) if isinstance(v, (int, float)) else v
                for k, v in VALID_GROUP_OPTIONS_NUMERIC.items()
                if k != "name"
            }
            result2 = await handler2.async_step_user(
                {"name": "My Test Group", **group_config}
            )
            if result2["type"] != FlowResultType.FORM:
                msg = f"Expected FORM, got {result2['type']}"
                raise AssertionError(msg)
            if result2["errors"] != {"name": "duplicate_name"}:
                msg = f"Expected duplicate_name error, got {result2['errors']}"
                raise AssertionError(msg)
