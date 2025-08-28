"""
Base test framework for Solar Window System tests.

This module provides standardized patterns and base classes for all test types
to ensure consistency across the test suite.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.solar_window_system.const import DOMAIN
from homeassistant import config_entries
from tests.helpers.fixtures_helpers import collect_entities_for_setup

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class BaseTestCase(ABC):
    """Base class for all Solar Window System tests."""

    test_type: str = "base"

    @abstractmethod
    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""

    def setup_test_environment(self, hass: HomeAssistant) -> dict[str, Any]:
        """Set up common test environment. Override in subclasses as needed."""
        return {
            "hass": hass,
            "domain": DOMAIN,
        }


class ConfigFlowTestCase(BaseTestCase):
    """Standardized base class for config flow tests."""

    test_type = "config_flow"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return ["hass"]

    async def init_flow(
        self,
        hass: HomeAssistant,
        source: str = "user",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Initialize a config flow with standardized parameters."""
        init_data = {"source": getattr(config_entries, f"SOURCE_{source.upper()}")}
        if data:
            init_data.update(data)

        result = await hass.config_entries.flow.async_init(DOMAIN, context=init_data)
        return dict(result)

    async def submit_form(
        self, hass: HomeAssistant, flow_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Submit form data with standardized parameters."""
        result = await hass.config_entries.flow.async_configure(
            flow_id=flow_id, user_input=data
        )
        return dict(result)


class PlatformTestCase(BaseTestCase):
    """Standardized base class for platform tests."""

    test_type = "platform"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return ["hass", "global_config_entry", "entity_configs_by_platform"]

    async def setup_platform_entities(
        self, hass: HomeAssistant, platform_module: Any, config_entry: MockConfigEntry
    ) -> list[Any]:
        """Set up platform entities with standardized approach."""
        return await collect_entities_for_setup(hass, platform_module, config_entry)


class IntegrationTestCase(BaseTestCase):
    """Standardized base class for integration tests."""

    test_type = "integration"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return ["hass", "global_config_entry"]

    async def setup_integration(
        self, hass: HomeAssistant, config_entry: MockConfigEntry
    ) -> None:
        """Set up integration with standardized approach."""
        config_entry.add_to_hass(hass)
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()


class ServiceTestCase(BaseTestCase):
    """Standardized base class for service tests."""

    test_type = "service"

    def get_required_fixtures(self) -> list[str]:
        """Return list of required fixture names for this test type."""
        return ["hass"]

    async def call_service(
        self, hass: HomeAssistant, service: str, data: dict[str, Any] | None = None
    ) -> None:
        """Call a service with standardized parameters."""
        await hass.services.async_call(DOMAIN, service, data or {}, blocking=True)


# Standardized test patterns
class TestPatterns:
    """Collection of standardized test patterns."""

    @staticmethod
    def assert_config_flow_result(
        result: dict[str, Any], expected_type: str, expected_step_id: str | None = None
    ) -> None:
        """Assert config flow results with standardized checks."""
        if result.get("type") != expected_type:
            msg = f"Expected type '{expected_type}', got '{result.get('type')}'"
            raise AssertionError(msg)
        if expected_step_id and result.get("step_id") != expected_step_id:
            step_id = result.get("step_id")
            msg = f"Expected step_id '{expected_step_id}', got '{step_id}'"
            raise AssertionError(msg)

    @staticmethod
    def assert_entity_creation(
        entities: list[Any], expected_count: int, entity_type: str
    ) -> None:
        """Assert entity creation with standardized checks."""
        if len(entities) != expected_count:
            actual_count = len(entities)
            msg = (
                f"Expected {expected_count} {entity_type} entities, got {actual_count}"
            )
            raise AssertionError(msg)

    @staticmethod
    def assert_service_registered(hass: HomeAssistant, service: str) -> None:
        """Assert service registration with standardized checks."""
        if not hass.services.has_service(DOMAIN, service):
            msg = f"Service '{service}' not registered"
            raise AssertionError(msg)


# Standardized fixture patterns
@pytest.fixture
def standard_config_entry() -> MockConfigEntry:
    """Return standard config entry fixture."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Solar Window System",
        data={"entry_type": "global_config"},
        entry_id="test_standard_entry",
    )


@pytest.fixture
def standard_window_entry() -> MockConfigEntry:
    """Return standard window config entry fixture."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Window",
        data={"entry_type": "window"},
        entry_id="test_window_entry",
    )


@pytest.fixture
def standard_group_entry() -> MockConfigEntry:
    """Return standard group config entry fixture."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Group",
        data={"entry_type": "group"},
        entry_id="test_group_entry",
    )
