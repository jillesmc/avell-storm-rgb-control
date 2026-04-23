# Dispositivos RGB: capacidades, combinações e UI

Este documento descreve o que o **ITE 8291** (retroiluminação do teclado) e o **ITE 8233** (barra LED) fazem ao nível de protocolo e de API deste repositório, **quais parâmetros se aplicam a cada efeito**, o que é **mutuamente exclusivo**, e como isso se reflete na **interface QML**. Foi elaborado a partir do código em `src/avell_storm_rgb/` e `src/app/`, cruzado com os projetos de referência locais [`ite8291r3-ctl`](https://github.com/pobrn/ite8291r3-ctl) e o script `ledbar` do repositório **ite8233-ledbar**.

### Debug (travamentos / CPU na aba Firmware)

- Exportar `AVELL_DEBUG_FIRMWARE_UI=1` (ou `true`/`yes`/`on`) antes de arrancar a app.
- No **stderr** Python: cada `KeyboardBackend.applyEffect` imprime uma linha com os parâmetros.
- Na **consola Qt** (onde `console.log` aparece): pedidos `requestFirmwareEffectApply`, `pushFirmwareEffectToDevice`, disparos do timer de debounce, e a cada **1 s** na aba Firmware um resumo `scrollBodyWidth+` (quantas vezes a largura útil do scroll mudou — se subir ao centenas ao redimensionar, há churn de layout), `paletteMirror+`, `req+`, `push+`.

### UI (agrupamento e brilho)

- **Teclado** ([`KeyboardPage.qml`](src/app/ui/pages/KeyboardPage.qml) + [`main.qml`](src/app/ui/main.qml)): o `ScrollView` usa **gutter fixo à direita** para a barra vertical (em vez de `rightPadding` condicionado ao conteúdo), para evitar oscilação largura ↔ reflow ↔ altura junto ao limite de scroll. O texto fechado do combo de cor de firmware é **atualizado só** quando mudam o índice ou o espelho da paleta (não em cada reflow). A secção **Device** (cabeçalho + texto + brilho) está **oculta** nas abas **Palette slot configuration** e **Tools**; noutras abas o brilho mostra-se como **0–100%** (convertido para 0–50 no USB); o movimento do slider chama `requestBrightnessFromUi` (debounce ~200 ms no [`KeyboardBackend`](src/app/ui/adapters/keyboard_backend.py)): envia `set_brightness` e, se o último modo aplicado pelo utilizador foi um **efeito de firmware**, volta a emitir o mesmo efeito com o novo brilho. No separador **Effect** (firmware), o envio ao dispositivo só ocorre **depois de o utilizador alterar** um controlo (efeito, tempo de ciclo, cor, direção, opções), com debounce ~200 ms; abrir a aba ou redimensionar a janela **não** reaplica o efeito. O botão **Apply** do rodapé só serve **Palette slot configuration** e **Per-key grid**; **Solid** aplica-se automaticamente (debounce ~200 ms) na respetiva aba. A sub-navegação do teclado na coluna do meio agrupa entradas em **Firmware**, **User-defined**, **Extra**, com cabeçalhos **não clicáveis** no estilo da barra lateral: **título + traço horizontal**. O combo de cor de paleta no firmware mostra **slot 1–7**, **#RRGGBB** e um **quadrante de cor**: usa o espelho de sessão quando existir; **sem entrada no espelho**, `paletteSlotR/G/B` devolve a **paleta por defeito do firmware** (a mesma que `restore_default_palette` / `_DEFAULT_PALETTE` no backend), na ordem dos slots 1–7. Controlos de tempo de ciclo / cor / direção / reactive / save ficam **desativados** quando o efeito selecionado não os usa (`effectSupports` + `EFFECT_KWARGS`). No conteúdo em scroll mantêm-se títulos como **Firmware (controlador)**, **Software (user)**, **Device · palette slots**, **Extra / tools**. **Animation file** e **Follow screen** são **abas separadas** no stack: na primeira, **Stop animation** junto de **Play**; na segunda, **Start following** e **Stop following**.
- **Barra LED** ([`LedBarPage.qml`](src/app/ui/pages/LedBarPage.qml)): mesma ideia — secção **Device** com brilho 0–100 e `requestBrightnessFromUi` / debounce no [`LedBarBackend`](src/app/ui/adapters/led_bar_backend.py), re-aplicando o último modo conhecido ou o efeito atualmente escolhido no *shell*. Removido o botão “Set brightness + effect” do cabeçalho; o combo rápido do cabeçalho foi integrado à lógica do *shell* nos separadores existentes.

---

## Resumo executivo

| Aspeto | ITE 8291 (teclado) | ITE 8233 (barra LED) |
|--------|--------------------|----------------------|
| **Modo principal “firmware”** | Efeitos integrados (`breathing`, `wave`, …) com pacote de 6 bytes no report de efeito | Efeitos `static`, `breathing`, `wave`, `impact`, `raindrop` com paleta e parâmetros no report HID |
| **Cor uniforme** | `set_color` (modo utilizador + envio por linhas) — RGB livre | `set_static_rgb` (uma cor na paleta + efeito `static`) |
| **Cores por tecla / animação** | Grelha 6×21, DSL de animação, `set_key_colors` | Não suportado |
| **Seguir ecrã** | Suportado (extra `[screen]` no projeto) | Não |
| **Brilho** | 0–50: comando dedicado **e** byte no pacote de efeito | 0–100: guardado no driver Python e enviado no próximo `_send_effect` |
| **“Paleta”** | **Slots 1–7** na memória do controlador + índice semântico no efeito (`red`…`purple`, `random`, `none`) | **Lista de até 9** cores RGB enviadas ao dispositivo; efeitos animados percorrem essa lista |

---

## ITE 8291 — modelo mental

### Dois “caminhos” de iluminação

1. **Efeito de firmware** — `set_effect(payload)`: o controlador corre uma animação interna. O payload inclui `effect`, `speed`, `brightness`, `color`, byte de direção **ou** reatividade, e `save`.
2. **Modo utilizador (per-key / cor sólida)** — `enable_user_mode` + envio de dados por **linha** (`set_color`, `set_key_colors`, animação DSL, follow-screen): o firmware deixa de ser a “fonte” da animação global e passa a mostrar cores definidas por software.

**Na prática**, ao aplicar um efeito de firmware substitui-se o modo atual de animação integrada; ao aplicar sólido/per-key/follow entra-se no modo utilizador. O utilizador deve tratar estes como **modos que se substituem** no uso normal (o documento upstream também descreve efeitos vs. `monocolor` / `anim` de forma separada).

### Brilho: dois mecanismos

- **`SET_BRIGHTNESS`** (`keyboard brightness` / `set_brightness`): altera o brilho global do controlador (0–50).
- **Byte de brilho dentro de `SET_EFFECT`**: cada chamada a `keyboard effect …` ou `applyEffect` envia um brilho no pacote; valores omitidos usam o **default 25** definido em `KEYBOARD_EFFECTS` (comportamento alinhado ao [README do ite8291r3-ctl](https://github.com/pobrn/ite8291r3-ctl): aplicar um efeito pode **redefinir** o brilho se não for passado explicitamente).

**Combinável?** Sim, no sentido de que pode primeiro ajustar com `keyboard brightness` e depois aplicar um efeito com `-b`; o efeito **pode** voltar a fixar outro valor. Na GUI, o slider na secção **Device** aplica-se em tempo real (ver “UI” acima); no separador **Effect** (firmware), cada alteração reenvia o pacote de efeito com o brilho atual (0–50) derivado do slider em **percentagem**.

### “Cor” no efeito ≠ RGB livre

O campo `color` no pacote **não** é um triplete RGB. É um **índice** mapeado em `KEYBOARD_PALETTE_SLOT_COLORS` (`src/avell_storm_rgb/infrastructure/usb/ite8291_usb.py`):

| Nome no CLI/GUI | Valor enviado | Significado no firmware |
|-----------------|---------------|-------------------------|
| `none` | 0 | Sem cor de slot (efeito pode ficar invisível — o upstream avisa para não usar `none` como cor principal) |
| `red` … `purple` | 1–7 | **Referência ao slot N da paleta** guardada no teclado (não “vermelho Pantone” fixo): se alterar o slot 3 na paleta, `-c yellow` (slot 3 no mapa semântico padrão) passa a ser a cor desse slot. |
| `random` | 8 | Uso “aleatório” / multi-cor da paleta conforme o efeito |

Ou seja: **`keyboard palette set …`** (slots 1–7 com RGB) **define a tabela**; **`-c` / combo “Palette slot colour”** escolhe **qual entrada** o efeito usa (ou `random`). Isto replica a nota do ite8291r3-ctl: *os nomes podem enganar — `red` é a primeira cor da paleta no esquema padrão*.

### Direção vs reativo — mesmo byte, exclusivos por desenho

Em `ite8291_usb.py`, `effect_attrs.DIRECTION` e `effect_attrs.REACTIVE` têm o **mesmo índice (4)** no array do efeito: ou o byte significa direção, ou “reativo”, consoante o efeito.

- A **CLI** usa grupo mutuamente exclusivo: `--direction` **ou** `--reactive`.
- A **GUI** mostra **sempre** o `ComboBox` de direção e o `CheckBox` “Reactive”; o `KeyboardBackend._effect_kwargs` **só inclui** o parâmetro que o efeito suporta — o outro é ignorado (o valor enviado fica o default do builder).

### Matriz efeito × parâmetros (código deste repo)

Legenda: **sim** = enviado e usado pelo builder; **—** = não faz parte do efeito (GUI/CLI não devem assumir efeito visível).

| Efeito | speed (0–10) | brightness (0–50) | color (índice slot) | direction | reactive | save |
|--------|----------------|-------------------|---------------------|-----------|----------|------|
| `breathing` | sim | sim | sim | — | — | sim |
| `wave` | sim | sim | — | sim | — | sim |
| `random` | sim | sim | sim | — | sim | sim |
| `rainbow` | — | sim | — | — | — | sim |
| `ripple` | sim | sim | sim | — | sim | sim |
| `marquee` | sim | sim | — | — | — | sim |
| `raindrop` | sim | sim | sim | — | — | sim |
| `aurora` | sim | sim | sim | — | sim | sim |
| `fireworks` | sim | sim | sim | — | sim | sim |

**Brilho:** qualquer efeito na tabela inclui `brightness` no pacote (incluindo `rainbow`). **Velocidade:** todos exceto `rainbow`. **Cor (slot):** todos com “sim” na coluna `color` — para efeitos sem `color`, o índice no hardware fica o default do builder (não há controlo útil na UI para isso além do brilho/`save`).

### Outras capacidades (teclado)

- **`keyboard power off` / `powerOnReplay`**: desliga; “power on” com replay restaura snapshot do último efeito quando disponível.
- **`freeze`**: coloca `speed` a 11 no snapshot atual (hack experimental).
- **`palette restore|random|set`**: só altera slots 1–7 na memória do teclado; **não** muda sozinho para um efeito novo.
- **Sólido / grelha / animação / follow-screen**: ver secção “Traço UI ↔ backend”.

---

## ITE 8233 — modelo mental

### Paleta na barra ≠ palette slot do teclado

- A barra mantém em software uma **`list[tuple[int,int,int]]`** (`self.palette`), até **`MAX_LED_BAR_PALETTE` = 9** (`ledbar_colors.py`).
- `CMD_COLOR` envia cada cor para um índice de slot no protocolo da barra; **`_send_effect`** calcula `num_colors = len(palette)` se houver mais de uma cor, senão **1**.
- **Presets** (`rainbow`, `fire`, …) ou lista `r,g,b,...` alimentam essa lista antes de `apply_visual_effect`.

### Efeitos e códigos

| Nome | Código (hex) |
|------|----------------|
| `static` | 0x01 |
| `breathing` | 0x02 |
| `wave` | 0x03 |
| `impact` | 0x04 |
| `raindrop` | 0x06 |

### Brilho e velocidade

- `set_brightness_level` / `set_motion_speed` apenas atualizam **`self.brightness`** e **`self.speed`** no objeto Python.
- O hardware só recebe novos valores quando **`apply_visual_effect`** (ou fluxo equivalente) chama **`_send_effect`**, que inclui `self.speed`, `self.brightness` e o código de efeito.

**Combinável com qualquer efeito?** Em termos de **API**, sim: qualquer efeito pode ser re-aplicado depois de mudar brilho/velocidade (é o padrão `setBrightnessWithEffect`, `led-bar brightness … --with-effect`, etc.). **Na perceção visual**, para **`static`** brilho altera o byte enviado (pode ser notável); a **velocidade** também é enviada no mesmo report — convém **validar no hardware** se altera algo visível em `static` ou é essencialmente irrelevante.

### Fluxos típicos

- **Cor única:** `set_static_rgb` → paleta `[uma cor]` + efeito `static`.
- **Paleta + animação:** `set_palette_colors` + `apply_visual_effect(nome)`.
- **Só mudar efeito:** reutiliza paleta e últimos brilho/velocidade em memória no objeto `Ite8233UsbDevice`.

---

## Exclusividade e transições

### Teclado (8291)

| Situação | Comportamento |
|----------|----------------|
| `power off` | Iluminação apagada; outros estados podem ser guardados para replay conforme implementação do backend |
| `set_effect` vs modo utilizador | Transição substitui o “motor” visual dominante |
| `--direction` vs `--reactive` na CLI | **Exclusivos** (mesmo byte no protocolo) |
| Direção + reactive na GUI | **Ambos visíveis**; só um tem efeito por tipo de efeito |
| `freeze` | Alteração pontual do array de efeito (velocidade 11) |

### Barra (8233)

| Situação | Comportamento |
|----------|----------------|
| `power off` | Sequência de desligar; apaga animação |
| `power on` | Inicialização; a GUI pode chamar `powerOnReplay` para repetir último modo |

---

## Traço UI ↔ backend

### Teclado (`KeyboardPage.qml` + `main.qml`)

O separador lateral (`keyboardSubNavIndex` 0…6) corresponde ao `StackLayout` interno. Na shell, a lista está **agrupada em secções** (Firmware, User-defined, Extra) com **título + traço horizontal** como na barra lateral principal; os índices 0…6 são os mesmos.

| Índice | Título (traduzível na app) | Botão “Apply” | Ação principal ao aplicar |
|--------|----------------------------|---------------|---------------------------|
| 0 | Effect (firmware) | Não (auto com debounce ~200 ms ao editar) | `KeyboardBackend.applyEffect(…)` |
| 1 | Palette slot configuration | Sim | `setPaletteSlotRgb(slot, r, g, b)` — **só** grava RGB no slot do teclado |
| 2 | Solid color | Não (auto com debounce ~200 ms na aba) | `setSolidNamed` ou `setSolidRgb` |
| 3 | Per-key grid | Sim | `applyKeyGrid(true)` |
| 4 | Animation file | Não | `playAnimationFile` / `stopFollowOrAnimation` (animação) |
| 5 | Follow screen | Não | `startFollowScreen` / `stopFollowOrAnimation` |
| 6 | Tools | Não | `demoTestPattern`, `freezeAnimation` (ações imediatas) |

**Bloco Device (brilho)** no topo do scroll do teclado: **oculto** nas abas **Palette slot configuration** e **Tools** (índices 1 e 6); visível nas restantes.

**Controlos do separador 0 (efeito firmware) sempre visíveis:** velocidade, combo “cor da paleta”, direção, reactive, save. O Python **filtra** com `EFFECT_KWARGS`; para muitos efeitos, **direção ou reactive não fazem nada**, e para `rainbow` **velocidade e cor de slot** não entram no pacote.

**Lacuna de UX/documentação:** o tooltip da direção na UI menciona *marquee*, mas **`marquee` não envia direção** no protocolo deste repo (alinha à matriz upstream: direção “—” para marquee). O utilizador pode achar que a direção afeta `marquee`, mas o valor é ignorado.

### Barra (`LedBarPage.qml`)

| Índice | Título | “Apply” / ação |
|--------|--------|----------------|
| 0 | Color (named / hex) | `setColorFromSpec` |
| 1 | Preset + effect | `applyPalette(spec, effect)` |
| 2 | Effect only | `applyEffect` |
| 3 | Brightness & motion | `applyBrightnessSpeedEffect` |

O slider de brilho no topo pode ser usado com o botão “Set brightness + effect” (`setBrightnessWithEffect`) sem passar pelo Apply do separador.

---

## Referência rápida CLI (`avell-storm-rgb`)

Comandos úteis para validar o comportamento descrito (com dispositivo ligado e permissões USB):

```bash
# Teclado — efeito com parâmetros
uv run avell-storm-rgb keyboard effect wave -s 3 -b 40 -d up

# Teclado — matriz de exclusão direção vs reactive (reactive só em efeitos que suportam)
uv run avell-storm-rgb keyboard effect aurora -r -s 2 -c red

# Teclado — paleta (slots 1–7) e depois efeito que usa “cor”
uv run avell-storm-rgb keyboard palette set 2 255,128,0
uv run avell-storm-rgb keyboard effect breathing -c orange

# Teclado — inspeção
uv run avell-storm-rgb keyboard inspect --fw-version --brightness --power

# Barra — paleta + efeito
uv run avell-storm-rgb led-bar palette rainbow --with-effect wave

# Barra — brilho e re-aplicar efeito
uv run avell-storm-rgb led-bar brightness 80 --with-effect breathing
```

---

## Checklist de validação no hardware

1. **Teclado — `rainbow`:** mudar velocidade e cor no separador firmware; confirmar que **só o brilho** (e `save`) altera o resultado.
2. **Teclado — `wave`:** alternar direção; ativar “Reactive” e confirmar que **não** há reatividade (valor ignorado).
3. **Teclado — `random` / `ripple`:** ativar reactive; tentar combinar com direção na CLI (deve ser rejeitado pelo argparse).
4. **Teclado — paleta:** `palette set 1` para vermelho puro; efeito com `-c red` vs `-c orange` após mudar só o slot 1.
5. **Barra — `static`:** mudar só velocidade com brilho fixo; notar se a animação “estática” muda.
6. **Barra — ordem:** `brightness` sem re-aplicar efeito na CLI antiga não enviaria ao HW — neste projeto **`led-bar brightness` sempre re-aplica** `--with-effect`.

---

## Ficheiros principais no repositório

| Tópico | Caminho |
|--------|---------|
| Protocolo e efeitos 8291 | `src/avell_storm_rgb/infrastructure/usb/ite8291_usb.py` |
| Filtro de kwargs na GUI | `src/app/ui/adapters/keyboard_backend.py` (`EFFECT_KWARGS`, `_effect_kwargs`) |
| UI teclado | `src/app/ui/pages/KeyboardPage.qml`, `src/app/ui/main.qml` |
| Protocolo 8233 | `src/avell_storm_rgb/infrastructure/usb/ite8233_usb.py` |
| Cores / paletas barra | `src/avell_storm_rgb/domain/ledbar_colors.py` |
| UI barra | `src/app/ui/pages/LedBarPage.qml`, `src/app/ui/adapters/led_bar_backend.py` |
| CLI | `src/avell_storm_rgb/adapters/cli/main.py` |

---

## Upstream local (análise cruzada)

- **`/home/jilles/git/ite8291r3-ctl/`** — mesma matriz de efeitos e notas sobre `color`/palette; secção *Effect property support matrix* no README.
- **`/home/jilles/git/ite8233-ledbar/ledbar`** — mesmos códigos de efeito, paleta, brilho e velocidade com re-aplicação implícita nos comandos do script.

Estes caminhos são opcionais no teu sistema; servem para comparar textos e comportamento quando o código aqui foi portado.
