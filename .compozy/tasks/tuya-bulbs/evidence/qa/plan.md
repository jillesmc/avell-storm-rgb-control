# Delivery QA plan — Tuya bulbs

Owner of execution: task_11. Planned in task_10 (2026-11-02). No bulb command was sent while planning.

## Hardware gate

> **No bulb command runs before the user's explicit go-ahead for this execution.** M-1–M-7 change real
> house lights. The go-ahead, the bulbs involved and the time are recorded in `report.md` before the first
> M-check. Automated checks (Q-1–Q-6) never touch real bulbs: they use `FakeBulb`, temp `XDG_CONFIG_HOME`
> and the fictional fixture.

**Safety / rollback for every M-check:** start from the bulb's current state (noted in the report); after the
check, restore it with the Smart Life app or the wall switch; never leave a bulb following a source; never
paste a real key or real home IP into evidence (use the bulb name only).

## Environment matrix

| Env | How | Used by |
|-----|-----|---------|
| E-full | `uv sync --extra gui --extra screen --extra tuya`; GUI tests with `uv run --with "PySide6==6.12.0"` (distro Kirigami is Qt 6.12, venv PySide6 is 6.11 — see `memory/MEMORY.md`) | Q-1, Q-2 |
| E-noextra | throwaway venv without `tuya` (`uv run --no-extra tuya` / temp copy) | Q-3, Q-4 |
| E-stock | the repo venv as locked (PySide6 6.11) | Q-2b (records the known Qt-mismatch failures) |
| Session | `echo $XDG_SESSION_TYPE` recorded; X11 only if a session is available | M-7 |
| Bulbs | Quarto, Escritório, Sala (names only); online/offline noted per check | M-1–M-7 |

## Checks

Evidence root: `.compozy/tasks/tuya-bulbs/evidence/qa/`. One file per check: command, environment,
expected, actual, pass/fail, and any log/screenshot.

| ID | Check | Action | Expected | Evidence | Go-ahead |
|----|-------|--------|----------|----------|----------|
| Q-1 | UT-071 cross-surface privacy | Author `tests/test_bulb_privacy_cross_surface.py`; run it in E-full | Sentinel key absent from CLI human/JSON (`list`, `status`, `import`), `state show`, model roles, `bulb(id)`, DEBUG logs; tinytuya logger pinned to WARNING; `set_debug` never called | `q1-ut071.md` | no |
| Q-2 | Full suite, all extras | `uv run --with "PySide6==6.12.0" pytest -q -m "not hardware"` (E-full) | 0 failures, 0 GUI skips | `q2-full-suite.md` | no |
| Q-2b | Full suite, stock venv | `make test` (E-stock) | Only the 5 known `test_gui_pages.py` Qt-mismatch failures | `q2-full-suite.md` | no |
| Q-3 | No-extra install path | E-noextra: `python -c "import avell_storm_rgb"`; `avell-storm-rgb -h`; `avell-storm-rgb bulb list` | Package imports; help lists `bulb`; verb prints the install hint, exit 1 | `q3-no-extra.md` | no |
| Q-4 | No-extra GUI shell | E2E-026 (`tests/test_gui_bulbs.py::test_e2e026…`) in E-full with `tuya_available` false | No `bulbListPanel`; sidebar = Devices only | `q4-no-extra-gui.md` | no |
| Q-5 | Corrupt inventory `state show` | E2E-016 test + one manual run with a temp `XDG_CONFIG_HOME` containing `{` as inventory | Device lines, `(inventory unreadable)` per bulb, error line, exit 3 | `q5-corrupt-inventory.md` | no |
| Q-6 | OQ-2 bulb icon | `ls /usr/share/icons/breeze*/**/lightbulb*`; GUI sidebar look | Icon exists, or fallback `preferences-desktop-color` renders | `q6-oq2-icon.md` | no |
| M-1 | Status matches Smart Life | `avell-storm-rgb bulb status` | Same on/off, mode, brightness/colour as the phone | `m1-status.md` | **yes** |
| M-2 | Restart leaves bulb unchanged | GUI Connect Escritório; quit; reopen (autostart) with bulb off | Bulb stays off; page shows real state | `m2-restart.md` | **yes** |
| M-3 | Controls | Drag brightness; set temperature; pick colour | Smooth, ≤ 1 command per 200 ms pause; values apply | `m3-controls.md` | **yes** |
| M-4 | Wall switch | Wall off → wait ≤ 30 s → back on → Retry | "Unavailable" then normal | `m4-wall-switch.md` | **yes** |
| M-5 | OQ-1: push to an off bulb | Escritório **off**; one `push_colour` through the adapter | Record on/off. Turns on → keep BR-12 gating, note in `docs/BULBS*`. Stays off → close OQ-1 | `m5-oq1.md` | **yes** |
| M-6 | Follow keyboard | Follow Keyboard + keyboard animation | Tracks without visible lag > ~250 ms or flicker | `m6-follow-keyboard.md` | **yes** |
| M-7 | Follow screen, one picker | Keyboard follow-screen + bulb Follow Screen on Wayland; X11 too if available | One portal picker; stopping the keyboard keeps the bulb following; record session(s) tested | `m7-follow-screen.md` | **yes** |

## Cross-check

- `_tests.md` manual checklist: M-1…M-7 each appear once above.
- UT-071, both full-suite runs, the no-extra path and the corrupt-inventory path each appear once (Q-1–Q-5).
- OQ-1 → M-5; OQ-2 → Q-6. Known Risks: follow turning a bulb on (M-5), single local connection (documented in `docs/BULBS`),
  firewall (error text checked by `test_bulb_worker.py`), follow-screen regression (UT-099/100 + M-7), flicker (M-6).
- `_review.md` resolutions are not re-opened.
