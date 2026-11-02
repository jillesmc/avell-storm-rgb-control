"""Route follow-screen to X11 or Wayland implementation."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from typing import TYPE_CHECKING

from avell_storm_rgb.application.screen_follow_session import is_wayland_session
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice

if TYPE_CHECKING:
    from PIL.Image import Image


def follow_screen_runtime_available() -> bool:
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        return False
    if is_wayland_session():
        try:
            from pipewire_capture import is_available
        except ImportError:
            return False
        try:
            return bool(is_available())
        except Exception:
            return False
    try:
        import Xlib  # noqa: F401
    except ImportError:
        return False
    return True


def iter_screen_frames(
    stop: threading.Event | None = None,
    *,
    offset_x: int | None = None,
    offset_y: int | None = None,
    width: int | None = None,
    height: int | None = None,
) -> Iterator["Image"]:
    """RGB frames from the X11 root (or region) or the Wayland portal window (ADR-004).

    Wayland ignores the region; a cancelled picker raises ``ScreenCaptureCancelled``.
    """
    if is_wayland_session():
        from avell_storm_rgb.application.screen_follow_wayland import iter_wayland_frames

        return iter_wayland_frames(stop)
    from avell_storm_rgb.application.screen_follow import iter_x11_frames

    return iter_x11_frames(stop, offset_x=offset_x, offset_y=offset_y, width=width, height=height)


def run_screen_follow_auto(
    keyboard: Ite8291UsbDevice,
    *,
    offset_x: int | None = None,
    offset_y: int | None = None,
    width: int | None = None,
    height: int | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    """CLI follow-screen: a thin apply loop over :func:`iter_screen_frames`."""
    from avell_storm_rgb.application.screen_follow import apply_frames_to_keyboard
    from avell_storm_rgb.application.screen_follow_wayland import ScreenCaptureCancelled

    try:
        frames = iter_screen_frames(
            stop_event, offset_x=offset_x, offset_y=offset_y, width=width, height=height
        )
        apply_frames_to_keyboard(keyboard, frames)
    except ScreenCaptureCancelled:
        return  # picker closed: same as before the split
