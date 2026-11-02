# Task 07 — follow keyboard and LED bar

Status: completed (uncommitted).

- `keyboard_backend._ColourTap` wraps the driver in `connectAt`; `KeyboardBackend.colorsSent(int,int,int)`
  (USB thread; AppFacade connects it queued → `bulbs.feed_colour("keyboard", rgb)`).
- LED bar source: `AppFacade._on_persist("led_bar")` → `_feed_led_bar_colour()` = average of the saved
  palette while `power == "on"`. Nothing at startup (restore never persists).
- `src/app/ui/adapters/bulb_follow.py`: `BulbFollower(worker, *, power_on, read_status)`; per-bulb
  250 ms tick + 5 s status read; `feed(source, rgb)`, `set_source(id, source)`, `stop_all()`,
  `source_of(id)`. Tests drive `_tick(id)` directly.
- `BulbsBackend._sync_follow()` runs inside every `_changed()`: follow is active only when the bulb is
  remembered, has a saved source, a known status and no failure. That covers disconnect/forget,
  unavailable (UT-098) and startup resume after the first read (IT-013).
- `BulbWorker.run_after(id, fn)` (no driver) and `set_hold_open` now return the Future; a failing task on a
  held bulb clears the hold and calls `hold_open(False)` + `close()`.
- `removeBulb` now writes the inventory on the bulb's queue after the close (UT-080), and hides the id
  through `_removing` meanwhile. Tests must drain the bulb worker before checking the inventory.
- `availableFollowSources` comes from `AppFacade._follow_sources()` (keyboard/led_bar when connected).
  task_08 adds `screen` there (only with the `screen` extra).
- QML: `bulbFollowCombo` + `bulbFollowMessage` on `BulbPage.qml`.
- Verification: `uv run --with "PySide6==6.12.0" pytest -q -m "not hardware"` → 510 passed.
