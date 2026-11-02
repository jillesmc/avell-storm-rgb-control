"""``infrastructure/tuya/bulb`` against a stub ``tinytuya.BulbDevice``.

No test here opens a socket: the stub stands in for the device and discovery is
always injected (UT-020–UT-028, UT-072, UT-073).
"""

from __future__ import annotations

import logging

import pytest

pytest.importorskip("tinytuya")

from avell_storm_rgb.application.bulb_inventory import BulbRecord
from avell_storm_rgb.domain.bulb_color import BulbStatus
from avell_storm_rgb.infrastructure.tuya.bulb import (
    BulbError,
    BulbUnreachable,
    Discovered,
    KeyRejected,
    TuyaBulb,
    discover_bulb,
)

BULB_ID = "eb1a2b3c4d5e6f70819202"
BULB_NAME = "Escritório"
KEY = "KEY-SENTINEL-123"
MAC = "10:d5:61:00:00:02"
IP = "192.168.0.22"

SENTINEL_ERROR = "SENTINEL-ERROR-TEXT"
SENTINEL_PAYLOAD = "SENTINEL-PAYLOAD-TEXT"

WHITE_STATUS = BulbStatus(on=True, mode="white", brightness=100, temperature=100, rgb=None)
RED_STATUS = BulbStatus(on=True, mode="colour", brightness=100, temperature=None, rgb=(255, 0, 0))


class StubBulbDevice:
    """Records every call and returns tinytuya-shaped dicts (never a socket)."""

    def __init__(self, *, dps=None, error=None, failures=None) -> None:
        self.dps = dict(dps or {})
        self.error = dict(error) if error is not None else None
        self.failures = list(failures or [])
        self.calls: list[tuple[str, tuple, dict]] = []
        self.status_reads = 0
        self.version = None
        self.socket_persistent = None
        self.socket_timeout = None
        self.retry = True
        self.closed = False
        self.pending: list[dict] = []

    # --- the tinytuya surface the adapter uses -----------------------------

    def status(self, nowait: bool = False) -> dict:
        self.status_reads += 1
        self.calls.append(("status", (), {"nowait": nowait}))
        return self._result(dict(self.dps))

    def set_multiple_values(self, data: dict, nowait: bool = False) -> dict:
        self.calls.append(("set_multiple_values", (dict(data),), {"nowait": nowait}))
        return self._result(dict(data))

    def receive(self):
        """Pending async frames on a persistent socket; ``None`` once drained."""
        self.calls.append(("receive", (), {"timeout": self.socket_timeout}))
        return self.pending.pop(0) if self.pending else None

    def set_socketTimeout(self, seconds: float) -> None:
        self.socket_timeout = seconds

    def set_socketPersistent(self, persistent: bool) -> None:
        self.socket_persistent = persistent

    def set_retry(self, retry: bool) -> None:
        self.retry = retry

    def set_version(self, version: float) -> None:
        self.version = version

    def close(self) -> None:
        self.closed = True

    # --- helpers -----------------------------------------------------------

    def _result(self, payload: dict) -> dict:
        if self.failures:
            failure = self.failures.pop(0)
            if isinstance(failure, BaseException):
                raise failure
            return dict(failure)
        if self.error is not None:
            return dict(self.error)
        return {"devId": BULB_ID, "dps": payload}

    @property
    def payloads(self) -> list[dict]:
        return [args[0] for name, args, _ in self.calls if name == "set_multiple_values"]

    @property
    def nowaits(self) -> list[bool]:
        return [kw["nowait"] for name, _, kw in self.calls if name == "set_multiple_values"]


def _record(**overrides) -> BulbRecord:
    data = {"id": BULB_ID, "name": BULB_NAME, "key": KEY, "mac": MAC, "protocol": "3.3"}
    data.update(overrides)
    return BulbRecord(**data)


def _no_discovery(bulb_id: str, timeout: float) -> None:
    return None


def _bulb(device: StubBulbDevice, discover=None, **record_overrides) -> TuyaBulb:
    return TuyaBulb(
        _record(**record_overrides),
        IP,
        device=device,
        discover=discover if discover is not None else _no_discovery,
    )


# --- DPS payloads (UT-020, UT-021, UT-022, UT-023, UT-024, UT-026) ----------


def test_set_brightness_in_white_mode_writes_dps_22() -> None:
    device = StubBulbDevice()

    _bulb(device).set_brightness(40, WHITE_STATUS)

    assert device.payloads == [{"20": True, "22": 400}]
    assert device.nowaits == [False]


def test_set_brightness_in_colour_mode_keeps_hue_and_sets_v() -> None:
    device = StubBulbDevice()

    _bulb(device).set_brightness(40, RED_STATUS)

    assert device.payloads == [{"20": True, "24": "000003e80190"}]


def test_set_white_writes_the_temperature_plus_ten() -> None:
    device = StubBulbDevice()

    _bulb(device).set_white(0, WHITE_STATUS)

    assert device.payloads == [{"20": True, "21": "white", "23": 0}]


def test_set_white_without_temperature_keeps_the_status_temperature() -> None:
    device = StubBulbDevice()
    status = BulbStatus(on=True, mode="white", brightness=50, temperature=20, rgb=None)

    _bulb(device).set_white(None, status)

    assert device.payloads == [{"20": True, "21": "white", "23": 200}]
    assert device.status_reads == 0


def test_set_white_without_any_temperature_omits_dps_23() -> None:
    device = StubBulbDevice()

    _bulb(device).set_white(None, None)

    assert device.payloads == [{"20": True, "21": "white"}]
    assert "23" not in device.payloads[0]
    assert device.status_reads == 0


def test_set_colour_writes_mode_and_colour_data() -> None:
    device = StubBulbDevice()

    _bulb(device).set_colour((255, 136, 0))

    assert device.payloads == [{"20": True, "21": "colour", "24": "002003e803e8"}]


def test_push_colour_never_writes_power_and_waits_for_its_echo() -> None:
    device = StubBulbDevice()

    _bulb(device).push_colour((0, 0, 255))

    assert device.payloads == [{"21": "colour", "24": "00f003e803e8"}]
    assert "20" not in device.payloads[0]
    assert device.nowaits == [False]  # consume the echo (hardware M-6)


def test_set_power_writes_dps_20_only() -> None:
    device = StubBulbDevice()

    _bulb(device).set_power(True)

    assert device.payloads == [{"20": True}]


# --- status reading (UT-027) ----------------------------------------------


@pytest.mark.parametrize(
    ("dps", "expected"),
    [
        ({"20": True, "21": "colour", "24": "000003e803e8"}, {"20": True, "24": "000003e80190"}),
        ({"20": True, "21": "white", "22": 1000}, {"20": True, "22": 400}),
    ],
)
def test_set_brightness_without_a_status_reads_once_on_the_same_driver(
    dps: dict, expected: dict
) -> None:
    device = StubBulbDevice(dps=dps)
    bulb = _bulb(device)

    bulb.set_brightness(40, None)

    assert device.status_reads == 1
    assert device.payloads == [expected]


def test_status_parses_the_dps_map() -> None:
    device = StubBulbDevice(dps={"20": True, "21": "colour", "24": "000003e803e8"})

    status = _bulb(device).status()

    assert status == BulbStatus(
        on=True, mode="colour", brightness=100, temperature=None, rgb=(255, 0, 0)
    )


# --- error mapping (UT-025, UT-028, UT-073) -------------------------------

CALLS = {
    "status": lambda bulb: bulb.status(),
    "set_power": lambda bulb: bulb.set_power(True),
    "set_brightness": lambda bulb: bulb.set_brightness(40, WHITE_STATUS),
    "set_white": lambda bulb: bulb.set_white(20, WHITE_STATUS),
    "set_colour": lambda bulb: bulb.set_colour((255, 136, 0)),
    "push_colour": lambda bulb: bulb.push_colour((0, 0, 255)),
}


@pytest.mark.parametrize("name", sorted(CALLS))
@pytest.mark.parametrize("code", [901, 902, 905])
def test_unreachable_error_codes_map_to_bulb_unreachable(name: str, code: int) -> None:
    device = StubBulbDevice(
        error={"Err": str(code), "Error": SENTINEL_ERROR, "Payload": SENTINEL_PAYLOAD}
    )

    with pytest.raises(BulbUnreachable) as exc:
        CALLS[name](_bulb(device))

    message = str(exc.value)
    assert message == "bulb is not reachable"
    assert SENTINEL_ERROR not in message
    assert SENTINEL_PAYLOAD not in message
    assert KEY not in message


@pytest.mark.parametrize("name", sorted(CALLS))
@pytest.mark.parametrize("code", [900, 903, 904, 906, 913])
def test_other_error_codes_map_to_bulb_error(name: str, code: int) -> None:
    device = StubBulbDevice(
        error={"Err": code, "Error": SENTINEL_ERROR, "Payload": SENTINEL_PAYLOAD}
    )

    with pytest.raises(BulbError) as exc:
        CALLS[name](_bulb(device))

    assert type(exc.value) is BulbError
    message = str(exc.value)
    assert message == "bulb command failed"
    assert SENTINEL_ERROR not in message
    assert SENTINEL_PAYLOAD not in message
    assert KEY not in message


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError("timed out"),
        ConnectionRefusedError("refused"),
        ConnectionResetError("reset"),
    ],
)
def test_transport_errors_map_to_bulb_unreachable(failure: BaseException) -> None:
    device = StubBulbDevice(failures=[failure])

    with pytest.raises(BulbUnreachable) as exc:
        _bulb(device).status()

    assert str(exc.value) == "bulb is not reachable"
    assert str(failure) not in str(exc.value)


def test_unexpected_errors_map_to_bulb_error() -> None:
    device = StubBulbDevice(failures=[RuntimeError(SENTINEL_ERROR)])

    with pytest.raises(BulbError) as exc:
        _bulb(device).status()

    assert type(exc.value) is BulbError
    assert SENTINEL_ERROR not in str(exc.value)


def test_key_rejected_message_is_the_fixed_phrase() -> None:
    device = StubBulbDevice(
        error={"Err": "914", "Error": SENTINEL_ERROR, "Payload": SENTINEL_PAYLOAD}
    )
    discoveries: list[tuple[str, float]] = []

    with pytest.raises(KeyRejected) as exc:
        _bulb(device, discover=lambda i, t: discoveries.append((i, t)) or None).set_colour(
            (255, 136, 0)
        )

    assert str(exc.value) == "local key or protocol rejected"
    assert len(discoveries) == 1
    assert SENTINEL_ERROR not in str(exc.value)
    assert SENTINEL_PAYLOAD not in str(exc.value)
    assert KEY not in str(exc.value)


# --- 914 retry (UT-028) ---------------------------------------------------


def test_914_retries_once_with_a_different_discovered_protocol() -> None:
    device = StubBulbDevice(failures=[{"Err": "914"}])
    discoveries: list[tuple[str, float]] = []

    def discover(bulb_id: str, timeout: float) -> Discovered:
        discoveries.append((bulb_id, timeout))
        return Discovered(IP, "3.5")

    bulb = _bulb(device, discover=discover)

    bulb.set_power(True)

    assert discoveries == [(BULB_ID, 6.0)]
    assert device.payloads == [{"20": True}, {"20": True}]  # one failed attempt, one retry
    assert device.version == 3.5
    assert bulb.protocol == "3.5"


@pytest.mark.parametrize("discovered", [None, Discovered(IP, "3.3"), Discovered(IP, "")])
def test_914_without_a_different_protocol_raises_key_rejected(discovered) -> None:
    device = StubBulbDevice(error={"Err": "914"})
    calls: list[tuple[str, float]] = []

    def discover(bulb_id: str, timeout: float):
        calls.append((bulb_id, timeout))
        return discovered

    with pytest.raises(KeyRejected) as exc:
        _bulb(device, discover=discover).set_power(True)

    assert str(exc.value) == "local key or protocol rejected"
    assert len(calls) == 1
    assert len(device.payloads) == 1  # one attempt, no retry


def test_914_retry_that_also_fails_raises_key_rejected() -> None:
    device = StubBulbDevice(failures=[{"Err": "914"}, {"Err": "914"}])
    discoveries: list[str] = []

    def discover(bulb_id: str, timeout: float) -> Discovered:
        discoveries.append(bulb_id)
        return Discovered(IP, "3.5")

    with pytest.raises(KeyRejected):
        _bulb(device, discover=discover).status()

    assert discoveries == [BULB_ID]
    assert device.status_reads == 2


# --- privacy (UT-072, UT-073) and delegation ------------------------------


def test_tuya_bulb_repr_and_str_never_contain_the_key() -> None:
    bulb = _bulb(StubBulbDevice())

    for text in (repr(bulb), str(bulb)):
        assert KEY not in text
        assert BULB_NAME in text
        assert BULB_ID in text


def test_hold_open_and_close_delegate_to_the_device() -> None:
    device = StubBulbDevice()
    bulb = _bulb(device)

    bulb.hold_open(True)
    assert device.socket_persistent is True

    bulb.hold_open(False)
    assert device.socket_persistent is False

    bulb.close()
    assert device.closed is True


# --- lazy import and logger pin (M3) --------------------------------------


def test_adapter_pins_the_tinytuya_logger_and_never_enables_debug(monkeypatch) -> None:
    import tinytuya

    def spy(*args, **kwargs):
        raise AssertionError("tinytuya.set_debug() must never be called")

    monkeypatch.setattr(tinytuya, "set_debug", spy, raising=False)
    logging.getLogger("tinytuya").setLevel(logging.DEBUG)

    TuyaBulb(_record(), IP)  # builds a real BulbDevice; the constructor opens no socket

    assert logging.getLogger("tinytuya").level == logging.WARNING


def test_discover_bulb_reads_the_ip_and_protocol(monkeypatch) -> None:
    import tinytuya

    seen: list[dict] = []

    def fake_device_scan(**kwargs):
        seen.append(kwargs)
        return {BULB_ID: {"ip": "192.168.0.23", "version": "3.3"}}

    monkeypatch.setattr(tinytuya, "deviceScan", fake_device_scan)

    assert discover_bulb(BULB_ID, 0.5) == Discovered("192.168.0.23", "3.3")
    assert seen[0]["poll"] is False
    assert seen[0]["byID"] is True
    assert seen[0]["maxretry"] == 0.5


def test_discover_bulb_returns_none_when_the_id_does_not_answer(monkeypatch) -> None:
    import tinytuya

    monkeypatch.setattr(tinytuya, "deviceScan", lambda **kwargs: {})
    assert discover_bulb(BULB_ID, 0.1) is None


def test_discover_bulb_swallows_discovery_failures(monkeypatch) -> None:
    import tinytuya

    def boom(**kwargs):
        raise OSError("no broadcast")

    monkeypatch.setattr(tinytuya, "deviceScan", boom)
    assert discover_bulb(BULB_ID, 0.1) is None


# --- status after follow pushes (hardware finding M-6) -----------------------
#
# Measured on the real bulb: after a few follow pushes, the frame read right after a
# status query was a partial update (21/24), then nothing, then the full reply.

PARTIAL = {"devId": BULB_ID, "dps": {"21": "colour", "24": "000003e803e8"}}
FULL = {"20": True, "21": "colour", "22": 1000, "24": "000003e803e8"}


def test_status_reads_on_past_partial_frames() -> None:
    device = StubBulbDevice(dps=FULL)
    device.failures = [PARTIAL]  # the query's first frame is a partial update
    device.pending = [PARTIAL, PARTIAL, {"devId": BULB_ID, "dps": dict(FULL)}]
    assert _bulb(device).status().on is True
    assert device.status_reads == 1  # no extra query while frames keep coming
    assert device.socket_timeout == 5.0  # restored


def test_status_resends_once_when_the_socket_goes_quiet() -> None:
    device = StubBulbDevice(dps=FULL)
    device.failures = [PARTIAL]
    assert _bulb(device).status().on is True
    assert device.status_reads == 2


def test_status_gives_up_when_power_never_arrives(monkeypatch) -> None:
    from avell_storm_rgb.infrastructure.tuya import bulb as tuya_bulb

    monkeypatch.setattr(tuya_bulb, "STATUS_DEADLINE", 0.05)
    device = StubBulbDevice(dps={"21": "colour"})  # never carries DPS 20
    with pytest.raises(BulbError):
        _bulb(device).status()
