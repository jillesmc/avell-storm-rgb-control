🇺🇸 English · [🇧🇷 Português](DEVELOPMENT.pt-BR.md)

# Development

⏱️ **Reading time:** ~6 min

> **TL;DR**
> - **`uv` only** (lockfile `uv.lock`). `make` targets are thin wrappers. Don't document `pip install`.
> - `make sync-all && make test` gives you everything that runs without hardware.
> - The bottom of this page has **recipes** for common changes. Follow them step by step.

**Read this if…** you want to set up, run, test or extend the project.

---

## 🛠️ Prerequisites

| Need | For | Check |
|------|-----|-------|
| Linux + **libusb** | everything | — |
| **Python ≥ 3.10** (`.python-version` pins 3.12) | everything | `uv python list` |
| **[uv](https://docs.astral.sh/uv/)** | install, run, test | `uv --version` |
| **udev rule** or root | talking to the devices | `avell-storm-rgb device list` shows them |
| **Kirigami 6** (+ `qqc2-breeze-style`) from the distro | GUI | `test -d /usr/lib/qt6/qml/org/kde/kirigami` |
| X11, **or** Wayland + xdg-desktop-portal + PipeWire | follow-screen | — |

## 🛠️ Setup and run

| Command | Does |
|---------|------|
| `make sync` | `uv sync --group dev` — CLI + pytest |
| `make sync-gui` | + extra `gui` (PySide6) |
| `make sync-screen` | + extra `screen` (Xlib, Pillow, pipewire-capture, numpy) |
| `make sync-all` | + both extras |
| `make run ARGS='device list'` | Run the CLI |
| `make gui` | Run the GUI |
| `make test` | `pytest -m "not hardware"` |
| `make test-all` | Every test, including `@hardware` |

**udev rules** (save as `/etc/udev/rules.d/99-avell-rgb.rules`, then `udevadm control --reload-rules && udevadm trigger`):

```text
SUBSYSTEMS=="usb", ATTRS{idVendor}=="048d", ATTRS{idProduct}=="ce00", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="048d", ATTR{idProduct}=="7000", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="048d", ATTR{idProduct}=="7001", MODE="0666"
```

> [!TIP]
> Adjust the keyboard `idProduct` to yours (`6004`, `6006`, `ce00` or `600b`). `lsusb | grep 048d` shows it.

## 🛠️ Tests

| File | Covers |
|------|--------|
| `test_anim_dsl.py`, `test_ledbar_domain.py`, `test_per_key_grid_mapping.py` | Pure domain logic |
| `test_ledbar_payload.py` | LED bar effect bytes (**characterisation**) |
| `test_protocols.py` | Drivers match the `ports` protocols |
| `test_cli_help.py` | CLI parser builds and `--help` works |
| `test_screen_follow_frame.py` | Frame → 16 × 6 colour map (needs Pillow) |
| `test_usb_worker.py` | Worker signals, busy / no-busy, failures |
| `test_device_state.py`, `test_device_facade_usb_id.py` | Saved state: store, validation, restore; open by USB id |
| `test_keyboard_backend_light.py`, `test_led_bar_backend_light.py` | Backends with fake drivers: saved looks, light switch |
| `test_keyboard_effect_supports.py` | `effectSupports` matrix |
| `test_app_facade_memory.py`, `test_app_restore_integration.py` | Remember / forget, startup restore, migration (real worker, fake USB) |
| `test_cli_state.py` | `state show` / `state restore` transcripts |
| `test_gui_remembered_devices.py` | Sidebar entries, light switch, unavailable page |
| `test_gui_smoke.py`, `test_gui_pages.py`, `test_gui_shell.py` | QML loads; `objectName` contracts |

- GUI tests run **offscreen** (`QT_QPA_PLATFORM=offscreen`, set in `tests/gui_helpers.py`).
- Most of them **skip** when PySide6 or Kirigami is missing. A skip is not a regression.

> [!WARNING]
> `tests/test_gui_pages.py` imports PySide6 **before** its `importorskip`. Without the `gui` extra, collection **errors** instead of skipping. Run `make sync-gui` (or `sync-all`) before `make test`.

## 🛠️ Environment variables and flags

| Name | Effect |
|------|--------|
| `--verbose` / `--debug` / `-v` (GUI) | DEBUG logging + full tracebacks for failed USB tasks |
| `AVELL_STORM_RGB_LOG=debug` | Same as above, through the environment |
| `AVELL_DEBUG_FIRMWARE_UI=1` | Logs firmware-tab churn (apply requests, layout width ticks) |
| `AVELL_RGB_QQC2_STYLE=<style>` | Forces a Qt Quick Controls style (debugging) |
| `QT_QUICK_CONTROLS_STYLE` | Respected when set by the session |
| `QML_IMPORT_PATH`, `QT_PLUGIN_PATH` | Extra roots; system Qt6 paths are prepended automatically |
| `keyboard --debug` (CLI) | Prints every USB packet to stderr |
| `WAYLAND_DISPLAY` / `XDG_SESSION_TYPE` | Decide X11 vs Wayland follow-screen |

## 🛠️ Recipes

### Add a keyboard firmware effect

1. Add a builder to `KEYBOARD_EFFECTS` in `src/avell_storm_rgb/infrastructure/usb/ite8291_usb.py:102` (effect id + supported parameters + defaults).
2. Extend `tests/test_keyboard_effect_supports.py`. The supported-parameter table (`KEYBOARD_EFFECT_PARAMS`) is derived from the builder.
4. Update [FEATURE_MATRIX](FEATURE_MATRIX.md) and [DEVICE_FEATURES_DEEP_DIVE](DEVICE_FEATURES_DEEP_DIVE.md) (both languages).

The CLI `choices` and the GUI list (`App.keyboardEffectNames`) pick it up automatically.

### Add an LED bar effect

1. Add `name: code` to `LED_BAR_EFFECT_CODES` in `src/avell_storm_rgb/infrastructure/usb/ite8233_usb.py:19`.
2. Update the docs, as in the keyboard recipe. The CLI and GUI pick it up automatically.

### Add a CLI subcommand

1. Write `_cmd_<group>_<name>(args) -> int` in `src/avell_storm_rgb/adapters/cli/main.py`. Open devices through `application.device_facade`.
2. Register it in `_build_parser()` with `.set_defaults(_handler=...)`.
3. Add a `--help` check in `tests/test_cli_help.py`.
4. Update the root README usage and FEATURE_MATRIX.

### Add a GUI action (button → USB)

1. In the backend (`keyboard_backend.py` / `led_bar_backend.py`), add a `@Slot` that clamps its inputs and wraps the USB work in `def task():`.
2. Call `self._worker.submit(task)`. Use `show_busy=False` **only** for long tasks that the user can stop.
3. Return results through a `Signal`. Use a `QueuedConnection` if you mutate backend state from the task.
4. **If it applies a look**, emit `persistUpdate` **after** the driver call succeeded, so it becomes the saved look. Never write `state.json` yourself.
5. Call it from QML as `App.keyboard.<slot>(...)`. **Never** touch USB from QML.
6. Add a backend test with the fakes in `tests/backend_fakes.py` (see `test_*_backend_light.py`).

### Add a QML page or tab

1. Create `src/app/ui/pages/<Name>.qml` and register it in `src/app/ui/pages/qmldir`.
2. Add it to the `StackLayout` and navigation in `src/app/ui/main.qml`.
3. Give important nodes a stable `objectName`. Add it to `tests/test_gui_pages.py` and/or `test_gui_shell.py`.
4. Follow [`src/app/ui/AGENTS.md`](../src/app/ui/AGENTS.md) (Kirigami-first, theme colours, HIG).

### Change a USB payload

> [!WARNING]
> Only with **hardware proof** or a **characterisation test** (like `tests/test_ledbar_payload.py`). The bytes come from upstream projects and are easy to break silently.

## 🛠️ Debugging tips

- **Device not found** → check udev rules, `lsusb | grep 048d`, and that the keyboard reports rev `0.03`.
- **GUI looks like plain Qt** → install `qqc2-breeze-style`; check `/usr/lib/qt6/qml/org/kde/desktop`.
- **QML fails to load** → install Kirigami 6; the app prints a hint and exits 1.
- **Lights not restored** → `avell-storm-rgb state show`. A broken file is moved to `state.json.invalid` and reported on the Devices page.
- **X11 `BadMatch`** in follow-screen → XWayland or a region outside the screen.
- **GUI seems frozen on USB** → a follow-screen or looping animation is probably running. Press **Stop**.
