🇺🇸 English · [🇧🇷 Português](FLOWS.pt-BR.md)

# Flows

⏱️ **Reading time:** ~8 min (or ~1 min per flow)

> **TL;DR**
> - Eight step-by-step flows, **one per section**. Jump straight to the one you need.
> - GUI flows always follow the same shape: **QML → `App.<backend>.<slot>` → `UsbWorker` → driver → USB**.
> - Watch for the **Warning** callouts; they mark the non-obvious steps.

**Read this if…** you need to know *what happens* when someone clicks or runs something.

| # | Flow | Section |
|---|------|---------|
| 1 | CLI command | [1](#-1--cli-command) |
| 2 | GUI startup and auto-connect | [2](#-2--gui-startup-and-auto-connect) |
| 3 | Firmware effect from the GUI | [3](#-3--firmware-effect-from-the-gui) |
| 4 | Brightness slider | [4](#-4--brightness-slider) |
| 5 | Per-key colours | [5](#-5--per-key-colours) |
| 6 | Follow screen | [6](#-6--follow-screen) |
| 7 | Power off and replay | [7](#-7--power-off-and-replay) |
| 8 | Animation script | [8](#-8--animation-script) |

---

## 🔁 1 · CLI command

```mermaid
sequenceDiagram
    actor U as User
    participant M as cli/main.py
    participant F as device_facade
    participant D as Ite8291UsbDevice
    U->>M: avell-storm-rgb keyboard effect wave -s 3
    M->>M: argparse → args._handler = _cmd_keyboard_effect
    M->>F: open_keyboard(bus_addr, debug)
    F->>D: find USB device, detach kernel driver
    M->>D: set_effect(KEYBOARD_EFFECTS["wave"](speed=3))
    D-->>U: exit 0 (errors → stderr, exit 1)
```

- **Every command opens the device fresh** and exits. Nothing is kept between runs.
- Handlers live in `src/avell_storm_rgb/adapters/cli/main.py` (`_cmd_*`). The parser is built in `_build_parser()` (`:273`).

## 🔁 2 · GUI startup and auto-connect

```mermaid
sequenceDiagram
    participant Main as main.py
    participant Fa as AppFacade
    participant Q as main.qml
    participant KB as KeyboardBackend
    participant W as UsbWorker
    Main->>Fa: AppFacade(engine) → context property "App"
    Main->>Q: engine.load(main.qml)
    Q->>Fa: refreshDevices()  (USB scan, GUI thread)
    Q->>Fa: tryAutoConnectDiscoveredDevices()
    Fa->>KB: connectAt(bus, addr)  (first keyboard)
    KB->>W: submit(task)
    W->>KB: open_keyboard → connectedChanged → inspect
    KB-->>Q: App.keyboard.connected = true → tab appears
```

- Auto-connect is **on by default**. It is skipped when `ui/autoConnectOnStartup` is false (**Settings** page).
- The LED bar follows the same path through `LedBarBackend.connectAt` (`open_led_bar_at(bus, addr)`).
- If QML fails to load (Kirigami missing), `main()` prints a hint and exits 1.

## 🔁 3 · Firmware effect from the GUI

```mermaid
sequenceDiagram
    actor U as User
    participant P as KeyboardPage.qml
    participant KB as KeyboardBackend
    participant W as UsbWorker
    participant D as Ite8291UsbDevice
    U->>P: change effect / speed / colour / direction
    P->>P: firmwareEffectDirty = true, restart 200 ms timer
    P->>KB: applyEffect(name, speed, brightness, color, dir, reactive, save)
    KB->>KB: remember params, brightness target = FIRMWARE_REAPPLY
    KB->>W: submit(task)
    W->>D: set_effect(builder(**_effect_kwargs(...)))
    W-->>P: inspectUpdate → fw / brightness / on-off
```

- **Debounce:** `fwEffectApplyTimer` (200 ms) in `src/app/ui/pages/KeyboardPage.qml:141`. Opening the tab or resizing **does not** send anything.
- **Filter:** `_effect_kwargs` (`keyboard_backend.py:428`) keeps only the parameters listed in `EFFECT_KWARGS` for that effect.

> [!WARNING]
> The **colour** sent is a **palette slot index** (1–7, 8 = random, 0 = none), **not RGB**.

## 🔁 4 · Brightness slider

```mermaid
stateDiagram-v2
    [*] --> GLOBAL_ONLY
    GLOBAL_ONLY --> FIRMWARE_REAPPLY: applyEffect()
    FIRMWARE_REAPPLY --> GLOBAL_ONLY: solid / per-key / animation / follow / power off / connect
```

1. Slider moves → `requestBrightnessFromUi(fw0to50)` (`keyboard_backend.py:402`). The QML converts % → 0–50.
2. A 200 ms `QTimer` collapses rapid moves into one call.
3. The task sends `set_brightness(v)`.
4. **If** the target is `FIRMWARE_REAPPLY` and the keyboard is on, the last firmware effect is **re-sent with the new brightness**. The effect packet has its own brightness byte, which would otherwise override the change.

**LED bar:** `requestBrightnessFromUi(value, shellEffect)` → 200 ms debounce → `set_brightness_level` + `apply_visual_effect(last or shell effect)`. The bar **only** applies brightness together with an effect.

## 🔁 5 · Per-key colours

```mermaid
sequenceDiagram
    actor U as User
    participant V as KeyboardLayoutView.qml
    participant KB as KeyboardBackend
    participant G as per_key_grid
    participant D as Ite8291UsbDevice
    U->>V: click a key (or drag-select)
    V->>KB: setKeyById(keyId, r, g, b, applyNow=false)
    KB->>G: key_id_to_ui_cell(keyId) → (uiRow, col)
    KB->>KB: _key_colors[(uiRow, col)] = rgb, keyGridEpoch++
    U->>KB: Apply → applyKeyGrid(true)
    KB->>G: color_map_ui_to_device(map)  (flip rows)
    KB->>D: set_key_colors → user mode + 6 × (row index + 65 bytes)
```

> [!WARNING]
> **Two coordinate systems.** GUI row 0 = **top** (F-keys). Device row 0 = **bottom**. Only the GUI per-key grid flips rows. **Animation scripts and follow-screen already use device coordinates.**

- Changes are **staged** (the dialogs pass `applyNow=false`). Nothing reaches the keyboard until **Apply**.
- QML repaints because each key's colour binding depends on `keyGridEpoch`.

## 🔁 6 · Follow screen

```mermaid
flowchart TB
    start["startFollowScreen / CLI follow-screen"] --> wl{"Wayland?<br/>WAYLAND_DISPLAY or<br/>XDG_SESSION_TYPE"}
    wl -- no --> x11["X11 source: Xlib root window<br/>(full screen or region)"]
    wl -- yes --> portal["Portal window picker<br/>→ PipeWire stream"]
    x11 --> cap["Grab next frame → PIL RGB"]
    portal --> cap
    cap --> small["Resize to 16 × 6 (BOX)"]
    small --> keys["set_key_colors<br/>(user mode once)"]
    keys --> stop{"Stop requested,<br/>Ctrl+C or window gone?"}
    stop -- no --> cap
    stop -- yes --> done["End"]
```

- **~10 fps** (0.1 s minimum between frames). Router: `screen_follow_dispatch.py:32`.
- **Wayland** ignores `--region`. You pick a **window**, not the whole desktop.
- In the GUI it runs with `show_busy=False`. **Stop** sets `_follow_stop`.

> [!WARNING]
> While it runs, it **holds the only USB thread**. Other GUI USB actions queue until you press Stop.

## 🔁 7 · Power off and replay

| Device | Power off | Power on (GUI) |
|--------|-----------|----------------|
| **Keyboard** | `powerOff` → `get_effect()` **snapshot** → `turn_off()` → `effectSnapshotUpdate` | `powerOnReplay` → `set_effect(snapshot)` |
| **LED bar** | `powerOff` → `power_off()` sequence | `powerOnReplay` → `power_on()` + `_replay_last_on_device()` |

- **LED bar replay record:** every action emits `replayModeUpdate` with a dict of kind `color`, `palette`, `effect`, `tune_bri`, `tune_sp` or `tune`. The last one wins.
- **Disconnect** clears both the snapshot and the replay record.
- The CLI has `keyboard power off` only. Power on with replay is **GUI only**.

## 🔁 8 · Animation script

```mermaid
flowchart LR
    file["Script lines"] --> parse["run_animation_lines"]
    parse -->|"pos R C r,g,b"| map[("colour map")]
    parse -->|clear / shift| map
    parse -->|apply| send["set_key_colors(map)"]
    parse -->|brightness N| br["set_brightness(N)"]
    parse -->|wait S| sleep["sleep(S)"]
```

- Parser: `src/avell_storm_rgb/domain/anim_dsl.py:20`. Grammar: [assets/animations/README](../assets/animations/README.md).
- **Comments:** lines starting with `#`, and nested `/* … */` blocks.
- **Loops:** CLI `--loop N` / `--forever`; GUI loops + "forever" checkbox. **Stop** sets the same `_follow_stop` event as follow-screen.
- Coordinates are **device rows** (row 0 = bottom).
