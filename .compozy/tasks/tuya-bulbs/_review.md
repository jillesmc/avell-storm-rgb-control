# Independent Review: Tuya smart bulbs spec

Reviewer: a different model than the one that authored the package (open model routed by the user).
Scope: `_spec.md`, `_user_stories.md`, `_dx.md`, `_uiux.md`, `_tests.md`, `adrs/adr-001..004`.
Method: every technical claim was checked against the working tree, the installed `tinytuya` 1.20.0
(`~/git/iot/.venv`), and the real `devices.json` (structure only, no secrets printed).

## Verdict

**Product part: solid.** Decisions, stories, edge cases and ADRs are coherent, and the coverage
matrix is complete (18/18 stories have rows; all 110 cited test ids are defined).

**Technical part: not ready for task breakdown yet.** Four contract gaps would each force an
implementer to invent behaviour, and two of them (single connection, sidebar wiring) would fail on
real hardware or in the GUI. Fix B1–B4 and M1–M6 in the spec first; the rest can be fixed as the
tasks are written.

## What holds up (verified, not assumed)

| Claim | Evidence |
|-------|----------|
| tinytuya returns errors as dicts, never raises for device errors | `core/XenonDevice.py:1069-1087` returns `_send_receive`; `error_json(...)` on failure |
| 914 = key **or version**, 905 = unreachable, 902 = timeout, 901 = connect | `core/error_helper.py:11-24` |
| `set_colour`/`set_white` add `switch: True` → KD-6 is right | `BulbDevice.py:549-555`, `:645-651` |
| Type-B DPS are 20/21/22/23/24 with 10–1000 | `BulbDevice.py:95-108` |
| A real `devices.json` has 3 `dj` entries; 1 has `version: "3.3"`, 2 have `version: ""` | inspected locally; the "default 3.3" rule is necessary, not cosmetic |
| `state_from_dict` ignores unknown `devices.*` keys, and `state_to_dict` rewrites only known ones | `application/device_state.py:235-303` |
| CLI already uses exit 3 for an unreadable state file; argparse gives 2 | `adapters/cli/main.py:297-322`, `:409-415` |
| Fake/testing infrastructure named in `_tests.md` exists | `tests/backend_fakes.py` (`drain`, `FakeKeyboard`, `FakeLedBar`), `tests/gui_helpers.py`, `tests/conftest.py:10` |
| Palette writes are not a visible-colour path | `set_palette_color` only feeds firmware effects; the tap's four paths are the right ones |
| Docs sync list matches the repo table | `docs/README.md:79-88` |

## Blocking

### B1. There is no channel for per-bulb results

`_spec.md` defines `BulbWorker.opFailed = Signal(str)` and, on the backend, only `modelChanged`,
`bulbEpochChanged`, `importSummaryChanged` and `persistUpdate` (`_spec.md:233-254`). But UT-048,
UT-049, UT-052 and UT-053 require per-row `unavailableReason`, `stateKnown` and `lightOn` to change
after a worker task. The worker must not mutate a `QAbstractListModel` off the GUI thread, and a
bare error string cannot identify the row.

Add, explicitly:

```python
class BulbWorker(QObject):
    opDone = Signal(str, object)   # (bulb_id, BulbStatus | BulbFailure); queued to the GUI thread
    opFailed = Signal(str)         # user-facing text only
```

and state that `BulbsBackend` is the single place that applies `opDone` to its row cache, bumps
`bulbEpoch` and emits `modelChanged`. Without this, UT-048/049/052/053 cannot be implemented as written.

### B2. The driver port cannot express BR-11 or `bulb white` without `--temp`

- `set_brightness(percent)` must keep hue/saturation in colour mode (BR-11, UT-021), but a fresh
  connection has no status, and the port carries no colour.
- `set_white(temperature_percent: int)` cannot mean "keep the current temperature", which
  `_dx.md:148` promises for `bulb white` with no `--temp`.

Choose one and write it down: pass a `BulbStatus` snapshot to the command (`set_brightness(percent,
rgb)`, `set_white(temperature_percent | None)`), or make the driver read status first and budget the
extra round trip. Today the spec implies both "one command per connection" and "no extra reads",
which cannot hold for these two verbs.

### B3. Following and per-command connections collide on real bulbs

BR/safety say a bulb usually accepts one local connection, and the GUI controls "keep working while
following" (`_spec.md:48`). The design opens a connection per command and keeps one persistent socket
only while following (`_spec.md:309`), but never says commands must **reuse** that socket. If
`setLightOn` opens a second driver for a following bulb, it fails on hardware.

Define a per-bulb session: while `hold_open(True)`, every command for that bulb goes through the same
`BulbDriver` on the same queue; `close()` is the only release, called on follow→none, disconnect,
forget, remove, unavailable and shutdown. Add a `FakeBulb` test that rejects a second concurrent
connection, so this cannot regress.

### B4. The sidebar and page stack are hardcoded to pages 0–4 and to keyboard/LED bar

Adding `page: 5` breaks five places in `src/app/ui/main.qml`, none of them mentioned in `_uiux.md` S4:

| Location | Today | Consequence for a bulb |
|----------|-------|------------------------|
| `Switch` objectName | `page === 1 ? "keyboardLightSwitch" : "ledBarLightSwitch"` | bulb entry is named `ledBarLightSwitch` |
| `Switch.checked` / `enabled` | two-way ternaries on page 1 vs else | bulb shows the LED bar state, not its own |
| `Switch.onToggled` | `if page === 1 … else if page === 2` | bulb switch does nothing |
| `unavailableReasonForPage()` | returns `""` unless page 1/2 (`main.qml:115-121`, bound at `:282`) | no "Unavailable" subtitle → US-005.AC-1 fails |
| `syncPrimarySidebarListIndex()` | only `primarySection <= 2` (`:60-70`) | selecting a bulb page sets `currentIndex = -1` |
| forgot-device reset | only pages 1 and 2 (`:107-110`) | disconnect/remove while on the bulb page leaves a stale page → US-003.AC-3 fails |

`_uiux.md` says "as with USB devices at `main.qml:106-110`", which points at the hardcoded check it
needs to generalise. Enumerate all six edits, and make the switch model-driven (`model.bulbId`,
`model.lightOn`, `model.available`) instead of page-driven. E2E-024 and E2E-023 depend on this.

## Major

### M1. The list model roles and the `bulb(id)` map keys are undefined

`_uiux.md` and `_tests.md` already use `title`, `subtitle`, `bulbId`, `remembered`, `lightOn`,
`stateKnown`, `unavailableReason`; `_spec.md` only says "list model". Add a role table and the
snapshot keys. UT-047/049/052 and E2E-021/024/025 are written against names the spec never fixes.

### M2. tinytuya returns error dicts; 914 is not "key rejected"

Every device method returns `{"Err": ..., "Error": ..., "Payload": ...}` instead of raising. The
adapter must inspect every return value (`status`, `set_power`, `set_brightness`, `set_white`,
`set_colour`, `push_colour`), raise the mapped exception, and **drop `Payload`** before it reaches
`_dx.md` error text. Also, 914 is "check device key **or version**" (`core/error_helper.py:24`), and
two of the three real bulbs import with `version: ""`. Either retry once with the version found by
discovery, or word the message as "local key or protocol rejected". Add a test for the version case.

### M3. tinytuya logs the local key in clear at DEBUG

`core/XenonDevice.py:1085` logs `self.local_key` when the status request fails. `_spec.md:372` pins
the logger to WARNING but does not forbid `tinytuya.set_debug()`, which calls `logging.basicConfig(level=DEBUG)`
and raises the package logger (`core/core.py:133-144`). State both rules: pin the parent `tinytuya`
logger immediately after the lazy import, and never call `set_debug`. UT-071 should force the
tinytuya logger to DEBUG during the test to prove the pin holds.

### M4. `importFile` receives a QUrl, not a path

`_uiux.md` S2 says `App.bulbs.importFile(selectedFile)` while the slot is `@Slot(str)`, and the
existing picker strips `file://` in QML (`KeyboardPage.qml:339-343`). Pick one: `@Slot(QUrl)` +
`toLocalFile()`, or pass the stripped path as the keyboard page does. As written, `Path("file:///…")`
fails.

### M5. "Drop ids missing from the inventory" can delete all bulb memory

`_spec.md:301` drops entries whose id is missing from the inventory on the next write, while
US-013.EC-2/UT-037 keep them when the `tuya` extra is absent. If the inventory is missing, corrupt or
unreadable, **every** id is "missing" and the next unrelated keyboard write erases `devices.bulbs`.
Restrict pruning to "extra available **and** inventory loaded successfully"; keep the entries
otherwise.

### M6. `bulb list` promises parallel reads with no design

`_dx.md:103` promises "in parallel, ≤ 6 s"; the core CLI is synchronous, a command timeout is 5 s and
discovery is 6 s. Three offline bulbs would take 15 s+. Either define a `ThreadPoolExecutor` with a
total deadline in `bulb_cli`, or drop the promise.

### M7. "Window visible" has no source

BR-8 and UT-054/055/056 depend on it, but nothing exposes it: `closeToTray` hides `appRoot.visible`
(`main.qml:52-56`) and `AppFacade` has no visibility property. Add `windowVisible` to `AppFacade`
(or `BulbsBackend`), bind it from QML, and test the transitions.

### M8. Brightness scaling assumes type B for every imported bulb

BR-10 hardcodes 1–100 % → 10–1000 (type B). A type-A `dj` bulb (DPS 1–8, 25–255) would import and be
mismapped. Either derive ranges from tinytuya's detected `dpset`, or restrict import to type B and
say so. Low risk today (all three bulbs are type B), but it is an unstated assumption.

## Minor

1. `_uiux.md` S1 says the row copy is "Remembered — control it from the sidebar." The real copy is
   "Remembered — configure it from the sidebar." (`DeviceListPanel.qml:152-154`).
2. Line drift: the unavailable subtitle is `main.qml:309-318` (not 300-318); `DevicesPage.qml` is
   23-48; `AppFacade._on_persist` (the single-writer path to extend) is at `:536` and is not cited.
3. `state show` needs the inventory for names; behaviour with a corrupt inventory is undefined (it is
   not a `bulb` verb, so the "exit 3" row does not clearly apply), and there is no test for
   `(not imported)`.
4. BR-2 requires `category == "dj"`. If the wizard omits `category`, every entry is skipped as
   "not a bulb (category None)". Decide: a distinct "missing category" reason, or accept when
   `mapping`/`model` is present.
5. BR-12 gates on "last known power is on"; add a test for **unknown** (pre-first-read) power → no push.
6. US-011.AC-1 (exit 0 when all bulbs answer) has no E2E case; E2E-005 only covers exit 1.
7. UT-087 does not assert that `keyboard` is absent when the keyboard is disconnected, though
   `_uiux.md` S6 hides the option.
8. US-007.EC-1 (debounce) is assigned to the manual checklist only; the offscreen harness can assert
   "one command per pause".
9. `set_last_ip` is a read-modify-write from the worker/CLI that can race with `import`/`remove`.
   Note it, or serialise inventory writes with a lock file.
10. `_dx.md` should say that an older build that rewrites `state.json` drops `devices.bulbs`
    (the spec says it, the DX contract does not).

## What to change before `cy-create-tasks`

1. Add `opDone(bulb_id, result)` and the GUI-thread application rule (B1).
2. Fix the driver port for brightness/white, and define the status source (B2).
3. Add the per-bulb session rule for following (B3).
4. Enumerate the six `main.qml` edits and make the sidebar switch model-driven (B4).
5. Add the model-role and `bulb(id)` snapshot tables (M1).
6. Add the tinytuya return-value/error-mapping rule, the 914 message, and the logger rule
   (M2, M3).
7. Fix `importFile`'s QUrl handling (M4).
8. Restrict state pruning (M5), define list concurrency (M6) and the visibility source (M7).

After that, the package is ready for task decomposition; nothing else found changes the product
decisions or the ADR set.

## Resolution (applied 2026-11-01)

All blocking and major items were applied to the package before task breakdown. The review is kept
as the audit trail; the spec files are the current contract.

| Item | Where it landed |
|------|-----------------|
| B1 `opDone` + GUI-thread rule | `_spec.md` Core Interfaces, Safety Invariant 2, `_tests.md` UT-048/049/052/053/063 |
| B2 `BulbStatus` for brightness/white | `_spec.md` `BulbDriver`, `_dx.md` control verbs, `_tests.md` UT-021/026/027 |
| B3 one driver per bulb | `_spec.md` Architectural Boundaries + Safety Invariant 9, ADR-003, `_tests.md` UT-064, IT-015 |
| B4 six `main.qml` edits | `_uiux.md` S4, `_spec.md` Impact Analysis, `_tests.md` E2E-021/023/024 |
| M1 model roles + snapshot | `_spec.md` Data Models, `_uiux.md` S4, `_tests.md` UT-047 |
| M2 error dicts + 914 | `_spec.md` Integration Points, `_dx.md` Errors, ADR-002, `_tests.md` UT-025/028 |
| M3 tinytuya logger pin | `_spec.md` Monitoring, ADR-001, `_tests.md` UT-071 |
| M4 `importFile` QUrl | `_spec.md` `BulbsBackend`, `_uiux.md` S2, `_tests.md` E2E-020 |
| M5 restricted pruning | `_spec.md` Data Models, `_tests.md` UT-035 |
| M6 `bulb list` deadline | `_dx.md` CLI, `_tests.md` E2E-011 |
| M7 window visibility | `_spec.md` QML surface, `_uiux.md` S5, `_tests.md` UT-054–057 |
| M8 detected ranges | `_spec.md` BR-10 + Assumptions |
| Minors 1–10 | `_uiux.md` S1/S4 refs, `_dx.md` `state show`/older builds, `_user_stories.md` US-001.EC-3/US-002.EC-3, `_tests.md` UT-071/087/101, E2E-015/016/028 |
