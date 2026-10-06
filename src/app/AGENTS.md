# AGENTS.md — `src/app/` (desktop GUI, Python side)

Applies to everything under `src/app/`. For `*.qml` files also follow [`ui/AGENTS.md`](ui/AGENTS.md),
which wins on QML component/theme questions. Repo-wide rules: [`/AGENTS.md`](../../AGENTS.md).
Architecture and flows: [`docs/ARCHITECTURE.md`](../../docs/ARCHITECTURE.md), [`docs/FLOWS.md`](../../docs/FLOWS.md).

## Stack

- **PySide6 only** (never PyQt). UI is **Qt Quick / QML**; Qt Widgets only where needed (the tray menu).
  Qt Designer / `pyside6-uic` are not used.
- Optional extra `gui` (`uv sync --extra gui`). Kirigami 6 comes from the distro, not PyPI.
- Entry point: `main.py` (`avell-storm-rgb-gui`). QML import paths and style: `qml_paths.py`.

## Layout

| Path | Put here |
|------|----------|
| `core/` | Non-UI logic used by the GUI (`UsbWorker`, device enumeration) |
| `ui/adapters/` | `QObject`s exposed to QML: `AppFacade` (`App`), `AppState`, `DeviceListModel`, `KeyboardBackend`, `LedBarBackend` |
| `ui/pages/`, `ui/components/` | QML (see `ui/AGENTS.md`) |

Device logic belongs in the core package (`src/avell_storm_rgb/`). Reuse `application` / `domain`; don't duplicate it here.

## Rules

- **USB only through `UsbWorker.submit(task)`.** A backend slot clamps inputs, wraps the USB call in `def task():`
  and submits it. Results go back through `Signal`s, using `Qt.QueuedConnection` when they mutate backend state.
- `show_busy=False` is only for long tasks the user can stop (follow-screen, animations). They hold the only
  USB thread, so stop them through the shared `threading.Event`.
- Expose to QML only what it needs: `Property` (+ `notify` signal), `Slot`, `Signal`. No business logic in QML/JS.
- Type hints on public APIs and on everything exposed to QML. Use `pathlib.Path`. No `import *`.
- Persist settings only through `QSettings` (keys under `ui/`).
- When adding a backend action, add a test with a fake driver (see `tests/test_*_power_replay.py`).

## Don't

- Add dependencies (PySide6 plugins, pytest-qt, themes) without an explicit request.
- Replace QML with another toolkit, or do sweeping refactors without a plan the user confirmed.
- Move or delete `src/avell_storm_rgb/` code to serve the GUI.
