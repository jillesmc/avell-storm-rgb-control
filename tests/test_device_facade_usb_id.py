"""device_facade: open devices by USB id (UT-020–UT-022)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from avell_storm_rgb.application import device_facade as f


def _dev(vid: int, pid: int, bus: int, addr: int) -> SimpleNamespace:
    return SimpleNamespace(idVendor=vid, idProduct=pid, bus=bus, address=addr)


def test_ut020_open_keyboard_by_usb_id(monkeypatch) -> None:
    opened: list = []
    monkeypatch.setattr(f, "iter_keyboard_usb_devices", lambda: [_dev(0x048D, 0x6004, 1, 2), _dev(0x048D, 0xCE00, 3, 9)])
    monkeypatch.setattr(f, "open_ite8291_device", lambda loc, debug=False: opened.append(loc) or "kb")
    assert f.open_keyboard(usb_id="048d:ce00") == "kb"
    assert opened == [(3, 9)]


def test_ut021_open_led_bar_first_match(monkeypatch) -> None:
    first, second = _dev(0x048D, 0x7001, 1, 4), _dev(0x048D, 0x7001, 1, 5)
    monkeypatch.setattr(f, "iter_led_bar_usb_devices", lambda: [first, second])
    monkeypatch.setattr(f, "Ite8233UsbDevice", lambda device: ("bar", device))
    assert f.open_led_bar(usb_id="048d:7001") == ("bar", first)


def test_ut022_no_match_errors(monkeypatch) -> None:
    monkeypatch.setattr(f, "iter_keyboard_usb_devices", lambda: [_dev(0x048D, 0xCE00, 3, 9)])
    monkeypatch.setattr(f, "iter_led_bar_usb_devices", lambda: [])
    with pytest.raises(FileNotFoundError, match="no suitable device found"):
        f.open_keyboard(usb_id="048d:6004")
    with pytest.raises(RuntimeError, match="No ITE 8233 LED bar found."):
        f.open_led_bar(usb_id="048d:7001")


def test_usb_id_of_is_lowercase_hex() -> None:
    assert f.usb_id_of(_dev(0x048D, 0xCE00, 0, 0)) == "048d:ce00"
