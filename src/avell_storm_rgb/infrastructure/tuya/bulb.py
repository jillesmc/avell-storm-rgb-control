"""Tuya LAN bulb adapter: the only code that imports ``tinytuya``.

``tinytuya`` is imported lazily inside the functions that need it, so
``import avell_storm_rgb`` and the CLI keep working without the optional
``tuya`` extra (ADR-001).

tinytuya never raises for device errors: every call returns
``{"Err", "Error", "Payload"}``. This module maps ``Err`` to
:class:`KeyRejected`, :class:`BulbUnreachable` or :class:`BulbError` and only
ever puts a fixed phrase in the message, so neither the payload nor the local
key can leak into a log line, a signal or the CLI (BR-3, M2).

Writes go through ``set_multiple_values`` with explicit DPS, because
tinytuya's ``set_colour``/``set_white`` add ``switch: True`` and would break
BR-12 (KD-6).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from avell_storm_rgb.domain.bulb_color import (
    BulbStatus,
    percent_to_device,
    rgb_to_colour_data_v2,
    status_from_dps,
)

if TYPE_CHECKING:
    from avell_storm_rgb.application.bulb_inventory import BulbRecord

__all__ = [
    "BulbError",
    "BulbUnreachable",
    "Discovered",
    "KeyRejected",
    "TuyaBulb",
    "discover_bulb",
]

_LOG = logging.getLogger("avell_storm_rgb.tuya")

COMMAND_TIMEOUT = 5.0
DISCOVERY_TIMEOUT = 6.0
DEFAULT_PROTOCOL = "3.3"

# tinytuya error codes (core/error_helper.py). Err is a *string* in its dicts.
ERR_KEY_OR_PROTOCOL = 914
ERR_UNREACHABLE = frozenset({901, 902, 905})

MSG_KEY_REJECTED = "local key or protocol rejected"
MSG_UNREACHABLE = "bulb is not reachable"
MSG_FAILED = "bulb command failed"

_NO_RESULT = object()


class BulbError(Exception):
    """A bulb operation failed; the message never contains a key or a payload."""


class BulbUnreachable(BulbError):
    """The bulb did not answer: offline, timed out, or no IP resolved."""


class KeyRejected(BulbError):
    """The bulb rejected the local key or the protocol version."""


@dataclass(frozen=True)
class Discovered:
    """A bulb that answered a UDP broadcast."""

    ip: str
    protocol: str = ""  # "" when the device did not report a version


def _tinytuya() -> Any:
    """Import tinytuya lazily and pin its logger (M3).

    tinytuya's own debug switch is never enabled: it raises the root logger to
    DEBUG and tinytuya logs the local key in clear at that level (ADR-001).
    """
    import tinytuya

    logging.getLogger("tinytuya").setLevel(logging.WARNING)
    return tinytuya


def _version_float(protocol: object) -> float:
    """``"3.3"``/``3.3``/``None`` → a float tinytuya accepts; default ``3.3``."""
    try:
        return float(protocol)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return float(DEFAULT_PROTOCOL)


def discover_bulb(bulb_id: str, timeout: float = DISCOVERY_TIMEOUT) -> Discovered | None:
    """One UDP broadcast round (ports 6666/6667); ``None`` when the id did not answer.

    Best effort by design: a firewalled UDP port must fall through to the next
    resolution step, not fail the command (ADR-003 risk note).
    """
    tinytuya = _tinytuya()
    try:
        found = tinytuya.deviceScan(
            verbose=False, maxretry=timeout, poll=False, byID=True
        )
    except Exception as exc:  # noqa: BLE001 - discovery never raises to the caller
        _LOG.debug("bulb discovery failed: %s", type(exc).__name__)
        return None
    entry = found.get(bulb_id) if isinstance(found, dict) else None
    if not isinstance(entry, dict):
        return None
    ip = entry.get("ip")
    if not isinstance(ip, str) or not ip:
        return None
    version = entry.get("version")
    protocol = str(version) if isinstance(version, (str, int, float)) and version else ""
    return Discovered(ip=ip, protocol=protocol)


#: ``status()`` keeps reading frames for its full reply this long (hardware M-6).
STATUS_DEADLINE = 3.0
#: Socket timeout while waiting for the next frame of that reply.
RECEIVE_TIMEOUT = 0.25


def _dps_of(result: Any) -> Mapping[str, Any]:
    if isinstance(result, dict):
        dps = result.get("dps")
        if isinstance(dps, dict):
            return dps
    return {}


def _err_of(result: Any) -> int | None:
    """The ``Err`` code of a tinytuya return value; ``None`` on success."""
    if not isinstance(result, dict):
        return None
    err = result.get("Err")
    if err is None or isinstance(err, bool):
        return None
    try:
        return int(err) or None
    except (TypeError, ValueError):
        return None


def _temperature_value(percent: int) -> int:
    """Map 0–100 % white temperature to the device range 0–1000 (0 = warmest)."""
    if not 0 <= percent <= 100:
        raise ValueError(f"temperature must be 0–100, got {percent}")
    return percent * 10


def _colour_with_value(rgb: tuple[int, int, int], value: int) -> str:
    """``colour_data_v2`` with the hue/saturation of ``rgb`` and an explicit V."""
    hue_and_saturation = rgb_to_colour_data_v2(rgb)[:8]
    return f"{hue_and_saturation}{max(0, min(1000, value)):04x}"


def _new_device(record: "BulbRecord", ip: str, timeout: float) -> Any:
    tinytuya = _tinytuya()
    device = tinytuya.BulbDevice(
        record.id, ip, record.key, version=_version_float(record.protocol)
    )
    device.set_socketTimeout(timeout)
    device.set_socketPersistent(False)
    device.set_retry(False)  # one attempt per command, no retry storm
    return device


class TuyaBulb:
    """One Tuya bulb over the LAN protocol; one driver per bulb (ADR-003).

    The local key stays inside this object: ``repr``/``str`` render the name, the
    id, the IP and the protocol only (BR-3, UT-072).
    """

    def __init__(
        self,
        record: "BulbRecord",
        ip: str,
        *,
        device: Any | None = None,
        discover: Callable[[str, float], Discovered | None] | None = None,
        command_timeout: float = COMMAND_TIMEOUT,
        discovery_timeout: float = DISCOVERY_TIMEOUT,
    ) -> None:
        self._id = record.id
        self._name = record.name
        self._protocol = record.protocol or DEFAULT_PROTOCOL
        self._ip = ip
        self._discover = discover if discover is not None else discover_bulb
        self._discovery_timeout = discovery_timeout
        self._command_timeout = command_timeout
        self._device = (
            device if device is not None else _new_device(record, ip, command_timeout)
        )

    def __repr__(self) -> str:
        return (
            f"TuyaBulb(name={self._name!r}, id={self._id!r}, ip={self._ip!r}, "
            f"protocol={self._protocol!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    @property
    def name(self) -> str:
        return self._name

    @property
    def bulb_id(self) -> str:
        return self._id

    @property
    def ip(self) -> str:
        return self._ip

    @property
    def protocol(self) -> str:
        return self._protocol

    # --- BulbDriver ---------------------------------------------------------

    def status(self) -> BulbStatus:
        """A full status reply (it carries DPS 20).

        On the persistent follow socket the bulb answers each push with an ack *and* an
        async partial update (21/24, no 20), late and in any order, so the frame read
        right after a query is often not its reply (hardware M-6). Read on until the full
        reply arrives; re-send the query once if the socket goes quiet.
        """
        dps = _dps_of(self._call("status", self._device.status))
        if "20" in dps:
            return status_from_dps(dps)
        deadline = time.monotonic() + STATUS_DEADLINE
        resent = False
        while time.monotonic() < deadline:
            self._device.set_socketTimeout(RECEIVE_TIMEOUT)
            try:
                frame = self._call("status", self._device.receive)
            finally:
                self._device.set_socketTimeout(self._command_timeout)
            dps = _dps_of(frame)
            if "20" in dps:
                return status_from_dps(dps)
            if frame is None and not resent:
                resent = True
                dps = _dps_of(self._call("status", self._device.status))
                if "20" in dps:
                    return status_from_dps(dps)
            _LOG.debug("bulb %s: skipped a partial status reply", self._id)
        raise BulbError(MSG_FAILED)

    def set_power(self, on: bool) -> None:
        self._write("set_power", {"20": bool(on)})

    def set_brightness(self, percent: int, status: BulbStatus | None = None) -> None:
        if status is None:
            # One extra round trip on the same driver: no second connection (BR-11).
            status = self.status()
        value = percent_to_device(percent)
        if status.mode == "colour" and status.rgb is not None:
            self._write(
                "set_brightness",
                {"20": True, "24": _colour_with_value(status.rgb, value)},
            )
            return
        self._write("set_brightness", {"20": True, "22": value})

    def set_white(
        self, temperature_percent: int | None = None, status: BulbStatus | None = None
    ) -> None:
        temperature = temperature_percent
        if temperature is None and status is not None:
            temperature = status.temperature
        dps: dict[str, Any] = {"20": True, "21": "white"}
        if temperature is not None:
            dps["23"] = _temperature_value(temperature)
        self._write("set_white", dps)

    def set_colour(self, rgb: tuple[int, int, int]) -> None:
        self._write(
            "set_colour", {"20": True, "21": "colour", "24": rgb_to_colour_data_v2(rgb)}
        )

    def push_colour(self, rgb: tuple[int, int, int]) -> None:
        # Following never writes DPS 20 (BR-12, KD-6). It *waits* for the bulb's echo
        # (20–130 ms, inside the 250 ms follow tick): unread echoes piled up on the
        # persistent socket and later reads/commands consumed them (hardware M-6).
        self._write("push_colour", {"21": "colour", "24": rgb_to_colour_data_v2(rgb)})

    def hold_open(self, persistent: bool) -> None:
        self._device.set_socketPersistent(bool(persistent))

    def close(self) -> None:
        self._device.close()

    # --- internals ---------------------------------------------------------

    def _write(self, label: str, dps: dict[str, Any], *, nowait: bool = False) -> None:
        self._call(label, self._device.set_multiple_values, dps, nowait=nowait)

    def _call(self, label: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        result = self._invoke(label, fn, args, kwargs)
        err = _err_of(result)
        if err is None:
            return result
        if err == ERR_KEY_OR_PROTOCOL:
            retried = self._retry_with_discovered_version(label, fn, args, kwargs)
            if retried is not _NO_RESULT:
                return retried
            raise KeyRejected(MSG_KEY_REJECTED)
        if err in ERR_UNREACHABLE:
            _LOG.debug("bulb %s: %s did not answer (Err %s)", self._id, label, err)
            raise BulbUnreachable(MSG_UNREACHABLE)
        _LOG.debug("bulb %s: %s failed (Err %s)", self._id, label, err)
        raise BulbError(MSG_FAILED)

    def _invoke(
        self,
        label: str,
        fn: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        try:
            return fn(*args, **kwargs)
        except OSError as exc:  # socket timeouts, refused or reset connections
            _LOG.debug("bulb %s: %s raised %s", self._id, label, type(exc).__name__)
            raise BulbUnreachable(MSG_UNREACHABLE) from None
        except Exception as exc:  # noqa: BLE001 - never surface tinytuya's text
            _LOG.debug("bulb %s: %s raised %s", self._id, label, type(exc).__name__)
            raise BulbError(MSG_FAILED) from None

    def _retry_with_discovered_version(
        self,
        label: str,
        fn: Callable[..., Any],
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        """One UDP discovery, one retry, only when the version actually differs (M2)."""
        found = self._discover(self._id, self._discovery_timeout)
        if found is None or not found.protocol:
            return _NO_RESULT
        if _version_float(found.protocol) == _version_float(self._protocol):
            return _NO_RESULT
        self._protocol = found.protocol
        self._device.set_version(_version_float(found.protocol))
        _LOG.debug("bulb %s: retrying %s with protocol %s", self._id, label, found.protocol)
        try:
            result = self._invoke(label, fn, args, kwargs)
        except BulbError:
            return _NO_RESULT
        return result if _err_of(result) is None else _NO_RESULT
