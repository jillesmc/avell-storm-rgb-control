# Feature matrix and parity (ITE 8291 + ITE 8233)

Upstream inspiration: [ite8291r3-ctl](https://github.com/pobrn/ite8291r3-ctl); LED bar protocol from MIT-licensed vendor sources (see NOTICE).  
CLI/API in this repo: `avell-storm-rgb` (see README). Each row should remain reachable through the unified interface (parity).

## ITE 8291 (keyboard backlight, USB `048d` products `6004`, `6006`, `CE00`, `600B`, `bcdDevice` 0.03)

| Capability | Limits / notes | Covered by unified CLI |
|------------|----------------|-------------------------|
| Power off | `turn_off` | `keyboard power off` |
| Brightness | 0–50 | `keyboard brightness set <n>` |
| Built-in firmware effects | breathing, wave, random, rainbow, ripple, marquee, raindrop, aurora, fireworks | `keyboard effect apply <name> …` |
| Effect options | speed 0–10, brightness, palette color slot, direction OR reactive, save | same subcommand flags |
| Solid color (full keyboard) | named colors or RGB | `keyboard solid-color …` |
| Palette | set slot 1–7, restore defaults, random | `keyboard palette …` |
| Demo test pattern | 6-step sequence | `keyboard demo-test-pattern` |
| Freeze animation | speed→11 | `keyboard freeze-animation` |
| Per-key colors + animation DSL | 6×21 grid; file/stdin | `keyboard play-animation …` |
| Follow screen | 16×6 sample; X11 optional region; Wayland portal window picker | `keyboard follow-screen …` (extra `[screen]`) |
| Inspect | FW version, brightness, on/off | `keyboard inspect …` |
| List compatible keyboards | USB enumeration | `device list --kind keyboard` |
| Debug USB traffic | stderr | global `--debug` |

## ITE 8233 (LED bar, USB `048d` `7000`/`7001` or product string `8233`)

| Capability | Limits / notes | Covered by unified CLI |
|------------|----------------|-------------------------|
| Power on / off | init sequence | `led-bar power on|off` |
| Static color | named + `#RRGGBB` | `led-bar color` + spec (name or `#RRGGBB`) |
| Palette | presets + comma-separated | `led-bar palette` + spec (preset or comma RGB list) |
| Visual effect | static, breathing, wave, impact, raindrop | `led-bar effect` + name |
| Brightness | 0–100 (applied with effect) | `led-bar brightness` + value; `--with-effect` |
| Motion speed | 1–10 | `led-bar speed` + value; `--with-effect` |
| Status / discovery | | `led-bar inspect` / `device list --kind led-bar` |

## USB reference (documentation only; udev packaging is a later phase)

- Keyboard: vendor `048d`, see product list above.
- LED bar: `048d:7000`, `048d:7001`, or product containing `8233`.
