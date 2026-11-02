---
status: completed
title: "Task 3: Terminal control with the `bulb` command group"
type: feature
complexity: high
---

# Task 3: Terminal control with the `bulb` command group

## Overview

This task gives the terminal the same bulb capabilities the app will have, so `avell-storm-rgb bulb …` replaces `~/git/iot/bulbs.py` before any GUI work. It is the earliest useful solution to the Motivating Problem: import once, then switch, dim, set white or colour, inspect and remove bulbs from a script or an agent, with `--json` everywhere.

## Shippable Outcome

- **Outcome:** `avell-storm-rgb bulb import|list|status|on|off|toggle|bright|white|color|remove` behaves exactly like the `_dx.md` transcripts: the same columns, the same JSON, the same exit codes, `key: set` and no key anywhere. `bulb list` finishes in about 6 s even with three offline bulbs.
- **Verify in this task:** `tests/test_cli_bulb.py` driving `main(argv)` with a fake `open_bulb`, a fixture inventory and real files in `tmp_path` (Tests below).
- **Integration verification:** task_11 re-runs the `_dx.md` transcripts against the delivered package.

## Requirements

- `_dx.md` is the contract for output, JSON shape, exit codes and errors. Reuse the existing CLI conventions in `main.py` (`_handler`, `error: …` on stderr, argparse for range/`all` errors).
- New `src/avell_storm_rgb/adapters/cli/bulb_cli.py`; `main.py` only registers the group. No `PySide6` import.
- Without the `tuya` extra, every `bulb` verb prints `error: bulb control needs the optional 'tuya' extra: uv sync --extra tuya` and exits 1, while `bulb -h` still lists the verbs (build the parser before checking availability).
- Targets: `all`, a case/accent-insensitive name, or a device id via `match_target`; `remove` rejects `all`; unknown and ambiguous names use the exact `_dx.md` text and exit 2.
- `bulb list` reads all bulbs in a `ThreadPoolExecutor` capped at 8 workers with **one** 6 s deadline for the whole command (5 s per command); exit 0 when the inventory loaded, offline is a normal result.
- `bulb status` defaults to `all`; exit 1 when any target is offline. `on|off|toggle|bright|white|color` accept `--json` with the documented `ok|offline|failed` result shape.
- `bright` reads the status first on the same connection because the target DPS depends on the mode (BR-11); a failed read is an `offline` result, never a guessed write. `white` without `--temp` sends mode-only and needs no read.
- Import: `added|updated|unchanged|skipped` with reasons `key changed`, `name changed`, `mac changed` comma-joined; import never removes entries.
- Keys never appear in human or JSON output; listings show `key: set` / `"key": "set"`.

## Subtasks

- [x] 3.1 `bulb_cli.py` handlers: import, list, status, control verbs, remove.
- [x] 3.2 Target resolution and error surfaces shared by the verbs.
- [x] 3.3 `bulb list` executor, per-command timeout and single 6 s deadline.
- [x] 3.4 `--json` serialisers and the no-extra gate.
- [x] 3.5 Register the `bulb` group in `_build_parser()`.
- [x] 3.6 CLI transcript suite with a fake opener and fixture files.

## Implementation Details

### Relevant Files

- `src/avell_storm_rgb/adapters/cli/main.py:45-76` — argparse value validators (`_valid_rgb`, `_valid_intrange`).
- `src/avell_storm_rgb/adapters/cli/main.py:291-345` — `_load_state`/`_cmd_state_show` printing and exit conventions.
- `src/avell_storm_rgb/adapters/cli/main.py:439-604` — `_build_parser()` where the `bulb` group joins.
- `src/avell_storm_rgb/adapters/cli/main.py:606-629` — `main()` error handling and `SystemExit` behaviour.
- `src/avell_storm_rgb/application/bulb_inventory.py` — import, upsert, remove, `match_target`.
- `src/avell_storm_rgb/application/bulb_facade.py` — `open_bulb`, `tuya_available`.

### Dependent Files

- `tests/test_cli_help.py` — add the `bulb` group to the help expectations.
- `tests/test_cli_state.py` — `state show` is task_04; keep it unchanged here.

### Related ADRs

- [ADR-001](adrs/adr-001.md) — import-only onboarding and key privacy.
- [ADR-002](adrs/adr-002.md) — explicit commands switch on; reads never write.

## Deliverables

- `src/avell_storm_rgb/adapters/cli/bulb_cli.py`
- `bulb` group registration in `src/avell_storm_rgb/adapters/cli/main.py`
- `tests/test_cli_bulb.py`, `tests/fixtures/tinytuya_devices.json` (reused from task_01)

## Tests

- [x] E2E-001, E2E-002, E2E-003, E2E-004 — import golden path, re-import/skips, non-list file, zero bulbs
- [x] E2E-005, E2E-015 — `bulb status` with offline/online bulbs, human and `--json`
- [x] E2E-006, E2E-007 — `white --temp all` with one offline, colour/off transcripts
- [x] E2E-008, E2E-009, E2E-010 — argparse ranges, unknown name, no inventory
- [x] E2E-011, E2E-012 — `list` output and 6 s deadline, `remove` and `remove all`
- [x] E2E-014 — no `tuya` extra hint while `bulb -h` still lists verbs

## Success Criteria

- `make test` is green, including the existing CLI suites.
- Every `_dx.md` console block in this task's scope reproduces byte-for-byte through `main(argv)`.
- `grep -rnE "^(from|import) tinytuya" src/avell_storm_rgb/adapters` finds nothing.
- `uv run avell-storm-rgb bulb -h` works with and without the extra; without it, a verb prints the install hint and exits 1.
