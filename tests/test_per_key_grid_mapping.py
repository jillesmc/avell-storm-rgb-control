import pytest

from avell_storm_rgb.domain.per_key_grid import (
    BASE_KEY_TO_DEVICE_CELL,
    KEY_LAYOUT_KEYS,
    color_map_ui_to_device,
    find_device_cell_conflicts,
    key_id_to_device_cell,
    key_id_to_ui_cell,
    resolve_key_to_device_cell,
    set_active_profile,
    ui_row_to_device_row,
)


def test_ui_row_to_device_row_inverts_for_six_rows() -> None:
    assert ui_row_to_device_row(0) == 5
    assert ui_row_to_device_row(5) == 0
    assert ui_row_to_device_row(3) == 2


def test_ui_row_to_device_row_bounds() -> None:
    with pytest.raises(ValueError):
        ui_row_to_device_row(-1)
    with pytest.raises(ValueError):
        ui_row_to_device_row(6)


def test_color_map_ui_to_device_flips_rows_only() -> None:
    ui = {(0, 0): (1, 2, 3), (5, 20): (4, 5, 6)}
    dev = color_map_ui_to_device(ui)
    assert dev == {(5, 0): (1, 2, 3), (0, 20): (4, 5, 6)}


def test_key_layout_keys_cover_keyboard_rows() -> None:
    rows = {int(k["row"]) for k in KEY_LAYOUT_KEYS}
    assert rows == {0, 1, 2, 3, 4, 5}


def test_key_id_to_ui_cell_known_keys() -> None:
    assert key_id_to_ui_cell("esc") == (0, 0)
    assert key_id_to_ui_cell("space")[0] == 5


def test_key_id_to_ui_cell_unknown_raises() -> None:
    with pytest.raises(ValueError):
        key_id_to_ui_cell("does_not_exist")


def test_key_layout_has_secondary_label_field() -> None:
    assert all("secondaryLabel" in k for k in KEY_LAYOUT_KEYS)


def test_key_id_to_device_cell_uses_base_map() -> None:
    assert key_id_to_device_cell("esc") == BASE_KEY_TO_DEVICE_CELL["esc"]


def test_resolve_key_to_device_cell_override_wins() -> None:
    assert resolve_key_to_device_cell("esc", {"esc": (0, 20)}) == (0, 20)


def test_find_device_cell_conflicts_detects_overlap() -> None:
    conflicts = find_device_cell_conflicts({"esc": (0, 0), "f1": (0, 0)})
    assert (0, 0) in conflicts
    assert {"esc", "f1"}.issubset(set(conflicts[(0, 0)]))


def test_find_device_cell_conflicts_profile_duplicates_without_overrides() -> None:
    set_active_profile("abnt2_laptop_21")
    conflicts = find_device_cell_conflicts({})
    assert (3, 12) not in conflicts
    assert (3, 14) not in conflicts


def test_find_device_cell_conflicts_clears_when_duplicate_key_moved() -> None:
    set_active_profile("abnt2_laptop_21")
    conflicts = find_device_cell_conflicts({"quote": (2, 12)})
    assert (1, 12) not in conflicts
    assert "quote" not in conflicts.get((1, 12), [])
