"""Follow screen colours on keyboard via X11 capture (Xlib + Pillow). Optional [screen] extra."""

from __future__ import annotations

import threading
import time

from avell_storm_rgb.application.screen_follow_frame import apply_pil_rgb_image_to_keyboard
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice


def run_screen_follow(
    keyboard: Ite8291UsbDevice,
    *,
    offset_x: int | None = None,
    offset_y: int | None = None,
    width: int | None = None,
    height: int | None = None,
    stop_event: threading.Event | None = None,
) -> None:
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

    keyboard.enable_user_mode()

    last_draw = 0.0
    while True:
        if stop_event is not None and stop_event.is_set():
            break
        try:
            raw = root.get_image(ox, oy, w, h, X.ZPixmap, 0xFFFFFFFF)
        except XError as e:
            raise RuntimeError(
                "X11 screen capture failed (often: Wayland session, invalid region, or "
                "XWayland). Follow-screen needs a working X11 root pixmap. Try an X11 session, "
                "use fullscreen capture only, or adjust region to fit the screen. "
                f"X error: {e}"
            ) from e
        im = Image.frombytes("RGB", (w, h), raw.data, "raw", "BGRX")
        apply_pil_rgb_image_to_keyboard(keyboard, im, enable_user_mode_flag=False)
        now = time.monotonic()
        if now - last_draw <= 0.1:
            wait = 0.1 - (now - last_draw)
            step = 0.05
            while wait > 0 and (stop_event is None or not stop_event.is_set()):
                time.sleep(min(step, wait))
                wait -= step
        last_draw = time.monotonic()
