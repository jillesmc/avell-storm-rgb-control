"""AppFacade: launch-at-login (XDG autostart) integration."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.core import xdg_autostart
from app.ui.adapters.app_facade import AppFacade


@pytest.fixture
def qapp_isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication([])
    unique = f"avell_test_{uuid.uuid4().hex[:12]}"
    inst.setOrganizationName(unique)
    inst.setApplicationName("facade_autostart_test")
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qt")
    )
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    yield inst


def test_launch_at_login_defaults_false_when_autostart_missing(
    qapp_isolated_settings,
) -> None:
    facade = AppFacade()
    assert facade.launchAtLogin is False
    facade.shutdown()


def test_launch_at_login_enable_writes_file(qapp_isolated_settings) -> None:
    facade = AppFacade()
    facade.launchAtLogin = True
    assert facade.launchAtLogin is True
    assert xdg_autostart.is_enabled() is True
    facade.shutdown()


def test_launch_at_login_disable_removes_file(qapp_isolated_settings) -> None:
    xdg_autostart.enable(exec_prefix="/usr/bin/avell-storm-rgb-gui")
    facade = AppFacade()
    assert facade.launchAtLogin is True
    facade.launchAtLogin = False
    assert facade.launchAtLogin is False
    assert xdg_autostart.is_enabled() is False
    facade.shutdown()


def test_launch_at_login_failure_keeps_state_and_shows_error(
    qapp_isolated_settings,
) -> None:
    facade = AppFacade()
    with patch("app.core.xdg_autostart.enable", side_effect=OSError("permission denied")):
        facade.launchAtLogin = True
    assert facade.launchAtLogin is False
    assert "Autostart:" in facade.settingsError
    facade.shutdown()


def test_refresh_launch_at_login_syncs_from_filesystem(qapp_isolated_settings) -> None:
    facade = AppFacade()
    assert facade.launchAtLogin is False
    xdg_autostart.enable(exec_prefix="/usr/bin/avell-storm-rgb-gui")
    facade.refreshLaunchAtLogin()
    assert facade.launchAtLogin is True
    xdg_autostart.disable()
    facade.refreshLaunchAtLogin()
    assert facade.launchAtLogin is False
    facade.shutdown()
