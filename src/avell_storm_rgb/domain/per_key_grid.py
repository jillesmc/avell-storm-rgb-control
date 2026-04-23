"""Per-key matrix: GUI vs ITE8291 row indices.

The USB protocol uses ``row`` in ``set_key_colors`` the same way as upstream
``ite8291r3-ctl`` (see ``screen_mode``: ``color_map[(row, col)] = im.getpixel((col, 5 - row))``).
Hardware row ``0`` is the bottom row of the keyboard; row ``NUM_ROWS - 1`` is the top
(number / function area). The GUI grid shows row ``0`` at the top, so we flip rows when
talking to the device.
"""

from __future__ import annotations

from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS


def ui_row_to_device_row(ui_row: int) -> int:
    if not 0 <= ui_row < NUM_ROWS:
        raise ValueError(f"ui_row must be in 0..{NUM_ROWS - 1}, got {ui_row}")
    return NUM_ROWS - 1 - ui_row


def color_map_ui_to_device(
    ui_map: dict[tuple[int, int], tuple[int, int, int]],
) -> dict[tuple[int, int], tuple[int, int, int]]:
    """Translate (ui_row, col) keys to (device_row, col) for ``Ite8291UsbDevice.set_key_colors``."""

    return {(ui_row_to_device_row(r), c): rgb for (r, c), rgb in ui_map.items()}
