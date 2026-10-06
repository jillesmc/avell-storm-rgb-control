"""AppFacade: remember / forget / unavailable devices and legacy migration (UT-030–UT-038, UT-090–UT-093)."""

from __future__ import annotations

import json

import pytest
import usb.core

from avell_storm_rgb.application.device_state import (
    DeviceState,
    KeyboardState,
    LedBarLook,
    LedBarState,
    SolidLook,
)
from facade_harness import KB_ROW, LED_ROW, LEGACY_AUTO_CONNECT_KEY, drain, rig  # noqa: F401

STATIC = LedBarLook(((255, 0, 0),), "static", 50, 3)


# --- device memory (UT-030–UT-038) ---------------------------------------------


def test_ut030_connect_remembers(rig) -> None:
    rig.rows = [KB_ROW]
    f = rig.facade()
    f.refreshDevices()
    f.connectDevice("keyboard", 3, 9)
    drain(f._worker)
    assert f.keyboardRemembered is True
    saved = json.loads(rig.state_path.read_text())["devices"]["keyboard"]
    assert saved["usb_id"] == "048d:ce00"
    assert saved["remembered"] is True


def test_ut031_failed_connect_remembers_nothing(rig) -> None:
    rig.rows = [KB_ROW]
    rig.kb_error = usb.core.USBError("Access denied", errno=13)
    f = rig.facade()
    f.refreshDevices()
    f.connectDevice("keyboard", 3, 9)
    drain(f._worker)
    assert f.keyboardRemembered is False
    assert not rig.state_path.exists()
    assert "Access denied" in f.state.lastError


def test_ut032_other_device_of_same_kind_replaces_id_keeps_look(rig) -> None:
    rig.save(DeviceState(keyboard=KeyboardState("048d:ce00", look=SolidLook((1, 2, 3)))))
    rig.rows = [{**KB_ROW, "pid": 0x6004, "bus": 1, "addr": 1}]
    f = rig.facade()
    f.refreshDevices()
    f.connectDevice("keyboard", 1, 1)
    drain(f._worker)
    kb = rig.store().load().keyboard
    assert kb.usb_id == "048d:6004"
    assert kb.look == SolidLook((1, 2, 3))


def test_ut033_double_connect_remembers_once(rig) -> None:
    rig.rows = [KB_ROW]
    f = rig.facade()
    saves: list = []
    original = f._store.save
    f._store.save = lambda state: (saves.append(state), original(state))  # type: ignore[method-assign]
    f.refreshDevices()
    f.connectDevice("keyboard", 3, 9)
    f.connectDevice("keyboard", 3, 9)
    drain(f._worker)
    assert len(saves) == 1
    assert f.keyboardRemembered is True


def test_ut034_disconnect_forgets_and_keeps_look(rig) -> None:
    rig.rows = [LED_ROW]
    f = rig.facade()
    f.refreshDevices()
    f.connectDevice("led_bar", 1, 4)
    drain(f._worker)
    f.ledBar.applyEffect("breathing")
    drain(f._worker)
    f.disconnectDeviceKind("led_bar")
    drain(f._worker)
    assert f.ledBarRemembered is False
    led = rig.store().load().led_bar
    assert led.remembered is False
    assert led.look is not None and led.look.effect == "breathing"
    assert led.power == "on"


def test_ut035_remembered_but_absent_is_unavailable(rig) -> None:
    rig.save(DeviceState(keyboard=KeyboardState("048d:ce00")))
    f = rig.facade()
    rig.start(f)
    assert f.keyboardRemembered is True
    assert f.keyboardUnavailableReason == "Not found (048d:ce00)"
    assert f.keyboard.connected is False


def test_ut036_forget_unavailable_keeps_look(rig) -> None:
    rig.save(DeviceState(keyboard=KeyboardState("048d:ce00", look=SolidLook((9, 9, 9)))))
    f = rig.facade()
    rig.start(f)
    f.forgetDevice("keyboard")
    assert f.keyboardRemembered is False
    kb = rig.store().load().keyboard
    assert kb.remembered is False and kb.look == SolidLook((9, 9, 9))


def test_ut037_retry_while_still_absent(rig) -> None:
    rig.save(DeviceState(keyboard=KeyboardState("048d:ce00")))
    f = rig.facade()
    rig.start(f)
    f.retryDevice("keyboard")
    drain(f._worker)
    assert f.keyboardUnavailableReason == "Not found (048d:ce00)"
    assert f.state.lastError == ""


def test_ut038_usb_error_reason(rig) -> None:
    rig.save(DeviceState(keyboard=KeyboardState("048d:ce00")))
    rig.rows = [KB_ROW]
    rig.kb_error = usb.core.USBError("Access denied", errno=13)
    f = rig.facade()
    rig.start(f)
    assert f.keyboardUnavailableReason == "USBError: [Errno 13] Access denied"


# --- migration (UT-090–UT-093) ----------------------------------------------------


def test_ut090_legacy_absent_remembers_first_devices(rig) -> None:
    rig.rows = [KB_ROW, {**KB_ROW, "addr": 10}, LED_ROW]
    f = rig.facade()
    rig.start(f)
    state = rig.store().load()
    assert state.keyboard == KeyboardState("048d:ce00")
    assert state.led_bar == LedBarState("048d:7001")
    assert not rig.settings().contains(LEGACY_AUTO_CONNECT_KEY)


def test_ut091_legacy_false_remembers_nothing(rig) -> None:
    rig.settings().setValue(LEGACY_AUTO_CONNECT_KEY, False)
    rig.rows = [KB_ROW, LED_ROW]
    f = rig.facade()
    rig.start(f)
    assert json.loads(rig.state_path.read_text()) == {"version": 1, "devices": {}}
    assert not rig.settings().contains(LEGACY_AUTO_CONNECT_KEY)
    assert f.keyboard.connected is False


def test_ut092_no_devices_writes_empty_state(rig) -> None:
    f = rig.facade()
    rig.start(f)
    assert json.loads(rig.state_path.read_text()) == {"version": 1, "devices": {}}
    assert not rig.settings().contains(LEGACY_AUTO_CONNECT_KEY)


def test_ut093_existing_state_skips_migration(rig) -> None:
    rig.save(DeviceState())
    rig.settings().setValue(LEGACY_AUTO_CONNECT_KEY, True)
    rig.rows = [KB_ROW]
    f = rig.facade()
    assert not rig.settings().contains(LEGACY_AUTO_CONNECT_KEY)
    rig.start(f)
    assert f.keyboardRemembered is False
    assert f.keyboard.connected is False


@pytest.mark.parametrize("kind", ["keyboard", "led_bar"])
def test_unknown_kind_is_ignored(rig, kind) -> None:
    f = rig.facade()
    f.forgetDevice("mouse")
    f.disconnectDeviceKind("mouse")
    assert getattr(f, "keyboardRemembered" if kind == "keyboard" else "ledBarRemembered") is False
