"""``legacy_builtin`` must match the original hard-coded ``per_key_grid`` maps."""

import json
from pathlib import Path

from avell_storm_rgb.domain.keyboard_layouts.loader import load_profile

_GOLDEN_PATH = Path(__file__).resolve().parent / "fixtures" / "legacy_builtin_device_cells.json"


def test_legacy_builtin_matches_golden_device_cells() -> None:
    golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    profile = load_profile("legacy_builtin")
    for key_id, cell in golden.items():
        assert profile.base_key_to_device_cell[key_id] == tuple(cell)


def test_legacy_backslash_ansi_position() -> None:
    profile = load_profile("legacy_builtin")
    assert profile.base_key_to_device_cell["backslash"] == (3, 14)
