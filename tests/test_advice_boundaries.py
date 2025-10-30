"""Boundary tests for ventilation advice mapping."""

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.room_ventilation_advisor.sensor import (
    SCORE_GOOD,
    SCORE_MODERATE,
    SCORE_POOR,
    VentilationDataUpdateCoordinator,
    VentilationSensor,
)


@pytest.mark.parametrize(
    "score",
    [
        SCORE_GOOD,
        SCORE_GOOD - 0.01,
        SCORE_MODERATE,
        SCORE_MODERATE - 0.01,
        SCORE_POOR,
        SCORE_POOR - 0.01,
        None,
    ],
)
async def test_advice_boundaries(
    hass: HomeAssistant,
    score: float | None,
    advice_category: Callable[[float | None], str],
) -> None:
    """Ensure advice string matches numeric score boundaries."""
    config_entry = MockConfigEntry(domain="room_ventilation_advisor", data={})
    coordinator = VentilationDataUpdateCoordinator(hass, config_entry)
    sensor = VentilationSensor(coordinator, "Boundary Room", {})
    sensor.hass = hass

    # Ensure coordinator contains room data so attributes are populated
    coordinator.data = {
        "outdoor_temp": 10,
        "outdoor_humidity": 70,
        "wind_speed": 5,
        "rooms": {
            "Boundary Room": {
                "indoor_temp": 20,
                "indoor_humidity": 50,
                "co2_level": None,
                "room_type": "living_room",
            }
        },
    }

    with patch.object(
        VentilationSensor,
        "native_value",
        new_callable=MagicMock,
    ) as mock_native:
        mock_native.__get__ = MagicMock(return_value=score)
        # Update attributes that read advice
        sensor._update_extra_state_attributes()
    attrs = sensor.extra_state_attributes
    expected = advice_category(score)
    assert attrs is not None
    assert expected in attrs["ventilation_advice"]
