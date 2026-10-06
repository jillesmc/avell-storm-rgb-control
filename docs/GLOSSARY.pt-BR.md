[🇺🇸 English](GLOSSARY.md) · 🇧🇷 Português

# Glossário

⏱️ **Leitura:** consulta (≈ 1 min por seção)

> **TL;DR**
> - Uma tabela por área: **Hardware**, **Teclado**, **Barra de LED**, **Internos da GUI**, **Ferramentas**.
> - Cada termo aponta onde ele vive no código.
> - Os termos ficam **em inglês** nos dois idiomas, porque é assim que aparecem no código.

**Leia isto se…** uma palavra em outro doc ou no código não fez sentido.

---

## Hardware

| Termo | Significado | No código |
|-------|-------------|-----------|
| **ITE 8291** | Controlador RGB do teclado (rev 0.03). USB `048d:6004/6006/ce00/600b` | `infrastructure/usb/ite8291_usb.py` |
| **ITE 8233** | Controlador da barra de LED. USB `048d:7000/7001` ou nome do produto com `8233` | `infrastructure/usb/ite8233_usb.py` |
| **Control transfer** | Comando USB pequeno (8 bytes) para o dispositivo. Usado em quase todo comando | `_send_ctrl`, `_send` |
| **Row write** | Transferência OUT de 65 bytes com as cores de uma linha do teclado | `Ite8291UsbDevice._send_data` |
| **udev rule** | Regra do Linux que deixa usuários sem root abrirem o dispositivo USB | README da raiz |

## Teclado

| Termo | Significado | No código |
|-------|-------------|-----------|
| **Firmware effect** | Animação que roda **dentro** do controlador (breathing, wave…) | `KEYBOARD_EFFECTS` |
| **Effect packet** | `[control, effect, speed, brightness, color, direction\|reactive, save]` | `_set_effect_impl` |
| **User mode** | Modo em que o software define as cores (sólido, por tecla, animação, follow). Id de efeito `51` | `enable_user_mode` |
| **Palette slot** | Uma das **7** cores RGB guardadas no controlador (1–7) | `set_palette_color` |
| **Color index** | O byte `color` de um efeito. **Não é RGB**: slot 1–7, `8` = random, `0` = none | `KEYBOARD_PALETTE_SLOT_COLORS` |
| **Direction / reactive** | Dois significados do **mesmo byte**. Um efeito usa um ou outro | `_EffectAttrs` |
| **Save** | Flag do efeito que pede ao controlador para guardar o efeito | kwarg `save` |
| **Freeze** | Reenvia o efeito atual com velocidade `11` ("pausa" experimental) | `freeze()` |
| **Solid colour** | Modo usuário com todas as teclas no mesmo RGB | `set_color` |
| **Per-key / key grid** | Cor individual por célula de LED numa matriz **6 × 21** | `set_key_colors` |
| **Key ID** | Nome semântico de uma tecla física (`esc`, `space`, `kp_enter_top`…) mapeado para uma célula | `domain/per_key_grid.py` |
| **UI row vs device row** | Linha 0 da GUI = topo; linha 0 do dispositivo = base. `ui_row_to_device_row` inverte | `per_key_grid.py:182` |
| **Animation DSL** | Script de texto: `pos`, `apply`, `wait`, `clear`, `brightness`, `shift` | `domain/anim_dsl.py` |
| **Follow screen** | Amostra a tela / uma janela em 16 × 6 e pinta as teclas | `application/screen_follow*.py` |
| **Portal / PipeWire** | Jeito do Wayland de capturar uma janela: o usuário escolhe num diálogo do sistema | `screen_follow_wayland.py` |

## Barra de LED

| Termo | Significado | No código |
|-------|-------------|-----------|
| **LED bar palette** | Lista de até **9** cores RGB **enviada junto com cada efeito** (não são slots guardados) | `Ite8233UsbDevice.palette` |
| **Preset** | Paleta com nome: `rainbow`, `fire`, `ice`, `forest` | `domain/ledbar_colors.py` |
| **Visual effect** | `static`, `breathing`, `wave`, `impact`, `raindrop` | `LED_BAR_EFFECT_CODES` |
| **Effect report** | `[0x08, 0x22, effect, speed, brightness, num_colors, 0, 0]` | `_send_effect` |
| **With-effect** | Brilho e velocidade só são enviados **junto com** um efeito; a flag `--with-effect` da CLI escolhe qual | CLI `led-bar brightness/speed` |

## Internos da GUI

| Termo | Significado | No código |
|-------|-------------|-----------|
| **`App`** | O único objeto Python que o QML enxerga (`AppFacade`) | `ui/adapters/app_facade.py:37` |
| **Backend** | `KeyboardBackend` / `LedBarBackend`: lógica voltada ao QML, por dispositivo | `ui/adapters/*_backend.py` |
| **UsbWorker** | Thread única em segundo plano que roda toda tarefa USB em ordem | `core/usb_worker.py:16` |
| **Task** | Closure local `def task():` que um slot entrega ao `UsbWorker.submit` | backends |
| **Busy overlay / `show_busy`** | Véu "USB operation in progress…"; `show_busy=False` não mostra o véu | `BusyOverlay.qml`, `AppState` |
| **Debounce** | Timer de 200 ms que junta mudanças rápidas de slider/controle numa chamada USB | `QTimer` nos backends, `Timer` no QML |
| **Brightness target** | `GLOBAL_ONLY` ou `FIRMWARE_REAPPLY`: se o brilho também reenvia o efeito | `_BrightnessTarget` |
| **Palette mirror** | Cópia de sessão das cores de slot que a GUI escreveu (o dispositivo não pode ser lido) | `_palette_mirror` |
| **Effect snapshot** | Bytes do efeito salvos ao desligar, repetidos ao ligar | `_last_effect_snapshot` |
| **Replay record** | Última ação da barra de LED (`color`, `palette`, `effect`, `tune*`) para repetir ao ligar | `_last_replay` |
| **Epoch** | Contador incrementado para forçar o QML a reler (`deviceConnectionEpoch`, `keyGridEpoch`) | facade / backend |
| **Close to tray** | Fechar a janela só esconde; sair pela bandeja | `ui/closeToTray` |
| **Auto-connect** | Conecta o primeiro teclado e a primeira barra após a varredura inicial | `ui/autoConnectOnStartup` |

## Ferramentas

| Termo | Significado |
|-------|-------------|
| **uv** | Gerenciador de pacotes / venv usado para tudo (`uv sync`, `uv run`) |
| **Extra** | Conjunto opcional de dependências: `gui`, `screen` |
| **Marcador `hardware`** | Marcador do pytest para testes que precisam dos dispositivos reais (pulados pelo `make test`) |
| **Kirigami** | Framework de UI em QML do KDE; vem da distro, **não** do PyPI |
| **Estilo QQC2 / `org.kde.desktop`** | Visual Breeze para o Qt Quick Controls; cai para `Fusion` se faltar |
| **Contrato de `objectName`** | Nomes QML estáveis que os testes procuram; renomear quebra os testes |
