"""USB discovery helpers."""

from __future__ import annotations

import usb.core
import usb.util

from avell_storm_rgb.infrastructure.usb.ite8233_usb import (
    KNOWN_PRODUCT_IDS,
    VENDOR_ID as LED_VENDOR,
    Ite8233UsbDevice,
)
from avell_storm_rgb.infrastructure.usb.ite8291_usb import open_ite8291_device

__all__ = [
    "open_ite8291_device",
    "iter_keyboard_usb_devices",
    "iter_led_bar_usb_devices",
    "find_led_bar_device",
]


def iter_keyboard_usb_devices():
    from avell_storm_rgb.infrastructure.usb.ite8291_usb import iter_keyboard_usb_devices as _iter

    return _iter()


def iter_led_bar_usb_devices():
    found: list[usb.core.Device] = []
    for dev in usb.core.find(find_all=True, idVendor=LED_VENDOR):
        if dev.idProduct in KNOWN_PRODUCT_IDS:
            found.append(dev)
            continue
        try:
            product = usb.util.get_string(dev, dev.iProduct)
            if product and "8233" in product:
                found.append(dev)
        except (usb.core.USBError, ValueError):
            pass
    return found


def find_led_bar_device() -> Ite8233UsbDevice:
    devices = iter_led_bar_usb_devices()
    if not devices:
        raise RuntimeError("No ITE 8233 LED bar found.")
    return Ite8233UsbDevice(device=devices[0])
