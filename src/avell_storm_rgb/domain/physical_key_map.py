"""Map Qt keyboard input to semantic ``keyId`` strings used by layout profiles."""

from __future__ import annotations

from PySide6.QtCore import Qt

# Modifiers allowed during calibration capture (numpad distinction only).
_DISALLOWED_MODIFIERS = (
    Qt.KeyboardModifier.ShiftModifier.value
    | Qt.KeyboardModifier.ControlModifier.value
    | Qt.KeyboardModifier.AltModifier.value
    | Qt.KeyboardModifier.MetaModifier.value
)
_KEYPAD_MODIFIER = Qt.KeyboardModifier.KeypadModifier.value

# Standard keys (main keyboard, no keypad modifier).
_QT_TO_KEY_ID: dict[int, str] = {
    Qt.Key.Key_Escape: "esc",
    Qt.Key.Key_Tab: "tab",
    Qt.Key.Key_CapsLock: "caps_lock",
    Qt.Key.Key_Return: "enter",
    Qt.Key.Key_Enter: "enter",
    Qt.Key.Key_Backspace: "backspace",
    Qt.Key.Key_Space: "space",
    Qt.Key.Key_Delete: "delete",
    Qt.Key.Key_Insert: "insert",
    Qt.Key.Key_Home: "home",
    Qt.Key.Key_End: "end",
    Qt.Key.Key_PageUp: "page_up",
    Qt.Key.Key_PageDown: "page_down",
    Qt.Key.Key_Pause: "pause",
    Qt.Key.Key_Print: "prtsc",
    Qt.Key.Key_ScrollLock: "scrlk",
    Qt.Key.Key_NumLock: "num_lock",
    Qt.Key.Key_Menu: "menu",
    Qt.Key.Key_Up: "up",
    Qt.Key.Key_Down: "down",
    Qt.Key.Key_Left: "left",
    Qt.Key.Key_Right: "right",
    Qt.Key.Key_F1: "f1",
    Qt.Key.Key_F2: "f2",
    Qt.Key.Key_F3: "f3",
    Qt.Key.Key_F4: "f4",
    Qt.Key.Key_F5: "f5",
    Qt.Key.Key_F6: "f6",
    Qt.Key.Key_F7: "f7",
    Qt.Key.Key_F8: "f8",
    Qt.Key.Key_F9: "f9",
    Qt.Key.Key_F10: "f10",
    Qt.Key.Key_F11: "f11",
    Qt.Key.Key_F12: "f12",
    Qt.Key.Key_QuoteLeft: "grave",
    Qt.Key.Key_0: "digit_0",
    Qt.Key.Key_1: "digit_1",
    Qt.Key.Key_2: "digit_2",
    Qt.Key.Key_3: "digit_3",
    Qt.Key.Key_4: "digit_4",
    Qt.Key.Key_5: "digit_5",
    Qt.Key.Key_6: "digit_6",
    Qt.Key.Key_7: "digit_7",
    Qt.Key.Key_8: "digit_8",
    Qt.Key.Key_9: "digit_9",
    Qt.Key.Key_Minus: "minus",
    Qt.Key.Key_Equal: "equal",
    Qt.Key.Key_BracketLeft: "bracket_left",
    Qt.Key.Key_BracketRight: "bracket_right",
    Qt.Key.Key_Backslash: "backslash",
    Qt.Key.Key_Semicolon: "semicolon",
    Qt.Key.Key_Apostrophe: "quote",
    Qt.Key.Key_Comma: "comma",
    Qt.Key.Key_Period: "dot",
    Qt.Key.Key_Slash: "slash",
    Qt.Key.Key_A: "a",
    Qt.Key.Key_B: "b",
    Qt.Key.Key_C: "c",
    Qt.Key.Key_D: "d",
    Qt.Key.Key_E: "e",
    Qt.Key.Key_F: "f",
    Qt.Key.Key_G: "g",
    Qt.Key.Key_H: "h",
    Qt.Key.Key_I: "i",
    Qt.Key.Key_J: "j",
    Qt.Key.Key_K: "k",
    Qt.Key.Key_L: "l",
    Qt.Key.Key_M: "m",
    Qt.Key.Key_N: "n",
    Qt.Key.Key_O: "o",
    Qt.Key.Key_P: "p",
    Qt.Key.Key_Q: "q",
    Qt.Key.Key_R: "r",
    Qt.Key.Key_S: "s",
    Qt.Key.Key_T: "t",
    Qt.Key.Key_U: "u",
    Qt.Key.Key_V: "v",
    Qt.Key.Key_W: "w",
    Qt.Key.Key_X: "x",
    Qt.Key.Key_Y: "y",
    Qt.Key.Key_Z: "z",
    Qt.Key.Key_Shift: "shift_left",
    Qt.Key.Key_Control: "ctrl_left",
    Qt.Key.Key_Alt: "alt_left",
    Qt.Key.Key_Meta: "meta_left",
    Qt.Key.Key_Super_L: "meta_left",
    Qt.Key.Key_Super_R: "meta_left",
    Qt.Key.Key_AltGr: "alt_right",
    Qt.Key.Key_Ccedilla: "cedilla",
    Qt.Key.Key_Asterisk: "bracket_square",
    Qt.Key.Key_MediaTogglePlayPause: "pause",
    Qt.Key.Key_VolumeMute: "mute",
    Qt.Key.Key_VolumeDown: "vol_down",
    Qt.Key.Key_VolumeUp: "vol_up",
}

# Linux evdev scancodes (Qt nativeScanCode) when Key_* is missing.
_SCANCODE_TO_KEY_ID: dict[int, str] = {
    54: "shift_right",
    70: "scrlk",
    97: "ctrl_right",
    99: "prtsc",
    100: "alt_right",
    125: "meta_right",
    183: "prtsc",
    57399: "fn",
}

_KEYPAD_QT_TO_KEY_ID: dict[int, str] = {
    Qt.Key.Key_0: "kp_0",
    Qt.Key.Key_1: "kp_1",
    Qt.Key.Key_2: "kp_2",
    Qt.Key.Key_3: "kp_3",
    Qt.Key.Key_4: "kp_4",
    Qt.Key.Key_5: "kp_5",
    Qt.Key.Key_6: "kp_6",
    Qt.Key.Key_7: "kp_7",
    Qt.Key.Key_8: "kp_8",
    Qt.Key.Key_9: "kp_9",
    Qt.Key.Key_Plus: "kp_plus",
    Qt.Key.Key_Minus: "kp_minus",
    Qt.Key.Key_Asterisk: "kp_mul",
    Qt.Key.Key_Slash: "kp_div",
    Qt.Key.Key_Period: "kp_dot",
    Qt.Key.Key_Enter: "kp_enter_top",
    Qt.Key.Key_Return: "kp_enter_top",
}


def _effective_modifiers(modifiers: int) -> int:
    mods = Qt.KeyboardModifier(modifiers).value
    return mods & ~_KEYPAD_MODIFIER


def has_disallowed_modifiers(modifiers: int) -> bool:
    return bool(_effective_modifiers(modifiers) & _DISALLOWED_MODIFIERS)


_ABNT2_KEY_ALIASES: dict[str, str] = {
    # Row L: Ç / ~ use legacy US ``semicolon`` / ``quote`` LED columns.
    "quote": "semicolon",
    "semicolon": "cedilla",
    # ABNT2 sends US ``]`` / ``\\`` / ``[`` scancodes for [ / ] / \\ respectively.
    "bracket_right": "bracket_square",
    "backslash": "bracket_right",
    "bracket_square": "backslash",
}


def resolve_profile_key_id(key_id: str) -> str:
    """Map generic evdev/Qt ids to profile-specific ``keyId`` strings."""

    from avell_storm_rgb.domain.per_key_grid import active_profile_id

    if active_profile_id() == "abnt2_laptop_21":
        return _ABNT2_KEY_ALIASES.get(key_id, key_id)
    return key_id


def qt_input_to_key_id(
    key: int,
    modifiers: int,
    native_scan_code: int = 0,
) -> tuple[str | None, str | None]:
    """Return ``(key_id, error_message)``. *error_message* is set when *key_id* is None."""

    if has_disallowed_modifiers(modifiers):
        return None, "modifier"

    mods = Qt.KeyboardModifier(modifiers)
    table = _KEYPAD_QT_TO_KEY_ID if mods & Qt.KeyboardModifier.KeypadModifier else _QT_TO_KEY_ID
    key_id = table.get(int(key))
    if key_id is not None:
        return resolve_profile_key_id(key_id), None

    if native_scan_code:
        scan_id = _SCANCODE_TO_KEY_ID.get(int(native_scan_code))
        if scan_id is not None:
            return resolve_profile_key_id(scan_id), None

    return None, "unknown"
