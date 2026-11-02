"""Per-bulb serial task queues (Tuya LAN I/O off the GUI thread, never on the USB thread).

ADR-003: one single-thread executor per bulb, so commands for one bulb run in order
while different bulbs run in parallel; each bulb has at most one open driver.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QObject, Signal

from avell_storm_rgb.application.bulb_inventory import BulbFailure
from avell_storm_rgb.application.bulb_facade import BulbError, BulbUnreachable, KeyRejected

if TYPE_CHECKING:
    from avell_storm_rgb.ports.protocols import BulbDriver

_LOG = logging.getLogger("avell_storm_rgb.gui")

UNREACHABLE_HINT = "Check that it is powered; discovery uses UDP 6666/6667."


def describe_failure(name: str, exc: BaseException) -> tuple[BulbFailure, str]:
    """``(row failure, banner text)`` for a failed bulb operation; never a key or payload (BR-3)."""
    detail = f"{type(exc).__name__}: {exc}" if isinstance(exc, BulbError) else type(exc).__name__
    if isinstance(exc, BulbUnreachable):
        reason = f"{name} is not reachable on the network"
        return BulbFailure(reason, detail), f"{reason}. {UNREACHABLE_HINT}"
    if isinstance(exc, KeyRejected):
        reason = f"{name} rejected the local key or protocol — re-import devices.json"
        return BulbFailure(reason, detail), reason
    message = str(exc) if isinstance(exc, BulbError) else "operation failed"
    reason = f"{name}: {message}"
    return BulbFailure(reason, detail), reason


class BulbWorker(QObject):
    """Runs bulb tasks off the GUI thread; ``opDone`` reaches GUI-thread slots (queued)."""

    opDone = Signal(str, object)  # (bulb_id, BulbStatus | BulbFailure)
    opFailed = Signal(str)  # user-facing text only

    def __init__(
        self,
        open_driver: Callable[[str], "BulbDriver"],
        parent: QObject | None = None,
        *,
        name_of: Callable[[str], str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._open_driver = open_driver
        self._name_of = name_of or (lambda bulb_id: bulb_id)
        self._lock = threading.Lock()
        self._pools: dict[str, ThreadPoolExecutor] = {}
        self._drivers: dict[str, "BulbDriver"] = {}  # touched only on that bulb's thread
        self._hold: dict[str, bool] = {}
        self._closed = False

    def _pool(self, bulb_id: str) -> ThreadPoolExecutor | None:
        with self._lock:
            if self._closed:
                return None
            pool = self._pools.get(bulb_id)
            if pool is None:
                pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="bulb")
                self._pools[bulb_id] = pool
            return pool

    def _driver(self, bulb_id: str) -> "BulbDriver":
        driver = self._drivers.get(bulb_id)
        if driver is None:
            driver = self._open_driver(bulb_id)
            self._drivers[bulb_id] = driver
        return driver

    def _release(self, bulb_id: str, *, unhold: bool = False) -> None:
        driver = self._drivers.pop(bulb_id, None)
        if driver is not None:
            try:
                if unhold:
                    driver.hold_open(False)
                driver.close()
            except Exception:  # closing a dead socket must not hide the real result
                _LOG.debug("bulb close failed", exc_info=True)

    def submit(self, bulb_id: str, fn: Callable[["BulbDriver"], Any]) -> Future | None:
        """Queue ``fn(driver)`` for ``bulb_id``; its return value is emitted with ``opDone``."""
        pool = self._pool(bulb_id)
        if pool is None:
            return None

        def run() -> None:
            try:
                result = fn(self._driver(bulb_id))
            except Exception as exc:
                held = bool(self._hold.get(bulb_id))
                self._hold[bulb_id] = False  # a dropped persistent socket is not reopened silently
                self._release(bulb_id, unhold=held)
                failure, text = describe_failure(self._name_of(bulb_id), exc)
                _LOG.info("bulb operation failed: %s", failure.detail)
                self.opDone.emit(bulb_id, failure)
                self.opFailed.emit(text)
                return
            if not self._hold.get(bulb_id):
                self._release(bulb_id)
            self.opDone.emit(bulb_id, result)

        return pool.submit(run)

    def run_after(self, bulb_id: str, fn: Callable[[], Any]) -> Future | None:
        """Run ``fn()`` on ``bulb_id``'s queue (no driver), after everything queued before it."""
        pool = self._pool(bulb_id)
        return None if pool is None else pool.submit(fn)

    def set_hold_open(self, bulb_id: str, hold: bool) -> Future | None:
        """Keep one persistent driver for ``bulb_id`` (follow only), or close it."""
        pool = self._pool(bulb_id)
        if pool is None:
            return None

        def run() -> None:
            self._hold[bulb_id] = hold
            try:
                if hold:
                    self._driver(bulb_id).hold_open(True)
                else:
                    self._release(bulb_id, unhold=True)
            except Exception as exc:
                self._hold[bulb_id] = False
                self._release(bulb_id)
                _LOG.info("bulb hold-open failed: %s", type(exc).__name__)

        return pool.submit(run)

    def shutdown(self, wait: bool = False) -> None:
        """Stop accepting work and close every open session (on its own thread)."""
        with self._lock:
            self._closed = True
            pools = dict(self._pools)
        for bulb_id, pool in pools.items():
            pool.submit(self._release, bulb_id)
            pool.shutdown(wait=wait, cancel_futures=False)
