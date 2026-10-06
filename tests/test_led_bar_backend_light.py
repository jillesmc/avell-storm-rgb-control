"""LedBarBackend: full-parameter looks saved on success, light toggle (UT-050–UT-053, UT-062)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtWidgets import QApplication

from app.core.usb_worker import UsbWorker
from app.ui.adapters.led_bar_backend import LedBarBackend
from avell_storm_rgb.application.device_state import LedBarLook, LedBarState
from avell_storm_rgb.domain.ledbar_colors import PALETTES
from backend_fakes import FakeLedBar, drain


@pytest.fixture
def worker():
    if QApplication.instance() is None:
        QApplication([])
    w = UsbWorker()
    yield w
    w.shutdown(wait=True)


def _connected(worker, monkeypatch, fake: FakeLedBar) -> tuple[LedBarBackend, list[dict]]:
    monkeypatch.setattr("app.ui.adapters.led_bar_backend.open_led_bar_at", lambda bus, addr: fake)
    lb = LedBarBackend(worker)
    persisted: list[dict] = []
    lb.persistUpdate.connect(persisted.append)
    lb.connectAt(1, 2)
    drain(worker)
    return lb, persisted


def test_ut050_preset_saved_with_driver_parameters(worker, monkeypatch) -> None:
    lb, persisted = _connected(worker, monkeypatch, FakeLedBar())
    lb.applyPalette("fire", "wave")
    drain(worker)
    assert persisted == [{"look": LedBarLook(tuple(PALETTES["fire"]), "wave", 50, 3), "power": "on"}]


def test_ut051_brightness_slider_updates_saved_look(worker, monkeypatch) -> None:
    lb, persisted = _connected(worker, monkeypatch, FakeLedBar())
    lb.requestBrightnessFromUi(80, "static")
    lb._led_brightness_timer.stop()
    lb._flush_led_brightness_debounced()
    drain(worker)
    assert persisted[-1]["look"].brightness == 80
    assert persisted[-1]["look"].effect == "static"


def test_ut052_failed_apply_not_saved(worker, monkeypatch) -> None:
    lb, persisted = _connected(worker, monkeypatch, FakeLedBar(fail_on=frozenset({"apply_visual_effect"})))
    lb.applyEffect("breathing")
    drain(worker)
    assert persisted == []


def test_ut053_palette_capped_at_nine(worker, monkeypatch) -> None:
    lb, persisted = _connected(worker, monkeypatch, FakeLedBar())
    lb.applyPalette(",".join(["red"] * 11), "static")
    drain(worker)
    assert len(persisted[-1]["look"].palette) == 9


def test_ut062_light_toggle_with_saved_look(worker, monkeypatch) -> None:
    fake = FakeLedBar()
    lb, persisted = _connected(worker, monkeypatch, fake)
    lb.applyPalette("ice", "breathing")
    drain(worker)
    fake.calls.clear()

    lb.setLightOn(False)
    drain(worker)
    assert fake.calls == [("power_off",)]
    assert lb.lightOn is False
    assert persisted[-1] == {"power": "off"}

    fake.calls.clear()
    lb.setLightOn(True)
    drain(worker)
    assert fake.names() == [
        "power_on",
        "set_palette_colors",
        "set_brightness_level",
        "set_motion_speed",
        "apply_visual_effect",
    ]
    assert lb.lightOn is True
    assert persisted[-1] == {"power": "on"}


def test_apply_while_off_powers_on_first(worker, monkeypatch) -> None:
    fake = FakeLedBar()
    lb, _ = _connected(worker, monkeypatch, fake)
    lb.setLightOn(False)
    drain(worker)
    fake.calls.clear()
    lb.applyEffect("wave")
    drain(worker)
    assert fake.names() == ["power_on", "apply_visual_effect"]
    assert lb.lightOn is True


def test_restore_never_persists(worker, monkeypatch) -> None:
    fake = FakeLedBar()
    lb, persisted = _connected(worker, monkeypatch, fake)
    lb.restore(LedBarState("048d:7001", power="off", look=LedBarLook(((1, 2, 3),), "static", 10, 2)))
    drain(worker)
    assert persisted == []
    assert fake.calls == [("power_off",)]
    assert lb.lightOn is False


def test_disconnect_and_reconnect_release_the_usb_handle(worker, monkeypatch) -> None:
    first, second = FakeLedBar(), FakeLedBar()
    devices = iter([first, second, FakeLedBar()])
    monkeypatch.setattr("app.ui.adapters.led_bar_backend.open_led_bar_at", lambda bus, addr: next(devices))
    lb = LedBarBackend(worker)
    lb.connectAt(1, 2)
    drain(worker)
    lb.disconnectDevice()
    drain(worker)
    assert first.names()[-1] == "close"
    lb.connectAt(1, 2)
    lb.connectAt(1, 2)
    drain(worker)
    assert "close" in second.names()
