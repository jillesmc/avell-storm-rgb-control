#!/usr/bin/env python3
"""Regenerate abnt2_laptop_21.json with visualV2 geometry."""

from __future__ import annotations

import json
from pathlib import Path

from avell_storm_rgb.domain.keyboard_layouts.abnt2_v2_layout import (
    LAYOUT_LABEL_OVERRIDES,
    SPEC,
    build_abnt2_placements,
    parts_to_visual_parts_v2,
    rect_to_visual_v2,
)
from avell_storm_rgb.domain.keyboard_layouts.schema import validate_profile_document

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "src/avell_storm_rgb/domain/keyboard_layouts/profiles/abnt2_laptop_21.json"
LEGACY = ROOT / "src/avell_storm_rgb/domain/keyboard_layouts/profiles/legacy_builtin.json"
VISUAL_HIDDEN = ("app",)
VISUAL_SHAPES = {"enter": "isoEnter"}
# ABNT2 row: L | Ç | ~ — Ç uses legacy ``semicolon`` LED, ~ uses legacy ``quote``.
# ABNT2 row P/L: ´ | [ | ] — [ uses legacy ``]`` LED, ] uses legacy ``\\`` LED.
DEVICE_CELL_OVERRIDES = {
    "cedilla": {"row": 2, "col": 11},
    "semicolon": {"row": 2, "col": 12},
    "bracket_square": {"row": 3, "col": 13},
    "bracket_right": {"row": 3, "col": 14},
}


def main() -> None:
    doc = json.loads(PROFILE.read_text(encoding="utf-8"))
    meta: dict[str, dict] = {}
    for row in doc["keys"]:
        for entry in row:
            kid = entry["keyId"]
            if kid == "_spacer":
                continue
            meta[kid] = {
                "label": entry.get("label", ""),
                "secondaryLabel": entry.get("secondaryLabel", ""),
                "deviceCell": entry["deviceCell"],
            }

    legacy_doc = json.loads(LEGACY.read_text(encoding="utf-8"))
    for row in legacy_doc["keys"]:
        for entry in row:
            kid = entry["keyId"]
            if kid == "_spacer" or kid in meta:
                continue
            meta[kid] = {
                "label": entry.get("label", ""),
                "secondaryLabel": entry.get("secondaryLabel", ""),
                "deviceCell": dict(entry["deviceCell"]),
            }

    for row in legacy_doc["keys"]:
        for entry in row:
            if entry["keyId"] == "bracket_right":
                meta["bracket_square"] = {
                    "label": "[",
                    "secondaryLabel": "{ª",
                    "deviceCell": dict(entry["deviceCell"]),
                }
                break

    simple, parts = build_abnt2_placements()

    for key_id, labels in LAYOUT_LABEL_OVERRIDES.items():
        if key_id in meta:
            meta[key_id].update(labels)

    for key_id, cell in DEVICE_CELL_OVERRIDES.items():
        if key_id in meta:
            meta[key_id]["deviceCell"] = dict(cell)

    rows: list[list[dict]] = [[] for _ in range(SPEC.row_count)]
    placed_ids: set[str] = set()

    def add_key(key_id: str, payload: dict) -> None:
        if key_id not in meta:
            raise KeyError(f"missing metadata for {key_id}")
        y = int(payload.get("visualV2", payload.get("visualPartsV2", [{}])[0])["y"])
        rows[y].append({
            "keyId": key_id,
            "label": meta[key_id]["label"],
            "secondaryLabel": meta[key_id]["secondaryLabel"],
            "deviceCell": meta[key_id]["deviceCell"],
            **payload,
        })
        placed_ids.add(key_id)

    for key_id, rect in sorted(simple.items()):
        add_key(key_id, {"visualV2": rect_to_visual_v2(rect)})

    for key_id, rects in sorted(parts.items()):
        payload: dict = {"visualPartsV2": parts_to_visual_parts_v2(rects)}
        if key_id in VISUAL_SHAPES:
            payload["visualShape"] = VISUAL_SHAPES[key_id]
        add_key(key_id, payload)

    for key_id in VISUAL_HIDDEN:
        if key_id not in meta:
            continue
        hidden_label = "App" if key_id == "app" else meta[key_id]["label"]
        rows[SPEC.row_count - 1].append({
            "keyId": key_id,
            "label": hidden_label,
            "secondaryLabel": meta[key_id]["secondaryLabel"],
            "deviceCell": meta[key_id]["deviceCell"],
            "visualHidden": True,
        })

    def _sort_x(entry: dict) -> float:
        if entry.get("visualHidden"):
            return 999.0
        if "visualV2" in entry:
            return float(entry["visualV2"]["x"])
        return float(entry["visualPartsV2"][0]["x"])

    for row in rows:
        row.sort(key=_sort_x)

    out = {
        "profileId": doc["profileId"],
        "description": "ABNT2 Avell Storm — visual v2 fractional layout",
        "visualLayout": {
            "version": 2,
            "keyGap": SPEC.key_gap,
            "wideGap": SPEC.wide_gap,
            "rowCount": SPEC.row_count,
        },
        "keys": rows,
    }
    validate_profile_document(out)
    PROFILE.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {PROFILE} ({sum(len(r) for r in rows)} keys, {len(rows)} rows)")


if __name__ == "__main__":
    main()
