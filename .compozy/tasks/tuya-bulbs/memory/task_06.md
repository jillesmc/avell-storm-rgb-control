# Task 06 — bulb surfaces (Devices, sidebar, page)

Status: completed (uncommitted).

- `components/BulbListPanel.qml` (loaded through a `Loader` on `App.bulbsAvailable`, so it is absent
  without the extra), `pages/BulbPage.qml` at stack index 5, `forgetHint` on `DeviceUnavailablePanel`.
- `main.qml`: `selectedBulbId`, bulb sidebar entries from `App.bulbs.rememberedBulbs()` (new slot,
  returns remembered row snapshots sorted by name), rebuild on `App.bulbs.modelChanged`, six edits,
  `onVisibleChanged: App.setWindowVisible(visible)`. Every `primaryNavModel` entry carries the bulb
  keys (`bulbId`, `lightOn`, `available`, `stateKnown`, `unavailableReason`) so ListModel roles stay uniform.
- Remove dialog actions go through panel functions `askRemove/confirmRemove/cancelRemove` (tests call them).
- Page debounces brightness, temperature and colour at 200 ms.
- Tests: `tests/test_gui_bulbs.py` (9 cases). They skip on the stock venv (Qt mismatch, see MEMORY.md);
  run with `uv run --with "PySide6==6.12.0"` → 9 passed; full suite 489 passed.
- task_07 adds the Follow combo (`bulbFollowCombo`) to `BulbPage.qml`'s FormLayout.
