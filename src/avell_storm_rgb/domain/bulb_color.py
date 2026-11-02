"""Pure Tuya bulb colour and status maths (no I/O).

Brightness and white temperature use the type-B device range 10–1000.
Colour is the Tuya ``colour_data_v2`` string: four hex digits each for hue
(0–360), saturation and value (0–1000). Black is clamped to 1 % so an explicit
colour command never leaves the bulb off.
"""

from __future__ import annotations

import colorsys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

RGB = tuple[int, int, int]
BulbMode = Literal["white", "colour", "scene", "music"]

DEVICE_MIN = 10
DEVICE_MAX = 1000
CHANGE_THRESHOLD = 8

_MODES = frozenset({"white", "colour", "scene", "music"})


@dataclass(frozen=True)
class BulbStatus:
    """Last state read from (or commanded to) a bulb."""

    on: bool
    mode: BulbMode
    brightness: int  # percent 1–100; 0 means the payload did not carry it
    temperature: int | None  # percent, white mode only
    rgb: RGB | None  # colour mode only


def percent_to_device(percent: int) -> int:
    """Map 1–100 % to the type-B device range 10–1000."""
    if not 1 <= percent <= 100:
        raise ValueError(f"percent must be 1–100, got {percent}")
    return percent * 10


def device_to_percent(value: int) -> int:
    """Map 0–1000 device value to 0–100 % (rounded)."""
    if not 0 <= value <= DEVICE_MAX:
        raise ValueError(f"device value must be 0–{DEVICE_MAX}, got {value}")
    return round(value / 10)


def rgb_to_colour_data_v2(rgb: RGB) -> str:
    """Encode RGB as the 12-hex-digit ``colour_data_v2`` string (V ≥ 1 %)."""
    r, g, b = rgb
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    hue = round(h * 360) % 360
    sat = round(s * 1000)
    val = max(DEVICE_MIN, round(v * 1000))
    return f"{hue:04x}{sat:04x}{val:04x}"


def colour_data_v2_to_rgb(value: str) -> RGB:
    """Decode a 12-hex-digit ``colour_data_v2`` string to RGB 0–255."""
    if len(value) != 12:
        raise ValueError(f"colour_data_v2 must be 12 hex digits, got {value!r}")
    try:
        hue = int(value[0:4], 16)
        sat = int(value[4:8], 16)
        val = int(value[8:12], 16)
    except ValueError as e:
        raise ValueError(f"colour_data_v2 must be 12 hex digits, got {value!r}") from e
    r, g, b = colorsys.hsv_to_rgb((hue % 360) / 360, min(sat, 1000) / 1000, min(val, 1000) / 1000)
    return (round(r * 255), round(g * 255), round(b * 255))


def average_rgb(colours: Iterable[RGB]) -> RGB:
    """Per-channel average of one or more colours."""
    items = list(colours)
    if not items:
        raise ValueError("average_rgb needs at least one colour")
    n = len(items)
    return (
        round(sum(c[0] for c in items) / n),
        round(sum(c[1] for c in items) / n),
        round(sum(c[2] for c in items) / n),
    )


def changed_enough(a: RGB, b: RGB, threshold: int = CHANGE_THRESHOLD) -> bool:
    """True when some channel moved by at least ``threshold`` (BR-13)."""
    return max(abs(x - y) for x, y in zip(a, b)) >= threshold


def status_from_dps(dps: Mapping[str, Any]) -> BulbStatus:
    """Build a :class:`BulbStatus` from a Tuya status DPS map.

    ``21`` selects the mode; ``22`` is white brightness, ``23`` white
    temperature, and ``24`` the colour payload (its V is the colour brightness).
    """
    raw_mode = dps.get("21")
    mode: BulbMode = raw_mode if raw_mode in _MODES else "white"  # type: ignore[assignment]
    brightness = 0
    temperature: int | None = None
    rgb: RGB | None = None

    if mode == "colour":
        colour = dps.get("24")
        if isinstance(colour, str) and len(colour) == 12:
            rgb = colour_data_v2_to_rgb(colour)
            brightness = device_to_percent(int(colour[8:12], 16))
    elif mode == "white":
        temp = dps.get("23")
        if isinstance(temp, int) and not isinstance(temp, bool):
            temperature = device_to_percent(temp)

    if brightness == 0:
        value = dps.get("22")
        if isinstance(value, int) and not isinstance(value, bool):
            brightness = device_to_percent(value)

    return BulbStatus(
        on=bool(dps.get("20", False)),
        mode=mode,
        brightness=brightness,
        temperature=temperature,
        rgb=rgb,
    )
