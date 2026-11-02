---
status: completed
title: "Task 6: Bulb surfaces in Devices, the sidebar and a page"
type: frontend
complexity: high
---

# Task 6: Bulb surfaces in Devices, the sidebar and a page

## Overview

This task puts the bulb backend on screen and completes slice 1. After it, the owner opens Devices, imports the wizard file, clicks Connect on Escritório, gets a sidebar entry with a light switch, and controls brightness, white temperature and colour on a bulb page — without the app ever turning a light on at startup.

## Shippable Outcome

- **Outcome:** with the `tuya` extra, Devices shows a "Smart bulbs" section with Import, bulb rows (Connect/Disconnect/Remove) and the import summary; remembered bulbs appear in the sidebar with a model-driven light switch and an "Unavailable" subtitle; the bulb page at index 5 shows the real state, "Reading…" before the first read, and the unavailable panel with Retry/Forget. Without the extra, no bulb surface exists.
- **Verify in this task:** offscreen `main.qml` journeys through `tests/gui_helpers.py` with a `FakeBulb` factory and `XDG_CONFIG_HOME=tmp_path` (Tests below).
- **Integration verification:** task_11 runs the GUI journey once on the delivered package; no named visual reference exists, so there are no visual-contract rows.

## Requirements

- `_uiux.md` S1–S5 and S7; all object names from *Component plan* (`bulbListPanel`, `bulbImportButton`, `bulbRow_<id>`, `bulbRemoveDialog`, `sidebarBulbEntry`, `bulbLightSwitch`, `bulbPage`, `bulbBrightnessRow`, `bulbTemperatureRow`, `bulbColorWell`). Keep every existing `objectName`.
- Follow `src/app/ui/AGENTS.md`: Kirigami first, QQC2 second, custom only in `components/`; colours from `Kirigami.Theme`, spacing from `Kirigami.Units`, icons with a `fallback`.
- Truthful UI: unknown state renders as "Reading…" with disabled controls, never as off; unsupported surfaces are **absent**, not disabled.
- `importFile` receives a `QUrl`; call `toLocalFile()` in Python. QML must **not** strip `file://` (unlike the animation picker).
- Debounce brightness and colour at 200 ms (existing `KeyboardPage.qml` pattern), last value wins.
- No bulb operation shows the busy overlay; errors use the existing inline error.

### Six required `main.qml` edits

| Location | Change |
|----------|--------|
| `Switch.objectName` (`:328`) | `page === 5 ? "bulbLightSwitch" : …` (keep the 1/2 arms) |
| `Switch.checked` (`:334-338`) | `page === 5 ? model.lightOn : (page === 1 ? … : …)` |
| `Switch.enabled` (`:334-338`) | `page === 5 ? model.available && model.stateKnown : …` |
| `Switch.onToggled` (`:339-343`) | add `else if (page === 5) App.bulbs.setLightOn(model.bulbId, checked)` |
| `unavailableReasonForPage()` (`:115-121`, bound `:282`) | add `page === 5 ? (model.available ? "" : model.unavailableReason)` |
| `syncPrimarySidebarListIndex()` (`:60-70`) and the forgotten reset (`:107-110`) | track every entry with `page >= 1`; reset to page 0 when the selected bulb disappears (disconnect, forget, remove) |

- Sidebar order: Devices, Keyboard, LED bar, then remembered bulbs sorted by name. Rebuild on `App.bulbs.modelChanged`.
- `main.qml` reports `App.setWindowVisible(visible)` on `Window.visibleChanged`, including hides through `closeToTray`.
- `DeviceUnavailablePanel` gains an optional `forgetHint` property, defaulting to today's text; the bulb page passes "Stop reconnecting this bulb. Its key is kept."

## Subtasks

- [x] 6.1 `components/BulbListPanel.qml`: header, Import button, hint, rows, import summary.
- [x] 6.2 Import `FileDialog` and the Remove `PromptDialog`.
- [x] 6.3 Sidebar bulb entries plus the six `main.qml` edits.
- [x] 6.4 `pages/BulbPage.qml` at index 5: header, switch, brightness, temperature, colour, mode chip, reading/unavailable states.
- [x] 6.5 `DeviceUnavailablePanel.forgetHint` and the page wiring.
- [x] 6.6 Window-visibility reporting and the GUI journey suite.

## Implementation Details

### Relevant Files

- `src/app/ui/main.qml:60-70, 107-110, 115-121, 282, 309-318, 327-348, 584-604` — the six edits and the content stack.
- `src/app/ui/pages/DevicesPage.qml:23-48` — where the bulb section joins below the USB panel.
- `src/app/ui/components/DeviceListPanel.qml:19, 152-154, 161-176` — row, remembered copy and Connect/Disconnect button pattern to compose (do not fork the component).
- `src/app/ui/components/DeviceUnavailablePanel.qml:1-50` — Retry/Forget panel to reuse with the new hint.
- `src/app/ui/components/SliderSpinRow.qml`, `components/ColorWell.qml` — controls to reuse.
- `src/app/ui/pages/KeyboardPage.qml:334-343` — `FileDialog` pattern and the 200 ms debounce.
- `tests/gui_helpers.py`, `tests/test_gui_shell.py`, `tests/test_gui_pages.py` — offscreen harness and shell expectations.

### Dependent Files

- `src/app/ui/adapters/bulbs_backend.py` — contract from task_05; QML reads only the documented roles and slots.
- `tests/test_gui_remembered_devices.py` — existing sidebar expectations; extend rather than rewrite.

### Related ADRs

- [ADR-002](adrs/adr-002.md) — the page shows the bulb's real state and never restores a look.

## Deliverables

- `src/app/ui/components/BulbListPanel.qml`
- `src/app/ui/pages/BulbPage.qml`
- Edited `src/app/ui/main.qml`, `pages/DevicesPage.qml`, `components/DeviceUnavailablePanel.qml`
- GUI journey cases in `tests/test_gui_bulbs.py`

## Tests

- [x] E2E-020 — empty inventory shows Import + hint; `importFile` with a `QUrl` yields three rows and the summary
- [x] E2E-021 — Connect adds the sidebar entry with an enabled switch; the entry opens page 5 with the real status and keeps the list selection
- [x] E2E-022 — Remove dialog: Cancel keeps the row, Remove deletes it
- [x] E2E-023 — disconnect/remove from the bulb page returns the content stack to index 0
- [x] E2E-024 — unavailable remembered bulb: sidebar "Unavailable", disabled switch, page reason and "Reading…" before the first read
- [x] E2E-025 — the sidebar switch sends `set_power(True)` and the page switch follows
- [x] E2E-026 — no `tuya` extra: no bulb panel, sidebar identical to today's shell expectations
- [x] E2E-028 — dragging the brightness row through five values in 200 ms sends one command with the last value

## Success Criteria

- `make test` is green, including `test_gui_shell`, `test_gui_pages` and `test_gui_remembered_devices`.
- Loading `main.qml` offscreen prints no QML binding errors.
- `grep -n "bulbLightSwitch\|bulbPage\|bulbRow_" src/app/ui/main.qml src/app/ui/pages src/app/ui/components` finds the documented object names.
- With `tuya_available()` false the Devices page and sidebar are byte-identical in structure to the current release.
