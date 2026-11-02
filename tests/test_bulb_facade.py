"""``application/bulb_facade``: IP resolution order, write-back and the extra gate.

No test here opens a socket or runs ``ip neigh``: the probe, the ARP lookup and
the discovery callable are injected (UT-030–UT-033).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess

import pytest

from avell_storm_rgb.application.bulb_facade import (
    BulbUnreachable,
    Discovered,
    arp_lookup,
    open_bulb,
    tuya_available,
)
from avell_storm_rgb.application.bulb_inventory import BulbInventory, BulbRecord
from avell_storm_rgb.domain.bulb_color import BulbStatus
from avell_storm_rgb.ports.protocols import BulbDriver

BULB_ID = "eb1a2b3c4d5e6f70819202"
KEY = "KEY-SENTINEL-123"
MAC = "10:d5:61:00:00:02"

BASE = {
    "id": BULB_ID,
    "name": "Escritório",
    "key": KEY,
    "mac": MAC,
    "protocol": "3.3",
    "last_ip": "192.168.0.22",
}


class FakeDriver:
    """Minimal ``BulbDriver`` for resolution tests; never talks to a device."""

    def __init__(self, record: BulbRecord, ip: str) -> None:
        self.record = record
        self.ip = ip
        self.closed = False

    def status(self) -> BulbStatus:
        return BulbStatus(on=False, mode="white", brightness=100, temperature=100, rgb=None)

    def set_power(self, on: bool) -> None: ...

    def set_brightness(self, percent: int, status: BulbStatus | None) -> None: ...

    def set_white(self, temperature_percent: int | None, status: BulbStatus | None) -> None: ...

    def set_colour(self, rgb: tuple[int, int, int]) -> None: ...

    def push_colour(self, rgb: tuple[int, int, int]) -> None: ...

    def hold_open(self, persistent: bool) -> None: ...

    def close(self) -> None:
        self.closed = True


class SpyInventory:
    """Records the write-backs and delegates them to a real inventory."""

    def __init__(self, real: BulbInventory) -> None:
        self.real = real
        self.written: list[tuple[str, str]] = []

    def set_last_ip(self, bulb_id: str, ip: str) -> None:
        self.written.append((bulb_id, ip))
        self.real.set_last_ip(bulb_id, ip)


def _inventory(tmp_path, **overrides) -> tuple[SpyInventory, BulbRecord]:
    real = BulbInventory(tmp_path / "tuya_devices.json")
    record = BulbRecord(**{**BASE, **overrides})
    real.save([record])
    return SpyInventory(real), record


def _factory(created: list[FakeDriver]):
    def make(record: BulbRecord, ip: str) -> FakeDriver:
        driver = FakeDriver(record, ip)
        created.append(driver)
        return driver

    return make


def _no_arp(mac: str) -> None:
    return None


# --- IP resolution order (UT-030, UT-031) ---------------------------------


def test_arp_answer_is_used_and_discovery_is_not_called(tmp_path) -> None:
    inventory, record = _inventory(tmp_path, last_ip=None)
    created: list[FakeDriver] = []
    discovered: list[str] = []
    probed: list[str] = []

    def probe(ip: str, timeout: float) -> bool:
        probed.append(ip)
        return ip == "192.168.0.22"

    driver = open_bulb(
        record,
        inventory,
        cache={},
        arp=lambda mac: "192.168.0.22",
        probe=probe,
        discover=lambda bulb_id, timeout: discovered.append(bulb_id),
        driver_factory=_factory(created),
    )

    assert isinstance(driver, BulbDriver)
    assert driver.ip == "192.168.0.22"
    assert probed == ["192.168.0.22"]
    assert discovered == []
    assert inventory.written == [(BULB_ID, "192.168.0.22")]
    assert inventory.real.load()[0].last_ip == "192.168.0.22"


def test_discovery_answer_is_used_and_written_back(tmp_path) -> None:
    inventory, record = _inventory(tmp_path)  # last_ip 192.168.0.22
    probed: list[str] = []

    def probe(ip: str, timeout: float) -> bool:
        probed.append(ip)
        return False  # ARP miss, last_ip does not answer

    driver = open_bulb(
        record,
        inventory,
        cache={},
        arp=_no_arp,
        probe=probe,
        discover=lambda bulb_id, timeout: Discovered("192.168.0.23", "3.3"),
        driver_factory=_factory([]),
    )

    assert driver.ip == "192.168.0.23"
    assert probed == ["192.168.0.22"]
    assert inventory.written == [(BULB_ID, "192.168.0.23")]
    assert inventory.real.load()[0].last_ip == "192.168.0.23"


def test_unchanged_last_ip_is_not_written_back(tmp_path) -> None:
    inventory, record = _inventory(tmp_path)  # last_ip 192.168.0.22

    driver = open_bulb(
        record,
        inventory,
        cache={},
        arp=_no_arp,
        probe=lambda ip, timeout: ip == "192.168.0.22",
        discover=lambda bulb_id, timeout: pytest.fail("discovery must not run"),
        driver_factory=_factory([]),
    )

    assert driver.ip == "192.168.0.22"
    assert inventory.written == []
    assert inventory.real.load()[0].last_ip == "192.168.0.22"


def test_process_cache_is_used_before_arp(tmp_path) -> None:
    inventory, record = _inventory(tmp_path)
    cache = {BULB_ID: "192.168.0.31"}
    arp_calls: list[str] = []

    driver = open_bulb(
        record,
        inventory,
        cache=cache,
        arp=lambda mac: arp_calls.append(mac),
        probe=lambda ip, timeout: ip == "192.168.0.31",
        discover=lambda bulb_id, timeout: pytest.fail("discovery must not run"),
        driver_factory=_factory([]),
    )

    assert driver.ip == "192.168.0.31"
    assert arp_calls == []
    assert cache == {BULB_ID: "192.168.0.31"}
    assert inventory.written == [(BULB_ID, "192.168.0.31")]


def test_stale_cache_entry_falls_through_to_last_ip(tmp_path) -> None:
    inventory, record = _inventory(tmp_path)  # last_ip 192.168.0.22
    cache = {BULB_ID: "192.168.0.30"}

    driver = open_bulb(
        record,
        inventory,
        cache=cache,
        arp=_no_arp,
        probe=lambda ip, timeout: ip == "192.168.0.22",
        discover=lambda bulb_id, timeout: pytest.fail("discovery must not run"),
        driver_factory=_factory([]),
    )

    assert driver.ip == "192.168.0.22"
    assert cache == {BULB_ID: "192.168.0.22"}


def test_write_back_lands_in_the_default_inventory_in_the_temp_xdg_config() -> None:
    inventory = BulbInventory()  # $XDG_CONFIG_HOME, pinned to a temp dir by conftest
    record = BulbRecord(**{**BASE, "last_ip": None})
    inventory.save([record])

    driver = open_bulb(
        record,
        inventory,
        cache={},
        arp=lambda mac: "192.168.0.22",
        probe=lambda ip, timeout: True,
        discover=lambda bulb_id, timeout: pytest.fail("discovery must not run"),
        driver_factory=_factory([]),
    )

    assert driver.ip == "192.168.0.22"
    assert str(inventory.path).startswith(os.environ["XDG_CONFIG_HOME"])
    assert inventory.load()[0].last_ip == "192.168.0.22"


def test_arp_and_last_ip_are_probed_only_once(tmp_path) -> None:
    """ARP and ``last_ip`` returning the same address must not double-probe."""
    inventory, record = _inventory(tmp_path)  # last_ip 192.168.0.22
    probed: list[str] = []

    with pytest.raises(BulbUnreachable):
        open_bulb(
            record,
            inventory,
            cache={},
            arp=lambda mac: "192.168.0.22",
            probe=lambda ip, timeout: probed.append(ip) or False,
            discover=lambda bulb_id, timeout: None,
            driver_factory=_factory([]),
        )

    assert probed == ["192.168.0.22"]


# --- exhausted resolution (UT-032) ----------------------------------------

def test_open_bulb_raises_the_bulb_name_when_every_step_misses(tmp_path) -> None:
    inventory, record = _inventory(tmp_path, name="Sala", last_ip=None)

    with pytest.raises(BulbUnreachable) as exc:
        open_bulb(
            record,
            inventory,
            cache={},
            arp=_no_arp,
            probe=lambda ip, timeout: False,
            discover=lambda bulb_id, timeout: None,
            driver_factory=_factory([]),
        )

    assert str(exc.value) == "Sala"
    assert inventory.written == []


# --- optional extra detection (UT-033) ------------------------------------


def test_tuya_available_follows_find_spec(monkeypatch) -> None:
    real_find_spec = importlib.util.find_spec

    def without_tinytuya(name: str, *args, **kwargs):
        return None if name == "tinytuya" else real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", without_tinytuya)
    assert tuya_available() is False

    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a, **k: object())
    assert tuya_available() is True


# --- ARP lookup -----------------------------------------------------------


def test_arp_lookup_maps_the_mac_from_ip_neigh(monkeypatch) -> None:
    output = (
        "192.168.0.22 dev wlan0 lladdr 10:D5:61:00:00:02 REACHABLE\n"
        "192.168.0.50 dev wlan0  FAILED\n"
        "192.168.0.60 dev wlan0 lladdr 10:d5:61:00:00:60 STALE\n"
    )

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=output, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert arp_lookup("10:d5:61:00:00:02") == "192.168.0.22"
    assert arp_lookup("10:D5:61:00:00:60") == "192.168.0.60"
    assert arp_lookup("10:d5:61:00:00:99") is None
    assert arp_lookup("") is None


def test_arp_lookup_survives_a_missing_ip_command(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise FileNotFoundError("ip")

    monkeypatch.setattr(subprocess, "run", boom)

    assert arp_lookup(MAC) is None
