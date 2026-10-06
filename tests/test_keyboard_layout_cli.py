from io import StringIO
from unittest.mock import MagicMock

from avell_storm_rgb.application.keyboard_layout_cli import (
    cmd_layout_list,
    cmd_layout_probe,
    cmd_layout_set,
)


def test_cmd_layout_list_includes_profiles() -> None:
    buf = StringIO()
    import sys

    old = sys.stdout
    sys.stdout = buf
    try:
        assert cmd_layout_list() == 0
    finally:
        sys.stdout = old
    text = buf.getvalue()
    assert "legacy_builtin" in text
    assert "abnt2_laptop_21" in text


def test_cmd_layout_set() -> None:
    assert cmd_layout_set("legacy_builtin") == 0


def test_cmd_layout_probe_stdout_json_all_skip() -> None:
    import json

    from avell_storm_rgb.infrastructure.usb.ite8291_usb import NUM_COLS, NUM_ROWS

    device = MagicMock()
    inp = StringIO("\n" * (NUM_ROWS * NUM_COLS))
    out = StringIO()
    assert (
        cmd_layout_probe(device, input_stream=inp, output_stream=out, prompt_stream=StringIO())
        == 0
    )
    payload = json.loads(out.getvalue())
    assert payload == {}
    assert device.set_key_colors.call_count >= 1
