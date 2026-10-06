# Developer Experience: Remembered devices and startup look

Public-surface contract for remembered devices and the startup look. It is a companion to `_spec.md` (Part II serves
this surface) and `_tests.md` (E2E journeys use these exact invocations). The GUI surface is in `_uiux.md`.

## Golden Path

```console
# 1. In the GUI: Devices → Connect on the keyboard and on the LED bar, pick a firmware effect, quit.

# 2. See what was saved
$ avell-storm-rgb state show
State file: /home/jilles/.config/avell-storm-rgb/state.json
keyboard  048d:ce00  remembered  light on   firmware effect wave (speed 5, brightness 40, direction up)
                                            brightness 40 · palette slots 1, 3
led-bar   048d:7001  remembered  light on   breathing · 4 colours · brightness 75 · speed 3

# 3. After a reboot, restore without opening the GUI
$ avell-storm-rgb state restore
led-bar   048d:7001  restored: breathing · 4 colours · brightness 75 · speed 3
keyboard  048d:ce00  restored: firmware effect wave (speed 5, brightness 40, direction up)
$ echo $?
0
```

## State file

**Location:** `${XDG_CONFIG_HOME:-$HOME/.config}/avell-storm-rgb/state.json` (dir `0700`, file `0600`).

- **Written by the GUI only**, atomically, after each successful apply, connect, disconnect or light toggle.
- **Read** by the GUI at startup and by `state show` / `state restore`.
- Don't edit it while the GUI runs; the GUI will overwrite it.

```json
{
  "version": 1,
  "devices": {
    "keyboard": {
      "usb_id": "048d:ce00",
      "remembered": true,
      "power": "on",
      "brightness": 40,
      "palette": { "1": [255, 0, 0], "3": [255, 119, 0] },
      "look": {
        "mode": "firmware_effect",
        "effect": "wave",
        "speed": 5,
        "brightness": 40,
        "color": "random",
        "direction": "up",
        "reactive": false,
        "save": false
      }
    },
    "led_bar": {
      "usb_id": "048d:7001",
      "remembered": true,
      "power": "on",
      "look": {
        "palette": [[255, 0, 0], [255, 80, 0], [255, 160, 0], [255, 200, 0]],
        "effect": "breathing",
        "brightness": 75,
        "speed": 3
      }
    }
  }
}
```

**Other keyboard `look` shapes:**

```json
{ "mode": "solid", "rgb": [255, 255, 255] }
{ "mode": "per_key", "cells": [[5, 0, 255, 0, 0], [2, 2, 255, 0, 0], [2, 3, 255, 0, 0]] }
{ "mode": "animation", "path": "/home/jilles/anim/gaming_mode", "loops": 1, "forever": true }
```

- `cells` items are `[device_row, col, r, g, b]`: row 0 = **bottom** of the keyboard (rows 0–5, cols 0–20).
- `look: null` means "connect only, send nothing".
- A device that was disconnected has `"remembered": false`; its look and power are kept for a later reconnect.

## CLI

### `avell-storm-rgb state show [--json]`

**No saved state:**

```console
$ avell-storm-rgb state show
No saved state at /home/jilles/.config/avell-storm-rgb/state.json
$ echo $?
0
```

**Saved state, with one device forgotten and the keyboard light off:**

```console
$ avell-storm-rgb state show
State file: /home/jilles/.config/avell-storm-rgb/state.json
keyboard  048d:ce00  remembered  light off  animation /home/jilles/anim/gaming_mode (forever)
led-bar   048d:7001  forgotten   light on   static · 1 colour · brightness 50 · speed 3
```

**JSON** (the state document plus `path`; key order as written):

```console
$ avell-storm-rgb state show --json
{"path": "/home/jilles/.config/avell-storm-rgb/state.json", "version": 1, "devices": {"keyboard": {"usb_id": "048d:ce00", "remembered": true, "power": "off", "brightness": null, "palette": {}, "look": {"mode": "animation", "path": "/home/jilles/anim/gaming_mode", "loops": 1, "forever": true}}, "led_bar": {"usb_id": "048d:7001", "remembered": false, "power": "on", "look": {"palette": [[136, 0, 255]], "effect": "static", "brightness": 50, "speed": 3}}}}
```

With no file: `{"path": "/home/jilles/.config/avell-storm-rgb/state.json", "version": 1, "devices": {}}`, exit 0.

### `avell-storm-rgb state restore [--kind all|keyboard|led-bar] [--no-animation] [--json]`

**Order:** LED bar, then keyboard. Only **remembered** devices are restored. The state file is never modified.

```console
$ avell-storm-rgb state restore
led-bar   048d:7001  restored: static · 1 colour · brightness 50 · speed 3
keyboard  048d:ce00  restored: light off
$ echo $?
0
```

**Forever animation (foreground until Ctrl+C):**

```console
$ avell-storm-rgb state restore --kind keyboard
keyboard  048d:ce00  restored: animation /home/jilles/anim/gaming_mode (forever) — playing, Ctrl+C to stop
^C
$ echo $?
0
```

**Skip the animation** (light state, palette and brightness are still applied):

```console
$ avell-storm-rgb state restore --no-animation
led-bar   048d:7001  restored: breathing · 4 colours · brightness 75 · speed 3
keyboard  048d:ce00  restored: palette, brightness (animation skipped)
```

**A remembered device is missing:**

```console
$ avell-storm-rgb state restore
led-bar   048d:7001  skipped: device not found
keyboard  048d:ce00  restored: solid #ffffff
$ echo $?
1
```

**JSON:**

```console
$ avell-storm-rgb state restore --no-animation --json
{"path": "/home/jilles/.config/avell-storm-rgb/state.json", "results": [{"kind": "led_bar", "usb_id": "048d:7001", "status": "skipped", "reason": "device not found"}, {"kind": "keyboard", "usb_id": "048d:ce00", "status": "restored", "applied": ["palette 1,3", "brightness 40", "firmware effect wave"], "warnings": []}]}
```

- `status` is `restored` | `skipped` | `failed`.
- Forgotten devices do not appear in `results`.

### Unchanged

- `keyboard …`, `led-bar …` and `device list` behave as before. They **do not** update `state.json`.

## Errors

| Condition | Surface | Exact output | Exit |
|-----------|---------|--------------|------|
| No state file | `state show` | `No saved state at <path>` | 0 |
| No state file | `state restore` | `Nothing to restore: no saved state at <path>` | 0 |
| Invalid JSON / schema / version | `state show`, `state restore` | `error: saved state is unreadable (<reason>): <path>` | 3 |
| Remembered device not present | `state restore` | `<kind>  <usb_id>  skipped: device not found` | 1 |
| USB error while restoring | `state restore` | `<kind>  <usb_id>  failed: <ExceptionType>: <message>` | 1 |
| Saved animation file missing | `state restore` | `<kind>  <usb_id>  restored: light on (warning: animation file not found: <path>)` | 1 |
| Bad flag / value | any | argparse usage message | 2 |
| Invalid state file at GUI start | GUI (Devices page error) | `Saved device state was unreadable (<reason>) and was moved to <path>.invalid. Starting fresh.` | — |
| Saved animation missing at GUI start | GUI (Devices page error) | `Keyboard: saved animation file not found: <path>. Light state restored; look not applied.` | — |
| State file not writable | GUI (Devices page error) | `Could not save device state to <path>: <reason>` | — |

`<reason>` examples: `invalid JSON at line 3 column 5`, `unsupported version 2`, `keyboard.look.speed must be 0–10, got 12`.
