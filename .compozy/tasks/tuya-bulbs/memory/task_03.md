# Task 03 — `avell-storm-rgb bulb …` command group

Status: completed (uncommitted; conductor reviews/commits).

## What was built

- `src/avell_storm_rgb/adapters/cli/bulb_cli.py` — every `bulb` verb, all output/JSON/exit
  codes from `_dx.md`. No `tinytuya`, no Qt import.
- `src/avell_storm_rgb/adapters/cli/main.py` — one import + `register_bulb_group(sub)` at the
  end of `_build_parser()`; nothing else changed (task_04's `state show` untouched).
- `tests/test_cli_bulb.py` — 43 cases driving `main(argv)` with a fake `open_bulb`
  (`World`/`FakeBulb`), the task_01 fixture inventory and real files in `tmp_path`.
- `tests/test_cli_help.py` — `bulb` in the top-level help + every verb in `bulb -h`.

## Verbs and their human output (all byte-verified against `_dx.md`)

| Verb | stdout |
|------|--------|
| `bulb import <devices.json>` | `{name:<12} {id}  added\|updated (reason)\|unchanged` then `{name:<12} {id}  skipped: <reason>`, then `Imported N bulb(s) into <path>` |
| `bulb list` | `Inventory: <path>` then `{name:<12} {id}  {online\|offline:<9}{ip\|—:<14}protocol <p>  key: set` |
| `bulb status [target]` | `{name:<12} on   {mode:<8}brightness N%[  temperature N%]` / `#rrggbb  brightness N%` / `{name:<12} off` / `offline` / `failed: …` |
| `bulb on\|off <target>` | `{name:<12} on` / `off` |
| `bulb toggle <target>` | `{name:<12} <new state>` |
| `bulb bright <1-100> <target>` | `{name:<12} brightness N%` |
| `bulb white [--temp 0-100] <target>` | `{name:<12} white N%` or `{name:<12} white` |
| `bulb color <R> <G> <B> <target>` | `{name:<12} colour #rrggbb` |
| `bulb remove <target>` | `Removed <name> (<id>) from <path>` |

The name column is `f"{name:<12} "` (13 columns) — `_dx.md`'s "padded to 12, then the result".

## JSON shapes (`ensure_ascii=False`, key order matters)

```json
{"path": "<inventory>", "results": [{"id","name","status"[,"reason"]}]}          # import (skipped last)
{"path": "<inventory>", "bulbs": [{"id","name","online","ip","protocol","key"}]} # list; ip null when offline
{"results": [{"id","name","online","on","mode","brightness","temperature","rgb"}]}  # status, online entry
{"results": [{"id","name","online": false}]}                                     # status, offline entry
{"results": [{"id","name","status","reason"}]}                                   # control verbs; reason null unless failed
```

Decisions where `_dx.md` is silent:
- status of a **failed** read (key rejected / other device error) → human `failed: …`, JSON
  `{"id","name","online": false,"status": "failed","reason": …}` (the documented offline entry
  plus the control-verb keys). Only `BulbUnreachable` is `offline`.
- control-verb JSON always carries `"reason"`, `null` for `ok`/`offline`.
- `Imported N bulb` is pluralised (`1 bulb` / `3 bulbs`); every transcript uses 3.
- `bulb import --json` with zero bulbs prints `No bulbs found in <path>` (not JSON), exit 1.
- a missing import file → `error: not a tinytuya devices.json (cannot read file (<strerror>)): <path>`.

## Exit codes

| Situation | Code |
|-----------|------|
| ok; `list` with offline bulbs; no bulbs imported on `list`/`status` | 0 |
| no `tuya` extra (every verb); offline/failed control or status; no bulbs imported on control/`remove`; import file unreadable/not a list/no bulbs | 1 |
| argparse usage (`bright` out of 1–100, `white --temp` out of 0–100, `color` out of 0–255, `remove all`); unknown/ambiguous target | 2 |
| inventory unreadable (every verb, incl. `import`) | 3 |

Error lines are stderr and start with `error: `; the two informational hints
(`NO_EXTRA_HINT`, `NO_BULBS_HINT`) go to stderr and stdout respectively.

## Timeout / executor design (`bulb list`)

- `LIST_WORKERS = 8`, `LIST_DEADLINE = 6.0` (module constants, monkeypatchable in tests).
- One `ThreadPoolExecutor(max_workers=min(8, len(records)), thread_name_prefix="bulb-list")`,
  one task per bulb = `_read_one` = `open_bulb` → `status()` → `close()`.
- `wait(futures, timeout=LIST_DEADLINE)` **once**; a future not done is `offline` and is
  cancelled. `pool.shutdown(wait=False, cancel_futures=True)` so the command never waits for
  the stragglers (3 offline bulbs ≈ 6 s, not 3 × 6 s).
- The 5 s per-command budget is `TuyaBulb`'s `COMMAND_TIMEOUT`; `open_bulb` takes no timeout
  argument, so nothing extra is passed.
- Control verbs run sequentially (order matters for `all`); only `list` is parallel.

## Seams task_04 / task_05 / task_11 reuse

- `bulb_cli.tuya_available` and `bulb_cli.open_bulb` are module attributes: monkeypatch them.
- `register_bulb_group(sub)` is the only entry point `main.py` needs.
- `NO_EXTRA_HINT`, `NO_BULBS_HINT`, `KEY_REJECTED_HINT`, `LIST_DEADLINE`, `LIST_WORKERS` are
  exported in `__all__` so tests/docs can assert the exact strings.
- task_04 (`state show`) must **not** gate on `tuya_available()` and must not use
  `_open_inventory()`; it needs the inventory names even without the extra.
- task_05/task_11: the same `BulbInventory`/`open_bulb` seams; `key: set` rendering lives in
  `_key_state` (human) and `_list_json` (JSON).

## Verification evidence

- `uv run pytest -q tests/test_cli_bulb.py tests/test_cli_help.py` → **46 passed**.
- `uv run pytest -q -m "not hardware"` → **416 passed, 11 skipped, 5 failed**; the 5 are the
  known pre-existing `tests/test_gui_pages.py::test_page_component_ready[*]` environment
  failures (373 baseline + 41 CLI cases + 2 help cases).
- Byte-for-byte: a throwaway script extracted 11 console blocks from `_dx.md` and diffed them
  against `main(argv)` stdout with a fake opener — all matched, including the `—` offline
  column, the em dash in `local key or protocol rejected — re-import devices.json`, and the
  literal `Escritório` in JSON (`ensure_ascii=False`).
  Blocks: Golden Path import/status/`off escritorio`, `bulb import`, `bulb import --json`,
  `bulb list`, `bulb list --json`, `bulb status`, `bulb status escritorio --json`,
  `bulb white --temp 20 all`, `bulb remove sala`.
- Without the extra (`sys.modules["tinytuya"] = None` → `tuya_available() is False`): three
  verbs printed the exact hint and returned 1, `bulb -h` exited 0 and listed all ten verbs.
- `uv run avell-storm-rgb bulb -h` (with the extra) lists `{import,list,status,on,off,toggle,bright,white,color,remove}`.
- `grep -rnE "^(from|import) tinytuya" src/avell_storm_rgb/adapters` → no match; the only
  occurrences are help/doc strings and `parse_tinytuya_devices`.
- No `PySide6` import added anywhere.
