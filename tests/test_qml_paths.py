"""Qt plugin path merging for PySide6 + distro Breeze (no mixed platform plugins)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import app.qml_paths
from app.qml_paths import (
    _is_unsafe_qt_plugin_path,
    ensure_qt_plugin_path_for_process,
    merge_qt_plugin_path,
)


@pytest.fixture(autouse=True)
def _arch_distro_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the distro Qt roots so the filtering is tested on any host (Debian CI has none)."""
    roots = [Path("/usr/lib/qt6/plugins").resolve(), Path("/usr/lib64/qt6/plugins").resolve()]
    monkeypatch.setattr(app.qml_paths, "_distro_qt6_plugin_base_dirs", lambda: list(dict.fromkeys(roots)))


def test_merge_puts_pyside_plugins_first() -> None:
    merged = merge_qt_plugin_path()
    assert merged
    first = Path(merged[0])
    assert first.is_dir()
    assert (first / "platforms").is_dir()
    assert "PySide6" in str(first) or "site-packages" in str(first)


def test_merge_never_includes_distro_plugins_root() -> None:
    merged = merge_qt_plugin_path(
        existing=os.pathsep.join(("/usr/lib/qt6/plugins", "/usr/lib64/qt6/plugins"))
    )
    assert "/usr/lib/qt6/plugins" not in merged
    assert "/usr/lib64/qt6/plugins" not in merged


def test_merge_never_includes_distro_platforms_subdir() -> None:
    merged = merge_qt_plugin_path(existing="/usr/lib/qt6/plugins/platforms")
    assert "/usr/lib/qt6/plugins/platforms" not in merged


@pytest.mark.parametrize(
    "entry",
    [
        "/usr/lib/qt6/plugins",
        "/usr/lib64/qt6/plugins",
        "/usr/lib/qt6/plugins/platforms",
        "/usr/lib/qt6/plugins/wayland-shell-integration",
    ],
)
def test_unsafe_plugin_paths(entry: str) -> None:
    if Path(entry).parent.name == "plugins" and not Path(entry).exists():
        pytest.skip("distro layout not present")
    if not Path(entry).exists() and entry.endswith("wayland-shell-integration"):
        assert _is_unsafe_qt_plugin_path(entry)
        return
    if Path(entry).exists() or entry.endswith(("plugins", "platforms")):
        assert _is_unsafe_qt_plugin_path(entry)


def test_ensure_sets_env_without_distro_platforms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QT_PLUGIN_PATH", "/usr/lib/qt6/plugins")
    ensure_qt_plugin_path_for_process()
    parts = os.environ["QT_PLUGIN_PATH"].split(os.pathsep)
    assert parts
    assert parts[0] != "/usr/lib/qt6/plugins"
    assert "/usr/lib/qt6/plugins" not in parts
    styles = [p for p in parts if p.endswith("/plugins/styles")]
    if Path("/usr/lib/qt6/plugins/styles").is_dir():
        assert styles
