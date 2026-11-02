"""Follow through AppFacade: sources, lifecycle stops, one driver (UT-080, UT-087–UT-089, UT-097, UT-098, IT-010, IT-012, IT-013, IT-015)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QUrl

from avell_storm_rgb.application.bulb_facade import BulbUnreachable
from avell_storm_rgb.application.device_state import BulbState, DeviceState
from backend_fakes import FakeBulb, drain, drain_bulbs
from facade_harness import KB_ROW, LED_ROW, rig  # noqa: F401

FIXTURE = Path(__file__).parent / "fixtures" / "tinytuya_devices.json"
ESC = "eb1a2b3c4d5e6f70819202"


@pytest.fixture
def world(rig, monkeypatch):
    monkeypatch.setattr("app.ui.adapters.app_facade.tuya_available", lambda: True)
    FakeBulb.live_connections = 0
    w = {"opened": [], "journal": [], "fail_push": False}

    def open_bulb(record, inventory):
        bulb = FakeBulb(journal=w["journal"], reject_second_connection=True)
        if w["fail_push"]:
            bulb.fail_on = frozenset({"push_colour"})
        w["opened"].append(bulb)
        return bulb

    monkeypatch.setattr("avell_storm_rgb.application.bulb_facade.open_bulb", open_bulb)
    rig.rows = [KB_ROW, LED_ROW]
    return w


def _settle(f) -> None:
    for _ in range(3):
        drain(f._worker)
        drain_bulbs(f.bulbs._worker)


def _tick(f, bulb_id=ESC) -> None:
    f.bulbs._follower._tick(bulb_id)
    _settle(f)


def _start_following(rig, f, source: str) -> None:
    f.refreshDevices()
    f.connectDevice("keyboard", 3, 9)
    f.connectDevice("led_bar", 1, 4)
    f.bulbs.importFile(QUrl.fromLocalFile(str(FIXTURE)))
    f.bulbs.connectBulb(ESC)
    _settle(f)
    f.bulbs.setFollow(ESC, source)
    _settle(f)


def _pushes(world) -> list:
    return [c[1] for b in world["opened"] for c in b.calls if c[0] == "push_colour"]


def test_it010_keyboard_solid_colour_reaches_bulb(rig, world) -> None:
    f = rig.facade()
    _start_following(rig, f, "keyboard")
    assert json.loads(rig.state_path.read_text())["devices"]["bulbs"][ESC]["follow"] == "keyboard"
    f.keyboard.setSolidRgb(0, 0, 255)
    _settle(f)
    _tick(f)
    assert _pushes(world) == [(0, 0, 255)]


def test_ut088_it012_led_bar_average_once(rig, world) -> None:
    f = rig.facade()
    _start_following(rig, f, "led_bar")
    f.ledBar.applyPalette("red,blue", "static")
    _settle(f)
    _tick(f)
    _tick(f)
    assert _pushes(world) == [(128, 0, 128)]


def test_ut089_led_bar_off_sends_nothing(rig, world) -> None:
    f = rig.facade()
    _start_following(rig, f, "led_bar")
    f.ledBar.setLightOn(False)
    _settle(f)
    _tick(f)
    assert _pushes(world) == []


def test_ut087_sources_follow_runtime(rig, world) -> None:
    f = rig.facade()
    f.keyboard.followScreenAvailable = False  # no screen extra
    f.bulbs.importFile(QUrl.fromLocalFile(str(FIXTURE)))
    assert f.bulbs.availableFollowSources(ESC) == []
    f.refreshDevices()
    f.connectDevice("keyboard", 3, 9)
    _settle(f)
    assert f.bulbs.availableFollowSources(ESC) == ["keyboard"]
    f.connectDevice("led_bar", 1, 4)
    _settle(f)
    assert f.bulbs.availableFollowSources(ESC) == ["keyboard", "led_bar"]
    f.keyboard.followScreenAvailable = True  # screen extra present
    assert f.bulbs.availableFollowSources(ESC) == ["keyboard", "screen", "led_bar"]


def test_it015_one_driver_for_commands_and_pushes(rig, world) -> None:
    f = rig.facade()
    _start_following(rig, f, "keyboard")
    held = world["opened"][-1]
    f.bulbs.setLightOn(ESC, True)
    f.keyboard.setSolidRgb(10, 20, 30)
    _settle(f)
    _tick(f)
    assert ("set_power", True) in held.calls
    assert ("push_colour", (10, 20, 30)) in held.calls
    assert world["opened"].index(held) == len(world["opened"]) - 1  # no driver opened after it


def test_ut097_disconnect_keeps_choice_connect_resumes(rig, world) -> None:
    f = rig.facade()
    _start_following(rig, f, "keyboard")
    held = world["opened"][-1]
    f.bulbs.disconnectBulb(ESC)
    _settle(f)
    assert held.closed and f.bulbs._follower.source_of(ESC) == "none"
    assert json.loads(rig.state_path.read_text())["devices"]["bulbs"][ESC]["follow"] == "keyboard"
    f.bulbs.connectBulb(ESC)
    _settle(f)
    assert f.bulbs._follower.source_of(ESC) == "keyboard"


def test_ut098_unreachable_push_marks_unavailable(rig, world) -> None:
    f = rig.facade()
    _start_following(rig, f, "keyboard")
    held = world["opened"][-1]
    held.fail_on = frozenset({"push_colour"})
    held.unreachable = False
    f.keyboard.setSolidRgb(0, 0, 255)
    _settle(f)
    _tick(f)
    assert f.bulbs.bulb(ESC)["unavailableReason"] != ""
    assert ("hold_open", False) in held.calls and held.closed
    assert f.bulbs._follower.source_of(ESC) == "none"
    before = len(world["opened"])
    f.keyboard.setSolidRgb(255, 0, 0)
    _settle(f)
    _tick(f)
    assert len(world["opened"]) == before  # no more pushes until Retry


def test_ut080_remove_stops_and_closes_before_inventory_write(rig, world, monkeypatch) -> None:
    f = rig.facade()
    _start_following(rig, f, "keyboard")
    held = world["opened"][-1]
    order: list[str] = []
    orig_close = held.close
    monkeypatch.setattr(held, "close", lambda: (order.append("close"), orig_close()))
    inventory = f.bulbs._inventory
    orig_remove = inventory.remove
    monkeypatch.setattr(inventory, "remove", lambda bid: (order.append("inventory"), orig_remove(bid))[1])
    f.bulbs.removeBulb(ESC)
    assert f.bulbs._follower.source_of(ESC) == "none"
    _settle(f)
    assert order == ["close", "inventory"]


def test_it013_restart_resumes_follow_without_push(rig, world) -> None:
    first = rig.facade()
    _start_following(rig, first, "keyboard")
    first.bulbs.shutdown()
    world["journal"].clear()
    f = rig.facade()
    rig.start(f)
    _settle(f)
    assert f.bulbs._follower.source_of(ESC) == "keyboard"
    assert "push_colour" not in world["journal"]
    assert any(("hold_open", True) in b.calls for b in world["opened"])


# --- screen source (UT-092–UT-094, IT-011) ----------------------------------------


def _frame(colour):
    from PIL import Image

    return Image.new("RGB", (32, 12), colour)


def test_ut092_green_frame_pushes_green(rig, world) -> None:
    pytest.importorskip("PIL")
    f = rig.facade()
    f.keyboard.followScreenAvailable = True
    _start_following(rig, f, "screen")
    assert f._screen_hub.is_subscribed(f"bulb:{ESC}")
    f._screen_hub.frame.emit(_frame((0, 255, 0)))
    _tick(f)
    assert _pushes(world) == [(0, 255, 0)]


def test_ut093_cancelled_capture_sets_none(rig, world) -> None:
    f = rig.facade()
    _start_following(rig, f, "screen")
    f._screen_hub._on_finished(f._screen_hub._stop, "cancelled", "")
    _settle(f)
    assert json.loads(rig.state_path.read_text())["devices"]["bulbs"][ESC]["follow"] == "none"
    assert f.bulbs._follower.source_of(ESC) == "none"
    assert f.state.lastError == "Screen capture cancelled — Escritório no longer follows the screen."


def test_ut094_ended_capture_sets_all_none(rig, world) -> None:
    f = rig.facade()
    _start_following(rig, f, "screen")
    f._screen_hub._on_finished(f._screen_hub._stop, "ended", "")
    _settle(f)
    assert f.bulbs._follower.source_of(ESC) == "none"
    assert f.state.lastError == "Screen capture ended — bulbs following the screen were set to None."


def test_it011_keyboard_and_bulb_share_one_capture(rig, world, monkeypatch) -> None:
    pytest.importorskip("PIL")
    starts: list = []

    def frames(stop, **region):
        starts.append(stop)
        stop.wait()
        return
        yield  # pragma: no cover

    f = rig.facade()
    monkeypatch.setattr(f._screen_hub, "_frames", frames)
    _start_following(rig, f, "screen")
    f.keyboard.startFollowScreen(True, 0, 0, 0, 0)
    assert len(starts) == 1  # one capture, one picker
    f._screen_hub.frame.emit(_frame((0, 0, 255)))
    _settle(f)
    _tick(f)
    assert _pushes(world) == [(0, 0, 255)]
    assert any(c[0] == "set_key_colors" for c in rig.kb.calls)  # keyboard sink got it too
    f.keyboard.stopFollowOrAnimation()
    assert f._screen_hub.running and f._screen_hub.is_subscribed(f"bulb:{ESC}")
    f._screen_hub.frame.emit(_frame((255, 0, 0)))
    _settle(f)
    _tick(f)
    assert _pushes(world) == [(0, 0, 255), (255, 0, 0)]
