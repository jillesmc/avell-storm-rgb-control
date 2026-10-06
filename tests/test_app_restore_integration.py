"""AppFacade + backends + real UsbWorker + state file, fake USB (IT-001–IT-012)."""

from __future__ import annotations

import json
import threading

from avell_storm_rgb.application.device_state import (
    AnimationLook,
    DeviceState,
    FirmwareEffectLook,
    KeyboardState,
    LedBarLook,
    LedBarState,
    SolidLook,
)
from avell_storm_rgb.domain.ledbar_colors import PALETTES
from avell_storm_rgb.infrastructure.usb.ite8291_usb import KEYBOARD_EFFECTS
from facade_harness import KB_ROW, LED_ROW, LEGACY_AUTO_CONNECT_KEY, drain, rig, wait_until  # noqa: F401

WAVE = FirmwareEffectLook("wave", 5, 40, "random", "up", False, False)
BREATHING = LedBarLook(((255, 0, 0), (0, 0, 255)), "breathing", 75, 3)


def test_it001_connect_writes_remembered_device(rig) -> None:
    rig.rows = [KB_ROW]
    f = rig.facade()
    changed: list[bool] = []
    f.deviceMemoryChanged.connect(lambda: changed.append(True))
    f.refreshDevices()
    f.connectDevice("keyboard", 3, 9)
    drain(f._worker)
    assert rig.store().load().keyboard == KeyboardState("048d:ce00")
    assert changed


def test_it002_startup_restores_led_bar_then_keyboard(rig) -> None:
    rig.save(DeviceState(
        keyboard=KeyboardState("048d:ce00", brightness=40, palette={1: (255, 0, 0)}, look=WAVE),
        led_bar=LedBarState("048d:7001", look=BREATHING),
    ))
    rig.rows = [{**KB_ROW, "bus": 7, "addr": 7}, {**LED_ROW, "bus": 8, "addr": 8}]
    f = rig.facade()
    rig.start(f)
    assert f.keyboard.connected and f.ledBar.connected
    devices = [d for d, _ in rig.journal]
    first_kb = devices.index("FakeKeyboard")
    assert "FakeLedBar" not in devices[first_kb:]
    assert [n for d, n in rig.journal if d == "FakeKeyboard"] == [
        "set_palette_color", "set_brightness", "set_effect",
    ]
    assert rig.kb.calls[-1] == ("set_effect", KEYBOARD_EFFECTS["wave"](speed=5, brightness=40, direction=3))


def test_it003_unavailable_then_retry(rig) -> None:
    rig.save(DeviceState(led_bar=LedBarState("048d:7001", look=BREATHING)))
    f = rig.facade()
    rig.start(f)
    assert f.ledBarUnavailableReason == "Not found (048d:7001)"
    assert f.state.lastError == ""
    rig.rows = [LED_ROW]
    f.retryDevice("led_bar")
    drain(f._worker)
    assert f.ledBar.connected
    assert f.ledBarUnavailableReason == ""
    assert ("apply_visual_effect", "breathing") in rig.led.calls


def test_it004_forgotten_device_reconnects_with_its_look(rig) -> None:
    rig.rows = [LED_ROW]
    f = rig.facade()
    f.refreshDevices()
    f.connectDevice("led_bar", 1, 4)
    drain(f._worker)
    f.ledBar.applyEffect("wave")
    drain(f._worker)
    f.disconnectDeviceKind("led_bar")
    drain(f._worker)

    g = rig.facade()
    rig.start(g)
    assert g.ledBar.connected is False
    rig.led.calls.clear()
    g.connectDevice("led_bar", 1, 4)
    drain(g._worker)
    assert g.ledBarRemembered is True
    assert rig.led.calls[-1] == ("apply_visual_effect", "wave")


def test_it005_looks_survive_restart_and_are_written_on_gui_thread(rig) -> None:
    rig.rows = [KB_ROW, LED_ROW]
    f = rig.facade()
    threads: list[bool] = []
    original = f._store.save
    f._store.save = lambda s: (threads.append(threading.current_thread() is threading.main_thread()), original(s))  # type: ignore[method-assign]
    f.refreshDevices()
    f.connectDevice("keyboard", 3, 9)
    f.connectDevice("led_bar", 1, 4)
    drain(f._worker)
    f.keyboard.setSolidRgb(1, 2, 3)
    f.ledBar.applyPalette("fire", "wave")
    drain(f._worker)
    state = rig.store().load()
    assert state.keyboard.look == SolidLook((1, 2, 3))
    assert state.led_bar.look == LedBarLook(tuple(PALETTES["fire"]), "wave", 50, 3)
    assert threads and all(threads)


def test_it006_forever_animation_restored_last_and_stopped_by_light_off(rig, tmp_path) -> None:
    script = tmp_path / "anim"
    script.write_text("pos 0 0 255,0,0\napply\nwait 0.02\n")
    rig.save(DeviceState(
        keyboard=KeyboardState("048d:ce00", look=AnimationLook(str(script), 1, True)),
        led_bar=LedBarState("048d:7001", look=BREATHING),
    ))
    rig.rows = [KB_ROW, LED_ROW]
    f = rig.facade()
    f.refreshDevices()
    f.restoreRememberedDevices()
    wait_until(lambda: ("FakeKeyboard", "set_key_colors") in rig.journal)
    first_anim = rig.journal.index(("FakeKeyboard", "set_key_colors"))
    assert ("FakeLedBar", "apply_visual_effect") in rig.journal[:first_anim]
    f.keyboard.setLightOn(False)
    drain(f._worker)
    assert rig.kb.names()[-1] == "turn_off"


def test_it007_missing_animation_warns_and_keeps_look(rig, tmp_path) -> None:
    missing = str(tmp_path / "gone")
    rig.save(DeviceState(keyboard=KeyboardState("048d:ce00", look=AnimationLook(missing, 1, True))))
    rig.rows = [KB_ROW]
    f = rig.facade()
    rig.start(f)
    assert f.state.lastError == (
        f"Keyboard: saved animation file not found: {missing}. Light state restored; look not applied."
    )
    assert rig.store().load().keyboard.look == AnimationLook(missing, 1, True)


def test_it008_failing_led_restore_does_not_block_keyboard(rig) -> None:
    rig.save(DeviceState(
        keyboard=KeyboardState("048d:ce00", look=WAVE),
        led_bar=LedBarState("048d:7001", look=BREATHING),
    ))
    rig.rows = [KB_ROW, LED_ROW]
    rig.led = None
    f = rig.facade()
    rig.led.fail_on = frozenset({"apply_visual_effect"})
    rig.start(f)
    assert "apply_visual_effect failed" in f.state.lastError
    assert rig.kb.names()[-1] == "set_effect"


def test_it009_user_change_after_restore_wins(rig) -> None:
    rig.save(DeviceState(keyboard=KeyboardState("048d:ce00", look=WAVE)))
    rig.rows = [KB_ROW]
    f = rig.facade()
    f.refreshDevices()
    f.restoreRememberedDevices()
    f.keyboard.applyEffect("breathing", 3, 20, "red", "none", False, False)
    drain(f._worker)
    assert rig.store().load().keyboard.look.effect == "breathing"
    assert rig.kb.calls[-1] == ("set_effect", KEYBOARD_EFFECTS["breathing"](speed=3, brightness=20, color=1))


def test_it010_light_off_is_restored(rig) -> None:
    rig.rows = [KB_ROW]
    f = rig.facade()
    f.refreshDevices()
    f.connectDevice("keyboard", 3, 9)
    drain(f._worker)
    f.keyboard.applyEffect("wave", 5, 40, "random", "up", False, False)
    f.keyboard.setLightOn(False)
    drain(f._worker)

    rig.kb.calls.clear()
    rig.kb.off = False
    g = rig.facade()
    rig.start(g)
    assert rig.kb.names() == ["turn_off"]
    assert g.keyboard.lightOn is False


def test_it011_migration_end_to_end(rig) -> None:
    rig.settings().setValue(LEGACY_AUTO_CONNECT_KEY, "true")
    rig.rows = [KB_ROW, LED_ROW]
    f = rig.facade()
    rig.start(f)
    assert f.keyboard.connected and f.ledBar.connected
    assert f.keyboardRemembered and f.ledBarRemembered
    assert not rig.settings().contains(LEGACY_AUTO_CONNECT_KEY)


def test_it012_invalid_state_file_is_quarantined(rig) -> None:
    rig.state_path.parent.mkdir(parents=True)
    rig.state_path.write_text("not json")
    rig.rows = [KB_ROW]
    f = rig.facade()
    assert (rig.state_path.parent / "state.json.invalid").read_text() == "not json"
    assert f.keyboardRemembered is False
    assert f.state.lastError.startswith("Saved device state was unreadable")
    rig.start(f)
    assert f.keyboard.connected is False  # no auto-migration over a broken file
    f.connectDevice("keyboard", 3, 9)
    drain(f._worker)
    assert json.loads(rig.state_path.read_text())["devices"]["keyboard"]["usb_id"] == "048d:ce00"
