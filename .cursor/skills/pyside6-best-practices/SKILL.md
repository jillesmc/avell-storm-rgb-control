---
name: pyside6-best-practices
description: Referência para PySide6 moderno — separação UI/lógica, QML vs Widgets, tipagem, sinais/slots, tema e threading. Usar em trabalho com UI PySide6/QML, controllers, QQmlApplicationEngine, ou ao discutir arquitetura de desktop Qt.
---

# pyside6-best-practices

## Encaixe: rule vs skill

- **repo-context.mdc** (always on): CLI vs GUI, `uv`, precedência.
- **pyside6-qml-desktop.mdc**: arquitetura **`src/app/`** (Python, pastas, threading).
- **kirigami-plasma6-qml.mdc**: apenas **`src/app/ui/**/*.qml`** — Kirigami-first, `Kirigami.Theme` / `Units`, TDD QML.
- **Esta skill**: guia **genérica** Qt/PySide6. Em conflito: **pyproject** + **repo-context** > rules deste repo > esta skill.

## Leitura obrigatória antes de codar aqui

1. UI nova → **QML** + lógica em Python (`core/` + adaptadores), salvo pedido explícito de fluxo só com Widgets.
2. **Qt Designer + `pyside6-uic`** → só quando a equipa optar por **Qt Widgets**; nunca como padrão silencioso que desvie o repo de QML.
3. **Dependências extra** (ex.: `qtvscodestyle`, PySide6) → só com **autorização explícita** (ver rule); neste repositório usar **`uv add`** / **`uv sync --extra …`** e **`uv run …`** para execução local (**não** `pip install` como padrão).

## Resumo prático

| Tema | Orientação |
|------|------------|
| Organização | QML = declarativo; Python = negócio, IO, integrações. Widgets: Designer → `pyside6-uic` → classe `Ui_*` composta num controller; **não** editar `ui_*.py` à mão. |
| QML | Qt Quick Controls 2; pouca lógica em JS; cálculos e regras em `QObject` / slots. |
| Tipos | Type hints em APIs públicas; **Black / Ruff / mypy** só se estiverem no `pyproject.toml` (ver `repo-context`). |
| Sinais | `signal.connect(slot)`; evitar lambdas em loops (usar `functools.partial` ou métodos dedicados). |
| HiDPI | Considerar `Qt.ApplicationAttribute.AA_UseHighDpiPixmaps` para ícones/SVG nítidos. |
| Tema (genérico) | Estilos globais ad hoc **só** com acordo de projeto. **Neste repo (GUI):** [`src/app/qml_paths.py`](../../../src/app/qml_paths.py) define QQC2 (`org.kde.desktop` ou `Fusion`); QML: rule **kirigami-plasma6-qml**. |
| Performance | Sem I/O bloqueante nem CPU pesada na GUI thread; **QThread** / **QRunnable** / padrões assíncronos compatíveis com Qt. |

## Quando aprofundar

Exemplos extensos (BAD/GOOD), snippets completos de Designer+uic, QML+`Backend`, sinais e threading: ver [reference.md](reference.md).

## Relação com outras skills do repo

- [kirigami-plasma6-gui](../kirigami-plasma6-gui/SKILL.md) — workflow Plasma 6 neste repositório.
- [python-module-pattern](../python-module-pattern/SKILL.md) — módulos em `core/` ou CLI.
- [qml-screen-generator](../qml-screen-generator/SKILL.md) — criar ecrãs novos.
- [pyside-ui-refactor](../pyside-ui-refactor/SKILL.md) — extrair negócio da UI.
