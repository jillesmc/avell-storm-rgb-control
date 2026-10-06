🇺🇸 English · [🇧🇷 Português](GLOSSARY.pt-BR.md)

# Glossary

⏱️ **Reading time:** lookup (≈ 1 min per section)

> **TL;DR**
> - One table per area: **Hardware**, **Keyboard**, **LED bar**, **GUI internals**, **Tooling**.
> - Each term links to where it lives in the code.
> - Terms are kept **in English** in both languages, because that is how they appear in the code.

**Read this if…** a word in another doc or in the code doesn't make sense.

---

## Hardware

| Term | Meaning | In code |
|------|---------|---------|
| **ITE 8291** | Keyboard RGB controller (rev 0.03). USB `048d:6004/6006/ce00/600b` | `infrastructure/usb/ite8291_usb.py` |
| **ITE 8233** | LED bar controller. USB `048d:7000/7001` or product name with `8233` | `infrastructure/usb/ite8233_usb.py` |
| **Control transfer** | Small (8-byte) USB command to the device. Used for almost every command | `_send_ctrl`, `_send` |
| **Row write** | 65-byte OUT transfer carrying one keyboard row of colours | `Ite8291UsbDevice._send_data` |
| **udev rule** | Linux rule that lets non-root users open the USB device | root README |

## Keyboard

| Term | Meaning | In code |
|------|---------|---------|
| **Firmware effect** | Animation that runs **inside** the controller (breathing, wave…) | `KEYBOARD_EFFECTS` |
| **Effect packet** | `[control, effect, speed, brightness, color, direction\|reactive, save]` | `_set_effect_impl` |
| **User mode** | Mode where software sets the colours (solid, per-key, animation, follow). Effect id `51` | `enable_user_mode` |
| **Palette slot** | One of **7** RGB colours stored in the controller (1–7) | `set_palette_color` |
| **Color index** | The `color` byte of an effect. **Not RGB**: slot 1–7, `8` = random, `0` = none | `KEYBOARD_PALETTE_SLOT_COLORS` |
| **Direction / reactive** | Two meanings of the **same byte**. An effect uses one or the other | `_EffectAttrs` |
| **Save** | Effect flag asking the controller to keep the effect | `save` kwarg |
| **Freeze** | Re-sends the current effect with speed `11` (experimental "pause") | `freeze()` |
| **Solid colour** | User mode with every key the same RGB | `set_color` |
| **Per-key / key grid** | Individual colour per LED cell in a **6 × 21** matrix | `set_key_colors` |
| **Key ID** | Semantic name of a physical key (`esc`, `space`, `kp_enter_top`…) mapped to a cell | `domain/per_key_grid.py` |
| **UI row vs device row** | GUI row 0 = top; device row 0 = bottom. `ui_row_to_device_row` flips them | `per_key_grid.py:182` |
| **Animation DSL** | Text script: `pos`, `apply`, `wait`, `clear`, `brightness`, `shift` | `domain/anim_dsl.py` |
| **Follow screen** | Samples the screen / a window at 16 × 6 and paints the keys | `application/screen_follow*.py` |
| **Portal / PipeWire** | Wayland's way to capture a window: the user picks it in a system dialog | `screen_follow_wayland.py` |

## LED bar

| Term | Meaning | In code |
|------|---------|---------|
| **LED bar palette** | List of up to **9** RGB colours **sent with each effect** (not stored slots) | `Ite8233UsbDevice.palette` |
| **Preset** | Named palette: `rainbow`, `fire`, `ice`, `forest` | `domain/ledbar_colors.py` |
| **Visual effect** | `static`, `breathing`, `wave`, `impact`, `raindrop` | `LED_BAR_EFFECT_CODES` |
| **Effect report** | `[0x08, 0x22, effect, speed, brightness, num_colors, 0, 0]` | `_send_effect` |
| **With-effect** | Brightness and speed are only sent **together with** an effect; the CLI flag `--with-effect` picks which one | CLI `led-bar brightness/speed` |

## GUI internals

| Term | Meaning | In code |
|------|---------|---------|
| **`App`** | The one Python object QML sees (`AppFacade`) | `ui/adapters/app_facade.py:37` |
| **Backend** | `KeyboardBackend` / `LedBarBackend`: QML-facing logic per device | `ui/adapters/*_backend.py` |
| **UsbWorker** | Single background thread that runs every USB task in order | `core/usb_worker.py:16` |
| **Task** | Local `def task():` closure a slot hands to `UsbWorker.submit` | backends |
| **Busy overlay / `show_busy`** | "USB operation in progress…" veil; `show_busy=False` skips it | `BusyOverlay.qml`, `AppState` |
| **Debounce** | 200 ms timer that merges rapid slider/control changes into one USB call | `QTimer` in backends, `Timer` in QML |
| **Brightness target** | `GLOBAL_ONLY` or `FIRMWARE_REAPPLY`: whether brightness also re-sends the effect | `_BrightnessTarget` |
| **Palette mirror** | Session copy of slot colours the GUI wrote (the device can't be read) | `_palette_mirror` |
| **Effect snapshot** | Effect bytes saved at power off, replayed at power on | `_last_effect_snapshot` |
| **Replay record** | LED bar's last action (`color`, `palette`, `effect`, `tune*`) for power-on replay | `_last_replay` |
| **Epoch** | Counter bumped to force QML to re-read (`deviceConnectionEpoch`, `keyGridEpoch`) | facade / backend |
| **Close to tray** | Closing the window hides it; quit from the tray | `ui/closeToTray` |
| **Auto-connect** | Connect the first keyboard and LED bar after the startup scan | `ui/autoConnectOnStartup` |

## Tooling

| Term | Meaning |
|------|---------|
| **uv** | Package / venv manager used for everything (`uv sync`, `uv run`) |
| **Extra** | Optional dependency set: `gui`, `screen` |
| **`hardware` marker** | Pytest marker for tests that need real devices (skipped by `make test`) |
| **Kirigami** | KDE's QML UI framework; installed from the distro, **not** PyPI |
| **QQC2 style / `org.kde.desktop`** | Breeze look for Qt Quick Controls; falls back to `Fusion` |
| **`objectName` contract** | Stable QML names that tests look up; renaming them breaks tests |
