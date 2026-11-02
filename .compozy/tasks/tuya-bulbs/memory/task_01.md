# Task 01 — bulb colour, inventory and driver port

Status: completed (uncommitted; conductor reviews/commits).

## What was built

- `src/avell_storm_rgb/domain/bulb_color.py` — pure colour/range/status maths, no I/O, no Qt.
- `src/avell_storm_rgb/application/bulb_inventory.py` — private inventory, tinytuya import,
  target matching; imports neither `tinytuya` nor Qt.
- `BulbDriver` added to `src/avell_storm_rgb/ports/protocols.py` (additive, `runtime_checkable`).
- `tests/test_bulb_color.py`, `tests/test_bulb_inventory.py`, `tests/fixtures/tinytuya_devices.json`.
- `tests/test_protocols.py` gained the `BulbDriver` runtime-checkable cases (existing cases untouched).

## Public signatures

`domain/bulb_color.py`:

```python
BulbStatus(on: bool, mode: Literal["white", "colour", "scene", "music"],
           brightness: int, temperature: int | None,
           rgb: tuple[int, int, int] | None)
percent_to_device(percent: int) -> int                    # 1..100 -> 10..1000
device_to_percent(value: int) -> int                      # 0..1000 -> 0..100
rgb_to_colour_data_v2(rgb: tuple[int, int, int]) -> str   # 12 hex digits
colour_data_v2_to_rgb(value: str) -> tuple[int, int, int]
average_rgb(colours: Iterable[tuple[int, int, int]]) -> tuple[int, int, int]
changed_enough(a, b, threshold: int = 8) -> bool
status_from_dps(dps: Mapping[str, Any]) -> BulbStatus
```

`application/bulb_inventory.py`:

```python
BulbRecord(id, name, key, mac, protocol="3.3", last_ip=None)   # frozen
BulbFailure(reason, detail)                                    # frozen
Skipped(id, name, reason)                                      # frozen
ImportResult(id, name, status, reason=None)                    # frozen
ImportReport(results: tuple[ImportResult, ...] = ())           # .imported == len(results)
InventoryFileError(path, reason)                               # .path, .reason
ImportFileError(reason)                                        # .reason
UnknownTarget(target, known)                                   # .target, .known
AmbiguousTarget(target, ids)                                   # .target, .ids
default_inventory_path() -> Path
parse_tinytuya_devices(doc: Any) -> tuple[list[BulbRecord], list[Skipped]]
match_target(records: Sequence[BulbRecord], target: str) -> list[BulbRecord]
BulbInventory(path: Path | None = None)                        # .path, .exists()
    .load() -> list[BulbRecord]
    .save(records: Sequence[BulbRecord]) -> None
    .upsert(records: Sequence[BulbRecord]) -> ImportReport
    .remove(bulb_id: str) -> BulbRecord | None
    .set_last_ip(bulb_id: str, ip: str) -> None
```

`BulbStatus` and `status_from_dps` are imported and re-exported from `bulb_inventory`
(both are in its `__all__`), so the `_spec.md` import path holds.

`ports/protocols.py`:

```python
@runtime_checkable
class BulbDriver(Protocol):
    status() -> BulbStatus
    set_power(on: bool) -> None
    set_brightness(percent: int, status: BulbStatus | None) -> None
    set_white(temperature_percent: int | None, status: BulbStatus | None) -> None
    set_colour(rgb: tuple[int, int, int]) -> None
    push_colour(rgb: tuple[int, int, int]) -> None
    hold_open(persistent: bool) -> None
    close() -> None
```

## Decisions where the spec was silent

1. **`ImportFileError` exists in addition to `InventoryFileError`.** UT-013 names
   `ImportFileError` for parse failures; task 01 names `InventoryFileError` for file-load
   failures. They are separate exceptions, both with `.reason`. `parse_tinytuya_devices`
   raises `ImportFileError`; `BulbInventory.load` raises `InventoryFileError`.
2. **`parse_tinytuya_devices` accepts either decoded JSON or JSON text.** UT-013 requires
   `parse_tinytuya_devices("{}")` → `expected a list of devices` and invalid text →
   `invalid JSON at line 1 column 2`, so a `str` argument is parsed with `json.loads` first.
3. **`ImportResult` helper.** `ImportReport` needs per-record `added`/`updated`/`unchanged`
   plus `reason` for the CLI (`_dx.md`), which the spec does not spell out. `imported` is a
   property equal to `len(results)`; an empty input returns `ImportReport()` without writing.
4. **Skip reasons beyond the documented three.** `missing id` (entry has no id) and
   `not an object` (non-dict list item) are defensive additions; the documented reasons are
   `no local key`, `not a bulb (category cz)`, `missing category`.
5. **Upsert keeps the learned `last_ip`.** An existing record keeps its `last_ip`; the
   imported `ip` only fills it when the stored one is `None`. `protocol` changes count as
   `updated` with reason `protocol changed` (the documented reasons stay key/name/mac).
   Reasons are joined in the order key, name, mac, protocol.
6. **0600 is enforced, not merely preserved.** `_write` uses `tempfile.mkstemp` in the
   target directory, fsync, `os.chmod(tmp, 0o600)` and `os.replace`, so an existing looser
   file is tightened to 0600. Writers also take an advisory `flock` on
   `<inventory>.lock` (ADR-001); the lock file is created next to the inventory.
7. **Status parsing.** Mode defaults to `"white"` when DPS 21 is missing/unknown.
   Temperature is parsed only in white mode; colour brightness comes from DPS 24 V, and
   DPS 22 is the fallback. `brightness == 0` means the payload carried none (device 0 maps
   to 0 %, which is also how a temperature of 0 is represented).
8. **`match_target`.** `"all"` is exact lowercase; an exact id wins over a name; names are
   NFKD-normalised + casefolded. Unknown → `UnknownTarget` listing names; multiple name
   matches → `AmbiguousTarget` listing ids, matching the `_dx.md` wording.

## For later tasks

- Use `BulbInventory` as-is; do not add a second writer. `save`/`upsert`/`remove`/
  `set_last_ip` already lock and replace atomically.
- `BulbRecord.__repr__`/`__str__` render `key='set'` (or `'missing'`) and never the key.
- `BulbDriver` is `runtime_checkable` by method name only; `BulbStatus` is imported under
  `TYPE_CHECKING`, so fakes only need the method names.
- `status_from_dps` expects string DPS keys (`"20"`, `"21"`, `"22"`, `"23"`, `"24"`).
- Tests use the temp `XDG_CONFIG_HOME`; `default_inventory_path()` follows the same
  `~/.config` fallback as `default_state_path()`.

## Verification evidence

- `uv run pytest -q tests/test_bulb_color.py tests/test_bulb_inventory.py tests/test_protocols.py`
  → **48 passed**.
- `uv run pytest -q -m "not hardware"` → **287 passed, 11 skipped, 5 failed**; the 5 are the
  known pre-existing `tests/test_gui_pages.py::test_page_component_ready[*]` environment
  failures (Qt/Kirigami 6.12 vs 6.11 plugin mismatch), unchanged from baseline.
- UT-070 observed mode: new inventory `0o600`; overwrite of the existing file `0o600`.
- `grep -rnE "^(from|import) tinytuya" src/avell_storm_rgb/domain src/avell_storm_rgb/application/bulb_inventory.py`
  → no matches.
- `grep -rn "PySide6" src/avell_storm_rgb` → **one pre-existing match**:
  `src/avell_storm_rgb/domain/physical_key_map.py:5:from PySide6.QtCore import Qt`
  (tracked since commit `d7175bc`, outside task 01's file scope and left untouched). The
  task's "must find nothing" criterion cannot pass until a separate task removes that
  dependency; this change adds no PySide6 import.
