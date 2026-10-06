"""AppFacade test harness: isolated QSettings + state file, fake USB scan and openers."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QCoreApplication, QSettings
from PySide6.QtWidgets import QApplication

from app.ui.adapters.app_facade import LEGACY_AUTO_CONNECT_KEY, AppFacade
from avell_storm_rgb.application.device_state import DeviceState, DeviceStateStore
from backend_fakes import FakeKeyboard, FakeLedBar, drain

KB_ROW = {"kind": "keyboard", "bus": 3, "addr": 9, "vid": 0x048D, "pid": 0xCE00, "label": "kb"}
LED_ROW = {"kind": "led_bar", "bus": 1, "addr": 4, "vid": 0x048D, "pid": 0x7001, "label": "led"}


@dataclass
class Rig:
    """Mutable fake world shared by the patched scan and openers."""

    tmp: Path
    rows: list[dict] = field(default_factory=list)
    journal: list = field(default_factory=list)
    kb_error: Exception | None = None
    led_error: Exception | None = None
    kb: FakeKeyboard | None = None
    led: FakeLedBar | None = None
    facades: list[AppFacade] = field(default_factory=list)

    @property
    def state_path(self) -> Path:
        return self.tmp / "cfg" / "state.json"

    def store(self) -> DeviceStateStore:
        return DeviceStateStore(self.state_path)

    def save(self, state: DeviceState) -> None:
        self.store().save(state)

    def facade(self) -> AppFacade:
        if self.kb is None:
            self.kb = FakeKeyboard(journal=self.journal)
        if self.led is None:
            self.led = FakeLedBar(journal=self.journal)
        f = AppFacade(store=self.store())
        self.facades.append(f)
        return f

    def start(self, f: AppFacade) -> None:
        """What main.qml does at startup."""
        f.refreshDevices()
        f.restoreRememberedDevices()
        drain(f._worker)

    def settings(self) -> QSettings:
        return QSettings()


@pytest.fixture
def rig(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName(f"avell_test_{uuid.uuid4().hex[:12]}")
    app.setApplicationName("facade_memory_test")
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)

    r = Rig(tmp=tmp_path)
    monkeypatch.setattr("app.ui.adapters.device_model.enumerate_usb_devices", lambda: [dict(x) for x in r.rows])

    def open_kb(**kw):
        if r.kb_error is not None:
            raise r.kb_error
        return r.kb

    def open_led(bus, addr):
        if r.led_error is not None:
            raise r.led_error
        return r.led

    monkeypatch.setattr("app.ui.adapters.keyboard_backend.open_keyboard", open_kb)
    monkeypatch.setattr("app.ui.adapters.led_bar_backend.open_led_bar_at", open_led)
    yield r
    for f in r.facades:
        f._keyboard.stopFollowOrAnimation()
        f._worker.shutdown(wait=True)


def wait_until(predicate, timeout: float = 3.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        QCoreApplication.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition not reached")


__all__ = ["KB_ROW", "LED_ROW", "LEGACY_AUTO_CONNECT_KEY", "Rig", "drain", "rig", "wait_until"]
