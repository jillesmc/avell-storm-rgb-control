"""Physical key → keyId mapping for calibration capture."""

from __future__ import annotations

from PySide6.QtCore import Qt

from avell_storm_rgb.domain.per_key_grid import set_active_profile
from avell_storm_rgb.domain.physical_key_map import (
    has_disallowed_modifiers,
    qt_input_to_key_id,
)


def test_letter_maps_without_modifiers() -> None:
    key_id, err = qt_input_to_key_id(int(Qt.Key.Key_Q), 0)
    assert err is None
    assert key_id == "q"


def test_rejects_shift_modifier() -> None:
    mods = Qt.KeyboardModifier.ShiftModifier.value
    key_id, err = qt_input_to_key_id(int(Qt.Key.Key_Q), mods)
    assert key_id is None
    assert err == "modifier"
    assert has_disallowed_modifiers(mods)


def test_numpad_digit_uses_keypad_modifier() -> None:
    mods = Qt.KeyboardModifier.KeypadModifier.value
    key_id, err = qt_input_to_key_id(int(Qt.Key.Key_7), mods)
    assert err is None
    assert key_id == "kp_7"


def test_main_digit_without_keypad_modifier() -> None:
    key_id, err = qt_input_to_key_id(int(Qt.Key.Key_7), 0)
    assert err is None
    assert key_id == "digit_7"


def test_f_key_and_esc() -> None:
    assert qt_input_to_key_id(int(Qt.Key.Key_F1), 0)[0] == "f1"
    assert qt_input_to_key_id(int(Qt.Key.Key_Escape), 0)[0] == "esc"


def test_scancode_maps_scroll_lock() -> None:
    key_id, err = qt_input_to_key_id(0, 0, 70)
    assert err is None
    assert key_id == "scrlk"


def test_scancode_maps_print_screen() -> None:
    assert qt_input_to_key_id(0, 0, 183)[0] == "prtsc"
    assert qt_input_to_key_id(0, 0, 99)[0] == "prtsc"


def test_unknown_key_returns_error() -> None:
    key_id, err = qt_input_to_key_id(int(Qt.Key.Key_Launch0), 0)
    assert key_id is None
    assert err == "unknown"


def test_abnt2_tilde_maps_to_semicolon() -> None:
    set_active_profile("abnt2_laptop_21")
    key_id, err = qt_input_to_key_id(int(Qt.Key.Key_Apostrophe), 0)
    assert err is None
    assert key_id == "semicolon"


def test_abnt2_cedilla_position_maps_from_semicolon_key() -> None:
    set_active_profile("abnt2_laptop_21")
    key_id, err = qt_input_to_key_id(int(Qt.Key.Key_Semicolon), 0)
    assert err is None
    assert key_id == "cedilla"


def test_abnt2_bracket_trio_rotates_us_scancodes() -> None:
    set_active_profile("abnt2_laptop_21")
    assert qt_input_to_key_id(int(Qt.Key.Key_BracketRight), 0)[0] == "bracket_square"
    assert qt_input_to_key_id(int(Qt.Key.Key_Backslash), 0)[0] == "bracket_right"
    assert qt_input_to_key_id(int(Qt.Key.Key_Asterisk), 0)[0] == "backslash"
