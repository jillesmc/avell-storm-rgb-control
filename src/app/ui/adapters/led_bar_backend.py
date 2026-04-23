from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot

from avell_storm_rgb.domain.ledbar_colors import COLORS as LED_NAMED_COLORS
from avell_storm_rgb.domain.ledbar_colors import PALETTES as LED_PALETTES
from avell_storm_rgb.domain.ledbar_colors import parse_color, parse_palette
from avell_storm_rgb.infrastructure.usb.ite8233_usb import LED_BAR_EFFECT_CODES

from app.core.devices import open_led_bar_at
from app.core.usb_worker import UsbWorker


class LedBarBackend(QObject):
    connectedChanged = Signal()
    infoChanged = Signal()
    replayModeUpdate = Signal(object)
    replayPowerOnAvailableChanged = Signal()

    def __init__(self, worker: UsbWorker, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._bar = None
        self._info = ""
        self._bus: int = -1
        self._addr: int = -1
        self._last_replay: dict[str, Any] | None = None

        self.replayModeUpdate.connect(
            self._apply_replay_mode, Qt.ConnectionType.QueuedConnection
        )
        self._pending_led_brightness: int | None = None
        self._pending_shell_effect: str = "static"
        self._led_brightness_timer = QTimer(self)
        self._led_brightness_timer.setSingleShot(True)
        self._led_brightness_timer.setInterval(200)
        self._led_brightness_timer.timeout.connect(self._flush_led_brightness_debounced)

    def _effect_name_from_replay(self) -> str | None:
        if not self._last_replay:
            return None
        kind = self._last_replay.get("kind")
        if kind == "effect":
            return str(self._last_replay.get("name", ""))
        if kind in ("palette", "tune_bri", "tune_sp", "tune"):
            return str(self._last_replay.get("effect", ""))
        if kind == "color":
            return "static"
        return None

    def _flush_led_brightness_debounced(self) -> None:
        v = self._pending_led_brightness
        if v is None:
            return
        shell_eff = (self._pending_shell_effect or "static").lower().strip()
        raw = self._effect_name_from_replay()
        eff_key = (raw or "").lower().strip()
        if eff_key not in LED_BAR_EFFECT_CODES:
            eff_key = shell_eff if shell_eff in LED_BAR_EFFECT_CODES else "static"
        vv = int(v)

        def task() -> None:
            if self._bar is None:
                return
            self._bar.set_brightness_level(vv)
            self._bar.apply_visual_effect(eff_key)
            self.replayModeUpdate.emit(
                {"kind": "tune_bri", "brightness": vv, "effect": eff_key}
            )

        self._worker.submit(task)

    @Property(bool, notify=connectedChanged)
    def connected(self) -> bool:
        return self._bar is not None

    @Property(int, notify=connectedChanged)
    def deviceBus(self) -> int:
        return self._bus

    @Property(int, notify=connectedChanged)
    def deviceAddr(self) -> int:
        return self._addr

    @Property(str, notify=infoChanged)
    def infoText(self) -> str:
        return self._info

    @Property(bool, notify=replayPowerOnAvailableChanged)
    def replayPowerOnAvailable(self) -> bool:
        return self._last_replay is not None

    def _apply_replay_mode(self, data: object) -> None:
        if data is None:
            self._last_replay = None
        elif isinstance(data, dict):
            self._last_replay = dict(data)
        else:
            self._last_replay = None
        self.replayPowerOnAvailableChanged.emit()

    def _refresh_info(self) -> None:
        if self._bar is None:
            self._info = ""
        else:
            pid = self._bar.product_id or 0
            fx = ", ".join(sorted(LED_BAR_EFFECT_CODES))
            self._info = f"ITE 8233 048d:{pid:04x}\nEffects: {fx}"
        self.infoChanged.emit()

    def _replay_last_on_device(self) -> None:
        if self._bar is None or self._last_replay is None:
            return
        mode = self._last_replay.get("kind")
        if mode == "effect":
            self._bar.apply_visual_effect(str(self._last_replay["name"]))
        elif mode == "color":
            r, g, b = parse_color(str(self._last_replay["spec"]))
            self._bar.set_static_rgb(r, g, b)
        elif mode == "palette":
            colors = parse_palette(str(self._last_replay["spec"]))
            self._bar.set_palette_colors(colors)
            self._bar.apply_visual_effect(str(self._last_replay["effect"]))
        elif mode == "tune_bri":
            self._bar.set_brightness_level(int(self._last_replay["brightness"]))
            self._bar.apply_visual_effect(str(self._last_replay["effect"]))
        elif mode == "tune_sp":
            self._bar.set_motion_speed(int(self._last_replay["speed"]))
            self._bar.apply_visual_effect(str(self._last_replay["effect"]))
        elif mode == "tune":
            self._bar.set_brightness_level(int(self._last_replay["brightness"]))
            self._bar.set_motion_speed(int(self._last_replay["speed"]))
            self._bar.apply_visual_effect(str(self._last_replay["effect"]))

    @Slot(int, int)
    def connectAt(self, bus: int, addr: int) -> None:
        def task() -> None:
            self._bar = open_led_bar_at(bus, addr)
            self._bus = bus
            self._addr = addr
            self.connectedChanged.emit()
            self._refresh_info()

        self._worker.submit(task)

    @Slot()
    def disconnectDevice(self) -> None:
        def task() -> None:
            self._bar = None
            self._bus = -1
            self._addr = -1
            self.connectedChanged.emit()
            self._refresh_info()
            self.replayModeUpdate.emit(None)

        self._worker.submit(task)

    @Slot()
    def refreshInspect(self) -> None:
        """Same information as CLI `led-bar inspect` (product id + effect list)."""

        def task() -> None:
            self._refresh_info()

        self._worker.submit(task)

    @Slot()
    def powerOn(self) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.power_on()
            self._refresh_info()

        self._worker.submit(task)

    @Slot()
    def powerOnReplay(self) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.power_on()
            self._replay_last_on_device()
            self._refresh_info()

        self._worker.submit(task)

    @Slot()
    def powerOff(self) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.power_off()

        self._worker.submit(task)

    @Slot(int, str)
    def requestBrightnessFromUi(self, value: int, shell_effect: str) -> None:
        """Debounced brightness: re-applies last known or ``shell_effect`` visual mode."""

        self._pending_led_brightness = max(0, min(100, int(value)))
        self._pending_shell_effect = shell_effect or "static"
        self._led_brightness_timer.stop()
        self._led_brightness_timer.start()

    @Slot(str)
    def setColorFromSpec(self, spec: str) -> None:
        """Named color or #RRGGBB."""

        def task() -> None:
            if self._bar is None:
                return
            r, g, b = parse_color(spec)
            self._bar.set_static_rgb(r, g, b)
            self.replayModeUpdate.emit({"kind": "color", "spec": spec})

        self._worker.submit(task)

    @Slot(str, str)
    def applyPalette(self, spec: str, effect: str) -> None:
        def task() -> None:
            if self._bar is None:
                return
            colors = parse_palette(spec)
            self._bar.set_palette_colors(colors)
            self._bar.apply_visual_effect(effect)
            self.replayModeUpdate.emit(
                {"kind": "palette", "spec": spec, "effect": effect}
            )

        self._worker.submit(task)

    @Slot(str)
    def applyEffect(self, name: str) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.apply_visual_effect(name)
            self.replayModeUpdate.emit({"kind": "effect", "name": name})

        self._worker.submit(task)

    @Slot(int, str)
    def setBrightnessWithEffect(self, value: int, effect: str) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.set_brightness_level(value)
            self._bar.apply_visual_effect(effect)
            self.replayModeUpdate.emit(
                {
                    "kind": "tune_bri",
                    "brightness": value,
                    "effect": effect,
                }
            )

        self._worker.submit(task)

    @Slot(int, str)
    def setSpeedWithEffect(self, value: int, effect: str) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.set_motion_speed(value)
            self._bar.apply_visual_effect(effect)
            self.replayModeUpdate.emit(
                {"kind": "tune_sp", "speed": value, "effect": effect}
            )

        self._worker.submit(task)

    @Slot(int, int, str)
    def applyBrightnessSpeedEffect(self, brightness: int, speed: int, effect: str) -> None:
        """Set brightness, motion speed, then re-apply effect (single apply from UI)."""

        def task() -> None:
            if self._bar is None:
                return
            self._bar.set_brightness_level(brightness)
            self._bar.set_motion_speed(speed)
            self._bar.apply_visual_effect(effect)
            self.replayModeUpdate.emit(
                {
                    "kind": "tune",
                    "brightness": brightness,
                    "speed": speed,
                    "effect": effect,
                }
            )

        self._worker.submit(task)
