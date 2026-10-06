---
status: pending
title: "Task 6: Document remembered devices in both languages"
type: docs
complexity: low
---

# Task 6: Document remembered devices in both languages

## Overview

This task updates the permanent docs (EN + pt-BR pairs) so that users and agents find the new behaviour: remembered devices, the saved look, the light switch, `state.json`, and `state show` / `state restore`. It also stale-proofs the docs by removing every mention of auto-connect, footer power buttons and replay.

## Shippable Outcome

- **Outcome:** every doc listed below describes the shipped behaviour in both languages, and no doc mentions the removed auto-connect setting, footer power buttons or replay.
- **Verify in this task:**
  - the link / anchor / bilingual-pair checker and Mermaid render used for the docs mapping (`docs/README.md` conventions);
  - `grep -rni "auto-connect\|autoConnect\|Power on\|powerOnReplay" docs README*.md` → only intentional history mentions.
- **Integration verification:** the manual hardware checklist in `_tests.md` (5 items), run together with the user before closing the workflow.

## Requirements

- The bilingual-pair and ADHD style rules in `docs/README.md` (header, TL;DR, callouts, ≤ ~250 lines, fixed emojis).
- Update both languages of:
  - `docs/OVERVIEW` — feature table: GUI light switch, remembered devices; CLI `state show/restore`;
  - `docs/ARCHITECTURE` — new `device_state` module in the layer table; *State and persistence* table (`state.json`, removed `ui/autoConnectOnStartup`); debt #3 and #4 status;
  - `docs/FLOWS` — §2 becomes "startup restore"; §7 becomes "light toggle"; new short flow for "remember / forget";
  - `docs/GLOSSARY` — add saved look, remembered device, light state; remove/replace replay and auto-connect;
  - `docs/FEATURE_MATRIX` — CLI `state` rows;
  - `docs/DEVELOPMENT` — `state.json` location; recipe note "new apply path must emit `persistUpdate`";
  - root `README` — GUI table and CLI usage.
- `AGENTS.md` / `src/app/AGENTS.md`: add the single-writer rule and "apply paths emit `persistUpdate`".

## Subtasks

- [ ] 6.1 Update the EN docs.
- [ ] 6.2 Update the pt-BR pairs.
- [ ] 6.3 Update the AGENTS rules.
- [ ] 6.4 Run the link/pair/Mermaid checks; run the hardware checklist with the user.

## Implementation Details

### Relevant Files

- `docs/README.md` — conventions and the "Keep docs in sync" table.
- `_dx.md`, `_uiux.md` — the sources for the user-facing wording.

### Dependent Files

- `docs/*.md`, `docs/*.pt-BR.md`, `README.md`, `README.pt-BR.md`, `AGENTS.md`, `src/app/AGENTS.md`

## Deliverables

- The updated doc pairs and AGENTS rules.

## Tests

- No `_tests.md` IDs. Checks: link/anchor/pair script, Mermaid render, the grep above, and the manual hardware checklist (items 1–5 in `_tests.md`).

## Success Criteria

- Checks pass with 0 problems.
- The user confirms the hardware checklist, or a failing item is reported back as a bug against the owning task.
