---
status: completed
title: "Task 10: Plan the delivery QA for bulbs"
type: qa-report
complexity: low
---

# Task 10: Plan the delivery QA for bulbs

## Overview

This task turns the remaining, non-automated checks in `_tests.md` into one executable plan. It fixes the environment, the evidence each check leaves behind, and the user go-ahead gate for the manual hardware checks that change real house lights. Planning evidence already exists in `_tests.md`; this task does not invent new cases.

## Shippable Outcome

- **Outcome:** `.compozy/tasks/tuya-bulbs/evidence/qa/plan.md` lists every remaining check with one owner, the exact command or GUI action, the environment, the expected result, the evidence artifact and the go-ahead requirement. task_11 can execute it without re-deriving scope.
- **Verify in this task:** plan review against `_tests.md` (all `M-1`–`M-7` present once), `_spec.md` Open Questions and Known Risks, and `_dx.md` messages.
- **Integration verification:** task_11 executes the plan; this task sends no bulb command and changes no product code.

## Requirements

- Read `_tests.md` (manual checklist and coverage matrix), `_spec.md` (Open Questions OQ-1/OQ-2, Known Risks, Safety Invariants), `_dx.md` (errors and transcripts) and `_review.md` (resolution table).
- The plan must cover, exactly once:
  - `M-1`–`M-7`, each with its precondition, action, expected result and the fact that it needs the user's explicit go-ahead because it changes real house lights;
  - the cross-surface privacy audit `UT-071` (authoring and running it belongs to task_11);
  - a full `make test` run with the GUI and Tuya extras, and a run without the `tuya` extra;
  - the no-extra installation path and the `state show` corrupt-inventory path;
  - X11 and Wayland screen follow if both are available (M-7), otherwise record the session actually tested.
- OQ-1 (does `push_colour` turn a switched-off bulb on?) must be recorded as an open hardware result: the plan says what to do if it turns on (keep BR-12 gating, document it) and if it does not (record and close the question).
- OQ-2 (Breeze bulb icon name) must be verified with the documented fallback `preferences-desktop-color`.
- Evidence path: `.compozy/tasks/tuya-bulbs/evidence/qa/` with one folder or file per check, including command, environment, expected/actual, pass/fail and any screenshot/log. Reuse existing evidence instead of recapturing it.
- No product-code changes; no bulb command sent while planning; no real key or IP written into the plan.

## Subtasks

- [x] 10.1 Enumerate the remaining checks and map each to one owner and one evidence artifact.
- [x] 10.2 Define the hardware go-ahead gate and the rollback/safety steps for M-1–M-7.
- [x] 10.3 Define the UT-071 privacy audit scope and its evidence.
- [x] 10.4 Define the environment matrix (extras, X11/Wayland, bulbs online/offline) and the final full-suite commands.
- [x] 10.5 Write `evidence/qa/plan.md` and cross-check it against `_tests.md`.

## Implementation Details

### Relevant Files

- `.compozy/tasks/tuya-bulbs/_tests.md:230-271` — CLI/GUI journeys and the manual hardware checklist.
- `.compozy/tasks/tuya-bulbs/_spec.md:98-101, 437-444` — Open Questions and Known Risks.
- `.compozy/tasks/tuya-bulbs/_dx.md:195-218` — exact error surfaces to verify.
- `.compozy/tasks/tuya-bulbs/_review.md` — applied resolutions; do not re-open them.
- `Makefile`, `pyproject.toml` — test and extra commands.

### Dependent Files

- `task_11.md` — consumes the plan; keep the check IDs stable.
- `docs/DEVELOPMENT.md` — task_09 documents the same commands; the plan must not contradict it.

### Related ADRs

- [ADR-002](adrs/adr-002.md) — the safety rule OQ-1 tests.
- [ADR-004](adrs/adr-004.md) — the screen-follow regression check M-7.

## Deliverables

- `.compozy/tasks/tuya-bulbs/evidence/qa/plan.md`

## Tests

No `_tests.md` IDs are assigned here; the plan covers `M-1`–`M-7` and hands the cross-surface privacy audit to task_11.

## Success Criteria

- `M-1`–`M-7` appear exactly once, each with owner, action, expected result, evidence path and go-ahead note.
- `UT-071`, the full-suite runs, the no-extra path and the corrupt-inventory path each appear once with an owner.
- The plan states explicitly that no bulb command runs before the user's go-ahead.
- No product file changes; `git status` shows only the new evidence file.
