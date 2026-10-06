"""CLI helpers for keyboard layout profiles and LED probe."""

from __future__ import annotations

import json
import sys
from typing import TextIO

from avell_storm_rgb.domain.keyboard_layouts import list_profile_ids, load_profile
from avell_storm_rgb.domain.per_key_grid import set_active_profile
from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS


def cmd_layout_list() -> int:
    for profile_id in list_profile_ids():
        print(profile_id)
    return 0


def cmd_layout_set(profile_id: str) -> int:
    load_profile(profile_id)
    set_active_profile(profile_id)
    print(f"active layout profile: {profile_id}")
    return 0


def cmd_layout_probe(
    device,
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    prompt_stream: TextIO | None = None,
) -> int:
    """Walk device cells (row 5→0, col 0→20); build keyId→deviceCell map on stdout."""

    inp = input_stream or sys.stdin
    out = output_stream or sys.stdout
    prompts = prompt_stream or sys.stderr
    mapping: dict[str, list[int]] = {}

    for device_row in range(NUM_ROWS - 1, -1, -1):
        for col in range(NUM_COLS):
            device.set_key_colors(
                {(device_row, col): (255, 255, 255)},
                enable_user_mode_flag=True,
            )
            prompts.write(f"Cell device row={device_row} col={col}\n")
            prompts.flush()
            try:
                line = inp.readline().strip()
            except (EOFError, KeyboardInterrupt):
                line = ""
            if not line:
                continue
            if line.lower() in {"skip", "s", "."}:
                continue
            if line in mapping:
                out.write(f"warning: overwriting {line!r}\n", file=sys.stderr)
            mapping[line] = [device_row, col]

    device.set_key_colors({}, enable_user_mode_flag=True)
    out.write(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    return 0
