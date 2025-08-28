"""
Test helpers module for Solar Window System integration.

This file contains tests for the helpers module functions.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from custom_components.solar_window_system.helpers import (
    get_temperature_sensor_entities,
)
from homeassistant.core import HomeAssistant


class TestGetTemperatureSensorEntities:
    """Test get_temperature_sensor_entities function."""

    @pytest.fixture
    def mock_hass(self) -> HomeAssistant:
        """Create a mock Home Assistant instance."""
        hass = Mock(spec=HomeAssistant)
        hass.states = Mock()
        hass.helpers = Mock()
        return hass

    @pytest.mark.asyncio
    async def test_get_temperature_sensor_entities_with_translation(
        self, mock_hass: HomeAssistant
    ) -> None:
        """Test getting temperature sensor entities with translation available."""
        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "sensor.temp1": Mock(
                entity_id="sensor.temp1", disabled_by=None, hidden_by=None
            ),
            "sensor.temp2": Mock(
                entity_id="sensor.temp2", disabled_by=None, hidden_by=None
            ),
            "sensor.humidity": Mock(
                entity_id="sensor.humidity", disabled_by=None, hidden_by=None
            ),
        }

        # Mock states with temperature sensors
        mock_state_temp1 = Mock()
        mock_state_temp1.name = "Temperature 1"
        mock_state_temp1.attributes = {"unit_of_measurement": "°C"}
        mock_state_temp2 = Mock()
        mock_state_temp2.name = "Temperature 2"
        mock_state_temp2.attributes = {"unit_of_measurement": "°F"}
        mock_state_humidity = Mock()
        mock_state_humidity.attributes = {"unit_of_measurement": "%"}

        mock_translation = Mock()
        mock_translation.async_gettext.return_value = "Inherit (translated)"

        with (
            patch(
                "custom_components.solar_window_system.helpers.er.async_get",
                return_value=mock_entity_registry,
            ),
            patch.object(
                mock_hass.states,
                "get",
                side_effect=lambda entity_id: {
                    "sensor.temp1": mock_state_temp1,
                    "sensor.temp2": mock_state_temp2,
                    "sensor.humidity": mock_state_humidity,
                }.get(entity_id),
            ),
            patch.object(mock_hass.helpers, "translation", mock_translation),
        ):
            result = await get_temperature_sensor_entities(mock_hass)

    @pytest.mark.asyncio
    async def test_get_temperature_sensor_entities_without_translation(
        self, mock_hass: HomeAssistant
    ) -> None:
        """Test getting temperature sensor entities without translation available."""
        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "sensor.temp1": Mock(
                entity_id="sensor.temp1", disabled_by=None, hidden_by=None
            ),
        }

        # Mock state with temperature sensor
        mock_state_temp1 = Mock()
        mock_state_temp1.name = "Temperature 1"
        mock_state_temp1.attributes = {"unit_of_measurement": "°C"}

        # Mock translation failure
        mock_translation = None

        with (
            patch(
                "custom_components.solar_window_system.helpers.er.async_get",
                return_value=mock_entity_registry,
            ),
            patch.object(
                mock_hass.states,
                "get",
                side_effect=lambda entity_id: {
                    "sensor.temp1": mock_state_temp1,
                }.get(entity_id),
            ),
            patch.object(mock_hass.helpers, "translation", mock_translation),
        ):
            result = await get_temperature_sensor_entities(mock_hass)

            # Should have inherit option + 1 temperature sensor
            assert len(result) == 2
            assert result[0] == {"value": "-1", "label": "Inherit (use parent value)"}
            assert result[1] == {"value": "sensor.temp1", "label": "Temperature 1"}

    @pytest.mark.asyncio
    async def test_get_temperature_sensor_entities_with_friendly_name_fallback(
        self, mock_hass: HomeAssistant
    ) -> None:
        """Test getting temperature sensor entities with friendly name fallback."""
        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "sensor.temp1": Mock(
                entity_id="sensor.temp1", disabled_by=None, hidden_by=None
            ),
        }

        # Mock state with temperature sensor (no name, use friendly_name)
        mock_state_temp1 = Mock()
        mock_state_temp1.name = None
        mock_state_temp1.attributes = {
            "unit_of_measurement": "°C",
            "friendly_name": "Friendly Temperature",
        }

        # Mock translation failure to use fallback
        mock_translation = None

        with (
            patch(
                "custom_components.solar_window_system.helpers.er.async_get",
                return_value=mock_entity_registry,
            ),
            patch.object(
                mock_hass.states,
                "get",
                side_effect=lambda entity_id: {
                    "sensor.temp1": mock_state_temp1,
                }.get(entity_id),
            ),
            patch.object(mock_hass.helpers, "translation", mock_translation),
        ):
            result = await get_temperature_sensor_entities(mock_hass)

            assert len(result) == 2
            assert result[1] == {
                "value": "sensor.temp1",
                "label": "Friendly Temperature",
            }

    @pytest.mark.asyncio
    async def test_get_temperature_sensor_entities_with_entity_id_fallback(
        self, mock_hass: HomeAssistant
    ) -> None:
        """Test getting temperature sensor entities with entity_id fallback."""
        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "sensor.temp1": Mock(
                entity_id="sensor.temp1", disabled_by=None, hidden_by=None
            ),
        }

        # Mock state with temperature sensor (no name, no friendly_name)
        mock_state_temp1 = Mock()
        mock_state_temp1.name = None
        mock_state_temp1.attributes = {"unit_of_measurement": "°C"}

        # Mock translation failure to use fallback
        mock_translation = None

        with (
            patch(
                "custom_components.solar_window_system.helpers.er.async_get",
                return_value=mock_entity_registry,
            ),
            patch.object(
                mock_hass.states,
                "get",
                side_effect=lambda entity_id: {
                    "sensor.temp1": mock_state_temp1,
                }.get(entity_id),
            ),
            patch.object(mock_hass.helpers, "translation", mock_translation),
        ):
            result = await get_temperature_sensor_entities(mock_hass)

            assert len(result) == 2
            assert result[1] == {"value": "sensor.temp1", "label": "sensor.temp1"}

    @pytest.mark.asyncio
    async def test_get_temperature_sensor_entities_filters_disabled_hidden(
        self, mock_hass: HomeAssistant
    ) -> None:
        """Test that disabled and hidden entities are filtered out."""
        # Mock entity registry with disabled and hidden entities
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "sensor.temp1": Mock(
                entity_id="sensor.temp1", disabled_by=None, hidden_by=None
            ),
            "sensor.temp2": Mock(
                entity_id="sensor.temp2", disabled_by="user", hidden_by=None
            ),
            "sensor.temp3": Mock(
                entity_id="sensor.temp3", disabled_by=None, hidden_by="user"
            ),
        }

        # Mock states
        mock_state_temp1 = Mock()
        mock_state_temp1.name = "Temperature 1"
        mock_state_temp1.attributes = {"unit_of_measurement": "°C"}

        # Mock translation failure to use fallback
        mock_translation = None

        with (
            patch(
                "custom_components.solar_window_system.helpers.er.async_get",
                return_value=mock_entity_registry,
            ),
            patch.object(
                mock_hass.states,
                "get",
                side_effect=lambda entity_id: {
                    "sensor.temp1": mock_state_temp1,
                }.get(entity_id),
            ),
            patch.object(mock_hass.helpers, "translation", mock_translation),
        ):
            result = await get_temperature_sensor_entities(mock_hass)

            # Should only include non-disabled, non-hidden entities
            assert len(result) == 2  # inherit + 1 temperature sensor
            assert result[1] == {"value": "sensor.temp1", "label": "Temperature 1"}

    @pytest.mark.asyncio
    async def test_get_temperature_sensor_entities_filters_non_temperature(
        self, mock_hass: HomeAssistant
    ) -> None:
        """Test that non-temperature sensors are filtered out."""
        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "sensor.temp1": Mock(
                entity_id="sensor.temp1", disabled_by=None, hidden_by=None
            ),
            "sensor.humidity": Mock(
                entity_id="sensor.humidity", disabled_by=None, hidden_by=None
            ),
            "sensor.pressure": Mock(
                entity_id="sensor.pressure", disabled_by=None, hidden_by=None
            ),
        }

        # Mock states with different units
        mock_state_temp1 = Mock()
        mock_state_temp1.name = "Temperature 1"
        mock_state_temp1.attributes = {"unit_of_measurement": "°C"}

        mock_state_humidity = Mock()
        mock_state_humidity.name = "Humidity"
        mock_state_humidity.attributes = {"unit_of_measurement": "%"}

        mock_state_pressure = Mock()
        mock_state_pressure.name = "Pressure"
        mock_state_pressure.attributes = {"unit_of_measurement": "hPa"}

        # Mock translation failure to use fallback
        mock_translation = None

        with (
            patch(
                "custom_components.solar_window_system.helpers.er.async_get",
                return_value=mock_entity_registry,
            ),
            patch.object(
                mock_hass.states,
                "get",
                side_effect=lambda entity_id: {
                    "sensor.temp1": mock_state_temp1,
                    "sensor.humidity": mock_state_humidity,
                    "sensor.pressure": mock_state_pressure,
                }.get(entity_id),
            ),
            patch.object(mock_hass.helpers, "translation", mock_translation),
        ):
            result = await get_temperature_sensor_entities(mock_hass)

            # Should only include temperature sensors
            assert len(result) == 2  # inherit + 1 temperature sensor
            assert result[1] == {"value": "sensor.temp1", "label": "Temperature 1"}

    @pytest.mark.asyncio
    async def test_get_temperature_sensor_entities_kelvin_support(
        self, mock_hass: HomeAssistant
    ) -> None:
        """Test that Kelvin temperature sensors are included."""
        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "sensor.temp_kelvin": Mock(
                entity_id="sensor.temp_kelvin", disabled_by=None, hidden_by=None
            ),
        }

        # Mock state with Kelvin temperature sensor
        mock_state_kelvin = Mock()
        mock_state_kelvin.name = "Temperature Kelvin"
        mock_state_kelvin.attributes = {"unit_of_measurement": "K"}

        # Mock translation failure to use fallback
        mock_translation = None

        with (
            patch(
                "custom_components.solar_window_system.helpers.er.async_get",
                return_value=mock_entity_registry,
            ),
            patch.object(
                mock_hass.states,
                "get",
                side_effect=lambda entity_id: {
                    "sensor.temp_kelvin": mock_state_kelvin,
                }.get(entity_id),
            ),
            patch.object(mock_hass.helpers, "translation", mock_translation),
        ):
            result = await get_temperature_sensor_entities(mock_hass)

            assert len(result) == 2  # inherit + 1 temperature sensor
            assert result[1] == {
                "value": "sensor.temp_kelvin",
                "label": "Temperature Kelvin",
            }

    @pytest.mark.asyncio
    async def test_get_temperature_sensor_entities_no_states(
        self, mock_hass: HomeAssistant
    ) -> None:
        """Test behavior when no states are available."""
        # Mock entity registry
        mock_entity_registry = Mock()
        mock_entity_registry.entities = {
            "sensor.temp1": Mock(
                entity_id="sensor.temp1", disabled_by=None, hidden_by=None
            ),
        }

        # Mock translation failure to use fallback
        mock_translation = None

        with (
            patch(
                "custom_components.solar_window_system.helpers.er.async_get",
                return_value=mock_entity_registry,
            ),
            patch.object(mock_hass.states, "get", return_value=None),
            patch.object(mock_hass.helpers, "translation", mock_translation),
        ):
            result = await get_temperature_sensor_entities(mock_hass)

            # Should only have inherit option since no valid temperature sensors
            assert len(result) == 1
            expected = {"value": "-1", "label": "Inherit (use parent value)"}
            assert result[0] == expected
