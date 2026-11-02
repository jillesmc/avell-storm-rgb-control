---
status: completed
title: "Task 7: Follow the keyboard and the LED bar"
type: feature
complexity: high
---

# Task 7: Follow the keyboard and the LED bar

## Overview

This task starts slice 2: a bulb can follow the keyboard or the LED bar. After it, choosing **Follow: Keyboard** on the bulb page makes the room light take the colour the app sends to the keyboard, and **Follow: LED bar** takes the static average of the applied palette. Following never switches a bulb on, is rate-limited, survives restarts and stops on disconnect, forget, remove or loss.

## Shippable Outcome

- **Outcome:** on the bulb page the owner picks None, Keyboard or LED bar (options absent when the source is unavailable); the choice is saved in `devices.bulbs.<id>.follow`; a following bulb receives coalesced colour pushes at most 4 times per second over one persistent driver, only while its last known power is on; restarting the app resumes the choice after the first read.
- **Verify in this task:** `tests/test_bulb_follow.py`, `tests/test_keyboard_colour_tap.py`, `tests/test_bulbs_backend_follow.py` and the follow integration cases (Tests below).
- **Integration verification:** task_08 adds the Screen source on the same follower; task_11 runs the follow journey once on hardware.

## Requirements

- `_spec.md` → *Core Interfaces* (`_ColourTap`, `KeyboardBackend.colorsSent`, `BulbFollower`), BR-12–BR-15, Safety Invariants 4, 6 and 9; ADR-003.
- `_ColourTap` wraps the driver at connect time and forwards every attribute. After a **successful** `set_key_colors`, emit `colorsSent(average_rgb(color_map.values()))`; after a successful `set_color`, emit `colorsSent(color)`. Firmware effects, `set_palette_color` and a keyboard light-off produce no event. A raising driver produces no signal.
- LED bar source: average of the palette in the last `persistUpdate` with `power == "on"`; light off or no palette → nothing. Static average only, never palette cycling.
- `BulbFollower`: 250 ms timer per following bulb, only the latest colour, only when a channel changed by at least 8, only when no push is in flight, at most 4 pushes per second. `set_source(id, source)` starts/stops cleanly.
- Persistent socket only while following: `BulbWorker.set_hold_open(id, True)` on follow, `hold_open(False)`/`close()` on follow → none, disconnect, forget, remove, unavailable and shutdown. A second driver for a following bulb is a bug.
- Power gate: `push_colour` only while the last known power is on. Unknown power counts as off (no push until the first successful read says on). A 5 s status read runs while following; `on=False` stops pushes.
- Persistence: `setFollow` emits `persistUpdate(id, {"follow": source})`; `AppFacade` writes it; startup resumes the saved choice once the bulb is read. Disconnect stops following but keeps the choice.
- `availableFollowSources(id)` returns the subset the runtime supports. In this task the subset is `keyboard` (connected) and `led_bar` (connected); the `screen` arm is added by task_08 and must remain absent without the `screen` extra (UT-087).
- `BulbPage.qml` gets the follow `ComboBox` and the information message: "Following the keyboard. Other apps on your network can't control this bulb locally while it follows."; paused states add "Paused while the light is off." / "Paused: LED bar not connected.".

## Subtasks

- [x] 7.1 `_ColourTap` and `KeyboardBackend.colorsSent` around the driver open/close path.
- [x] 7.2 LED bar palette source from `persistUpdate`.
- [x] 7.3 `BulbFollower` with coalescing, threshold, in-flight guard and per-bulb timer.
- [x] 7.4 `BulbsBackend.setFollow`, `availableFollowSources`, persistence and lifecycle stops.
- [x] 7.5 Power gating and the 5 s status read while following.
- [x] 7.6 Follow selector and paused messages in `BulbPage.qml`.
- [x] 7.7 Unit and integration suites.

## Implementation Details

### Relevant Files

- `src/app/ui/adapters/keyboard_backend.py:973-1016` — driver open/close where the tap is installed.
- `src/app/ui/adapters/keyboard_backend.py:1231-1250, 1300-1380` — solid colour, animation loop and follow-screen call sites the tap covers.
- `src/app/ui/adapters/led_bar_backend.py:24, 86-93, 159-176, 226-230` — `persistUpdate` with the applied palette and power.
- `src/app/core/bulb_worker.py`, `src/app/ui/adapters/bulbs_backend.py` — worker and backend from task_05.
- `src/app/ui/pages/BulbPage.qml` — page from task_06 where the selector joins.
- `src/app/ui/adapters/app_facade.py:536` — single-writer path for `follow`.
- `src/avell_storm_rgb/domain/bulb_color.py` — `average_rgb`, `changed_enough`.
- `tests/backend_fakes.py` — `FakeKeyboard`, `FakeLedBar`, `FakeBulb`.

### Dependent Files

- `src/app/ui/adapters/keyboard_backend.py` — task_08 later moves follow-screen onto the hub; keep the tap independent of that refactor.
- `tests/test_keyboard_backend_colors.py`, `tests/test_keyboard_backend_light.py`, `tests/test_led_bar_backend_light.py` — existing behaviour must stay green.

### Related ADRs

- [ADR-002](adrs/adr-002.md) — follow never writes power and never sends while off.
- [ADR-003](adrs/adr-003.md) — persistent socket only while following; one driver per bulb; coalesced pushes.

## Deliverables

- `src/app/ui/adapters/bulb_follow.py`
- `_ColourTap` and `colorsSent` in `src/app/ui/adapters/keyboard_backend.py`
- `setFollow`/`availableFollowSources` and lifecycle wiring in `src/app/ui/adapters/bulbs_backend.py`
- Follow selector in `src/app/ui/pages/BulbPage.qml`
- `tests/test_bulb_follow.py`, `tests/test_keyboard_colour_tap.py`, `tests/test_bulbs_backend_follow.py`

## Tests

- [x] UT-080 — remove while following stops the follower and closes the socket before the inventory write
- [x] UT-081, UT-082, UT-084, UT-085 — colour tap on solid/per-key writes, no event for firmware effects or keyboard off
- [x] UT-083, UT-086 — ≤ 4 pushes per second with the latest colour; change threshold 8
- [x] UT-087 — follow sources absent without their runtime (screen arm completed by task_08)
- [x] UT-088, UT-089 — LED bar palette average once; light off sends nothing
- [x] UT-095, UT-096, UT-101 — last known power off, 5 s read sees off, unknown power never pushes
- [x] UT-097, UT-098 — disconnect keeps the choice and stops the socket; unreachable push marks unavailable and releases the driver
- [x] IT-010, IT-012, IT-013, IT-015 — keyboard solid colour reaches the bulb, LED bar average, restart resumes follow, one driver while following
- [x] E2E-027 — selector lacks unavailable sources and shows the following message for Keyboard

## Success Criteria

- `make test` is green, including the existing keyboard, LED bar and backend suites.
- A following bulb's `FakeBulb` open count stays 1 across commands and pushes; `reject_second_connection` is never triggered.
- No `push_colour` is recorded while the last known power is off or unknown.
- `grep -rn "set_colour\|set_multiple_values" src/app/ui` finds no direct driver write outside `bulb_follow.py`/`bulbs_backend.py`.
