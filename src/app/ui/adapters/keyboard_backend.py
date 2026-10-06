from __future__ import annotations

import enum
import os
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot

from avell_storm_rgb.application.device_facade import open_keyboard
from avell_storm_rgb.application.screen_follow_dispatch import (
    follow_screen_runtime_available,
    run_screen_follow_auto,
)
from avell_storm_rgb.application.screen_follow_session import is_wayland_session
from avell_storm_rgb.domain.anim_dsl import run_animation_lines
from avell_storm_rgb.domain.keyboard_solid_colors import SOLID_COLOR_NAMES
from avell_storm_rgb.domain.per_key_grid import (
    KEY_LAYOUT_KEYS,
    color_map_ui_to_device,
    key_id_to_ui_cell,
)
from avell_storm_rgb.infrastructure.usb.ite8291_usb import (
    KEYBOARD_EFFECT_PARAMS,
    KEYBOARD_EFFECTS,
    NUM_COLS,
    NUM_ROWS,
    keyboard_effect_kwargs,
)

from app.core.usb_worker import UsbWorker


def _debug_firmware_ui() -> bool:
    return os.environ.get("AVELL_DEBUG_FIRMWARE_UI", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


class _BrightnessTarget(enum.IntEnum):
    """Whether brightness slider should also refresh the firmware effect packet."""

    GLOBAL_ONLY = 0
    FIRMWARE_REAPPLY = 1


class KeyboardBackend(QObject):
    """Keyboard RGB control; all USB via UsbWorker."""

    connectedChanged = Signal()
    inspectChanged = Signal()
    debugChanged = Signal()
    keyGridChanged = Signal()

    inspectUpdate = Signal(str, int, bool)
    effectSnapshotUpdate = Signal(object)
    replayPowerOnAvailableChanged = Signal()
    paletteMirrorChanged = Signal()
    paletteClearRequest = Signal()
    paletteSlotWritten = Signal(int, int, int, int)
    paletteBatchReady = Signal(object)

    #: Matches ``restore_default_palette`` in ite8291_usb (session mirror only).
    _DEFAULT_PALETTE: dict[int, tuple[int, int, int]] = {
        1: (255, 0, 0),
        2: (255, 28, 0),
        3: (255, 119, 0),
        4: (0, 255, 0),
        5: (0, 0, 255),
        6: (0, 255, 255),
        7: (255, 0, 255),
    }

    def __init__(self, worker: UsbWorker, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.followScreenAvailable = follow_screen_runtime_available()
        self._follow_screen_wayland_picker = is_wayland_session()
        self._worker = worker
        self._kb = None
        self._bus: int = -1
        self._addr: int = -1
        self._debug = False
        self._fw = ""
        self._brightness = 0
        self._off = True
        self._follow_stop = threading.Event()
        #: (ui_row, col) with ui_row 0 = top of keyboard (number row); see ``per_key_grid``.
        self._key_colors: dict[tuple[int, int], tuple[int, int, int]] = {}
        self._key_grid_epoch = 0
        self._last_effect_snapshot: list[int] | None = None
        self._palette_mirror: dict[int, tuple[int, int, int]] = {}
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY
        self._last_fw_name: str = ""
        self._last_fw_speed: int = 5
        self._last_fw_brightness: int = 25
        self._last_fw_color_name: str = "random"
        self._last_fw_direction_name: str = "right"
        self._last_fw_reactive: bool = False
        self._last_fw_save: bool = False
        self._pending_brightness: int | None = None
        self._brightness_timer = QTimer(self)
        self._brightness_timer.setSingleShot(True)
        self._brightness_timer.setInterval(200)
        self._brightness_timer.timeout.connect(self._flush_brightness_debounced)

        self.inspectUpdate.connect(
            self._apply_inspect, Qt.ConnectionType.QueuedConnection
        )
        self.effectSnapshotUpdate.connect(
            self._apply_effect_snapshot, Qt.ConnectionType.QueuedConnection
        )
        self.paletteClearRequest.connect(
            self._clear_palette_mirror, Qt.ConnectionType.QueuedConnection
        )
        self.paletteSlotWritten.connect(
            self._apply_palette_slot_write, Qt.ConnectionType.QueuedConnection
        )
        self.paletteBatchReady.connect(
            self._on_palette_batch_ready, Qt.ConnectionType.QueuedConnection
        )

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

    @Property(bool, notify=replayPowerOnAvailableChanged)
    def replayPowerOnAvailable(self) -> bool:
        return self._last_effect_snapshot is not None

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

    @Property(bool, constant=True)
    def followScreenUsesWaylandPicker(self) -> bool:
        """True on Wayland: follow uses portal window picker (region controls are N/A)."""

        return self._follow_screen_wayland_picker

    @Property(int, constant=True)
    def gridRows(self) -> int:
        return NUM_ROWS

    @Property(int, constant=True)
    def gridCols(self) -> int:
        return NUM_COLS

    @Property("QVariantList", constant=True)
    def keyLayoutKeys(self) -> list[dict[str, int | str]]:
        return KEY_LAYOUT_KEYS

    @Property(int, notify=keyGridChanged)
    def keyGridEpoch(self) -> int:
        return self._key_grid_epoch

    def _bump_key_grid(self) -> None:
        self._key_grid_epoch += 1
        self.keyGridChanged.emit()

    @Slot(int, int, result=str)
    def keyCellHex(self, row: int, col: int) -> str:
        """``row``/``col`` are UI coordinates (row 0 = top of keyboard)."""
        t = self._key_colors.get((row, col))
        if t is None:
            return "#353535"
        r, g, b = t
        return f"#{r:02x}{g:02x}{b:02x}"

    @Slot(str, result=str)
    def keyHexById(self, key_id: str) -> str:
        try:
            row, col = key_id_to_ui_cell(key_id)
        except ValueError:
            return "#353535"
        return self.keyCellHex(row, col)

    def _apply_inspect(self, fw: str, brightness: int, off: bool) -> None:
        self._fw = fw
        self._brightness = brightness
        self._off = off
        self.inspectChanged.emit()

    def _apply_effect_snapshot(self, snap: object) -> None:
        if snap is None:
            self._last_effect_snapshot = None
        else:
            self._last_effect_snapshot = list(snap)  # type: ignore[arg-type]
        self.replayPowerOnAvailableChanged.emit()

    def _clear_palette_mirror(self) -> None:
        self._palette_mirror.clear()
        self.paletteMirrorChanged.emit()

    def _apply_palette_slot_write(self, slot: int, r: int, g: int, b: int) -> None:
        self._palette_mirror[int(slot)] = (int(r), int(g), int(b))
        self.paletteMirrorChanged.emit()

    def _on_palette_batch_ready(self, batch: object) -> None:
        if not isinstance(batch, dict):
            return
        d: dict[int, tuple[int, int, int]] = {}
        for k, v in batch.items():
            ki = int(k)
            if isinstance(v, (list, tuple)) and len(v) == 3:
                d[ki] = (int(v[0]), int(v[1]), int(v[2]))
        self._palette_mirror = d
        self.paletteMirrorChanged.emit()

    def _palette_slot_rgb(self, slot: int) -> tuple[int, int, int]:
        """Session mirror if present, else firmware default palette (restore_default order)."""
        s = max(1, min(7, slot))
        t = self._palette_mirror.get(s)
        if t is not None:
            return t
        return self._DEFAULT_PALETTE[s]

    @Slot(int, result=int)
    def paletteSlotR(self, slot: int) -> int:
        return self._palette_slot_rgb(slot)[0]

    @Slot(int, result=int)
    def paletteSlotG(self, slot: int) -> int:
        return self._palette_slot_rgb(slot)[1]

    @Slot(int, result=int)
    def paletteSlotB(self, slot: int) -> int:
        return self._palette_slot_rgb(slot)[2]

    @Slot(int, result=bool)
    def paletteSlotKnown(self, slot: int) -> bool:
        return max(1, min(7, slot)) in self._palette_mirror

    def _reset_brightness_context(self) -> None:
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY
        self._last_fw_name = ""

    @Slot(str, str, result=bool)
    def effectSupports(self, effect_name: str, capability: str) -> bool:
        """Whether ``capability`` is used by ``effect_name`` (speed, color, direction, reactive, save)."""

        caps = KEYBOARD_EFFECT_PARAMS.get(effect_name, frozenset())
        return capability in caps

    @Slot(int, int)
    def connectAt(self, bus: int, addr: int) -> None:
        def task() -> None:
            self._kb = open_keyboard(bus_addr=(bus, addr), debug=self._debug)
            self._bus = bus
            self._addr = addr
            self.connectedChanged.emit()
            self._reset_brightness_context()
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
            self.effectSnapshotUpdate.emit(None)
            self.paletteClearRequest.emit()
            self._reset_brightness_context()

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
        self._reset_brightness_context()

        def task() -> None:
            if self._kb is None:
                return
            snap = list(self._kb.get_effect())
            self._kb.turn_off()
            self.effectSnapshotUpdate.emit(snap)
            self._do_inspect_emit()

        self._worker.submit(task)

    @Slot()
    def powerOnReplay(self) -> None:
        snap = self._last_effect_snapshot
        if snap is None:
            return
        payload = list(snap)

        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_effect(payload)
            self._do_inspect_emit()

        self._worker.submit(task)

    @Slot(int)
    def setBrightness(self, value: int) -> None:
        """Immediate USB brightness (no debounce); keeps firmware packet in sync when applicable."""

        def task() -> None:
            if self._kb is None:
                return
            v = max(0, min(50, value))
            self._kb.set_brightness(v)
            if (
                self._brightness_target == _BrightnessTarget.FIRMWARE_REAPPLY
                and self._last_fw_name
                and not self._kb.is_off()
            ):
                self._reapply_cached_firmware_effect(v)
            self._do_inspect_emit()

        self._worker.submit(task)

    def _reapply_cached_firmware_effect(self, brightness: int) -> None:
        assert self._kb is not None
        name = self._last_fw_name
        builder = KEYBOARD_EFFECTS.get(name)
        if builder is None:
            return
        kw = self._effect_kwargs(
            name,
            self._last_fw_speed,
            brightness,
            self._last_fw_color_name,
            self._last_fw_direction_name,
            self._last_fw_reactive,
            self._last_fw_save,
        )
        self._kb.set_effect(builder(**kw))

    @Slot(int)
    def requestBrightnessFromUi(self, value: int) -> None:
        """Debounced brightness from the device slider (global + optional firmware packet refresh)."""

        self._pending_brightness = max(0, min(50, int(value)))
        self._brightness_timer.stop()
        self._brightness_timer.start()

    def _flush_brightness_debounced(self) -> None:
        v = self._pending_brightness
        if v is None:
            return

        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_brightness(v)
            if (
                self._brightness_target == _BrightnessTarget.FIRMWARE_REAPPLY
                and self._last_fw_name
                and not self._kb.is_off()
            ):
                self._reapply_cached_firmware_effect(v)
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
        return keyboard_effect_kwargs(
            name,
            speed=speed,
            brightness=brightness,
            color=color_name,
            direction=direction_name,
            reactive=reactive,
            save=save,
        )

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

        self._last_fw_name = name
        self._last_fw_speed = speed
        self._last_fw_brightness = brightness
        self._last_fw_color_name = color_name
        self._last_fw_direction_name = direction_name
        self._last_fw_reactive = reactive
        self._last_fw_save = save
        self._brightness_target = _BrightnessTarget.FIRMWARE_REAPPLY

        if _debug_firmware_ui():
            print(
                "[avell-storm-rgb] applyEffect",
                f"name={name!r} speed={speed} brightness={brightness} color={color_name!r} "
                f"dir={direction_name!r} reactive={reactive} save={save}",
                file=sys.stderr,
                flush=True,
            )

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
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY

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
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY

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

    @Slot(int, int, int, int)
    def setPaletteSlotRgb(self, slot: int, r: int, g: int, b: int) -> None:
        s = max(1, min(7, slot))
        rgb = (
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b)),
        )

        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_palette_color(s, rgb)
            self.paletteSlotWritten.emit(s, rgb[0], rgb[1], rgb[2])

        self._worker.submit(task)

    @Slot()
    def paletteRestore(self) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.restore_default_palette()
            self.paletteBatchReady.emit(dict(self._DEFAULT_PALETTE))

        self._worker.submit(task)

    @Slot()
    def paletteRandom(self) -> None:
        import random

        def task() -> None:
            if self._kb is None:
                return
            batch: dict[int, tuple[int, int, int]] = {}
            for i in range(1, 8):
                c = (
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                )
                self._kb.set_palette_color(i, c)
                batch[i] = c
            self.paletteBatchReady.emit(batch)

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
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY
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

        self._worker.submit(task, show_busy=forever)

    @Slot(bool, int, int, int, int)
    def startFollowScreen(self, fullscreen: bool, x: int, y: int, w: int, h: int) -> None:
        self._follow_stop.clear()
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY

        def task() -> None:
            if self._kb is None:
                return
            if fullscreen:
                run_screen_follow_auto(self._kb, stop_event=self._follow_stop)
            else:
                run_screen_follow_auto(
                    self._kb,
                    offset_x=x,
                    offset_y=y,
                    width=w,
                    height=h,
                    stop_event=self._follow_stop,
                )

        self._worker.submit(task, show_busy=False)

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
                self._kb.set_key_colors(color_map_ui_to_device(dict(self._key_colors)))

            self._worker.submit(task)

    @Slot(str, int, int, int, bool)
    def setKeyById(self, key_id: str, r: int, g: int, b: int, apply_now: bool) -> None:
        try:
            row, col = key_id_to_ui_cell(key_id)
        except ValueError:
            return
        self.setKeyCell(row, col, r, g, b, apply_now)

    @Slot("QVariantList", int, int, int, bool)
    def setKeysByIdColor(
        self,
        key_ids: list[str],
        r: int,
        g: int,
        b: int,
        apply_now: bool,
    ) -> None:
        rv = max(0, min(255, r))
        gv = max(0, min(255, g))
        bv = max(0, min(255, b))
        changed = False
        for raw_key_id in key_ids:
            key_id = str(raw_key_id)
            try:
                row, col = key_id_to_ui_cell(key_id)
            except ValueError:
                continue
            self._key_colors[(row, col)] = (rv, gv, bv)
            changed = True
        if not changed:
            return
        self._bump_key_grid()
        if apply_now:

            def task() -> None:
                if self._kb is None:
                    return
                self._kb.set_key_colors(color_map_ui_to_device(dict(self._key_colors)))

            self._worker.submit(task)

    @Slot(bool)
    def applyKeyGrid(self, enable_user_mode: bool) -> None:
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY

        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_key_colors(
                color_map_ui_to_device(dict(self._key_colors)),
                enable_user_mode_flag=enable_user_mode,
            )

        self._worker.submit(task)
