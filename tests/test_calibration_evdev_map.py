"""Evdev key map for calibration capture."""

from __future__ import annotations

import pytest

from app.core.calibration_evdev_capture import evdev_available, evdev_code_to_key_id

pytestmark = pytest.mark.skipif(not evdev_available(), reason="evdev not installed")


def test_evdev_maps_scroll_lock_and_print() -> None:
    from evdev import ecodes

    assert evdev_code_to_key_id(ecodes.KEY_SCROLLLOCK) == "scrlk"
    assert evdev_code_to_key_id(ecodes.KEY_PRINT) == "prtsc"
    assert evdev_code_to_key_id(ecodes.KEY_SYSRQ) == "prtsc"


def test_evdev_maps_letter_q() -> None:
    from evdev import ecodes

    assert evdev_code_to_key_id(ecodes.KEY_Q) == "q"


def test_evdev_abnt2_bracket_trio_rotates_us_scancodes() -> None:
    from evdev import ecodes

    from avell_storm_rgb.domain.per_key_grid import set_active_profile

    set_active_profile("abnt2_laptop_21")
    assert evdev_code_to_key_id(ecodes.KEY_RIGHTBRACE) == "bracket_square"
    assert evdev_code_to_key_id(ecodes.KEY_BACKSLASH) == "bracket_right"
    assert evdev_code_to_key_id(ecodes.KEY_102ND) == "backslash"
