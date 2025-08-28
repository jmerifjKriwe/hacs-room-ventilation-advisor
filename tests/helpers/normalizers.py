"""
Helpers to normalize transient or environment-dependent fields for snapshot testing.

These helpers are intentionally small and focused. Add more as PoC tests
require deterministic snapshots.

"""

from collections.abc import MutableMapping
from typing import Any


def normalize_entity_snapshot(
    payload: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Normalize small transient fields for entity snapshots.

    The function mutates and returns ``payload`` for convenience.
    """
    if payload.get("entity_id") is None:
        payload["entity_id"] = ""

    # Example extension point: remove runtime-only diagnostics
    payload.pop("_internal_timestamp", None)

    return payload


def normalize_timestamps(
    payload: MutableMapping[str, Any],
    *,
    keys: tuple[str, ...] = ("last_updated", "created_at"),
) -> MutableMapping[str, Any]:
    """
    Remove common timestamp-like keys from snapshot payloads.

    Removes keys at the top level and inside ``attributes`` when present.
    """
    for k in keys:
        payload.pop(k, None)
        attrs = payload.get("attributes")
        if isinstance(attrs, dict):
            attrs.pop(k, None)
    return payload


def trim_name_prefix(
    payload: MutableMapping[str, Any], *, prefix: str = "SWS_GLOBAL "
) -> MutableMapping[str, Any]:
    """
    Trim a noisy prefix from ``attributes.name`` or ``attributes.friendly_name``.

    Returns the mutated payload.
    """
    attrs = payload.get("attributes")
    if isinstance(attrs, dict):
        name = attrs.get("name") or attrs.get("friendly_name")
        if isinstance(name, str) and name.startswith(prefix):
            if "name" in attrs:
                attrs["name"] = name[len(prefix) :]
            else:
                attrs["friendly_name"] = name[len(prefix) :]
    return payload
