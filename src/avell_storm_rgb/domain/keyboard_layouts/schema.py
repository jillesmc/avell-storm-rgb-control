"""Validate keyboard layout profile documents."""

from __future__ import annotations

from typing import Any

from avell_storm_rgb.domain.keyboard_layouts.visual_geometry import (
    VisualLayoutSpec,
    collect_visual_rects,
    find_overlaps,
)
from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS

SPACER_KEY_ID = "_spacer"


def _is_spacer(key: dict[str, Any]) -> bool:
    return str(key.get("keyId", "")) == SPACER_KEY_ID


def _uses_visual_v2(doc: dict[str, Any]) -> bool:
    spec = VisualLayoutSpec.from_document(doc)
    return spec is not None


def validate_profile_document(doc: dict[str, Any]) -> None:
    if not isinstance(doc, dict):
        raise ValueError("profile must be a JSON object")
    profile_id = doc.get("profileId")
    if not isinstance(profile_id, str) or not profile_id.strip():
        raise ValueError("profileId must be a non-empty string")
    keys = doc.get("keys")
    if not isinstance(keys, list) or not keys:
        raise ValueError("keys must be a non-empty list of rows")

    if _uses_visual_v2(doc):
        _validate_profile_v2(doc)
    else:
        _validate_profile_v1(doc)


def _validate_profile_v1(doc: dict[str, Any]) -> None:
    keys = doc["keys"]
    if len(keys) != NUM_ROWS:
        raise ValueError(f"keys must be a list of {NUM_ROWS} rows")

    seen_ids: set[str] = set()
    width_by_ui_row = [0] * NUM_ROWS
    for row_i, row in enumerate(keys):
        if not isinstance(row, list):
            raise ValueError(f"row {row_i} must be a list")
        for entry in row:
            if not isinstance(entry, dict):
                raise ValueError(f"row {row_i} entries must be objects")
            key_id = entry.get("keyId")
            if not isinstance(key_id, str) or not key_id:
                raise ValueError(f"row {row_i}: keyId required")
            if key_id != SPACER_KEY_ID:
                if key_id in seen_ids:
                    raise ValueError(f"duplicate keyId: {key_id}")
                seen_ids.add(key_id)

            visual = entry.get("visual")
            visual_parts = entry.get("visualParts")
            if visual is not None and visual_parts is not None:
                raise ValueError(f"{key_id}: use visual or visualParts, not both")
            if visual_parts is not None:
                if not isinstance(visual_parts, list) or not visual_parts:
                    raise ValueError(f"{key_id}: visualParts must be a non-empty list")
                for part in visual_parts:
                    _validate_visual_part_v1(key_id, part)
                    width_by_ui_row[int(part["row"])] += int(part["w"])
            elif visual is not None:
                _validate_visual_part_v1(key_id, visual)
                vr = int(visual["row"])
                if vr != row_i:
                    raise ValueError(f"{key_id}: visual.row must match keys row index {row_i}")
                width_by_ui_row[vr] += int(visual["w"])
            else:
                raise ValueError(f"{key_id}: visual or visualParts required")

            _validate_device_cell(entry, key_id)

    for row_i, width in enumerate(width_by_ui_row):
        if width != NUM_COLS:
            raise ValueError(f"ui row {row_i} visual width must be {NUM_COLS}, got {width}")


def _validate_profile_v2(doc: dict[str, Any]) -> None:
    spec = VisualLayoutSpec.from_document(doc)
    assert spec is not None
    keys = doc["keys"]
    if len(keys) != spec.row_count:
        raise ValueError(f"keys must have {spec.row_count} rows for visual v2, got {len(keys)}")

    seen_ids: set[str] = set()
    for row_i, row in enumerate(keys):
        if not isinstance(row, list):
            raise ValueError(f"row {row_i} must be a list")
        for entry in row:
            if not isinstance(entry, dict):
                raise ValueError(f"row {row_i} entries must be objects")
            key_id = entry.get("keyId")
            if not isinstance(key_id, str) or not key_id:
                raise ValueError(f"row {row_i}: keyId required")
            if key_id == SPACER_KEY_ID:
                raise ValueError(f"{key_id}: spacers are not used in visual v2 profiles")
            if key_id in seen_ids:
                raise ValueError(f"duplicate keyId: {key_id}")
            seen_ids.add(key_id)

            if entry.get("visualHidden") is True:
                _validate_device_cell(entry, key_id)
                continue

            visual = entry.get("visual")
            visual_parts = entry.get("visualParts")
            v2 = entry.get("visualV2")
            parts_v2 = entry.get("visualPartsV2")
            legacy = visual is not None or visual_parts is not None
            modern = v2 is not None or parts_v2 is not None
            if legacy and modern:
                raise ValueError(f"{key_id}: cannot mix visual v1 and visualV2")
            if not modern:
                raise ValueError(f"{key_id}: visualV2 or visualPartsV2 required")
            if v2 is not None and parts_v2 is not None:
                raise ValueError(f"{key_id}: use visualV2 or visualPartsV2, not both")
            if parts_v2 is not None:
                if not isinstance(parts_v2, list) or not parts_v2:
                    raise ValueError(f"{key_id}: visualPartsV2 must be a non-empty list")
                for part in parts_v2:
                    _validate_visual_part_v2(key_id, part)
            elif v2 is not None:
                _validate_visual_part_v2(key_id, v2)

            _validate_device_cell(entry, key_id)

    overlaps = find_overlaps(collect_visual_rects(doc))
    if overlaps:
        raise ValueError(overlaps[0])


def _validate_device_cell(entry: dict[str, Any], key_id: str) -> None:
    if _is_spacer(entry):
        if entry.get("deviceCell") is not None:
            raise ValueError(f"{key_id}: spacer must not have deviceCell")
        return
    cell = entry.get("deviceCell")
    if not isinstance(cell, dict):
        raise ValueError(f"{key_id}: deviceCell required")
    dr = int(cell["row"])
    dc = int(cell["col"])
    if not (0 <= dr < NUM_ROWS and 0 <= dc < NUM_COLS):
        raise ValueError(f"{key_id}: deviceCell out of range")


def _validate_visual_part_v1(key_id: str, part: Any) -> None:
    if not isinstance(part, dict):
        raise ValueError(f"{key_id}: visual part must be an object")
    for field in ("row", "x", "w", "h"):
        if field not in part:
            raise ValueError(f"{key_id}: visual part missing {field}")
    ui_row = int(part["row"])
    if not 0 <= ui_row < NUM_ROWS:
        raise ValueError(f"{key_id}: visual row out of range")
    w = int(part["w"])
    if w < 1:
        raise ValueError(f"{key_id}: visual w must be >= 1")


def _validate_visual_part_v2(key_id: str, part: Any) -> None:
    if not isinstance(part, dict):
        raise ValueError(f"{key_id}: visual part must be an object")
    for field in ("x", "y", "w", "h"):
        if field not in part:
            raise ValueError(f"{key_id}: visualV2 missing {field}")
    w = float(part["w"])
    h = float(part["h"])
    if w <= 0 or h <= 0:
        raise ValueError(f"{key_id}: visualV2 w and h must be > 0")
    spec_row = part.get("row")
    if spec_row is not None:
        y = float(part["y"])
        if int(spec_row) != int(y):
            raise ValueError(f"{key_id}: visualV2 row must match y")
