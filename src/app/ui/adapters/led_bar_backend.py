from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from avell_storm_rgb.domain.ledbar_colors import COLORS as LED_NAMED_COLORS
from avell_storm_rgb.domain.ledbar_colors import PALETTES as LED_PALETTES
from avell_storm_rgb.domain.ledbar_colors import parse_color, parse_palette
from avell_storm_rgb.infrastructure.usb.ite8233_usb import LED_BAR_EFFECT_CODES

from app.core.devices import open_led_bar_at
from app.core.usb_worker import UsbWorker


class LedBarBackend(QObject):
    connectedChanged = Signal()
    infoChanged = Signal()

    def __init__(self, worker: UsbWorker, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._bar = None
        self._info = ""
        self._bus: int = -1
        self._addr: int = -1

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

    def _refresh_info(self) -> None:
        if self._bar is None:
            self._info = ""
        else:
            pid = self._bar.product_id or 0
            fx = ", ".join(sorted(LED_BAR_EFFECT_CODES))
            self._info = f"ITE 8233 048d:{pid:04x}\nEffects: {fx}"
        self.infoChanged.emit()

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
    def powerOff(self) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.power_off()

        self._worker.submit(task)

    @Slot(str)
    def setColorFromSpec(self, spec: str) -> None:
        """Named color or #RRGGBB."""

        def task() -> None:
            if self._bar is None:
                return
            r, g, b = parse_color(spec)
            self._bar.set_static_rgb(r, g, b)

        self._worker.submit(task)

    @Slot(str, str)
    def applyPalette(self, spec: str, effect: str) -> None:
        def task() -> None:
            if self._bar is None:
                return
            colors = parse_palette(spec)
            self._bar.set_palette_colors(colors)
            self._bar.apply_visual_effect(effect)

        self._worker.submit(task)

    @Slot(str)
    def applyEffect(self, name: str) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.apply_visual_effect(name)

        self._worker.submit(task)

    @Slot(int, str)
    def setBrightnessWithEffect(self, value: int, effect: str) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.set_brightness_level(value)
            self._bar.apply_visual_effect(effect)

        self._worker.submit(task)

    @Slot(int, str)
    def setSpeedWithEffect(self, value: int, effect: str) -> None:
        def task() -> None:
            if self._bar is None:
                return
            self._bar.set_motion_speed(value)
            self._bar.apply_visual_effect(effect)

        self._worker.submit(task)
