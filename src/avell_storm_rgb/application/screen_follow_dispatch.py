"""Route follow-screen to X11 or Wayland implementation."""

from __future__ import annotations

import threading

from avell_storm_rgb.application.screen_follow_session import is_wayland_session
from avell_storm_rgb.infrastructure.usb.ite8291_usb import Ite8291UsbDevice


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


def run_screen_follow_auto(
    keyboard: Ite8291UsbDevice,
    *,
    offset_x: int | None = None,
    offset_y: int | None = None,
    width: int | None = None,
    height: int | None = None,
    stop_event: threading.Event | None = None,
) -> None:
    if is_wayland_session():
        from avell_storm_rgb.application.screen_follow_wayland import run_screen_follow_wayland

        run_screen_follow_wayland(keyboard, stop_event=stop_event)
        return

    from avell_storm_rgb.application.screen_follow import run_screen_follow

    run_screen_follow(
        keyboard,
        offset_x=offset_x,
        offset_y=offset_y,
        width=width,
        height=height,
        stop_event=stop_event,
    )
