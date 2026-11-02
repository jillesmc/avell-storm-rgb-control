# User Stories: Tuya smart bulbs

Canonical behavior catalog for Tuya bulb integration. Companion to `_spec.md`; consumed by
`_spec.md` Part II (component mapping), `_uiux.md` (surface states), and `_tests.md` (coverage matrix).

## Personas

- **Owner** — uses the desktop GUI daily for the keyboard and LED bar, and has Tuya bulbs at home (Quarto, Escritório, Sala). Wants the desk light in the same app, without the cloud.
- **Script/agent** — drives lights from the terminal or an agent through `avell-storm-rgb` with `--json`.

## Story Index

| ID | Feature Area | Persona | Story |
|----|--------------|---------|-------|
| US-001 | Setup | Owner | Import bulbs from the tinytuya `devices.json` |
| US-002 | Setup | Owner | Connect a bulb: it is remembered and shows in the sidebar |
| US-003 | Setup | Owner | Disconnect or remove a bulb |
| US-004 | Setup | Owner | Remembered bulbs reconnect at start without changing |
| US-005 | Setup | Owner | A remembered bulb is unreachable |
| US-006 | Control | Owner | Switch the light on/off |
| US-007 | Control | Owner | Set brightness |
| US-008 | Control | Owner | Set white temperature |
| US-009 | Control | Owner | Set a colour |
| US-010 | Control | Owner | See changes made outside the app |
| US-011 | CLI | Script/agent | Control and read bulbs from the terminal |
| US-012 | CLI | Script/agent | List and remove bulbs; see them in `state show` |
| US-013 | Optional | Owner | Without the `tuya` extra, nothing changes |
| US-014 | Privacy | Owner | Local keys are never displayed |
| US-015 | Follow (slice 2) | Owner | The bulb follows the keyboard |
| US-016 | Follow (slice 2) | Owner | The bulb follows the screen |
| US-017 | Follow (slice 2) | Owner | The bulb follows the LED bar |
| US-018 | Follow (slice 2) | Owner | Follow survives restarts and never switches the light on |

## Setup

### US-001: Import bulbs

**As the** owner, **I want** to import the `devices.json` the tinytuya wizard wrote, **so that** the app knows my bulbs and their local keys.

Acceptance criteria:

- AC-1: Given the Devices page with the `tuya` extra, when I click **Import Tuya devices…** and pick `~/git/iot/devices.json`, then the "Smart bulbs" section lists Quarto, Escritório and Sala, each marked online or offline, and a line reads "Imported 3 bulbs".
- AC-2: Given the same file, when I run `avell-storm-rgb bulb import ~/git/iot/devices.json`, then each bulb is printed with `added` and the command exits 0.
- AC-3: Given bulbs already imported, when I import a file where Sala's key changed, then Sala is reported `updated` and the others `unchanged`; no bulb is removed.

Edge cases:

- EC-1: File is not JSON or not a list → nothing imported; error `not a tinytuya devices.json (<reason>)`.
- EC-2: An entry without `key` → skipped with `no local key`; the others are imported.
- EC-3: An entry that is not a light (category ≠ `dj`, e.g. a plug) → skipped with `not a bulb (category cz)`; an entry with no `category` → skipped with `missing category`.
- EC-4: File with zero bulbs → "No bulbs found in <path>"; inventory unchanged; CLI exit 1.
- EC-5: Import while bulbs are connected → connected bulbs keep working; the new key is used from the next command.

### US-002: Connect a bulb

**As the** owner, **I want** to connect a bulb from Devices, **so that** it appears in the sidebar like my keyboard and LED bar.

Acceptance criteria:

- AC-1: Given Escritório is online in the list, when I click **Connect**, then its state is read and an "Escritório" entry with a light switch appears under "Enabled devices", and the row button becomes **Disconnect**.
- AC-2: Given Escritório is connected, when I quit and reopen the app, then the entry is still there (remembered).
- AC-3: Given I click the sidebar entry, then the bulb page opens showing its current on/off, mode, brightness and colour or temperature.

Edge cases:

- EC-1: The bulb does not answer at Connect → not remembered; error "Escritório is not reachable on the network" with the row unchanged.
- EC-2: Connect clicked twice quickly → one entry, one read.
- EC-3: The key is wrong (bulb re-paired) or the protocol version does not match → not remembered; error "Escritório rejected the local key or protocol — re-import devices.json".

### US-003: Disconnect or remove a bulb

**As the** owner, **I want** to remove a bulb from the sidebar or from the app entirely, **so that** only the lights I use stay in view.

Acceptance criteria:

- AC-1: Given Escritório is connected, when I click **Disconnect** on Devices, then its sidebar entry disappears, it is not reconnected at start, and it stays in the list for a later Connect.
- AC-2: Given Sala is in the list, when I click **Remove** and confirm, then Sala disappears from the list and its key is deleted from the app.
- AC-3: Given I was on Escritório's page, when it is disconnected, forgotten or removed, then the app returns to Devices.

Edge cases:

- EC-1: Remove cancelled in the confirmation dialog → nothing changes.
- EC-2: Remove a bulb that was following a source (slice 2) → following stops before the key is removed.

### US-004: Reconnect at start without changing

**As the** owner, **I want** remembered bulbs to be back in the sidebar when the app opens, **so that** I can use them immediately, without the app turning any light on.

Acceptance criteria:

- AC-1: Given Escritório is remembered and off, when the app starts at login, then its switch shows off and the bulb stays off.
- AC-2: Given Escritório is remembered and on in white, when the app starts, then the page shows white with the bulb's real brightness and temperature, and no command was sent.
- AC-3: Given the app just started, before the first read finishes, then the switch is disabled and the page says "Reading…".

Edge cases:

- EC-1: The bulb's IP changed since last time → the bulb is found again (ARP or discovery) and shown normally.
- EC-2: The network is not up yet at login → shown as unavailable; the 30 s refresh brings it back once the network is up.

### US-005: Unreachable remembered bulb

**As the** owner, **I want** to see when a remembered bulb cannot be reached and retry, **so that** a power-cut bulb does not look like it is on.

Acceptance criteria:

- AC-1: Given Sala is remembered but its wall switch is off, when the app reads it, then the sidebar entry shows "Unavailable" with a disabled switch, and the page shows "Sala is not reachable on the network" with **Retry** and **Forget** (Forget stops remembering it and keeps the key, like the USB devices).
- AC-2: Given Sala becomes reachable, when I click **Retry** or the next refresh runs, then the entry and page show its real state again.

Edge cases:

- EC-1: Retry while still unreachable → same message; no busy overlay; the rest of the app stays usable.
- EC-2: One bulb unreachable → the other bulbs keep responding (no shared queue).

## Control

### US-006: Light switch

**As the** owner, **I want** to switch a bulb on/off from the sidebar or its page, **so that** I control the room light without leaving the app.

Acceptance criteria:

- AC-1: Given Escritório is off, when I turn its sidebar switch on, then the bulb turns on in its previous mode and colour, and the switch stays on.
- AC-2: Given it is on, when I turn the page switch off, then the bulb turns off and the sidebar switch follows.

Edge cases:

- EC-1: The command fails → the switch returns to the bulb's real state and an error names the bulb.
- EC-2: Rapid toggling → commands run in order; the final state matches the last toggle.

### US-007: Brightness

**As the** owner, **I want** to set brightness, **so that** I can dim the light.

Acceptance criteria:

- AC-1: Given white mode, when I set the slider to 40 %, then the white brightness becomes 40 % (and the bulb turns on if it was off).
- AC-2: Given colour mode, when I set the slider to 40 %, then the colour keeps its hue and becomes dimmer.

Edge cases:

- EC-1: Slider dragged continuously → one command per 200 ms pause (debounced), last value wins.
- EC-2: Value 0 is not offered; the minimum is 1 %.

### US-008: White temperature

**As the** owner, **I want** to choose warm or cold white, **so that** the light suits the time of day.

Acceptance criteria:

- AC-1: Given any mode, when I move the temperature slider to 0 %, then the bulb shows its warmest white and the page shows white mode.

Edge cases:

- EC-1: Bulb in scene or music mode (set from the phone) → the page shows the mode name; moving the slider switches to white.

### US-009: Colour

**As the** owner, **I want** to pick a colour, **so that** the room matches my setup.

Acceptance criteria:

- AC-1: Given any mode, when I pick orange in the colour well, then the bulb shows orange, the page shows colour mode, and the bulb turns on if it was off.

Edge cases:

- EC-1: Black picked → sent at the minimum brightness (1 %), not off; the switch is the way to turn it off.

### US-010: Changes made outside the app

**As the** owner, **I want** the app to show changes made from the phone or the wall switch, **so that** what I see is true.

Acceptance criteria:

- AC-1: Given the window is visible, when someone turns Escritório off from the phone, then within 30 s its switch shows off.
- AC-2: Given the app was hidden in the tray, when I show the window, then bulbs are read right away.

Edge cases:

- EC-1: Window hidden → no reads (no network traffic), except following bulbs (slice 2).

## CLI

### US-011: Control and read from the terminal

**As a** script/agent, **I want** bulb commands in `avell-storm-rgb`, **so that** I no longer need `bulbs.py`.

Acceptance criteria:

- AC-1: When I run `avell-storm-rgb bulb status`, then each imported bulb prints its state (or `offline`), exit 0 if all answered.
- AC-2: When I run `avell-storm-rgb bulb off sala`, then Sala turns off and `Sala  off` is printed.
- AC-3: `bulb on|off|toggle|bright|white|color` accept a name (accent/case-insensitive), an id, or `all`.
- AC-4: `bulb status --json` prints a JSON list with `id`, `name`, `online` and the state fields, with no key.

Edge cases:

- EC-1: Unknown name → `error: no bulb named 'cozinha'. Known: Quarto, Escritório, Sala`, exit 2.
- EC-2: Two bulbs share the name → `error: 'luz' matches 2 bulbs; use the id: <id1>, <id2>`, exit 2.
- EC-3: Target `all` with one bulb offline → the others are applied, the offline one prints `offline`, exit 1.
- EC-4: `bright 0` or `bright 150` → argparse error, exit 2.
- EC-5: No bulbs imported → message pointing to `bulb import`, exit 1 for control verbs, exit 0 for `list`/`status`.

### US-012: List, remove and state show

**As a** script/agent, **I want** to list and remove imported bulbs and see which are remembered, **so that** I can inspect the setup without the GUI.

Acceptance criteria:

- AC-1: `bulb list` prints name, id, online/offline, IP, protocol and `key: set`.
- AC-2: `bulb remove sala` deletes Sala and its key from the inventory and prints the inventory path.
- AC-3: `state show` adds one `bulb` line per bulb saved in `state.json` (remembered or not, follow source), and `--json` includes `devices.bulbs`.
- AC-4: `state restore` does not contact bulbs.

Edge cases:

- EC-1: `bulb remove` on a bulb the GUI remembers → removed from the inventory; the GUI drops it from `state.json` on its next write.

## Optional and private

### US-013: Without the `tuya` extra

**As the** owner, **I want** the app unchanged when bulb support is not installed, **so that** the feature is truly optional.

Acceptance criteria:

- AC-1: Given `tinytuya` is not installed, when I open the app, then Devices, the sidebar and Settings look exactly as before (no "Smart bulbs" section).
- AC-2: Given the same, when I run `avell-storm-rgb bulb list`, then it prints `error: bulb control needs the optional 'tuya' extra: uv sync --extra tuya` and exits 1.

Edge cases:

- EC-1: The extra is installed but nothing is imported → the "Smart bulbs" section shows only the Import button and a one-line hint.
- EC-2: `state.json` has `bulbs` entries but the extra was removed → GUI ignores them and keeps them in the file. `state show` still lists them.

### US-014: Keys are never displayed

**As the** owner, **I want** local keys kept out of everything I can see or share, **so that** a pasted log or state file does not expose my devices.

Acceptance criteria:

- AC-1: The inventory file is created with permission 0600.
- AC-2: No GUI text, CLI output (human or JSON), log line at any level, or `state.json` contains a local key.

Edge cases:

- EC-1: A tinytuya error message → shown with the bulb name and error type; never with the payload or key.

## Follow (slice 2)

### US-015: Follow the keyboard

**As the** owner, **I want** the desk bulb to take the colour the keyboard shows, **so that** the room matches it.

Acceptance criteria:

- AC-1: Given Escritório is on and set to **Follow: Keyboard**, when I apply solid blue to the keyboard, then the bulb turns blue within 1 s.
- AC-2: Given a keyboard animation is playing, then the bulb changes with it, at most 4 times per second.
- AC-3: Given **Follow: None**, keyboard changes no longer affect the bulb.

Edge cases:

- EC-1: The keyboard runs a firmware effect (wave) → the bulb keeps its last colour.
- EC-2: The keyboard light is switched off → the bulb keeps its last colour.
- EC-3: Tiny colour changes (< 8 per channel) → nothing sent.

### US-016: Follow the screen

**As the** owner, **I want** the bulb to follow the screen's average colour, **so that** I get ambient light while watching something.

Acceptance criteria:

- AC-1: Given **Follow: Screen** and no capture running, when I choose it, then the screen/window picker appears once, and the bulb then tracks the captured average colour.
- AC-2: Given the keyboard is already following the screen, when I choose **Follow: Screen** for a bulb, then no second picker appears and both use the same capture.
- AC-3: Given the bulb and keyboard both follow the screen, when I stop the keyboard's follow-screen, then the bulb keeps following.

Edge cases:

- EC-1: The `screen` extra is missing → the Screen option is absent from the selector.
- EC-2: The picker is cancelled → follow returns to None with the message "Screen capture cancelled".
- EC-3: The captured window closes → capture stops; following bulbs keep their last colour and return to None with a message.

### US-017: Follow the LED bar

**As the** owner, **I want** the bulb to match the LED bar, **so that** the desk lighting is consistent.

Acceptance criteria:

- AC-1: Given **Follow: LED bar** and an LED bar palette of red and blue, then the bulb shows their average (purple), steady.
- AC-2: When I apply a new LED bar palette, then the bulb changes within 1 s.

Edge cases:

- EC-1: The LED bar is not connected → the LED bar option is absent.
- EC-2: The LED bar light is off → the bulb keeps its colour.

### US-018: Persistence and safety

**As the** owner, **I want** my follow choice kept and the bulb never switched on by it, **so that** following is set-and-forget and safe at login.

Acceptance criteria:

- AC-1: Given Escritório follows the keyboard, when I restart the app, then it follows the keyboard again once it has been read.
- AC-2: Given Escritório follows the keyboard and is off, when the keyboard colour changes, then the bulb stays off.
- AC-3: Given I switch the bulb off from the phone while it follows, then within 5 s the app stops sending colours to it.

Edge cases:

- EC-1: Disconnect while following → following stops; Connect later resumes the saved choice.
- EC-2: The bulb drops off the network while following → it becomes unavailable and the persistent connection closes; Retry resumes.
- EC-3: Another local client (e.g. `bulbs.py`) cannot connect to a following bulb → expected; documented on the page as a hint.
