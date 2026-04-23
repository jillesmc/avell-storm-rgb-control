"""Per-key matrix helpers: semantic key IDs and GUI/device row mapping.

The USB protocol uses ``row`` in ``set_key_colors`` the same way as upstream
``ite8291r3-ctl`` (see ``screen_mode``: ``color_map[(row, col)] = im.getpixel((col, 5 - row))``).
Hardware row ``0`` is the bottom row of the keyboard; row ``NUM_ROWS - 1`` is the top
(number / function area). The GUI shows row ``0`` at the top, so rows are flipped when
talking to the device.
"""

from __future__ import annotations

from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS


def _layout_rows() -> list[list[tuple[str, str, int]]]:
    # key_id, label, width_units; each row sums to NUM_COLS (21).
    return [
        [
            ("esc", "Esc", 1),
            ("f1", "F1", 1),
            ("f2", "F2", 1),
            ("f3", "F3", 1),
            ("f4", "F4", 1),
            ("f5", "F5", 1),
            ("f6", "F6", 1),
            ("f7", "F7", 1),
            ("f8", "F8", 1),
            ("f9", "F9", 1),
            ("f10", "F10", 1),
            ("f11", "F11", 1),
            ("f12", "F12", 1),
            ("prtsc", "PrtSc", 1),
            ("scrlk", "ScrLk", 1),
            ("pause", "Pause", 1),
            ("mute", "Mute", 1),
            ("vol_down", "Vol-", 1),
            ("vol_up", "Vol+", 1),
            ("kp_div", "N/", 1),
            ("kp_mul", "N*", 1),
        ],
        [
            ("grave", "`", 1),
            ("digit_1", "1", 1),
            ("digit_2", "2", 1),
            ("digit_3", "3", 1),
            ("digit_4", "4", 1),
            ("digit_5", "5", 1),
            ("digit_6", "6", 1),
            ("digit_7", "7", 1),
            ("digit_8", "8", 1),
            ("digit_9", "9", 1),
            ("digit_0", "0", 1),
            ("minus", "-", 1),
            ("equal", "=", 1),
            ("backspace", "Backspace", 2),
            ("insert", "Ins", 1),
            ("home", "Home", 1),
            ("page_up", "PgUp", 1),
            ("num_lock", "NumLk", 1),
            ("kp_7", "N7", 1),
            ("kp_8", "N8", 1),
        ],
        [
            ("tab", "Tab", 2),
            ("q", "Q", 1),
            ("w", "W", 1),
            ("e", "E", 1),
            ("r", "R", 1),
            ("t", "T", 1),
            ("y", "Y", 1),
            ("u", "U", 1),
            ("i", "I", 1),
            ("o", "O", 1),
            ("p", "P", 1),
            ("bracket_left", "[", 1),
            ("bracket_right", "]", 1),
            ("backslash", "\\", 2),
            ("delete", "Del", 1),
            ("end", "End", 1),
            ("page_down", "PgDn", 1),
            ("kp_9", "N9", 1),
            ("kp_minus", "N-", 1),
        ],
        [
            ("caps_lock", "Caps", 2),
            ("a", "A", 1),
            ("s", "S", 1),
            ("d", "D", 1),
            ("f", "F", 1),
            ("g", "G", 1),
            ("h", "H", 1),
            ("j", "J", 1),
            ("k", "K", 1),
            ("l", "L", 1),
            ("semicolon", ";", 1),
            ("quote", "'", 1),
            ("enter", "Enter", 3),
            ("kp_4", "N4", 1),
            ("kp_5", "N5", 1),
            ("kp_6", "N6", 1),
            ("kp_plus", "N+", 2),
        ],
        [
            ("shift_left", "Shift", 3),
            ("z", "Z", 1),
            ("x", "X", 1),
            ("c", "C", 1),
            ("v", "V", 1),
            ("b", "B", 1),
            ("n", "N", 1),
            ("m", "M", 1),
            ("comma", ",", 1),
            ("dot", ".", 1),
            ("slash", "/", 1),
            ("shift_right", "Shift", 3),
            ("up", "Up", 1),
            ("kp_1", "N1", 1),
            ("kp_2", "N2", 1),
            ("kp_3", "N3", 1),
            ("kp_enter_top", "NEnt", 1),
        ],
        [
            ("ctrl_left", "Ctrl", 1),
            ("meta_left", "Meta", 1),
            ("alt_left", "Alt", 1),
            ("space", "Space", 7),
            ("alt_right", "AltGr", 1),
            ("fn", "Fn", 1),
            ("menu", "Menu", 1),
            ("ctrl_right", "Ctrl", 1),
            ("left", "Left", 1),
            ("down", "Down", 1),
            ("right", "Right", 1),
            ("kp_0", "N0", 2),
            ("kp_dot", "N.", 1),
            ("app", "App", 1),
        ],
    ]


def _build_layout_keys() -> list[dict[str, int | str]]:
    # Fine-tune where each semantic key writes in the 6x21 LED matrix.
    # Value is absolute LED column in the row.
    led_col_overrides: dict[str, int] = {
        "backspace": 14,
        "tab": 1,
        "backslash": 14,
        "caps_lock": 1,
        "enter": 13,
        "shift_left": 1,
        "shift_right": 13,
        "space": 6,
        "kp_0": 18,
    }
    keys: list[dict[str, int | str]] = []
    for row_i, row in enumerate(_layout_rows()):
        x = 0
        for key_id, label, w in row:
            led_col = led_col_overrides.get(key_id, x + (w - 1) // 2)
            keys.append({
                "keyId": key_id,
                "label": label,
                "row": row_i,
                "col": led_col,
                "x": x,
                "y": row_i,
                "w": w,
                "h": 1,
            })
            x += w
        if x != NUM_COLS:
            raise ValueError(f"layout row {row_i} width must be {NUM_COLS}, got {x}")
    return keys


KEY_LAYOUT_KEYS: list[dict[str, int | str]] = _build_layout_keys()
KEY_ID_TO_UI_CELL: dict[str, tuple[int, int]] = {
    str(k["keyId"]): (int(k["row"]), int(k["col"])) for k in KEY_LAYOUT_KEYS
}


def ui_row_to_device_row(ui_row: int) -> int:
    if not 0 <= ui_row < NUM_ROWS:
        raise ValueError(f"ui_row must be in 0..{NUM_ROWS - 1}, got {ui_row}")
    return NUM_ROWS - 1 - ui_row


def color_map_ui_to_device(
    ui_map: dict[tuple[int, int], tuple[int, int, int]],
) -> dict[tuple[int, int], tuple[int, int, int]]:
    """Translate (ui_row, col) keys to (device_row, col) for ``Ite8291UsbDevice.set_key_colors``."""

    return {(ui_row_to_device_row(r), c): rgb for (r, c), rgb in ui_map.items()}


def key_id_to_ui_cell(key_id: str) -> tuple[int, int]:
    if key_id not in KEY_ID_TO_UI_CELL:
        raise ValueError(f"unknown key id: {key_id}")
    return KEY_ID_TO_UI_CELL[key_id]
