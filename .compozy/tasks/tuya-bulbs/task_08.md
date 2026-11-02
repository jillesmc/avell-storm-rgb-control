---
status: completed
title: "Task 8: Screen follow over one shared capture"
type: feature
complexity: high
---

# Task 8: Screen follow over one shared capture

## Overview

This task finishes slice 2 by moving the follow-screen capture out of the USB task and behind one ref-counted hub. After it, a bulb can follow the screen, the keyboard and any number of bulbs share a single capture and a single Wayland picker, and stopping the keyboard no longer stops a bulb. The keyboard's existing follow-screen behaviour is preserved and characterised before the refactor.

## Shippable Outcome

- **Outcome:** choosing **Follow: Screen** opens the picker once and makes the bulb track the captured average colour; if the keyboard already follows the screen, no second picker appears; stopping the keyboard keeps the bulb following. Cancelling or losing the capture returns followers to None with the exact `_dx.md` messages. The CLI `keyboard follow-screen` behaves as before.
- **Verify in this task:** `tests/test_screen_hub.py`, `tests/test_screen_follow_split.py`, `tests/test_keyboard_follow_screen.py` and the follow integration cases (Tests below), plus a manual X11/Wayland check recorded by task_11.
- **Integration verification:** task_11 runs the hardware checklist including M-7.

## Requirements

- ADR-004; BR-16; Safety Invariant 7. This task refactors a working feature, so the characterisation tests UT-099 and UT-100 are written and green **before** the capture split.
- `src/app/core/screen_hub.py`: `ScreenFrameHub(QObject)` with `frame = Signal(object)` (PIL RGB, latest only), `subscribe(owner)` and `unsubscribe(owner)`. The first subscriber starts capture (portal picker on Wayland); the last stops it; a second subscriber never starts another capture.
- `src/avell_storm_rgb/application/screen_follow*.py`: split capture from apply. `iter_screen_frames(stop, **region)` yields frames for X11 or Wayland; `screen_follow_frame.py` keeps `build_key_color_map_from_pil_rgb` and `apply_pil_rgb_image_to_keyboard`.
- The keyboard becomes a hub subscriber: each frame is coalesced (latest wins) into one `UsbWorker` task that writes the 16×6 map; `stopFollowOrAnimation()` semantics stay the same and no `set_key_colors` runs after the stop returns and drains.
- The CLI `keyboard follow-screen` keeps its behaviour through a thin loop over `iter_screen_frames`; `tests/test_screen_follow_frame.py` stays green.
- `BulbFollower` gains the `screen` source: subscribe on follow, average the frame with `average_rgb`, unsubscribe on stop. `availableFollowSources` adds `screen` only when `screen_follow_runtime_available()`; it stays absent without the `screen` extra (UT-087 from task_07).
- Capture cancelled → follow `none`, `persistUpdate(id, {"follow": "none"})`, message `Screen capture cancelled — <name> no longer follows the screen.` Capture ended → all screen followers set to `none`, message `Screen capture ended — bulbs following the screen were set to None.`
- One capture per process; it stops when the last subscriber unsubscribes (Safety Invariant 7).

## Subtasks

- [x] 8.1 Characterisation tests for the keyboard follow-screen sequence and stop.
- [x] 8.2 Split `iter_screen_frames` from the apply loop (X11 and Wayland paths).
- [x] 8.3 `ScreenFrameHub` with ref-counted subscribers and a coalesced `frame` signal.
- [x] 8.4 Keyboard follow-screen becomes a subscriber; CLI keeps a thin loop.
- [x] 8.5 Bulb `screen` source, selector arm and the cancelled/ended messages.
- [x] 8.6 Hub, split and integration suites; keep `test_screen_follow_frame.py` green.

## Implementation Details

### Relevant Files

- `src/avell_storm_rgb/application/screen_follow.py:12-60` — X11 capture loop to split.
- `src/avell_storm_rgb/application/screen_follow_wayland.py:24-90` — Wayland portal capture loop to split.
- `src/avell_storm_rgb/application/screen_follow_frame.py:13-34` — `build_key_color_map_from_pil_rgb` / `apply_pil_rgb_image_to_keyboard` to keep.
- `src/avell_storm_rgb/application/screen_follow_dispatch.py:11-56` — runtime availability and dispatch.
- `src/avell_storm_rgb/application/screen_follow_session.py:8-12` — session detection.
- `src/app/ui/adapters/keyboard_backend.py:1357-1370` — the USB task that currently owns capture.
- `src/app/core/usb_worker.py:16-49` — the sink that receives coalesced frames.
- `src/app/ui/adapters/bulb_follow.py` — follower from task_07.
- `src/avell_storm_rgb/adapters/cli/main.py:166-193` — `_cmd_keyboard_follow_screen`.
- `tests/test_screen_follow_frame.py` — existing contract to keep.

### Dependent Files

- `src/app/ui/pages/BulbPage.qml` — selector already has the Screen arm gated by `availableFollowSources`; no new surface.
- `docs/ARCHITECTURE.md` / `docs/FLOWS.md` — task_09 documents the hub and the removed debt #6 for follow-screen.

### Related ADRs

- [ADR-004](adrs/adr-004.md) — one shared capture, capture split from apply, keyboard as subscriber.
- [ADR-003](adrs/adr-003.md) — the bulb keeps one driver while following.

## Deliverables

- `src/app/core/screen_hub.py`
- `iter_screen_frames` in the `screen_follow*` modules; thin CLI loop
- Keyboard subscriber wiring in `src/app/ui/adapters/keyboard_backend.py`
- `screen` source in `src/app/ui/adapters/bulb_follow.py` and `availableFollowSources`
- `tests/test_screen_hub.py`, `tests/test_screen_follow_split.py`, `tests/test_keyboard_follow_screen.py`

## Tests

- [x] UT-090, UT-091 — first subscribe starts capture once; ref-count keeps it alive and the last unsubscribe stops it
- [x] UT-092 — a solid-green frame pushes `(0, 255, 0)` to a screen follower
- [x] UT-093, UT-094 — cancelled and ended capture return followers to None with the exact messages
- [x] UT-099, UT-100 — characterisation: follow-screen writes the expected maps; stop stops all further writes
- [x] IT-011 — keyboard and bulb share one frame source; stopping the keyboard keeps the bulb receiving
- [x] IT-014 — CLI `keyboard follow-screen` produces the same `set_key_colors` sequence

## Success Criteria

- `make test` is green, including `test_screen_follow_frame.py` and the keyboard/LED bar suites.
- A run with the keyboard and one bulb following the screen opens one capture source and one picker; `unsubscribe` from the keyboard leaves the bulb subscribed.
- `grep -rn "iter_screen_frames\|ScreenFrameHub" src` shows the keyboard and the CLI consuming the split loop, not their own capture.
- No `set_key_colors` runs on the USB thread while following the screen (the frame sink submits one task per coalesced frame).
