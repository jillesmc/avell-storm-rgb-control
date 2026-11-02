"""App → bulbs → state.json round-trips with real files and FakeBulb (IT-001–IT-006)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QUrl

from avell_storm_rgb.application.bulb_inventory import BulbInventory
from avell_storm_rgb.application.device_state import (
    DeviceState,
    KeyboardState,
    LedBarLook,
    LedBarState,
    SolidLook,
)
from backend_fakes import FakeBulb, drain_bulbs
from facade_harness import KB_ROW, LED_ROW, drain, rig  # noqa: F401

FIXTURE = Path(__file__).parent / "fixtures" / "tinytuya_devices.json"
ESC = "eb1a2b3c4d5e6f70819202"
FIXTURE_KEYS = [d["key"] for d in json.loads(FIXTURE.read_text(encoding="utf-8"))]


@pytest.fixture
def bulbs(rig, monkeypatch):
    """Extra present; every open returns a new FakeBulb sharing one journal."""
    monkeypatch.setattr("app.ui.adapters.app_facade.tuya_available", lambda: True)
    FakeBulb.live_connections = 0
    world = {"journal": [], "opened": []}

    def open_bulb(record, inventory):
        bulb = FakeBulb(journal=world["journal"], key=record.key)
        world["opened"].append(bulb)
        return bulb

    monkeypatch.setattr("avell_storm_rgb.application.bulb_facade.open_bulb", open_bulb)
    return world


def _saved_bulbs(rig) -> dict:
    return json.loads(rig.state_path.read_text())["devices"].get("bulbs", {})


def _flow(rig, f) -> None:
    memory: list = []
    f.deviceMemoryChanged.connect(lambda: memory.append(1))
    f.bulbs.importFile(QUrl.fromLocalFile(str(FIXTURE)))
    f.bulbs.connectBulb(ESC)
    drain_bulbs(f.bulbs._worker)
    assert _saved_bulbs(rig)[ESC]["remembered"] is True  # IT-001
    assert memory
    f.bulbs.disconnectBulb(ESC)
    assert _saved_bulbs(rig)[ESC]["remembered"] is False  # IT-002
    assert any(r.id == ESC and r.key for r in BulbInventory().load())
    f.bulbs.removeBulb(ESC)
    drain_bulbs(f.bulbs._worker)
    assert ESC not in _saved_bulbs(rig)  # IT-003
    assert all(r.id != ESC for r in BulbInventory().load())


def test_it001_it003_import_connect_disconnect_remove(rig, bulbs) -> None:
    f = rig.facade()
    _flow(rig, f)


def test_it004_startup_reads_bulbs_only(rig, bulbs) -> None:
    rig.rows = [KB_ROW, LED_ROW]
    first = rig.facade()
    first.bulbs.importFile(QUrl.fromLocalFile(str(FIXTURE)))
    first.bulbs.connectBulb(ESC)
    drain_bulbs(first.bulbs._worker)
    state = rig.store().load()
    rig.save(
        DeviceState(
            keyboard=KeyboardState("048d:ce00", look=SolidLook((1, 2, 3))),
            led_bar=LedBarState("048d:7001", look=LedBarLook(((255, 0, 0),), "static", 50, 3)),
            bulbs=state.bulbs,
        )
    )
    bulbs["journal"].clear()
    rig.journal.clear()
    f = rig.facade()
    rig.start(f)
    drain_bulbs(f.bulbs._worker)
    assert ("FakeKeyboard", "set_color") in rig.journal
    assert any(who == "FakeLedBar" for who, _ in rig.journal)
    assert bulbs["journal"] == ["status"]
    assert f.bulbs.bulb(ESC)["stateKnown"] is True


def test_it005_reimport_new_key_used_next(rig, bulbs, tmp_path) -> None:
    f = rig.facade()
    f.bulbs.importFile(QUrl.fromLocalFile(str(FIXTURE)))
    f.bulbs.connectBulb(ESC)
    drain_bulbs(f.bulbs._worker)
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for d in doc:
        if d["id"] == ESC:
            d["key"] = "new_example_key_02"
    newer = tmp_path / "devices.json"
    newer.write_text(json.dumps(doc), encoding="utf-8")
    f.bulbs.importFile(QUrl.fromLocalFile(str(newer)))
    f.bulbs.setLightOn(ESC, True)
    drain_bulbs(f.bulbs._worker)
    assert bulbs["opened"][-1].key == "new_example_key_02"
    assert ("set_power", True) in bulbs["opened"][-1].calls


def test_it006_no_keys_in_debug_logs(rig, bulbs, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    f = rig.facade()
    _flow(rig, f)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert caplog.records  # the flow does log
    for key in FIXTURE_KEYS:
        assert key not in text
