"""Offscreen main.qml: remembered devices in the sidebar, light switch, unavailable page (E2E-004–E2E-007)."""

from __future__ import annotations

import uuid

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QMetaObject, QObject, QSettings
from PySide6.QtWidgets import QApplication

from avell_storm_rgb.application.device_state import (
    DeviceState,
    DeviceStateStore,
    KeyboardState,
    LedBarState,
    default_state_path,
)
from backend_fakes import FakeKeyboard, FakeLedBar, drain
from gui_helpers import ensure_qapp, find_child_named, load_main_qml_engine, root_quick_window

KB_ROW = {"kind": "keyboard", "bus": 3, "addr": 9, "vid": 0x048D, "pid": 0xCE00, "label": "kb"}


@pytest.fixture
def world(tmp_path, monkeypatch):
    ensure_qapp()
    app = QApplication.instance()
    app.setOrganizationName(f"avell_gui_{uuid.uuid4().hex[:12]}")
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qs"))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    w = {"rows": [], "kb": FakeKeyboard(), "led": FakeLedBar(), "engines": []}
    monkeypatch.setattr("app.ui.adapters.device_model.enumerate_usb_devices", lambda: [dict(r) for r in w["rows"]])
    monkeypatch.setattr("app.ui.adapters.keyboard_backend.open_keyboard", lambda **kw: w["kb"])
    monkeypatch.setattr("app.ui.adapters.led_bar_backend.open_led_bar_at", lambda bus, addr: w["led"])
    yield w
    for engine, facade in w["engines"]:
        facade._worker.shutdown(wait=True)
        engine.deleteLater()


def _load(world):
    engine, facade = load_main_qml_engine()
    if facade is None:
        pytest.skip("Kirigami / QML imports missing.")
    world["engines"].append((engine, facade))
    drain(facade._worker)
    return root_quick_window(engine), facade


def find_item(win, name: str):
    """Depth-first over the visual item tree (ListView delegates have no QObject parent)."""
    stack = [win.contentItem()]
    while stack:
        item = stack.pop()
        if item.objectName() == name:
            return item
        stack.extend(item.childItems())
    return find_child_named(win, name)


def _save(state: DeviceState) -> None:
    DeviceStateStore(default_state_path()).save(state)


def _texts(root: QObject) -> list[str]:
    out = []
    for child in root.findChildren(QObject):
        text = child.property("text")
        if isinstance(text, str) and child.property("visible") is not False:
            out.append(text)
    return out


def test_e2e004_connect_remembers_and_survives_restart(world) -> None:
    _save(DeviceState())  # no legacy migration
    world["rows"] = [KB_ROW]
    win, facade = _load(world)
    assert find_item(win, "sidebarKeyboardEntry") is None

    facade.connectDevice("keyboard", 3, 9)
    drain(facade._worker)
    assert find_item(win, "sidebarKeyboardEntry") is not None

    win2, facade2 = _load(world)
    assert find_item(win2, "sidebarKeyboardEntry") is not None
    assert facade2.keyboard.connected is True


def test_e2e005_light_switch_and_forget_returns_to_devices(world) -> None:
    _save(DeviceState(keyboard=KeyboardState("048d:ce00")))
    world["rows"] = [KB_ROW]
    win, facade = _load(world)

    switch = find_item(win, "keyboardLightSwitch")
    assert switch is not None and switch.property("checked") is True
    QMetaObject.invokeMethod(switch, "toggle")
    QMetaObject.invokeMethod(switch, "toggled")
    drain(facade._worker)
    assert world["kb"].names()[-1] == "turn_off"
    assert switch.property("checked") is False

    stack = find_child_named(win, "deviceContentStack")
    win.setProperty("primarySection", 1)
    stack.setProperty("currentIndex", 1)
    facade.disconnectDeviceKind("keyboard")
    drain(facade._worker)
    assert find_item(win, "sidebarKeyboardEntry") is None
    assert stack.property("currentIndex") == 0


def test_e2e006_unavailable_device_page(world) -> None:
    _save(DeviceState(led_bar=LedBarState("048d:7001")))
    win, facade = _load(world)
    assert find_item(win, "sidebarLedBarEntry") is not None
    switch = find_item(win, "ledBarLightSwitch")
    assert switch.property("enabled") is False
    assert switch.property("checked") is True  # saved light state "on" (US-008.EC-3)
    win.setProperty("primarySection", 2)
    find_child_named(win, "deviceContentStack").setProperty("currentIndex", 2)
    panel = find_child_named(win, "ledBarUnavailable")
    assert panel is not None and panel.property("visible") is True
    assert panel.property("reason") == "Not found (048d:7001)"


def test_e2e007_power_buttons_and_auto_connect_option_are_gone(world) -> None:
    _save(DeviceState())
    win, facade = _load(world)
    kb = find_child_named(win, "keyboardPage")
    lb = find_child_named(win, "ledBarPage")
    for page in (kb, lb):
        texts = _texts(page)
        assert "Power off" not in texts and "Power on" not in texts
    all_texts = _texts(win)
    assert not any(t.startswith("Auto-connect") for t in all_texts)
    assert find_child_named(kb, "keyboardApplyConfig") is not None
    assert find_child_named(lb, "ledBarApplyConfig") is not None
