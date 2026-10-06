"""Settings autostart checkbox must update backend when toggled (QML binding)."""

from __future__ import annotations

import sys

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QEventLoop, QMetaObject, QTimer
from PySide6.QtWidgets import QApplication

from app.core import xdg_autostart
from gui_helpers import find_child_named, load_main_qml_engine, root_quick_window


def test_settings_launch_at_login_checkbox_toggle_writes_autostart(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    path = xdg_autostart.autostart_file_path()
    if path.is_file():
        path.unlink()

    app = QApplication.instance() or QApplication([])
    engine, facade = load_main_qml_engine()
    if facade is None:
        pytest.skip("Kirigami / QML imports missing.")

    win = root_quick_window(engine)
    assert win is not None
    win.setProperty("primarySection", 3)
    find_child_named(win, "deviceContentStack").setProperty("currentIndex", 3)

    settings = find_child_named(win, "settingsPage")
    checkbox = find_child_named(settings, "launchAtLoginCheck")
    assert checkbox is not None
    assert facade.launchAtLogin is False

    assert QMetaObject.invokeMethod(checkbox, "click") is True
    loop = QEventLoop()
    QTimer.singleShot(200, loop.quit)
    loop.exec()

    assert facade.launchAtLogin is True
    assert xdg_autostart.is_enabled() is True
    assert checkbox.property("checked") is True
    facade.shutdown()
