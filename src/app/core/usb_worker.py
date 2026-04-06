"""Single-thread USB task queue (all pyusb I/O off the GUI thread)."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

from PySide6.QtCore import QObject, Signal, Slot

from app.logutil import log_usb_failure

T = TypeVar("T")


class UsbWorker(QObject):
    """Runs callables sequentially in one background thread; signals fire on GUI thread."""

    opStarted = Signal()
    opFinished = Signal()
    opFailed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="usb")

    def submit(self, fn: Callable[[], Any]) -> None:
        self.opStarted.emit()

        def run() -> None:
            try:
                fn()
                self.opFinished.emit()
            except Exception as e:
                self.opFailed.emit(log_usb_failure(e))

        self._pool.submit(run)

    @Slot()
    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=False)
