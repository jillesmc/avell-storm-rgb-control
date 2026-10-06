🇺🇸 English · [🇧🇷 Português](README.pt-BR.md)

# avell-storm-rgb-control

⏱️ **Reading time:** ~5 min

> **TL;DR**
> - Controls the **RGB keyboard** (ITE 8291) and the **LED bar** (ITE 8233) of Avell Storm laptops on **Linux**, over USB.
> - Two ways to use it: the CLI **`avell-storm-rgb`** and the KDE/Plasma GUI **`avell-storm-rgb-gui`**.
> - Install with **uv**: `make sync-all`, then `make gui` or `make run ARGS='device list'`.

**Read this if…** you want to install and use the tool. For the docs map, see [docs/README](docs/README.md).

---

## 🧭 What you get

| Device | USB IDs | Highlights |
|--------|---------|------------|
| **Keyboard — ITE 8291** (rev 0.03) | `048d:6004`, `6006`, `ce00`, `600b` | 9 firmware effects, 7-slot palette, solid colour, **per-key** colours, animation scripts, **follow screen** |
| **LED bar — ITE 8233** | `048d:7000`, `7001`, or product name contains `8233` | 5 effects, static colour, palettes of up to 9 colours, brightness, speed |

- Full feature list → [docs/FEATURE_MATRIX](docs/FEATURE_MATRIX.md).
- How it works inside → [docs/ARCHITECTURE](docs/ARCHITECTURE.md).

> [!NOTE]
> The CLI command tree is **new and semantic**. It is **not** compatible with the legacy `ite8291r3-ctl` / `ledbar` commands.

## 🛠️ Install

This repo uses **[uv](https://docs.astral.sh/uv/)** only (`uv.lock` is the lockfile). `make` targets just call `uv`.

```bash
make sync          # CLI + pytest            (uv sync --group dev)
make sync-gui      # + desktop GUI (PySide6) (uv sync --group dev --extra gui)
make sync-screen   # + follow-screen deps    (uv sync --group dev --extra screen)
make sync-all      # everything
```

**USB permissions:** you need **root** or a **udev rule**. Ready-to-copy rules are in [docs/DEVELOPMENT](docs/DEVELOPMENT.md) (section *Setup and run*).

## 🛠️ Use the CLI

```bash
uv run avell-storm-rgb device list [--kind all|keyboard|led-bar]
uv run avell-storm-rgb keyboard [--debug] [--device BUS/ADDR] <subcommand> …
uv run avell-storm-rgb led-bar <subcommand> …
# or: make run ARGS='device list'
```

**Keyboard**

```bash
avell-storm-rgb keyboard power off
avell-storm-rgb keyboard brightness 25                  # 0–50
avell-storm-rgb keyboard effect wave -s 3 -d up -b 40   # speed 0–10, brightness 0–50
avell-storm-rgb keyboard effect aurora -r -c red        # -r (reactive) and -d (direction) are exclusive
avell-storm-rgb keyboard solid-color --name white -b 10
avell-storm-rgb keyboard solid-color --rgb 255,45,23
avell-storm-rgb keyboard palette restore
avell-storm-rgb keyboard palette random
avell-storm-rgb keyboard palette set-slot 3 255,13,14
avell-storm-rgb keyboard demo-test-pattern
avell-storm-rgb keyboard freeze-animation
avell-storm-rgb keyboard follow-screen --fullscreen     # X11: full screen · Wayland: window picker
avell-storm-rgb keyboard follow-screen --region 0,0,800,600   # X11 only
avell-storm-rgb keyboard play-animation --file path/to/script --loop 3
avell-storm-rgb keyboard play-animation --file path/to/script --forever
avell-storm-rgb keyboard inspect --fw-version --brightness --power
```

> [!WARNING]
> In `keyboard effect … -c NAME`, the colour is a **palette slot** (`red` = slot 1, `orange` = slot 2, …), not a fixed RGB colour. Change the slot with `palette set-slot` and the effect changes with it.

**Animation scripts:** `pos ROW COL r,g,b`, `apply`, `wait SEC`, `clear`, `brightness N`, `shift DROW DCOL`, `#` and `/* */` comments. Format and examples: [assets/animations/](assets/animations/README.md). Inherited from [ite8291r3-ctl](https://github.com/pobrn/ite8291r3-ctl).

**LED bar**

```bash
avell-storm-rgb led-bar power on
avell-storm-rgb led-bar power off
avell-storm-rgb led-bar color red
avell-storm-rgb led-bar color '#ff5500'
avell-storm-rgb led-bar palette rainbow --with-effect wave
avell-storm-rgb led-bar effect breathing
avell-storm-rgb led-bar brightness 75 --with-effect static    # 0–100
avell-storm-rgb led-bar speed 5 --with-effect breathing       # 1–10
avell-storm-rgb led-bar inspect
```

## 🛠️ Use the GUI

```bash
make sync-gui && make gui
# or: uv sync --extra gui && uv run avell-storm-rgb-gui
```

| Feature | Notes |
|---------|-------|
| **Auto-connect** | After the startup scan, connects the first keyboard and LED bar (on by default; **Settings**) |
| **Device tabs** | **Keyboard** / **LED bar** only show while that device is connected |
| **Close to tray** | Closing hides the window (option in **Settings**). Quit from the tray menu or **Settings → Quit application** |
| **Follow screen** | Runs without the busy overlay. **Stop** ends capture and clears the portal indicator. (A *forever* animation currently does show the overlay — [debt #7](docs/ARCHITECTURE.md)) |
| **Logs** | `--verbose` / `--debug`, or `AVELL_STORM_RGB_LOG=debug` → DEBUG + full tracebacks on stderr |

### ⚠️ GUI needs Kirigami from the distro

**Kirigami is not on PyPI.** Install it from your distro (or use a KDE Flatpak runtime). The app prepends `/usr/lib/qt6/qml`, `/usr/lib64/qt6/qml` and `/usr/share/qt6/qml`, because PySide6's bundled Qt does not search them.

```bash
test -d /usr/lib/qt6/qml/org/kde/kirigami && echo OK || echo "Install kirigami (Qt6)"
test -d /usr/lib/qt6/qml/org/kde/desktop  && echo OK || echo "Install qqc2-breeze-style"
```

| Distro | Packages |
|--------|----------|
| **Arch / CachyOS** | `kirigami`, `qqc2-breeze-style`, `breeze` |
| **Fedora KDE** | `kf6-kirigami`, `qqc2-breeze-style`, `breeze` |
| **Debian / Ubuntu** | `kirigami2`, `qqc2-breeze-style`, `breeze` (Qt6 names may include `6`) |

**Sliders and buttons look like plain Qt ("Fusion")?** Kirigami loaded, but the **Breeze Qt Quick Controls style** (`org.kde.desktop`) is missing. Install `qqc2-breeze-style` and restart.

- The app picks `org.kde.desktop` when present, otherwise `Fusion`.
- A session `QT_QUICK_CONTROLS_STYLE` is respected.
- `AVELL_RGB_QQC2_STYLE` forces a style (debugging).

### ⚠️ Follow-screen needs the `screen` extra

| Session | How it captures | Requirements |
|---------|-----------------|--------------|
| **X11** | `python-xlib` root window (optional region) | X11. `BadMatch` usually means XWayland or a region outside the screen |
| **Wayland** | **xdg-desktop-portal** ScreenCast + **PipeWire** (`pipewire-capture`) | You **pick a window**, not the whole desktop. Needs a portal backend (e.g. `xdg-desktop-portal-kde`) |

**Wayland smoke test:** `make sync-screen`, then `avell-storm-rgb keyboard follow-screen --fullscreen`. Accept the portal, pick a window and watch the keys follow it. Stop with `Ctrl+C`.

## 🏗️ Architecture in 30 seconds

| Path | Role |
|------|------|
| `src/avell_storm_rgb/domain/` | Pure logic: parsing, animation DSL, key layout |
| `src/avell_storm_rgb/application/` | Use cases: open devices, follow-screen |
| `src/avell_storm_rgb/infrastructure/usb/` | **Wire-accurate** USB drivers. Don't change bytes without hardware proof |
| `src/avell_storm_rgb/adapters/cli/` | `argparse` CLI |
| `src/app/` | PySide6 + QML GUI. All USB goes through **one worker thread** |

Details, diagrams and known debts → [docs/ARCHITECTURE](docs/ARCHITECTURE.md). Agents: start at [AGENTS.md](AGENTS.md).

## 🛠️ Development

`make test` runs the tests that need no hardware. Setup, env vars and recipes → [docs/DEVELOPMENT](docs/DEVELOPMENT.md).

## 🧭 Licences and credits

**GPL-2.0-or-later** — see [LICENSE](LICENSE). The project combines code informed by:

| Upstream | Licence | Link |
|----------|---------|------|
| ite8291r3-ctl | GPL-2.0 | https://github.com/pobrn/ite8291r3-ctl |
| ite8233-ledbar (MIT, several forks) | MIT | Parsing/protocol mirrored in `src/avell_storm_rgb/`; see NOTICE |

See [NOTICE](NOTICE) for attribution. GPLv2 applies to the combined work you distribute. The MIT parts stay usable under GPL-compatible terms. For commercial use, get a proper legal review.
