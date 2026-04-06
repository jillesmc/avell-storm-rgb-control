"""QML import roots and Qt Quick Controls 2 style (KDE Breeze vs neutral fallback)."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QLibraryInfo
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle


def ensure_qml_import_path_for_process() -> None:
    """Prepend system Qt6 QML roots to :envvar:`QML_IMPORT_PATH`.

    PySide6 bundles its own Qt; :func:`QQmlApplicationEngine.addImportPath` does **not**
    affect how :class:`PySide6.QtQuickControls2.QQuickStyle` resolves third-party styles
    such as ``org.kde.desktop``. Without system paths in the process environment, Breeze
    may silently fail to load and controls fall back to a generic look even when
    ``/usr/lib/qt6/qml/org/kde/desktop`` exists on disk.
    """
    prepend_resolved: list[str] = []
    for candidate in (
        Path("/usr/lib/qt6/qml"),
        Path("/usr/lib64/qt6/qml"),
        Path("/usr/share/qt6/qml"),
    ):
        if candidate.is_dir():
            prepend_resolved.append(str(candidate.resolve()))
    qml = QLibraryInfo.path(QLibraryInfo.LibraryPath.QmlImportsPath)
    if qml:
        p = str(Path(qml).resolve())
        if p not in prepend_resolved:
            prepend_resolved.append(p)
    existing = os.environ.get("QML_IMPORT_PATH", "").strip()
    tail = [x.strip() for x in existing.split(os.pathsep) if x.strip()]
    merged: list[str] = []
    for part in prepend_resolved + tail:
        if part not in merged:
            merged.append(part)
    os.environ["QML_IMPORT_PATH"] = os.pathsep.join(merged)


def ensure_qt_plugin_path_for_process() -> None:
    """Prepend distro Qt6 plugin dirs so style/platform plugins can load (optional)."""
    prepend_resolved: list[str] = []
    for candidate in (Path("/usr/lib/qt6/plugins"), Path("/usr/lib64/qt6/plugins")):
        if candidate.is_dir():
            prepend_resolved.append(str(candidate.resolve()))
    existing = os.environ.get("QT_PLUGIN_PATH", "").strip()
    tail = [x.strip() for x in existing.split(os.pathsep) if x.strip()]
    merged: list[str] = []
    for part in prepend_resolved + tail:
        if part not in merged:
            merged.append(part)
    if merged:
        os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(merged)


def qml_import_candidates() -> list[Path]:
    """Ordered search path for QML modules (Kirigami, org.kde.desktop, PySide6 embed)."""
    out: list[Path] = []
    for candidate in (
        Path("/usr/lib/qt6/qml"),
        Path("/usr/lib64/qt6/qml"),
        Path("/usr/share/qt6/qml"),
    ):
        if candidate.is_dir():
            out.append(candidate)
    qml = QLibraryInfo.path(QLibraryInfo.LibraryPath.QmlImportsPath)
    if qml:
        out.append(Path(qml))
    extra = os.environ.get("QML_IMPORT_PATH", "")
    for part in extra.split(os.pathsep):
        part = part.strip()
        if part:
            out.append(Path(part))
    return out


def kde_desktop_qqc2_available(candidates: list[Path] | None = None) -> bool:
    """True if KDE's Qt Quick Controls style (Breeze) is on disk."""
    if candidates is None:
        candidates = qml_import_candidates()
    return any((base / "org" / "kde" / "desktop").is_dir() for base in candidates)


def configure_quick_controls_style() -> None:
    """Use Breeze QQC2 on Plasma/KDE when installed; otherwise Fusion (neutral, broadly available)."""
    ensure_qml_import_path_for_process()
    ensure_qt_plugin_path_for_process()
    explicit = os.environ.get("AVELL_RGB_QQC2_STYLE", "").strip()
    if explicit:
        QQuickStyle.setStyle(explicit)
        return
    session = os.environ.get("QT_QUICK_CONTROLS_STYLE", "").strip()
    if session:
        QQuickStyle.setStyle(session)
        return
    if kde_desktop_qqc2_available():
        QQuickStyle.setStyle("org.kde.desktop")
        return
    QQuickStyle.setStyle("Fusion")


def add_qml_import_paths(engine: QQmlApplicationEngine) -> None:
    seen: set[str] = set()
    for p in qml_import_candidates():
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            engine.addImportPath(key)
