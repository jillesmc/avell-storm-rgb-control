"""PySide6 + QML entrypoint for the desktop GUI."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

from app.logutil import setup_logging, strip_verbose_argv
from app.qml_paths import add_qml_import_paths, configure_quick_controls_style
from app.tray import TrayController
from app.ui.adapters.app_facade import AppFacade


def main() -> int:
    start_in_background = "--background" in sys.argv
    qt_argv, verbose = strip_verbose_argv(
        [arg for arg in sys.argv if arg != "--background"]
    )
    setup_logging(verbose=verbose)

    configure_quick_controls_style()

    app = QApplication(qt_argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Avell Storm RGB")
    app.setOrganizationName("avell-storm-rgb")

    engine = QQmlApplicationEngine()
    facade = AppFacade(engine)
    engine.rootContext().setContextProperty("App", facade)
    app.aboutToQuit.connect(facade.shutdown)

    app_dir = Path(__file__).resolve().parent
    ui = app_dir / "ui"
    engine.addImportPath(str(ui))
    add_qml_import_paths(engine)

    engine.load(QUrl.fromLocalFile(str(ui / "main.qml")))

    roots = engine.rootObjects()
    if not roots:
        print(
            "QML failed to load. Install Kirigami 6 (e.g. distro package kirigami, "
            "sometimes kirigami2 for Qt6) so org.kde.kirigami is on QML_IMPORT_PATH. "
            "See README.",
            file=sys.stderr,
        )
        return 1

    window = roots[0]
    if not isinstance(window, QQuickWindow):
        print("Unexpected QML root object.", file=sys.stderr)
        return 1

    repo_root = app_dir.parents[1]
    icon_dir = repo_root / "assets" / "gui"
    app_icon = TrayController._resolve_icon(icon_dir if icon_dir.is_dir() else None)
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
        window.setIcon(app_icon)
    TrayController(window, app_icon, icon_dir if icon_dir.is_dir() else None, parent=app)

    if start_in_background:
        window.hide()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
