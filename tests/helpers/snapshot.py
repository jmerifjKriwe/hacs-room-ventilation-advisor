"""
Small snapshot helpers for tests.

This module stores JSON snapshots under ``tests/__snapshots__`` and provides a
minimal API to save and compare snapshots. On first run the snapshot is
created; the test will fail so the developer can review the snapshot.
"""

import json
from pathlib import Path
from typing import Any

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "__snapshots__"


def _snapshot_path(name: str) -> Path:
    """
    Return the target Path for the named snapshot.

    The snapshot file is stored as JSON with the given name and the `.json`
    suffix.
    """
    return SNAPSHOT_DIR / (name + ".json")


def save_snapshot(name: str, data: Any) -> None:
    """Write the provided data as a deterministic JSON snapshot."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(name)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, sort_keys=True, indent=2)


def load_snapshot(name: str) -> Any:
    """
    Load and return the JSON snapshot for the given name.

    Raises FileNotFoundError if the snapshot does not exist.
    """
    path = _snapshot_path(name)
    if not path.exists():
        msg = f"Snapshot not found: {path}"
        raise FileNotFoundError(msg)
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def assert_matches_snapshot(name: str, data: Any) -> None:
    """
    Compare `data` against a stored snapshot named `name`.

    If no snapshot exists it will be written and the test will fail with an
    instructive message so the developer can inspect the generated snapshot.
    """
    path = _snapshot_path(name)

    # If snapshot does not exist, create it and instruct the developer to
    # verify the generated file. This makes the first run explicit.
    if not path.exists():
        save_snapshot(name, data)
        msg = f"Created snapshot: {path}. Please verify and re-run tests."
        raise AssertionError(msg)

    # Otherwise load the expected snapshot and compare deterministically.
    expected = load_snapshot(name)
    expected_txt = json.dumps(expected, sort_keys=True, indent=2, ensure_ascii=False)
    actual_txt = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
    if expected_txt != actual_txt:
        msg = (
            f"Snapshot mismatch for '{name}'\n--- expected\n+++ actual\n\n"
            f"Expected:\n{expected_txt}\n\nActual:\n{actual_txt}\n"
        )
        raise AssertionError(msg)
