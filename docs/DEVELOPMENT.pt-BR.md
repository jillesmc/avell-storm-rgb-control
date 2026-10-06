[🇺🇸 English](DEVELOPMENT.md) · 🇧🇷 Português

# Desenvolvimento

⏱️ **Leitura:** ~6 min

> **TL;DR**
> - **Só `uv`** (lockfile `uv.lock`). Os alvos do `make` são só atalhos. Não documente `pip install`.
> - `make sync-all && make test` te dá tudo que roda sem hardware.
> - No fim da página há **receitas** para mudanças comuns. Siga passo a passo.

**Leia isto se…** você quer montar o ambiente, rodar, testar ou estender o projeto.

---

## 🛠️ Pré-requisitos

| Precisa | Para | Verificar |
|---------|------|-----------|
| Linux + **libusb** | tudo | — |
| **Python ≥ 3.10** (`.python-version` fixa 3.12) | tudo | `uv python list` |
| **[uv](https://docs.astral.sh/uv/)** | instalar, rodar, testar | `uv --version` |
| **Regra udev** ou root | falar com os dispositivos | `avell-storm-rgb device list` mostra os dispositivos |
| **Kirigami 6** (+ `qqc2-breeze-style`) da distro | GUI | `test -d /usr/lib/qt6/qml/org/kde/kirigami` |
| X11, **ou** Wayland + xdg-desktop-portal + PipeWire | follow-screen | — |

## 🛠️ Montar e rodar

| Comando | Faz |
|---------|-----|
| `make sync` | `uv sync --group dev` — CLI + pytest |
| `make sync-gui` | + extra `gui` (PySide6) |
| `make sync-screen` | + extra `screen` (Xlib, Pillow, pipewire-capture, numpy) |
| `make sync-all` | + os dois extras |
| `make run ARGS='device list'` | Roda a CLI |
| `make gui` | Roda a GUI |
| `make test` | `pytest -m "not hardware"` |
| `make test-all` | Todos os testes, inclusive `@hardware` |

**Regras udev** (salve em `/etc/udev/rules.d/99-avell-rgb.rules` e depois rode `udevadm control --reload-rules && udevadm trigger`):

```text
SUBSYSTEMS=="usb", ATTRS{idVendor}=="048d", ATTRS{idProduct}=="ce00", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="048d", ATTR{idProduct}=="7000", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="048d", ATTR{idProduct}=="7001", MODE="0666"
```

> [!TIP]
> Ajuste o `idProduct` do teclado para o seu (`6004`, `6006`, `ce00` ou `600b`). `lsusb | grep 048d` mostra qual é.

## 🛠️ Testes

| Arquivo | Cobre |
|---------|-------|
| `test_anim_dsl.py`, `test_ledbar_domain.py`, `test_per_key_grid_mapping.py` | Lógica pura de domínio |
| `test_ledbar_payload.py` | Bytes do efeito da barra de LED (**caracterização**) |
| `test_protocols.py` | Drivers batem com os protocolos de `ports` |
| `test_cli_help.py` | O parser da CLI monta e o `--help` funciona |
| `test_screen_follow_frame.py` | Frame → mapa de cores 16 × 6 (precisa de Pillow) |
| `test_usb_worker.py` | Sinais do worker, com e sem ocupado, falhas |
| `test_device_state.py`, `test_device_facade_usb_id.py` | Estado salvo: store, validação, restore; abrir por USB id |
| `test_keyboard_backend_light.py`, `test_led_bar_backend_light.py` | Backends com drivers falsos: visuais salvos, switch de luz |
| `test_keyboard_effect_supports.py` | Matriz `effectSupports` |
| `test_app_facade_memory.py`, `test_app_restore_integration.py` | Lembrar / esquecer, restauração ao abrir, migração (worker real, USB falso) |
| `test_cli_state.py` | Transcrições de `state show` / `state restore` |
| `test_gui_remembered_devices.py` | Entradas da barra lateral, switch de luz, página indisponível |
| `test_gui_smoke.py`, `test_gui_pages.py`, `test_gui_shell.py` | QML carrega; contratos de `objectName` |

- Os testes de GUI rodam **offscreen** (`QT_QPA_PLATFORM=offscreen`, definido em `tests/gui_helpers.py`).
- A maioria **pula** quando falta PySide6 ou Kirigami. Pular não é regressão.

> [!WARNING]
> `tests/test_gui_pages.py` importa PySide6 **antes** do `importorskip`. Sem o extra `gui`, a coleta **dá erro** em vez de pular. Rode `make sync-gui` (ou `sync-all`) antes do `make test`.

## 🛠️ Variáveis de ambiente e flags

| Nome | Efeito |
|------|--------|
| `--verbose` / `--debug` / `-v` (GUI) | Log em DEBUG + tracebacks completos das tarefas USB que falharem |
| `AVELL_STORM_RGB_LOG=debug` | O mesmo, via ambiente |
| `AVELL_DEBUG_FIRMWARE_UI=1` | Loga a agitação da aba de firmware (pedidos de apply, mudanças de largura do layout) |
| `AVELL_RGB_QQC2_STYLE=<estilo>` | Força um estilo do Qt Quick Controls (debug) |
| `QT_QUICK_CONTROLS_STYLE` | Respeitado quando a sessão define |
| `QML_IMPORT_PATH`, `QT_PLUGIN_PATH` | Raízes extras; os caminhos Qt6 do sistema entram na frente automaticamente |
| `keyboard --debug` (CLI) | Imprime cada pacote USB no stderr |
| `WAYLAND_DISPLAY` / `XDG_SESSION_TYPE` | Decidem follow-screen X11 vs Wayland |

## 🛠️ Receitas

### Adicionar um efeito de firmware do teclado

1. Adicione um builder em `KEYBOARD_EFFECTS` em `src/avell_storm_rgb/infrastructure/usb/ite8291_usb.py:102` (id do efeito + parâmetros suportados + padrões).
2. Estenda `tests/test_keyboard_effect_supports.py`. A tabela de parâmetros suportados (`KEYBOARD_EFFECT_PARAMS`) é derivada do builder.
4. Atualize [FEATURE_MATRIX](FEATURE_MATRIX.pt-BR.md) e [DEVICE_FEATURES_DEEP_DIVE](DEVICE_FEATURES_DEEP_DIVE.pt-BR.md) (nos dois idiomas).

As `choices` da CLI e a lista da GUI (`App.keyboardEffectNames`) pegam o novo efeito sozinhas.

### Adicionar um efeito da barra de LED

1. Adicione `nome: código` em `LED_BAR_EFFECT_CODES` em `src/avell_storm_rgb/infrastructure/usb/ite8233_usb.py:19`.
2. Atualize os docs como na receita do teclado. A CLI e a GUI pegam sozinhas.

### Adicionar um subcomando na CLI

1. Escreva `_cmd_<grupo>_<nome>(args) -> int` em `src/avell_storm_rgb/adapters/cli/main.py`. Abra dispositivos via `application.device_facade`.
2. Registre em `_build_parser()` com `.set_defaults(_handler=...)`.
3. Adicione uma checagem de `--help` em `tests/test_cli_help.py`.
4. Atualize o uso no README da raiz e a FEATURE_MATRIX.

### Adicionar uma ação na GUI (botão → USB)

1. No backend (`keyboard_backend.py` / `led_bar_backend.py`), adicione um `@Slot` que limita as entradas e embrulha o trabalho USB em `def task():`.
2. Chame `self._worker.submit(task)`. Use `show_busy=False` **só** em tarefas longas que o usuário pode parar.
3. Devolva resultados por um `Signal`. Use `QueuedConnection` se a task alterar estado do backend.
4. **Se a ação aplica um visual**, emita `persistUpdate` **depois** que a chamada ao driver deu certo, para ele virar o visual salvo. Nunca grave o `state.json` diretamente.
5. Chame do QML como `App.keyboard.<slot>(...)`. **Nunca** toque em USB pelo QML.
6. Adicione um teste do backend com os fakes de `tests/backend_fakes.py` (veja `test_*_backend_light.py`).

### Adicionar uma página ou aba QML

1. Crie `src/app/ui/pages/<Nome>.qml` e registre em `src/app/ui/pages/qmldir`.
2. Adicione no `StackLayout` e na navegação de `src/app/ui/main.qml`.
3. Dê um `objectName` estável aos nós importantes. Adicione em `tests/test_gui_pages.py` e/ou `test_gui_shell.py`.
4. Siga [`src/app/ui/AGENTS.md`](../src/app/ui/AGENTS.md) (Kirigami primeiro, cores do tema, HIG).

### Mudar um payload USB

> [!WARNING]
> Só com **prova no hardware** ou um **teste de caracterização** (como `tests/test_ledbar_payload.py`). Os bytes vêm de projetos upstream e quebram em silêncio com facilidade.

## 🛠️ Dicas de debug

- **Dispositivo não encontrado** → confira as regras udev, `lsusb | grep 048d`, e se o teclado reporta rev `0.03`.
- **GUI com cara de Qt puro** → instale `qqc2-breeze-style`; confira `/usr/lib/qt6/qml/org/kde/desktop`.
- **QML não carrega** → instale o Kirigami 6; o app imprime uma dica e sai com 1.
- **Luzes não foram restauradas** → `avell-storm-rgb state show`. Um arquivo quebrado vai para `state.json.invalid` e aparece como erro na página Devices.
- **`BadMatch` no X11** durante o follow-screen → XWayland ou região fora da tela.
- **GUI parece travada no USB** → provavelmente há um follow-screen ou uma animação em loop rodando. Aperte **Stop**.
