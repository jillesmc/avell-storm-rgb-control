# Developer Experience: Tuya smart bulbs

Public-surface contract for Tuya bulb integration. Companion to `_spec.md` (Part II serves this surface)
and `_tests.md` (E2E journeys use these exact invocations). Ids, keys, MACs and IPs below are fictional.

## Golden Path

```console
# 0. Once, outside the app: get local keys from the Tuya cloud (writes devices.json)
$ cd ~/git/iot && python -m tinytuya wizard

# 1. Install bulb support (optional extra) and import
$ cd ~/git/avell-storm-rgb-control && uv sync --extra gui --extra tuya
$ uv run avell-storm-rgb bulb import ~/git/iot/devices.json
Quarto       eb1a2b3c4d5e6f70819201  added
Escritório   eb1a2b3c4d5e6f70819202  added
Sala         eb1a2b3c4d5e6f70819203  added
Imported 3 bulbs into /home/jilles/.config/avell-storm-rgb/tuya_devices.json

# 2. Use it
$ uv run avell-storm-rgb bulb status
Quarto       on   white   brightness 100%  temperature 100%
Escritório   on   colour  #ff8800  brightness 100%
Sala         off
$ uv run avell-storm-rgb bulb off escritorio
Escritório   off

# 3. In the GUI: Devices → Smart bulbs → Connect on Escritório → it is in the sidebar with a light switch.
```

## Installation

| Command | Effect |
|---------|--------|
| `uv sync --extra tuya` | Installs `tinytuya>=1.20,<2`. Enables the `bulb` CLI verbs and, with `--extra gui`, the bulb GUI. |
| (no `tuya` extra) | App and CLI behave exactly as before; `bulb …` prints the install hint (see Errors). |

## Files

### Inventory — `$XDG_CONFIG_HOME/avell-storm-rgb/tuya_devices.json` (default `~/.config/…`)

Written by `bulb import`, `bulb remove`, the GUI's Import/Remove, and when a bulb answers on a new IP.
Mode **0600**. Holds the local keys: do not share it.

```json
{
  "version": 1,
  "devices": [
    {"id": "eb1a2b3c4d5e6f70819201", "name": "Quarto", "key": "q6R!x2_example_01", "mac": "10:d5:61:00:00:01", "protocol": "3.3", "last_ip": "192.168.0.21"},
    {"id": "eb1a2b3c4d5e6f70819202", "name": "Escritório", "key": "q6R!x2_example_02", "mac": "10:d5:61:00:00:02", "protocol": "3.3", "last_ip": "192.168.0.22"},
    {"id": "eb1a2b3c4d5e6f70819203", "name": "Sala", "key": "q6R!x2_example_03", "mac": "10:d5:61:00:00:03", "protocol": "3.3", "last_ip": null}
  ]
}
```

### `state.json` — new `devices.bulbs` section (written only by the GUI)

```json
{
  "version": 1,
  "devices": {
    "keyboard": {"usb_id": "048d:600b", "remembered": true, "power": "on", "brightness": 36, "palette": {}, "look": {"mode": "solid", "rgb": [0, 120, 255]}},
    "led_bar": {"usb_id": "048d:7001", "remembered": true, "power": "on", "look": {"palette": [[255, 0, 0], [0, 0, 255]], "effect": "wave", "brightness": 100, "speed": 3}},
    "bulbs": {
      "eb1a2b3c4d5e6f70819202": {"remembered": true, "follow": "keyboard"},
      "eb1a2b3c4d5e6f70819203": {"remembered": false, "follow": "none"}
    }
  }
}
```

- `remembered`: shown in the sidebar and reconnected (read only) at start.
- `follow`: `none` | `keyboard` | `screen` | `led_bar` (slice 2; `none` until then).
- No colour, brightness or key is saved for bulbs. The bulb itself is the source of truth.
- An **older build** that rewrites `state.json` only knows `keyboard`/`led_bar`, so it drops `devices.bulbs`. Nothing breaks: a bulb that was remembered appears in the sidebar again after a new Connect. Documented, not migrated (single user).

## CLI

Targets: a name (case- and accent-insensitive: `escritorio` = `Escritório`), a device id, or `all`.
Columns: name padded to 12, then the result.

### `avell-storm-rgb bulb import <devices.json> [--json]`

```console
$ avell-storm-rgb bulb import ~/git/iot/devices.json
Quarto       eb1a2b3c4d5e6f70819201  unchanged
Escritório   eb1a2b3c4d5e6f70819202  unchanged
Sala         eb1a2b3c4d5e6f70819203  updated (key changed)
Tomada       eb1a2b3c4d5e6f70819204  skipped: not a bulb (category cz)
Imported 3 bulbs into /home/jilles/.config/avell-storm-rgb/tuya_devices.json
$ echo $?
0
```

```console
$ avell-storm-rgb bulb import ~/git/iot/devices.json --json
{"path": "/home/jilles/.config/avell-storm-rgb/tuya_devices.json", "results": [{"id": "eb1a2b3c4d5e6f70819201", "name": "Quarto", "status": "unchanged"}, {"id": "eb1a2b3c4d5e6f70819202", "name": "Escritório", "status": "unchanged"}, {"id": "eb1a2b3c4d5e6f70819203", "name": "Sala", "status": "updated", "reason": "key changed"}, {"id": "eb1a2b3c4d5e6f70819204", "name": "Tomada", "status": "skipped", "reason": "not a bulb (category cz)"}]}
```

`status`: `added` | `updated` | `unchanged` | `skipped`. `updated` reasons: `key changed`, `name changed`, `mac changed` (comma-joined).

### `avell-storm-rgb bulb list [--json]`

Reads every bulb once, in a `ThreadPoolExecutor` (one task per bulb, capped at 8 workers). The whole command has a **10 s deadline** (above the 6 s UDP discovery, QA defect D-2): a bulb that has not answered by then prints `offline`, so three offline bulbs still finish in ~10 s, not 3 × 10 s. Each task keeps the 5 s per-command timeout. Exit 0 when the inventory loaded, even if some bulbs are offline (offline is a normal `list` result).

```console
$ avell-storm-rgb bulb list
Inventory: /home/jilles/.config/avell-storm-rgb/tuya_devices.json
Quarto       eb1a2b3c4d5e6f70819201  online   192.168.0.21  protocol 3.3  key: set
Escritório   eb1a2b3c4d5e6f70819202  online   192.168.0.22  protocol 3.3  key: set
Sala         eb1a2b3c4d5e6f70819203  offline  —             protocol 3.3  key: set
$ echo $?
0
```

```console
$ avell-storm-rgb bulb list --json
{"path": "/home/jilles/.config/avell-storm-rgb/tuya_devices.json", "bulbs": [{"id": "eb1a2b3c4d5e6f70819201", "name": "Quarto", "online": true, "ip": "192.168.0.21", "protocol": "3.3", "key": "set"}, {"id": "eb1a2b3c4d5e6f70819202", "name": "Escritório", "online": true, "ip": "192.168.0.22", "protocol": "3.3", "key": "set"}, {"id": "eb1a2b3c4d5e6f70819203", "name": "Sala", "online": false, "ip": null, "protocol": "3.3", "key": "set"}]}
```

### `avell-storm-rgb bulb status [target] [--json]`

Default target `all`. Exit 1 if any target is offline.

```console
$ avell-storm-rgb bulb status
Quarto       on   white   brightness 100%  temperature 100%
Escritório   on   colour  #ff8800  brightness 100%
Sala         offline
$ echo $?
1
```

```console
$ avell-storm-rgb bulb status escritorio --json
{"results": [{"id": "eb1a2b3c4d5e6f70819202", "name": "Escritório", "online": true, "on": true, "mode": "colour", "brightness": 100, "temperature": null, "rgb": [255, 136, 0]}]}
```

Modes: `white`, `colour`, `scene`, `music` (the last two only when set from the phone). An offline entry is `{"id": …, "name": …, "online": false}`.

### Control verbs

| Verb | Effect | Output per bulb |
|------|--------|-----------------|
| `bulb on <target>` | Switch on (previous mode/colour) | `Sala         on` |
| `bulb off <target>` | Switch off | `Sala         off` |
| `bulb toggle <target>` | Read, then invert | `Quarto       off` (the new state) |
| `bulb bright <1-100> <target>` | Brightness of the current mode; switches on | `Escritório   brightness 40%` |
| `bulb white [--temp 0-100] <target>` | White mode (0 warm … 100 cold; keeps temperature if omitted); switches on | `Quarto       white 20%` / `Quarto       white` |
| `bulb color <R> <G> <B> <target>` | Colour mode, RGB 0–255; switches on | `Escritório   colour #ff8800` |

```console
$ avell-storm-rgb bulb white --temp 20 all
Quarto       white 20%
Escritório   white 20%
Sala         offline
$ echo $?
1
```

Every control verb accepts `--json`: `{"results": [{"id": …, "name": …, "status": "ok" | "offline" | "failed", "reason": …}]}`.

`bulb bright` reads the bulb's status first, on the same connection, because the target DPS depends on the mode (BR-11). `bulb white` without `--temp` sends mode-only (`{"20": true, "21": "white"}`) and keeps the temperature the bulb already has, so it needs no read. A read that fails turns the verb into an `offline` result; it never sends a guess.

### `avell-storm-rgb bulb remove <target>`

`all` is not accepted here.

```console
$ avell-storm-rgb bulb remove sala
Removed Sala (eb1a2b3c4d5e6f70819203) from /home/jilles/.config/avell-storm-rgb/tuya_devices.json
$ echo $?
0
```

### `avell-storm-rgb state show` — bulb lines (existing command, extended)

Names come from the inventory, which `state show` reads even when the `tuya` extra is not installed. Missing file → every bulb line shows `(not imported)`. Corrupt or unreadable file → the keyboard/LED bar lines still print, each bulb line reads `<id>  (inventory unreadable)`, and the command exits 3 after the inventory error. `--json` includes `devices.bulbs` exactly as stored (names are not needed).

```console
$ avell-storm-rgb state show
State file: /home/jilles/.config/avell-storm-rgb/state.json
keyboard  048d:600b  remembered  light on   solid #0078ff
led-bar   048d:7001  remembered  light on   wave · 2 colours · brightness 100 · speed 3
bulb      Escritório  eb1a2b3c4d5e6f70819202  remembered  follow keyboard
bulb      Sala        eb1a2b3c4d5e6f70819203  forgotten   follow none
```

`state show --json` includes `devices.bulbs` exactly as stored. `state restore` never contacts bulbs and does not list them.

### Unchanged

`keyboard …`, `led-bar …`, `device list`, `state restore` behave as before.

## Errors

| Condition | Surface | Exact output | Exit |
|-----------|---------|--------------|------|
| `tuya` extra not installed | any `bulb` verb | `error: bulb control needs the optional 'tuya' extra: uv sync --extra tuya` | 1 |
| No bulbs imported | `bulb list`, `bulb status` | `No bulbs imported. Import the devices.json written by 'python -m tinytuya wizard':`<br>`  avell-storm-rgb bulb import <path/to/devices.json>` | 0 |
| No bulbs imported | control verbs, `remove` | same message | 1 |
| Import file unreadable / not a list | `bulb import`, GUI Import | `error: not a tinytuya devices.json (<reason>): <path>` | 1 |
| Import file has no bulbs | `bulb import`, GUI Import | `No bulbs found in <path>` | 1 |
| Inventory file corrupt | any `bulb` verb, `state show`, GUI start | `error: bulb inventory is unreadable (<reason>): <path>` (GUI: Devices page error; bulb surfaces empty) | 3 |
| Unknown target | `bulb` verbs | `error: no bulb named 'cozinha'. Known: Quarto, Escritório, Sala` | 2 |
| Ambiguous name | `bulb` verbs | `error: 'luz' matches 2 bulbs; use the id: eb1a…11, eb1a…12` | 2 |
| `all` given to `remove` | `bulb remove` | argparse usage message | 2 |
| Out-of-range value | `bright`, `white --temp`, `color` | argparse usage message | 2 |
| Bulb not reachable | control/status | `<name padded>  offline` | 1 |
| Bulb not reachable | GUI Connect / Retry | `Escritório is not reachable on the network. Check that it is powered; discovery uses UDP 6666/6667.` | — |
| Wrong local key or protocol | CLI | `<name padded>  failed: local key or protocol rejected — re-import devices.json` | 1 |
| Wrong local key or protocol | GUI | `Escritório rejected the local key or protocol — re-import devices.json` | — |
| Other device error | CLI | `<name padded>  failed: <ExceptionType>: <message>` | 1 |
| Screen capture cancelled (slice 2) | GUI | `Screen capture cancelled — Escritório no longer follows the screen.` | — |
| Captured window closed (slice 2) | GUI | `Screen capture ended — bulbs following the screen were set to None.` | — |
| `state.json` bulbs invalid | `state show`, GUI start | existing message, e.g. `error: saved state is unreadable (bulbs.eb1a….follow must be one of none, keyboard, screen, led_bar, got 'music'): <path>` | 3 |

`<reason>` never includes a key or payload.
