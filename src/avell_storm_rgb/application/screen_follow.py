"""Follow screen colours on keyboard via X11 capture (Xlib + Pillow). Optional [screen] extra.

Capture (``iter_x11_frames``) is split from apply (``screen_follow_frame``) so one capture
can feed several consumers (ADR-004).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING

from avell_storm_rgb.application.screen_follow_frame import apply_pil_rgb_image_to_keyboard
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice

if TYPE_CHECKING:
    from PIL.Image import Image

FRAME_INTERVAL = 0.1


def pace(last: float, stop: threading.Event | None) -> float:
    """Keep at most one frame per ``FRAME_INTERVAL`` while honouring ``stop``; returns the new mark."""
    now = time.monotonic()
    if now - last <= FRAME_INTERVAL:
        wait = FRAME_INTERVAL - (now - last)
        step = 0.05
        while wait > 0 and (stop is None or not stop.is_set()):
            time.sleep(min(step, wait))
            wait -= step
    return time.monotonic()


def iter_x11_frames(
    stop_event: threading.Event | None = None,
    *,
    offset_x: int | None = None,
    offset_y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> Iterator["Image"]:
    """Yield RGB frames of the X11 root window (or a region) until ``stop_event`` is set."""
    from Xlib import X, display
    from Xlib.error import XError
    from PIL import Image

    disp = display.Display()
    root = disp.screen().root
    geom = root.get_geometry()
    ox = 0 if offset_x is None else max(0, offset_x)
    oy = 0 if offset_y is None else max(0, offset_y)
    w = geom.width if width is None else width
    h = geom.height if height is None else height
    # Avoid X BadMatch from out-of-bounds get_image
    w = max(1, min(int(w), int(geom.width) - ox))
    h = max(1, min(int(h), int(geom.height) - oy))

    last_draw = 0.0
    while stop_event is None or not stop_event.is_set():
        try:
            raw = root.get_image(ox, oy, w, h, X.ZPixmap, 0xFFFFFFFF)
        except XError as e:
            raise RuntimeError(
                "X11 screen capture failed (often: Wayland session, invalid region, or "
                "XWayland). Follow-screen needs a working X11 root pixmap. Try an X11 session, "
                "use fullscreen capture only, or adjust region to fit the screen. "
                f"X error: {e}"
            ) from e
        yield Image.frombytes("RGB", (w, h), raw.data, "raw", "BGRX")
        last_draw = pace(last_draw, stop_event)


def apply_frames_to_keyboard(keyboard: Ite8291UsbDevice, frames: Iterator["Image"]) -> None:
    """Thin apply loop: user mode once on the first frame, then one 16×6 write per frame."""
    first = True
    for im in frames:
        if first:
            keyboard.enable_user_mode()
            first = False
        apply_pil_rgb_image_to_keyboard(keyboard, im, enable_user_mode_flag=False)


def run_screen_follow(
    keyboard: Ite8291UsbDevice,
    *,
    offset_x: int | None = None,
    offset_y: int | None = None,
    width: int | None = None,
    height: int | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    apply_frames_to_keyboard(
        keyboard,
        iter_x11_frames(
            stop_event, offset_x=offset_x, offset_y=offset_y, width=width, height=height
        ),
    )
