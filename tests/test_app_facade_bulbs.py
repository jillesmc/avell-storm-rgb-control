"""AppFacade + bulbs: pruning, extra absent, visibility forwarding (UT-035, UT-037, UT-057)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from avell_storm_rgb.application.bulb_inventory import BulbInventory, default_inventory_path, parse_tinytuya_devices
from avell_storm_rgb.application.device_state import BulbState, DeviceState
from facade_harness import rig  # noqa: F401

FIXTURE = Path(__file__).parent / "fixtures" / "tinytuya_devices.json"
ESC = "eb1a2b3c4d5e6f70819202"
GONE = "ffffffffffffffffffffff"


def _import_fixture() -> None:
    records, _ = parse_tinytuya_devices(FIXTURE.read_text(encoding="utf-8"))
    BulbInventory().upsert(records)


def _saved_bulb_ids(rig) -> list[str]:
    return sorted(json.loads(rig.state_path.read_text())["devices"].get("bulbs", {}))


def _force_write(f) -> None:
    f._save()


def test_ut035_prunes_only_with_extra_and_loaded_inventory(rig, monkeypatch) -> None:
    monkeypatch.setattr("app.ui.adapters.app_facade.tuya_available", lambda: True)
    _import_fixture()
    rig.save(DeviceState(bulbs=(BulbState(ESC), BulbState(GONE))))
    f = rig.facade()
    _force_write(f)
    assert _saved_bulb_ids(rig) == [ESC]


@pytest.mark.parametrize("inventory", ["missing", "corrupt"])
def test_ut035_keeps_entries_when_inventory_unusable(rig, monkeypatch, inventory) -> None:
    monkeypatch.setattr("app.ui.adapters.app_facade.tuya_available", lambda: True)
    if inventory == "corrupt":
        path = default_inventory_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{")
    rig.save(DeviceState(bulbs=(BulbState(ESC), BulbState(GONE))))
    f = rig.facade()
    _force_write(f)
    assert _saved_bulb_ids(rig) == sorted([ESC, GONE])


def test_ut037_extra_absent_keeps_bulbs(rig, monkeypatch) -> None:
    monkeypatch.setattr("app.ui.adapters.app_facade.tuya_available", lambda: False)
    _import_fixture()
    rig.save(DeviceState(bulbs=(BulbState(ESC, follow="keyboard"), BulbState(GONE, remembered=False))))
    f = rig.facade()
    assert f.bulbsAvailable is False
    assert f.bulbs.model.rows() == []
    _force_write(f)
    doc = json.loads(rig.state_path.read_text())["devices"]["bulbs"]
    assert doc == {
        ESC: {"remembered": True, "follow": "keyboard"},
        GONE: {"remembered": False, "follow": "none"},
    }


def test_ut057_set_window_visible_forwards(rig, monkeypatch) -> None:
    monkeypatch.setattr("app.ui.adapters.app_facade.tuya_available", lambda: True)
    f = rig.facade()
    calls: list = []
    monkeypatch.setattr(f.bulbs, "refresh", lambda: calls.append(1))
    f.setWindowVisible(True)
    f.setWindowVisible(True)
    assert f.bulbs.windowVisible is True
    assert calls == [1]
    f.setWindowVisible(False)
    assert f.bulbs.windowVisible is False and not f.bulbs._timer.isActive()
