[🇺🇸 English](DEVICE_FEATURES_DEEP_DIVE.md) · 🇧🇷 Português

# Dispositivos RGB: capacidades, combinações e UI

⏱️ **Leitura:** ~10 min

> **TL;DR**
> - **Teclado (8291):** efeitos de firmware **ou** modo usuário (cores por software). Um substitui o outro. A "cor" de um efeito é um **índice de slot da paleta**, não RGB.
> - **Barra de LED (8233):** brilho e velocidade só são enviados **dentro de um efeito**, então mudar qualquer um deles sempre reaplica um efeito.
> - A GUI **desabilita** os controles que o efeito não usa (`effectSupports`), e o backend **filtra** os parâmetros (`EFFECT_KWARGS`).

**Leia isto se…** você precisa saber qual parâmetro funciona com qual efeito, o que exclui o quê, e como a UI se liga ao backend.

Fontes: o código em `src/avell_storm_rgb/` e `src/app/`, cruzado com o [ite8291r3-ctl](https://github.com/pobrn/ite8291r3-ctl) e o script `ledbar` do **ite8233-ledbar**.

---

## 🧭 Resumo executivo

| Aspecto | ITE 8291 (teclado) | ITE 8233 (barra de LED) |
|---------|--------------------|-------------------------|
| **Modo principal "firmware"** | Efeitos embutidos (`breathing`, `wave`, …), pacote de efeito de 6 bytes | `static`, `breathing`, `wave`, `impact`, `raindrop` com paleta + parâmetros no report HID |
| **Cor uniforme** | `set_color` (modo usuário + escrita por linha), RGB livre | `set_static_rgb` (uma cor na paleta + `static`) |
| **Por tecla / animação** | Grade 6 × 21, DSL de animação, `set_key_colors` | Não suportado |
| **Seguir a tela** | Sim (extra `[screen]`) | Não |
| **Brilho** | 0–50: comando dedicado **e** um byte no pacote de efeito | 0–100: guardado no driver Python, enviado no próximo `_send_effect` |
| **"Paleta"** | **Slots 1–7** na memória do controlador + índice semântico no efeito | **Lista de até 9** cores RGB enviadas ao dispositivo |

## 🏗️ ITE 8291 — modelo mental

### Dois caminhos de iluminação

1. **Efeito de firmware.** `set_effect(payload)` faz o controlador rodar uma animação interna. O payload tem `effect`, `speed`, `brightness`, `color`, um byte de direção **ou** reativo, e `save`.
2. **Modo usuário** (sólido / por tecla). `enable_user_mode` mais dados **linha a linha** (`set_color`, `set_key_colors`, DSL de animação, follow-screen). O software decide as cores.

> [!NOTE]
> Trate os dois como **modos que se substituem**. Aplicar um efeito de firmware sai do modo usuário. Sólido, por tecla e follow-screen entram no modo usuário.

### Brilho: dois mecanismos

- **`SET_BRIGHTNESS`** (`keyboard brightness` / `set_brightness`): brilho global do controlador (0–50).
- **Byte de brilho dentro do `SET_EFFECT`:** toda chamada de efeito envia um. Se for omitido, vale o padrão **25** do builder em `KEYBOARD_EFFECTS`.

> [!WARNING]
> **Aplicar um efeito pode redefinir o brilho** se você não passar `-b` (igual ao upstream). A GUI evita isso: na aba **Effect**, toda mudança reenvia o pacote com o brilho atual do slider, e o slider da seção **Device** reenvia o último efeito (veja [FLOWS § 4](FLOWS.pt-BR.md#-4--slider-de-brilho)).

### "Cor" do efeito ≠ RGB livre

O campo `color` é um **índice** (`KEYBOARD_PALETTE_SLOT_COLORS` em `ite8291_usb.py`):

| Nome na CLI / GUI | Valor enviado | Significado no firmware |
|-------------------|---------------|-------------------------|
| `none` | 0 | Sem cor de slot. O efeito pode ficar invisível (o upstream não recomenda) |
| `red` … `purple` | 1–7 | **Referência ao slot N** da paleta do teclado. Mude o slot 3 e `-c yellow` muda junto |
| `random` | 8 | Uso "aleatório" / multicor da paleta, conforme o efeito |

- **`keyboard palette set-slot …`** preenche a tabela.
- **`-c` / o combo "palette slot colour"** escolhe **qual entrada** o efeito usa.
- Como diz o upstream: *os nomes podem enganar — `red` é só a primeira cor da paleta no esquema padrão.*

### Direção vs reativo: mesmo byte, exclusivos por desenho

`effect_attrs.DIRECTION` e `effect_attrs.REACTIVE` dividem o **índice 4** do array do efeito.

- **CLI:** grupo mutuamente exclusivo, `--direction` **ou** `--reactive`.
- **GUI:** cada controle só fica **habilitado quando o efeito selecionado usa aquele parâmetro** (`effectSupports`). `_effect_kwargs` envia só os parâmetros suportados.

### Matriz efeito × parâmetro

**sim** = enviado e usado pelo builder · **—** = não faz parte do efeito.

| Efeito | speed (0–10) | brightness (0–50) | color (slot) | direction | reactive | save |
|--------|--------------|-------------------|--------------|-----------|----------|------|
| `breathing` | sim | sim | sim | — | — | sim |
| `wave` | sim | sim | — | sim | — | sim |
| `random` | sim | sim | sim | — | sim | sim |
| `rainbow` | — | sim | — | — | — | sim |
| `ripple` | sim | sim | sim | — | sim | sim |
| `marquee` | sim | sim | — | — | — | sim |
| `raindrop` | sim | sim | sim | — | — | sim |
| `aurora` | sim | sim | sim | — | sim | sim |
| `fireworks` | sim | sim | sim | — | sim | sim |

- **Brilho:** todos os efeitos, inclusive `rainbow`.
- **Velocidade:** todos menos `rainbow`.
- **Cor:** efeitos sem cor mantêm o índice padrão do builder; a GUI só oferece brilho e `save` para eles.

### Outras capacidades do teclado

- **`keyboard power off` / `powerOnReplay` da GUI:** desliga; ligar pela GUI repete um snapshot do último efeito.
- **`freeze`:** põe `speed` em 11 no efeito atual (gambiarra experimental).
- **`palette restore | random | set-slot`:** só muda os slots 1–7. **Não** troca de efeito sozinho.

## 🏗️ ITE 8233 — modelo mental

### Paleta da barra ≠ slot de paleta do teclado

- A barra mantém em software uma **`list[tuple[int,int,int]]`** (`self.palette`), com até **`MAX_LED_BAR_PALETTE = 9`** cores.
- `CMD_COLOR` envia cada cor para um índice de slot. `_send_effect` envia `num_colors = len(palette)` se houver mais de uma cor, senão **1**.
- **Presets** (`rainbow`, `fire`, `ice`, `forest`) ou uma lista `r,g,b,…` preenchem a lista antes do `apply_visual_effect`.

### Efeitos e códigos

| Nome | Código |
|------|--------|
| `static` | `0x01` |
| `breathing` | `0x02` |
| `wave` | `0x03` |
| `impact` | `0x04` |
| `raindrop` | `0x06` |

### Brilho e velocidade

- `set_brightness_level` / `set_motion_speed` só atualizam **`self.brightness`** / **`self.speed`** no Python.
- O hardware só vê os valores quando **`apply_visual_effect`** chama **`_send_effect`**.

> [!TIP]
> **Funciona com qualquer efeito?** Pela API, sim: reaplique qualquer efeito depois de mudar brilho ou velocidade. **Visualmente**, o brilho muda o `static` com clareza. Se a velocidade muda algo no `static` ainda precisa de **validação no hardware**.

### Fluxos típicos

- **Cor única:** `set_static_rgb` → paleta `[uma cor]` + `static`.
- **Paleta + animação:** `set_palette_colors` + `apply_visual_effect(nome)`.
- **Só trocar o efeito:** reaproveita a paleta e o último brilho / velocidade guardados no objeto `Ite8233UsbDevice`.

## ⚠️ Exclusividade e transições

| Situação no teclado | Comportamento |
|---------------------|---------------|
| `power off` | Luzes apagadas; a GUI guarda um snapshot para replay |
| `set_effect` vs modo usuário | A transição substitui o "motor" visual ativo |
| `--direction` vs `--reactive` (CLI) | **Exclusivos** (mesmo byte do protocolo) |
| Direção / reativo (GUI) | Só o que o efeito suporta fica habilitado |
| `freeze` | Mudança pontual no array do efeito (velocidade 11) |

| Situação na barra | Comportamento |
|-------------------|---------------|
| `power off` | Sequência de desligar; a animação para |
| `power on` | Sequência de inicialização; o `powerOnReplay` da GUI repete o último modo |

## 🔁 Rastro UI ↔ backend

### Teclado (`KeyboardPage.qml` + `main.qml`)

A sub-navegação (`keyboardSubNavIndex` 0…6) controla o `StackLayout` interno. Ela é agrupada sob os cabeçalhos **Firmware**, **User-defined** e **Extra** (título + traço horizontal).

| # | Aba | Botão "Apply"? | Chamada principal no backend |
|---|-----|----------------|------------------------------|
| 0 | Effect | Não — automático, debounce de ~200 ms após uma mudança | `applyEffect(…)` |
| 1 | Palette slot configuration | Sim | `setPaletteSlotRgb(slot, r, g, b)` — só grava o slot |
| 2 | Solid color | Não — automático, debounce de ~200 ms | `setSolidNamed` / `setSolidRgb` |
| 3 | Per-key grid | Sim | `applyKeyGrid(true)` |
| 4 | Animation file | Não | `playAnimationFile` / `stopFollowOrAnimation` |
| 5 | Follow screen | Não | `startFollowScreen` / `stopFollowOrAnimation` |
| 6 | Tools | Não | `demoTestPattern`, `freezeAnimation` (imediatos) |

- **Bloco Device (brilho):** escondido nas abas **1** e **6**. Mostrado como **0–100 %** e convertido para 0–50; com debounce via `requestBrightnessFromUi`.
- **Aba Effect:** abrir a aba ou redimensionar a janela **nunca** reenvia. Só uma mudança do usuário reenvia.
- **Combo de cor do firmware:** mostra slot 1–7, `#RRGGBB` e uma amostra. Usa o espelho de sessão; sem entrada no espelho, `paletteSlotR/G/B` devolve a **paleta padrão do firmware**.
- **Por tecla:** um layout de teclado real (rótulos, larguras variáveis). Clique = uma tecla; arrastar = lote. Cada tecla tem um `keyId`; `per_key_grid.py` mapeia `keyId → (row, col)`.
- **Mapeamento de linhas:** a linha 0 do dispositivo é a **base**. O per-key da GUI passa por `color_map_ui_to_device`. **DSL de animação e follow-screen mantêm coordenadas do dispositivo**, por compatibilidade.

### Barra de LED (`LedBarPage.qml`)

| # | Aba | Ação |
|---|-----|------|
| 0 | Color (named / hex) | `setColorFromSpec` |
| 1 | Preset + effect | `applyPalette(spec, effect)` |
| 2 | Effect only | `applyEffect` |
| 3 | Brightness & motion | `applyBrightnessSpeedEffect` |

- **Bloco Device:** um slider de brilho 0–100 → `requestBrightnessFromUi(value, selectedEffect)` (com debounce). Reaplica o último modo conhecido, ou o efeito escolhido na casca.

## 🛠️ Debug da aba Firmware

1. Exporte `AVELL_DEBUG_FIRMWARE_UI=1` (ou `true` / `yes` / `on`) antes de abrir o app.
2. **stderr do Python:** cada `KeyboardBackend.applyEffect` imprime uma linha com os parâmetros.
3. **Console do Qt** (`console.log`): `requestFirmwareEffectApply`, `pushFirmwareEffectToDevice`, disparos do timer de debounce.
4. A cada **1 s** na aba Firmware sai um resumo: `scrollBodyWidth+`, `paletteMirror+`, `req+`, `push+`.

> [!TIP]
> Se `scrollBodyWidth+` subir para as centenas ao redimensionar, há agitação de layout. O `ScrollView` usa uma **calha fixa à direita** para a barra de rolagem, evitando a oscilação largura ↔ reflow.

## 🛠️ Referência rápida da CLI

```bash
uv run avell-storm-rgb keyboard effect wave -s 3 -b 40 -d up        # efeito com parâmetros
uv run avell-storm-rgb keyboard effect aurora -r -s 2 -c red        # reativo (sem direção)
uv run avell-storm-rgb keyboard palette set-slot 2 255,128,0        # slot 2 = "orange"
uv run avell-storm-rgb keyboard effect breathing -c orange          # usa o slot 2
uv run avell-storm-rgb keyboard inspect --fw-version --brightness --power
uv run avell-storm-rgb led-bar palette rainbow --with-effect wave
uv run avell-storm-rgb led-bar brightness 80 --with-effect breathing
```

## 🛠️ Checklist de validação no hardware

1. **Teclado `rainbow`:** mude velocidade e cor → só o **brilho** (e o `save`) deveriam mudar algo.
2. **Teclado `wave`:** alterne a direção. O reativo fica desabilitado na GUI para `wave`.
3. **Teclado `random` / `ripple`:** ative o reativo. Combinar com direção na CLI tem que ser rejeitado pelo argparse.
4. **Paleta do teclado:** `palette set-slot 1 255,0,0`, depois compare `-c red` vs `-c orange` mudando só o slot 1.
5. **Barra `static`:** mude só a velocidade com brilho fixo. A animação estática muda?
6. **Ordem na barra:** aqui `led-bar brightness` **sempre** reaplica `--with-effect` (scripts antigos não enviavam o brilho sozinho).

## 🧭 Arquivos principais

| Tema | Caminho |
|------|---------|
| Protocolo e efeitos do 8291 | `src/avell_storm_rgb/infrastructure/usb/ite8291_usb.py` |
| Filtro de kwargs na GUI | `src/app/ui/adapters/keyboard_backend.py` (`EFFECT_KWARGS`, `_effect_kwargs`) |
| UI do teclado | `src/app/ui/pages/KeyboardPage.qml`, `src/app/ui/main.qml` |
| Protocolo do 8233 | `src/avell_storm_rgb/infrastructure/usb/ite8233_usb.py` |
| Cores / paletas da barra | `src/avell_storm_rgb/domain/ledbar_colors.py` |
| UI da barra | `src/app/ui/pages/LedBarPage.qml`, `src/app/ui/adapters/led_bar_backend.py` |
| CLI | `src/avell_storm_rgb/adapters/cli/main.py` |

## 🧭 Cópias locais do upstream (opcional)

- `/home/jilles/git/ite8291r3-ctl/`: mesma matriz de efeitos e notas sobre `color` / paleta (README, *Effect property support matrix*).
- `/home/jilles/git/ite8233-ledbar/ledbar`: mesmos códigos de efeito, paleta, brilho e velocidade, com reaplicação implícita.

Esses caminhos só existem na máquina do mantenedor. Use-os para comparar o comportamento com o código portado.
