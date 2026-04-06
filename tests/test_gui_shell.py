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


def test_shell_has_nav_and_stack_and_pages():
    ensure_qapp()
    engine, facade = load_main_qml_engine()
    if facade is None:
        pytest.skip("Kirigami / QML imports missing.")

    win = root_quick_window(engine)
    assert win is not None

    nav = find_child_named(win, "mainNavTabs")
    assert nav is not None, "mainNavTabs (NavigationTabBar) missing"

    stack = find_child_named(win, "mainStack")
    assert stack is not None, "mainStack (StackLayout) missing"

    for name in ("devicesPage", "keyboardPage", "ledBarPage", "aboutPage"):
        obj = find_child_named(win, name)
        assert obj is not None, f"{name} missing"

    stack = find_child_named(win, "mainStack")
    assert stack is not None
    assert stack.property("currentIndex") == 0, "stack should start on Devices (index 0), not bind to tab bar index"

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
