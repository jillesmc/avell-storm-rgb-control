🇺🇸 English · [🇧🇷 Português](FEATURE_MATRIX.pt-BR.md)

# Feature matrix and parity (ITE 8291 + ITE 8233)

⏱️ **Reading time:** ~2 min

> **TL;DR**
> - Every hardware capability and the **CLI command** that reaches it, one row each.
> - **Parity rule:** every row must stay reachable through the unified CLI `avell-storm-rgb`.
> - Parameters per effect and what excludes what → [DEVICE_FEATURES_DEEP_DIVE](DEVICE_FEATURES_DEEP_DIVE.md). CLI vs GUI → [OVERVIEW](OVERVIEW.md).

**Read this if…** you need to know whether something is supported and how to call it.

Upstream inspiration: [ite8291r3-ctl](https://github.com/pobrn/ite8291r3-ctl). The LED bar protocol comes from MIT-licensed vendor sources (see [NOTICE](../NOTICE)).

---

## 🧭 ITE 8291 — keyboard backlight

USB `048d` products `6004`, `6006`, `CE00`, `600B`, `bcdDevice` 0.03.

| Capability | Limits / notes | CLI |
|------------|----------------|-----|
| Power off | `turn_off` | `keyboard power off` |
| Brightness | **0–50** | `keyboard brightness <n>` |
| Built-in firmware effects | breathing, wave, random, rainbow, ripple, marquee, raindrop, aurora, fireworks | `keyboard effect <name> …` |
| Effect options | speed 0–10, brightness, palette colour slot, direction **or** reactive, save | same subcommand flags |
| Solid colour (whole keyboard) | named colours or RGB | `keyboard solid-color …` |
| Palette | set slot 1–7, restore defaults, random | `keyboard palette restore \| random \| set-slot` |
| Demo test pattern | 6-step sequence | `keyboard demo-test-pattern` |
| Freeze animation | speed → 11 | `keyboard freeze-animation` |
| Per-key colours + animation DSL | 6 × 21 grid; file or stdin | `keyboard play-animation …` |
| Follow screen | 16 × 6 sample; X11 optional region; Wayland portal window picker | `keyboard follow-screen …` (extra `[screen]`) |
| Inspect | FW version, brightness, on/off | `keyboard inspect …` |
| List compatible keyboards | USB enumeration | `device list --kind keyboard` |
| Debug USB traffic | stderr | `keyboard --debug …` |

> [!WARNING]
> The effect **colour** option selects a **palette slot**, not an RGB value. **Direction** and **reactive** share one protocol byte, so the CLI makes them mutually exclusive.

## 🧭 ITE 8233 — LED bar

USB `048d:7000`, `048d:7001`, or product string containing `8233`.

| Capability | Limits / notes | CLI |
|------------|----------------|-----|
| Power on / off | init sequence | `led-bar power on \| off` |
| Static colour | named + `#RRGGBB` | `led-bar color <spec>` |
| Palette | presets + comma-separated list | `led-bar palette <spec>` |
| Visual effect | static, breathing, wave, impact, raindrop | `led-bar effect <name>` |
| Brightness | **0–100** (applied with an effect) | `led-bar brightness <n> --with-effect …` |
| Motion speed | 1–10 (applied with an effect) | `led-bar speed <n> --with-effect …` |
| Status / discovery | | `led-bar inspect` / `device list --kind led-bar` |

> [!NOTE]
> The LED bar only receives brightness and speed **inside an effect report**. That is why both commands re-apply an effect (`--with-effect`).

## 🧭 Saved state (both devices)

The GUI remembers connected devices and their last look in `state.json`. The CLI can read it.

| Capability | Limits / notes | CLI |
|------------|----------------|-----|
| Show the saved state | human or `--json` | `state show [--json]` |
| Restore without the GUI | LED bar then keyboard; remembered devices only; never writes the file | `state restore [--kind all\|keyboard\|led-bar] [--no-animation] [--json]` |

## 🧭 Tuya bulbs (optional `tuya` extra)

| Feature | CLI | GUI |
|---------|-----|-----|
| Import tinytuya `devices.json` | `bulb import` | Devices → Import Tuya devices… |
| List / status | `bulb list`, `bulb status` | Devices rows, page status line |
| On / off / toggle | `bulb on\|off\|toggle` | Sidebar + page switch |
| Brightness 1–100 % | `bulb bright` | Page slider |
| White temperature 0–100 | `bulb white --temp` | Page slider |
| Colour RGB | `bulb color R G B` | Page colour well |
| Remember / forget / remove | `bulb remove` (remove only) | Connect / Disconnect / Forget / Remove |
| Follow keyboard / screen / LED bar | ❌ (needs the running GUI) | Page **Follow** |
| Saved state | `state show` lists bulbs | `state.json` `devices.bulbs` (remembered + follow; no colour) |

Details → [BULBS](BULBS.md).

## 🛠️ USB reference

- Keyboard: vendor `048d`, products listed above.
- LED bar: `048d:7000`, `048d:7001`, or product containing `8233`.
- udev rules: [DEVELOPMENT](DEVELOPMENT.md). They are not packaged by this repo yet.
