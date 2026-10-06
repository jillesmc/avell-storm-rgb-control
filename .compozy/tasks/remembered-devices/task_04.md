---
status: completed
title: "Task 4: Sidebar shows remembered devices and their availability"
type: frontend
complexity: medium
---

# Task 4: Sidebar shows remembered devices and their availability

## Overview

The sidebar lists only remembered devices and marks unavailable ones. An unavailable device's page offers **Retry** and **Forget**, and the Devices page wording explains that Connect remembers. This finishes the GUI surface of the feature.

## Shippable Outcome

- **Outcome:**
  - With nothing remembered, the sidebar shows only Devices.
  - Connecting adds the entry.
  - An unplugged remembered device shows *Unavailable*, and its page offers Retry / Forget.
  - Disconnecting while on its page returns to Devices.
- **Verify in this task:** the offscreen GUI E2E suite (Tests below) and a short manual look with `make gui` (sidebar, unavailable page, light switch).
- **Integration verification:** none beyond this task's E2E. task_06 runs the manual hardware checklist with the user.

## Requirements

- Surfaces S1, S3, S4 and S8 from `_uiux.md`, plus the S2 states that depend on availability (disabled switch).
- Kirigami-first per `src/app/ui/AGENTS.md`; no business logic in QML.
- Stable `objectName`s: `sidebarKeyboardEntry`, `sidebarLedBarEntry`, `keyboardLightSwitch`, `ledBarLightSwitch`, `keyboardUnavailable`, `ledBarUnavailable`.
- The nav model is rebuilt by one function from `App.keyboardRemembered`, `App.ledBarRemembered` and `App.deviceConnectionEpoch`. The "Enabled devices" header shows only with at least one entry.
- New component `src/app/ui/components/DeviceUnavailablePanel.qml`, registered in `components/qmldir`: `PlaceholderMessage` with Retry as `helpfulAction` plus a flat Forget `Button`.
- Copy exactly as in `_uiux.md` S4; accessible names "Keyboard light" / "LED bar light".

## Subtasks

- [x] 4.1 Dynamic nav model and entries (remembered, unavailable subtitle, header visibility, fall back to Devices when the current entry disappears).
- [x] 4.2 `DeviceUnavailablePanel` and its use in `KeyboardPage.qml` / `LedBarPage.qml` (footer hidden in that state).
- [x] 4.3 Devices page copy (row tooltips, connected line, page hint).
- [x] 4.4 GUI E2E tests via `tests/gui_helpers.py` with `XDG_CONFIG_HOME=tmp_path` and fake USB.

## Implementation Details

### Relevant Files

- `src/app/ui/main.qml:41-170` — shell state, nav models, startup.
- `src/app/ui/main.qml:175-330` — sidebar list, section header, delegate with switch.
- `src/app/ui/components/DeviceListPanel.qml:55-190` — error message and device rows.
- `src/app/ui/pages/DevicesPage.qml:22-36` — page hint and connect wiring.
- `src/app/ui/pages/KeyboardPage.qml`, `src/app/ui/pages/LedBarPage.qml` — page roots for the unavailable state.
- `tests/gui_helpers.py`, `tests/test_gui_shell.py` — offscreen loading and `objectName` lookups.

### Dependent Files

- `src/app/ui/components/qmldir` — register the new component.
- `tests/test_gui_pages.py` — keep the page compile tests green.

## Deliverables

- QML changes plus the new component.
- `tests/test_gui_remembered_devices.py`.

## Tests

- [x] E2E-004, E2E-005, E2E-006 — sidebar memory, light switch and disconnect, unavailable page
- [x] E2E-007 — no footer power buttons, no auto-connect checkbox, Apply buttons still present (covers task_02 and task_03 removals)

## Success Criteria

- `make test` is green with the `gui` extra.
- No QML warnings about undefined `App.*` members at load (check stderr in the E2E run).

## Completion Notes

- The middle column (device tabs) is hidden while the device is unavailable (`showKeyboardSubNav` / `showLedSubNav` in `main.qml`); only the placeholder is shown.
- The disabled switch of an unavailable device shows the **saved** light state (`App.keyboardSavedLightOn` / `App.ledBarSavedLightOn`, notify `savedLightChanged`). A separate signal is used so toggling the light never rebuilds the sidebar (which would destroy the switch mid-click).
- ListView delegates have no `QObject` parent, so GUI tests look sidebar entries up through the visual item tree (`find_item`).
- Offscreen screenshots reviewed: Devices page with the remembered keyboard; the LED bar unavailable page with Retry / Forget and no tabs column. The "Unavailable" subtitle and the existing "Enabled devices" header use `disabledTextColor`, which the offscreen Fusion palette renders almost invisible; under Breeze they are visible. **A manual look under Plasma is still useful (task_06 checklist).**
- Evidence: `tests/test_gui_remembered_devices.py` (E2E-004–007, 4 passed ×3); full suite 114 passed; no QML warnings at load.
