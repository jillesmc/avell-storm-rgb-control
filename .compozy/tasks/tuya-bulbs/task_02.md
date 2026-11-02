---
status: completed
title: "Task 2: Tuya LAN adapter and bulb opener"
type: backend
complexity: high
---

# Task 2: Tuya LAN adapter and bulb opener

## Overview

This task adds the only code that imports `tinytuya` and the opener that finds a bulb on the LAN. After it, `open_bulb(record, inventory)` returns a `BulbDriver` that reads real status, writes the four control payloads and maps tinytuya's error dicts without ever surfacing a key or a payload. It also adds the optional `tuya` extra that gates every later surface.

## Shippable Outcome

- **Outcome:** with `uv sync --extra tuya`, `open_bulb()` resolves an IP in the order process cache → ARP by MAC → `last_ip` → UDP discovery, writes a changed IP back to the inventory, and returns a `TuyaBulb` whose `status`, `set_power`, `set_brightness`, `set_white`, `set_colour` and `push_colour` match `_spec.md`. Without the extra, `tuya_available()` is `False` and importing the package still works.
- **Verify in this task:** `tests/test_tuya_bulb_adapter.py` (`pytest.importorskip("tinytuya")`) and `tests/test_bulb_facade.py` (Tests below).
- **Integration verification:** task_03 exercises the real opener through the CLI; task_05 uses it from `BulbWorker`.

## Requirements

- Interfaces exactly as `_spec.md` → *Core Interfaces* (`BulbDriver`, `tuya_available`, `open_bulb`), *Integration Points* (error mapping, 914 retry, ARP, UDP) and *Monitoring and Observability* (logger pin).
- `pyproject.toml` extra `tuya = ["tinytuya>=1.20,<2"]`, added with `uv add --optional tuya "tinytuya>=1.20,<2"`; `uv.lock` updated.
- `tinytuya` is imported **lazily inside functions**, only in `src/avell_storm_rgb/infrastructure/tuya/`, so `import avell_storm_rgb` and the CLI work without the extra.
- DPS contract: `set_brightness(percent, status)` → DPS 22 in white mode, DPS 24 (same hue/sat, V = percent) in colour mode, plus `20: True`; `set_white(temp|None, status)` → DPS 21/23, omitting 23 when both are unknown; `set_colour` → DPS 21/24; `push_colour` → DPS 21/24 with `nowait=True` and **never** DPS 20 (KD-6, BR-12).
- `status=None` means read once on the same driver before writing (BR-11); no second connection.
- Error mapping: `Err` 914 → `KeyRejected`; 901, 902, 905 and timeouts → `BulbUnreachable`; anything else → `BulbError`. Only the exception type and a fixed phrase reach the message; `Error`/`Payload` never do.
- 914: run one UDP discovery for that id; retry the call once only when the discovered version differs from the stored one; otherwise raise `KeyRejected("local key or protocol rejected")`.
- Logger: immediately after the lazy import, `logging.getLogger("tinytuya").setLevel(logging.WARNING)`; `tinytuya.set_debug()` is never called.
- `BulbRecord` and `TuyaBulb` `repr`/`str` never contain the key (UT-072).
- No Qt import in the core; the GUI never calls this module on its own thread (task_05 owns that).

## Subtasks

- [x] 2.1 Add the `tuya` extra and refresh `uv.lock`.
- [x] 2.2 `infrastructure/tuya/bulb.py`: lazy import, logger pin, `status_from_dps`, DPS writers, error inspection, one-shot 914 retry.
- [x] 2.3 `application/bulb_facade.py`: `tuya_available()` and `open_bulb()` with cache, `ip neigh` ARP lookup, `last_ip`, UDP discovery, write-back and `BulbUnreachable`.
- [x] 2.4 Stub `tinytuya.BulbDevice` test double and fake ARP/discovery callables.
- [x] 2.5 Adapter and opener unit suites, including the payload-leak and repr assertions.

## Implementation Details

### Relevant Files

- `src/avell_storm_rgb/application/bulb_inventory.py` — `BulbRecord`, `set_last_ip`, `BulbFailure` from task_01.
- `src/avell_storm_rgb/ports/protocols.py` — `BulbDriver` from task_01.
- `src/avell_storm_rgb/infrastructure/usb/discovery.py:23-48` — existing discovery style and logging.
- `src/avell_storm_rgb/application/device_facade.py:22-53` — opener shape and error text conventions.
- `src/app/logutil.py` — logging helpers; the tinytuya logger pin is separate and unconditional.

### Dependent Files

- `pyproject.toml`, `uv.lock` — the new extra.
- `tests/backend_fakes.py` — `FakeBulb` (task_05) implements the same port; keep it in sync.

### External References

- `~/git/iot/bulbs.py` — the script being replaced: name matching, ARP lookup, brightness mapping.
- `~/git/iot/.venv/lib/python3.13/site-packages/tinytuya/BulbDevice.py:393-418` and the `set_colour`/`set_white` `check_values` with `'switch': True` — why `push_colour` writes DPS directly (KD-6). External, not vendored.

### Related ADRs

- [ADR-001](adrs/adr-001.md) — optional extra and key privacy.
- [ADR-002](adrs/adr-002.md) — read-not-restore and `push_colour` never writing power.
- [ADR-003](adrs/adr-003.md) — one driver per bulb; this adapter is the object the worker owns.

## Deliverables

- `src/avell_storm_rgb/infrastructure/tuya/__init__.py`, `src/avell_storm_rgb/infrastructure/tuya/bulb.py`
- `src/avell_storm_rgb/application/bulb_facade.py`
- `tuya` extra in `pyproject.toml` and `uv.lock`
- `tests/test_tuya_bulb_adapter.py`, `tests/test_bulb_facade.py`

## Tests

- [x] UT-020, UT-021, UT-022, UT-023, UT-024, UT-026, UT-027 — DPS payloads per mode, white fallback, status read on the same driver, `push_colour` without DPS 20
- [x] UT-025, UT-028 — error-dict mapping, 914 discovery/retry, no payload in messages
- [x] UT-030, UT-031, UT-032 — IP resolution order, write-back only on change, exhausted resolution
- [x] UT-033 — `tuya_available()` follows `find_spec("tinytuya")`
- [x] UT-072, UT-073 — `repr`/`str` and surfaced errors never contain the key or a payload

## Success Criteria

- `uv sync --extra tuya` then `make test` is green, including the existing suites.
- `uv sync` without the extra still imports `avell_storm_rgb` and runs the CLI; the adapter suites skip via `importorskip`.
- `grep -rnE "^(from|import) tinytuya" src/avell_storm_rgb --include='*.py'` matches only `infrastructure/tuya/`; `bulb_facade.py` may name the module only inside `find_spec("tinytuya")`.
- `grep -rn "set_debug" src tests` finds no call outside the spy/assertion in the test.
