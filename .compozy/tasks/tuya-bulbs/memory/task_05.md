# Task 05 — GUI bulb backend, worker and startup refresh

Status: completed (uncommitted).

## Landed

- `src/app/core/bulb_worker.py` — `BulbWorker(open_driver, parent, *, name_of=None)`; one
  `ThreadPoolExecutor(1, "bulb")` per bulb; `submit(id, fn)` opens lazily, closes after the task
  unless held; any exception → `opDone(id, BulbFailure)` + `opFailed(text)`.
  `describe_failure(name, exc)` builds the `_dx.md` texts (row reason vs banner).
- `src/app/ui/adapters/bulb_model.py` — `BulbListModel`, roles = `ROLE_KEYS` (spec table).
- `src/app/ui/adapters/bulbs_backend.py` — `BulbsBackend(app_state, *, saved, available, inventory, open_driver)`.
  Rows come from the inventory (names sorted); remembered/follow from `saved()` (AppFacade).
  `bulb(id)` returns `{}` for an unknown id.
- `AppFacade`: `bulbsAvailable`, `bulbs`, `setWindowVisible`, `_on_bulb_persist` (direct connection),
  `_pruned()` applied in every `_save()`.
- Tests: `test_bulb_worker.py`, `test_bulbs_backend.py`, `test_app_facade_bulbs.py`,
  `test_app_bulbs_integration.py`; `FakeBulb` + `drain_bulbs` in `tests/backend_fakes.py`.

## Decisions task_06+ must know

- `windowVisible` starts **false**; `main.qml` must call `App.setWindowVisible(visible)`.
  The first `true` refreshes once and starts the 30 s timer.
- `refresh()` skips bulbs that already have a read in flight (`_reading`), so the startup pair
  `refreshDevices()` + `restoreRememberedDevices()` reads each bulb once.
- Queued commands build on `_chain` (latest status seen on that bulb's thread), not on the
  GUI row cache, so `setWhite` then `setBrightness` don't clobber each other. The row cache
  still changes only in `_on_op_done`.
- Any failed operation sets `unavailableReason` (row `available=false`, subtitle `offline`).
- `subtitle` is `""` for a never-connected, not-remembered bulb with no read yet.
- `setFollow` only persists; `availableFollowSources` returns `[]` until task_07/08.
- Tests patch `app.ui.adapters.app_facade.tuya_available` and
  `avell_storm_rgb.application.bulb_facade.open_bulb` (looked up lazily per open).

## Verification

- `uv run pytest -q -m "not hardware"` → 464 passed, 11 skipped, 5 failed (the known
  `test_gui_pages.py` Qt-style failures).
- `grep -rn UsbWorker src/app/core/bulb_worker.py src/app/ui/adapters/bulbs_backend.py` → none.
