from __future__ import annotations

import enum
import json
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
    set_active_profile,
    ui_row_to_device_row,
    visual_cell_to_device,
)
from avell_storm_rgb.domain.physical_key_map import qt_input_to_key_id
from avell_storm_rgb.infrastructure.usb.ite8291_usb import (
    KEYBOARD_DIRECTIONS,
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
    effectSnapshotUpdate = Signal(object)
    replayPowerOnAvailableChanged = Signal()
    paletteMirrorChanged = Signal()
    paletteClearRequest = Signal()
    paletteSlotWritten = Signal(int, int, int, int)
    paletteBatchReady = Signal(object)
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
        self._last_fw_name: str = ""
        self._last_fw_speed: int = 5
        self._last_fw_brightness: int = 25
        self._last_fw_color_name: str = "random"
        self._last_fw_direction_name: str = "right"
        self._last_fw_reactive: bool = False
        self._last_fw_save: bool = False
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
        self._last_fw_name = ""

    @Slot(str, str, result=bool)
    def effectSupports(self, effect_name: str, capability: str) -> bool:
        """Whether ``capability`` is used by ``effect_name`` (speed, color, direction, reactive, save)."""

        caps = EFFECT_KWARGS.get(effect_name, frozenset())
        return capability in caps

    @Slot(int, int)
    def connectAt(self, bus: int, addr: int) -> None:
        def task() -> None:
            self._kb = open_keyboard(bus_addr=(bus, addr), debug=self._debug)
            self._bus = bus
            self._addr = addr
            self._load_mapping_for_current_device()
            self._evdev_unavailable_reason = ""
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
            self._device_mapping_key = "keyboard:unknown"
            self._calibration_overrides = {}
            self._calibration_unused_cells = set()
            self._evdev_unavailable_reason = ""
            self._stop_auto_calibration()
            self._clear_calibration_workflow()
            self.connectedChanged.emit()
            self.effectSnapshotUpdate.emit(None)
            self.paletteClearRequest.emit()
            self.calibrationChanged.emit()
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

            def task() -> None:
                if self._kb is None:
                    return
                self._kb.set_key_colors(self._build_device_color_map())

            self._worker.submit(task)

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

            def task() -> None:
                if self._kb is None:
                    return
                self._kb.set_key_colors(self._build_device_color_map())

            self._worker.submit(task)

    @Slot(bool)
    def applyKeyGrid(self, enable_user_mode: bool) -> None:
        self._brightness_target = _BrightnessTarget.GLOBAL_ONLY

        def task() -> None:
            if self._kb is None:
                return
            self._kb.set_key_colors(
                self._build_device_color_map(),
                enable_user_mode_flag=enable_user_mode,
            )

        self._worker.submit(task)

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
