# Task 04 — saved bulb state and `state show` bulb lines

Status: completed (uncommitted; conductor reviews/commits).

## What was built

- `src/avell_storm_rgb/application/device_state.py` — `Follow`, `FOLLOW_VALUES`,
  `BulbState`, `DeviceState.bulbs`, bulbs (de)serialisation, exact follow validation.
- `src/avell_storm_rgb/adapters/cli/main.py` — `_cmd_state_show` now prints one `bulb`
  line per saved bulb and returns the inventory exit code. `_cmd_state_restore` is
  untouched.
- `tests/test_device_state.py` — UT-034, UT-038, UT-039 plus sorting/omit-key cases.
- `tests/test_cli_state.py` — UT-036, E2E-013, E2E-016 plus `--json` omit-key case.

## Exact model shapes

```python
Follow = Literal["none", "keyboard", "screen", "led_bar"]
FOLLOW_VALUES: tuple[Follow, ...] = ("none", "keyboard", "screen", "led_bar")  # message order

@dataclass(frozen=True)
class BulbState:
    id: str
    remembered: bool = True
    follow: Follow = "none"

@dataclass(frozen=True)
class DeviceState:
    keyboard: KeyboardState | None = None
    led_bar: LedBarState | None = None
    bulbs: tuple[BulbState, ...] = ()

    def __post_init__(self) -> None:  # invariant: sorted by id, everywhere
        object.__setattr__(self, "bulbs", tuple(sorted(self.bulbs, key=lambda b: b.id)))
```

`device_state.py` remains Qt-free and tinytuya-free; it imports only
`bulb_inventory`-free stdlib + domain/USB constants as before.

## `state.json` dict schema (additive, version stays 1)

```json
"devices": {
  "bulbs": {
    "<tuya-id>": {"remembered": true, "follow": "keyboard"}
  }
}
```

- `state_from_dict`: missing/`null` `bulbs` → `bulbs == ()`; a non-object raises
  `bulbs must be an object, got …`; each entry must be an object; `remembered` uses the
  existing `_bool` message; `follow` uses `_follow` with the exact message below.
- `state_to_dict`: writes `devices.bulbs` **only when `state.bulbs` is non-empty**.
  A file without bulbs therefore round-trips with the key still absent (success
  criterion, and `state show --json` keeps the old shape).
- `bulbs` is sorted by id both in memory (`__post_init__`) and in JSON insertion order.

## Exact validation message

```
bulbs.<id>.follow must be one of none, keyboard, screen, led_bar, got 'music'
```

`_follow` uses `FOLLOW_VALUES` in declaration order (not `sorted()` like `_choice`, whose
order would be `led_bar, keyboard, none, screen`). `DeviceStateStore.load` wraps it in
`StateFileError` with that reason, so `state show` prints the `_dx.md` line:
`error: saved state is unreadable (bulbs.<id>.follow …): <path>` and exits 3.

## `state show` formatting (helpers reused)

Reused: `_KIND_LABEL`, the `:<10` kind column, `:<12` remembered/forgotten column,
`describe_look`, `_PREFIX_WIDTH`, `INVENTORY_UNREADABLE` (from `bulb_cli`),
`BulbInventory`/`InventoryFileError` (from `application.bulb_inventory`).

New helpers in `main.py`:

```python
_BULB_NAME_WIDTH = 12
_BULB_NOT_IMPORTED = "(not imported)"
_BULB_UNREADABLE = "(inventory unreadable)"
_bulb_line(bulb, name, note=None) -> str
_print_saved_bulbs(state) -> int   # 0 or 3
```

Human lines (byte-verified against `_dx.md`):

```
bulb      Escritório  eb1a2b3c4d5e6f70819202  remembered  follow keyboard
bulb      Sala        eb1a2b3c4d5e6f70819203  forgotten   follow none
bulb      eb1a2b3c4d5e6f70819202  (not imported)
bulb      eb1a2b3c4d5e6f70819202  (inventory unreadable)
```

- Inventory is read **directly** via `BulbInventory.load()`; `tuya_available()` is never
  called, so names work without the `tuya` extra.
- Missing file → `(not imported)` per bulb, exit 0.
- Corrupt/unreadable → device lines already printed, each bulb line `(inventory
  unreadable)`, then `error: bulb inventory is unreadable (<reason>): <path>` on stderr,
  exit 3. This happens even when there are zero saved bulbs (matches `_dx.md` Errors).
- A saved id absent from a readable inventory → `(not imported)`.
- `--json` does not touch the inventory: `devices.bulbs` is exactly as stored; the key is
  omitted when `bulbs == ()`.
- `state restore` only iterates `_saved_devices()` (keyboard/led_bar), so it prints no
  bulb line and has no `open_bulb` reference at all (`grep` is empty).

## What task_05 must implement (pruning)

Only `AppFacade` writes `state.json`, so pruning belongs there, not in `device_state`:

1. On load/rewrite, drop `devices.bulbs` entries whose id is missing from the inventory
   **only if** `tuya_available()` is true **and** `BulbInventory.load()` succeeded.
2. If the extra is absent, or the inventory is missing/corrupt/unreadable, keep every
   entry as-is and rewrite it unchanged (UT-035/UT-037).
3. Do not add pruning to `DeviceStateStore` or the CLI: the model must keep round-tripping
   whatever it is given.

## Verification evidence

- `uv run pytest -q tests/test_device_state.py tests/test_cli_state.py` → **46 passed**.
- `uv run pytest -q -m "not hardware"` → **427 passed, 11 skipped, 5 failed**; the 5 are
  the known pre-existing `tests/test_gui_pages.py::test_page_component_ready[*]` Qt/Kirigami
  environment failures (416 baseline + 11 new cases).
- Manual, real temp `XDG_CONFIG_HOME` and the real `avell-storm-rgb` binary:
  - normal inventory → two named `bulb` lines, exit 0;
  - missing inventory → two `(not imported)` lines, exit 0;
  - corrupt inventory → keyboard + led-bar lines first, two `(inventory unreadable)` lines,
    stderr inventory error, exit 3;
  - current-release file (no `devices.bulbs`) loads `bulbs == ()` and rewrites with the
    key still absent;
  - `state restore` printed only the led-bar/keyboard lines, exit 0, and a spy on
    `bulb_cli.open_bulb` recorded zero calls.
- `grep -rn "PySide6\|tinytuya" src/avell_storm_rgb/application/device_state.py` → no match.
- `grep -rn "open_bulb" src/avell_storm_rgb/adapters/cli/main.py` → no match.
