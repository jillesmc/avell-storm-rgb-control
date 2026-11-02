# SPDX-License-Identifier: GPL-2.0-or-later
"""``avell-storm-rgb bulb …`` — Tuya bulb verbs for the terminal.

``.compozy/tasks/tuya-bulbs/_dx.md`` is the byte-level contract for every line,
JSON document and exit code below. Keys never reach the output: listings print
``key: set`` and JSON prints ``"key": "set"`` (ADR-001, BR-3).

This module never imports ``tinytuya`` (only ``application.bulb_facade`` names it
inside ``find_spec``) and never imports Qt. Without the ``tuya`` extra every verb
prints the install hint and exits 1, while ``bulb -h`` still lists the verbs:
the parser is built unconditionally, the availability check runs in the handler.

Exit codes (``_dx.md`` Errors): 0 ok, 1 bulb/extra/file failure, 2 argparse or
target error, 3 unreadable inventory.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from avell_storm_rgb.application.bulb_facade import (
    BulbUnreachable,
    KeyRejected,
    open_bulb,
    tuya_available,
)
from avell_storm_rgb.application.bulb_inventory import (
    AmbiguousTarget,
    BulbInventory,
    BulbRecord,
    ImportFileError,
    ImportResult,
    InventoryFileError,
    Skipped,
    UnknownTarget,
    match_target,
    parse_tinytuya_devices,
)
from avell_storm_rgb.domain.bulb_color import BulbStatus

__all__ = [
    "KEY_REJECTED_HINT",
    "LIST_DEADLINE",
    "LIST_WORKERS",
    "NO_BULBS_HINT",
    "NO_EXTRA_HINT",
    "register_bulb_group",
]

NO_EXTRA_HINT = "error: bulb control needs the optional 'tuya' extra: uv sync --extra tuya"
NO_BULBS_HINT = (
    "No bulbs imported. Import the devices.json written by 'python -m tinytuya wizard':\n"
    "  avell-storm-rgb bulb import <path/to/devices.json>"
)
KEY_REJECTED_HINT = "local key or protocol rejected — re-import devices.json"
INVENTORY_UNREADABLE = "error: bulb inventory is unreadable ({reason}): {path}"

#: ``_dx.md``: "Columns: name padded to 12, then the result" (one space separator).
NAME_WIDTH = 12
#: ``online  `` / ``offline `` — 9 columns before the IP.
STATE_WIDTH = 9
#: ``192.168.0.21  `` / ``—             `` — 14 columns before ``protocol``.
IP_WIDTH = 14
#: ``on   `` before the mode.
POWER_WIDTH = 5
#: ``white   `` / ``colour  ``.
MODE_WIDTH = 8
DASH = "—"

#: ``bulb list``: one task per bulb, at most 8 at a time, one deadline for the command.
LIST_WORKERS = 8
LIST_DEADLINE = 10.0  # > discovery (6 s) + one read, so a bulb with no known IP fits (D-2)


# --- small shared helpers ---------------------------------------------------------


def _valid_intrange(lo: int, hi: int):
    """Same contract as ``main._valid_intrange``: argparse exits 2 on a bad value."""

    def f(x: str) -> int:
        try:
            value = int(x)
        except ValueError as e:
            raise argparse.ArgumentTypeError("must be an integer") from e
        if not (lo <= value <= hi):
            raise argparse.ArgumentTypeError(f"must be between {lo} and {hi} inclusive")
        return value

    return f


def _not_all(x: str) -> str:
    """``bulb remove all`` is an argparse usage error (exit 2), not a target error."""
    if x == "all":
        raise argparse.ArgumentTypeError("'all' is not accepted; remove one bulb by name or id")
    return x


def _require_tuya() -> bool:
    if tuya_available():
        return True
    print(NO_EXTRA_HINT, file=sys.stderr)
    return False


def _open_inventory() -> tuple[BulbInventory, list[BulbRecord]] | None:
    """Inventory plus records, or ``None`` after printing the unreadable error (exit 3)."""
    inventory = BulbInventory()
    try:
        return inventory, inventory.load()
    except InventoryFileError as e:
        print(INVENTORY_UNREADABLE.format(reason=e.reason, path=e.path), file=sys.stderr)
        return None


def _no_bulbs(code: int) -> int:
    print(NO_BULBS_HINT)
    return code


def _targets(records: list[BulbRecord], target: str) -> list[BulbRecord] | None:
    """Resolved targets, or ``None`` after printing the unknown/ambiguous error (exit 2)."""
    try:
        return match_target(records, target)
    except (UnknownTarget, AmbiguousTarget) as e:
        print(f"error: {e}", file=sys.stderr)
        return None


def _name_cell(name: str) -> str:
    return f"{name:<{NAME_WIDTH}} "


def _key_state(record: BulbRecord) -> str:
    return "set" if record.key else "missing"


def _close(driver: Any) -> None:
    if driver is None:
        return
    try:
        driver.close()
    except Exception:  # noqa: BLE001 - closing a dead socket is best effort
        pass


def _driver_ip(driver: Any, record: BulbRecord) -> str | None:
    """Resolved IP of an open driver (``BulbDriver`` does not require the property)."""
    return getattr(driver, "ip", None) or record.last_ip


def _json_line(doc: dict[str, Any]) -> None:
    # ensure_ascii=False: names keep their accents, as in the _dx.md transcripts.
    print(json.dumps(doc, ensure_ascii=False))


# --- import -----------------------------------------------------------------------


def _import_text(result: ImportResult) -> str:
    return result.status if result.reason is None else f"{result.status} ({result.reason})"


def _import_json(
    results: tuple[ImportResult, ...], skipped: list[Skipped]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for result in results:
        entry: dict[str, Any] = {"id": result.id, "name": result.name, "status": result.status}
        if result.reason is not None:
            entry["reason"] = result.reason
        out.append(entry)
    for skip in skipped:
        out.append({"id": skip.id, "name": skip.name, "status": "skipped", "reason": skip.reason})
    return out


def _cmd_import(args: argparse.Namespace) -> int:
    if not _require_tuya():
        return 1
    path = Path(args.file).expanduser()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        print(
            f"error: not a tinytuya devices.json (cannot read file ({e.strerror})): {path}",
            file=sys.stderr,
        )
        return 1
    try:
        records, skipped = parse_tinytuya_devices(text)
    except ImportFileError as e:
        print(f"error: not a tinytuya devices.json ({e.reason}): {path}", file=sys.stderr)
        return 1
    inventory = BulbInventory()
    try:
        report = inventory.upsert(records)
    except InventoryFileError as e:
        print(INVENTORY_UNREADABLE.format(reason=e.reason, path=e.path), file=sys.stderr)
        return 3
    if report.imported == 0:
        print(f"No bulbs found in {path}")
        return 1
    if args.json:
        _json_line({"path": str(inventory.path), "results": _import_json(report.results, skipped)})
        return 0
    for result in report.results:
        print(_name_cell(result.name) + result.id + "  " + _import_text(result))
    for skip in skipped:
        print(_name_cell(skip.name) + skip.id + "  skipped: " + skip.reason)
    count = report.imported
    plural = "" if count == 1 else "s"
    print(f"Imported {count} bulb{plural} into {inventory.path}")
    return 0


# --- list / status ----------------------------------------------------------------


@dataclass(frozen=True)
class _Read:
    """One status read, or why it did not happen (``failure`` None = unreachable)."""

    record: BulbRecord
    online: bool
    ip: str | None = None
    status: BulbStatus | None = None
    failure: str | None = None


def _read_one(inventory: BulbInventory, record: BulbRecord) -> _Read:
    """Open, read once, close. Never raises: one bad bulb must not abort the command."""
    driver = None
    try:
        driver = open_bulb(record, inventory)
        status = driver.status()
        return _Read(record, True, _driver_ip(driver, record), status)
    except BulbUnreachable:
        return _Read(record, False)
    except KeyRejected:
        return _Read(record, False, failure=KEY_REJECTED_HINT)
    except Exception as e:  # noqa: BLE001 - BulbError and anything else share one shape
        return _Read(record, False, failure=f"{type(e).__name__}: {e}")
    finally:
        _close(driver)


def _read_many(inventory: BulbInventory, records: list[BulbRecord]) -> list[_Read]:
    """Read every bulb once, in parallel, under a single ``LIST_DEADLINE`` (E2E-011).

    ``ThreadPoolExecutor`` capped at 8 workers, one 10 s deadline for the whole
    command: a bulb that has not answered by then is ``offline``. Each task keeps
    the adapter's 5 s per-command timeout (``TuyaBulb``'s ``COMMAND_TIMEOUT``).
    The pool is shut down without waiting, so three offline bulbs cost ~10 s, not
    3 × 10 s.
    """
    workers = max(1, min(LIST_WORKERS, len(records)))
    pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="bulb-list")
    try:
        futures: dict[Future[_Read], BulbRecord] = {
            pool.submit(_read_one, inventory, record): record for record in records
        }
        wait(futures, timeout=LIST_DEADLINE)
        reads: list[_Read] = []
        for future, record in futures.items():
            if future.done() and not future.cancelled():
                try:
                    reads.append(future.result())
                except Exception as e:  # noqa: BLE001 - defensive; _read_one does not raise
                    reads.append(_Read(record, False, failure=f"{type(e).__name__}: {e}"))
            else:
                future.cancel()
                reads.append(_Read(record, False))
        return reads
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _list_line(read: _Read) -> str:
    state = "online" if read.online else "offline"
    ip = (read.ip or DASH) if read.online else DASH
    record = read.record
    return (
        _name_cell(record.name)
        + record.id
        + "  "
        + f"{state:<{STATE_WIDTH}}{ip:<{IP_WIDTH}}"
        + f"protocol {record.protocol}  key: {_key_state(record)}"
    )


def _list_json(read: _Read) -> dict[str, Any]:
    record = read.record
    return {
        "id": record.id,
        "name": record.name,
        "online": read.online,
        "ip": read.ip if read.online else None,
        "protocol": record.protocol,
        "key": _key_state(record),
    }


def _cmd_list(args: argparse.Namespace) -> int:
    if not _require_tuya():
        return 1
    loaded = _open_inventory()
    if loaded is None:
        return 3
    inventory, records = loaded
    if not records:
        return _no_bulbs(0)
    reads = _read_many(inventory, records)
    if args.json:
        _json_line({"path": str(inventory.path), "bulbs": [_list_json(r) for r in reads]})
        return 0
    print(f"Inventory: {inventory.path}")
    for read in reads:
        print(_list_line(read))
    return 0


def _look_text(status: BulbStatus) -> str:
    if status.mode == "colour" and status.rgb is not None:
        r, g, b = status.rgb
        return f"#{r:02x}{g:02x}{b:02x}  brightness {status.brightness}%"
    if status.mode == "white" and status.temperature is not None:
        return f"brightness {status.brightness}%  temperature {status.temperature}%"
    return f"brightness {status.brightness}%"


def _status_text(read: _Read) -> str:
    if read.failure is not None:
        return f"failed: {read.failure}"
    if not read.online or read.status is None:
        return "offline"
    status = read.status
    if not status.on:
        return "off"
    return f"{'on':<{POWER_WIDTH}}{status.mode:<{MODE_WIDTH}}{_look_text(status)}"


def _status_json(read: _Read) -> dict[str, Any]:
    record = read.record
    if read.failure is not None:
        return {
            "id": record.id,
            "name": record.name,
            "online": False,
            "status": "failed",
            "reason": read.failure,
        }
    if not read.online or read.status is None:
        return {"id": record.id, "name": record.name, "online": False}
    status = read.status
    return {
        "id": record.id,
        "name": record.name,
        "online": True,
        "on": status.on,
        "mode": status.mode,
        "brightness": status.brightness,
        "temperature": status.temperature,
        "rgb": list(status.rgb) if status.rgb is not None else None,
    }


def _cmd_status(args: argparse.Namespace) -> int:
    if not _require_tuya():
        return 1
    loaded = _open_inventory()
    if loaded is None:
        return 3
    inventory, records = loaded
    if not records:
        return _no_bulbs(0)
    targets = _targets(records, args.target)
    if targets is None:
        return 2
    reads = [_read_one(inventory, record) for record in targets]
    if args.json:
        _json_line({"results": [_status_json(r) for r in reads]})
    else:
        for read in reads:
            print(_name_cell(read.record.name) + _status_text(read))
    return 0 if all(r.online and r.failure is None for r in reads) else 1


# --- control verbs ----------------------------------------------------------------


@dataclass(frozen=True)
class _Outcome:
    """Result of one control command: ``ok`` | ``offline`` | ``failed``."""

    record: BulbRecord
    status: str
    summary: str  # human tail after the name column
    reason: str | None  # JSON ``reason`` (None unless failed)


def _apply(driver: Any, verb: str, args: argparse.Namespace) -> str:
    """Send one command through ``driver`` and return the human tail."""
    if verb == "on":
        driver.set_power(True)
        return "on"
    if verb == "off":
        driver.set_power(False)
        return "off"
    if verb == "toggle":
        status = driver.status()
        driver.set_power(not status.on)
        return "off" if status.on else "on"
    if verb == "bright":
        # BR-11: the target DPS depends on the mode, so read first on the same
        # connection; a failed read becomes an offline result, never a guess.
        status = driver.status()
        driver.set_brightness(args.value, status)
        return f"brightness {args.value}%"
    if verb == "white":
        if args.temp is None:
            # Mode-only payload ({"20": True, "21": "white"}): no read needed.
            driver.set_white(None, None)
            return "white"
        driver.set_white(args.temp, None)
        return f"white {args.temp}%"
    if verb == "color":
        rgb = (args.r, args.g, args.b)
        driver.set_colour(rgb)
        return f"colour #{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    raise ValueError(f"unknown bulb verb {verb!r}")  # pragma: no cover - parser guards this


def _control_one(inventory: BulbInventory, record: BulbRecord, verb: str, args: argparse.Namespace) -> _Outcome:
    driver = None
    try:
        driver = open_bulb(record, inventory)
        summary = _apply(driver, verb, args)
        return _Outcome(record, "ok", summary, None)
    except BulbUnreachable:
        return _Outcome(record, "offline", "offline", None)
    except KeyRejected:
        return _Outcome(record, "failed", f"failed: {KEY_REJECTED_HINT}", KEY_REJECTED_HINT)
    except Exception as e:  # noqa: BLE001 - BulbError and anything else share one shape
        detail = f"{type(e).__name__}: {e}"
        return _Outcome(record, "failed", f"failed: {detail}", detail)
    finally:
        _close(driver)


def _outcome_json(outcome: _Outcome) -> dict[str, Any]:
    return {
        "id": outcome.record.id,
        "name": outcome.record.name,
        "status": outcome.status,
        "reason": outcome.reason,
    }


def _control(args: argparse.Namespace, verb: str) -> int:
    if not _require_tuya():
        return 1
    loaded = _open_inventory()
    if loaded is None:
        return 3
    inventory, records = loaded
    if not records:
        return _no_bulbs(1)
    targets = _targets(records, args.target)
    if targets is None:
        return 2
    outcomes = [_control_one(inventory, record, verb, args) for record in targets]
    if args.json:
        _json_line({"results": [_outcome_json(o) for o in outcomes]})
    else:
        for outcome in outcomes:
            print(_name_cell(outcome.record.name) + outcome.summary)
    return 0 if all(o.status == "ok" for o in outcomes) else 1


def _cmd_on(args: argparse.Namespace) -> int:
    return _control(args, "on")


def _cmd_off(args: argparse.Namespace) -> int:
    return _control(args, "off")


def _cmd_toggle(args: argparse.Namespace) -> int:
    return _control(args, "toggle")


def _cmd_bright(args: argparse.Namespace) -> int:
    return _control(args, "bright")


def _cmd_white(args: argparse.Namespace) -> int:
    return _control(args, "white")


def _cmd_color(args: argparse.Namespace) -> int:
    return _control(args, "color")


# --- remove -----------------------------------------------------------------------


def _cmd_remove(args: argparse.Namespace) -> int:
    if not _require_tuya():
        return 1
    loaded = _open_inventory()
    if loaded is None:
        return 3
    inventory, records = loaded
    if not records:
        return _no_bulbs(1)
    targets = _targets(records, args.target)
    if targets is None:
        return 2
    record = targets[0]
    try:
        removed = inventory.remove(record.id)
    except InventoryFileError as e:
        print(INVENTORY_UNREADABLE.format(reason=e.reason, path=e.path), file=sys.stderr)
        return 3
    if removed is None:
        known = ", ".join(r.name for r in records)
        print(f"error: no bulb named {args.target!r}. Known: {known}", file=sys.stderr)
        return 2
    print(f"Removed {removed.name} ({removed.id}) from {inventory.path}")
    return 0


# --- parser -----------------------------------------------------------------------


def _add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Machine-readable output")


def register_bulb_group(sub: argparse._SubParsersAction) -> None:
    """Register the ``bulb`` group. Built unconditionally, extra or not (BR-17)."""
    bulb = sub.add_parser("bulb", help="Tuya smart bulbs (needs the optional extra [tuya])")
    bulb_sub = bulb.add_subparsers(dest="bulb_cmd", required=True)

    imp = bulb_sub.add_parser("import", help="Import the tinytuya wizard's devices.json")
    imp.add_argument("file", metavar="devices.json")
    _add_json(imp)
    imp.set_defaults(_handler=_cmd_import)

    lst = bulb_sub.add_parser("list", help="List imported bulbs and whether they answer")
    _add_json(lst)
    lst.set_defaults(_handler=_cmd_list)

    st = bulb_sub.add_parser("status", help="Read the state of one bulb, a name, or all")
    st.add_argument("target", nargs="?", default="all", help="Name, device id, or all (default)")
    _add_json(st)
    st.set_defaults(_handler=_cmd_status)

    on = bulb_sub.add_parser("on", help="Switch on (previous mode/colour)")
    on.add_argument("target", help="Name, device id, or all")
    _add_json(on)
    on.set_defaults(_handler=_cmd_on)

    off = bulb_sub.add_parser("off", help="Switch off")
    off.add_argument("target", help="Name, device id, or all")
    _add_json(off)
    off.set_defaults(_handler=_cmd_off)

    toggle = bulb_sub.add_parser("toggle", help="Read, then invert")
    toggle.add_argument("target", help="Name, device id, or all")
    _add_json(toggle)
    toggle.set_defaults(_handler=_cmd_toggle)

    bright = bulb_sub.add_parser("bright", help="Brightness 1–100 of the current mode; switches on")
    bright.add_argument("value", type=_valid_intrange(1, 100))
    bright.add_argument("target", help="Name, device id, or all")
    _add_json(bright)
    bright.set_defaults(_handler=_cmd_bright)

    white = bulb_sub.add_parser("white", help="White mode 0 warm … 100 cold; switches on")
    white.add_argument("--temp", type=_valid_intrange(0, 100), default=None)
    white.add_argument("target", help="Name, device id, or all")
    _add_json(white)
    white.set_defaults(_handler=_cmd_white)

    color = bulb_sub.add_parser("color", help="Colour mode RGB 0–255; switches on")
    color.add_argument("r", type=_valid_intrange(0, 255))
    color.add_argument("g", type=_valid_intrange(0, 255))
    color.add_argument("b", type=_valid_intrange(0, 255))
    color.add_argument("target", help="Name, device id, or all")
    _add_json(color)
    color.set_defaults(_handler=_cmd_color)

    rm = bulb_sub.add_parser("remove", help="Forget a bulb and delete its key")
    rm.add_argument("target", type=_not_all, help="Name or device id (not all)")
    rm.set_defaults(_handler=_cmd_remove)
