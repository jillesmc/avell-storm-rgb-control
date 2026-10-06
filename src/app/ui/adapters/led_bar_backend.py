from __future__ import annotations

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from avell_storm_rgb.application.device_state import LedBarLook, LedBarState, restore_led_bar
from avell_storm_rgb.domain.ledbar_colors import MAX_LED_BAR_PALETTE, parse_color, parse_palette
from avell_storm_rgb.infrastructure.usb.ite8233_usb import LED_BAR_EFFECT_CODES

from app.core.devices import open_led_bar_at
from app.core.usb_worker import UsbWorker


class LedBarBackend(QObject):
    """LED bar control; all USB via UsbWorker.

    After every successful apply the full resulting parameters (palette, effect,
    brightness, speed) are emitted as ``persistUpdate``. The bar's on/off state
    cannot be read back, so ``lightOn`` tracks the last power command.
    """

    connectedChanged = Signal()
    infoChanged = Signal()
    lightChanged = Signal()
    persistUpdate = Signal(object)
    connectFailed = Signal(str)

    def __init__(self, worker: UsbWorker, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._bar = None
        self._info = ""
        self._bus: int = -1
        self._addr: int = -1
        self._light_on = True
        self._saved_look: LedBarLook | None = None
        self._pending_led_brightness: int | None = None
        self._pending_shell_effect: str = "static"
        self._led_brightness_timer = QTimer(self)
        self._led_brightness_timer.setSingleShot(True)
        self._led_brightness_timer.setInterval(200)
        self._led_brightness_timer.timeout.connect(self._flush_led_brightness_debounced)

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

    @Property(bool, notify=lightChanged)
    def lightOn(self) -> bool:
        return self._bar is not None and self._light_on

    def _refresh_info(self) -> None:
        if self._bar is None:
            self._info = ""
        else:
            pid = self._bar.product_id or 0
            fx = ", ".join(sorted(LED_BAR_EFFECT_CODES))
            self._info = f"ITE 8233 048d:{pid:04x}\nEffects: {fx}"
        self.infoChanged.emit()

    # --- USB-thread helpers --------------------------------------------------------

    def _set_light(self, on: bool) -> None:
        self._light_on = on
        self.lightChanged.emit()

    def _ensure_on(self) -> None:
        """Applying a look while the light is off turns it on (BR-8)."""
        if not self._light_on:
            self._bar.power_on()

    def _after_apply(self, effect: str) -> None:
        bar = self._bar
        look = LedBarLook(
            palette=tuple(tuple(c) for c in list(bar.palette)[:MAX_LED_BAR_PALETTE]),
            effect=effect,
            brightness=int(bar.brightness),
            speed=int(bar.speed),
        )
        self._saved_look = look
        self._set_light(True)
        self.persistUpdate.emit({"look": look, "power": "on"})

    def _submit_apply(self, effect: str, apply) -> None:
        """Run ``apply(bar)`` on the worker, then record the resulting look."""

        def task() -> None:
            if self._bar is None:
                return
            self._ensure_on()
            apply(self._bar)
            self._after_apply(effect)

        self._worker.submit(task)

    # --- connection ------------------------------------------------------------------

    @Slot(int, int)
    def connectAt(self, bus: int, addr: int) -> None:
        def task() -> None:
            try:
                self._bar = open_led_bar_at(bus, addr)
            except Exception as e:
                self.connectFailed.emit(f"{type(e).__name__}: {e}")
                raise
            self._bus = bus
            self._addr = addr
            self.connectedChanged.emit()
            self._set_light(True)
            self._refresh_info()

        self._worker.submit(task)

    @Slot()
    def disconnectDevice(self) -> None:
        def task() -> None:
            self._bar = None
            self._bus = -1
            self._addr = -1
            self.connectedChanged.emit()
            self.lightChanged.emit()
            self._refresh_info()

        self._worker.submit(task)

    @Slot()
    def refreshInspect(self) -> None:
        """Same information as CLI `led-bar inspect` (product id + effect list)."""

        def task() -> None:
            self._refresh_info()

        self._worker.submit(task)

    # --- light and restore -------------------------------------------------------------

    @Slot(bool)
    def setLightOn(self, on: bool) -> None:
        look = self._saved_look

        def task() -> None:
            if self._bar is None:
                return
            if on:
                self._bar.power_on()
                if look is not None:
                    restore_led_bar(self._bar, LedBarState(usb_id="", look=look))
            else:
                self._bar.power_off()
            self._set_light(on)
            self.persistUpdate.emit({"power": "on" if on else "off"})

        self._worker.submit(task)

    def restore(self, state: LedBarState) -> None:
        """Apply a saved state through the worker. Never emits ``persistUpdate``."""
        self._saved_look = state.look

        def task() -> None:
            if self._bar is None:
                return
            restore_led_bar(self._bar, state)
            self._set_light(state.power == "on")

        self._worker.submit(task)

    # --- looks -------------------------------------------------------------------------

    @Slot(int, str)
    def requestBrightnessFromUi(self, value: int, shell_effect: str) -> None:
        """Debounced brightness: re-applies the saved effect, else ``shell_effect``."""

        self._pending_led_brightness = max(0, min(100, int(value)))
        self._pending_shell_effect = shell_effect or "static"
        self._led_brightness_timer.stop()
        self._led_brightness_timer.start()

    def _flush_led_brightness_debounced(self) -> None:
        v = self._pending_led_brightness
        if v is None:
            return
        if self._saved_look is not None:
            effect = self._saved_look.effect
        else:
            shell = (self._pending_shell_effect or "static").lower().strip()
            effect = shell if shell in LED_BAR_EFFECT_CODES else "static"

        def apply(bar) -> None:
            bar.set_brightness_level(v)
            bar.apply_visual_effect(effect)

        self._submit_apply(effect, apply)

    @Slot(str)
    def setColorFromSpec(self, spec: str) -> None:
        """Named color or #RRGGBB."""

        def apply(bar) -> None:
            r, g, b = parse_color(spec)
            bar.set_static_rgb(r, g, b)

        self._submit_apply("static", apply)

    @Slot(str, str)
    def applyPalette(self, spec: str, effect: str) -> None:
        def apply(bar) -> None:
            bar.set_palette_colors(parse_palette(spec))
            bar.apply_visual_effect(effect)

        self._submit_apply(effect, apply)

    @Slot(str)
    def applyEffect(self, name: str) -> None:
        self._submit_apply(name, lambda bar: bar.apply_visual_effect(name))

    @Slot(int, str)
    def setBrightnessWithEffect(self, value: int, effect: str) -> None:
        def apply(bar) -> None:
            bar.set_brightness_level(value)
            bar.apply_visual_effect(effect)

        self._submit_apply(effect, apply)

    @Slot(int, str)
    def setSpeedWithEffect(self, value: int, effect: str) -> None:
        def apply(bar) -> None:
            bar.set_motion_speed(value)
            bar.apply_visual_effect(effect)

        self._submit_apply(effect, apply)

    @Slot(int, int, str)
    def applyBrightnessSpeedEffect(self, brightness: int, speed: int, effect: str) -> None:
        """Set brightness, motion speed, then re-apply effect (single apply from UI)."""

        def apply(bar) -> None:
            bar.set_brightness_level(brightness)
            bar.set_motion_speed(speed)
            bar.apply_visual_effect(effect)

        self._submit_apply(effect, apply)
