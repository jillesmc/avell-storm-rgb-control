---
name: python-module-pattern
description: Cria ou refatora módulos Python com type hints e serviços isolados no CLI (src/avell_storm_rgb) ou na app desktop (src/app/core), ou extrai lógica de UI/scripts. Usar em pedidos de serviço, repositório ou domínio.
---

# python-module-pattern

## Dois contextos neste repositório

- **CLI / USB (código atual):** **`src/avell_storm_rgb/`** — manter `domain/`, `application/`, `infrastructure/`, `ports/`, `adapters/`. Para tarefas só RGB/CLI, **não** assumir `src/app/`.
- **Desktop PySide6/QML:** **`src/app/core/`** — ver [repo-context](../../rules/repo-context.mdc) e [pyside6-qml-desktop](../../rules/pyside6-qml-desktop.mdc).

## Objetivo

Criar ou refatorar módulos de serviço/domínio no **contexto certo** (CLI vs GUI).

## Quando usar

- Novo serviço, repositório ou módulo de domínio.
- Extrair lógica de handlers de UI, CLI ou scripts soltos.

## Como agir

- **CLI:** colocar código na camada certa sob `src/avell_storm_rgb/`.
- **Desktop:** `src/app/core/` ou subpastas (`services/`, `repositories/`, …) para lógica usada pela GUI em `src/app/`.
- Sempre:
  - Type hints em APIs públicas.
  - Evitar `typing.Any` sem justificativa clara.
  - Usar `pathlib.Path` para caminhos e ficheiros.
  - Docstrings curtas (módulo ou classe: responsabilidade).
- Preferir funções e classes de propósito único; evitar funções grandes, multi-responsabilidade ou parâmetros booleanos que desviem o comportamento.

**Tooling (este repo):** validar com **`uv run pytest`** (e `uv run avell-storm-rgb` para fluxos CLI); novas dependências com **`uv add`** / **`uv sync`** — ver [.cursor/rules/repo-context.mdc](../../rules/repo-context.mdc).

## Padrão de módulo

Ao criar um módulo novo, usar este esqueleto como base (ajustar nomes ao domínio):

```python
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class DataSource(Protocol):
    def load(self) -> dict: ...
    def save(self, data: dict) -> None: ...


class AppService:
    """
    Serviço responsável por <explique em 1-2 frases>.
    """

    def __init__(self, data_source: DataSource) -> None:
        self._data_source = data_source

    def load_state(self) -> dict:
        """Carrega o estado atual da aplicação a partir do data_source."""
        return self._data_source.load()

    def save_state(self, data: dict) -> None:
        """Persiste o estado da aplicação no data_source."""
        self._data_source.save(data)
```

(Tipar `dict` de forma mais estrita quando o domínio tiver modelo claro, por exemplo `TypedDict` ou dataclass.)

## Restrições

- Não mover módulos para fora de `src/` sem pedido explícito do usuário.
- Não trocar a camada de persistência (ex.: ficheiros ↔ base de dados) sem instruções explícitas.

## Ver também

- [pyside6-best-practices](../pyside6-best-practices/SKILL.md) — quando o módulo alimenta adaptadores ou backend QML.
