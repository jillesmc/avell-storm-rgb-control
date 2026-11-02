# Delivery QA report — Tuya bulbs

Executed 2026-11-02 against the uncommitted worktree `calm-badger` (task_01–task_09 complete).
Plan: [`plan.md`](plan.md). Evidence is inline below (commands and outputs are short; no separate files needed).
No real key or home IP appears here; temp `XDG_CONFIG_HOME` dirs were deleted after each run.

## Summary

| ID | Result | Notes |
|----|--------|-------|
| Q-1 UT-071 | ✅ pass | `tests/test_bulb_privacy_cross_surface.py` |
| Q-2 full suite, all extras | ✅ pass | 526 passed, 0 skipped |
| Q-2b full suite, stock venv | ⚠️ known | 500 passed, 21 skipped, 5 failed — all `test_gui_pages.py` Qt mismatch (pre-existing, environmental) |
| Q-3 no-extra install path | ✅ pass | |
| Q-4 no-extra GUI shell | ✅ pass | E2E-026 |
| Q-5 corrupt inventory | ✅ pass | exit 3 |
| Q-6 OQ-2 bulb icon | ✅ pass after fix | defect D-1 (task_06) fixed |
| M-1 … M-7 | ✅ pass (M-7 Wayland only; X11 not available, accepted by user) | D-2, D-3, D-4 found and fixed; D-5 was the launch env |

## Q-1 — UT-071 cross-surface privacy

- Env: E-full (`uv run --with "PySide6==6.12.0"`), temp `XDG_CONFIG_HOME`, fake drivers only.
- Command: `uv run --with "PySide6==6.12.0" pytest -q tests/test_bulb_privacy_cross_surface.py` → `1 passed`.
- Covers: `bulb import|list|status` human + `--json`, `state show` human + `--json`, `state.json`, every `BulbListModel`
  role, both `bulb(id)` snapshots, the inline error, DEBUG `caplog` during connect / unreachable / refresh.
  Guards against a vacuous pass (surfaces must render the bulb name ≥ 8 times and `key: set`; logs must exist).
  tinytuya logger forced to DEBUG → `_tinytuya()` restores WARNING; `tinytuya.set_debug` spy recorded 0 calls.

## Q-2 / Q-2b — full suites

| Env | Command | Result |
|-----|---------|--------|
| E-full | `uv run --with "PySide6==6.12.0" pytest -q -m "not hardware"` | **526 passed**, 1 warning (pre-existing evdev DeprecationWarning) |
| E-stock | `make test` | 500 passed, 21 skipped, **5 failed**: `test_gui_pages.py::test_page_component_ready[*]` |

Root cause of the stock failures/skips: distro Kirigami/Breeze QML plugins are Qt 6.12, the locked PySide6 is 6.11
(`The plugin '/usr/lib/qt6/qml/org/kde/kirigami/libKirigamiplugin.so' uses incompatible Qt library. (6.12.0)`).
Not caused by this feature; with a matching PySide6 everything passes. Bumping the lock is an operator decision.

## Q-3 — no-extra install path

Throwaway venv `uv venv /tmp/avell-noextra` + `uv pip install -e .` (no extras):

```text
import ok; tinytuya present: False
avell-storm-rgb -h            → lists "bulb"
avell-storm-rgb bulb list     → error: bulb control needs the optional 'tuya' extra: uv sync --extra tuya
exit=1
```

## Q-4 — no-extra GUI shell

`tests/test_gui_bulbs.py::test_e2e026_no_extra_no_bulb_surface` (E-full) → pass: no `bulbListPanel`, sidebar = `sidebarDevicesEntry` only.

## Q-5 — corrupt inventory `state show`

Temp `XDG_CONFIG_HOME`, inventory = `{`, one saved bulb, no-extra venv:

```text
error: bulb inventory is unreadable (invalid JSON at line 1 column 2): <tmp>/avell-storm-rgb/tuya_devices.json
State file: <tmp>/avell-storm-rgb/state.json
bulb      eb1a2b3c4d5e6f70819202  (inventory unreadable)
exit=3
```

Also covered by `tests/test_cli_state.py` (E2E-016).

## Q-6 — OQ-2 bulb icon

- `find /usr/share/icons -iname "lightbulb*"` → **nothing** on this machine (Breeze has no `lightbulb`).
- `preferences-desktop-color` exists (`/usr/share/icons/breeze/preferences/22/preferences-desktop-color.svg`).
- **D-1 (task_06):** the sidebar `Icon` used the generic `fallback: "applications-other"` for every entry, so bulbs
  would not show the documented fallback. Fixed in `src/app/ui/main.qml` (bulb entries fall back to
  `preferences-desktop-color`); GUI suites re-run → 19 passed. OQ-2 closed: name `lightbulb`, fallback `preferences-desktop-color`.

## M-1 … M-7 — hardware

Not run: they change real house lights and need someone at the bulbs, the phone and the GUI
(smoothness, flicker, portal picker). The user's go-ahead for this execution has **not** been recorded yet.
OQ-1 (M-5) therefore stays **open**; BR-12 gating (no push unless last known power is on) remains the guard.
Display session for M-7: not detectable from this non-graphical shell (`XDG_SESSION_TYPE` empty); record it when M-7 runs.

### Hardware attempt 1 (2026-11-02, go-ahead given in chat: "fazemos agora juntos")

- Imported the user's wizard file into the real inventory: `bulb import ~/git/iot/devices.json` → 3 × `added`, exit 0; file mode `600`.
- **M-1 blocked:** `bulb status` → all three `offline`, exit 1. Diagnosis (no key printed):
  laptop on the 192.168.18.x/24 LAN; no bulb MAC in `ip neigh`; only Escritório has a stored IP, on 192.168.0.x/24,
  TCP 6668 there times out; `python -m tinytuya scan 20` (empty dir) → **0 devices** on UDP 6666/6667/7000.
- Conclusion: no Tuya bulb is visible from this machine right now (powered off at the wall, or on another network/subnet).
  The app reports this correctly (`offline`, no command sent). M-2–M-7 wait until the bulbs are reachable.

### Hardware attempt 2 (user joined the Wi-Fi, 192.168.0.x/24)

- First `bulb list`: Escritório `online`, Quarto/Sala `offline`, although all three were on.
  Direct reads right after: all three answer (TCP 6668 open; `status()` ok in 0.3–1.3 s).
  Re-run `bulb list` ×2 → all `online`; `bulb status` → all `on white brightness 100% temperature 100%`, exit 0.
- Cause → **D-2**: Quarto/Sala had no IP in the wizard file and no ARP entry yet, so `open_bulb` fell back to UDP
  discovery (`DEFAULT_DISCOVERY_TIMEOUT` 6 s) inside `bulb list`'s 6 s deadline (`LIST_DEADLINE`). Self-heals once an
  IP is cached/saved (`set_last_ip`), but the very first list after import can report bulbs as offline.
- M-1: CLI result recorded above; comparison with the Smart Life app pending the user's confirmation.

### M-1 / M-2 results

- **M-1 ✅** user confirmed the CLI status matches the Smart Life app (all on, white, 100 %, 100 %).
- GUI launched from the branch (`uv run --with "PySide6==6.12.0" avell-storm-rgb-gui`); user connected all three bulbs
  and switched them off from the sidebar, then Escritório back on.
- M-2 first try **invalid**: the first GUI instance had not really quit (closed to an invisible tray), so two instances
  ran. Both were killed (SIGTERM), leaving no GUI process.
- **M-2 ✅ (redo)** with no GUI running: Quarto off, Escritório on, Sala off. Fresh single instance started (startup reads):
  `bulb status` identical — no bulb changed. `devices.bulbs` held the three ids, `remembered: true`.

### M-4 / M-5 results

- **M-4 ✅** Escritório off at the wall → GUI "Unavailable" + banner `Escritório is not reachable on the network. Check that it
  is powered; discovery uses UDP 6666/6667.`; back on → **Retry** restored it. → **D-3**: the banner stayed until
  "Clear error" after the successful Retry.
- **M-5 ✅ — OQ-1 closed.** Escritório off (switched off in the app). One `push_colour((255, 0, 0))` through the adapter, read
  2.5 s later: `before on=False mode=white` → `after on=False mode=colour rgb=(255, 0, 0)`. **The bulb does not turn on**,
  but it **stores** the new mode/colour, so it lights red the next time it is switched on. BR-12 gating (no push while off or
  unknown) stays: it is now what keeps a follow source from silently changing an off bulb's next colour.

### M-6 attempts

- Try 1 (old build): the sidebar switch flipped off/on at random while following; banner `Escritório: bulb command failed`.
  → **D-4 (task_02)**: on the persistent follow socket, nowait `push_colour` left the bulb's echoes (partial DPS 21/24, no 20)
  unread; the 5 s `status()` read one of them → `on=False` → switch off + follow gated; other reads/commands hit stale frames
  → generic `BulbError`.
- Fix A: `TuyaBulb.status()` skips partial replies (up to 3 reads). Try 2: switch stable, but the banner came back and the bulb
  showed "Unavailable" while on (status gave up after 3 partials, or a command read a stale echo).
- Fix B (root cause): `push_colour` now **waits for its echo** (`nowait=False`), so nothing piles up on the socket; spec KD-6
  updated. D-3 fixed at the same time (a successful op clears the banner that bulb caused). Suite: 530 passed.
- Try 3 (debug log `AVELL_STORM_RGB_LOG=debug`): still "Unavailable" + `bulb command failed`, e.g. right after stopping keyboard
  follow-screen. Log: many `skipped a partial status reply` before each failure → the bulb also queues one **async** partial
  update per push; in 5 s of following up to ~20 pile up, so 3 skips are not enough.
- Fix C (root cause): `TuyaBulb.status()` drains the persistent socket first (`receive()` with a 50 ms timeout until `None`,
  cap 64 frames, timeout restored), then reads its own reply. Tests: 20 queued updates → one status read, `on=True`. Suite: 532 passed.
- Try 4: still "Unavailable" — 3 partial frames, then failure, even after draining.
- Experiment on Escritório (GUI closed; only DPS key names printed): each push yields an ack **and** an async update, late and
  out of order; a push reply was sometimes empty; draining with 50 ms caught one frame, but more arrived later; status after the
  pushes read `[21, 24]` partial → `None` → full `[20…26]`. Timing-based draining cannot work.
- Fix D (root cause, replaces C): `status()` sends one query and keeps reading frames (`receive()`, 0.25 s each, 3 s deadline)
  until a reply carrying DPS 20 arrives; re-sends the query once if the socket goes quiet; else `BulbError`.
  Real-bulb check: 5 rounds × 4 pushes on the persistent socket, then `status()` → **5/5 `on=True`**, 0.02–0.11 s each.
  Suite: 531 passed.
- Try 5 (status reads until the full reply, 3 s deadline, one re-query): user ran keyboard follow-screen + Escritório
  Follow: Keyboard, then stopped follow-screen → no "Unavailable", no `bulb command failed`. Debug log: many
  `skipped a partial status reply`, **0** `bulb operation failed` / ERROR lines. **D-4 fixed.**
- **M-6 ✅** user: the bulb follows the keyboard quickly, no visible lag or flicker.

### M-3 result

- **M-3 ✅** user: brightness slider smooth; temperature and colour applied.

### M-7 result

- **M-7 ✅ (Wayland)** keyboard follow-screen + Escritório Follow: Screen → one portal picker, both follow the screen;
  stopping the keyboard leaves the bulb following. X11 not exercised: only Wayland is available on this machine; the user accepted this as a known gap.

- Side finding **D-5 (pre-existing, not bulbs)**: GUI log `QSystemTrayIcon::setVisible: No Icon set` — the tray icon never
  shows, so "close to tray" hides the app with no way back (explains the "app not really closed" during M-2).

## Defects

| ID | Check | Owner | Status |
|----|-------|-------|--------|
| D-1 | Q-6 icon fallback | task_06 | fixed |
| D-3 | error banner from a bulb stays after its successful Retry | task_05 / task_06 | fixed |
| D-4 | follow socket: unread push echoes → false off / `bulb command failed` | task_02 | fixed (M-6 try 5) |
| D-5 | tray icon not set (`QSystemTrayIcon::setVisible: No Icon set`) | test launch env | not a code defect (see note) |
| D-2 | first `bulb list` after import: discovery (6 s) ≥ list deadline (6 s) → false `offline` | task_02 / task_03 | fixed (`LIST_DEADLINE` 10 s) |

> [!NOTE]
> **Launch environment.** The branch GUI was started from the Compozy terminal, whose env lacked `KDE_FULL_SESSION` /
> `KDE_SESSION_VERSION`. Without them Qt does not load the KDE platform theme, so colours/icon theme differed from the
> installed app (autostarted by Plasma) and the tray icon resolved empty (D-5). Relaunched with the Plasma session vars:
> the warning is gone and the user confirmed theme + tray icon match the installed app. The installed app is unaffected.
