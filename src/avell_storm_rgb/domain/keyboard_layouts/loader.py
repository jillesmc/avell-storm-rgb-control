"""Load keyboard layout profiles from packaged JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from avell_storm_rgb.domain.keyboard_layouts.schema import SPACER_KEY_ID, validate_profile_document
from avell_storm_rgb.domain.keyboard_layouts.visual_geometry import (
    VisualLayoutSpec,
    collect_visual_rects,
    layout_bounds,
)
from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS

_PACKAGE = "avell_storm_rgb.domain.keyboard_layouts"


@dataclass(frozen=True)
class LoadedProfile:
    profile_id: str
    key_layout_keys: list[dict[str, int | str | list | float | bool]]
    key_id_to_ui_cell: dict[str, tuple[int, int]]
    base_key_to_device_cell: dict[str, tuple[int, int]]
    duplicate_device_cells: dict[tuple[int, int], list[str]] = field(default_factory=dict)
    visual_layout: VisualLayoutSpec | None = None
    layout_bounds_u: tuple[float, float, float, float] | None = None


def profile_path(profile_id: str) -> Path:
    ref = resources.files(_PACKAGE).joinpath("profiles", f"{profile_id}.json")
    return Path(ref)


def list_profile_ids() -> list[str]:
    root = resources.files(_PACKAGE).joinpath("profiles")
    out: list[str] = []
    for entry in root.iterdir():
        if entry.name.endswith(".json"):
            out.append(entry.name[: -len(".json")])
    return sorted(out)


def load_profile(profile_id: str) -> LoadedProfile:
    path = profile_path(profile_id)
    if not path.is_file():
        raise FileNotFoundError(f"unknown layout profile: {profile_id}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    validate_profile_document(doc)
    return _build_loaded_profile(doc)


def load_profile_document(doc: dict[str, Any]) -> LoadedProfile:
    validate_profile_document(doc)
    return _build_loaded_profile(doc)


def resolve_usb_default_profile(product_id: int) -> str:
    ref = resources.files(_PACKAGE).joinpath("usb_defaults.json")
    data = json.loads(ref.read_text(encoding="utf-8"))
    by_pid = data.get("by_product_id", {})
    key = f"{product_id:04X}"
    if key in by_pid:
        return str(by_pid[key])
    return str(data.get("default", "legacy_builtin"))


def _part_dict_v2(part: dict[str, Any]) -> dict[str, float]:
    return {
        "xU": float(part["x"]),
        "yU": float(part["y"]),
        "wU": float(part["w"]),
        "hU": float(part["h"]),
        "x": float(part["x"]),
        "y": float(part["y"]),
        "w": float(part["w"]),
        "h": float(part["h"]),
    }


def _build_loaded_profile(doc: dict[str, Any]) -> LoadedProfile:
    profile_id = str(doc["profileId"])
    spec = VisualLayoutSpec.from_document(doc)
    keys_flat: list[dict[str, int | str | list | float | bool]] = []
    key_id_to_ui: dict[str, tuple[int, int]] = {}
    base_device: dict[str, tuple[int, int]] = {}
    by_cell: dict[tuple[int, int], list[str]] = {}

    if spec is not None:
        keys_flat, key_id_to_ui, base_device, by_cell = _flatten_v2(doc, spec)
        bounds = layout_bounds(collect_visual_rects(doc))
        duplicates = {c: ids for c, ids in by_cell.items() if len(ids) > 1}
        return LoadedProfile(
            profile_id=profile_id,
            key_layout_keys=keys_flat,
            key_id_to_ui_cell=key_id_to_ui,
            base_key_to_device_cell=base_device,
            duplicate_device_cells=duplicates,
            visual_layout=spec,
            layout_bounds_u=bounds,
        )

    keys_flat, key_id_to_ui, base_device, by_cell = _flatten_v1(doc)
    duplicates = {c: ids for c, ids in by_cell.items() if len(ids) > 1}
    return LoadedProfile(
        profile_id=profile_id,
        key_layout_keys=keys_flat,
        key_id_to_ui_cell=key_id_to_ui,
        base_key_to_device_cell=base_device,
        duplicate_device_cells=duplicates,
    )


def _flatten_v2(
    doc: dict[str, Any],
    spec: VisualLayoutSpec,
) -> tuple[
    list[dict[str, int | str | list | float | bool]],
    dict[str, tuple[int, int]],
    dict[str, tuple[int, int]],
    dict[tuple[int, int], list[str]],
]:
    keys_flat: list[dict[str, int | str | list | float | bool]] = []
    key_id_to_ui: dict[str, tuple[int, int]] = {}
    base_device: dict[str, tuple[int, int]] = {}
    by_cell: dict[tuple[int, int], list[str]] = {}

    for row in doc["keys"]:
        for entry in row:
            key_id = str(entry["keyId"])
            label = str(entry.get("label", ""))
            secondary = str(entry.get("secondaryLabel", ""))
            cell = entry["deviceCell"]
            dev_row, dev_col = int(cell["row"]), int(cell["col"])
            base_device[key_id] = (dev_row, dev_col)
            by_cell.setdefault((dev_row, dev_col), []).append(key_id)

            if entry.get("visualHidden") is True:
                continue

            parts_v2 = entry.get("visualPartsV2")
            v2 = entry.get("visualV2")
            visual_shape = entry.get("visualShape")

            if parts_v2 is not None:
                visual_parts = [_part_dict_v2(p) for p in parts_v2]
                anchor = visual_parts[0]
                flat: dict[str, int | str | list | float | bool] = {
                    "keyId": key_id,
                    "label": label,
                    "secondaryLabel": secondary,
                    "row": int(anchor["yU"]),
                    "col": dev_col,
                    "xU": anchor["xU"],
                    "yU": anchor["yU"],
                    "wU": anchor["wU"],
                    "hU": anchor["hU"],
                    "visualVersion": 2,
                    "visualParts": visual_parts,
                }
                if isinstance(visual_shape, str) and visual_shape:
                    flat["visualShape"] = visual_shape
                keys_flat.append(flat)
            else:
                assert v2 is not None
                part = _part_dict_v2(v2)
                flat = {
                    "keyId": key_id,
                    "label": label,
                    "secondaryLabel": secondary,
                    "row": int(part["yU"]),
                    "col": dev_col,
                    "xU": part["xU"],
                    "yU": part["yU"],
                    "wU": part["wU"],
                    "hU": part["hU"],
                    "visualVersion": 2,
                }
                if isinstance(visual_shape, str) and visual_shape:
                    flat["visualShape"] = visual_shape
                keys_flat.append(flat)

            anchor_y = int(keys_flat[-1]["yU"])  # type: ignore[arg-type]
            key_id_to_ui[key_id] = (anchor_y, dev_col)

    return keys_flat, key_id_to_ui, base_device, by_cell


def _flatten_v1(
    doc: dict[str, Any],
) -> tuple[
    list[dict[str, int | str | list | float | bool]],
    dict[str, tuple[int, int]],
    dict[str, tuple[int, int]],
    dict[tuple[int, int], list[str]],
]:
    keys_flat: list[dict[str, int | str | list | float | bool]] = []
    key_id_to_ui: dict[str, tuple[int, int]] = {}
    base_device: dict[str, tuple[int, int]] = {}
    by_cell: dict[tuple[int, int], list[str]] = {}

    for row in doc["keys"]:
        for entry in row:
            key_id = str(entry["keyId"])
            if key_id == SPACER_KEY_ID:
                visual = entry["visual"]
                keys_flat.append({
                    "keyId": key_id,
                    "label": "",
                    "secondaryLabel": "",
                    "row": int(visual["row"]),
                    "col": int(visual["x"]),
                    "x": int(visual["x"]),
                    "y": int(visual["row"]),
                    "w": int(visual["w"]),
                    "h": int(visual["h"]),
                    "isSpacer": True,
                })
                continue

            label = str(entry.get("label", ""))
            secondary = str(entry.get("secondaryLabel", ""))
            cell = entry["deviceCell"]
            dev_row, dev_col = int(cell["row"]), int(cell["col"])
            parts = entry.get("visualParts")
            if parts is not None:
                visual_parts: list[dict[str, int | float]] = []
                ui_row = int(parts[0]["row"])
                x0 = int(parts[0]["x"])
                for part in parts:
                    ui_part_row = int(part["row"])
                    visual_parts.append({
                        "row": ui_part_row,
                        "x": int(part["x"]),
                        "y": ui_part_row,
                        "w": int(part["w"]),
                        "h": int(part["h"]),
                    })
                keys_flat.append({
                    "keyId": key_id,
                    "label": label,
                    "secondaryLabel": secondary,
                    "row": ui_row,
                    "col": dev_col,
                    "x": x0,
                    "y": ui_row,
                    "w": int(parts[0]["w"]),
                    "h": int(parts[0]["h"]),
                    "visualParts": visual_parts,
                })
            else:
                visual = entry["visual"]
                ui_row = int(visual["row"])
                keys_flat.append({
                    "keyId": key_id,
                    "label": label,
                    "secondaryLabel": secondary,
                    "row": ui_row,
                    "col": dev_col,
                    "x": int(visual["x"]),
                    "y": ui_row,
                    "w": int(visual["w"]),
                    "h": int(visual["h"]),
                })

            ui_row = int(keys_flat[-1]["row"])  # type: ignore[arg-type]
            key_id_to_ui[key_id] = (ui_row, dev_col)
            base_device[key_id] = (dev_row, dev_col)
            by_cell.setdefault((dev_row, dev_col), []).append(key_id)

    return keys_flat, key_id_to_ui, base_device, by_cell
