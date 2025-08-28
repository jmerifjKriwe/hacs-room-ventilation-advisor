"""Shared helpers for Solar Window System custom component."""

from typing import Any

from homeassistant.helpers import entity_registry as er


async def get_temperature_sensor_entities(hass: Any) -> list[dict]:
    """
    Collect temperature sensor options for selectors.

    Returns a list of option dicts with keys:
      - value: the entity_id (what gets saved)
      - label: the friendly name to show in the UI

    Keeps filtering logic from before but exposes friendly names so the
    selector can display user-friendly labels while returning the entity_id
    when selected.
    """
    entity_registry = er.async_get(hass)
    options: list[dict] = []

    # Add an explicit "inherit" option displayed in the UI as "-1" value.
    # The label is provided via translation in the front-end; use a safe
    # fallback label here in case translations aren't loaded at call time.
    try:
        inherit_label = await hass.helpers.translation.async_gettext(
            "options.step.global_basic.data_description.option_inherit"
        )
    except (AttributeError, TypeError):
        # If translation helper isn't available in this context, use fallback.
        # TypeError can be raised if the translation key is not found.
        inherit_label = "Inherit (use parent value)"
    options.append({"value": "-1", "label": str(inherit_label)})

    for ent in entity_registry.entities.values():
        if (
            ent.entity_id.startswith("sensor.")
            and not ent.disabled_by
            and not ent.hidden_by
        ):
            state = hass.states.get(ent.entity_id)
            if state and state.attributes.get("unit_of_measurement") in (
                "°C",
                "°F",
                "K",
            ):
                label = (
                    state.name or state.attributes.get("friendly_name") or ent.entity_id
                )
                options.append({"value": ent.entity_id, "label": str(label)})

    return options
