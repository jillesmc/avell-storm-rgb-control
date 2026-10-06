"""Evdev device path discovery fallback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.core.calibration_evdev_capture import (
    _discover_device_paths,
    _is_internal_keyboard,
    _select_calibration_devices,
    evdev_available,
)

pytestmark = pytest.mark.skipif(not evdev_available(), reason="evdev not installed")


def test_discover_falls_back_to_glob_when_list_devices_empty() -> None:
    with patch("app.core.calibration_evdev_capture.evdev.list_devices", return_value=[]):
        with patch(
            "app.core.calibration_evdev_capture.glob.glob",
            return_value=["/dev/input/event3", "/dev/input/event4"],
        ):
            assert _discover_device_paths() == ["/dev/input/event3", "/dev/input/event4"]


def test_is_internal_keyboard_detects_ps2_laptop() -> None:
    device = MagicMock()
    device.phys = "isa0060/serio0/input0"
    device.name = "AT Translated Set 2 keyboard"
    assert _is_internal_keyboard(device) is True


def test_is_internal_keyboard_rejects_usb_external() -> None:
    device = MagicMock()
    device.phys = "usb-0000:80:14.0-3/input0"
    device.name = "MX Keys Keyboard"
    assert _is_internal_keyboard(device) is False


def test_select_calibration_devices_prefers_internal() -> None:
    internal = MagicMock()
    internal.phys = "isa0060/serio0/input0"
    internal.name = "AT Translated Set 2 keyboard"
    external = MagicMock()
    external.phys = "usb-0000:80:14.0-3/input0"
    external.name = "MX Keys Keyboard"
    assert _select_calibration_devices([external, internal]) == [internal]


def test_select_calibration_devices_keeps_all_when_no_internal() -> None:
    external_a = MagicMock()
    external_a.phys = "usb-0000:80:14.0-3/input0"
    external_b = MagicMock()
    external_b.phys = "20:bd:1d:c8:7a:7f"
    devices = [external_a, external_b]
    assert _select_calibration_devices(devices) == devices
