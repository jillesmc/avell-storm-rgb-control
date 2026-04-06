# SPDX-License-Identifier: MIT
# LED bar color/palette parsing derived from ite8233-ledbar (MIT).

from __future__ import annotations

COLORS: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "orange": (255, 123, 0),
    "yellow": (255, 183, 0),
    "green": (0, 255, 0),
    "cyan": (0, 255, 255),
    "blue": (0, 0, 255),
    "purple": (136, 0, 255),
    "magenta": (255, 0, 255),
    "pink": (255, 105, 180),
    "white": (255, 255, 255),
    "warm": (255, 200, 150),
    "cool": (200, 220, 255),
}

PALETTES: dict[str, list[tuple[int, int, int]]] = {
    "rainbow": [
        (255, 0, 0),
        (255, 123, 0),
        (255, 183, 0),
        (0, 255, 0),
        (0, 255, 255),
        (0, 0, 255),
        (136, 0, 255),
        (255, 0, 255),
    ],
    "fire": [
        (255, 0, 0),
        (255, 80, 0),
        (255, 160, 0),
        (255, 200, 0),
    ],
    "ice": [
        (0, 200, 255),
        (0, 150, 255),
        (0, 100, 255),
        (100, 200, 255),
    ],
    "forest": [
        (0, 255, 0),
        (0, 200, 50),
        (0, 150, 0),
        (50, 200, 50),
    ],
}

MAX_LED_BAR_PALETTE = 9


def parse_color(color_str: str) -> tuple[int, int, int]:
    color_str = color_str.lower().strip().strip("\"'")
    if color_str in COLORS:
        return COLORS[color_str]
    hexpart = color_str[1:] if color_str.startswith("#") else color_str
    if len(hexpart) == 6:
        r = int(hexpart[0:2], 16)
        g = int(hexpart[2:4], 16)
        b = int(hexpart[4:6], 16)
        return (r, g, b)
    raise ValueError(f"Unknown color: {color_str}")


def parse_palette(palette_str: str) -> list[tuple[int, int, int]]:
    palette_str = palette_str.lower().strip()
    if palette_str in PALETTES:
        return list(PALETTES[palette_str])
    colors: list[tuple[int, int, int]] = []
    for part in palette_str.split(","):
        part = part.strip()
        if part:
            colors.append(parse_color(part))
    if not colors:
        raise ValueError("Empty palette")
    return colors


def build_led_bar_effect_report(
    effect_code: int, speed: int, brightness: int, num_colors: int
) -> bytes:
    """8-byte HID set_report payload for CMD_EFFECT (0x08); see ite8233-ledbar."""
    return bytes(
        [0x08, 0x22, effect_code & 0xFF, speed & 0xFF, brightness & 0xFF, num_colors & 0xFF, 0x00, 0x00]
    )
