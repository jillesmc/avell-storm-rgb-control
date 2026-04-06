.PHONY: help sync sync-screen sync-gui sync-all lock test test-all run gui clean

UV := uv
CLI := avell-storm-rgb
GUI := avell-storm-rgb-gui

help:
	@echo "Targets:"
	@echo "  make sync         - uv sync --group dev (CLI + pytest)"
	@echo "  make sync-screen  - dev + extra screen (X11 follow-screen)"
	@echo "  make sync-gui     - dev + extra gui (PySide6 / desktop)"
	@echo "  make sync-all     - dev + screen + gui (full optional extras)"
	@echo "  make lock         - uv lock"
	@echo "  make test         - pytest excluding @hardware (QML smoke needs sync-gui)"
	@echo "  make test-all     - full pytest"
	@echo "  make run ARGS=... - run CLI (example: make run ARGS='device list')"
	@echo "  make gui          - run desktop GUI ($(GUI); install with make sync-gui)"

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

run:
	$(UV) run $(CLI) $(ARGS)

gui:
	$(UV) run $(GUI)

clean:
	rm -rf .pytest_cache build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
