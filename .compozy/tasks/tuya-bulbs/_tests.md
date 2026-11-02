# Test Specification: Tuya smart bulbs

Canonical test contract for Tuya bulb integration. Companion to `_spec.md`.
Derived from `_user_stories.md` (behavior), `_spec.md` Part II (components), `_dx.md` (CLI journeys) and `_uiux.md` (GUI journeys).

## Strategy

- **Framework**: pytest (`tests/`), `make test` (`-m "not hardware"`). GUI cases need the `gui` extra and Kirigami; they skip otherwise (existing behaviour). `pytest-qt` stays out (repo rule).
- **Fakes at I/O boundaries only**:
  - `FakeBulb` (new, in `tests/backend_fakes.py`) implements `BulbDriver`: a call journal, a programmable `BulbStatus`, `fail_on`, `unreachable`, an open count, and an optional `reject_second_connection` flag (Safety Invariant 9).
  - A fake `open_bulb` factory for CLI and backend tests.
  - Fake `arp_lookup` / `discover` callables for IP resolution.
  - A stub `tinytuya.BulbDevice` (records `set_multiple_values`, `set_value`, `turn_on`/`turn_off`) for adapter payload tests, guarded with `pytest.importorskip("tinytuya")`.
  - A fake frame source (yields PIL images, honours the stop event) for `ScreenFrameHub`.
  - Existing `FakeKeyboard`/`FakeLedBar`, `drain(worker)`.
- **Isolation**: `tests/conftest.py` already points `XDG_CONFIG_HOME` at `tmp_path`; the inventory and `state.json` both live there. The "extra missing" path is tested by monkeypatching `tuya_available()` → `False`.
- **Conventions**: one behaviour per test; names `test_<unit>_<behaviour>`; table-driven with `pytest.mark.parametrize` for ranges and conversions.

## Coverage Matrix

| Source | Behavior | Unit | Integration | E2E |
|--------|----------|------|-------------|-----|
| US-001 | Import bulbs | UT-010, UT-011 | — | E2E-001, E2E-020 |
| US-001.AC-3 | Re-import upserts | UT-012 | — | E2E-002 |
| US-001.EC-1 | Not JSON / not a list | UT-013 | — | E2E-003 |
| US-001.EC-2 | Entry without key skipped | UT-014 | — | — |
| US-001.EC-3 | Non-bulb skipped | UT-015 | — | E2E-002 |
| US-001.EC-4 | Zero bulbs | UT-016 | — | E2E-004 |
| US-001.EC-5 | Import while connected | — | IT-005 | — |
| US-002 | Connect remembers | UT-040 | IT-001 | E2E-021 |
| US-002.EC-1 | Unreachable → not remembered | UT-041 | — | — |
| US-002.EC-2 | Double connect | UT-042 | — | — |
| US-002.EC-3 | Wrong key or protocol message | UT-043 | — | — |
| US-003.AC-1 | Disconnect keeps key | UT-044 | IT-002 | — |
| US-003.AC-2 | Remove deletes key + state | UT-045 | IT-003 | E2E-022 |
| US-003.AC-3 | Back to Devices | — | — | E2E-023 |
| US-003.EC-1 | Remove cancelled | — | — | E2E-022 |
| US-003.EC-2 | Remove while following | UT-080 | — | — |
| US-004 | Start reads only | UT-046 | IT-004 | — |
| US-004.AC-3 | Unknown before first read | UT-047 | — | E2E-024 |
| US-004.EC-1 | IP changed | UT-030, UT-031 | — | — |
| US-004.EC-2 | Network late at login | UT-048 | — | — |
| US-005 | Unavailable + Retry | UT-049, UT-050 | — | E2E-024 |
| US-005.EC-1 | Retry still down, no busy | UT-051 | — | — |
| US-005.EC-2 | One bulb down, others fine | UT-060 | — | — |
| US-006 | Light switch | UT-052 | — | E2E-025 |
| US-006.EC-1 | Failure snaps back | UT-053 | — | — |
| US-006.EC-2 | Rapid toggles ordered | UT-061 | — | — |
| US-007 | Brightness per mode | UT-020, UT-021 | — | — |
| US-007.EC-1 | Debounce | — | — | E2E-028 |
| US-007.EC-2 | Minimum 1 % | UT-001 | — | E2E-008 |
| US-008 | White temperature | UT-022 | — | — |
| US-008.EC-1 | Scene/music mode shown | UT-005 | — | — |
| US-009 | Colour | UT-023 | — | E2E-007 |
| US-009.EC-1 | Black clamps to 1 % | UT-003 | — | — |
| US-010 | Outside changes / refresh cadence | UT-054, UT-055, UT-057 | — | — |
| US-010.EC-1 | Hidden → no reads | UT-056 | — | — |
| US-011 | CLI control/status | UT-017 | — | E2E-005, E2E-006, E2E-007, E2E-015 |
| US-011.EC-1 | Unknown name | UT-018 | — | E2E-009 |
| US-011.EC-2 | Ambiguous name | UT-019 | — | — |
| US-011.EC-3 | `all` with one offline | — | — | E2E-006 |
| US-011.EC-4 | Out of range | — | — | E2E-008 |
| US-011.EC-5 | No inventory | — | — | E2E-010 |
| US-012 | list / remove / state show | — | — | E2E-011, E2E-012, E2E-013, E2E-016 |
| US-012.AC-4 | `state restore` ignores bulbs | UT-036 | — | — |
| US-012.EC-1 | GUI drops removed ids | UT-035 | — | — |
| US-013.AC-1 | No extra → GUI unchanged | — | — | E2E-026 |
| US-013.AC-2 | No extra → CLI hint | — | — | E2E-014 |
| US-013.EC-1 | Extra, nothing imported | — | — | E2E-020 |
| US-013.EC-2 | Bulbs kept when extra removed | UT-037 | — | — |
| US-014 | Keys never displayed | UT-070, UT-071, UT-072 | IT-006 | E2E-011 |
| US-014.EC-1 | Error text without payload | UT-073 | — | — |
| US-015 | Follow keyboard | UT-081, UT-082, UT-083 | IT-010 | — |
| US-015.EC-1 | Firmware effect → no colour | UT-084 | — | — |
| US-015.EC-2 | Keyboard off → no colour | UT-085 | — | — |
| US-015.EC-3 | Threshold | UT-086 | — | — |
| US-016 | Follow screen, shared capture | UT-090, UT-091, UT-092 | IT-011 | — |
| US-016.EC-1 | Screen option absent | UT-087 | — | E2E-027 |
| US-016.EC-2 | Picker cancelled | UT-093 | — | — |
| US-016.EC-3 | Captured window closed | UT-094 | — | — |
| US-017 | Follow LED bar | UT-004, UT-088 | IT-012 | — |
| US-017.EC-1 | LED bar option absent | UT-087 | — | E2E-027 |
| US-017.EC-2 | LED bar off | UT-089 | — | — |
| US-018.AC-1 | Follow resumes after restart | UT-034 | IT-013 | — |
| US-018.AC-2 | Never push while off | UT-024, UT-095, UT-101 | — | — |
| US-018.AC-3 | Phone switch-off stops pushes ≤ 5 s | UT-096 | — | — |
| US-018.EC-1 | Disconnect stops, Connect resumes | UT-097 | — | — |
| US-018.EC-2 | Dropped → unavailable, socket closed | UT-098 | — | — |
| US-018.EC-3 | Other clients locked out | reason: documented behaviour; message checked in E2E-027 | — | E2E-027 |
| Follow-screen refactor (ADR-004) | Keyboard behaviour unchanged | UT-099, UT-100 | IT-014 | — |
| Safety Inv. 2, 8, 9 | No USB thread / busy; `opDone` on the GUI thread; one driver per bulb | UT-062, UT-063, UT-064 | IT-015 | — |
| `domain/bulb_color` | HSV round-trip, change threshold | UT-002, UT-006 | — | — |
| `tuya/bulb` adapter | Error dicts; 914 → key or protocol; 905/timeout → unreachable | UT-025, UT-026, UT-027, UT-028 | — | — |
| `bulb_facade` | Resolution exhausted; extra detection | UT-032, UT-033 | — | — |
| `device_state` bulbs | Invalid follow rejected; files without `bulbs` load | UT-038, UT-039 | — | — |

## Unit Tests

### `domain/bulb_color` (Spec: Core Interfaces; BR-10, BR-11)

- **UT-001** (boundary): `percent_to_device(1)` → `10`, `percent_to_device(100)` → `1000`, `percent_to_device(40)` → `400`; `0` and `101` raise `ValueError`.
- **UT-002** (happy): `rgb_to_colour_data_v2((255, 136, 0))` → `"002003e803e8"` (h=32, s=1000, v=1000) and back via `colour_data_v2_to_rgb` within ±2 per channel.
- **UT-003** (boundary): `rgb_to_colour_data_v2((0, 0, 0))` → V = `10` (clamped to 1 %), not 0.
- **UT-004** (happy): `average_rgb([(255, 0, 0), (0, 0, 255)])` → `(128, 0, 128)`; `average_rgb([])` raises `ValueError`.
- **UT-005** (happy): parsing a status `{"20": true, "21": "scene", "22": 500, …}` gives `BulbStatus(on=True, mode="scene", brightness=50, …)`; `{"21": "colour", "24": "000003e803e8"}` gives `rgb=(255, 0, 0)` and brightness 100 (from V).
- **UT-006** (boundary): `changed_enough((10, 10, 10), (17, 10, 10))` → `False`; `(18, 10, 10)` → `True` (threshold 8).

### `application/bulb_inventory` (Spec: Data Models; BR-1–BR-3)

- **UT-010** (happy): `parse_tinytuya_devices` on a fixture copy of the wizard format (3 `dj` entries, fictional keys) returns 3 `BulbRecord`s with lower-case MACs and `protocol` from `version`, defaulting to `"3.3"` when blank.
- **UT-011** (happy): `BulbInventory.upsert` on an empty file writes `{"version": 1, "devices": [...]}` and reports 3 × `added`.
- **UT-012** (idempotency): re-upsert with Sala's key changed → `updated` (`key changed`), the others `unchanged`; no record removed; file order stable.
- **UT-013** (error): `parse_tinytuya_devices("{}")`, a dict, or invalid JSON → `ImportFileError` with reason `expected a list of devices` / `invalid JSON at line 1 column 2`.
- **UT-014** (error): entry without `key` → in `skipped` with reason `no local key`.
- **UT-015** (error): entry with `category: "cz"` → skipped `not a bulb (category cz)`.
- **UT-016** (boundary): list with zero bulbs → `ImportReport.imported == 0`; inventory file unchanged.
- **UT-017** (happy): `match_target(records, "all")` → all; `"escritorio"` → Escritório; the id → that bulb.
- **UT-018** (error): `match_target(records, "cozinha")` → `UnknownTarget` listing `Quarto, Escritório, Sala`.
- **UT-019** (error): two records named `Luz` → `AmbiguousTarget` with both ids.
- **UT-070** (state): a new inventory file has mode `0o600`; a save over an existing file keeps `0o600` (tmp + `os.replace`).

### `infrastructure/tuya/bulb` adapter (Spec: Core Interfaces; KD-6; BR-9, BR-12) — `importorskip("tinytuya")`

- **UT-020** (happy): white-mode `BulbStatus` snapshot, `set_brightness(40, status)` → stub receives DPS `{"20": True, "22": 400}`.
- **UT-021** (happy): colour-mode red `BulbStatus`, `set_brightness(40, status)` → DPS 24 with the same hue/sat and V = 400, plus `"20": True`.
- **UT-022** (happy): `set_white(0, status)` → `{"20": True, "21": "white", "23": 0}`.
- **UT-023** (happy): `set_colour((255, 136, 0))` → `{"20": True, "21": "colour", "24": "002003e803e8"}`.
- **UT-024** (state): `push_colour((0, 0, 255))` → exactly `{"21": "colour", "24": …}` with `nowait=True`; DPS `20` never present.
- **UT-025** (error): every device method returns a dict; `{"Err": 914, …}` → `KeyRejected`; 901, 902, 905 and a timeout → `BulbUnreachable`; any other `Err` → `BulbError`; with a sentinel `Error`/`Payload`, the raised message contains neither (checked for `status`, `set_power`, `set_brightness`, `set_white`, `set_colour`, `push_colour`).
- **UT-026** (state): `set_white(None, status)` → `{"20": True, "21": "white", "23": status.temperature}`; `set_white(None, None)` → `{"20": True, "21": "white"}` with no DPS 23.
- **UT-027** (state): `set_brightness(40, None)` on the stub → exactly one `status()` read on the same stub instance before the write, and the mode for the target DPS comes from that read (no second connection).
- **UT-028** (error): a stored protocol gets 914, discovery reports a different version (`3.3`), and the retry succeeds; when discovery reports the same or no version, or the retry also fails, the adapter raises `KeyRejected("local key or protocol rejected")`.

### `application/bulb_facade` — IP resolution (Spec: Core Interfaces)

- **UT-030** (ordering): ARP has the MAC → that IP is used; discovery not called.
- **UT-031** (ordering): ARP miss, `last_ip` fails, discovery finds the id at `.23` → `.23` used and `inventory.set_last_ip` written; nothing written when the IP is unchanged.
- **UT-032** (error): every step misses → `BulbUnreachable("Sala")`.
- **UT-033** (happy): `tuya_available()` is `False` when `find_spec("tinytuya")` is `None`.

### `device_state` — bulbs (Spec: Data Models; BR-15)

- **UT-034** (happy): round-trip `DeviceState(bulbs=(BulbState("eb…02", True, "keyboard"),))` → `devices.bulbs` object → same value.
- **UT-035** (state): the GUI writing state drops ids missing from the inventory **only** when the inventory loaded successfully and `tuya_available()` is true; a missing, corrupt or unreadable inventory, or an absent extra, keeps every `devices.bulbs` entry.
- **UT-036** (happy): `state restore` with `devices.bulbs` present never calls `open_bulb` (spy) and prints no bulb line.
- **UT-037** (state): with `tuya_available()` `False`, `AppFacade` loads and rewrites `state.json` keeping `devices.bulbs` unchanged.
- **UT-038** (error): `follow: "music"` → `ValueError` `bulbs.eb….follow must be one of none, keyboard, screen, led_bar, got 'music'`.
- **UT-039** (happy): a file without `bulbs` (written by the current release) loads with `bulbs == ()`.

### `BulbsBackend` (Spec: Core Interfaces; BR-4–BR-9)

- **UT-040** (happy): `connectBulb(id)` with a reachable `FakeBulb` → one `status()`, then `opDone` on the GUI thread, then `persistUpdate(id, {"remembered": True})`; the model row is `remembered`.
- **UT-041** (error): unreachable → no `persistUpdate`; `opFailed` text `Escritório is not reachable on the network. …`.
- **UT-042** (idempotency): `connectBulb` twice before the first completes → one status read, one `opDone`, one `persistUpdate`.
- **UT-043** (error): `KeyRejected` → `Escritório rejected the local key or protocol — re-import devices.json`.
- **UT-044** (happy): `disconnectBulb` → `persistUpdate(id, {"remembered": False})`; inventory unchanged.
- **UT-045** (happy): `removeBulb` → inventory record gone; `persistUpdate(id, {"remove": True})`.
- **UT-046** (state): `refresh()` on remembered bulbs → each `FakeBulb` journal contains only `status`.
- **UT-047** (state): before the first read, `bulb(id)` returns the full `_spec.md` snapshot with `stateKnown: False`, `brightness: 0`, `temperature: -1`, `rgb: []`, `unavailableReason: ""`.
- **UT-048** (state): first read unreachable → the queued `opDone` sets `unavailableReason`; a later `refresh()` that succeeds clears it.
- **UT-049** (state): unreachable remembered bulb → after `opDone`, the row's `unavailableReason == "Sala is not reachable on the network"`.
- **UT-050** (happy): `retryBulb` after the bulb comes back → reason cleared, state known.
- **UT-051** (state): retry still unreachable → `AppState.busy` never set; reason unchanged.
- **UT-052** (happy): `setLightOn(id, True)` → journal `set_power(True)`; row `lightOn` is true only after the queued `opDone` (never optimistically).
- **UT-053** (error): `set_power` fails → `opDone` carries the failure; row `lightOn` equals the previous real value; `opFailed` names the bulb.
- **UT-054** (happy): with `windowVisible` true, the refresh timer interval is 30 000 ms and firing it calls `refresh()`.
- **UT-055** (happy): `setWindowVisible(False)` then `setWindowVisible(True)` triggers exactly one immediate `refresh()`.
- **UT-056** (state): `setWindowVisible(False)` with no bulb following → the timer is stopped and no reads happen.
- **UT-057** (state): `setWindowVisible` updates the `windowVisible` property, and `App.setWindowVisible` forwards to it; a repeated `True` does not refresh twice.

### `BulbWorker` (Spec: ADR-003; Safety Invariants 2, 8)

- **UT-060** (concurrency): bulb A's task blocks on an event; bulb B's task completes meanwhile.
- **UT-061** (ordering): 5 tasks for one bulb run in submission order.
- **UT-062** (state): bulb tasks run on threads named `bulb-*`, never `usb*`, and never emit `UsbWorker.opStarted`.
- **UT-063** (state): `opDone` emitted from a `bulb-*` thread reaches a slot that runs on the GUI thread (`QThread.currentThread()` is the app thread), and the row cache changes only there.
- **UT-064** (state): with `set_hold_open(id, True)`, two queued commands and a `push_colour` all use the same `FakeBulb` instance; a `FakeBulb` that rejects a second concurrent connection is never asked for one.

### Privacy (Spec: BR-3; Safety Invariant 1)

- **UT-071** (state): with a sentinel key `KEY-SENTINEL-123`, the outputs of `bulb list/status/import --json` and human, `state show`, every model role, `bulb(id)` maps, and `caplog` at DEBUG during connect/fail/refresh never contain the sentinel. In the same case the test forces `logging.getLogger("tinytuya")` to DEBUG and asserts the adapter's pin restores WARNING, and a spy proves `tinytuya.set_debug()` is never called.
- **UT-072** (state): `str()`/`repr()` of `BulbRecord` and `TuyaBulb` do not contain the key.
- **UT-073** (error): a tinytuya error dict carrying a payload → the surfaced message is `<name>: <ExceptionType>: <message>` without payload or key.

### Follow (slice 2) (Spec: BR-12–BR-16; ADR-002, ADR-004)

- **UT-080** (ordering): `removeBulb` on a following bulb → follower stopped and socket closed before the inventory write.
- **UT-081** (happy): `_ColourTap.set_color((0, 0, 255))` on success → `colorsSent(0, 0, 255)`; a raising driver → no signal.
- **UT-082** (happy): `_ColourTap.set_key_colors({(0,0): (255,0,0), (0,1): (0,0,255)})` → `colorsSent(128, 0, 128)`.
- **UT-083** (boundary): 20 source colours within 1 s on a following bulb → at most 4 `push_colour` calls; the last call carries the last colour.
- **UT-084** (state): `set_effect(...)` through the tap → no `colorsSent`.
- **UT-085** (state): keyboard `setLightOn(False)` → no colour event; the bulb receives nothing.
- **UT-086** (boundary): source changes of 7 then 8 in one channel → only the second pushes.
- **UT-087** (state): `availableFollowSources(id)` lacks `screen` without the `screen` extra, lacks `led_bar` when the LED bar is not connected, and lacks `keyboard` when the keyboard is not connected (`_uiux.md` S6).
- **UT-088** (happy): LED bar `persistUpdate` with palette red+blue → a following bulb receives `(128, 0, 128)` once.
- **UT-089** (state): LED bar light off → no push.
- **UT-090** (happy): `ScreenFrameHub.subscribe(a)` starts the fake frame source once; `subscribe(b)` does not start another.
- **UT-091** (happy): `unsubscribe(a)` keeps capture running for `b`; `unsubscribe(b)` sets the stop event.
- **UT-092** (happy): a frame of solid green → a bulb following the screen pushes `(0, 255, 0)`.
- **UT-093** (error): the frame source reports "cancelled" → follow set to `none`, `persistUpdate(id, {"follow": "none"})`, message `Screen capture cancelled — Escritório no longer follows the screen.`
- **UT-094** (error): the frame source ends (window closed) → all screen followers set to `none`, message `Screen capture ended — bulbs following the screen were set to None.`
- **UT-095** (state): last known power off → source changes produce no `push_colour`.
- **UT-096** (state): while following, the 5 s status read returns `on=False` → subsequent source changes produce no push.
- **UT-101** (state): a following bulb whose power has never been read (`stateKnown == False`) receives no `push_colour` until the first successful status read reports `on=True` (BR-12).
- **UT-097** (state): `disconnectBulb` on a following bulb → socket closed, `follow` kept in state; `connectBulb` → follower active again.
- **UT-098** (error): `push_colour` raises `BulbUnreachable` → bulb unavailable, `hold_open(False)` called, no more pushes until Retry.
- **UT-099** (state, characterisation — write before the refactor): keyboard follow-screen fed a fixed 2-frame sequence → `FakeKeyboard` journal shows `enable_user_mode` once, then two `set_key_colors` with the maps from `build_key_color_map_from_pil_rgb`.
- **UT-100** (state, characterisation): `stopFollowOrAnimation()` during follow-screen → no further `set_key_colors` after the stop returns and drains.

## Integration Tests

### Facade + bulbs backend + worker + store (real wiring, `FakeBulb` factory, `XDG_CONFIG_HOME=tmp_path`)

- **IT-001**: import a fixture file, `connectBulb(Escritório)` → `state.json` has `devices.bulbs.<id>.remembered == true` and `AppFacade` emits `deviceMemoryChanged`.
- **IT-002**: then `disconnectBulb` → `remembered == false`; inventory still has the key.
- **IT-003**: then `removeBulb` → inventory without the record; `state.json` without the id.
- **IT-004**: new `AppFacade` on the same files, `restoreRememberedDevices()` → keyboard/LED bar restored as before, then bulbs read; the bulb journal shows only `status`.
- **IT-005**: with Escritório connected, re-import with a new key → the next `setLightOn` uses a `FakeBulb` opened with the new key.
- **IT-006**: the full flow IT-001–IT-003 at DEBUG logging → no record contains the fixture keys.
- **IT-015**: Escritório follows `keyboard` (persistent `FakeBulb`), then `setLightOn(true)` through the backend → the same `FakeBulb` instance receives `set_power(True)` and the follower's next push; its open count stays 1 (Safety Invariant 9).

### Follow (slice 2)

- **IT-010**: Escritório follows `keyboard`; `KeyboardBackend.setSolidRgb(0, 0, 255)` through `FakeKeyboard` → within one follower tick the bulb journal has `push_colour((0, 0, 255))`.
- **IT-011**: keyboard follow-screen and bulb follow `screen` on a fake frame source → one source instance; both sinks receive frames; stopping the keyboard keeps the bulb receiving.
- **IT-012**: LED bar `applyPalette` red+blue → a following bulb gets `(128, 0, 128)`.
- **IT-013**: follow `keyboard` saved, new `AppFacade` → after the first successful read the follower is active (journal shows `hold_open(True)`), and no push happens until a keyboard colour event.
- **IT-014**: the CLI `keyboard follow-screen` over `iter_screen_frames` with a fake source → the same `set_key_colors` sequence as UT-099.

## End-to-End Tests

### CLI journeys — `_dx.md` transcripts through `main(argv)`, fake `open_bulb`, real files in `tmp_path`

- **E2E-001**: `bulb import <fixture>` → output and exit 0 exactly as the Golden Path (3 × `added`, `Imported 3 bulbs into …`).
- **E2E-002**: re-import with Sala's key changed and a plug entry → `unchanged`, `updated (key changed)`, `skipped: not a bulb (category cz)`; `--json` matches the `_dx.md` shape.
- **E2E-003**: import of a non-list file → `error: not a tinytuya devices.json (expected a list of devices): <path>`, exit 1.
- **E2E-004**: import of a list with no bulbs → `No bulbs found in <path>`, exit 1.
- **E2E-005**: `bulb status` with Sala offline → the three `_dx.md` lines, exit 1; `bulb status escritorio --json` → the `_dx.md` JSON.
- **E2E-006**: `bulb white --temp 20 all` with Sala offline → the `_dx.md` transcript, exit 1.
- **E2E-007**: `bulb color 255 136 0 Escritório` → `Escritório   colour #ff8800`, exit 0; `bulb off sala` → `Sala         off`.
- **E2E-008**: `bulb bright 0 sala` and `bulb bright 150 sala` → argparse usage, exit 2.
- **E2E-009**: `bulb on cozinha` → `error: no bulb named 'cozinha'. Known: Quarto, Escritório, Sala`, exit 2.
- **E2E-010**: no inventory: `bulb list` → the import hint, exit 0; `bulb on sala` → the same hint, exit 1.
- **E2E-011**: `bulb list` and `bulb list --json` → the `_dx.md` output, `key: set` / `"key": "set"`, no fixture key in stdout; with all three bulbs offline the command still returns in under 11 s (one 10 s deadline, not 3 × 10 s; raised from 6 s by QA defect D-2).
- **E2E-012**: `bulb remove sala` → `Removed Sala (eb1a2b3c4d5e6f70819203) from <path>`, exit 0; `bulb remove all` → usage, exit 2.
- **E2E-013**: `state show` with `devices.bulbs` → the two `bulb` lines from `_dx.md`; `--json` contains `devices.bulbs` verbatim.
- **E2E-014**: `tuya_available()` false → every `bulb` verb prints `error: bulb control needs the optional 'tuya' extra: uv sync --extra tuya`, exit 1; `bulb -h` still lists the verbs.
- **E2E-015**: `bulb status` with all three bulbs online → the three state lines, exit 0 (US-011.AC-1).
- **E2E-016**: `state show` with a corrupt inventory → keyboard/LED bar lines print, each bulb line is `<id>  (inventory unreadable)`, the inventory error prints and exit is 3; with the inventory missing, bulb lines show `(not imported)` and exit is 0.

### GUI journeys — offscreen `main.qml` via `tests/gui_helpers.py`, `FakeBulb` factory, `XDG_CONFIG_HOME=tmp_path`

- **E2E-020**: extra present, empty inventory → `bulbListPanel` shows `bulbImportButton` and the hint. Calling `App.bulbs.importFile(QUrl.fromLocalFile(<fixture>))` → 3 `bulbRow_*` rows and the summary "Imported 3 bulbs"; the same slot given a `file://` URL imports correctly (M4).
- **E2E-021**: Connect on Escritório's row → a `sidebarBulbEntry` titled "Escritório" appears with `bulbLightSwitch` enabled; the entry opens `bulbPage` at index 5 with the `FakeBulb` status (mode chip "White", `bulbBrightnessRow` 100), and selecting it keeps `primaryList.currentIndex` on that entry (not −1).
- **E2E-022**: Remove on Sala → `bulbRemoveDialog` opens; Cancel → row stays; Remove → row gone.
- **E2E-023**: on Escritório's page (index 5), Disconnect from Devices → `deviceContentStack.currentIndex == 0`; repeat starting from the page and Remove → also index 0.
- **E2E-024**: remembered bulb unreachable at start → sidebar subtitle "Unavailable", switch disabled, and `unavailableReasonForPage()` returns the reason for page 5; page shows `DeviceUnavailablePanel` with the reason; before the first read, the page shows "Reading…".
- **E2E-025**: toggle `bulbLightSwitch` → `FakeBulb` journal `set_power(True)`; the page switch follows.
- **E2E-026**: `tuya_available()` false → no `bulbListPanel`, sidebar entries identical to today's (`test_gui_shell` expectations).
- **E2E-027** (slice 2): `bulbFollowCombo` model without `screen` (no extra), without `led_bar` (LED bar not connected) and without `keyboard` (keyboard not connected); selecting Keyboard shows the "Following the keyboard. Other apps on your network can't control this bulb locally while it follows." message.
- **E2E-028**: dragging `bulbBrightnessRow` through five values within 200 ms → one `setBrightness` call after the pause, with the last value (US-007.EC-1).

## Manual hardware checklist (not automated; needs the user's go-ahead — it changes real house lights)

- **M-1**: `bulb status` on the real bulbs matches the Smart Life app.
- **M-2**: GUI Connect Escritório; quit; reopen at login (autostart) → the bulb is unchanged (stays off if off).
- **M-3**: brightness slider drag → smooth, no command flood; temperature and colour apply.
- **M-4**: switch the bulb off at the wall → "Unavailable" within 30 s; back on → normal after Retry/refresh.
- **M-5** (slice 2, OQ-1): with Escritório **off**, send one `push_colour` → record whether the bulb turns on. If it does, keep BR-12's gating as the only guard and note it in the docs.
- **M-6** (slice 2): Follow Keyboard with an animation → the bulb tracks it with no visible lag above ~250 ms and no flicker.
- **M-7** (slice 2): Follow Screen on Wayland with the keyboard also following → one portal picker only; X11 session too, if available.
