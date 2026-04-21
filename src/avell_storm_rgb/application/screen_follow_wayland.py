"""Follow window colors on keyboard (Wayland + xdg-desktop-portal + PipeWire). Optional [screen] extra."""

from __future__ import annotations

import threading
import time

from avell_storm_rgb.application.screen_follow_frame import apply_pil_rgb_image_to_keyboard
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice


def _numpy_bgra_to_pil_rgb(frame: object) -> object:
    import numpy as np
    from PIL import Image

    arr = np.asarray(frame, dtype=np.uint8)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError(f"expected HxWx4 BGRA frame, got shape {getattr(arr, 'shape', None)}")
    # BGRA -> RGB
    rgb = arr[:, :, [2, 1, 0]]
    return Image.fromarray(rgb, mode="RGB")


def run_screen_follow_wayland(
    keyboard: Ite8291UsbDevice,
    *,
    stop_event: threading.Event | None = None,
) -> None:
    try:
        from pipewire_capture import CaptureStream, PortalCapture, is_available
    except ImportError as e:
        raise RuntimeError(
            "Wayland follow-screen needs optional dependencies: uv sync --extra screen "
            f"({e})"
        ) from e

    if not is_available():
        raise RuntimeError(
            "Wayland follow-screen: xdg-desktop-portal ScreenCast is not available "
            "(no session D-Bus or portal missing). Install and run "
            "xdg-desktop-portal with a backend (e.g. xdg-desktop-portal-kde on Plasma)."
        )

    portal = PortalCapture()
    session = portal.select_window()
    if session is None:
        return

    stream = None
    try:
        w = max(1, int(session.width))
        h = max(1, int(session.height))
        stream = CaptureStream(
            int(session.fd),
            int(session.node_id),
            w,
            h,
            capture_interval=0.1,
        )
        stream.start()
    except Exception:
        session.close()
        raise

    assert stream is not None

    keyboard.enable_user_mode()
    last_draw = 0.0
    try:
        while stop_event is None or not stop_event.is_set():
            if stream.window_invalid:
                break
            frame = stream.get_frame()
            if frame is not None:
                im = _numpy_bgra_to_pil_rgb(frame)
                apply_pil_rgb_image_to_keyboard(keyboard, im, enable_user_mode_flag=False)
                now = time.monotonic()
                if now - last_draw <= 0.1:
                    wait = 0.1 - (now - last_draw)
                    step = 0.05
                    while wait > 0 and (stop_event is None or not stop_event.is_set()):
                        time.sleep(min(step, wait))
                        wait -= step
                last_draw = time.monotonic()
            else:
                time.sleep(0.01)
    finally:
        if stream is not None:
            stream.stop()
        session.close()
