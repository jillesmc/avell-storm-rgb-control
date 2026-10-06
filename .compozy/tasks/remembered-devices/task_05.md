---
status: completed
title: "Task 5: CLI shows and restores the saved state"
type: feature
complexity: medium
---

# Task 5: CLI shows and restores the saved state

## Overview

This task adds `avell-storm-rgb state show` and `avell-storm-rgb state restore`. With them, a script, a login hook or an agent can inspect and re-apply the saved lights without opening the GUI.

## Shippable Outcome

- **Outcome:** `avell-storm-rgb state show [--json]` and `avell-storm-rgb state restore [--kind all|keyboard|led-bar] [--no-animation] [--json]` behave exactly as the `_dx.md` transcripts, with exit codes 0 / 1 / 3 (2 for usage).
- **Verify in this task:** CLI unit and E2E suites through `main(argv)` with fake openers and a real state file (Tests below). Plus `uv run avell-storm-rgb state show` against the real config.
- **Integration verification:** none.

## Requirements

- Contract: `_dx.md` → *CLI* and *Errors*. The outputs are byte-exact, including the column alignment and `describe_look` strings.
- BR-13: the CLI never writes `state.json`; device commands don't touch it. Safety Invariant 3.
- Restore order: LED bar, then keyboard. Only remembered devices. `--kind` filters.
- A `pending_animation` runs in the foreground with the same loop semantics as `keyboard play-animation`. `Ctrl+C` exits 0. `--no-animation` skips it.
- Error mapping:
  - `StateFileError` → exit 3 with `error: saved state is unreadable (<reason>): <path>`;
  - device not found → `skipped: device not found`, exit 1;
  - other driver exceptions → `failed: <Type>: <msg>`, exit 1.
- Reuse `device_state` and `device_facade.open_*(usb_id=…)`; no PySide6 import.

## Subtasks

- [x] 5.1 `state` subparser with `show` and `restore` in `_build_parser()`.
- [x] 5.2 `show`: human and `--json` output.
- [x] 5.3 `restore`: ordering, filtering, results, animation in the foreground, `--json`, exit codes.
- [x] 5.4 Tests.

## Implementation Details

### Relevant Files

- `src/avell_storm_rgb/adapters/cli/main.py:176-201` — `_cmd_keyboard_play_animation` loop semantics to reuse.
- `src/avell_storm_rgb/adapters/cli/main.py:273-412` — parser layout and handler registration.
- `src/avell_storm_rgb/adapters/cli/main.py:415-438` — `main()` error handling (keep it consistent).
- `tests/test_cli_help.py` — existing CLI test style.

### Dependent Files

- `tests/test_cli_help.py` — add `state --help`.

### Related ADRs

- [ADR-001](adrs/adr-001.md) — the CLI reads the file only.

## Deliverables

- CLI `state` group.
- `tests/test_cli_state.py`.

## Tests

- [x] UT-070, UT-071, UT-072 — `state show`
- [x] UT-073, UT-074, UT-075, UT-076, UT-077, UT-078, UT-079, UT-080 — `state restore`
- [x] E2E-001, E2E-002, E2E-003 — the `_dx.md` transcripts

## Success Criteria

- `make test` is green.
- `uv run avell-storm-rgb state --help` lists `show` and `restore`.

## Completion Notes

- Human output and the example state file are copied **verbatim from `_dx.md`** into `tests/test_cli_state.py` (no runtime dependency on `.compozy/`, which may be archived after merge).
- `--json` with no state file prints `{"path": …, "results": []}` (not specified in `_dx.md`; mirrors `state show --json`).
- `tests/backend_fakes.py` no longer imports PySide6 at module level, so the CLI tests reuse the same fakes without Qt.
- Evidence: `tests/test_cli_state.py` (16 passed: UT-070–080, E2E-001–003 + 2 extra) and `state -h` in `tests/test_cli_help.py`; full suite 131 passed; the CLI imports with PySide6 blocked.
