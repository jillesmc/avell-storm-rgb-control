"""
Stable entry points for adapters (CLI, future PySide).

USB I/O should run on a single thread or a dedicated worker queue; do not
call these from multiple threads concurrently without external locking.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from avell_storm_rgb.infrastructure.usb.discovery import (
    find_led_bar_device,
    iter_keyboard_usb_devices,
    iter_led_bar_usb_devices,
    open_ite8291_device,
)
from avell_storm_rgb.infrastructure.usb.ite8233_usb import Ite8233UsbDevice
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice


def usb_id_of(dev: Any) -> str:
    """Stable identity of a USB device: ``vendor:product`` in lowercase hex (e.g. ``048d:ce00``)."""
    return f"{dev.idVendor:04x}:{dev.idProduct:04x}"


def open_keyboard(
    *,
    bus_addr: tuple[int, int] | None = None,
    usb_id: str | None = None,
    debug: bool = False,
) -> Ite8291UsbDevice:
    """Open by bus/address, by USB id (first match in scan order), or the first compatible keyboard."""
    if usb_id is not None and bus_addr is None:
        for dev in iter_keyboard_usb_devices():
            if usb_id_of(dev) == usb_id:
                bus_addr = (int(dev.bus), int(dev.address))
                break
        else:
            raise FileNotFoundError("no suitable device found")
    return open_ite8291_device(bus_addr, debug=debug)


def open_led_bar(*, usb_id: str | None = None) -> Ite8233UsbDevice:
    """Open the first LED bar, or the first one whose USB id matches."""
    if usb_id is None:
        return find_led_bar_device()
    for dev in iter_led_bar_usb_devices():
        if usb_id_of(dev) == usb_id:
            return Ite8233UsbDevice(device=dev)
    raise RuntimeError("No ITE 8233 LED bar found.")


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
