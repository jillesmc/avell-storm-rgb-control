"""BulbsBackend: connect/forget/remove, read-only refresh, commands, cadence (UT-040–UT-057)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from app.core.usb_worker import UsbWorker
from app.ui.adapters.app_state import AppState
from app.ui.adapters.bulbs_backend import REFRESH_INTERVAL_MS, BulbsBackend
from avell_storm_rgb.application.bulb_facade import BulbUnreachable, KeyRejected
from avell_storm_rgb.application.bulb_inventory import BulbInventory
from avell_storm_rgb.application.device_state import BulbState
from avell_storm_rgb.domain.bulb_color import BulbStatus
from backend_fakes import FakeBulb, drain_bulbs

FIXTURE = Path(__file__).parent / "fixtures" / "tinytuya_devices.json"
QUARTO, ESC, SALA = "eb1a2b3c4d5e6f70819201", "eb1a2b3c4d5e6f70819202", "eb1a2b3c4d5e6f70819203"


@dataclass
class Env:
    backend: BulbsBackend
    state: AppState
    saved: dict = field(default_factory=dict)
    fakes: dict = field(default_factory=dict)  # id -> FakeBulb (reused per open unless replaced)
    errors: dict = field(default_factory=dict)  # id -> exception raised on open
    opens: list = field(default_factory=list)
    persisted: list = field(default_factory=list)

    def drain(self) -> None:
        drain_bulbs(self.backend._worker)

    def row(self, bulb_id: str) -> dict:
        return self.backend.bulb(bulb_id)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    QApplication.instance() or QApplication([])
    FakeBulb.live_connections = 0
    inventory = BulbInventory(tmp_path / "inv.json")
    usb = UsbWorker()
    state = AppState(usb)
    holder: dict = {}

    def opener(record, _inventory):
        e = holder["env"]
        e.opens.append((record.id, record.key))
        if record.id in e.errors:
            raise e.errors[record.id]
        return e.fakes.setdefault(record.id, FakeBulb())

    backend = BulbsBackend(
        state,
        saved=lambda: tuple(holder["env"].saved.values()) if "env" in holder else (),
        inventory=inventory,
        open_driver=opener,
    )
    e = Env(backend, state)
    holder["env"] = e

    def persist(bulb_id, changes):
        e.persisted.append((bulb_id, changes))
        if changes.get("remove"):
            e.saved.pop(bulb_id, None)
            return
        cur = e.saved.get(bulb_id, BulbState(bulb_id, remembered=False))
        if "remembered" in changes:
            cur = replace(cur, remembered=changes["remembered"])
        if "follow" in changes:
            cur = replace(cur, follow=changes["follow"])
        e.saved[bulb_id] = cur

    backend.persistUpdate.connect(persist)
    backend.importFile(QUrl.fromLocalFile(str(FIXTURE)))
    yield e
    backend.shutdown()
    usb.shutdown(wait=True)


def _remember(env: Env, *ids: str) -> None:
    for i in ids:
        env.saved[i] = BulbState(i)


def test_import_summary_and_rows(env) -> None:
    assert env.backend.importSummary == "Imported 3 bulbs"
    assert [r["title"] for r in env.backend.model.rows()] == ["Escritório", "Quarto", "Sala"]


def test_import_not_a_list_reports(env, tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{}")
    env.backend.importFile(QUrl.fromLocalFile(str(bad)))
    assert env.state.lastError == f"error: not a tinytuya devices.json (expected a list of devices): {bad}"


def test_ut040_connect_remembers(env) -> None:
    env.backend.connectBulb(ESC)
    assert env.row(ESC)["busy"] is True
    assert env.persisted == []
    env.drain()
    assert env.fakes[ESC].names() == ["status", "close"]
    assert env.persisted == [(ESC, {"remembered": True})]
    row = env.row(ESC)
    assert row["remembered"] and row["stateKnown"] and not row["busy"]


def test_ut041_unreachable_not_remembered(env) -> None:
    env.errors[ESC] = BulbUnreachable("Escritório")
    env.backend.connectBulb(ESC)
    env.drain()
    assert env.persisted == []
    assert env.state.lastError.startswith("Escritório is not reachable on the network. ")


def test_ut042_double_connect_reads_once(env) -> None:
    env.backend.connectBulb(ESC)
    env.backend.connectBulb(ESC)
    env.drain()
    assert env.fakes[ESC].names().count("status") == 1
    assert env.persisted == [(ESC, {"remembered": True})]


def test_ut043_key_rejected_message(env) -> None:
    env.errors[ESC] = KeyRejected("local key or protocol rejected")
    env.backend.connectBulb(ESC)
    env.drain()
    assert env.state.lastError == "Escritório rejected the local key or protocol — re-import devices.json"


def test_ut044_disconnect_keeps_key(env) -> None:
    _remember(env, ESC)
    env.backend.disconnectBulb(ESC)
    assert env.persisted == [(ESC, {"remembered": False})]
    assert ESC in {r.id for r in BulbInventory(env.backend._inventory.path).load()}
    assert env.row(ESC)["remembered"] is False


def test_ut045_remove_deletes_record_and_state(env) -> None:
    _remember(env, ESC)
    env.backend.removeBulb(ESC)
    env.drain()
    assert ESC not in {r.id for r in env.backend._inventory.load()}
    assert env.persisted == [(ESC, {"remove": True})]
    assert env.row(ESC) == {}


def test_ut046_refresh_reads_only_remembered(env) -> None:
    _remember(env, ESC, SALA)
    env.backend.refresh()
    env.drain()
    assert set(env.fakes) == {ESC, SALA}
    for fake in env.fakes.values():
        assert [n for n in fake.names() if n != "close"] == ["status"]


def test_ut047_unknown_snapshot(env) -> None:
    _remember(env, ESC)
    env.backend._changed()
    assert env.row(ESC) == {
        "bulbId": ESC,
        "title": "Escritório",
        "subtitle": "Reading…",
        "remembered": True,
        "available": False,
        "lightOn": False,
        "stateKnown": False,
        "unavailableReason": "",
        "mode": "unknown",
        "brightness": 0,
        "temperature": -1,
        "rgb": [],
        "follow": "none",
        "ip": "192.168.0.22",
        "busy": False,
    }


def test_ut048_ut049_unreachable_then_recovers(env) -> None:
    _remember(env, SALA)
    env.errors[SALA] = BulbUnreachable("Sala")
    env.backend.refresh()
    env.drain()
    assert env.row(SALA)["unavailableReason"] == "Sala is not reachable on the network"
    assert env.row(SALA)["subtitle"] == "offline"
    del env.errors[SALA]
    env.backend.refresh()
    env.drain()
    assert env.row(SALA)["unavailableReason"] == ""
    assert env.row(SALA)["available"] is True


def test_ut050_retry_clears_reason(env) -> None:
    _remember(env, SALA)
    env.errors[SALA] = BulbUnreachable("Sala")
    env.backend.refresh()
    env.drain()
    del env.errors[SALA]
    env.backend.retryBulb(SALA)
    env.drain()
    assert env.row(SALA)["unavailableReason"] == "" and env.row(SALA)["stateKnown"]


def test_ut051_retry_still_down_never_busy(env) -> None:
    _remember(env, SALA)
    env.errors[SALA] = BulbUnreachable("Sala")
    seen: list[bool] = []
    env.state.busyChanged.connect(lambda: seen.append(env.state.busy))
    env.backend.refresh()
    env.drain()
    env.backend.retryBulb(SALA)
    env.drain()
    assert seen == [] and env.state.busy is False
    assert env.row(SALA)["unavailableReason"] == "Sala is not reachable on the network"


def test_ut052_light_switch_applied_on_op_done(env) -> None:
    _remember(env, ESC)
    env.fakes[ESC] = FakeBulb(status=BulbStatus(False, "white", 50, 30, None))
    env.backend.refresh()
    env.drain()
    env.backend.setLightOn(ESC, True)
    assert env.row(ESC)["lightOn"] is False  # never optimistic
    env.drain()
    assert ("set_power", True) in env.fakes[ESC].calls
    assert env.row(ESC)["lightOn"] is True


def test_ut053_failure_keeps_real_value(env) -> None:
    _remember(env, ESC)
    env.fakes[ESC] = FakeBulb(status=BulbStatus(False, "white", 50, 30, None))
    env.backend.refresh()
    env.drain()
    env.fakes[ESC].fail_on = frozenset({"set_power"})
    env.backend.setLightOn(ESC, True)
    env.drain()
    assert env.row(ESC)["lightOn"] is False
    assert env.state.lastError.startswith("Escritório")


def test_commands_update_mode_fields(env) -> None:
    _remember(env, ESC)
    env.backend.refresh()
    env.drain()
    env.backend.setColor(ESC, 255, 0, 0)
    env.drain()
    row = env.row(ESC)
    assert (row["mode"], row["rgb"], row["temperature"], row["brightness"]) == ("colour", [255, 0, 0], -1, 100)
    env.backend.setWhite(ESC, 70)
    env.backend.setBrightness(ESC, 40)
    env.drain()
    row = env.row(ESC)
    assert (row["mode"], row["temperature"], row["brightness"], row["rgb"]) == ("white", 70, 40, [])


def test_ut054_timer_interval_and_fire(env, monkeypatch) -> None:
    calls: list = []
    env.backend.windowVisible = True
    assert env.backend._timer.interval() == REFRESH_INTERVAL_MS == 30_000
    assert env.backend._timer.isActive()
    monkeypatch.setattr(env.backend, "refresh", lambda: calls.append(1))
    env.backend._timer.timeout.disconnect()
    env.backend._timer.timeout.connect(env.backend.refresh)
    env.backend._timer.timeout.emit()
    assert calls == [1]


def test_ut055_ut057_show_refreshes_once(env) -> None:
    _remember(env, ESC)
    env.backend.windowVisible = True
    env.backend.windowVisible = True  # repeated True: no second refresh
    env.drain()
    assert env.fakes[ESC].names().count("status") == 1
    env.backend.windowVisible = False
    env.backend.windowVisible = True
    env.drain()
    assert env.fakes[ESC].names().count("status") == 2


def test_ut056_hidden_stops_timer(env) -> None:
    _remember(env, ESC)
    env.backend.windowVisible = True
    env.drain()
    env.backend.windowVisible = False
    assert not env.backend._timer.isActive()
    env.drain()
    assert env.fakes[ESC].names().count("status") == 1


def test_inert_when_unavailable(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    QApplication.instance() or QApplication([])
    usb = UsbWorker()
    backend = BulbsBackend(AppState(usb), saved=lambda: (), available=False,
                           inventory=BulbInventory(tmp_path / "inv.json"))
    backend.importFile(QUrl.fromLocalFile(str(FIXTURE)))
    backend.windowVisible = True
    assert backend.model.rows() == [] and not backend._timer.isActive()
    assert not (tmp_path / "inv.json").exists()
    backend.shutdown()
    usb.shutdown(wait=True)


def test_d3_success_clears_the_bulbs_own_banner(env) -> None:
    _remember(env, SALA)
    env.errors[SALA] = BulbUnreachable("Sala")
    env.backend.retryBulb(SALA)
    env.drain()
    assert env.state.lastError.startswith("Sala is not reachable")
    del env.errors[SALA]
    env.backend.retryBulb(SALA)
    env.drain()
    assert env.state.lastError == ""


def test_d3_other_banners_stay(env) -> None:
    _remember(env, ESC)
    env.state.reportError("Could not save device state")
    env.backend.refresh()
    env.drain()
    assert env.state.lastError == "Could not save device state"
