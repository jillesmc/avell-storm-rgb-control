"""Smoke: QML engine loads main window (PySide6 + Kirigami QML from the system)."""

from __future__ import annotations

from PySide6.QtCore import QEventLoop, QTimer

from gui_helpers import load_main_qml_engine, ensure_qapp


def test_main_qml_loads():
    ensure_qapp()
    engine, facade = load_main_qml_engine()
    if facade is None:
        import pytest

        pytest.skip(
            "Kirigami / QML imports missing (install distro kirigami for Qt6; "
            "set QML_IMPORT_PATH if needed)."
        )

    loop = QEventLoop()
    QTimer.singleShot(100, loop.quit)
    loop.exec()
    facade.shutdown()
