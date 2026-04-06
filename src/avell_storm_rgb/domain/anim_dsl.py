"""Animation DSL: pos/apply/wait/clear/brightness/shift (from ite8291r3-ctl __main__)."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


def parse_rgb_triplet(s: str) -> tuple[int, int, int]:
    parts = tuple(int(x) for x in s.strip().split(","))
    if len(parts) != 3:
        raise ValueError("RGB must be three integers separated by commas")
    return (parts[0], parts[1], parts[2])


def run_animation_lines(
    lines: Iterable[str],
    *,
    on_apply: Callable[[dict[tuple[int, int], tuple[int, int, int]]], None],
    on_brightness: Callable[[int], None],
    sleep: Callable[[float], None],
) -> None:
    color_map: dict[tuple[int, int], tuple[int, int, int]] = {}
    comment = 0

    def do_shift(rowdiff: int, coldiff: int) -> None:
        nonlocal color_map
        new_map: dict[tuple[int, int], tuple[int, int, int]] = {}
        for (row, col), color in color_map.items():
            nr, nc = row + rowdiff, col + coldiff
            if 0 <= nr <= 5 and 0 <= nc <= 15:
                new_map[(nr, nc)] = color
        color_map = new_map

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("/*"):
            comment += 1
            continue
        if line.startswith("*/"):
            comment -= 1
            continue
        if comment != 0:
            continue
        parts = line.split()
        op = parts[0]
        if op == "pos":
            _, row_s, col_s, rgb_s = line.split(maxsplit=3)
            color_map[(int(row_s), int(col_s))] = parse_rgb_triplet(rgb_s)
        elif op == "apply":
            on_apply(color_map)
        elif op == "wait":
            sleep(float(parts[1]))
        elif op == "clear":
            color_map.clear()
        elif op == "brightness":
            on_brightness(int(parts[1]))
        elif op == "shift":
            do_shift(int(parts[1]), int(parts[2]))
        else:
            raise ValueError(f"Unknown animation opcode: {op}")
