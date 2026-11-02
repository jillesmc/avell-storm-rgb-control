"""Capture split from apply (ADR-004): iterators, dispatch, Wayland cancel."""

from __future__ import annotations

import sys
import threading
import types

import pytest

pytest.importorskip("PIL")

from avell_storm_rgb.application import screen_follow_dispatch
from avell_storm_rgb.application.screen_follow_wayland import ScreenCaptureCancelled, iter_wayland_frames
from backend_fakes import FakeKeyboard
from test_keyboard_follow_screen import FRAMES, fake_xlib  # noqa: F401


def test_x11_iterator_yields_rgb_frames(fake_xlib) -> None:
    from avell_storm_rgb.application.screen_follow import iter_x11_frames

    stop = threading.Event()
    fake_xlib["stop"] = stop
    frames = list(iter_x11_frames(stop))
    assert [f.getpixel((0, 0)) for f in frames] == FRAMES


def test_dispatch_routes_to_x11(fake_xlib) -> None:
    stop = threading.Event()
    fake_xlib["stop"] = stop
    frames = list(screen_follow_dispatch.iter_screen_frames(stop))
    assert len(frames) == 2


def test_wayland_cancelled_picker_raises(monkeypatch) -> None:
    mod = types.ModuleType("pipewire_capture")
    mod.is_available = lambda: True
    mod.PortalCapture = lambda: types.SimpleNamespace(select_window=lambda: None)
    mod.CaptureStream = object
    monkeypatch.setitem(sys.modules, "pipewire_capture", mod)
    with pytest.raises(ScreenCaptureCancelled):
        next(iter_wayland_frames(threading.Event()))


def test_cli_loop_ignores_cancel(monkeypatch) -> None:
    def cancelled(stop=None, **region):
        raise ScreenCaptureCancelled()

    monkeypatch.setattr(screen_follow_dispatch, "iter_screen_frames", cancelled)
    kb = FakeKeyboard()
    screen_follow_dispatch.run_screen_follow_auto(kb)
    assert kb.calls == []
