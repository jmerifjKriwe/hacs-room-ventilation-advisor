"""
Serialize a Home Assistant entity/state into a compact JSON snapshot.

The functions accept either mapping-like objects (dicts) or objects with
``entity_id``, ``state`` and ``attributes`` attributes (Home Assistant
``State`` objects). They optionally normalise numeric-looking state strings
into numbers which makes snapshots more stable.

"""

from collections.abc import Mapping
from typing import Any


def _to_number_if_possible(value: Any) -> Any:
    """Try to convert string numbers to int/float; leave other values untouched."""
    if not isinstance(value, str):
        return value
    # avoid converting boolean-like strings; only attempt numeric casts
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def serialize_entity(obj: Any, *, normalize_numbers: bool = True) -> dict:
    """
    Return a minimal dict for ``obj``.

    The returned dict contains at least ``entity_id``, ``state`` and
    ``attributes``. If a ``unique_id`` can be determined it will be included.

    Args:
        obj: A mapping (dict-like) or an object with ``entity_id``,
            ``state``, and ``attributes`` attributes.
        normalize_numbers: If True, attempt to convert numeric-looking state
            strings into numbers (int/float).

    """
    entity_id = None
    unique_id = None
    state = None
    attributes = {}

    if isinstance(obj, Mapping):
        entity_id = obj.get("entity_id")
        unique_id = obj.get("unique_id") or (obj.get("attributes") or {}).get(
            "unique_id"
        )
        state = obj.get("state")
        attributes = dict(obj.get("attributes") or {})
    else:
        entity_id = getattr(obj, "entity_id", None)
        state = getattr(obj, "state", None)
        attributes = getattr(obj, "attributes", {}) or {}
        # common pattern for helper-backed entities
        unique_id = getattr(obj, "unique_id", None) or attributes.get("unique_id")

    if normalize_numbers:
        state = _to_number_if_possible(state)

    out: dict[str, Any] = {
        "entity_id": entity_id,
        "state": state,
        "attributes": attributes,
    }
    if unique_id:
        out["unique_id"] = unique_id
    return out
