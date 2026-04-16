from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from PySide6.QtCore import QModelIndex, Property, QObject, QSettings, Signal, Slot
from PySide6.QtWidgets import QApplication


def _package_version() -> str:
    try:
        return version("avell-storm-rgb")
    except PackageNotFoundError:
        return "0.0.0-dev"

from avell_storm_rgb.domain.keyboard_solid_colors import SOLID_COLOR_NAMES
from avell_storm_rgb.infrastructure.usb.ite8291_usb import (
    KEYBOARD_DIRECTIONS,
    KEYBOARD_EFFECTS,
    KEYBOARD_PALETTE_SLOT_COLORS,
)
from avell_storm_rgb.infrastructure.usb.ite8233_usb import LED_BAR_EFFECT_CODES

from app.ui.adapters.app_state import AppState
from app.ui.adapters.device_model import DeviceListModel
from app.ui.adapters.keyboard_backend import KeyboardBackend
from app.ui.adapters.led_bar_backend import LedBarBackend
from app.core.usb_worker import UsbWorker


class AppFacade(QObject):
    """Root context object exposed to QML as ``App`` (parent: engine, avoids premature GC)."""

    animationPreviewChanged = Signal()
    deviceConnectionChanged = Signal()
    closeToTrayChanged = Signal()
    autoConnectOnStartupChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._settings = QSettings()
        raw = self._settings.value("ui/closeToTray")
        if raw is None:
            self._close_to_tray = True
        elif isinstance(raw, str):
            self._close_to_tray = raw.lower() in ("1", "true", "yes", "on")
        else:
            self._close_to_tray = bool(raw)
        raw_ac = self._settings.value("ui/autoConnectOnStartup")
        if raw_ac is None:
            self._auto_connect_on_startup = True
        elif isinstance(raw_ac, str):
            self._auto_connect_on_startup = raw_ac.lower() in ("1", "true", "yes", "on")
        else:
            self._auto_connect_on_startup = bool(raw_ac)
        self._worker = UsbWorker(self)
        self._state = AppState(self._worker, self)
        self._devices = DeviceListModel(self)
        self._keyboard = KeyboardBackend(self._worker, self)
        self._led = LedBarBackend(self._worker, self)
        self._anim_preview = ""
        self._anim_path = ""
        self._app_version = _package_version()
        self._device_epoch = 0
        self._keyboard.connectedChanged.connect(self._bump_device_epoch)
        self._led.connectedChanged.connect(self._bump_device_epoch)

    @Property(str, constant=True)
    def applicationVersion(self) -> str:
        return self._app_version

    @Property(bool, notify=closeToTrayChanged)
    def closeToTray(self) -> bool:
        return self._close_to_tray

    @closeToTray.setter
    def closeToTray(self, value: bool) -> None:
        v = bool(value)
        if self._close_to_tray != v:
            self._close_to_tray = v
            self._settings.setValue("ui/closeToTray", v)
            self.closeToTrayChanged.emit()

    @Property(bool, notify=autoConnectOnStartupChanged)
    def autoConnectOnStartup(self) -> bool:
        return self._auto_connect_on_startup

    @autoConnectOnStartup.setter
    def autoConnectOnStartup(self, value: bool) -> None:
        v = bool(value)
        if self._auto_connect_on_startup != v:
            self._auto_connect_on_startup = v
            self._settings.setValue("ui/autoConnectOnStartup", v)
            self.autoConnectOnStartupChanged.emit()

    @Slot()
    def quitApplication(self) -> None:
        inst = QApplication.instance()
        if inst is not None:
            inst.quit()

    @Property(int, notify=deviceConnectionChanged)
    def deviceConnectionEpoch(self) -> int:
        return self._device_epoch

    def _bump_device_epoch(self) -> None:
        self._device_epoch += 1
        self.deviceConnectionChanged.emit()

    @Slot(str, int, int, result=bool)
    def isDeviceOpenInApp(self, kind: str, bus: int, addr: int) -> bool:
        if kind == "keyboard":
            return (
                self._keyboard.connected
                and self._keyboard.deviceBus == bus
                and self._keyboard.deviceAddr == addr
            )
        if kind == "led_bar":
            return (
                self._led.connected
                and self._led.deviceBus == bus
                and self._led.deviceAddr == addr
            )
        return False

    @Slot(str)
    def disconnectDeviceKind(self, kind: str) -> None:
        if kind == "keyboard":
            self._keyboard.disconnectDevice()
        elif kind == "led_bar":
            self._led.disconnectDevice()

    @Property(QObject, constant=True)
    def state(self) -> AppState:
        return self._state

    @Property(QObject, constant=True)
    def devices(self) -> DeviceListModel:
        return self._devices

    @Property(QObject, constant=True)
    def keyboard(self) -> KeyboardBackend:
        return self._keyboard

    @Property(QObject, constant=True)
    def ledBar(self) -> LedBarBackend:
        return self._led

    @Property(list, constant=True)
    def keyboardEffectNames(self) -> list[str]:
        return sorted(KEYBOARD_EFFECTS.keys())

    @Property(list, constant=True)
    def paletteSlotColorNames(self) -> list[str]:
        return sorted(KEYBOARD_PALETTE_SLOT_COLORS.keys())

    @Property(list, constant=True)
    def directionNames(self) -> list[str]:
        return [k for k in sorted(KEYBOARD_DIRECTIONS.keys()) if k != "none"] + ["none"]

    @Property(list, constant=True)
    def solidColorNames(self) -> list[str]:
        return sorted(SOLID_COLOR_NAMES.keys())

    @Property(list, constant=True)
    def solidColorEntries(self) -> list[dict[str, int | str]]:
        """For QML named-color grid: {name, r, g, b}."""
        return [
            {"name": k, "r": v[0], "g": v[1], "b": v[2]}
            for k, v in sorted(SOLID_COLOR_NAMES.items())
        ]

    @Property(list, constant=True)
    def ledEffectNames(self) -> list[str]:
        return sorted(LED_BAR_EFFECT_CODES.keys())

    @Property(list, constant=True)
    def ledNamedColors(self) -> list[str]:
        from avell_storm_rgb.domain import ledbar_colors

        return sorted(ledbar_colors.COLORS.keys())

    @Property(list, constant=True)
    def ledNamedColorEntries(self) -> list[dict[str, int | str]]:
        from avell_storm_rgb.domain import ledbar_colors

        return [
            {"name": k, "r": v[0], "g": v[1], "b": v[2]}
            for k, v in sorted(ledbar_colors.COLORS.items())
        ]

    @Property(list, constant=True)
    def ledPalettePresets(self) -> list[str]:
        from avell_storm_rgb.domain import ledbar_colors

        return sorted(ledbar_colors.PALETTES.keys())

    @Property(str, notify=animationPreviewChanged)
    def animationPreviewText(self) -> str:
        return self._anim_preview

    @Property(str, notify=animationPreviewChanged)
    def animationFilePath(self) -> str:
        return self._anim_path

    @Slot(str)
    def loadAnimationPreview(self, path: str) -> None:
        p = Path(path) if path else Path()
        self._anim_path = str(p) if path else ""
        if not path or not p.is_file():
            self._anim_preview = ""
            self.animationPreviewChanged.emit()
            return
        text = p.read_text(encoding="utf-8", errors="replace")
        if len(text) > 120_000:
            text = text[:120_000] + "\n…"
        self._anim_preview = text
        self.animationPreviewChanged.emit()

    @Slot()
    def refreshDevices(self) -> None:
        self._devices.refresh()

    @Slot(str)
    def connectFirstDiscovered(self, kind: str) -> None:
        """Connect the first USB row of this kind (scan order), like sidebar toggle ON."""
        if kind not in ("keyboard", "led_bar"):
            return
        root = QModelIndex()
        n = self._devices.rowCount(root)
        for row in range(n):
            idx = self._devices.index(row, 0)
            k = self._devices.data(idx, DeviceListModel.KindRole)
            if k != kind:
                continue
            bus = self._devices.data(idx, DeviceListModel.BusRole)
            addr = self._devices.data(idx, DeviceListModel.AddrRole)
            if bus is None or addr is None:
                continue
            ibus, iaddr = int(bus), int(addr)
            if self.isDeviceOpenInApp(kind, ibus, iaddr):
                return
            self.connectDevice(kind, ibus, iaddr)
            return

    @Slot()
    def tryAutoConnectDiscoveredDevices(self) -> None:
        if not self._auto_connect_on_startup:
            return
        root = QModelIndex()
        n = self._devices.rowCount(root)
        keyboard_done = False
        led_done = False
        for row in range(n):
            idx = self._devices.index(row, 0)
            kind = self._devices.data(idx, DeviceListModel.KindRole)
            bus = self._devices.data(idx, DeviceListModel.BusRole)
            addr = self._devices.data(idx, DeviceListModel.AddrRole)
            if kind is None or bus is None or addr is None:
                continue
            if kind == "keyboard" and not keyboard_done:
                if not self.isDeviceOpenInApp("keyboard", int(bus), int(addr)):
                    self.connectDevice("keyboard", int(bus), int(addr))
                keyboard_done = True
            elif kind == "led_bar" and not led_done:
                if not self.isDeviceOpenInApp("led_bar", int(bus), int(addr)):
                    self.connectDevice("led_bar", int(bus), int(addr))
                led_done = True

    @Slot(str, int, int)
    def connectDevice(self, kind: str, bus: int, addr: int) -> None:
        if kind == "keyboard":
            self._keyboard.connectAt(bus, addr)
        elif kind == "led_bar":
            self._led.connectAt(bus, addr)

    @Slot()
    def shutdown(self) -> None:
        self._worker.shutdown()
