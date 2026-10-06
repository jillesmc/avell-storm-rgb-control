"""CLI `state show` / `state restore` (UT-070–UT-080, E2E-001–E2E-003). Expected output comes from _dx.md."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from avell_storm_rgb.adapters.cli import main as cli
from avell_storm_rgb.application.device_state import (
    AnimationLook,
    DeviceState,
    DeviceStateStore,
    KeyboardState,
    LedBarLook,
    LedBarState,
    SolidLook,
    default_state_path,
)
from backend_fakes import FakeKeyboard, FakeLedBar

DX = (Path(__file__).resolve().parents[1] / ".compozy/tasks/remembered-devices/_dx.md").read_text()
DX_PATH = "/home/jilles/.config/avell-storm-rgb/state.json"


def _dx_console(after: str) -> list[str]:
    """Output lines printed after the console line ``$ <after>`` in the _dx.md golden path."""
    block = DX.split("$ " + after + "\n", 1)[1]
    out = []
    for line in block.splitlines():
        if line.startswith("$") or line.startswith("#") or line == "" or line.startswith("```"):
            break
        out.append(line)
    return out


def _dx_example_state() -> str:
    return re.search(r"## State file.*?```json\n(.*?)```", DX, re.S).group(1)


@pytest.fixture
def fakes(monkeypatch):
    world = {"kb": FakeKeyboard(), "led": FakeLedBar(), "journal": [], "kb_error": None, "led_error": None}
    world["kb"].journal = world["journal"]
    world["led"].journal = world["journal"]

    def open_kb(**kw):
        world.setdefault("kb_opened", []).append(kw)
        if world["kb_error"]:
            raise world["kb_error"]
        return world["kb"]

    def open_led(**kw):
        world.setdefault("led_opened", []).append(kw)
        if world["led_error"]:
            raise world["led_error"]
        return world["led"]

    monkeypatch.setattr(cli, "open_keyboard", open_kb)
    monkeypatch.setattr(cli, "open_led_bar", open_led)
    return world


def _write_example() -> Path:
    path = default_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dx_example_state())
    return path


def _save(state: DeviceState) -> Path:
    store = DeviceStateStore(default_state_path())
    store.save(state)
    return store.path


def _run(capsys, *argv) -> tuple[int, str, str]:
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


# --- show (UT-070–UT-072) ----------------------------------------------------------


def test_ut070_show_matches_golden_path(capsys) -> None:
    path = _write_example()
    code, out, _ = _run(capsys, "state", "show")
    expected = [line.replace(DX_PATH, str(path)) for line in _dx_console("avell-storm-rgb state show")]
    assert out.splitlines() == expected
    assert code == 0


def test_ut071_show_without_file(capsys) -> None:
    path = default_state_path()
    code, out, _ = _run(capsys, "state", "show")
    assert (code, out.strip()) == (0, f"No saved state at {path}")
    code, out, _ = _run(capsys, "state", "show", "--json")
    assert json.loads(out) == {"path": str(path), "version": 1, "devices": {}}


def test_ut072_show_invalid_file(capsys) -> None:
    path = default_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{")
    code, _, err = _run(capsys, "state", "show")
    assert code == 3
    assert err.strip() == f"error: saved state is unreadable (invalid JSON at line 1 column 2): {path}"
    assert path.read_text() == "{"


# --- restore (UT-073–UT-080) ---------------------------------------------------------


def test_ut073_restore_order_and_file_untouched(capsys, fakes) -> None:
    path = _write_example()
    before = path.read_bytes()
    code, _, _ = _run(capsys, "state", "restore")
    devices = [d for d, _ in fakes["journal"]]
    assert devices.index("FakeKeyboard") > max(i for i, d in enumerate(devices) if d == "FakeLedBar")
    assert code == 0
    assert path.read_bytes() == before


def test_ut074_kind_filter(capsys, fakes) -> None:
    _write_example()
    _run(capsys, "state", "restore", "--kind", "keyboard")
    assert "led_opened" not in fakes
    assert fakes["kb_opened"] == [{"usb_id": "048d:ce00"}]


def test_ut075_no_animation_skips_forever_animation(capsys, fakes, tmp_path) -> None:
    script = tmp_path / "anim"
    script.write_text("apply\n")
    _save(DeviceState(keyboard=KeyboardState("048d:ce00", brightness=40, palette={1: (1, 1, 1)},
                                             look=AnimationLook(str(script), 1, True))))
    code, out, _ = _run(capsys, "state", "restore", "--no-animation")
    assert out.strip() == "keyboard  048d:ce00  restored: palette, brightness (animation skipped)"
    assert "set_key_colors" not in fakes["kb"].names()
    assert code == 0


def test_ut076_missing_device_is_skipped_others_restored(capsys, fakes) -> None:
    _write_example()
    fakes["led_error"] = RuntimeError("No ITE 8233 LED bar found.")
    code, out, _ = _run(capsys, "state", "restore")
    lines = out.splitlines()
    assert lines[0] == "led-bar   048d:7001  skipped: device not found"
    assert lines[1].startswith("keyboard  048d:ce00  restored:")
    assert code == 1


def test_ut077_forgotten_device_is_silent(capsys, fakes) -> None:
    _save(DeviceState(led_bar=LedBarState("048d:7001", remembered=False, look=LedBarLook(((1, 2, 3),), "static", 50, 3))))
    code, out, _ = _run(capsys, "state", "restore")
    assert (code, out) == (0, "")
    assert "led_opened" not in fakes


def test_ut078_restore_without_file(capsys, fakes) -> None:
    code, out, _ = _run(capsys, "state", "restore")
    assert (code, out.strip()) == (0, f"Nothing to restore: no saved state at {default_state_path()}")


def test_ut079_restore_invalid_file(capsys, fakes) -> None:
    path = default_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json")
    code, _, _ = _run(capsys, "state", "restore")
    assert code == 3
    assert "kb_opened" not in fakes and "led_opened" not in fakes


def test_ut080_missing_animation_warns(capsys, fakes, tmp_path) -> None:
    missing = str(tmp_path / "gone")
    _save(DeviceState(keyboard=KeyboardState("048d:ce00", look=AnimationLook(missing, 1, True))))
    code, out, _ = _run(capsys, "state", "restore")
    assert out.strip() == (
        f"keyboard  048d:ce00  restored: light on (warning: animation file not found: {missing})"
    )
    assert code == 1


def test_restore_light_off_and_solid(capsys, fakes) -> None:
    _save(DeviceState(
        keyboard=KeyboardState("048d:ce00", power="off", look=SolidLook((255, 255, 255))),
        led_bar=LedBarState("048d:7001", look=LedBarLook(((136, 0, 255),), "static", 50, 3)),
    ))
    code, out, _ = _run(capsys, "state", "restore")
    assert out.splitlines() == [
        "led-bar   048d:7001  restored: static · 1 colour · brightness 50 · speed 3",
        "keyboard  048d:ce00  restored: light off",
    ]
    assert fakes["kb"].names() == ["turn_off"]


def test_restore_json(capsys, fakes) -> None:
    _write_example()
    fakes["led_error"] = RuntimeError("No ITE 8233 LED bar found.")
    code, out, _ = _run(capsys, "state", "restore", "--no-animation", "--json")
    doc = json.loads(out)
    assert doc["results"][0] == {"kind": "led_bar", "usb_id": "048d:7001", "status": "skipped", "reason": "device not found"}
    assert doc["results"][1] == {
        "kind": "keyboard", "usb_id": "048d:ce00", "status": "restored",
        "applied": ["palette 1,3", "brightness 40", "firmware effect wave"], "warnings": [],
    }
    assert code == 1


# --- E2E (E2E-001–E2E-003) -----------------------------------------------------------


def test_e2e001_show_transcript_and_json(capsys) -> None:
    path = _write_example()
    _, out, _ = _run(capsys, "state", "show")
    assert out.splitlines() == [l.replace(DX_PATH, str(path)) for l in _dx_console("avell-storm-rgb state show")]
    _, out, _ = _run(capsys, "state", "show", "--json")
    doc = json.loads(out)
    assert doc.pop("path") == str(path)
    assert doc == json.loads(_dx_example_state())


def test_e2e002_restore_transcript(capsys, fakes) -> None:
    path = _write_example()
    before = path.read_bytes()
    code, out, _ = _run(capsys, "state", "restore")
    assert out.splitlines() == _dx_console("avell-storm-rgb state restore")
    assert code == 0
    assert path.read_bytes() == before


def test_e2e003_restore_failure_journeys(capsys, fakes) -> None:
    code, out, _ = _run(capsys, "state", "restore")
    assert code == 0 and out.startswith("Nothing to restore")

    path = default_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]")
    code, _, err = _run(capsys, "state", "restore")
    assert code == 3 and err.startswith("error: saved state is unreadable")

    _write_example()
    fakes["led_error"] = RuntimeError("No ITE 8233 LED bar found.")
    code, out, _ = _run(capsys, "state", "restore")
    assert code == 1 and "skipped: device not found" in out
