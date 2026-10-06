---
status: pending
title: "Task 1: Saved device state core"
type: backend
complexity: medium
---

# Task 1: Saved device state core

## Overview

This task adds the Qt-free model, JSON store and restore functions for the saved state of each device, and lets the core open a device by its USB id. Every later task builds on it:
- task_02 (backends save and restore looks);
- task_03 (the app remembers and restores devices);
- task_05 (the CLI reads and restores the state).

## Shippable Outcome

- **Outcome:** `avell_storm_rgb.application.device_state` round-trips a `DeviceState` through `state.json` atomically, quarantines invalid files, and restores a keyboard / LED bar onto any driver that follows the `ports` protocols. `device_facade` opens devices by `usb_id`.
- **Verify in this task:** the unit suites for the store, validation, restore and open-by-USB-id (Tests below) plus the existing `tests/test_keyboard_effect_supports.py` after the KD-9 move.
- **Integration verification:** none (consumers verify their wiring in task_02, task_03 and task_05).

## Requirements

- Interfaces exactly as in `_spec.md` → *Core Interfaces* (`device_state.py`, `device_facade.py` additions).
- Data rules: `_spec.md` → *Data Models*. File shape: `_dx.md` → *State file*.
- Safety Invariants 1, 3, 5 and 8 hold for this module. Writes are atomic (KD-2). No PySide6 import.
- KD-9:
  - move `EFFECT_KWARGS` from `src/app/ui/adapters/keyboard_backend.py` to `ite8291_usb.KEYBOARD_EFFECT_PARAMS`;
  - update its importer (`keyboard_backend.py`, `effectSupports`) in the same change;
  - leave no copy and no re-export.
- The restore functions drop parameters an effect doesn't accept (via `KEYBOARD_EFFECT_PARAMS`), never apply the look when `power == "off"`, and return animations as `pending_animation` instead of running them.
- `describe_look` strings exactly as in `_dx.md` (they are part of the CLI contract).

## Subtasks

- [ ] 1.1 Move `EFFECT_KWARGS` → `KEYBOARD_EFFECT_PARAMS` and update the importer.
- [ ] 1.2 Model dataclasses + strict validation + JSON (de)serialisation (`version: 1`).
- [ ] 1.3 `DeviceStateStore`: path resolution, `load`, atomic `save` (0700 dir / 0600 file), `quarantine`, `exists`.
- [ ] 1.4 `restore_keyboard`, `restore_led_bar`, `RestorePlan`, `describe_look`.
- [ ] 1.5 `device_facade`: `usb_id` filter for `open_keyboard` / `open_led_bar`, and `usb_id_of`.

## Implementation Details

The new module lives at `src/avell_storm_rgb/application/device_state.py`. Follow `_spec.md` Part II *Core Interfaces* and *Data Models*.

### Relevant Files

- `src/avell_storm_rgb/infrastructure/usb/ite8291_usb.py:38-158` — effect builders, slot colours, directions; destination of `KEYBOARD_EFFECT_PARAMS`.
- `src/avell_storm_rgb/infrastructure/usb/ite8291_usb.py:334-363` — keyboard matching by vendor/product/rev.
- `src/avell_storm_rgb/infrastructure/usb/ite8233_usb.py:28-129` — LED bar driver attributes and the effect codes used by the restore.
- `src/avell_storm_rgb/infrastructure/usb/discovery.py:23-48` — LED bar enumeration.
- `src/avell_storm_rgb/application/device_facade.py:22-53` — openers to extend.
- `src/avell_storm_rgb/ports/protocols.py:7-42` — the driver protocols the restore functions use.
- `src/avell_storm_rgb/domain/ledbar_colors.py:52` — `MAX_LED_BAR_PALETTE`.

### Dependent Files

- `src/app/ui/adapters/keyboard_backend.py:52-62,285-290` — `EFFECT_KWARGS` and `effectSupports` switch to the moved table.
- `tests/test_keyboard_effect_supports.py` — must stay green after the move.

### Related ADRs

- [ADR-001: Saved device state in a Qt-free JSON file](adrs/adr-001.md) — this task implements it.

## Deliverables

- `src/avell_storm_rgb/application/device_state.py`
- `KEYBOARD_EFFECT_PARAMS` in `ite8291_usb.py`; `device_facade.py` additions
- `tests/test_device_state.py`, `tests/test_device_facade_usb_id.py`

## Tests

- [ ] UT-001, UT-002, UT-003, UT-004, UT-005, UT-006, UT-007, UT-008, UT-009 — store, validation, quarantine, atomicity, Qt-free import
- [ ] UT-010, UT-011, UT-012, UT-013, UT-014, UT-015, UT-016, UT-017 — restore functions and `describe_look`
- [ ] UT-020, UT-021, UT-022 — open by USB id

## Success Criteria

- `make test` is green, including the existing suites.
- `grep -rn EFFECT_KWARGS src` finds nothing.
