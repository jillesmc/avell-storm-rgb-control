"""KeyboardBackend: looks saved on success, light toggle, stop-before-apply (UT-040–UT-049, UT-060–UT-067)."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtWidgets import QApplication

from app.core.usb_worker import UsbWorker
from app.ui.adapters.keyboard_backend import KeyboardBackend
from avell_storm_rgb.application.device_state import (
    AnimationLook,
    FirmwareEffectLook,
    KeyboardState,
    PerKeyLook,
    SolidLook,
)
from avell_storm_rgb.infrastructure.usb.ite8291_usb import KEYBOARD_EFFECTS
from backend_fakes import FakeKeyboard, drain

WAVE = FirmwareEffectLook("wave", 5, 40, "random", "up", False, False)


@pytest.fixture
def worker():
    if QApplication.instance() is None:
        QApplication([])
    w = UsbWorker()
    yield w
    w.shutdown(wait=True)


def _connected(worker, monkeypatch, fake: FakeKeyboard) -> tuple[KeyboardBackend, list[dict]]:
    monkeypatch.setattr("app.ui.adapters.keyboard_backend.open_keyboard", lambda **kw: fake)
    kb = KeyboardBackend(worker)
    persisted: list[dict] = []
    kb.persistUpdate.connect(persisted.append)
    kb.connectAt(1, 2)
    drain(worker)
    return kb, persisted


def _looks(persisted: list[dict]) -> list:
    return [p["look"] for p in persisted if "look" in p]


def _animation(tmp_path: Path, wait: str = "0.02") -> Path:
    script = tmp_path / "anim"
    script.write_text(f"pos 0 0 255,0,0\napply\nwait {wait}\n")
    return script


def _wait_for(predicate, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition not reached")


def _spy_submit(kb: KeyboardBackend, stop_event) -> list[bool]:
    seen: list[bool] = []
    original = kb._worker.submit

    def spy(fn, **kw):
        seen.append(stop_event.is_set())
        return original(fn, **kw)

    kb._worker.submit = spy  # type: ignore[method-assign]
    return seen


# --- persist (UT-040–UT-049) ----------------------------------------------------


def test_ut040_firmware_effect_saved(worker, monkeypatch) -> None:
    kb, persisted = _connected(worker, monkeypatch, FakeKeyboard())
    kb.applyEffect("wave", 5, 40, "random", "up", False, False)
    drain(worker)
    assert persisted == [{"look": WAVE, "power": "on"}]


def test_ut041_solid_saved(worker, monkeypatch) -> None:
    kb, persisted = _connected(worker, monkeypatch, FakeKeyboard())
    kb.setSolidRgb(255, 255, 255)
    drain(worker)
    assert _looks(persisted) == [SolidLook((255, 255, 255))]


def test_ut042_per_key_saved_in_device_coordinates(worker, monkeypatch) -> None:
    fake = FakeKeyboard()
    kb, persisted = _connected(worker, monkeypatch, fake)
    kb.setKeyById("esc", 255, 0, 0, False)
    kb.applyKeyGrid(True)
    drain(worker)
    assert _looks(persisted) == [PerKeyLook(((5, 0, (255, 0, 0)),))]
    assert fake.calls[-1] == ("set_key_colors", {(5, 0): (255, 0, 0)})


def test_ut043_empty_grid_saved(worker, monkeypatch) -> None:
    kb, persisted = _connected(worker, monkeypatch, FakeKeyboard())
    kb.applyKeyGrid(True)
    drain(worker)
    assert _looks(persisted) == [PerKeyLook(())]


def test_ut044_animation_saved_when_started(worker, monkeypatch, tmp_path) -> None:
    script = _animation(tmp_path, wait="0")
    kb, persisted = _connected(worker, monkeypatch, FakeKeyboard())
    kb.playAnimationFile(str(script), 3, False)
    drain(worker)
    assert persisted == [{"look": AnimationLook(str(script.resolve()), 3, False), "power": "on"}]


def test_ut045_disconnect_stops_animation_first(worker, monkeypatch, tmp_path) -> None:
    fake = FakeKeyboard()
    kb, _ = _connected(worker, monkeypatch, fake)
    kb.playAnimationFile(str(_animation(tmp_path)), 1, True)
    _wait_for(lambda: "set_key_colors" in fake.names())
    running_stop = kb._follow_stop
    seen = _spy_submit(kb, running_stop)
    kb.disconnectDevice()
    assert seen == [True]
    drain(worker)
    assert kb.connected is False


def test_ut046_failed_apply_not_saved(worker, monkeypatch) -> None:
    kb, persisted = _connected(worker, monkeypatch, FakeKeyboard(fail_on=frozenset({"set_effect"})))
    kb.applyEffect("wave", 5, 40, "random", "up", False, False)
    drain(worker)
    assert persisted == []


def test_ut047_follow_test_pattern_freeze_not_saved(worker, monkeypatch) -> None:
    kb, persisted = _connected(worker, monkeypatch, FakeKeyboard())
    kb.startFollowScreen(True, 0, 0, 0, 0)
    kb.demoTestPattern()
    kb.freezeAnimation()
    drain(worker)
    assert _looks(persisted) == []


def test_ut048_palette_saved(worker, monkeypatch) -> None:
    kb, persisted = _connected(worker, monkeypatch, FakeKeyboard())
    kb.setPaletteSlotRgb(3, 1, 2, 3)
    drain(worker)
    assert persisted == [{"palette": {3: (1, 2, 3)}}]
    kb.paletteRestore()
    drain(worker)
    assert persisted[-1] == {"palette": KeyboardBackend._DEFAULT_PALETTE}


def test_ut049_brightness_updates_firmware_look(worker, monkeypatch) -> None:
    kb, persisted = _connected(worker, monkeypatch, FakeKeyboard())
    kb.applyEffect("wave", 5, 40, "random", "up", False, False)
    drain(worker)
    kb.requestBrightnessFromUi(30)
    kb._brightness_timer.stop()
    kb._flush_brightness_debounced()
    drain(worker)
    assert persisted[-1] == {"brightness": 30, "look": replace(WAVE, brightness=30)}


# --- light (UT-060–UT-067) --------------------------------------------------------


def test_ut060_light_off(worker, monkeypatch) -> None:
    fake = FakeKeyboard()
    kb, persisted = _connected(worker, monkeypatch, fake)
    assert kb.lightOn is True
    kb.setLightOn(False)
    drain(worker)
    assert fake.names()[-1] == "turn_off"
    assert kb.lightOn is False
    assert persisted[-1] == {"power": "off"}


def test_ut061_light_on_reapplies_saved_look(worker, monkeypatch) -> None:
    fake = FakeKeyboard()
    kb, persisted = _connected(worker, monkeypatch, fake)
    kb.setSolidRgb(255, 255, 255)
    kb.setLightOn(False)
    drain(worker)
    fake.calls.clear()
    kb.setLightOn(True)
    drain(worker)
    assert fake.calls == [("set_color", (255, 255, 255), None, False)]
    assert persisted[-1] == {"power": "on"}
    assert kb.lightOn is True


def test_ut063_apply_while_off_turns_light_on(worker, monkeypatch) -> None:
    kb, persisted = _connected(worker, monkeypatch, FakeKeyboard())
    kb.setLightOn(False)
    drain(worker)
    assert kb.lightOn is False
    kb.applyEffect("wave", 5, 40, "random", "up", False, False)
    drain(worker)
    assert kb.lightOn is True
    assert persisted[-1]["power"] == "on"


def test_ut064_light_off_stops_animation_first(worker, monkeypatch, tmp_path) -> None:
    fake = FakeKeyboard()
    kb, _ = _connected(worker, monkeypatch, fake)
    kb.playAnimationFile(str(_animation(tmp_path)), 1, True)
    _wait_for(lambda: "set_key_colors" in fake.names())
    seen = _spy_submit(kb, kb._follow_stop)
    kb.setLightOn(False)
    assert seen == [True]
    drain(worker)
    assert fake.names()[-1] == "turn_off"


def test_ut065_light_on_uses_session_snapshot(worker, monkeypatch) -> None:
    fake = FakeKeyboard()
    fake.effect = [3, 5, 25, 0, 1, 0]
    kb, _ = _connected(worker, monkeypatch, fake)
    kb.setLightOn(False)
    drain(worker)
    fake.calls.clear()
    kb.setLightOn(True)
    drain(worker)
    assert fake.calls == [("set_effect", [3, 5, 25, 0, 1, 0])]


def test_ut066_light_on_without_look_or_snapshot_uses_rainbow(worker, monkeypatch) -> None:
    fake = FakeKeyboard()
    kb, _ = _connected(worker, monkeypatch, fake)
    kb.setLightOn(True)
    drain(worker)
    assert fake.calls == [("set_effect", KEYBOARD_EFFECTS["rainbow"]())]


def test_ut067_rapid_toggles_apply_in_order(worker, monkeypatch) -> None:
    fake = FakeKeyboard()
    kb, persisted = _connected(worker, monkeypatch, fake)
    kb.setLightOn(False)
    kb.setLightOn(True)
    kb.setLightOn(False)
    drain(worker)
    assert fake.names() == ["turn_off", "set_effect", "turn_off"]
    assert kb.lightOn is False
    assert persisted[-1] == {"power": "off"}


def test_restored_per_key_look_maps_cells_back_to_key_ids(worker, monkeypatch) -> None:
    """Saved device cells → keyId colours (profile + calibration aware) after restore."""
    fake = FakeKeyboard()
    kb, persisted = _connected(worker, monkeypatch, fake)
    kb.setKeyById("esc", 255, 0, 0, False)
    kb.applyKeyGrid(True)
    drain(worker)
    look = _looks(persisted)[-1]

    other, _ = _connected(worker, monkeypatch, FakeKeyboard())
    assert other.keyHexById("esc") != "#ff0000"
    other.restore(KeyboardState("048d:600b", look=look))
    drain(worker)
    assert other.keyHexById("esc") == "#ff0000"


def test_disconnect_and_reconnect_release_the_usb_handle(worker, monkeypatch) -> None:
    """Regression: reconnect hit [Errno 16] Resource busy because the old handle stayed claimed."""
    first, second = FakeKeyboard(), FakeKeyboard()
    devices = iter([first, second])
    monkeypatch.setattr("app.ui.adapters.keyboard_backend.open_keyboard", lambda **kw: next(devices))
    kb = KeyboardBackend(worker)
    kb.connectAt(1, 2)
    drain(worker)
    kb.disconnectDevice()
    drain(worker)
    assert first.names()[-1] == "close"
    kb.connectAt(1, 2)
    kb.connectAt(1, 2)  # reconnect over a live connection closes the previous handle too
    drain(worker)
    assert "close" in second.names()
