# UI/UX Change Map: Tuya smart bulbs

Every UI surface this feature touches: where it lives today, what changes, which states change.
There are no named visual references; this is existing-surface work in the app's Kirigami/Breeze language.

Companions: `_spec.md` Part I (behavior authority), `_user_stories.md` (states come from ACs/ECs), `_dx.md` (non-UI half).

## Design constraints

- Follow `src/app/ui/AGENTS.md`: Kirigami first, then QQC2, custom only in `components/`. Colours from `Kirigami.Theme`, spacing from `Kirigami.Units`, icons with a `fallback`.
- **Truthful UI.** Unknown bulb state renders as unknown ("Reading…", switch disabled), never as off. Affordances the runtime cannot support are **absent**, not disabled: the whole bulb surface without the `tuya` extra (US-013), the Screen/LED bar follow options without their source (US-016.EC-1, US-017.EC-1).
- **Same model as USB devices.** Bulb rows, sidebar entries and the unavailable state reuse the existing patterns and words: Connect / Disconnect / Forget / Retry. **Remove** is the only new verb, and it is the only one that deletes a key.
- **No busy overlay** for bulb operations (Safety Invariant 8). Feedback is per bulb (button text, "Reading…"), and errors go to the existing inline error.
- Bulb names are user data: show as-is with elide. Never show a key (US-014).
- Debounce sliders and colour changes at 200 ms (existing `KeyboardPage.qml` pattern).

## Surface map

| # | Surface | Kind | Core change | Stories |
|---|---------|------|-------------|---------|
| S1 | Devices page — "Smart bulbs" section | new section in existing page | Import button, bulb rows with Connect/Disconnect/Remove | US-001, US-002, US-003, US-013 |
| S2 | Import file dialog | new | Pick `devices.json` | US-001 |
| S3 | Remove confirmation | new | Confirm key deletion | US-003 |
| S4 | Sidebar bulb entries | modify | One entry + light switch per remembered bulb | US-002, US-004, US-005, US-006 |
| S5 | Bulb page | new page | Switch, brightness, temperature, colour, unavailable state | US-004–US-010 |
| S6 | Follow selector (slice 2) | new control on S5 | None / Keyboard / Screen / LED bar | US-015–US-018 |
| S7 | Inline error and busy overlay | modify (behaviour only) | Bulb errors shown; never busy | US-002.EC-1, US-005.EC-1 |

### S1. Devices page — "Smart bulbs" section

- **Today**: `src/app/ui/pages/DevicesPage.qml:23-48` shows `DeviceListPanel` (USB rows, Connect/Disconnect at `components/DeviceListPanel.qml:161-176`) and a footer Refresh.
- **Change**: below the USB panel, a new `BulbListPanel` with a section header "Smart bulbs" (title + separator on the same row), an **Import Tuya devices…** button, and one row per imported bulb. The footer Refresh also refreshes bulbs. The whole section exists only when `App.bulbsAvailable`.
- **States to design**:
  - Absent: no `tuya` extra (US-013.AC-1).
  - Empty: extra present, nothing imported. Import button plus the hint "Import the devices.json written by the tinytuya wizard to control your Tuya bulbs." (US-013.EC-1).
  - Import summary line after an import: "Imported 3 bulbs" / "No bulbs found in <file>" (US-001.AC-1, EC-4).
  - Row: name; subtitle `online · 192.168.0.22` / `offline` / `Reading…`; button **Connect** or **Disconnect**; an icon button **Remove** (`edit-delete`, tooltip "Remove from this app (deletes its local key)").
  - Row connecting: button disabled, text "Connecting…" (US-002.EC-2).
  - Row remembered: secondary line "Remembered — configure it from the sidebar." (the exact copy of `DeviceListPanel.qml:152-154`).
- **Artboard**: none — no named visual reference.

### S2. Import file dialog

- **Change**: `QtQuick.Dialogs.FileDialog`, `fileMode: OpenFile`, `nameFilters: ["tinytuya devices (*.json)", "All files (*)"]`, starting in the home folder. Same component as the animation picker at `pages/KeyboardPage.qml:334-343`.
- **States**: accepted → `App.bulbs.importFile(selectedFile)`. `selectedFile` is a `url` and the slot is `@Slot("QUrl")`, which calls `toLocalFile()` — unlike `KeyboardPage.qml:339-343`, QML must **not** strip `file://`. Cancelled → nothing.
- **Artboard**: none — no named visual reference.

### S3. Remove confirmation

- **Change**: `Kirigami.PromptDialog`, title "Remove Sala?", text "Its local key is deleted from this app. You can import it again later.", buttons **Remove** (destructive) / **Cancel**.
- **States**: confirm → removed and gone from S1/S4 (US-003.AC-2); cancel → unchanged (US-003.EC-1).
- **Artboard**: none — no named visual reference.

### S4. Sidebar bulb entries

- **Today**: `src/app/ui/main.qml:71-112` (`rebuildPrimaryNav`) appends Devices, then Keyboard/LED bar when remembered. The light switch and the "Unavailable" subtitle are page-number ternaries (`main.qml:327-348`, `:309-318`); `syncPrimarySidebarListIndex` (`:60-70`) only tracks pages 1–2, `unavailableReasonForPage` (`:115-121`, bound at `:282`) returns `""` outside 1–2, and the forgotten-device reset (`:107-110`) only resets pages 1–2.
- **Change**: after the LED bar, append one entry per remembered bulb sorted by name: `sectionName: "enabled"`, `entryName: "sidebarBulbEntry"`, `title: <name>`, `iconName: "lightbulb"` (fallback `preferences-desktop-color`; OQ-2), `page: 5`, `bulbId: <id>`, `showSwitch: true`, plus the row snapshot keys from `_spec.md` (`available`, `lightOn`, `stateKnown`, `unavailableReason`). Rebuild on `App.bulbs.modelChanged`. The switch is **model-driven, not page-driven**.
- **Six required `main.qml` edits** (B4) — without them `page: 5` breaks the shell:

| Location | Today | Change |
|----------|-------|--------|
| `Switch.objectName` (`:328`) | `page === 1 ? "keyboardLightSwitch" : "ledBarLightSwitch"` | `page === 5 ? "bulbLightSwitch" : …` (keep the 1/2 arms) |
| `Switch.checked` (`:334-338`) | page 1 vs else | `page === 5 ? model.lightOn : (page === 1 ? … : …)` |
| `Switch.enabled` (`:334-338`) | page 1 vs else | `page === 5 ? model.available && model.stateKnown : …` |
| `Switch.onToggled` (`:339-343`) | `if page === 1 … else if page === 2` | add `else if page === 5 → App.bulbs.setLightOn(model.bulbId, checked)` |
| `unavailableReasonForPage()` (`:115-121`, bound `:282`) | returns `""` unless page 1/2 | add `page === 5 → model.available ? "" : model.unavailableReason` |
| `syncPrimarySidebarListIndex()` (`:60-70`) and the forgotten reset (`:107-110`) | `primarySection <= 2`; reset only pages 1/2 | track every entry with `page >= 1`, and reset to page 0 whenever the selected bulb disappears (disconnect, forget, remove — US-003.AC-3) |

`model` is the selected sidebar entry from the repeater, so no new QML component is needed.
- **States to design**:
  - Unknown (before the first read): switch disabled, unchecked (US-004.AC-3).
  - On / off: switch reflects the last read or command (US-006).
  - Unavailable: subtitle "Unavailable", switch disabled (US-005.AC-1).
  - Command failed: switch snaps back to the real state (US-006.EC-1).
  - Selected bulb disconnected, forgotten or removed: back to Devices (US-003.AC-3), through the generalised reset above.
- **Artboard**: none — no named visual reference.

### S5. Bulb page

- **Today**: none. The content `StackLayout` is at `main.qml:584-604` (Devices 0, Keyboard 1, LED bar 2, Settings 3, About 4).
- **Change**: new `pages/BulbPage.qml` at index 5, with a `bulbId` property set from the sidebar entry. It re-reads `App.bulbs.bulb(bulbId)` on `App.bulbs.bulbEpoch`. Layout: `Kirigami.ScrollablePage` titled with the bulb name. The header shows the status line ("On · White · 192.168.0.22") and the light switch. A `Kirigami.FormLayout` holds:
  - **Brightness**: `SliderSpinRow` 1–100 % (US-007).
  - **White temperature**: `SliderSpinRow` 0–100 with "Warm" / "Cold" end labels (US-008).
  - **Colour**: `ColorWell` opening a `ColorDialog` (US-009).
  - **Mode**: read-only `Kirigami.Chip` (White / Colour / Scene / Music) (US-008.EC-1).
- **States to design**:
  - Reading: controls disabled until `stateKnown`, "Reading…" (US-004.AC-3).
  - Ready, white / colour: controls show the bulb's values (US-004.AC-2).
  - Scene / music (set from the phone): chip shows it; controls stay enabled; using one leaves the mode (US-008.EC-1).
  - Off: controls enabled. Using brightness/temperature/colour switches the bulb on (BR-9); a one-line hint under the switch says so.
  - Unavailable: `DeviceUnavailablePanel` (Retry / Forget) with the reason "Sala is not reachable on the network". The Forget tooltip is "Stop reconnecting this bulb. Its key is kept." (needs a tooltip property on the panel) (US-005).
  - Outside change: values update within 30 s while visible, and at once when the window is shown (US-010). `main.qml` reports `Window.visible` and `closeToTray` hides to `App.setWindowVisible(visible)`; `App.bulbs.windowVisible` starts/stops the timer (M7).
- **Artboard**: none — no named visual reference.

### S6. Follow selector (slice 2)

- **Change**: on S5, a `ComboBox` "Follow" in the FormLayout with options **None**, **Keyboard** (only when the keyboard is connected), **Screen** (only when the `screen` extra is available), **LED bar** (only when the LED bar is connected). Calls `App.bulbs.setFollow(id, source)`. While following, a `Kirigami.InlineMessage` (information) says: "Following the keyboard. Other apps on your network can't control this bulb locally while it follows." (US-018.EC-3).
- **States to design**: None; following (per source); waiting for the first colour (no change yet); capture picker open (Screen, US-016.AC-1); capture cancelled/ended → back to None plus an error line (US-016.EC-2, EC-3); bulb off while following → the message adds "Paused while the light is off." (US-018.AC-2); source disappears (LED bar disconnected) → keeps the choice, message "Paused: LED bar not connected.".
- **Artboard**: none — no named visual reference.

### S7. Inline error and busy overlay

- **Today**: `DeviceListPanel` shows `App.state.lastError` (`deviceErrorInline`). `BusyOverlay` binds `App.state.busy` (`main.qml:607-611`).
- **Change**: bulb results arrive through `BulbWorker.opDone` → `BulbsBackend` on the GUI thread (row cache, `modelChanged`, `bulbEpoch`); user-facing failures arrive through `BulbWorker.opFailed` → `AppState.reportError` with the bulb name (copy in `_dx.md` Errors). Bulb operations never toggle `busy`.
- **Artboard**: none — no named visual reference.

## Component plan (design → production mapping)

### Rules

- Bulb rows compose `ItemDelegate` content like `DeviceListPanel` rows. Do not fork `DeviceListPanel`; the bulb list is its own small component, because its data source (`App.bulbs.model`) and actions differ.
- Keep existing `objectName`s. New ones: `bulbListPanel`, `bulbImportButton`, `bulbRow_<id>`, `bulbRemoveDialog`, `sidebarBulbEntry`, `bulbLightSwitch`, `bulbPage`, `bulbBrightnessRow`, `bulbTemperatureRow`, `bulbColorWell`, `bulbFollowCombo`.

### New shared primitives

None. Reuses `SliderSpinRow`, `ColorWell` and `DeviceUnavailablePanel` (gains an optional `forgetHint` property, defaulting to today's text).

### New domain components

| Component | Composed from | Used by |
|-----------|---------------|---------|
| `components/BulbListPanel.qml` | `Kirigami.Heading`/`Separator` row, `Button`, `ListView` + `ItemDelegate`, `FileDialog`, `Kirigami.PromptDialog` | S1–S3 |
| `pages/BulbPage.qml` | `Kirigami.ScrollablePage`, `Kirigami.FormLayout`, `Switch`, `SliderSpinRow`, `ColorWell` + `ColorDialog`, `Kirigami.Chip`, `ComboBox`, `Kirigami.InlineMessage`, `DeviceUnavailablePanel` | S5, S6 |

### Signal & state mapping

| State | Primitive + token |
|-------|-------------------|
| online / offline / Reading… | row subtitle `Label`, `Kirigami.Theme.disabledTextColor` for offline/Reading… |
| Unavailable (sidebar) | existing subtitle `Label` (`main.qml:309-318`) |
| Mode chip | `Kirigami.Chip`, `checkable: false` |
| Following / paused | `Kirigami.InlineMessage`, `type: Information` |
| Errors | existing `deviceErrorInline` (`Kirigami.InlineMessage`, error) |
