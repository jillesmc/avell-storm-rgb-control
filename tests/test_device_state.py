"""Saved device state: store, validation, quarantine, restore (UT-001–UT-017)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from avell_storm_rgb.application import device_state as ds
from avell_storm_rgb.application.device_state import (
    AnimationLook,
    BulbState,
    DeviceState,
    DeviceStateStore,
    FirmwareEffectLook,
    KeyboardState,
    LedBarLook,
    LedBarState,
    PerKeyLook,
    SolidLook,
    StateFileError,
    describe_look,
    restore_keyboard,
    restore_led_bar,
)
from avell_storm_rgb.infrastructure.usb.ite8291_usb import KEYBOARD_EFFECTS

WAVE = FirmwareEffectLook("wave", 5, 40, "random", "up", False, False)
STATIC_RED = LedBarLook(((255, 0, 0),), "static", 50, 3)


def _doc(**keyboard_look) -> dict:
    look = {"mode": "firmware_effect", "effect": "wave", "speed": 5, "brightness": 40,
            "color": "random", "direction": "up", "reactive": False, "save": False}
    look.update(keyboard_look)
    return {"version": 1, "devices": {"keyboard": {
        "usb_id": "048d:ce00", "remembered": True, "power": "on",
        "brightness": None, "palette": {}, "look": look}}}


def _write(path: Path, doc) -> None:
    path.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")


# --- store (UT-001–UT-009) ---------------------------------------------------


def test_ut001_round_trip(tmp_path: Path) -> None:
    store = DeviceStateStore(tmp_path / "state.json")
    state = DeviceState(
        keyboard=KeyboardState("048d:ce00", brightness=40, palette={1: (255, 0, 0)}, look=WAVE),
        led_bar=LedBarState("048d:7001", power="off", look=STATIC_RED),
    )
    store.save(state)
    assert store.load() == state


def test_ut002_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    _write(p, "{")
    with pytest.raises(StateFileError) as e:
        DeviceStateStore(p).load()
    assert e.value.reason.startswith("invalid JSON")
    assert e.value.reason == "invalid JSON at line 1 column 2"


def test_ut003_unsupported_version(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    _write(p, {"version": 2, "devices": {}})
    with pytest.raises(StateFileError) as e:
        DeviceStateStore(p).load()
    assert e.value.reason == "unsupported version 2"


def test_ut004_speed_boundary(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    _write(p, _doc(speed=11))
    with pytest.raises(StateFileError) as e:
        DeviceStateStore(p).load()
    assert "keyboard.look.speed must be 0–10, got 11" in e.value.reason
    _write(p, _doc(speed=10))
    assert DeviceStateStore(p).load().keyboard.look.speed == 10


def test_ut005_quarantine_replaces_old_backup(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    _write(p, "broken")
    (tmp_path / "state.json.invalid").write_text("older")
    store = DeviceStateStore(p)
    target = store.quarantine()
    assert target == tmp_path / "state.json.invalid"
    assert target.read_text() == "broken"
    assert not store.exists()


def test_ut006_save_to_readonly_dir_keeps_previous(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    p = tmp_path / "state.json"
    store = DeviceStateStore(p)
    store.save(DeviceState(led_bar=LedBarState("048d:7001")))
    before = p.read_bytes()
    tmp_path.chmod(0o500)
    try:
        with pytest.raises(OSError):
            store.save(DeviceState())
    finally:
        tmp_path.chmod(0o700)
    assert p.read_bytes() == before


def test_ut007_atomic_replace_failure_leaves_no_temp(tmp_path: Path, monkeypatch) -> None:
    p = tmp_path / "state.json"
    store = DeviceStateStore(p)
    store.save(DeviceState(led_bar=LedBarState("048d:7001")))
    before = p.read_bytes()

    def boom(src, dst):
        raise OSError("replace failed")

    monkeypatch.setattr(ds.os, "replace", boom)
    with pytest.raises(OSError):
        store.save(DeviceState())
    assert p.read_bytes() == before
    assert sorted(x.name for x in tmp_path.iterdir()) == ["state.json"]


def test_ut008_module_is_qt_free() -> None:
    code = (
        "import sys; sys.modules['PySide6'] = None\n"
        "import avell_storm_rgb.application.device_state\n"
        "print('ok')"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "ok"


def test_ut009_missing_file_is_empty_state(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    assert DeviceStateStore(p).load() == DeviceState(keyboard=None, led_bar=None)
    assert not p.exists()


def test_save_uses_private_permissions(tmp_path: Path) -> None:
    p = tmp_path / "cfg" / "avell-storm-rgb" / "state.json"
    DeviceStateStore(p).save(DeviceState())
    assert p.stat().st_mode & 0o777 == 0o600
    assert p.parent.stat().st_mode & 0o777 == 0o700


def test_default_path_follows_xdg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert ds.default_state_path() == tmp_path / "avell-storm-rgb" / "state.json"
    monkeypatch.setenv("XDG_CONFIG_HOME", "relative/ignored")
    assert ds.default_state_path() == Path.home() / ".config" / "avell-storm-rgb" / "state.json"


# --- bulbs (UT-034, UT-038, UT-039) ------------------------------------------

BULB_ID = "eb1a2b3c4d5e6f70819202"


def test_ut034_bulbs_round_trip(tmp_path: Path) -> None:
    store = DeviceStateStore(tmp_path / "state.json")
    state = DeviceState(bulbs=(BulbState(BULB_ID, True, "keyboard"),))
    store.save(state)
    assert store.load() == state
    doc = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert doc["devices"]["bulbs"] == {BULB_ID: {"remembered": True, "follow": "keyboard"}}


def test_ut034_bulbs_are_sorted_by_id() -> None:
    state = DeviceState(bulbs=(BulbState("b"), BulbState("a")))
    assert [bulb.id for bulb in state.bulbs] == ["a", "b"]
    assert list(ds.state_to_dict(state)["devices"]["bulbs"]) == ["a", "b"]


def test_ut038_invalid_follow_raises_exact_value_error() -> None:
    doc = {"version": 1, "devices": {"bulbs": {BULB_ID: {"remembered": True, "follow": "music"}}}}
    with pytest.raises(ValueError) as e:
        ds.state_from_dict(doc)
    assert str(e.value) == (
        f"bulbs.{BULB_ID}.follow must be one of none, keyboard, screen, led_bar, got 'music'"
    )


def test_ut038_store_reports_the_field_path(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    _write(p, {"version": 1, "devices": {"bulbs": {BULB_ID: {"remembered": True, "follow": "music"}}}})
    with pytest.raises(StateFileError) as e:
        DeviceStateStore(p).load()
    assert e.value.reason == (
        f"bulbs.{BULB_ID}.follow must be one of none, keyboard, screen, led_bar, got 'music'"
    )


def test_ut039_file_without_bulbs_loads_empty_and_rewrites_without_key(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    _write(p, {"version": 1, "devices": {}})
    store = DeviceStateStore(p)
    state = store.load()
    assert state.bulbs == ()
    store.save(state)
    assert "bulbs" not in json.loads(p.read_text(encoding="utf-8"))["devices"]


def test_ut039_current_release_file_keeps_no_bulbs_key(tmp_path: Path) -> None:
    p = tmp_path / "state.json"
    _write(p, _doc())
    store = DeviceStateStore(p)
    store.save(store.load())
    assert "bulbs" not in json.loads(p.read_text(encoding="utf-8"))["devices"]


# --- restore (UT-010–UT-017) ---------------------------------------------------


class FakeKeyboard:
    def __init__(self) -> None:
        self.calls: list = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, *args) if not kwargs else (name, *args, kwargs))
        return record


class FakeLedBar(FakeKeyboard):
    pass


def test_ut010_firmware_effect_order_and_filtered_kwargs() -> None:
    kb = FakeKeyboard()
    look = FirmwareEffectLook("wave", 5, 40, "random", "up", False, True)
    plan = restore_keyboard(kb, KeyboardState("048d:ce00", brightness=40, palette={1: (255, 0, 0)}, look=look))
    assert kb.calls == [
        ("set_palette_color", 1, (255, 0, 0)),
        ("set_brightness", 40),
        ("set_effect", KEYBOARD_EFFECTS["wave"](speed=5, brightness=40, direction=3, save=1)),
    ]
    assert plan.applied == ("palette 1", "brightness 40", "firmware effect wave")


def test_ut011_solid() -> None:
    kb = FakeKeyboard()
    restore_keyboard(kb, KeyboardState("048d:ce00", look=SolidLook((255, 255, 255))))
    assert kb.calls == [("set_color", (255, 255, 255), None, False)]


def test_ut012_per_key_uses_device_coordinates() -> None:
    kb = FakeKeyboard()
    restore_keyboard(kb, KeyboardState("048d:ce00", look=PerKeyLook(((5, 0, (255, 0, 0)),))))
    assert kb.calls == [("set_key_colors", {(5, 0): (255, 0, 0)})]


def test_ut013_power_off_skips_look() -> None:
    kb = FakeKeyboard()
    plan = restore_keyboard(
        kb, KeyboardState("048d:ce00", power="off", brightness=10, palette={2: (1, 2, 3)}, look=WAVE)
    )
    assert kb.calls == [("set_palette_color", 2, (1, 2, 3)), ("set_brightness", 10), ("turn_off",)]
    assert plan.pending_animation is None
    assert plan.applied[-1] == "light off"


def test_ut014_animation_is_returned_not_run(tmp_path: Path) -> None:
    script = tmp_path / "anim"
    script.write_text("apply\n")
    look = AnimationLook(str(script), 1, True)
    kb = FakeKeyboard()
    plan = restore_keyboard(kb, KeyboardState("048d:ce00", look=look))
    assert plan.pending_animation == look
    assert kb.calls == []


def test_ut015_missing_animation_warns_and_keeps_power(tmp_path: Path) -> None:
    missing = str(tmp_path / "gone")
    kb = FakeKeyboard()
    plan = restore_keyboard(kb, KeyboardState("048d:ce00", brightness=30, look=AnimationLook(missing, 1, True)))
    assert plan.pending_animation is None
    assert plan.warnings == (f"animation file not found: {missing}",)
    assert kb.calls == [("set_brightness", 30)]


def test_ut016_led_bar_restore_and_power_off() -> None:
    bar = FakeLedBar()
    look = LedBarLook(((255, 0, 0), (0, 0, 255)), "wave", 75, 5)
    restore_led_bar(bar, LedBarState("048d:7001", look=look))
    assert bar.calls == [
        ("set_palette_colors", [(255, 0, 0), (0, 0, 255)]),
        ("set_brightness_level", 75),
        ("set_motion_speed", 5),
        ("apply_visual_effect", "wave"),
    ]
    bar = FakeLedBar()
    restore_led_bar(bar, LedBarState("048d:7001", power="off", look=look))
    assert bar.calls == [("power_off",)]


def test_ut017_describe_look() -> None:
    assert describe_look(WAVE) == "firmware effect wave (speed 5, brightness 40, direction up)"
    four = LedBarLook(((1, 1, 1),) * 4, "breathing", 75, 3)
    assert describe_look(four) == "breathing · 4 colours · brightness 75 · speed 3"
    assert describe_look(STATIC_RED) == "static · 1 colour · brightness 50 · speed 3"
    assert describe_look(SolidLook((255, 255, 255))) == "solid #ffffff"
    assert describe_look(AnimationLook("/a/b", 1, True)) == "animation /a/b (forever)"
    assert describe_look(AnimationLook("/a/b", 3, False)) == "animation /a/b (3 loops)"
    assert describe_look(None) == "no look"
