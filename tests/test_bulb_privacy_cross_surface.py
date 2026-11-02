"""UT-071: a local key never reaches any surface (CLI human/JSON, state, model, snapshots, logs).

Uses a sentinel key, the temp ``XDG_CONFIG_HOME`` from conftest, and fakes only: no socket opens.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

pytest.importorskip("tinytuya")

import tinytuya

from avell_storm_rgb.adapters.cli import bulb_cli
from avell_storm_rgb.adapters.cli import main as cli
from avell_storm_rgb.application.bulb_facade import BulbUnreachable
from avell_storm_rgb.application.bulb_inventory import BulbInventory
from avell_storm_rgb.application.device_state import (
    BulbState,
    DeviceState,
    DeviceStateStore,
    default_state_path,
)
from avell_storm_rgb.infrastructure.tuya import bulb as tuya_bulb
from backend_fakes import FakeBulb

SENTINEL = "KEY-SENTINEL-123"
ONLINE, OFFLINE = "eb1a2b3c4d5e6f70819202", "eb1a2b3c4d5e6f70819203"


def _wizard_file(tmp_path: Path) -> Path:
    doc = [
        {"name": "Escritório", "id": ONLINE, "key": SENTINEL, "mac": "10:d5:61:00:00:02",
         "category": "dj", "version": "3.3", "ip": "192.168.0.22"},
        {"name": "Sala", "id": OFFLINE, "key": SENTINEL, "mac": "10:d5:61:00:00:03",
         "category": "dj", "version": "3.3"},
    ]
    path = tmp_path / "devices.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _open(record, inventory):
    if record.id == OFFLINE:
        raise BulbUnreachable(record.name)
    return FakeBulb(key=record.key)


@pytest.fixture
def set_debug_calls(monkeypatch):
    calls: list = []
    monkeypatch.setattr(tinytuya, "set_debug", lambda *a, **k: calls.append((a, k)))
    return calls


def test_ut071_sentinel_never_surfaces(tmp_path, capsys, caplog, monkeypatch, set_debug_calls) -> None:
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(bulb_cli, "tuya_available", lambda: True)
    monkeypatch.setattr(bulb_cli, "open_bulb", _open)
    monkeypatch.setattr(bulb_cli, "LIST_DEADLINE", 0.5)
    wizard = _wizard_file(tmp_path)
    outputs: list[str] = []

    for argv in (
        ["bulb", "import", str(wizard)],
        ["bulb", "import", str(wizard), "--json"],
        ["bulb", "list"],
        ["bulb", "list", "--json"],
        ["bulb", "status"],
        ["bulb", "status", "--json"],
    ):
        cli.main(argv)
        out, err = capsys.readouterr()
        outputs.append(out + err)

    assert any(r.key == SENTINEL for r in BulbInventory().load())  # the key really is stored
    DeviceStateStore(default_state_path()).save(DeviceState(bulbs=(BulbState(ONLINE, follow="keyboard"),)))
    for argv in (["state", "show"], ["state", "show", "--json"]):
        cli.main(argv)
        out, err = capsys.readouterr()
        outputs.append(out + err)
    outputs.append(default_state_path().read_text(encoding="utf-8"))

    # GUI: model roles, bulb(id) snapshots and logs during connect / fail / refresh.
    pytest.importorskip("PySide6.QtCore")
    from PySide6.QtWidgets import QApplication

    from app.core.usb_worker import UsbWorker
    from app.ui.adapters.app_state import AppState
    from app.ui.adapters.bulbs_backend import BulbsBackend
    from backend_fakes import drain_bulbs

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    QApplication.instance() or QApplication([])
    usb = UsbWorker()
    state = AppState(usb)
    saved = {ONLINE: BulbState(ONLINE), OFFLINE: BulbState(OFFLINE)}
    backend = BulbsBackend(state, saved=lambda: tuple(saved.values()), open_driver=_open)
    backend.connectBulb(ONLINE)
    backend.connectBulb(OFFLINE)
    backend.refresh()
    drain_bulbs(backend._worker)
    model = backend.model
    for row in range(model.rowCount()):
        for role in model.roleNames():
            outputs.append(repr(model.data(model.index(row), role)))
    outputs.append(repr(backend.bulb(ONLINE)) + repr(backend.bulb(OFFLINE)))
    outputs.append(state.lastError)
    backend.shutdown()
    usb.shutdown(wait=True)

    outputs.append("\n".join(f"{r.getMessage()} {r.args!r}" for r in caplog.records))
    joined = "\n".join(outputs)
    assert joined.count("Escritório") >= 8 and "key: set" in joined  # surfaces really rendered
    assert caplog.records  # and the flows really logged
    for text in outputs:
        assert SENTINEL not in text

    # The adapter pins tinytuya's logger even if something raised it; set_debug is never called.
    logging.getLogger("tinytuya").setLevel(logging.DEBUG)
    tuya_bulb._tinytuya()
    assert logging.getLogger("tinytuya").level == logging.WARNING
    assert set_debug_calls == []
