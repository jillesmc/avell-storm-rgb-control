"""ScreenFrameHub: one ref-counted capture (UT-090, UT-091) and its end states."""

from __future__ import annotations

import threading
import time

import pytest

pytest.importorskip("PySide6.QtCore")
pytest.importorskip("PIL")

from PIL import Image
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from app.core.screen_hub import ScreenFrameHub
from avell_storm_rgb.application.screen_follow_wayland import ScreenCaptureCancelled


class FakeSource:
    """Frame source: yields a solid frame every 10 ms until stopped (or a scripted end)."""

    def __init__(self, colour=(0, 255, 0), *, end_after: int | None = None, cancel: bool = False) -> None:
        self.starts = 0
        self.stops: list[threading.Event] = []
        self.colour = colour
        self.end_after = end_after
        self.cancel = cancel

    def __call__(self, stop, **region):
        self.starts += 1
        self.stops.append(stop)
        if self.cancel:
            raise ScreenCaptureCancelled()
        n = 0
        while not stop.is_set():
            if self.end_after is not None and n >= self.end_after:
                return
            yield Image.new("RGB", (8, 4), self.colour)
            n += 1
            time.sleep(0.01)


def wait_until(predicate, timeout: float = 2.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        QCoreApplication.processEvents()
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("condition not reached")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_ut090_first_subscriber_starts_once(app) -> None:
    source = FakeSource()
    hub = ScreenFrameHub(frames=source)
    frames: list = []
    hub.frame.connect(frames.append)
    hub.subscribe("a")
    hub.subscribe("b")
    hub.subscribe("a")
    wait_until(lambda: len(frames) >= 2)
    assert source.starts == 1
    hub.shutdown()


def test_ut091_last_unsubscribe_stops(app) -> None:
    source = FakeSource()
    hub = ScreenFrameHub(frames=source)
    hub.subscribe("a")
    hub.subscribe("b")
    hub.unsubscribe("a")
    assert not source.stops[0].is_set() and hub.running
    hub.unsubscribe("b")
    assert source.stops[0].is_set() and not hub.running


def test_cancelled_and_ended_drop_subscribers(app) -> None:
    hub = ScreenFrameHub(frames=FakeSource(cancel=True))
    seen: list[str] = []
    hub.cancelled.connect(lambda: seen.append("cancelled"))
    hub.subscribe("a")
    wait_until(lambda: seen == ["cancelled"])
    assert not hub.is_subscribed("a") and not hub.running

    hub = ScreenFrameHub(frames=FakeSource(end_after=1))
    hub.ended.connect(lambda: seen.append("ended"))
    hub.subscribe("a")
    wait_until(lambda: "ended" in seen)
    assert not hub.running


def test_error_reports_failed(app) -> None:
    def broken(stop, **region):
        raise RuntimeError("X11 screen capture failed")
        yield  # pragma: no cover

    hub = ScreenFrameHub(frames=broken)
    seen: list[str] = []
    hub.failed.connect(seen.append)
    hub.subscribe("a")
    wait_until(lambda: seen)
    assert seen == ["Follow screen: X11 screen capture failed"]
