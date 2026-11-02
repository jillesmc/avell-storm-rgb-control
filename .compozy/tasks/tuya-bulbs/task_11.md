---
status: completed
title: "Task 11: Execute the delivery QA for bulbs"
type: qa-execution
complexity: medium
---

# Task 11: Execute the delivery QA for bulbs

## Overview

This task executes the plan from task_10 against the delivered package and records the evidence. It authors and runs the one cross-surface privacy test, verifies the full suite with and without the optional extras, and runs the manual hardware checklist with the user's explicit go-ahead. It closes the delivery loop for the spec.

## Shippable Outcome

- **Outcome:** `.compozy/tasks/tuya-bulbs/evidence/qa/report.md` records every check from the plan with pass/fail, command, environment and artifact; `tests/test_bulb_privacy_cross_surface.py` (UT-071) passes; the manual checklist results (including OQ-1 and OQ-2) are recorded; defects are filed back to the owning task instead of being hidden.
- **Verify in this task:** the executed plan, `UT-071`, the full `make test` runs and the recorded hardware results.
- **Integration verification:** this is the final delivery owner; no later task exists.

## Requirements

- Execute `evidence/qa/plan.md` in order. Reuse existing evidence; capture only missing or invalidated checks.
- **Hardware gate:** `M-1`–`M-7` change real house lights. Do not run them until the user explicitly agrees for this execution. Record the go-ahead, the bulbs involved and the result.
- `UT-071` (new `tests/test_bulb_privacy_cross_surface.py`): with a sentinel key, assert that the human and `--json` output of `bulb list`, `bulb status`, `bulb import`, `state show`, every `BulbListModel` role, every `bulb(id)` snapshot and `caplog` at DEBUG during connect/fail/refresh never contain the sentinel. In the same test, force `logging.getLogger("tinytuya")` to DEBUG and assert the adapter's pin restores WARNING, and use a spy to prove `tinytuya.set_debug()` is never called.
- Run `make test` with the GUI and Tuya extras, and the no-extra path (`uv sync` then the CLI import/help checks). Record exact commands and results.
- Re-check the no-extra GUI shell (E2E-026 evidence) and the corrupt-inventory `state show` exit code (E2E-016 evidence).
- OQ-1: with a bulb off, send one `push_colour` only after the go-ahead; record whether it turns on. If it does, confirm BR-12 gating stays and note it for the docs; if not, record that the question is closed.
- OQ-2: verify the bulb icon name on the machine; if absent, confirm the `preferences-desktop-color` fallback renders.
- Do not change product code in this task. If a check fails, file the defect to its owning task and mark the report accordingly; the only new code is the UT-071 test.
- Never write a real key or a real home IP into the report or its artifacts.

## Subtasks

- [x] 11.1 Write `tests/test_bulb_privacy_cross_surface.py` (UT-071) and run it.
- [x] 11.2 Run the full suite with `--extra gui --extra tuya`; record results.
- [x] 11.3 Run the no-extra install/CLI/GUI-shell checks; record results.
- [x] 11.4 Ask for the hardware go-ahead, then execute `M-1`–`M-7`; record OQ-1 and OQ-2.
- [x] 11.5 Write `evidence/qa/report.md` with per-check evidence and any filed defects.

## Implementation Details

### Relevant Files

- `.compozy/tasks/tuya-bulbs/evidence/qa/plan.md` — the checks to execute (task_10).
- `.compozy/tasks/tuya-bulbs/_tests.md:263-271` — `M-1`–`M-7`.
- `tests/` — full suite; place the new privacy test next to the other bulb tests.
- `tests/conftest.py` — `XDG_CONFIG_HOME` isolation; the privacy test must not read real config.
- `src/avell_storm_rgb/infrastructure/tuya/bulb.py` — the logger pin and `set_debug` rule under test.
- `src/app/ui/adapters/bulbs_backend.py` — model roles and `bulb(id)` snapshots under test.

### Dependent Files

- `docs/DEVELOPMENT.md` — update only if the plan reveals a wrong command; otherwise report it to task_09.
- Owning tasks of any defect found (`task_01`–`task_08`); do not fix their code here.

### Related ADRs

- [ADR-001](adrs/adr-001.md) — key privacy, the subject of UT-071.
- [ADR-002](adrs/adr-002.md) — the safety rule M-5/OQ-1 verifies.
- [ADR-004](adrs/adr-004.md) — the screen-follow regression check M-7.

## Deliverables

- `tests/test_bulb_privacy_cross_surface.py`
- `.compozy/tasks/tuya-bulbs/evidence/qa/report.md` with per-check evidence
- Hardware results for `M-1`–`M-7`, including OQ-1 and OQ-2

## Tests

- [x] UT-071 — sentinel key absent from CLI, state, model roles, snapshots and logs; tinytuya logger pin holds; `set_debug()` never called
- [x] M-1, M-2, M-3, M-4 — status matches the app, restart leaves the bulb unchanged, slider/temperature/colour behave, wall-switch off/on recovers
- [x] M-5, M-6, M-7 — OQ-1 power result, keyboard follow smoothness, one picker with keyboard + bulb on Wayland and X11

## Success Criteria

- Every plan row has a pass/fail and an evidence artifact in `report.md`.
- `UT-071` passes and the full suite is green with the GUI and Tuya extras.
- The no-extra path imports the package, runs the CLI and shows no bulb surface.
- Hardware checks ran only after the recorded go-ahead, and no real key or IP appears in the evidence.
- Any failure is linked to its owning task with the exact failing check.
