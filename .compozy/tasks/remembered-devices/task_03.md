---
status: completed
title: "Task 3: App remembers devices and restores them at startup"
type: feature
complexity: high
---

# Task 3: App remembers devices and restores them at startup

## Overview

This task solves the Motivating Problem end to end. Connecting a device on **Devices** remembers it; Disconnect forgets it. Every app start reconnects remembered devices and re-applies their saved look and light state. The old auto-connect setting is migrated and removed, and the sidebar switch becomes the light switch.

## Shippable Outcome

- **Outcome:** the user connects the keyboard on Devices, picks an effect and quits. On reopening, the keyboard reconnects and shows that effect without any click. Flipping the sidebar switch turns the light off/on, and that state is restored at the next start.
- **Verify in this task:** the facade unit and integration suites with a real `UsbWorker`, a real store in `tmp_path` and fake USB (Tests below).
- **Integration verification:** task_04 (E2E-004, E2E-005 through the loaded QML).

## Requirements

- Contract: `_spec.md` → *Core Interfaces* (`AppFacade` block); rules BR-1–BR-3, BR-6, BR-9, BR-10, BR-12, BR-14, BR-15; KD-1, KD-7.
- `AppFacade` owns one `DeviceStateStore`. It is the **only writer** (Safety Invariants 1 and 3); it merges `persistUpdate` payloads on the GUI thread and saves.
- Remember on **successful** connect only (BR-1a): on `connectedChanged → True`, record the `usb_id` (`usb_id_of`) with `remembered: true`.
- `restoreRememberedDevices()`:
  - replaces `tryAutoConnectDiscoveredDevices()`;
  - order: LED bar, then keyboard; animation last (Safety Invariant 6);
  - each absent or failing device is marked unavailable with its reason (no popup).
- `retryDevice(kind)` rescans and reconnects one kind. `forgetDevice(kind)` sets `remembered: false` and keeps the look.
- Migration (BR-14), once, when no state file exists: read the legacy `QSettings` `ui/autoConnectOnStartup` (absent ⇒ true), remember the first discovered devices or none, always write `state.json`, then delete the key.
- Invalid file (BR-15): quarantine and set `App.state.lastError` with the exact `_dx.md` message.
- Hard-cut (`_spec.md` → *Impact Analysis*): `autoConnectOnStartup`, `tryAutoConnectDiscoveredDevices`, `connectFirstDiscovered`, and the Settings auto-connect checkbox (`SettingsPage.qml:56-63`).
- Sidebar switch (`_uiux.md` S2): `checked` ← `lightOn`, `onToggled` → `setLightOn`, `enabled` ← connected. This is needed because `connectFirstDiscovered` disappears in this task.
- `main.qml` startup calls `App.refreshDevices()` then `App.restoreRememberedDevices()`.

## Subtasks

- [x] 3.1 Store ownership, `persistUpdate` merge/save, save-error message (US-012.EC-2).
- [x] 3.2 Remember on connect, forget on disconnect, `forgetDevice`, `retryDevice`, the remembered/unavailable properties and `deviceMemoryChanged`.
- [x] 3.3 `restoreRememberedDevices` with ordering and unavailable reasons; missing-animation message.
- [x] 3.4 Migration from `ui/autoConnectOnStartup`; invalid-file quarantine.
- [x] 3.5 QML: startup call, sidebar switch → light, remove the Settings checkbox.
- [x] 3.6 Rewrite `tests/test_app_facade_autoconnect.py` into remember/restore/migration suites.

## Implementation Details

### Relevant Files

- `src/app/ui/adapters/app_facade.py:44-76` — init, `QSettings` reads, backend wiring.
- `src/app/ui/adapters/app_facade.py:118-146` — `isDeviceOpenInApp`, `disconnectDeviceKind`.
- `src/app/ui/adapters/app_facade.py:242-300` — `refreshDevices`, `connectFirstDiscovered`, `tryAutoConnectDiscoveredDevices`, `connectDevice`, `shutdown`.
- `src/app/core/devices.py:14-49` — enumeration dicts (`vid`, `pid`, `bus`, `addr`).
- `src/app/ui/main.qml:97-131` — startup calls and nav model.
- `src/app/ui/main.qml:272-293` — the sidebar `Switch`.
- `src/app/ui/pages/SettingsPage.qml:56-63` — the checkbox to remove.
- `tests/test_app_facade_autoconnect.py:20-32` — isolated `QSettings` fixture to reuse.

### Dependent Files

- `tests/gui_helpers.py` — the facade constructor and startup calls may change; keep the helpers working.

### Related ADRs

- [ADR-001](adrs/adr-001.md) — single writer, quarantine.
- [ADR-002](adrs/adr-002.md) — what gets saved.

## Deliverables

- Updated `AppFacade`, `main.qml` (startup + switch) and `SettingsPage.qml`.
- `tests/test_app_facade_memory.py` (replacing `test_app_facade_autoconnect.py`), `tests/test_app_restore_integration.py`.

## Tests

- [x] UT-030, UT-031, UT-032, UT-033, UT-034, UT-035, UT-036, UT-037, UT-038 — device memory
- [x] UT-090, UT-091, UT-092, UT-093 — migration
- [x] IT-001, IT-002, IT-003, IT-004, IT-005, IT-006, IT-007, IT-008, IT-009, IT-010, IT-011, IT-012 — facade + backends + worker + store

## Success Criteria

- `make test` is green.
- `grep -rn "autoConnectOnStartup\|connectFirstDiscovered\|tryAutoConnect" src tests` finds nothing, except migration code that reads the legacy key name.

## Completion Notes

- Backends gained a `connectFailed(str)` signal (emitted before re-raising inside the connect task). The facade uses it to show the USB error as the unavailable reason (UT-038) and to remember nothing on a failed Devices connect (BR-1a). `AppState.reportError(str)` shows a message without touching the busy counter.
- `connectDevice` also applies the saved look of that kind when one exists, so a forgotten device comes back as it was (US-003.AC-3).
- `refreshDevices` retries remembered devices that are currently unavailable (US-004.AC-2 "or Refresh list"). An invalid state file is never auto-migrated (BR-14 + BR-15).
- `tests/conftest.py` isolates `XDG_CONFIG_HOME` for every test, so GUI tests never touch the real `state.json`. Old `test_app_facade_autoconnect.py` replaced.
- Evidence: `tests/test_app_facade_memory.py` + `tests/test_app_restore_integration.py` (27 passed, includes a GUI-thread check for state writes); full suite 110 passed ×3; no QML binding errors on load; grep for removed names → only `LEGACY_AUTO_CONNECT_KEY`.
