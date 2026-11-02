"""Saved device state: remembered devices, light state and last applied look.

Qt-free on purpose: the GUI writes ``state.json`` and the CLI reads it
(``avell-storm-rgb state show|restore``). Only the GUI thread may call
:meth:`DeviceStateStore.save`; restore functions never write the file.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Union

from avell_storm_rgb.domain.ledbar_colors import MAX_LED_BAR_PALETTE
from avell_storm_rgb.infrastructure.usb.ite8233_usb import LED_BAR_EFFECT_CODES
from avell_storm_rgb.infrastructure.usb.ite8291_usb import (
    KEYBOARD_DIRECTIONS,
    KEYBOARD_EFFECT_PARAMS,
    KEYBOARD_EFFECTS,
    KEYBOARD_PALETTE_SLOT_COLORS,
    NUM_COLS,
    NUM_ROWS,
    keyboard_effect_kwargs,
)

if TYPE_CHECKING:
    from avell_storm_rgb.ports.protocols import KeyboardRgbDriver, LedBarDriver

DeviceKind = Literal["keyboard", "led_bar"]
Power = Literal["on", "off"]
RGB = tuple[int, int, int]
Follow = Literal["none", "keyboard", "screen", "led_bar"]

#: Order is part of the public validation message (``_dx.md``), so it is not sorted.
FOLLOW_VALUES: tuple[Follow, ...] = ("none", "keyboard", "screen", "led_bar")

STATE_VERSION = 1
STATE_FILENAME = "state.json"


@dataclass(frozen=True)
class FirmwareEffectLook:
    effect: str
    speed: int
    brightness: int
    color: str
    direction: str
    reactive: bool
    save: bool


@dataclass(frozen=True)
class SolidLook:
    rgb: RGB


@dataclass(frozen=True)
class PerKeyLook:
    cells: tuple[tuple[int, int, RGB], ...]  # (device_row, col, rgb); device row 0 = bottom


@dataclass(frozen=True)
class AnimationLook:
    path: str
    loops: int
    forever: bool


KeyboardLook = Union[FirmwareEffectLook, SolidLook, PerKeyLook, AnimationLook]


@dataclass(frozen=True)
class LedBarLook:
    palette: tuple[RGB, ...]
    effect: str
    brightness: int
    speed: int


@dataclass(frozen=True)
class KeyboardState:
    usb_id: str
    remembered: bool = True
    power: Power = "on"
    brightness: int | None = None
    palette: dict[int, RGB] = field(default_factory=dict)
    look: KeyboardLook | None = None


@dataclass(frozen=True)
class LedBarState:
    usb_id: str
    remembered: bool = True
    power: Power = "on"
    look: LedBarLook | None = None


@dataclass(frozen=True)
class BulbState:
    """One saved bulb: remembered in the sidebar and the follow source (BR-15)."""

    id: str
    remembered: bool = True
    follow: Follow = "none"


@dataclass(frozen=True)
class DeviceState:
    keyboard: KeyboardState | None = None
    led_bar: LedBarState | None = None
    bulbs: tuple[BulbState, ...] = ()  # sorted by id

    def __post_init__(self) -> None:
        object.__setattr__(self, "bulbs", tuple(sorted(self.bulbs, key=lambda b: b.id)))


class StateFileError(Exception):
    """state.json exists but cannot be used (parse error, schema violation, unknown version)."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(f"{reason}: {path}")
        self.path = path
        self.reason = reason


# --- (de)serialisation -------------------------------------------------------

_USB_ID = re.compile(r"^[0-9a-f]{4}:[0-9a-f]{4}$")


def _int(v: Any, where: str, lo: int, hi: int) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"{where} must be an integer, got {v!r}")
    if not lo <= v <= hi:
        raise ValueError(f"{where} must be {lo}–{hi}, got {v}")
    return v


def _bool(v: Any, where: str) -> bool:
    if not isinstance(v, bool):
        raise ValueError(f"{where} must be true or false, got {v!r}")
    return v


def _choice(v: Any, where: str, allowed) -> str:
    if v not in allowed:
        raise ValueError(f"{where} must be one of {', '.join(sorted(allowed))}, got {v!r}")
    return v


def _rgb(v: Any, where: str) -> RGB:
    if not isinstance(v, list) or len(v) != 3:
        raise ValueError(f"{where} must be [r, g, b], got {v!r}")
    return (_int(v[0], where, 0, 255), _int(v[1], where, 0, 255), _int(v[2], where, 0, 255))


def _obj(v: Any, where: str) -> dict:
    if not isinstance(v, dict):
        raise ValueError(f"{where} must be an object, got {v!r}")
    return v


def _keyboard_look_from(d: Any, where: str) -> KeyboardLook | None:
    if d is None:
        return None
    d = _obj(d, where)
    mode = _choice(d.get("mode"), f"{where}.mode", {"firmware_effect", "solid", "per_key", "animation"})
    if mode == "firmware_effect":
        return FirmwareEffectLook(
            effect=_choice(d.get("effect"), f"{where}.effect", KEYBOARD_EFFECTS),
            speed=_int(d.get("speed"), f"{where}.speed", 0, 10),
            brightness=_int(d.get("brightness"), f"{where}.brightness", 0, 50),
            color=_choice(d.get("color"), f"{where}.color", KEYBOARD_PALETTE_SLOT_COLORS),
            direction=_choice(d.get("direction"), f"{where}.direction", KEYBOARD_DIRECTIONS),
            reactive=_bool(d.get("reactive"), f"{where}.reactive"),
            save=_bool(d.get("save"), f"{where}.save"),
        )
    if mode == "solid":
        return SolidLook(rgb=_rgb(d.get("rgb"), f"{where}.rgb"))
    if mode == "per_key":
        cells = d.get("cells")
        if not isinstance(cells, list):
            raise ValueError(f"{where}.cells must be a list, got {cells!r}")
        out = []
        for i, c in enumerate(cells):
            w = f"{where}.cells[{i}]"
            if not isinstance(c, list) or len(c) != 5:
                raise ValueError(f"{w} must be [row, col, r, g, b], got {c!r}")
            out.append((_int(c[0], w, 0, NUM_ROWS - 1), _int(c[1], w, 0, NUM_COLS - 1), _rgb(c[2:], w)))
        return PerKeyLook(cells=tuple(out))
    path = d.get("path")
    if not isinstance(path, str) or not os.path.isabs(path):
        raise ValueError(f"{where}.path must be an absolute path, got {path!r}")
    return AnimationLook(
        path=path,
        loops=_int(d.get("loops"), f"{where}.loops", 1, 1_000_000),
        forever=_bool(d.get("forever"), f"{where}.forever"),
    )


def _keyboard_look_to(look: KeyboardLook | None) -> dict | None:
    if look is None:
        return None
    if isinstance(look, FirmwareEffectLook):
        return {
            "mode": "firmware_effect",
            "effect": look.effect,
            "speed": look.speed,
            "brightness": look.brightness,
            "color": look.color,
            "direction": look.direction,
            "reactive": look.reactive,
            "save": look.save,
        }
    if isinstance(look, SolidLook):
        return {"mode": "solid", "rgb": list(look.rgb)}
    if isinstance(look, PerKeyLook):
        return {"mode": "per_key", "cells": [[r, c, *rgb] for r, c, rgb in look.cells]}
    return {"mode": "animation", "path": look.path, "loops": look.loops, "forever": look.forever}


def _led_look_from(d: Any, where: str) -> LedBarLook | None:
    if d is None:
        return None
    d = _obj(d, where)
    pal = d.get("palette")
    if not isinstance(pal, list) or not 1 <= len(pal) <= MAX_LED_BAR_PALETTE:
        raise ValueError(f"{where}.palette must hold 1–{MAX_LED_BAR_PALETTE} colours, got {pal!r}")
    return LedBarLook(
        palette=tuple(_rgb(c, f"{where}.palette[{i}]") for i, c in enumerate(pal)),
        effect=_choice(d.get("effect"), f"{where}.effect", LED_BAR_EFFECT_CODES),
        brightness=_int(d.get("brightness"), f"{where}.brightness", 0, 100),
        speed=_int(d.get("speed"), f"{where}.speed", 1, 10),
    )


def _common(d: dict, where: str) -> tuple[str, bool, Power]:
    usb_id = d.get("usb_id")
    if not isinstance(usb_id, str) or not _USB_ID.match(usb_id):
        raise ValueError(f"{where}.usb_id must look like 048d:ce00, got {usb_id!r}")
    return (
        usb_id,
        _bool(d.get("remembered"), f"{where}.remembered"),
        _choice(d.get("power"), f"{where}.power", {"on", "off"}),  # type: ignore[return-value]
    )


def _follow(v: Any, where: str) -> Follow:
    if v not in FOLLOW_VALUES:
        raise ValueError(f"{where} must be one of {', '.join(FOLLOW_VALUES)}, got {v!r}")
    return v  # type: ignore[return-value]


def state_from_dict(doc: Any) -> DeviceState:
    """Validate a decoded ``state.json`` document. Raises ``ValueError`` with a field path."""
    doc = _obj(doc, "state")
    version = doc.get("version")
    if version != STATE_VERSION:
        raise ValueError(f"unsupported version {version}")
    devices = _obj(doc.get("devices", {}), "devices")
    kb = led = None
    if devices.get("keyboard") is not None:
        d = _obj(devices["keyboard"], "keyboard")
        usb_id, remembered, power = _common(d, "keyboard")
        b = d.get("brightness")
        pal = _obj(d.get("palette", {}), "keyboard.palette")
        palette: dict[int, RGB] = {}
        for k, v in pal.items():
            if k not in {str(i) for i in range(1, 8)}:
                raise ValueError(f"keyboard.palette slot must be 1–7, got {k!r}")
            palette[int(k)] = _rgb(v, f"keyboard.palette.{k}")
        kb = KeyboardState(
            usb_id=usb_id,
            remembered=remembered,
            power=power,
            brightness=None if b is None else _int(b, "keyboard.brightness", 0, 50),
            palette=palette,
            look=_keyboard_look_from(d.get("look"), "keyboard.look"),
        )
    if devices.get("led_bar") is not None:
        d = _obj(devices["led_bar"], "led_bar")
        usb_id, remembered, power = _common(d, "led_bar")
        led = LedBarState(
            usb_id=usb_id,
            remembered=remembered,
            power=power,
            look=_led_look_from(d.get("look"), "led_bar.look"),
        )
    bulbs: list[BulbState] = []
    raw_bulbs = devices.get("bulbs")
    if raw_bulbs is not None:
        for bulb_id, entry in _obj(raw_bulbs, "bulbs").items():
            where = f"bulbs.{bulb_id}"
            entry = _obj(entry, where)
            bulbs.append(
                BulbState(
                    id=bulb_id,
                    remembered=_bool(entry.get("remembered"), f"{where}.remembered"),
                    follow=_follow(entry.get("follow"), f"{where}.follow"),
                )
            )
    return DeviceState(keyboard=kb, led_bar=led, bulbs=tuple(bulbs))


def state_to_dict(state: DeviceState) -> dict:
    devices: dict[str, Any] = {}
    if state.keyboard is not None:
        k = state.keyboard
        devices["keyboard"] = {
            "usb_id": k.usb_id,
            "remembered": k.remembered,
            "power": k.power,
            "brightness": k.brightness,
            "palette": {str(s): list(rgb) for s, rgb in sorted(k.palette.items())},
            "look": _keyboard_look_to(k.look),
        }
    if state.led_bar is not None:
        b = state.led_bar
        devices["led_bar"] = {
            "usb_id": b.usb_id,
            "remembered": b.remembered,
            "power": b.power,
            "look": None
            if b.look is None
            else {
                "palette": [list(c) for c in b.look.palette],
                "effect": b.look.effect,
                "brightness": b.look.brightness,
                "speed": b.look.speed,
            },
        }
    if state.bulbs:
        devices["bulbs"] = {
            bulb.id: {"remembered": bulb.remembered, "follow": bulb.follow} for bulb in state.bulbs
        }
    return {"version": STATE_VERSION, "devices": devices}


# --- store -------------------------------------------------------------------


def default_state_path() -> Path:
    """``$XDG_CONFIG_HOME/avell-storm-rgb/state.json``, falling back to ``~/.config``."""
    base = os.environ.get("XDG_CONFIG_HOME", "")
    root = Path(base) if base and os.path.isabs(base) else Path.home() / ".config"
    return root / "avell-storm-rgb" / STATE_FILENAME


class DeviceStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else default_state_path()

    @property
    def path(self) -> Path:
        return self._path

    def exists(self) -> bool:
        return self._path.is_file()

    def load(self) -> DeviceState:
        """Missing file → empty state. Unusable file → :class:`StateFileError`."""
        try:
            raw = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return DeviceState()
        except OSError as e:
            raise StateFileError(self._path, f"cannot read file ({e.strerror})") from e
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as e:
            raise StateFileError(self._path, f"invalid JSON at line {e.lineno} column {e.colno}") from e
        try:
            return state_from_dict(doc)
        except ValueError as e:
            raise StateFileError(self._path, str(e)) from e

    def save(self, state: DeviceState) -> None:
        """Atomic write: temp file in the same directory, fsync, then ``os.replace``."""
        directory = self._path.parent
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        data = json.dumps(state_to_dict(state), indent=2) + "\n"
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".state.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, self._path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    def quarantine(self) -> Path:
        """Move an unusable file aside (replacing an older backup) and return the new path."""
        target = self._path.with_name(self._path.name + ".invalid")
        os.replace(self._path, target)
        return target


# --- describe / restore ------------------------------------------------------


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def describe_look(look: KeyboardLook | LedBarLook | None) -> str:
    """Human summary shared by the CLI and GUI messages."""
    if look is None:
        return "no look"
    if isinstance(look, FirmwareEffectLook):
        params = KEYBOARD_EFFECT_PARAMS.get(look.effect, frozenset())
        parts = []
        if "speed" in params:
            parts.append(f"speed {look.speed}")
        if "brightness" in params:
            parts.append(f"brightness {look.brightness}")
        if "color" in params:
            parts.append(f"colour {look.color}")
        if "direction" in params:
            parts.append(f"direction {look.direction}")
        if "reactive" in params and look.reactive:
            parts.append("reactive")
        if "save" in params and look.save:
            parts.append("saved")
        return f"firmware effect {look.effect} ({', '.join(parts)})"
    if isinstance(look, SolidLook):
        return "solid #{:02x}{:02x}{:02x}".format(*look.rgb)
    if isinstance(look, PerKeyLook):
        return f"per-key ({_plural(len(look.cells), 'key')})"
    if isinstance(look, AnimationLook):
        mode = "forever" if look.forever else _plural(look.loops, "loop")
        return f"animation {look.path} ({mode})"
    return (
        f"{look.effect} · {_plural(len(look.palette), 'colour')} · "
        f"brightness {look.brightness} · speed {look.speed}"
    )


def _short_look(look: KeyboardLook) -> str:
    if isinstance(look, FirmwareEffectLook):
        return f"firmware effect {look.effect}"
    return describe_look(look)


@dataclass(frozen=True)
class RestorePlan:
    """What a restore applied, and the long-running part the caller must run itself."""

    applied: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    pending_animation: AnimationLook | None = None


def firmware_effect_payload(look: FirmwareEffectLook) -> list[int]:
    kw = keyboard_effect_kwargs(
        look.effect,
        speed=look.speed,
        brightness=look.brightness,
        color=look.color,
        direction=look.direction,
        reactive=look.reactive,
        save=look.save,
    )
    return KEYBOARD_EFFECTS[look.effect](**kw)


def restore_keyboard(kb: "KeyboardRgbDriver", state: KeyboardState) -> RestorePlan:
    """Palette → brightness → light off *or* look. Animations are returned, not run."""
    applied: list[str] = []
    warnings: list[str] = []
    pending: AnimationLook | None = None
    if state.palette:
        for slot in sorted(state.palette):
            kb.set_palette_color(slot, state.palette[slot])
        applied.append("palette " + ",".join(str(s) for s in sorted(state.palette)))
    if state.brightness is not None:
        kb.set_brightness(state.brightness)
        applied.append(f"brightness {state.brightness}")
    if state.power == "off":
        kb.turn_off()
        applied.append("light off")
        return RestorePlan(tuple(applied), tuple(warnings), None)
    look = state.look
    if isinstance(look, FirmwareEffectLook):
        kb.set_effect(firmware_effect_payload(look))
    elif isinstance(look, SolidLook):
        kb.set_color(look.rgb, None, False)
    elif isinstance(look, PerKeyLook):
        kb.set_key_colors({(r, c): rgb for r, c, rgb in look.cells})
    elif isinstance(look, AnimationLook):
        if Path(look.path).is_file():
            pending = look
        else:
            warnings.append(f"animation file not found: {look.path}")
            look = None
    if look is not None:
        applied.append(_short_look(look))
    return RestorePlan(tuple(applied), tuple(warnings), pending)


def restore_led_bar(bar: "LedBarDriver", state: LedBarState) -> RestorePlan:
    if state.power == "off":
        bar.power_off()
        return RestorePlan(("light off",))
    look = state.look
    if look is None:
        return RestorePlan()
    bar.set_palette_colors(list(look.palette))
    bar.set_brightness_level(look.brightness)
    bar.set_motion_speed(look.speed)
    bar.apply_visual_effect(look.effect)
    return RestorePlan((describe_look(look),))
