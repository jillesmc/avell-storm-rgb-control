from __future__ import annotations

import enum
import json
import os
import sys
import threading
import time
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
from avell_storm_rgb.domain.keyboard_layouts import resolve_usb_default_profile
from avell_storm_rgb.domain import per_key_grid as pkg_per_key_grid
from avell_storm_rgb.domain.per_key_grid import (
    device_cell_from_linear_index,
    device_row_to_ui_row,
    find_all_device_cell_conflicts,
    key_id_to_device_cell,
    key_id_to_ui_cell,
    overrides_by_device_cell,
    profile_calibration_matrix_cell_order,
    profile_key_id_at_device_cell,
    resolve_key_to_device_cell,
    resolve_key_to_device_map,
    set_active_profile,
    ui_row_to_device_row,
    visual_cell_to_device,
)
from avell_storm_rgb.domain.physical_key_map import qt_input_to_key_id
from avell_storm_rgb.infrastructure.usb.ite8291_usb import (
    KEYBOARD_DIRECTIONS,
    KEYBOARD_EFFECT_PARAMS,
    KEYBOARD_EFFECTS,
    KEYBOARD_PALETTE_SLOT_COLORS,
    NUM_COLS,
    NUM_ROWS,
)

from app.core.usb_worker import UsbWorker
from app.core.calibration_evdev_capture import CalibrationEvdevCapture, evdev_available
from app.ui.adapters.keyboard_mapping_store import (
    load_device_overrides,
    load_device_profile_id,
    load_device_unused_cells,
    save_device_mapping,
    save_device_overrides,
)


def _debug_firmware_ui() -> bool:
    return os.environ.get("AVELL_DEBUG_FIRMWARE_UI", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


# #region agent log
_AGENT_DEBUG_LOG = Path("/home/jilles/.cursor/.cursor/debug-d917c9.log")


def _agent_debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "d917c9",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        with _AGENT_DEBUG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except OSError:
        pass


# #endregion


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
    _restoredKeyGrid = Signal(object)
    calibrationChanged = Signal()
    calibrationPendingChanged = Signal()
    calibrationMessageChanged = Signal()
    calibrationModeChanged = Signal()
    calibrationInputChanged = Signal()
    evdevKeyPressed = Signal(str, int)
    layoutProfileChanged = Signal()

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
        self._key_colors: dict[str, tuple[int, int, int]] = {}
        self._layout_profile_id = "legacy_builtin"
        self._layout_visual_version = 1
        self._layout_key_gap_u = 0.0
        self._layout_bounds_min_x = 0.0
        self._layout_bounds_min_y = 0.0
        self._layout_bounds_width_u = 21.0
        self._layout_bounds_height_u = 6.0
        self._key_grid_epoch = 0
        self._last_effect_snapshot: list[int] | None = None
        self._palette_mirror: dict[int, tuple[int, int, int]] = {}
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY
        #: Firmware effect re-sent when brightness changes (FIRMWARE_REAPPLY).
        self._fw_look: FirmwareEffectLook | None = None
        #: Last look applied or restored; re-applied when the light is switched on.
        self._saved_look: KeyboardLook | None = None
        self._pending_brightness: int | None = None
        self._calibration_overrides: dict[str, tuple[int, int]] = {}
        self._calibration_pending: tuple[int, int] | None = None
        self._calibration_preview_cell: tuple[int, int] | None = None
        self._calibration_undo: list[tuple[str, tuple[int, int] | None]] = []
        self._calibration_mode = "manual"
        self._calibration_auto_running = False
        self._calibration_auto_paused = False
        self._calibration_auto_index = 0
        self._calibration_auto_cells: list[tuple[int, int]] = []
        self._calibration_unused_cells: set[tuple[int, int]] = set()
        self._calibration_selected_cell: tuple[int, int] | None = None
        self._calibration_message = ""
        self._calibration_evdev_active = False
        self._evdev_unavailable_reason = ""
        self._device_mapping_key = "keyboard:unknown"
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
        self._restoredKeyGrid.connect(self._on_restored_key_grid, queued)
        self._evdev_capture: CalibrationEvdevCapture | None = None
        if evdev_available():
            self._evdev_capture = CalibrationEvdevCapture(self._emit_evdev_key_pressed)
            self.evdevKeyPressed.connect(
                self._on_evdev_calibration_key, Qt.ConnectionType.QueuedConnection
            )
        self.calibrationPendingChanged.connect(self._sync_calibration_input_capture)

    @Property(bool, notify=calibrationInputChanged)
    def calibrationEvdevActive(self) -> bool:
        return self._calibration_evdev_active

    @Property(bool, notify=calibrationInputChanged)
    def calibrationEvdevExclusive(self) -> bool:
        capture = self._evdev_capture
        return bool(capture and capture.active and capture.exclusive)

    def _emit_evdev_key_pressed(self, key_id: str, code: int) -> None:
        self.evdevKeyPressed.emit(key_id, code)

    def _on_evdev_calibration_key(self, key_id: str, code: int) -> None:
        # #region agent log
        _agent_debug_log(
            "H-S4",
            "keyboard_backend._on_evdev_calibration_key",
            "evdev_key",
            {
                "key_id": key_id,
                "code": code,
                "pending": self._calibration_pending is not None,
                "auto_paused": self._calibration_auto_paused,
            },
        )
        # #endregion
        if self._calibration_pending is None or self._calibration_auto_paused:
            return
        self._set_calibration_message("")
        self.commitCalibrationKey(key_id)

    def _sync_calibration_input_capture(self) -> None:
        capture = self._evdev_capture
        prev = self._calibration_evdev_active
        if capture is None:
            self._calibration_evdev_active = False
        elif self.calibrationListening:
            if self._evdev_unavailable_reason:
                self._calibration_evdev_active = False
            else:
                self._calibration_evdev_active = capture.start()
                if not self._calibration_evdev_active:
                    self._evdev_unavailable_reason = capture.last_error
            err = capture.last_error or self._evdev_unavailable_reason
            if not self._calibration_evdev_active and err:
                self._set_calibration_message(err)
            elif self._calibration_evdev_active and not capture.exclusive:
                self._set_calibration_message(
                    "Shared input capture (no exclusive grab). ScrLk should work; "
                    "PrtSc may still open the screenshot tool."
                )
        else:
            capture.stop()
            self._calibration_evdev_active = False
        if prev != self._calibration_evdev_active:
            self.calibrationInputChanged.emit()

    @Slot()
    def shutdownCalibrationInput(self) -> None:
        if self._evdev_capture is not None:
            self._evdev_capture.stop()
        if self._calibration_evdev_active:
            self._calibration_evdev_active = False
            self.calibrationInputChanged.emit()

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

    @Property(str, notify=layoutProfileChanged)
    def layoutProfileId(self) -> str:
        return self._layout_profile_id

    @Property("QVariantList", notify=layoutProfileChanged)
    def keyLayoutKeys(self) -> list[dict[str, int | str]]:
        from avell_storm_rgb.domain.per_key_grid import KEY_LAYOUT_KEYS

        return KEY_LAYOUT_KEYS

    @Property(int, notify=layoutProfileChanged)
    def layoutVisualVersion(self) -> int:
        return self._layout_visual_version

    @Property(float, notify=layoutProfileChanged)
    def layoutKeyGapU(self) -> float:
        return self._layout_key_gap_u

    @Property(float, notify=layoutProfileChanged)
    def layoutBoundsMinX(self) -> float:
        return self._layout_bounds_min_x

    @Property(float, notify=layoutProfileChanged)
    def layoutBoundsMinY(self) -> float:
        return self._layout_bounds_min_y

    @Property(float, notify=layoutProfileChanged)
    def layoutBoundsWidthU(self) -> float:
        return self._layout_bounds_width_u

    @Property(float, notify=layoutProfileChanged)
    def layoutBoundsHeightU(self) -> float:
        return self._layout_bounds_height_u

    @Property("QVariantList", notify=calibrationChanged)
    def calibratedKeyIds(self) -> list[str]:
        return sorted(self._calibration_overrides.keys())

    @Property("QVariantList", notify=calibrationChanged)
    def conflictKeyIds(self) -> list[str]:
        conflicts = find_all_device_cell_conflicts(self._calibration_overrides)
        seen: set[str] = set()
        out: list[str] = []
        for key_ids in conflicts.values():
            for key_id in key_ids:
                if key_id not in seen:
                    seen.add(key_id)
                    out.append(key_id)
        return out

    @Property(str, notify=calibrationChanged)
    def calibrationConflictSummary(self) -> str:
        conflicts = find_all_device_cell_conflicts(self._calibration_overrides)
        if not conflicts:
            return ""
        lines: list[str] = []
        for (dr, dc), key_ids in sorted(conflicts.items()):
            ids = sorted(key_ids)
            lines.append(f"LED ({dr},{dc}): {' ↔ '.join(ids)}")
        return "\n".join(lines)

    @Slot(str, result=str)
    def calibrationConflictTooltip(self, key_id: str) -> str:
        key_id = key_id.strip()
        if not key_id:
            return ""
        conflicts = find_all_device_cell_conflicts(self._calibration_overrides)
        for (dr, dc), key_ids in conflicts.items():
            if key_id not in key_ids:
                continue
            others = sorted(k for k in key_ids if k != key_id)
            if not others:
                continue
            return f"LED ({dr},{dc}) shared with: {', '.join(others)}"
        return ""

    @Property("QVariantList", notify=calibrationChanged)
    def calibrationOverrides(self) -> list[dict[str, int | str]]:
        rows: list[dict[str, int | str]] = []
        for key_id, (row, col) in sorted(self._calibration_overrides.items()):
            rows.append({"keyId": key_id, "row": row, "col": col})
        return rows

    @Property(int, notify=calibrationPendingChanged)
    def calibrationPendingDeviceRow(self) -> int:
        if self._calibration_pending is None:
            return -1
        return self._calibration_pending[0]

    @Property(int, notify=calibrationPendingChanged)
    def calibrationPendingDeviceCol(self) -> int:
        if self._calibration_pending is None:
            return -1
        return self._calibration_pending[1]

    @Property(str, notify=calibrationPendingChanged)
    def calibrationPendingProfileKeyId(self) -> str:
        if self._calibration_pending is None:
            return ""
        dr, dc = self._calibration_pending
        return profile_key_id_at_device_cell(dr, dc)

    @Property(bool, notify=calibrationChanged)
    def calibrationCanUndo(self) -> bool:
        return len(self._calibration_undo) > 0

    @Property(str, notify=calibrationModeChanged)
    def calibrationMode(self) -> str:
        return self._calibration_mode

    @Property(bool, notify=calibrationModeChanged)
    def calibrationAutoRunning(self) -> bool:
        return self._calibration_auto_running

    @Property(bool, notify=calibrationModeChanged)
    def calibrationAutoPaused(self) -> bool:
        return self._calibration_auto_paused

    @Property(str, notify=calibrationChanged)
    def calibrationAutoProgress(self) -> str:
        total = len(self._calibration_auto_cells)
        if total <= 0:
            total = NUM_ROWS * NUM_COLS
        return f"{min(self._calibration_auto_index, total)} / {total}"

    @Property(str, notify=calibrationMessageChanged)
    def calibrationMessage(self) -> str:
        return self._calibration_message

    @Property(bool, notify=calibrationPendingChanged)
    def calibrationListening(self) -> bool:
        return (
            self._kb is not None
            and self._calibration_pending is not None
            and not self._calibration_auto_paused
        )

    @Property(int, notify=calibrationPendingChanged)
    def calibrationPendingVisualRow(self) -> int:
        if self._calibration_pending is None:
            return -1
        dr, _ = self._calibration_pending
        return device_row_to_ui_row(dr)

    @Property(int, notify=calibrationPendingChanged)
    def calibrationSelectedVisualRow(self) -> int:
        if self._calibration_selected_cell is None:
            return -1
        dr, _ = self._calibration_selected_cell
        return device_row_to_ui_row(dr)

    @Property(int, notify=calibrationPendingChanged)
    def calibrationSelectedCol(self) -> int:
        if self._calibration_selected_cell is None:
            return -1
        return self._calibration_selected_cell[1]

    @Property(int, notify=keyGridChanged)
    def keyGridEpoch(self) -> int:
        return self._key_grid_epoch

    def _bump_key_grid(self) -> None:
        self._key_grid_epoch += 1
        self.keyGridChanged.emit()

    @Slot(str, result=str)
    def keyHexById(self, key_id: str) -> str:
        t = self._key_colors.get(key_id)
        if t is None:
            return "#353535"
        r, g, b = t
        return f"#{r:02x}{g:02x}{b:02x}"

    @Slot(str, result=int)
    def resolvedDeviceRowById(self, key_id: str) -> int:
        try:
            row, _ = resolve_key_to_device_cell(key_id, self._calibration_overrides)
        except ValueError:
            return -1
        return row

    @Slot(str, result=int)
    def resolvedDeviceColById(self, key_id: str) -> int:
        try:
            _, col = resolve_key_to_device_cell(key_id, self._calibration_overrides)
        except ValueError:
            return -1
        return col

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

    def _compute_device_mapping_key(self) -> str:
        if self._kb is None:
            return "keyboard:unknown"
        dev = getattr(getattr(self._kb, "channel", None), "dev", None)
        vendor = getattr(dev, "idVendor", 0)
        product = getattr(dev, "idProduct", 0)
        rev = getattr(dev, "bcdDevice", 0)
        return f"keyboard:{vendor:04x}:{product:04x}:{rev:04x}:{self._bus}:{self._addr}"

    def _usb_default_profile_id(self) -> str:
        if self._kb is None:
            return "legacy_builtin"
        dev = getattr(getattr(self._kb, "channel", None), "dev", None)
        product = int(getattr(dev, "idProduct", 0))
        return resolve_usb_default_profile(product)

    def _apply_layout_profile(self, profile_id: str) -> None:
        profile = set_active_profile(profile_id)
        self._layout_profile_id = profile_id
        if profile.visual_layout is not None and profile.layout_bounds_u is not None:
            min_x, min_y, max_x, max_y = profile.layout_bounds_u
            self._layout_visual_version = 2
            self._layout_key_gap_u = profile.visual_layout.key_gap
            self._layout_bounds_min_x = min_x
            self._layout_bounds_min_y = min_y
            self._layout_bounds_width_u = max_x - min_x
            self._layout_bounds_height_u = max_y - min_y
        else:
            self._layout_visual_version = 1
            self._layout_key_gap_u = 0.0
            self._layout_bounds_min_x = 0.0
            self._layout_bounds_min_y = 0.0
            self._layout_bounds_width_u = 21.0
            self._layout_bounds_height_u = 6.0
        self.layoutProfileChanged.emit()

    def _load_mapping_for_current_device(self) -> None:
        self._device_mapping_key = self._compute_device_mapping_key()
        default_profile = self._usb_default_profile_id()
        profile_id = load_device_profile_id(self._device_mapping_key, default_profile)
        self._apply_layout_profile(profile_id)
        self._calibration_overrides = load_device_overrides(self._device_mapping_key)
        self._calibration_unused_cells = load_device_unused_cells(self._device_mapping_key)
        self.calibrationChanged.emit()

    def _save_mapping_for_current_device(self) -> None:
        save_device_mapping(
            self._device_mapping_key,
            self._layout_profile_id,
            self._calibration_overrides,
            self._calibration_unused_cells,
        )
        self.calibrationChanged.emit()

    def _build_device_color_map(self) -> dict[tuple[int, int], tuple[int, int, int]]:
        out: dict[tuple[int, int], tuple[int, int, int]] = {}
        for key_id, color in self._key_colors.items():
            try:
                dev_cell = resolve_key_to_device_cell(key_id, self._calibration_overrides)
            except ValueError:
                continue
            out[dev_cell] = color
        return out

    def _clear_calibration_workflow(self) -> None:
        self._calibration_pending = None
        self._calibration_preview_cell = None
        self._calibration_selected_cell = None
        self._calibration_undo.clear()
        self.calibrationPendingChanged.emit()

    def _set_calibration_message(self, message: str) -> None:
        message = message.strip()
        if self._calibration_message != message:
            self._calibration_message = message
            self.calibrationMessageChanged.emit()

    def _stop_auto_calibration(self, *, message: str = "") -> None:
        self._calibration_auto_running = False
        self._calibration_auto_paused = False
        self._calibration_auto_index = 0
        self._calibration_auto_cells = []
        self._calibration_pending = None
        self._calibration_preview_cell = None
        self.calibrationPendingChanged.emit()
        self.calibrationModeChanged.emit()
        if message:
            self._set_calibration_message(message)
        self._restore_after_calibration_preview()

    def _purge_stale_unused_for_profile_keys(self) -> None:
        """Drop unused marks on LEDs the active profile maps to a key (stale generic marks)."""

        profile_cells = set(pkg_per_key_grid.BASE_KEY_TO_DEVICE_CELL.values())
        before = len(self._calibration_unused_cells)
        self._calibration_unused_cells -= profile_cells
        if len(self._calibration_unused_cells) != before:
            self._persist_calibration_overrides()

    def _cell_is_auto_done(self, device_row: int, col: int) -> bool:
        """True when auto-cal may skip this matrix LED."""

        cell = (int(device_row), int(col))
        if cell in self._calibration_unused_cells:
            return True
        assignee = overrides_by_device_cell(self._calibration_overrides).get(cell)
        if assignee is None:
            return False
        profile_key = profile_key_id_at_device_cell(device_row, col)
        if profile_key and assignee != profile_key:
            return False
        return True

    def _advance_auto_calibration(self) -> None:
        if not self._calibration_auto_running or self._calibration_auto_paused:
            return
        if not self._calibration_auto_cells:
            self._calibration_auto_cells = profile_calibration_matrix_cell_order()
        total = len(self._calibration_auto_cells)
        while self._calibration_auto_index < total:
            device_row, col = self._calibration_auto_cells[self._calibration_auto_index]
            self._calibration_auto_index += 1
            if self._cell_is_auto_done(device_row, col):
                continue
            cell = (device_row, col)
            self._calibration_pending = cell
            self._calibration_preview_cell = cell
            self.calibrationPendingChanged.emit()
            self.calibrationChanged.emit()
            self._apply_calibration_preview_async()
            self._set_calibration_message("")
            return
        self._stop_auto_calibration(message="Calibration complete.")

    def _persist_calibration_overrides(self) -> None:
        save_device_mapping(
            self._device_mapping_key,
            self._layout_profile_id,
            self._calibration_overrides,
            self._calibration_unused_cells,
        )
        self.calibrationChanged.emit()

    def _apply_calibration_preview_async(self) -> None:
        cell = self._calibration_preview_cell
        if cell is None:
            return

        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_key_colors({cell: (255, 255, 255)}, enable_user_mode_flag=True)

        self._worker.submit(task, show_busy=False)

    def _restore_after_calibration_preview(self) -> None:
        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_key_colors(
                self._build_device_color_map(),
                enable_user_mode_flag=True,
            )

        self._worker.submit(task, show_busy=False)

    @Slot(int, result=int)
    def deviceRowForVisualRow(self, visual_row: int) -> int:
        if not 0 <= visual_row < NUM_ROWS:
            return -1
        return ui_row_to_device_row(visual_row)

    @Slot(int, int, result=bool)
    def isCalibrationCellPending(self, visual_row: int, col: int) -> bool:
        if self._calibration_pending is None:
            return False
        dr, dc = visual_cell_to_device(visual_row, col)
        return self._calibration_pending == (dr, dc)

    @Slot(int, int, result=str)
    def calibrationCellAssignee(self, visual_row: int, col: int) -> str:
        dr, dc = visual_cell_to_device(visual_row, col)
        for key_id, cell in self._calibration_overrides.items():
            if cell == (dr, dc):
                return key_id
        return ""

    @Slot(int, int, result=bool)
    def isCalibrationCellConflict(self, visual_row: int, col: int) -> bool:
        dr, dc = visual_cell_to_device(visual_row, col)
        conflicts = find_all_device_cell_conflicts(self._calibration_overrides)
        key_ids = conflicts.get((dr, dc), [])
        return len(key_ids) > 1

    @Slot(int, int, result=bool)
    def isCalibrationCellUnused(self, visual_row: int, col: int) -> bool:
        dr, dc = visual_cell_to_device(visual_row, col)
        return (dr, dc) in self._calibration_unused_cells

    @Slot(int, int, result=bool)
    def isCalibrationCellSelected(self, visual_row: int, col: int) -> bool:
        if self._calibration_selected_cell is None:
            return False
        dr, dc = visual_cell_to_device(visual_row, col)
        return self._calibration_selected_cell == (dr, dc)

    @Slot(int, int, result=str)
    def calibrationCellProfileHint(self, visual_row: int, col: int) -> str:
        dr, dc = visual_cell_to_device(visual_row, col)
        if self.calibrationCellAssignee(visual_row, col):
            return ""
        if (dr, dc) in self._calibration_unused_cells:
            return ""
        return profile_key_id_at_device_cell(dr, dc)

    @Slot(str)
    def setCalibrationMode(self, mode: str) -> None:
        mode = mode.strip().lower()
        if mode not in ("manual", "auto"):
            return
        if self._calibration_mode == mode:
            return
        self._stop_auto_calibration()
        self._calibration_mode = mode
        self.calibrationModeChanged.emit()

    @Slot()
    def startAutoCalibration(self) -> None:
        if self._kb is None or self._calibration_mode != "auto":
            return
        self._calibration_auto_running = True
        self._calibration_auto_paused = False
        self._calibration_auto_index = 0
        self._calibration_auto_cells = profile_calibration_matrix_cell_order()
        self._purge_stale_unused_for_profile_keys()
        self._calibration_selected_cell = None
        self.calibrationModeChanged.emit()
        self._advance_auto_calibration()

    @Slot()
    def stopAutoCalibration(self) -> None:
        self._stop_auto_calibration()

    @Slot()
    def pauseAutoCalibration(self) -> None:
        if not self._calibration_auto_running or self._calibration_auto_paused:
            return
        self._calibration_auto_paused = True
        self._calibration_pending = None
        self._calibration_preview_cell = None
        self.calibrationPendingChanged.emit()
        self.calibrationModeChanged.emit()
        self._restore_after_calibration_preview()

    @Slot()
    def resumeAutoCalibration(self) -> None:
        if not self._calibration_auto_running or not self._calibration_auto_paused:
            return
        self._calibration_auto_paused = False
        self.calibrationModeChanged.emit()
        self._advance_auto_calibration()

    @Slot()
    def markCalibrationCellUnused(self) -> None:
        if self._calibration_pending is None:
            return
        dr, dc = self._calibration_pending
        assignee = overrides_by_device_cell(self._calibration_overrides).get((dr, dc))
        if assignee:
            self.clearCalibrationOverride(assignee)
        self._calibration_unused_cells.add((dr, dc))
        self._calibration_pending = None
        self._calibration_preview_cell = None
        self.calibrationPendingChanged.emit()
        self._persist_calibration_overrides()
        self._restore_after_calibration_preview()
        self._set_calibration_message("")
        if self._calibration_auto_running and not self._calibration_auto_paused:
            self._advance_auto_calibration()

    @Slot(int, int)
    def clearCalibrationCell(self, visual_row: int, col: int) -> None:
        if not (0 <= visual_row < NUM_ROWS and 0 <= col < NUM_COLS):
            return
        dr, dc = visual_cell_to_device(visual_row, col)
        assignee = overrides_by_device_cell(self._calibration_overrides).get((dr, dc))
        if assignee:
            self.clearCalibrationOverride(assignee)
        self._calibration_unused_cells.discard((dr, dc))
        if self._calibration_selected_cell == (dr, dc):
            self._calibration_selected_cell = None
            self.calibrationPendingChanged.emit()
        self._persist_calibration_overrides()

    @Slot(int, int, int)
    def commitCalibrationFromPhysicalKey(
        self, qt_key: int, modifiers: int, native_scan_code: int
    ) -> None:
        if self._calibration_pending is None or self._calibration_auto_paused:
            return
        key_id, err = qt_input_to_key_id(qt_key, modifiers, native_scan_code)
        if err == "modifier":
            self._set_calibration_message(
                "Release Shift, Ctrl, Alt, or Meta before pressing the key."
            )
            return
        if key_id is None:
            self._set_calibration_message(
                "Unrecognized key — use Mark as unused if this LED has no key."
            )
            return
        self._set_calibration_message("")
        self.commitCalibrationKey(key_id)

    @Slot(str)
    def commitCalibrationFromLayoutKey(self, key_id: str) -> None:
        key_id = key_id.strip()
        if not key_id or key_id == "_spacer":
            return
        if self._calibration_pending is None:
            self._set_calibration_message("Select an LED cell in the grid first.")
            return
        if self._calibration_auto_paused:
            return
        self._set_calibration_message("")
        self.commitCalibrationKey(key_id)

    @Slot(int, int)
    def selectCalibrationCellForUnbind(self, visual_row: int, col: int) -> None:
        if self._kb is None or not (0 <= visual_row < NUM_ROWS and 0 <= col < NUM_COLS):
            return
        if not self.calibrationCellAssignee(visual_row, col):
            return
        dr, dc = visual_cell_to_device(visual_row, col)
        self._calibration_selected_cell = (dr, dc)
        self._calibration_pending = None
        self._calibration_preview_cell = None
        self.calibrationPendingChanged.emit()
        self.calibrationChanged.emit()
        self._restore_after_calibration_preview()

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
            self._close_device()
            try:
                self._kb = open_keyboard(bus_addr=(bus, addr), debug=self._debug)
            except Exception as e:
                self.connectFailed.emit(f"{type(e).__name__}: {e}")
                raise
            self._bus = bus
            self._addr = addr
            self._load_mapping_for_current_device()
            self._evdev_unavailable_reason = ""
            self.connectedChanged.emit()
            self._do_inspect_emit()

        self._reset_brightness_context()
        self._worker.submit(task)

    @Slot()
    def disconnectDevice(self) -> None:
        self._stop_long_task()
        self._reset_brightness_context()

        def task() -> None:
            self._close_device()
            self._bus = -1
            self._addr = -1
            self._device_mapping_key = "keyboard:unknown"
            self._calibration_overrides = {}
            self._calibration_unused_cells = set()
            self._evdev_unavailable_reason = ""
            self._stop_auto_calibration()
            self._clear_calibration_workflow()
            self.connectedChanged.emit()
            self.lightChanged.emit()
            self.effectSnapshotUpdate.emit(None)
            self.paletteClearRequest.emit()
            self.calibrationChanged.emit()

        self._worker.submit(task)

    def _close_device(self) -> None:
        """USB thread: release the current handle so the next open does not hit EBUSY."""
        kb, self._kb = self._kb, None
        if kb is not None:
            try:
                kb.close()
            except Exception:  # noqa: BLE001 - device may already be gone
                pass

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
        self._use_brightness_context_of(state.look if state.power == "on" else None)

        def task() -> None:
            if self._kb is None:
                return
            plan = restore_keyboard(self._kb, state)
            if isinstance(state.look, PerKeyLook):
                # Overrides for this device are loaded by the connect task, so map here.
                self._restoredKeyGrid.emit(self._key_colors_from_cells(state.look.cells))
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
        device = self._build_device_color_map()
        return PerKeyLook(cells=tuple(sorted((r, c, rgb) for (r, c), rgb in device.items())))

    def _key_colors_from_cells(self, cells) -> dict[str, tuple[int, int, int]]:
        """Saved device cells → key ids, using this device's calibration overrides (USB thread)."""
        by_cell: dict[tuple[int, int], str] = {}
        for key_id, cell in resolve_key_to_device_map(self._calibration_overrides).items():
            by_cell.setdefault(cell, key_id)
        return {by_cell[(r, c)]: rgb for r, c, rgb in cells if (r, c) in by_cell}

    def _on_restored_key_grid(self, grid: object) -> None:
        if isinstance(grid, dict):
            self._key_colors = dict(grid)
            self._bump_key_grid()

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

    @Slot(str, int, int, int, bool)
    def setKeyById(self, key_id: str, r: int, g: int, b: int, apply_now: bool) -> None:
        try:
            key_id_to_ui_cell(key_id)
        except ValueError:
            return
        self._key_colors[key_id] = (
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b)),
        )
        self._bump_key_grid()
        if apply_now:
            self._submit_grid()

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
                key_id_to_ui_cell(key_id)
            except ValueError:
                continue
            self._key_colors[key_id] = (rv, gv, bv)
            changed = True
        if not changed:
            return
        self._bump_key_grid()
        if apply_now:
            self._submit_grid()

    @Slot(bool)
    def applyKeyGrid(self, enable_user_mode: bool) -> None:
        self._submit_grid(enable_user_mode=enable_user_mode)

    @Slot(str, int, int)
    def setCalibrationOverride(self, key_id: str, device_row: int, col: int) -> None:
        """Persist override using firmware ``device_row`` (not visual/UI row)."""

        if not (0 <= device_row < NUM_ROWS and 0 <= col < NUM_COLS):
            return
        try:
            key_id_to_ui_cell(key_id)
        except ValueError:
            return
        cell = (int(device_row), int(col))
        for other_id in list(self._calibration_overrides):
            if other_id != key_id and self._calibration_overrides[other_id] == cell:
                del self._calibration_overrides[other_id]
        self._calibration_overrides[str(key_id)] = cell
        self._persist_calibration_overrides()

    @Slot(str)
    def clearCalibrationOverride(self, key_id: str) -> None:
        if key_id in self._calibration_overrides:
            del self._calibration_overrides[key_id]
            self._persist_calibration_overrides()

    @Slot()
    def resetCalibrationProfile(self) -> None:
        self._calibration_overrides = {}
        self._calibration_unused_cells = set()
        self._stop_auto_calibration()
        self._clear_calibration_workflow()
        self._persist_calibration_overrides()
        self._restore_after_calibration_preview()
        self._set_calibration_message("")

    @Slot(int, int)
    def selectCalibrationCell(self, visual_row: int, col: int) -> None:
        if self._kb is None or not (0 <= visual_row < NUM_ROWS and 0 <= col < NUM_COLS):
            return
        if self._calibration_auto_running:
            return
        dr, dc = visual_cell_to_device(visual_row, col)
        self._calibration_selected_cell = None
        self._calibration_unused_cells.discard((dr, dc))
        self._calibration_pending = (dr, dc)
        self._calibration_preview_cell = (dr, dc)
        self.calibrationPendingChanged.emit()
        self._set_calibration_message("")
        self._apply_calibration_preview_async()

    @Slot(str)
    def commitCalibrationKey(self, key_id: str) -> None:
        key_id = key_id.strip()
        if self._calibration_pending is None:
            # #region agent log
            _agent_debug_log(
                "H-S4",
                "keyboard_backend.commitCalibrationKey",
                "rejected_no_pending",
                {"key_id": key_id},
            )
            # #endregion
            return
        try:
            key_id_to_ui_cell(key_id)
        except ValueError as exc:
            # #region agent log
            _agent_debug_log(
                "H-S4",
                "keyboard_backend.commitCalibrationKey",
                "rejected_unknown_key",
                {"key_id": key_id, "error": str(exc)},
            )
            # #endregion
            return
        dr, dc = self._calibration_pending
        prev = self._calibration_overrides.get(key_id)
        self._calibration_undo.append((key_id, prev))
        self._calibration_unused_cells.discard((dr, dc))
        self.setCalibrationOverride(key_id, dr, dc)
        self._calibration_pending = None
        self._calibration_preview_cell = None
        self.calibrationPendingChanged.emit()
        self._restore_after_calibration_preview()
        # #region agent log
        _agent_debug_log(
            "H-S4",
            "keyboard_backend.commitCalibrationKey",
            "committed",
            {"key_id": key_id, "device_row": dr, "device_col": dc},
        )
        # #endregion
        if self._calibration_auto_running and not self._calibration_auto_paused:
            self._advance_auto_calibration()

    @Slot()
    def undoLastCalibration(self) -> None:
        if not self._calibration_undo:
            return
        key_id, prev = self._calibration_undo.pop()
        if prev is None:
            self.clearCalibrationOverride(key_id)
        else:
            dr, dc = prev
            self.setCalibrationOverride(key_id, dr, dc)
        self.calibrationChanged.emit()

    @Slot(str)
    def setLayoutProfileId(self, profile_id: str) -> None:
        profile_id = profile_id.strip()
        if not profile_id:
            return
        try:
            self._apply_layout_profile(profile_id)
        except FileNotFoundError:
            return
        self._calibration_overrides = {}
        self._calibration_unused_cells = set()
        self._stop_auto_calibration()
        self._clear_calibration_workflow()
        self._key_colors.clear()
        self._bump_key_grid()
        self._persist_calibration_overrides()
        self._restore_after_calibration_preview()

    @Slot(result="QStringList")
    def listLayoutProfileIds(self) -> list[str]:
        from avell_storm_rgb.domain.keyboard_layouts import list_profile_ids

        return list_profile_ids()
