from __future__ import annotations

import logging
import os
from dataclasses import replace
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from PySide6.QtCore import Property, QObject, QSettings, Qt, Signal, Slot
from PySide6.QtWidgets import QApplication


def _package_version() -> str:
    try:
        return version("avell-storm-rgb")
    except PackageNotFoundError:
        return "0.0.0-dev"

from avell_storm_rgb.application.device_state import (
    DeviceState,
    DeviceStateStore,
    KeyboardState,
    LedBarState,
    StateFileError,
)
from avell_storm_rgb.domain.keyboard_solid_colors import SOLID_COLOR_NAMES
from avell_storm_rgb.infrastructure.usb.ite8291_usb import (
    KEYBOARD_DIRECTIONS,
    KEYBOARD_EFFECTS,
    KEYBOARD_FIRMWARE_COLOR_CHOICES,
    KEYBOARD_PALETTE_SLOT_COLORS,
)
from avell_storm_rgb.infrastructure.usb.ite8233_usb import LED_BAR_EFFECT_CODES

from app.core import xdg_autostart
from app.ui.adapters.app_state import AppState
from app.ui.adapters.device_model import DeviceListModel
from app.ui.adapters.keyboard_backend import KeyboardBackend
from app.ui.adapters.led_bar_backend import LedBarBackend
from app.core.usb_worker import UsbWorker


_LOG = logging.getLogger("avell_storm_rgb.gui")

#: Legacy QSettings key replaced by remembered devices (migrated once, then deleted).
LEGACY_AUTO_CONNECT_KEY = "ui/autoConnectOnStartup"

KINDS = ("keyboard", "led_bar")


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _truthy(raw: object) -> bool:
    if isinstance(raw, str):
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return bool(raw)


def _usb_id(row: dict) -> str:
    return f"{int(row['vid']):04x}:{int(row['pid']):04x}"


class AppFacade(QObject):
    """Root context object exposed to QML as ``App`` (parent: engine, avoids premature GC)."""

    animationPreviewChanged = Signal()
    deviceConnectionChanged = Signal()
    closeToTrayChanged = Signal()
    deviceMemoryChanged = Signal()
    savedLightChanged = Signal()
    launchAtLoginChanged = Signal()
    settingsErrorChanged = Signal()

    def __init__(
        self, parent: QObject | None = None, *, store: DeviceStateStore | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = QSettings()
        raw = self._settings.value("ui/closeToTray")
        self._close_to_tray = True if raw is None else _truthy(raw)
        self._launch_at_login = xdg_autostart.is_enabled()
        self._settings_error = ""
        self._worker = UsbWorker(self)
        self._state = AppState(self._worker, self)
        self._devices = DeviceListModel(self)
        self._keyboard = KeyboardBackend(self._worker, self)
        self._led = LedBarBackend(self._worker, self)
        self._anim_preview = ""
        self._anim_path = ""
        self._app_version = _package_version()
        self._device_epoch = 0
        self._debug_firmware_ui = _env_truthy("AVELL_DEBUG_FIRMWARE_UI")

        # Saved device state (single writer: this object, on the GUI thread).
        self._store = store if store is not None else DeviceStateStore()
        self._saved = DeviceState()
        self._unavailable: dict[str, str] = {k: "" for k in KINDS}
        self._connecting_usb_id: dict[str, str | None] = {k: None for k in KINDS}
        self._needs_migration = False
        self._load_saved_state()

        queued = Qt.ConnectionType.QueuedConnection
        for kind, backend in self._backends():
            backend.connectedChanged.connect(self._bump_device_epoch, queued)
            backend.connectedChanged.connect(
                lambda k=kind: self._on_connected_changed(k), queued
            )
            backend.connectFailed.connect(
                lambda msg, k=kind: self._on_connect_failed(k, msg), queued
            )
            backend.persistUpdate.connect(
                lambda changes, k=kind: self._on_persist(k, changes), queued
            )
        self._keyboard.restoreWarning.connect(self._state.reportError, queued)

    @Property(str, constant=True)
    def applicationVersion(self) -> str:
        return self._app_version

    @Property(bool, constant=True)
    def debugFirmwareUi(self) -> bool:
        """When true (env ``AVELL_DEBUG_FIRMWARE_UI``), Keyboard firmware tab logs layout/apply churn to stderr."""
        return self._debug_firmware_ui

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

    @Property(bool, notify=launchAtLoginChanged)
    def launchAtLogin(self) -> bool:
        return self._launch_at_login

    @launchAtLogin.setter
    def launchAtLogin(self, value: bool) -> None:
        enabled = bool(value)
        if enabled == self._launch_at_login:
            return
        try:
            if enabled:
                xdg_autostart.enable()
            else:
                xdg_autostart.disable()
        except OSError as exc:
            path = xdg_autostart.autostart_file_path()
            self._settings_error = f"Autostart: cannot write {path}: {exc}"
            self.settingsErrorChanged.emit()
            self.launchAtLoginChanged.emit()
            return
        self._launch_at_login = enabled
        self.launchAtLoginChanged.emit()
        if self._settings_error:
            self._settings_error = ""
            self.settingsErrorChanged.emit()

    @Property(str, notify=settingsErrorChanged)
    def settingsError(self) -> str:
        return self._settings_error

    @Slot()
    def refreshLaunchAtLogin(self) -> None:
        current = xdg_autostart.is_enabled()
        if current != self._launch_at_login:
            self._launch_at_login = current
            self.launchAtLoginChanged.emit()

    @Slot()
    def clearSettingsError(self) -> None:
        if self._settings_error:
            self._settings_error = ""
            self.settingsErrorChanged.emit()

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
        """Release USB and forget the device; its saved look and light state are kept (BR-9)."""
        backend = self._backend(kind)
        if backend is None:
            return
        backend.disconnectDevice()
        self._set_remembered(kind, False)

    @Slot(str)
    def forgetDevice(self, kind: str) -> None:
        """Forget a remembered device that is unavailable (no USB to release)."""
        if self._backend(kind) is not None:
            self._set_remembered(kind, False)

    @Slot(str)
    def retryDevice(self, kind: str) -> None:
        """Rescan USB and reconnect one remembered, unavailable device."""
        self._devices.refresh()
        self._restore_kind(kind)
        self.deviceMemoryChanged.emit()

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
    def firmwarePaletteColorChoices(self) -> list[dict[str, int | str]]:
        """Rows for firmware colour ComboBox: key (CLI/API), palette_slot 1–7 or -1 for random/none."""
        rows: list[dict[str, int | str]] = []
        for key, fw in KEYBOARD_FIRMWARE_COLOR_CHOICES:
            slot = fw if 1 <= fw <= 7 else -1
            rows.append({"key": key, "palette_slot": slot, "fw_index": fw})
        return rows

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
        """Rescan USB; remembered devices that were unavailable are retried."""
        self._devices.refresh()
        retried = False
        for kind in KINDS:
            if self._unavailable[kind]:
                self._restore_kind(kind)
                retried = True
        if retried:
            self.deviceMemoryChanged.emit()

    @Slot(str, int, int)
    def connectDevice(self, kind: str, bus: int, addr: int) -> None:
        """Connect from the Devices page; the device is remembered once the connection succeeds."""
        backend = self._backend(kind)
        if backend is None:
            return
        row = next(
            (
                r
                for r in self._devices.rows()
                if r["kind"] == kind and int(r["bus"]) == bus and int(r["addr"]) == addr
            ),
            None,
        )
        self._connecting_usb_id[kind] = _usb_id(row) if row is not None else None
        backend.connectAt(bus, addr)
        saved = self._saved_for(kind)
        if saved is not None:
            # Reconnecting a forgotten or replaced device brings its saved look back (US-003.AC-3).
            backend.restore(saved)

    @Slot()
    def restoreRememberedDevices(self) -> None:
        """Startup: migrate once, then reconnect remembered devices and apply their saved state.

        Order (BR-10): LED bar first, then keyboard; a keyboard animation is queued last
        by the backend itself.
        """
        if self._needs_migration:
            self._migrate_legacy_auto_connect()
        for kind in ("led_bar", "keyboard"):
            self._restore_kind(kind)
        self.deviceMemoryChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        self._keyboard.shutdownCalibrationInput()
        self._worker.shutdown()

    # --- remembered devices (QML) -------------------------------------------------

    @Property(bool, notify=deviceMemoryChanged)
    def keyboardRemembered(self) -> bool:
        return self._is_remembered("keyboard")

    @Property(bool, notify=deviceMemoryChanged)
    def ledBarRemembered(self) -> bool:
        return self._is_remembered("led_bar")

    @Property(bool, notify=savedLightChanged)
    def keyboardSavedLightOn(self) -> bool:
        saved = self._saved.keyboard
        return saved is not None and saved.power == "on"

    @Property(bool, notify=savedLightChanged)
    def ledBarSavedLightOn(self) -> bool:
        saved = self._saved.led_bar
        return saved is not None and saved.power == "on"

    @Property(str, notify=deviceMemoryChanged)
    def keyboardUnavailableReason(self) -> str:
        return self._unavailable["keyboard"]

    @Property(str, notify=deviceMemoryChanged)
    def ledBarUnavailableReason(self) -> str:
        return self._unavailable["led_bar"]

    # --- internals ------------------------------------------------------------------

    def _backends(self):
        return (("keyboard", self._keyboard), ("led_bar", self._led))

    def _backend(self, kind: str):
        return {"keyboard": self._keyboard, "led_bar": self._led}.get(kind)

    def _saved_for(self, kind: str) -> KeyboardState | LedBarState | None:
        return self._saved.keyboard if kind == "keyboard" else self._saved.led_bar

    def _is_remembered(self, kind: str) -> bool:
        saved = self._saved_for(kind)
        return saved is not None and saved.remembered

    def _put(self, kind: str, value: KeyboardState | LedBarState | None) -> None:
        if kind == "keyboard":
            self._saved = replace(self._saved, keyboard=value)
        else:
            self._saved = replace(self._saved, led_bar=value)

    def _save(self) -> None:
        try:
            self._store.save(self._saved)
        except OSError as e:
            msg = f"Could not save device state to {self._store.path}: {e.strerror or e}"
            _LOG.error(msg)
            self._state.reportError(msg)
        else:
            _LOG.debug("state saved: %s", self._store.path)

    def _load_saved_state(self) -> None:
        existed = self._store.exists()
        try:
            self._saved = self._store.load()
        except StateFileError as e:
            backup = self._store.quarantine()
            msg = (
                f"Saved device state was unreadable ({e.reason}) and was moved to "
                f"{backup}. Starting fresh."
            )
            _LOG.warning(msg)
            self._state.reportError(msg)
            self._saved = DeviceState()
            existed = True  # never auto-migrate over a file the user may want back
        if existed:
            self._settings.remove(LEGACY_AUTO_CONNECT_KEY)
        else:
            self._needs_migration = True

    def _migrate_legacy_auto_connect(self) -> None:
        """BR-14: turn the old auto-connect behaviour into remembered devices, once."""
        raw = self._settings.value(LEGACY_AUTO_CONNECT_KEY)
        enabled = True if raw is None else _truthy(raw)
        if enabled:
            rows = self._devices.rows()
            for kind in KINDS:
                row = next((r for r in rows if r["kind"] == kind), None)
                if row is None:
                    continue
                if kind == "keyboard":
                    self._put(kind, KeyboardState(usb_id=_usb_id(row)))
                else:
                    self._put(kind, LedBarState(usb_id=_usb_id(row)))
        self._settings.remove(LEGACY_AUTO_CONNECT_KEY)
        self._needs_migration = False
        self._save()

    def _restore_kind(self, kind: str) -> None:
        saved = self._saved_for(kind)
        if saved is None or not saved.remembered:
            self._unavailable[kind] = ""
            return
        backend = self._backend(kind)
        if backend.connected:
            self._unavailable[kind] = ""
            return
        row = next(
            (
                r
                for r in self._devices.rows()
                if r["kind"] == kind and _usb_id(r) == saved.usb_id
            ),
            None,
        )
        if row is None:
            if not self._unavailable[kind].startswith("Not found") and self._unavailable[kind]:
                return  # keep a USB error reason until the device is seen again
            self._unavailable[kind] = f"Not found ({saved.usb_id})"
            _LOG.info("restore skipped: %s %s not found", kind, saved.usb_id)
            return
        self._unavailable[kind] = ""
        self._connecting_usb_id[kind] = saved.usb_id
        backend.connectAt(int(row["bus"]), int(row["addr"]))
        backend.restore(saved)

    def _set_remembered(self, kind: str, remembered: bool) -> None:
        saved = self._saved_for(kind)
        self._unavailable[kind] = ""
        if saved is not None and saved.remembered != remembered:
            self._put(kind, replace(saved, remembered=remembered))
            self._save()
        self.deviceMemoryChanged.emit()

    def _on_connected_changed(self, kind: str) -> None:
        backend = self._backend(kind)
        usb_id = self._connecting_usb_id[kind]
        if not backend.connected or usb_id is None:
            return
        self._connecting_usb_id[kind] = None
        self._unavailable[kind] = ""
        saved = self._saved_for(kind)
        if saved is None:
            new = KeyboardState(usb_id=usb_id) if kind == "keyboard" else LedBarState(usb_id=usb_id)
            self._put(kind, new)
            self._save()
        elif not saved.remembered or saved.usb_id != usb_id:
            self._put(kind, replace(saved, usb_id=usb_id, remembered=True))
            self._save()
        self.deviceMemoryChanged.emit()

    def _on_connect_failed(self, kind: str, msg: str) -> None:
        self._connecting_usb_id[kind] = None
        if self._is_remembered(kind):
            self._unavailable[kind] = msg
            self.deviceMemoryChanged.emit()

    def _on_persist(self, kind: str, changes: object) -> None:
        saved = self._saved_for(kind)
        if saved is None or not isinstance(changes, dict):
            return
        fields = {k: changes[k] for k in ("look", "power") if k in changes}
        if kind == "keyboard":
            if "brightness" in changes:
                fields["brightness"] = changes["brightness"]
            if "palette" in changes:
                fields["palette"] = {**saved.palette, **changes["palette"]}
        self._put(kind, replace(saved, **fields))
        self._save()
        if "power" in fields and fields["power"] != saved.power:
            self.savedLightChanged.emit()
