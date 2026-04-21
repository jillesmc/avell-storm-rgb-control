"""Core tests for the single-queue USB worker (no hardware)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QCoreApplication, QTimer

from app.core.usb_worker import UsbWorker


def _qcore_app() -> QCoreApplication:
    inst = QCoreApplication.instance()
    return inst if inst is not None else QCoreApplication([])


def test_usb_worker_runs_task_on_gui_thread():
    app = _qcore_app()
    worker = UsbWorker()
    done: list[str] = []
    worker.opFinished.connect(lambda: done.append("ok"))
    worker.submit(lambda: None)
    QTimer.singleShot(2000, app.quit)
    app.exec()
    worker.shutdown()
    assert done == ["ok"]


def test_usb_worker_submit_without_busy_signals():
    app = _qcore_app()
    worker = UsbWorker()
    started: list[str] = []
    finished: list[str] = []
    worker.opStarted.connect(lambda: started.append("s"))
    worker.opFinished.connect(lambda: finished.append("f"))
    worker.submit(lambda: None, show_busy=False)
    QTimer.singleShot(2000, app.quit)
    app.exec()
    worker.shutdown()
    assert started == []
    assert finished == []


def test_usb_worker_failed_emits_message():
    app = _qcore_app()
    worker = UsbWorker()
    errors: list[str] = []

    def on_fail(msg: str) -> None:
        errors.append(msg)

    worker.opFailed.connect(on_fail)

    def boom() -> None:
        raise ValueError("expected")

    worker.submit(boom)
    QTimer.singleShot(2000, app.quit)
    app.exec()
    worker.shutdown()
    assert len(errors) == 1
    assert "expected" in errors[0]


def test_usb_worker_failed_without_busy_still_emits_op_failed():
    app = _qcore_app()
    worker = UsbWorker()
    errors: list[str] = []
    worker.opFailed.connect(errors.append)

    def boom() -> None:
        raise RuntimeError("silent fail")

    worker.submit(boom, show_busy=False)
    QTimer.singleShot(2000, app.quit)
    app.exec()
    worker.shutdown()
    assert len(errors) == 1
    assert "silent fail" in errors[0]
