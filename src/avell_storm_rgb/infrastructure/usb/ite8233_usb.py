# SPDX-License-Identifier: MIT
# USB protocol for ITE 8233 LED bar (8-byte HID reports). Derived from ite8233-ledbar (MIT).

from __future__ import annotations

import usb.core
import usb.util

from avell_storm_rgb.domain.ledbar_colors import MAX_LED_BAR_PALETTE

VENDOR_ID = 0x048D
KNOWN_PRODUCT_IDS = [0x7000, 0x7001]

CMD_EFFECT = 0x08
CMD_STATE = 0x12
CMD_COLOR = 0x14
CMD_INIT = 0x1A

LED_BAR_EFFECT_CODES: dict[str, int] = {
    "static": 0x01,
    "breathing": 0x02,
    "wave": 0x03,
    "impact": 0x04,
    "raindrop": 0x06,
}


class Ite8233UsbDevice:
    def __init__(self, device: usb.core.Device | None = None) -> None:
        self.brightness = 50
        self.speed = 3
        self.palette: list[tuple[int, int, int]] = [(136, 0, 255)]
        self._device = device
        self.product_id: int | None = None
        if device is not None:
            self.product_id = device.idProduct
            self._detach_if_needed(device)
        else:
            self._connect()

    def _usb_dev(self) -> usb.core.Device:
        if self._device is None:
            raise RuntimeError("LED bar device not connected")
        return self._device

    @staticmethod
    def _detach_if_needed(dev: usb.core.Device) -> None:
        for iface in range(2):
            try:
                if dev.is_kernel_driver_active(iface):
                    dev.detach_kernel_driver(iface)
            except (usb.core.USBError, NotImplementedError):
                pass

    def _connect(self) -> None:
        for dev in usb.core.find(find_all=True, idVendor=VENDOR_ID):
            if dev.idProduct in KNOWN_PRODUCT_IDS:
                self._device = dev
                self.product_id = dev.idProduct
                break
            try:
                product = usb.util.get_string(dev, dev.iProduct)
                if product and "8233" in product:
                    self._device = dev
                    self.product_id = dev.idProduct
                    break
            except (usb.core.USBError, ValueError):
                pass
        if self._device is None:
            raise RuntimeError(
                "LED bar not found (looking for ITE 8233 devices). "
                "Check connection and USB permissions."
            )
        self._detach_if_needed(self._device)

    def _send(self, data: list[int]) -> None:
        self._usb_dev().ctrl_transfer(0x21, 0x09, 0x0300, 0x0001, bytes(data))

    def _send_state(self) -> None:
        self._send([CMD_STATE, 0x00, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00])

    def _send_palette(self) -> None:
        for i, (r, g, b) in enumerate(self.palette[:MAX_LED_BAR_PALETTE], start=1):
            self._send([CMD_COLOR, 0x02, i, r, g, b, 0x00, 0x00])

    def _send_effect(self, effect: int) -> None:
        num_colors = len(self.palette) if len(self.palette) > 1 else 1
        self._send(
            [CMD_EFFECT, 0x22, effect, self.speed, self.brightness, num_colors, 0x00, 0x00]
        )

    def close(self) -> None:
        """Release the USB handle now (see ``Ite8291UsbDevice.close``)."""
        if self._device is not None:
            usb.util.dispose_resources(self._device)

    def power_on(self) -> None:
        self._send([CMD_EFFECT, 0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00])
        self._send([CMD_INIT, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
        self._send([CMD_INIT, 0x02, 0x01, 0x04, 0x00, 0x00, 0x00, 0x01])

    def power_off(self) -> None:
        self._send_state()
        self._send([CMD_EFFECT, 0x05, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        self._send([CMD_EFFECT, 0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00])
        self._send([CMD_INIT, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])

    def set_static_rgb(self, r: int, g: int, b: int) -> None:
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        self.palette = [(r, g, b)]
        self._send([CMD_COLOR, 0x02, 1, r, g, b, 0x00, 0x00])
        self._send_effect(LED_BAR_EFFECT_CODES["static"])

    def set_palette_colors(self, colors: list[tuple[int, int, int]]) -> None:
        self.palette = [
            (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            for r, g, b in colors[:MAX_LED_BAR_PALETTE]
        ]

    def apply_visual_effect(self, name: str) -> None:
        key = name.lower()
        if key not in LED_BAR_EFFECT_CODES:
            raise ValueError(f"Unknown effect: {name}")
        self._send_state()
        self._send_palette()
        self._send_effect(LED_BAR_EFFECT_CODES[key])

    def set_brightness_level(self, level: int) -> None:
        self.brightness = max(0, min(100, level))

    def set_motion_speed(self, speed: int) -> None:
        self.speed = max(1, min(10, speed))
