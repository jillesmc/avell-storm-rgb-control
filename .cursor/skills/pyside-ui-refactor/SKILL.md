---
name: pyside-ui-refactor
description: Orienta refatoração de telas PySide6 e QML, separando apresentação de lógica em src/app/core. Usar em refactor de GUI; irrelevante para o CLI em src/avell_storm_rgb salvo pedido explícito.
---

# pyside-ui-refactor

**Âmbito:** app desktop em **`src/app/`** (ver [.cursor/rules/repo-context.mdc](../../rules/repo-context.mdc)). Não confundir com o pacote **`src/avell_storm_rgb/`**.

**Tooling:** após refactors, **`uv run pytest`**; dependências só com **`uv`** — [.cursor/rules/repo-context.mdc](../../rules/repo-context.mdc).

## Objetivo

Melhorar a arquitetura do código de UI: QML em apresentação e interação leve; Python com negócio, dados e integrações.

## Quando usar

- Refactor pedido em janelas/telas PySide6.
- UI a misturar regras de negócio com detalhes de apresentação.
- Funções longas em ficheiros de UI que implementam regras de negócio.

## Como agir

1. **Ler primeiro** o que for relevante em `src/app/ui/` (QML, helpers de UI) e `src/app/core/` (serviços, domínio).
2. **Identificar**:
   - Negócio em handlers de botão, sinais ou expressões QML/JavaScript.
   - Disco, rede ou persistência chamados diretamente a partir de código de UI.
3. **Propor** um plano curto (3–5 bullets) **antes** de editar ficheiros.

## Padrões

- Mover regras para classes ou funções em `src/app/core/`.
- No Python exposto ao QML, usar apenas o necessário:
  - `@Property` para dados da UI.
  - `Signal` para eventos.
  - `Slot` para ações invocadas a partir do QML.
- No QML:
  - Bindings simples às propriedades expostas.
  - Evitar negócio complexo em JavaScript inline.
  - Repetição visual → componentes em `src/app/ui/components/`.

## Boas práticas Qt / PySide6

- Não bloquear o thread de UI: IO ou CPU pesado com `QThread`, `QRunnable` ou padrão assíncrono adequado.
- IDs e nomes de componentes QML claros; evitar abreviações obscuras.
- Nunca `from PySide6.QtWidgets import *`; importar só símbolos usados.

## Restrições

- Não trocar a toolkit de UI sem pedido explícito do usuário.
- Não reestruturar o projeto inteiro: limitar aos ficheiros/telas indicados, salvo autorização para alargar o escopo.

## Ver também

- [kirigami-plasma6-gui](../kirigami-plasma6-gui/SKILL.md) — se o refactor tocar muito em **QML** (contratos `objectName`, smoke).
- [pyside6-best-practices](../pyside6-best-practices/SKILL.md) — padrões gerais PySide6/QML.
