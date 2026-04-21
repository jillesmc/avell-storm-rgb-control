# avell-storm-rgb-control

Unified **Python** tool for:

- **ITE 8291** (rev 0.03) per-key / firmware-effect **keyboard RGB** (USB `048d`, products `6004`, `6006`, `CE00`, `600B`).
- **ITE 8233** **LED bar** (USB `048d` `7000`/`7001` or product string containing `8233`).

The CLI is **`avell-storm-rgb`** with a **new, semantic** command tree (not compatible with legacy `ite8291r3-ctl` / `ledbar` names). Feature parity is tracked in [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md).

## Development

This repo uses **[uv](https://docs.astral.sh/uv/)** only for resolution and installs (**`uv.lock`** is the lockfile). Do not document `pip install -e .` as the primary workflow.

```bash
uv sync --group dev    # project + dev deps (pytest); same as: make sync
uv run pytest -m "not hardware" -q   # unit tests + QML smoke if PySide6 is installed (`uv sync --extra gui`)
uv run avell-storm-rgb device list      # CLI without activating .venv manually

# Convenience wrappers (call uv under the hood):
make sync
make test
make run ARGS='device list'

# Optional extras (same as uv `--extra`):
make sync-screen   # follow-screen (X11 + Wayland portal deps)
make sync-gui      # PySide6 desktop GUI (+ QML tests)
make sync-all      # screen + gui
make gui           # launch GUI (after sync-gui)
```

Optional **follow screen** mode (`[screen]` extra):

- **X11:** `python-xlib` + Pillow — samples the root window (optional region).
- **Wayland:** Pillow + **`pipewire-capture`** (uses **xdg-desktop-portal** ScreenCast and a **window picker**; not whole-desktop capture).

```bash
make sync-screen
# or: uv sync --group dev --extra screen
```

Desktop GUI (**PySide6** + **Qt Quick Controls 2** + **[Kirigami 6](https://develop.kde.org/docs/features/kirigami/)** QML) so colours and spacing follow **Breeze** on Plasma. **Kirigami is not installed via PyPI**: install it from your distro (e.g. Arch/CachyOS `kirigami`, Debian/Ubuntu `kirigami2` for Qt6) or run under a **KDE Flatpak** runtime that provides KF6 QML. The app prepends common Linux locations (`/usr/lib/qt6/qml`, `/usr/lib64/qt6/qml`, `/usr/share/qt6/qml`) because the PySide6 wheel’s own QML import path usually does not include Kirigami. Quick check:

```bash
test -d /usr/lib/qt6/qml/org/kde/kirigami && echo OK || echo "Install kirigami (Qt6)"
test -d /usr/lib/qt6/qml/org/kde/desktop && echo OK || echo "Install qqc2-breeze-style (Breeze for Qt Quick Controls)"
```

**If sliders, spin boxes and buttons look like plain Qt (thin track, “Fusion” look) while Kirigami cards/headings look fine:** Kirigami layouts and `AbstractCard` load correctly, but **Qt Quick Controls 2** are drawn by the active style. Install the **KDE Breeze** QQC2 style so the app can pick **`org.kde.desktop`** (same as system apps on Plasma):

| Distro (examples) | Typical packages |
|---------------------|------------------|
| **Arch / CachyOS** | `kirigami`, `qqc2-breeze-style`, `breeze` (icons/theme; optional but common on Plasma) |
| **Fedora KDE** | `kf6-kirigami`, `qqc2-breeze-style`, `breeze` |
| **Debian / Ubuntu** | `kirigami2`, `qqc2-breeze-style`, `breeze` (Qt6 package names may include `6` — search `qqc2` / `kirigami` in your repo) |

Then confirm the folder exists: `/usr/lib/qt6/qml/org/kde/desktop`. Restart the app (clear `QT_QUICK_CONTROLS_STYLE` unless you set it on purpose).

On **Plasma**, sliders and buttons match Dolphin when the **`org.kde.desktop`** QML module is present (Arch/CachyOS: **`qqc2-breeze-style`**; some distros bundle it with **`breeze`**). The app selects **`org.kde.desktop`** automatically if that folder exists; otherwise it falls back to **`Fusion`** (neutral, bundled with Qt—no purple Material accents). **PySide6 uses a bundled Qt:** the GUI entrypoint prepends system **`QML_IMPORT_PATH`** (and **`QT_PLUGIN_PATH`**) so `QQuickStyle` can resolve Breeze the same way as native KDE apps—without this, controls may look generic even when `/usr/lib/qt6/qml/org/kde/desktop` exists. Respect session **`QT_QUICK_CONTROLS_STYLE`** if already set. **`AVELL_RGB_QQC2_STYLE`** forces a style for debugging. Extra roots can still be appended via **`QML_IMPORT_PATH`** (path-separated).

**Close to tray:** closing the window hides it when the option in **About** is enabled; use the tray menu **Quit** (or **Quit application** in About) to exit. Requires a working system tray.

**Auto-connect:** After startup USB scan, the app can connect the first matching keyboard and LED bar automatically (default on). Disable in **About → Settings** if you prefer **Devices** manual connect. **Keyboard** / **LED bar** tabs only show while that device is connected in the app.

```bash
make sync-gui && make gui
# or: uv sync --extra gui && uv run avell-storm-rgb-gui
```

**Logs (stderr):** every failed USB/background task is logged. Use **`--verbose`** / **`--debug`** (or environment **`AVELL_STORM_RGB_LOG=debug`**) for **DEBUG** level and **full tracebacks** on failures.

**Follow-screen (`[screen]` extra):** on **X11**, uses `Xlib` root capture ( **`BadMatch`** often means XWayland, invalid region, or similar). On **Wayland**, uses **portal + PipeWire** via `pipewire-capture`: you must **pick a window** in the system dialog; colours follow that window. Requires a working **xdg-desktop-portal** backend (e.g. **xdg-desktop-portal-kde** on Plasma) and **PipeWire**.

**Wayland smoke (manual):** after `uv sync --extra screen`, on a Wayland Plasma session run `avell-storm-rgb keyboard follow-screen --fullscreen`, accept the portal prompt, choose a window, confirm key colours track it; **Ctrl+C** to stop.

**GUI:** follow-screen and “loop forever” animation run **without** blocking the global USB busy overlay so you can use **Stop follow / animation** to end capture and clear the portal screencast indicator.

## Usage (overview)

After `uv sync --group dev`, invoke the CLI with `uv run avell-storm-rgb …` (or `make run ARGS='…'`). Examples below use the bare command name for brevity.

```bash
avell-storm-rgb device list [--kind all|keyboard|led-bar]

avell-storm-rgb keyboard [--debug] [--device BUS/ADDR] <subcommand> ...
avell-storm-rgb led-bar <subcommand> ...
```

### Keyboard examples

```bash
avell-storm-rgb keyboard power off
avell-storm-rgb keyboard brightness set 25
avell-storm-rgb keyboard effect apply wave -s 0 --direction up -b 40
avell-storm-rgb keyboard solid-color --name white -b 10
avell-storm-rgb keyboard solid-color --rgb 255,45,23
avell-storm-rgb keyboard palette restore
avell-storm-rgb keyboard palette random
avell-storm-rgb keyboard palette set-slot 3 '255,13,14'
avell-storm-rgb keyboard demo-test-pattern
avell-storm-rgb keyboard freeze-animation
avell-storm-rgb keyboard follow-screen --fullscreen    # X11: full screen; Wayland: window picker
avell-storm-rgb keyboard play-animation --file path/to/script --loop 3
avell-storm-rgb keyboard play-animation --file path/to/script --forever
avell-storm-rgb keyboard inspect --fw-version --brightness --power
```

Animation DSL lines: `pos ROW COL r,g,b`, `apply`, `wait SEC`, `clear`, `brightness N`, `shift DROW DCOL`, `/*` `*/` comments (examples in [assets/animations/](assets/animations/); formato herdeiro do [ite8291r3-ctl](https://github.com/pobrn/ite8291r3-ctl)).

### LED bar examples

```bash
avell-storm-rgb led-bar power on
avell-storm-rgb led-bar power off
avell-storm-rgb led-bar color red
avell-storm-rgb led-bar color '#ff5500'
avell-storm-rgb led-bar palette rainbow --with-effect wave
avell-storm-rgb led-bar effect breathing
avell-storm-rgb led-bar brightness 75 --with-effect static
avell-storm-rgb led-bar speed 5 --with-effect breathing
avell-storm-rgb led-bar inspect
```

## USB permissions (udev)

Accessing USB devices usually requires **root** or **udev** rules. This is **not** installed by this repo automatically; add rules when you package or configure the machine.

**Keyboard (example — adjust `idProduct` for your device):**

```
SUBSYSTEMS=="usb", ATTRS{idVendor}=="048d", ATTRS{idProduct}=="ce00", MODE="0666"
```

**LED bar (from upstream README):**

```
SUBSYSTEM=="usb", ATTR{idVendor}=="048d", ATTR{idProduct}=="7000", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="048d", ATTR{idProduct}=="7001", MODE="0666"
```

Then `udevadm control --reload-rules && udevadm trigger` (or replug).

## Architecture (for maintenance / future GUI)

Python package under **`src/avell_storm_rgb/`**:

- **`domain/`** — parsing, pure helpers (no USB).
- **`ports/protocols.py`** — `Protocol` types for keyboard / LED bar drivers (use fakes in tests).
- **`application/`** — `device_facade.open_keyboard`, `open_led_bar`, `describe_*` (stable entry points for CLI and a future GUI). **Run USB calls on one thread** or queue them from Qt.
- **`infrastructure/usb/`** — **wire-accurate** `pyusb` code (feature reports, endpoints, byte order). Do not change payloads without characterization tests or hardware proof.
- **`adapters/cli/`** — argparse only.

## Repository layout and Cursor

- **CLI (current):** `src/avell_storm_rgb/` as above; **`requires-python >=3.10`** (see `pyproject.toml`).
- **Desktop app (planned, optional):** a separate tree **`src/app/`** (PySide6 + QML) may be added later; it is **not** required to build and run the CLI.
- **Agent rules:** [.cursor/rules/repo-context.mdc](.cursor/rules/repo-context.mdc) describes what exists vs. what is planned; **[Project skills](.cursor/skills/)** hold workflows (QML, refactors, module patterns). When rules conflict with `pyproject`/disk, **trust `pyproject` and repo-context**.

## Licenses and credits

This project is licensed under the **GNU General Public License v2.0 or later** — see [LICENSE](LICENSE). It **aggregates** code informed by:

| Upstream | License | Link |
|----------|---------|------|
| ite8291r3-ctl | GPL-2.0 | https://github.com/pobrn/ite8291r3-ctl |
| ite8233-ledbar (MIT, vários forks) | MIT | parsing/protocolo espelhado em `src/avell_storm_rgb/`; ver NOTICE |

See [NOTICE](NOTICE) for attribution notes. **GPLv2** applies to the combined work you distribute; **MIT** components remain usable under GPL-compatible terms when combined this way — for commercial use, seek proper legal review.

## GUI (planned)

A future **PySide6 + QML** app under **`src/app/`** (see `.cursor/rules/pyside6-qml-desktop.mdc` when that tree exists) should call the same **`application.device_facade`** entry points from a **worker thread or command queue**; do not drive USB from QML directly. Dependencies for that app will be opt-in extras managed with **uv** (e.g. `uv sync --extra …`) once defined in `pyproject.toml`.
