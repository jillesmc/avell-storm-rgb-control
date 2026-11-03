"""Dev instances keep their own config dir (AVELL_STORM_RGB_CONFIG_DIR) apart from production."""

from __future__ import annotations

from pathlib import Path

import pytest

from avell_storm_rgb.application.bulb_inventory import default_inventory_path
from avell_storm_rgb.application.config_paths import CONFIG_DIR_ENV, app_config_dir
from avell_storm_rgb.application.device_state import default_state_path


def test_default_is_xdg_app_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert app_config_dir() == tmp_path / "avell-storm-rgb"
    assert default_state_path() == tmp_path / "avell-storm-rgb" / "state.json"
    assert default_inventory_path() == tmp_path / "avell-storm-rgb" / "tuya_devices.json"


def test_override_moves_state_and_inventory(tmp_path, monkeypatch) -> None:
    dev = tmp_path / "dev"
    monkeypatch.setenv(CONFIG_DIR_ENV, str(dev))
    assert default_state_path() == dev / "state.json"
    assert default_inventory_path() == dev / "tuya_devices.json"


def test_dev_instance_cannot_enable_launch_at_login(tmp_path, monkeypatch) -> None:
    pytest.importorskip("PySide6.QtCore")
    from gui_helpers import ensure_qapp
    from PySide6.QtQml import QQmlApplicationEngine

    from app.core import xdg_autostart
    from app.ui.adapters.app_facade import AppFacade

    ensure_qapp()
    monkeypatch.setenv(CONFIG_DIR_ENV, str(tmp_path / "dev"))
    engine = QQmlApplicationEngine()  # keep alive: it parents the facade
    facade = AppFacade(engine)
    facade.launchAtLogin = True
    assert facade.launchAtLogin is False
    assert not xdg_autostart.autostart_file_path().exists()
    assert CONFIG_DIR_ENV in facade.settingsError
    facade.shutdown()
