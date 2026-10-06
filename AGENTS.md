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

## Tooling

- **uv only:** `uv sync` (groups/extras from `pyproject.toml`), lockfile `uv.lock`, run with `uv run …`. `Makefile` just wraps uv.
  Never present `pip install` or Poetry as the workflow.
- **Python:** `requires-python >=3.10` (`.python-version` pins 3.12). Don't claim 3.12 is the minimum.
- **Tests:** pytest in `tests/`. Run `make test` (`-m "not hardware"`). GUI tests need `make sync-gui`.
  `pytest-qt` is not a dependency; don't add it without being asked.
- **Black / Ruff / mypy** are not configured. Don't require them.

## Hard rules

- **USB payloads** (`src/avell_storm_rgb/infrastructure/usb/`) are wire-accurate ports of upstream code.
  Don't change bytes, offsets or command order without hardware proof or a characterisation test.
- **GUI USB I/O** goes only through `UsbWorker.submit` (one background thread). Never call USB from QML or the GUI thread.
- **No new dependencies** without an explicit request. Add them with `uv add` (optional extras for GUI/screen).
- Tasks about **CLI / USB / `avell_storm_rgb`**: don't import PySide6 there.
  Tasks about **GUI / QML / `src/app/`**: follow the folder `AGENTS.md`.
- If these rules contradict `pyproject.toml` or the real tree on disk, trust `pyproject.toml` and the disk, and fix the rule.

## Documentation conventions

- Every Markdown doc is a **bilingual pair**: `NAME.md` (English) + `NAME.pt-BR.md` (Brazilian Portuguese), side by side.
  **Update both in the same change.** Exceptions (English only): `AGENTS.md`, `CLAUDE.md`, `LICENSE`, `NOTICE`.
- ADHD-friendly style: language link, ⏱️ reading time, TL;DR (≤ 3 bullets), "Read this if…", short sections,
  tables and lists over prose, GitHub callouts, small Mermaid diagrams (≤ ~12 nodes), files ≤ ~250 lines.
  Full rules: [`docs/README.md`](docs/README.md).
- When behaviour changes, update the docs listed in the "Keep docs in sync" table of [`docs/README.md`](docs/README.md).
