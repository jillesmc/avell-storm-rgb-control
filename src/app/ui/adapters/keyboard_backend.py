from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, Signal, Slot

from avell_storm_rgb.application.device_facade import open_keyboard
from avell_storm_rgb.domain.anim_dsl import run_animation_lines
from avell_storm_rgb.domain.keyboard_solid_colors import SOLID_COLOR_NAMES
from avell_storm_rgb.infrastructure.usb.ite8291_usb import (
    KEYBOARD_DIRECTIONS,
    KEYBOARD_EFFECTS,
    KEYBOARD_PALETTE_SLOT_COLORS,
    NUM_COLS,
    NUM_ROWS,
)

from app.core.usb_worker import UsbWorker

EFFECT_KWARGS: dict[str, frozenset[str]] = {
    "breathing": frozenset({"speed", "brightness", "color", "save"}),
    "wave": frozenset({"speed", "brightness", "direction", "save"}),
    "random": frozenset({"speed", "brightness", "color", "reactive", "save"}),
    "rainbow": frozenset({"brightness", "save"}),
    "ripple": frozenset({"speed", "brightness", "color", "reactive", "save"}),
    "marquee": frozenset({"speed", "brightness", "save"}),
    "raindrop": frozenset({"speed", "brightness", "color", "save"}),
    "aurora": frozenset({"speed", "brightness", "color", "reactive", "save"}),
    "fireworks": frozenset({"speed", "brightness", "color", "reactive", "save"}),
}


class KeyboardBackend(QObject):
    """Keyboard RGB control; all USB via UsbWorker."""

    connectedChanged = Signal()
    inspectChanged = Signal()
    debugChanged = Signal()
    keyGridChanged = Signal()

    inspectUpdate = Signal(str, int, bool)

    def __init__(self, worker: UsbWorker, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.followScreenAvailable = True
        self._worker = worker
        self._kb = None
        self._bus: int = -1
        self._addr: int = -1
        self._debug = False
        self._fw = ""
        self._brightness = 0
        self._off = True
        self._follow_stop = threading.Event()
        self._key_colors: dict[tuple[int, int], tuple[int, int, int]] = {}
        self._key_grid_epoch = 0

        self.inspectUpdate.connect(
            self._apply_inspect, Qt.ConnectionType.QueuedConnection
        )

        try:
            import Xlib  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            self.followScreenAvailable = False

    @Property(bool, notify=connectedChanged)
    def connected(self) -> bool:
        return self._kb is not None

    @Property(int, notify=connectedChanged)
    def deviceBus(self) -> int:
        return self._bus

    @Property(int, notify=connectedChanged)
    def deviceAddr(self) -> int:
        return self._addr

    @Property(str, notify=inspectChanged)
    def fwVersion(self) -> str:
        return self._fw

    @Property(int, notify=inspectChanged)
    def brightnessRead(self) -> int:
        return self._brightness

    @Property(bool, notify=inspectChanged)
    def isOff(self) -> bool:
        return self._off

    @Property(bool, notify=debugChanged)
    def debugUsb(self) -> bool:
        return self._debug

    @debugUsb.setter
    def debugUsb(self, v: bool) -> None:
        if self._debug != v:
            self._debug = v
            self.debugChanged.emit()

    @Property(bool, constant=True)
    def followScreenExtraOk(self) -> bool:
        return self.followScreenAvailable

    @Property(int, constant=True)
    def gridRows(self) -> int:
        return NUM_ROWS

    @Property(int, constant=True)
    def gridCols(self) -> int:
        return NUM_COLS

    @Property(int, notify=keyGridChanged)
    def keyGridEpoch(self) -> int:
        return self._key_grid_epoch

    def _bump_key_grid(self) -> None:
        self._key_grid_epoch += 1
        self.keyGridChanged.emit()

    @Slot(int, int, result=str)
    def keyCellHex(self, row: int, col: int) -> str:
        t = self._key_colors.get((row, col))
        if t is None:
            return "#353535"
        r, g, b = t
        return f"#{r:02x}{g:02x}{b:02x}"

    def _apply_inspect(self, fw: str, brightness: int, off: bool) -> None:
        self._fw = fw
        self._brightness = brightness
        self._off = off
        self.inspectChanged.emit()

    @Slot(int, int)
    def connectAt(self, bus: int, addr: int) -> None:
        def task() -> None:
            self._kb = open_keyboard(bus_addr=(bus, addr), debug=self._debug)
            self._bus = bus
            self._addr = addr
            self.connectedChanged.emit()
            self._do_inspect_emit()

        self._worker.submit(task)

    @Slot()
    def disconnectDevice(self) -> None:
        def task() -> None:
            self._follow_stop.set()
            self._kb = None
            self._bus = -1
            self._addr = -1
            self.connectedChanged.emit()

        self._worker.submit(task)

    def _do_inspect_emit(self) -> None:
        if self._kb is None:
            return
        v = self._kb.get_fw_version()
        fw = ".".join(str(x) for x in v)
        br = self._kb.get_brightness()
        off = self._kb.is_off()
        self.inspectUpdate.emit(fw, br, off)

    @Slot()
    def refreshInspect(self) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._do_inspect_emit()

        self._worker.submit(task)

    @Slot()
    def powerOff(self) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.turn_off()
            self._do_inspect_emit()

        self._worker.submit(task)

    @Slot(int)
    def setBrightness(self, value: int) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_brightness(max(0, min(50, value)))
            self._do_inspect_emit()

        self._worker.submit(task)

    def _effect_kwargs(
        self,
        name: str,
        speed: int,
        brightness: int,
        color_name: str,
        direction_name: str,
        reactive: bool,
        save: bool,
    ) -> dict[str, int]:
        keys = EFFECT_KWARGS.get(name, frozenset())
        out: dict[str, int] = {}
        if "speed" in keys:
            out["speed"] = max(0, min(10, speed))
        if "brightness" in keys:
            out["brightness"] = max(0, min(50, brightness))
        if "color" in keys:
            out["color"] = KEYBOARD_PALETTE_SLOT_COLORS.get(
                color_name.lower(), KEYBOARD_PALETTE_SLOT_COLORS["random"]
            )
        if "direction" in keys:
            out["direction"] = KEYBOARD_DIRECTIONS.get(direction_name.lower(), 0)
        if "reactive" in keys:
            out["reactive"] = 1 if reactive else 0
        if "save" in keys:
            out["save"] = 1 if save else 0
        return out

    @Slot(str, int, int, str, str, bool, bool)
    def applyEffect(
        self,
        name: str,
        speed: int,
        brightness: int,
        color_name: str,
        direction_name: str,
        reactive: bool,
        save: bool,
    ) -> None:
        builder = KEYBOARD_EFFECTS.get(name)
        if builder is None:
            return

        def task() -> None:
            if self._kb is None:
                return
            kw = self._effect_kwargs(
                name, speed, brightness, color_name, direction_name, reactive, save
            )
            self._kb.set_effect(builder(**kw))
            self._do_inspect_emit()

        self._worker.submit(task)

    @Slot(str)
    def setSolidNamed(self, name: str) -> None:
        def task() -> None:
            if self._kb is None:
                return
            rgb = SOLID_COLOR_NAMES.get(name.lower())
            if rgb is None:
                return
            self._kb.set_color(rgb, None, False)
            self._do_inspect_emit()

        self._worker.submit(task)

    @Slot(int, int, int)
    def setSolidRgb(self, r: int, g: int, b: int) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_color(
                (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))),
                None,
                False,
            )
            self._do_inspect_emit()

        self._worker.submit(task)

    @Slot(int, int, int, int, int)
    def setPaletteSlotRgb(self, slot: int, r: int, g: int, b: int) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_palette_color(
                max(1, min(7, slot)),
                (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))),
            )

        self._worker.submit(task)

    @Slot()
    def paletteRestore(self) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.restore_default_palette()

        self._worker.submit(task)

    @Slot()
    def paletteRandom(self) -> None:
        import random

        def task() -> None:
            if self._kb is None:
                return
            for i in range(1, 8):
                self._kb.set_palette_color(
                    i,
                    (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
                )

        self._worker.submit(task)

    @Slot()
    def demoTestPattern(self) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.test_pattern()

        self._worker.submit(task)

    @Slot()
    def freezeAnimation(self) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.freeze()

        self._worker.submit(task)

    @Slot(str, int, bool)
    def playAnimationFile(self, path: str, loops: int, forever: bool) -> None:
        p = Path(path)
        if not p.is_file():
            return
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()

        def task() -> None:
            if self._kb is None:
                return

            def one_pass() -> None:
                run_animation_lines(
                    lines,
                    on_apply=lambda m: self._kb.set_key_colors(m),
                    on_brightness=self._kb.set_brightness,
                    sleep=time.sleep,
                )

            if forever:
                while not self._follow_stop.is_set():
                    one_pass()
            else:
                for _ in range(max(1, loops)):
                    if self._follow_stop.is_set():
                        break
                    one_pass()

        self._worker.submit(task)

    @Slot(bool, int, int, int, int)
    def startFollowScreen(self, fullscreen: bool, x: int, y: int, w: int, h: int) -> None:
        from avell_storm_rgb.application.screen_follow import run_screen_follow

        self._follow_stop.clear()

        def task() -> None:
            if self._kb is None:
                return
            if fullscreen:
                run_screen_follow(self._kb, stop_event=self._follow_stop)
            else:
                run_screen_follow(
                    self._kb,
                    offset_x=x,
                    offset_y=y,
                    width=w,
                    height=h,
                    stop_event=self._follow_stop,
                )

        self._worker.submit(task)

    @Slot()
    def stopFollowOrAnimation(self) -> None:
        self._follow_stop.set()

    @Slot()
    def clearKeyGrid(self) -> None:
        self._key_colors.clear()
        self._bump_key_grid()

    @Slot(int, int, int, int, int, bool)
    def setKeyCell(self, row: int, col: int, r: int, g: int, b: int, apply_now: bool) -> None:
        if not (0 <= row < NUM_ROWS and 0 <= col < NUM_COLS):
            return
        self._key_colors[(row, col)] = (
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b)),
        )
        self._bump_key_grid()

        if apply_now:

            def task() -> None:
                if self._kb is None:
                    return
                self._kb.set_key_colors(dict(self._key_colors))

            self._worker.submit(task)

    @Slot(bool)
    def applyKeyGrid(self, enable_user_mode: bool) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_key_colors(
                dict(self._key_colors),
                enable_user_mode_flag=enable_user_mode,
            )

        self._worker.submit(task)
