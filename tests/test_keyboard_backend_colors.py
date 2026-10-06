"""KeyboardBackend per-key colors keyed by keyId (no Qt event loop)."""

from __future__ import annotations

from avell_storm_rgb.domain.per_key_grid import set_active_profile

from app.ui.adapters.keyboard_backend import KeyboardBackend
from app.core.usb_worker import UsbWorker


def test_key_colors_stored_by_key_id() -> None:
    set_active_profile("legacy_builtin")
    worker = UsbWorker()
    kb = KeyboardBackend(worker)
    kb.setKeyById("esc", 10, 20, 30, False)
    assert kb._key_colors["esc"] == (10, 20, 30)


def test_build_device_color_map_uses_device_cells() -> None:
    set_active_profile("legacy_builtin")
    worker = UsbWorker()
    kb = KeyboardBackend(worker)
    kb.setKeyById("esc", 255, 0, 0, False)
    kb.setKeyById("f1", 0, 255, 0, False)
    dev_map = kb._build_device_color_map()
    assert dev_map[(5, 0)] == (255, 0, 0)
    assert dev_map[(5, 1)] == (0, 255, 0)


def test_build_device_color_map_uses_calibration_override() -> None:
    set_active_profile("legacy_builtin")
    worker = UsbWorker()
    kb = KeyboardBackend(worker)
    kb.setCalibrationOverride("esc", 3, 7)
    kb.setKeyById("esc", 255, 0, 0, False)
    dev_map = kb._build_device_color_map()
    assert dev_map[(3, 7)] == (255, 0, 0)
    assert (5, 0) not in dev_map


def test_key_hex_by_id_reads_key_id_colors() -> None:
    set_active_profile("legacy_builtin")
    worker = UsbWorker()
    kb = KeyboardBackend(worker)
    kb.setKeyById("space", 1, 2, 3, False)
    assert kb.keyHexById("space") == "#010203"
