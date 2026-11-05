🇺🇸 English · [🇧🇷 Português](BULBS.pt-BR.md)

# Tuya smart bulbs

⏱️ **Reading time:** ~6 min

> **TL;DR**
> - Optional: `uv sync --extra tuya` (plus `--extra gui` for the app). Without it, nothing changes.
> - Import the `devices.json` from the tinytuya wizard **once**; after that everything is **local** (LAN, no cloud).
> - Opening the app **never changes** a bulb, and local keys are **never shown**.

**Read this if…** you want to control Tuya bulbs from this app or its CLI, or you are changing bulb code.

---

## 🛠️ Set up (once)

| Step | Command / action |
|------|------------------|
| 1. Get local keys (outside the app, uses the Tuya cloud once) | `python -m tinytuya wizard` → writes `devices.json` |
| 2. Install bulb support | `uv sync --extra gui --extra tuya` |
| 3. Import | CLI: `uv run avell-storm-rgb bulb import ~/path/devices.json` · GUI: **Devices → Smart bulbs → Import Tuya devices…** |
| 4. Connect (GUI) | Click **Connect** on a bulb → it appears in the sidebar with a light switch |

Import keeps only light entries (`category: dj`) that have a local key. Others are listed as skipped
(`no local key`, `not a bulb (category cz)`, `missing category`). Re-import updates by id and **never deletes**.

## 🧭 Files

| File | Written by | Holds |
|------|------------|-------|
| `~/.config/avell-storm-rgb/tuya_devices.json` (mode **0600**) | `bulb import`/`remove`, GUI Import/Remove, a bulb answering on a new IP | id, name, **local key**, MAC, protocol, last IP |
| `~/.config/avell-storm-rgb/state.json` → `devices.bulbs` | **only** the GUI (`AppFacade`) | `{"<id>": {"remembered": true, "follow": "keyboard"}}` |

> [!WARNING]
> `tuya_devices.json` contains the local keys. Do not share it. The keys never appear in `state.json`,
> logs, GUI text, CLI output (human or `--json`) or error messages; listings show `key: set`.

No colour or brightness is saved for bulbs: **the bulb is its own source of truth**.
`$XDG_CONFIG_HOME` replaces `~/.config` when set.

## 🛠️ CLI

Target = a name (case- and accent-insensitive: `escritorio` = `Escritório`), a device id, or `all`.

| Command | Effect | Exit |
|---------|--------|------|
| `bulb import <devices.json> [--json]` | Import/update the inventory | 0 · 1 bad file / no bulbs · 3 inventory unreadable |
| `bulb list [--json]` | Every bulb once, in parallel, 10 s deadline (`online`/`offline`, IP, `key: set`) | 0 |
| `bulb status [target] [--json]` | On/off, mode, brightness, temperature or colour | 1 if a target is offline |
| `bulb on\|off\|toggle <target>` | Switch on/off; `toggle` reads, then inverts | 1 if a target is offline/failed |
| `bulb bright <1-100> <target>` | Brightness of the current mode; **switches on** | same |
| `bulb white [--temp 0-100] <target>` | White mode (0 warm … 100 cold); **switches on** | same |
| `bulb color <R> <G> <B> <target>` | Colour mode, RGB 0–255; **switches on** | same |
| `bulb remove <target>` | Delete the entry **and its key** (`all` not accepted) | 0 |
| `state show [--json]` | Also lists saved bulbs (`bulb  Escritório  <id>  remembered  follow keyboard`) | 3 if the inventory is unreadable |

```console
$ uv run avell-storm-rgb bulb status
Quarto       on   white   brightness 100%  temperature 100%
Escritório   on   colour  #ff8800  brightness 100%
Sala         offline
```

Without the extra, every `bulb` verb prints
`error: bulb control needs the optional 'tuya' extra: uv sync --extra tuya` (exit 1). `state restore` never contacts bulbs.

## 🧭 GUI

| Where | What |
|-------|------|
| **Devices → Smart bulbs** | Import button, one row per bulb (`online · <ip>` / `offline`), **Connect** / **Disconnect**, **Remove** (asks first; deletes the key) |
| **Sidebar** | One entry per remembered bulb, sorted by name, with a light switch. Disabled until the first read; "Unavailable" when it can't be reached |
| **Bulb page** | Status line ("On · White · 192.168.0.22"), switch, brightness, white temperature, colour, mode, **Follow** |
| **Unavailable** | Reason + **Retry** / **Forget** (Forget keeps the key) |

Disconnect/Forget = stop remembering (key kept). Remove = delete the key. Bulb operations never show the busy overlay.

## 🧭 What the app does — and never does

| Rule | Detail |
|------|--------|
| **Start reads only** | At start, retry and refresh the app only **reads** bulbs. It never switches a light on at login |
| **Real state** | The page shows the last read or command result; "Reading…" before the first read |
| **Refresh** | At start, when the window is shown, when a page opens, and every **30 s** while visible. Nothing while hidden in the tray (except bulbs that follow, read every 5 s) |
| **Explicit commands switch on** | Brightness, white and colour switch the bulb on (like the Tuya app) |
| **Local only** | Tuya LAN protocol (3.3), TCP 6668; discovery on UDP 6666/6667; IP from memory → ARP → last IP → discovery |

## 🔁 Follow (keyboard, screen, LED bar)

On the bulb page, **Follow** = None / Keyboard / Screen / LED bar. Only sources available right now are listed.

| Source | Colour sent to the bulb |
|--------|-------------------------|
| **Keyboard** | Average of each solid/per-key/animation/follow-screen write the app sends to the keyboard. Firmware effects and keyboard off send nothing |
| **Screen** (`screen` extra) | Average of the screen capture. **One capture** is shared with keyboard follow-screen (one picker on Wayland) |
| **LED bar** | Static average of the applied palette, while the LED bar light is on |

- **Never switches a bulb on**: only colour is sent, and only while the last read says the bulb is on (unknown = off).
- **Rate:** at most 4 updates/s per bulb, only when a channel changed by ≥ 8.
- **One local connection** is held while following; other apps on your network can't control that bulb locally meanwhile.
- The choice is saved and resumes at the next start. Disconnect stops following but keeps the choice.
- Capture cancelled or window closed → screen followers go back to None, with a message.

## ⚠️ Errors you may see

| Situation | Message |
|-----------|---------|
| Bulb off the network | `Escritório is not reachable on the network. Check that it is powered; discovery uses UDP 6666/6667.` |
| Wrong key or protocol | `Escritório rejected the local key or protocol — re-import devices.json` |
| Key changed (for example after re-pairing the bulb) | `Escritório: unexpected reply from the bulb: its local key may have changed (re-pairing creates a new one); update devices.json and re-import it` |
| Inventory corrupt | `error: bulb inventory is unreadable (<reason>): <path>` |

Ids, keys, MACs and IPs on this page are fictional.

## Next

- Code layout and threads → [ARCHITECTURE](ARCHITECTURE.md#-tuya-bulbs)
- Step-by-step flows → [FLOWS](FLOWS.md#-9--tuya-bulbs)
- Tests without bulbs → [DEVELOPMENT](DEVELOPMENT.md#-tests)
