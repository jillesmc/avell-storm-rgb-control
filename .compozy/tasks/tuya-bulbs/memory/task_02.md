# Task 02 — Tuya LAN adapter and bulb opener

Status: completed (uncommitted; conductor reviews/commits).

## What was built

- `pyproject.toml` + `uv.lock`: extra `tuya = ["tinytuya>=1.20,<2"]`, added with
  `uv add --optional tuya "tinytuya>=1.20,<2"` (resolved `tinytuya==1.20.0`).
- `src/avell_storm_rgb/infrastructure/tuya/__init__.py` — re-exports the adapter API.
- `src/avell_storm_rgb/infrastructure/tuya/bulb.py` — the only module that imports
  `tinytuya`, lazily inside `_tinytuya()` / `_new_device()` / `discover_bulb()`.
- `src/avell_storm_rgb/application/bulb_facade.py` — `tuya_available()`, `open_bulb()`,
  `arp_lookup()`.
- `tests/test_tuya_bulb_adapter.py` (75 cases), `tests/test_bulb_facade.py` (11 cases).

## Public signatures

`infrastructure/tuya/bulb.py`:

```python
BulbError(Exception)                 # base; message is a fixed phrase
BulbUnreachable(BulbError)           # 901/902/905, timeouts, OSError, exhausted resolution
KeyRejected(BulbError)               # Err 914 with no usable protocol discovery

Discovered(ip: str, protocol: str = "")           # frozen; protocol "" = unknown
discover_bulb(bulb_id: str, timeout: float = 6.0) -> Discovered | None
    # tinytuya.deviceScan(verbose=False, maxretry=timeout, poll=False, byID=True)
    # never raises; poll=False so discovery opens no TCP connection

TuyaBulb(record: BulbRecord, ip: str, *, device=None,
         discover=None, command_timeout=5.0, discovery_timeout=6.0)
    .status() -> BulbStatus
    .set_power(on: bool) -> None
    .set_brightness(percent: int, status: BulbStatus | None = None) -> None
    .set_white(temperature_percent: int | None = None, status: BulbStatus | None = None) -> None
    .set_colour(rgb: tuple[int, int, int]) -> None
    .push_colour(rgb: tuple[int, int, int]) -> None
    .hold_open(persistent: bool) -> None
    .close() -> None
    # read-only: .name .bulb_id .ip .protocol ; repr/str never contain the key
```

`application/bulb_facade.py`:

```python
tuya_available() -> bool                       # importlib.util.find_spec("tinytuya") is not None
arp_lookup(mac: str) -> str | None             # read-only `ip neigh`
open_bulb(record: BulbRecord, inventory: BulbInventory, *,
          discover_timeout: float = 6.0, probe_timeout: float = 1.5,
          cache: MutableMapping[str, str] | None = None,
          arp: Callable[[str], str | None] | None = None,
          discover: Callable[[str, float], Discovered | None] | None = None,
          probe: Callable[[str, float], bool] | None = None,
          driver_factory: Callable[[BulbRecord, str], BulbDriver] | None = None) -> BulbDriver
# re-exports BulbError, BulbUnreachable, KeyRejected, Discovered
```

## Exact DPS payloads (all writes via `set_multiple_values`)

| Call | Payload | nowait |
|------|---------|--------|
| `set_power(True)` | `{"20": True}` | False |
| `set_brightness(40, white)` | `{"20": True, "22": 400}` | False |
| `set_brightness(40, colour rgb=(255,0,0))` | `{"20": True, "24": "000003e80190"}` | False |
| `set_white(0, status)` | `{"20": True, "21": "white", "23": 0}` | False |
| `set_white(None, status.temperature=20)` | `{"20": True, "21": "white", "23": 200}` | False |
| `set_white(None, None)` | `{"20": True, "21": "white"}` (no `23`) | False |
| `set_colour((255,136,0))` | `{"20": True, "21": "colour", "24": "002003e803e8"}` | False |
| `push_colour((0,0,255))` | `{"21": "colour", "24": "00f003e803e8"}` (never `20`) | True |

Brightness uses `percent_to_device` (validates 1–100 → 10–1000). Temperature uses
`percent*10` (0 is legal, 0 = warmest). Colour-mode brightness keeps the hue/sat of
`status.rgb` and overrides V with `percent*10`.

## Error mapping and messages

- `Err` 914 → one `discover_bulb(id, 6.0)`; retry **once** only when the discovered
  protocol parses and differs from the stored one. Otherwise, or when the retry fails,
  `KeyRejected("local key or protocol rejected")`. The new version sticks on the driver
  (`device.set_version`) but is **not** written back to the inventory (spec only asks for
  the IP write-back).
- `Err` 901/902/905 → `BulbUnreachable("bulb is not reachable")`.
- `OSError`/`TimeoutError`/`ConnectionError` raised by tinytuya → same `BulbUnreachable`.
- Any other `Err`, or any other exception → `BulbError("bulb command failed")`.
- Only the fixed phrase reaches the message. `Error`/`Payload` are never copied, never
  logged; the numeric `Err` code and the call label go to `avell_storm_rgb.tuya` at DEBUG.
- `BulbUnreachable` raised by `open_bulb` carries the **bulb name** (`str(exc) == "Sala"`,
  UT-032).
- After the lazy import: `logging.getLogger("tinytuya").setLevel(logging.WARNING)` on every
  `_tinytuya()` call. tinytuya's debug switch is never enabled.

## IP resolution seams (how tests inject)

`open_bulb` tries, in order: process cache (`_IP_CACHE`, module level) → `arp(record.mac)`
→ `record.last_ip` → `discover(record.id, discover_timeout)`. The first three are
validated with `probe(ip, probe_timeout)` (default: TCP connect to 6668, ~ms, no protocol
traffic, no key). The discovery result is accepted without a probe (it just answered UDP).
Each IP is probed at most once. The winner goes into the cache, and
`inventory.set_last_ip(id, ip)` runs **only when it differs from `record.last_ip`**.
Nothing answers → `BulbUnreachable(record.name)`. `driver_factory(record, ip)` builds the
driver last, so a factory failure writes nothing.

All five seams (`cache`, `arp`, `discover`, `probe`, `driver_factory`) are keyword-only and
default to the real implementations, so tests never open a socket or run `ip neigh`.

## What task_03 and task_05 must call

- Gate every bulb surface on `tuya_available()`; the CLI hint text lives in `_dx.md`.
- `driver = open_bulb(record, inventory)` then use only the `BulbDriver` methods, and
  `driver.close()` when done (one driver per bulb). `open_bulb` does **no** status read:
  the caller decides (BR-6/BR-7).
- Catch `KeyRejected` / `BulbUnreachable` / `BulbError` from
  `avell_storm_rgb.application.bulb_facade` (also re-exported by
  `avell_storm_rgb.infrastructure.tuya`). Map them to the `_dx.md` strings; never print
  `exc` verbatim into JSON without the `<ExceptionType>: <message>` shape.
- `set_brightness(percent, status)` / `set_white(temp, status)` take the caller's snapshot;
  pass `None` for brightness only when no snapshot exists (it costs one extra read on the
  same driver). `set_white` never reads.
- `push_colour` only while the last known power is on; `hold_open(True)` for follow,
  `hold_open(False)`/`close()` on release (ADR-003).
- `BulbWorker` may call `open_bulb` on its `bulb-*` thread; nothing here touches Qt.

## Decisions where the spec was silent

1. **Exceptions live in `infrastructure/tuya/bulb.py`** (re-exported by `bulb_facade`), not
   in a new domain module: the deliverables list is fixed and both the adapter and the
   facade need the same types.
2. **`probe` = TCP connect to 6668.** UT-031 needs "`last_ip` fails" and `_spec.md` says "a
   different **successful** IP", so candidate IPs must be validated before returning a
   driver. A bare TCP connect validates reachability without a status read (which would
   double every command's round trips) and without the key.
3. **`set_white(..., None)` does not read status.** UT-026 (`{"20": True, "21": "white"}`
   with no `23`) and `_dx.md` ("`bulb white` without `--temp` … needs no read") both require
   it; the task prompt's generic "status=None means read once" applies to `set_brightness`
   only.
4. **All writes use `set_multiple_values`**, including power (`{"20": on}`): it keeps the
   exact DPS, avoids tinytuya's `dpset` detection and its `switch: True` additions (KD-6).
5. **`BulbRecord` is not imported at runtime** by the adapter (TYPE_CHECKING only), so
   `infrastructure` does not depend on `application`.
6. **Discovery protocol is not persisted.** Only the IP is written back, as specified; a
   discovered-but-different protocol is retried and kept in memory for that driver.
7. **Logger names:** `avell_storm_rgb.gui` for the discovery/`via` DEBUG line (as
   `_spec.md` *Monitoring* says), `avell_storm_rgb.tuya` for the adapter's internal DEBUG.

## Verification evidence

- `uv sync --extra tuya` → `uv run python -c "import tinytuya; print(tinytuya.__version__)"`
  → `1.20.0`.
- `uv run pytest -q tests/test_tuya_bulb_adapter.py tests/test_bulb_facade.py` →
  **86 passed** (not skipped; the adapter suite uses `pytest.importorskip("tinytuya")`).
- `uv run pytest -q -m "not hardware"` → **373 passed, 11 skipped, 5 failed**; the 5 are the
  known pre-existing `tests/test_gui_pages.py::test_page_component_ready[*]` environment
  failures (287 baseline + 48 from task_01 + 86 from this task).
- Without tinytuya: `sys.modules["tinytuya"] = None` then
  `import avell_storm_rgb`, `bulb_facade`, `infrastructure.tuya`, `adapters.cli.main` →
  all import, `tuya_available() is False`, and `"tinytuya" in sys.modules` stays false.
- `grep -rnE "^(from|import) tinytuya" src/avell_storm_rgb --include='*.py'` → no match
  (the import is indented inside `_tinytuya()`); the non-anchored
  `grep -rn "import tinytuya" src/avell_storm_rgb` matches only
  `infrastructure/tuya/bulb.py:87`.
- `grep -rn "set_debug" src tests` → only the spy/assertion in
  `tests/test_tuya_bulb_adapter.py` (405, 407).
- No `PySide6` import added; `domain/physical_key_map.py:5` remains the known pre-existing
  debt from `MEMORY.md`.
