# SPDX-License-Identifier: GPL-2.0-or-later
#
# USB protocol implementation for ITE 8291 rev 0.03.
# Derived from ite8291r3-ctl (Copyright (C) Barnabás Pőcze et al., GPLv2).

from __future__ import annotations

import sys
from typing import Any

import usb.core
import usb.util

VENDOR_ID = 0x048D
PRODUCT_IDS = [0x6004, 0x6006, 0xCE00, 0x600B]
REV_NUMBER = 0x0003

NUM_ROWS = 6
NUM_COLS = 21
ROW_BUFFER_LEN = 3 * NUM_COLS + 2
ROW_RED_OFFSET = 1 + 2 * NUM_COLS
ROW_GREEN_OFFSET = 1 + 1 * NUM_COLS
ROW_BLUE_OFFSET = 1 + 0 * NUM_COLS


class _Commands:
    SET_EFFECT = 8
    SET_BRIGHTNESS = 9
    SET_PALETTE_COLOR = 20
    SET_ROW_INDEX = 22
    GET_FW_VERSION = 128
    GET_EFFECT = 136


commands = _Commands()


KEYBOARD_PALETTE_SLOT_COLORS: dict[str, int] = {
    "none": 0,
    "red": 1,
    "orange": 2,
    "yellow": 3,
    "green": 4,
    "blue": 5,
    "teal": 6,
    "purple": 7,
    "random": 8,
}

# Stable UI / firmware-effect picker order (slot 1–7, then random, none).
KEYBOARD_FIRMWARE_COLOR_CHOICES: list[tuple[str, int]] = [
    ("red", 1),
    ("orange", 2),
    ("yellow", 3),
    ("green", 4),
    ("blue", 5),
    ("teal", 6),
    ("purple", 7),
    ("random", 8),
    ("none", 0),
]

KEYBOARD_DIRECTIONS: dict[str, int] = {
    "none": 0,
    "right": 1,
    "left": 2,
    "up": 3,
    "down": 4,
}


class _EffectAttrs:
    EFFECT = 0
    SPEED = 1
    BRIGHTNESS = 2
    COLOR = 3
    DIRECTION = 4
    REACTIVE = 4
    SAVE = 5


effect_attrs = _EffectAttrs()


def _effect_factory(effect_id: int, args: dict[str, tuple[int, int]]):
    max_arg_idx = max(x[0] for x in args.values())

    def f(**kwargs: int) -> list[int]:
        res = [0] * (max_arg_idx + 1)
        for k, (idx, default) in args.items():
            res[idx] = default
        for k, v in kwargs.items():
            if k not in args:
                raise ValueError(f"'{k}' attr is not needed by effect")
            res[args[k][0]] = v
        res[effect_attrs.EFFECT] = effect_id
        return res

    f.params = frozenset(args)  # type: ignore[attr-defined]
    return f


KEYBOARD_EFFECTS: dict[str, Any] = {
    "breathing": _effect_factory(0x02, {
        "speed": (effect_attrs.SPEED, 5),
        "brightness": (effect_attrs.BRIGHTNESS, 25),
        "color": (effect_attrs.COLOR, KEYBOARD_PALETTE_SLOT_COLORS["random"]),
        "save": (effect_attrs.SAVE, 0),
    }),
    "wave": _effect_factory(0x03, {
        "speed": (effect_attrs.SPEED, 5),
        "brightness": (effect_attrs.BRIGHTNESS, 25),
        "direction": (effect_attrs.DIRECTION, KEYBOARD_DIRECTIONS["right"]),
        "save": (effect_attrs.SAVE, 0),
    }),
    "random": _effect_factory(0x04, {
        "speed": (effect_attrs.SPEED, 5),
        "brightness": (effect_attrs.BRIGHTNESS, 25),
        "color": (effect_attrs.COLOR, KEYBOARD_PALETTE_SLOT_COLORS["random"]),
        "reactive": (effect_attrs.REACTIVE, 0),
        "save": (effect_attrs.SAVE, 0),
    }),
    "rainbow": _effect_factory(0x05, {
        "brightness": (effect_attrs.BRIGHTNESS, 25),
        "save": (effect_attrs.SAVE, 0),
    }),
    "ripple": _effect_factory(0x06, {
        "speed": (effect_attrs.SPEED, 5),
        "brightness": (effect_attrs.BRIGHTNESS, 25),
        "color": (effect_attrs.COLOR, KEYBOARD_PALETTE_SLOT_COLORS["random"]),
        "reactive": (effect_attrs.REACTIVE, 0),
        "save": (effect_attrs.SAVE, 0),
    }),
    "marquee": _effect_factory(0x09, {
        "speed": (effect_attrs.SPEED, 5),
        "brightness": (effect_attrs.BRIGHTNESS, 25),
        "save": (effect_attrs.SAVE, 0),
    }),
    "raindrop": _effect_factory(0x0A, {
        "speed": (effect_attrs.SPEED, 5),
        "brightness": (effect_attrs.BRIGHTNESS, 25),
        "color": (effect_attrs.COLOR, KEYBOARD_PALETTE_SLOT_COLORS["random"]),
        "save": (effect_attrs.SAVE, 0),
    }),
    "aurora": _effect_factory(0x0E, {
        "speed": (effect_attrs.SPEED, 5),
        "brightness": (effect_attrs.BRIGHTNESS, 25),
        "color": (effect_attrs.COLOR, KEYBOARD_PALETTE_SLOT_COLORS["random"]),
        "reactive": (effect_attrs.REACTIVE, 0),
        "save": (effect_attrs.SAVE, 0),
    }),
    "fireworks": _effect_factory(0x11, {
        "speed": (effect_attrs.SPEED, 5),
        "brightness": (effect_attrs.BRIGHTNESS, 25),
        "color": (effect_attrs.COLOR, KEYBOARD_PALETTE_SLOT_COLORS["random"]),
        "reactive": (effect_attrs.REACTIVE, 0),
        "save": (effect_attrs.SAVE, 0),
    }),
}

# Parameters each effect builder accepts (speed, brightness, color, direction, reactive, save).
KEYBOARD_EFFECT_PARAMS: dict[str, frozenset[str]] = {
    name: builder.params for name, builder in KEYBOARD_EFFECTS.items()
}


def keyboard_effect_kwargs(
    name: str,
    *,
    speed: int,
    brightness: int,
    color: str,
    direction: str,
    reactive: bool,
    save: bool,
) -> dict[str, int]:
    """Clamp and map UI/saved values to the kwargs ``KEYBOARD_EFFECTS[name]`` accepts."""
    keys = KEYBOARD_EFFECT_PARAMS.get(name, frozenset())
    out: dict[str, int] = {}
    if "speed" in keys:
        out["speed"] = max(0, min(10, speed))
    if "brightness" in keys:
        out["brightness"] = max(0, min(50, brightness))
    if "color" in keys:
        out["color"] = KEYBOARD_PALETTE_SLOT_COLORS.get(
            color.lower(), KEYBOARD_PALETTE_SLOT_COLORS["random"]
        )
    if "direction" in keys:
        out["direction"] = KEYBOARD_DIRECTIONS.get(direction.lower(), 0)
    if "reactive" in keys:
        out["reactive"] = 1 if reactive else 0
    if "save" in keys:
        out["save"] = 1 if save else 0
    return out


class UsbChannel:
    def __init__(self, dev: usb.core.Device, fd_out: int) -> None:
        self.dev = dev
        self.fd_out = fd_out

    def ctrl_transfer(self, *args: Any, **kwargs: Any) -> Any:
        return self.dev.ctrl_transfer(*args, **kwargs)

    def write(self, payload: bytes | bytearray) -> int:
        return self.dev.write(self.fd_out, payload)


class Ite8291UsbDevice:
    def __init__(self, channel: UsbChannel, *, debug: bool = False) -> None:
        self.channel = channel
        self._debug = debug

    def _send_data(self, payload: bytes | bytearray) -> int:
        if self._debug:
            print(f"sending data ({len(payload)} bytes) to device: {payload!r}", file=sys.stderr)
        return self.channel.write(payload)

    def _send_ctrl(self, *payload: int) -> None:
        padded = tuple(payload) + (0,) * (8 - len(payload))
        if self._debug:
            print(f"sending ctrl device: {padded}", file=sys.stderr)
        self.channel.ctrl_transfer(
            usb.util.build_request_type(
                usb.util.CTRL_OUT, usb.util.CTRL_TYPE_CLASS, usb.util.CTRL_RECIPIENT_INTERFACE
            ),
            0x009,
            0x300,
            0x001,
            padded,
        )

    def _get_ctrl(self, length: int) -> Any:
        data = self.channel.ctrl_transfer(
            usb.util.build_request_type(
                usb.util.CTRL_IN, usb.util.CTRL_TYPE_CLASS, usb.util.CTRL_RECIPIENT_INTERFACE
            ),
            0x001,
            0x300,
            0x001,
            length,
        )
        if self._debug:
            print(f"received ctrl from device: {data}", file=sys.stderr)
        return data

    def get_fw_version(self) -> tuple[int, int, int, int]:
        self._send_ctrl(commands.GET_FW_VERSION)
        buf = self._get_ctrl(8)
        return (buf[1], buf[2], buf[3], buf[4])

    def get_effect(self) -> list[int]:
        self._send_ctrl(commands.GET_EFFECT)
        return list(self._get_ctrl(8)[2:])

    def _set_row_index(self, row_idx: int) -> None:
        self._send_ctrl(commands.SET_ROW_INDEX, 0x00, row_idx)

    def _set_effect_impl(
        self,
        control: int,
        effect: int = 0x00,
        speed: int = 0x00,
        brightness: int = 0x00,
        color: int = 0x00,
        direction_or_reactive: int = 0x00,
        save: int = 0x00,
    ) -> None:
        self._send_ctrl(
            commands.SET_EFFECT,
            control,
            effect,
            speed,
            brightness,
            color,
            direction_or_reactive,
            save,
        )

    def set_effect(self, effect_data: list[int]) -> None:
        self._set_effect_impl(0x02, *effect_data)

    def set_brightness(self, brightness: int) -> None:
        if not (0 <= brightness <= 50):
            raise ValueError("brightness must be between 0 and 50 inclusive")
        self._send_ctrl(commands.SET_BRIGHTNESS, 0x02, brightness)

    def freeze(self) -> None:
        effect = self.get_effect()
        effect[effect_attrs.SPEED] = 11
        self.set_effect(effect)

    def close(self) -> None:
        """Release claimed interfaces and the USB handle now.

        pyusb keeps a reference cycle (device -> active configuration -> device), so
        dropping the object does not free the handle until the cyclic GC runs; a new
        handle opened before that gets ``[Errno 16] Resource busy``.
        """
        usb.util.dispose_resources(self.channel.dev)

    def turn_off(self) -> None:
        self._set_effect_impl(control=0x01)

    def is_off(self) -> bool:
        self._send_ctrl(commands.GET_EFFECT)
        return self._get_ctrl(8)[1] == 0x01

    def get_brightness(self) -> int:
        return self.get_effect()[effect_attrs.BRIGHTNESS]

    def enable_user_mode(self, brightness: int | None = None, save: bool = False) -> None:
        if brightness is None:
            brightness = self.get_brightness()
        self.set_effect([51, 0, brightness, 0, 0, 1 if save else 0])

    def set_color(
        self, color: tuple[int, int, int], brightness: int | None = None, save: bool = False
    ) -> None:
        self.enable_user_mode(brightness, save)
        for row in range(NUM_ROWS):
            arr = [0] * ROW_BUFFER_LEN
            for i in range(NUM_COLS):
                arr[ROW_RED_OFFSET + i] = color[0]
                arr[ROW_GREEN_OFFSET + i] = color[1]
                arr[ROW_BLUE_OFFSET + i] = color[2]
            self._set_row_index(row)
            self._send_data(bytearray(arr))

    def set_palette_color(self, idx: int, color: tuple[int, int, int] | list[int]) -> None:
        if not (1 <= idx <= 7):
            raise ValueError("palette color index must be between 1 and 7 (inclusive)")
        self._send_ctrl(commands.SET_PALETTE_COLOR, 0, idx, *color)

    def restore_default_palette(self) -> None:
        self.set_palette_color(1, (255, 0, 0))
        self.set_palette_color(2, (255, 28, 0))
        self.set_palette_color(3, (255, 119, 0))
        self.set_palette_color(4, (0, 255, 0))
        self.set_palette_color(5, (0, 0, 255))
        self.set_palette_color(6, (0, 255, 255))
        self.set_palette_color(7, (255, 0, 255))

    def test_pattern(self, shift: int = 0, brightness: int | None = None, save: bool = False) -> None:
        self.enable_user_mode(brightness, save)
        c = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        for row in range(NUM_ROWS):
            arr = [0] * ROW_BUFFER_LEN
            for i in range(0, NUM_COLS, 3):
                for j in range(3):
                    rr, gg, bb = c[(j + row + shift) % 3]
                    arr[ROW_RED_OFFSET + i + j] = rr
                    arr[ROW_GREEN_OFFSET + i + j] = gg
                    arr[ROW_BLUE_OFFSET + i + j] = bb
            self._set_row_index(row)
            self._send_data(bytearray(arr))

    def set_key_colors(
        self,
        color_map: dict[tuple[int, int], tuple[int, int, int]] | None = None,
        brightness: int | None = None,
        save: bool = False,
        enable_user_mode_flag: bool = True,
    ) -> None:
        if color_map is None:
            color_map = {}
        arr = [[0] * ROW_BUFFER_LEN for _ in range(NUM_ROWS)]
        for (row, col), color in color_map.items():
            arr[row][ROW_RED_OFFSET + col] = color[0]
            arr[row][ROW_GREEN_OFFSET + col] = color[1]
            arr[row][ROW_BLUE_OFFSET + col] = color[2]
        if enable_user_mode_flag or save:
            self.enable_user_mode(brightness, save)
        for row in range(NUM_ROWS):
            self._set_row_index(row)
            self._send_data(bytearray(arr[row]))


def open_ite8291_device(
    loc: tuple[int, int] | None = None, *, debug: bool = False
) -> Ite8291UsbDevice:
    if loc:
        bus, addr = loc
        dev = usb.core.find(bus=bus, address=addr)
    else:
        dev = usb.core.find(
            idVendor=VENDOR_ID,
            custom_match=lambda d: d.idProduct in PRODUCT_IDS and d.bcdDevice == REV_NUMBER,
        )
    if not dev:
        raise FileNotFoundError("no suitable device found")
    if dev.is_kernel_driver_active(1):
        dev.detach_kernel_driver(1)
    cfg = dev.get_active_configuration()
    fd_out = usb.util.find_descriptor(
        cfg[(1, 0)],
        custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress)
        == usb.util.ENDPOINT_OUT,
    )
    return Ite8291UsbDevice(UsbChannel(dev, fd_out), debug=debug)


def iter_keyboard_usb_devices() -> Any:
    return usb.core.find(
        find_all=True,
        idVendor=VENDOR_ID,
        custom_match=lambda d: d.idProduct in PRODUCT_IDS and d.bcdDevice == REV_NUMBER,
    )
