.PHONY: help sync sync-screen sync-gui sync-all lock test test-all run gui clean

UV := uv
CLI := avell-storm-rgb
GUI := avell-storm-rgb-gui

help:
	@echo "Targets:"
	@echo "  make sync         - uv sync --group dev (CLI + pytest)"
	@echo "  make sync-screen  - dev + extra screen (follow-screen: X11 + Wayland)"
	@echo "  make sync-gui     - dev + extra gui (PySide6 / desktop)"
	@echo "  make sync-all     - dev + screen + gui (full optional extras)"
	@echo "  make lock         - uv lock"
	@echo "  make test         - pytest excluding @hardware (QML smoke needs sync-gui)"
	@echo "  make test-all     - full pytest"
	@echo "  make run ARGS=... - run CLI with the dev config (example: make run ARGS='device list')"
	@echo "  make gui          - run desktop GUI with the dev config (DEV_CONFIG=$(DEV_CONFIG))"

sync:
	@command -v $(UV) >/dev/null || (echo "uv not found"; exit 1)
	$(UV) sync --group dev

sync-screen:
	$(UV) sync --group dev --extra screen

sync-gui:
	$(UV) sync --group dev --extra gui

sync-all:
	$(UV) sync --group dev --extra screen --extra gui

lock:
	$(UV) lock

test:
	$(UV) run pytest -m "not hardware" -q

test-all:
	$(UV) run pytest -q

# Dev runs keep their own config, apart from the installed (production) app.
DEV_CONFIG ?= $(HOME)/.config/avell-storm-rgb-dev

run:
	AVELL_STORM_RGB_CONFIG_DIR=$(DEV_CONFIG) $(UV) run $(CLI) $(ARGS)

gui:
	AVELL_STORM_RGB_CONFIG_DIR=$(DEV_CONFIG) $(UV) run $(GUI)

clean:
	rm -rf .pytest_cache build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
