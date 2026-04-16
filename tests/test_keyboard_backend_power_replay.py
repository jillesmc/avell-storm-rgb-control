"""KeyboardBackend: snapshot effect before power off and replay on power on (no hardware)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.core.usb_worker import UsbWorker
from app.ui.adapters.keyboard_backend import KeyboardBackend


@pytest.fixture(scope="module")
def _qapp_module() -> QApplication:
    inst = QApplication.instance()
    return inst if inst is not None else QApplication([])


@pytest.fixture(scope="module")
def _usb_worker_module(_qapp_module: QApplication) -> UsbWorker:
    w = UsbWorker()
    loop = QEventLoop()
    primed: list[bool] = []

    def on_done() -> None:
        primed.append(True)
        loop.quit()

    w.opFinished.connect(on_done)
    w.submit(lambda: None)
    QTimer.singleShot(2000, loop.quit)
    loop.exec()
    w.opFinished.disconnect(on_done)
    assert primed, "USB worker prime failed"
    yield w
    w.shutdown(wait=True)


class MockKeyboard:
    def __init__(self) -> None:
        self.effect = [10, 20, 30, 40, 50, 60]
        self.calls: list = []

    def get_effect(self) -> list[int]:
        self.calls.append("get_effect")
        return list(self.effect)

    def turn_off(self) -> None:
        self.calls.append("turn_off")

    def set_effect(self, data: list[int]) -> None:
        self.calls.append(("set_effect", list(data)))

    def get_fw_version(self) -> tuple[int, int, int, int]:
        return (1, 2, 3, 4)

    def get_brightness(self) -> int:
        return 25

    def is_off(self) -> bool:
        return False


def _wait_usb(app: QApplication, worker: UsbWorker) -> None:
    loop = QEventLoop()
    done: list[bool] = []

    def on_done() -> None:
        done.append(True)
        loop.quit()

    worker.opFinished.connect(on_done)
    QTimer.singleShot(3000, loop.quit)
    loop.exec()
    worker.opFinished.disconnect(on_done)
    assert done, "USB task did not finish"


def test_power_off_snapshots_effect_before_turn_off(
    _qapp_module: QApplication,
    _usb_worker_module: UsbWorker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = MockKeyboard()
    monkeypatch.setattr(
        "app.ui.adapters.keyboard_backend.open_keyboard",
        lambda bus_addr=None, debug=False: mock,
    )
    kb = KeyboardBackend(_usb_worker_module)
    kb.connectAt(1, 2)
    _wait_usb(_qapp_module, _usb_worker_module)

    kb.powerOff()
    _wait_usb(_qapp_module, _usb_worker_module)

    assert mock.calls[0] == "get_effect"
    assert mock.calls[1] == "turn_off"
    assert kb.replayPowerOnAvailable is True

    kb.disconnectDevice()
    _wait_usb(_qapp_module, _usb_worker_module)


def test_power_on_replay_applies_snapshot(
    _qapp_module: QApplication,
    _usb_worker_module: UsbWorker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = MockKeyboard()
    monkeypatch.setattr(
        "app.ui.adapters.keyboard_backend.open_keyboard",
        lambda bus_addr=None, debug=False: mock,
    )
    kb = KeyboardBackend(_usb_worker_module)
    kb.connectAt(1, 2)
    _wait_usb(_qapp_module, _usb_worker_module)

    expected = list(mock.effect)
    kb.powerOff()
    _wait_usb(_qapp_module, _usb_worker_module)
    mock.calls.clear()

    kb.powerOnReplay()
    _wait_usb(_qapp_module, _usb_worker_module)

    assert ("set_effect", expected) in mock.calls

    kb.disconnectDevice()
    _wait_usb(_qapp_module, _usb_worker_module)


def test_power_on_replay_noop_without_snapshot(
    _qapp_module: QApplication,
    _usb_worker_module: UsbWorker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = MockKeyboard()
    monkeypatch.setattr(
        "app.ui.adapters.keyboard_backend.open_keyboard",
        lambda bus_addr=None, debug=False: mock,
    )
    kb = KeyboardBackend(_usb_worker_module)
    kb.connectAt(1, 2)
    _wait_usb(_qapp_module, _usb_worker_module)

    assert kb.replayPowerOnAvailable is False
    kb.powerOnReplay()
    assert not any(
        isinstance(c, tuple) and len(c) > 0 and c[0] == "set_effect" for c in mock.calls
    )

    kb.disconnectDevice()
    _wait_usb(_qapp_module, _usb_worker_module)
