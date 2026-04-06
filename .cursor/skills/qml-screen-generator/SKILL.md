---
name: qml-screen-generator
description: Cria telas QML e integração PySide6 com src/app/core. Usar para nova tela/diálogo QML ou protótipo GUI; não para o CLI USB em avell_storm_rgb salvo pedido explícito.
---

# qml-screen-generator

**Âmbito:** **`src/app/ui/`** + **`src/app/core/`** (GUI). O CLI permanece em **`src/avell_storm_rgb/`** — ver [.cursor/rules/repo-context.mdc](../../rules/repo-context.mdc).

**Tooling:** ver [.cursor/rules/repo-context.mdc](../../rules/repo-context.mdc) (`uv`, não `pip` como fluxo principal).

## Objetivo

Criar telas QML completas e o Python necessário para as ligar ao backend, sem misturar negócio na UI.

## Quando usar

- Nova tela, diálogo ou peça visual em QML.
- Protótipo rápido de ecrã respeitando pastas e separação core/UI.

## Como agir

1. **Clarificar** (perguntar ou inferir do contexto):
   - Fluxo principal: dados in/out, ações do utilizador.
   - Que serviços em `src/app/core/` a tela precisa.
2. **Propor** antes de escrever ficheiros:
   - Caminho do QML: `src/app/ui/` ou `src/app/ui/components/`.
   - Contrato Python: propriedades, sinais, slots; onde vive o adaptador (ver abaixo).
3. **Gerir entregáveis**:
   - **QML**: esqueleto com propriedades essenciais, `signal` para eventos relevantes, handlers ligados ao contexto Python (`Connections` / chamadas a objectos raiz expostos).
   - **Python**: expor `@Property` / `Signal` / `Slot`; delegar trabalho a serviços existentes em `core/`.

## Padrão QML

- **Kirigami-first** para shell, layouts e controlos com equivalente — ver [.cursor/rules/kirigami-plasma6-qml.mdc](../../rules/kirigami-plasma6-qml.mdc); **Qt Quick Controls 2** onde Kirigami não chegar (com estilo de [`src/app/qml_paths.py`](../../../src/app/qml_paths.py)).
- `objectName` estável em nós que testes ou Python possam localizar.
- Negócio que cresça no JS do QML → mover para Python e expor só estado/resultado.

## Padrão Python

- Adaptadores UI (cola QML ↔ core): pasta coerente, por exemplo `src/app/ui/adapters/`.
- Classes **finas**: instanciam ou recebem serviços de `core/`; sem duplicar lógica de domínio.
- Type hints e docstrings curtas no adaptador descrevendo o contrato com o QML.

## Restrições

- Não adicionar dependências externas sem autorização explícita.
- Não duplicar serviços em `core/`; reutilizar e compor.

## Ver também

- [kirigami-plasma6-gui](../kirigami-plasma6-gui/SKILL.md) — checklist GUI e TDD neste repo.
- [pyside6-best-practices](../pyside6-best-practices/SKILL.md) — separação UI/lógica, propriedades/slots, performance.
