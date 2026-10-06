from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import QStandardPaths

from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS

_SCHEMA_VERSION = 2


def _config_path() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
    p = Path(base) / "keyboard_mapping_overrides.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _sanitize_payload(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"schema_version": _SCHEMA_VERSION, "devices": {}}
    version = raw.get("schema_version")
    if version != _SCHEMA_VERSION:
        return {"schema_version": _SCHEMA_VERSION, "devices": {}}
    devices = raw.get("devices")
    if not isinstance(devices, dict):
        devices = {}
    return {"schema_version": _SCHEMA_VERSION, "devices": devices}


def _load_all() -> dict[str, Any]:
    p = _config_path()
    if not p.is_file():
        return {"schema_version": _SCHEMA_VERSION, "devices": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": _SCHEMA_VERSION, "devices": {}}
    return _sanitize_payload(data)


def _save_all(payload: dict[str, Any]) -> None:
    p = _config_path()
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _parse_overrides(raw: Any) -> dict[str, tuple[int, int]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, tuple[int, int]] = {}
    for key_id, value in raw.items():
        if not isinstance(key_id, str) or not isinstance(value, (list, tuple)) or len(value) != 2:
            continue
        row = int(value[0])
        col = int(value[1])
        if 0 <= row < NUM_ROWS and 0 <= col < NUM_COLS:
            out[key_id] = (row, col)
    return out


def _parse_unused_cells(raw: Any) -> set[tuple[int, int]]:
    if not isinstance(raw, list):
        return set()
    out: set[tuple[int, int]] = set()
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        row = int(item[0])
        col = int(item[1])
        if 0 <= row < NUM_ROWS and 0 <= col < NUM_COLS:
            out.add((row, col))
    return out


def load_device_profile_id(device_key: str, default_profile_id: str) -> str:
    payload = _load_all()
    raw = payload["devices"].get(device_key)
    if not isinstance(raw, dict):
        return default_profile_id
    profile_id = raw.get("profileId")
    if isinstance(profile_id, str) and profile_id.strip():
        return profile_id.strip()
    return default_profile_id


def save_device_profile_id(device_key: str, profile_id: str) -> None:
    payload = _load_all()
    entry = payload["devices"].setdefault(device_key, {})
    if not isinstance(entry, dict):
        entry = {}
        payload["devices"][device_key] = entry
    entry["profileId"] = profile_id
    if "overrides" not in entry or not isinstance(entry["overrides"], dict):
        entry["overrides"] = {}
    _save_all(payload)


def load_device_overrides(device_key: str) -> dict[str, tuple[int, int]]:
    payload = _load_all()
    raw = payload["devices"].get(device_key)
    if not isinstance(raw, dict):
        return {}
    overrides = raw.get("overrides")
    if overrides is None and raw and "profileId" not in raw:
        return _parse_overrides(raw)
    return _parse_overrides(overrides)


def load_device_unused_cells(device_key: str) -> set[tuple[int, int]]:
    payload = _load_all()
    raw = payload["devices"].get(device_key)
    if not isinstance(raw, dict):
        return set()
    return _parse_unused_cells(raw.get("unusedCells"))


def save_device_overrides(device_key: str, overrides: dict[str, tuple[int, int]]) -> None:
    payload = _load_all()
    entry = payload["devices"].setdefault(device_key, {})
    if not isinstance(entry, dict):
        entry = {}
    if "profileId" not in entry:
        entry["profileId"] = "legacy_builtin"
    entry["overrides"] = {k: [int(v[0]), int(v[1])] for k, v in overrides.items()}
    payload["devices"][device_key] = entry
    _save_all(payload)


def save_device_mapping(
    device_key: str,
    profile_id: str,
    overrides: dict[str, tuple[int, int]],
    unused_cells: set[tuple[int, int]] | None = None,
) -> None:
    payload = _load_all()
    prev = payload["devices"].get(device_key)
    prev_unused: list[list[int]] = []
    if isinstance(prev, dict) and isinstance(prev.get("unusedCells"), list):
        prev_unused = prev["unusedCells"]
    entry: dict[str, Any] = {
        "profileId": profile_id,
        "overrides": {k: [int(v[0]), int(v[1])] for k, v in overrides.items()},
    }
    cells = unused_cells if unused_cells is not None else _parse_unused_cells(prev_unused)
    if cells:
        entry["unusedCells"] = sorted([list(c) for c in cells])
    payload["devices"][device_key] = entry
    _save_all(payload)


def clear_device_mapping(device_key: str, profile_id: str) -> None:
    save_device_mapping(device_key, profile_id, {}, set())
