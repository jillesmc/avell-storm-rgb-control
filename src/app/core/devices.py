"""Structured USB device listing for the GUI."""

from __future__ import annotations

import usb.core

from avell_storm_rgb.infrastructure.usb.ite8233_usb import Ite8233UsbDevice
from avell_storm_rgb.infrastructure.usb.discovery import (
    iter_keyboard_usb_devices,
    iter_led_bar_usb_devices,
)


def enumerate_usb_devices() -> list[dict[str, str | int]]:
    items: list[dict[str, str | int]] = []
    for dev in iter_keyboard_usb_devices():
        items.append(_keyboard_entry(dev))
    for dev in iter_led_bar_usb_devices():
        items.append(_led_entry(dev))
    return items


def _keyboard_entry(dev: usb.core.Device) -> dict[str, str | int]:
    return {
        "kind": "keyboard",
        "bus": int(dev.bus),
        "addr": int(dev.address),
        "vid": int(dev.idVendor),
        "pid": int(dev.idProduct),
        "label": f"Keyboard {dev.idVendor:04x}:{dev.idProduct:04x}  bus {dev.bus}  addr {dev.address}",
    }


def _led_entry(dev: usb.core.Device) -> dict[str, str | int]:
    return {
        "kind": "led_bar",
        "bus": int(dev.bus),
        "addr": int(dev.address),
        "vid": int(dev.idVendor),
        "pid": int(dev.idProduct),
        "label": f"LED bar {dev.idVendor:04x}:{dev.idProduct:04x}  bus {dev.bus}  addr {dev.address}",
    }


def open_led_bar_at(bus: int, addr: int) -> Ite8233UsbDevice:
    dev = usb.core.find(bus=bus, address=addr)
    if dev is None:
        raise RuntimeError(f"No USB device at bus {bus} addr {addr}")
    return Ite8233UsbDevice(device=dev)
