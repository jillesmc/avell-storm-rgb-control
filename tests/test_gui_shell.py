"""Structural tests for main QML shell (objectName contracts, Kirigami navigation)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QEventLoop, QTimer

from gui_helpers import (
    ensure_qapp,
    find_child_named,
    load_main_qml_engine,
    root_quick_window,
)


def test_shell_has_sidebar_stack_and_pages():
    ensure_qapp()
    engine, facade = load_main_qml_engine()
    if facade is None:
        pytest.skip("Kirigami / QML imports missing.")

    win = root_quick_window(engine)
    assert win is not None

    sidebar = find_child_named(win, "primarySidebar")
    assert sidebar is not None, "primarySidebar missing"

    stack = find_child_named(win, "deviceContentStack")
    assert stack is not None, "deviceContentStack missing"

    for name in ("devicesPage", "keyboardPage", "ledBarPage", "settingsPage", "aboutPage"):
        obj = find_child_named(win, name)
        assert obj is not None, f"{name} missing"

    assert stack.property("currentIndex") == 0, "stack should start on Devices (index 0)"

    kb_nav = find_child_named(win, "keyboardSubNav")
    assert kb_nav is not None, "keyboardSubNav missing"

    loop = QEventLoop()
    QTimer.singleShot(50, loop.quit)
    loop.exec()
    facade.shutdown()


def test_keyboard_effect_grid_exists():
    ensure_qapp()
    engine, facade = load_main_qml_engine()
    if facade is None:
        pytest.skip("Kirigami / QML imports missing.")

    win = root_quick_window(engine)
    grid = find_child_named(win, "keyboardEffectGrid")
    assert grid is not None
    facade.shutdown()


def test_device_error_inline_exists():
    ensure_qapp()
    engine, facade = load_main_qml_engine()
    if facade is None:
        pytest.skip("Kirigami / QML imports missing.")

    win = root_quick_window(engine)
    inline = find_child_named(win, "deviceErrorInline")
    assert inline is not None
    facade.shutdown()


def test_keyboard_and_led_apply_config_buttons_exist():
    ensure_qapp()
    engine, facade = load_main_qml_engine()
    if facade is None:
        pytest.skip("Kirigami / QML imports missing.")

    win = root_quick_window(engine)
    kb = find_child_named(win, "keyboardPage")
    lb = find_child_named(win, "ledBarPage")
    assert kb is not None
    assert lb is not None
    assert find_child_named(kb, "keyboardApplyConfig") is not None
    assert find_child_named(lb, "ledBarApplyConfig") is not None
    facade.shutdown()
