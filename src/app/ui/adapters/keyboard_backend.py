from __future__ import annotations

import enum
import os
import sys
import threading
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Property, QObject, Qt, QTimer, Signal, Slot

from avell_storm_rgb.application.device_facade import open_keyboard
from avell_storm_rgb.application.device_state import (
    AnimationLook,
    FirmwareEffectLook,
    KeyboardLook,
    KeyboardState,
    PerKeyLook,
    SolidLook,
    firmware_effect_payload,
    restore_keyboard,
)
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
    ui_row_to_device_row,
)
from avell_storm_rgb.infrastructure.usb.ite8291_usb import (
    KEYBOARD_DIRECTIONS,
    KEYBOARD_EFFECT_PARAMS,
    KEYBOARD_EFFECTS,
    KEYBOARD_PALETTE_SLOT_COLORS,
    NUM_COLS,
    NUM_ROWS,
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


class _Stopped(Exception):
    """Raised inside a long animation task when its stop event fires."""


class KeyboardBackend(QObject):
    """Keyboard RGB control; all USB via UsbWorker.

    Every successful apply emits ``persistUpdate`` (a dict with any of ``look``,
    ``palette``, ``brightness``, ``power``) from inside the USB task; the facade
    merges it into the saved state. ``restore()`` applies a saved state and never
    emits ``persistUpdate``.
    """

    connectedChanged = Signal()
    inspectChanged = Signal()
    debugChanged = Signal()
    keyGridChanged = Signal()
    lightChanged = Signal()

    persistUpdate = Signal(object)
    restoreWarning = Signal(str)
    connectFailed = Signal(str)

    inspectUpdate = Signal(str, int, bool)
    effectSnapshotUpdate = Signal(object)
    paletteMirrorChanged = Signal()
    paletteClearRequest = Signal()
    paletteSlotWritten = Signal(int, int, int, int)
    paletteBatchReady = Signal(object)
    _pendingAnimation = Signal(object)

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
        #: Stop event of the current long task (animation / follow-screen); one per task.
        self._follow_stop = threading.Event()
        #: (ui_row, col) with ui_row 0 = top of keyboard (number row); see ``per_key_grid``.
        self._key_colors: dict[tuple[int, int], tuple[int, int, int]] = {}
        self._key_grid_epoch = 0
        self._last_effect_snapshot: list[int] | None = None
        self._palette_mirror: dict[int, tuple[int, int, int]] = {}
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY
        #: Firmware effect re-sent when brightness changes (FIRMWARE_REAPPLY).
        self._fw_look: FirmwareEffectLook | None = None
        #: Last look applied or restored; re-applied when the light is switched on.
        self._saved_look: KeyboardLook | None = None
        self._pending_brightness: int | None = None
        self._brightness_timer = QTimer(self)
        self._brightness_timer.setSingleShot(True)
        self._brightness_timer.setInterval(200)
        self._brightness_timer.timeout.connect(self._flush_brightness_debounced)

        queued = Qt.ConnectionType.QueuedConnection
        self.inspectUpdate.connect(self._apply_inspect, queued)
        self.effectSnapshotUpdate.connect(self._apply_effect_snapshot, queued)
        self.paletteClearRequest.connect(self._clear_palette_mirror, queued)
        self.paletteSlotWritten.connect(self._apply_palette_slot_write, queued)
        self.paletteBatchReady.connect(self._on_palette_batch_ready, queued)
        self._pendingAnimation.connect(self._on_pending_animation, queued)

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

    @Property(bool, notify=lightChanged)
    def lightOn(self) -> bool:
        return self._kb is not None and not self._off

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
        self.lightChanged.emit()

    def _apply_effect_snapshot(self, snap: object) -> None:
        self._last_effect_snapshot = None if snap is None else list(snap)  # type: ignore[arg-type]

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
        self._fw_look = None

    def _use_brightness_context_of(self, look: KeyboardLook | None) -> None:
        if isinstance(look, FirmwareEffectLook):
            self._brightness_target = _BrightnessTarget.FIRMWARE_REAPPLY
            self._fw_look = look
        else:
            self._reset_brightness_context()

    @Slot(str, str, result=bool)
    def effectSupports(self, effect_name: str, capability: str) -> bool:
        """Whether ``capability`` is used by ``effect_name`` (speed, color, direction, reactive, save)."""

        caps = KEYBOARD_EFFECT_PARAMS.get(effect_name, frozenset())
        return capability in caps

    # --- long tasks (animation / follow-screen) --------------------------------

    def _stop_long_task(self) -> None:
        """Stop the running or queued animation / follow-screen (GUI thread, before submitting)."""
        self._follow_stop.set()

    def _new_long_task_stop(self) -> threading.Event:
        self._stop_long_task()
        ev = threading.Event()
        self._follow_stop = ev
        return ev

    @Slot()
    def stopFollowOrAnimation(self) -> None:
        self._stop_long_task()

    # --- persistence helpers (USB thread) ----------------------------------------

    def _remember_look(self, look: KeyboardLook) -> None:
        self._saved_look = look
        self.persistUpdate.emit({"look": look, "power": "on"})

    # --- connection --------------------------------------------------------------

    @Slot(int, int)
    def connectAt(self, bus: int, addr: int) -> None:
        def task() -> None:
            try:
                self._kb = open_keyboard(bus_addr=(bus, addr), debug=self._debug)
            except Exception as e:
                self.connectFailed.emit(f"{type(e).__name__}: {e}")
                raise
            self._bus = bus
            self._addr = addr
            self.connectedChanged.emit()
            self._do_inspect_emit()

        self._reset_brightness_context()
        self._worker.submit(task)

    @Slot()
    def disconnectDevice(self) -> None:
        self._stop_long_task()
        self._reset_brightness_context()

        def task() -> None:
            self._kb = None
            self._bus = -1
            self._addr = -1
            self.connectedChanged.emit()
            self.lightChanged.emit()
            self.effectSnapshotUpdate.emit(None)
            self.paletteClearRequest.emit()

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

    # --- light -------------------------------------------------------------------

    @Slot(bool)
    def setLightOn(self, on: bool) -> None:
        """Switch the backlight off, or on again re-applying the saved look (BR-6, BR-7)."""
        if not on:
            self._stop_long_task()
            self._reset_brightness_context()

            def off_task() -> None:
                if self._kb is None:
                    return
                snap = list(self._kb.get_effect())
                self._kb.turn_off()
                self.effectSnapshotUpdate.emit(snap)
                self.persistUpdate.emit({"power": "off"})
                self._do_inspect_emit()

            self._worker.submit(off_task)
            return

        look = self._saved_look
        if isinstance(look, AnimationLook):
            if self._start_animation(look, persist={"power": "on"}):
                return
            look = None
        snap = self._last_effect_snapshot
        self._stop_long_task()
        self._use_brightness_context_of(look)

        def on_task() -> None:
            if self._kb is None:
                return
            if look is not None:
                restore_keyboard(self._kb, KeyboardState(usb_id="", look=look))
            elif snap is not None:
                self._kb.set_effect(list(snap))
            else:
                self._kb.set_effect(KEYBOARD_EFFECTS["rainbow"]())
            self.persistUpdate.emit({"power": "on"})
            self._do_inspect_emit()

        self._worker.submit(on_task)

    # --- restore -----------------------------------------------------------------

    def restore(self, state: KeyboardState) -> None:
        """Apply a saved state through the worker (palette → brightness → off or look)."""
        self._saved_look = state.look
        if state.palette:
            self._palette_mirror.update(state.palette)
            self.paletteMirrorChanged.emit()
        if isinstance(state.look, PerKeyLook):
            self._key_colors = {
                (ui_row_to_device_row(r), c): rgb for r, c, rgb in state.look.cells
            }
            self._bump_key_grid()
        self._use_brightness_context_of(state.look if state.power == "on" else None)

        def task() -> None:
            if self._kb is None:
                return
            plan = restore_keyboard(self._kb, state)
            for warning in plan.warnings:
                self.restoreWarning.emit(
                    f"Keyboard: saved {warning}. Light state restored; look not applied."
                )
            if plan.pending_animation is not None:
                self._pendingAnimation.emit(plan.pending_animation)
            self._do_inspect_emit()

        self._worker.submit(task)

    def _on_pending_animation(self, look: object) -> None:
        if isinstance(look, AnimationLook):
            self._start_animation(look, persist=None)

    # --- brightness --------------------------------------------------------------

    def _brightness_task(self, value: int):
        v = max(0, min(50, int(value)))

        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_brightness(v)
            changes: dict[str, object] = {"brightness": v}
            fw = self._fw_look
            if (
                self._brightness_target == _BrightnessTarget.FIRMWARE_REAPPLY
                and fw is not None
                and not self._kb.is_off()
            ):
                fw = replace(fw, brightness=v)
                self._kb.set_effect(firmware_effect_payload(fw))
                self._fw_look = fw
                self._saved_look = fw
                changes["look"] = fw
            self.persistUpdate.emit(changes)
            self._do_inspect_emit()

        return task

    @Slot(int)
    def setBrightness(self, value: int) -> None:
        """Immediate USB brightness (no debounce); keeps firmware packet in sync when applicable."""
        self._worker.submit(self._brightness_task(value))

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
        self._worker.submit(self._brightness_task(v))

    # --- looks -------------------------------------------------------------------

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
        if name not in KEYBOARD_EFFECTS:
            return
        color = color_name.lower() if color_name.lower() in KEYBOARD_PALETTE_SLOT_COLORS else "random"
        direction = (
            direction_name.lower() if direction_name.lower() in KEYBOARD_DIRECTIONS else "none"
        )
        look = FirmwareEffectLook(
            effect=name,
            speed=max(0, min(10, int(speed))),
            brightness=max(0, min(50, int(brightness))),
            color=color,
            direction=direction,
            reactive=bool(reactive),
            save=bool(save),
        )
        self._stop_long_task()
        self._use_brightness_context_of(look)

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
            self._kb.set_effect(firmware_effect_payload(look))
            self._remember_look(look)
            self._do_inspect_emit()

        self._worker.submit(task)

    def _apply_solid(self, rgb: tuple[int, int, int]) -> None:
        look = SolidLook(rgb)
        self._stop_long_task()
        self._reset_brightness_context()

        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_color(rgb, None, False)
            self._remember_look(look)
            self._do_inspect_emit()

        self._worker.submit(task)

    @Slot(str)
    def setSolidNamed(self, name: str) -> None:
        rgb = SOLID_COLOR_NAMES.get(name.lower())
        if rgb is not None:
            self._apply_solid(rgb)

    @Slot(int, int, int)
    def setSolidRgb(self, r: int, g: int, b: int) -> None:
        self._apply_solid((max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))

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
            self.persistUpdate.emit({"palette": {s: rgb}})

        self._worker.submit(task)

    @Slot()
    def paletteRestore(self) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.restore_default_palette()
            self.paletteBatchReady.emit(dict(self._DEFAULT_PALETTE))
            self.persistUpdate.emit({"palette": dict(self._DEFAULT_PALETTE)})

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
            self.persistUpdate.emit({"palette": dict(batch)})

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

    def _start_animation(self, look: AnimationLook, *, persist: dict | None) -> bool:
        """Submit an animation as a stoppable long task. ``persist`` is emitted once it starts."""
        try:
            lines = Path(look.path).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return False
        self._reset_brightness_context()
        stop = self._new_long_task_stop()

        def sleep(seconds: float) -> None:
            if stop.wait(seconds):
                raise _Stopped

        def task() -> None:
            kb = self._kb
            if kb is None or stop.is_set():
                return
            if persist is not None:
                if "look" in persist:
                    self._saved_look = look
                self.persistUpdate.emit(dict(persist))

            def one_pass() -> None:
                run_animation_lines(
                    lines,
                    on_apply=lambda m: kb.set_key_colors(m),
                    on_brightness=kb.set_brightness,
                    sleep=sleep,
                )

            try:
                if look.forever:
                    while not stop.is_set():
                        one_pass()
                else:
                    for _ in range(look.loops):
                        if stop.is_set():
                            break
                        one_pass()
            except _Stopped:
                pass

        # Long-running: never hold the busy overlay (Stop must stay reachable).
        self._worker.submit(task, show_busy=False)
        return True

    @Slot(str, int, bool)
    def playAnimationFile(self, path: str, loops: int, forever: bool) -> None:
        p = Path(path)
        if not p.is_file():
            return
        look = AnimationLook(path=str(p.resolve()), loops=max(1, int(loops)), forever=bool(forever))
        self._start_animation(look, persist={"look": look, "power": "on"})

    @Slot(bool, int, int, int, int)
    def startFollowScreen(self, fullscreen: bool, x: int, y: int, w: int, h: int) -> None:
        self._reset_brightness_context()
        stop = self._new_long_task_stop()

        def task() -> None:
            if self._kb is None or stop.is_set():
                return
            if fullscreen:
                run_screen_follow_auto(self._kb, stop_event=stop)
            else:
                run_screen_follow_auto(
                    self._kb,
                    offset_x=x,
                    offset_y=y,
                    width=w,
                    height=h,
                    stop_event=stop,
                )

        self._worker.submit(task, show_busy=False)

    # --- per-key grid ------------------------------------------------------------

    def _grid_look(self) -> PerKeyLook:
        device = color_map_ui_to_device(dict(self._key_colors))
        return PerKeyLook(cells=tuple(sorted((r, c, rgb) for (r, c), rgb in device.items())))

    def _submit_grid(self, *, enable_user_mode: bool = True) -> None:
        look = self._grid_look()
        self._stop_long_task()
        self._reset_brightness_context()

        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_key_colors(
                {(r, c): rgb for r, c, rgb in look.cells},
                enable_user_mode_flag=enable_user_mode,
            )
            self._remember_look(look)

        self._worker.submit(task)

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
            self._submit_grid()

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
            self._submit_grid()

    @Slot(bool)
    def applyKeyGrid(self, enable_user_mode: bool) -> None:
        self._submit_grid(enable_user_mode=enable_user_mode)
