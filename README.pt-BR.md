[🇺🇸 English](README.md) · 🇧🇷 Português

# avell-storm-rgb-control

⏱️ **Leitura:** ~5 min

> **TL;DR**
> - Controla o **teclado RGB** (ITE 8291) e a **barra de LED** (ITE 8233) dos notebooks Avell Storm no **Linux**, via USB.
> - Duas formas de usar: a CLI **`avell-storm-rgb`** e a GUI KDE/Plasma **`avell-storm-rgb-gui`**.
> - Instale com **uv**: `make sync-all`, depois `make gui` ou `make run ARGS='device list'`.

**Leia isto se…** você quer instalar e usar a ferramenta. Para o mapa dos docs, veja [docs/README](docs/README.pt-BR.md).

---

## 🧭 O que você ganha

| Dispositivo | IDs USB | Destaques |
|-------------|---------|-----------|
| **Teclado — ITE 8291** (rev 0.03) | `048d:6004`, `6006`, `ce00`, `600b` | 9 efeitos de firmware, paleta de 7 slots, cor sólida, cores **por tecla**, scripts de animação, **seguir a tela** |
| **Barra de LED — ITE 8233** | `048d:7000`, `7001`, ou nome do produto contém `8233` | 5 efeitos, cor estática, paletas de até 9 cores, brilho, velocidade |

- Lista completa de funcionalidades → [docs/FEATURE_MATRIX](docs/FEATURE_MATRIX.pt-BR.md).
- Como funciona por dentro → [docs/ARCHITECTURE](docs/ARCHITECTURE.pt-BR.md).

> [!NOTE]
> A árvore de comandos da CLI é **nova e semântica**. **Não** é compatível com os comandos antigos do `ite8291r3-ctl` / `ledbar`.

## 🛠️ Instalar

Este repo usa **só [uv](https://docs.astral.sh/uv/)** (`uv.lock` é o lockfile). Os alvos do `make` só chamam o `uv`.

```bash
make sync          # CLI + pytest                       (uv sync --group dev)
make sync-gui      # + GUI desktop (PySide6)            (uv sync --group dev --extra gui)
make sync-screen   # + dependências do follow-screen    (uv sync --group dev --extra screen)
make sync-all      # tudo
```

**Permissões USB:** você precisa de **root** ou de uma **regra udev**. Regras prontas para copiar estão em [docs/DEVELOPMENT](docs/DEVELOPMENT.pt-BR.md) (seção *Montar e rodar*).

## 🛠️ Usar a CLI

```bash
uv run avell-storm-rgb device list [--kind all|keyboard|led-bar]
uv run avell-storm-rgb keyboard [--debug] [--device BUS/ADDR] <subcomando> …
uv run avell-storm-rgb led-bar <subcomando> …
# ou: make run ARGS='device list'
```

**Teclado**

```bash
avell-storm-rgb keyboard power off
avell-storm-rgb keyboard brightness 25                  # 0–50
avell-storm-rgb keyboard effect wave -s 3 -d up -b 40   # velocidade 0–10, brilho 0–50
avell-storm-rgb keyboard effect aurora -r -c red        # -r (reativo) e -d (direção) são exclusivos
avell-storm-rgb keyboard solid-color --name white -b 10
avell-storm-rgb keyboard solid-color --rgb 255,45,23
avell-storm-rgb keyboard palette restore
avell-storm-rgb keyboard palette random
avell-storm-rgb keyboard palette set-slot 3 255,13,14
avell-storm-rgb keyboard demo-test-pattern
avell-storm-rgb keyboard freeze-animation
avell-storm-rgb keyboard follow-screen --fullscreen     # X11: tela cheia · Wayland: seletor de janela
avell-storm-rgb keyboard follow-screen --region 0,0,800,600   # só X11
avell-storm-rgb keyboard play-animation --file caminho/do/script --loop 3
avell-storm-rgb keyboard play-animation --file caminho/do/script --forever
avell-storm-rgb keyboard inspect --fw-version --brightness --power
```

> [!WARNING]
> Em `keyboard effect … -c NOME`, a cor é um **slot da paleta** (`red` = slot 1, `orange` = slot 2, …), não uma cor RGB fixa. Mude o slot com `palette set-slot` e o efeito muda junto.

**Scripts de animação:** `pos LINHA COLUNA r,g,b`, `apply`, `wait SEG`, `clear`, `brightness N`, `shift DLINHA DCOLUNA`, comentários com `#` e `/* */`. Formato e exemplos: [assets/animations/](assets/animations/README.pt-BR.md). Herdado do [ite8291r3-ctl](https://github.com/pobrn/ite8291r3-ctl).

**Barra de LED**

```bash
avell-storm-rgb led-bar power on
avell-storm-rgb led-bar power off
avell-storm-rgb led-bar color red
avell-storm-rgb led-bar color '#ff5500'
avell-storm-rgb led-bar palette rainbow --with-effect wave
avell-storm-rgb led-bar effect breathing
avell-storm-rgb led-bar brightness 75 --with-effect static    # 0–100
avell-storm-rgb led-bar speed 5 --with-effect breathing       # 1–10
avell-storm-rgb led-bar inspect
```

## 🛠️ Usar a GUI

```bash
make sync-gui && make gui
# ou: uv sync --extra gui && uv run avell-storm-rgb-gui
```

| Funcionalidade | Notas |
|----------------|-------|
| **Auto-connect** | Depois da varredura inicial, conecta o primeiro teclado e a primeira barra (ligado por padrão; **Settings**) |
| **Abas de dispositivo** | **Keyboard** / **LED bar** só aparecem enquanto aquele dispositivo está conectado |
| **Fechar para a bandeja** | Fechar esconde a janela (opção em **Settings**). Saia pelo menu da bandeja ou por **Settings → Quit application** |
| **Seguir a tela** | Roda sem o véu de ocupado. O **Stop** encerra a captura e apaga o indicador do portal. (Uma animação *forever* hoje mostra o véu — [dívida nº 7](docs/ARCHITECTURE.pt-BR.md)) |
| **Logs** | `--verbose` / `--debug`, ou `AVELL_STORM_RGB_LOG=debug` → DEBUG + tracebacks completos no stderr |

### ⚠️ A GUI precisa do Kirigami da distro

**O Kirigami não está no PyPI.** Instale pela sua distro (ou use um runtime Flatpak do KDE). O app põe `/usr/lib/qt6/qml`, `/usr/lib64/qt6/qml` e `/usr/share/qt6/qml` na frente do caminho de busca, porque o Qt embutido no PySide6 não procura lá.

```bash
test -d /usr/lib/qt6/qml/org/kde/kirigami && echo OK || echo "Instale kirigami (Qt6)"
test -d /usr/lib/qt6/qml/org/kde/desktop  && echo OK || echo "Instale qqc2-breeze-style"
```

| Distro | Pacotes |
|--------|---------|
| **Arch / CachyOS** | `kirigami`, `qqc2-breeze-style`, `breeze` |
| **Fedora KDE** | `kf6-kirigami`, `qqc2-breeze-style`, `breeze` |
| **Debian / Ubuntu** | `kirigami2`, `qqc2-breeze-style`, `breeze` (os nomes Qt6 podem ter `6`) |

**Sliders e botões com cara de Qt puro ("Fusion")?** O Kirigami carregou, mas falta o **estilo Breeze do Qt Quick Controls** (`org.kde.desktop`). Instale `qqc2-breeze-style` e reinicie o app.

- O app escolhe `org.kde.desktop` quando existe, senão `Fusion`.
- Um `QT_QUICK_CONTROLS_STYLE` definido pela sessão é respeitado.
- `AVELL_RGB_QQC2_STYLE` força um estilo (debug).

### ⚠️ O follow-screen precisa do extra `screen`

| Sessão | Como captura | Requisitos |
|--------|--------------|------------|
| **X11** | Janela raiz via `python-xlib` (região opcional) | X11. `BadMatch` costuma ser XWayland ou região fora da tela |
| **Wayland** | ScreenCast do **xdg-desktop-portal** + **PipeWire** (`pipewire-capture`) | Você **escolhe uma janela**, não o desktop inteiro. Precisa de um backend de portal (ex.: `xdg-desktop-portal-kde`) |

**Teste rápido no Wayland:** `make sync-screen`, depois `avell-storm-rgb keyboard follow-screen --fullscreen`. Aceite o portal, escolha uma janela e veja as teclas acompanharem. Pare com `Ctrl+C`.

## 🏗️ Arquitetura em 30 segundos

| Caminho | Papel |
|---------|-------|
| `src/avell_storm_rgb/domain/` | Lógica pura: parsing, DSL de animação, layout das teclas |
| `src/avell_storm_rgb/application/` | Casos de uso: abrir dispositivos, follow-screen |
| `src/avell_storm_rgb/infrastructure/usb/` | Drivers USB **fiéis ao protocolo**. Não mude bytes sem prova no hardware |
| `src/avell_storm_rgb/adapters/cli/` | CLI com `argparse` |
| `src/app/` | GUI PySide6 + QML. Todo USB passa por **uma única thread de worker** |

Detalhes, diagramas e dívidas conhecidas → [docs/ARCHITECTURE](docs/ARCHITECTURE.pt-BR.md). Agentes: comecem pelo [AGENTS.md](AGENTS.md).

## 🛠️ Desenvolvimento

`make test` roda os testes que não precisam de hardware. Setup, variáveis de ambiente e receitas → [docs/DEVELOPMENT](docs/DEVELOPMENT.pt-BR.md).

## 🧭 Licenças e créditos

**GPL-2.0-or-later** — veja [LICENSE](LICENSE). O projeto combina código baseado em:

| Upstream | Licença | Link |
|----------|---------|------|
| ite8291r3-ctl | GPL-2.0 | https://github.com/pobrn/ite8291r3-ctl |
| ite8233-ledbar (MIT, vários forks) | MIT | Parsing/protocolo espelhado em `src/avell_storm_rgb/`; veja NOTICE |

Veja o [NOTICE](NOTICE) para as atribuições. A GPLv2 vale para a obra combinada que você distribuir. As partes MIT continuam usáveis em termos compatíveis com a GPL. Para uso comercial, procure uma revisão jurídica adequada.
