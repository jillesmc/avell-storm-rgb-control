"""Follow window colors on keyboard (Wayland + xdg-desktop-portal + PipeWire). Optional [screen] extra."""

from __future__ import annotations

import threading
import time

from collections.abc import Iterator
from typing import TYPE_CHECKING

from avell_storm_rgb.application.screen_follow import apply_frames_to_keyboard, pace
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice

if TYPE_CHECKING:
    from PIL.Image import Image


def _numpy_bgra_to_pil_rgb(frame: object) -> object:
    import numpy as np
    from PIL import Image

    arr = np.asarray(frame, dtype=np.uint8)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError(f"expected HxWx4 BGRA frame, got shape {getattr(arr, 'shape', None)}")
    # BGRA -> RGB
    rgb = arr[:, :, [2, 1, 0]]
    return Image.fromarray(rgb, mode="RGB")


class ScreenCaptureCancelled(Exception):
    """The user closed the portal picker without choosing a window."""


def iter_wayland_frames(stop_event: threading.Event | None = None) -> Iterator["Image"]:
    """Yield RGB frames of the window picked in the portal until stopped or the window closes.

    Raises :class:`ScreenCaptureCancelled` when the picker is cancelled.
    """
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
        raise ScreenCaptureCancelled()

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

    last_draw = 0.0
    try:
        while stop_event is None or not stop_event.is_set():
            if stream.window_invalid:
                break
            frame = stream.get_frame()
            if frame is not None:
                yield _numpy_bgra_to_pil_rgb(frame)
                last_draw = pace(last_draw, stop_event)
            else:
                time.sleep(0.01)
    finally:
        if stream is not None:
            stream.stop()
        session.close()


def run_screen_follow_wayland(
    keyboard: Ite8291UsbDevice,
    *,
    stop_event: threading.Event | None = None,
) -> None:
    try:
        apply_frames_to_keyboard(keyboard, iter_wayland_frames(stop_event))
    except ScreenCaptureCancelled:
        return
