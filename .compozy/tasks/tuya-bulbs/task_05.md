---
status: completed
title: "Task 5: GUI bulb backend, worker and startup refresh"
type: feature
complexity: high
---

# Task 5: GUI bulb backend, worker and startup refresh

## Overview

This task makes bulbs first-class GUI devices below the QML layer: `App.bulbs` can import, connect, remember, forget, remove, retry and control bulbs through a per-bulb worker, and `AppFacade` becomes the only writer of `devices.bulbs`. After it, every bulb behaviour is testable headlessly; task_06 only adds the QML surfaces.

## Shippable Outcome

- **Outcome:** with a real `DeviceStateStore` in `tmp_path` and a `FakeBulb` factory, `App.bulbs.importFile`, `connectBulb`, `disconnectBulb`, `forgetBulb`, `removeBulb`, `retryBulb`, `refresh`, `setLightOn`, `setBrightness`, `setWhite` and `setColor` work through `BulbWorker`; results reach the row cache only through `opDone` on the GUI thread; `App.bulbs.windowVisible` drives a 30 s refresh that stops while hidden; startup reads remembered bulbs without sending a command.
- **Verify in this task:** `tests/test_bulb_worker.py`, `tests/test_bulbs_backend.py`, `tests/test_app_facade_bulbs.py`, `tests/test_app_bulbs_integration.py` (Tests below).
- **Integration verification:** task_06 proves the same wiring through the loaded QML.

## Requirements

- Interfaces exactly as `_spec.md` → *Core Interfaces* (`BulbWorker`, `BulbsBackend`, `AppFacade` additions) and *Data Models* → `BulbListModel` roles and `bulb(id)` snapshot.
- `BulbWorker`: one single-thread executor **per bulb** (`thread_name_prefix="bulb"`), FIFO per bulb, parallel across bulbs, `opDone(str, object)` and `opFailed(str)`; `submit` opens the driver lazily through `open_driver(bulb_id)` and closes it after the task unless `set_hold_open(id, True)`; `shutdown` closes every session. Never touch `UsbWorker`, never emit `opStarted`, never set `AppState.busy`.
- `BulbsBackend`: row cache, `bulbEpoch`, `modelChanged`, `importSummary`, `windowVisible`, all slots from the contract, `bulb(id)` snapshot, and `_on_op_done` as the **only** place a worker result reaches the cache. `opFailed` goes to `AppState.reportError` with the bulb name.
- `AppFacade`: `bulbsAvailable` = `tuya_available()`; `bulbs` property (inert when unavailable); `_on_bulb_persist` as the only writer of `devices.bulbs`; `setWindowVisible`; `restoreRememberedDevices()` calls `bulbs.refresh()` after LED bar and keyboard; `refreshDevices()` also refreshes bulbs.
- Pruning rule (UT-035/UT-037): drop `devices.bulbs` ids missing from the inventory **only** when `tuya_available()` is true and the inventory loaded successfully. An absent extra, or a missing/corrupt/unreadable inventory, keeps every entry and rewrites it unchanged.
- Connect remembers only after a successful status read (BR-4). Double connect before the first completes → one read, one `opDone`, one `persistUpdate`.
- Commands are never optimistic: the row changes only when `opDone` arrives. A failed command leaves the previous real value and reports the bulb.
- Import while connected keeps the bulb working; the next command opens with the new key (inventory is read per open, not cached).
- `FakeBulb` in `tests/backend_fakes.py` implements `BulbDriver`: journal, programmable `BulbStatus`, `fail_on`, `unreachable`, open count, optional `reject_second_connection`.

## Subtasks

- [x] 5.1 `BulbWorker` with per-bulb executors, lazy driver lifetime, hold-open and shutdown.
- [x] 5.2 `BulbListModel` roles and the row cache behind `bulb(id)`.
- [x] 5.3 `BulbsBackend` slots, `opDone`/`opFailed` handling, import summary, refresh timer and visibility.
- [x] 5.4 `AppFacade` wiring, `_on_bulb_persist`, pruning, startup and Devices refresh.
- [x] 5.5 `FakeBulb` plus the worker/backend/facade/integration suites.

## Implementation Details

### Relevant Files

- `src/app/core/usb_worker.py:16-49` — signal/executor pattern `BulbWorker` mirrors, without sharing the USB thread.
- `src/app/ui/adapters/device_model.py:1-52` — list-model pattern for `BulbListModel`.
- `src/app/ui/adapters/app_facade.py:76-117` — construction and backend signal wiring.
- `src/app/ui/adapters/app_facade.py:325-380` — `refreshDevices`, `restoreRememberedDevices`, `shutdown`.
- `src/app/ui/adapters/app_facade.py:500-549` — `_set_remembered`, `_on_connected_changed`, `_on_connect_failed`, `_on_persist` (single-writer path).
- `src/app/ui/adapters/app_state.py:8-58` — `reportError` and the busy counter that bulbs must not touch.
- `src/avell_storm_rgb/application/bulb_facade.py` — `open_bulb`, `tuya_available`.
- `src/avell_storm_rgb/application/device_state.py` — `BulbState`, `DeviceState.bulbs` from task_04.
- `tests/backend_fakes.py`, `tests/conftest.py`, `tests/facade_harness.py` — fakes and isolated `XDG_CONFIG_HOME`.

### Dependent Files

- `tests/gui_helpers.py` — may need the bulbs backend in the harness; keep the existing helper calls working.
- `src/app/ui/adapters/keyboard_backend.py`, `led_bar_backend.py` — no edit here; task_07 adds the follow sources.

### Related ADRs

- [ADR-002](adrs/adr-002.md) — startup/refresh only read.
- [ADR-003](adrs/adr-003.md) — per-bulb serial queues and one driver per bulb.

## Deliverables

- `src/app/core/bulb_worker.py`
- `src/app/ui/adapters/bulb_model.py`, `src/app/ui/adapters/bulbs_backend.py`
- `AppFacade` additions in `src/app/ui/adapters/app_facade.py`
- `FakeBulb` in `tests/backend_fakes.py`
- `tests/test_bulb_worker.py`, `tests/test_bulbs_backend.py`, `tests/test_app_facade_bulbs.py`, `tests/test_app_bulbs_integration.py`

## Tests

- [x] UT-035, UT-037 — GUI pruning only when the extra and inventory load succeed; entries kept when the extra is absent
- [x] UT-040, UT-041, UT-042, UT-043 — connect remembers, unreachable/key-rejected errors, double connect
- [x] UT-044, UT-045 — disconnect keeps the key; remove deletes record and state
- [x] UT-046, UT-047, UT-048, UT-049, UT-050, UT-051 — read-only refresh, unknown snapshot, unavailable reason, retry, no busy
- [x] UT-052, UT-053 — light switch applied only on `opDone`; failure keeps the real value
- [x] UT-054, UT-055, UT-056, UT-057 — 30 s timer, one immediate refresh on show, stop while hidden, property forwarding
- [x] UT-060, UT-061, UT-062, UT-063, UT-064 — per-bulb concurrency, FIFO order, `bulb-*` threads, GUI-thread `opDone`, one held driver
- [x] IT-001, IT-002, IT-003, IT-004, IT-005, IT-006 — import/connect/disconnect/remove round-trip, startup reads only, re-import key, no keys in debug logs

## Success Criteria

- `make test` is green, including the existing GUI suites.
- `grep -rn "UsbWorker" src/app/core/bulb_worker.py src/app/ui/adapters/bulbs_backend.py` finds no use.
- A bulb operation never changes `App.state.busy`; the existing BusyOverlay tests stay green.
- `state.json` is written only by `AppFacade`, and a corrupt/missing inventory never drops `devices.bulbs`.
