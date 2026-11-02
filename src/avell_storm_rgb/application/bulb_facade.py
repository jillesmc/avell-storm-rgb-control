"""Open a Tuya bulb: optional-extra detection and IP resolution.

``open_bulb`` is the only way adapters get a :class:`BulbDriver`. It resolves the
IP in the order process cache → ARP by MAC → ``record.last_ip`` → UDP discovery,
and writes a changed IP back to the inventory. The returned driver is one fresh
:class:`TuyaBulb`; the caller owns its lifetime (one per bulb, ADR-003).

This module never imports ``tinytuya``: it only *names* it inside
``find_spec("tinytuya")`` so the surfaces can gate on the optional extra (BR-17).
"""

from __future__ import annotations

import importlib.util
import logging
import socket
import subprocess
from collections.abc import Callable, MutableMapping
from typing import TYPE_CHECKING

from avell_storm_rgb.application.bulb_inventory import BulbInventory, BulbRecord
from avell_storm_rgb.infrastructure.tuya.bulb import (
    BulbError,
    BulbUnreachable,
    Discovered,
    KeyRejected,
    TuyaBulb,
    discover_bulb,
)

if TYPE_CHECKING:
    from avell_storm_rgb.ports.protocols import BulbDriver

__all__ = [
    "BulbError",
    "BulbUnreachable",
    "Discovered",
    "KeyRejected",
    "arp_lookup",
    "open_bulb",
    "tuya_available",
]

_LOG = logging.getLogger("avell_storm_rgb.gui")

DEFAULT_DISCOVERY_TIMEOUT = 6.0
DEFAULT_PROBE_TIMEOUT = 1.5
TUYA_PORT = 6668

#: IPs that already answered in this process, by bulb id.
_IP_CACHE: dict[str, str] = {}


def tuya_available() -> bool:
    """True when the optional ``tuya`` extra is importable (BR-17, UT-033)."""
    return importlib.util.find_spec("tinytuya") is not None


def _parse_neigh(text: str) -> dict[str, str]:
    """``ip neigh`` output → ``{mac: ip}`` (lower-case MACs, entries with an lladdr)."""
    table: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            index = parts.index("lladdr")
        except ValueError:
            continue
        if index + 1 < len(parts):
            table[parts[index + 1].lower()] = parts[0]
    return table


def arp_lookup(mac: str) -> str | None:
    """IP for ``mac`` from the kernel neighbour table (read-only ``ip neigh``)."""
    if not mac:
        return None
    try:
        completed = subprocess.run(
            ["ip", "neigh"], capture_output=True, text=True, timeout=2, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return _parse_neigh(completed.stdout).get(mac.lower())


def _port_open(ip: str, timeout: float) -> bool:
    """True when something accepts a TCP connection on the Tuya LAN port."""
    try:
        with socket.create_connection((ip, TUYA_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def _new_driver(record: BulbRecord, ip: str) -> "BulbDriver":
    return TuyaBulb(record, ip)


def open_bulb(
    record: BulbRecord,
    inventory: BulbInventory,
    *,
    discover_timeout: float = DEFAULT_DISCOVERY_TIMEOUT,
    probe_timeout: float = DEFAULT_PROBE_TIMEOUT,
    cache: MutableMapping[str, str] | None = None,
    arp: Callable[[str], str | None] | None = None,
    discover: Callable[[str, float], Discovered | None] | None = None,
    probe: Callable[[str, float], bool] | None = None,
    driver_factory: Callable[[BulbRecord, str], "BulbDriver"] | None = None,
) -> "BulbDriver":
    """Resolve ``record`` on the LAN and return a fresh, unread :class:`BulbDriver`.

    Every candidate IP except the discovery result is probed on TCP 6668; the
    first one that answers wins. A different answering IP is written back with
    ``inventory.set_last_ip``. When nothing answers: :class:`BulbUnreachable`
    carrying the bulb name.
    """
    ips = _IP_CACHE if cache is None else cache
    arp_fn = arp_lookup if arp is None else arp
    discover_fn = discover_bulb if discover is None else discover
    probe_fn = _port_open if probe is None else probe
    factory = _new_driver if driver_factory is None else driver_factory

    def accept(ip: str, via: str, protocol: str = "") -> "BulbDriver":
        driver = factory(record, ip)
        ips[record.id] = ip
        if ip != record.last_ip:
            inventory.set_last_ip(record.id, ip)
        _LOG.debug(
            "bulb %s at %s protocol %s via %s",
            record.name,
            ip,
            protocol or record.protocol,
            via,
        )
        return driver

    tried: set[str] = set()

    def answers(ip: str | None) -> bool:
        if not ip or ip in tried:
            return False
        tried.add(ip)
        return probe_fn(ip, probe_timeout)

    cached = ips.get(record.id)
    if cached and answers(cached):
        return accept(cached, "cache")
    if cached is not None:
        ips.pop(record.id, None)

    arp_ip = arp_fn(record.mac) if record.mac else None
    if arp_ip and answers(arp_ip):
        return accept(arp_ip, "arp")

    last_ip = record.last_ip
    if last_ip and answers(last_ip):
        return accept(last_ip, "last_ip")

    found = discover_fn(record.id, discover_timeout)
    if found is not None and found.ip:
        return accept(found.ip, "discovery", found.protocol)

    raise BulbUnreachable(record.name)
