# UI/UX Change Map: Remembered devices and startup look

This map covers every GUI surface the feature touches: where it lives today, what changes, which states change, and which visual reference applies.
This repo's UI is **PySide6 + QML + Kirigami** (`src/app/ui/`), not `web/`. The design grammar is the
KDE HIG and the rules in [`src/app/ui/AGENTS.md`](../../../src/app/ui/AGENTS.md). No artboards are needed: every change adjusts an existing surface or uses a stock Kirigami component.

Companions: `_spec.md` Part I (behaviour authority), `_user_stories.md` (states come from ACs/ECs), `_dx.md` (the CLI half).

## Design constraints

- **Kirigami-first:** `Kirigami.PlaceholderMessage` for the unavailable state, stock `Switch` for the light, `Kirigami.InlineMessage` for errors. Colours come from `Kirigami.Theme` only.
- **Truthful UI:**
  - The light switch is **disabled** (not hidden) while its device is unavailable, and shows the last saved light state.
  - The LED bar's light state is tracked, not read; its tooltip doesn't claim otherwise.
  - "Unavailable" always states the reason in text (not only colour): `Not found (048d:7001)` or the USB error.
- **Copy:**
  - Short; no helper paragraphs under headings.
  - Device names "Keyboard" and "LED bar" as today.
  - Accessible names "Keyboard light" / "LED bar light" (`Accessible.name`).
- **Keyboard / focus:** the sidebar switch stays reachable with Tab, and Space toggles it. Activating the row (Enter / click) still opens the page, as today.
- **Stable `objectName`s for tests:** `sidebarKeyboardEntry`, `sidebarLedBarEntry`, `keyboardLightSwitch`, `ledBarLightSwitch`, `keyboardUnavailable`, `ledBarUnavailable`.

## Surface map

| # | Surface | Kind | Core change | Stories |
|---|---------|------|-------------|---------|
| S1 | Sidebar device entries | modify | Shown only for **remembered** devices; *unavailable* subtitle | US-001, US-002, US-003, US-004 |
| S2 | Sidebar switch | modify | **Light on/off** instead of connect/disconnect | US-008 |
| S3 | Device page — unavailable state | new (inside existing pages) | Placeholder with reason, **Retry**, **Forget** | US-004 |
| S4 | Devices page rows | modify | Connect = remember, Disconnect = forget; wording | US-001, US-003 |
| S5 | Keyboard page footer | modify | Remove **Power off** | US-008 |
| S6 | LED bar page footer | modify | Remove **Power off** / **Power on** | US-008 |
| S7 | Settings page | modify | Remove the auto-connect checkbox | US-011 |
| S8 | Startup / save messages | modify | Errors for an unreadable state file, missing animation, unwritable file | US-007, US-012 |

### S1. Sidebar device entries

- **Today:** `primaryNavModel` always appends **Keyboard** and **LED bar** (`src/app/ui/main.qml:107-131`). The "Enabled devices" header is always shown (`main.qml:198-231`).
- **Change:**
  - An entry exists iff `App.keyboardRemembered` / `App.ledBarRemembered`.
  - The "Enabled devices" header shows only when at least one entry exists.
  - Unavailable entries show a second line `Unavailable` in `Kirigami.Theme.disabledTextColor` and no chevron.
  - When an entry disappears while its page is shown, the view switches to **Devices**.
- **States:**
  - none remembered → Devices only (US-001.AC-3);
  - remembered + connected → title, chevron and switch (US-001.AC-1);
  - remembered + unavailable → title, "Unavailable" and a disabled switch (US-004.AC-1);
  - removed while selected → view returns to Devices (US-003.EC-2).
- **Artboard:** none — no named visual reference.

### S2. Sidebar switch

- **Today:** `Switch.checked` = `connected`; `onToggled` calls `connectFirstDiscovered` / `disconnectDeviceKind` (`main.qml:272-293`).
- **Change:**
  - `checked` = `App.keyboard.lightOn` / `App.ledBar.lightOn`; `onToggled` → `setLightOn(on)`.
  - `enabled` = device connected.
  - Tooltip: "Turn the keyboard light on/off" / "Turn the LED bar light on/off".
- **States:**
  - on (US-008.AC-2), off (US-008.AC-1);
  - disabled while unavailable (US-008.EC-3);
  - flips to on when a look is applied while off (US-008.AC-4);
  - rapid toggles end at the last position (US-008.EC-4).
- **Artboard:** none — no named visual reference.

### S3. Device page — unavailable state

- **Today:** no such state. Pages assume a connected device and only disable their controls.
- **Change:**
  - When the page's device is remembered but not connected, the page body is replaced by `Kirigami.PlaceholderMessage`:
    - icon `network-disconnect-symbolic` (fallback `dialog-warning-symbolic`);
    - text **"Keyboard unavailable"** / **"LED bar unavailable"**;
    - explanation = the unavailable reason;
    - **Retry** as the placeholder's `helpfulAction` (`App.retryDevice(kind)`), and **Forget** as a flat `Button` below it (`App.forgetDevice(kind)`). `PlaceholderMessage` holds only one action.
  - The footer is hidden in this state.
- **States:** not found (US-004.AC-1), USB error (US-004.EC-2), retry still failing (US-004.EC-1), retry success → normal page (US-004.AC-2), forget → entry gone (US-004.AC-3).
- **Artboard:** none — no named visual reference.

### S4. Devices page rows

- **Today:** the Connect/Disconnect button with tooltips "Claim this USB device…" / "Release the USB handle…". The "Open in this app" line and the page hint "Select a device, then Connect…" live in `src/app/ui/components/DeviceListPanel.qml:150-180` and `src/app/ui/pages/DevicesPage.qml:30`.
- **Change:**
  - Connect tooltip: "Connect and remember this device. It reconnects when the app opens."
  - Disconnect tooltip: "Disconnect and forget this device. Its saved look is kept."
  - Connected line: "Remembered — configure it from the sidebar."
  - Page hint: "Connect a device to remember it. USB access usually needs udev rules — see README."
- **States:** not connected, connected/remembered (US-001.AC-1), connect failed → inline error (US-001.EC-1), disconnect (US-003.AC-1).
- **Artboard:** none — no named visual reference.

### S5. Keyboard page footer

- **Today:** **Power off** on the left, **Apply** on the right (`src/app/ui/pages/KeyboardPage.qml:1203-1227`).
- **Change:** remove **Power off**. **Apply** keeps its visibility rules.
- **States:** footer with Apply only (US-008.AC-3).
- **Artboard:** none — no named visual reference.

### S6. LED bar page footer

- **Today:** **Power off**, **Power on** (replay) and **Apply** (`src/app/ui/pages/LedBarPage.qml:440-469`).
- **Change:** remove both power buttons; keep **Apply**.
- **States:** footer with Apply only (US-008.AC-3).
- **Artboard:** none — no named visual reference.

### S7. Settings page

- **Today:** the "Auto-connect keyboard and LED bar when the app starts…" checkbox (`src/app/ui/pages/SettingsPage.qml:56-63`).
- **Change:** remove it. "Close to system tray" and "Keyboard diagnostics" stay.
- **States:** no auto-connect option (US-011.AC-3).
- **Artboard:** none — no named visual reference.

### S8. Startup / save messages

- **Today:** `AppState.lastError` is shown in the Devices page `InlineMessage` (`DeviceListPanel.qml:55-70`).
- **Change:** same channel, with new messages from [_dx.md § Errors](_dx.md#errors): unreadable state file, missing animation, unwritable state file.
- **States:** unreadable file (US-012.AC-1, EC-1), missing animation (US-007.EC-1), unwritable (US-012.EC-2), cleared with "Clear error" as today.
- **Artboard:** none — no named visual reference.

## Component plan (design → production mapping)

### Rules

- Sidebar logic stays in `main.qml`. The nav model is rebuilt from `App.keyboardRemembered`, `App.ledBarRemembered` and `App.deviceConnectionEpoch` (single function `rebuildPrimaryNav()`).
- The unavailable state is one reusable component, used by both pages.
- No business logic in QML: remember/forget/retry/light are `App` slots.

### New Kirigami/QQC2 primitives

None. `Kirigami.PlaceholderMessage`, `Switch` and `Kirigami.InlineMessage` already cover every need.

### New domain components

- `src/app/ui/components/DeviceUnavailablePanel.qml` — composes `Kirigami.PlaceholderMessage` (Retry as `helpfulAction`) plus a flat `Button` for Forget. Properties: `deviceTitle`, `reason`; signals `retryRequested()`, `forgetRequested()`. Used by S3 in `KeyboardPage.qml` and `LedBarPage.qml`, and registered in `components/qmldir`.

### Signal & state mapping

| State | Primitive + token |
|-------|-------------------|
| Light on / off | `Switch.checked` (style default) |
| Light switch unavailable | `Switch.enabled: false` |
| Sidebar "Unavailable" subtitle | `Label`, `Kirigami.Theme.disabledTextColor`, small font |
| Unavailable page | `Kirigami.PlaceholderMessage` (`icon.name`, `text`, `explanation`, `helpfulAction`) |
| Startup / save error | `Kirigami.InlineMessage`, `type: Kirigami.MessageType.Error` (existing) |
