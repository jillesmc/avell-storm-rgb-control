import json
from pathlib import Path

import pytest

from avell_storm_rgb.domain.keyboard_layouts.loader import (
    list_profile_ids,
    load_profile,
    load_profile_document,
    profile_path,
    resolve_usb_default_profile,
)
from avell_storm_rgb.domain.keyboard_layouts.schema import SPACER_KEY_ID, validate_profile_document
from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS


def test_list_profile_ids_includes_builtin() -> None:
    ids = list_profile_ids()
    assert "legacy_builtin" in ids
    assert "abnt2_laptop_21" in ids


def test_profile_path_resolves_to_file() -> None:
    p = profile_path("legacy_builtin")
    assert p.is_file()


def test_load_legacy_builtin_row_count() -> None:
    profile = load_profile("legacy_builtin")
    rows = {int(k["row"]) for k in profile.key_layout_keys if k.get("keyId") != SPACER_KEY_ID}
    assert rows == {0, 1, 2, 3, 4, 5}


def test_spacer_has_no_device_cell_in_document() -> None:
    doc = json.loads(profile_path("legacy_builtin").read_text(encoding="utf-8"))
    for row in doc["keys"]:
        for entry in row:
            if entry["keyId"] == SPACER_KEY_ID:
                assert "deviceCell" not in entry


def test_abnt2_visual_v2_row_count() -> None:
    doc = json.loads(profile_path("abnt2_laptop_21").read_text(encoding="utf-8"))
    assert doc["visualLayout"]["version"] == 2
    assert len(doc["keys"]) == 7


def test_device_cell_not_inferred_from_visual_x() -> None:
    """Explicit deviceCell can differ from visual.x (wide keys / ABNT2)."""
    profile = load_profile("legacy_builtin")
    tab = next(k for k in profile.key_layout_keys if k["keyId"] == "tab")
    assert int(tab["x"]) == 0
    assert profile.base_key_to_device_cell["tab"] == (3, 1)


def test_invalid_profile_raises() -> None:
    with pytest.raises(ValueError):
        validate_profile_document({"profileId": "x", "keys": []})


def test_duplicate_key_id_in_profile_raises() -> None:
    doc = {
        "profileId": "bad",
        "keys": [[{
            "keyId": "a",
            "label": "A",
            "secondaryLabel": "",
            "visual": {"row": 0, "x": 0, "w": 21, "h": 1},
            "deviceCell": {"row": 5, "col": 0},
        }]] * NUM_ROWS,
    }
    doc["keys"][1][0]["keyId"] = "a"
    with pytest.raises(ValueError, match="duplicate"):
        validate_profile_document(doc)


def test_usb_defaults_abnt2_for_avell_products() -> None:
    assert resolve_usb_default_profile(0x6006) == "abnt2_laptop_21"
    assert resolve_usb_default_profile(0x9999) == "legacy_builtin"


def test_visual_parts_loaded() -> None:
    doc = json.loads(Path("tests/fixtures/profile_enter_visual_parts.json").read_text(encoding="utf-8"))
    profile = load_profile_document(doc)
    enter = next(k for k in profile.key_layout_keys if k["keyId"] == "enter")
    assert "visualParts" in enter
    assert len(enter["visualParts"]) == 2
