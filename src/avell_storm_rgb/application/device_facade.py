"""
Stable entry points for adapters (CLI, future PySide).

USB I/O should run on a single thread or a dedicated worker queue; do not
call these from multiple threads concurrently without external locking.
"""

from __future__ import annotations

from collections.abc import Iterator

from avell_storm_rgb.infrastructure.usb.discovery import (
    find_led_bar_device,
    iter_keyboard_usb_devices,
    iter_led_bar_usb_devices,
    open_ite8291_device,
)
from avell_storm_rgb.infrastructure.usb.ite8233_usb import Ite8233UsbDevice
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice


def open_keyboard(*, bus_addr: tuple[int, int] | None = None, debug: bool = False) -> Ite8291UsbDevice:
    return open_ite8291_device(bus_addr, debug=debug)


def open_led_bar() -> Ite8233UsbDevice:
    return find_led_bar_device()


def describe_keyboard_usb_devices() -> Iterator[str]:
    """Yield human-readable lines for supported ITE8291 devices."""
    for dev in iter_keyboard_usb_devices():
        try:
            prod = repr(dev.product)
            mfr = repr(dev.manufacturer)
        except Exception:
            prod = "?"
            mfr = "?"
        yield (
            f"{dev.idVendor:04x}:{dev.idProduct:04x} "
            f"bus {dev.bus} addr {dev.address} "
            f"rev {dev.bcdDevice >> 8:x}.{(dev.bcdDevice & 0xFF):02x} "
            f"product {prod} manufacturer {mfr}"
        )


def describe_led_bar_usb_devices() -> Iterator[str]:
    for dev in iter_led_bar_usb_devices():
        try:
            prod = dev.product
        except Exception:
            prod = "?"
        yield f"{dev.idVendor:04x}:{dev.idProduct:04x} bus {dev.bus} addr {dev.address} product {prod!r}"
