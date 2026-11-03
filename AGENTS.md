# AGENTS.md — repository rules

Source of truth for agents working in this repo. Folder-specific rules live in
[`src/app/AGENTS.md`](src/app/AGENTS.md) (GUI Python) and
[`src/app/ui/AGENTS.md`](src/app/ui/AGENTS.md) (QML). `CLAUDE.md` files only import these.

## Read first

- Map of the docs: [`docs/README.md`](docs/README.md)
- Architecture, threading, known debts: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Step-by-step flows: [`docs/FLOWS.md`](docs/FLOWS.md)
- Setup, tests, env vars, recipes: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)
- Terms: [`docs/GLOSSARY.md`](docs/GLOSSARY.md)

## What exists

- **`src/avell_storm_rgb/`** — core + CLI (`avell-storm-rgb`), USB control of the ITE 8291 keyboard and ITE 8233 LED bar.
  Layers: `domain/` (pure), `ports/`, `application/`, `infrastructure/usb/` (wire protocol), `adapters/cli/`.
- **`src/app/`** — PySide6 + QML (Kirigami) desktop GUI (`avell-storm-rgb-gui`). Depends on the core; the core never imports `app`.
- **Tuya smart bulbs** (optional extra `tuya`): `domain/bulb_color.py`, `application/bulb_inventory.py`, `application/bulb_facade.py`,
  `infrastructure/tuya/bulb.py`, `adapters/cli/bulb_cli.py`; GUI in `src/app/` (`BulbWorker`, `BulbsBackend`, `BulbFollower`). See [`docs/BULBS.md`](docs/BULBS.md).

## Tooling

- **uv only:** `uv sync` (groups/extras from `pyproject.toml`), lockfile `uv.lock`, run with `uv run …`. `Makefile` just wraps uv.
  Never present `pip install` or Poetry as the workflow.
- **Python:** `requires-python >=3.12` (`.python-version` pins 3.12). PySide6 6.12 (needed to match the distro Qt for Kirigami) aborts at exit on 3.10/3.11.
- **Tests:** pytest in `tests/`. Run `make test` (`-m "not hardware"`). GUI tests need `make sync-gui`.
  `pytest-qt` is not a dependency; don't add it without being asked.
- **Black / Ruff / mypy** are not configured. Don't require them.

## Hard rules

- **USB payloads** (`src/avell_storm_rgb/infrastructure/usb/`) are wire-accurate ports of upstream code.
  Don't change bytes, offsets or command order without hardware proof or a characterisation test.
- **GUI USB I/O** goes only through `UsbWorker.submit` (one background thread). Never call USB from QML or the GUI thread.
- **Saved device state** (`state.json`, `avell_storm_rgb.application.device_state`) has **one writer**: `AppFacade`, on the GUI thread.
  The CLI and restore functions only read it. `device_state` must stay Qt-free.
- **Bulbs:** only `infrastructure/tuya/bulb.py` imports `tinytuya`; everything else gates on `tuya_available()`.
  Local keys live only in `tuya_devices.json` (0600) and never reach `state.json`, logs, GUI text, CLI output or errors.
  `devices.bulbs` in `state.json` has the same single writer (`AppFacade`). Startup/refresh only **read** bulbs; nothing turns a light on unasked.
  Tests and docs use only the fictional ids/keys/IPs from `tests/fixtures/tinytuya_devices.json`; never touch real bulbs from tests.
- Tests must never touch the user's real config: `tests/conftest.py` points `XDG_CONFIG_HOME` at a temp dir; keep it.
- **No new dependencies** without an explicit request. Add them with `uv add` (optional extras for GUI/screen).
- Tasks about **CLI / USB / `avell_storm_rgb`**: don't import PySide6 there.
  Tasks about **GUI / QML / `src/app/`**: follow the folder `AGENTS.md`.
- If these rules contradict `pyproject.toml` or the real tree on disk, trust `pyproject.toml` and the disk, and fix the rule.

## Documentation conventions

- Every Markdown doc is a **bilingual pair**: `NAME.md` (English) + `NAME.pt-BR.md` (Brazilian Portuguese), side by side.
  **Update both in the same change.** Exceptions (English only): `AGENTS.md`, `CLAUDE.md`, `LICENSE`, `NOTICE`,
  and spec-cycle artifacts under `.compozy/tasks/` (specs, stories, tests, ADRs, task files).
- ADHD-friendly style: language link, ⏱️ reading time, TL;DR (≤ 3 bullets), "Read this if…", short sections,
  tables and lists over prose, GitHub callouts, small Mermaid diagrams (≤ ~12 nodes), files ≤ ~250 lines.
  Full rules: [`docs/README.md`](docs/README.md).
- When behaviour changes, update the docs listed in the "Keep docs in sync" table of [`docs/README.md`](docs/README.md).
