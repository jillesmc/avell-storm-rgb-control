---
status: completed
title: "Task 4: Saved bulb state and `state show`"
type: backend
complexity: medium
---

# Task 4: Saved bulb state and `state show`

## Overview

This task extends the saved state with an additive `devices.bulbs` map and teaches `state show` to print it. After it, remembered bulbs and their follow choice survive restarts, agents can inspect them with `state show --json`, and `state restore` still never contacts a bulb.

## Shippable Outcome

- **Outcome:** `state.json` round-trips `DeviceState(bulbs=(BulbState(...),))` through `devices.bulbs` with strict follow validation; a file written by the current release (no `bulbs`) loads with `bulbs == ()`; `state show` prints one `bulb` line per saved bulb with its inventory name and exits 3 when the inventory is corrupt; `state restore` ignores bulbs entirely.
- **Verify in this task:** `tests/test_device_state.py` and `tests/test_cli_state.py` (Tests below).
- **Integration verification:** task_05 proves the GUI-side pruning rule; task_11 re-runs the CLI transcript.

## Requirements

- `_spec.md` → *Data Models* (`state.json` section) and *Core Interfaces* (`Follow`, `BulbState`, `DeviceState.bulbs`); `_dx.md` → *`state.json`* and *`state show` — bulb lines*.
- `BulbState(id, remembered=True, follow="none")`; `DeviceState.bulbs` is a tuple sorted by id.
- Validation message exactly: `bulbs.<id>.follow must be one of none, keyboard, screen, led_bar, got 'music'`; unknown fields elsewhere keep today's behaviour.
- `state show` reads the inventory even when the `tuya` extra is not installed. Missing inventory → every bulb line shows `(not imported)`. Corrupt or unreadable inventory → keyboard/LED bar lines still print, each bulb line reads `<id>  (inventory unreadable)`, the inventory error prints and the command exits 3.
- `state show --json` includes `devices.bulbs` exactly as stored (no names needed). `state restore` prints no bulb line and never calls `open_bulb`.
- Qt-free: `device_state.py` must not import `PySide6` or `tinytuya`.
- This task does not implement the GUI pruning of ids missing from the inventory (UT-035/UT-037 are task_05); it only defines the model and the read-only surfaces.

## Subtasks

- [x] 4.1 `Follow`/`BulbState` and `DeviceState.bulbs` in `device_state.py`.
- [x] 4.2 `state_from_dict`/`state_to_dict` validation and round-trip for `devices.bulbs`, including files without the key.
- [x] 4.3 `_cmd_state_show` bulb lines (human) with inventory names, `(not imported)` and `(inventory unreadable)`.
- [x] 4.4 `state show --json` includes `devices.bulbs`; `state restore` stays bulb-free.
- [x] 4.5 Unit and CLI tests.

## Implementation Details

### Relevant Files

- `src/avell_storm_rgb/application/device_state.py:35-110` — dataclasses and `DeviceState` to extend.
- `src/avell_storm_rgb/application/device_state.py:225-373` — `state_from_dict`, `state_to_dict`, `DeviceStateStore`.
- `src/avell_storm_rgb/adapters/cli/main.py:291-345` — `_cmd_state_show`, `_saved_devices`, `_KIND_LABEL`, `_PREFIX_WIDTH`.
- `src/avell_storm_rgb/adapters/cli/main.py:405-438` — `_cmd_state_restore`, which must stay unchanged.
- `src/avell_storm_rgb/application/bulb_inventory.py` — inventory loading and `InventoryFileError` from task_01.
- `tests/test_device_state.py`, `tests/test_cli_state.py` — existing suites to extend.

### Dependent Files

- `src/app/ui/adapters/app_facade.py` — consumes `DeviceState.bulbs` in task_05; no edit here.

### Related ADRs

- [ADR-001](adrs/adr-001.md) — `state.json` never holds keys.
- [ADR-002](adrs/adr-002.md) — `state restore` does not contact bulbs.

## Deliverables

- `BulbState`, `Follow` and `DeviceState.bulbs` in `src/avell_storm_rgb/application/device_state.py`
- Extended `state show` in `src/avell_storm_rgb/adapters/cli/main.py`
- New cases in `tests/test_device_state.py` and `tests/test_cli_state.py`

## Tests

- [x] UT-034 — `devices.bulbs` round-trip through the store
- [x] UT-036 — `state restore` never calls `open_bulb` and prints no bulb line
- [x] UT-038 — invalid follow value raises the exact `ValueError`
- [x] UT-039 — a file without `bulbs` loads with `bulbs == ()`
- [x] E2E-013 — `state show` bulb lines and `--json` containing `devices.bulbs`
- [x] E2E-016 — corrupt inventory → `(inventory unreadable)` + exit 3; missing inventory → `(not imported)` + exit 0

## Success Criteria

- `make test` is green, including the existing state and CLI suites.
- `grep -rn "PySide6\|tinytuya" src/avell_storm_rgb/application/device_state.py` finds nothing.
- A `state.json` written by the current release still loads and rewrites without adding `devices.bulbs`.
- `state show` with a corrupt inventory prints the keyboard/LED bar lines before the inventory error and exits 3.
