---
status: completed
title: "Task 1: Bulb colour, inventory and driver port"
type: backend
complexity: medium
---

# Task 1: Bulb colour, inventory and driver port

## Overview

This task adds the pure core every later bulb task builds on: colour/range math, the private inventory that holds imported bulbs and their local keys, and the `BulbDriver` port. After it, a tinytuya `devices.json` can become a validated 0600 inventory and a target can be resolved by name or id, without importing `tinytuya` or Qt.

## Shippable Outcome

- **Outcome:** `avell_storm_rgb.domain.bulb_color` converts brightness/temperature/colour and parses a status dict; `avell_storm_rgb.application.bulb_inventory` imports, upserts, removes and matches bulbs in `$XDG_CONFIG_HOME/avell-storm-rgb/tuya_devices.json` (mode 0600); `ports.protocols.BulbDriver` describes the driver that later tasks implement and fake.
- **Verify in this task:** `tests/test_bulb_color.py` and `tests/test_bulb_inventory.py` (Tests below) plus the existing suites.
- **Integration verification:** none. task_02 consumes the port and inventory, task_03/task_04 consume the inventory, task_05 fakes the port.

## Requirements

- Interfaces exactly as `_spec.md` → *Core Interfaces* (`BulbRecord`, `BulbStatus`, `BulbFailure`, `default_inventory_path`, `BulbInventory`, `parse_tinytuya_devices`, `match_target`) and *Data Models* → inventory file table.
- Rules: BR-1 (id is identity; names case- and accent-insensitive; duplicates allowed), BR-2 (import filter and exact skip reasons), BR-3 (keys private), BR-10 (ranges and conversions).
- File contract: `version: 1`, `devices[]` fields from the table, `0600`, tmp file + `os.replace`, missing file → `[]`, invalid file → `InventoryFileError`.
- `BulbStatus` and `status_from_dps` live in `domain/bulb_color.py` and are re-exported from `bulb_inventory.py`, so the documented import path in `_spec.md` still holds.
- `BulbRecord.__repr__`/`__str__` must not contain `key` (the cross-surface assertion is UT-072 in task_02; the safe representation starts here).
- No `tinytuya` import, no `PySide6` import, no I/O in `domain/`.

## Subtasks

- [x] 1.1 `domain/bulb_color.py`: `percent_to_device`, `device_to_percent`, `rgb_to_colour_data_v2`, `colour_data_v2_to_rgb`, `average_rgb`, `changed_enough`, `status_from_dps`, `BulbStatus`.
- [x] 1.2 `application/bulb_inventory.py`: `BulbRecord`, `BulbFailure`, `Skipped`, `ImportReport`, `InventoryFileError`, `default_inventory_path`.
- [x] 1.3 `BulbInventory.load`/`save`/`upsert`/`remove`/`set_last_ip` with atomic 0600 writes and stable file order.
- [x] 1.4 `parse_tinytuya_devices` with `dj` filter, missing-key and missing-category skips, lower-case MACs and the `3.3` protocol default.
- [x] 1.5 `match_target` (`all` / name / id) plus `UnknownTarget` and `AmbiguousTarget`.
- [x] 1.6 `ports/protocols.py`: `BulbDriver` protocol (additive, `runtime_checkable`).
- [x] 1.7 Fixture `tests/fixtures/tinytuya_devices.json` with three `dj` bulbs and fictional keys; unit suites.

## Implementation Details

### Relevant Files

- `src/avell_storm_rgb/domain/ledbar_colors.py:1-60` — existing pure-domain style and parsing helpers to mirror.
- `src/avell_storm_rgb/application/device_state.py:313-373` — `DeviceStateStore` path, atomic save and quarantine pattern to mirror for the inventory.
- `src/avell_storm_rgb/ports/protocols.py:1-44` — where `BulbDriver` joins `KeyboardRgbDriver` and `LedBarDriver`.
- `tests/conftest.py` — `XDG_CONFIG_HOME` isolation that keeps inventory tests off the real config.
- `tests/test_ledbar_domain.py` — table-driven domain test style.

### Dependent Files

- `src/avell_storm_rgb/application/device_state.py` — imports the inventory type only in later tasks; no edit here.
- `tests/test_protocols.py` — may gain the `BulbDriver` runtime-checkable assertion; keep existing cases green.

### Related ADRs

- [ADR-001: tinytuya extra, imported keys, private inventory file](adrs/adr-001.md) — the 0600 inventory and key-privacy decisions implemented here.

## Deliverables

- `src/avell_storm_rgb/domain/bulb_color.py`
- `src/avell_storm_rgb/application/bulb_inventory.py`
- `BulbDriver` in `src/avell_storm_rgb/ports/protocols.py`
- `tests/test_bulb_color.py`, `tests/test_bulb_inventory.py`, `tests/fixtures/tinytuya_devices.json`

## Tests

- [x] UT-001, UT-002, UT-003, UT-004, UT-005, UT-006 — range conversion, HSV round-trip, black clamp, averaging, status parsing, change threshold
- [x] UT-010, UT-011, UT-012, UT-013, UT-014, UT-015, UT-016, UT-017, UT-018, UT-019 — wizard parsing, upsert/update/unchanged, invalid file, skips, zero bulbs, target matching and its errors
- [x] UT-070 — inventory file mode `0o600`, including a save over an existing file

## Success Criteria

- `make test` is green, including the existing suites.
- `grep -rnE "^(from|import) tinytuya" src/avell_storm_rgb/domain src/avell_storm_rgb/application/bulb_inventory.py` finds nothing.
- `grep -rn "PySide6" src/avell_storm_rgb` finds nothing.
- A fresh inventory created by `save` is `0o600`, and an existing `0o600` file keeps that mode after `upsert`.
