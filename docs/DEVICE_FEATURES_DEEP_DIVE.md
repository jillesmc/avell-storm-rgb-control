🇺🇸 English · [🇧🇷 Português](DEVICE_FEATURES_DEEP_DIVE.pt-BR.md)

# RGB devices: capabilities, combinations and UI

⏱️ **Reading time:** ~10 min

> **TL;DR**
> - **Keyboard (8291):** firmware effects **or** user mode (software colours). They replace each other. An effect's "colour" is a **palette slot index**, not RGB.
> - **LED bar (8233):** brightness and speed are only sent **inside an effect**, so changing them always re-applies an effect.
> - The GUI **disables** controls an effect doesn't use (`effectSupports`), and the backend **filters** parameters (`KEYBOARD_EFFECT_PARAMS`).

**Read this if…** you need to know which parameter works with which effect, what excludes what, and how the UI maps to the backend.

Sources: the code in `src/avell_storm_rgb/` and `src/app/`, cross-checked with [ite8291r3-ctl](https://github.com/pobrn/ite8291r3-ctl) and the **ite8233-ledbar** `ledbar` script.

---

## 🧭 Executive summary

| Aspect | ITE 8291 (keyboard) | ITE 8233 (LED bar) |
|--------|---------------------|--------------------|
| **Main "firmware" mode** | Built-in effects (`breathing`, `wave`, …), 6-byte effect packet | `static`, `breathing`, `wave`, `impact`, `raindrop` with palette + params in the HID report |
| **Uniform colour** | `set_color` (user mode + row writes), free RGB | `set_static_rgb` (one palette colour + `static`) |
| **Per-key / animation** | 6 × 21 grid, animation DSL, `set_key_colors` | Not supported |
| **Follow screen** | Yes (extra `[screen]`) | No |
| **Brightness** | 0–50: dedicated command **and** a byte in the effect packet | 0–100: kept in the Python driver, sent with the next `_send_effect` |
| **"Palette"** | **Slots 1–7** in controller memory + a semantic index in the effect | **List of up to 9** RGB colours sent to the device |

## 🏗️ ITE 8291 — mental model

### Two lighting paths

1. **Firmware effect.** `set_effect(payload)` makes the controller run an internal animation. The payload has `effect`, `speed`, `brightness`, `color`, a direction **or** reactive byte, and `save`.
2. **User mode** (solid / per-key). `enable_user_mode` plus **row-by-row** data (`set_color`, `set_key_colors`, animation DSL, follow-screen). Software decides the colours.

> [!NOTE]
> Treat them as **modes that replace each other**. Applying a firmware effect leaves user mode. Solid, per-key and follow-screen enter user mode.

### Brightness: two mechanisms

- **`SET_BRIGHTNESS`** (`keyboard brightness` / `set_brightness`): global controller brightness (0–50).
- **Brightness byte inside `SET_EFFECT`:** every effect call sends one. When it is omitted, the builder default **25** from `KEYBOARD_EFFECTS` is used.

> [!WARNING]
> **Applying an effect can reset brightness** if you don't pass `-b` (same as upstream). The GUI avoids this: in the **Effect** tab every change re-sends the packet with the slider's current brightness, and the **Device** slider re-sends the last effect (see [FLOWS § 4](FLOWS.md#-4--brightness-slider)).

### Effect "colour" ≠ free RGB

The `color` field is an **index** (`KEYBOARD_PALETTE_SLOT_COLORS` in `ite8291_usb.py`):

| CLI / GUI name | Value sent | Meaning in firmware |
|----------------|------------|---------------------|
| `none` | 0 | No slot colour. The effect may be invisible (upstream warns against it) |
| `red` … `purple` | 1–7 | **Reference to slot N** of the keyboard palette. Change slot 3 and `-c yellow` changes too |
| `random` | 8 | "Random" / multi-colour use of the palette, depending on the effect |

- **`keyboard palette set-slot …`** fills the table.
- **`-c` / the "palette slot colour" combo** picks **which entry** the effect uses.
- As upstream puts it: *the names can mislead — `red` is just the first palette colour in the default scheme.*

### Direction vs reactive: same byte, exclusive by design

`effect_attrs.DIRECTION` and `effect_attrs.REACTIVE` share **index 4** of the effect array.

- **CLI:** mutually exclusive group, `--direction` **or** `--reactive`.
- **GUI:** each control is **enabled only when the selected effect uses it** (`effectSupports`). `keyboard_effect_kwargs` sends only supported parameters.

### Effect × parameter matrix

**yes** = sent and used by the builder · **—** = not part of the effect.

| Effect | speed (0–10) | brightness (0–50) | color (slot) | direction | reactive | save |
|--------|--------------|-------------------|--------------|-----------|----------|------|
| `breathing` | yes | yes | yes | — | — | yes |
| `wave` | yes | yes | — | yes | — | yes |
| `random` | yes | yes | yes | — | yes | yes |
| `rainbow` | — | yes | — | — | — | yes |
| `ripple` | yes | yes | yes | — | yes | yes |
| `marquee` | yes | yes | — | — | — | yes |
| `raindrop` | yes | yes | yes | — | — | yes |
| `aurora` | yes | yes | yes | — | yes | yes |
| `fireworks` | yes | yes | yes | — | yes | yes |

- **Brightness:** every effect, including `rainbow`.
- **Speed:** every effect except `rainbow`.
- **Colour:** effects without it keep the builder's default index; the GUI only offers brightness and `save` for them.

### Other keyboard capabilities

- **`keyboard power off` / GUI light switch:** turns off. Switching on in the GUI re-applies the **saved look** (or the effect it had before switching off).
- **`freeze`:** sets `speed` to 11 in the current effect (experimental hack).
- **`palette restore | random | set-slot`:** only changes slots 1–7. It does **not** switch to a new effect by itself.

## 🏗️ ITE 8233 — mental model

### LED bar palette ≠ keyboard palette slot

- The bar keeps a software **`list[tuple[int,int,int]]`** (`self.palette`), up to **`MAX_LED_BAR_PALETTE = 9`**.
- `CMD_COLOR` sends each colour to a slot index. `_send_effect` sends `num_colors = len(palette)` if there is more than one colour, otherwise **1**.
- **Presets** (`rainbow`, `fire`, `ice`, `forest`) or an `r,g,b,…` list fill the list before `apply_visual_effect`.

### Effects and codes

| Name | Code |
|------|------|
| `static` | `0x01` |
| `breathing` | `0x02` |
| `wave` | `0x03` |
| `impact` | `0x04` |
| `raindrop` | `0x06` |

### Brightness and speed

- `set_brightness_level` / `set_motion_speed` only update **`self.brightness`** / **`self.speed`** in Python.
- The hardware sees them only when **`apply_visual_effect`** calls **`_send_effect`**.

> [!TIP]
> **Works with any effect?** API-wise, yes: re-apply any effect after changing brightness or speed. **Visually**, brightness clearly changes `static`. Whether speed changes anything in `static` still needs **hardware validation**.

### Typical flows

- **Single colour:** `set_static_rgb` → palette `[one colour]` + `static`.
- **Palette + animation:** `set_palette_colors` + `apply_visual_effect(name)`.
- **Change effect only:** reuses the palette and the last brightness / speed kept on the `Ite8233UsbDevice` object.

## ⚠️ Exclusivity and transitions

| Keyboard situation | Behaviour |
|--------------------|-----------|
| Light switch off | Lights off; the light state is saved and restored at startup |
| `set_effect` vs user mode | The transition replaces the active visual "engine" |
| `--direction` vs `--reactive` (CLI) | **Exclusive** (same protocol byte) |
| Direction / reactive (GUI) | Only the one the effect supports is enabled |
| `freeze` | One-off change to the effect array (speed 11) |

| LED bar situation | Behaviour |
|-------------------|-----------|
| Light switch off | Power-off sequence; animation stops; the light state is saved |
| Light switch on | Init sequence, then the GUI re-applies the saved look |

## 🔁 UI ↔ backend trace

### Keyboard (`KeyboardPage.qml` + `main.qml`)

The sub-navigation (`keyboardSubNavIndex` 0…7) drives the inner `StackLayout`. It is grouped under **Firmware**, **User-defined** and **Extra** headers (title + trailing line).

| # | Tab | "Apply" button? | Main backend call |
|---|-----|-----------------|-------------------|
| 0 | Effect | No — auto, ~200 ms debounce after a change | `applyEffect(…)` |
| 1 | Palette slot configuration | Yes | `setPaletteSlotRgb(slot, r, g, b)` — writes the slot only |
| 2 | Solid color | No — auto, ~200 ms debounce | `setSolidNamed` / `setSolidRgb` |
| 3 | Per-key grid | Yes | `applyKeyGrid(true)` |
| 4 | Animation file | No | `playAnimationFile` / `stopFollowOrAnimation` |
| 5 | Follow screen | No | `startFollowScreen` / `stopFollowOrAnimation` |
| 6 | Calibration | No | Adjusts `keyId → (device_row, col)` per device (saved per hardware) |
| 7 | Tools | No | `demoTestPattern`, `freezeAnimation` (immediate) |

- **Device block (brightness):** hidden on tabs **1** (palette) and **7** (Tools). Shown as **0–100 %**, converted to 0–50; debounced through `requestBrightnessFromUi`.
- **Effect tab:** opening the tab or resizing the window **never** re-sends. Only a user change does.
- **Firmware colour combo:** shows slot 1–7, `#RRGGBB` and a swatch. It uses the session mirror; without a mirror entry, `paletteSlotR/G/B` returns the **firmware default palette**.
- **Per-key:** a real keyboard layout (labels, variable widths). Click = one key; drag = batch. Session colours are kept **per `keyId`**, not per visual cell.
- **Layout profiles:** JSON profiles in `src/avell_storm_rgb/domain/keyboard_layouts/profiles/` separate visual geometry, identity (`keyId`) and the real LED `deviceCell`. Built in: `legacy_builtin`, `abnt2_laptop_21` (USB default for this repo's ITE 8291 PIDs), `ansi_104_21`. Changing profile clears overrides and session colours.
- **Calibration:** per-device overrides `keyId → (device_row, col)` in `keyboard_mapping_overrides.json` (schema v2: `profileId` + `overrides`); `resolve_key_to_device_cell` applies them over the profile. Conflicts (two keys on one cell) show in red.
- **Row mapping:** device row 0 is the **bottom**. **Animation DSL and follow-screen keep device coordinates** for compatibility. A saved per-key look stores device cells and is mapped back to `keyId`s with the device's overrides at restore.
- **CLI:** `avell-storm-rgb keyboard layout list|set|probe` (`probe` walks the cells; stdout = JSON `keyId → [row, col]`).

### LED bar (`LedBarPage.qml`)

| # | Tab | Action |
|---|-----|--------|
| 0 | Color (named / hex) | `setColorFromSpec` |
| 1 | Preset + effect | `applyPalette(spec, effect)` |
| 2 | Effect only | `applyEffect` |
| 3 | Brightness & motion | `applyBrightnessSpeedEffect` |

- **Device block:** a 0–100 brightness slider → `requestBrightnessFromUi(value, selectedEffect)` (debounced). It re-applies the last known mode, or the effect chosen in the shell.

## 🛠️ Debugging the Firmware tab

1. Export `AVELL_DEBUG_FIRMWARE_UI=1` (or `true` / `yes` / `on`) before starting the app.
2. **Python stderr:** each `KeyboardBackend.applyEffect` prints one line with its parameters.
3. **Qt console** (`console.log`): `requestFirmwareEffectApply`, `pushFirmwareEffectToDevice`, debounce timer fires.
4. Every **1 s** on the Firmware tab you get a summary: `scrollBodyWidth+`, `paletteMirror+`, `req+`, `push+`.

> [!TIP]
> If `scrollBodyWidth+` climbs into the hundreds while resizing, there is layout churn. The `ScrollView` uses a **fixed right gutter** for the scrollbar to prevent width ↔ reflow oscillation.

## 🛠️ CLI quick reference

```bash
uv run avell-storm-rgb keyboard effect wave -s 3 -b 40 -d up        # effect with params
uv run avell-storm-rgb keyboard effect aurora -r -s 2 -c red        # reactive (no direction)
uv run avell-storm-rgb keyboard palette set-slot 2 255,128,0        # slot 2 = "orange"
uv run avell-storm-rgb keyboard effect breathing -c orange          # uses slot 2
uv run avell-storm-rgb keyboard inspect --fw-version --brightness --power
uv run avell-storm-rgb led-bar palette rainbow --with-effect wave
uv run avell-storm-rgb led-bar brightness 80 --with-effect breathing
```

## 🛠️ Hardware validation checklist

1. **Keyboard `rainbow`:** change speed and colour → only **brightness** (and `save`) should change anything.
2. **Keyboard `wave`:** switch direction. Reactive is disabled in the GUI for `wave`.
3. **Keyboard `random` / `ripple`:** enable reactive. Combining it with direction in the CLI must be rejected by argparse.
4. **Keyboard palette:** `palette set-slot 1 255,0,0`, then compare `-c red` vs `-c orange` after changing only slot 1.
5. **LED bar `static`:** change only speed at fixed brightness. Does the static animation change?
6. **LED bar order:** `led-bar brightness` **always** re-applies `--with-effect` here (old scripts didn't send brightness alone).

## 🏗️ Tuya bulb — mental model

| DPS | Meaning | Values |
|-----|---------|--------|
| 20 | Power | `true` / `false` |
| 21 | Mode | `white`, `colour` (`scene`, `music` only from the phone) |
| 22 | White brightness | device 10–1000 ↔ 1–100 % |
| 23 | White temperature | 0–1000 ↔ 0 warm … 100 cold |
| 24 | Colour | HSV hex `HHHHSSSSVVVV`; V is the colour brightness (≥ 1 %) |

- Brightness follows the mode: white → DPS 22, colour → V of DPS 24.
- Explicit commands send DPS 20 (switch on). **Follow** sends only 21 + 24 (`push_colour`), never 20.
- More → [BULBS](BULBS.md).

## 🧭 Main files

| Topic | Path |
|-------|------|
| 8291 protocol and effects | `src/avell_storm_rgb/infrastructure/usb/ite8291_usb.py` |
| Effect parameter filter | `src/avell_storm_rgb/infrastructure/usb/ite8291_usb.py` (`KEYBOARD_EFFECT_PARAMS`, `keyboard_effect_kwargs`) |
| Saved look / restore | `src/avell_storm_rgb/application/device_state.py` |
| Keyboard UI | `src/app/ui/pages/KeyboardPage.qml`, `src/app/ui/main.qml` |
| 8233 protocol | `src/avell_storm_rgb/infrastructure/usb/ite8233_usb.py` |
| LED bar colours / palettes | `src/avell_storm_rgb/domain/ledbar_colors.py` |
| LED bar UI | `src/app/ui/pages/LedBarPage.qml`, `src/app/ui/adapters/led_bar_backend.py` |
| CLI | `src/avell_storm_rgb/adapters/cli/main.py` |

## 🧭 Local upstream copies (optional)

- `/home/jilles/git/ite8291r3-ctl/`: same effect matrix and notes on `color` / palette (README, *Effect property support matrix*).
- `/home/jilles/git/ite8233-ledbar/ledbar`: same effect codes, palette, brightness and speed, with implicit re-apply.

These paths exist only on the maintainer's machine. Use them to compare behaviour with the ported code.
