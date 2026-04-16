"""LedBarBackend: record last visual mode and replay after power on (no hardware)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.core.usb_worker import UsbWorker
from app.ui.adapters.led_bar_backend import LedBarBackend


@pytest.fixture(scope="module")
def _qapp_module() -> QApplication:
    inst = QApplication.instance()
    return inst if inst is not None else QApplication([])


@pytest.fixture(scope="module")
def _usb_worker_module(_qapp_module: QApplication) -> UsbWorker:
    w = UsbWorker()
    # Prime the pool so the first real test's opFinished is delivered reliably
    # after other modules (e.g. keyboard replay) have torn down their workers.
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


class MockLedBar:
    def __init__(self) -> None:
        self.calls: list = []
        self.product_id = 0x7000
        self.brightness = 50
        self.speed = 3
        self.palette: list = [(255, 0, 0)]

    def power_on(self) -> None:
        self.calls.append("power_on")

    def power_off(self) -> None:
        self.calls.append("power_off")

    def apply_visual_effect(self, name: str) -> None:
        self.calls.append(("effect", name))

    def set_static_rgb(self, r: int, g: int, b: int) -> None:
        self.calls.append(("rgb", r, g, b))

    def set_palette_colors(self, colors: list) -> None:
        self.calls.append(("palette", list(colors)))

    def set_brightness_level(self, level: int) -> None:
        self.calls.append(("brightness", level))

    def set_motion_speed(self, speed: int) -> None:
        self.calls.append(("speed", speed))


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


def test_apply_effect_records_replay_and_power_on_replay(
    _qapp_module: QApplication,
    _usb_worker_module: UsbWorker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = MockLedBar()
    monkeypatch.setattr(
        "app.ui.adapters.led_bar_backend.open_led_bar_at",
        lambda bus, addr: mock,
    )
    lb = LedBarBackend(_usb_worker_module)
    lb.connectAt(1, 2)
    _wait_usb(_qapp_module, _usb_worker_module)

    lb.applyEffect("wave")
    _wait_usb(_qapp_module, _usb_worker_module)
    assert lb.replayPowerOnAvailable is True

    lb.powerOff()
    _wait_usb(_qapp_module, _usb_worker_module)
    mock.calls.clear()

    lb.powerOnReplay()
    _wait_usb(_qapp_module, _usb_worker_module)

    assert mock.calls[0] == "power_on"
    assert mock.calls[1] == ("effect", "wave")

    lb.disconnectDevice()
    _wait_usb(_qapp_module, _usb_worker_module)


def test_disconnect_clears_replay(
    _qapp_module: QApplication,
    _usb_worker_module: UsbWorker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = MockLedBar()
    monkeypatch.setattr(
        "app.ui.adapters.led_bar_backend.open_led_bar_at",
        lambda bus, addr: mock,
    )
    lb = LedBarBackend(_usb_worker_module)
    lb.connectAt(1, 2)
    _wait_usb(_qapp_module, _usb_worker_module)
    lb.applyEffect("static")
    _wait_usb(_qapp_module, _usb_worker_module)
    assert lb.replayPowerOnAvailable is True

    lb.disconnectDevice()
    _wait_usb(_qapp_module, _usb_worker_module)
    assert lb.replayPowerOnAvailable is False


def test_apply_brightness_speed_effect_records_tune(
    _qapp_module: QApplication,
    _usb_worker_module: UsbWorker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock = MockLedBar()
    monkeypatch.setattr(
        "app.ui.adapters.led_bar_backend.open_led_bar_at",
        lambda bus, addr: mock,
    )
    lb = LedBarBackend(_usb_worker_module)
    lb.connectAt(1, 2)
    _wait_usb(_qapp_module, _usb_worker_module)

    lb.applyBrightnessSpeedEffect(80, 7, "breathing")
    _wait_usb(_qapp_module, _usb_worker_module)

    assert ("brightness", 80) in mock.calls
    assert ("speed", 7) in mock.calls
    assert ("effect", "breathing") in mock.calls
    assert lb.replayPowerOnAvailable is True

    lb.powerOff()
    _wait_usb(_qapp_module, _usb_worker_module)
    mock.calls.clear()
    lb.powerOnReplay()
    _wait_usb(_qapp_module, _usb_worker_module)

    assert mock.calls[0] == "power_on"
    assert ("brightness", 80) in mock.calls
    assert ("speed", 7) in mock.calls
    assert ("effect", "breathing") in mock.calls

    lb.disconnectDevice()
    _wait_usb(_qapp_module, _usb_worker_module)
