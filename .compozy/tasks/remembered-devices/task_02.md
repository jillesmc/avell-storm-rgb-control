---
status: pending
title: "Task 2: Backends save looks, toggle the light and restore"
type: feature
complexity: high
---

# Task 2: Backends save looks, toggle the light and restore

## Overview

This task changes the keyboard and LED bar backends:
- they report every successfully applied look as a `persistUpdate`;
- they expose a `lightOn` / `setLightOn` pair;
- they can `restore(state)` a saved state through the USB worker.

The old footer power buttons and replay machinery go away. task_03 consumes these signals and methods to remember and restore devices.

## Shippable Outcome

- **Outcome:** in the GUI, the footers no longer show **Power on / Power off**. Each backend emits `persistUpdate` after every successful apply and can turn its light off/on, re-applying the last look.
- **Verify in this task:** the backend suites with fake drivers and a real `UsbWorker` (Tests below).
- **Integration verification:** task_03 (IT-002, IT-006, IT-009, IT-010 exercise these backends through the facade); task_04 (E2E-007, footer absence).

## Requirements

- Contract: `_spec.md` → *Core Interfaces* (`KeyboardBackend` / `LedBarBackend` blocks).
- Rules: BR-4, BR-5, BR-6, BR-7, BR-8, BR-11; KD-3, KD-5, KD-6.
- `persistUpdate` payload keys:
  - `look` (`device_state` look objects), `palette` (`{slot: rgb}`), `brightness` (int), `power` (`"on"` / `"off"`);
  - emitted **from inside the USB task after the driver call returns** (Safety Invariant 2);
  - per-key looks converted to device coordinates (KD-4).
- Not a look (no `look` key): follow-screen, demo test pattern, freeze.
- BR-11 / Safety Invariant 7: `setLightOn(False)`, any new keyboard look, and `disconnectDevice()` set `_follow_stop` on the GUI thread **before** submitting.
- `restore(state)` uses `device_state.restore_keyboard` / `restore_led_bar` inside a worker task. `pending_animation` is submitted afterwards as the existing long task (`playAnimationFile` path), and warnings go to `opFailed`-style user messages.
- Keyboard `lightOn` = connected and not `is_off()` (refreshed by inspect). LED bar `lightOn` is tracked from the last power command.
- Hard-cut, with no shim (`_spec.md` → *Impact Analysis*, delete targets):
  - `KeyboardBackend.powerOff`, `powerOnReplay`, `replayPowerOnAvailable` (QML-facing);
  - `LedBarBackend.powerOn`, `powerOnReplay`, `powerOff`, `replayPowerOnAvailable`, `replayModeUpdate`, `_last_replay`, `_replay_last_on_device`, `_effect_name_from_replay`;
  - the footer **Power off / Power on** buttons in `KeyboardPage.qml` and `LedBarPage.qml`.
- Keep the keyboard effect snapshot as the private fallback for BR-7.

## Subtasks

- [ ] 2.1 Keyboard: emit `persistUpdate` from effect, solid, per-key Apply, animation start, palette slot/restore/random and brightness flush.
- [ ] 2.2 Keyboard: `lightOn`, `setLightOn`, BR-7 fallback (snapshot → `rainbow`), BR-8, BR-11 stop rule.
- [ ] 2.3 LED bar: replace replay records with full-parameter looks (KD-5); `lightOn`, `setLightOn`, `persistUpdate`.
- [ ] 2.4 Both: `restore(state)` via worker using the core restore functions; animation submitted last.
- [ ] 2.5 Remove the footer power buttons and the hard-cut members; rewrite `tests/test_*_power_replay.py`.

## Implementation Details

### Relevant Files

- `src/app/ui/adapters/keyboard_backend.py:92-138` — state fields and queued signal wiring to extend.
- `src/app/ui/adapters/keyboard_backend.py:293-363` — connect/disconnect/powerOff/powerOnReplay and the snapshot pattern.
- `src/app/ui/adapters/keyboard_backend.py:401-576` — brightness debounce, `applyEffect`, solid, palette slots.
- `src/app/ui/adapters/keyboard_backend.py:596-732` — animation, follow-screen, stop event, per-key grid.
- `src/app/ui/adapters/led_bar_backend.py:16-294` — the whole backend; replay record replaced.
- `src/app/core/usb_worker.py:16-49` — `submit(show_busy)` semantics.
- `src/avell_storm_rgb/domain/per_key_grid.py:182-199` — UI → device row flip.

### Dependent Files

- `src/app/ui/pages/KeyboardPage.qml:1203-1213` — footer **Power off** to remove.
- `src/app/ui/pages/LedBarPage.qml:444-459` — footer **Power off / Power on** to remove.
- `tests/test_keyboard_backend_power_replay.py`, `tests/test_led_bar_backend_power_replay.py` — rewritten for light toggle and persisted looks.

### Related ADRs

- [ADR-002: Implicit "last applied look"](adrs/adr-002.md) — what triggers a save.

## Deliverables

- Updated backends and pages.
- Backend test suites (rename to `test_keyboard_backend_light.py` / `test_led_bar_backend_light.py` or keep the names).

## Tests

- [ ] UT-040, UT-041, UT-042, UT-043, UT-044, UT-045, UT-046, UT-047, UT-048, UT-049 — keyboard persist and the stop-before-disconnect rule
- [ ] UT-050, UT-051, UT-052, UT-053 — LED bar persist
- [ ] UT-060, UT-061, UT-062, UT-063, UT-064, UT-065, UT-066, UT-067 — light toggle

## Success Criteria

- `make test` is green.
- `grep -rn "powerOnReplay\|replayPowerOnAvailable\|replayModeUpdate" src` finds nothing.
