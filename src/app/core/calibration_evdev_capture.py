"""Linux evdev capture for calibration (exclusive grab bypasses compositor shortcuts)."""

from __future__ import annotations

import glob
import json
import select
import threading
import time
from pathlib import Path
from typing import Callable

try:
    import evdev
    from evdev import InputDevice, ecodes

    _EVDEV_AVAILABLE = True
except ImportError:
    _EVDEV_AVAILABLE = False

# #region agent log
_AGENT_DEBUG_LOG = Path("/home/jilles/.cursor/.cursor/debug-d917c9.log")


def _agent_debug_log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "d917c9",
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    try:
        with _AGENT_DEBUG_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    except OSError:
        pass


# #endregion


def evdev_available() -> bool:
    return _EVDEV_AVAILABLE


def _evdev_key_table() -> dict[int, str]:
    if not _EVDEV_AVAILABLE:
        return {}

    named: list[tuple[str, str]] = [
        ("KEY_ESC", "esc"),
        ("KEY_TAB", "tab"),
        ("KEY_CAPSLOCK", "caps_lock"),
        ("KEY_ENTER", "enter"),
        ("KEY_BACKSPACE", "backspace"),
        ("KEY_SPACE", "space"),
        ("KEY_DELETE", "delete"),
        ("KEY_INSERT", "insert"),
        ("KEY_HOME", "home"),
        ("KEY_END", "end"),
        ("KEY_PAGEUP", "page_up"),
        ("KEY_PAGEDOWN", "page_down"),
        ("KEY_PAUSE", "pause"),
        ("KEY_SCROLLLOCK", "scrlk"),
        ("KEY_PRINT", "prtsc"),
        ("KEY_SYSRQ", "prtsc"),
        ("KEY_NUMLOCK", "num_lock"),
        ("KEY_COMPOSE", "menu"),
        ("KEY_RIGHTMETA", "meta_left"),
        ("KEY_LEFTMETA", "meta_left"),
        ("KEY_UP", "up"),
        ("KEY_DOWN", "down"),
        ("KEY_LEFT", "left"),
        ("KEY_RIGHT", "right"),
        ("KEY_GRAVE", "grave"),
        ("KEY_MINUS", "minus"),
        ("KEY_EQUAL", "equal"),
        ("KEY_LEFTBRACE", "bracket_left"),
        ("KEY_RIGHTBRACE", "bracket_right"),
        ("KEY_BACKSLASH", "backslash"),
        ("KEY_102ND", "bracket_square"),
        ("KEY_SEMICOLON", "semicolon"),
        ("KEY_APOSTROPHE", "quote"),
        ("KEY_COMMA", "comma"),
        ("KEY_DOT", "dot"),
        ("KEY_SLASH", "slash"),
        ("KEY_LEFTSHIFT", "shift_left"),
        ("KEY_RIGHTSHIFT", "shift_right"),
        ("KEY_LEFTCTRL", "ctrl_left"),
        ("KEY_RIGHTCTRL", "ctrl_right"),
        ("KEY_LEFTALT", "alt_left"),
        ("KEY_RIGHTALT", "alt_right"),
        ("KEY_MUTE", "mute"),
        ("KEY_VOLUMEDOWN", "vol_down"),
        ("KEY_VOLUMEUP", "vol_up"),
        ("KEY_KPMINUS", "kp_minus"),
        ("KEY_KPPLUS", "kp_plus"),
        ("KEY_KPASTERISK", "kp_mul"),
        ("KEY_KPSLASH", "kp_div"),
        ("KEY_KPDOT", "kp_dot"),
        ("KEY_KPENTER", "kp_enter_top"),
    ]
    for index in range(1, 13):
        named.append((f"KEY_F{index}", f"f{index}"))
    for index in range(10):
        named.append((f"KEY_{index}", f"digit_{index}"))
    for index in range(10):
        named.append((f"KEY_KP{index}", f"kp_{index}"))
    for letter in "abcdefghijklmnopqrstuvwxyz":
        named.append((f"KEY_{letter.upper()}", letter))

    out: dict[int, str] = {}
    for ec_name, key_id in named:
        code = getattr(ecodes, ec_name, None)
        if code is not None:
            out[int(code)] = key_id
    return out


_EVDEV_KEY_TABLE = _evdev_key_table()


def evdev_code_to_key_id(code: int) -> str | None:
    from avell_storm_rgb.domain.physical_key_map import resolve_profile_key_id

    key_id = _EVDEV_KEY_TABLE.get(int(code))
    if key_id is None:
        return None
    return resolve_profile_key_id(key_id)


def _looks_like_keyboard(device: InputDevice) -> bool:
    caps = device.capabilities()
    keys = caps.get(ecodes.EV_KEY, [])
    return ecodes.KEY_A in keys and ecodes.KEY_ENTER in keys


def _is_internal_keyboard(device: InputDevice) -> bool:
    """Built-in PS/2 laptop keyboard (isa0060/serio0), not USB/BT externals."""

    phys = (device.phys or "").lower()
    name = (device.name or "").lower()
    return "serio0" in phys or "isa0060" in phys or "at translated set 2" in name


def _select_calibration_devices(candidates: list[InputDevice]) -> list[InputDevice]:
    """Prefer the laptop built-in keyboard when calibrating RGB on the internal matrix."""

    internal = [device for device in candidates if _is_internal_keyboard(device)]
    return internal if internal else candidates


def _discover_device_paths() -> list[str]:
    """``evdev.list_devices()`` can return empty on some systems; fall back to glob."""

    if not _EVDEV_AVAILABLE:
        return []
    paths = list(evdev.list_devices())
    if not paths:
        paths = sorted(glob.glob("/dev/input/event*"))
    return paths


def _permission_denied_message(open_errors: list[str]) -> str:
    return (
        "permission denied on /dev/input/event* — add your user to group 'input' "
        "(sudo usermod -aG input $USER), then log out and back in"
    )


class CalibrationEvdevCapture:
    """Read keyboard evdev nodes while calibration is listening."""

    def __init__(self, on_key_id: Callable[[str, int], None]) -> None:
        self._on_key_id = on_key_id
        self._devices: list[InputDevice] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._active = False
        self._exclusive = False
        self._last_error = ""
        self._open_errors: list[str] = []
        self._device_labels: list[str] = []

    @property
    def active(self) -> bool:
        return self._active

    @property
    def device_labels(self) -> list[str]:
        return list(self._device_labels)

    @property
    def exclusive(self) -> bool:
        return self._exclusive

    @property
    def last_error(self) -> str:
        return self._last_error

    def start(self) -> bool:
        if not _EVDEV_AVAILABLE or self._active:
            return self._active
        self._last_error = ""
        self._exclusive = False
        self._open_errors = []
        devices: list[InputDevice] = []
        open_errors: list[str] = []
        for path in _discover_device_paths():
            try:
                device = InputDevice(path)
            except PermissionError:
                open_errors.append(f"{path}: permission denied")
                continue
            except OSError as exc:
                open_errors.append(f"{path}: {exc}")
                continue
            if _looks_like_keyboard(device):
                devices.append(device)
        devices = _select_calibration_devices(devices)
        self._open_errors = open_errors
        if not devices:
            if open_errors and all("permission denied" in item for item in open_errors):
                self._last_error = _permission_denied_message(open_errors)
            elif open_errors:
                self._last_error = open_errors[-1]
            else:
                self._last_error = "no keyboard evdev device found"
            return False

        grabbed: list[InputDevice] = []
        grab_error = ""
        try:
            for device in devices:
                device.grab()
                grabbed.append(device)
            self._exclusive = True
        except (OSError, PermissionError) as exc:
            grab_error = str(exc)
            for device in grabbed:
                try:
                    device.ungrab()
                except OSError:
                    pass
            grabbed = devices
            self._exclusive = False
            self._last_error = f"exclusive grab failed ({exc}); using shared capture"

        self._devices = grabbed
        self._device_labels = [f"{device.name} ({device.path})" for device in grabbed]
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="calibration-evdev", daemon=True)
        self._thread.start()
        self._active = True
        # #region agent log
        _agent_debug_log(
            "H-S3",
            "calibration_evdev_capture.start",
            "devices_selected",
            {
                "count": len(self._devices),
                "exclusive": self._exclusive,
                "devices": self._device_labels,
                "internal_only": all(_is_internal_keyboard(d) for d in self._devices),
            },
        )
        # #endregion
        return True

    def stop(self) -> None:
        if not self._active and not self._devices:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._exclusive:
            for device in self._devices:
                try:
                    device.ungrab()
                except OSError:
                    pass
        self._devices = []
        self._active = False
        self._exclusive = False
        self._device_labels = []

    def _run(self) -> None:
        devices = self._devices
        while not self._stop.is_set() and devices:
            try:
                readable, _, _ = select.select(devices, [], [], 0.5)
            except OSError:
                break
            for device in readable:
                try:
                    events = device.read()
                except OSError:
                    continue
                for event in events:
                    if self._stop.is_set():
                        return
                    if event.type != ecodes.EV_KEY:
                        continue
                    # #region agent log
                    if event.value in (0, 1, 2):
                        key_name = ""
                        try:
                            key_name = ecodes.KEY[event.code]
                        except (KeyError, IndexError):
                            key_name = "?"
                        _agent_debug_log(
                            "H-S1",
                            "calibration_evdev_capture._run",
                            "evdev_raw_key",
                            {
                                "code": int(event.code),
                                "value": int(event.value),
                                "key_name": key_name,
                                "mapped_key_id": evdev_code_to_key_id(event.code),
                                "device": device.path,
                            },
                        )
                    # #endregion
                    if event.value != 1:
                        continue
                    key_id = evdev_code_to_key_id(event.code)
                    if key_id is not None:
                        self._on_key_id(key_id, int(event.code))
