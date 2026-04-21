"""Unit tests for screen-follow PIL → key colour map (no USB / no portal)."""

from __future__ import annotations

import pytest

pytest.importorskip("PIL")

from avell_storm_rgb.application.screen_follow_frame import (
    apply_pil_rgb_image_to_keyboard,
    build_key_color_map_from_pil_rgb,
)
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice


def test_build_key_color_map_solid_red() -> None:
    from PIL import Image

    im = Image.new("RGB", (32, 12), (255, 0, 0))
    m = build_key_color_map_from_pil_rgb(im)
    assert len(m) == 16 * 6
    assert m[(0, 0)] == (255, 0, 0)
    assert m[(5, 15)] == (255, 0, 0)


def test_build_key_color_map_horizontal_gradient() -> None:
    from PIL import Image

    im = Image.new("RGB", (16, 1))
    for x in range(16):
        im.putpixel((x, 0), (x * 16, 0, 0))
    m = build_key_color_map_from_pil_rgb(im)
    assert m[(5, 0)][0] < m[(5, 15)][0]


def test_apply_pil_rgb_image_to_keyboard_calls_set_key_colors(monkeypatch) -> None:
    from PIL import Image

    calls: list[tuple[dict, bool]] = []

    def fake_set_key_colors(self, color_map, brightness=None, save=False, enable_user_mode_flag=True):
        calls.append((dict(color_map) if color_map else {}, enable_user_mode_flag))

    monkeypatch.setattr(Ite8291UsbDevice, "set_key_colors", fake_set_key_colors)

    kb = Ite8291UsbDevice.__new__(Ite8291UsbDevice)
    im = Image.new("RGB", (4, 4), (0, 128, 255))
    apply_pil_rgb_image_to_keyboard(kb, im, enable_user_mode_flag=False)
    assert len(calls) == 1
    cmap, flag = calls[0]
    assert flag is False
    assert cmap[(0, 0)] == (0, 128, 255)
