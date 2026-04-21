"""Map a PIL RGB image sample to per-key colors (shared by X11 and Wayland follow-screen)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice

if TYPE_CHECKING:
    from PIL.Image import Image


def build_key_color_map_from_pil_rgb(im: Image) -> dict[tuple[int, int], tuple[int, int, int]]:
    from PIL import Image as PILImage

    rgb = im.convert("RGB")
    small = rgb.resize((16, 6), resample=PILImage.Resampling.BOX)
    color_map: dict[tuple[int, int], tuple[int, int, int]] = {}
    for row in range(6):
        for col in range(16):
            color_map[(row, col)] = small.getpixel((col, 5 - row))
    return color_map


def apply_pil_rgb_image_to_keyboard(
    keyboard: Ite8291UsbDevice,
    im: Image,
    *,
    enable_user_mode_flag: bool = False,
) -> None:
    keyboard.set_key_colors(
        build_key_color_map_from_pil_rgb(im),
        enable_user_mode_flag=enable_user_mode_flag,
    )
