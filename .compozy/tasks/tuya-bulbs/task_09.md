---
status: completed
title: "Task 9: Document Tuya bulbs in both languages"
type: docs
complexity: low
---

# Task 9: Document Tuya bulbs in both languages

## Overview

This task makes the delivered feature discoverable and supportable: how to install the optional extra, import the wizard file, use the CLI and the GUI, and what the app does (and never does) with bulbs. Every Markdown doc is a bilingual pair, so the English and Brazilian Portuguese files change together.

## Shippable Outcome

- **Outcome:** a reader can install `--extra tuya`, import `devices.json`, use `bulb …`, understand the inventory file and its permissions, find bulbs in Devices/sidebar/page, and read the follow limits and privacy rules — in English and Portuguese. The repo's agent rules describe the new module boundaries and the threading/single-writer constraints.
- **Verify in this task:** bilingual pair, relative-link and Mermaid checks (no test IDs); review against `_dx.md` and `_uiux.md` for factual accuracy.
- **Integration verification:** task_11 re-checks the documented commands on the delivered package.

## Requirements

- Follow `docs/README.md`: bilingual pairs side by side, first line links the other language, change both in the same commit, ADHD-friendly structure (⏱️ reading time, TL;DR ≤ 3 bullets, "Read this if…", short sections, tables/lists, GitHub callouts, Mermaid ≤ ~12 nodes, files ≤ ~250 lines).
- Update the "Keep docs in sync" table in `docs/README.md` if a new doc or row is needed.
- Files: `README.md` + `README.pt-BR.md`, `docs/OVERVIEW`, `docs/ARCHITECTURE`, `docs/FLOWS`, `docs/FEATURE_MATRIX`, `docs/GLOSSARY`, `docs/DEVICE_FEATURES_DEEP_DIVE`, `docs/DEVELOPMENT` (all with `.pt-BR.md` twins).
- Agent rules: root `AGENTS.md` and `src/app/AGENTS.md` gain the bulb rules (optional extra, key privacy, `BulbWorker`/`bulb-*` threads, one driver per bulb, single writer of `devices.bulbs`, startup reads only). `AGENTS.md` stays English-only, as the repo requires.
- Content must match the delivered behaviour: `tuya_devices.json` 0600, no cloud at run time, import-only onboarding, `state.json` `devices.bulbs`, the CLI verbs and exit codes, follow sources/limits, one local connection, keys never displayed.
- Use only fictional ids, keys, MACs and IPs from `_dx.md`. Never paste a real key or a real home IP.
- No product-code changes in this task.

## Subtasks

- [x] 9.1 README (install/use/CLI/GUI) in both languages.
- [x] 9.2 OVERVIEW + FEATURE_MATRIX: bulbs as an optional feature, slice 1 vs slice 2.
- [x] 9.3 ARCHITECTURE + FLOWS: core/GUI boundaries, `BulbWorker`, `BulbFollower`, `ScreenFrameHub`, state and inventory writers.
- [x] 9.4 DEVELOPMENT: extras, tests, fixtures, no-hardware commands.
- [x] 9.5 GLOSSARY + DEVICE_FEATURES_DEEP_DIVE: bulb terms, DPS/modes, follow.
- [x] 9.6 Agent rules in root `AGENTS.md` and `src/app/AGENTS.md`.
- [x] 9.7 Pair/link/Mermaid/sync-table check.

## Implementation Details

### Relevant Files

- `README.md`, `README.pt-BR.md` — install, CLI and GUI entry points.
- `docs/README.md` — doc index and the "Keep docs in sync" table.
- `docs/OVERVIEW.md`, `docs/FEATURE_MATRIX.md` — feature framing.
- `docs/ARCHITECTURE.md` — layers, threading, state table, known debts #1 and #6.
- `docs/FLOWS.md` — startup, import, connect, control and follow flows.
- `docs/DEVELOPMENT.md` — `uv sync` extras, `make test`, fixtures.
- `docs/GLOSSARY.md`, `docs/DEVICE_FEATURES_DEEP_DIVE.md` — terms and payload detail.
- `AGENTS.md`, `src/app/AGENTS.md` — repo and GUI rules.

### Dependent Files

- `_dx.md`, `_uiux.md`, `_spec.md` — source of truth for every documented command and surface; do not invent behaviour.
- `tests/` — test names and extras referenced by DEVELOPMENT.

### Related ADRs

- [ADR-001](adrs/adr-001.md), [ADR-002](adrs/adr-002.md), [ADR-003](adrs/adr-003.md), [ADR-004](adrs/adr-004.md) — decisions the docs must state in user terms.

## Deliverables

- Updated English + `.pt-BR.md` pairs for the files above
- Updated root `AGENTS.md` and `src/app/AGENTS.md`
- Updated `docs/README.md` sync table if needed

## Tests

No `_tests.md` IDs. Evidence is the documentation checks below.

## Success Criteria

- Every listed doc has a matching `.pt-BR.md` updated in the same change; the first line of each links the twin.
- No broken relative links; Mermaid diagrams render and stay ≤ ~12 nodes; no file exceeds ~250 lines without a split.
- Documented commands, paths, exit codes and messages match `_dx.md`; documented surfaces and object names match `_uiux.md`.
- `grep -rn "q6R!x2_example\|192\.168\." README* docs AGENTS.md src/app/AGENTS.md` shows only the fictional examples from `_dx.md`.
- `docs/README.md` "Keep docs in sync" rows cover bulbs, the inventory file and `state.json`.
