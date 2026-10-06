# User Stories: Remembered devices and startup look

Canonical behaviour catalog for remembered devices and the startup look. It is a companion to `_spec.md` and is consumed by
`_spec.md` Part II (component mapping), `_uiux.md` (surface states) and `_tests.md` (coverage matrix).

## Personas

- **Laptop owner** — uses the desktop GUI daily. Wants the lights to come back exactly as they left them, with as few controls and steps as possible.
- **Script / agent** — runs the CLI (login script, automation, an AI agent). Needs to inspect and re-apply the saved state without a GUI, with structured output and stable exit codes.

## Story Index

| ID | Feature Area | Persona | Story |
|----|--------------|---------|-------|
| US-001 | Device memory | Laptop owner | Connecting on Devices remembers the device and adds it to the sidebar |
| US-002 | Device memory | Laptop owner | Remembered devices reconnect when the app opens |
| US-003 | Device memory | Laptop owner | Disconnecting on Devices forgets the device but keeps its look |
| US-004 | Device memory | Laptop owner | A remembered device that is unavailable can be retried or forgotten |
| US-005 | Saved look | Laptop owner | The keyboard's last applied look is saved automatically |
| US-006 | Saved look | Laptop owner | The LED bar's last applied look is saved automatically |
| US-007 | Saved look | Laptop owner | Saved looks and light state are applied when the app opens |
| US-008 | Light toggle | Laptop owner | The sidebar switch turns a device's light on and off |
| US-009 | CLI | Script / agent | Show the saved state |
| US-010 | CLI | Script / agent | Restore the saved state without the GUI |
| US-011 | Upgrade | Laptop owner | Upgrading keeps today's auto-connect behaviour |
| US-012 | Robustness | Laptop owner | An unreadable state file never blocks the app |

## Device memory

### US-001: Connect and remember

**As a** laptop owner, **I want** connecting a device on the Devices page to remember it, **so that** I configure it once and it appears in the sidebar.

Acceptance criteria:

- AC-1: Given a keyboard listed on Devices and not remembered, when I press **Connect**, then the keyboard connects, a **Keyboard** entry appears in the sidebar and the row says it is remembered.
- AC-2: Given the keyboard was connected via Devices, when I quit and reopen the app, then the Keyboard entry is in the sidebar without pressing Connect again.
- AC-3: Given no device is remembered, when the app is open, then the sidebar shows only **Devices** (plus Settings/About) and no device entries.

Edge cases:

- EC-1: Connect fails (USB permission denied) → an error message is shown on Devices. The device is **not** remembered and gets no sidebar entry.
- EC-2: A different keyboard (another USB id) is connected while one is already remembered → the new one replaces the remembered keyboard. The saved look is kept and applied to the new one on its next restore.
- EC-3: Connect is pressed twice quickly → one connection. The device is remembered once, with no duplicate sidebar entry.

### US-002: Reconnect at startup

**As a** laptop owner, **I want** remembered devices to reconnect when the app opens, **so that** I never press Connect again.

Acceptance criteria:

- AC-1: Given a remembered keyboard and LED bar that are both plugged in, when the app opens, then both are connected and their tabs are usable without any click.
- AC-2: Given a device present but not remembered, when the app opens, then it is not connected and has no sidebar entry.

Edge cases:

- EC-1: The device is on a different USB bus/address than last time (reboot, replug) → it is still found and connected (identity is the USB id).
- EC-2: Two present devices share the remembered USB id → the first in scan order is connected.
- EC-3: Remembered device absent at startup → no error dialog. Its sidebar entry shows *unavailable* (see US-004).

### US-003: Disconnect forgets

**As a** laptop owner, **I want** Disconnect on Devices to forget the device, **so that** the app stops touching it at startup.

Acceptance criteria:

- AC-1: Given a connected, remembered LED bar, when I press **Disconnect** on Devices, then USB is released and the LED bar entry leaves the sidebar.
- AC-2: Given I disconnected the LED bar, when I reopen the app, then it is not connected and has no sidebar entry.
- AC-3: Given I disconnected the LED bar earlier, when I press **Connect** on it again, then it comes back with the look and light state it had before.

Edge cases:

- EC-1: Disconnecting the keyboard while an animation or follow-screen runs → it stops first, then USB is released.
- EC-2: Disconnecting while the Keyboard page is shown → the view goes back to **Devices**.

### US-004: Unavailable remembered device

**As a** laptop owner, **I want** a remembered device that is missing or fails to open to say so, **so that** I know why and can retry or forget it.

Acceptance criteria:

- AC-1: Given a remembered LED bar that is not plugged in, when the app opens, then its sidebar entry shows *unavailable*. Its page shows "Not found (048d:7001)" with **Retry** and **Forget** actions, and its light switch is disabled.
- AC-2: Given the bar is plugged in later, when I press **Retry** (or **Refresh list** on Devices), then it connects and its saved look and light state are applied.
- AC-3: Given an unavailable entry, when I press **Forget**, then the entry leaves the sidebar and the device is no longer reconnected at startup. Its saved look is kept.

Edge cases:

- EC-1: Retry while the device is still absent → the entry stays *unavailable* and the reason is unchanged, with no error popup.
- EC-2: USB permission error → the reason shows the error text, not "Not found".

## Saved look

### US-005: Keyboard look saved automatically

**As a** laptop owner, **I want** whatever I last applied on the keyboard to be saved, **so that** I don't need a save step.

Acceptance criteria:

- AC-1: Given the keyboard is connected, when a firmware effect is applied (Effect tab), then that effect and its parameters become the saved keyboard look.
- AC-2: Given the keyboard is connected, when a solid colour is applied, then that colour becomes the saved look.
- AC-3: Given per-key colours are set, when I press **Apply**, then the grid becomes the saved look.
- AC-4: Given an animation file is played (N loops or forever), when playback starts successfully, then the file path and loop mode become the saved look.
- AC-5: Given I change a palette slot or the brightness slider, when the change is applied, then the slot colour / brightness is saved alongside the look.

Edge cases:

- EC-1: The USB apply fails → the saved look is unchanged.
- EC-2: Follow-screen, demo test pattern or freeze is used → the saved look is unchanged. The next startup restores the previous look.
- EC-3: Settings changed quickly → each apply is debounced as today. The last successful one is what is saved.
- EC-4: Per-key Apply with no keys set → saved as a per-key look with no cells (keyboard dark). This matches what the user sees.

### US-006: LED bar look saved automatically

**As a** laptop owner, **I want** the LED bar's last applied colour/preset/effect/brightness/speed to be saved, **so that** it comes back as is.

Acceptance criteria:

- AC-1: Given the LED bar is connected, when I apply a colour, a preset + effect, an effect, or brightness & motion, then the bar's full resulting parameters (colours, effect, brightness, speed) become its saved look.
- AC-2: Given I move the LED bar brightness slider, when the debounced apply succeeds, then the saved look's brightness updates.

Edge cases:

- EC-1: The USB apply fails → the saved look is unchanged.
- EC-2: A palette longer than 9 colours → only the first 9 are applied and saved (driver limit).

### US-007: Restore at startup

**As a** laptop owner, **I want** saved looks and light states applied when the app opens, **so that** the lights look like I left them.

Acceptance criteria:

- AC-1: Given a saved keyboard firmware effect and light `on`, when the app opens, then the keyboard shows that effect with the saved palette slots and brightness.
- AC-2: Given a saved keyboard animation (forever), when the app opens, then the LED bar is restored first and the animation then starts on the keyboard and keeps playing.
- AC-3: Given a saved light `off`, when the app opens, then the device's light is off, the look is not applied and the switch shows off.
- AC-4: Given a remembered device with no saved look and light `on`, when the app opens, then it connects and nothing else is sent.

Edge cases:

- EC-1: Saved animation file was deleted or moved → the light state is applied but the look is not. A warning names the file, and the saved look is kept (it works again if the file comes back).
- EC-2: A restore step fails on USB → the error is shown like any USB failure. Later steps for other devices still run.
- EC-3: The user changes a look while restore is still in progress → their change is applied after the restore steps and becomes the saved look.
- EC-4: A firmware effect was saved with the hardware `save` flag → it is restored the same way. A double apply is harmless.

## Light toggle

### US-008: Sidebar light switch

**As a** laptop owner, **I want** the switch next to a device in the sidebar to turn its light on and off, **so that** I don't need footer power buttons.

Acceptance criteria:

- AC-1: Given a connected keyboard with its light on, when I switch it off, then the backlight turns off, the switch shows off and the light state `off` is saved.
- AC-2: Given the light is off, when I switch it on, then the saved look is re-applied and `on` is saved.
- AC-3: Given the Keyboard or LED bar page, when I look at the footer, then there are no **Power on** / **Power off** buttons; **Apply** is still where it was.
- AC-4: Given the light is off, when I apply any look, then the light turns on and the switch shows on.

Edge cases:

- EC-1: Switch off while a keyboard animation or follow-screen runs → it stops first, then the light turns off.
- EC-2: Switch on with no saved look → keyboard: the effect it had before the last switch-off in this session, else firmware **rainbow** at default brightness; LED bar: power-on only.
- EC-3: Device unavailable → the switch is disabled and shows the last saved light state.
- EC-4: Switch flipped rapidly → commands are applied in order, and the final switch position is the final light state.

## CLI

### US-009: Show saved state

**As a** script / agent, **I want** `avell-storm-rgb state show`, **so that** I can inspect what will be restored.

Acceptance criteria:

- AC-1: Given a state file, when I run `state show`, then each saved device prints its kind, USB id, remembered flag, light state and look summary, with exit code 0.
- AC-2: Given `--json`, when I run `state show --json`, then the output is the state document plus the file path, with exit code 0.

Edge cases:

- EC-1: No state file → prints "No saved state at <path>", exit 0 (`--json`: `{"path": …, "devices": {}}`).
- EC-2: Invalid state file → prints the reason, exit 3. The file is not changed.

### US-010: Restore without the GUI

**As a** script / agent, **I want** `avell-storm-rgb state restore`, **so that** the lights can be restored without opening the GUI.

Acceptance criteria:

- AC-1: Given remembered devices with saved looks, when I run `state restore`, then the LED bar and then the keyboard get their saved light state and look. Each prints a result line; exit 0.
- AC-2: Given `--kind keyboard`, when I run it, then only the keyboard is restored.
- AC-3: Given a saved forever animation, when I run `state restore`, then it plays in the foreground until Ctrl+C. With `--no-animation`, it is skipped and the command returns.
- AC-4: Given any run, when it finishes, then the state file is unchanged.

Edge cases:

- EC-1: A remembered device not present → reported as skipped "device not found", other devices still restored, exit 1.
- EC-2: Device not remembered (forgotten) → skipped silently and not counted as a failure.
- EC-3: No state file → "Nothing to restore", exit 0.
- EC-4: Invalid state file → reason printed, exit 3, nothing sent to USB.
- EC-5: The saved animation file is missing → warning; the light state is still applied; exit 1.
- EC-6: The GUI is running at the same time → both may talk to USB; the last command wins. Documented, not prevented.

## Upgrade and robustness

### US-011: Upgrade keeps auto-connect behaviour

**As a** laptop owner upgrading, **I want** my devices to keep connecting at startup, **so that** the upgrade doesn't feel broken.

Acceptance criteria:

- AC-1: Given the old auto-connect setting was on (or never changed) and no state file exists, when the new version opens the first time, then the first discovered keyboard and LED bar are connected and remembered with light `on`.
- AC-2: Given the old setting was off, when the new version opens the first time, then nothing is remembered and nothing connects.
- AC-3: Given the migration ran, when I open Settings, then there is no auto-connect option.

Edge cases:

- EC-1: No devices present at the first start of the new version → nothing is remembered. The legacy key is still removed, and the migration does not run again.
- EC-2: A state file already exists (e.g. created by a previous run) → no migration; the legacy key is removed.

### US-012: Unreadable state file

**As a** laptop owner, **I want** a broken state file not to block the app, **so that** I can keep using it and still recover the file.

Acceptance criteria:

- AC-1: Given `state.json` contains invalid JSON, when the app opens, then it starts with nothing remembered. An error says the saved state was unreadable and was moved to `state.json.invalid`.
- AC-2: Given that situation, when I connect a device, then a fresh `state.json` is written.

Edge cases:

- EC-1: The file has `version` 2 (written by a newer version) → treated as unreadable, moved aside and the error names the version. Nothing is deleted.
- EC-2: The config directory is not writable → saving fails with a logged error and an error message. The app keeps working with in-memory state for this session.
