"""One shared screen capture per process (ADR-004, BR-16, Safety Invariant 7).

The first subscriber starts the capture (one portal picker on Wayland); the last
unsubscribe stops it. Frames are emitted from the capture thread and reach GUI-thread
slots queued; consumers coalesce (latest wins).
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal


def _default_frames(stop: threading.Event, **region: Any) -> Iterator[Any]:
    from avell_storm_rgb.application.screen_follow_dispatch import iter_screen_frames

    return iter_screen_frames(stop, **region)


def _is_cancelled(exc: BaseException) -> bool:
    return type(exc).__name__ == "ScreenCaptureCancelled"


class ScreenFrameHub(QObject):
    frame = Signal(object)  # PIL RGB image
    cancelled = Signal()  # picker closed: subscribers were dropped
    ended = Signal()  # capture ended on its own (window closed): subscribers were dropped
    failed = Signal(str)  # capture error: subscribers were dropped
    _finished = Signal(object, str, str)  # (stop event, kind, message) → GUI thread

    def __init__(
        self,
        frames: Callable[..., Iterator[Any]] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._frames = frames or _default_frames
        self._owners: list[object] = []
        self._stop: threading.Event | None = None
        self._finished.connect(self._on_finished, Qt.ConnectionType.QueuedConnection)

    @property
    def running(self) -> bool:
        return self._stop is not None

    def is_subscribed(self, owner: object) -> bool:
        return owner in self._owners

    def subscribe(self, owner: object, **region: Any) -> None:
        """Add ``owner``; the first subscriber starts the capture with its ``region``."""
        if self.is_subscribed(owner):
            return
        self._owners.append(owner)
        if self._stop is None:
            self._start(region)

    def unsubscribe(self, owner: object) -> None:
        self._owners = [o for o in self._owners if o != owner]
        if not self._owners and self._stop is not None:
            self._stop.set()
            self._stop = None

    def shutdown(self) -> None:
        self._owners = []
        if self._stop is not None:
            self._stop.set()
            self._stop = None

    def _start(self, region: dict) -> None:
        stop = threading.Event()
        self._stop = stop
        frames = self._frames

        def run() -> None:
            try:
                for image in frames(stop, **region):
                    if stop.is_set():
                        return
                    self.frame.emit(image)
            except Exception as exc:
                if not stop.is_set():
                    kind = "cancelled" if _is_cancelled(exc) else "failed"
                    self._finished.emit(stop, kind, f"Follow screen: {exc}")
                return
            if not stop.is_set():
                self._finished.emit(stop, "ended", "")

        threading.Thread(target=run, name="screen-capture", daemon=True).start()

    def _on_finished(self, stop: object, kind: str, message: str) -> None:
        if stop is not self._stop:
            return  # an older capture that was already stopped
        self._stop = None
        self._owners = []
        if kind == "cancelled":
            self.cancelled.emit()
        elif kind == "ended":
            self.ended.emit()
        else:
            self.failed.emit(message)
