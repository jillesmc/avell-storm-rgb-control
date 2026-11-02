"""CLI `bulb …` verbs (E2E-001–E2E-012, E2E-014, E2E-015). Expected output comes from _dx.md.

The fake ``open_bulb`` keeps every socket closed; ids, keys, MACs and IPs are the
fictional ones from ``tests/fixtures/tinytuya_devices.json`` and the temp
``XDG_CONFIG_HOME`` from ``tests/conftest.py``.
"""

from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

import pytest

from avell_storm_rgb.adapters.cli import bulb_cli
from avell_storm_rgb.adapters.cli import main as cli
from avell_storm_rgb.application.bulb_facade import (
    DEFAULT_DISCOVERY_TIMEOUT,
    BulbError,
    BulbUnreachable,
    KeyRejected,
)
from avell_storm_rgb.application.bulb_inventory import (
    BulbInventory,
    BulbRecord,
    default_inventory_path,
    parse_tinytuya_devices,
)
from avell_storm_rgb.domain.bulb_color import BulbStatus

FIXTURE = Path(__file__).parent / "fixtures" / "tinytuya_devices.json"
DX_PATH = "/home/jilles/.config/avell-storm-rgb/tuya_devices.json"

QUARTO = "eb1a2b3c4d5e6f70819201"
ESCRITORIO = "eb1a2b3c4d5e6f70819202"
SALA = "eb1a2b3c4d5e6f70819203"
PLUG = "eb1a2b3c4d5e6f70819204"

WHITE_100 = BulbStatus(on=True, mode="white", brightness=100, temperature=100, rgb=None)
COLOUR_FF8800 = BulbStatus(on=True, mode="colour", brightness=100, temperature=None, rgb=(255, 136, 0))
OFF = BulbStatus(on=False, mode="white", brightness=0, temperature=None, rgb=None)

# Verbatim from _dx.md "No bulbs imported".
NO_BULBS = [
    "No bulbs imported. Import the devices.json written by 'python -m tinytuya wizard':",
    "  avell-storm-rgb bulb import <path/to/devices.json>",
]


class FakeBulb:
    """A ``BulbDriver`` with a call journal and a programmable status (no socket)."""

    def __init__(
        self,
        status: BulbStatus,
        *,
        ip: str | None = None,
        unreachable: bool = False,
        key_rejected: bool = False,
        error: Exception | None = None,
        delay: float = 0.0,
    ) -> None:
        self._status = status
        self.ip = ip
        self.unreachable = unreachable
        self.key_rejected = key_rejected
        self.error = error
        self.delay = delay
        self.calls: list[tuple] = []
        self.closed = False

    def _check(self) -> None:
        if self.delay:
            time.sleep(self.delay)
        if self.key_rejected:
            raise KeyRejected("local key or protocol rejected")
        if self.unreachable:
            raise BulbUnreachable("bulb is not reachable")
        if self.error is not None:
            raise self.error

    def status(self) -> BulbStatus:
        self.calls.append(("status",))
        self._check()
        return self._status

    def set_power(self, on: bool) -> None:
        self.calls.append(("set_power", on))
        self._check()
        self._status = replace(self._status, on=on)

    def set_brightness(self, percent: int, status: BulbStatus | None = None) -> None:
        self.calls.append(("set_brightness", percent, status))
        self._check()
        self._status = replace(self._status, on=True, brightness=percent)

    def set_white(self, temperature_percent: int | None = None, status=None) -> None:
        self.calls.append(("set_white", temperature_percent, status))
        self._check()
        self._status = replace(self._status, on=True, mode="white", temperature=temperature_percent)

    def set_colour(self, rgb) -> None:
        self.calls.append(("set_colour", tuple(rgb)))
        self._check()
        self._status = replace(self._status, on=True, mode="colour", rgb=tuple(rgb))

    def push_colour(self, rgb) -> None:
        self.calls.append(("push_colour", tuple(rgb)))

    def hold_open(self, persistent: bool) -> None:
        self.calls.append(("hold_open", persistent))

    def close(self) -> None:
        self.closed = True

    def names(self) -> list[str]:
        return [call[0] for call in self.calls]


class World:
    """Fake ``open_bulb``: known ids answer, unknown ids are unreachable."""

    def __init__(self) -> None:
        self.bulbs: dict[str, FakeBulb] = {}
        self.opened: list[str] = []

    def add(self, bulb_id: str, status: BulbStatus = WHITE_100, **kwargs) -> FakeBulb:
        bulb = FakeBulb(status, **kwargs)
        self.bulbs[bulb_id] = bulb
        return bulb

    def open(self, record: BulbRecord, inventory: BulbInventory) -> FakeBulb:
        self.opened.append(record.id)
        bulb = self.bulbs.get(record.id)
        if bulb is None:
            raise BulbUnreachable(record.name)
        return bulb


@pytest.fixture(autouse=True)
def extra_installed(monkeypatch):
    """Every test runs as if the optional ``tuya`` extra were installed."""
    monkeypatch.setattr(bulb_cli, "tuya_available", lambda: True)


@pytest.fixture
def world(monkeypatch):
    w = World()
    monkeypatch.setattr(bulb_cli, "open_bulb", w.open)
    return w


def _run(capsys, *argv) -> tuple[int, str, str]:
    code = cli.main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def _dx(lines: list[str]) -> list[str]:
    return [line.replace(DX_PATH, str(default_inventory_path())) for line in lines]


def _inventory(**changes: dict) -> Path:
    """Write the _dx.md inventory (Quarto, Escritório, Sala) and return its path."""
    records, _ = parse_tinytuya_devices(FIXTURE.read_text(encoding="utf-8"))
    if changes:
        records = [replace(record, **changes[record.id]) if record.id in changes else record for record in records]
    inventory = BulbInventory()
    inventory.save(records)
    return inventory.path


def _reimport_file(tmp_path: Path) -> Path:
    """devices.json for E2E-002: Sala's key changed, plus a non-bulb plug."""
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc[2]["key"] = "q6R!x2_example_03_changed"
    doc.append(
        {
            "name": "Tomada",
            "id": PLUG,
            "key": "q6R!x2_example_04",
            "mac": "10:d5:61:00:00:04",
            "category": "cz",
            "version": "3.3",
        }
    )
    path = tmp_path / "devices.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


# --- import (E2E-001–E2E-004) -------------------------------------------------------


def test_e2e001_import_golden_path(capsys) -> None:
    path = default_inventory_path()
    code, out, err = _run(capsys, "bulb", "import", str(FIXTURE))
    assert out.splitlines() == _dx(
        [
            "Quarto       eb1a2b3c4d5e6f70819201  added",
            "Escritório   eb1a2b3c4d5e6f70819202  added",
            "Sala         eb1a2b3c4d5e6f70819203  added",
            "Imported 3 bulbs into /home/jilles/.config/avell-storm-rgb/tuya_devices.json",
        ]
    )
    assert (code, err) == (0, "")
    assert path.is_file()
    assert "q6R!x2_example" not in out


def test_e2e002_reimport_transcript(capsys, tmp_path) -> None:
    _run(capsys, "bulb", "import", str(FIXTURE))
    second = _reimport_file(tmp_path)
    code, out, _ = _run(capsys, "bulb", "import", str(second))
    assert out.splitlines() == _dx(
        [
            "Quarto       eb1a2b3c4d5e6f70819201  unchanged",
            "Escritório   eb1a2b3c4d5e6f70819202  unchanged",
            "Sala         eb1a2b3c4d5e6f70819203  updated (key changed)",
            "Tomada       eb1a2b3c4d5e6f70819204  skipped: not a bulb (category cz)",
            "Imported 3 bulbs into /home/jilles/.config/avell-storm-rgb/tuya_devices.json",
        ]
    )
    assert code == 0


def test_e2e002_reimport_json(capsys, tmp_path) -> None:
    _run(capsys, "bulb", "import", str(FIXTURE))
    second = _reimport_file(tmp_path)
    code, out, _ = _run(capsys, "bulb", "import", str(second), "--json")
    assert out.strip() == _dx(
        [
            '{"path": "/home/jilles/.config/avell-storm-rgb/tuya_devices.json", "results": '
            '[{"id": "eb1a2b3c4d5e6f70819201", "name": "Quarto", "status": "unchanged"}, '
            '{"id": "eb1a2b3c4d5e6f70819202", "name": "Escritório", "status": "unchanged"}, '
            '{"id": "eb1a2b3c4d5e6f70819203", "name": "Sala", "status": "updated", "reason": "key changed"}, '
            '{"id": "eb1a2b3c4d5e6f70819204", "name": "Tomada", "status": "skipped", '
            '"reason": "not a bulb (category cz)"}]}'
        ]
    )[0]
    assert code == 0
    assert "q6R!x2_example" not in out


def test_e2e003_import_not_a_list(capsys, tmp_path) -> None:
    bad = tmp_path / "devices.json"
    bad.write_text('{"devices": []}', encoding="utf-8")
    code, out, err = _run(capsys, "bulb", "import", str(bad))
    assert (code, out) == (1, "")
    assert err.strip() == f"error: not a tinytuya devices.json (expected a list of devices): {bad}"
    assert not default_inventory_path().exists()


def test_e2e004_import_without_bulbs(capsys, tmp_path) -> None:
    empty = tmp_path / "devices.json"
    empty.write_text(
        json.dumps([{"name": "Tomada", "id": PLUG, "key": "k", "category": "cz"}]),
        encoding="utf-8",
    )
    code, out, err = _run(capsys, "bulb", "import", str(empty))
    assert (code, out.strip(), err) == (1, f"No bulbs found in {empty}", "")
    assert not default_inventory_path().exists()


def test_import_missing_file(capsys, tmp_path) -> None:
    missing = tmp_path / "gone.json"
    code, out, err = _run(capsys, "bulb", "import", str(missing))
    assert (code, out) == (1, "")
    assert err.strip() == (
        f"error: not a tinytuya devices.json (cannot read file (No such file or directory)): {missing}"
    )


def test_import_joins_update_reasons(capsys, tmp_path) -> None:
    _run(capsys, "bulb", "import", str(FIXTURE))
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    doc[2]["key"] = "q6R!x2_example_03_changed"
    doc[2]["name"] = "Sala Nova"
    doc[2]["mac"] = "10:d5:61:00:00:99"
    second = tmp_path / "devices.json"
    second.write_text(json.dumps(doc), encoding="utf-8")
    _, out, _ = _run(capsys, "bulb", "import", str(second))
    assert "Sala Nova    eb1a2b3c4d5e6f70819203  updated (key changed, name changed, mac changed)" in out.splitlines()


def test_import_never_removes_entries(capsys, tmp_path) -> None:
    _run(capsys, "bulb", "import", str(FIXTURE))
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))[:1]
    one = tmp_path / "one.json"
    one.write_text(json.dumps(doc), encoding="utf-8")
    _run(capsys, "bulb", "import", str(one))
    assert [record.id for record in BulbInventory().load()] == [QUARTO, ESCRITORIO, SALA]


# --- list (E2E-011) -----------------------------------------------------------------


def test_e2e011_list_transcript(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    world.add(ESCRITORIO, COLOUR_FF8800, ip="192.168.0.22")
    code, out, _ = _run(capsys, "bulb", "list")
    assert out.splitlines() == _dx(
        [
            "Inventory: /home/jilles/.config/avell-storm-rgb/tuya_devices.json",
            "Quarto       eb1a2b3c4d5e6f70819201  online   192.168.0.21  protocol 3.3  key: set",
            "Escritório   eb1a2b3c4d5e6f70819202  online   192.168.0.22  protocol 3.3  key: set",
            "Sala         eb1a2b3c4d5e6f70819203  offline  —             protocol 3.3  key: set",
        ]
    )
    assert code == 0
    assert "q6R!x2_example" not in out


def test_e2e011_list_json(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    world.add(ESCRITORIO, COLOUR_FF8800, ip="192.168.0.22")
    code, out, _ = _run(capsys, "bulb", "list", "--json")
    assert out.strip() == _dx(
        [
            '{"path": "/home/jilles/.config/avell-storm-rgb/tuya_devices.json", "bulbs": '
            '[{"id": "eb1a2b3c4d5e6f70819201", "name": "Quarto", "online": true, '
            '"ip": "192.168.0.21", "protocol": "3.3", "key": "set"}, '
            '{"id": "eb1a2b3c4d5e6f70819202", "name": "Escritório", "online": true, '
            '"ip": "192.168.0.22", "protocol": "3.3", "key": "set"}, '
            '{"id": "eb1a2b3c4d5e6f70819203", "name": "Sala", "online": false, '
            '"ip": null, "protocol": "3.3", "key": "set"}]}'
        ]
    )[0]
    assert code == 0
    assert "q6R!x2_example" not in out


def test_list_limits_and_deadline_constants() -> None:
    assert bulb_cli.LIST_WORKERS == 8
    # D-2: the deadline must cover a UDP discovery plus one read.
    assert bulb_cli.LIST_DEADLINE > DEFAULT_DISCOVERY_TIMEOUT


def test_e2e011_list_uses_one_deadline_for_the_whole_command(capsys, monkeypatch, world) -> None:
    _inventory()
    monkeypatch.setattr(bulb_cli, "LIST_DEADLINE", 0.3)
    for bulb_id, ip in ((QUARTO, "192.168.0.21"), (ESCRITORIO, "192.168.0.22"), (SALA, "192.168.0.23")):
        world.add(bulb_id, WHITE_100, ip=ip, delay=1.0)  # each read would take 1 s
    start = time.monotonic()
    code, out, _ = _run(capsys, "bulb", "list")
    elapsed = time.monotonic() - start
    assert code == 0
    assert elapsed < 0.9, elapsed  # one deadline, not three in a row
    assert world.opened == [QUARTO, ESCRITORIO, SALA]  # all three started together
    assert all("  offline" in line for line in out.splitlines()[1:])


# --- status (E2E-005, E2E-015) ------------------------------------------------------


def test_e2e005_status_transcript(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    world.add(ESCRITORIO, COLOUR_FF8800, ip="192.168.0.22")
    code, out, _ = _run(capsys, "bulb", "status")
    assert out.splitlines() == _dx(
        [
            "Quarto       on   white   brightness 100%  temperature 100%",
            "Escritório   on   colour  #ff8800  brightness 100%",
            "Sala         offline",
        ]
    )
    assert code == 1


def test_e2e005_status_json(capsys, world) -> None:
    _inventory()
    world.add(ESCRITORIO, COLOUR_FF8800, ip="192.168.0.22")
    code, out, _ = _run(capsys, "bulb", "status", "escritorio", "--json")
    assert out.strip() == _dx(
        [
            '{"results": [{"id": "eb1a2b3c4d5e6f70819202", "name": "Escritório", '
            '"online": true, "on": true, "mode": "colour", "brightness": 100, '
            '"temperature": null, "rgb": [255, 136, 0]}]}'
        ]
    )[0]
    assert code == 0


def test_status_json_offline_entry(capsys, world) -> None:
    _inventory()
    code, out, _ = _run(capsys, "bulb", "status", "sala", "--json")
    assert json.loads(out) == {"results": [{"id": SALA, "name": "Sala", "online": False}]}
    assert code == 1


def test_e2e015_status_all_online(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    world.add(ESCRITORIO, COLOUR_FF8800, ip="192.168.0.22")
    world.add(SALA, OFF, ip="192.168.0.23")
    code, out, _ = _run(capsys, "bulb", "status")
    assert out.splitlines() == _dx(
        [
            "Quarto       on   white   brightness 100%  temperature 100%",
            "Escritório   on   colour  #ff8800  brightness 100%",
            "Sala         off",
        ]
    )
    assert code == 0


def test_status_key_rejected_is_failed(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21", key_rejected=True)
    code, out, _ = _run(capsys, "bulb", "status", "quarto")
    assert (code, out.splitlines()) == (
        1,
        ["Quarto       failed: local key or protocol rejected — re-import devices.json"],
    )
    code, out, _ = _run(capsys, "bulb", "status", "quarto", "--json")
    assert json.loads(out) == {
        "results": [
            {
                "id": QUARTO,
                "name": "Quarto",
                "online": False,
                "status": "failed",
                "reason": "local key or protocol rejected — re-import devices.json",
            }
        ]
    }
    assert code == 1


def test_status_target_by_device_id(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    code, out, _ = _run(capsys, "bulb", "status", QUARTO)
    assert (code, out.splitlines()) == (0, ["Quarto       on   white   brightness 100%  temperature 100%"])


# --- control verbs (E2E-006–E2E-008) ------------------------------------------------


def test_e2e006_white_temp_all_with_one_offline(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    world.add(ESCRITORIO, COLOUR_FF8800, ip="192.168.0.22")
    code, out, _ = _run(capsys, "bulb", "white", "--temp", "20", "all")
    assert out.splitlines() == _dx(
        [
            "Quarto       white 20%",
            "Escritório   white 20%",
            "Sala         offline",
        ]
    )
    assert code == 1
    assert world.bulbs[QUARTO].calls == [("set_white", 20, None)]
    assert world.bulbs[ESCRITORIO].calls == [("set_white", 20, None)]


def test_e2e007_color_and_off_transcripts(capsys, world) -> None:
    _inventory()
    world.add(ESCRITORIO, COLOUR_FF8800, ip="192.168.0.22")
    world.add(SALA, WHITE_100, ip="192.168.0.23")

    code, out, _ = _run(capsys, "bulb", "color", "255", "136", "0", "Escritório")
    assert (code, out.splitlines()) == (0, ["Escritório   colour #ff8800"])
    assert world.bulbs[ESCRITORIO].calls == [("set_colour", (255, 136, 0))]

    code, out, _ = _run(capsys, "bulb", "off", "escritorio")
    assert (code, out.splitlines()) == (0, ["Escritório   off"])

    code, out, _ = _run(capsys, "bulb", "off", "sala")
    assert (code, out.splitlines()) == (0, ["Sala         off"])
    assert world.bulbs[SALA].calls == [("set_power", False)]


def test_e2e008_bright_out_of_range_is_argparse(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["bulb", "bright", "0", "sala"])
    assert excinfo.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_e2e008_bright_above_range_is_argparse(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["bulb", "bright", "150", "sala"])
    assert excinfo.value.code == 2
    assert "usage:" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["bulb", "white", "--temp", "101", "sala"],
        ["bulb", "white", "--temp", "-1", "sala"],
        ["bulb", "color", "256", "0", "0", "sala"],
    ],
)
def test_out_of_range_values_are_argparse(capsys, argv) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(argv)
    assert excinfo.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_toggle_reads_then_inverts(capsys, world) -> None:
    _inventory()
    bulb = world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    code, out, _ = _run(capsys, "bulb", "toggle", "quarto")
    assert (code, out.splitlines()) == (0, ["Quarto       off"])
    assert bulb.calls == [("status",), ("set_power", False)]


def test_bright_reads_once_and_passes_the_snapshot(capsys, world) -> None:
    _inventory()
    bulb = world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    code, out, _ = _run(capsys, "bulb", "bright", "40", "quarto")
    assert (code, out.splitlines()) == (0, ["Quarto       brightness 40%"])
    assert bulb.calls == [("status",), ("set_brightness", 40, WHITE_100)]


def test_bright_failed_read_is_offline_and_never_writes(capsys, world) -> None:
    _inventory()
    bulb = world.add(QUARTO, WHITE_100, ip="192.168.0.21", unreachable=True)
    code, out, _ = _run(capsys, "bulb", "bright", "40", "quarto")
    assert (code, out.splitlines()) == (1, ["Quarto       offline"])
    assert bulb.names() == ["status"]


def test_white_without_temp_sends_mode_only_and_does_not_read(capsys, world) -> None:
    _inventory()
    bulb = world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    code, out, _ = _run(capsys, "bulb", "white", "quarto")
    assert (code, out.splitlines()) == (0, ["Quarto       white"])
    assert bulb.calls == [("set_white", None, None)]


def test_on_by_name_is_case_and_accent_insensitive(capsys, world) -> None:
    _inventory()
    bulb = world.add(ESCRITORIO, COLOUR_FF8800, ip="192.168.0.22")
    code, out, _ = _run(capsys, "bulb", "on", "escritorio")
    assert (code, out.splitlines()) == (0, ["Escritório   on"])
    assert bulb.calls == [("set_power", True)]


def test_key_rejected_is_failed_with_the_dx_hint(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21", key_rejected=True)
    code, out, _ = _run(capsys, "bulb", "on", "quarto")
    assert (code, out.splitlines()) == (
        1,
        ["Quarto       failed: local key or protocol rejected — re-import devices.json"],
    )


def test_other_device_error_keeps_the_exception_shape(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21", error=BulbError("bulb command failed"))
    code, out, _ = _run(capsys, "bulb", "on", "quarto")
    assert (code, out.splitlines()) == (1, ["Quarto       failed: BulbError: bulb command failed"])


def test_control_json_shape(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21")
    code, out, _ = _run(capsys, "bulb", "on", "quarto", "--json")
    assert json.loads(out) == {
        "results": [{"id": QUARTO, "name": "Quarto", "status": "ok", "reason": None}]
    }
    assert code == 0


def test_control_json_offline_and_failed(capsys, world) -> None:
    _inventory()
    world.add(QUARTO, WHITE_100, ip="192.168.0.21", key_rejected=True)
    code, out, _ = _run(capsys, "bulb", "on", "all", "--json")
    results = json.loads(out)["results"]
    assert results[0] == {
        "id": QUARTO,
        "name": "Quarto",
        "status": "failed",
        "reason": "local key or protocol rejected — re-import devices.json",
    }
    assert [entry["status"] for entry in results[1:]] == ["offline", "offline"]
    assert code == 1


# --- targets, inventory and remove (E2E-009, E2E-010, E2E-012) ----------------------


def test_e2e009_unknown_target(capsys, world) -> None:
    _inventory()
    code, out, err = _run(capsys, "bulb", "on", "cozinha")
    assert (code, out) == (2, "")
    assert err.strip() == "error: no bulb named 'cozinha'. Known: Quarto, Escritório, Sala"


def test_ambiguous_name(capsys, world) -> None:
    BulbInventory().save(
        [
            BulbRecord(id="eb1a00000000000000000011", name="Luz", key="k1", mac="10:d5:61:00:00:11"),
            BulbRecord(id="eb1a00000000000000000012", name="Luz", key="k2", mac="10:d5:61:00:00:12"),
        ]
    )
    code, out, err = _run(capsys, "bulb", "on", "luz")
    assert (code, out) == (2, "")
    assert err.strip() == (
        "error: 'luz' matches 2 bulbs; use the id: eb1a00000000000000000011, eb1a00000000000000000012"
    )


def test_e2e010_no_inventory(capsys, world) -> None:
    code, out, _ = _run(capsys, "bulb", "list")
    assert (code, out.splitlines()) == (0, NO_BULBS)
    code, out, _ = _run(capsys, "bulb", "status")
    assert (code, out.splitlines()) == (0, NO_BULBS)
    code, out, _ = _run(capsys, "bulb", "on", "sala")
    assert (code, out.splitlines()) == (1, NO_BULBS)
    code, out, _ = _run(capsys, "bulb", "remove", "sala")
    assert (code, out.splitlines()) == (1, NO_BULBS)


def test_e2e012_remove_transcript(capsys, world) -> None:
    _inventory()
    code, out, _ = _run(capsys, "bulb", "remove", "sala")
    assert out.strip() == _dx(
        ["Removed Sala (eb1a2b3c4d5e6f70819203) from /home/jilles/.config/avell-storm-rgb/tuya_devices.json"]
    )[0]
    assert code == 0
    assert [record.id for record in BulbInventory().load()] == [QUARTO, ESCRITORIO]
    assert world.opened == []  # remove never contacts a bulb


def test_e2e012_remove_all_is_argparse(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["bulb", "remove", "all"])
    assert excinfo.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_corrupt_inventory_exits_3(capsys, world, tmp_path) -> None:
    path = default_inventory_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{", encoding="utf-8")
    expected = f"error: bulb inventory is unreadable (invalid JSON at line 1 column 2): {path}"
    for argv in (
        ["bulb", "list"],
        ["bulb", "status"],
        ["bulb", "on", "sala"],
        ["bulb", "remove", "sala"],
        ["bulb", "import", str(FIXTURE)],
    ):
        code, out, err = _run(capsys, *argv)
        assert (code, out) == (3, ""), argv
        assert err.strip() == expected, argv


# --- no `tuya` extra (E2E-014) ------------------------------------------------------


def test_e2e014_without_extra_hint_and_help(capsys, monkeypatch) -> None:
    monkeypatch.setattr(bulb_cli, "tuya_available", lambda: False)
    for argv in (
        ["bulb", "import", "devices.json"],
        ["bulb", "list"],
        ["bulb", "status"],
        ["bulb", "status", "all", "--json"],
        ["bulb", "on", "sala"],
        ["bulb", "off", "all"],
        ["bulb", "toggle", "sala"],
        ["bulb", "bright", "40", "sala"],
        ["bulb", "white", "--temp", "20", "all"],
        ["bulb", "color", "1", "2", "3", "sala"],
        ["bulb", "remove", "sala"],
    ):
        code, out, err = _run(capsys, *argv)
        assert (code, out) == (1, ""), argv
        assert err.strip() == bulb_cli.NO_EXTRA_HINT, argv

    with pytest.raises(SystemExit) as excinfo:
        cli.main(["bulb", "-h"])
    assert excinfo.value.code == 0
    help_text = capsys.readouterr().out
    for verb in ("import", "list", "status", "on", "off", "toggle", "bright", "white", "color", "remove"):
        assert verb in help_text
