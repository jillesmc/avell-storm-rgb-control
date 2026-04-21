"""Single-thread USB task queue (all pyusb I/O off the GUI thread)."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, TypeVar

from PySide6.QtCore import QObject, Signal

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

    def submit(self, fn: Callable[[], Any], *, show_busy: bool = True) -> None:
        """Queue ``fn`` on the USB thread.

        Long-running tasks (e.g. follow-screen) should pass ``show_busy=False`` so the
        global BusyOverlay does not block the GUI until the task returns.
        """
        if show_busy:
            self.opStarted.emit()

        def run() -> None:
            try:
                fn()
            except Exception as e:
                self.opFailed.emit(log_usb_failure(e))
            else:
                if show_busy:
                    self.opFinished.emit()

        self._pool.submit(run)

    def shutdown(self, wait: bool = False) -> None:
        """Stop accepting new work. Use wait=True in tests so the next UsbWorker gets a clean thread."""
        self._pool.shutdown(wait=wait, cancel_futures=False)
