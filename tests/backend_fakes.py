"""Fake USB drivers and worker helpers for GUI backend / facade tests (no hardware)."""

from __future__ import annotations



def drain(worker, rounds: int = 4) -> None:
    """Wait until every queued USB task ran, then deliver queued signals; repeat for follow-ups."""
    from PySide6.QtCore import QCoreApplication

    for _ in range(rounds):
        worker._pool.submit(lambda: None).result(timeout=5)
        QCoreApplication.processEvents()


class FakeKeyboard:
    """Implements ``ports.protocols.KeyboardRgbDriver`` (+ inspect calls); records every call."""

    def __init__(self, *, fail_on: frozenset[str] = frozenset(), journal: list | None = None) -> None:
        self.calls: list[tuple] = []
        self.journal = journal
        self.off = False
        self.effect = [10, 20, 30, 40, 50, 60]
        self.fail_on = fail_on

    def _rec(self, name: str, *args) -> None:
        if name in self.fail_on:
            raise RuntimeError(f"{name} failed")
        self.calls.append((name, *args))
        if self.journal is not None:
            self.journal.append((type(self).__name__, name))

    def get_fw_version(self) -> tuple[int, int, int, int]:
        return (1, 2, 3, 4)

    def get_brightness(self) -> int:
        return 25

    def is_off(self) -> bool:
        return self.off

    def get_effect(self) -> list[int]:
        return list(self.effect)

    def close(self) -> None:
        self._rec("close")

    def turn_off(self) -> None:
        self._rec("turn_off")
        self.off = True

    def set_effect(self, data: list[int]) -> None:
        self._rec("set_effect", list(data))
        self.off = False

    def set_brightness(self, value: int) -> None:
        self._rec("set_brightness", value)

    def set_color(self, color, brightness=None, save=False) -> None:
        self._rec("set_color", tuple(color), brightness, save)
        self.off = False

    def set_key_colors(self, color_map=None, brightness=None, save=False, enable_user_mode_flag=True) -> None:
        self._rec("set_key_colors", dict(color_map or {}))
        self.off = False

    def set_palette_color(self, idx: int, color) -> None:
        self._rec("set_palette_color", idx, tuple(color))

    def restore_default_palette(self) -> None:
        self._rec("restore_default_palette")

    def test_pattern(self, shift: int = 0, brightness=None, save=False) -> None:
        self._rec("test_pattern")

    def freeze(self) -> None:
        self._rec("freeze")

    def enable_user_mode(self, brightness=None, save=False) -> None:
        self._rec("enable_user_mode")

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]


class FakeLedBar:
    """Implements ``ports.protocols.LedBarDriver`` with the real driver's attribute semantics."""

    def __init__(
        self, *, fail_on: frozenset[str] = frozenset(), product_id: int = 0x7001, journal: list | None = None
    ) -> None:
        self.calls: list[tuple] = []
        self.journal = journal
        self.fail_on = fail_on
        self.product_id = product_id
        self.brightness = 50
        self.speed = 3
        self.palette: list[tuple[int, int, int]] = [(136, 0, 255)]

    def _rec(self, name: str, *args) -> None:
        if name in self.fail_on:
            raise RuntimeError(f"{name} failed")
        self.calls.append((name, *args))
        if self.journal is not None:
            self.journal.append((type(self).__name__, name))

    def close(self) -> None:
        self._rec("close")

    def power_on(self) -> None:
        self._rec("power_on")

    def power_off(self) -> None:
        self._rec("power_off")

    def set_static_rgb(self, r: int, g: int, b: int) -> None:
        self._rec("set_static_rgb", r, g, b)
        self.palette = [(r, g, b)]

    def set_palette_colors(self, colors) -> None:
        self._rec("set_palette_colors", [tuple(c) for c in colors])
        self.palette = [tuple(c) for c in colors][:9]

    def apply_visual_effect(self, name: str) -> None:
        self._rec("apply_visual_effect", name)

    def set_brightness_level(self, level: int) -> None:
        self._rec("set_brightness_level", level)
        self.brightness = max(0, min(100, level))

    def set_motion_speed(self, speed: int) -> None:
        self._rec("set_motion_speed", speed)
        self.speed = max(1, min(10, speed))

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]


class FakeBulb:
    """Implements ``ports.protocols.BulbDriver``; records every call, never touches the network."""

    opened = 0  # class-wide open count (one per instance)
    live_connections = 0

    def __init__(
        self,
        *,
        status=None,
        fail_on: frozenset[str] = frozenset(),
        unreachable: bool = False,
        key: str = "",
        journal: list | None = None,
        reject_second_connection: bool = False,
    ) -> None:
        from avell_storm_rgb.domain.bulb_color import BulbStatus

        self.calls: list[tuple] = []
        self.journal = journal
        self.state = status or BulbStatus(True, "white", 50, 30, None)
        self.fail_on = fail_on
        self.unreachable = unreachable
        self.key = key
        self.closed = False
        self.held = False
        self.reject_second_connection = reject_second_connection
        if reject_second_connection and FakeBulb.live_connections > 0:
            raise AssertionError("second concurrent connection")
        FakeBulb.opened += 1
        FakeBulb.live_connections += 1

    def _rec(self, name: str, *args) -> None:
        from avell_storm_rgb.application.bulb_facade import BulbError, BulbUnreachable

        if self.unreachable:
            raise BulbUnreachable("fake")
        if name in self.fail_on:
            raise BulbError(f"{name} failed")
        self.calls.append((name, *args))
        if self.journal is not None:
            self.journal.append(name)

    def status(self):
        self._rec("status")
        return self.state

    def set_power(self, on: bool) -> None:
        self._rec("set_power", on)

    def set_brightness(self, percent: int, status=None) -> None:
        self._rec("set_brightness", percent)

    def set_white(self, temperature_percent, status=None) -> None:
        self._rec("set_white", temperature_percent)

    def set_colour(self, rgb) -> None:
        self._rec("set_colour", tuple(rgb))

    def push_colour(self, rgb) -> None:
        self._rec("push_colour", tuple(rgb))

    def hold_open(self, persistent: bool) -> None:
        self.held = persistent
        self.calls.append(("hold_open", persistent))

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            FakeBulb.live_connections -= 1
        self.calls.append(("close",))

    def names(self) -> list[str]:
        return [c[0] for c in self.calls]


def drain_bulbs(worker, rounds: int = 4) -> None:
    """Wait for every queued bulb task, then deliver queued signals; repeat for follow-ups."""
    from PySide6.QtCore import QCoreApplication

    for _ in range(rounds):
        for pool in list(worker._pools.values()):
            pool.submit(lambda: None).result(timeout=5)
        QCoreApplication.processEvents()
