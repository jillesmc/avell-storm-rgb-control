# Task 08 — screen follow over one shared capture

Status: completed (uncommitted). Manual X11/Wayland check still owed to task_11 (M-7).

- Core split: `screen_follow.iter_x11_frames`, `screen_follow_wayland.iter_wayland_frames`
  (raises `ScreenCaptureCancelled` when the picker is closed), `screen_follow_dispatch.iter_screen_frames`.
  `apply_frames_to_keyboard(kb, frames)` = user mode on the first frame + one 16×6 write per frame.
  `run_screen_follow*` and the CLI are thin loops over the iterators; cancel is still silent there.
  Frame pacing (0.1 s) moved into `screen_follow.pace()`.
- `src/app/core/screen_hub.py`: `ScreenFrameHub(frames=None)`; `subscribe(owner, **region)` /
  `unsubscribe(owner)` / `is_subscribed` / `running` / `shutdown`; signals `frame`, `cancelled`,
  `ended`, `failed(str)`. Owners compare with `==` (bulbs use `"bulb:<id>"`). Capture runs on a
  daemon thread `screen-capture`; end states clear every subscriber (GUI thread, `_on_finished`).
- Keyboard follow-screen is a subscriber: frames coalesced (latest wins) into one `UsbWorker` task
  at a time; `_stop_long_task()` unsubscribes. `KeyboardBackend(worker, parent, *, screen_hub=None)`.
- Bulbs: `BulbFollower(screen_hub=…)` subscribes for `screen`, averages a 16×6 downscale.
  `BulbsBackend` maps hub `cancelled` / `ended` / `failed` to follow `none` + the `_dx.md` messages.
  `AppFacade._follow_sources()` adds `screen` when `keyboard.followScreenAvailable`.
- `tests/conftest.py` now pins `app.core.screen_hub._default_frames` to an idle fake: no test can
  open a real capture or the portal picker. The old `run_screen_follow_auto` monkeypatch in
  `test_keyboard_backend_light.py::test_ut047` was removed (symbol gone; conftest covers it).
- Verification: PySide6 6.12 overlay → 525 passed; stock venv → 499 passed + the 5 known Qt failures.
