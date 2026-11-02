"""Offscreen main.qml journeys for Tuya bulbs (E2E-020–E2E-026, E2E-028)."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QCoreApplication, QMetaObject, QSettings, QUrl, Q_ARG
from PySide6.QtWidgets import QApplication

from avell_storm_rgb.application.bulb_facade import BulbUnreachable
from avell_storm_rgb.application.bulb_inventory import BulbInventory, parse_tinytuya_devices
from avell_storm_rgb.application.device_state import (
    BulbState,
    DeviceState,
    DeviceStateStore,
    default_state_path,
)
from backend_fakes import FakeBulb, drain, drain_bulbs
from gui_helpers import ensure_qapp, find_child_named, load_main_qml_engine, root_quick_window

FIXTURE = Path(__file__).parent / "fixtures" / "tinytuya_devices.json"
QUARTO, ESC, SALA = "eb1a2b3c4d5e6f70819201", "eb1a2b3c4d5e6f70819202", "eb1a2b3c4d5e6f70819203"


@pytest.fixture
def world(tmp_path, monkeypatch):
    ensure_qapp()
    app = QApplication.instance()
    app.setOrganizationName(f"avell_gui_{uuid.uuid4().hex[:12]}")
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qs"))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    FakeBulb.live_connections = 0
    w = {"bulbs": {}, "errors": {}, "engines": [], "available": True}
    monkeypatch.setattr("app.ui.adapters.device_model.enumerate_usb_devices", lambda: [])
    monkeypatch.setattr("app.ui.adapters.app_facade.tuya_available", lambda: w["available"])

    def open_bulb(record, inventory):
        if record.id in w["errors"]:
            raise w["errors"][record.id]
        return w["bulbs"].setdefault(record.id, FakeBulb())

    monkeypatch.setattr("avell_storm_rgb.application.bulb_facade.open_bulb", open_bulb)
    DeviceStateStore(default_state_path()).save(DeviceState())  # no legacy migration
    yield w
    for engine, facade in w["engines"]:
        facade.shutdown()
        engine.deleteLater()


def _import_fixture() -> None:
    BulbInventory().upsert(parse_tinytuya_devices(FIXTURE.read_text(encoding="utf-8"))[0])


def _load(world):
    engine, facade = load_main_qml_engine()
    if facade is None:
        pytest.skip("Kirigami / QML imports missing.")
    world["engines"].append((engine, facade))
    _settle(facade)
    return root_quick_window(engine), facade


def _settle(facade) -> None:
    drain(facade._worker)
    drain_bulbs(facade.bulbs._worker)
    QCoreApplication.processEvents()


def find_item(win, name: str):
    stack = [win.contentItem()]
    while stack:
        item = stack.pop()
        if item.objectName() == name:
            return item
        stack.extend(item.childItems())
    return find_child_named(win, name)


def find_items(win, name: str) -> list:
    out, stack = [], [win.contentItem()]
    while stack:
        item = stack.pop()
        if item.objectName() == name:
            out.append(item)
        stack.extend(item.childItems())
    return out


def _sidebar_titles(win) -> list[str]:
    return [e.property("text") or _entry_title(e) for e in _entries(win)]


def _entries(win) -> list:
    sidebar = find_item(win, "primarySidebar")
    content = sidebar.property("contentItem")
    items = [c for c in content.childItems() if c.objectName().startswith("sidebar")]
    return sorted(items, key=lambda i: i.property("y"))


def _entry_title(entry) -> str:
    stack = [entry]
    while stack:
        item = stack.pop()
        text = item.property("text")
        if isinstance(text, str) and text and text not in ("›", "Unavailable"):
            return text
        stack.extend(item.childItems())
    return ""


def _click(item) -> None:
    QMetaObject.invokeMethod(item, "clicked")
    QCoreApplication.processEvents()


def test_e2e020_import_shows_rows_and_summary(world) -> None:
    win, facade = _load(world)
    panel = find_item(win, "bulbListPanel")
    assert panel is not None
    assert find_item(win, "bulbImportButton") is not None
    assert find_item(win, "bulbEmptyHint").property("visible") is True
    facade.bulbs.importFile(QUrl.fromLocalFile(str(FIXTURE)))
    _settle(facade)
    for bulb_id in (QUARTO, ESC, SALA):
        assert find_item(win, f"bulbRow_{bulb_id}") is not None
    assert find_item(win, "bulbImportSummary").property("text") == "Imported 3 bulbs"
    assert find_item(win, "bulbEmptyHint").property("visible") is False


def test_e2e021_connect_adds_sidebar_entry_and_page(world) -> None:
    _import_fixture()
    win, facade = _load(world)
    _click(find_item(win, f"bulbConnectButton_{ESC}"))
    _settle(facade)
    entries = find_items(win, "sidebarBulbEntry")
    assert len(entries) == 1
    switch = find_item(win, "bulbLightSwitch")
    assert switch.property("enabled") is True and switch.property("checked") is True
    _click(entries[0])
    stack = find_item(win, "deviceContentStack")
    assert stack.property("currentIndex") == 5
    assert find_item(win, "primarySidebar").property("currentIndex") == 1
    page = find_item(win, "bulbPage")
    assert page.property("bulbId") == ESC
    assert find_item(win, "bulbStatusLine").property("text") == "On · White · 192.168.0.22"


def test_e2e022_remove_dialog_cancel_and_confirm(world) -> None:
    _import_fixture()
    win, facade = _load(world)
    panel = find_item(win, "bulbListPanel")
    QMetaObject.invokeMethod(panel, "askRemove", Q_ARG("QVariant", SALA), Q_ARG("QVariant", "Sala"))
    QMetaObject.invokeMethod(panel, "cancelRemove")
    QCoreApplication.processEvents()
    assert find_item(win, f"bulbRow_{SALA}") is not None
    QMetaObject.invokeMethod(panel, "askRemove", Q_ARG("QVariant", SALA), Q_ARG("QVariant", "Sala"))
    QMetaObject.invokeMethod(panel, "confirmRemove")
    _settle(facade)
    assert find_item(win, f"bulbRow_{SALA}") is None
    assert all(r.id != SALA for r in BulbInventory().load())


@pytest.mark.parametrize("action", ["disconnectBulb", "removeBulb"])
def test_e2e023_leaving_bulb_page_returns_to_devices(world, action) -> None:
    _import_fixture()
    DeviceStateStore(default_state_path()).save(DeviceState(bulbs=(BulbState(ESC),)))
    win, facade = _load(world)
    _click(find_items(win, "sidebarBulbEntry")[0])
    stack = find_item(win, "deviceContentStack")
    assert stack.property("currentIndex") == 5
    getattr(facade.bulbs, action)(ESC)
    _settle(facade)
    assert stack.property("currentIndex") == 0
    assert find_items(win, "sidebarBulbEntry") == []


def test_e2e024_unavailable_bulb(world) -> None:
    _import_fixture()
    DeviceStateStore(default_state_path()).save(DeviceState(bulbs=(BulbState(SALA),)))
    world["errors"][SALA] = BulbUnreachable("Sala")
    engine, facade = load_main_qml_engine()
    if facade is None:
        pytest.skip("Kirigami / QML imports missing.")
    world["engines"].append((engine, facade))
    win = root_quick_window(engine)
    QCoreApplication.processEvents()
    # Before the first read lands: Reading…, switch disabled.
    _click(find_items(win, "sidebarBulbEntry")[0])
    assert find_item(win, "bulbStatusLine").property("text") == "Reading…"
    assert find_item(win, "bulbLightSwitch").property("enabled") is False
    _settle(facade)
    entry = find_items(win, "sidebarBulbEntry")[0]
    assert _has_text(entry, "Unavailable")
    assert find_item(win, "bulbLightSwitch").property("enabled") is False
    panel = find_item(win, "bulbUnavailable")
    assert panel.property("visible") is True
    assert panel.property("reason") == "Sala is not reachable on the network"
    assert panel.property("forgetHint") == "Stop reconnecting this bulb. Its key is kept."


def _has_text(root, wanted: str) -> bool:
    stack = [root]
    while stack:
        item = stack.pop()
        if item.property("text") == wanted and item.property("visible"):
            return True
        stack.extend(item.childItems())
    return False


def test_e2e025_sidebar_switch_sends_power(world) -> None:
    _import_fixture()
    from avell_storm_rgb.domain.bulb_color import BulbStatus

    world["bulbs"][ESC] = FakeBulb(status=BulbStatus(False, "white", 50, 30, None))
    DeviceStateStore(default_state_path()).save(DeviceState(bulbs=(BulbState(ESC),)))
    win, facade = _load(world)
    _click(find_items(win, "sidebarBulbEntry")[0])
    switch = find_item(win, "bulbLightSwitch")
    assert switch.property("checked") is False
    switch.setProperty("checked", True)
    QMetaObject.invokeMethod(switch, "toggled")
    _settle(facade)
    assert ("set_power", True) in world["bulbs"][ESC].calls
    assert find_item(win, "bulbLightSwitch").property("checked") is True
    assert find_item(win, "bulbPageSwitch").property("checked") is True


def test_e2e026_no_extra_no_bulb_surface(world) -> None:
    world["available"] = False
    _import_fixture()
    DeviceStateStore(default_state_path()).save(DeviceState(bulbs=(BulbState(ESC),)))
    win, facade = _load(world)
    assert find_item(win, "bulbListPanel") is None
    assert find_items(win, "sidebarBulbEntry") == []
    assert [e.objectName() for e in _entries(win)] == ["sidebarDevicesEntry"]


def test_e2e028_brightness_debounced_to_last_value(world) -> None:
    _import_fixture()
    DeviceStateStore(default_state_path()).save(DeviceState(bulbs=(BulbState(ESC),)))
    win, facade = _load(world)
    _click(find_items(win, "sidebarBulbEntry")[0])
    row = find_item(win, "bulbBrightnessRow")
    for v in (10, 20, 30, 40, 55):
        QMetaObject.invokeMethod(row, "userAdjusted", Q_ARG(int, v))
        QCoreApplication.processEvents()
    end = time.monotonic() + 0.6
    while time.monotonic() < end:
        QCoreApplication.processEvents()
        time.sleep(0.02)
    _settle(facade)
    sent = [c for c in world["bulbs"][ESC].calls if c[0] == "set_brightness"]
    assert sent == [("set_brightness", 55)]


def test_e2e027_follow_combo_and_message(world) -> None:
    _import_fixture()
    DeviceStateStore(default_state_path()).save(DeviceState(bulbs=(BulbState(ESC),)))
    win, facade = _load(world)
    facade.keyboard.followScreenAvailable = False  # no screen extra
    facade.bulbs._changed()
    _click(find_items(win, "sidebarBulbEntry")[0])
    combo = find_item(win, "bulbFollowCombo")
    # No keyboard, no LED bar, no screen extra: only "none".
    assert combo.property("count") == 1
    message = find_item(win, "bulbFollowMessage")
    assert message.property("visible") is False
    facade.bulbs.setFollow(ESC, "keyboard")
    _settle(facade)
    text = find_item(win, "bulbFollowMessage").property("text")
    assert text.startswith(
        "Following the keyboard. Other apps on your network can't control this bulb locally while it follows."
    )
    assert "Paused: Keyboard not connected." in text
