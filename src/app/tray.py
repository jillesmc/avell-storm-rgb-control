"""System tray for the QML application (show/hide/quit)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


class TrayController(QObject):
    def __init__(
        self,
        window: QQuickWindow,
        icon_search_dir: Path | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._window = window
        self._tray = QSystemTrayIcon(self)

        self._tray.setIcon(self._resolve_icon(icon_search_dir))
        self._tray.setToolTip(window.title() or "Avell Storm RGB")

        menu = QMenu()
        act_show = QAction("Show", self)
        act_hide = QAction("Hide", self)
        act_quit = QAction("Quit", self)
        menu.addAction(act_show)
        menu.addAction(act_hide)
        menu.addSeparator()
        menu.addAction(act_quit)
        self._tray.setContextMenu(menu)

        act_show.triggered.connect(self._show_window)
        act_hide.triggered.connect(self._hide_window)
        act_quit.triggered.connect(QApplication.quit)
        self._tray.activated.connect(self._on_tray_activated)

        self._tray.show()

    @staticmethod
    def _resolve_icon(search_dir: Path | None) -> QIcon:
        if search_dir and search_dir.is_dir():
            for name in ("tray.png", "tray.svg", "icon.png", "icon.svg"):
                p = search_dir / name
                if p.is_file():
                    return QIcon(str(p))
        for theme in (
            "adjustrgb",
            "input-keyboard",
            "preferences-desktop-keyboard-symbolic",
            "preferences-desktop-color",
        ):
            ic = QIcon.fromTheme(theme)
            if not ic.isNull():
                return ic
        return QIcon()

    @Slot()
    def _show_window(self) -> None:
        self._window.show()
        self._window.raise_()
        self._window.requestActivate()

    @Slot()
    def _hide_window(self) -> None:
        self._window.hide()

    @Slot()
    def _toggle_window(self) -> None:
        if self._window.isVisible():
            self._hide_window()
        else:
            self._show_window()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self._toggle_window()
