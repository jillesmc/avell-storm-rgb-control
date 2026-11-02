"""Bulb follow (slice 2): coalesce source colours into rate-limited pushes per bulb.

BR-12: pushes only mode + colour (``push_colour``), only while the last known power is on.
BR-13: one 250 ms tick per following bulb → at most 4 pushes/s, latest colour only,
       only when a channel moved by at least 8, never while a push is in flight.
ADR-003: a persistent driver (``set_hold_open``) only while following.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtCore import QObject, QTimer

from avell_storm_rgb.domain.bulb_color import average_rgb, changed_enough

from app.core.bulb_worker import BulbWorker
from app.core.screen_hub import ScreenFrameHub

TICK_MS = 250
STATUS_READ_MS = 5_000

RGB = tuple[int, int, int]


def _owner(bulb_id: str) -> str:
    return f"bulb:{bulb_id}"


@dataclass
class _Following:
    source: str
    tick: QTimer
    status: QTimer
    latest: RGB | None = None
    sent: RGB | None = None
    in_flight: list = field(default_factory=lambda: [False])  # shared with the bulb thread


class BulbFollower(QObject):
    def __init__(
        self,
        worker: BulbWorker,
        *,
        power_on: Callable[[str], bool],
        read_status: Callable[[str], None],
        screen_hub: ScreenFrameHub | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._hub = screen_hub
        if screen_hub is not None:
            screen_hub.frame.connect(self._on_screen_frame)
        self._worker = worker
        self._power_on = power_on
        self._read_status = read_status
        self._following: dict[str, _Following] = {}
        self._last: dict[str, RGB] = {}  # latest colour per source, for bulbs that join later

    def source_of(self, bulb_id: str) -> str:
        entry = self._following.get(bulb_id)
        return entry.source if entry is not None else "none"

    def set_source(self, bulb_id: str, source: str) -> None:
        current = self._following.get(bulb_id)
        if current is not None and current.source == source:
            return
        if current is not None:
            current.tick.stop()
            current.status.stop()
            del self._following[bulb_id]
            if current.source == "screen" and self._hub is not None:
                self._hub.unsubscribe(_owner(bulb_id))
            if source == "none":
                self._worker.set_hold_open(bulb_id, False)
        if source == "none":
            return
        tick = QTimer(self)
        tick.setInterval(TICK_MS)
        tick.timeout.connect(lambda: self._tick(bulb_id))
        status = QTimer(self)
        status.setInterval(STATUS_READ_MS)
        status.timeout.connect(lambda: self._read_status(bulb_id))
        entry = _Following(source, tick, status, latest=self._last.get(source))
        self._following[bulb_id] = entry
        if current is None:
            self._worker.set_hold_open(bulb_id, True)
        if source == "screen" and self._hub is not None:
            self._hub.subscribe(_owner(bulb_id))  # one shared capture (BR-16)
        tick.start()
        status.start()

    def screen_followers(self) -> list[str]:
        return [bulb_id for bulb_id, e in self._following.items() if e.source == "screen"]

    def _on_screen_frame(self, image: object) -> None:
        """Average the shared capture's frame for bulbs following the screen."""
        if not self.screen_followers():
            return
        small = image.convert("RGB").resize((16, 6))
        self.feed("screen", average_rgb(small.getpixel((x, y)) for x in range(16) for y in range(6)))

    def feed(self, source: str, rgb: RGB) -> None:
        """A source produced a colour (GUI thread)."""
        rgb = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        self._last[source] = rgb
        for entry in self._following.values():
            if entry.source == source:
                entry.latest = rgb

    def stop_all(self) -> None:
        for bulb_id in list(self._following):
            self.set_source(bulb_id, "none")

    def _tick(self, bulb_id: str) -> None:
        entry = self._following.get(bulb_id)
        if entry is None or entry.latest is None or entry.in_flight[0]:
            return
        if not self._power_on(bulb_id):  # unknown counts as off (BR-12)
            return
        if entry.sent is not None and not changed_enough(entry.latest, entry.sent):
            return
        rgb = entry.latest
        flag = entry.in_flight
        flag[0] = True

        def push(driver) -> None:
            driver.push_colour(rgb)
            return None

        future = self._worker.submit(bulb_id, push)
        if future is None:
            flag[0] = False
            return
        entry.sent = rgb
        future.add_done_callback(lambda _f: flag.__setitem__(0, False))
