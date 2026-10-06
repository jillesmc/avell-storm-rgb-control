# Test Specification: Remembered devices and startup look

Canonical test contract for remembered devices and the startup look. It is a companion to `_spec.md`.
It derives from `_user_stories.md` (behaviour), `_spec.md` Part II (components), `_dx.md` (CLI journeys) and `_uiux.md` (GUI journeys).

## Strategy

- **Framework:** pytest. Existing patterns:
  - isolated `QSettings` fixture (`tests/test_app_facade_autoconnect.py:20-32`);
  - fake drivers (`tests/test_*_power_replay.py`);
  - offscreen QML (`tests/gui_helpers.py`).
- **Fakes only at the USB boundary:** `FakeKeyboard` / `FakeLedBar` implement `ports.protocols` and record calls. `device_facade.open_*` and `app.core.devices.enumerate_usb_devices` are monkeypatched.
- **State file:** `DeviceStateStore(tmp_path / "state.json")` or `XDG_CONFIG_HOME=tmp_path`.
- **Async GUI work:** wait for the real `UsbWorker` (`shutdown(wait=True)`, or a `QEventLoop` until a signal) and then process queued events.
- **Execution:** `make test` (`-m "not hardware"`). GUI cases skip without PySide6 / Kirigami, as today.
- **Hardware:** a manual checklist (no automated hardware tests).

## Coverage Matrix

| Source | Behavior | Unit | Integration | E2E |
|--------|----------|------|-------------|-----|
| US-001 | Connect remembers + sidebar entry | UT-030 | IT-001 | E2E-004 |
| US-001.EC-1 | Failed connect remembers nothing | UT-031 | — | — |
| US-001.EC-2 | Other device of same kind replaces | UT-032 | — | — |
| US-001.EC-3 | Double connect → one memory | UT-033 | — | — |
| US-002 | Reconnect at startup | — | IT-002 | E2E-004 |
| US-002.EC-1 | New bus/addr still found | UT-020 | IT-002 | — |
| US-002.EC-2 | Duplicate USB id → first | UT-021 | — | — |
| US-002.EC-3 | Absent → unavailable, no popup | — | IT-003 | — |
| US-003 | Disconnect forgets, keeps look | UT-034 | IT-004 | — |
| US-003.EC-1 | Disconnect stops animation first | UT-045 | — | — |
| US-003.EC-2 | View returns to Devices | — | — | E2E-005 |
| US-004 | Unavailable: retry / forget | UT-035, UT-036 | IT-003 | E2E-006 |
| US-004.EC-1 | Retry still absent | UT-037 | — | — |
| US-004.EC-2 | USB error reason shown | UT-038 | — | — |
| US-005 | Keyboard look auto-saved | UT-040–UT-044 | IT-005 | — |
| US-005.EC-1 | Failed apply not saved | UT-046 | — | — |
| US-005.EC-2 | Follow/test/freeze not saved | UT-047 | — | — |
| US-005.EC-3 | Debounced, last wins | existing debounce tests in `tests/test_keyboard_*` + UT-040 | — | — |
| US-005.EC-4 | Empty per-key grid saved | UT-043 | — | — |
| US-006 | LED bar look auto-saved | UT-050, UT-051 | IT-005 | — |
| US-006.EC-1 | Failed apply not saved | UT-052 | — | — |
| US-006.EC-2 | Palette capped at 9 | UT-053 | — | — |
| US-007 | Restore at startup | UT-010–UT-016 | IT-002, IT-006 | E2E-004 |
| US-007.EC-1 | Missing animation | UT-015 | IT-007 | — |
| US-007.EC-2 | Step failure doesn't stop others | — | IT-008 | — |
| US-007.EC-3 | User change after restore wins | — | IT-009 | — |
| US-007.EC-4 | `save` flag restored as-is | UT-010 | — | — |
| US-008 | Light switch | UT-060–UT-063 | IT-010 | E2E-005 |
| US-008.AC-3 | No footer power buttons | — | — | E2E-007 |
| US-008.EC-1 | Off stops animation first | UT-064 | — | — |
| US-008.EC-2 | On without saved look | UT-065, UT-066 | — | — |
| US-008.EC-3 | Disabled when unavailable | — | — | E2E-006 |
| US-008.EC-4 | Rapid toggles, last wins | UT-067 | — | — |
| US-009 | `state show` | UT-070 | — | E2E-001 |
| US-009.EC-1 / EC-2 | No file / invalid file | UT-071, UT-072 | — | E2E-003 |
| US-010 | `state restore` | UT-073–UT-075 | — | E2E-002 |
| US-010.EC-1 | Remembered device missing | UT-076 | — | E2E-003 |
| US-010.EC-2 | Forgotten device skipped | UT-077 | — | — |
| US-010.EC-3 | No state file | UT-078 | — | E2E-003 |
| US-010.EC-4 | Invalid state file | UT-079 | — | E2E-003 |
| US-010.EC-5 | Missing animation file | UT-080 | — | — |
| US-010.EC-6 | GUI + CLI concurrently | no automated test: documented behaviour; USB arbitration is outside the app | — | — |
| US-011 | Migration from auto-connect | UT-090, UT-091 | IT-011 | — |
| US-011.EC-1 | No devices at first start | UT-092 | — | — |
| US-011.EC-2 | State file already exists | UT-093 | — | — |
| US-012 | Unreadable state file | UT-002, UT-004, UT-005 | IT-012 | — |
| US-012.EC-1 | Newer schema version | UT-003 | — | — |
| US-012.EC-2 | Unwritable config dir | UT-006 | — | — |
| `DeviceStateStore` | Load/save/atomic/quarantine | UT-001–UT-007 | — | — |
| Safety invariant 8 | `device_state` is Qt-free | UT-008 | — | — |

## Unit Tests

### `device_state` — model and store (Spec: Data Models, KD-2)

- **UT-001** (happy): `DeviceStateStore(p).save(state)` then `load()` with a keyboard `FirmwareEffectLook(effect="wave", speed=5, brightness=40, color="random", direction="up", reactive=False, save=False)` and an LED bar `LedBarLook(palette=((255,0,0),), effect="static", brightness=50, speed=3)` → returns an equal `DeviceState`.
- **UT-002** (error): `load()` on a file containing `{` → raises `StateFileError` whose `reason` starts with `invalid JSON`.
- **UT-003** (error): `load()` with `"version": 2` → `StateFileError(reason="unsupported version 2")`.
- **UT-004** (boundary): `load()` with `keyboard.look.speed = 11` → `StateFileError` whose reason contains `keyboard.look.speed must be 0–10, got 11`; with `speed = 10` → loads.
- **UT-005** (happy): `quarantine()` renames `state.json` to `state.json.invalid`, replacing an existing `.invalid`, and returns the new path. `exists()` is then False.
- **UT-006** (error): `save()` into a read-only directory → raises `OSError`; the previous `state.json` content is unchanged.
- **UT-007** (state): `save()` writes through a temp file in the same directory and `os.replace`. Patch `os.replace` to raise → the original file is intact and no temp file is left.
- **UT-008** (boundary): importing `avell_storm_rgb.application.device_state` in a subprocess with `PySide6` blocked (`sys.modules["PySide6"] = None`) succeeds.
- **UT-009** (happy): `load()` on a missing file → `DeviceState(keyboard=None, led_bar=None)`; no file is created.

### `device_state` — restore functions (Spec: Core Interfaces)

- **UT-010** (happy): `restore_keyboard(fake, KeyboardState(usb_id="048d:ce00", palette={1:(255,0,0)}, brightness=40, look=FirmwareEffectLook(... save=True)))` → calls, in order, `set_palette_color(1,(255,0,0))`, `set_brightness(40)`, `set_effect(KEYBOARD_EFFECTS["wave"](speed=5, brightness=40, direction=3, save=1))`.
- **UT-011** (happy): `SolidLook((255,255,255))` → `set_color((255,255,255), None, False)`.
- **UT-012** (happy): `PerKeyLook(((5,0,(255,0,0)),))` → `set_key_colors({(5,0):(255,0,0)})`, with no row flip.
- **UT-013** (state): `power="off"` with any look → only palette, brightness and `turn_off()`; the look is not sent.
- **UT-014** (happy): `AnimationLook(path=<existing file>, loops=1, forever=True)` → `RestorePlan.pending_animation` equals the look; no animation calls are made on the driver.
- **UT-015** (error): an `AnimationLook` whose path does not exist → `pending_animation is None`; `warnings == ("animation file not found: <path>",)`; the power state is still applied.
- **UT-016** (happy): `restore_led_bar(fake, LedBarState(look=LedBarLook(((255,0,0),(0,0,255)),"wave",75,5)))` → `set_palette_colors([...])`, `set_brightness_level(75)`, `set_motion_speed(5)`, `apply_visual_effect("wave")`. With `power="off"` → `power_off()` only.
- **UT-017** (happy): `describe_look(FirmwareEffectLook("wave",5,40,"random","up",False,False))` → `"firmware effect wave (speed 5, brightness 40, direction up)"`. `LedBarLook` with 4 colours → `"breathing · 4 colours · brightness 75 · speed 3"`.

### `device_facade` — open by USB id (Spec: Core Interfaces)

- **UT-020** (happy): fake `usb.core.find` returns a keyboard `048d:ce00` at bus 3 addr 9 → `open_keyboard(usb_id="048d:ce00")` opens bus 3 addr 9.
- **UT-021** (boundary): two LED bars `048d:7001` → `open_led_bar(usb_id="048d:7001")` returns the first in scan order.
- **UT-022** (error): no matching device → `open_keyboard(usb_id="048d:6004")` raises `FileNotFoundError("no suitable device found")`; `open_led_bar(usb_id=…)` raises `RuntimeError("No ITE 8233 LED bar found.")`.

### `AppFacade` — device memory (Spec: Core Interfaces, BR-1–BR-3, BR-9)

- **UT-030** (happy): `connectDevice("keyboard", 3, 9)` with a fake opener for `048d:ce00` → after the worker drains, `keyboardRemembered is True` and `state.json` has `keyboard.usb_id == "048d:ce00"` and `remembered: true`.
- **UT-031** (error): the opener raises `USBError(13, "Access denied")` → `keyboardRemembered is False`, `state.json` is not created, and `App.state.lastError` contains `Access denied`.
- **UT-032** (state): a keyboard `048d:ce00` is remembered with a solid look; connecting `048d:6004` → `usb_id == "048d:6004"` and the look is unchanged.
- **UT-033** (idempotency): `connectDevice` twice for the same device → one `persistUpdate` remembering it; `deviceMemoryChanged` leaves one entry.
- **UT-034** (state): `disconnectDeviceKind("led_bar")` → `ledBarRemembered is False`; `state.json` keeps `led_bar.look` and `power`, with `remembered: false`.
- **UT-035** (happy): a remembered keyboard absent at `restoreRememberedDevices()` → `keyboardUnavailableReason == "Not found (048d:ce00)"`, `keyboard.connected is False`.
- **UT-036** (happy): `forgetDevice("keyboard")` on an unavailable keyboard → `keyboardRemembered is False`; the look is kept in the file.
- **UT-037** (state): `retryDevice("keyboard")` with the device still absent → the reason is unchanged and `lastError` is unchanged.
- **UT-038** (error): the opener raises `USBError(13, "Access denied")` at restore → the reason is `"USBError: [Errno 13] Access denied"`.

### Backends — persist (Spec: KD-3, KD-5, BR-4, BR-5)

- **UT-040** (happy): `KeyboardBackend.applyEffect("wave",5,40,"random","up",False,False)` → one `persistUpdate` with `{"look": FirmwareEffectLook(...), "power": "on"}` after `set_effect` succeeds.
- **UT-041** (happy): `setSolidRgb(255,255,255)` → `persistUpdate` look `SolidLook((255,255,255))`.
- **UT-042** (happy): `setKeyById("esc",255,0,0,False)` then `applyKeyGrid(True)` → `PerKeyLook` cells `((5,0,(255,0,0)),)` (UI row 0 → device row 5).
- **UT-043** (boundary): `applyKeyGrid(True)` with an empty grid → `PerKeyLook(())`.
- **UT-044** (happy): `playAnimationFile(path, 3, False)` → `persistUpdate` with `AnimationLook(abs(path), 3, False)`, emitted once playback has started.
- **UT-045** (ordering): `disconnectDevice()` while `playAnimationFile(..., forever=True)` runs → `_follow_stop` is set before the disconnect task is submitted.
- **UT-046** (error): the fake `set_effect` raises → no `persistUpdate`.
- **UT-047** (state): `startFollowScreen`, `demoTestPattern` and `freezeAnimation` → no `persistUpdate` with a `look` key.
- **UT-048** (happy): `setPaletteSlotRgb(3,1,2,3)` → `persistUpdate {"palette": {3: (1,2,3)}}`. `paletteRestore()` → all 7 default slots.
- **UT-049** (happy): the brightness slider flush with value 30 while the look is a firmware effect → `persistUpdate {"brightness": 30, "look": FirmwareEffectLook(... brightness=30)}`.
- **UT-050** (happy): `LedBarBackend.applyPalette("fire","wave")` → `persistUpdate` look `LedBarLook(<fire colours>, "wave", <driver.brightness>, <driver.speed>)`.
- **UT-051** (happy): `requestBrightnessFromUi(80,"static")` flush → the saved look's `brightness == 80`.
- **UT-052** (error): the fake `apply_visual_effect` raises → no `persistUpdate`.
- **UT-053** (boundary): `applyPalette` with 11 colours → the saved palette has 9 entries.

### Backends — light (Spec: BR-6–BR-8, BR-11)

- **UT-060** (happy): `KeyboardBackend.setLightOn(False)` → `turn_off()`; `lightOn` becomes False; `persistUpdate {"power": "off"}`.
- **UT-061** (happy): `setLightOn(True)` with a saved `SolidLook` → `set_color(...)`; `persistUpdate {"power": "on"}`.
- **UT-062** (happy): `LedBarBackend.setLightOn(False)` / `(True)` with a saved look → `power_off()` / `power_on()` and then the look via `restore_led_bar`.
- **UT-063** (state): light off, then `applyEffect(...)` → `lightOn` becomes True and `persistUpdate` includes `"power": "on"`.
- **UT-064** (ordering): `setLightOn(False)` while a forever animation runs → `_follow_stop` is set before `turn_off` is queued; `turn_off` is called after the animation task returns.
- **UT-065** (state): keyboard `setLightOn(True)` with no saved look and a session snapshot `[3,5,25,0,1,0]` → `set_effect([3,5,25,0,1,0])`.
- **UT-066** (state): keyboard `setLightOn(True)` with no look and no snapshot → `set_effect(KEYBOARD_EFFECTS["rainbow"]())`.
- **UT-067** (concurrency): `setLightOn(False)`, `(True)`, `(False)` in quick succession → driver calls in that order; final `lightOn is False`; the last `persistUpdate` is `{"power": "off"}`.

### CLI `state` (Spec: Agent Manageability; `_dx.md` CLI)

- **UT-070** (happy): `main(["state","show"])` with the `_dx.md` example file → stdout equals the golden-path block; exit 0.
- **UT-071** (boundary): `main(["state","show"])` with no file → `No saved state at <path>`; exit 0. `--json` → `{"path": …, "version": 1, "devices": {}}`.
- **UT-072** (error): an invalid file → stderr `error: saved state is unreadable (invalid JSON at line 1 column 2): <path>`; exit 3; the file is unchanged.
- **UT-073** (happy): `main(["state","restore"])` with fake drivers → LED bar calls happen before keyboard calls; exit 0; the file bytes are unchanged.
- **UT-074** (happy): `--kind keyboard` → no LED bar opener call.
- **UT-075** (happy): a forever `AnimationLook` with `--no-animation` → the line ends `(animation skipped)`; no animation run; exit 0.
- **UT-076** (error): the LED bar opener raises `RuntimeError("No ITE 8233 LED bar found.")` → line `led-bar   048d:7001  skipped: device not found`; the keyboard is still restored; exit 1.
- **UT-077** (state): `led_bar.remembered = false` → no LED bar line and no opener call; exit 0.
- **UT-078** (boundary): no file → `Nothing to restore: no saved state at <path>`; exit 0.
- **UT-079** (error): an invalid file → exit 3; no opener called.
- **UT-080** (error): the animation path is missing → `restored: light on (warning: animation file not found: <path>)`; exit 1.

### Migration (Spec: BR-14)

- **UT-090** (happy): no state file, legacy key absent, fake scan with keyboard + LED bar → both remembered, `power: "on"`, `look: null`; the legacy key is removed.
- **UT-091** (happy): legacy key `false` → nothing remembered; the key is removed; `state.json` is written with an empty `devices` (so the migration never re-runs).
- **UT-092** (boundary): no devices present → empty `devices` written; the key is removed.
- **UT-093** (state): a state file already exists, legacy key `true` → no migration; the key is removed.

## Integration Tests

### Facade + backends + worker + store (real wiring, fake USB)

- **IT-001**: `AppFacade` with an empty store; `connectDevice("keyboard", 3, 9)`; drain the worker → `state.json` keyboard remembered; `keyboardRemembered` emitted.
- **IT-002**: the store has a keyboard (`FirmwareEffectLook`, power on) and an LED bar (`LedBarLook`, power on); the fake scan puts them on new bus/addr; `restoreRememberedDevices()` → both connected; recorded driver call order: all LED bar calls, then keyboard palette → brightness → effect.
- **IT-003**: the store has a remembered LED bar; the scan has none → `ledBarUnavailableReason == "Not found (048d:7001)"`; no `lastError`. Add the device to the fake scan, then `retryDevice("led_bar")` → connected and look restored.
- **IT-004**: connect the LED bar, apply an effect, `disconnectDeviceKind("led_bar")`, recreate `AppFacade`, `restoreRememberedDevices()` → the LED bar is not connected; `connectDevice` again → the saved look is applied.
- **IT-005**: apply a keyboard solid colour and an LED bar preset → a new `DeviceStateStore(path).load()` from another instance returns those looks (simulates restart).
- **IT-006**: the store has a keyboard `AnimationLook(forever=True)` and an LED bar look; restore → LED bar calls are complete before the animation task starts; then `setLightOn(False)` on the keyboard → the animation stops and `turn_off` is called.
- **IT-007**: the store has a keyboard `AnimationLook` with a missing path, power on → `lastError` is `Keyboard: saved animation file not found: <path>. Light state restored; look not applied.`; the file still holds the animation look.
- **IT-008**: the fake LED bar `apply_visual_effect` raises during restore → `lastError` is set; the keyboard is still restored.
- **IT-009**: during restore, call `applyEffect("breathing", …)` before the worker drains → the final saved look is `breathing`; the final driver call is the breathing effect.
- **IT-010**: `setLightOn(False)`, then recreate the facade and restore → `turn_off` is called; the look is not sent; `lightOn is False`.
- **IT-011**: migration end to end: isolated `QSettings` with `ui/autoConnectOnStartup=true`, no state file, fake scan with both devices → after `restoreRememberedDevices()`, both connected and remembered; `QSettings` no longer has the key.
- **IT-012**: `state.json` contains `not json` → after facade init, `state.json.invalid` exists, nothing is remembered, and `lastError` starts with `Saved device state was unreadable`. Connecting a device writes a fresh valid `state.json`.

## End-to-End Tests

### CLI journeys (US-009, US-010) — `_dx.md` transcripts through `main(argv)`, fake USB openers, real state file

- **E2E-001**: write the `_dx.md` example `state.json` → `avell-storm-rgb state show` → output matches the golden-path block; `state show --json` parses back to the same document plus `path`.
- **E2E-002**: same file, fakes for both devices → `avell-storm-rgb state restore` → the two `restored:` lines from the golden path; exit 0; `state.json` bytes are unchanged.
- **E2E-003**: three runs. (a) no file → `state restore` prints `Nothing to restore…`, exit 0. (b) invalid file → exit 3. (c) LED bar absent → `skipped: device not found`, exit 1.

### GUI journeys (US-001–US-004, US-008) — offscreen `main.qml` via `tests/gui_helpers.py`, fake USB, `XDG_CONFIG_HOME=tmp_path`

- **E2E-004**: empty config, fake scan with a keyboard. Load the GUI → no `sidebarKeyboardEntry`. Call `App.connectDevice("keyboard", …)` → `sidebarKeyboardEntry` appears. Reload the engine with a fresh facade → `sidebarKeyboardEntry` is present and `App.keyboard.connected` is true without any call.
- **E2E-005**: a remembered, connected keyboard. Toggle `keyboardLightSwitch` off → the fake recorded `turn_off`. Disconnect via `App.disconnectDeviceKind("keyboard")` while the keyboard page is current → the entry disappears and `deviceContentStack.currentIndex == 0`.
- **E2E-006**: a remembered LED bar absent from the scan → `sidebarLedBarEntry` is present; `ledBarLightSwitch.enabled == false`; the LED bar page shows `ledBarUnavailable` with the text `Not found (048d:7001)`.
- **E2E-007**: the loaded GUI has no child with text `Power off` / `Power on` under `keyboardPage` / `ledBarPage`, and no auto-connect `CheckBox` under the Settings page; `keyboardApplyConfig` and `ledBarApplyConfig` still exist.

## Manual hardware checklist (not automated)

1. Connect both devices, apply a firmware effect + an LED preset, quit, reopen → both restored.
2. Restore a forever animation → the LED bar is restored first; the keyboard light switch off stops the animation.
3. Light off, quit, reboot, `avell-storm-rgb state restore` → the lights stay off.
4. Unplug the LED bar, open the app → unavailable; plug it in, Retry → restored.
5. Confirm identity by USB id after a replug on another port.
