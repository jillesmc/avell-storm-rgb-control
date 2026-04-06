"""Shared setup for QML GUI tests (mirrors src/app/main.py engine paths and style)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from app.qml_paths import add_qml_import_paths, configure_quick_controls_style
from app.ui.adapters.app_facade import AppFacade

REPO_ROOT = Path(__file__).resolve().parents[1]


def ensure_qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    inst = QApplication.instance()
    return inst if inst is not None else QApplication([])


def ui_dir() -> Path:
    return REPO_ROOT / "src" / "app" / "ui"


def load_main_qml_engine() -> tuple[QQmlApplicationEngine, AppFacade | None]:
    """Build engine like main.py: style, import paths, App facade, main.qml loaded."""
    configure_quick_controls_style()
    engine = QQmlApplicationEngine()
    ui = ui_dir()
    engine.addImportPath(str(ui))
    add_qml_import_paths(engine)
    facade = AppFacade(engine)
    engine.rootContext().setContextProperty("App", facade)
    engine.load(QUrl.fromLocalFile(str(ui / "main.qml")))
    if not engine.rootObjects():
        return engine, None
    return engine, facade


def root_quick_window(engine: QQmlApplicationEngine) -> QQuickWindow | None:
    roots = engine.rootObjects()
    if not roots:
        return None
    w = roots[0]
    return w if isinstance(w, QQuickWindow) else None


def find_child_named(root: QObject, name: str) -> QObject | None:
    return root.findChild(QObject, name, Qt.FindChildOption.FindChildrenRecursively)
