# SPDX-License-Identifier: GPL-2.0-or-later

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from collections.abc import Callable

from avell_storm_rgb.application.device_facade import (
    describe_keyboard_usb_devices,
    describe_led_bar_usb_devices,
    open_keyboard,
    open_led_bar,
)
from avell_storm_rgb.application.device_state import (
    AnimationLook,
    DeviceState,
    DeviceStateStore,
    KeyboardState,
    LedBarState,
    StateFileError,
    describe_look,
    restore_keyboard,
    restore_led_bar,
    state_to_dict,
)
from avell_storm_rgb.application.screen_follow_dispatch import run_screen_follow_auto
from avell_storm_rgb.application.screen_follow_session import is_wayland_session
from avell_storm_rgb.domain.anim_dsl import run_animation_lines
from avell_storm_rgb.domain.keyboard_solid_colors import SOLID_COLOR_NAMES
from avell_storm_rgb.domain.ledbar_colors import parse_color, parse_palette
from avell_storm_rgb.infrastructure.usb.ite8233_usb import LED_BAR_EFFECT_CODES
from avell_storm_rgb.infrastructure.usb.ite8291_usb import KEYBOARD_DIRECTIONS, KEYBOARD_EFFECTS, KEYBOARD_PALETTE_SLOT_COLORS


def _valid_rgb(x: str) -> tuple[int, int, int]:
    try:
        value = tuple(int(p) for p in x.strip().split(","))
    except ValueError as e:
        raise argparse.ArgumentTypeError("three integers separated by comma") from e
    if len(value) != 3:
        raise argparse.ArgumentTypeError("must have exactly three integers")
    return (value[0], value[1], value[2])


def _valid_intrange(lo: int, hi: float = math.inf):
    def f(x: str) -> int:
        try:
            value = int(x)
        except ValueError as e:
            raise argparse.ArgumentTypeError("must be an integer") from e
        if not (lo <= value <= hi):
            raise argparse.ArgumentTypeError(f"must be between {lo} and {hi} inclusive")
        return value

    return f


def _parse_bus_addr(devid: str) -> tuple[int, int]:
    try:
        bus, addr = (int(x) for x in devid.split("/"))
    except ValueError as e:
        raise argparse.ArgumentTypeError("expected bus/addr") from e
    if bus < 0 or addr < 0:
        raise argparse.ArgumentTypeError("bus and address must be non-negative")
    return (bus, addr)


def _cmd_device_list(args: argparse.Namespace) -> int:
    kind = args.kind
    if kind in ("all", "keyboard"):
        for line in describe_keyboard_usb_devices():
            print(line)
    if kind in ("all", "led-bar"):
        for line in describe_led_bar_usb_devices():
            print(line)
    return 0


def _open_kb(args: argparse.Namespace):
    return open_keyboard(bus_addr=getattr(args, "device", None), debug=getattr(args, "debug", False))


def _cmd_keyboard_power(args: argparse.Namespace) -> int:
    kb = _open_kb(args)
    if args.state == "off":
        kb.turn_off()
    return 0


def _cmd_keyboard_brightness(args: argparse.Namespace) -> int:
    _open_kb(args).set_brightness(args.value)
    return 0


def _cmd_keyboard_effect(args: argparse.Namespace) -> int:
    kb = _open_kb(args)
    builder = KEYBOARD_EFFECTS.get(args.name)
    if builder is None:
        print(f"unknown effect: {args.name}", file=sys.stderr)
        return 1
    data: dict[str, int] = {}
    if args.speed is not None:
        data["speed"] = args.speed
    if args.brightness is not None:
        data["brightness"] = args.brightness
    if args.color is not None:
        data["color"] = KEYBOARD_PALETTE_SLOT_COLORS[args.color]
    if args.direction is not None:
        data["direction"] = KEYBOARD_DIRECTIONS[args.direction]
    if args.reactive:
        data["reactive"] = 1
    if args.save:
        data["save"] = 1
    kb.set_effect(builder(**data))
    return 0


def _cmd_keyboard_solid_color(args: argparse.Namespace) -> int:
    kb = _open_kb(args)
    if args.name:
        rgb = SOLID_COLOR_NAMES[args.name]
    else:
        rgb = args.rgb
    kb.set_color(rgb, args.brightness)
    return 0


def _cmd_keyboard_palette(args: argparse.Namespace) -> int:
    kb = _open_kb(args)
    if args.action == "restore":
        kb.restore_default_palette()
    elif args.action == "random":
        for i in range(7):
            kb.set_palette_color(i + 1, (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    else:
        kb.set_palette_color(args.slot, _valid_rgb(args.rgb_triplet))
    return 0


def _cmd_keyboard_demo_test_pattern(args: argparse.Namespace) -> int:
    kb = _open_kb(args)
    b = kb.get_brightness()
    for i in range(6):
        kb.test_pattern(i, 50 - i * 10)
        if i != 5:
            time.sleep(2)
    kb.set_key_colors({}, b)
    return 0


def _cmd_keyboard_freeze(args: argparse.Namespace) -> int:
    _open_kb(args).freeze()
    return 0


def _cmd_keyboard_follow_screen(args: argparse.Namespace) -> int:
    try:
        kb = _open_kb(args)
        if is_wayland_session() and not args.fullscreen:
            print(
                "Wayland: --region is ignored; pick a window in the portal dialog.",
                file=sys.stderr,
            )
        if args.fullscreen or is_wayland_session():
            run_screen_follow_auto(kb)
        else:
            parts = [int(x) for x in args.region.split(",")]
            if len(parts) != 4:
                print("region must be x,y,width,height", file=sys.stderr)
                return 1
            run_screen_follow_auto(kb, offset_x=parts[0], offset_y=parts[1], width=parts[2], height=parts[3])
    except ImportError as e:
        print(
            "follow-screen needs optional dependencies: uv sync --extra screen "
            f"({e})",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        pass
    return 0


def _cmd_keyboard_play_animation(args: argparse.Namespace) -> int:
    kb = _open_kb(args)
    file_obj = args.file
    repeat = None if args.forever else args.loop
    text = file_obj.read()
    lines = text.splitlines()

    def one_pass() -> None:
        run_animation_lines(
            lines,
            on_apply=lambda m: kb.set_key_colors(m),
            on_brightness=kb.set_brightness,
            sleep=time.sleep,
        )

    try:
        if repeat is None:
            while True:
                one_pass()
        else:
            for _ in range(repeat):
                one_pass()
    except KeyboardInterrupt:
        pass
    return 0


def _cmd_keyboard_inspect(args: argparse.Namespace) -> int:
    if not (args.fw_version or args.brightness or args.power):
        print("specify at least one of: --fw-version --brightness --power", file=sys.stderr)
        return 1
    kb = _open_kb(args)
    if args.fw_version:
        print("{}.{}.{}.{}".format(*kb.get_fw_version()))
    if args.brightness:
        print(kb.get_brightness())
    if args.power:
        print("off" if kb.is_off() else "on")
    return 0


def _open_led_bar(_args: argparse.Namespace):
    return open_led_bar()


def _cmd_led_bar_power(args: argparse.Namespace) -> int:
    bar = _open_led_bar(args)
    if args.state == "on":
        bar.power_on()
    else:
        bar.power_off()
    return 0


def _cmd_led_bar_color(args: argparse.Namespace) -> int:
    bar = _open_led_bar(args)
    r, g, b = parse_color(args.spec)
    bar.set_static_rgb(r, g, b)
    return 0


def _cmd_led_bar_palette(args: argparse.Namespace) -> int:
    bar = _open_led_bar(args)
    colors = parse_palette(args.spec)
    bar.set_palette_colors(colors)
    bar.apply_visual_effect(args.with_effect)
    return 0


def _cmd_led_bar_effect(args: argparse.Namespace) -> int:
    bar = _open_led_bar(args)
    bar.apply_visual_effect(args.name)
    return 0


def _cmd_led_bar_brightness(args: argparse.Namespace) -> int:
    bar = _open_led_bar(args)
    bar.set_brightness_level(args.value)
    bar.apply_visual_effect(args.with_effect)
    return 0


def _cmd_led_bar_speed(args: argparse.Namespace) -> int:
    bar = _open_led_bar(args)
    bar.set_motion_speed(args.value)
    bar.apply_visual_effect(args.with_effect)
    return 0


def _cmd_led_bar_inspect(args: argparse.Namespace) -> int:
    bar = _open_led_bar(args)
    pid = bar.product_id or 0
    print(f"ITE 8233 LED bar 048d:{pid:04x} connected")
    print("effects:", ", ".join(LED_BAR_EFFECT_CODES))
    return 0


# --- state show / restore ---------------------------------------------------------

_KIND_LABEL = {"keyboard": "keyboard", "led_bar": "led-bar"}
_PREFIX_WIDTH = 44  # "keyboard  " + "048d:ce00  " + "remembered  " + "light on   "


def _load_state(store: DeviceStateStore) -> DeviceState | None:
    """Loaded state, or ``None`` after printing the unreadable-file error (exit 3)."""
    try:
        return store.load()
    except StateFileError as e:
        print(f"error: saved state is unreadable ({e.reason}): {e.path}", file=sys.stderr)
        return None


def _saved_devices(state: DeviceState) -> list[tuple[str, KeyboardState | LedBarState]]:
    out: list[tuple[str, KeyboardState | LedBarState]] = []
    if state.keyboard is not None:
        out.append(("keyboard", state.keyboard))
    if state.led_bar is not None:
        out.append(("led_bar", state.led_bar))
    return out


def _cmd_state_show(args: argparse.Namespace) -> int:
    store = DeviceStateStore()
    state = _load_state(store)
    if state is None:
        return 3
    if args.json:
        print(json.dumps({"path": str(store.path), **state_to_dict(state)}))
        return 0
    if not store.exists():
        print(f"No saved state at {store.path}")
        return 0
    print(f"State file: {store.path}")
    for kind, saved in _saved_devices(state):
        prefix = (
            f"{_KIND_LABEL[kind]:<10}{saved.usb_id}  "
            f"{'remembered' if saved.remembered else 'forgotten':<12}"
            f"{'light ' + saved.power:<11}"
        )
        print(prefix + describe_look(saved.look))
        if isinstance(saved, KeyboardState):
            extras = []
            if saved.brightness is not None:
                extras.append(f"brightness {saved.brightness}")
            if saved.palette:
                extras.append("palette slots " + ", ".join(str(s) for s in sorted(saved.palette)))
            if extras:
                print(" " * _PREFIX_WIDTH + " · ".join(extras))
    return 0


def _play_animation_foreground(kb, look: AnimationLook) -> None:
    lines = open(look.path, encoding="utf-8", errors="replace").read().splitlines()

    def one_pass() -> None:
        run_animation_lines(
            lines,
            on_apply=lambda m: kb.set_key_colors(m),
            on_brightness=kb.set_brightness,
            sleep=time.sleep,
        )

    try:
        if look.forever:
            while True:
                one_pass()
        else:
            for _ in range(look.loops):
                one_pass()
    except KeyboardInterrupt:
        pass


def _restore_one(kind: str, saved, *, no_animation: bool) -> tuple[dict, str, object]:
    """Restore one device. Returns (json result, human summary, (kb, animation) to play or None)."""
    base = {"kind": kind, "usb_id": saved.usb_id}
    try:
        dev = open_keyboard(usb_id=saved.usb_id) if kind == "keyboard" else open_led_bar(usb_id=saved.usb_id)
    except FileNotFoundError:
        return {**base, "status": "skipped", "reason": "device not found"}, "skipped: device not found", None
    except RuntimeError as e:
        if str(e).startswith("No ITE 8233"):
            return {**base, "status": "skipped", "reason": "device not found"}, "skipped: device not found", None
        return {**base, "status": "failed", "reason": f"{type(e).__name__}: {e}"}, f"failed: {type(e).__name__}: {e}", None
    except Exception as e:
        return {**base, "status": "failed", "reason": f"{type(e).__name__}: {e}"}, f"failed: {type(e).__name__}: {e}", None
    try:
        plan = restore_keyboard(dev, saved) if kind == "keyboard" else restore_led_bar(dev, saved)
    except Exception as e:
        return {**base, "status": "failed", "reason": f"{type(e).__name__}: {e}"}, f"failed: {type(e).__name__}: {e}", None

    result = {**base, "status": "restored", "applied": list(plan.applied), "warnings": list(plan.warnings)}
    play = None
    if saved.power == "off":
        summary = "light off"
    elif plan.warnings:
        summary = "light on (warning: " + "; ".join(plan.warnings) + ")"
    elif plan.pending_animation is not None and no_animation:
        done = [a.split()[0] for a in plan.applied if not a.startswith("animation")]
        summary = (", ".join(done) or "light on") + " (animation skipped)"
    elif plan.pending_animation is not None:
        summary = describe_look(plan.pending_animation)
        summary += " — playing, Ctrl+C to stop" if plan.pending_animation.forever else " — playing"
        play = (dev, plan.pending_animation)
    elif saved.look is not None:
        summary = describe_look(saved.look)
    else:
        summary = "light on"
    return result, "restored: " + summary, play


def _cmd_state_restore(args: argparse.Namespace) -> int:
    store = DeviceStateStore()
    state = _load_state(store)
    if state is None:
        return 3
    if not store.exists():
        if args.json:
            print(json.dumps({"path": str(store.path), "results": []}))
        else:
            print(f"Nothing to restore: no saved state at {store.path}")
        return 0
    wanted = {"all": ("led_bar", "keyboard"), "keyboard": ("keyboard",), "led-bar": ("led_bar",)}[args.kind]
    devices = dict(_saved_devices(state))
    results: list[dict] = []
    play = None
    code = 0
    for kind in ("led_bar", "keyboard"):
        saved = devices.get(kind)
        if kind not in wanted or saved is None or not saved.remembered:
            continue
        result, summary, to_play = _restore_one(kind, saved, no_animation=args.no_animation)
        results.append(result)
        if result["status"] != "restored" or result.get("warnings"):
            code = 1
        if not args.json:
            print(f"{_KIND_LABEL[kind]:<10}{saved.usb_id}  {summary}", flush=True)
        play = to_play or play
    if args.json:
        print(json.dumps({"path": str(store.path), "results": results}), flush=True)
    if play is not None:
        _play_animation_foreground(*play)
    return code


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="avell-storm-rgb",
        description="Unified USB control for ITE 8291 keyboard RGB and ITE 8233 LED bar.",
    )

    sub = p.add_subparsers(dest="domain", required=True)

    # device list
    dev = sub.add_parser("device", help="Discover devices")
    dev_sub = dev.add_subparsers(dest="device_cmd", required=True)
    dl = dev_sub.add_parser("list", help="List supported USB devices")
    dl.add_argument(
        "--kind",
        choices=["all", "keyboard", "led-bar"],
        default="all",
        help="Which family to list",
    )
    dl.set_defaults(_handler=_cmd_device_list)

    # keyboard
    kb = sub.add_parser("keyboard", help="ITE 8291 keyboard backlight")
    kb.add_argument("--debug", action="store_true")
    kb.add_argument("--device", type=_parse_bus_addr, default=None)
    kb_sub = kb.add_subparsers(dest="kb_cmd", required=True)

    k_off = kb_sub.add_parser("power", help="Power / backlight")
    k_off.add_argument("state", choices=["off"])
    k_off.set_defaults(_handler=_cmd_keyboard_power)

    k_br = kb_sub.add_parser("brightness", help="Set brightness 0–50")
    k_br.add_argument("value", type=_valid_intrange(0, 50))
    k_br.set_defaults(_handler=_cmd_keyboard_brightness)

    k_ef = kb_sub.add_parser("effect", help="Apply built-in firmware effect")
    k_ef.add_argument("name", choices=list(KEYBOARD_EFFECTS.keys()))
    k_ef.add_argument("-s", "--speed", type=_valid_intrange(0, 10), default=None)
    k_ef.add_argument("-b", "--brightness", type=_valid_intrange(0, 50), default=None)
    k_ef.add_argument("-c", "--color", choices=list(KEYBOARD_PALETTE_SLOT_COLORS.keys()), default=None)
    k_ef.add_argument("--save", action="store_true")
    g = k_ef.add_mutually_exclusive_group()
    g.add_argument("-d", "--direction", choices=list(KEYBOARD_DIRECTIONS.keys()))
    g.add_argument("-r", "--reactive", action="store_true")
    k_ef.set_defaults(_handler=_cmd_keyboard_effect)

    k_so = kb_sub.add_parser("solid-color", help="Uniform keyboard color")
    g2 = k_so.add_mutually_exclusive_group(required=True)
    g2.add_argument("--name", choices=list(SOLID_COLOR_NAMES.keys()))
    g2.add_argument("--rgb", type=_valid_rgb)
    k_so.add_argument("-b", "--brightness", type=_valid_intrange(0, 50), default=None)
    k_so.set_defaults(_handler=_cmd_keyboard_solid_color)

    k_pa = kb_sub.add_parser("palette", help="Keyboard palette slots 1–7")
    pa_sub = k_pa.add_subparsers(dest="action", required=True)
    pa_sub.add_parser("restore").set_defaults(_handler=_cmd_keyboard_palette)
    pa_sub.add_parser("random").set_defaults(_handler=_cmd_keyboard_palette)
    p_set = pa_sub.add_parser("set-slot")
    p_set.add_argument("slot", type=_valid_intrange(1, 7))
    p_set.add_argument("rgb_triplet")
    p_set.set_defaults(_handler=_cmd_keyboard_palette)

    kb_sub.add_parser("demo-test-pattern", help="RGB test pattern then restore").set_defaults(
        _handler=_cmd_keyboard_demo_test_pattern
    )
    kb_sub.add_parser("freeze-animation", help="Freeze current effect (experimental)").set_defaults(
        _handler=_cmd_keyboard_freeze
    )

    k_fs = kb_sub.add_parser(
        "follow-screen",
        help="Map display/window to keys (X11 region or Wayland portal; needs extra [screen])",
    )
    g3 = k_fs.add_mutually_exclusive_group(required=True)
    g3.add_argument("--fullscreen", action="store_true")
    g3.add_argument("--region", metavar="X,Y,W,H")
    k_fs.set_defaults(_handler=_cmd_keyboard_follow_screen)

    k_an = kb_sub.add_parser("play-animation", help="Per-key animation DSL (file or stdin)")
    k_an.add_argument(
        "--file",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Animation script path (default: stdin)",
    )
    k_an.add_argument("--loop", type=int, default=1, help="Repeat count (default: 1)")
    k_an.add_argument("--forever", action="store_true", help="Loop animation until Ctrl+C")
    k_an.set_defaults(_handler=_cmd_keyboard_play_animation)

    k_in = kb_sub.add_parser("inspect", help="Query keyboard controller")
    k_in.add_argument("--fw-version", action="store_true")
    k_in.add_argument("--brightness", action="store_true")
    k_in.add_argument("--power", action="store_true", help="Print on or off")
    k_in.set_defaults(_handler=_cmd_keyboard_inspect)

    # led-bar
    lb = sub.add_parser("led-bar", help="ITE 8233 LED bar")
    lb_sub = lb.add_subparsers(dest="lb_cmd", required=True)

    lb_pw = lb_sub.add_parser("power", help="Power LED bar")
    lb_pw.add_argument("state", choices=["on", "off"])
    lb_pw.set_defaults(_handler=_cmd_led_bar_power)

    lb_c = lb_sub.add_parser("color", help="Static color")
    lb_c.add_argument("spec", help="Color name or #RRGGBB")
    lb_c.set_defaults(_handler=_cmd_led_bar_color)

    lb_p = lb_sub.add_parser("palette", help="Palette preset or comma-separated colors")
    lb_p.add_argument("spec", help="Preset name or r,g,b,...")
    lb_p.add_argument(
        "--with-effect",
        default="breathing",
        choices=list(LED_BAR_EFFECT_CODES.keys()),
    )
    lb_p.set_defaults(_handler=_cmd_led_bar_palette)

    lb_e = lb_sub.add_parser("effect", help="Built-in bar effect")
    lb_e.add_argument("name", choices=list(LED_BAR_EFFECT_CODES.keys()))
    lb_e.set_defaults(_handler=_cmd_led_bar_effect)

    lb_b = lb_sub.add_parser("brightness", help="Brightness 0–100 (re-applies effect)")
    lb_b.add_argument("value", type=_valid_intrange(0, 100))
    lb_b.add_argument(
        "--with-effect",
        default="static",
        choices=list(LED_BAR_EFFECT_CODES.keys()),
    )
    lb_b.set_defaults(_handler=_cmd_led_bar_brightness)

    lb_s = lb_sub.add_parser("speed", help="Animation speed 1–10 (re-applies effect)")
    lb_s.add_argument("value", type=_valid_intrange(1, 10))
    lb_s.add_argument(
        "--with-effect",
        default="breathing",
        choices=list(LED_BAR_EFFECT_CODES.keys()),
    )
    lb_s.set_defaults(_handler=_cmd_led_bar_speed)

    lb_sub.add_parser("inspect", help="LED bar status").set_defaults(_handler=_cmd_led_bar_inspect)

    # state
    st = sub.add_parser("state", help="Saved device state written by the GUI")
    st_sub = st.add_subparsers(dest="state_cmd", required=True)
    st_show = st_sub.add_parser("show", help="Show the saved state")
    st_show.add_argument("--json", action="store_true", help="Machine-readable output")
    st_show.set_defaults(_handler=_cmd_state_show)
    st_re = st_sub.add_parser("restore", help="Apply the saved state to remembered devices")
    st_re.add_argument("--kind", choices=["all", "keyboard", "led-bar"], default="all")
    st_re.add_argument("--no-animation", action="store_true", help="Skip a saved animation")
    st_re.add_argument("--json", action="store_true", help="Machine-readable output")
    st_re.set_defaults(_handler=_cmd_state_restore)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = _build_parser()
    args = parser.parse_args(argv)

    handler: Callable[[argparse.Namespace], int] | None = getattr(args, "_handler", None)
    if handler is None:
        parser.print_help()
        return 0
    try:
        return int(handler(args))
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
