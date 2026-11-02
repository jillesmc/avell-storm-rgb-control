"""Keyboard follow-screen characterisation (UT-099, UT-100) and CLI loop (IT-014).

UT-099 was written against the pre-refactor X11 loop and must stay green after the
capture/apply split (ADR-004).
"""

from __future__ import annotations

import sys
import threading
import types

import pytest

pytest.importorskip("PIL")

from PIL import Image

from avell_storm_rgb.application.screen_follow_frame import build_key_color_map_from_pil_rgb
from backend_fakes import FakeKeyboard

W, H = 32, 12
FRAMES = [(255, 0, 0), (0, 0, 255)]


def _bgrx(rgb) -> bytes:
    r, g, b = rgb
    return bytes([b, g, r, 0]) * (W * H)


@pytest.fixture
def fake_xlib(monkeypatch):
    """A fake X server that serves FRAMES, then sets the stop event."""
    state = {"i": 0, "stop": None}

    class Root:
        def get_geometry(self):
            return types.SimpleNamespace(width=W, height=H)

        def get_image(self, *a):
            i = state["i"]
            state["i"] += 1
            if i >= len(FRAMES) - 1 and state["stop"] is not None:
                state["stop"].set()
            return types.SimpleNamespace(data=_bgrx(FRAMES[min(i, len(FRAMES) - 1)]))

    display_mod = types.ModuleType("Xlib.display")
    display_mod.Display = lambda: types.SimpleNamespace(screen=lambda: types.SimpleNamespace(root=Root()))
    x_mod = types.ModuleType("Xlib.X")
    x_mod.ZPixmap = 2
    err_mod = types.ModuleType("Xlib.error")
    err_mod.XError = type("XError", (Exception,), {})
    pkg = types.ModuleType("Xlib")
    pkg.X, pkg.display, pkg.error = x_mod, display_mod, err_mod
    for name, mod in {"Xlib": pkg, "Xlib.X": x_mod, "Xlib.display": display_mod, "Xlib.error": err_mod}.items():
        monkeypatch.setitem(sys.modules, name, mod)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    return state


def _expected_maps():
    return [build_key_color_map_from_pil_rgb(Image.new("RGB", (W, H), c)) for c in FRAMES]


def _key_color_calls(kb):
    return [c for c in kb.calls if c[0] in ("enable_user_mode", "set_key_colors")]


def test_ut099_x11_follow_sequence(fake_xlib) -> None:
    from avell_storm_rgb.application.screen_follow import run_screen_follow

    kb = FakeKeyboard()
    stop = threading.Event()
    fake_xlib["stop"] = stop
    run_screen_follow(kb, stop_event=stop)
    calls = _key_color_calls(kb)
    assert [c[0] for c in calls] == ["enable_user_mode", "set_key_colors", "set_key_colors"]
    assert [c[1] for c in calls[1:]] == _expected_maps()


def test_it014_cli_follow_screen_same_sequence(fake_xlib, monkeypatch) -> None:
    """``avell-storm-rgb keyboard follow-screen --fullscreen`` over the split loop."""
    from avell_storm_rgb.adapters.cli import main as cli

    kb = FakeKeyboard()
    stop = threading.Event()
    fake_xlib["stop"] = stop
    monkeypatch.setattr(cli, "_open_kb", lambda args: kb)
    real = cli.run_screen_follow_auto
    monkeypatch.setattr(cli, "run_screen_follow_auto", lambda k, **kw: real(k, stop_event=stop, **kw))
    assert cli.main(["keyboard", "follow-screen", "--fullscreen"]) == 0
    calls = _key_color_calls(kb)
    assert [c[0] for c in calls] == ["enable_user_mode", "set_key_colors", "set_key_colors"]
    assert [c[1] for c in calls[1:]] == _expected_maps()


def test_ut099_ut100_gui_subscriber_writes_maps_and_stops(monkeypatch) -> None:
    pytest.importorskip("PySide6.QtCore")
    from PySide6.QtWidgets import QApplication

    from app.core.screen_hub import ScreenFrameHub
    from app.core.usb_worker import UsbWorker
    from app.ui.adapters.keyboard_backend import KeyboardBackend
    from backend_fakes import drain

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    QApplication.instance() or QApplication([])
    def idle(stop, **r):
        stop.wait()
        return
        yield  # pragma: no cover

    hub = ScreenFrameHub(frames=idle)
    worker = UsbWorker()
    fake = FakeKeyboard()
    monkeypatch.setattr("app.ui.adapters.keyboard_backend.open_keyboard", lambda **kw: fake)
    kb = KeyboardBackend(worker, screen_hub=hub)
    kb.connectAt(1, 2)
    drain(worker)
    fake.calls.clear()
    kb.startFollowScreen(True, 0, 0, 0, 0)
    for colour in FRAMES:  # each frame drained → one write per frame (UT-099)
        hub.frame.emit(Image.new("RGB", (W, H), colour))
        drain(worker)
    calls = _key_color_calls(fake)
    assert [c[0] for c in calls] == ["enable_user_mode", "set_key_colors", "set_key_colors"]
    assert [c[1] for c in calls[1:]] == _expected_maps()
    kb.stopFollowOrAnimation()  # UT-100
    assert not hub.is_subscribed(kb)
    hub.frame.emit(Image.new("RGB", (W, H), (0, 255, 0)))
    drain(worker)
    assert len(_key_color_calls(fake)) == 3
    worker.shutdown(wait=True)
