"""Bulbs exposed to QML as ``App.bulbs``: import, memory, refresh and control.

Every network call runs on :class:`BulbWorker` (never the USB thread, never ``AppState.busy``).
Worker results reach the row cache only in :meth:`BulbsBackend._on_op_done`, on the GUI thread.
Saved memory (remembered / follow) is owned by ``AppFacade``; this object asks for changes
through ``persistUpdate`` and reads the result back through ``saved``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Property, QObject, Qt, QTimer, QUrl, Signal, Slot

from avell_storm_rgb.application.bulb_inventory import (
    BulbFailure,
    BulbInventory,
    BulbRecord,
    ImportFileError,
    InventoryFileError,
    parse_tinytuya_devices,
)
from avell_storm_rgb.application.device_state import FOLLOW_VALUES, BulbState
from avell_storm_rgb.domain.bulb_color import BulbStatus

from app.core.bulb_worker import BulbWorker
from app.core.screen_hub import ScreenFrameHub
from app.ui.adapters.app_state import AppState
from app.ui.adapters.bulb_follow import BulbFollower
from app.ui.adapters.bulb_model import BulbListModel

if TYPE_CHECKING:
    from avell_storm_rgb.ports.protocols import BulbDriver

_LOG = logging.getLogger("avell_storm_rgb.gui")

REFRESH_INTERVAL_MS = 30_000


@dataclass
class _Live:
    """What the app last learned from one bulb (BR-7)."""

    status: BulbStatus | None = None
    failure: BulbFailure | None = None
    busy: bool = False


def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def _colour_brightness(rgb: tuple[int, int, int]) -> int:
    """V of ``rgb`` in percent, at least 1 (BR-10)."""
    return max(1, round(max(rgb) * 100 / 255))


class BulbsBackend(QObject):
    modelChanged = Signal()
    bulbEpochChanged = Signal()
    importSummaryChanged = Signal()
    windowVisibleChanged = Signal()
    persistUpdate = Signal(str, object)  # (bulb_id, {"remembered": bool} | {"follow": str} | {"remove": True})

    def __init__(
        self,
        app_state: AppState,
        *,
        saved: Callable[[], tuple[BulbState, ...]],
        available: bool = True,
        inventory: BulbInventory | None = None,
        open_driver: Callable[[BulbRecord, BulbInventory], "BulbDriver"] | None = None,
        follow_sources: Callable[[], list[str]] | None = None,
        screen_hub: ScreenFrameHub | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._app_state = app_state
        self._saved = saved
        self._available = available
        self._inventory = inventory if inventory is not None else BulbInventory()
        self._opener = open_driver
        self._records: list[BulbRecord] = []
        self._live: dict[str, _Live] = {}
        self._connecting: set[str] = set()
        self._reading: set[str] = set()  # status reads queued and not answered yet
        self._removing: set[str] = set()  # removed here, inventory write still queued
        self._follow_sources = follow_sources or (lambda: [])
        # Latest status per bulb as seen by that bulb's own (serial) thread; lets queued
        # commands build on each other. Only bulb threads touch it; the row cache is separate.
        self._chain: dict[str, BulbStatus] = {}
        self._epoch = 0
        self._import_summary = ""
        self._window_visible = False
        self._model = BulbListModel(self)
        self._worker = BulbWorker(self._open_driver, self, name_of=self._name)
        queued = Qt.ConnectionType.QueuedConnection
        self._worker.opDone.connect(self._on_op_done, queued)
        self._worker.opFailed.connect(self._on_op_failed, queued)
        self._reported: dict[str, str] = {}  # bulb name → banner text it caused
        self._follower = BulbFollower(
            self._worker,
            power_on=self._power_on,
            read_status=self._follow_read,
            screen_hub=screen_hub,
            parent=self,
        )
        if screen_hub is not None:
            screen_hub.cancelled.connect(self._on_screen_cancelled)
            screen_hub.ended.connect(self._on_screen_ended)
            screen_hub.failed.connect(lambda _msg: self._drop_screen_followers())
        self._timer = QTimer(self)
        self._timer.setInterval(REFRESH_INTERVAL_MS)
        self._timer.timeout.connect(self.refresh)
        if available:
            self._load_records()
        self._publish()

    # --- properties ------------------------------------------------------------------

    @Property(QObject, constant=True)
    def model(self) -> BulbListModel:
        return self._model

    @Property(int, notify=bulbEpochChanged)
    def bulbEpoch(self) -> int:
        return self._epoch

    @Property(str, notify=importSummaryChanged)
    def importSummary(self) -> str:
        return self._import_summary

    def _get_window_visible(self) -> bool:
        return self._window_visible

    def _set_window_visible(self, visible: bool) -> None:
        visible = bool(visible)
        if visible == self._window_visible:
            return
        self._window_visible = visible
        self.windowVisibleChanged.emit()
        if not self._available:
            return
        if visible:
            self.refresh()
            self._timer.start()
        else:
            self._timer.stop()

    windowVisible = Property(bool, _get_window_visible, _set_window_visible, notify=windowVisibleChanged)

    # --- slots -----------------------------------------------------------------------

    @Slot("QUrl")
    def importFile(self, file_url: QUrl | str) -> None:
        if not self._available:
            return
        path = Path(file_url.toLocalFile() if isinstance(file_url, QUrl) else file_url)
        try:
            records, _skipped = parse_tinytuya_devices(path.read_text(encoding="utf-8"))
        except OSError as e:
            self._app_state.reportError(
                f"error: not a tinytuya devices.json (cannot read file ({e.strerror})): {path}"
            )
            return
        except ImportFileError as e:
            self._app_state.reportError(f"error: not a tinytuya devices.json ({e.reason}): {path}")
            return
        try:
            report = self._inventory.upsert(records)
        except InventoryFileError as e:
            self._app_state.reportError(f"error: bulb inventory is unreadable ({e.reason}): {e.path}")
            return
        self._removing -= {r.id for r in records}
        count = report.imported
        if count == 0:
            self._set_summary(f"No bulbs found in {path}")
        else:
            self._set_summary(f"Imported {count} bulb{'' if count == 1 else 's'}")
        self._load_records()
        self._changed()

    @Slot(str)
    def connectBulb(self, bulb_id: str) -> None:
        """Read the bulb once; remember it only when the read succeeds (BR-4)."""
        if not self._available or self._record(bulb_id) is None or bulb_id in self._connecting:
            return
        self._connecting.add(bulb_id)
        self._read(bulb_id, busy=True)

    @Slot(str)
    def retryBulb(self, bulb_id: str) -> None:
        if self._available and self._record(bulb_id) is not None and not self._live_for(bulb_id).busy:
            self._read(bulb_id, busy=True)

    @Slot(str)
    def disconnectBulb(self, bulb_id: str) -> None:
        """Stop remembering the bulb; its key stays in the inventory (BR-5)."""
        if not self._available or self._record(bulb_id) is None:
            return
        self._worker.set_hold_open(bulb_id, False)
        self._live_for(bulb_id).failure = None
        self.persistUpdate.emit(bulb_id, {"remembered": False})
        self._changed()

    @Slot(str)
    def forgetBulb(self, bulb_id: str) -> None:
        self.disconnectBulb(bulb_id)

    @Slot(str)
    def removeBulb(self, bulb_id: str) -> None:
        """Delete the inventory record (and key) and the saved entry (BR-5)."""
        if not self._available or self._record(bulb_id) is None:
            return
        # Follower stopped and socket closed *before* the inventory write: both run on
        # this bulb's FIFO queue, the write after the close (UT-080).
        self._follower.set_source(bulb_id, "none")
        self._worker.set_hold_open(bulb_id, False)
        self._removing.add(bulb_id)
        inventory = self._inventory

        def write() -> None:
            try:
                inventory.remove(bulb_id)
            except InventoryFileError as e:
                self._worker.opFailed.emit(
                    f"error: bulb inventory is unreadable ({e.reason}): {e.path}"
                )

        self._worker.run_after(bulb_id, write)
        self._live.pop(bulb_id, None)
        self._connecting.discard(bulb_id)
        self.persistUpdate.emit(bulb_id, {"remove": True})
        self._load_records()
        self._changed()

    @Slot()
    def refresh(self) -> None:
        """Read every remembered bulb; never sends a command (BR-6, BR-8)."""
        if not self._available:
            return
        self._load_records()
        remembered = {b.id for b in self._saved() if b.remembered}
        for record in self._records:
            if record.id in remembered and record.id not in self._reading:
                self._read(record.id, busy=False)
        self._changed()

    @Slot(str, bool)
    def setLightOn(self, bulb_id: str, on: bool) -> None:
        on = bool(on)

        def task(driver: "BulbDriver") -> BulbStatus:
            prev = self._chain.get(bulb_id)
            driver.set_power(on)
            return replace(prev, on=on) if prev is not None else driver.status()

        self._command(bulb_id, task)

    @Slot(str, int)
    def setBrightness(self, bulb_id: str, percent: int) -> None:
        percent = _clamp(percent, 1, 100)

        def task(driver: "BulbDriver") -> BulbStatus:
            prev = self._chain.get(bulb_id)
            driver.set_brightness(percent, prev)
            return replace(prev, on=True, brightness=percent) if prev is not None else driver.status()

        self._command(bulb_id, task)

    @Slot(str, int)
    def setWhite(self, bulb_id: str, temperature_percent: int) -> None:
        temperature = _clamp(temperature_percent, 0, 100)

        def task(driver: "BulbDriver") -> BulbStatus:
            prev = self._chain.get(bulb_id)
            driver.set_white(temperature, prev)
            if prev is None:
                return driver.status()
            return replace(prev, on=True, mode="white", temperature=temperature, rgb=None)

        self._command(bulb_id, task)

    @Slot(str, int, int, int)
    def setColor(self, bulb_id: str, r: int, g: int, b: int) -> None:
        rgb = (_clamp(r, 0, 255), _clamp(g, 0, 255), _clamp(b, 0, 255))

        def task(driver: "BulbDriver") -> BulbStatus:
            prev = self._chain.get(bulb_id)
            driver.set_colour(rgb)
            if prev is None:
                return driver.status()
            return replace(
                prev, on=True, mode="colour", rgb=rgb, temperature=None,
                brightness=_colour_brightness(rgb),
            )

        self._command(bulb_id, task)

    @Slot(str, str)
    def setFollow(self, bulb_id: str, source: str) -> None:
        """Save the follow choice; the follower runs while the bulb is remembered and reachable."""
        if self._available and source in FOLLOW_VALUES and self._record(bulb_id) is not None:
            self.persistUpdate.emit(bulb_id, {"follow": source})
            self._changed()

    @Slot(str, result=list)
    def availableFollowSources(self, bulb_id: str) -> list[str]:
        """Sources this runtime can follow right now (absent, not disabled, otherwise)."""
        return list(self._follow_sources()) if self._available else []

    def feed_colour(self, source: str, rgb: tuple[int, int, int]) -> None:
        """A follow source produced a colour (GUI thread)."""
        if self._available:
            self._follower.feed(source, rgb)

    @Slot(result=list)
    def rememberedBulbs(self) -> list[dict]:
        """Sidebar entries: snapshots of remembered bulbs, sorted by name."""
        return [row for row in self._model.rows() if row["remembered"]]

    @Slot(str, result="QVariantMap")
    def bulb(self, bulb_id: str) -> dict:
        return next((row for row in self._model.rows() if row["bulbId"] == bulb_id), {})

    def shutdown(self) -> None:
        self._timer.stop()
        self._follower.stop_all()
        self._worker.shutdown()

    # --- worker results (GUI thread) -------------------------------------------------

    @Slot(str, object)
    def _on_op_done(self, bulb_id: str, result: object) -> None:
        """The only place a worker result reaches the row cache."""
        if result is None or self._record(bulb_id) is None:
            return  # a follow push (no state), or removed while in flight
        live = self._live_for(bulb_id)
        live.busy = False
        self._reading.discard(bulb_id)
        connecting = bulb_id in self._connecting
        self._connecting.discard(bulb_id)
        if isinstance(result, BulbStatus):
            live.status = result
            live.failure = None
            self._clear_reported(self._name(bulb_id))
            if connecting:
                self.persistUpdate.emit(bulb_id, {"remembered": True})
        elif isinstance(result, BulbFailure):
            live.failure = result
        self._changed()

    # --- internals -------------------------------------------------------------------

    def _open_driver(self, bulb_id: str) -> "BulbDriver":
        """Runs on the bulb thread; reads the inventory per open so a re-import's key applies (IT-005)."""
        record = next((r for r in self._inventory.load() if r.id == bulb_id), None)
        if record is None:
            raise LookupError("bulb is no longer imported")
        if self._opener is not None:
            return self._opener(record, self._inventory)
        from avell_storm_rgb.application.bulb_facade import open_bulb

        return open_bulb(record, self._inventory)

    def _read(self, bulb_id: str, *, busy: bool) -> None:
        self._reading.add(bulb_id)
        if busy:
            self._live_for(bulb_id).busy = True
            self._changed()
        self._worker.submit(bulb_id, self._chained(bulb_id, lambda driver: driver.status()))

    def _command(self, bulb_id: str, task: Callable[["BulbDriver"], BulbStatus]) -> None:
        """Commands are never optimistic: the row changes when ``opDone`` arrives (UT-052)."""
        if self._available and self._record(bulb_id) is not None:
            self._worker.submit(bulb_id, self._chained(bulb_id, task))

    def _chained(
        self, bulb_id: str, task: Callable[["BulbDriver"], BulbStatus]
    ) -> Callable[["BulbDriver"], BulbStatus]:
        def run(driver: "BulbDriver") -> BulbStatus:
            try:
                status = task(driver)
            except Exception:
                self._chain.pop(bulb_id, None)  # unknown again: next command reads first
                raise
            self._chain[bulb_id] = status
            return status

        return run

    def _on_op_failed(self, text: str) -> None:
        name = next((r.name for r in self._records if text.startswith(r.name)), "")
        if name:
            self._reported[name] = text
        self._app_state.reportError(text)

    def _clear_reported(self, name: str) -> None:
        """A bulb that answers again takes its own error banner away (QA D-3)."""
        text = self._reported.pop(name, None)
        if text is not None and self._app_state.lastError == text:
            self._app_state.clearError()

    def _drop_screen_followers(self) -> list[str]:
        """The shared capture stopped: screen followers go back to None (US-016.EC-2/3)."""
        ids = self._follower.screen_followers()
        for bulb_id in ids:
            self.persistUpdate.emit(bulb_id, {"follow": "none"})
        if ids:
            self._changed()
        return ids

    def _on_screen_cancelled(self) -> None:
        for bulb_id in self._drop_screen_followers():
            self._app_state.reportError(
                f"Screen capture cancelled — {self._name(bulb_id)} no longer follows the screen."
            )

    def _on_screen_ended(self) -> None:
        if self._drop_screen_followers():
            self._app_state.reportError(
                "Screen capture ended — bulbs following the screen were set to None."
            )

    def _power_on(self, bulb_id: str) -> bool:
        live = self._live.get(bulb_id)
        return live is not None and live.failure is None and live.status is not None and live.status.on

    def _follow_read(self, bulb_id: str) -> None:
        if bulb_id not in self._reading:
            self._read(bulb_id, busy=False)

    def _sync_follow(self) -> None:
        """Follow runs only for remembered, reachable bulbs with a saved source (BR-15, UT-097/098)."""
        saved = {b.id: b for b in self._saved()}
        for record in self._records:
            state = saved.get(record.id)
            live = self._live.get(record.id)
            active = (
                state is not None
                and state.remembered
                and live is not None
                and live.status is not None
                and live.failure is None
            )
            self._follower.set_source(record.id, state.follow if active else "none")

    def _load_records(self) -> None:
        try:
            records = [r for r in self._inventory.load() if r.id not in self._removing]
            self._records = sorted(records, key=lambda r: r.name.casefold())
        except InventoryFileError as e:
            _LOG.warning("bulb inventory unreadable: %s", e.reason)
            self._records = []

    def _record(self, bulb_id: str) -> BulbRecord | None:
        return next((r for r in self._records if r.id == bulb_id), None)

    def _name(self, bulb_id: str) -> str:
        record = self._record(bulb_id)
        return record.name if record is not None else bulb_id

    def _live_for(self, bulb_id: str) -> _Live:
        return self._live.setdefault(bulb_id, _Live())

    def _set_summary(self, text: str) -> None:
        if text != self._import_summary:
            self._import_summary = text
            self.importSummaryChanged.emit()

    def _row(self, record: BulbRecord, saved: BulbState | None) -> dict:
        live = self._live.get(record.id, _Live())
        status = live.status
        known = status is not None
        available = known and live.failure is None
        ip = record.last_ip or ""
        remembered = saved is not None and saved.remembered
        if live.failure is not None:
            subtitle = "offline"
        elif known:
            subtitle = f"online · {ip}" if ip else "online"
        elif live.busy or remembered:
            subtitle = "Reading…"
        else:
            subtitle = ""
        return {
            "bulbId": record.id,
            "title": record.name,
            "subtitle": subtitle,
            "remembered": remembered,
            "available": available,
            "lightOn": bool(status.on) if known else False,
            "stateKnown": known,
            "unavailableReason": live.failure.reason if live.failure is not None else "",
            "mode": status.mode if known else "unknown",
            "brightness": status.brightness if known else 0,
            "temperature": status.temperature if known and status.temperature is not None else -1,
            "rgb": list(status.rgb) if known and status.rgb is not None else [],
            "follow": saved.follow if saved is not None else "none",
            "ip": ip,
            "busy": live.busy,
        }

    def _publish(self) -> None:
        saved = {b.id: b for b in self._saved()} if self._available else {}
        self._model.set_rows([self._row(r, saved.get(r.id)) for r in self._records])

    def _changed(self) -> None:
        if self._available:
            self._sync_follow()
        self._publish()
        self._epoch += 1
        self.bulbEpochChanged.emit()
        self.modelChanged.emit()
