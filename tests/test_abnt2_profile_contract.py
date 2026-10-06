import json
from pathlib import Path

import pytest

from avell_storm_rgb.domain.keyboard_layouts.loader import load_profile
from avell_storm_rgb.domain.keyboard_layouts.visual_geometry import VisualLayoutSpec
from avell_storm_rgb.domain.per_key_grid import set_active_profile

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "abnt2_laptop_21.expected.json"


def _abnt2():
    return load_profile("abnt2_laptop_21")


def test_abnt2_uses_visual_v2() -> None:
    profile = _abnt2()
    assert profile.visual_layout is not None
    assert profile.visual_layout.version == 2
    assert profile.layout_bounds_u is not None


def test_abnt2_no_spacers() -> None:
    profile = _abnt2()
    assert all(k["keyId"] != "_spacer" for k in profile.key_layout_keys)


def test_abnt2_no_backslash_on_p_row() -> None:
    profile = _abnt2()
    for key in profile.key_layout_keys:
        if key["keyId"] == "backslash":
            assert int(key["yU"]) == 4.0


def test_abnt2_has_cedilla() -> None:
    profile = _abnt2()
    assert "cedilla" in profile.base_key_to_device_cell
    assert profile.base_key_to_device_cell["cedilla"] == (2, 11)
    assert profile.base_key_to_device_cell["semicolon"] == (2, 12)


def test_abnt2_bracket_right_not_backslash_cell() -> None:
    profile = _abnt2()
    assert profile.base_key_to_device_cell["bracket_right"] == (3, 14)
    assert profile.base_key_to_device_cell["backslash"] == (1, 2)
    assert profile.base_key_to_device_cell["backslash"] != profile.base_key_to_device_cell["bracket_right"]


def test_abnt2_iso_enter_visual_parts() -> None:
    enter = next(k for k in _abnt2().key_layout_keys if k["keyId"] == "enter")
    assert enter.get("visualVersion") == 2
    assert enter.get("visualShape") == "isoEnter"
    assert "visualParts" in enter
    assert len(enter["visualParts"]) == 2


def test_abnt2_kp_enter_single_tall_key() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    nent = by_id["kp_enter_top"]
    assert nent["label"] == "NEnt"
    assert nent["hU"] == 2.0
    assert "app" not in by_id


def test_abnt2_app_hidden_but_mapped() -> None:
    profile = _abnt2()
    assert profile.base_key_to_device_cell["app"] == (0, 20)


def test_abnt2_bracket_square_left_of_enter() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    assert by_id["bracket_left"]["label"] == "´"
    assert by_id["bracket_square"]["label"] == "["
    assert by_id["bracket_square"]["secondaryLabel"] == "{ª"
    assert by_id["p"]["xU"] < by_id["bracket_left"]["xU"] < by_id["bracket_square"]["xU"]
    assert by_id["bracket_square"]["yU"] == by_id["bracket_left"]["yU"]
    assert _abnt2().base_key_to_device_cell["bracket_square"] == (3, 13)
    assert _abnt2().base_key_to_device_cell["bracket_left"] == (3, 12)
    enter = by_id["enter"]
    assert enter["xU"] > by_id["bracket_square"]["xU"]


def test_abnt2_qw_secondaries_and_shift_semicolon() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    assert by_id["q"]["secondaryLabel"] == "/"
    assert by_id["w"]["secondaryLabel"] == "?"
    assert by_id["e"]["secondaryLabel"] == "°"
    assert by_id["slash"]["label"] == ";"
    assert by_id["slash"]["yU"] == 4.0
    assert by_id["slash"]["xU"] != by_id["q"]["xU"]


def test_abnt2_numpad_island_right_of_main() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    main_right = max(
        by_id[k]["xU"] + by_id[k]["wU"]
        for k in ("right", "menu", "shift_right", "delete")
        if k in by_id
    )
    assert by_id["home"]["xU"] >= main_right
    assert by_id["num_lock"]["yU"] == 1.0
    assert by_id["kp_div"]["yU"] == 1.0
    assert by_id["kp_7"]["yU"] == 2.0


def test_abnt2_modifier_key_widths() -> None:
    """ABNT2 visual v2 uses fractional key widths in u."""
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    assert by_id["tab"]["wU"] == 1.5
    assert by_id["caps_lock"]["wU"] == 1.75
    assert by_id["shift_left"]["wU"] == 1.25
    assert by_id["space"]["wU"] == 6.0
    assert by_id["shift_right"]["wU"] > 2.75
    assert by_id["backspace"]["wU"] > 2.0


def test_abnt2_scrlk_between_f12_and_prtsc() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    assert "scrlk" in by_id
    assert by_id["scrlk"]["label"] == "SC"
    assert by_id["f12"]["xU"] < by_id["scrlk"]["xU"] < by_id["prtsc"]["xU"] < by_id["delete"]["xU"]
    assert _abnt2().base_key_to_device_cell["scrlk"] == (5, 14)


def test_abnt2_backspace_enter_shift_align_with_delete() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    del_right = by_id["delete"]["xU"] + by_id["delete"]["wU"]
    assert abs(by_id["backspace"]["xU"] + by_id["backspace"]["wU"] - del_right) < 0.01
    assert abs(by_id["shift_right"]["xU"] + by_id["shift_right"]["wU"] - del_right) < 0.01
    enter = next(k for k in _abnt2().key_layout_keys if k["keyId"] == "enter")
    top = enter["visualParts"][0]
    bot = enter["visualParts"][1]
    assert abs(top["xU"] + top["wU"] - del_right) < 0.01
    assert abs(bot["xU"] + bot["wU"] - del_right) < 0.01


def test_abnt2_no_insert_key() -> None:
    ids = {k["keyId"] for k in _abnt2().key_layout_keys}
    assert "insert" not in ids


def test_abnt2_arrow_cluster_inverted_t() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    assert by_id["up"]["yU"] == 5.0
    assert by_id["down"]["yU"] == 6.0
    assert by_id["down"]["xU"] == by_id["up"]["xU"]
    assert by_id["left"]["yU"] == 6.0
    assert by_id["right"]["yU"] == 6.0
    assert by_id["left"]["xU"] < by_id["down"]["xU"] < by_id["right"]["xU"]


def test_abnt2_arrow_cluster_centered_under_shift() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    shift = by_id["shift_right"]
    shift_center = shift["xU"] + shift["wU"] / 2
    cluster_center = (
        by_id["left"]["xU"] + by_id["right"]["xU"] + by_id["right"]["wU"]
    ) / 2
    assert abs(cluster_center - shift_center) < 0.05


def test_abnt2_numpad_standard_gap_from_main() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    main_right = max(
        by_id[k]["xU"] + by_id[k]["wU"]
        for k in ("shift_right", "delete", "right")
        if k in by_id
    )
    assert abs(by_id["home"]["xU"] - main_right - 0.15) < 0.02


def test_abnt2_kp_zero_same_row_as_space() -> None:
    by_id = {k["keyId"]: k for k in _abnt2().key_layout_keys}
    assert by_id["space"]["yU"] == 5.0
    assert by_id["kp_0"]["yU"] == 5.0
    assert by_id["kp_dot"]["yU"] == 5.0


def test_abnt2_trio_distinct_device_cells() -> None:
    profile = _abnt2()
    cells = {
        profile.base_key_to_device_cell["l"],
        profile.base_key_to_device_cell["enter"],
        profile.base_key_to_device_cell["backslash"],
    }
    assert len(cells) == 3


@pytest.mark.parametrize(
    ("key_id", "device_cell"),
    [
        pytest.param(
            "l",
            (2, 10),
            id="l",
        ),
        pytest.param(
            "enter",
            (2, 13),
            id="enter",
        ),
        pytest.param(
            "backslash",
            (1, 2),
            id="backslash",
        ),
    ],
)
def test_abnt2_golden_device_cells(key_id: str, device_cell: tuple[int, int]) -> None:
    if not _FIXTURE.is_file():
        pytest.skip("golden fixture not filled from hardware session")
    golden = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    expected = tuple(golden[key_id])
    profile = _abnt2()
    assert profile.base_key_to_device_cell[key_id] == expected
    assert profile.base_key_to_device_cell[key_id] == device_cell


def test_active_profile_abnt2_apply() -> None:
    set_active_profile("abnt2_laptop_21")
    from avell_storm_rgb.domain import per_key_grid as pkg

    assert pkg.active_profile_id() == "abnt2_laptop_21"
    assert pkg.key_id_to_device_cell("backslash") == (1, 2)
    assert pkg.key_id_to_ui_cell("backslash") == (4, 2)
    backslash = next(k for k in pkg.KEY_LAYOUT_KEYS if k["keyId"] == "backslash")
    assert backslash["wU"] == 1.0
    set_active_profile("legacy_builtin")
