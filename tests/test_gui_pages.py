"""Regression: modular pages under ui/pages compile with the same engine setup as main."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

pytest.importorskip("PySide6.QtCore")

from app.qml_paths import add_qml_import_paths, configure_quick_controls_style
from app.ui.adapters.app_facade import AppFacade

from gui_helpers import ensure_qapp, ui_dir


@pytest.mark.parametrize(
    "qml_name",
    [
        "DevicesPage.qml",
        "KeyboardPage.qml",
        "LedBarPage.qml",
        "AppAboutPage.qml",
        "SettingsPage.qml",
    ],
)
def test_page_component_ready(qml_name: str) -> None:
    ensure_qapp()
    configure_quick_controls_style()

    engine = QQmlApplicationEngine()
    ui = ui_dir()
    engine.addImportPath(str(ui))
    add_qml_import_paths(engine)
    facade = AppFacade(engine)
    engine.rootContext().setContextProperty("App", facade)

    comp = QQmlComponent(engine)
    comp.loadUrl(QUrl.fromLocalFile(str(ui / "pages" / qml_name)))
    assert comp.isReady(), comp.errorString()
    facade.shutdown()
