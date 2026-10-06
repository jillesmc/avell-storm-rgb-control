"""Calibration grid-first workflow (no USB hardware)."""

from __future__ import annotations

from PySide6.QtCore import Qt

from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS

from avell_storm_rgb.domain.per_key_grid import (
    device_cell_from_linear_index,
    key_id_to_device_cell,
    profile_calibration_cell_order,
    profile_calibration_matrix_cell_order,
    set_active_profile,
    ui_row_to_device_row,
    visual_cell_to_device,
)

from app.core.usb_worker import UsbWorker
from app.ui.adapters.keyboard_backend import KeyboardBackend


def test_visual_cell_to_device_top_left_is_esc_row() -> None:
    set_active_profile("abnt2_laptop_21")
    assert visual_cell_to_device(0, 0) == (5, 0)
    assert visual_cell_to_device(5, 0) == (0, 0)


def test_select_calibration_cell_sets_pending_device_coords() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb.selectCalibrationCell(0, 0)
    assert kb.calibrationPendingDeviceRow == 5
    assert kb.calibrationPendingDeviceCol == 0


def test_commit_calibration_key_persists_device_override() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb._kb = object()
    kb.selectCalibrationCell(0, 0)
    kb.commitCalibrationKey("esc")
    assert kb._calibration_overrides["esc"] == (5, 0)
    assert kb.calibrationPendingDeviceRow == -1


def test_commit_from_physical_key_maps_q() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb._kb = object()
    kb.selectCalibrationCell(1, 4)
    kb.commitCalibrationFromPhysicalKey(int(Qt.Key.Key_Q), 0, 0)
    dr, dc = visual_cell_to_device(1, 4)
    assert kb._calibration_overrides["q"] == (dr, dc)


def test_commit_from_layout_key_maps_scrlk() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb._kb = object()
    kb.selectCalibrationCell(0, 14)
    kb.commitCalibrationFromLayoutKey("scrlk")
    assert kb._calibration_overrides["scrlk"] == visual_cell_to_device(0, 14)
    assert kb.calibrationPendingDeviceRow == -1


def test_layout_key_requires_pending_cell() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb.commitCalibrationFromLayoutKey("scrlk")
    assert "scrlk" not in kb._calibration_overrides
    assert "grid" in kb.calibrationMessage.lower()


def test_layout_key_advances_auto_mode() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb._kb = object()
    kb.setCalibrationMode("auto")
    kb.startAutoCalibration()
    idx_before = kb._calibration_auto_index
    hint = kb.calibrationCellProfileHint(
        kb.calibrationPendingVisualRow,
        kb.calibrationPendingDeviceCol,
    )
    assert hint
    kb.commitCalibrationFromLayoutKey(hint)
    assert kb._calibration_auto_index > idx_before


def test_physical_key_rejects_shift_modifier() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb.selectCalibrationCell(0, 0)
    kb.commitCalibrationFromPhysicalKey(
        int(Qt.Key.Key_Q), Qt.KeyboardModifier.ShiftModifier.value, 0
    )
    assert "q" not in kb._calibration_overrides
    assert "Shift" in kb.calibrationMessage or "Release" in kb.calibrationMessage


def test_move_key_override_to_new_cell() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb._kb = object()
    kb.setCalibrationOverride("q", 4, 8)
    kb.selectCalibrationCell(2, 5)
    kb.commitCalibrationKey("q")
    assert kb._calibration_overrides["q"] == visual_cell_to_device(2, 5)
    assert kb.calibrationCellAssignee(1, 8) == ""


def test_undo_last_calibration_restores_previous() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb.setCalibrationOverride("esc", 4, 1)
    kb._kb = object()
    kb.selectCalibrationCell(0, 0)
    kb.commitCalibrationKey("esc")
    assert kb._calibration_overrides["esc"] == (5, 0)
    kb.undoLastCalibration()
    assert kb._calibration_overrides["esc"] == (4, 1)


def test_undo_removes_fresh_override() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb._kb = object()
    kb.selectCalibrationCell(0, 0)
    kb.commitCalibrationKey("esc")
    assert "esc" in kb._calibration_overrides
    kb.undoLastCalibration()
    assert "esc" not in kb._calibration_overrides


def test_reset_clears_overrides_unused_and_undo() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb.selectCalibrationCell(1, 2)
    kb.commitCalibrationKey("f1")
    kb._calibration_unused_cells.add((3, 3))
    kb.resetCalibrationProfile()
    assert kb._calibration_overrides == {}
    assert kb._calibration_unused_cells == set()
    assert not kb.calibrationCanUndo
    assert kb.calibrationPendingDeviceRow == -1


def test_mark_unused_advances_auto_mode() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb.setCalibrationMode("auto")
    kb.startAutoCalibration()
    first = device_cell_from_linear_index(0)
    assert kb.calibrationPendingDeviceRow == first[0]
    kb.markCalibrationCellUnused()
    assert first in kb._calibration_unused_cells
    assert kb.calibrationPendingDeviceCol >= 0


def test_clear_calibration_cell_removes_override_and_unused() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb.setCalibrationOverride("esc", 5, 0)
    kb._calibration_unused_cells.add((5, 0))
    kb.clearCalibrationCell(0, 0)
    assert "esc" not in kb._calibration_overrides
    assert (5, 0) not in kb._calibration_unused_cells


def test_auto_skips_overridden_cells() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb.setCalibrationOverride("esc", *device_cell_from_linear_index(0))
    kb.setCalibrationMode("auto")
    kb.startAutoCalibration()
    assert (kb.calibrationPendingDeviceRow, kb.calibrationPendingDeviceCol) == (5, 1)


def test_auto_matrix_walks_row5_left_to_right() -> None:
    set_active_profile("abnt2_laptop_21")
    order = profile_calibration_matrix_cell_order()
    assert order.index((5, 12)) < order.index((5, 13)) < order.index((5, 14)) < order.index((5, 15))
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    for key_id in (
        "esc", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9",
        "f10", "f11", "f12",
    ):
        kb.setCalibrationOverride(key_id, *key_id_to_device_cell(key_id))
    kb.setCalibrationMode("auto")
    kb.startAutoCalibration()
    assert (kb.calibrationPendingDeviceRow, kb.calibrationPendingDeviceCol) == (5, 13)
    assert kb.calibrationPendingProfileKeyId == "prtsc"


def test_auto_advances_to_row5_col15_after_f_row_cluster() -> None:
    from avell_storm_rgb.domain.keyboard_layouts.loader import load_profile

    set_active_profile("abnt2_laptop_21")
    profile = load_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    for key_id in (
        "esc", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9",
        "f10", "f11", "f12", "prtsc", "scrlk",
    ):
        cell = profile.base_key_to_device_cell[key_id]
        kb.setCalibrationOverride(key_id, *cell)
    kb.setCalibrationMode("auto")
    kb.startAutoCalibration()
    assert (kb.calibrationPendingDeviceRow, kb.calibrationPendingDeviceCol) == (5, 15)
    assert kb.calibrationPendingProfileKeyId == ""


def test_auto_does_not_skip_wrong_assignee_on_arrow_left() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb.setCalibrationOverride("up", 0, 14)
    cells = profile_calibration_matrix_cell_order()
    kb._calibration_auto_cells = cells
    kb._calibration_auto_index = cells.index((0, 14))
    kb._calibration_auto_running = True
    kb._advance_auto_calibration()
    assert kb.calibrationPendingDeviceRow == 0
    assert kb.calibrationPendingDeviceCol == 14


def test_auto_clears_stale_unused_on_profile_key_at_start() -> None:
    from avell_storm_rgb.domain.keyboard_layouts.loader import load_profile

    set_active_profile("abnt2_laptop_21")
    profile = load_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb._device_mapping_key = "test-dev"
    delete_cell = profile.base_key_to_device_cell["delete"]
    kb._calibration_unused_cells.add(delete_cell)
    kb.setCalibrationMode("auto")
    kb.startAutoCalibration()
    assert delete_cell not in kb._calibration_unused_cells
    cells = profile_calibration_matrix_cell_order()
    kb._calibration_auto_cells = cells
    kb._calibration_auto_index = cells.index(delete_cell)
    kb._calibration_auto_running = True
    kb._advance_auto_calibration()
    assert (kb.calibrationPendingDeviceRow, kb.calibrationPendingDeviceCol) == delete_cell


def test_auto_purges_stale_unused_then_visits_backslash() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb._calibration_unused_cells.add((1, 2))
    kb.setCalibrationMode("auto")
    kb.startAutoCalibration()
    assert (1, 2) not in kb._calibration_unused_cells
    cells = profile_calibration_matrix_cell_order()
    kb._calibration_auto_cells = cells
    kb._calibration_auto_index = cells.index((1, 2))
    kb._calibration_auto_running = True
    kb._advance_auto_calibration()
    assert (kb.calibrationPendingDeviceRow, kb.calibrationPendingDeviceCol) == (1, 2)


def test_auto_pending_profile_key_id_matches_profile_hint() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb.setCalibrationMode("auto")
    kb.startAutoCalibration()
    assert kb.calibrationPendingProfileKeyId == "esc"


def test_auto_visits_empty_matrix_slots_in_grid_order() -> None:
    set_active_profile("abnt2_laptop_21")
    matrix_total = NUM_ROWS * NUM_COLS
    kb = KeyboardBackend(UsbWorker())
    kb._kb = object()
    kb.setCalibrationMode("auto")
    kb.startAutoCalibration()
    assert kb.calibrationAutoProgress.endswith(f"/ {matrix_total}")
    assert kb.calibrationPendingProfileKeyId == "esc"
    for key_id in (
        "esc", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9",
        "f10", "f11", "f12", "prtsc", "scrlk",
    ):
        kb.setCalibrationOverride(key_id, *key_id_to_device_cell(key_id))
    kb._advance_auto_calibration()
    assert (kb.calibrationPendingDeviceRow, kb.calibrationPendingDeviceCol) == (5, 15)


def test_set_override_clears_other_assignee_on_same_cell() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb.setCalibrationOverride("up", 0, 14)
    kb.setCalibrationOverride("left", 0, 14)
    assert kb._calibration_overrides == {"left": (0, 14)}


def test_calibration_cell_assignee_uses_visual_row() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb.setCalibrationOverride("esc", 5, 0)
    assert kb.calibrationCellAssignee(0, 0) == "esc"
    assert kb.calibrationCellAssignee(5, 0) == ""


def test_profile_hint_when_no_override() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    hint = kb.calibrationCellProfileHint(0, 0)
    assert hint == "esc"


def test_device_row_for_visual_row_matches_converter() -> None:
    set_active_profile("legacy_builtin")
    kb = KeyboardBackend(UsbWorker())
    for visual in range(6):
        assert kb.deviceRowForVisualRow(visual) == ui_row_to_device_row(visual)


def test_commit_abnt2_tilde_via_apostrophe_key() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb._kb = object()
    kb.selectCalibrationCell(3, 12)
    kb.commitCalibrationFromPhysicalKey(int(Qt.Key.Key_Apostrophe), 0, 0)
    assert kb._calibration_overrides["semicolon"] == visual_cell_to_device(3, 12)


def test_commit_abnt2_cedilla_via_semicolon_key() -> None:
    set_active_profile("abnt2_laptop_21")
    kb = KeyboardBackend(UsbWorker())
    kb._device_mapping_key = "test-dev"
    kb._kb = object()
    kb.selectCalibrationCell(3, 11)
    kb.commitCalibrationFromPhysicalKey(int(Qt.Key.Key_Semicolon), 0, 0)
    assert kb._calibration_overrides["cedilla"] == visual_cell_to_device(3, 11)
