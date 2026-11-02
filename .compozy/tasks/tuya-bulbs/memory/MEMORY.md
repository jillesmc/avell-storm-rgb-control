# Shared memory — tuya-bulbs

Durable context every task worker must read before editing code. Task-local notes live in
`memory/task_NN.md`.

## Execution route

- Conductor: the main session, running the `cy-orchestrate-tasks` workflow manually.
- One worker subagent per task, in `_tasks.md` graph order, foreground and sequential.
- The Compozy `implement-tasks` loop was rejected: `ext__spec_cycle__import_tasks` is scoped to the
  registered workspace root (`/home/jilles/git/avell-storm-rgb-control`), so it cannot see
  `.compozy/tasks/tuya-bulbs/` inside the worktree. Using it would need a mirror in the main repo.
- All work happens in the worktree `/home/jilles/.compozy/worktrees/avell-storm-rgb-control/calm-badger`.

## Baseline (before task_01)

- `uv run pytest -q -m "not hardware"` → **241 passed, 11 skipped, 5 failed**.
- The 5 failures are pre-existing and environmental, not ours:
  `tests/test_gui_pages.py::test_page_component_ready[*]` for DevicesPage, KeyboardPage, LedBarPage,
  AppAboutPage, SettingsPage, all with `QQuickStyle::setStyle() must be called before loading QML that
  imports Qt Quick Controls 2`. `QT_QPA_PLATFORM=offscreen` does not change it.
- Therefore "the suite is green" means: **no new failures beyond those 5**, and the task's own tests pass.
- **Root cause found in task_06:** the venv has PySide6 6.11 but the distro Kirigami/Breeze QML plugins
  are built for Qt 6.12, so every `main.qml` test skips or fails here. With
  `uv run --with "PySide6==6.12.0" pytest -q -m "not hardware"` the whole suite passes (489 passed,
  0 failed, 0 skipped after task_06). Run GUI tasks' checks that way; the lock was **not** bumped
  (operator decision).

## Hard rules (from AGENTS.md)

- `uv` only. No new dependencies without an explicit request.
- USB payloads are wire-accurate; never change bytes/offsets/order without hardware proof.
- GUI USB I/O only through `UsbWorker.submit`; never from QML or the GUI thread.
- `device_state` has one writer (`AppFacade`, GUI thread) and must stay Qt-free.
- Tests must never touch the real config (`tests/conftest.py` pins `XDG_CONFIG_HOME`).
- Core (`src/avell_storm_rgb/`) never imports PySide6; CLI/core never import Qt.
- Docs are bilingual pairs: update `NAME.md` **and** `NAME.pt-BR.md` in the same change.
- Never touch real bulbs, never read or print real local keys.

## Landed contracts (read before task_02+)

- `domain/bulb_color.py`: `percent_to_device`, `device_to_percent`, `rgb_to_colour_data_v2`,
  `colour_data_v2_to_rgb`, `average_rgb`, `changed_enough`, `status_from_dps`, `BulbStatus`.
  Constants `DEVICE_MIN=10`, `DEVICE_MAX=1000`, `CHANGE_THRESHOLD=8`.
- `application/bulb_inventory.py`: `BulbRecord`, `BulbFailure`, `Skipped`, `ImportResult`,
  `ImportReport`, `InventoryFileError`, `ImportFileError`, `UnknownTarget`, `AmbiguousTarget`,
  `default_inventory_path`, `BulbInventory`, `parse_tinytuya_devices`, `match_target`.
- **Two error types, on purpose:** `InventoryFileError` = the inventory file cannot be used;
  `ImportFileError` = the wizard `devices.json` is not a JSON list of devices (UT-013, `_dx.md`).
  `_spec.md` *Core Interfaces* was updated to list both plus `ImportResult`.
- `BulbInventory` writes take an advisory `flock` on `<inventory>.lock` (ADR-001); that lock file
  appears next to `tuya_devices.json` and must be expected by later tests and docs.
- `match_target` returns a **list** (`"all"` → many), raises `UnknownTarget` / `AmbiguousTarget`.
- `ports/protocols.py` now exports `BulbDriver` (runtime_checkable, `BulbStatus` under `TYPE_CHECKING`).

## Known pre-existing debt (do not fix silently)

- `src/avell_storm_rgb/domain/physical_key_map.py:5` imports `PySide6.QtCore`, which violates the
  "core never imports Qt" rule. It predates this workflow (commit `d7175bc`). task_01's
  `grep -rn "PySide6" src/avell_storm_rgb` criterion therefore cannot pass as written; treat it as
  "no new PySide6 import". Report it; do not refactor it inside a bulb task.

## Landed contracts (task_02)

- `infrastructure/tuya/bulb.py`: `TuyaBulb` (implements `BulbDriver`), `BulbError`, `BulbUnreachable`,
  `KeyRejected`, `Discovered`, `discover_bulb`; `tinytuya` is imported only inside `_tinytuya()`,
  which also pins `logging.getLogger("tinytuya")` to WARNING.
- `application/bulb_facade.py`: `tuya_available()`, `open_bulb()`, `arp_lookup()`, and re-exports of
  the three error types. `application → infrastructure` is allowed by `docs/ARCHITECTURE.md`
  (`adapters → application → domain / infrastructure`).
- `open_bulb` probes each candidate IP on TCP 6668 (injectable `probe=`), accepts the discovery
  result without a probe, and writes `set_last_ip` only when the answering IP differs.
- `set_white(None, status)` does **not** read the status; it omits DPS 23 when no temperature is
  known. Only `set_brightness(..., None)` reads once on the same driver.
- Extra `tuya = ["tinytuya>=1.20,<2"]` in `pyproject.toml`; tests need `uv sync --extra tuya`.

## Tracking protocol

- Update `task_NN.md` frontmatter `status` and its checkboxes only after implementation **and**
  verification evidence exist.
- Update `_tasks.md` only when the task is complete.
- Leave code changes uncommitted; the operator reviews and commits.
