---
name: kirigami-plasma6-gui
description: >-
  Workflow GUI deste repo com Kirigami 6, PySide6, qml_paths e testes QML.
  Usar ao implementar ou refatorar telas Plasma 6, smoke pytest ou packaging QML.
---

# Kirigami + Plasma 6 (avell-storm-rgb GUI)

**Âmbito:** [`src/app/`](../../../src/app/) (desktop). CLI: [`src/avell_storm_rgb/`](../../../src/avell_storm_rgb/).

## Stack fixa

- **Entry:** [`src/app/main.py`](../../../src/app/main.py) — `QApplication`, tray, `QQmlApplicationEngine`.
- **QML roots + estilo QQC2:** [`src/app/qml_paths.py`](../../../src/app/qml_paths.py) — `add_qml_import_paths`, `configure_quick_controls_style` (distro `/usr/lib*/qt6/qml`, Kirigami + `org.kde.desktop`).
- **UI:** [`src/app/ui/main.qml`](../../../src/app/ui/main.qml) + [`src/app/ui/components/`](../../../src/app/ui/components/).

## Checklist antes de PR / commit grande

1. `uv run pytest -m "not hardware"` — inclui smoke GUI se Kirigami disponível.
2. Se mudaste **shell ou contrato visual** — há teste em `tests/` que valida carga QML ou `objectName` acordados?
3. Em máquina com Plasma: abrir `uv run avell-storm-rgb-gui` e ver separadores, scroll e lista (smoke manual curto).

## TDD sugerido (QML)

1. **Red:** teste que falha (ex. `findChild` por `objectName` ou tipo esperado após `engine.load`).
2. **Green:** alteração QML mínima.
3. **Refactor:** extrair `pages/*.qml`, Units, sem quebrar o teste.

Smokes partilham a mesma ordem de import que `main.py` (reutilizar helpers quando existirem em `tests/`).

## Ambiente sem Kirigami

- `test_gui_smoke` pode fazer `pytest.skip` — não é regressão de código; documentar em README.
- CI opcional “com KF6”: mesmo teste deve passar **sem** skip.

## Hierarquia de componentes

Seguir a rule [kirigami-plasma6-qml.mdc](../../rules/kirigami-plasma6-qml.mdc): Kirigami → QQC2 → custom.

## Ver também

- [pyside-ui-refactor](../pyside-ui-refactor/SKILL.md) — separar negócio (`core/`) de apresentação.
- [pyside6-best-practices](../pyside6-best-practices/SKILL.md) — PySide6 geral.
