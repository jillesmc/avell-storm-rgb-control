from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from app.core.usb_worker import UsbWorker


class AppState(QObject):
    """Global busy / error for BusyOverlay + snack message."""

    busyChanged = Signal()
    lastErrorChanged = Signal()

    def __init__(self, worker: UsbWorker, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._pending = 0
        self._last_error = ""
        worker.opStarted.connect(self._on_started)
        worker.opFinished.connect(self._on_finished)
        worker.opFailed.connect(self._on_failed)

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._pending > 0

    @Property(str, notify=lastErrorChanged)
    def lastError(self) -> str:
        return self._last_error

    @Slot(str)
    def reportError(self, msg: str) -> None:
        """Show a message in the error banner without touching the busy counter."""
        if msg and self._last_error != msg:
            self._last_error = msg
            self.lastErrorChanged.emit()

    @Slot()
    def clearError(self) -> None:
        if self._last_error:
            self._last_error = ""
            self.lastErrorChanged.emit()

    def _on_started(self) -> None:
        self._pending += 1
        self.busyChanged.emit()

    @Slot()
    def _on_finished(self) -> None:
        self._pending = max(0, self._pending - 1)
        self.busyChanged.emit()

    @Slot(str)
    def _on_failed(self, msg: str) -> None:
        self._pending = max(0, self._pending - 1)
        self.busyChanged.emit()
        self._last_error = msg
        self.lastErrorChanged.emit()
