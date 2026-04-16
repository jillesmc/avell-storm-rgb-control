"""AppFacade: autoConnectOnStartup setting and tryAutoConnectDiscoveredDevices policy."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.ui.adapters.app_facade import AppFacade
from app.ui.adapters.device_model import DeviceListModel


@pytest.fixture
def qapp_isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication([])
    unique = f"avell_test_{uuid.uuid4().hex[:12]}"
    inst.setOrganizationName(unique)
    inst.setApplicationName("facade_autoconnect_test")
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path)
    )
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    yield inst


def test_auto_connect_on_startup_defaults_true_when_setting_absent(
    qapp_isolated_settings,
) -> None:
    facade = AppFacade()
    assert facade.autoConnectOnStartup is True
    facade.shutdown()


def test_auto_connect_on_startup_persists(qapp_isolated_settings, tmp_path) -> None:
    facade = AppFacade()
    facade.autoConnectOnStartup = False
    assert facade.autoConnectOnStartup is False
    facade.shutdown()

    facade2 = AppFacade()
    assert facade2.autoConnectOnStartup is False
    facade2.autoConnectOnStartup = True
    facade2.shutdown()


def test_try_auto_connect_skips_when_setting_off(qapp_isolated_settings, monkeypatch) -> None:
    fake_devices = [
        {"kind": "keyboard", "bus": 3, "addr": 5, "label": "kb"},
        {"kind": "led_bar", "bus": 3, "addr": 4, "label": "led"},
    ]
    monkeypatch.setattr(
        "app.ui.adapters.device_model.enumerate_usb_devices", lambda: list(fake_devices)
    )

    facade = AppFacade()
    facade.autoConnectOnStartup = False
    facade._keyboard.connectAt = MagicMock()  # type: ignore[method-assign]
    facade._led.connectAt = MagicMock()  # type: ignore[method-assign]

    facade.refreshDevices()
    facade.tryAutoConnectDiscoveredDevices()

    facade._keyboard.connectAt.assert_not_called()
    facade._led.connectAt.assert_not_called()
    facade.shutdown()


def test_try_auto_connect_first_keyboard_and_led_when_enabled(
    qapp_isolated_settings, monkeypatch
) -> None:
    fake_devices = [
        {"kind": "keyboard", "bus": 3, "addr": 5, "label": "kb"},
        {"kind": "keyboard", "bus": 3, "addr": 9, "label": "kb2"},
        {"kind": "led_bar", "bus": 1, "addr": 2, "label": "led"},
        {"kind": "led_bar", "bus": 1, "addr": 3, "label": "led2"},
    ]
    monkeypatch.setattr(
        "app.ui.adapters.device_model.enumerate_usb_devices", lambda: list(fake_devices)
    )

    facade = AppFacade()
    facade.autoConnectOnStartup = True
    facade._keyboard.connectAt = MagicMock()  # type: ignore[method-assign]
    facade._led.connectAt = MagicMock()  # type: ignore[method-assign]

    facade.refreshDevices()
    facade.tryAutoConnectDiscoveredDevices()

    facade._keyboard.connectAt.assert_called_once_with(3, 5)
    facade._led.connectAt.assert_called_once_with(1, 2)
    facade.shutdown()


def test_try_auto_connect_skips_if_already_open_same_device(
    qapp_isolated_settings, monkeypatch
) -> None:
    fake_devices = [
        {"kind": "keyboard", "bus": 3, "addr": 5, "label": "kb"},
    ]
    monkeypatch.setattr(
        "app.ui.adapters.device_model.enumerate_usb_devices", lambda: list(fake_devices)
    )

    facade = AppFacade()
    facade.autoConnectOnStartup = True
    facade._keyboard.connectAt = MagicMock()  # type: ignore[method-assign]

    facade.refreshDevices()
    facade._keyboard._kb = object()
    facade._keyboard._bus = 3
    facade._keyboard._addr = 5

    facade.tryAutoConnectDiscoveredDevices()

    facade._keyboard.connectAt.assert_not_called()
    facade.shutdown()


def test_connect_first_discovered_keyboard_first_in_list(
    qapp_isolated_settings, monkeypatch
) -> None:
    fake_devices = [
        {"kind": "led_bar", "bus": 9, "addr": 1, "label": "led"},
        {"kind": "keyboard", "bus": 3, "addr": 5, "label": "kb"},
    ]
    monkeypatch.setattr(
        "app.ui.adapters.device_model.enumerate_usb_devices", lambda: list(fake_devices)
    )

    facade = AppFacade()
    facade._keyboard.connectAt = MagicMock()  # type: ignore[method-assign]

    facade.refreshDevices()
    facade.connectFirstDiscovered("keyboard")

    facade._keyboard.connectAt.assert_called_once_with(3, 5)
    facade.shutdown()


def test_connect_first_discovered_skips_when_already_on_that_device(
    qapp_isolated_settings, monkeypatch
) -> None:
    fake_devices = [
        {"kind": "keyboard", "bus": 3, "addr": 5, "label": "kb"},
    ]
    monkeypatch.setattr(
        "app.ui.adapters.device_model.enumerate_usb_devices", lambda: list(fake_devices)
    )

    facade = AppFacade()
    facade._keyboard.connectAt = MagicMock()  # type: ignore[method-assign]
    facade.refreshDevices()
    facade._keyboard._kb = object()
    facade._keyboard._bus = 3
    facade._keyboard._addr = 5

    facade.connectFirstDiscovered("keyboard")

    facade._keyboard.connectAt.assert_not_called()
    facade.shutdown()
