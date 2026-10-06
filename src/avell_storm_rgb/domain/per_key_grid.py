"""Per-key matrix helpers: semantic key IDs and GUI/device mapping.

Profiles are loaded from ``keyboard_layouts/profiles/*.json``. Use
``set_active_profile`` to switch layout at runtime (GUI / CLI).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from avell_storm_rgb.domain.keyboard_layouts.loader import LoadedProfile, load_profile
from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS

if TYPE_CHECKING:
    pass

DEFAULT_PROFILE_ID = "legacy_builtin"

_active: LoadedProfile = load_profile(DEFAULT_PROFILE_ID)

KEY_LAYOUT_KEYS: list[dict[str, int | str | list]] = _active.key_layout_keys
KEY_ID_TO_UI_CELL: dict[str, tuple[int, int]] = dict(_active.key_id_to_ui_cell)
BASE_KEY_TO_DEVICE_CELL: dict[str, tuple[int, int]] = dict(_active.base_key_to_device_cell)


def active_profile_id() -> str:
    return _active.profile_id


def active_profile_duplicate_cells() -> dict[tuple[int, int], list[str]]:
    return dict(_active.duplicate_device_cells)


def set_active_profile(profile_id: str) -> LoadedProfile:
    """Load profile and refresh module-level maps used by GUI and tests."""

    global _active, KEY_LAYOUT_KEYS, KEY_ID_TO_UI_CELL, BASE_KEY_TO_DEVICE_CELL
    _active = load_profile(profile_id)
    KEY_LAYOUT_KEYS = _active.key_layout_keys
    KEY_ID_TO_UI_CELL = dict(_active.key_id_to_ui_cell)
    BASE_KEY_TO_DEVICE_CELL = dict(_active.base_key_to_device_cell)
    return _active


def ui_row_to_device_row(ui_row: int) -> int:
    if not 0 <= ui_row < NUM_ROWS:
        raise ValueError(f"ui_row must be in 0..{NUM_ROWS - 1}, got {ui_row}")
    return NUM_ROWS - 1 - ui_row


def device_row_to_ui_row(device_row: int) -> int:
    if not 0 <= device_row < NUM_ROWS:
        raise ValueError(f"device_row must be in 0..{NUM_ROWS - 1}, got {device_row}")
    return NUM_ROWS - 1 - device_row


def color_map_ui_to_device(
    ui_map: dict[tuple[int, int], tuple[int, int, int]],
) -> dict[tuple[int, int], tuple[int, int, int]]:
    """Translate (ui_row, col) keys to (device_row, col) for ``Ite8291UsbDevice.set_key_colors``."""

    return {(ui_row_to_device_row(r), c): rgb for (r, c), rgb in ui_map.items()}


def key_id_to_ui_cell(key_id: str) -> tuple[int, int]:
    if key_id not in KEY_ID_TO_UI_CELL:
        raise ValueError(f"unknown key id: {key_id}")
    return KEY_ID_TO_UI_CELL[key_id]


def key_id_to_device_cell(key_id: str) -> tuple[int, int]:
    if key_id not in BASE_KEY_TO_DEVICE_CELL:
        raise ValueError(f"unknown key id: {key_id}")
    return BASE_KEY_TO_DEVICE_CELL[key_id]


def resolve_key_to_device_cell(
    key_id: str,
    overrides: dict[str, tuple[int, int]] | None = None,
) -> tuple[int, int]:
    if overrides and key_id in overrides:
        return overrides[key_id]
    return key_id_to_device_cell(key_id)


def resolve_key_to_device_map(
    overrides: dict[str, tuple[int, int]] | None = None,
) -> dict[str, tuple[int, int]]:
    resolved: dict[str, tuple[int, int]] = {}
    for key_id in KEY_ID_TO_UI_CELL:
        resolved[key_id] = resolve_key_to_device_cell(key_id, overrides)
    return resolved


def visual_cell_to_device(visual_row: int, col: int) -> tuple[int, int]:
    """Map GUI grid coordinates (row 0 = top) to firmware device cell."""

    return (ui_row_to_device_row(visual_row), int(col))


def profile_key_id_at_device_cell(device_row: int, col: int) -> str:
    """First profile ``keyId`` whose base ``deviceCell`` matches (may duplicate in profile)."""

    for key_id, cell in BASE_KEY_TO_DEVICE_CELL.items():
        if cell == (int(device_row), int(col)):
            return key_id
    return ""


def device_cell_linear_index(device_row: int, col: int) -> int:
    visual_row = device_row_to_ui_row(device_row)
    return visual_row * NUM_COLS + int(col)


def device_cell_from_linear_index(index: int) -> tuple[int, int]:
    if not 0 <= index < NUM_ROWS * NUM_COLS:
        raise ValueError(f"index must be in 0..{NUM_ROWS * NUM_COLS - 1}, got {index}")
    visual_row = index // NUM_COLS
    col = index % NUM_COLS
    return visual_cell_to_device(visual_row, col)


def _profile_calibration_key_entries() -> list[tuple[float, float, str]]:
    """Keys in layout order (yU→xU), with matrix column order within one device row."""

    layout_by_id = {str(key["keyId"]): key for key in KEY_LAYOUT_KEYS}
    groups: dict[tuple[float, int], list[tuple[int, str]]] = defaultdict(list)
    group_min_x: dict[tuple[float, int], float] = {}

    for key_id, (device_row, col) in BASE_KEY_TO_DEVICE_CELL.items():
        layout = layout_by_id.get(key_id, {})
        y = float(layout.get("yU", layout.get("row", 0)))
        x = float(layout.get("xU", layout.get("x", col)))
        group = (y, int(device_row))
        groups[group].append((int(col), key_id))
        group_min_x[group] = min(group_min_x.get(group, x), x)

    ordered_groups = sorted(groups.keys(), key=lambda g: (g[0], group_min_x[g]))
    entries: list[tuple[float, float, str]] = []
    for group in ordered_groups:
        y, _device_row = group
        for col, key_id in sorted(groups[group]):
            entries.append((y, float(col), key_id))
    return entries


def profile_calibration_key_order() -> list[str]:
    """Profile key ids in calibration order (layout top→bottom, left→right)."""

    return [key_id for _, _, key_id in _profile_calibration_key_entries()]


def profile_calibration_matrix_cell_order() -> list[tuple[int, int]]:
    """Every matrix LED in firmware grid order (visual top→bottom, left→right)."""

    cells = [(device_row, col) for device_row in range(NUM_ROWS) for col in range(NUM_COLS)]
    cells.sort(key=lambda rc: (device_row_to_ui_row(rc[0]), rc[1]))
    return cells


def profile_calibration_cell_order() -> list[tuple[int, int]]:
    """Alias for ``profile_calibration_matrix_cell_order`` (auto-cal walks the full grid)."""

    return profile_calibration_matrix_cell_order()


def profile_unmapped_device_cell_order() -> list[tuple[int, int]]:
    """Matrix LEDs with no key in the active profile (visual top→bottom, left→right)."""

    mapped = set(BASE_KEY_TO_DEVICE_CELL.values())
    unmapped: list[tuple[int, int]] = []
    for device_row in range(NUM_ROWS):
        for col in range(NUM_COLS):
            cell = (device_row, col)
            if cell not in mapped:
                unmapped.append(cell)
    unmapped.sort(key=lambda rc: (device_row_to_ui_row(rc[0]), rc[1]))
    return unmapped


def overrides_by_device_cell(
    overrides: dict[str, tuple[int, int]] | None = None,
) -> dict[tuple[int, int], str]:
    """Last key id wins if multiple overrides targeted the same cell (should not happen)."""

    out: dict[tuple[int, int], str] = {}
    for key_id, cell in (overrides or {}).items():
        out[cell] = key_id
    return out


def find_device_cell_conflicts(
    overrides: dict[str, tuple[int, int]] | None = None,
) -> dict[tuple[int, int], list[str]]:
    by_cell: dict[tuple[int, int], list[str]] = defaultdict(list)
    for key_id, cell in resolve_key_to_device_map(overrides).items():
        by_cell[cell].append(key_id)
    return {cell: ids for cell, ids in by_cell.items() if len(ids) > 1}


def find_all_device_cell_conflicts(
    overrides: dict[str, tuple[int, int]] | None = None,
) -> dict[tuple[int, int], list[str]]:
    """Resolved overrides plus profile defaults that share a device cell."""

    conflicts = dict(find_device_cell_conflicts(overrides))
    for cell, key_ids in active_profile_duplicate_cells().items():
        merged = sorted(set(conflicts.get(cell, [])) | set(key_ids))
        if len(merged) > 1:
            conflicts[cell] = merged
    return conflicts
