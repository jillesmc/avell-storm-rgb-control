import pytest

from avell_storm_rgb.domain.per_key_grid import (
    KEY_LAYOUT_KEYS,
    color_map_ui_to_device,
    key_id_to_ui_cell,
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
